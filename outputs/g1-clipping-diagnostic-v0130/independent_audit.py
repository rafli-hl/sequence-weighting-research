"""Independent raw-array arithmetic and new F10 binary audit; no training."""
import math
import os
import shutil
import time

import torch
from model import Model
from engine import evaluate, tensor_hash
from run import HERE, NEW, ROOT, MAX_BYTES, ARCHIVE_RESERVE_BYTES, RECEIPT_RESERVE_BYTES, RESERVE_BYTES

SECONDS = 600
SCALAR_TOL = 2e-6
FIT_TOL = 1e-6


def check_budget(start):
    if time.monotonic() - start >= SECONDS:
        raise RuntimeError('600-second analysis/audit cap')
    if shutil.disk_usage(ROOT).free < RESERVE_BYTES:
        raise RuntimeError('2-GiB free-space reserve')
    size = sum(p.stat().st_size for root in (HERE, NEW) for p in root.rglob('*') if p.is_file())
    if size + ARCHIVE_RESERVE_BYTES + RECEIPT_RESERVE_BYTES > MAX_BYTES:
        raise RuntimeError('512-MiB raw/output/receipt/archive allowance')


def near(x, y, tol=SCALAR_TOL):
    return math.isfinite(float(x)) and math.isfinite(float(y)) and abs(float(x) - float(y)) <= tol


def _one_fit(weights, gains, saved):
    weights = [float(v) for v in weights]
    gains = [float(v) for v in gains]
    total = sum(gains)
    reason = ('constant_weights' if max(weights)-min(weights) < 1e-12 else
              'nonpositive_total_gain' if total <= 1e-10 else None)
    assert near(total, saved['guard_total_gain'])
    assert near(math.fsum(gains), saved['total_gain'])
    assert near(sum(max(0., x) for x in gains), saved['positive_gain_mass'])
    assert near(-sum(min(0., x) for x in gains), saved['negative_gain_mass'])
    assert near(sum(x < 0 for x in gains)/len(gains), saved['negative_gain_fraction'])
    denominator = saved['positive_gain_mass'] + saved['negative_gain_mass']
    cancellation = None if denominator == 0 else abs(total)/denominator
    if cancellation is None:
        assert saved['cancellation_ratio'] is None
    else:
        assert near(cancellation, saved['cancellation_ratio'])
    if reason:
        assert saved['p'] is None and saved['reason'] == reason
        return None
    assert saved.get('reason') is None
    p = saved['p']
    assert p is not None and 0 <= p <= 8
    order = sorted(range(len(weights)), key=lambda i: weights[i])
    z = [p*math.log(weights[i]) for i in order]
    m = max(z)
    predictions = [math.exp(v-m) for v in z]
    normalizer = sum(predictions)
    residuals, cumulative = [], 0.
    for index, prediction in zip(order, predictions):
        cumulative += gains[index]/total - prediction/normalizer
        residuals.append(cumulative)
    objective = sum(x*x for x in residuals)/len(residuals)
    assert near(objective, saved['objective'], FIT_TOL)
    # Independent bounded search check: objective agreement, without demanding
    # parameter agreement in shallow or multimodal fits.
    logs = [math.log(weights[i]) for i in order]
    ordered_gains = [gains[i]/total for i in order]
    def objective_at(candidate):
        zs = [candidate*x for x in logs]
        shift = max(zs)
        model = [math.exp(z-shift) for z in zs]
        mass = sum(model)
        cumulative = 0.
        score = 0.
        for actual, predicted in zip(ordered_gains, model):
            cumulative += actual-predicted/mass
            score += cumulative*cumulative
        return score/len(logs)
    grid = [i/10 for i in range(81)]
    j = min(range(len(grid)), key=lambda i: objective_at(grid[i]))
    lo, hi = grid[max(0,j-1)], grid[min(80,j+1)]
    phi = (5**.5-1)/2
    for _ in range(35):
        left = hi-phi*(hi-lo)
        right = lo+phi*(hi-lo)
        if objective_at(left) <= objective_at(right):
            hi = right
        else:
            lo = left
    reference = min(objective_at(0.), objective_at(8.), objective_at((lo+hi)/2))
    assert objective <= reference + FIT_TOL
    assert saved['at_lower_bound'] == (p <= .001)
    assert saved['at_upper_bound'] == (p >= 7.999)
    return residuals


def audit_gain(weights, initial, current, saved):
    assert weights.ndim == 1 and len(weights) == len(initial['loss'])
    full = (initial['loss']-current['loss']).double().tolist()
    components = (initial['component_loss'].double()-current['component_loss'].double())
    identity_error = float((components.mean(1)-torch.tensor(full, dtype=torch.float64)).abs().max())
    assert identity_error < SCALAR_TOL
    assert near(saved['identity_max_abs_error'], identity_error)
    fits = {'full': (full, saved['fit'])}
    for i, name in enumerate(('shared', 'group', 'instance')):
        fits[name] = (components[:, i].tolist(), saved['component_fits'][name])
    for name, (gain, fit) in fits.items():
        residual = _one_fit(weights.tolist(), gain, fit)
        recorded = saved['cumulative_residuals'][name]
        if residual is None:
            assert recorded is None
        else:
            assert len(residual) == len(recorded)
            assert max(abs(a-b) for a,b in zip(residual, recorded)) <= FIT_TOL
    return {'defined': sum(fit['p'] is not None for gain, fit in fits.values()),
            'undefined': {name: fit.get('reason') for name, (_, fit) in fits.items() if fit['p'] is None}}


def reevaluate_f10(row, checkpoint_path, datasets, stored, start):
    check_budget(start)
    model = Model(row['width'], row['layers'], 40).cuda()
    state = torch.load(checkpoint_path, weights_only=True)
    model.load_state_dict(state, strict=True)
    for split in ('train', 'validation', 'test'):
        check_budget(start)
        metrics, arrays = evaluate(model, datasets[split])
        for key in ('loss', 'component_loss', 'component_accuracy'):
            assert torch.equal(arrays[key], stored[split][key]), (row['name'], split, key)
        assert near(metrics['loss'], float(stored[split]['loss'].mean()))
    del model
