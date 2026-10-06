"""Independent arithmetic/data/checkpoint audit; never trains a model."""
import time
import argparse
import csv
import hashlib
import math
import random
import statistics
import sys
from pathlib import Path
sys.dont_write_bytecode=True
from common import (HERE,RUN,OUT,ARMS,CORPORA,PRESEEDS,MODEL_SEEDS,Guard,require,read,write,
                    sha,utc,pairs,pair_name,binding,check_binding,verify_manifest)

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
    # Candidate objective/gradient fixtures are outcome-independent. Only this
    # section imports the worker; final NLL audit above uses separate code.
    import experiment as candidate
    candidate.imports()
    class FixedLogits(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.logits=torch.nn.Parameter(torch.linspace(-.8,.8,2*40*84,dtype=torch.float64).reshape(2,40,84))
        def forward(self,x): return self.logits
    fixture=FixedLogits(); tokens=torch.arange(82).reshape(2,41)%84
    kinds=torch.full((2,40),-1,dtype=torch.long)
    for j in range(12): kinds[:,j*3+4]=j%3
    w=torch.tensor([.3,1.7]); uniform=torch.ones(2,3)
    instance=torch.stack((torch.ones(2),torch.ones(2),w),1)
    masks={'Uclip':uniform,'Iclip':instance,'Unoclip':uniform,'Inoclip':instance}
    losses={}
    for arm,mask in masks.items():
        actual,_,_=candidate.component_objective(fixture,tokens,kinds,mask)
        ce=F.cross_entropy(fixture.logits.reshape(-1,84),tokens[:,1:].reshape(-1),reduction='none').reshape(2,40)
        reference=sum(ce[row,kinds[row]==j].mean()*mask[row,j] for row in range(2) for j in range(3))/6
        close(actual.detach(),reference.detach(),1e-7)
        grad_actual=torch.autograd.grad(actual,fixture.logits,retain_graph=True)[0]
        grad_reference=torch.autograd.grad(reference,fixture.logits)[0]
        close(grad_actual,grad_reference,1e-7); losses[arm]=float(actual.detach())
    close(losses['Iclip']-losses['Uclip'],losses['Inoclip']-losses['Unoclip'],1e-7)
    fixture_report=dict(status='PASS',objective_and_gradient_arms=list(ARMS),tolerance=1e-7)
    # Validate instrumentation independently on synthetic parameters, not a
    # scientific trajectory; no intermediate research optimizer update is replayed.
    class ParameterFixture(torch.nn.Module):
        def __init__(self,zero=False):
            super().__init__()
            value=torch.zeros(621696,device='cuda') if zero else torch.linspace(-.5,.5,621696,device='cuda')
            self.theta=torch.nn.Parameter(value)
    for arm in ARMS:
        guard.check()
        holder=ParameterFixture(); snapshot=candidate.StepSnapshot(holder)
        before=holder.theta.detach().double().clone()
        optimizer=torch.optim.AdamW(holder.parameters(),lr=1e-4,weight_decay=.1)
        holder.theta.grad=torch.linspace(-3.,3.,621696,device='cuda')
        clip=None if arm in ('Unoclip','Inoclip') else 1.
        norm=torch.nn.utils.clip_grad_norm_(holder.parameters(),math.inf if clip is None else clip,error_if_nonfinite=True)
        if clip is None: close(torch.linalg.vector_norm(holder.theta.grad.double()),float(norm),1e-3)
        else: require(float(torch.linalg.vector_norm(holder.theta.grad.double()))<=1+2e-6,'Clipping fixture failed')
        snapshot.before(); optimizer.step(); measured=snapshot.after()
        after=holder.theta.detach().double()
        actual=float(torch.linalg.vector_norm(after-before)); before_norm=float(torch.linalg.vector_norm(before))
        close(measured['parameter_step_l2'],actual,1e-9)
        close(measured['parameter_norm_before'],before_norm,1e-9)
        close(measured['relative_step_l2'],actual/before_norm,1e-9)
        require(snapshot.buffer.numel()*snapshot.buffer.element_size()==2486784,'Snapshot size fixture failed')
        del holder,snapshot,optimizer,before,after
    holder=ParameterFixture(zero=True); snapshot=candidate.StepSnapshot(holder)
    snapshot.before()
    with torch.no_grad(): holder.theta[0]=.125
    guarded=snapshot.after()
    require(guarded['relative_step_l2'] is None and guarded['relative_guard']=='parameter_norm_le_1e-12',
            'Relative norm guard fixture failed')
    close(guarded['parameter_step_l2'],.125,1e-12)
    with torch.no_grad(): holder.theta[0]=float('inf')
    try: snapshot.before()
    except RuntimeError: pass
    else: raise RuntimeError('Nonfinite snapshot fixture was not rejected')
    del holder,snapshot; torch.cuda.empty_cache()
    fixture_report.update(step_snapshot_arms=list(ARMS),step_tolerance=1e-9,
                          guarded_zero_norm=True,nonfinite_rejected=True,clip_gradient_norm_tolerance=1e-3)
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
        matrices={'Uclip':uniform,'Iclip':instance,'Unoclip':uniform,'Inoclip':instance}
        ds=load(RUN/'inputs'/f'corpus-{d}.pt')
        obj=Model(128,3,40).cuda(); obj.load_state_dict(load(base/'pretrained.pt'))
        require({k:thash(v) for k,v in obj.state_dict().items()}==b['pretrained_tensor_sha256'],'Baseline state hash mismatch')
        initial_metrics,initial=reevaluate(obj,{k:ds[k] for k in ('train','test')})
        require(sha(base/'initial-arrays.pt')==b['initial_arrays_sha256'],'Initial arrays binding mismatch')
        compare_arrays(load(base/'initial-arrays.pt'),initial); compare_metrics(b['initial_metrics'],initial_metrics)
        _,pre_recomputed=reevaluate(obj,load(RUN/'inputs'/f'pretrain-{p}.pt'))
        compare_arrays(load(base/'pretraining-arrays.pt'),pre_recomputed)
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
            expected_clip=None if arm in ('Unoclip','Inoclip') else 1.
            require(r['epoch']==10 and r['width']==128 and r['layers']==3 and r['lr']==1e-4 and
                    r['weight_decay']==.1 and r['clip']==expected_clip and r['batch']==32 and r['coefficients']==[1/3]*3,
                    'Fixed optimizer/endpoint mismatch')
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
            require(r['snapshot_bytes']==2486784 and r['snapshot_parameter_layout']==layout and r['relative_norm_guard']==1e-12,
                    'Snapshot shape/order/storage guard mismatch')
            compare_arrays(load(target/'F10-arrays.pt'),arrays); compare_metrics(r['metrics'],recomputed)
            trace=read(target/'update-trace.json'); require(len(trace)==160 and r['updates']==160,'Wrong update count')
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
        cclip=g['Iclip']-g['Uclip']; cnoclip=g['Inoclip']-g['Unoclip']
        primary=cclip-cnoclip
        adequacy=initial_metrics['test']['group']['loss']-g['Unoclip']
        row=dict(data_seed=d,seed=s,primary_D=primary,Cclip=cclip,Cnoclip=cnoclip,
                 Unoclip_own_baseline_group_gain=adequacy,initial_group_test_nll=initial_metrics['test']['group']['loss'],
                 arm_metrics=scores,update_summaries=update_summaries,
                 total_test_Cclip=scores['Iclip']['test']['loss']-scores['Uclip']['test']['loss'],
                 total_test_Cnoclip=scores['Inoclip']['test']['loss']-scores['Unoclip']['test']['loss'])
        close(primary,((g['Iclip']-g['Inoclip'])-(g['Uclip']-g['Unoclip'])),1e-12)
        rows.append(row)
        # Signed own-baseline conditional instance-allocation contrasts, secondary.
        baseline=initial['train']['component_loss'].double()
        ranks=sorted(range(512),key=lambda index:(float(w[index]),index)); low=ranks[:128]; high=ranks[-128:]
        gains={arm:baseline-train_arrays[arm] for arm in ARMS}
        clip_gain=gains['Iclip']-gains['Uclip']; noclip_gain=gains['Inoclip']-gains['Unoclip']
        allocation.append(dict(data_seed=d,seed=s,quartile_rule='ascending (saved weight, sequence index); 128 per extreme',
            clip_gain_low=clip_gain[low].mean(0).tolist(),clip_gain_high=clip_gain[high].mean(0).tolist(),
            noclip_gain_low=noclip_gain[low].mean(0).tolist(),noclip_gain_high=noclip_gain[high].mean(0).tolist(),
            allocation_interaction_high_minus_low=((clip_gain[high]-noclip_gain[high]).mean(0)-
                                                  (clip_gain[low]-noclip_gain[low]).mean(0)).tolist()))
        del obj; torch.cuda.empty_cache()
    require(len(rows)==10 and trace_checks==6400,'Incomplete experiment')
    corpus=[]
    for d in CORPORA:
        selected=[r for r in rows if r['data_seed']==d]; require(len(selected)==2,'Wrong nested seed count')
        corpus.append(dict(data_seed=d,primary_D=statistics.mean(r['primary_D'] for r in selected),
                           Cclip=statistics.mean(r['Cclip'] for r in selected),
                           Cnoclip=statistics.mean(r['Cnoclip'] for r in selected),
                           Unoclip_own_baseline_group_gain=statistics.mean(r['Unoclip_own_baseline_group_gain'] for r in selected)))
    values=[r['primary_D'] for r in corpus]; adequate=all(r['Unoclip_own_baseline_group_gain']>0 for r in corpus)
    practical=statistics.mean(values)>=.01 and all(v>0 for v in values)
    verdict='inconclusive_mechanism_failed_Unoclip_adequacy' if not adequate else (
        'practical_interaction_supported_at_tested_policy' if practical else 'practical_interaction_not_supported')
    summary=dict(version='v0133',utc=utc(),primary_mean=statistics.mean(values),
        corpus_values=corpus,corpus_sd=statistics.stdev(values),minimum=min(values),maximum=max(values),
        positive_corpora=sum(v>0 for v in values),verdict=verdict,
        practical_threshold_nats=.01,practical_criterion_met=practical,Unoclip_adequacy_pass=adequate,
        conditional_mean={key:statistics.mean(r[key] for r in corpus) for key in ('Cclip','Cnoclip')},
        conditional_sd={key:statistics.stdev(r[key] for r in corpus) for key in ('Cclip','Cnoclip')},
        conditional_range={key:[min(r[key] for r in corpus),max(r[key] for r in corpus)] for key in ('Cclip','Cnoclip')},
        adequacy_mean=statistics.mean(r['Unoclip_own_baseline_group_gain'] for r in corpus),
        adequacy_sd=statistics.stdev(r['Unoclip_own_baseline_group_gain'] for r in corpus),
        adequacy_range=[min(r['Unoclip_own_baseline_group_gain'] for r in corpus),max(r['Unoclip_own_baseline_group_gain'] for r in corpus)],
        primary_units='nats/group answer token; positive = more adverse or less beneficial instance effect under clip 1',
        inference='Five independent fresh corpus draws; two nested seeds averaged before equal corpus weighting. Descriptive direction and dispersion; no p-value or mediation claim.',
        warnings=['Fixed optimizer/clipping/teacher-forced synthetic design only','No universal mechanism or mediation proof',
                  'Trace/source review is evidence of execution policy; intermediate updates not independently replayed'])
    write(OUT/'PAIRS.json',rows); write(OUT/'CORPUS_SUMMARY.json',summary); write(OUT/'ALLOCATION.json',allocation)
    with (OUT/'CORPUS_CONTRASTS.csv').open('x',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(corpus[0])); writer.writeheader(); writer.writerows(corpus)
    guard.check(disk=True)
    audit=dict(status='PASS_NUMERICAL_AND_PAIRING_AUDIT',utc=utc(),manifest_sha256=verify_manifest(),
        checkpoint_reevaluations=50,full_input_regenerations=10,adaptation_update_trace_rows=trace_checks,
        objective_fixtures=fixture_report,tolerance_nll=2e-6,
        discrepancy_maxima={str(tol):max(error for t,error in discrepancy_checks if t==tol)
                            for tol in sorted({t for t,_ in discrepancy_checks})},
        discrepancy_check_count=len(discrepancy_checks),
        paired_seed_rows=10,corpus_rows=5,trajectories=40,source_review_required_separately=True,
        output_hashes=binding(OUT),limitations=summary['warnings'])
    write(OUT/'AUDIT.json',audit)

if __name__=='__main__': main()
