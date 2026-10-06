"""v0.4 numerical engine: copied v0.3 data, model, evaluation and pretraining helpers."""
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


