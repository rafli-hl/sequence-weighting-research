"""Stage11 paired rule-tying data and training primitives; no launch on import."""
import hashlib
import math
import random

import torch

from core import exponent, make_data_lists
from model import losses

TYPES = ('shared', 'group', 'instance')


def tensor_hash(*tensors):
    h = hashlib.sha256()
    for tensor in tensors:
        value = tensor.detach().cpu().contiguous()
        h.update(str((tuple(value.shape), str(value.dtype))).encode('utf-8'))
        h.update(value.numpy().tobytes())
    return h.hexdigest()


def cpu_state(model):
    return {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}


def _namespace(raw, meta, seed, pretrain):
    pool = random.Random(991).sample(range(32**3), 32**3)
    keys = {}
    for name, (rows, _) in raw.items():
        bounds = ((0, 4096) if name == 'train' else (4096, 8192)) if pretrain else {
            'train': (8192, 16384), 'validation': (16384, 24576), 'test': (24576, 32768)}[name]
        keys[name] = random.Random(seed + 77).sample(pool[bounds[0]:bounds[1]], len(rows))
        for row, key in zip(rows, keys[name]):
            row[2:5] = [17 + key // 1024, 17 + key // 32 % 32, 17 + key % 32]
    meta.pop('sequence_keys')
    meta['sequence_keys_by_split'] = keys
    meta['key_namespace'] = 'pretraining' if pretrain else 'adaptation'
    return {name: (torch.tensor(rows, dtype=torch.long), torch.tensor(kinds, dtype=torch.long))
            for name, (rows, kinds) in raw.items() if rows}


def support_counts(dataset, condition, sequence_weights=None):
    """Actual group-rule support; weighted mass is optional and never a filter."""
    tokens, kinds = dataset
    if condition not in ('G16', 'G1'):
        raise ValueError(condition)
    n = len(tokens)
    if sequence_weights is not None and len(sequence_weights) != n:
        raise ValueError('Weight/support length mismatch')
    counts = [[0] * 16 for _ in range(16)]
    rules = [[0] * 16 for _ in range(16 if condition == 'G16' else 1)]
    weighted = [[0.] * 16 for _ in rules] if sequence_weights is not None else None
    answers = [0] * 16
    for row, mask, index in zip(tokens.tolist(), kinds.tolist(), range(n)):
        group = row[1] - 1
        for target_index, kind in enumerate(mask):
            if kind != 1:
                continue
            query = row[target_index] - 52
            answer = row[target_index + 1] - 68
            rule = group if condition == 'G16' else 0
            if not (0 <= group < 16 and 0 <= query < 16 and 0 <= answer < 16):
                raise ValueError('Invalid group/query/answer coding')
            counts[group][query] += 1
            rules[rule][query] += 1
            answers[answer] += 1
            if weighted is not None:
                weighted[rule][query] += float(sequence_weights[index])
    return {'group_query_counts': counts, 'rule_query_counts': rules,
            'rule_query_weight_mass': weighted, 'group_answer_histogram': answers,
            'missing_group_query_cells': sum(x == 0 for row in counts for x in row),
            'missing_rule_query_cells': sum(x == 0 for row in rules for x in row),
            'expected_group_query_count': n * 4 / 256,
            'expected_rule_query_count': n * 4 / (256 if condition == 'G16' else 16)}


def tie_group_rule(dataset, permutation):
    tokens, kinds = (value.clone() for value in dataset)
    permutation = torch.as_tensor(permutation, dtype=torch.long)
    if sorted(permutation.tolist()) != list(range(16)):
        raise ValueError('The tied rule must be a permutation of sixteen answers')
    rows, target_columns = (kinds == 1).nonzero(as_tuple=True)
    query = tokens[rows, target_columns] - 52
    if not ((query >= 0) & (query < 16)).all():
        raise ValueError('Invalid group query')
    tokens[rows, target_columns + 1] = 68 + permutation[query]
    return tokens, kinds


def paired_data(seed):
    raw, original_meta = make_data_lists(seed, 'mixed', 512, 256, 512)
    g16 = _namespace(raw, original_meta, seed, False)
    g1 = {name: tie_group_rule(pair, original_meta['group_permutations'][0]) for name, pair in g16.items()}
    datasets = {'G16': g16, 'G1': g1}
    metadata = {}
    for condition, splits in datasets.items():
        metadata[condition] = dict(original_meta, condition=condition,
            effective_rule_count=16 if condition == 'G16' else 1,
            tensor_sha256={name: tensor_hash(*pair) for name, pair in splits.items()},
            support={name: support_counts(pair, condition) for name, pair in splits.items()})
    return datasets, metadata


def data(seed, condition, include_test=True):
    if condition not in ('G16', 'G1'):
        raise ValueError(condition)
    datasets, metadata = paired_data(seed)
    # Complete generation precedes visibility, including RNG and metadata.
    splits = dict(datasets[condition])
    if not include_test:
        splits.pop('test')
    return splits, metadata[condition]


def pre_data(seed):
    raw, meta = make_data_lists(seed, 'mixed', 2048, 256, 0)
    splits = _namespace(raw, meta, seed, True)
    meta['variant'] = 'U'
    meta['tensor_sha256'] = {name: tensor_hash(*pair) for name, pair in splits.items()}
    return splits, meta


def validate_weights(values, allow_constant=False):
    w = torch.as_tensor(values).detach().cpu()
    if w.ndim != 1 or not len(w) or not torch.isfinite(w).all() or not (w > 0).all():
        raise ValueError('Weights must be a finite positive vector')
    if allow_constant and float(w.max() - w.min()) < 1e-12:
        return
    if w.unique().numel() != w.numel():
        raise ValueError('Tied random weights: stop preparation; no automatic resampling')


def weights(seed, arm):
    if arm not in ('random', 'uniform'):
        raise ValueError(arm)
    rng = random.Random(1000 + seed)
    w = torch.tensor([math.exp(rng.uniform(math.log(.01), math.log(10))) for _ in range(512)], dtype=torch.float32)
    if arm == 'uniform':
        w.fill_(1.)
    w = w / w.mean()
    validate_weights(w, allow_constant=arm == 'uniform')
    return w


def orders(seed, n=512, epochs=30):
    return torch.stack([torch.randperm(n, generator=torch.Generator().manual_seed(999 + seed + epoch))
                        for epoch in range(1, epochs + 1)])


def pretraining_objective(logits, tokens, kinds):
    if logits.shape[:2] != kinds.shape or tokens.shape[1] != kinds.shape[1] + 1:
        raise ValueError('Pretraining shape mismatch')
    logp = logits.log_softmax(-1)
    hard = -logp.gather(-1, tokens[:, 1:, None]).squeeze(-1)
    shared = kinds == 0
    auxiliary = (kinds == 1) | (kinds == 2)
    if not shared.any() or not auxiliary.any():
        raise ValueError('U objective requires both shared and auxiliary positions')
    result = (hard * shared).sum() / shared.sum()
    result = result + (-logp[:, :, 68:84].mean(-1) * auxiliary).sum() / auxiliary.sum()
    if not torch.isfinite(result):
        raise FloatingPointError('Nonfinite U objective')
    return result


@torch.no_grad()
def evaluate(model, dataset, device='cuda'):
    model.eval()
    seq, comp, acc = [], [], []
    for start in range(0, len(dataset[0]), 32):
        tokens, kinds = (x[start:start + 32].to(device) for x in dataset)
        sequence_loss, token_loss, correct = losses(model, tokens, kinds)
        if not torch.isfinite(sequence_loss).all() or not torch.isfinite(token_loss).all():
            raise FloatingPointError('Nonfinite evaluation loss')
        seq.append(sequence_loss.cpu())
        cs, ac = [], []
        for kind in range(3):
            mask = kinds == kind
            count = mask.sum(1)
            if not (count == 4).all():
                raise ValueError('Stage11 requires exactly four answers per component')
            cs.append(((token_loss * mask).sum(1) / count).cpu())
            ac.append(((correct * mask).sum(1) / count).cpu())
        comp.append(torch.stack(cs, 1))
        acc.append(torch.stack(ac, 1))
    sequence_loss, component_loss, component_accuracy = torch.cat(seq), torch.cat(comp), torch.cat(acc)
    metrics = {'loss': float(sequence_loss.mean())}
    for kind, name in enumerate(TYPES):
        metrics[name] = {'loss': float(component_loss[:, kind].mean()),
                         'accuracy': float(component_accuracy[:, kind].mean())}
    return metrics, {'loss': sequence_loss, 'component_loss': component_loss,
                     'component_accuracy': component_accuracy}


def train_epoch(model, optimizer, dataset, w, order, clip, device='cuda'):
    model.train()
    norms = []
    for ids in order.split(32):
        tokens, kinds = (x[ids].to(device) for x in dataset)
        sequence_loss, _, _ = losses(model, tokens, kinds)
        objective = (sequence_loss * w[ids].to(device)).mean()
        optimizer.zero_grad(set_to_none=True)
        objective.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), math.inf if clip is None else clip)
        if not torch.isfinite(objective) or not torch.isfinite(norm):
            raise FloatingPointError('Nonfinite training objective/gradient')
        optimizer.step()
        norms.append(float(norm))
    if not norms:
        raise ValueError('Empty training order')
    return {'gradient_norm_mean': sum(norms) / len(norms), 'gradient_norm_max': max(norms),
            'gradient_clip_fraction': 0. if clip is None else sum(x > clip for x in norms) / len(norms),
            'updates': len(norms)}


def _fit(w, gain, no_adaptation):
    g = gain.double()
    if g.ndim != 1 or len(g) != len(w) or not torch.isfinite(g).all():
        raise FloatingPointError('Invalid or nonfinite gain vector')
    values = g.tolist()
    result = {'p': None, 'reason': 'no_adaptation'} if no_adaptation else exponent(w.tolist(), values)
    if result.get('p') is not None:
        if not math.isfinite(result['p']) or not math.isfinite(result['objective']):
            raise FloatingPointError('Nonfinite exponent fit')
    total = float(g.sum())
    positive = float(g[g > 0].sum())
    negative = float(-g[g < 0].sum())
    result.update(total_gain=total, guard_total_gain=sum(values), mean_gain=float(g.mean()),
        positive_gain_mass=positive, negative_gain_mass=negative,
        cancellation_ratio=None if positive + negative == 0 else abs(total) / (positive + negative),
        negative_gain_fraction=float((g < 0).double().mean()),
        at_lower_bound=result.get('p') is not None and result['p'] <= .001,
        at_upper_bound=result.get('p') is not None and result['p'] >= 7.999)
    return result


def _residuals(w, gain, fit):
    if fit.get('p') is None:
        return None
    order = sorted(range(len(w)), key=lambda index: float(w[index]))
    gs = [float(gain[i]) for i in order]
    ws = [float(w[i]) for i in order]
    z = [fit['p'] * math.log(x) for x in ws]
    shift = max(z)
    model = [math.exp(x - shift) for x in z]
    denominator = sum(float(x) for x in gain)
    normalizer = sum(model)
    cumulative = 0.
    residuals = []
    for g, q in zip(gs, model):
        cumulative += g / denominator - q / normalizer
        residuals.append(cumulative)
    if not all(math.isfinite(x) for x in residuals):
        raise FloatingPointError('Nonfinite cumulative fit residual')
    # Same operation order as core.exponent, without a second numerical search.
    objective = 0.0
    for residual in residuals:
        objective += residual * residual
    objective /= len(residuals)
    if objective != fit['objective']:
        raise AssertionError('Saved residuals disagree with original fit objective')
    return residuals


def diagnostics(w, initial, current, *, no_adaptation=False):
    w = torch.as_tensor(w).detach().cpu()
    validate_weights(w, allow_constant=True)
    for record in (initial, current):
        if record['loss'].dtype != torch.float32 or record['component_loss'].dtype != torch.float32:
            raise TypeError('Saved losses must preserve historical float32 dtype')
        if not torch.isfinite(record['loss']).all() or not torch.isfinite(record['component_loss']).all():
            raise FloatingPointError('Nonfinite saved losses')
        if tuple(record['loss'].shape) != (len(w),) or tuple(record['component_loss'].shape) != (len(w), 3):
            raise ValueError('Saved loss shape mismatch')
    total_gain = (initial['loss'] - current['loss']).double()
    component_gain = initial['component_loss'].double() - current['component_loss'].double()
    if no_adaptation and (torch.count_nonzero(total_gain) or torch.count_nonzero(component_gain)):
        raise ValueError('No-adaptation record has changed losses')
    error = float((component_gain.mean(1) - total_gain).abs().max())
    if not error < 2e-6:
        raise AssertionError(f'Component identity error {error} exceeds inherited tolerance')
    primary = _fit(w, total_gain, no_adaptation)
    components = {name: _fit(w, component_gain[:, index], no_adaptation) for index, name in enumerate(TYPES)}
    residuals = {'full': _residuals(w, total_gain, primary)}
    residuals.update({name: _residuals(w, component_gain[:, index], components[name])
                      for index, name in enumerate(TYPES)})
    return {'fit': primary, 'group_fit': components['group'], 'component_fits': components,
            'primary': primary, 'components': {name: {'fit': value} for name, value in components.items()},
            'identity_max_abs_error': error, 'component_gain_identity_error': error,
            'gain_operation_order': {'full': 'float32 subtraction then float64 promotion',
                                    'components': 'float64 promotion then subtraction'},
            'cumulative_residuals': residuals,
            'residual_order': 'ascending saved sequence weight; stable index order',
            'signed_gain': {name: primary[name] for name in ('total_gain', 'guard_total_gain',
                'positive_gain_mass', 'negative_gain_mass', 'cancellation_ratio', 'negative_gain_fraction')}}
