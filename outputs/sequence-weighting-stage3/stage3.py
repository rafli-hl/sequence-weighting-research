"""v0.4: fresh paired confirmation of frozen Stage 3 policies."""
import argparse
import gc
import json
import platform
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
sys.dont_write_bytecode=True
import torch
from engine import (ROOT,HERE,CAPS,GRID,EPOCHS,TUNE,read,write,sha,utc,event,data,
                    corpus,baseline,weights,orders,tensor_hash,evaluate,train_epoch,cpu_state)
from diagnostics import fit,validate_diagnostics

OLD=ROOT/'work/runs/generalization-v03-20260928-01'
OLD_REPORT=ROOT/'outputs/sequence-weighting-stage2/results-generalization-v03-20260928-01-r2'
REPS=[(d,s,p) for d,p in [(22360,94101),(24494,94102),(26457,94103)] for s in [301,302,303]]
SOURCES=['stage3.py','engine.py','core.py','model.py','diagnostics.py','PROTOCOL_STAGE3.md']
LIMIT_SECONDS=7200


def tuning_selection():
    extracted, input_hashes = [], {}
    for width,_ in CAPS:
        for i,setting in enumerate(GRID):
            for d,s,_ in TUNE:
                for arm in ['random','uniform']:
                    path=OLD/'runs'/f'tune-w{width}-d{d}-s{s}-g{i:02d}-{arm}'/'history.json'
                    input_hashes[str(path.relative_to(ROOT))]=sha(path)
                    h=read(path)
                    for row in h:
                        extracted.append(dict(width=width,grid_index=i,data_seed=d,seed=s,arm=arm,
                                              epoch=row['epoch'],validation_nll=row['validation']['loss']))
    policies={'F':{},'J':{},'R':{}}
    all_scores={}
    old=read(OLD/'selection.json')
    for width,_ in CAPS:
        policies['F'][str(width)]=dict(grid_index=6,**GRID[6],epoch=60)
        for policy,arms in [('J',['random','uniform']),('R',['random'])]:
            candidates=[]
            for i,setting in enumerate(GRID):
                for epoch in EPOCHS:
                    scores=[x['validation_nll'] for x in extracted if x['width']==width and
                            x['grid_index']==i and x['epoch']==epoch and x['arm'] in arms]
                    assert len(scores)==2*len(arms)
                    candidates.append(dict(grid_index=i,**setting,epoch=epoch,
                                           validation_nll=sum(scores)/len(scores),scores=scores))
            chosen=min(candidates,key=lambda x:(x['validation_nll'],x['epoch'],x['lr'],x['wd'],x['clip'] is None))
            policies[policy][str(width)]=chosen
            all_scores[f'{policy}-{width}']=candidates
            if policy=='J':
                previous=old['decisions'][str(width)]['selected']
                assert all(chosen[k]==previous[k] for k in ['grid_index','lr','wd','clip','epoch','validation_nll'])
    configs={str(w):sorted({policies[p][str(w)]['grid_index'] for p in policies}) for w,_ in CAPS}
    schedule=[]
    for w,l in CAPS:
        for d,s,p in REPS:
            for i in configs[str(w)]:
                for arm in ['random','uniform']:
                    schedule.append(dict(name=f'confirm-w{w}-d{d}-s{s}-g{i:02d}-{arm}',width=w,layers=l,
                        data_seed=d,seed=s,pretrain_seed=p,grid_index=i,**GRID[i],arm=arm,
                        policies=[policy for policy in policies if policies[policy][str(w)]['grid_index']==i],
                        epochs=60,test_epochs=EPOCHS))
    assert len(schedule)<=144
    return dict(reused_tuning=True,test_used=False,confirmation_used=False,
                criterion={'J':'mean random + uniform validation NLL','R':'random-only validation NLL'},
                tie_order=['score full precision','earliest epoch','ascending LR','ascending WD','clip 1 before disabled'],
                inputs=extracted,input_hashes=input_hashes,all_scores=all_scores,policies=policies,
                schedules={'EJ':{w:c['epoch'] for w,c in policies['J'].items()},
                           'ER':{w:c['epoch'] for w,c in policies['R'].items()}},
                unique_configs=configs,run_schedule=schedule,planned_runs=len(schedule))


def validate(root):
    for d,_,p in REPS:
        full,m=data(d); hidden,_=data(d,include_test=False); pre,pm=data(p,pretrain=True)
        for split in ['train','validation']:
            assert all(torch.equal(a,b) for a,b in zip(full[split],hidden[split]))
            assert torch.equal(full[split][0][:,1:],hidden[split][0][:,1:])
        keys=sum(m['sequence_keys_by_split'].values(),[])+sum(pm['sequence_keys_by_split'].values(),[])
        assert len(keys)==len(set(keys))
        for tokens,kinds in full.values():
            assert tokens.shape[1]==41 and kinds.shape[1]==40
            assert all(((kinds==j).sum(1)==4).all() for j in range(3))
    for s in [301,302,303]:
        assert len(weights(s,'random').unique())==512, 'Rank-kernel unique weights assumption'
        assert torch.equal(orders(s),orders(s))
    validate_diagnostics()
    write(root/'VALIDATION.json',dict(status='PASS',utc=utc(),checks=[
        'complete token/label/type test-toggle equality','pretrain/adaptation/validation/test disjoint keys',
        'four answers per component','random weight ranks unique','signed component decomposition identities',
        'undefined negative-component gain and uniform behavior','factorial contrast arithmetic']))


def historical_manifest():
    preserved={x['path']:x['sha256'] for x in read(ROOT/'migration/source-files.json')
               if x['path'].startswith(('outputs/sequence-weighting-pilot/','work/runs/'))}
    preserved.update({str((OLD/rel).relative_to(ROOT)):h for rel,h in read(OLD_REPORT/'raw-manifest.json').items()})
    for path in (ROOT/'outputs/sequence-weighting-stage2').rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            preserved[str(path.relative_to(ROOT))]=sha(path)
    return preserved


def prepare(root):
    root.mkdir(parents=True,exist_ok=False)
    (root/'source').mkdir()
    manifest={name:sha(HERE/name) for name in SOURCES}
    for name in SOURCES: shutil.copy2(HERE/name,root/'source'/name)
    write(root/'source_manifest.json',manifest)
    event(root,'protocol_source_frozen',sha256=manifest)
    check=subprocess.run([sys.executable,'-m','pip','check'],check=True,capture_output=True,text=True)
    (root/'PACKAGE_CHECK.txt').write_text(check.stdout,encoding='utf-8')
    lock=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True)
    (root/'environment-lock.txt').write_text(lock,encoding='utf-8')
    write(root/'runtime.json',dict(utc=utc(),root=str(ROOT),torch=torch.__version__,python=platform.python_version(),
          gpu=torch.cuda.get_device_name(0),gpu_total_mib=torch.cuda.get_device_properties(0).total_memory/2**20,
          precision='float32',threads=4,budget_seconds=LIMIT_SECONDS))
    validate(root)
    selection=tuning_selection()
    selection['frozen_utc']=utc()
    write(root/'selection.json',selection)
    event(root,'selection_frozen',sha256=sha(root/'selection.json'),planned_runs=selection['planned_runs'])
    write(root/'historical_manifest.json',historical_manifest())
    print(json.dumps(dict(planned_runs=selection['planned_runs'],policies=selection['policies'],
                          schedules=selection['schedules'],validation='PASS')),flush=True)


def run(root,config,stage_start):
    folder=root/'runs'/config['name']
    folder.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter()
    event(root,'run_start',name=config['name'])
    config=dict(config,source_sha256=read(root/'source_manifest.json'),selection_sha256=sha(root/'selection.json'))
    try:
        if time.perf_counter()-stage_start>LIMIT_SECONDS: raise RuntimeError('Preregistered two-hour budget exhausted')
        model,pre=baseline(root,config['width'],config['layers'],config['seed'],config['pretrain_seed'])
        ds,dm=corpus(root,config['data_seed'])
        assert set(sum(dm['sequence_keys_by_split'].values(),[])).isdisjoint(sum(pre['data']['sequence_keys_by_split'].values(),[]))
        w=weights(config['seed'],config['arm']); order=orders(config['seed'])
        torch.save(dict(weights=w,orders=order),folder/'assignment.pt')
        config.update(parameters=sum(p.numel() for p in model.parameters()),baseline_sha256=pre['checkpoint_sha256'],
            data_sha256=dm['tensor_sha256'],weight_sha256=tensor_hash(w),batch_order_sha256=tensor_hash(order))
        write(folder/'config.json',config)
        opt=torch.optim.AdamW(model.parameters(),lr=config['lr'],weight_decay=config['wd'])
        torch.cuda.reset_peak_memory_stats()
        tr0,initial=evaluate(model,ds['train']); va0,vr0=evaluate(model,ds['validation'])
        history=[dict(epoch=0,train=tr0,validation=va0,p_star=dict(p=None,reason='no_adaptation'),
                      total_gain=0.,negative_gain_fraction=0.,test=None)]
        records=[dict(epoch=0,train=initial,validation=vr0,test=None)]
        stats=[]; checkpoint_hashes={}
        for e in range(1,61):
            if time.perf_counter()-stage_start>LIMIT_SECONDS: raise RuntimeError('Preregistered two-hour budget exhausted')
            stat=train_epoch(model,opt,ds['train'],w,order[e-1],config['clip'])
            stats.append(dict(epoch=e,**stat))
            if e not in EPOCHS: continue
            tr,trrec=evaluate(model,ds['train']); va,varec=evaluate(model,ds['validation'])
            event(root,'test_evaluation',name=config['name'],epoch=e,selection_sha256=config['selection_sha256'])
            te,terec=evaluate(model,ds['test'])
            fitted=fit(w,initial['loss']-trrec['loss'])
            history.append(dict(epoch=e,train=tr,validation=va,test=te,p_star=fitted,
                                total_gain=fitted['total_gain'],negative_gain_fraction=fitted['negative_gain_fraction'],
                                clipping_cumulative=sum(x['gradient_clip_fraction'] for x in stats)/e,**stat))
            records.append(dict(epoch=e,train=trrec,validation=varec,test=terec))
            checkpoint=folder/f'model-e{e:02d}.pt'
            torch.save(cpu_state(model),checkpoint)
            checkpoint_hashes[str(e)]=sha(checkpoint)
            write(folder/'history.json',history); write(folder/'epoch_stats.json',stats)
            torch.save(dict(weights=w,checkpoints=records),folder/'sequence_losses.pt')
        torch.cuda.synchronize()
        result=dict(config=config,history=history,epoch_stats=stats,checkpoint_sha256=checkpoint_hashes,
                    pretrain_validation=pre['history'][-1]['validation'],status='complete',completed_utc=utc(),
                    elapsed_seconds=time.perf_counter()-start,
                    peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
        write(folder/'result.json',result)
        event(root,'run_complete',name=config['name'],seconds=result['elapsed_seconds'])
        print(f'DONE {config["name"]} seconds={result["elapsed_seconds"]:.2f}',flush=True)
        del opt,model; gc.collect()
    except Exception:
        write(folder/'failure.json',dict(config=config,utc=utc(),traceback=traceback.format_exc()))
        event(root,'run_failed',name=config['name'])
        raise


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--run-id',required=True)
    ap.add_argument('--phase',choices=['prepare','experiment'],required=True)
    args=ap.parse_args()
    assert Path(args.run_id).name==args.run_id
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark=False
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    if not torch.cuda.is_available(): raise RuntimeError('Local WSL CUDA required')
    root=ROOT/'work/runs'/args.run_id
    if args.phase=='prepare': prepare(root); return
    assert read(root/'source_manifest.json')=={name:sha(HERE/name) for name in SOURCES}
    assert not (root/'runs').exists(), 'No implicit resume: preserve existing runs'
    selection=read(root/'selection.json')
    assert {k:v for k,v in selection.items() if k!='frozen_utc'}==tuning_selection()
    start=time.perf_counter(); event(root,'experiment_started',planned_runs=selection['planned_runs'])
    for config in selection['run_schedule']: run(root,config,start)
    write(root/'COMPLETE.json',dict(utc=utc(),completed_runs=selection['planned_runs'],
          elapsed_seconds=time.perf_counter()-start,pretraining_checkpoints=27))
    event(root,'experiment_complete',completed_runs=selection['planned_runs'])


if __name__=='__main__': main()
