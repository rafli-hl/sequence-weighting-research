"""Fresh G1 preconditioning factorial worker; execute only through reviewed manual supervisor."""
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
from common import (HERE, ROOT, RUN, ARMS, ARM_POLICY, CORPORA, PRESEEDS, MODEL_SEEDS, Guard,
                    require, read, write, sha, utc, pairs, pair_name, binding, check_binding,
                    verify_manifest, resources, SNAPSHOT_PAIR, SNAPSHOT_STEPS)

def imports():
    global torch, Model, engine, NormMatchedAdamW
    sys.path.insert(0, str(HERE/'vendor'))
    import torch
    from model import Model
    import engine
    from optimizer import NormMatchedAdamW

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
    require(not RUN.exists(),'Preparation cannot overwrite/resume a run')
    RUN.mkdir(parents=True,exist_ok=False)
    source_hash=verify_manifest()
    write(RUN/'DESIGN_FREEZE.json',dict(version='v0135',utc=utc(),manifest_sha256=source_hash,
        corpus_seeds=CORPORA,pretraining_seeds=PRESEEDS,model_weight_seeds=MODEL_SEEDS,
        arms=ARMS,width=128,layers=3,epochs=10,lr=1e-4,weight_decay=.1,batch=32,
        component_coefficients=[1/3]*3,
        policies=ARM_POLICY,
        primary='mean_corpus mean_seed ((I-Adam_group-U-Adam_group)-(I-isotropic_group-U-isotropic_group))',
        practical_threshold_nats=.01,all_five_positive_required=True,
        interpretation_gates=['native instance penalty > 0 all five corpora','both uniform baseline gains > 0 all five corpora','abs uniform arm group NLL gap <= .01 all five corpora','I-Adam minus I-isotropic > 0 all five corpora'],
        no_clip=True,betas=[.9,.999],eps=1e-8,snapshot_pair=list(SNAPSHOT_PAIR),snapshot_steps=list(SNAPSHOT_STEPS),
        outcomes_generated=False))
    inputs=RUN/'inputs'; inputs.mkdir()
    census=read(HERE/'SEED_CENSUS.json')
    reconciliation=read(HERE/'FRESHNESS_RECONCILIATION.json')
    require(reconciliation['status']=='SOURCE_CANDIDATES_CLEAR_REQUIRES_INDEPENDENT_SEMANTIC_REVIEW' and
            reconciliation['collisions']==[] and reconciliation['census_sha256']==sha(HERE/'SEED_CENSUS.json'),
            'Semantic freshness reconciliation drift')
    all_seeds=set(CORPORA+PRESEEDS+tuple(s for row in MODEL_SEEDS for s in row))
    require(all_seeds==set(census['candidates']) and census['candidate_matches']==[], 'Seed census mismatch')
    require(all_seeds==set(reconciliation['candidates']), 'Semantic candidate identities mismatch')
    # Review binds the census snapshot. Freeze checks every inventoried text file
    # again and rejects drift; do not scan v0135 itself as prior scientific data.
    for row in census['records']:
        guard.check()
        p=ROOT/row['path']
        require(p.is_file() and sha(p)==row['sha256'], 'Historical census input drift: '+row['path'])
    write(RUN/'SEED_VERIFICATION.json',dict(census_sha256=sha(HERE/'SEED_CENSUS.json'),
        all_inventoried_files_unchanged=True, candidate_matches=[], undocumented_seeds_not_ruled_out=True))
    for i,d in enumerate(CORPORA):
        guard.check(disk=True)
        ds,metadata=engine.data(d,'G1',include_test=True)
        validate_dataset(ds)
        save(inputs/f'corpus-{d}.pt',ds,guard)
        write(inputs/f'corpus-{d}.json',metadata)
        pre,meta=engine.pre_data(PRESEEDS[i]); validate_dataset(pre,True)
        # Key namespaces must also be disjoint between pretraining and adaptation.
        adapt_keys=set(x for values in metadata['sequence_keys_by_split'].values() for x in values)
        pre_keys=set(x for values in meta['sequence_keys_by_split'].values() for x in values)
        require(not adapt_keys.intersection(pre_keys),'Pretraining/adaptation key overlap')
        save(inputs/f'pretrain-{PRESEEDS[i]}.pt',pre,guard)
        write(inputs/f'pretrain-{PRESEEDS[i]}.json',meta)
        for s in MODEL_SEEDS[i]:
            w=engine.weights(s,'random')
            order=engine.orders(s,512,10); pre_order=engine.orders(s,2048,4)
            uniform=torch.ones(512,3)
            instance=torch.stack((torch.ones_like(w),torch.ones_like(w),w),1)
            matrices={arm:(uniform if ARM_POLICY[arm][0]=='uniform' else instance).clone() for arm in ARMS}
            require(all(torch.allclose(m.mean(0),torch.ones(3),atol=2e-7,rtol=0) for m in matrices.values()),
                    'Component weight means changed')
            save(inputs/f'assignment-{s}.pt',dict(random_weights=w,orders=order,
                 pretrain_orders=pre_order,arm_weights=matrices),guard)
    write(RUN/'INPUT_MANIFEST.json',binding(inputs))
    guard.check(disk=True)
    write(RUN/'PREPARE_COMPLETE.json',dict(utc=utc(),manifest_sha256=source_hash,
          input_manifest_sha256=sha(RUN/'INPUT_MANIFEST.json'),outcomes_generated=False))

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
    from fixtures import run_fixtures
    fixture_report=run_fixtures(guard)
    write(RUN/'OPTIMIZER_FIXTURES.json',fixture_report)
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
        initial_metrics,initial_arrays=evaluate(obj,{k:adapt[k] for k in ('train','test')},guard)
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
    write(RUN/'PRETRAIN_COMPLETE.json',dict(utc=utc(),baselines=10,
          baseline_manifest_sha256=sha(RUN/'BASELINE_MANIFEST.json'),fixture_sha256=sha(RUN/'OPTIMIZER_FIXTURES.json'),manifest_sha256=verify_manifest()))

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
    require((RUN/'PRETRAIN_COMPLETE.json').is_file(),'Missing ten pretrained checkpoints')
    require(read(RUN/'PRETRAIN_COMPLETE.json')['baseline_manifest_sha256']==sha(RUN/'BASELINE_MANIFEST.json'),
            'Baseline manifest changed')
    check_binding(RUN/'baselines',read(RUN/'BASELINE_MANIFEST.json'))
    runtime()
    require(read(RUN/'OPTIMIZER_FIXTURES.json')['status']=='PASS_PRETRAINING_FIXTURES','Optimizer fixtures missing')
    require(read(RUN/'PRETRAIN_COMPLETE.json')['fixture_sha256']==sha(RUN/'OPTIMIZER_FIXTURES.json'),'Fixture binding changed')
    folder=RUN/'trajectories'; folder.mkdir(exist_ok=False)
    for corpus_index,d,s,p in pairs():
        name=pair_name(d,s); base=RUN/'baselines'/name
        b=read(base/'record.json'); assignment=load(RUN/'inputs'/f'assignment-{s}.pt')
        ds=load(RUN/'inputs'/f'corpus-{d}.pt'); validate_dataset(ds)
        data_hash={k:engine.tensor_hash(*v) for k,v in ds.items()}
        for arm in ARMS:
            guard.check(disk=True); start=time.monotonic()
            target=folder/(name+'-'+arm); target.mkdir()
            require(sha(base/'pretrained.pt')==b['checkpoint_sha256'],'Checkpoint pairing broken')
            obj=model(s); obj.load_state_dict(load(base/'pretrained.pt'))
            require(state_hash(obj)==b['pretrained_tensor_sha256'],'Initial state pairing broken')
            # A fresh optimizer with identical hyperparameters for every arm.
            opt=NormMatchedAdamW(obj.named_parameters(),ARM_POLICY[arm][1])
            snapshot_bindings={}
            w=assignment['arm_weights'][arm]; order=assignment['orders']
            trace=[]; torch.cuda.reset_peak_memory_stats()
            for epoch in range(10):
                obj.train()
                for step,ids in enumerate(order[epoch].split(32)):
                    guard.check()
                    tokens,kinds=(v[ids].cuda() for v in ds['train'])
                    objective,component,weighted=component_objective(obj,tokens,kinds,w[ids].cuda())
                    opt.zero_grad(); objective.backward()
                    number=epoch*16+step+1
                    selected=(d,s)==SNAPSHOT_PAIR and number in SNAPSHOT_STEPS
                    before=opt.capture(gradient=True) if selected else None
                    step_record=opt.step()
                    if selected:
                        after=opt.capture()
                        snap=target/f'step-{number:03d}.pt'
                        snapshot_bindings[snap.name]=save(snap,dict(before=before,after=after,
                            mode=ARM_POLICY[arm][1],lr=1e-4,weight_decay=.1,betas=[.9,.999],eps=1e-8,
                            data_seed=d,seed=s,arm=arm,epoch=epoch+1,batch_index=step,
                            ids_sha256=engine.tensor_hash(ids),scalar=step_record),guard)
                        del before,after
                    trace.append(dict(epoch=epoch+1,step=step,ids_sha256=engine.tensor_hash(ids),
                         objective=float(objective.detach()),unweighted_component_means=component.tolist(),
                         weighted_component_contributions=weighted.tolist(),**step_record))
                check_finite(obj); guard.check(disk=True)
            torch.cuda.synchronize()
            # Fixed final endpoint only; validation/test never select a checkpoint.
            metrics,arrays=evaluate(obj,ds,guard)
            check_finite(obj)
            checkpoint_sha=save(target/'F10.pt',engine.cpu_state(obj),guard)
            array_sha=save(target/'F10-arrays.pt',arrays,guard)
            write(target/'update-trace.json',trace)
            write(target/'record.json',dict(corpus_index=corpus_index,data_seed=d,seed=s,pretrain_seed=p,
                arm=arm,epoch=10,width=128,layers=3,lr=1e-4,weight_decay=.1,clip=None,batch=32,optimizer_mode=ARM_POLICY[arm][1],betas=[.9,.999],eps=1e-8,
                coefficients=[1/3]*3,updates=160,initial_checkpoint_sha256=b['checkpoint_sha256'],
                initial_tensor_sha256=b['pretrained_tensor_sha256'],data_sha256=data_hash,
                order_sha256=engine.tensor_hash(order),random_weights_sha256=engine.tensor_hash(assignment['random_weights']),
                arm_weights_sha256=engine.tensor_hash(w),checkpoint_sha256=checkpoint_sha,
                arrays_sha256=array_sha,trace_sha256=sha(target/'update-trace.json'),metrics=metrics,
                gradient_clip_fraction=0.,snapshot_bindings=snapshot_bindings,
                snapshot_parameter_layout=opt.names,relative_norm_guard=1e-12,
                elapsed_seconds=time.monotonic()-start,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,manifest_sha256=verify_manifest()))
            print(name,arm,'F10 saved',flush=True)
            del obj,opt; gc.collect(); torch.cuda.empty_cache()
    check_binding(RUN/'inputs',read(RUN/'INPUT_MANIFEST.json'))
    check_binding(RUN/'baselines',read(RUN/'BASELINE_MANIFEST.json'))
    write(RUN/'TRAJECTORY_MANIFEST.json',binding(folder))
    guard.check(disk=True)
    write(RUN/'ADAPT_COMPLETE.json',dict(utc=utc(),trajectories=40,epoch=10,
          trajectory_manifest_sha256=sha(RUN/'TRAJECTORY_MANIFEST.json'),manifest_sha256=verify_manifest()))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('prepare','pretrain','adapt'))
    parser.add_argument('--admission',type=Path,required=True)
    args=parser.parse_args()
    guard=Guard(args.admission); guard.check(disk=True)
    imports(); guard.check()
    globals()[args.phase](guard)

if __name__=='__main__': main()
