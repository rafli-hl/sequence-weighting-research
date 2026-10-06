"""Prespecified objective diagnostics; original estimator is never replaced."""
import math
from decimal import Decimal, localcontext

DPS = 80
GRID = [i / 20 for i in range(161)]


def prefix(values):
    out, running = [], 0.0
    for value in values:
        running += value
        out.append(running)
    return out


def float_model(logs, p):
    z = [p * x for x in logs]
    m = max(z)
    z = [math.exp(x - m) for x in z]
    total = sum(z)
    probabilities = [v / total for v in z]
    return probabilities, prefix(probabilities)


def decimal_model(logs, p):
    power = Decimal.from_float(float(p))
    z = [power * x for x in logs]
    m = max(z)
    z = [(x-m).exp() for x in z]
    total = sum(z, Decimal(0))
    cumulative, running = [], Decimal(0)
    for value in z:
        running += value / total
        cumulative.append(running)
    return cumulative


def build_cache(weights, grid=GRID):
    w = [float(v) for v in weights]
    order = sorted(range(len(w)), key=w.__getitem__)
    logs = [math.log(w[i]) for i in order]
    fmodels = [float_model(logs, p) for p in grid]
    with localcontext() as ctx:
        ctx.prec = DPS
        dlogs = [Decimal.from_float(w[i]).ln() for i in order]
        dmodels = [decimal_model(dlogs, p) for p in grid]
    return dict(order=order, logs=logs, float_models=fmodels, decimal_logs=dlogs,
                decimal_models=dmodels, grid=list(grid), dps=DPS)


def legacy_value(gn, probabilities):
    c, loss = 0.0, 0.0
    for a, b in zip(gn, probabilities):
        c += a - b
        loss += c * c
    return loss / len(gn)


def stable_contrast(gprefix, q, anchor):
    return math.fsum((q0-v)*(2*g-v-q0) for g, v, q0 in zip(gprefix, q, anchor)) / len(q)


def decimal_values(gprefix, q, anchor):
    n = Decimal(len(q))
    objective = sum(((g-v)**2 for g, v in zip(gprefix, q)), Decimal(0)) / n
    contrast = sum(((q0-v)*(2*g-v-q0) for g, v, q0 in zip(gprefix, q, anchor)), Decimal(0)) / n
    return objective, contrast


def evaluate(weights, gains, original_p=None, cache=None):
    w, g = [float(v) for v in weights], [float(v) for v in gains]
    if cache is None:
        cache = build_cache(w)
    assert cache['dps'] == DPS
    total = sum(g)
    reason = ('constant_weights' if max(w)-min(w) < 1e-12 else
              'nonpositive_total_gain' if total <= 1e-10 else None)
    out = dict(legacy_reason=reason, hp_reason=None, hp_dps=DPS,
               total_gain_legacy=total, total_gain_fsum=math.fsum(g), total_gain_hp=None,
               legacy_J=None, naive_D64=None, stable_D64=None, hp_J=None, hp_D=None,
               hp_identity_max_abs_error=None, original_point=None)
    if original_p is not None:
        out['original_point'] = dict(p=float(original_p), legacy_J=None, naive_D64=None,
                                     stable_D64=None, hp_J=None, hp_D=None)
    if reason is None:
        gn = [g[i] / total for i in cache['order']]
        cumulative = prefix(gn)
        anchor = cache['float_models'][0][1]
        out['legacy_J'] = [legacy_value(gn, probs) for probs, _ in cache['float_models']]
        out['naive_D64'] = [v - out['legacy_J'][0] for v in out['legacy_J']]
        out['stable_D64'] = [stable_contrast(cumulative, q, anchor) for _, q in cache['float_models']]
        if original_p is not None:
            probs, q = float_model(cache['logs'], float(original_p))
            value = legacy_value(gn, probs)
            out['original_point'].update(legacy_J=value, naive_D64=value-out['legacy_J'][0],
                                         stable_D64=stable_contrast(cumulative, q, anchor))
    with localcontext() as ctx:
        ctx.prec = DPS
        dg = [Decimal.from_float(v) for v in g]
        dt = sum(dg, Decimal(0))
        dw = [Decimal.from_float(v) for v in w]
        dreason = ('constant_weights' if max(dw)-min(dw) < Decimal.from_float(1e-12) else
                   'nonpositive_total_gain' if dt <= Decimal.from_float(1e-10) else None)
        out['hp_reason'], out['total_gain_hp'] = dreason, str(dt)
        if dreason is None:
            cumulative, running = [], Decimal(0)
            for i in cache['order']:
                running += dg[i] / dt
                cumulative.append(running)
            anchor = cache['decimal_models'][0]
            pairs = [decimal_values(cumulative, q, anchor) for q in cache['decimal_models']]
            js, ds = [x[0] for x in pairs], [x[1] for x in pairs]
            out['hp_J'], out['hp_D'] = list(map(str, js)), list(map(str, ds))
            errors = [abs((v-js[0])-d) for v, d in zip(js, ds)]
            tolerance = Decimal('1e-50') * max(Decimal(1), max(abs(d) for d in ds))
            assert max(errors) <= tolerance, '80-digit contrast identity failed'
            if original_p is not None:
                q = decimal_model(cache['decimal_logs'], float(original_p))
                j, d = decimal_values(cumulative, q, anchor)
                errors.append(abs((j-js[0])-d))
                assert errors[-1] <= tolerance
                out['original_point'].update(hp_J=str(j), hp_D=str(d))
            out['hp_identity_max_abs_error'] = str(max(errors))
    return out
