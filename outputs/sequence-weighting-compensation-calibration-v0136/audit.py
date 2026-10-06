"""Independent arithmetic/data/checkpoint audit; never trains a model."""
import time
import argparse
import csv
import hashlib
import math
import random
import statistics
import os
import platform
import sys
from pathlib import Path
sys.dont_write_bytecode=True
from common import (HERE,RUN,OUT,ARMS,CORPORA,PRESEEDS,MODEL_SEEDS,Guard,require,read,write,
                    sha,utc,pairs,pair_name,binding,check_binding,verify_manifest,resources)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('audit',))
    parser.add_argument('--admission',type=Path,required=True)
    args=parser.parse_args(); guard=Guard(args.admission); guard.check(disk=True)
    sys.path.insert(0,str(HERE/'vendor'))
    import torch
    from torch.nn import functional as F
    from model import Model
    import numpy as np
    require(np.__version__=='2.2.6','Unreviewed audit NumPy')
    torch.set_num_threads(4)
    require(torch.cuda.is_available(),'Audit requires CUDA; no CPU fallback')
    require(torch.__version__=='2.7.0+cu126' and torch.version.cuda=='12.6' and platform.python_version()=='3.12.3','Unreviewed audit environment')
    require(torch.cuda.get_device_name(0)=='NVIDIA GeForce RTX 3050 Laptop GPU','Unreviewed audit GPU')
    require(os.environ.get('CUBLAS_WORKSPACE_CONFIG') is None,'Inherited audit CUBLAS policy')
    torch.backends.cudnn.benchmark=False
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(False)
    require((RUN/'ADAPT_COMPLETE.json').is_file(),'Missing complete 12-trajectory run')
    require(read(RUN/'ADAPT_COMPLETE.json')['trajectory_manifest_sha256']==sha(RUN/'TRAJECTORY_MANIFEST.json'),
            'Trajectory manifest changed')
    require(read(RUN/'PRETRAIN_COMPLETE.json')['baseline_manifest_sha256']==sha(RUN/'BASELINE_MANIFEST.json'),
            'Baseline manifest changed')
    require(read(RUN/'PREPARE_COMPLETE.json')['input_manifest_sha256']==sha(RUN/'INPUT_MANIFEST.json'),
            'Input manifest changed')
    for folder,manifest in (('inputs','INPUT_MANIFEST.json'),('baselines','BASELINE_MANIFEST.json'),
                            ('trajectories','TRAJECTORY_MANIFEST.json')):
        guard.check(); check_binding(RUN/folder,read(RUN/manifest)); guard.check()
    OUT.mkdir(exist_ok=False)
    def load(p): return torch.load(p,map_location='cpu',weights_only=True)
    def thash(*tensors):
        h=hashlib.sha256()
        for tensor in tensors:
            v=tensor.detach().cpu().contiguous()
            h.update(str((tuple(v.shape),str(v.dtype))).encode('utf-8')); h.update(v.numpy().tobytes())
        return h.hexdigest()
    discrepancy_checks=[]
    def close(a,b,tolerance=2e-6):
        aa=torch.as_tensor(a,dtype=torch.float64).detach().cpu(); bb=torch.as_tensor(b,dtype=torch.float64).detach().cpu()
        require(aa.shape==bb.shape and torch.isfinite(aa).all().item() and torch.isfinite(bb).all().item(),
                'Audit numeric shape/nonfinite mismatch')
        error=(aa-bb).abs().max().item()
        discrepancy_checks.append((tolerance,error))
        require(error<=tolerance,'Independent numerical comparison failed')
    def regenerate(seed,pre=False):
        # Independently implement documented RNG consumption, namespaces and G1
        # relabeling; never call core.make_data_lists or engine.data/pre_data.
        sizes=(2048,256,0) if pre else (512,256,512)
        rng=random.Random(seed); permutations=[rng.sample(range(16),16) for _ in range(16)]
        original_keys=rng.sample(range(32768),sum(sizes))
        rows=[]; masks=[]
        for index,key in enumerate(original_keys):
            kinds=[0]*4+[1]*4+[2]*4; rng.shuffle(kinds)
            queries=rng.sample(range(16),12); random_answers=[rng.randrange(16) for _ in queries]
            group=index%16; row=[0,group+1,17+key//1024,17+key//32%32,17+key%32]; mask=[-1]*5
            for kind,x,instance in zip(kinds,queries,random_answers):
                y=(x+1)%16 if kind==0 else permutations[group if pre else 0][x] if kind==1 else instance
                row.extend((49+kind,52+x,68+y)); mask.extend((-1,-1,kind))
            rows.append(row); masks.append(mask[1:])
        pool=random.Random(991).sample(range(32768),32768); output={}; offset=0
        for split,size in zip(('train','validation','test'),sizes):
            if not size: continue
            bounds=((0,4096) if split=='train' else (4096,8192)) if pre else {
                'train':(8192,16384),'validation':(16384,24576),'test':(24576,32768)}[split]
            keys=random.Random(seed+77).sample(pool[bounds[0]:bounds[1]],size)
            selected=rows[offset:offset+size]
            for row,key in zip(selected,keys): row[2:5]=[17+key//1024,17+key//32%32,17+key%32]
            output[split]=(torch.tensor(selected,dtype=torch.long),torch.tensor(masks[offset:offset+size],dtype=torch.long))
            offset+=size
        return output
    @torch.no_grad()
    def reevaluate(obj,ds):
        output={}; metrics={}
        obj.eval()
        for split,(all_tokens,all_kinds) in ds.items():
            comps=[]; accuracies=[]; totals=[]
            for start in range(0,len(all_tokens),32):
                guard.check()
                x=all_tokens[start:start+32].cuda(); labels=all_kinds[start:start+32].cuda()
                logits=obj(x[:,:-1]); targets=x[:,1:]
                nll=-logits.log_softmax(-1).gather(-1,targets.unsqueeze(-1)).squeeze(-1)
                cs=[]; ac=[]
                for k in range(3):
                    selected=labels==k
                    require((selected.sum(1)==4).all().item(),'Component count audit failed')
                    cs.append(nll.masked_select(selected).reshape(len(x),4).mean(1).cpu())
                    ac.append(logits.argmax(-1).eq(targets).masked_select(selected).reshape(len(x),4).float().mean(1).cpu())
                comps.append(torch.stack(cs,1)); accuracies.append(torch.stack(ac,1))
                totals.append(nll.masked_select(labels>=0).reshape(len(x),12).mean(1).cpu())
            values=torch.cat(comps); total=torch.cat(totals); accuracy=torch.cat(accuracies)
            close(values.mean(1),total)
            output[split]={'loss':total,'component_loss':values,'component_accuracy':accuracy}
            metrics[split]={'loss':float(total.mean()),**{name:{'loss':float(values[:,j].mean()),
                             'accuracy':float(accuracy[:,j].mean())} for j,name in enumerate(('shared','group','instance'))}}
        return metrics,output
    def compare_arrays(expected,observed):
        require(set(expected)==set(observed),'Saved split set mismatch')
        for split in expected:
            require(set(expected[split])==set(observed[split]),'Saved field set mismatch')
            for field in expected[split]: close(expected[split][field],observed[split][field])
    def compare_metrics(a,b):
        for split in a:
            close(a[split]['loss'],b[split]['loss'])
            for name in ('shared','group','instance'):
                for key in ('loss','accuracy'): close(a[split][name][key],b[split][name][key])
    require((RUN/'FIT_COMPLETE.json').is_file(),'Missing calibration fits')
    require(read(RUN/'FIT_COMPLETE.json')['fit_manifest_sha256']==sha(RUN/'FIT_MANIFEST.json'),'Fit manifest drift')
    require(read(RUN/'FIT_COMPLETE.json')['decision_sha256']==sha(RUN/'CALIBRATION_DECISION.json'),'Decision drift')
    check_binding(RUN/'fits',read(RUN/'FIT_MANIFEST.json'))
    fixture_sha=sha(RUN/'SOURCE_FIXTURES.json')
    require(read(RUN/'PREPARE_COMPLETE.json')['fixtures_sha256']==fixture_sha,
            'Independent preparation fixture binding failed')
    require(read(RUN/'PRETRAIN_COMPLETE.json')['fixture_sha256']==fixture_sha,
            'Independent pretraining fixture binding failed')
    require(read(RUN/'SOURCE_FIXTURES.json')['status']=='PASS_CALIBRATION_FIXTURES','Fixture status')
    from audit_fit import audit_fit,audit_gates
    from audit_steps import audit_steps
    verified_data={}; reports=[]; rows=[]; step_reports=[]
    for d,p in zip(CORPORA,PRESEEDS):
        for seed,pre,prefix in ((d,False,'corpus'),(p,True,'pretrain')):
            guard.check()
            stored=load(RUN/'inputs'/f'{prefix}-{seed}.pt'); regenerated=regenerate(seed,pre)
            require(set(stored)==set(regenerated),'Split mismatch')
            for split in stored:
                require(all(torch.equal(a,b) for a,b in zip(stored[split],regenerated[split])),'Full token/label regeneration')
            verified_data[str(seed)]={k:thash(*v) for k,v in stored.items()}
    for _,d,s,p in pairs():
        guard.check(disk=True); name=pair_name(d,s); base=RUN/'baselines'/name; b=read(base/'record.json')
        ds=load(RUN/'inputs'/f'corpus-{d}.pt'); a=load(RUN/'inputs'/f'assignment-{s}.pt')
        rng=random.Random(s+1000)
        raw=torch.tensor([math.exp(rng.uniform(math.log(.5),math.log(2))) for _ in range(512)],dtype=torch.float32)
        q=raw/raw.mean()
        require(torch.equal(raw,a['raw_q']) and torch.equal(q,a['q']),'Target RNG or normalization')
        orders=torch.stack([torch.randperm(512,generator=torch.Generator().manual_seed(s+999+e)) for e in range(1,11)])
        po=torch.stack([torch.randperm(2048,generator=torch.Generator().manual_seed(s+999+e)) for e in range(1,5)])
        require(torch.equal(orders,a['orders']) and torch.equal(po,a['pretrain_orders']),'Applied order pairing')
        require(sha(base/'pretrained.pt')==b['checkpoint_sha256'],'Pretraining hash')
        obj=Model(128,3,40).cuda(); obj.load_state_dict(load(base/'pretrained.pt'))
        require({k:thash(v) for k,v in obj.state_dict().items()}==b['pretrained_tensor_sha256'],'Initial state hash')
        initial_metrics,initial=reevaluate(obj,ds)
        compare_arrays(load(base/'initial-arrays.pt'),initial); compare_metrics(b['initial_metrics'],initial_metrics)
        premetrics,prearrays=reevaluate(obj,load(RUN/'inputs'/f'pretrain-{p}.pt'))
        compare_arrays(load(base/'pretraining-arrays.pt'),prearrays); compare_metrics(b['pretrain_metrics'],premetrics)
        pt=read(base/'pretraining-trace.json'); require(len(pt)==256,'Pretrain update count')
        for i,t in enumerate(pt):
            e,j=divmod(i,64)
            require(t['epoch']==e+1 and t['step']==j and t['ids_sha256']==thash(po[e][j*32:(j+1)*32]),'Pretraining order trace')
        final={}
        for arm in ARMS:
            target=RUN/'trajectories'/(name+'-'+arm); r=read(target/'record.json')
            require(r['data_seed']==d and r['seed']==s and r['arm']==arm and r['pretrain_seed']==p,'Arm identities')
            require(r['epoch']==10 and r['updates']==160 and r['clip']==1 and r['lr']==1e-4 and r['weight_decay']==.1 and r['batch']==32 and r['width']==128 and r['layers']==3 and r['coefficients']==[1/3]*3 and r['whole_sequence_weighting'] is True and r['betas']==[.9,.999] and r['eps']==1e-8,'Canonical policy')
            weights=torch.ones(512,3) if arm=='U' else q[:,None].repeat(1,3)
            require(torch.equal(a['arm_weights'][arm],weights) and r['arm_weights_sha256']==thash(weights),'Whole-sequence weights')
            require(r['order_sha256']==thash(orders) and r['q_sha256']==thash(q) and r['data_sha256']==verified_data[str(d)],'Input hashes')
            require(r['initial_checkpoint_sha256']==b['checkpoint_sha256'] and r['initial_tensor_sha256']==b['pretrained_tensor_sha256'],'Initialization pairing')
            require(sha(target/'F10.pt')==r['checkpoint_sha256'] and sha(target/'F10-arrays.pt')==r['arrays_sha256'] and sha(target/'update-trace.json')==r['trace_sha256'],'Endpoint/trace binding')
            obj.load_state_dict(load(target/'F10.pt')); metrics,arrays=reevaluate(obj,ds)
            compare_arrays(load(target/'F10-arrays.pt'),arrays); compare_metrics(r['metrics'],metrics); final[arm]=arrays
            trace=read(target/'update-trace.json'); require(len(trace)==160,'Adapt trace count')
            for i,t in enumerate(trace):
                e,j=divmod(i,16)
                require(t['epoch']==e+1 and t['step']==j and t['ids_sha256']==thash(orders[e][j*32:(j+1)*32]),'Adapt order trace')
                require(t['policy']=='native_AdamW_clip1' and math.isfinite(t['objective']) and math.isfinite(t['pre_clip_norm']) and 0<=t['post_clip_norm']<=1.00001 and t['clipped']==(t['pre_clip_norm']>1),'Clip trace')
                close(t['objective'],sum(t['weighted_contributions']))
            close(r['gradient_clip_fraction'],sum(t['clipped'] for t in trace)/160,1e-12)
            close(r['ESS'],float(weights[:,0].double().sum()**2/weights[:,0].double().square().sum()),1e-10)
            if d==CORPORA[0] and s==MODEL_SEEDS[0][0]:
                step_reports.extend(audit_steps(target,ds,weights,orders,guard))
        cg=load(RUN/'baselines'/name/'initial-arrays.pt')['train']['loss']-load(RUN/'trajectories'/(name+'-R')/'F10-arrays.pt')['train']['loss']
        independently_recomputed=initial['train']['loss']-final['R']['train']['loss']
        close(cg,independently_recomputed,4e-6)
        # Fit audit uses exact saved FP32 gain bytes after independent checkpoint checking.
        saved=read(RUN/'fits'/(name+'.json')); g=cg.double().tolist()
        checked=audit_fit(q.tolist(),g,saved['fit'],guard)
        own={arm:float((initial['validation']['loss']-final[arm]['validation']['loss']).double().mean()) for arm in ARMS}
        saved_own={arm:math.fsum(saved['allocation'][arm]['validation']['signed_gains'])/256 for arm in ARMS}
        for arm in ARMS: close(own[arm],saved_own[arm],4e-6)
        # Gate quantities use saved independently verified arrays, avoiding reevaluation rounding at thresholds.
        exact_initial=load(base/'initial-arrays.pt')
        exact_final={arm:load(RUN/'trajectories'/(name+'-'+arm)/'F10-arrays.pt') for arm in ARMS}
        u_gain=float((exact_initial['validation']['loss']-exact_final['U']['validation']['loss']).double().mean())
        r_gain=float((exact_initial['validation']['loss']-exact_final['R']['validation']['loss']).double().mean())
        cost=float(exact_final['R']['validation']['loss'].double().mean()-exact_final['U']['validation']['loss'].double().mean())
        close(saved['U_validation_gain'],u_gain,1e-12); close(saved['R_validation_gain'],r_gain,1e-12)
        close(saved['R_minus_U_validation'],cost,1e-12); close(saved['mean_R_gain'],math.fsum(g)/512,1e-12)
        for arm in ARMS:
            for split in exact_initial:
                expected=(exact_initial[split]['loss']-exact_final[arm][split]['loss']).double()
                close(saved['allocation'][arm][split]['signed_gains'],expected,1e-12)
        sorted_q=torch.argsort(q,stable=True)
        for arm in ARMS:
            observed=saved['allocation'][arm]['train']
            require(observed['ascending_q_indices']==sorted_q.tolist(),'Allocation order')
            close(observed['target_cumulative'],(q.double()[sorted_q]/q.double().sum()).cumsum(0),1e-12)
            train=(exact_initial['train']['loss']-exact_final[arm]['train']['loss']).double()
            total=math.fsum(train.tolist())
            if total<=1e-10: require(observed['gain_cumulative'] is None,'Undefined allocation must remain null')
            else: close(observed['gain_cumulative'],(train[sorted_q]/total).cumsum(0),1e-12)
        fitted=saved['allocation']['R']['train']['fitted_cumulative']
        if saved['fit']['p'] is None: require(fitted is None,'Undefined fitted allocation')
        else:
            mass=q.double().pow(saved['fit']['p'])
            close(fitted,(mass[sorted_q]/mass.sum()).cumsum(0),1e-12)
        rows.append(dict(identity=name,data_seed=d,fit=checked,mean_R_gain=math.fsum(g)/512,
            U_validation_gain=u_gain,R_validation_gain=r_gain,R_minus_U_validation=cost))
        reports.append(dict(identity=name,fit=checked))
        del obj; torch.cuda.empty_cache()
    summary=audit_gates(rows); candidate=read(RUN/'CALIBRATION_DECISION.json')
    require(summary['status']==candidate['status'],'Independent gate verdict disagreement')
    if summary['pcal'] is None: require(candidate['pcal'] is None,'Undefined pcal disagreement')
    else: close(summary['pcal'],candidate['pcal'],1e-5)
    # Compare every boolean, not just a final AND that could conceal offsetting errors.
    seed_map={'mean_gain':'mean_R_gain','interior_identified':'defined_interior_identified',
        'minimum_p':'minimum_p','fit_RMS':'fit_RMS','seed_stability':'seed_stability'}
    corpus_map={'improvement':'fit_improvement_vs_p0','U_gain':'U_validation_gain',
        'R_gain':'R_validation_gain','cost':'R_validation_cost','LOO_stability':'leave_one_corpus_out_stability'}
    lookup={(x['identity'],x['gate']):x['passed'] for x in candidate['checks']}
    for r in summary['seed_records']:
        for k,v in r['gates'].items(): require(lookup[(r['identity'],seed_map[k])]==v,'Seed gate disagreement')
    for r in summary['corpus_records']:
        for k,v in r['gates'].items(): require(lookup[(str(r['data_seed']),corpus_map[k])]==v,'Corpus gate disagreement')
    write(OUT/'INDEPENDENT_FITS.json',reports)
    write(OUT/'CALIBRATION_DECISION.json',summary)
    write(OUT/'AUDIT.json',dict(status='PASS_CALIBRATION_NUMERICAL_AUDIT',utc=utc(),
        manifest_sha256=verify_manifest(),scientific_status=summary['status'],
        input_regenerations=6,checkpoint_reevaluations=24,trajectories=12,nested_pairs=6,independent_corpora=3,
        discrepancy_count=len(discrepancy_checks),snapshot_audit=step_reports,
        fit_audit='independent derivative roots, dense kernel, Decimal35/60, finite profile identification',
        parameter_tolerance=1e-5,objective_absolute=1e-10,objective_relative=1e-8,
        scientific_PASS_is_not_numerical_PASS=True,confirmation_authorized=False,
        output_hashes={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}))
    guard.check(disk=True)
if __name__=='__main__': main()
