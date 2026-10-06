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
    torch.set_num_threads(4)
    require(torch.cuda.is_available(),'Audit requires CUDA; no CPU fallback')
    require(torch.__version__=='2.7.0+cu126' and torch.version.cuda=='12.6' and platform.python_version()=='3.12.3','Unreviewed audit environment')
    require(torch.cuda.get_device_name(0)=='NVIDIA GeForce RTX 3050 Laptop GPU','Unreviewed audit GPU')
    require(os.environ.get('CUBLAS_WORKSPACE_CONFIG') is None,'Inherited audit CUBLAS policy')
    torch.backends.cudnn.benchmark=False
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(False)
    require((RUN/'ADAPT_COMPLETE.json').is_file(),'Missing complete 40-trajectory run')
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
    fixture_report=read(RUN/'OPTIMIZER_FIXTURES.json')
    require(fixture_report['status']=='PASS_PRETRAINING_FIXTURES' and
            read(RUN/'PRETRAIN_COMPLETE.json')['fixture_sha256']==sha(RUN/'OPTIMIZER_FIXTURES.json'),
            'Pretraining fixture receipt binding')
    from audit_optimizer import audit_snapshots
    snapshot_reports=[]
    verified_data={}
    for d,p in zip(CORPORA,PRESEEDS):
        guard.check()
        for seed,pre,prefix in ((d,False,'corpus'),(p,True,'pretrain')):
            stored=load(RUN/'inputs'/f'{prefix}-{seed}.pt'); regenerated=regenerate(seed,pre)
            require(set(stored)==set(regenerated),'Data split mismatch')
            for split in stored:
                require(all(torch.equal(a,b) for a,b in zip(stored[split],regenerated[split])),
                        'Full token/label regeneration failed')
            verified_data[str(seed)]={k:thash(*v) for k,v in stored.items()}
    rows=[]; allocation=[]; trace_checks=0
    for _,d,s,p in pairs():
        guard.check(disk=True)
        name=pair_name(d,s); base=RUN/'baselines'/name; b=read(base/'record.json')
        require(sha(base/'pretrained.pt')==b['checkpoint_sha256'],'Baseline checkpoint hash mismatch')
        assignment=load(RUN/'inputs'/f'assignment-{s}.pt')
        rng=random.Random(1000+s)
        w=torch.tensor([math.exp(rng.uniform(math.log(.01),math.log(10))) for _ in range(512)],dtype=torch.float32)
        w=w/w.mean(); require(torch.equal(w,assignment['random_weights']),'Weight RNG mismatch')
        require(w.unique().numel()==512 and torch.isfinite(w).all().item() and (w>0).all().item(),'Invalid random weights')
        expected_orders=torch.stack([torch.randperm(512,generator=torch.Generator().manual_seed(999+s+e)) for e in range(1,11)])
        pre_orders=torch.stack([torch.randperm(2048,generator=torch.Generator().manual_seed(999+s+e)) for e in range(1,5)])
        require(torch.equal(assignment['orders'],expected_orders) and torch.equal(assignment['pretrain_orders'],pre_orders),
                'Batch-order RNG mismatch')
        uniform=torch.ones(512,3); instance=torch.stack((torch.ones_like(w),torch.ones_like(w),w),1)
        matrices={'U-Adam':uniform,'I-Adam':instance,'U-isotropic':uniform,'I-isotropic':instance}
        ds=load(RUN/'inputs'/f'corpus-{d}.pt')
        obj=Model(128,3,40).cuda(); obj.load_state_dict(load(base/'pretrained.pt'))
        require({k:thash(v) for k,v in obj.state_dict().items()}==b['pretrained_tensor_sha256'],'Baseline state hash mismatch')
        initial_metrics,initial=reevaluate(obj,{k:ds[k] for k in ('train','test')})
        require(sha(base/'initial-arrays.pt')==b['initial_arrays_sha256'],'Initial arrays binding mismatch')
        compare_arrays(load(base/'initial-arrays.pt'),initial); compare_metrics(b['initial_metrics'],initial_metrics)
        pre_metrics,pre_recomputed=reevaluate(obj,load(RUN/'inputs'/f'pretrain-{p}.pt'))
        compare_arrays(load(base/'pretraining-arrays.pt'),pre_recomputed)
        compare_metrics(b['pretrain_metrics'],pre_metrics)
        trace=read(base/'pretraining-trace.json'); require(len(trace)==256,'Pretraining trace count mismatch')
        for index,row in enumerate(trace):
            epoch,step=divmod(index,64)
            require(row['epoch']==epoch+1 and row['step']==step and row['ids_sha256']==thash(pre_orders[epoch][step*32:(step+1)*32]),
                    'Pretraining applied-order trace mismatch')
            require(math.isfinite(row['objective']) and math.isfinite(row['norm']) and row['norm']>=0,'Pretraining nonfinite trace')
        scores={}; train_arrays={}; update_summaries={}
        for arm in ARMS:
            target=RUN/'trajectories'/(name+'-'+arm); r=read(target/'record.json')
            require(r['data_seed']==d and r['seed']==s and r['pretrain_seed']==p and r['arm']==arm,
                    'Wrong factorial arm/seed record')
            expected_clip=None
            require(r['epoch']==10 and r['width']==128 and r['layers']==3 and r['lr']==1e-4 and
                    r['weight_decay']==.1 and r['clip']==expected_clip and r['batch']==32 and r['coefficients']==[1/3]*3,
                    'Fixed optimizer/endpoint mismatch')
            require(r['optimizer_mode']==('adam' if arm.endswith('Adam') else 'isotropic') and r['betas']==[.9,.999] and r['eps']==1e-8,'Preconditioning arm policy mismatch')
            require(r['initial_checkpoint_sha256']==b['checkpoint_sha256'] and r['initial_tensor_sha256']==b['pretrained_tensor_sha256'],
                    'Four-arm initialization pairing failed')
            require(r['data_sha256']==verified_data[str(d)] and r['order_sha256']==thash(expected_orders),
                    'Data/batch-order pairing failed')
            require(torch.equal(assignment['arm_weights'][arm],matrices[arm]) and r['arm_weights_sha256']==thash(matrices[arm]) and
                    r['random_weights_sha256']==thash(w),'Arm weight mask mismatch')
            require(sha(target/'F10.pt')==r['checkpoint_sha256'] and sha(target/'F10-arrays.pt')==r['arrays_sha256'] and
                    sha(target/'update-trace.json')==r['trace_sha256'],'Trajectory binding mismatch')
            state=load(target/'F10.pt'); require(all(torch.isfinite(v).all().item() for v in state.values()),'Nonfinite final checkpoint')
            obj.load_state_dict(state); recomputed,arrays=reevaluate(obj,ds)
            layout=[dict(name=n,shape=list(p.shape),numel=p.numel()) for n,p in sorted(obj.named_parameters())]
            require(r['snapshot_parameter_layout']==layout and r['relative_norm_guard']==1e-12,
                    'Snapshot shape/order/storage guard mismatch')
            snapshot_reports.extend(audit_snapshots(target,r,load(base/'pretrained.pt'),state,obj,ds,assignment,guard,sha,load))
            compare_arrays(load(target/'F10-arrays.pt'),arrays); compare_metrics(r['metrics'],recomputed)
            trace=read(target/'update-trace.json'); require(len(trace)==160 and r['updates']==160,'Wrong update count')
            for number in (1,160):
                snapfile=target/f'step-{number:03d}.pt'
                if snapfile.name in r['snapshot_bindings']:
                    saved_step=load(snapfile)['scalar']
                    require(all(trace[number-1][key]==value for key,value in saved_step.items()),
                            'Trace scalar differs from independently audited snapshot')
            for index,row in enumerate(trace):
                epoch,step=divmod(index,16)
                require(row['epoch']==epoch+1 and row['step']==step and row['ids_sha256']==thash(expected_orders[epoch][step*32:(step+1)*32]),
                        'Applied-order trace mismatch')
                close(row['objective'],sum(row['weighted_component_contributions']),2e-6)
                require(math.isfinite(row['gradient_norm']) and row['gradient_norm']>=0,'Invalid gradient norm')
                require(all(math.isfinite(x) for x in row['unweighted_component_means']),'Invalid component trace')
                step=row['parameter_step_l2']; denominator=row['parameter_norm_before']; relative=row['relative_step_l2']
                require(math.isfinite(step) and step>=0 and math.isfinite(denominator) and denominator>=0,'Nonfinite step instrumentation')
                if denominator<=1e-12:
                    require(relative is None and row['relative_guard']=='parameter_norm_le_1e-12','Broken relative norm guard')
                else:
                    require(relative is not None and row['relative_guard'] is None,'Unexpected relative norm guard')
                    close(relative,step/denominator,1e-12)
                require(row['optimizer_step']==index+1 and row['mode']==r['optimizer_mode'],'Applied optimizer step/mode mismatch')
                for key in ('first_moment_norm','second_moment_norm','mhat_norm','adaptive_counterfactual_norm','direction_norm','isotropic_scale','norm_matching_abs_error'):
                    require(math.isfinite(row[key]) and row[key]>=0,'Invalid moment/direction instrumentation')
                require(row['norm_matching_abs_error']<=1e-8+2e-6*row['adaptive_counterfactual_norm'],'Trace norm match failed')
                close(row['direction_norm'],row['adaptive_counterfactual_norm'],1e-8+2e-6*row['adaptive_counterfactual_norm'])
                if row['exact_zero_update']:
                    require(row['mhat_norm']==row['adaptive_counterfactual_norm']==row['direction_norm']==row['isotropic_scale']==0.,'Exact-zero trace mismatch')
                else:
                    require(row['mhat_norm']>1e-12 and row['adaptive_counterfactual_norm']>1e-12,'Near-zero trace accepted')
                    close(row['isotropic_scale'],row['adaptive_counterfactual_norm']/row['mhat_norm'],1e-12)
                trace_checks+=1
            close(r['gradient_clip_fraction'],0. if expected_clip is None else sum(x['gradient_norm']>1 for x in trace)/160,1e-12)
            defined=[x['relative_step_l2'] for x in trace if x['relative_step_l2'] is not None]
            update_summaries[arm]=dict(parameter_step_l2_mean=statistics.mean(x['parameter_step_l2'] for x in trace),
                parameter_step_l2_range=[min(x['parameter_step_l2'] for x in trace),max(x['parameter_step_l2'] for x in trace)],
                relative_step_l2_mean=statistics.mean(defined) if defined else None,
                relative_step_defined_count=len(defined),relative_step_guard_count=len(trace)-len(defined),
                gradient_clip_fraction=r['gradient_clip_fraction'])
            scores[arm]=recomputed; train_arrays[arm]=arrays['train']['component_loss'].double()
        g={arm:scores[arm]['test']['group']['loss'] for arm in ARMS}
        cadam=g['I-Adam']-g['U-Adam']; cisotropic=g['I-isotropic']-g['U-isotropic']
        primary=cadam-cisotropic
        adequacy=initial_metrics['test']['group']['loss']-g['U-isotropic']
        adam_adequacy=initial_metrics['test']['group']['loss']-g['U-Adam']
        uniform_gap=g['U-isotropic']-g['U-Adam']
        direct_I=g['I-Adam']-g['I-isotropic']
        row=dict(data_seed=d,seed=s,primary_D=primary,CAdam=cadam,Cisotropic=cisotropic,
                 U_isotropic_own_baseline_group_gain=adequacy,U_Adam_own_baseline_group_gain=adam_adequacy,
                 uniform_group_gap=uniform_gap,direct_I_improvement=direct_I,initial_group_test_nll=initial_metrics['test']['group']['loss'],
                 arm_metrics=scores,update_summaries=update_summaries,
                 total_test_CAdam=scores['I-Adam']['test']['loss']-scores['U-Adam']['test']['loss'],
                 total_test_Cisotropic=scores['I-isotropic']['test']['loss']-scores['U-isotropic']['test']['loss'])
        close(primary,((g['I-Adam']-g['I-isotropic'])-(g['U-Adam']-g['U-isotropic'])),1e-12)
        rows.append(row)
        # Signed own-baseline conditional instance-allocation contrasts, secondary.
        baseline=initial['train']['component_loss'].double()
        ranks=sorted(range(512),key=lambda index:(float(w[index]),index)); low=ranks[:128]; high=ranks[-128:]
        gains={arm:baseline-train_arrays[arm] for arm in ARMS}
        adam_gain=gains['I-Adam']-gains['U-Adam']; isotropic_gain=gains['I-isotropic']-gains['U-isotropic']
        allocation.append(dict(data_seed=d,seed=s,quartile_rule='ascending (saved weight, sequence index); 128 per extreme',
            adam_gain_low=adam_gain[low].mean(0).tolist(),adam_gain_high=adam_gain[high].mean(0).tolist(),
            isotropic_gain_low=isotropic_gain[low].mean(0).tolist(),isotropic_gain_high=isotropic_gain[high].mean(0).tolist(),
            allocation_interaction_high_minus_low=((adam_gain[high]-isotropic_gain[high]).mean(0)-
                                                  (adam_gain[low]-isotropic_gain[low]).mean(0)).tolist()))
        del obj; torch.cuda.empty_cache()
    require(len(rows)==10 and trace_checks==6400,'Incomplete experiment')
    require(len(snapshot_reports)==8,'Incomplete fixed first/last optimizer snapshots')
    corpus=[]
    keys=('primary_D','CAdam','Cisotropic','U_Adam_own_baseline_group_gain',
          'U_isotropic_own_baseline_group_gain','uniform_group_gap','direct_I_improvement')
    for d in CORPORA:
        selected=[r for r in rows if r['data_seed']==d]; require(len(selected)==2,'Wrong nested seed count')
        corpus.append(dict(data_seed=d,**{key:statistics.mean(r[key] for r in selected) for key in keys}))
    values=[r['primary_D'] for r in corpus]
    practical=statistics.mean(values)>=.01 and all(v>0 for v in values)
    gates=dict(native_instance_penalty_positive_all5=all(r['CAdam']>0 for r in corpus),
        U_Adam_improves_initial_all5=all(r['U_Adam_own_baseline_group_gain']>0 for r in corpus),
        U_isotropic_improves_initial_all5=all(r['U_isotropic_own_baseline_group_gain']>0 for r in corpus),
        uniform_group_gap_within_utility_margin_all5=all(abs(r['uniform_group_gap'])<=.01 for r in corpus),
        I_isotropic_improves_over_I_Adam_all5=all(r['direct_I_improvement']>0 for r in corpus))
    clean=practical and all(gates.values())
    verdict=('clean_practical_attenuation_at_tested_policy' if clean else
             'practical_interaction_but_interpretation_gate_failed' if practical else
             'practical_preconditioning_attenuation_not_supported')
    summary=dict(version='v0135',utc=utc(),primary_mean=statistics.mean(values),
        corpus_values=corpus,corpus_sd=statistics.stdev(values),minimum=min(values),maximum=max(values),
        positive_corpora=sum(v>0 for v in values),verdict=verdict,
        practical_threshold_nats=.01,practical_criterion_met=practical,interpretation_gates=gates,
        clean_attenuation_interpretation=clean,uniform_utility_margin_nats=.01,
        secondary_mean={key:statistics.mean(r[key] for r in corpus) for key in keys if key!='primary_D'},
        secondary_sd={key:statistics.stdev(r[key] for r in corpus) for key in keys if key!='primary_D'},
        primary_units='nats/group answer token; positive = more adverse instance effect under coordinate-wise Adam',
        inference='Five fresh independent corpus pairs; two nested seeds averaged first, then five corpus means equally. No p-value or mediation claim.',
        warnings=['Uniform margin is prospective utility margin, not formal equivalence',
                  'Same-state counterfactual adaptive norm matching, not another arm step matching',
                  'Weight decay contributes to total steps; trajectories and moments diverge',
                  'Independent eight-step snapshots, not full optimization replay',
                  'Fixed synthetic optimizer-policy intervention only; no universal mechanism or peak claim'])
    write(OUT/'PAIRS.json',rows); write(OUT/'CORPUS_SUMMARY.json',summary); write(OUT/'ALLOCATION.json',allocation)
    with (OUT/'CORPUS_CONTRASTS.csv').open('x',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(corpus[0])); writer.writeheader(); writer.writerows(corpus)
    guard.check(disk=True)
    audit=dict(status='PASS_NUMERICAL_AND_PRECONDITIONING_AUDIT',utc=utc(),manifest_sha256=verify_manifest(),
        checkpoint_reevaluations=50,full_input_regenerations=10,adaptation_update_trace_rows=trace_checks,
        pretraining_fixtures=fixture_report,tolerance_nll=2e-6,independent_snapshot_audit=snapshot_reports,
        snapshot_count=8,storage_at_audit_completion=resources(),
        discrepancy_maxima={str(tol):max(error for t,error in discrepancy_checks if t==tol)
                            for tol in sorted({t for t,_ in discrepancy_checks})},
        discrepancy_check_count=len(discrepancy_checks),
        paired_seed_rows=10,corpus_rows=5,trajectories=40,source_review_required_separately=True,
        output_hashes=binding(OUT),limitations=summary['warnings'])
    write(OUT/'AUDIT.json',audit)
    guard.check(disk=True)

if __name__=='__main__': main()
