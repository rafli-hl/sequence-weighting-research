"""Post-analysis independent verification of saved Stage9 evidence.

This file is not an experiment source. It imports no Stage9 calculation module,
fits no model and evaluates no objective. It checks saved numbers and artifacts.
Run only after the completed analysis has been authorized for final inspection.
"""
import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
import time
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
METHODS = ['legacy_J', 'naive_D64', 'stable_D64']
SOURCES = ['core.py', 'precision_math.py', 'reference_math.py', 'metrics.py',
    'inputs_stage4.py', 'inputs_stage56.py', 'common_stage9.py', 'stage9.py',
    'audit_stage9.py', 'analyze_stage9.py', 'check_stage9.py', 'analysis_checks.py',
    'PROTOCOL_STAGE9.md', 'README.md', 'DERIVATION.json']
COHORTS = ['S4_fixed30', 'S5_R', 'S6_P1_R', 'S6_P2_R', 'S6_P3_R', 'S6_P4_R']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def lines(path):
    return [json.loads(v) for v in Path(path).read_text(encoding='utf-8').splitlines() if v.strip()]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda: f.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def count(values):
    return dict(Counter(values))


def stamp(value):
    return datetime.fromisoformat(value)


def repair_function_identity():
    """The repair may only change context availability and report plumbing."""
    originals = ast.parse((HERE/'analyze_stage9.py').read_text(encoding='utf-8'))
    repaired = ast.parse((HERE/'analyze_stage9_r1.py').read_text(encoding='utf-8'))
    old = {node.name:node for node in originals.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    new = {node.name:node for node in repaired.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    changed_allowed = {'context', 'figures', 'report', 'main'}
    unchanged = sorted(set(old)-changed_allowed)
    assert set(old) <= set(new)
    for name in unchanged:
        assert ast.dump(old[name], include_attributes=False) == ast.dump(new[name], include_attributes=False), name
    assert {'summarize_profiles', 'signed_context', 'join_references', 'summarize_references'} <= set(unchanged)
    for mod in ['metrics', 'common_stage9']:
        imports_old = [ast.dump(node, include_attributes=False) for node in originals.body
            if isinstance(node, ast.ImportFrom) and node.module == mod]
        imports_new = [ast.dump(node, include_attributes=False) for node in repaired.body
            if isinstance(node, ast.ImportFrom) and node.module == mod]
        assert imports_old == imports_new, mod
    return unchanged


def verify_repair(raw, out, analysis, source):
    repair = read(out/'ANALYSIS_REPAIR.json')
    check_subset(repair, dict(status='PASS', revision='r1', selected_test_metrics_retained=324,
        test_gain_available=270, missing_initial_test_references=54, raw_profiles_unchanged=True,
        frozen_source_preserved=True, original_failure_preserved=True), 'repair')
    original_dir = HERE / ('results-' + raw.name)
    assert {p.name for p in original_dir.iterdir()} == {'ANALYSIS_FAILURE.json'}
    failure_path = original_dir/'ANALYSIS_FAILURE.json'
    assert repair['original_failure_path'] == failure_path.relative_to(ROOT).as_posix()
    assert digest(failure_path) == digest(out/'ORIGINAL_ANALYSIS_FAILURE.json') == repair['original_failure_sha256']
    failure = read(failure_path)
    assert failure['status'] == 'FAILED' and 'NoneType' in failure['error']
    assert repair['original_analysis_sha256'] == source['analyze_stage9.py']
    assert repair['profiles_sha256'] == analysis['profiles_sha256'] == digest(raw/'profiles.jsonl')
    repairs = repair['repair_source_sha256']
    assert set(repairs) == {'analyze_stage9_r1.py', 'analysis_checks_r1.py', 'ANALYSIS_REPAIR_R1.md'}
    assert analysis['repair_source_sha256'] == repairs and analysis['analysis_revision'] == 'r1'
    for name, expected in repairs.items():
        assert digest(HERE/name) == digest(out/name) == expected, name
    assert repair['fixtures_path'] == 'work/stage9-analysis-repair-checks-20260930-01.json'
    fixture_path = ROOT/repair['fixtures_path']
    assert digest(fixture_path) == digest(out/'ANALYSIS_REPAIR_CHECKS.json') == repair['fixtures_sha256'] == analysis['repair_fixture_sha256']
    fixtures = read(fixture_path)
    assert fixtures['status'] == 'PASS' and fixtures['measured_outcomes_read'] is False
    assert set(fixtures['source_sha256']) == set(repairs) | {'metrics.py', 'common_stage9.py'}
    for name, expected in fixtures['source_sha256'].items():
        assert digest(HERE/name) == expected, name
    review_path = ROOT/'work/stage9-analysis-repair-review-20260930-01.json'
    review = read(review_path)
    check_subset(review, dict(status='PASS', original_source_sha256=source, repair_source_sha256=repairs,
        fixture_evidence_file=repair['fixtures_path'], fixture_evidence_sha256=repair['fixtures_sha256'],
        original_failure_file=repair['original_failure_path'], original_failure_sha256=repair['original_failure_sha256'],
        numerical_source_unchanged=True, context_references_verified=324,
        initial_test_missing_by_stage={'4':54,'5':0,'6':0}, selected_test_missing_by_stage={'4':0,'5':0,'6':0},
        analysis_output_existed_before_review=False, objective_or_fit_calls=False), 'pre-run repair review')
    assert digest(ROOT/'work/review_stage9_analysis_r1.py') == review['reviewer_source_sha256']
    unchanged = repair_function_identity()
    assert review['unchanged_function_names'] == unchanged
    assert stamp(failure['utc']) < stamp(fixtures['utc']) <= stamp(review['utc']) <= stamp(repair['utc']) <= stamp(analysis['utc'])
    return dict(status='PASS', repair_evidence_sha256=digest(out/'ANALYSIS_REPAIR.json'),
        pre_run_review_sha256=digest(review_path), repair_source_sha256=repairs,
        fixtures_sha256=repair['fixtures_sha256'], original_failure_sha256=repair['original_failure_sha256'],
        unchanged_function_names=unchanged)


def verify_presentation(raw, out, analysis):
    record = read(out/'PRESENTATION_R2.json')
    check_subset(record, dict(status='PASS', revision='r2', prior_archive_crc='PASS',
        recomputed_objectives=False, recomputed_numerical_summaries=False,
        modified_plots=['grid-agreement.png','contrast-errors.png','model-context.png']), 'presentation')
    prior = HERE/('results-' + raw.name + '-r1')
    assert record['prior_report'] == prior.relative_to(ROOT).as_posix()
    assert not (out/'PRESENTATION_FAILURE.json').exists() and not (prior/'ANALYSIS_FAILURE.json').exists()
    previous_archive = read(prior/'ARCHIVE_CHECK.json')
    assert previous_archive['status'] == previous_archive['crc'] == 'PASS'
    assert digest(prior/'run-records.zip') == previous_archive['sha256'] == record['prior_archive_sha256']
    assert (prior/'run-records.zip').stat().st_size == previous_archive['bytes'] == record['prior_archive_bytes']
    expected_numeric = {'profile-metrics.jsonl','policy-reference-metrics.jsonl','profile-metrics.csv',
        'policy-reference-metrics.csv','summaries.json','summaries.csv','SUMMARY_AUDIT.json',
        'raw-manifest.json','AUDIT.json','ANALYSIS_REPAIR.json','ANALYSIS_REPAIR_CHECKS.json',
        'ORIGINAL_ANALYSIS_FAILURE.json'}
    assert set(record['preserved_numeric_sha256']) == expected_numeric
    for name, expected in record['preserved_numeric_sha256'].items():
        assert digest(prior/name) == digest(out/name) == expected, name
    excluded = set(record['modified_plots']) | {'run-records.zip','ARCHIVE_CHECK.json','PLOT_CHECKS.json','REPORT.md'}
    copied = []
    for path in prior.iterdir():
        assert path.is_file()
        if path.name not in excluded:
            assert digest(path) == digest(out/path.name), path.name
            copied.append(path.name)
    assert {p.name for p in out.iterdir()} == {p.name for p in prior.iterdir()} | {'finalize_stage9_r2.py','PRESENTATION_R2.json'}
    prior_manifest = read(prior/'raw-manifest.json')
    with zipfile.ZipFile(prior/'run-records.zip') as z:
        assert z.testzip() is None
        names = z.namelist()
        assert len(names) == len(set(names))
        assert {n[4:] for n in names if n.startswith('raw/')} == set(prior_manifest)
        assert {n[7:] for n in names if n.startswith('report/')} == {p.name for p in prior.iterdir()
            if p.is_file() and p.name not in ['ARCHIVE_CHECK.json','run-records.zip']}
        for name in names:
            if name.startswith('raw/'):
                expected = prior_manifest[name[4:]]
            else:
                assert name.startswith('report/')
                expected = digest(prior/name[7:])
            assert hashlib.sha256(z.read(name)).hexdigest() == expected, name
    assert record['profiles_sha256'] == digest(raw/'profiles.jsonl') == analysis['profiles_sha256']
    assert record['parent_figure_source_sha256'] == digest(HERE/'analyze_stage9_r1.py') == digest(out/'analyze_stage9_r1.py')
    assert record['finalizer_sha256'] == digest(HERE/'finalize_stage9_r2.py') == digest(out/'finalize_stage9_r2.py')
    parent_text = (HERE/'analyze_stage9_r1.py').read_text(encoding='utf-8')
    parent_ast = ast.parse(parent_text)
    parent_fig = next(node for node in parent_ast.body if isinstance(node, ast.FunctionDef) and node.name == 'figures')
    figure_text = ''.join(parent_text.splitlines(keepends=True)[parent_fig.lineno-1:parent_fig.end_lineno])
    finalizer_ast = ast.parse((HERE/'finalize_stage9_r2.py').read_text(encoding='utf-8'))
    corrector = next(node for node in finalizer_ast.body if isinstance(node, ast.FunctionDef) and node.name == 'corrected_figure_source')
    fixed = next(node.value.value for node in corrector.body if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == 'fixed' for target in node.targets))
    start, end = figure_text.index('    def scaled('), figure_text.index('\n    fig, axes =')
    derived = figure_text[:start] + fixed + figure_text[end:]
    assert hashlib.sha256(derived.encode('utf-8')).hexdigest() == record['derived_figure_function_sha256']
    derived_ast = ast.parse(derived).body[0]
    def without_scaled(node):
        node.body = [item for item in node.body if not (isinstance(item, ast.FunctionDef) and item.name == 'scaled')]
        return ast.dump(node, include_attributes=False)
    assert without_scaled(parent_fig) == without_scaled(derived_ast)
    original_report = (prior/'REPORT.md').read_text(encoding='utf-8')
    heading, rest = original_report.split('\n\n', 1)
    note = ('Presentation r2 fixes axis-limit expansion in the error and stored-point plots. Every numerical table, model-context value and raw record is byte-identical to r1. The preserved r1 report documents the separate null-handling repair.\n\n')
    assert (out/'REPORT.md').read_text(encoding='utf-8') == heading+'\n\n'+note+rest
    assert stamp(analysis['utc']) <= stamp(previous_archive['utc']) < stamp(record['utc'])
    return dict(status='PASS', presentation_evidence_sha256=digest(out/'PRESENTATION_R2.json'),
        preserved_numeric_files=len(expected_numeric), copied_files_verified=len(copied),
        prior_archive_sha256=previous_archive['sha256'], prior_archive_crc='PASS',
        prior_archive_bytes=previous_archive['bytes'], finalizer_sha256=record['finalizer_sha256'],
        only_nested_axis_helper_changed=True, objectives_or_summaries_recomputed=False)


def check_subset(actual, expected, label):
    for key, value in expected.items():
        assert actual[key] == value, (label, key, actual[key], value)


def stats(values):
    """Independent conditional aggregation, retaining the complete denominator."""
    numbers = [Decimal(v) for v in values if v is not None]
    n = len(numbers)
    average = sum(numbers, Decimal(0)) / n if n else None
    variance = sum(((v - average) ** 2 for v in numbers), Decimal(0)) / (n - 1) if n > 1 else None
    ordered = sorted(numbers)
    median = ordered[(n - 1) // 2] + (ordered[n // 2] - ordered[(n - 1) // 2]) / 2 if n else None
    return dict(total=len(values), defined=n, undefined=len(values) - n,
        conditional_mean=None if average is None else str(average),
        conditional_sd=None if variance is None else str(variance.sqrt()),
        conditional_minimum=str(ordered[0]) if n else None,
        conditional_maximum=str(ordered[-1]) if n else None,
        conditional_median=None if median is None else str(median),
        unconditional_mean=str(average) if n == len(values) and n else None)


def same_stats(actual, expected, label):
    # Decimal equivalent strings are acceptable, while null placement is exact.
    for key, value in expected.items():
        observed = actual[key]
        if isinstance(value, str):
            assert observed is not None and Decimal(observed) == Decimal(value), (label, key)
        else:
            assert observed == value, (label, key, observed, value)


def raw_ranking(row, metric, independent, classification):
    """Recompute ranking/error summaries from saved 80- and 110-digit grids."""
    valid = row['legacy_reason'] is None
    hp_valid = row['hp_reason'] is None
    assert row['hp_dps'] == 80 and independent['hp_dps'] == 110
    assert row['hp_reason'] == independent['hp_reason']
    assert Decimal(row['total_gain_hp']) == Decimal(independent['total_gain_hp'])
    for key in ['original_p', 'original_objective', 'original_reason', 'legacy_reason', 'hp_reason',
                'total_gain_legacy', 'total_gain_fsum', 'total_gain_hp', 'weights_sha256', 'gains_sha256']:
        assert row[key] == metric[key], key
    check_subset(metric, dict(legacy_defined=valid, reference_defined=hp_valid,
        both_defined=valid and hp_valid, domain_mismatch=valid != hp_valid), row['source_id'])
    assert metric['reference_validation'] == classification == independent['classification']
    assert metric['reference_classification_unresolved'] == classification['unresolved']
    for name in METHODS:
        assert (row[name] is not None) == valid
        assert metric['methods'][name]['available'] == valid
    if not hp_valid:
        assert row['hp_J'] is row['hp_D'] is independent['hp_J'] is independent['hp_D'] is None
        assert metric['reference'] is metric['pairwise'] is metric['original_point'] is None
        assert not classification['eligible'] and not classification['unresolved']
        assert row['original_point'] is None
        assert all(metric['methods'][m]['argmin_index'] is None for m in METHODS)
        return
    d = list(map(Decimal, row['hp_D']))
    j = list(map(Decimal, row['hp_J']))
    d110 = list(map(Decimal, independent['hp_D']))
    j110 = list(map(Decimal, independent['hp_J']))
    assert len(d) == len(j) == len(d110) == len(j110) == 161
    assert all(v.is_finite() for v in d + j + d110 + j110)
    scale = max(Decimal(1), *map(abs, d))
    tau = Decimal('2e-50') * scale
    tol_d = Decimal('1e-50') * max(Decimal(1), *map(abs, d110))
    assert all(abs(a-b) <= tol_d for a, b in zip(d, d110))
    assert all(abs(a-b) <= Decimal('1e-50') * max(Decimal(1), abs(b)) for a, b in zip(j, j110))
    assert d[0] == d110[0] == 0
    lo = min(d)
    min_index = d.index(lo)
    exact = [i for i, v in enumerate(d) if v == lo]
    band = [i for i, v in enumerate(d) if v <= lo + tau]
    band110 = [i for i, v in enumerate(d110) if v - min(d110) <= tau]
    reference = metric['reference']
    check_subset(reference, dict(argmin_index=min_index, argmin_p=min_index / 20,
        exact_minimum_indices=exact, exact_minimum_count=len(exact),
        minimum_set_indices=band, minimum_set_size=len(band)), 'reference rank')
    for key, value in dict(minimum_D=lo, contrast_scale=scale, contrast_span=max(d)-lo,
                           top_two_gap=sorted(d)[1]-sorted(d)[0], tau=tau).items():
        assert Decimal(reference[key]) == value, key
    pair = dict(total_pairs=12880, reference_exact_ties=0,
                reference_nonexact_near_ties=0, reference_strict_pairs=0)
    pairs = {name: dict(raw_exact_ties_all_pairs=0, strict_agreements=0,
        strict_reversals=0, float_ties_against_reference_strict=0,
        float_strict_on_reference_nonstrict=0, float_ties_on_reference_nonstrict=0)
        for name in METHODS}
    relation80, relation110 = Counter(), Counter()
    changed, boundary = [], []
    drift = max(abs(a-b) for a, b in zip(d, d110))
    for i in range(161):
        for k in range(i + 1, 161):
            diff = d[i] - d[k]
            diff110 = d110[i] - d110[k]
            strict = abs(diff) > tau
            rel = (1 if diff > 0 else -1) if strict else 0
            rel110 = (1 if diff110 > 0 else -1) if abs(diff110) > tau else 0
            relation80[str(rel)] += 1
            relation110[str(rel110)] += 1
            if rel != rel110:
                changed.append([i, k])
            if abs(abs(diff110)-tau) <= 2*drift:
                boundary.append([i, k])
            pair['reference_strict_pairs' if strict else
                 'reference_exact_ties' if diff == 0 else 'reference_nonexact_near_ties'] += 1
            for name in METHODS:
                if not valid:
                    continue
                a, b = row[name][i], row[name][k]
                cmp = (a > b) - (a < b)
                if not cmp:
                    pairs[name]['raw_exact_ties_all_pairs'] += 1
                if strict:
                    key = 'float_ties_against_reference_strict' if cmp == 0 else (
                        'strict_agreements' if (cmp > 0) == (diff > 0) else 'strict_reversals')
                else:
                    key = 'float_ties_on_reference_nonstrict' if cmp == 0 else 'float_strict_on_reference_nonstrict'
                pairs[name][key] += 1
    assert metric['pairwise'] == pair
    assert reference['raw_exact_ties_all_pairs'] == pair['reference_exact_ties']
    near_min = [i for i, v in enumerate(d110) if abs((v-min(d110))-tau) <= 2*drift]
    unresolved = bool(min_index != d110.index(min(d110)) or band != band110 or changed or boundary or near_min)
    check_subset(classification, dict(eligible=True, unresolved=unresolved,
        strict_minimum_index_80=min_index, strict_minimum_index_110=d110.index(min(d110)),
        strict_argmin_agreement=min_index == d110.index(min(d110)),
        minimizer_indices_80=band, minimizer_indices_110=band110, minimizer_set_agreement=band == band110,
        changed_pairs=changed, changed_pair_count=len(changed), pair_count=12880,
        pairwise_relation_counts_80=dict(relation80), pairwise_relation_counts_110=dict(relation110),
        near_tau_boundary_pairs=boundary, near_tau_boundary_pair_count=len(boundary),
        near_tau_boundary_minimizer_indices=near_min), 'independent classification')
    for name in METHODS:
        if not valid:
            continue
        values = row[name]
        assert len(values) == 161 and all(math.isfinite(v) for v in values)
        indexes = [i for i, v in enumerate(values) if v == min(values)]
        chosen = indexes[0]
        m = metric['methods'][name]
        check_subset(m, dict(argmin_index=chosen, argmin_p=chosen/20,
            exact_minimum_indices=indexes, exact_minimum_count=len(indexes),
            exact_argmin_agreement=chosen == min_index, reference_minset_agreement=chosen in band,
            raw_exact_ties_all_pairs=pairs[name]['raw_exact_ties_all_pairs'], pairwise=pairs[name]), name)
        regret = d[chosen] - lo
        assert Decimal(m['reference_regret']) == regret
        assert Decimal(m['reference_regret_excess_over_tau']) == max(Decimal(0), regret-tau)
        targets = j if name == 'legacy_J' else d
        error = max(abs(Decimal.from_float(v)-t) for v, t in zip(values, targets))
        assert Decimal(m['error']['max_abs_error']) == error
        assert Decimal(m['error']['relative_to_contrast_scale']) == error / scale
        assert (None if m['error']['relative_to_contrast_span'] is None else Decimal(m['error']['relative_to_contrast_span'])) == (error/(max(d)-lo) if max(d)>lo else None)
    original = row['original_point']
    assert (original is None) == (independent['original_point'] is None)
    if original is not None:
        other = independent['original_point']
        assert original['p'] == row['original_p'] == other['p'] == metric['original_point']['p']
        assert original['legacy_J'] == row['original_objective']
        assert abs(Decimal(original['hp_D'])-Decimal(other['hp_D'])) <= tol_d
        assert abs(Decimal(original['hp_J'])-Decimal(other['hp_J'])) <= Decimal('1e-50') * max(Decimal(1), abs(Decimal(other['hp_J'])))
        assert Decimal(metric['original_point']['signed_HP_gap_vs_grid_min']) == Decimal(original['hp_D'])-lo


def aggregate_check(summary, rows, label):
    available = [r for r in rows if r['reference_defined']]
    comparable = [r for r in rows if r['both_defined']]
    expected = dict(total=len(rows), unique_inputs=len({r['source_id'] for r in rows}),
        legacy_defined=sum(r['legacy_defined'] for r in rows), reference_defined=len(available),
        both_defined=len(comparable), domain_mismatches=sum(r['domain_mismatch'] for r in rows),
        legacy_undefined_reasons=count(r['legacy_reason'] for r in rows if not r['legacy_defined']),
        hp_undefined_reasons=count(r['hp_reason'] for r in rows if not r['reference_defined']),
        reference_classification_unresolved=sum(r['reference_classification_unresolved'] for r in rows),
        reference_argmin_frequencies=count(str(r['reference']['argmin_index']) for r in available),
        reference_exact_minimum_tie_profiles=sum(r['reference']['exact_minimum_count'] > 1 for r in available),
        reference_band_minimum_tie_profiles=sum(r['reference']['minimum_set_size'] > 1 for r in available),
        reference_exact_pair_ties=sum(r['pairwise']['reference_exact_ties'] for r in available),
        reference_nonexact_near_pair_ties=sum(r['pairwise']['reference_nonexact_near_ties'] for r in available),
        reference_strict_pairs=sum(r['pairwise']['reference_strict_pairs'] for r in available))
    check_subset(summary, expected, label)
    for key in ['contrast_scale', 'contrast_span', 'top_two_gap', 'tau']:
        same_stats(summary['reference_' + key], stats([r['reference'][key] if r['reference'] else None for r in rows]), key)
    gaps = [r['original_point']['signed_HP_gap_vs_grid_min'] if r['original_point'] else None for r in rows]
    same_stats(summary['original_point_signed_gap'], stats(gaps), 'signed gaps')
    assert summary['original_point_below_grid_count'] == sum(Decimal(v) < 0 for v in gaps if v is not None)
    assert summary['original_point_equal_grid_count'] == sum(Decimal(v) == 0 for v in gaps if v is not None)
    for name in METHODS:
        ms = [r['methods'][name] for r in rows if r['methods'][name]['available']]
        cs = [r['methods'][name] for r in comparable]
        exact = sum(m['exact_argmin_agreement'] for m in cs)
        band = sum(m['reference_minset_agreement'] for m in cs)
        target = summary['methods'][name]
        check_subset(target, dict(available=len(ms), comparable=len(cs),
            argmin_frequencies=count(str(m['argmin_index']) for m in ms),
            exact_minimum_tie_profiles=sum(m['exact_minimum_count'] > 1 for m in ms),
            raw_exact_ties_all_pairs_available=sum(m['raw_exact_ties_all_pairs'] for m in ms),
            exact_argmin_agreements=exact, reference_minset_agreements=band,
            exact_argmin_agreement_rate_conditional=exact/len(cs) if cs else None,
            reference_minset_agreement_rate_conditional=band/len(cs) if cs else None,
            any_strict_reversal_profiles=sum(m['pairwise']['strict_reversals'] > 0 for m in cs),
            any_float_tie_on_reference_strict_profiles=sum(m['pairwise']['float_ties_against_reference_strict'] > 0 for m in cs)), label + name)
        den = sum(r['pairwise']['reference_strict_pairs'] for r in comparable)
        pair_fields = ['raw_exact_ties_all_pairs', 'strict_agreements', 'strict_reversals',
            'float_ties_against_reference_strict', 'float_strict_on_reference_nonstrict', 'float_ties_on_reference_nonstrict']
        totals = {key: sum(m['pairwise'][key] for m in cs) for key in pair_fields}
        totals.update(reference_strict_denominator=den, possible_pairs=12880*len(cs),
            float_tie_rate_on_reference_strict=totals['float_ties_against_reference_strict']/den if den else None,
            strict_reversal_rate=totals['strict_reversals']/den if den else None)
        assert target['pairwise'] == totals
        for key in ['reference_regret', 'reference_regret_excess_over_tau']:
            same_stats(target[key], stats([r['methods'][name][key] for r in rows]), name + key)
        for key in ['max_abs_error', 'relative_to_contrast_scale', 'relative_to_contrast_span']:
            same_stats(target['error'][key], stats([r['methods'][name]['error'][key] if r['methods'][name]['error'] else None for r in rows]), name + key)


def check_all(run_id, visual_path):
    import numpy as np
    import torch
    raw = ROOT / 'work/runs' / run_id
    out = HERE / ('results-' + run_id + '-r2')
    complete, audit = read(raw/'COMPLETE.json'), read(raw/'AUDIT.json')
    assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
    assert not any((raw/n).exists() for n in ['FAILURE.json', 'AUDIT_FAILURE.json'])
    assert not (out/'ANALYSIS_FAILURE.json').exists()
    freeze, start, source = read(raw/'FREEZE.json'), read(raw/'START.json'), read(raw/'source_manifest.json')
    assert set(source) == set(SOURCES) and freeze['source_sha256'] == audit['source_sha256'] == source
    assert freeze['new_objective_profiles_computed'] is False
    for name, expected in source.items():
        assert digest(HERE/name) == digest(raw/'source'/name) == digest(out/name) == expected, name
    for filename, key in [('config.json', 'config_sha256'), ('input_manifest.json', 'input_manifest_sha256'),
            ('INVENTORY.json', 'inventory_sha256'), ('historical_manifest.json', 'historical_manifest_sha256'),
            ('CHECKS.json', 'checks_sha256'), ('ANALYSIS_CHECKS.json', 'analysis_checks_sha256'), ('DESIGN_REVIEW.json', 'design_review_sha256')]:
        assert digest(raw/filename) == freeze[key], filename
    for name in ['CHECKS.json', 'ANALYSIS_CHECKS.json', 'DESIGN_REVIEW.json']:
        evidence = read(raw/name)
        assert evidence['status'] == 'PASS'
        for filename, expected in evidence['source_sha256'].items():
            assert source[filename] == expected
        if 'utc' in evidence:
            assert stamp(evidence['utc']) <= stamp(freeze['utc']), name
    analysis = read(out/'analysis-provenance.json')
    assert stamp(freeze['utc']) < stamp(start['utc']) < stamp(complete['utc']) <= stamp(audit['utc']) <= stamp(analysis['utc'])
    assert analysis['source_sha256'] == source
    repair_review = verify_repair(raw, out, analysis, source)
    presentation_review = verify_presentation(raw, out, analysis)
    assert complete['training'] is audit['training'] is False
    assert complete['original_estimates_modified'] is audit['original_estimates_modified'] is False
    assert complete['failed_cases'] == audit['failed_cases'] == []
    assert max(complete['elapsed_seconds'], complete['utc_elapsed_seconds'], audit['elapsed_seconds'], audit['utc_elapsed_seconds']) <= 3600
    runtime = read(raw/'runtime.json')
    assert max(runtime['preparation_elapsed_seconds'], runtime['preparation_utc_elapsed_seconds']) <= 1800
    assert runtime['source_snapshot_bytes'] <= 1024**3 and runtime['free_disk_bytes'] >= 2*1024**3
    config = read(raw/'config.json')
    check_subset(config, dict(cases=186, policy_references=324, native_checkpoints=207,
        grid=[i/20 for i in range(161)], primary_precision=80, audit_precision=110,
        training=False, gpu=False, adaptive_precision=False, adaptive_grid=False), 'configuration')
    input_manifest = read(raw/'input_manifest.json')
    for name, expected in input_manifest.items():
        assert digest(raw/name) == expected, name
    assert set(input_manifest) == {p.relative_to(raw).as_posix() for p in (raw/'inputs').rglob('*') if p.is_file()}
    origin = read(raw/'inputs/origin_manifest.json')
    for name, expected in origin.items():
        assert digest(ROOT/name) == digest(raw/'inputs/source-files'/name) == expected, name
    old_design = [(4, 'baseline-v05-20260929-01', 'results-baseline-v05-20260929-01-r2'),
                  (5, 'utility-v06-20260929-01', 'results-utility-v06-20260929-01-r1'),
                  (6, 'stability-v07-20260929-01', 'results-stability-v07-20260929-01')]
    old_raw_bindings = 0
    for stage, old_run, report in old_design:
        old_manifest = read(raw/'inputs/source-files'/f'outputs/sequence-weighting-stage{stage}'/report/'raw-manifest.json')
        prefix = f'work/runs/{old_run}/'
        for name, expected in origin.items():
            if name.startswith(prefix):
                assert old_manifest[name[len(prefix):]] == expected, name
                old_raw_bindings += 1
    historical = read(raw/'historical_manifest.json')
    for name, expected in historical.items():
        assert digest(ROOT/name) == expected, name
    assert digest(raw/'profiles.jsonl') == complete['profiles_sha256'] == audit['profiles_sha256'] == analysis['profiles_sha256']
    profiles, refs = read(raw/'inputs/profiles.json'), read(raw/'inputs/references.json')
    rows = lines(raw/'profiles.jsonl')
    metrics = lines(out/'profile-metrics.jsonl')
    aliases = lines(out/'policy-reference-metrics.jsonl')
    assert len(rows) == len(profiles) == len(metrics) == 186
    assert len(refs) == len(aliases) == len({r['reference_id'] for r in refs}) == 324
    assert len({r['native_id'] for r in refs}) == 207
    assert len({r['weightgroup'] for r in refs}) == 9
    assert count(r['cohort'] for r in refs) == {c:54 for c in COHORTS}
    input_map = {r['source_id']:r for r in profiles}
    row_map = {r['source_id']:r for r in rows}
    metric_map = {r['source_id']:r for r in metrics}
    alias_map = {r['reference_id']:r for r in aliases}
    assert set(input_map) == set(row_map) == set(metric_map) and len(input_map) == 186
    cases = read(raw/'case_manifest.json')
    audcases = read(raw/'audit_profile_manifest.json')
    assert digest(raw/'audit_profile_manifest.json') == audit['audit_profile_manifest_sha256'] == analysis['audit_profile_manifest_sha256']
    classified = read(raw/'REFERENCE_CLASSIFICATION.json')
    assert digest(raw/'REFERENCE_CLASSIFICATION.json') == audit['classification_evidence_sha256'] == analysis['classification_evidence_sha256']
    classifications = {v['source_id']:v for v in classified['cases']}
    assert set(classifications) == set(input_map)
    for prefix, manifest in [('cases', cases), ('audit_profiles', audcases)]:
        assert set(manifest) == {f'{prefix}/{sid}.json' for sid in input_map}
        assert set(manifest) == {p.relative_to(raw).as_posix() for p in (raw/prefix).iterdir() if p.is_file()}
        for name, expected in manifest.items():
            assert digest(raw/name) == expected, name
    for sid, row in row_map.items():
        assert read(raw/'cases'/f'{sid}.json') == row
        check_subset(row, input_map[sid], sid)
        raw_ranking(row, metric_map[sid], read(raw/'audit_profiles'/f'{sid}.json'), classifications[sid])
    assert sum(r['legacy_reason'] is None for r in rows) == sum(r['hp_reason'] is None for r in rows) == 179
    assert count(r['hp_reason'] for r in rows if r['hp_reason']) == {'nonpositive_total_gain':7}
    assert sum(r['original_fit'].get('p') is not None for r in refs) == 269
    assert count(r['original_fit'].get('reason') for r in refs if r['original_fit'].get('p') is None) == {'no_adaptation':54, 'nonpositive_total_gain':1}
    assert audit['eligible_decimal_cases'] == 179 and audit['guard_decimal_cases'] == 7
    assert audit['eligible_grid_points'] == 179*161 and audit['original_points_verified'] == 179
    assert audit['unresolved_reference_count'] == sum(c['unresolved'] for c in classifications.values()) == classified['unresolved_count']

    def tensor_sha(value):
        arr = np.asarray(value)
        h = hashlib.sha256(json.dumps(dict(dtype=arr.dtype.str, shape=list(arr.shape)),
            sort_keys=True, separators=(',', ':')).encode('utf-8'))
        h.update(arr.tobytes(order='C'))
        return h.hexdigest()

    tensors = {}
    def tensor_file(name):
        if name not in tensors:
            tensors[name] = torch.load(raw/'inputs/source-files'/name, map_location='cpu', weights_only=True)
        return tensors[name]

    groups = defaultdict(list)
    datasets_checked = set()
    initial_test_missing = Counter()
    selected_test_missing = Counter()
    for ref in refs:
        alias = alias_map[ref['reference_id']]
        sid = ref['source_id']
        assert alias['policy_reference'] == ref and ref['profile_id'] == sid
        for key, value in metric_map[sid].items():
            assert alias[key] == value, (ref['reference_id'], key)
        assert ref['reference_id'] in input_map[sid]['reference_ids'] and ref['native_id'] in input_map[sid]['native_ids']
        history = read(raw/'inputs/source-files'/ref['source_paths']['result'])
        if ref['canonical_zero']:
            assert ref['history'] == ref['initial_history']
            assert all(ref['history'][k] == v for k,v in history['metrics'].items())
            assert ref['original_fit'] == {'p':None,'reason':'no_adaptation'}
        else:
            old = {h['epoch']:h for h in history['history']}
            assert ref['history'] == old[ref['epoch']] and ref['initial_history'] == old[0]
            assert ref['original_fit'] == ref['history']['p_star']
        seq = tensor_file(ref['source_paths']['sequence'])
        dataset_path = ref['source_paths']['dataset']
        if dataset_path not in datasets_checked:
            copied = tensor_file(dataset_path)
            live = torch.load(ROOT/dataset_path, map_location='cpu', weights_only=True)
            assert copied.keys() == live.keys()
            for split in live:
                assert len(live[split]) == len(copied[split]) == 2
                for a,b in zip(live[split],copied[split]):
                    assert a.dtype == b.dtype and a.shape == b.shape and torch.equal(a,b)
                assert torch.equal(live[split][0][:,:-1],copied[split][0][:,:-1])
                assert torch.equal(live[split][0][:,1:],copied[split][0][:,1:])
            datasets_checked.add(dataset_path)
        if ref['canonical_zero']:
            init = now = seq['train']['loss'].numpy()
        else:
            checkpoints = {v['epoch']:v for v in seq['checkpoints']}
            init, now = (checkpoints[e]['train']['loss'].numpy() for e in [0, ref['epoch']])
        w = tensor_file(ref['source_paths']['assignment'])['weights'].numpy()
        g = np.subtract(init, now, dtype=np.float32).astype(np.float64)
        assert {k:tensor_sha(v) for k,v in dict(weights=w, initial_loss=init, current_loss=now, gains=g).items()} == ref['array_hashes']
        with np.load(raw/'inputs/arrays'/f'{sid}.npz', allow_pickle=False) as saved:
            assert np.array_equal(saved['weights'],w) and np.array_equal(saved['gains'],g)
        identity = hashlib.sha256(w.astype('<f8').tobytes() + g.astype('<f8').tobytes()).hexdigest()
        assert input_map[sid]['input_sha256'] == identity and sid == 'input-' + identity[:24]
        context = alias['context']
        fit = ref['original_fit']
        for key, value in dict(original_p=fit.get('p'), original_objective=fit.get('objective'),
                original_policy_reason=fit.get('reason'), original_at_lower_bound=fit.get('at_lower_bound'),
                original_at_upper_bound=fit.get('at_upper_bound'), canonical_zero=ref['canonical_zero']).items():
            assert context[key] == value
        assert input_map[sid]['original_p'] == fit.get('p') and input_map[sid]['original_objective'] == fit.get('objective')
        for split in ['train', 'validation', 'test']:
            for component in [None, 'shared', 'group', 'instance']:
                h, h0 = ref['history'][split], ref['initial_history'][split]
                prefix = split
                if split == 'test' and component is None:
                    initial_test_missing[str(ref['stage'])] += h0 is None
                    selected_test_missing[str(ref['stage'])] += h is None
                if component:
                    h = h[component] if h is not None else None
                    h0 = h0[component] if h0 is not None else None
                    prefix += '_' + component
                assert h is not None, (ref['reference_id'], prefix, 'selected metric missing')
                assert context[prefix + '_loss'] == h['loss']
                assert context[prefix + '_initial_loss'] == (h0['loss'] if h0 is not None else None)
                assert context[prefix + '_loss_gain'] == (h0['loss'] - h['loss'] if h0 is not None else None)
                assert (h0 is None) == (ref['stage'] == 4 and split == 'test')
                if component:
                    assert context[prefix + '_accuracy'] == h['accuracy']
                    assert context[prefix + '_initial_accuracy'] == (h0['accuracy'] if h0 is not None else None)
                    assert context[prefix + '_accuracy_gain'] == (h['accuracy'] - h0['accuracy'] if h0 is not None else None)
        for key in ['clipping_cumulative', 'gradient_clip_fraction', 'gradient_norm_mean', 'gradient_norm_max']:
            assert context[key] == ref['history'].get(key)
        total = sum((Decimal.from_float(float(v)) for v in g), Decimal(0))
        absolute = sum((abs(Decimal.from_float(float(v))) for v in g), Decimal(0))
        assert Decimal(context['signed_total_exact']) == total and Decimal(context['absolute_mass']) == absolute
        assert (None if context['signed_total_over_absolute_mass'] is None else Decimal(context['signed_total_over_absolute_mass'])) == (total/absolute if absolute else None)
        groups[ref['cohort'],ref['variant'],ref['width']].append(alias)
    assert dict(initial_test_missing) == {'4': 54, '5': 0, '6': 0}
    assert dict(selected_test_missing) == {'4': 0, '5': 0, '6': 0}
    plot_checks = read(out/'PLOT_CHECKS.json')
    assert plot_checks['status'] == 'PASS' and plot_checks['all_available_points_shown'] is True
    check_subset(plot_checks['limits']['memorization_test'], dict(points=270, total_policy_references=324,
        missing_coordinates=54, missing_own_initial_test_loss=54), 'test-gain plot availability')
    summaries = read(out/'summaries.json')
    aggregate_check(summaries['unique_inputs'], metrics, 'unique')
    aggregate_check(summaries['policy_references'], aliases, 'policy aliases')
    cells = summaries['cells']
    assert len(cells) == len(groups) == 36
    assert set(groups) == {(c,v,w) for c in COHORTS for v in ['M','U'] for w in [64,128,256]}
    for cell in cells:
        condition = cell['condition']
        group = groups[condition['cohort'],condition['variant'],condition['width']]
        assert len(group) == 9 and len({r['policy_reference']['data_seed'] for r in group}) == 3
        assert len({(r['policy_reference']['data_seed'],r['policy_reference']['seed']) for r in group}) == 9
        aggregate_check(cell, group, str(condition))
        for key, summary in cell['context'].items():
            same_stats(summary, stats([r['context'][key] for r in group]), str(condition) + key)
        assert cell['original_p_defined'] == sum(r['context']['original_p'] is not None for r in group)
        assert cell['canonical_zero_references'] == sum(r['context']['canonical_zero'] for r in group)
        assert cell['original_policy_undefined_reasons'] == count(r['context']['original_policy_reason'] for r in group if r['context']['original_p'] is None)
    report_manifest = read(out/'raw-manifest.json')
    allraw = {p.relative_to(raw).as_posix() for p in raw.rglob('*') if p.is_file()}
    assert set(report_manifest) == allraw
    for name, expected in report_manifest.items():
        assert digest(raw/name) == expected
    archive = out/'run-records.zip'
    archivecheck = read(out/'ARCHIVE_CHECK.json')
    assert archivecheck['status'] == archivecheck['crc'] == 'PASS'
    assert digest(archive) == archivecheck['sha256'] and archive.stat().st_size == archivecheck['bytes']
    assert archivecheck['raw_files'] == len(allraw)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert len(names) == len(set(names))
        assert {n[4:] for n in names if n.startswith('raw/')} == allraw
        for name in names:
            if name.startswith('raw/'):
                expected = report_manifest[name[4:]]
            else:
                assert name.startswith('report/')
                expected = digest(out/name[7:])
            assert hashlib.sha256(z.read(name)).hexdigest() == expected, name
        archived_reports = {n[7:] for n in names if n.startswith('report/')}
        assert archived_reports == {p.name for p in out.iterdir() if p.is_file() and p.name not in ['ARCHIVE_CHECK.json','run-records.zip']}
    visual = dict(status='PENDING', images=[], claim='No human or agent visual inspection is implied by numerical or archive checks.')
    if visual_path:
        visual = read(visual_path)
        assert visual['status'] == 'PASS'
        assert set(visual['images']) == {'grid-agreement.png','contrast-errors.png','model-context.png'}
        for name, evidence in visual['images'].items():
            assert evidence['sha256'] == digest(out/name) and evidence['findings']
    unique = summaries['unique_inputs']
    return dict(status='PASS', utc=datetime.now(timezone.utc).isoformat(), run_id=run_id,
        verifier_sha256=digest(Path(__file__)), source_sha256=source, frozen_source_files=len(source),
        input_files_verified=len(input_manifest), source_origin_files_verified=len(origin),
        prior_raw_manifest_bindings=old_raw_bindings, full_token_label_datasets_verified=len(datasets_checked),
        historical_files_verified=len(historical), historical_coverage=freeze['historical_coverage'],
        raw_files_verified=len(allraw), archive_sha256=archivecheck['sha256'], archive_crc='PASS',
        archive_bytes=archivecheck['bytes'], profiles=186, native_checkpoints=207, policy_references=324,
        defined_profiles=179, guarded_profiles=7, defined_policy_references=269,
        original_no_adaptation_references=54, original_nonpositive_references=1,
        cells=36, references_per_cell=9, classification_unresolved=unique['reference_classification_unresolved'],
        domain_mismatches=unique['domain_mismatches'], original_estimates_and_histories_preserved=True,
        independently_recomputed_saved_rankings=True, no_objectives_fits_or_models_evaluated=True,
        unique_method_results={name:{key:unique['methods'][name][key] for key in [
            'comparable','exact_argmin_agreements','reference_minset_agreements',
            'exact_minimum_tie_profiles','any_strict_reversal_profiles','raw_exact_ties_all_pairs_available']}
            for name in METHODS},
        unique_pairwise_results={name:unique['methods'][name]['pairwise'] for name in METHODS},
        original_point_below_grid_count=unique['original_point_below_grid_count'],
        initial_test_missing_by_stage=dict(initial_test_missing),
        selected_test_missing_by_stage=dict(selected_test_missing),
        analysis_revision='r1', analysis_repair_review=repair_review,
        presentation_revision='r2', presentation_review=presentation_review,
        visual_review=visual, limitations=[
            'Final verifier checks saved numerical profiles and independently recomputes ranks; it does not re-evaluate objectives.',
            'Historical coverage excludes a fresh hash pass of all model binaries; selected arrays and dependencies are separately bound.',
            'Repeated policy references and model seeds are not independent dataset replications.',
            'Grid agreement does not establish recovery, continuous optimality, usefulness, or a capacity peak.',
            'Original Stage6 failed utility gate and all original p, K, and selection records remain unchanged.'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--visual-evidence')
    parser.add_argument('--output')
    args = parser.parse_args()
    assert args.run_id.startswith('model-precision-v010-') and '/' not in args.run_id and '\\' not in args.run_id
    target = Path(args.output) if args.output else HERE / ('FINAL_REVIEW-' + args.run_id + '-r2.json')
    assert not target.exists(), 'Final evidence is create-only'
    started = time.perf_counter()
    try:
        with localcontext() as ctx:
            ctx.prec = 110
            result = check_all(args.run_id, args.visual_evidence)
    except BaseException as exc:
        result = dict(status='FAILED', utc=datetime.now(timezone.utc).isoformat(), error=repr(exc),
            traceback=traceback.format_exc(), verifier_sha256=digest(Path(__file__)))
        raise
    finally:
        if 'result' in locals():
            result['elapsed_seconds'] = time.perf_counter() - started
            with target.open('x', encoding='utf-8') as f:
                json.dump(result, f, indent=2, allow_nan=False)
                f.write('\n')
    print(json.dumps({key:result[key] for key in ['status','profiles','policy_references','defined_profiles','classification_unresolved','domain_mismatches','unique_method_results','elapsed_seconds']}), flush=True)


if __name__ == '__main__':
    main()
