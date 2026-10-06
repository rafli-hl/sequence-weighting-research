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
NEW = ROOT / 'work/runs/g1-noclip-v0129-20261003-01'
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
RESERVE_BYTES = 2 * 2**30


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
    if storage and sum(p.stat().st_size for p in NEW.rglob('*') if p.is_file()) + ARCHIVE_RESERVE_BYTES > MAX_BYTES:
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
                          'initial': bind(initial), 'control_config': bind(old / 'config.json'),
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
    args = parser.parse_args()
    if not args.execute:
        parser.error('Requires explicit --execute after separate launch approval')
    if NEW.exists():
        raise RuntimeError('Unique run directory already exists; no resume/retry')
    if os.environ.get('CUBLAS_WORKSPACE_CONFIG') != ':4096:8':
        raise RuntimeError('Set CUBLAS_WORKSPACE_CONFIG=:4096:8 before launch')
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    if not torch.cuda.is_available():
        raise RuntimeError('Local CUDA required')
    start = time.monotonic()
    source = source_hashes()
    rows = plan()
    NEW.mkdir(parents=True, exist_ok=False)
    write(NEW / 'plan.json', {'source_sha256': source, 'rows': rows,
          'started_utc': datetime.now(timezone.utc).isoformat(), 'expected_trajectories': 30})
    try:
        for row in rows:
            if source_hashes() != source:
                raise RuntimeError('Source drift')
            train_one(row, source, start)
        budget(start, storage=True)
        write(NEW / 'TRAINING_COMPLETE.json', {'status': 'complete', 'rows': 30,
              'elapsed_seconds': time.monotonic() - start})
    except BaseException as exc:
        write(NEW / 'FAILURE.json', {'error': repr(exc), 'elapsed_seconds': time.monotonic() - start})
        raise


if __name__ == '__main__':
    main()
