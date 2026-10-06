"""Independent Decimal110 audit on fixed Stage7 binary64 arrays.

This module deliberately does not import precision_math or stage8. Decimal
probabilities/prefixes are rebuilt here; D is evaluated as J(p)-J(0).
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import time
import traceback
sys.dont_write_bytecode = True
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = ROOT/'work/runs/estimator-v08-20260930-01'
GRID = [i/20 for i in range(161)]
PRECISION = 110
BUDGET = 3600
SOURCES = ['core.py', 'precision_math.py', 'stage8.py', 'check_stage8.py',
           'audit_stage8.py', 'analyze_stage8.py', 'analysis_checks.py',
           'PROTOCOL_STAGE8.md', 'README.md']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def array_sha(values):
    return hashlib.sha256(np.asarray(values, dtype='<f8').tobytes(order='C')).hexdigest()


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


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


def historical_inventory():
    files = set()
    for folder in (ROOT/'outputs').iterdir():
        if folder.is_dir() and folder.name.startswith('sequence-weighting-') and folder != HERE:
            files.update(p.relative_to(ROOT).as_posix() for p in folder.rglob('*')
                         if p.is_file() and '__pycache__' not in p.parts)
    for folder in (ROOT/'work/runs').iterdir():
        if folder.is_dir() and not folder.name.startswith('precision-v09-'):
            files.update(p.relative_to(ROOT).as_posix() for p in folder.iterdir() if p.is_file())
            for name in ['source', 'analysis-source']:
                files.update(p.relative_to(ROOT).as_posix() for p in (folder/name).rglob('*') if p.is_file())
    return files


def audit(raw):
    started_clock, started_utc = time.perf_counter(), datetime.now(timezone.utc)
    raw = Path(raw)
    def budget():
        a, b = time.perf_counter()-started_clock, (datetime.now(timezone.utc)-started_utc).total_seconds()
        if max(a, b) > BUDGET:
            raise RuntimeError('Independent precision audit exceeded its prespecified 3600-second budget')
        return a, b
    assert not (raw/'FAILURE.json').exists()
    complete = read(raw/'COMPLETE.json')
    assert complete['status'] == 'COMPLETE' and complete['cases'] == 1536 and complete['blocks'] == 128
    assert complete['failed_cases'] == [] and complete['training'] is False and complete['original_estimates_modified'] is False
    assert 0 < complete['elapsed_seconds'] <= BUDGET and 0 < complete['utc_elapsed_seconds'] <= BUDGET
    assert math.isfinite(complete['peak_rss_mib']) and complete['peak_rss_mib'] > 0
    manifest = read(raw/'source_manifest.json')
    assert set(manifest) == set(SOURCES)
    for name, digest in manifest.items():
        assert sha(HERE/name) == sha(raw/'source'/name) == digest, name
    assert manifest['core.py'] == sha(ROOT/'outputs/sequence-weighting-stage7/core.py')
    freeze, start = read(raw/'FREEZE.json'), read(raw/'START.json')
    assert freeze['status'] == 'PASS' and freeze['new_objective_profiles_computed'] is False
    assert freeze['source_sha256'] == manifest and start['source_and_inputs_verified'] is True
    assert datetime.fromisoformat(freeze['utc']) < datetime.fromisoformat(start['utc']) < datetime.fromisoformat(complete['utc']) < started_utc
    interval = (datetime.fromisoformat(complete['utc'])-datetime.fromisoformat(start['utc'])).total_seconds()
    assert abs(interval-complete['utc_elapsed_seconds']) < 1. and interval <= BUDGET
    for name, key in [('config.json', 'config_sha256'), ('input_manifest.json', 'input_manifest_sha256'),
                      ('CHECKS.json', 'checks_sha256'), ('ANALYSIS_CHECKS.json', 'analysis_checks_sha256'),
                      ('DESIGN_REVIEW.json', 'design_review_sha256')]:
        assert sha(raw/name) == freeze[key]
    for name in ['CHECKS.json', 'ANALYSIS_CHECKS.json', 'DESIGN_REVIEW.json']:
        checks = read(raw/name)
        assert checks['status'] == 'PASS' and checks['source_sha256']
        assert all(k in manifest and v == manifest[k] for k, v in checks['source_sha256'].items())
    assert read(raw/'CHECKS.json')['source_sha256'] == manifest
    expected_config = dict(version='v0.9', run_id=raw.name, parent_run=PARENT.name,
        family='cancellation', ns=[128, 512], generator_ps=[.2, 1.], cs=[1., .1, .01, 1e-12, 0., -.01],
        replicates=list(range(64)), cases=1536, blocks=128, grid=GRID, grid_size=161, anchor_p=0.,
        primary_precision=80, audit_precision=110, convergence_relative_tolerance='1e-50',
        reference_tie_factor='2e-50', budget_seconds=3600, audit_budget_seconds=3600,
        selection='design indices only; all cases retained',
        original_p_role='reference evaluation only; original continuous estimates unchanged')
    assert read(raw/'config.json') == expected_config
    runtime = read(raw/'runtime.json')
    assert runtime['free_disk_bytes'] >= 1024**3 and runtime['python'] == sys.version and runtime['numpy'] == np.__version__
    history = read(raw/'historical_manifest.json')
    assert set(history) == historical_inventory() and len(history) == freeze['historical_files']
    for name, digest in history.items():
        budget()
        assert sha(ROOT/name) == digest, f'Historical change: {name}'
    print(f'Limited historical integrity PASS ({len(history)} files).', flush=True)
    inputs = read(raw/'input_manifest.json')
    assert set(inputs) == {p.relative_to(raw).as_posix() for p in (raw/'inputs').rglob('*') if p.is_file()}
    for name, digest in inputs.items():
        assert sha(raw/name) == digest
    for name in ['COMPLETE.json', 'AUDIT.json', 'config.json', 'source_manifest.json', 'block_manifest.json']:
        assert sha(raw/'inputs'/f'parent_{name}') == sha(PARENT/name)
    parent_complete, parent_audit = read(PARENT/'COMPLETE.json'), read(PARENT/'AUDIT.json')
    assert parent_audit['status'] == 'PASS'
    assert sha(PARENT/'results.jsonl') == parent_complete['results_sha256'] == parent_audit['results_sha256']
    old_rows = [json.loads(line) for line in (PARENT/'results.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(old_rows) == 8320
    selected = [row for row in old_rows if row['family'] == 'cancellation' and row['n'] in [128, 512]
                and row['generator_p'] in [.2, 1.] and row['c'] in [1., .1, .01, 1e-12, 0., -.01]
                and row['replicate'] in range(64)]
    assert selected == read(raw/'inputs/selected_rows.json') and len(selected) == 1536
    expected_ids = {f'n{n}-r{rep:03d}-c{index:02d}' for n in [128, 512] for rep in range(64) for index in range(48, 60)}
    assert {row['id'] for row in selected} == expected_ids
    blocks = sorted({row['block_id'] for row in selected}); assert len(blocks) == 128
    assert {p.name for p in (raw/'inputs/blocks').iterdir()} == {f'{block}.npz' for block in blocks}
    parent_blocks = read(PARENT/'block_manifest.json')
    for block in blocks:
        assert sha(raw/'inputs/blocks'/f'{block}.npz') == sha(PARENT/'blocks'/f'{block}.npz') == parent_blocks[f'blocks/{block}.npz']
    assert sha(raw/'profiles.jsonl') == complete['profiles_sha256']
    profiles = [json.loads(line) for line in (raw/'profiles.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(profiles) == 1536 and {row['source_id'] for row in profiles} == expected_ids
    case_manifest = read(raw/'case_manifest.json')
    assert set(case_manifest) == {f'cases/{block}.json' for block in blocks}
    assert {p.relative_to(raw).as_posix() for p in (raw/'cases').iterdir()} == set(case_manifest)
    for name, digest in case_manifest.items():
        assert sha(raw/name) == digest
    assert profiles == [row for block in blocks for row in read(raw/'cases'/f'{block}.json')]
    output = raw/'audit_profiles'
    output.mkdir(exist_ok=False)
    profile_hashes, classifications = {}, []
    legacy_reasons, decimal_reasons = Counter(), Counter()
    domain_mismatches, eligible_count, original_count, count = [], 0, 0, 0
    for block in blocks:
        budget()
        with np.load(raw/'inputs/blocks'/f'{block}.npz', allow_pickle=False) as arrays:
            weights = arrays['weights'].tolist(); gains_matrix = arrays['gains'].copy()
            assert arrays['weights'].dtype == gains_matrix.dtype == np.dtype('<f8')
        originals = [row for row in selected if row['block_id'] == block]
        measured = read(raw/'cases'/f'{block}.json')
        assert len(originals) == len(measured) == 12
        cache = build_decimal_cache(weights, GRID, budget=budget)
        budget()
        path = output/f'{block}.json'
        with path.open('x', encoding='utf-8') as stream:
            stream.write('[\n')
            saved_count = 0
            try:
                for old, row in zip(originals, measured):
                    budget(); case_start = time.perf_counter()
                    assert row['source_id'] == old['id']
                    gains = gains_matrix[old['array_index']].tolist()
                    assert len(weights) == len(gains) == old['n']
                    assert array_sha(weights) == old['weights_sha256'] and array_sha(gains) == old['gains_sha256']
                    fields = ['block_id', 'n', 'replicate', 'generator_p', 'c', 'truth_p', 'seed_weights',
                              'seed_noise', 'weights_sha256', 'gains_sha256']
                    assert all(row[key] == old[key] for key in fields)
                    assert row['source_array_index'] == old['array_index']
                    assert row['original_p'] == old['p'] and row['original_reason'] == old['reason']
                    assert row['original_objective'] == old['objective'] and row['hp_dps'] == 80
                    assert math.isfinite(row['elapsed_seconds']) and row['elapsed_seconds'] >= 0
                    floating = independent_float_profile(weights, gains, old['p'], cache)
                    assert floating['legacy_reason'] == old['reason']
                    for key, value in floating.items():
                        if key != 'original_point':
                            assert row[key] == value, f'Legacy/stable mismatch: {old["id"]}/{key}'
                    assert (floating['original_point'] is None) == (row['original_point'] is None)
                    if floating['original_point'] is not None:
                        assert all(row['original_point'][key] == value for key, value in floating['original_point'].items())
                        assert row['original_point']['legacy_J'] == old['objective']
                    reference = independent_decimal_profile(weights, gains, GRID, old['p'], cache)
                    try:
                        convergence, classification = compare_references(row, reference, old['id'])
                    except BaseException as exc:
                        # Preserve the computed reference even when its comparison
                        # fails; the enclosing finally closes valid partial JSON.
                        failed_reference = dict(source_id=old['id'], source_array_index=old['array_index'],
                            block_id=block, weights_sha256=old['weights_sha256'], gains_sha256=old['gains_sha256'],
                            **reference, comparison_status='FAILED', error=repr(exc), traceback=traceback.format_exc())
                        if saved_count:
                            stream.write(',\n')
                        json.dump(failed_reference, stream, allow_nan=False); stream.flush()
                        saved_count += 1
                        raise
                    legacy_reasons[str(row['legacy_reason'])] += 1
                    decimal_reasons[str(reference['hp_reason'])] += 1
                    if row['legacy_reason'] != reference['hp_reason']:
                        domain_mismatches.append(old['id'])
                    eligible_count += int(convergence['eligible'])
                    original_count += int(convergence['original_point_checked'])
                    evidence_row = dict(source_id=old['id'], source_array_index=old['array_index'],
                        block_id=block, weights_sha256=old['weights_sha256'], gains_sha256=old['gains_sha256'],
                        **reference, convergence=convergence, classification=classification,
                        elapsed_seconds=time.perf_counter()-case_start)
                    if saved_count:
                        stream.write(',\n')
                    json.dump(evidence_row, stream, allow_nan=False); stream.flush()
                    saved_count += 1; count += 1; classifications.append(classification)
            finally:
                stream.write('\n]\n'); stream.flush()
        profile_hashes[path.relative_to(raw).as_posix()] = sha(path)
        del cache
        if len(profile_hashes) % 8 == 0:
            print(f'AUDIT precision cases {count}/1536; blocks {len(profile_hashes)}/128; seconds={budget()[0]:.1f}', flush=True)
    assert count == 1536 and len(classifications) == 1536 and len(profile_hashes) == 128
    unresolved = [row['source_id'] for row in classifications if row['unresolved']]
    classification_evidence = dict(precision_pair=[80, 110], source_ids=1536, cases=classifications,
        uncertainty_rule='Unresolved if strict argmin, tau-minimizer set or pair classes differ, or a tau boundary is within twice the observed maximum 80/110 contrast drift. These cases remain included; this is numerical convergence evidence, not exact arithmetic.',
        unresolved_source_ids=unresolved, unresolved_count=len(unresolved))
    write_new(raw/'REFERENCE_CLASSIFICATION.json', classification_evidence)
    write_new(raw/'audit_profile_manifest.json', profile_hashes)
    for name, digest in manifest.items():
        assert sha(HERE/name) == sha(raw/'source'/name) == digest
    assert sha(raw/'profiles.jsonl') == complete['profiles_sha256']
    assert sha(PARENT/'results.jsonl') == parent_complete['results_sha256']
    elapsed, utc_elapsed = budget()
    return dict(status='PASS', utc=datetime.now(timezone.utc).isoformat(), run_id=raw.name,
        cases=1536, blocks=128, grid_size=161, primary_precision=80, audit_precision=110,
        eligible_decimal_cases=eligible_count, guard_decimal_cases=1536-eligible_count,
        eligible_grid_points=eligible_count*161, original_points_verified=original_count,
        legacy_reasons=dict(legacy_reasons), decimal_reasons=dict(decimal_reasons),
        domain_mismatch_count=len(domain_mismatches), domain_mismatch_source_ids=domain_mismatches,
        source_sha256=manifest, profiles_sha256=complete['profiles_sha256'],
        input_manifest_sha256=sha(raw/'input_manifest.json'),
        audit_profile_manifest_sha256=sha(raw/'audit_profile_manifest.json'),
        classification_evidence_file='REFERENCE_CLASSIFICATION.json',
        classification_evidence_sha256=sha(raw/'REFERENCE_CLASSIFICATION.json'),
        unresolved_reference_count=len(unresolved), unresolved_source_ids=unresolved,
        original_parent_results_sha256=parent_complete['results_sha256'], original_estimates_modified=False,
        historical_files_unchanged=len(history), historical_manifest_sha256=sha(raw/'historical_manifest.json'),
        historical_coverage='Prior versioned outputs plus raw top-level/source snapshots; not every historical model/sequence array. All selected Stage7 input blocks and original results were separately byte-verified.',
        elapsed_seconds=elapsed, utc_elapsed_seconds=utc_elapsed, timer_difference_seconds=utc_elapsed-elapsed,
        simulation_elapsed_seconds=complete['elapsed_seconds'], simulation_utc_elapsed_seconds=complete['utc_elapsed_seconds'],
        budget_seconds=BUDGET, both_budget_timers_pass=True,
        peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        failed_cases=[], training=False, checks=[
            'frozen sources, scoped checks/review and input manifests match before profile start',
            'all 1536 design-index cases and 128 fixed Stage7 blocks preserved exactly',
            'original continuous estimates byte-bound to audited Stage7 results; original-point objectives independently reevaluated without optimization',
            'all legacy grid objectives and factored float64 contrasts independently reconstructed',
            'own Decimal110 cache and cumulative raw-mass normalization; no Decimal80 cache promotion',
            'all eligible 161 grid points and available original-p points satisfy frozen J/D convergence bounds',
            'direct Decimal110 J-J0 checked against Decimal80 factored contrast; original identity recorded',
            'full Decimal110 profiles and every 80/110 classification comparison retained without filtering',
            'explicit limited historical coverage and dual-clock phase budgets verified'])


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id and args.run_id not in ['.', '..'] and '/' not in args.run_id and '\\' not in args.run_id
    raw = ROOT/'work/runs'/args.run_id
    assert raw.resolve().parent == (ROOT/'work/runs').resolve()
    assert not (raw/'AUDIT.json').exists() and not (raw/'AUDIT_FAILURE.json').exists(), 'Refuse implicit audit resume/overwrite'
    try:
        evidence = audit(raw); write_new(raw/'AUDIT.json', evidence)
        print(json.dumps(dict(status='PASS', cases=evidence['cases'], eligible=evidence['eligible_decimal_cases'],
                              unresolved=evidence['unresolved_reference_count'], elapsed_seconds=evidence['elapsed_seconds'])), flush=True)
    except BaseException as exc:
        write_new(raw/'AUDIT_FAILURE.json', dict(status='FAILED', utc=datetime.now(timezone.utc).isoformat(),
            error=repr(exc), traceback=traceback.format_exc(), no_implicit_retry=True))
        raise


if __name__ == '__main__':
    main()
