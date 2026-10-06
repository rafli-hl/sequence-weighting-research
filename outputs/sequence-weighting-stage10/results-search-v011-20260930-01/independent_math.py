"""Independent Stage 10 Decimal objective-only search on a denser mesh.

Uses unshifted exponentials, cumulative raw numerator ratios and golden-section
brackets. Finite mesh brackets do not certify the global minimum.
"""
from decimal import Decimal, localcontext
import hashlib
import math
import struct

DPS = 110
MESH_DENOMINATOR = 128
WIDTH_TOLERANCE = Decimal('1e-12')
MAX_STEPS = 80


def decimal_p(value):
    if isinstance(value, float):
        return Decimal.from_float(value)
    return Decimal(value)


def _hash(values):
    packed = [struct.pack('<d', float(value)) for value in values]
    return hashlib.sha256(b''.join(packed)).hexdigest()


def _check(budget):
    if budget is not None:
        budget()


def _model(log_weights, power):
    numerators = [(power * log_weight).exp() for log_weight in log_weights]
    denominator = sum(numerators, Decimal(0))
    running, cumulative = Decimal(0), []
    for numerator in numerators:
        running += numerator
        cumulative.append(running / denominator)
    return cumulative


def build_cache(weights, budget=None, dps=DPS):
    weights = [float(value) for value in weights]
    assert weights and all(value > 0 and math.isfinite(value) for value in weights)
    order = sorted(range(len(weights)), key=lambda index: weights[index])
    with localcontext() as context:
        context.prec = dps
        logs = [Decimal.from_float(weights[index]).ln() for index in order]
        mesh = [Decimal(index) / MESH_DENOMINATOR for index in range(8 * MESH_DENOMINATOR + 1)]
        models = []
        for p in mesh:
            _check(budget)
            models.append(_model(logs, p))
    return dict(dps=dps, weights_sha256=_hash(weights), weights=weights,
                order=order, logs=logs, mesh=mesh, models=models)


def _gain_prefix(cache, gains):
    gain_decimals = [Decimal.from_float(float(gain)) for gain in gains]
    total = sum(gain_decimals, Decimal(0))
    cumulative_raw = Decimal(0)
    prefix = []
    for index in cache['order']:
        cumulative_raw += gain_decimals[index]
        prefix.append(cumulative_raw / total)
    return prefix


def _objective(prefix, model):
    differences = [(gain - expected) ** 2 for gain, expected in zip(prefix, model)]
    return sum(differences, Decimal(0)) / Decimal(len(prefix))


def objective_at(cache, gains, p):
    with localcontext() as context:
        context.prec = cache['dps']
        return _objective(_gain_prefix(cache, gains), _model(cache['logs'], decimal_p(p)))


def golden_brackets(mesh, objectives, objective_at, budget=None,
                    width_tolerance=WIDTH_TOLERANCE, max_steps=MAX_STEPS):
    """Refine every local mesh minimum satisfying <= both, < at least one.

    Caller owns Decimal precision. All sampled objective values are retained.
    A finite bracket need not be unimodal; no certification is inferred.
    """
    assert len(mesh) == len(objectives) and len(mesh) >= 2
    ratio = (Decimal(5).sqrt() - 1) / 2
    brackets = []
    for i in range(1, len(mesh) - 1):
        if not (objectives[i] <= objectives[i - 1] and objectives[i] <= objectives[i + 1]
                and (objectives[i] < objectives[i - 1] or objectives[i] < objectives[i + 1])):
            continue
        a, b = mesh[i - 1], mesh[i + 1]
        initial = dict(lo=str(a), hi=str(b), mesh_center=str(mesh[i]), J_center=str(objectives[i]))
        c, d = b - ratio * (b - a), a + ratio * (b - a)
        _check(budget)
        fc = objective_at(c)
        _check(budget)
        fd = objective_at(d)
        trace = [dict(p=str(c), J=str(fc)), dict(p=str(d), J=str(fd))]
        iterations = 0
        for step in range(max_steps):
            _check(budget)
            if b - a <= width_tolerance:
                break
            iterations += 1
            if fc <= fd:
                b, d, fd = d, c, fc
                c = b - ratio * (b - a)
                fc = objective_at(c)
                trace.append(dict(p=str(c), J=str(fc)))
            else:
                a, c, fc = c, d, fd
                d = a + ratio * (b - a)
                fd = objective_at(d)
                trace.append(dict(p=str(d), J=str(fd)))
        converged = b - a <= width_tolerance
        brackets.append(dict(mesh_center_index=i, initial=initial,
            final=dict(lo=str(a), hi=str(b)), width=str(b - a), iterations=iterations,
            converged=converged, status='converged' if converged else 'iteration_limit',
            p=str((a + b) / 2), trace=trace))
    return brackets


def evaluate(weights, gains, original_p, cache, budget=None):
    weights = [float(value) for value in weights]
    gains = [float(value) for value in gains]
    assert len(weights) == len(gains) and _hash(weights) == cache['weights_sha256']
    assert all(math.isfinite(value) for value in gains)
    legacy_reason = ('constant_weights' if max(weights) - min(weights) < 1e-12
                     else 'nonpositive_total_gain' if sum(gains) <= 1e-10 else None)
    with localcontext() as context:
        context.prec = cache['dps']
        decimal_weights = [Decimal.from_float(value) for value in weights]
        total = sum((Decimal.from_float(value) for value in gains), Decimal(0))
        reason = ('constant_weights' if max(decimal_weights) - min(decimal_weights) < Decimal.from_float(1e-12)
                  else 'nonpositive_total_gain' if total <= Decimal.from_float(1e-10) else None)
        result = dict(method='objective_golden', precision=cache['dps'], legacy_reason=legacy_reason,
                      hp_reason=reason, total_gain_hp=str(total), mesh_p=None, mesh_J=None,
                      exact_equal_neighbor_pairs=[], brackets=[], candidates=[], winner=None,
                      original_point=None, mesh_span=None, mesh_minimum=None,
                      all_brackets_converged=None)
        if original_p is not None:
            result['original_point'] = dict(p=str(decimal_p(original_p)), J=None)
        if reason is not None:
            return result
        prefix = _gain_prefix(cache, gains)
        js = []
        for model in cache['models']:
            _check(budget)
            js.append(_objective(prefix, model))
        mesh = cache['mesh']
        result.update(mesh_p=list(map(str, mesh)), mesh_J=list(map(str, js)),
                      mesh_span=str(max(js) - min(js)),
                      mesh_minimum=dict(p=str(mesh[js.index(min(js))]), J=str(min(js))),
                      exact_equal_neighbor_pairs=[[i, i + 1] for i in range(len(js) - 1) if js[i] == js[i + 1]])
        def j_at(p):
            return _objective(prefix, _model(cache['logs'], p))
        brackets = golden_brackets(mesh, js, j_at, budget=budget)
        candidates = [dict(p=str(p), J=str(j), origin='mesh', mesh_index=i)
                      for i, (p, j) in enumerate(zip(mesh, js))]
        for i, bracket in enumerate(brackets):
            _check(budget)
            p = Decimal(bracket['p'])
            candidates.append(dict(p=str(p), J=str(j_at(p)), origin='objective_bracket', bracket_index=i))
        winner = min(candidates, key=lambda row: (Decimal(row['J']), Decimal(row['p'])))
        result.update(brackets=brackets, candidates=candidates, winner=dict(winner),
                      all_brackets_converged=all(bracket['converged'] for bracket in brackets))
        if original_p is not None:
            _check(budget)
            result['original_point']['J'] = str(j_at(decimal_p(original_p)))
        return result
