"""Prospective G1 no-clip diagnostic. Never import v0128 launch code."""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = ROOT / 'outputs/sequence-weighting-stage11-v0128'
OLD = ROOT / 'work/runs/rule-tying-v0128-20261001-01'
NEW = ROOT / 'work/runs/g1-noclip-v0130-20261003-01'
OUT = HERE / 'results'
sys.path.insert(0, str(PARENT))
import torch
from model import Model
from engine import evaluate, diagnostics, tensor_hash, cpu_state

CORPORA = {88547: 98201, 88771: 98202, 88993: 98203, 89203: 98204, 89431: 98205}
CAPS = {64: 2, 128: 3, 256: 4}
SEEDS = (150101, 150201)
EPOCHS = (0, 1, 3, 5, 10)
PARENT_FILES = ('core.py', 'model.py', 'engine.py', 'config.py', 'artifacts.py')
MAX_SECONDS = 1200
MAX_BYTES = 512 * 2**20
ARCHIVE_RESERVE_BYTES = 64 * 2**20
RECEIPT_RESERVE_BYTES = 2 * 2**20
RESERVE_BYTES = 2 * 2**30
PARENT_ANCHORS = {
    'TRAINING_COMPLETE.json': '2485f828ab75d4b7731199c693b76cd3b71cca422f7ac31ea391723689a4436f',
    'source_manifest.json': '90a6f6838e36ff9e69bee9e32932cb606195cda2c2160ef251ea0a488e283b2a',
    'environment.json': 'f3a15779199e355fa132232268e48b02ccb1b187bd4845d8bd82856f954e3b4f',
}
AUDIT = ROOT / 'outputs/sequence-weighting-stage11-v0128/results-scientific-audit-v0128-r2-20261002-01/AUDIT_RESULT.json'
AUDIT_SHA = 'c12e570e56c0d96df8df689651ea69404da18725374780f3162b103e3ee99397'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def source_hashes():
    return {str(p.relative_to(ROOT)): sha(p) for p in
            sorted(HERE.glob('*.py')) + sorted(HERE.glob('*.md')) + [PARENT / n for n in PARENT_FILES]}


def verify_approved_manifest(expected_sha):
    path = HERE / 'MANIFEST.txt'
    if len(expected_sha) != 64 or sha(path) != expected_sha.lower():
        raise RuntimeError('Reviewed candidate manifest SHA256 mismatch')
    listed = {}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if line.startswith('sha256 '):
            _, digest, rel = line.split(' ', 2)
            if rel in listed or len(digest) != 64:
                raise RuntimeError('Duplicate/invalid manifest entry')
            listed[rel] = digest
    if listed != source_hashes():
        raise RuntimeError('Reviewed source manifest differs from current source bytes')
    for name, digest in PARENT_ANCHORS.items():
        if sha(OLD / name) != digest:
            raise RuntimeError('Historical run anchor changed: ' + name)
    if sha(AUDIT) != AUDIT_SHA:
        raise RuntimeError('Accepted scientific audit anchor changed')
    completion = read(OLD / 'TRAINING_COMPLETE.json')
    if len(completion['completed']) != 212 or completion['confirmation_trajectories'] != 140:
        raise RuntimeError('Historical completion inventory changed')
    if read(AUDIT)['trajectories'] != 212:
        raise RuntimeError('Historical audit coverage changed')
    inherited = read(OLD / 'source_manifest.json')
    for name in PARENT_FILES:
        if inherited[name] != sha(PARENT / name) or sha(OLD / 'source' / name) != inherited[name]:
            raise RuntimeError('Inherited source drift: ' + name)
    environment = read(OLD / 'environment.json')
    if environment['deterministic_algorithms'] is not False or environment['cublas_workspace_config'] is not None:
        raise RuntimeError('Historical runtime mismatch')
    return {'approved_manifest_sha256': expected_sha.lower(),
            'historical_completion_sha256': PARENT_ANCHORS['TRAINING_COMPLETE.json'],
            'historical_audit_sha256': AUDIT_SHA}


def setup_runtime():
    if os.environ.get('CUBLAS_WORKSPACE_CONFIG') is not None:
        raise RuntimeError('Historical CUBLAS_WORKSPACE_CONFIG must be unset')
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(False)
    if not torch.cuda.is_available():
        raise RuntimeError('Local CUDA required')
    prior = read(OLD / 'environment.json')
    current = {'torch': torch.__version__, 'cuda': torch.version.cuda,
               'gpu': torch.cuda.get_device_name(0), 'threads': torch.get_num_threads(),
               'cudnn_benchmark': torch.backends.cudnn.benchmark,
               'matmul_tf32': torch.backends.cuda.matmul.allow_tf32,
               'cudnn_tf32': torch.backends.cudnn.allow_tf32,
               'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
               'cublas_workspace_config': os.environ.get('CUBLAS_WORKSPACE_CONFIG')}
    if any(current[key] != prior[key] for key in current):
        raise RuntimeError('Historical runtime configuration mismatch')
    return current


def bind(path):
    return {'path': str(path.relative_to(ROOT)).replace('\\', '/'), 'sha256': sha(path), 'bytes': path.stat().st_size}


def check_bound(item):
    p = (ROOT / item['path']).resolve()
    if not p.is_relative_to(ROOT) or sha(p) != item['sha256'] or p.stat().st_size != item['bytes']:
        raise RuntimeError('Input binding mismatch: ' + str(p))
    return p


def budget(start, storage=False):
    if time.monotonic() - start > MAX_SECONDS:
        raise RuntimeError('20-minute training cap')
    if shutil.disk_usage(ROOT).free < RESERVE_BYTES:
        raise RuntimeError('2-GiB free-space reserve')
    if storage and (sum(p.stat().st_size for p in NEW.rglob('*') if p.is_file()) +
                    sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file()) +
                    ARCHIVE_RESERVE_BYTES + RECEIPT_RESERVE_BYTES > MAX_BYTES):
        raise RuntimeError('512-MiB additional storage cap including archive reserve')


def plan():
    rows = []
    for width, layers in CAPS.items():
        for corpus, preseed in CORPORA.items():
            for seed in SEEDS:
                old_name = f'confirm-G1-w{width}-d{corpus}-s{seed}-g02-random'
                old = OLD / 'runs' / old_name
                config = read(old / 'config.json')
                assert (config['width'], config['layers'], config['data_seed'], config['seed'],
                        config['pretrain_seed'], config['arm'], config['clip'], config['lr'], config['wd']) == (
                            width, layers, corpus, seed, preseed, 'random', 1., 1e-4, .1)
                assert read(old / 'retained_checkpoints.json')['10']['roles'].count('F10') == 1
                baseline = OLD / 'baselines' / f'U-w{width}-s{seed}-d{preseed}' / 'pretrained.pt'
                assignment = OLD / 'assignments' / f'{seed}-random.pt'
                datasets = {split: OLD / 'corpora' / f'G1-{corpus}' / f'{split}.pt'
                            for split in ('train', 'validation', 'test')}
                initial = OLD / 'initial' / config['initial_alias'] / 'sequence_losses.pt'
                inputs = {'baseline': bind(baseline), 'assignment': bind(assignment),
                          'baseline_result': bind(baseline.parent / 'result.json'),
                          'initial': bind(initial), 'initial_result': bind(initial.parent / 'result.json'),
                          'control_config': bind(old / 'config.json'),
                          'control_history': bind(old / 'history.json'),
                          'control_arrays': bind(old / 'sequence_losses.pt'),
                          'control_F10': bind(old / 'epoch-10.pt'),
                          'control_result': bind(old / 'result.json'),
                          **{split: bind(p) for split, p in datasets.items()}}
                if inputs['baseline']['sha256'] != config['baseline_sha256']:
                    raise RuntimeError('U checkpoint mismatch')
                if inputs['control_F10']['sha256'] != read(old / 'retained_checkpoints.json')['10']['sha256']:
                    raise RuntimeError('F10 control mismatch')
                if read(old / 'result.json')['status'] != 'complete':
                    raise RuntimeError('Incomplete control')
                old_result = read(old / 'result.json')
                if (old_result['config'] != config or
                    config['source_sha256'] != read(OLD / 'source_manifest.json') or
                    old_result['history_sha256'] != inputs['control_history']['sha256'] or
                    old_result['arrays_sha256'] != inputs['control_arrays']['sha256'] or
                    old_name not in read(OLD / 'TRAINING_COMPLETE.json')['completed']):
                    raise RuntimeError('Historical result/config/array identity mismatch')
                if (sha(baseline.parent / 'result.json') != inputs['baseline_result']['sha256'] or
                    read(baseline.parent / 'result.json')['checkpoint_sha256'] != inputs['baseline']['sha256']):
                    raise RuntimeError('Historical baseline identity mismatch')
                if read(initial.parent / 'result.json')['arrays_sha256'] != inputs['initial']['sha256']:
                    raise RuntimeError('Historical initial arrays identity mismatch')
                rows.append({'name': old_name.replace('confirm-', 'noclip-'), 'width': width,
                             'layers': layers, 'corpus': corpus, 'seed': seed,
                             'pretrain_seed': preseed, 'inputs': inputs,
                             'expected_data_hashes': config['data_sha256'],
                             'expected_weight_hash': config['weight_sha256'],
                             'expected_order_hash': config['order_sha256']})
    assert len(rows) == 30 and len({r['name'] for r in rows}) == 30
    return rows


def train_one(row, source, start):
    budget(start, storage=True)
    folder = NEW / 'runs' / row['name']
    folder.mkdir(parents=True, exist_ok=False)
    paths = {k: check_bound(v) for k, v in row['inputs'].items()}
    ds = {split: torch.load(paths[split], weights_only=True) for split in ('train', 'validation', 'test')}
    for split, pair in ds.items():
        if tensor_hash(*pair) != row['expected_data_hashes'][split]:
            raise RuntimeError('Full token/label/type equality failed: ' + split)
    assignment = torch.load(paths['assignment'], weights_only=True)
    w, orders = assignment['weights'], assignment['orders'][:10]
    if tensor_hash(w) != row['expected_weight_hash'] or tensor_hash(assignment['orders']) != row['expected_order_hash']:
        raise RuntimeError('Weight/order equality failed')
    if tuple(orders.shape) != (10, 512) or any(sorted(x.tolist()) != list(range(512)) for x in orders):
        raise RuntimeError('Invalid first ten batch orders')
    torch.manual_seed(row['seed'])
    torch.cuda.manual_seed_all(row['seed'])
    model = Model(row['width'], row['layers'], 40).cuda()
    model.load_state_dict(torch.load(paths['baseline'], weights_only=True))
    base_result = read(paths['baseline_result'])
    if {k: tensor_hash(v) for k, v in cpu_state(model).items()} != base_result['pretrained_tensor_sha256']:
        raise RuntimeError('U tensor mismatch')
    old_initial = torch.load(paths['initial'], weights_only=True)
    initial_metrics, initial_arrays = {}, {}
    for split in ds:
        initial_metrics[split], initial_arrays[split] = evaluate(model, ds[split])
        for key in ('loss', 'component_loss', 'component_accuracy'):
            if not torch.equal(initial_arrays[split][key], old_initial[split][key]):
                raise RuntimeError('Initial full-array pairing failed: ' + split + '/' + key)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=.1)
    t0 = time.monotonic()
    torch.cuda.reset_peak_memory_stats()
    history, arrays, updates = [], [], []
    for epoch in range(11):
        budget(start)
        if epoch in EPOCHS:
            metrics, records = {}, {}
            for split in ds:
                metrics[split], records[split] = evaluate(model, ds[split])
            diag = None if epoch == 0 else diagnostics(w, initial_arrays['train'], records['train'])
            history.append({'epoch': epoch, 'metrics': metrics, 'diagnostic': diag})
            arrays.append({'epoch': epoch, **records})
            torch.save(arrays, folder / 'sequence_losses.pt')
            write(folder / 'history.json', history)
        if epoch == 10:
            break
        model.train()
        for update, ids in enumerate(orders[epoch].split(32)):
            budget(start)
            tokens, kinds = (x[ids].cuda() for x in ds['train'])
            from model import losses
            seq_loss, _, _ = losses(model, tokens, kinds)
            objective = (seq_loss * w[ids].cuda()).mean()
            optimizer.zero_grad(set_to_none=True)
            if not torch.isfinite(objective) or not torch.isfinite(seq_loss).all():
                raise FloatingPointError('Nonfinite adaptation loss')
            objective.backward()
            grad_sq = torch.zeros((), device='cuda')
            for p in model.parameters():
                if p.grad is not None:
                    if not torch.isfinite(p.grad).all():
                        raise FloatingPointError('Nonfinite adaptation gradient')
                    grad_sq += p.grad.float().square().sum()
            norm = float(grad_sq.sqrt())
            if not torch.isfinite(torch.tensor(norm)):
                raise FloatingPointError('Nonfinite gradient norm')
            optimizer.step()
            updates.append({'epoch': epoch + 1, 'update': update, 'gradient_norm': norm,
                            'objective': float(objective.detach())})
        write(folder / 'updates.json', updates)
    torch.cuda.synchronize()
    torch.save(cpu_state(model), folder / 'epoch-10.pt')
    write(folder / 'result.json', {'status': 'complete', 'row': row, 'source_sha256': source,
          'history': bind(folder / 'history.json'), 'arrays': bind(folder / 'sequence_losses.pt'),
          'updates': bind(folder / 'updates.json'), 'F10': bind(folder / 'epoch-10.pt'),
          'elapsed_seconds': time.monotonic() - t0,
          'peak_allocated_mib': torch.cuda.max_memory_allocated() / 2**20,
          'peak_reserved_mib': torch.cuda.max_memory_reserved() / 2**20})
    budget(start, storage=True)
    print('complete', row['name'], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--approved-manifest-sha256', required=True)
    args = parser.parse_args()
    if not args.execute:
        parser.error('Requires explicit --execute after separate launch approval')
    if NEW.exists():
        raise RuntimeError('Unique run directory already exists; no resume/retry')
    start = time.monotonic()
    anchors = verify_approved_manifest(args.approved_manifest_sha256)
    runtime = setup_runtime()
    source = source_hashes()
    rows = plan()
    NEW.mkdir(parents=True, exist_ok=False)
    write(NEW / 'plan.json', {'source_sha256': source, 'anchors': anchors, 'runtime': runtime, 'rows': rows,
          'started_utc': datetime.now(timezone.utc).isoformat(), 'expected_trajectories': 30})
    try:
        for row in rows:
            if source_hashes() != source:
                raise RuntimeError('Source drift')
            train_one(row, source, start)
        budget(start, storage=True)
        write(NEW / 'TRAINING_COMPLETE.json', {'status': 'complete', 'rows': 30,
              'elapsed_seconds_before_receipt': time.monotonic() - start})
        budget(start, storage=True)
    except BaseException as exc:
        (NEW / 'TRAINING_COMPLETE.json').unlink(missing_ok=True)
        write(NEW / 'FAILURE.json', {'error': repr(exc), 'elapsed_seconds': time.monotonic() - start})
        raise


if __name__ == '__main__':
    main()
