"""Stage 11: explicit freeze and single local training launch, no auto-resume.

The prepare/freeze workflow creates no model outcomes. run is a separate command.
Only copied Stage11 code is imported, and source hashes are checked throughout.
"""
import argparse
import gc
import os
import platform
import re
import shutil
import subprocess
import sys
import time
PROCESS_START = time.perf_counter()
import traceback
from pathlib import Path
sys.dont_write_bytecode = True
import torch
from config import (ROOT, HERE, CAPS, CONDITIONS, ARMS, EPOCHS, GRID, F_INDEX,
                    TUNE, CONFIRM, PARAMETERS, FREE_START_BYTES, PREP_SECONDS)
from artifacts import read, write, sha, utc, bind, check_binding, source_manifest, event, Budget
from model import Model
from engine import (paired_data, pre_data, weights, orders, tensor_hash,
                    evaluate, train_epoch, cpu_state, pretraining_objective, diagnostics, support_counts)
from policies import tuning_schedule, select, confirmation_schedule
from preparation import assert_launchable
from revision_evidence import verify_reuse, compare_prepared, require


def setup_runtime():
    torch.set_num_threads(4)
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required; no CPU fallback')
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False


def snapshot_environment():
    return dict(python=platform.python_version(), torch=torch.__version__,
        cuda=torch.version.cuda, gpu=torch.cuda.get_device_name(0),
        cudnn=torch.backends.cudnn.version(), threads=torch.get_num_threads(),
        cudnn_benchmark=torch.backends.cudnn.benchmark,
        matmul_tf32=torch.backends.cuda.matmul.allow_tf32,
        cudnn_tf32=torch.backends.cudnn.allow_tf32,
        deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),
        cublas_workspace_config=os.environ.get('CUBLAS_WORKSPACE_CONFIG'),
        package_lock=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))


def run_path(run_id):
    if not re.fullmatch(r'rule-tying-v0128-[a-zA-Z0-9-]+', run_id):
        raise ValueError('Use a unique rule-tying-v0128-* run ID')
    return ROOT/'work'/'runs'/run_id


def save_tensor(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(value, path)
    return bind(path)


def prepare_inputs(args, root, guard):
    """Called only inside the new launcher's timed preparation transaction."""
    guard.check('review and exact dependency reuse')
    review_path = Path(args.review).resolve()
    review = read(review_path)
    require(review['status'] == 'PASS_IMPLEMENTATION_READY_V0128','V2 review status')
    require(review['source_sha256'] == source_manifest(),'V2 review source drift')
    for item in review['evidence']:
        check_binding(item)
    require(review['final_preparation_limit_seconds']==180,'Review preparation limit')
    write(root/'DEPENDENCY_REUSE.json',verify_reuse())
    require(shutil.disk_usage(ROOT).free >= FREE_START_BYTES,'6 GiB start-free guard')
    guard.check('runtime initialization')
    setup_runtime()
    event(root, 'preparation_start', outcomes_computed=False)
    manifest = source_manifest()
    require(manifest==guard.source_sha256,'Source changed since process start')
    (root/'source').mkdir()
    for name in manifest:
        shutil.copyfile(HERE/name, root/'source'/name)
    write(root/'source_manifest.json', manifest)
    guard.check('environment capture')
    environment = snapshot_environment()
    write(root/'environment.json', environment)
    from revision_evidence import FAILED
    require(environment==read(FAILED/'environment.json'),
            'Environment changed since inherited resource benchmark')
    write(root/'design.json', dict(tuning=TUNE, confirmation=CONFIRM, capacities=CAPS,
        grid=GRID, conditions=CONDITIONS, epochs=EPOCHS, inherited_sources=read(HERE/'PARENT_SOURCES.json'),
        review=bind(review_path), limits=read(HERE/'RESOURCE_ACCEPTANCE.json'),
        preparation_revision=bind(HERE/'PREPARATION_INTEGRATION.md')))
    planned = tuning_schedule()
    assert len(planned) == 72
    write(root/'tuning_schedule.json', planned)
    # Exact original generation; each split remains separately visible to training.
    for seed in sorted({d for d,s,p in TUNE+CONFIRM}):
        guard.check(f'generate adaptation corpus {seed}')
        datasets, metadata = paired_data(seed)
        for condition in CONDITIONS:
            folder = root/'corpora'/f'{condition}-{seed}'
            for split, tensors in datasets[condition].items():
                save_tensor(folder/f'{split}.pt', tensors)
            write(folder/'metadata.json', metadata[condition])
    for seed in sorted({p for d,s,p in TUNE+CONFIRM}):
        guard.check(f'generate U corpus {seed}')
        dataset, metadata = pre_data(seed)
        folder = root/'corpora'/f'U-{seed}'
        for split,tensors in dataset.items():
            save_tensor(folder/f'{split}.pt', tensors)
        write(folder/'metadata.json', metadata)
    for seed in sorted({s for d,s,p in TUNE+CONFIRM}):
        guard.check(f'generate assignments {seed}')
        for arm in ARMS:
            save_tensor(root/'assignments'/f'{seed}-{arm}.pt',
                        dict(weights=weights(seed,arm),orders=orders(seed)))
        save_tensor(root/'assignments'/f'{seed}-pretrain.pt',orders(seed,2048,4))
    for d,s,p in TUNE+CONFIRM:
        guard.check(f'support data {d} model {s}')
        for condition in CONDITIONS:
            train = load_data(root,condition,d,['train'])['train']
            for arm in ARMS:
                write(root/'support'/f'{condition}-d{d}-s{s}-{arm}.json',
                      support_counts(train,condition,weights(s,arm)))
    write(root/'INPUT_EQUALITY.json',compare_prepared(root,guard))
    guard.check('final source and storage validation')
    require(source_manifest()==manifest,'Source drift during preparation')
    for name,digest in manifest.items():
        require(sha(root/'source'/name)==digest,'Copied source drift: '+name)
    from config import NEW_STORAGE_BYTES, FREE_RESERVE_BYTES
    limits=read(HERE/'RESOURCE_ACCEPTANCE.json')
    require(shutil.disk_usage(ROOT).free>=FREE_RESERVE_BYTES,'2 GiB reserve guard')
    raw=sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    require(raw+limits['archive_reserve_bytes']<=NEW_STORAGE_BYTES,'4 GiB storage guard')
    files = [bind(p,root) for p in sorted(root.rglob('*')) if p.is_file()
             and p.name not in {'events.jsonl','PREPARATION_IN_PROGRESS.json'}]
    write(root/'INPUT_MANIFEST.json', dict(files=files))
    guard.check('input manifest written')
    return dict(utc=utc(),status='frozen_before_research_outcomes',
        review=bind(review_path),source_sha256=manifest,
        inputs=bind(root/'INPUT_MANIFEST.json',root),
        research_model_outcomes_generated=False)


def load_data(root, condition, seed, splits):
    return {split:torch.load(root/'corpora'/f'{condition}-{seed}'/f'{split}.pt',weights_only=True)
            for split in splits}


def state_hash(model):
    return {key:tensor_hash(value) for key,value in cpu_state(model).items()}


def new_model(width,layers,seed):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    model = Model(width,layers,40).cuda()
    assert sum(p.numel() for p in model.parameters()) == PARAMETERS[width]
    return model


def pretrained(root,width,layers,seed,preseed,budget):
    folder = root/'baselines'/f'U-w{width}-s{seed}-d{preseed}'
    model = new_model(width,layers,seed)
    if folder.exists():
        metadata = read(folder/'result.json')
        assert sha(folder/'pretrained.pt') == metadata['checkpoint_sha256']
        model.load_state_dict(torch.load(folder/'pretrained.pt',weights_only=True))
        assert state_hash(model) == metadata['pretrained_tensor_sha256']
        return model,metadata
    folder.mkdir(parents=True,exist_ok=False)
    start = time.perf_counter()
    torch.cuda.reset_peak_memory_stats()
    save_tensor(folder/'cold.pt',cpu_state(model))
    cold_hash = state_hash(model)
    ds = load_data(root,'U',preseed,['train','validation'])
    order = torch.load(root/'assignments'/f'{seed}-pretrain.pt',weights_only=True)
    optimizer = torch.optim.AdamW(model.parameters(),lr=3e-4,weight_decay=.1)
    history,arrays = [],[]
    for epoch in range(1,5):
        budget.check()
        model.train()
        norms,objectives = [],[]
        for ids in order[epoch-1].split(32):
            tokens,kinds = [x[ids].cuda() for x in ds['train']]
            objective = pretraining_objective(model(tokens[:,:-1]),tokens,kinds)
            optimizer.zero_grad(set_to_none=True)
            objective.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(),5.)
            if not torch.isfinite(objective) or not torch.isfinite(norm):
                raise FloatingPointError('Nonfinite pretraining objective or gradient')
            optimizer.step()
            norms.append(float(norm)); objectives.append(float(objective.detach()))
        metrics,records = {},{}
        for split in ds:
            metrics[split],records[split] = evaluate(model,ds[split])
        history.append(dict(epoch=epoch,**metrics,objective=sum(objectives)/len(objectives),
            gradient_norm_mean=sum(norms)/len(norms),gradient_norm_max=max(norms),
            gradient_clip_fraction=sum(x>5 for x in norms)/len(norms),updates=len(norms)))
        arrays.append(dict(epoch=epoch,**records))
        write(folder/'history.json',history)
        save_tensor(folder/'sequence_losses.pt',arrays)
    save_tensor(folder/'pretrained.pt',cpu_state(model))
    torch.cuda.synchronize()
    metadata = dict(width=width,layers=layers,seed=seed,pretrain_seed=preseed,
        cold_sha256=sha(folder/'cold.pt'),checkpoint_sha256=sha(folder/'pretrained.pt'),
        cold_tensor_sha256=cold_hash,pretrained_tensor_sha256=state_hash(model),
        order_sha256=tensor_hash(order),data_hashes={k:tensor_hash(*v) for k,v in ds.items()},
        elapsed_seconds=time.perf_counter()-start,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
        peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
    write(folder/'result.json',metadata)
    event(root,'pretraining_complete',name=folder.name)
    budget.check(storage=True)
    return model,metadata


def initial_name(c):
    return f'{c["phase"]}-{c["condition"]}-w{c["width"]}-d{c["data_seed"]}-s{c["seed"]}'


def initial(root,c,model,baseline,budget):
    folder = root/'initial'/initial_name(c)
    if folder.exists():
        saved = read(folder/'result.json')
        assert saved['baseline_sha256'] == baseline['checkpoint_sha256']
        assert sha(folder/'sequence_losses.pt') == saved['arrays_sha256']
        return saved,torch.load(folder/'sequence_losses.pt',weights_only=True)
    folder.mkdir(parents=True,exist_ok=False)
    splits = ['train','validation'] + (['test'] if c['phase']=='confirmation' else [])
    ds = load_data(root,c['condition'],c['data_seed'],splits)
    metrics,arrays = {},{}
    for split in splits:
        budget.check()
        if split=='test':
            event(root,'initial_test_evaluation',name=folder.name,selection_sha256=sha(root/'SELECTION_FREEZE.json'))
        metrics[split],arrays[split] = evaluate(model,ds[split])
    save_tensor(folder/'sequence_losses.pt',arrays)
    metadata = dict(condition=c['condition'],width=c['width'],phase=c['phase'],
        data_seed=c['data_seed'],seed=c['seed'],pretrain_seed=c['pretrain_seed'],
        epoch=0,grid_index=None,arm=None,status='complete',**metrics,
        baseline_sha256=baseline['checkpoint_sha256'],arrays_sha256=sha(folder/'sequence_losses.pt'),
        data_sha256={k:tensor_hash(*v) for k,v in ds.items()},clipping=None,
        fit=dict(p=None,reason='no_adaptation'),group_fit=dict(p=None,reason='no_adaptation'))
    write(folder/'result.json',metadata)
    return metadata,arrays


def trajectory(root,c,budget,decisions=None):
    budget.check(storage=True)
    folder = root/'runs'/c['name']
    folder.mkdir(parents=True,exist_ok=False)
    event(root,'trajectory_start',name=c['name'])
    start = time.perf_counter()
    model,baseline = pretrained(root,c['width'],c['layers'],c['seed'],c['pretrain_seed'],budget)
    base,initial_arrays = initial(root,c,model,baseline,budget)
    splits = ['train','validation'] + (['test'] if c['phase']=='confirmation' else [])
    ds = load_data(root,c['condition'],c['data_seed'],splits)
    assignment = torch.load(root/'assignments'/f'{c["seed"]}-{c["arm"]}.pt',weights_only=True)
    w,order = assignment['weights'],assignment['orders']
    metadata = dict(c,baseline_sha256=baseline['checkpoint_sha256'],
        data_sha256={k:tensor_hash(*v) for k,v in ds.items()},weight_sha256=tensor_hash(w),
        order_sha256=tensor_hash(order),initial_alias=initial_name(c),
        source_sha256=read(root/'source_manifest.json'),selection_sha256=
        sha(root/'SELECTION_FREEZE.json') if c['phase']=='confirmation' else None)
    assert metadata['data_sha256'] == base['data_sha256']
    write(folder/'config.json',metadata)
    # Every arm/config aliases one canonical initial evaluation. Exact parameter
    # and complete token/type hashes bind that alias to this trajectory.
    optimizer = torch.optim.AdamW(model.parameters(),lr=c['lr'],weight_decay=c['wd'])
    history = [dict(base,arm=c['arm'],grid_index=c['grid_index'])]
    arrays = [dict(epoch=0,initial_alias=initial_name(c))]
    stats,checkpoint_hashes,retained = [],{},{}
    chosen = decisions[c['condition']][str(c['width'])] if decisions else None
    torch.cuda.reset_peak_memory_stats()
    for epoch in range(1,31):
        budget.check()
        stat = train_epoch(model,optimizer,ds['train'],w,order[epoch-1],c['clip'])
        stats.append(dict(epoch=epoch,**stat))
        if epoch not in EPOCHS:
            continue
        metrics,records = {},{}
        for split in splits:
            if split=='test':
                event(root,'test_evaluation',name=c['name'],epoch=epoch,
                      selection_sha256=sha(root/'SELECTION_FREEZE.json'))
            metrics[split],records[split] = evaluate(model,ds[split])
        diag = diagnostics(w,initial_arrays['train'],records['train'])
        checkpoint_hashes[str(epoch)] = state_hash(model)
        roles = []
        if epoch==30: roles.append('terminal')
        if c['grid_index']==F_INDEX and epoch==10: roles.append('F10')
        if chosen and chosen['grid_index']==c['grid_index'] and chosen['epoch']==epoch: roles.append('R')
        if roles:
            checkpoint = folder/f'epoch-{epoch}.pt'
            save_tensor(checkpoint,cpu_state(model))
            retained[str(epoch)] = dict(roles=roles,sha256=sha(checkpoint))
        history.append(dict(condition=c['condition'],width=c['width'],data_seed=c['data_seed'],
            seed=c['seed'],arm=c['arm'],phase=c['phase'],grid_index=c['grid_index'],epoch=epoch,
            status='complete',**metrics,fit=diag['fit'],group_fit=diag['group_fit'],
            diagnostic=diag,clipping=stat['gradient_clip_fraction']))
        arrays.append(dict(epoch=epoch,**records))
        write(folder/'history.json',history)
        write(folder/'training_stats.json',stats)
        write(folder/'checkpoint_hashes.json',checkpoint_hashes)
        write(folder/'retained_checkpoints.json',retained)
        save_tensor(folder/'sequence_losses.pt',arrays)
    torch.cuda.synchronize()
    write(folder/'result.json',dict(status='complete',config=metadata,
        elapsed_seconds=time.perf_counter()-start,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
        peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
        history_sha256=sha(folder/'history.json'),arrays_sha256=sha(folder/'sequence_losses.pt')))
    budget.check(storage=True)
    event(root,'trajectory_complete',name=c['name'])
    print(f'complete {c["name"]} elapsed={budget.check():.1f}s',flush=True)
    del model,optimizer
    gc.collect()


def run(args):
    root = run_path(args.run_id)
    assert_launchable(root)
    frozen = read(root/'FREEZE.json')
    assert frozen['status']=='frozen_before_research_outcomes'
    assert source_manifest()==frozen['source_sha256']
    check_binding(frozen['review'])
    check_binding(frozen['inputs'],root)
    for item in read(root/'INPUT_MANIFEST.json')['files']:
        check_binding(item,root)
    setup_runtime()
    assert snapshot_environment()==read(root/'environment.json'), 'Environment drift'
    assert shutil.disk_usage(ROOT).free>=FREE_START_BYTES
    with (root/'RUN_STARTED.json').open('x',encoding='utf-8') as stream:
        stream.write('{"utc":"'+utc()+'","resume_allowed":false}\n')
    budget = Budget(root,read(root/'design.json')['limits']['archive_reserve_bytes'])
    schedule = read(root/'tuning_schedule.json')
    try:
        event(root,'training_start',freeze_sha256=sha(root/'FREEZE.json'))
        for c in schedule:
            trajectory(root,c,budget)
        inputs,input_hashes = [],{}
        for c in schedule:
            path = root/'runs'/c['name']/'history.json'
            input_hashes[path.relative_to(root).as_posix()] = sha(path)
            for h in read(path):
                inputs.append({**{k:c[k] for k in ['condition','width','data_seed','seed','grid_index','arm']},
                    'epoch':h['epoch'],'validation_nll':h['validation']['loss']})
        selection = select(inputs)
        confirmation = confirmation_schedule(selection['decisions'])
        write(root/'selection.json',dict(selection,input_hashes=input_hashes,inputs=inputs))
        write(root/'confirmation_schedule.json',confirmation)
        write(root/'SELECTION_FREEZE.json',dict(utc=utc(),selection=bind(root/'selection.json',root),
            schedule=bind(root/'confirmation_schedule.json',root),test_used=False,
            confirmation_training_started=False))
        event(root,'selection_frozen',sha256=sha(root/'SELECTION_FREEZE.json'))
        schedule += confirmation
        # Ensure all 60 condition baselines exist even if R chooses epoch zero.
        for c in confirmation:
            trajectory(root,c,budget,selection['decisions'])
        elapsed = budget.check(storage=True)
        completed = [c['name'] for c in schedule if (root/'runs'/c['name']/'result.json').exists()]
        assert len(completed)==len(schedule)
        write(root/'TRAINING_COMPLETE.json',dict(utc=utc(),elapsed_seconds=elapsed,
            tuning_trajectories=72,confirmation_trajectories=len(confirmation),
            completed=completed,raw_bytes=budget.last_storage,
            analysis_and_independent_audit_pending=True))
        event(root,'training_complete',elapsed_seconds=elapsed)
    except BaseException as exc:
        completed = [c['name'] for c in schedule if (root/'runs'/c['name']/'result.json').exists()]
        write(root/'FAILURE.json',dict(utc=utc(),error=repr(exc),traceback=traceback.format_exc(),
            completed=completed,planned_missing=[c['name'] for c in schedule if c['name'] not in completed],
            confirmation_plan='not selected yet' if not (root/'SELECTION_FREEZE.json').exists() else 'frozen'))
        event(root,'failure',error=repr(exc))
        raise


def main():
    raise SystemExit('Use launch_stage11.py; direct stage11.py execution is disabled in v0.12.2')


if __name__=='__main__':
    main()
