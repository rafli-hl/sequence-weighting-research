"""Fresh G1 whole-sequence calibration worker; execute only through reviewed manual supervisor."""
import time
PROCESS_START = time.monotonic()
import argparse
import gc
import math
import os
import platform
import random
import sys
import torch
from pathlib import Path
sys.dont_write_bytecode = True
from common import (HERE, ROOT, RUN, ARMS, CORPORA, PRESEEDS, MODEL_SEEDS, Guard,
                    require, read, write, sha, utc, pairs, pair_name, binding, check_binding,
                    verify_manifest, resources)

def imports():
    global torch, Model, engine
    sys.path.insert(0, str(HERE/'vendor'))
    import torch
    from model import Model
    import engine


def runtime():
    torch.set_num_threads(4)
    require(torch.cuda.is_available(), 'CUDA required; no CPU fallback')
    require(torch.__version__=='2.7.0+cu126' and torch.version.cuda=='12.6', 'Unreviewed torch/CUDA environment')
    require(platform.python_version()=='3.12.3', 'Unreviewed Python environment')
    require(torch.cuda.get_device_name(0)=='NVIDIA GeForce RTX 3050 Laptop GPU', 'Unreviewed GPU')
    require(os.environ.get('CUBLAS_WORKSPACE_CONFIG') is None, 'Inherited policy requires unset CUBLAS_WORKSPACE_CONFIG')
    torch.backends.cudnn.benchmark=False
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(False)
    return dict(utc=utc(),python=platform.python_version(),torch=torch.__version__,cuda=torch.version.cuda,
                gpu=torch.cuda.get_device_name(0),cudnn=torch.backends.cudnn.version(),
                threads=4,precision='float32',tf32=False,deterministic_algorithms=False,
                strict_determinism_claim=False)

def save(path, value, guard):
    guard.check(disk=True)
    path.parent.mkdir(parents=True,exist_ok=True)
    require(not path.exists(), 'Refuse overwrite: '+str(path))
    with path.open('xb') as stream: torch.save(value, stream)
    guard.check(disk=True)
    return sha(path)

def load(path):
    require(path.is_file(), 'Missing input: '+str(path))
    return torch.load(path, map_location='cpu', weights_only=True)

def model(seed):
    torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    obj=Model(128,3,40).cuda()
    require(sum(p.numel() for p in obj.parameters())==621696, 'Architecture mismatch')
    return obj

def state_hash(obj):
    return {k:engine.tensor_hash(v) for k,v in obj.state_dict().items()}

def check_finite(obj):
    require(all(torch.isfinite(v).all().item() for v in obj.state_dict().values()), 'Nonfinite model state')

def validate_dataset(ds, pretrain=False):
    sizes={'train':2048,'validation':256} if pretrain else {'train':512,'validation':256,'test':512}
    require(set(ds)==set(sizes),'Wrong split set')
    keys=[]
    for split,(tokens,kinds) in ds.items():
        require(tokens.dtype==torch.long and kinds.dtype==torch.long,'Wrong data dtype')
        require(tuple(tokens.shape)==(sizes[split],41) and tuple(kinds.shape)==(sizes[split],40),'Wrong data shapes')
        require(((tokens>=0)&(tokens<84)).all().item(),'Invalid token')
        for j in range(3): require(((kinds==j).sum(1)==4).all().item(),'Component counts changed')
        keys.extend(((tokens[:,2]-17)*1024+(tokens[:,3]-17)*32+tokens[:,4]-17).tolist())
    require(len(set(keys))==len(keys),'Repeated keys across splits')

def prepare(guard):
    require(not RUN.exists(),'No overwrite or resume')
    source_hash=verify_manifest()
    census=read(HERE/'SEED_CENSUS.json'); reconciliation=read(HERE/'FRESHNESS_RECONCILIATION.json')
    require(census['candidate_matches']==[] and reconciliation['collisions']==[],'Freshness rejected')
    require(reconciliation['census_sha256']==sha(HERE/'SEED_CENSUS.json'),'Census binding')
    seeds=set(CORPORA+PRESEEDS+tuple(s for row in MODEL_SEEDS for s in row))
    require(seeds==set(census['candidates'])==set(reconciliation['candidates']),'Seed identities')
    for row in census['records']:
        guard.check()
        require((ROOT/row['path']).is_file() and sha(ROOT/row['path'])==row['sha256'],'Historical census drift')
    RUN.mkdir(exist_ok=False)
    write(RUN/'DESIGN_FREEZE.json',dict(version='v0136',manifest_sha256=source_hash,utc=utc(),
        corpus_seeds=CORPORA,pretraining_seeds=PRESEEDS,model_weight_seeds=MODEL_SEEDS,
        arms=ARMS,whole_sequence_weighting=True,width=128,layers=3,epochs=10,batch=32,
        lr=1e-4,weight_decay=.1,clip=1,coefficients=[1/3]*3,confirmation_authorized=False))
    from fixtures import run_fixtures
    write(RUN/'SOURCE_FIXTURES.json',run_fixtures(guard))
    inputs=RUN/'inputs'; inputs.mkdir()
    for i,d in enumerate(CORPORA):
        guard.check(disk=True)
        ds,meta=engine.data(d,'G1',include_test=True); validate_dataset(ds)
        save(inputs/f'corpus-{d}.pt',ds,guard); write(inputs/f'corpus-{d}.json',meta)
        pre,pm=engine.pre_data(PRESEEDS[i]); validate_dataset(pre,True)
        require(not set(x for v in meta['sequence_keys_by_split'].values() for x in v).intersection(
            x for v in pm['sequence_keys_by_split'].values() for x in v),'Key namespace overlap')
        save(inputs/f'pretrain-{PRESEEDS[i]}.pt',pre,guard); write(inputs/f'pretrain-{PRESEEDS[i]}.json',pm)
        for s in MODEL_SEEDS[i]:
            rng=random.Random(s+1000)
            raw=torch.tensor([math.exp(rng.uniform(math.log(.5),math.log(2))) for _ in range(512)],dtype=torch.float32)
            q=raw/raw.mean()
            require(torch.isfinite(q).all().item() and (q>0).all().item(),'Invalid q')
            require(float(q.max()/q.min())<=4+1e-6 and abs(float(q.mean())-1)<=2e-7,'q global normalization')
            order=engine.orders(s,512,10); po=engine.orders(s,2048,4)
            save(inputs/f'assignment-{s}.pt',dict(q=q,raw_q=raw,orders=order,pretrain_orders=po,
                arm_weights={'U':torch.ones(512,3),'R':q[:,None].repeat(1,3)}),guard)
    write(RUN/'INPUT_MANIFEST.json',binding(inputs))
    guard.check(disk=True)
    write(RUN/'PREPARE_COMPLETE.json',dict(utc=utc(),manifest_sha256=source_hash,
        input_manifest_sha256=sha(RUN/'INPUT_MANIFEST.json'),fixtures_sha256=sha(RUN/'SOURCE_FIXTURES.json')))

def verify_inputs():
    require((RUN/'PREPARE_COMPLETE.json').is_file(),'Missing preparation completion')
    require(read(RUN/'DESIGN_FREEZE.json')['manifest_sha256']==verify_manifest(),'Freeze source mismatch')
    require(read(RUN/'PREPARE_COMPLETE.json')['input_manifest_sha256']==sha(RUN/'INPUT_MANIFEST.json'),
            'Input manifest changed')
    check_binding(RUN/'inputs',read(RUN/'INPUT_MANIFEST.json'))

def evaluate(obj,ds,guard):
    metrics={}; arrays={}
    for split,pair in ds.items():
        guard.check()
        metrics[split],arrays[split]=engine.evaluate(obj,pair)
        guard.check()
    return metrics,arrays

def pretrain(guard):
    verify_inputs()

    fixture_sha=sha(RUN/'SOURCE_FIXTURES.json')
    require(read(RUN/'PREPARE_COMPLETE.json')['fixtures_sha256']==fixture_sha,
            'Preparation fixture report binding changed')
    fixture_report=read(RUN/'SOURCE_FIXTURES.json')
    require(fixture_report['status']=='PASS_CALIBRATION_FIXTURES','Fixtures rejected')
    folder=RUN/'baselines'; folder.mkdir(exist_ok=False)
    env=runtime(); write(RUN/'ENVIRONMENT.json',env)
    for _,d,s,p in pairs():
        guard.check(disk=True)
        name=pair_name(d,s); target=folder/name; target.mkdir()
        obj=model(s); cold=state_hash(obj)
        ds=load(RUN/'inputs'/f'pretrain-{p}.pt')
        assignment=load(RUN/'inputs'/f'assignment-{s}.pt')
        opt=torch.optim.AdamW(obj.parameters(),lr=3e-4,weight_decay=.1)
        trace=[]
        start=time.monotonic(); torch.cuda.reset_peak_memory_stats()
        for epoch in range(4):
            obj.train()
            for step,ids in enumerate(assignment['pretrain_orders'][epoch].split(32)):
                guard.check()
                tokens,kinds=(v[ids].cuda() for v in ds['train'])
                objective=engine.pretraining_objective(obj(tokens[:,:-1]),tokens,kinds)
                opt.zero_grad(set_to_none=True); objective.backward()
                norm=torch.nn.utils.clip_grad_norm_(obj.parameters(),5.,error_if_nonfinite=True)
                require(torch.isfinite(objective).item() and torch.isfinite(norm).item(),'Nonfinite pretraining update')
                opt.step()
                trace.append(dict(epoch=epoch+1,step=step,objective=float(objective.detach()),norm=float(norm),
                                  ids_sha256=engine.tensor_hash(ids)))
            check_finite(obj); guard.check(disk=True)
        torch.cuda.synchronize()
        pre_metrics,pre_arrays=evaluate(obj,ds,guard)
        checkpoint_sha=save(target/'pretrained.pt',engine.cpu_state(obj),guard)
        save(target/'pretraining-arrays.pt',pre_arrays,guard)
        write(target/'pretraining-trace.json',trace)
        # Shared initial train/test evaluation includes the frozen adequacy baseline.
        adapt=load(RUN/'inputs'/f'corpus-{d}.pt')
        initial_metrics,initial_arrays=evaluate(obj,adapt,guard)
        initial_sha=save(target/'initial-arrays.pt',initial_arrays,guard)
        write(target/'record.json',dict(data_seed=d,seed=s,pretrain_seed=p,cold_tensor_sha256=cold,
              checkpoint_sha256=checkpoint_sha,pretrained_tensor_sha256=state_hash(obj),
              initial_arrays_sha256=initial_sha,pretrain_metrics=pre_metrics,initial_metrics=initial_metrics,
              pretrain_data_sha256={k:engine.tensor_hash(*v) for k,v in ds.items()},
              pretrain_order_sha256=engine.tensor_hash(assignment['pretrain_orders']),updates=256,
              elapsed_seconds=time.monotonic()-start,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
              peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20))
        del obj,opt; gc.collect(); torch.cuda.empty_cache()
    write(RUN/'BASELINE_MANIFEST.json',binding(folder))
    guard.check(disk=True)
    require(sha(RUN/'SOURCE_FIXTURES.json')==fixture_sha,'Fixture report changed during pretraining')
    write(RUN/'PRETRAIN_COMPLETE.json',dict(utc=utc(),baselines=6,
          baseline_manifest_sha256=sha(RUN/'BASELINE_MANIFEST.json'),fixture_sha256=fixture_sha,manifest_sha256=verify_manifest()))

def component_objective(obj,tokens,kinds,weights):
    _,token_loss,_=engine.losses(obj,tokens,kinds)
    components=[]
    for j in range(3):
        mask=kinds==j; count=mask.sum(1)
        require((count==4).all().item(),'Broken component balance')
        components.append((token_loss*mask).sum(1)/count)
    values=torch.stack(components,1)
    weighted=(values*weights)/3.0
    objective=weighted.sum(1).mean()
    require(torch.isfinite(values).all().item() and torch.isfinite(objective).item(),'Nonfinite component objective')
    return objective,values.mean(0).detach(),weighted.mean(0).detach()

def adapt(guard):
    verify_inputs()
    require(read(RUN/'PRETRAIN_COMPLETE.json')['baselines']==6,'Six baselines required')
    require(read(RUN/'PRETRAIN_COMPLETE.json')['baseline_manifest_sha256']==sha(RUN/'BASELINE_MANIFEST.json'),'Baseline manifest')
    check_binding(RUN/'baselines',read(RUN/'BASELINE_MANIFEST.json')); runtime()
    folder=RUN/'trajectories'; folder.mkdir(exist_ok=False)
    for _,d,s,p in pairs():
        name=pair_name(d,s); base=RUN/'baselines'/name; b=read(base/'record.json')
        ds=load(RUN/'inputs'/f'corpus-{d}.pt'); a=load(RUN/'inputs'/f'assignment-{s}.pt')
        for arm in ARMS:
            guard.check(disk=True); target=folder/(name+'-'+arm); target.mkdir()
            require(sha(base/'pretrained.pt')==b['checkpoint_sha256'],'Checkpoint binding')
            obj=model(s); obj.load_state_dict(load(base/'pretrained.pt'))
            require(state_hash(obj)==b['pretrained_tensor_sha256'],'Initial state pairing')
            opt=torch.optim.AdamW(obj.parameters(),lr=1e-4,weight_decay=.1,betas=(.9,.999),
                                  eps=1e-8,foreach=False,fused=False)
            require(len(opt.state)==0,'Moments must reset')
            w=a['arm_weights'][arm]; trace=[]; start=time.monotonic(); torch.cuda.reset_peak_memory_stats()
            for epoch in range(10):
                obj.train()
                for step,ids in enumerate(a['orders'][epoch].split(32)):
                    guard.check()
                    tokens,kinds=(v[ids].cuda() for v in ds['train'])
                    objective,component,weighted=component_objective(obj,tokens,kinds,w[ids].cuda())
                    opt.zero_grad(set_to_none=True); objective.backward()
                    number=epoch*16+step+1
                    selected=d==CORPORA[0] and s==MODEL_SEEDS[0][0] and number in (1,160)
                    if selected:
                        snap_before=dict(theta=engine.cpu_state(obj),
                            gradient={n:v.grad.detach().cpu().clone() for n,v in obj.named_parameters()},
                            m={n:opt.state[v]['exp_avg'].detach().cpu().clone() if v in opt.state else torch.zeros_like(v,device='cpu') for n,v in obj.named_parameters()},
                            v={n:opt.state[v]['exp_avg_sq'].detach().cpu().clone() if v in opt.state else torch.zeros_like(v,device='cpu') for n,v in obj.named_parameters()},
                            step=number-1)
                    pre=float(torch.nn.utils.clip_grad_norm_(obj.parameters(),1.,error_if_nonfinite=True))
                    post=float(torch.sqrt(sum((v.grad.double().square().sum() for v in obj.parameters() if v.grad is not None))))
                    require(math.isfinite(pre) and math.isfinite(post) and post<=1.00001,'Clipping/norm failed')
                    opt.step()
                    if selected:
                        save(target/f'step-{number:03d}.pt',dict(before=snap_before,
                            after=dict(theta=engine.cpu_state(obj),
                            m={n:opt.state[v]['exp_avg'].detach().cpu().clone() for n,v in obj.named_parameters()},
                            v={n:opt.state[v]['exp_avg_sq'].detach().cpu().clone() for n,v in obj.named_parameters()},step=number),
                            ids=ids.clone(),weights=w[ids].clone(),data_seed=d,seed=s,arm=arm,
                            pre_clip_norm=pre,post_clip_norm=post),guard)
                        del snap_before
                    require(all(torch.isfinite(v).all().item() for state in opt.state.values()
                                for v in state.values() if isinstance(v,torch.Tensor)),'Nonfinite optimizer')
                    trace.append(dict(epoch=epoch+1,step=step,ids_sha256=engine.tensor_hash(ids),
                        objective=float(objective.detach()),component_means=component.tolist(),
                        weighted_contributions=weighted.tolist(),pre_clip_norm=pre,post_clip_norm=post,
                        clipped=pre>1.,policy='native_AdamW_clip1'))
                check_finite(obj); guard.check(disk=True)
            torch.cuda.synchronize(); metrics,arrays=evaluate(obj,ds,guard)
            cp=save(target/'F10.pt',engine.cpu_state(obj),guard); ap=save(target/'F10-arrays.pt',arrays,guard)
            write(target/'update-trace.json',trace)
            q=a['q']
            write(target/'record.json',dict(data_seed=d,seed=s,pretrain_seed=p,arm=arm,epoch=10,
                width=128,layers=3,lr=1e-4,weight_decay=.1,clip=1,batch=32,updates=160,
                betas=[.9,.999],eps=1e-8,coefficients=[1/3]*3,whole_sequence_weighting=True,
                initial_checkpoint_sha256=b['checkpoint_sha256'],initial_tensor_sha256=b['pretrained_tensor_sha256'],
                data_sha256={k:engine.tensor_hash(*v) for k,v in ds.items()},
                order_sha256=engine.tensor_hash(a['orders']),q_sha256=engine.tensor_hash(q),
                arm_weights_sha256=engine.tensor_hash(w),checkpoint_sha256=cp,arrays_sha256=ap,
                trace_sha256=sha(target/'update-trace.json'),metrics=metrics,
                gradient_clip_fraction=sum(row['clipped'] for row in trace)/160,
                weight_min=float(w.min()),weight_max=float(w.max()),
                ESS=float((w[:,0].double().sum()**2/w[:,0].double().square().sum())),
                elapsed_seconds=time.monotonic()-start,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,manifest_sha256=verify_manifest()))
            print(name,arm,'F10 saved',flush=True)
            del obj,opt; gc.collect(); torch.cuda.empty_cache()
    check_binding(RUN/'inputs',read(RUN/'INPUT_MANIFEST.json'))
    check_binding(RUN/'baselines',read(RUN/'BASELINE_MANIFEST.json'))
    write(RUN/'TRAJECTORY_MANIFEST.json',binding(folder)); guard.check(disk=True)
    write(RUN/'ADAPT_COMPLETE.json',dict(utc=utc(),trajectories=12,
        trajectory_manifest_sha256=sha(RUN/'TRAJECTORY_MANIFEST.json'),manifest_sha256=verify_manifest()))

def fit(guard):
    verify_inputs()
    check_binding(RUN/'baselines',read(RUN/'BASELINE_MANIFEST.json'))
    from fit import fit as estimate,gates
    require((RUN/'ADAPT_COMPLETE.json').is_file(),'Missing adaptations')
    check_binding(RUN/'trajectories',read(RUN/'TRAJECTORY_MANIFEST.json'))
    folder=RUN/'fits'; folder.mkdir(exist_ok=False); rows=[]
    for _,d,s,_ in pairs():
        guard.check(disk=True); name=pair_name(d,s)
        base=load(RUN/'baselines'/name/'initial-arrays.pt')
        final={arm:load(RUN/'trajectories'/(name+'-'+arm)/'F10-arrays.pt') for arm in ARMS}
        q=load(RUN/'inputs'/f'assignment-{s}.pt')['q']
        # Explicit inherited loss arithmetic: float32 subtraction, then promotion.
        gains=(base['train']['loss']-final['R']['train']['loss']).double()
        result=estimate(q.tolist(),gains.tolist(),guard)
        signed={arm:{split:(base[split]['loss']-final[arm][split]['loss']).double().tolist()
                for split in base} for arm in ARMS}
        allocation={arm:{split:{'total_gain':math.fsum(values),'negative_count':sum(x<0 for x in values),
            'signed_gains':values} for split,values in splits.items()} for arm,splits in signed.items()}
        order=sorted(range(512),key=lambda i:(float(q[i]),i))
        target_mass=q.double()/q.double().sum()
        target_cumulative=target_mass[order].cumsum(0).tolist()
        fitted_cumulative=None
        if result['p'] is not None:
            mass=q.double().pow(result['p']); fitted_cumulative=(mass[order]/mass.sum()).cumsum(0).tolist()
        for arm in ARMS:
            vector=signed[arm]['train']; total=math.fsum(vector)
            cumulative=None if total<=1e-10 else torch.tensor([vector[i]/total for i in order],dtype=torch.float64).cumsum(0).tolist()
            allocation[arm]['train']['ascending_q_indices']=order
            allocation[arm]['train']['target_cumulative']=target_cumulative
            allocation[arm]['train']['gain_cumulative']=cumulative
            allocation[arm]['train']['undefined_reason']='nonpositive_or_tiny_total_gain' if total<=1e-10 else None
        allocation['R']['train']['fitted_cumulative']=fitted_cumulative
        record=dict(identity=name,data_seed=d,seed=s,fit=result,mean_R_gain=math.fsum(gains.tolist())/512,
            U_validation_gain=math.fsum(signed['U']['validation'])/256,
            R_validation_gain=math.fsum(signed['R']['validation'])/256,
            R_minus_U_validation=float(final['R']['validation']['loss'].double().mean()-final['U']['validation']['loss'].double().mean()),
            q=q.tolist(),allocation=allocation)
        write(folder/(name+'.json'),record); rows.append(record)
    summary=gates(rows); write(RUN/'CALIBRATION_DECISION.json',summary)
    write(RUN/'FIT_MANIFEST.json',binding(folder)); guard.check(disk=True)
    write(RUN/'FIT_COMPLETE.json',dict(utc=utc(),fit_manifest_sha256=sha(RUN/'FIT_MANIFEST.json'),
        decision_sha256=sha(RUN/'CALIBRATION_DECISION.json'),status=summary['status'],
        independent_audit_pending=True,confirmation_authorized=False))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('prepare','pretrain','adapt','fit'))
    parser.add_argument('--admission',type=Path,required=True)
    args=parser.parse_args(); guard=Guard(args.admission); guard.check(disk=True)
    imports(); globals()[args.phase](guard)
if __name__=='__main__': main()
