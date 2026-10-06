"""Independent saved-record audit; never evaluates an objective or runs a search.

This administrative verifier is outside the 13 frozen experiment sources.
It checks stored arithmetic, trace structure, complete reporting and archives.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import time
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
D = Decimal
STATUSES = ['compared', 'guard', 'unresolved', 'not_run']
FLAGS = ['precision_converged', 'search_objective_agreement', 'parameter_agreement',
         'original_objective_agreement', 'original_parameter_agreement',
         'original_better_than_search', 'weak_neighborhood', 'unresolved']
VALUES = ['primary_p', 'reference_p', 'original_p_exact', 'J_primary_110', 'J_reference_110',
          'J_original_110', 'search_signed_gap', 'original_signed_gap', 'search_parameter_delta',
          'original_parameter_delta', 'reference_mesh_span', 'search_objective_tolerance',
          'original_objective_tolerance', 'parameter_tolerance']
COHORTS = ['S4_fixed30', 'S5_R', 'S6_P1_R', 'S6_P2_R', 'S6_P3_R', 'S6_P4_R']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def lines(path):
    return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s.strip()]


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def dec(value):
    return D.from_float(value) if isinstance(value, float) else D(value)


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def counts(values):
    return dict(Counter(values))


def numeric_equal(actual, expected):
    if expected is None:
        assert actual is None
    else:
        assert actual is not None and dec(actual) == expected, (actual, str(expected))


def statistics(values):
    nums = [dec(v) for v in values if v is not None]
    assert all(v.is_finite() for v in nums)
    n = len(nums)
    mean = sum(nums, D(0)) / n if n else None
    sd = (sum(((x - mean) ** 2 for x in nums), D(0)) / (n - 1)).sqrt() if n > 1 else None
    ordered = sorted(nums)
    median = (ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2) if n else None
    return dict(total=len(values), defined=n, undefined=len(values) - n,
                conditional_mean=mean, conditional_sd=sd, conditional_minimum=min(nums) if n else None,
                conditional_maximum=max(nums) if n else None, conditional_median=median,
                unconditional_mean=mean if n == len(values) else None)


def check_stats(actual, values):
    for key, value in statistics(values).items():
        if isinstance(value, int):
            assert actual[key] == value
        else:
            numeric_equal(actual[key], value)


def inspect_search(result, denominator, primary):
    """Replay bracket decisions from saved values, without objective evaluations."""
    precision = 80 if primary else 110
    assert result['precision'] == precision
    assert result['method'] == ('derivative_bisection' if primary else 'objective_golden')
    if result['hp_reason'] is not None:
        assert result['hp_reason'] in ['constant_weights', 'nonpositive_total_gain']
        assert result['mesh_p'] is result['mesh_J'] is result['winner'] is None
        assert not result['candidates'] and not result['brackets']
        return
    mesh = [D(i) / denominator for i in range(8 * denominator + 1)]
    js = list(map(D, result['mesh_J']))
    assert list(map(D, result['mesh_p'])) == mesh and len(js) == len(mesh)
    assert all(j.is_finite() and j >= 0 for j in js)
    assert abs(D(result['mesh_span']) - (max(js) - min(js))) <= D('1e-75')
    assert result['mesh_minimum'] == dict(p=result['mesh_p'][js.index(min(js))], J=str(min(js)))
    if primary:
        ds = list(map(D, result['mesh_derivative']))
        assert len(ds) == len(mesh) and all(d.is_finite() for d in ds)
        eligible = [i for i in range(len(mesh) - 1) if (ds[i] < 0 < ds[i + 1]) or (ds[i + 1] < 0 < ds[i])]
        assert [b['mesh_interval'] for b in result['brackets']] == eligible
        nodes = [i for i, d in enumerate(ds) if d == 0]
        runs = []
        for i in nodes:
            if runs and runs[-1][-1] + 1 == i:
                runs[-1].append(i)
            else:
                runs.append([i])
        assert result['exact_zero_nodes'] == nodes and result['exact_zero_runs'] == runs
    else:
        eligible = [i for i in range(1, len(mesh) - 1) if js[i] <= min(js[i - 1], js[i + 1])
                    and js[i] < max(js[i - 1], js[i + 1])]
        assert [b['mesh_center_index'] for b in result['brackets']] == eligible
        assert result['exact_equal_neighbor_pairs'] == [[i, i + 1] for i in range(len(js) - 1) if js[i] == js[i + 1]]
    candidates = result['candidates']
    assert len(candidates) == len(mesh) + len(eligible)
    for i, c in enumerate(candidates[:len(mesh)]):
        assert c == dict(p=result['mesh_p'][i], J=result['mesh_J'][i], origin='mesh', mesh_index=i)
    for k, (i, bracket) in enumerate(zip(eligible, result['brackets'])):
        initial, final, trace = bracket['initial'], bracket['final'], bracket['trace']
        a, b = mesh[i if primary else i - 1], mesh[i + 1]
        assert D(initial['lo']) == a and D(initial['hi']) == b
        with localcontext() as context:
            context.prec = precision
            if primary:
                fa, fb = ds[i], ds[i + 1]
                assert D(initial['derivative_lo']) == fa and D(initial['derivative_hi']) == fb
                assert len(trace) == bracket['iterations'] <= 40
                for node in trace:
                    assert b - a > D('1e-12')
                    middle, fm = (a + b) / 2, D(node['derivative'])
                    assert D(node['p']) == middle and fm.is_finite()
                    if fm == 0:
                        a = b = middle
                        fa = fb = fm
                    elif (fa < 0 < fm) or (fm < 0 < fa):
                        b, fb = middle, fm
                    else:
                        a, fa = middle, fm
                assert D(final['derivative_lo']) == fa and D(final['derivative_hi']) == fb
            else:
                assert D(initial['mesh_center']) == mesh[i] and D(initial['J_center']) == js[i]
                assert len(trace) == bracket['iterations'] + 2 and bracket['iterations'] <= 80
                ratio = (D(5).sqrt() - 1) / 2
                c, d = b - ratio * (b - a), a + ratio * (b - a)
                assert D(trace[0]['p']) == c and D(trace[1]['p']) == d
                fc, fd = D(trace[0]['J']), D(trace[1]['J'])
                for node in trace[2:]:
                    assert b - a > D('1e-12')
                    if fc <= fd:
                        b, d, fd = d, c, fc
                        c = b - ratio * (b - a)
                        assert D(node['p']) == c
                        fc = D(node['J'])
                    else:
                        a, c, fc = c, d, fd
                        d = a + ratio * (b - a)
                        assert D(node['p']) == d
                        fd = D(node['J'])
                    assert fc.is_finite() and fd.is_finite() and min(fc, fd) >= 0
            assert D(final['lo']) == a and D(final['hi']) == b
            assert D(bracket['width']) == b - a and D(bracket['p']) == (a + b) / 2
        converged = D(bracket['width']) <= D('1e-12')
        assert bracket['converged'] == converged
        assert bracket['status'] == ('converged' if converged else 'iteration_limit')
        candidate = candidates[len(mesh) + k]
        assert candidate['p'] == bracket['p'] and candidate['bracket_index'] == k
        assert candidate['origin'] == ('derivative_bracket' if primary else 'objective_bracket')
    assert all(D(c['J']).is_finite() and D(c['J']) >= 0 for c in candidates)
    assert result['winner'] == sorted(candidates, key=lambda c: (D(c['J']), D(c['p'])))[0]
    assert result['all_brackets_converged'] == all(b['converged'] for b in result['brackets'])


def inspect_comparison(metadata, primary, reference, row):
    for key, value in metadata.items():
        assert row[key] == value, (metadata['source_id'], key)
    assert row['primary_reason'] == primary['hp_reason'] and row['reference_reason'] == reference['hp_reason']
    reasons = []
    if len({primary['hp_reason'], reference['hp_reason'], metadata['expected_guard'],
            primary['legacy_reason'], reference['legacy_reason']}) != 1:
        reasons.append('domain_mismatch')
    expected = {flag: None for flag in FLAGS}
    expected['unresolved'] = False
    if primary['hp_reason'] is not None or reference['hp_reason'] is not None:
        assert row['values'] is None and row['neighborhood'] == [] and row['point_checks'] == []
        expected.update(unresolved=bool(reasons), reasons=reasons)
        assert row['classification'] == expected
        assert row['status'] == ('unresolved' if reasons else 'guard')
        return
    checks = row['point_checks']
    buckets = defaultdict(list)
    for point in checks:
        p, evaluated, ref = D(point['p']), D(point['evaluated_J']), D(point['reference_J'])
        gap, tolerance = evaluated - ref, D('1e-50') * max(D(1), abs(ref))
        assert 0 <= p <= 8 and evaluated.is_finite() and ref.is_finite()
        numeric_equal(point['signed_gap'], gap)
        numeric_equal(point['tolerance'], tolerance)
        assert point['passed'] == (abs(gap) <= tolerance)
        assert point['evaluated_precision'] == (110 if point['label'].startswith('saved_reference') else 80)
        buckets[point['label']].append(point)
    assert len(buckets['shared_mesh']) == 513
    for i, point in enumerate(buckets['shared_mesh']):
        assert D(point['p']) == D(i) / 64
        assert D(point['evaluated_J']) == D(primary['mesh_J'][i])
        assert D(point['reference_J']) == D(reference['mesh_J'][2 * i])
    values = row['values']
    pp, rp = D(primary['winner']['p']), D(reference['winner']['p'])
    op = D.from_float(metadata['original_p']) if metadata['original_p'] is not None else None
    jp, jr = D(values['J_primary_110']), D(values['J_reference_110'])
    jo = D(values['J_original_110']) if op is not None else None
    expected_points = dict(primary_winner=(pp, None, jp), reference_winner=(rp, None, jr),
        saved_primary_winner=(pp, D(primary['winner']['J']), jp),
        saved_reference_winner=(rp, D(reference['winner']['J']), jr))
    if op is not None:
        assert D(primary['original_point']['p']) == D(reference['original_point']['p']) == op
        expected_points.update(original_point=(op, None, jo),
            saved_primary_original=(op, D(primary['original_point']['J']), jo),
            saved_reference_original=(op, D(reference['original_point']['J']), jo))
    for label, (p, evaluated, ref) in expected_points.items():
        assert len(buckets[label]) == 1
        point = buckets[label][0]
        assert D(point['p']) == p and D(point['reference_J']) == ref
        if evaluated is not None:
            assert D(point['evaluated_J']) == evaluated
    neighbors = sorted({max(D(0), rp - D('.001')), min(D(8), rp + D('.001'))} - {rp})
    assert [D(n['p']) for n in row['neighborhood']] == neighbors
    assert len(buckets['neighborhood']) == len(neighbors)
    for node, point in zip(row['neighborhood'], buckets['neighborhood']):
        assert D(node['p']) == D(point['p']) and D(node['J']) == D(point['reference_J'])
        numeric_equal(node['signed_gap'], D(node['J']) - jr)
    assert set(buckets) == {'shared_mesh', 'neighborhood'} | set(expected_points)
    span = max(map(D, reference['mesh_J'])) - min(map(D, reference['mesh_J']))
    scale = max(D(1), span)
    search_tol, original_tol, parameter_tol = D('1e-18') * scale, D('1e-12') * scale, D('1e-6')
    sg, og, pd, od = jp - jr, jo - jr if jo is not None else None, pp - rp, op - rp if op is not None else None
    expected_values = dict(primary_p=pp, reference_p=rp, original_p_exact=op,
        J_primary_110=jp, J_reference_110=jr, J_original_110=jo,
        search_signed_gap=sg, original_signed_gap=og, search_parameter_delta=pd, original_parameter_delta=od,
        reference_mesh_span=span, search_objective_tolerance=search_tol,
        original_objective_tolerance=original_tol, parameter_tolerance=parameter_tol)
    assert set(values) == set(expected_values)
    for key, value in expected_values.items():
        numeric_equal(values[key], value)
    expected.update(precision_converged=all(c['passed'] for c in checks),
        search_objective_agreement=abs(sg) <= search_tol, parameter_agreement=abs(pd) <= parameter_tol,
        original_objective_agreement=abs(og) <= original_tol if og is not None else None,
        original_parameter_agreement=abs(od) <= parameter_tol if od is not None else None,
        original_better_than_search=og < -original_tol if og is not None else None,
        weak_neighborhood=all(abs(D(n['signed_gap'])) <= original_tol for n in row['neighborhood']))
    if not expected['precision_converged']:
        reasons.append('precision_not_converged')
    if not expected['search_objective_agreement']:
        reasons.append('search_objective_disagreement')
    if not primary['all_brackets_converged']:
        reasons.append('primary_bracket_not_converged')
    if not reference['all_brackets_converged']:
        reasons.append('reference_bracket_not_converged')
    if expected['original_better_than_search']:
        reasons.append('original_better_than_search')
    if any(D(n['signed_gap']) < -search_tol for n in row['neighborhood']):
        reasons.append('lower_neighbor')
    expected.update(unresolved=bool(reasons), reasons=reasons)
    assert row['classification'] == expected
    assert row['status'] == ('unresolved' if reasons else 'compared')
    assert row['arithmetic_summary']['points'] == len(checks)
    numeric_equal(row['arithmetic_summary']['maximum_normalized_discrepancy'],
                  max(abs(D(c['signed_gap'])) / D(c['tolerance']) for c in checks))


def inspect_summary(actual, rows):
    assert actual['total'] == len(rows)
    assert actual['unique_inputs'] == len({r['source_id'] for r in rows})
    assert actual['status_counts'] == {s: sum(r['status'] == s for r in rows) for s in STATUSES}
    assert actual['original_defined'] == sum(r['planned_metadata']['original_p'] is not None for r in rows)
    assert actual['original_undefined_reasons'] == counts(r['planned_metadata']['original_reason'] for r in rows if r['planned_metadata']['original_p'] is None)
    for target, field, nested in [('expected_guard_reasons', 'expected_guard', True),
                                  ('primary_guard_reasons', 'primary_reason', False),
                                  ('reference_guard_reasons', 'reference_reason', False)]:
        values = [(r['planned_metadata'] if nested else r).get(field) for r in rows]
        assert actual[target] == counts(v for v in values if v is not None)
    assert actual['unresolved_reasons'] == counts(v for r in rows for v in r['classification']['reasons'])
    for flag in FLAGS:
        values = [r['classification'][flag] for r in rows]
        available, yes, no = sum(v is not None for v in values), sum(v is True for v in values), sum(v is False for v in values)
        assert actual['classification'][flag] == dict(total=len(rows), available=available, unavailable=len(rows) - available,
            true=yes, false=no, conditional_true_rate=yes / available if available else None,
            unconditional_true_rate=yes / len(rows) if rows and available == len(rows) else None)
    for field in VALUES:
        values = [(r.get('values') or {}).get(field) for r in rows]
        check_stats(actual['values'][field], values)
        if field.endswith('_signed_gap'):
            for sign, predicate in [('negative', lambda x: x < 0), ('zero', lambda x: x == 0), ('positive', lambda x: x > 0)]:
                assert actual['values'][field][sign] == sum(predicate(D(v)) for v in values if v is not None)
    for field in ['primary_p', 'reference_p', 'original_p_exact']:
        values = [D((r.get('values') or {})[field]) for r in rows if (r.get('values') or {}).get(field) is not None]
        assert actual[field + '_boundary'] == dict(available=len(values), exact_zero=values.count(D(0)), exact_eight=values.count(D(8)),
            within_1e_6_lower=sum(0 <= v <= D('1e-6') for v in values),
            within_1e_6_upper=sum(D(8) - D('1e-6') <= v <= 8 for v in values))
    assert actual['global_optimality_certified'] is False


def verify(args):
    started = time.perf_counter()
    raw = ROOT / 'work/runs' / args.run_id
    out = args.report_dir or HERE / f'results-{args.run_id}'
    destination = args.output or HERE / f'FINAL_REVIEW-{args.run_id}.json'
    visual_path = args.visual_review or HERE / f'VISUAL_REVIEW-{args.run_id}.json'
    assert not destination.exists(), 'Preserve previous final reviews'
    freeze, start, end, audit = [read(raw / name) for name in ['FREEZE.json', 'START.json', 'END.json', 'AUDIT.json']]
    assert freeze['status'] == 'PASS' and freeze['new_objective_profiles_computed'] is False
    assert end['status'] in ['COMPLETE', 'BUDGET_EXHAUSTED', 'FAILED']
    assert audit['status'] == ('PASS' if end['status'] == 'COMPLETE' else 'PARTIAL') and not audit['storage_errors']
    assert datetime.fromisoformat(freeze['utc']) < datetime.fromisoformat(start['utc']) <= datetime.fromisoformat(end['utc'])
    assert start['shared_budget_seconds'] == end['shared_budget_seconds'] == 3600
    source = read(raw / 'source_manifest.json')
    assert len(source) == 13 and source == freeze['source_sha256'] == audit['source_sha256']
    for name, digest in source.items():
        assert sha(HERE / name) == sha(raw / 'source' / name) == sha(out / name) == digest, name
    for name, key in [('config.json', 'config_sha256'), ('input_manifest.json', 'input_manifest_sha256'),
                      ('historical_manifest.json', 'historical_manifest_sha256'), ('CHECKS.json', 'checks_sha256'),
                      ('ANALYSIS_CHECKS.json', 'analysis_checks_sha256'), ('DESIGN_REVIEW.json', 'design_review_sha256')]:
        assert sha(raw / name) == freeze[key], name
    for name in ['CHECKS.json', 'ANALYSIS_CHECKS.json', 'DESIGN_REVIEW.json']:
        check = read(raw / name)
        assert check['status'] == 'PASS'
        assert all(source[k] == v for k, v in check['source_sha256'].items())
    assert read(raw / 'CHECKS.json')['source_sha256'] == read(raw / 'DESIGN_REVIEW.json')['source_sha256'] == source
    inputs = read(raw / 'input_manifest.json')
    for name, digest in inputs.items():
        assert sha(raw / name) == digest, name
    origin = read(raw / 'inputs/origin_manifest.json')
    for name, digest in origin.items():
        assert sha(ROOT / name) == sha(raw / 'inputs/source-files' / name) == digest, name
    for name, binding in read(raw / 'inputs/PARENT_BINDINGS.json').items():
        assert sha(raw / name) == sha(ROOT / binding['source']) == binding['sha256'], name
    history = read(raw / 'historical_manifest.json')
    for name, digest in history.items():
        assert sha(ROOT / name) == digest, name
    case_manifest = read(raw / 'case_manifest.json')
    assert sha(raw / 'case_manifest.json') == audit['case_manifest_sha256']
    assert set(case_manifest) == {p.relative_to(raw).as_posix() for directory in ['primary', 'reference', 'comparison'] for p in (raw / directory).glob('*.json')}
    for name, digest in case_manifest.items():
        assert sha(raw / name) == digest, name
    assert sha(raw / 'results.jsonl') == end['results_sha256'] == audit['results_sha256']
    planned, refs = read(raw / 'inputs/profiles.json'), read(raw / 'inputs/references.json')
    observed, metrics, aliases = lines(raw / 'results.jsonl'), lines(out / 'input-metrics.jsonl'), lines(out / 'policy-reference-metrics.jsonl')
    assert len(planned) == len(metrics) == 186 and len(refs) == len(aliases) == 324
    assert len({r['weightgroup'] for r in planned}) == 9 and all(r['n'] == 512 for r in planned)
    planned_map, observed_map = {p['source_id']: p for p in planned}, {r['source_id']: r for r in observed}
    assert len(planned_map) == 186 and len(observed_map) == len(observed)
    assert set(observed_map) <= set(planned_map)
    assert end['completed_source_ids'] == [r['source_id'] for r in observed]
    assert end['remaining_source_ids'] == [p['source_id'] for p in planned if p['source_id'] not in observed_map]
    assert end['completed_cases'] == audit['completed_cases'] == len(observed)
    assert end['planned_cases'] == audit['planned_cases'] == 186
    if end['status'] == 'COMPLETE':
        assert len(observed) == 186 and max(end['elapsed_seconds'], end['utc_elapsed_seconds']) <= 3600
    method_records = {}
    for folder, denominator, primary_flag in [('primary', 64, True), ('reference', 128, False)]:
        method_records[folder] = {}
        for path in sorted((raw / folder).glob('*.json')):
            assert path.stem in planned_map
            record = read(path)
            inspect_search(record, denominator, primary_flag)
            method_records[folder][path.stem] = record
    count_points = 0
    for sid, row in observed_map.items():
        primary, reference = method_records['primary'][sid], method_records['reference'][sid]
        comparison = read(raw / 'comparison' / f'{sid}.json')
        inspect_comparison(planned_map[sid], primary, reference, comparison)
        assert row == {k: v for k, v in comparison.items() if k != 'point_checks'}
        count_points += len(comparison['point_checks'])
    assert audit['precision_checks'] == count_points
    assert audit['status_counts'] == counts(r['status'] for r in observed)
    assert audit['unresolved_source_ids'] == [r['source_id'] for r in observed if r['classification']['unresolved']]
    assert audit['shared_numerical_budget_enforced'] is True and audit['global_optimality_certified'] is False
    assert [r['source_id'] for r in metrics] == [p['source_id'] for p in planned]
    for row, metadata in zip(metrics, planned):
        sid = row['source_id']
        assert row['planned_metadata'] == metadata and row['global_optimality_certified'] is False
        base = {k: v for k, v in row.items() if k not in ['planned_metadata', 'global_optimality_certified']}
        if sid in observed_map:
            assert base == observed_map[sid]
        else:
            flags = dict({flag: None for flag in FLAGS}, unresolved=True, reasons=['not_run_after_' + end['status']])
            expected = dict(metadata, status='not_run', primary_reason=None, reference_reason=None,
                            classification=flags, values=None, neighborhood=[], elapsed_seconds=None)
            assert base == expected
    old_context = {r['reference_id']: r for r in lines(raw / 'inputs/stage9_policy_context.jsonl')}
    by_source, ref_map = {r['source_id']: r for r in metrics}, {r['reference_id']: r for r in refs}
    assert len(old_context) == len(ref_map) == 324 and {r['reference_id'] for r in aliases} == set(ref_map)
    for row in aliases:
        ref = ref_map[row['reference_id']]
        old = old_context[row['reference_id']]
        assert old['policy_reference'] == ref and old['source_id'] == row['source_id']
        expected = dict(by_source[row['source_id']], reference_id=ref['reference_id'], native_id=ref['native_id'],
                        cohort=ref['cohort'], variant=ref['variant'], width=ref['width'],
                        policy_reference=ref, context=old['context'])
        assert row == expected
    assert len({r['native_id'] for r in aliases}) == 207
    assert sum(r['context']['test_loss'] is not None for r in aliases) == 324
    assert sum(r['context']['test_initial_loss'] is None for r in aliases) == 54
    assert sum(r['context']['test_loss_gain'] is None for r in aliases) == 54
    assert {r['cohort'] for r in aliases if r['context']['test_initial_loss'] is None} == {'S4_fixed30'}
    summaries = read(out / 'summaries.json')
    inspect_summary(summaries['unique_inputs'], metrics)
    inspect_summary(summaries['policy_references'], aliases)
    groups = defaultdict(list)
    for row in aliases:
        groups[row['cohort'], row['variant'], row['width']].append(row)
    assert set(groups) == {(c, v, w) for c in COHORTS for v in ['M', 'U'] for w in [64, 128, 256]}
    assert len(summaries['cells']) == 36
    for cell in summaries['cells']:
        key = tuple(cell['condition'][f] for f in ['cohort', 'variant', 'width'])
        rows = groups[key]
        assert len(rows) == 9 and len({r['policy_reference']['data_seed'] for r in rows}) == 3
        assert len({(r['policy_reference']['data_seed'], r['policy_reference']['seed']) for r in rows}) == 9
        inspect_summary(cell, rows)
        assert cell['native_checkpoints'] == len({r['native_id'] for r in rows})
        assert cell['reference_ids'] == [r['reference_id'] for r in rows]
        assert cell['source_ids'] == [r['source_id'] for r in rows]
        for field, stat in cell['historical_context'].items():
            check_stats(stat, [r['context'].get(field) for r in rows])
    assert summaries['global_optimality_certified'] is False
    summary_audit = read(out / 'SUMMARY_AUDIT.json')
    assert summary_audit['status'] == 'PASS' and summary_audit['observed_rows'] == len(observed)
    assert summary_audit['unavailable_initial_test'] == 54 and summary_audit['test_gain_available'] == 270
    provenance = read(out / 'analysis-provenance.json')
    assert provenance['source_sha256'] == source and provenance['results_sha256'] == end['results_sha256']
    assert provenance['stage9_policy_context_sha256'] == sha(raw / 'inputs/stage9_policy_context.jsonl')
    assert provenance['END_sha256'] == sha(raw / 'END.json') and provenance['AUDIT_sha256'] == sha(raw / 'AUDIT.json')
    plot = read(out / 'PLOT_CHECKS.json')
    assert plot['status'] == 'PASS' and plot['all_available_points_shown'] is True
    for field in ['search_signed_gap', 'original_signed_gap', 'search_parameter_delta', 'original_parameter_delta']:
        available = [(i, row, (row.get('values') or {}).get(field)) for i, row in enumerate(metrics) if (row.get('values') or {}).get(field) is not None]
        evidence = plot['data_limits'][field]
        assert evidence['points'] == len(available) and evidence['unavailable'] == 186 - len(available)
        assert evidence['plotted_source_ids'] == [row['source_id'] for _, row, _ in available]
        assert all(evidence['xlim'][0] <= i <= evidence['xlim'][1] and evidence['ylim'][0] <= float(D(v)) <= evidence['ylim'][1] for i, _, v in available)
    visual = read(visual_path)
    assert visual['status'] == 'PASS'
    image_names = {'objective-gaps.png', 'parameter-differences.png', 'cohort-coverage.png'}
    assert set(visual['images']) == image_names
    for name in image_names:
        assert visual['images'][name]['sha256'] == sha(out / name)
    raw_manifest = read(out / 'raw-manifest.json')
    assert set(raw_manifest) == {p.relative_to(raw).as_posix() for p in raw.rglob('*') if p.is_file()}
    for name, digest in raw_manifest.items():
        assert sha(raw / name) == digest, name
    archive, archive_check = out / 'run-records.zip', read(out / 'ARCHIVE_CHECK.json')
    assert archive_check['status'] == archive_check['crc'] == 'PASS'
    assert sha(archive) == archive_check['sha256'] and archive.stat().st_size == archive_check['bytes']
    report_files = {p.name: p for p in out.iterdir() if p.is_file() and p.name not in ['run-records.zip', 'ARCHIVE_CHECK.json']}
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        expected_members = {'raw/' + name for name in raw_manifest} | {'report/' + name for name in report_files}
        assert set(bundle.namelist()) == expected_members and len(bundle.namelist()) == len(expected_members)
        for name, digest in raw_manifest.items():
            assert hashlib.sha256(bundle.read('raw/' + name)).hexdigest() == digest, name
        for name, path in report_files.items():
            assert hashlib.sha256(bundle.read('report/' + name)).hexdigest() == sha(path), name
    result = dict(status='PASS', utc=datetime.now(timezone.utc).isoformat(), run_id=args.run_id,
        verifier_sha256=sha(Path(__file__)), source_sha256=source, frozen_source_files=len(source),
        input_files_verified=len(inputs), source_origin_files_verified=len(origin), historical_files_verified=len(history),
        historical_coverage=freeze['historical_coverage'], case_files_verified=len(case_manifest), raw_files_verified=len(raw_manifest),
        report_files_verified=len(report_files), archive_sha256=archive_check['sha256'], archive_crc='PASS', archive_bytes=archive_check['bytes'],
        planned_inputs=186, completed_inputs=len(observed), native_checkpoints=207, policy_references=324,
        cells=36, references_per_cell=9, saved_point_checks_verified=count_points,
        independently_replayed_saved_brackets=True, independently_recomputed_saved_classifications=True,
        independently_recomputed_report_summaries=True, original_estimates_and_context_preserved=True,
        initial_test_missing=54, selected_test_available=324, test_gain_available=270,
        unique_status_counts=summaries['unique_inputs']['status_counts'],
        unique_classification=summaries['unique_inputs']['classification'],
        policy_classification=summaries['policy_references']['classification'],
        end_status=end['status'], numerical_elapsed_seconds=end['elapsed_seconds'],
        visual_review_sha256=sha(visual_path), visual_review=visual,
        global_optimality_certified=False, no_objectives_fits_or_models_evaluated=True,
        limitations=['Final verification uses saved numerical values; it performs no objective evaluations or new searches.',
                     'Finite subdivision agreement does not certify global optimality, recovery, identifiability or utility.',
                     'Reused policy aliases and shared model seeds are not independent corpus replications.',
                     'Historical coverage excludes a fresh hash pass of all model binaries.'],
        elapsed_seconds=time.perf_counter() - started)
    write(destination, result)
    print(json.dumps(dict(status='PASS', review=str(destination), completed=len(observed), references=324, archive=archive_check['sha256'])), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--report-dir', type=Path)
    parser.add_argument('--visual-review', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    assert args.run_id.startswith('search-v011-') and '/' not in args.run_id and '\\' not in args.run_id
    with localcontext() as context:
        context.prec = 110
        verify(args)


if __name__ == '__main__':
    main()
