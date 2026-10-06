"""Stage 10 Decimal derivative search; no historical estimate is replaced.

The complete fixed mesh and every strict derivative sign change are searched.
Finite subdivision is not a global-optimality certificate.
"""
from decimal import Decimal, localcontext
import hashlib
import math
import struct

DPS = 80
MESH_DENOMINATOR = 64
WIDTH_TOLERANCE = Decimal('1e-12')
MAX_STEPS = 40


def decimal_p(value):
    """Preserve supplied Decimal/decimal strings and exact binary64 originals."""
    return Decimal.from_float(value) if isinstance(value, float) else Decimal(value)


def _hash(values):
    return hashlib.sha256(b''.join(struct.pack('<d', float(v)) for v in values)).hexdigest()


def _check(budget):
    if budget is not None:
        budget()


def _model(logs, p):
    logits = [p * x for x in logs]
    shift = max(logits)
    masses = [(x - shift).exp() for x in logits]
    denominator = sum(masses, Decimal(0))
    probabilities = [mass / denominator for mass in masses]
    mean_log = sum((q * x for q, x in zip(probabilities, logs)), Decimal(0))
    cumulative, cumulative_derivative = [], []
    running = running_derivative = Decimal(0)
    for q, x in zip(probabilities, logs):
        running += q
        running_derivative += q * (x - mean_log)
        cumulative.append(running)
        cumulative_derivative.append(running_derivative)
    return cumulative, cumulative_derivative


def build_cache(weights, budget=None, dps=DPS):
    weights = list(map(float, weights))
    assert weights and all(math.isfinite(w) and w > 0 for w in weights)
    order = sorted(range(len(weights)), key=weights.__getitem__)
    with localcontext() as ctx:
        ctx.prec = dps
        logs = [Decimal.from_float(weights[i]).ln() for i in order]
        mesh = [Decimal(i) / MESH_DENOMINATOR for i in range(8 * MESH_DENOMINATOR + 1)]
        models = []
        for p in mesh:
            _check(budget)
            models.append(_model(logs, p))
    return dict(dps=dps, weights_sha256=_hash(weights), weights=weights,
                order=order, logs=logs, mesh=mesh, models=models)


def _gain_prefix(cache, gains):
    values = [Decimal.from_float(float(v)) for v in gains]
    total = sum(values, Decimal(0))
    running, prefix = Decimal(0), []
    for index in cache['order']:
        running += values[index] / total
        prefix.append(running)
    return prefix


def _objective(gprefix, model):
    q, _ = model
    return sum(((g - value) ** 2 for g, value in zip(gprefix, q)), Decimal(0)) / len(q)


def _derivative(gprefix, model):
    q, dq = model
    return -Decimal(2) * sum(((g - value) * derivative for g, value, derivative
                            in zip(gprefix, q, dq)), Decimal(0)) / len(q)


def objective_at(cache, gains, p):
    with localcontext() as ctx:
        ctx.prec = cache['dps']
        return _objective(_gain_prefix(cache, gains), _model(cache['logs'], decimal_p(p)))


def derivative_at(cache, gains, p):
    with localcontext() as ctx:
        ctx.prec = cache['dps']
        return _derivative(_gain_prefix(cache, gains), _model(cache['logs'], decimal_p(p)))


def bisect_sign_changes(mesh, derivatives, derivative_at, budget=None,
                        width_tolerance=WIDTH_TOLERANCE, max_steps=MAX_STEPS):
    """Refine all strict sign changes, including maxima; return full traces.

    Caller owns the Decimal precision context. Exact-zero mesh nodes are kept
    separately by evaluate(), so zero endpoints are not strict brackets.
    """
    assert len(mesh) == len(derivatives) and len(mesh) >= 2
    brackets = []
    for i in range(len(mesh) - 1):
        fa, fb = derivatives[i], derivatives[i + 1]
        if not ((fa < 0 < fb) or (fb < 0 < fa)):
            continue
        a, b = mesh[i], mesh[i + 1]
        initial = dict(lo=str(a), hi=str(b), derivative_lo=str(fa), derivative_hi=str(fb))
        trace = []
        for step in range(max_steps):
            _check(budget)
            if b - a <= width_tolerance:
                break
            m = (a + b) / 2
            fm = derivative_at(m)
            trace.append(dict(p=str(m), derivative=str(fm)))
            if fm == 0:
                a = b = m
                fa = fb = fm
                break
            if (fa < 0 < fm) or (fm < 0 < fa):
                b, fb = m, fm
            else:
                a, fa = m, fm
        converged = b - a <= width_tolerance
        brackets.append(dict(mesh_interval=i, initial=initial,
            final=dict(lo=str(a), hi=str(b), derivative_lo=str(fa), derivative_hi=str(fb)),
            width=str(b - a), iterations=len(trace), converged=converged,
            status='converged' if converged else 'iteration_limit', p=str((a + b) / 2), trace=trace))
    return brackets


def evaluate(weights, gains, original_p, cache, budget=None):
    weights, gains = list(map(float, weights)), list(map(float, gains))
    assert len(weights) == len(gains) and _hash(weights) == cache['weights_sha256']
    assert all(math.isfinite(g) for g in gains)
    legacy_reason = ('constant_weights' if max(weights) - min(weights) < 1e-12
                     else 'nonpositive_total_gain' if sum(gains) <= 1e-10 else None)
    with localcontext() as ctx:
        ctx.prec = cache['dps']
        dw = [Decimal.from_float(w) for w in weights]
        total = sum((Decimal.from_float(g) for g in gains), Decimal(0))
        hp_reason = ('constant_weights' if max(dw) - min(dw) < Decimal.from_float(1e-12)
                     else 'nonpositive_total_gain' if total <= Decimal.from_float(1e-10) else None)
        out = dict(method='derivative_bisection', precision=cache['dps'], legacy_reason=legacy_reason,
                   hp_reason=hp_reason, total_gain_hp=str(total), mesh_p=None, mesh_J=None,
                   mesh_derivative=None, exact_zero_nodes=[], exact_zero_runs=[], brackets=[],
                   candidates=[], winner=None, original_point=None, mesh_span=None,
                   mesh_minimum=None, all_brackets_converged=None)
        if original_p is not None:
            out['original_point'] = dict(p=str(decimal_p(original_p)), J=None)
        if hp_reason is not None:
            return out
        prefix = _gain_prefix(cache, gains)
        js, derivatives = [], []
        for model in cache['models']:
            _check(budget)
            js.append(_objective(prefix, model))
            derivatives.append(_derivative(prefix, model))
        mesh = cache['mesh']
        out.update(mesh_p=list(map(str, mesh)), mesh_J=list(map(str, js)),
                   mesh_derivative=list(map(str, derivatives)), mesh_span=str(max(js) - min(js)),
                   mesh_minimum=dict(p=str(mesh[js.index(min(js))]), J=str(min(js))))
        zero_nodes = [i for i, value in enumerate(derivatives) if value == 0]
        runs = []
        for index in zero_nodes:
            if runs and index == runs[-1][-1] + 1:
                runs[-1].append(index)
            else:
                runs.append([index])
        out.update(exact_zero_nodes=zero_nodes, exact_zero_runs=runs)
        def d_at(p):
            return _derivative(prefix, _model(cache['logs'], p))
        brackets = bisect_sign_changes(mesh, derivatives, d_at, budget=budget)
        candidates = [dict(p=str(p), J=str(j), origin='mesh', mesh_index=i)
                      for i, (p, j) in enumerate(zip(mesh, js))]
        for i, bracket in enumerate(brackets):
            _check(budget)
            p = Decimal(bracket['p'])
            j = _objective(prefix, _model(cache['logs'], p))
            candidates.append(dict(p=str(p), J=str(j), origin='derivative_bracket', bracket_index=i))
        winner = min(candidates, key=lambda c: (Decimal(c['J']), Decimal(c['p'])))
        out.update(brackets=brackets, candidates=candidates, winner=dict(winner),
                   all_brackets_converged=all(b['converged'] for b in brackets))
        if original_p is not None:
            _check(budget)
            out['original_point']['J'] = str(_objective(prefix, _model(cache['logs'], decimal_p(original_p))))
        return out
