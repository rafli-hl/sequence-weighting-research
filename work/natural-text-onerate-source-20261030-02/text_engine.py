"""Torch functions for the natural-text ladder worker. Imported only by the Linux worker (lazily, via framework setup).

orders() and weights() follow vendor/engine.py exactly (999 + seed + epoch permutations; log-uniform 0.01-10 from
random.Random(1000 + seed), FP32, one mean normalization), generalized to any count n.
"""
import hashlib, math, random
import numpy as np
import torch
from torch.nn import functional as F
import text_plan as plan


def tensor_hash(*tensors):
    h = hashlib.sha256()
    for tensor in tensors:
        value = tensor.detach().cpu().contiguous()
        h.update(str((tuple(value.shape), str(value.dtype))).encode('utf-8'))
        h.update(value.numpy().tobytes())
    return h.hexdigest()


def cpu_state(model):
    return {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}


def load_sequences(raw, indices):
    """Rows `indices` of a little-endian uint16 sequence file (SEQ_TOKENS ids per row) as an int64 tensor."""
    a = np.frombuffer(raw, dtype='<u2').reshape(-1, plan.SEQ_TOKENS)
    return torch.from_numpy(a[np.asarray(indices, dtype=np.int64)].astype(np.int64))


def losses(model, tokens):
    """Per-sequence mean next-token NLL over the CONTEXT targets."""
    logits = model(tokens[:, :-1])
    return F.cross_entropy(logits.transpose(1, 2), tokens[:, 1:], reduction='none').mean(1)


@torch.no_grad()
def evaluate(model, tokens, device='cuda', batch=plan.EVAL_BATCH):
    model.eval(); out = []
    for start in range(0, len(tokens), batch):
        out.append(losses(model, tokens[start:start + batch].to(device)).float().cpu())
    return torch.cat(out)


def orders(seed, n, epochs):
    return torch.stack([torch.randperm(n, generator=torch.Generator().manual_seed(999 + seed + epoch)) for epoch in range(1, epochs + 1)])


def weights(seed, n):
    rng = random.Random(1000 + seed)
    w = torch.tensor([math.exp(rng.uniform(math.log(.01), math.log(10))) for _ in range(n)], dtype=torch.float32)
    w = w / w.mean()
    if w.ndim != 1 or not torch.isfinite(w).all() or not (w > 0).all() or w.unique().numel() != w.numel(): raise ValueError('Weights')
    return w
