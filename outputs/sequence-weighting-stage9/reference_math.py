"""Independent Decimal110 helpers preserved from frozen Stage8 audit source."""
from collections import Counter
from decimal import Decimal, localcontext
import hashlib
import math
import numpy as np
GRID = [i/20 for i in range(161)]
PRECISION = 110

def array_sha(values):
    return hashlib.sha256(np.asarray(values, dtype='<f8').tobytes(order='C')).hexdigest()

def _decimal_model(log_weights, power):
    """Independent route: unshifted exp, cumulative numerator / denominator."""
    p = Decimal.from_float(float(power))
    numerators = [(p*value).exp() for value in log_weights]
    denominator = sum(numerators, Decimal(0))
    running = Decimal(0)
    cumulative = []
    for numerator in numerators:
        running += numerator
        cumulative.append(running/denominator)
    return cumulative


def _float_model(log_weights, power):
    logits = [float(power)*value for value in log_weights]
    shift = max(logits)
    masses = [math.exp(value-shift) for value in logits]
    total = sum(masses)
    probabilities = [mass/total for mass in masses]
    running, cumulative = 0., []
    for probability in probabilities:
        running += probability
        cumulative.append(running)
    return probabilities, cumulative


def build_decimal_cache(weights, grid=None, budget=None):
    """Own precision110 cache. No Decimal80 object or cache is accepted."""
    weights = [float(value) for value in weights]
    grid = list(GRID if grid is None else grid)
    assert grid and grid[0] == 0.
    order = sorted(range(len(weights)), key=lambda i: weights[i])
    with localcontext() as context:
        context.prec = PRECISION
        log_weights = [Decimal.from_float(weights[i]).ln() for i in order]
        decimal_models = []
        for power in grid:
            if budget is not None:
                budget()
            decimal_models.append(_decimal_model(log_weights, power))
    float_logs = [math.log(weights[i]) for i in order]
    return dict(precision=PRECISION, weights_sha256=array_sha(weights), grid=grid,
                order=order, decimal_logs=log_weights, decimal_models=decimal_models,
                float_logs=float_logs, float_models=[_float_model(float_logs, p) for p in grid])


def independent_decimal_profile(weights, gains, grid=None, original_p=None, cache=None):
    weights, gains = list(map(float, weights)), list(map(float, gains))
    grid = list(GRID if grid is None else grid)
    if cache is None:
        cache = build_decimal_cache(weights, grid)
    assert cache['precision'] == PRECISION and cache['weights_sha256'] == array_sha(weights)
    assert cache['grid'] == grid
    with localcontext() as context:
        context.prec = PRECISION
        dw = [Decimal.from_float(value) for value in weights]
        dg = [Decimal.from_float(value) for value in gains]
        total = sum(dg, Decimal(0))
        reason = ('constant_weights' if max(dw)-min(dw) < Decimal.from_float(1e-12)
                  else 'nonpositive_total_gain' if total <= Decimal.from_float(1e-10) else None)
        result = dict(hp_dps=PRECISION, hp_reason=reason, total_gain_hp=str(total),
                      hp_J=None, hp_D=None, original_point=None)
        if original_p is not None:
            result['original_point'] = dict(p=float(original_p), hp_J=None, hp_D=None)
        if reason is not None:
            return result
        # Cumulative raw gains / exact promoted total, not sum of normalized gains.
        running, gprefix = Decimal(0), []
        for index in cache['order']:
            running += dg[index]
            gprefix.append(running/total)
        def objective(q):
            return sum(((g-model)**2 for g, model in zip(gprefix, q)), Decimal(0))/Decimal(len(gains))
        js = [objective(q) for q in cache['decimal_models']]
        ds = [value-js[0] for value in js]
        result.update(hp_J=list(map(str, js)), hp_D=list(map(str, ds)))
        if original_p is not None:
            j = objective(_decimal_model(cache['decimal_logs'], original_p))
            result['original_point'].update(hp_J=str(j), hp_D=str(j-js[0]))
        return result


def independent_float_profile(weights, gains, original_p, cache):
    total = sum(gains)
    reason = ('constant_weights' if max(weights)-min(weights) < 1e-12 else
              'nonpositive_total_gain' if total <= 1e-10 else None)
    out = dict(legacy_reason=reason, total_gain_legacy=total, total_gain_fsum=math.fsum(gains),
               legacy_J=None, naive_D64=None, stable_D64=None, original_point=None)
    if original_p is not None:
        out['original_point'] = dict(p=float(original_p), legacy_J=None, naive_D64=None, stable_D64=None)
    if reason is not None:
        return out
    normalized_gain = [gains[index]/total for index in cache['order']]
    running, gain_prefix = 0., []
    for gain in normalized_gain:
        running += gain
        gain_prefix.append(running)
    def legacy_objective(probabilities):
        running, squared = 0., 0.
        for gain, probability in zip(normalized_gain, probabilities):
            running += gain-probability
            squared += running*running
        return squared/len(gains)
    anchor = cache['float_models'][0][1]
    def contrast(prefix):
        terms = [(base-model)*(2*gain-model-base)
                 for gain, model, base in zip(gain_prefix, prefix, anchor)]
        return math.fsum(terms)/len(gains)
    js = [legacy_objective(model[0]) for model in cache['float_models']]
    out.update(legacy_J=js, naive_D64=[value-js[0] for value in js],
               stable_D64=[contrast(model[1]) for model in cache['float_models']])
    if original_p is not None:
        probabilities, prefix = _float_model(cache['float_logs'], original_p)
        j = legacy_objective(probabilities)
        out['original_point'].update(legacy_J=j, naive_D64=j-js[0], stable_D64=contrast(prefix))
    return out


def compare_references(profile80, profile110, source_id):
    """Convergence plus classifications; unresolved cases remain in all outputs."""
    assert profile80['hp_reason'] == profile110['hp_reason'], '80/110 domain mismatch'
    with localcontext() as context:
        context.prec = PRECISION
        assert Decimal(profile80['total_gain_hp']) == Decimal(profile110['total_gain_hp'])
        if profile110['hp_reason'] is not None:
            assert profile80['hp_J'] is None and profile80['hp_D'] is None
            assert profile80['hp_identity_max_abs_error'] is None
            return (dict(eligible=False, grid_points=0, original_point_checked=False),
                    dict(source_id=source_id, eligible=False, unresolved=False,
                         status='domain_not_comparable', hp_reason=profile110['hp_reason']))
        j80, d80 = [[Decimal(value) for value in profile80[key]] for key in ['hp_J', 'hp_D']]
        j110, d110 = [[Decimal(value) for value in profile110[key]] for key in ['hp_J', 'hp_D']]
        assert len(j80) == len(d80) == len(j110) == len(d110) == len(GRID)
        scale110 = max(Decimal(1), max(abs(value) for value in d110))
        tolerance_d = Decimal('1e-50')*scale110
        errors_j = [abs(a-b) for a, b in zip(j80, j110)]
        errors_d = [abs(a-b) for a, b in zip(d80, d110)]
        tolerances_j = [Decimal('1e-50')*max(Decimal(1), abs(value)) for value in j110]
        assert all(error <= tolerance for error, tolerance in zip(errors_j, tolerances_j)), 'J80/110 convergence failed'
        assert all(error <= tolerance_d for error in errors_d), 'D80/110 convergence failed'
        with localcontext() as c80:
            c80.prec = 80
            identity_errors = [abs((j-j80[0])-d) for j, d in zip(j80, d80)]
            tolerance80 = Decimal('1e-50')*max(Decimal(1), max(abs(d) for d in d80))
            assert max(identity_errors) <= tolerance80
        original_errors = None
        a, b = profile80['original_point'], profile110['original_point']
        assert (a is None) == (b is None)
        if a is not None:
            assert a['p'] == b['p']
            ej, ed = abs(Decimal(a['hp_J'])-Decimal(b['hp_J'])), abs(Decimal(a['hp_D'])-Decimal(b['hp_D']))
            tj = Decimal('1e-50')*max(Decimal(1), abs(Decimal(b['hp_J'])))
            assert ej <= tj and ed <= tolerance_d, 'Original-point convergence failed'
            with localcontext() as c80:
                c80.prec = 80
                identity_errors.append(abs((Decimal(a['hp_J'])-j80[0])-Decimal(a['hp_D'])))
                assert identity_errors[-1] <= tolerance80
            original_errors = dict(J_abs_error=str(ej), D_abs_error=str(ed), J_tolerance=str(tj), D_tolerance=str(tolerance_d))
        assert max(identity_errors) == Decimal(profile80['hp_identity_max_abs_error'])
        tau = Decimal('2e-50')*max(Decimal(1), max(abs(d) for d in d80))
        min80, min110 = min(d80), min(d110)
        index80, index110 = d80.index(min80), d110.index(min110)
        set80 = [i for i, value in enumerate(d80) if value-min80 <= tau]
        set110 = [i for i, value in enumerate(d110) if value-min110 <= tau]
        actual_drift = max(errors_d)
        boundary_margin = 2*actual_drift
        changed_pairs, near_boundary_pairs = [], []
        counts80, counts110 = Counter(), Counter()
        for i in range(len(GRID)):
            for j in range(i+1, len(GRID)):
                delta80, delta110 = d80[i]-d80[j], d110[i]-d110[j]
                a = 0 if abs(delta80) <= tau else 1 if delta80 > 0 else -1
                b = 0 if abs(delta110) <= tau else 1 if delta110 > 0 else -1
                counts80[str(a)] += 1; counts110[str(b)] += 1
                if a != b:
                    changed_pairs.append([i, j])
                if abs(abs(delta110)-tau) <= boundary_margin:
                    near_boundary_pairs.append([i, j])
        near_boundary_min = [i for i, value in enumerate(d110) if abs((value-min110)-tau) <= boundary_margin]
        unresolved = bool(index80 != index110 or set80 != set110 or changed_pairs or near_boundary_pairs or near_boundary_min)
        classification = dict(source_id=source_id, eligible=True, hp_reason=None, unresolved=unresolved,
            status='unresolved_reference_classification' if unresolved else 'reference_classifications_converged',
            tau=str(tau), tau_source='frozen Decimal80 contrast scale, shared by both comparisons',
            strict_minimum_index_80=index80, strict_minimum_index_110=index110,
            strict_argmin_agreement=index80 == index110, minimizer_indices_80=set80, minimizer_indices_110=set110,
            minimizer_set_agreement=set80 == set110, pair_count=12880,
            pairwise_relation_counts_80=dict(counts80), pairwise_relation_counts_110=dict(counts110),
            changed_pair_count=len(changed_pairs), changed_pairs=changed_pairs,
            observed_max_D_drift=str(actual_drift), boundary_margin=str(boundary_margin),
            near_tau_boundary_pair_count=len(near_boundary_pairs), near_tau_boundary_pairs=near_boundary_pairs,
            near_tau_boundary_minimizer_indices=near_boundary_min)
        convergence = dict(eligible=True, grid_points=len(GRID), J_abs_errors=list(map(str, errors_j)),
            D_abs_errors=list(map(str, errors_d)), J_tolerances=list(map(str, tolerances_j)),
            D_tolerance=str(tolerance_d), max_J_abs_error=str(max(errors_j)), max_D_abs_error=str(actual_drift),
            original_point_checked=original_errors is not None, original_point=original_errors,
            original_80_identity_max_abs_error=profile80['hp_identity_max_abs_error'])
        return convergence, classification


