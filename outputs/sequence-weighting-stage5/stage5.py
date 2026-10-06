"""v0.6 useful adaptation with a canonical no-adaptation selection candidate."""
import argparse
import gc
import itertools
import math
import platform
import random
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime,timezone
from pathlib import Path
sys.dont_write_bytecode=True
import torch
from torch.nn import functional as F
from core import make_data_lists
from model import Model, losses
from engine import (ROOT,HERE,CAPS,EPOCHS,read,write,sha,utc,event,data,weights,
                    orders,tensor_hash,evaluate,train_epoch,cpu_state)
from diagnostics import fit,validate_diagnostics

VARIANTS=['M','U']
POLICIES=['R','J']
GRID=[dict(lr=lr,wd=wd,clip=1.) for lr,wd in itertools.product([.00001,.00003,.0001],[.1,1.])]
TUNE=[(48371,701,96101),(50723,702,96102)]
CONFIRM=[(d,s,p) for d,p in [(52919,96201),(55049,96202),(57163,96203)] for s in [801,802,803]]
SOURCES=['stage5.py','engine.py','model.py','core.py','diagnostics.py','diagnostics_roundoff.py','check_stage5.py','PROTOCOL_STAGE5.md']
LIMIT_SECONDS=10800
MAX_EPOCHS=30
START_UTC=None


def pretraining_objective(logits,tokens,kinds,variant):
    logp=logits.log_softmax(-1)
    hard=-logp.gather(-1,tokens[:,1:,None]).squeeze(-1)
    shared=kinds==0
    objective=(hard*shared).sum()/shared.sum()
    if variant=='U':
        auxiliary=(kinds==1)|(kinds==2)
        objective=objective+(-logp[:,:,68:84].mean(-1)*auxiliary).sum()/auxiliary.sum()
    return objective


def pre_data(seed,variant):
    if variant=='S': return data(seed,pretrain=True)
    raw,meta=make_data_lists(seed,'mixed',2048,256,0)
    pool=random.Random(991).sample(range(32**3),32**3)
    keys={}
    for name,(rows,_) in raw.items():
        bounds=(0,4096) if name=='train' else (4096,8192)
        keys[name]=random.Random(seed+77).sample(pool[bounds[0]:bounds[1]],len(rows))
        for row,key in zip(rows,keys[name]):
            row[2:5]=[17+key//1024,17+key//32%32,17+key%32]
    meta.pop('sequence_keys'); meta['sequence_keys_by_split']=keys
    return {n:tuple(torch.tensor(x,dtype=torch.long) for x in pair) for n,pair in raw.items() if pair[0]},meta


def corpus(root,seed,variant=None):
    kind='adapt' if variant is None else 'preshared' if variant=='S' else 'premixed'
    folder=root/'corpora'/f'{kind}-{seed}'
    if folder.exists(): return torch.load(folder/'dataset.pt',weights_only=True),read(folder/'metadata.json')
    folder.mkdir(parents=True)
    ds,meta=data(seed) if variant is None else pre_data(seed,variant)
    meta['tensor_sha256']={n:tensor_hash(*pair) for n,pair in ds.items()}
    torch.save(ds,folder/'dataset.pt'); meta['file_sha256']=sha(folder/'dataset.pt')
    write(folder/'metadata.json',meta)
    return ds,meta


def check_budget(start):
    elapsed=time.perf_counter()-start
    utc_elapsed=0 if START_UTC is None else (datetime.now(timezone.utc)-START_UTC).total_seconds()
    if max(elapsed,utc_elapsed)>LIMIT_SECONDS:
        raise RuntimeError('Preregistered three-hour training-stage budget exhausted')


def baseline(root,width,layers,seed,preseed,variant,stage_start):
    name=f'{variant}-w{width}-s{seed}-d{preseed}'
    folder=root/'baselines'/name
    torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    model=Model(width,layers,40).cuda()
    if folder.exists():
        meta=read(folder/'result.json')
        assert sha(folder/'pretrained.pt')==meta['checkpoint_sha256']
        model.load_state_dict(torch.load(folder/'pretrained.pt',weights_only=True)); return model,meta
    folder.mkdir(parents=True)
    torch.cuda.reset_peak_memory_stats(); start=time.perf_counter()
    cold=cpu_state(model); torch.save(cold,folder/'cold.pt')
    cold_tensors={k:tensor_hash(v) for k,v in cold.items()}
    ds,dm=corpus(root,preseed,variant)
    opt=torch.optim.AdamW(model.parameters(),lr=.0003,weight_decay=.1)
    order=orders(seed,2048,4); torch.save(order,folder/'orders.pt')
    history=[]; records=[]
    for e in range(1,5):
        check_budget(stage_start); model.train(); norms=[]; objectives=[]
        for ids in order[e-1].split(32):
            tokens,kinds=(x[ids].cuda() for x in ds['train'])
            objective=pretraining_objective(model(tokens[:,:-1]),tokens,kinds,variant)
            opt.zero_grad(set_to_none=True); objective.backward()
            norm=torch.nn.utils.clip_grad_norm_(model.parameters(),5.)
            if not torch.isfinite(objective) or not torch.isfinite(norm): raise FloatingPointError('Pretraining nonfinite')
            opt.step(); norms.append(float(norm)); objectives.append(float(objective.detach()))
        tr,trr=evaluate(model,ds['train']); va,var=evaluate(model,ds['validation'])
        history.append(dict(epoch=e,train=tr,validation=va,training_objective=sum(objectives)/len(objectives),
                            gradient_norm_mean=sum(norms)/len(norms),gradient_clip_fraction=sum(x>5 for x in norms)/len(norms)))
        records.append(dict(epoch=e,train=trr,validation=var))
    torch.save(cpu_state(model),folder/'pretrained.pt'); torch.save(records,folder/'sequence_losses.pt')
    torch.cuda.synchronize()
    meta=dict(variant=variant,width=width,layers=layers,seed=seed,data_seed=preseed,history=history,
        checkpoint_sha256=sha(folder/'pretrained.pt'),cold_sha256=sha(folder/'cold.pt'),cold_tensor_sha256=cold_tensors,
        data=dm,source_sha256=read(root/'source_manifest.json'),batch_order_sha256=tensor_hash(order),
        elapsed_seconds=time.perf_counter()-start,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
        peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
    write(folder/'result.json',meta); event(root,'pretraining_complete',name=name)
    return model,meta


def config(phase,v,w,l,d,s,p,i):
    return dict(name=f'{phase}-{v}-w{w}-d{d}-s{s}-g{i:02d}',phase=phase,variant=v,width=w,layers=l,
                data_seed=d,seed=s,pretrain_seed=p,grid_index=i,**GRID[i],epochs=MAX_EPOCHS)


def tuning_schedule():
    return [dict(config('tune',v,w,l,d,s,p,i),name=config('tune',v,w,l,d,s,p,i)['name']+'-'+arm,arm=arm)
        for w,l in CAPS for d,s,p in TUNE for v in VARIANTS for i in range(len(GRID)) for arm in ['random','uniform']]


def select(root):
    inputs=[]; input_hashes={}
    for c in tuning_schedule():
        path=root/'runs'/c['name']/'history.json'; input_hashes[str(path.relative_to(root))]=sha(path)
        for h in read(path):
            inputs.append(dict(variant=c['variant'],width=c['width'],data_seed=c['data_seed'],seed=c['seed'],
                grid_index=c['grid_index'],arm=c['arm'],epoch=h['epoch'],validation_nll=h['validation']['loss']))
    decisions={}; all_scores={}; schedule=[]
    for policy in POLICIES:
        decisions[policy]={}
        for v in VARIANTS:
            decisions[policy][v]={}
            for w,l in CAPS:
                # One baseline candidate per capacity/condition, not repeated grid candidates.
                scores=[]
                for d,s,p in TUNE:
                    copies=[x['validation_nll'] for x in inputs if x['variant']==v and x['width']==w
                            and x['data_seed']==d and x['seed']==s and x['epoch']==0]
                    assert len(copies)==2*len(GRID) and len(set(copies))==1
                    scores.append(copies[0])
                candidates=[dict(grid_index=None,lr=None,wd=None,clip=None,epoch=0,
                                 validation_nll=sum(scores)/len(scores),scores=scores)]
                for i,g in enumerate(GRID):
                    for e in EPOCHS:
                        scores=[x['validation_nll'] for x in inputs if x['variant']==v and x['width']==w and
                                x['grid_index']==i and x['epoch']==e and (policy=='J' or x['arm']=='random')]
                        assert len(scores)==(4 if policy=='J' else 2)
                        candidates.append(dict(grid_index=i,**g,epoch=e,validation_nll=sum(scores)/len(scores),scores=scores))
                chosen=min(candidates,key=selection_key)
                decisions[policy][v][str(w)]=chosen; all_scores[f'{policy}-{v}-{w}']=candidates
    for w,l in CAPS:
        for d,s,p in CONFIRM:
            for v in VARIANTS:
                indices={decisions[policy][v][str(w)]['grid_index'] for policy in POLICIES}-{None}
                for i in sorted(indices):
                    for arm in ['random','uniform']:
                        c=config('confirm',v,w,l,d,s,p,i)
                        schedule.append(dict(c,name=c['name']+'-'+arm,arm=arm))
    return dict(criterion={'R':'Primary: mean random-arm validation NLL over two fresh tuning corpus/model pairs',
                           'J':'Secondary: joint random/uniform mean validation NLL over the same tuning pairs'},
        test_used=False,confirmation_used=False,tie_order=['full precision validation NLL','earliest epoch','LR ascending','WD ascending'],
        inputs=inputs,input_hashes=input_hashes,decisions=decisions,all_scores=all_scores,
        run_schedule=schedule,planned_confirmation=len(schedule),baseline_test_evaluations=54)


def selection_key(candidate):
    return (candidate['validation_nll'],candidate['epoch'],candidate['lr'] or 0.,candidate['wd'] or 0.)


def evaluate_initial(root,v,w,l,d,s,p,stage_start):
    check_budget(stage_start); start=time.perf_counter()
    name=f'{v}-w{w}-d{d}-s{s}'
    folder=root/'initial-evaluations'/name; folder.mkdir(parents=True,exist_ok=False)
    model,pre=baseline(root,w,l,s,p,v,stage_start)
    ds,dm=corpus(root,d); metrics={}; records={}
    selection_hash=sha(root/'selection.json')
    torch.cuda.reset_peak_memory_stats()
    for split in ['train','validation','test']:
        if split=='test': event(root,'baseline_test_evaluation',name=name,epoch=0,selection_sha256=selection_hash)
        metrics[split],records[split]=evaluate(model,ds[split])
    torch.save(records,folder/'sequence_losses.pt'); torch.cuda.synchronize()
    write(folder/'result.json',dict(name=name,variant=v,width=w,layers=l,data_seed=d,seed=s,pretrain_seed=p,
        parameters=sum(q.numel() for q in model.parameters()),baseline_sha256=pre['checkpoint_sha256'],
        data_sha256=dm['tensor_sha256'],source_sha256=read(root/'source_manifest.json'),selection_sha256=selection_hash,
        metrics=metrics,sequence_file_sha256=sha(folder/'sequence_losses.pt'),elapsed_seconds=time.perf_counter()-start,
        peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20))
    del model; gc.collect()


def run(root,c,stage_start):
    folder=root/'runs'/c['name']; folder.mkdir(parents=True,exist_ok=False); start=time.perf_counter()
    event(root,'run_start',name=c['name'])
    c=dict(c,source_sha256=read(root/'source_manifest.json'),
           selection_sha256=sha(root/'selection.json') if c['phase']=='confirm' else None)
    try:
        check_budget(stage_start)
        model,pre=baseline(root,c['width'],c['layers'],c['seed'],c['pretrain_seed'],c['variant'],stage_start)
        ds,dm=corpus(root,c['data_seed'])
        assert set(sum(dm['sequence_keys_by_split'].values(),[])).isdisjoint(sum(pre['data']['sequence_keys_by_split'].values(),[]))
        w=weights(c['seed'],c['arm']); order=orders(c['seed'])
        torch.save(dict(weights=w,orders=order),folder/'assignment.pt')
        c.update(parameters=sum(p.numel() for p in model.parameters()),baseline_sha256=pre['checkpoint_sha256'],
            data_sha256=dm['tensor_sha256'],weight_sha256=tensor_hash(w),batch_order_sha256=tensor_hash(order))
        write(folder/'config.json',c)
        opt=torch.optim.AdamW(model.parameters(),lr=c['lr'],weight_decay=c['wd'])
        torch.cuda.reset_peak_memory_stats()
        tr0,initial=evaluate(model,ds['train']); va0,vr0=evaluate(model,ds['validation'])
        te0=ter0=None
        if c['phase']=='confirm':
            initial_folder=root/'initial-evaluations'/f'{c["variant"]}-w{c["width"]}-d{c["data_seed"]}-s{c["seed"]}'
            saved=read(initial_folder/'result.json'); rec=torch.load(initial_folder/'sequence_losses.pt',weights_only=True)
            assert saved['baseline_sha256']==pre['checkpoint_sha256']
            for split,record in [('train',initial),('validation',vr0)]:
                assert all(torch.equal(value,rec[split][key]) for key,value in record.items())
            te0,ter0=saved['metrics']['test'],rec['test']
        history=[dict(epoch=0,train=tr0,validation=va0,p_star=dict(p=None,reason='no_adaptation'),test=te0,
                      total_gain=0.,negative_gain_fraction=0.)]
        records=[dict(epoch=0,train=initial,validation=vr0,test=ter0)]; stats=[]; checkpoint_hashes={}
        for e in range(1,MAX_EPOCHS+1):
            check_budget(stage_start)
            stat=train_epoch(model,opt,ds['train'],w,order[e-1],c['clip']); stats.append(dict(epoch=e,**stat))
            if e not in EPOCHS: continue
            tr,trrec=evaluate(model,ds['train']); va,varec=evaluate(model,ds['validation'])
            te=terec=None
            if c['phase']=='confirm':
                event(root,'test_evaluation',name=c['name'],epoch=e,selection_sha256=c['selection_sha256'])
                te,terec=evaluate(model,ds['test'])
            fitted=fit(w,initial['loss']-trrec['loss'])
            history.append(dict(epoch=e,train=tr,validation=va,test=te,p_star=fitted,total_gain=fitted['total_gain'],
                negative_gain_fraction=fitted['negative_gain_fraction'],clipping_cumulative=sum(x['gradient_clip_fraction'] for x in stats)/e,**stat))
            records.append(dict(epoch=e,train=trrec,validation=varec,test=terec))
            checkpoint=folder/f'model-e{e:02d}.pt'; torch.save(cpu_state(model),checkpoint)
            checkpoint_hashes[str(e)]=sha(checkpoint)
            write(folder/'history.json',history); write(folder/'epoch_stats.json',stats)
            torch.save(dict(weights=w,checkpoints=records),folder/'sequence_losses.pt')
        torch.cuda.synchronize()
        result=dict(config=c,history=history,epoch_stats=stats,checkpoint_sha256=checkpoint_hashes,
            status='complete',completed_utc=utc(),elapsed_seconds=time.perf_counter()-start,
            peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
        write(folder/'result.json',result); event(root,'run_complete',name=c['name'],seconds=result['elapsed_seconds'])
        print(f'DONE {c["name"]} seconds={result["elapsed_seconds"]:.2f}',flush=True)
        del model,opt; gc.collect()
    except Exception:
        write(folder/'failure.json',dict(config=c,utc=utc(),traceback=traceback.format_exc()))
        event(root,'run_failed',name=c['name']); raise


def validate():
    validate_diagnostics()
    for d,s,p in TUNE+CONFIRM:
        ds,meta=data(d); hidden,_=data(d,include_test=False)
        for split in ['train','validation']:
            assert all(torch.equal(a,b) for a,b in zip(ds[split],hidden[split]))
        a,ma=pre_data(p,'M'); b,mb=pre_data(p,'U'); ss,ms=pre_data(p,'S')
        assert ma==mb
        for split in a: assert all(torch.equal(x,y) for x,y in zip(a[split],b[split]))
        keys=sum(meta['sequence_keys_by_split'].values(),[])+sum(ma['sequence_keys_by_split'].values(),[])
        assert len(keys)==len(set(keys))
        assert ma['sequence_keys_by_split']==ms['sequence_keys_by_split']
        assert len(weights(s,'random').unique())==512
    # Independent analytic derivative verifies exact target support and normalization.
    tokens,kinds=(t[:2].clone() for t in a['train'])
    logits=torch.randn(2,40,84,dtype=torch.float64,generator=torch.Generator().manual_seed(17),requires_grad=True)
    m=pretraining_objective(logits,tokens,kinds,'M'); u=pretraining_objective(logits,tokens,kinds,'U')
    gm=torch.autograd.grad(m,logits,retain_graph=True)[0]; gu=torch.autograd.grad(u,logits)[0]
    mask=(kinds==1)|(kinds==2); target=torch.zeros_like(logits); target[:,:,68:84]=1/16
    expected=(logits.detach().softmax(-1)-target)*mask[:,:,None]/mask.sum()
    assert torch.allclose(gu-gm,expected,atol=1e-12,rtol=0)
    assert torch.equal(gm[mask],torch.zeros_like(gm[mask]))
    changed=tokens.clone(); changed[:,1:][mask]=68
    assert torch.equal(pretraining_objective(logits,tokens,kinds,'U'),pretraining_objective(logits,changed,kinds,'U'))
    uniform=torch.zeros_like(logits)
    assert abs(float(pretraining_objective(uniform,tokens,kinds,'U'))-2*math.log(84))<1e-12
    return dict(status='PASS',utc=utc(),checks=['full data/test-toggle equality','M/U exact pretraining tokens and labels',
        'disjoint split/phase namespaces','shared pretrain namespace pairing','unique random weights',
        'soft-target objective analytic gradient and exact answer support','hard nonshared targets unused at fixed logits',
        'signed gain/component/reference diagnostics'])


def historical_manifest():
    oldroot=ROOT/'work/runs/baseline-v05-20260929-01'
    oldreport=ROOT/'outputs/sequence-weighting-stage4/results-baseline-v05-20260929-01-r2'
    result=read(oldroot/'historical_manifest.json')
    result.update({str((oldroot/n).relative_to(ROOT)):h for n,h in read(oldreport/'raw-manifest.json').items()})
    for path in oldroot.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            key=str(path.relative_to(ROOT))
            if key not in result: result[key]=sha(path)
    for path in (ROOT/'outputs/sequence-weighting-stage4').rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts: result[str(path.relative_to(ROOT))]=sha(path)
    return result


def prepare(root):
    root.mkdir(parents=True,exist_ok=False); (root/'source').mkdir()
    manifest={n:sha(HERE/n) for n in SOURCES}
    for n in SOURCES: shutil.copy2(HERE/n,root/'source'/n)
    write(root/'source_manifest.json',manifest); event(root,'protocol_source_frozen',sha256=manifest)
    check=subprocess.run([sys.executable,'-m','pip','check'],check=True,capture_output=True,text=True)
    (root/'PACKAGE_CHECK.txt').write_text(check.stdout,encoding='utf-8')
    (root/'environment-lock.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True),encoding='utf-8')
    write(root/'runtime.json',dict(utc=utc(),torch=torch.__version__,python=platform.python_version(),
        gpu=torch.cuda.get_device_name(0),gpu_total_mib=torch.cuda.get_device_properties(0).total_memory/2**20,
        root=str(ROOT),precision='float32',threads=4,budget_seconds=LIMIT_SECONDS))
    write(root/'VALIDATION.json',validate()); write(root/'historical_manifest.json',historical_manifest())
    from check_stage5 import checks
    write(root/'SELECTION_CHECKS.json',checks())
    write(root/'tuning_schedule.json',tuning_schedule())
    assert len(tuning_schedule())==144
    print('PREPARED: checks PASS; 144 tuning runs; <=216 confirmation runs; 54 baseline tests; max 3 hours.',flush=True)


def main():
    global START_UTC
    ap=argparse.ArgumentParser(); ap.add_argument('--run-id',required=True)
    ap.add_argument('--phase',choices=['validate','prepare','experiment'],required=True); args=ap.parse_args()
    torch.set_num_threads(4)
    if args.phase=='validate': print(validate(),flush=True); return
    assert Path(args.run_id).name==args.run_id
    torch.backends.cudnn.benchmark=False; torch.backends.cuda.matmul.allow_tf32=False; torch.backends.cudnn.allow_tf32=False
    if not torch.cuda.is_available(): raise RuntimeError('Local WSL CUDA required')
    root=ROOT/'work/runs'/args.run_id
    if args.phase=='prepare': prepare(root); return
    assert read(root/'source_manifest.json')=={n:sha(HERE/n) for n in SOURCES}
    analysis_manifest=read(root/'analysis_source_manifest.json')
    assert analysis_manifest=={n:sha(HERE/n) for n in analysis_manifest}
    assert all(sha(root/'analysis-source'/n)==h for n,h in analysis_manifest.items())
    assert read(root/'ANALYSIS_CHECKS.json')['status']=='PASS'
    assert not (root/'runs').exists(), 'Refuse implicit resume/overwrite'
    start=time.perf_counter(); START_UTC=datetime.now(timezone.utc); event(root,'experiment_started')
    try:
        for c in read(root/'tuning_schedule.json'): run(root,c,start)
        selection=select(root); selection['frozen_utc']=utc(); write(root/'selection.json',selection)
        event(root,'selection_frozen',sha256=sha(root/'selection.json'),planned_confirmation=selection['planned_confirmation'])
        print(f'SELECTION FROZEN; {selection["planned_confirmation"]} confirmation runs.',flush=True)
        for w,l in CAPS:
            for d,s,p in CONFIRM:
                for v in VARIANTS: evaluate_initial(root,v,w,l,d,s,p,start)
        for c in selection['run_schedule']: run(root,c,start)
        check_budget(start)
        write(root/'COMPLETE.json',dict(utc=utc(),tuning_runs=144,confirmation_runs=selection['planned_confirmation'],
            elapsed_seconds=time.perf_counter()-start,utc_elapsed_seconds=(datetime.now(timezone.utc)-START_UTC).total_seconds(),
            pretraining_checkpoints=66,baseline_test_evaluations=54))
        event(root,'experiment_complete')
    except Exception:
        write(root/'EXPERIMENT_FAILURE.json',dict(utc=utc(),traceback=traceback.format_exc(),
            elapsed_seconds=time.perf_counter()-start,utc_elapsed_seconds=(datetime.now(timezone.utc)-START_UTC).total_seconds()))
        event(root,'experiment_failed'); raise


if __name__=='__main__': main()
