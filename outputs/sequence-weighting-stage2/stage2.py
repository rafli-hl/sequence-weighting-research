"""Frozen v0.3 experiment. All operational paths derive from this file."""
import argparse
import gc
import hashlib
import itertools
import json
import math
import platform
import random
import shutil
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
import torch
from core import exponent, make_data_lists
from model import Model, losses, TYPES

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAPS = [(64, 2), (128, 3), (256, 4)]
EPOCHS = [1, 3, 10, 30, 60]
GRID = [dict(lr=lr, wd=wd, clip=clip) for lr, wd, clip in
        itertools.product([.00003, .0001, .0003], [.1, 1., 10.], [1., None])]
TUNE = [(31415, 101, 93101), (16180, 102, 93102)]
CONFIRM = [(d, s, p) for d, p in [(57721, 93201), (14142, 93202), (17320, 93203)]
           for s in range(201, 206)]
SOURCES = ['stage2.py', 'model.py', 'core.py', 'PROTOCOL_STAGE2.md']


def utc():
    return datetime.now(timezone.utc).isoformat()


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def tensor_hash(*tensors):
    h = hashlib.sha256()
    for t in tensors:
        h.update(str((tuple(t.shape), str(t.dtype))).encode())
        h.update(t.contiguous().numpy().tobytes())
    return h.hexdigest()


def event(root, kind, **details):
    with (root/'events.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps(dict(utc=utc(), kind=kind, **details), allow_nan=False)+'\n')


def data(seed, pretrain=False, include_test=True):
    # Fixed complete generation precedes any choice of evaluation visibility.
    raw, meta = make_data_lists(seed, 'shared' if pretrain else 'mixed',
                                2048 if pretrain else 512, 256, 0 if pretrain else 512)
    pool = random.Random(991).sample(range(32**3), 32**3)
    keys = {}
    for name, (rows, _) in raw.items():
        bounds = ((0, 4096) if name == 'train' else (4096, 8192)) if pretrain else {
            'train': (8192, 16384), 'validation': (16384, 24576), 'test': (24576, 32768)}[name]
        keys[name] = random.Random(seed+77).sample(pool[bounds[0]:bounds[1]], len(rows))
        for row, key in zip(rows, keys[name]):
            row[2:5] = [17+key//1024, 17+key//32 % 32, 17+key % 32]
    meta.pop('sequence_keys')
    meta['sequence_keys_by_split'] = keys
    ds = {name: tuple(torch.tensor(x, dtype=torch.long) for x in pair)
          for name, pair in raw.items() if pair[0]}
    if not include_test:
        ds.pop('test', None)
    return ds, meta


def weights(seed, arm):
    rng = random.Random(1000+seed)
    w = torch.tensor([math.exp(rng.uniform(math.log(.01), math.log(10))) for _ in range(512)])
    if arm == 'uniform':
        w.fill_(1)
    return w/w.mean()


def orders(seed, n=512, epochs=60):
    return torch.stack([torch.randperm(n, generator=torch.Generator().manual_seed(999+seed+e))
                        for e in range(1, epochs+1)])


@torch.no_grad()
def evaluate(model, dataset):
    model.eval()
    seq, comp, acc = [], [], []
    for start in range(0, len(dataset[0]), 32):
        tokens, kinds = (x[start:start+32].cuda() for x in dataset)
        sl, tl, correct = losses(model, tokens, kinds)
        seq.append(sl.cpu())
        cs, ac = [], []
        for j in range(3):
            mask = kinds == j
            count = mask.sum(1).clamp_min(1)
            cs.append(((tl*mask).sum(1)/count).cpu())
            ac.append(((correct*mask).sum(1)/count).cpu())
        comp.append(torch.stack(cs, 1))
        acc.append(torch.stack(ac, 1))
    seq, comp, acc = torch.cat(seq), torch.cat(comp), torch.cat(acc)
    metrics = {'loss': float(seq.mean())}
    for j, typ in enumerate(TYPES):
        if (dataset[1] == j).any():
            metrics[typ] = {'loss': float(comp[:, j].mean()), 'accuracy': float(acc[:, j].mean())}
    return metrics, {'loss': seq, 'component_loss': comp, 'component_accuracy': acc}


def train_epoch(model, optimizer, dataset, w, order, clip):
    model.train()
    norms = []
    for ids in order.split(32):
        tokens, kinds = (x[ids].cuda() for x in dataset)
        sl, _, _ = losses(model, tokens, kinds)
        loss = (sl*w[ids].cuda()).mean()
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), math.inf if clip is None else clip)
        if not torch.isfinite(loss) or not torch.isfinite(norm):
            raise FloatingPointError('Non-finite loss/gradient')
        optimizer.step()
        norms.append(float(norm))
    return {'gradient_norm_mean': sum(norms)/len(norms), 'gradient_norm_max': max(norms),
            'gradient_clip_fraction': 0. if clip is None else sum(x > clip for x in norms)/len(norms),
            'updates': len(norms)}


def cpu_state(model):
    return {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}


def corpus(root, dseed, pretrain=False):
    folder = root/'corpora'/f'{"pre" if pretrain else "adapt"}-{dseed}'
    if folder.exists():
        return torch.load(folder/'dataset.pt', weights_only=True), read(folder/'metadata.json')
    folder.mkdir(parents=True)
    ds, meta = data(dseed, pretrain=pretrain)
    meta['tensor_sha256'] = {name: tensor_hash(*pair) for name, pair in ds.items()}
    torch.save(ds, folder/'dataset.pt')
    meta['file_sha256'] = sha(folder/'dataset.pt')
    write(folder/'metadata.json', meta)
    return ds, meta


def baseline(root, width, layers, seed, preseed):
    folder = root/'baselines'/f'w{width}-s{seed}-d{preseed}'
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    model = Model(width, layers, 40).cuda()
    if folder.exists():
        meta = read(folder/'result.json')
        assert sha(folder/'pretrained.pt') == meta['checkpoint_sha256']
        model.load_state_dict(torch.load(folder/'pretrained.pt', weights_only=True))
        return model, meta
    folder.mkdir(parents=True)
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    torch.save(cpu_state(model), folder/'cold.pt')
    ds, dm = corpus(root, preseed, True)
    opt = torch.optim.AdamW(model.parameters(), lr=.0003, weight_decay=.1)
    order = orders(seed, 2048, 4)
    torch.save(order, folder/'orders.pt')
    hist, records = [], []
    for e in range(1, 5):
        stats = train_epoch(model, opt, ds['train'], torch.ones(2048), order[e-1], 5.)
        tr, trrec = evaluate(model, ds['train'])
        va, varec = evaluate(model, ds['validation'])
        hist.append({'epoch': e, 'train': tr, 'validation': va, **stats})
        records.append({'epoch': e, 'train': trrec, 'validation': varec})
    torch.save(cpu_state(model), folder/'pretrained.pt')
    torch.save(records, folder/'sequence_losses.pt')
    torch.cuda.synchronize()
    meta = dict(width=width, layers=layers, seed=seed, data_seed=preseed, history=hist,
                checkpoint_sha256=sha(folder/'pretrained.pt'), cold_sha256=sha(folder/'cold.pt'),
                data=dm, source_sha256=read(root/'source_manifest.json'),
                batch_order_sha256=tensor_hash(order), elapsed_seconds=time.perf_counter()-start,
                peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
    write(folder/'result.json', meta)
    event(root, 'pretraining_complete', name=folder.name)
    return model, meta


def run(root, phase, width, layers, dseed, seed, preseed, index, setting, arm, selected_epoch=None):
    name = f'{phase}-w{width}-d{dseed}-s{seed}-g{index:02d}-{arm}'
    folder = root/'runs'/name
    if (folder/'result.json').exists():
        return read(folder/'result.json')
    if folder.exists():
        raise RuntimeError(f'Incomplete run retained: {folder}')
    folder.mkdir(parents=True)
    start = time.perf_counter()
    event(root, 'run_start', name=name, phase=phase)
    config = dict(name=name, phase=phase, width=width, layers=layers, data_seed=dseed,
                  seed=seed, pretrain_seed=preseed, grid_index=index, **setting, arm=arm,
                  epochs=60, selected_epoch=selected_epoch, source_sha256=read(root/'source_manifest.json'))
    try:
        model, pre = baseline(root, width, layers, seed, preseed)
        ds, dm = corpus(root, dseed)
        prekeys = set(sum(pre['data']['sequence_keys_by_split'].values(), []))
        adaptkeys = sum(dm['sequence_keys_by_split'].values(), [])
        assert len(set(adaptkeys)) == len(adaptkeys) and prekeys.isdisjoint(adaptkeys)
        w, order = weights(seed, arm), orders(seed)
        torch.save({'weights': w, 'orders': order}, folder/'assignment.pt')
        config.update(parameters=sum(p.numel() for p in model.parameters()),
                      baseline_sha256=pre['checkpoint_sha256'], data_sha256=dm['tensor_sha256'],
                      weight_sha256=tensor_hash(w), batch_order_sha256=tensor_hash(order),
                      weight_effective_sample_size=float(w.sum()**2/w.square().sum()),
                      selection_sha256=sha(root/'selection.json') if phase == 'confirm' else None)
        write(folder/'config.json', config)
        opt = torch.optim.AdamW(model.parameters(), lr=setting['lr'], weight_decay=setting['wd'])
        torch.cuda.reset_peak_memory_stats()
        tr0, initial = evaluate(model, ds['train'])
        va0, vr0 = evaluate(model, ds['validation'])
        hist = [dict(epoch=0, train=tr0, validation=va0,
                     p_star={'p': None, 'reason': 'no_adaptation'}, total_gain=0., negative_gain_fraction=0.)]
        records = [dict(epoch=0, train=initial, validation=vr0)]
        stats, test, test_record = [], None, None
        for e in range(1, 61):
            stat = train_epoch(model, opt, ds['train'], w, order[e-1], setting['clip'])
            stats.append(dict(epoch=e, **stat))
            if e not in EPOCHS:
                continue
            tr, trec = evaluate(model, ds['train'])
            va, varec = evaluate(model, ds['validation'])
            gain = initial['loss']-trec['loss']
            fit = exponent(w.tolist(), gain.tolist())
            fit['at_lower_bound'] = fit['p'] is not None and fit['p'] <= .001
            hist.append(dict(epoch=e, train=tr, validation=va, p_star=fit,
                             total_gain=float(gain.double().sum()),
                             negative_gain_fraction=float((gain < 0).float().mean()),
                             gradient_clip_fraction_cumulative=sum(x['gradient_clip_fraction'] for x in stats)/e,
                             **stat))
            records.append(dict(epoch=e, train=trec, validation=varec))
            if phase == 'confirm' and e == selected_epoch:
                event(root, 'test_evaluation', name=name, epoch=e, selection_sha256=config['selection_sha256'])
                test, test_record = evaluate(model, ds['test'])
                torch.save(cpu_state(model), folder/'selected.pt')
            # Durable recovery evidence even if a later epoch fails.
            write(folder/'history.json', hist)
            write(folder/'epoch_stats.json', stats)
            torch.save(dict(weights=w, checkpoints=records, test=test_record), folder/'sequence_losses.pt')
        torch.save(cpu_state(model), folder/'final.pt')
        torch.cuda.synchronize()
        result = dict(config=config, history=hist, final_test=test, test_epoch=selected_epoch,
                      pretrain_validation=pre['history'][-1]['validation'], epoch_stats=stats,
                      elapsed_seconds=time.perf_counter()-start,
                      peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                      peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
                      model_sha256={'final': sha(folder/'final.pt'),
                                    'selected': sha(folder/'selected.pt') if (folder/'selected.pt').exists() else None},
                      completed_utc=utc(), status='complete')
        write(folder/'result.json', result)
        event(root, 'run_complete', name=name, phase=phase, seconds=result['elapsed_seconds'])
        print(f'DONE {name} seconds={result["elapsed_seconds"]:.2f}', flush=True)
        del model, opt
        gc.collect()
        return result
    except Exception:
        write(folder/'failure.json', dict(config=config, utc=utc(), traceback=traceback.format_exc()))
        event(root, 'run_failed', name=name)
        raise


def validate(root):
    for dseed, _, preseed in TUNE+CONFIRM+[(42424, 99, 93099)]:
        full, fm = data(dseed)
        hidden, hm = data(dseed, include_test=False)
        for split in ['train', 'validation']:
            for a, b in zip(full[split], hidden[split]):
                assert torch.equal(a, b)
            assert torch.equal(full[split][0][:, 1:], hidden[split][0][:, 1:])
        pre, pm = data(preseed, pretrain=True)
        keys = sum(fm['sequence_keys_by_split'].values(), [])+sum(pm['sequence_keys_by_split'].values(), [])
        assert len(keys) == len(set(keys))
        for name, pair in full.items():
            assert pair[0].shape[1] == 41 and pair[1].shape[1] == 40
            assert ((pair[1] >= 0).sum(1) == 12).all()
    for p in [0., .5, 1., 2.]:
        w = [.01, .03, .1, .3, 1., 3., 10.]
        assert abs(exponent(w, [x**p for x in w])['p']-p) < 1e-5
    assert exponent([1., 1.], [1., 2.])['p'] is None
    assert exponent([1., 2.], [-2., 1.])['p'] is None
    signed = [-.1, .4, 1., 3.]
    fit = exponent([.01, .1, 1., 10.], signed)
    assert fit['p'] is not None
    w = [.01, .1, 1., 10.]
    wp = [x**fit['p'] for x in w]
    residual = [g/sum(signed)-q/sum(wp) for g, q in zip(signed, wp)]
    direct = sum(residual[i]*min((i+1)/4, (j+1)/4)*residual[j] for i in range(4) for j in range(4))
    assert abs(direct-fit['objective']) < 1e-12
    write(root/'validation.json', dict(status='PASS', utc=utc(),
          checks=['full token/label/type test-toggle equality for all scheduled corpus seeds',
                  'disjoint pretrain/adaptation/validation/test keys', 'answer counts/shapes',
                  'known exponent recovery', 'signed-gain direct rank-kernel equivalence',
                  'uniform/nonpositive gain undefined']))


def select(root):
    decisions = {}
    for width, _ in CAPS:
        candidates = []
        baseline_scores = []
        for i, setting in enumerate(GRID):
            paths = [root/'runs'/f'tune-w{width}-d{d}-s{s}-g{i:02d}-{arm}'/'history.json'
                     for d, s, _ in TUNE for arm in ['random', 'uniform']]
            # Selection reader accesses validation history only; no test or p* criterion.
            complete = all((p.parent/'result.json').exists() for p in paths)
            if not complete:
                continue
            histories = [read(p) for p in paths]
            if not baseline_scores:
                baseline_scores = [h[0]['validation']['loss'] for h in histories]
            for e in EPOCHS:
                scores = [next(x['validation']['loss'] for x in h if x['epoch'] == e) for h in histories]
                candidates.append(dict(grid_index=i, **setting, epoch=e, validation_nll=sum(scores)/len(scores),
                                       individual_validation_nll=scores))
        if not candidates:
            raise RuntimeError(f'No complete candidate for capacity {width}')
        best = min(candidates, key=lambda x: (x['validation_nll'], x['epoch'], x['lr'], x['wd'], x['clip'] is None))
        decisions[str(width)] = dict(selected=best, candidates=candidates,
                                     epoch0_validation_nll=sum(baseline_scores)/len(baseline_scores),
                                     adapted_worse_than_epoch0=best['validation_nll'] > sum(baseline_scores)/len(baseline_scores))
    return dict(criterion='mean validation NLL across both arms and both tuning replications',
                tie_order=['score', 'earliest epoch', 'ascending LR', 'ascending WD', 'clip 1 before disabled'],
                test_used=False, decisions=decisions)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--phase', choices=['benchmark', 'experiment'], required=True)
    args = ap.parse_args()
    if Path(args.run_id).name != args.run_id:
        raise ValueError('run-id must be a single name')
    root = ROOT/'work/runs'/args.run_id
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    if not torch.cuda.is_available():
        raise RuntimeError('Local CUDA required')
    manifest = {name: sha(HERE/name) for name in SOURCES}
    if args.phase == 'benchmark':
        root.mkdir(parents=True, exist_ok=False)
        (root/'source').mkdir()
        for name in SOURCES:
            shutil.copy2(HERE/name, root/'source'/name)
        write(root/'source_manifest.json', manifest)
        shutil.copy2(ROOT/'migration/environment-lock-D.txt', root/'environment-lock.txt')
        write(root/'runtime.json', dict(utc=utc(), root=str(ROOT), python=platform.python_version(),
              torch=torch.__version__, gpu=torch.cuda.get_device_name(0), precision='float32'))
        event(root, 'protocol_frozen', manifest=manifest)
        validate(root)
        result = run(root, 'benchmark', 256, 4, 42424, 99, 93099, 0, GRID[6], 'random')
        gate = dict(benchmark_seconds=result['elapsed_seconds'],
                    conservative_306_run_projection_seconds=306*result['elapsed_seconds'],
                    proceed=306*result['elapsed_seconds'] <= 4*3600,
                    peak_allocated_mib=result['peak_allocated_mib'],
                    criterion='Only runtime/memory/success; no outcomes inspected')
        write(root/'runtime_gate.json', gate)
        print(json.dumps(gate), flush=True)
    else:
        assert read(root/'source_manifest.json') == manifest, 'Frozen source changed'
        assert read(root/'runtime_gate.json')['proceed'], 'Runtime gate requires versioned design revision'
        event(root, 'grid_started')
        for width, layers in CAPS:
            for i, setting in enumerate(GRID):
                for d, s, p in TUNE:
                    for arm in ['random', 'uniform']:
                        run(root, 'tune', width, layers, d, s, p, i, setting, arm)
        if not (root/'selection.json').exists():
            selection = select(root)
            selection['frozen_utc'] = utc()
            write(root/'selection.json', selection)
            event(root, 'selection_frozen', sha256=sha(root/'selection.json'))
        selection = read(root/'selection.json')
        for width, layers in CAPS:
            chosen = selection['decisions'][str(width)]['selected']
            for d, s, p in CONFIRM:
                for arm in ['random', 'uniform']:
                    run(root, 'confirm', width, layers, d, s, p, chosen['grid_index'],
                        {k: chosen[k] for k in ['lr', 'wd', 'clip']}, arm, chosen['epoch'])
        event(root, 'experiment_complete', tuning_runs=216, confirmation_runs=90)
        write(root/'COMPLETE.json', dict(utc=utc(), tuning_runs=216, confirmation_runs=90))


if __name__ == '__main__':
    main()
