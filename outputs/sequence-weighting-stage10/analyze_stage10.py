"""Prespecified descriptive Stage10 analysis; searches never replace saved estimates."""
import argparse
import copy
import csv
import json
import math
import os
import resource
import shutil
import sys
import time
import traceback
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
sys.dont_write_bytecode = True
from common_stage10 import ROOT, HERE, SOURCES, read, sha, write, utc, verify_source, verify_inputs

PRECISION = 110
COHORTS = ['S4_fixed30', 'S5_R', 'S6_P1_R', 'S6_P2_R', 'S6_P3_R', 'S6_P4_R']
STATUSES = ['compared', 'guard', 'unresolved', 'not_run']
FLAGS = ['precision_converged', 'search_objective_agreement', 'parameter_agreement',
         'original_objective_agreement', 'original_parameter_agreement',
         'original_better_than_search', 'weak_neighborhood', 'unresolved']
VALUE_FIELDS = ['primary_p', 'reference_p', 'original_p_exact', 'J_primary_110', 'J_reference_110',
    'J_original_110', 'search_signed_gap', 'original_signed_gap', 'search_parameter_delta',
    'original_parameter_delta', 'reference_mesh_span', 'search_objective_tolerance',
    'original_objective_tolerance', 'parameter_tolerance']


def dec(value):
    return Decimal.from_float(value) if isinstance(value, float) else Decimal(value)


def fmt(value):
    return 'undefined' if value is None else format(dec(value), '.6g')


def counts(values):
    return dict(sorted(Counter(values).items(), key=lambda item: str(item[0])))


def decimal_stats(values):
    """Nulls retain their denominator; values are never rounded through binary64."""
    numbers = [dec(value) for value in values if value is not None]
    assert all(v.is_finite() for v in numbers)
    with localcontext() as ctx:
        ctx.prec = PRECISION
        mean = sum(numbers, Decimal(0)) / len(numbers) if numbers else None
        sd = (sum(((v - mean) ** 2 for v in numbers), Decimal(0)) / (len(numbers) - 1)).sqrt() if len(numbers) > 1 else None
        ordered = sorted(numbers)
        middle = len(numbers) // 2
        median = (ordered[middle] if len(numbers) % 2 else (ordered[middle - 1] + ordered[middle]) / 2) if numbers else None
        return dict(total=len(values), defined=len(numbers), undefined=len(values) - len(numbers),
            conditional_mean=str(mean) if mean is not None else None,
            conditional_sd=str(sd) if sd is not None else None,
            conditional_minimum=str(min(numbers)) if numbers else None,
            conditional_maximum=str(max(numbers)) if numbers else None,
            conditional_median=str(median) if median is not None else None,
            unconditional_mean=str(mean) if mean is not None and len(numbers) == len(values) else None)


def materialize(planned, observed, end_status):
    """Every planned input survives interrupted execution with an explicit status."""
    expected = {p['source_id']: p for p in planned}
    actual = {p['source_id']: p for p in observed}
    assert len(expected) == len(planned) and len(actual) == len(observed)
    assert set(actual) <= set(expected)
    rows = []
    for metadata in planned:
        key = metadata['source_id']
        if key in actual:
            row = copy.deepcopy(actual[key])
            assert row['status'] in STATUSES[:-1]
            for field in ['source_id', 'original_p', 'original_objective', 'original_reason', 'expected_guard', 'reference_ids', 'native_ids']:
                if field in row and field in metadata:
                    assert row[field] == metadata[field], (key, field)
            assert isinstance(row['classification'], dict)
            for field in FLAGS:
                assert field in row['classification'], (key, field)
                assert row['classification'][field] is None or type(row['classification'][field]) is bool, (key, field)
            assert isinstance(row['classification'].get('reasons'), list)
            assert all(isinstance(reason, str) for reason in row['classification']['reasons'])
            assert row['classification']['unresolved'] == (row['status'] == 'unresolved')
            if row['status'] == 'guard':
                assert row.get('values') is None
                assert row['primary_reason'] == row['reference_reason'] == metadata['expected_guard']
                assert row['primary_reason'] is not None
                assert all(row['classification'][field] is None for field in FLAGS if field != 'unresolved')
            elif row.get('values') is not None:
                for field in VALUE_FIELDS:
                    assert field in row['values'], (key, field)
                    value = row['values'][field]
                    assert value is None or dec(value).is_finite(), (key, field)
            if row['status'] == 'compared':
                assert row.get('values') is not None
        else:
            row = dict(copy.deepcopy(metadata), status='not_run', primary_reason=None, reference_reason=None,
                classification=dict({field: None for field in FLAGS}, unresolved=True,
                    reasons=['not_run_after_' + end_status]), values=None, neighborhood=[], elapsed_seconds=None)
        row['planned_metadata'] = copy.deepcopy(metadata)
        row['global_optimality_certified'] = False
        rows.append(row)
    return rows


def summarize(rows):
    result = dict(total=len(rows), unique_inputs=len({r['source_id'] for r in rows}),
        status_counts={status: sum(r['status'] == status for r in rows) for status in STATUSES},
        original_defined=sum(r['planned_metadata'].get('original_p') is not None for r in rows),
        original_undefined_reasons=counts(r['planned_metadata'].get('original_reason') for r in rows if r['planned_metadata'].get('original_p') is None),
        expected_guard_reasons=counts(r['planned_metadata'].get('expected_guard') for r in rows if r['planned_metadata'].get('expected_guard') is not None),
        primary_guard_reasons=counts(r.get('primary_reason') for r in rows if r.get('primary_reason') is not None),
        reference_guard_reasons=counts(r.get('reference_reason') for r in rows if r.get('reference_reason') is not None),
        unresolved_reasons=counts(reason for r in rows for reason in r['classification'].get('reasons', [])),
        classification={}, values={}, global_optimality_certified=False)
    for field in FLAGS:
        values = [r['classification'].get(field) for r in rows]
        available = sum(v is not None for v in values)
        yes = sum(v is True for v in values)
        result['classification'][field] = dict(total=len(rows), available=available, unavailable=len(rows) - available,
            true=yes, false=sum(v is False for v in values), conditional_true_rate=yes / available if available else None,
            unconditional_true_rate=yes / len(rows) if rows and available == len(rows) else None)
    for field in VALUE_FIELDS:
        values = [(r.get('values') or {}).get(field) for r in rows]
        result['values'][field] = decimal_stats(values)
        if field.endswith('_signed_gap'):
            result['values'][field]['negative'] = sum(dec(v) < 0 for v in values if v is not None)
            result['values'][field]['zero'] = sum(dec(v) == 0 for v in values if v is not None)
            result['values'][field]['positive'] = sum(dec(v) > 0 for v in values if v is not None)
    for field in ['primary_p', 'reference_p', 'original_p_exact']:
        values = [(r.get('values') or {}).get(field) for r in rows]
        result[field + '_boundary'] = dict(available=sum(v is not None for v in values),
            exact_zero=sum(dec(v) == 0 for v in values if v is not None),
            exact_eight=sum(dec(v) == 8 for v in values if v is not None),
            within_1e_6_lower=sum(0 <= dec(v) <= Decimal('1e-6') for v in values if v is not None),
            within_1e_6_upper=sum(Decimal('8') - Decimal('1e-6') <= dec(v) <= 8 for v in values if v is not None))
    assert sum(result['status_counts'].values()) == len(rows)
    return result


def join_context(rows, references, historical):
    by_source = {row['source_id']: row for row in rows}
    old = {row['reference_id']: row for row in historical}
    assert len(old) == len(historical) and set(old) == {r['reference_id'] for r in references}
    aliases = []
    for ref in references:
        previous = old[ref['reference_id']]
        assert previous['policy_reference'] == ref, ref['reference_id']
        key = ref.get('profile_id', ref.get('source_id'))
        assert previous['source_id'] == key
        row = copy.deepcopy(by_source[key])
        row.update(reference_id=ref['reference_id'], native_id=ref['native_id'],
            cohort=ref['cohort'], variant=ref['variant'], width=ref['width'],
            policy_reference=copy.deepcopy(ref), context=copy.deepcopy(previous['context']))
        aliases.append(row)
    assert len({r['reference_id'] for r in aliases}) == len(aliases)
    assert set(by_source) == {r['source_id'] for r in aliases}
    return aliases


def cells_for(aliases, enforce_design=True):
    groups = defaultdict(list)
    for row in aliases:
        groups[row['cohort'], row['variant'], row['width']].append(row)
    if enforce_design:
        assert set(groups) == {(c, v, w) for c in COHORTS for v in ['M', 'U'] for w in [64, 128, 256]}
    cells = []
    for key in sorted(groups, key=lambda k: (COHORTS.index(k[0]), k[1], k[2])):
        group = groups[key]
        if enforce_design:
            assert len(group) == 9
            assert len({(r['policy_reference']['data_seed'], r['policy_reference']['seed']) for r in group}) == 9
            assert len({r['policy_reference']['data_seed'] for r in group}) == 3
        cell = summarize(group)
        cell.update(condition=dict(cohort=key[0], variant=key[1], width=key[2]),
            native_checkpoints=len({r['native_id'] for r in group}),
            dataset_seeds=sorted({r['policy_reference']['data_seed'] for r in group}),
            model_weight_seeds=sorted({r['policy_reference']['seed'] for r in group}),
            historical_context={field: decimal_stats([r['context'].get(field) for r in group])
                for field in group[0]['context'] if field not in ['original_policy_reason', 'canonical_zero',
                    'clipping_applicable', 'original_at_lower_bound', 'original_at_upper_bound']},
            original_policy_undefined_reasons=counts(r['context']['original_policy_reason'] for r in group if r['context']['original_p'] is None),
            original_lower_boundary=sum(r['context']['original_at_lower_bound'] is True for r in group),
            original_upper_boundary=sum(r['context']['original_at_upper_bound'] is True for r in group),
            reference_ids=[r['reference_id'] for r in group], source_ids=[r['source_id'] for r in group])
        cells.append(cell)
    return cells


def flatten(value, prefix=''):
    out = {}
    for key, item in value.items():
        label = f'{prefix}_{key}' if prefix else str(key)
        if isinstance(item, dict):
            out.update(flatten(item, label))
        elif isinstance(item, list):
            out[label] = json.dumps(item, allow_nan=False)
        else:
            out[label] = item
    return out


def jsonlines(path, rows):
    with path.open('x', encoding='utf-8') as stream:
        for row in rows:
            stream.write(json.dumps(row, allow_nan=False) + '\n')


def csvwrite(path, rows):
    with path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        writer.writeheader()
        writer.writerows(rows)


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
        ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows])


def figures(out, rows, cells):
    mpl = ROOT / 'work/.matplotlib'
    mpl.mkdir(parents=True, exist_ok=True)
    os.environ['MPLCONFIGDIR'] = str(mpl)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'figure.dpi': 140, 'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False})
    evidence = {}

    def points(field):
        chosen = [(i, (r.get('values') or {}).get(field)) for i, r in enumerate(rows)]
        out = [(i, float(dec(value))) for i, value in chosen if value is not None]
        assert all(math.isfinite(v) for _, v in out)
        return out

    def draw(ax, field, title, ylabel, color, tolerance=None):
        pairs = points(field)
        xs, ys = ([p[i] for p in pairs] for i in [0, 1])
        if pairs:
            ax.scatter(xs, ys, s=17, alpha=.7, color=color)
        ax.axhline(0, color='black', lw=.6)
        if tolerance is not None:
            ax.axhline(tolerance, color='#666666', linestyle=':', lw=.8)
            ax.axhline(-tolerance, color='#666666', linestyle=':', lw=.8)
        bounds_values = ys + [0.] + ([-tolerance, tolerance] if tolerance is not None else [])
        nonzero = [abs(v) for v in bounds_values if v]
        if nonzero:
            threshold = max(1e-300, 10. ** (math.floor(math.log10(min(nonzero))) - 1))
            ax.set_yscale('symlog', linthresh=threshold)
            transform = ax.yaxis.get_transform()
            lo, hi = transform.transform([min(bounds_values), max(bounds_values)])
            pad = (hi - lo) * .05
            ylim = tuple(transform.inverted().transform([lo - pad, hi + pad]))
            ax.set_ylim(ylim)
            # Tick installation must never expand these explicit transformed data bounds.
            ticks = [v for v in ax.get_yticks() if ylim[0] <= v <= ylim[1] and (v == 0 or abs(v) > threshold * 1.01)]
            ax.set_yticks(ticks)
            ax.set_ylim(ylim)
        else:
            ax.set_ylim(-1., 1.)
        if not pairs:
            ax.text(.5, .5, 'No available comparisons', transform=ax.transAxes, ha='center', va='center')
        ax.set(title=f'{title}: {len(pairs)}/{len(rows)} available', xlabel='Prespecified distinct-input index',
            ylabel=ylabel, xlim=(-2, max(1, len(rows) + 1)))
        ax.grid(alpha=.15)
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        assert all(xlim[0] <= x <= xlim[1] and ylim[0] <= y <= ylim[1] for x, y in pairs)
        evidence[field] = dict(points=len(pairs), unavailable=len(rows) - len(pairs),
            xlim=list(map(float, xlim)), ylim=list(map(float, ylim)), ticks=list(map(float, ax.get_yticks())),
            tolerance_lines=[-tolerance, tolerance] if tolerance is not None else [],
            plotted_source_ids=[rows[i]['source_id'] for i, _ in pairs])

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.7), layout='constrained')
    draw(axes[0], 'search_signed_gap', 'Primary minus independent search', 'Signed objective gap at Decimal110 (symlog)', '#2374a6')
    draw(axes[1], 'original_signed_gap', 'Saved original minus independent search', 'Signed objective gap at Decimal110 (symlog)', '#70508b')
    fig.suptitle('Signed gaps are retained; negative gaps do not establish a better global optimum\nGuards, unfinished searches and missing comparisons retain explicit nulls in every table')
    fig.savefig(out / 'objective-gaps.png')
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.7), layout='constrained')
    draw(axes[0], 'search_parameter_delta', 'Difference between reference methods', 'Recorded parameter difference (symlog)', '#2374a6', 1e-6)
    draw(axes[1], 'original_parameter_delta', 'Difference from saved original', 'Recorded parameter difference (symlog)', '#70508b', 1e-6)
    fig.suptitle('Parameter differences are diagnostic; objective agreement and weak neighborhoods are reported separately\nDotted lines mark the ±1e-6 parameter tolerance; no original estimate is replaced')
    fig.savefig(out / 'parameter-differences.png')
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(14, 7.5), layout='constrained')
    colors = {'compared': '#2374a6', 'guard': '#999999', 'unresolved': '#bf582f', 'not_run': '#e4c35d'}
    for ax, cohort in zip(axes.flat, COHORTS):
        group = [c for c in cells if c['condition']['cohort'] == cohort]
        labels = [f"{c['condition']['variant']}{c['condition']['width']}" for c in group]
        x = np.arange(len(group))
        bottom = np.zeros(len(group))
        for status in STATUSES:
            values = np.array([c['status_counts'][status] for c in group])
            ax.bar(x, values, bottom=bottom, label=status, color=colors[status], width=.7)
            bottom += values
        ax.set(title=cohort, xticks=x, xticklabels=labels, ylim=(0, 10.4), yticks=[0, 3, 6, 9], ylabel='Policy references (of 9)')
        for i, cell in enumerate(group):
            comparison = cell['classification']['original_objective_agreement']
            ax.text(i, 9.25, f"{comparison['true']}/{comparison['available']}", ha='center', fontsize=8)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='outside lower center', ncol=4, frameon=False)
    fig.suptitle('Every policy reference retained; labels show original-objective matches / available comparisons\nStatus counts preserve guards and incomplete cases; repeated panels are not independent replications')
    fig.savefig(out / 'cohort-coverage.png')
    plt.close(fig)
    evidence['cohort_coverage'] = dict(cells=len(cells), references=sum(c['total'] for c in cells), statuses=STATUSES)
    write(out / 'PLOT_CHECKS.json', dict(status='PASS', data_limits=evidence, all_available_points_shown=True,
        rounding_to_binary64_is_plot_only=True, tick_setting_preserves_data_limits=True, visual_review='pending'))


def report(raw, out, unique, aliases_summary, cells, end, audit):
    text = '# Stage 10 — continuous-search agreement on retained model gains\n\n'
    text += f"Run `{raw.name}` ended with status **{end['status']}**; infrastructure/provenance audit: **{audit['status']}**. "
    text += 'The complete design retains 186 distinct weight/gain inputs, 207 saved native checkpoints and 324 policy references. Original estimates, model selections and utility conclusions remain unchanged.\n\n'
    text += '## Coverage and measured agreement\n\n'
    text += table(['Counting unit', 'Planned', 'Compared', 'Guard', 'Unresolved', 'Not run'], [
        [label, summary['total']] + [summary['status_counts'][s] for s in STATUSES]
        for label, summary in [('Distinct inputs', unique), ('Policy references (reused inputs)', aliases_summary)]]) + '\n\n'
    text += table(['Diagnostic (distinct inputs)', 'True', 'False', 'Available', 'Unavailable'], [
        [field] + [unique['classification'][field][k] for k in ['true', 'false', 'available', 'unavailable']]
        for field in FLAGS]) + '\n\n'
    text += 'All denominators include the full design. Conditional rates use only available comparisons and are explicitly labeled; an unavailable comparison is not an agreement or disagreement. Guards retain their mathematical reasons, epoch0 retains historical `no_adaptation`, and interruption leaves explicit `not_run` records. Numerical disagreement and incomplete convergence remain reported.\n\n'
    text += '## Frozen search methods and limits\n\n'
    text += 'The primary Decimal80 search scans 513 points j/64 on [0,8], retains every mesh point (including endpoints and exact-zero derivative nodes), and bisects every strict derivative sign-change bracket to width 1e-12 with at most 40 iterations. Its candidates comprise all mesh points and final bracket midpoints. The independent Decimal110 search uses a different algorithm: 1,025 points j/128 and golden-section objective refinement of every declared mesh-local-minimum neighborhood to width 1e-12 with at most 80 iterations. Its candidates comprise all mesh points and final bracket midpoints. Candidate, mesh, bracket, derivative, refinement and failure records are retained in the raw run. The frozen protocol and config define plateau handling, deterministic ties and all convergence rules.\n\n'
    text += 'Both candidate points and the saved original point are compared using Decimal110 arithmetic. The search-agreement objective tolerance is 1e-18 times the frozen profile scale; original-point objective tolerance is 1e-12 times that scale; parameter tolerance is 1e-6. Per-input scale/tolerances and signed gaps remain in the tables. Different parameter values may be objective-equivalent in weakly separated profiles. Precision convergence and objective/parameter classifications remain separate.\n\n'
    text += 'Neither search provides a global-optimality certificate. Finite meshes and local refinements can miss stationary structure; agreement means agreement between these bounded searches. A saved original point lower than the reference beyond tolerance is unresolved reference-search evidence. The original point never participates in candidate selection. The shared numerical search/audit ceiling is one hour, checked with monotonic and UTC elapsed time, including verification and cache preparation. No adaptive retry, grid expansion or outcome-based subset is permitted.\n\n'
    text += table(['Quantity', 'Available /186', 'Conditional mean', 'Minimum', 'Maximum', 'Negative / zero / positive'], [
        [field, f"{unique['values'][field]['defined']}/186", fmt(unique['values'][field]['conditional_mean']),
         fmt(unique['values'][field]['conditional_minimum']), fmt(unique['values'][field]['conditional_maximum']),
         '/'.join(str(unique['values'][field].get(k, '—')) for k in ['negative', 'zero', 'positive'])]
        for field in ['search_signed_gap', 'original_signed_gap', 'search_parameter_delta', 'original_parameter_delta', 'reference_mesh_span']]) + '\n\n'
    text += '![Signed objective gaps](objective-gaps.png)\n\n![Parameter differences](parameter-differences.png)\n\n'
    text += 'Signed gaps and Decimal strings are preserved without clipping. Summary arithmetic uses 110 decimal digits. Nulls prevent an unconditional mean; conditional statistics retain availability counts. Boundary counts distinguish exact endpoints and proximity within 1e-6, while historical boundary flags remain unchanged in model-context records. Neighborhood points and their signed objective gaps remain fully recorded; weak neighborhoods describe numerical separation, not statistical confidence intervals.\n\n'
    text += '## Policy cells and preserved model context\n\n'
    text += 'Each of the 36 cells contains three corpus seeds × three model/weight seeds. Model seeds within one corpus and reused Stage6 panel selections are paired observations, not additional independent datasets. These tables are descriptive and do not re-evaluate Stage6 usefulness or any p* peak.\n\n'
    text += table(['Cohort', 'Variant', 'Width', 'Distinct /9', 'Compared', 'Guard', 'Unresolved', 'Not run', 'Original objective match / available'], [
        [c['condition']['cohort'], c['condition']['variant'], c['condition']['width'], c['unique_inputs']] +
        [c['status_counts'][s] for s in STATUSES] +
        [f"{c['classification']['original_objective_agreement']['true']}/{c['classification']['original_objective_agreement']['available']}"] for c in cells]) + '\n\n'
    text += '![Complete cohort coverage](cohort-coverage.png)\n\n'
    text += 'Historical contexts are copied exactly from the audited Stage9 report and joined by full policy-reference identity. They supply saved training memorization, validation/test losses, clipping, signed gain/cancellation and original fit context; no Stage9 grid statistic is reused as a Stage10 conclusion. All 324 selected test losses remain available. Stage4 intentionally did not measure own-initial epoch0 test metrics, so those 54 test gains remain null; 270/324 test gains are available. No imputation or premixed-baseline proxy is used.\n\n'
    text += table(['Cohort', 'Variant', 'Width', 'Train NLL gain', 'Validation NLL gain', 'Selected test NLL', 'Test NLL gain', 'Test gain available /9', 'Train instance accuracy', 'Clipping (available)', 'Original p (available)', 'Original fit J (available)'], [
        [c['condition']['cohort'], c['condition']['variant'], c['condition']['width']] +
        [fmt(c['historical_context'][f]['conditional_mean']) for f in ['train_loss_gain', 'validation_loss_gain', 'test_loss', 'test_loss_gain']] +
        [f"{c['historical_context']['test_loss_gain']['defined']}/9"] +
        [fmt(c['historical_context']['train_instance_accuracy']['conditional_mean'])] +
        [f"{fmt(c['historical_context'][f]['conditional_mean'])} ({c['historical_context'][f]['defined']}/9)"
         for f in ['clipping_cumulative', 'original_p', 'original_objective']]
        for c in cells]) + '\n\n'
    text += '## Interpretation and provenance\n\n'
    text += 'This is a bounded numerical search diagnostic on saved signed gains, not fresh known-truth recovery or model generalization. No model training, inference, retuning, p* replacement, K recomputation or utility-gate revision occurs. Stage6 primary utility failures remain unchanged. Three capacities cannot establish a shift between two interior peaks; one Pythia size/seed cannot establish a scaling curve. No novelty or publication claim is made. The next research focus is a bounded Stage4–10 synthesis, with numerical validity, recovery and held-out usefulness kept distinct. No further experiment is launched automatically.\n\n'
    text += f"Results SHA256: `{sha(raw / 'results.jsonl')}`. All frozen sources, copied input provenance, raw searches/comparisons, guards, incomplete records, complete histories, fixture checks and report artifacts are archived. CRC and SHA256 are checked; final visual review is recorded separately.\n\n"
    text += 'Execution record:\n\n```json\n' + json.dumps(end, indent=2, allow_nan=False) + '\n```\n'
    (out / 'REPORT.md').write_text(text, encoding='utf-8')


def main():
    started, wall = time.perf_counter(), datetime.now(timezone.utc)
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id and args.run_id not in ['.', '..'] and '/' not in args.run_id and '\\' not in args.run_id
    raw, out = ROOT / 'work/runs' / args.run_id, HERE / f'results-{args.run_id}'
    assert not out.exists(), 'Preserve previous or partial analyses'
    end, audit = read(raw / 'END.json'), read(raw / 'AUDIT.json')
    assert end['status'] in ['COMPLETE', 'BUDGET_EXHAUSTED', 'FAILED']
    assert audit['status'] in ['PASS', 'PARTIAL']
    verify_source(raw)
    verify_inputs(raw)
    source = read(raw / 'source_manifest.json')
    results_sha = sha(raw / 'results.jsonl')
    assert results_sha == end['results_sha256'] == audit['results_sha256']
    planned = read(raw / 'inputs/profiles.json')
    refs = read(raw / 'inputs/references.json')
    historical = [json.loads(line) for line in (raw / 'inputs/stage9_policy_context.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    observed = [json.loads(line) for line in (raw / 'results.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(planned) == 186 and len(refs) == len(historical) == 324
    if end['status'] == 'COMPLETE':
        assert len(observed) == len(planned)
    out.mkdir()
    try:
        rows = materialize(planned, observed, end['status'])
        aliases = join_context(rows, refs, historical)
        assert len({r['native_id'] for r in aliases}) == 207
        assert sum(r['context']['test_loss'] is not None for r in aliases) == 324
        assert sum(r['context']['test_loss_gain'] is None for r in aliases) == 54
        assert {r['cohort'] for r in aliases if r['context']['test_initial_loss'] is None} == {'S4_fixed30'}
        unique, aliases_summary, cells = summarize(rows), summarize(aliases), cells_for(aliases)
        jsonlines(out / 'input-metrics.jsonl', rows)
        jsonlines(out / 'policy-reference-metrics.jsonl', aliases)
        csvwrite(out / 'input-metrics.csv', [flatten(r) for r in rows])
        csvwrite(out / 'policy-reference-metrics.csv', [flatten({k: v for k, v in r.items() if k not in ['policy_reference', 'planned_metadata']}) for r in aliases])
        write(out / 'summaries.json', dict(unique_inputs=unique, policy_references=aliases_summary, cells=cells,
            counting_units='Unique inputs and reused policy references reported separately; no IID inference', global_optimality_certified=False))
        csvwrite(out / 'summaries.csv', [flatten(c) for c in cells])
        write(out / 'SUMMARY_AUDIT.json', dict(status='PASS', utc=utc(), planned_inputs=len(rows), observed_rows=len(observed),
            policy_references=len(aliases), native_checkpoints=207, cells=len(cells),
            original_p_preserved=True, context_copied_exactly=True, selected_test_available=324,
            test_gain_available=270, unavailable_initial_test=54, decimal_precision=PRECISION,
            global_optimality_certified=False, end_status=end['status'], numerical_audit_status=audit['status']))
        figures(out, rows, cells)
        report(raw, out, unique, aliases_summary, cells, end, audit)
        for name in source:
            shutil.copy2(raw / 'source' / name, out / name)
        shutil.copy2(raw / 'AUDIT.json', out / 'AUDIT.json')
        write(out / 'analysis-provenance.json', dict(utc=utc(), source_sha256=source, results_sha256=results_sha,
            stage9_policy_context_sha256=sha(raw / 'inputs/stage9_policy_context.jsonl'),
            END_sha256=sha(raw / 'END.json'), AUDIT_sha256=sha(raw / 'AUDIT.json'), visual_review='pending'))
        write(out / 'ANALYSIS_RUNTIME.json', dict(utc=utc(), pre_archive_elapsed_seconds=time.perf_counter() - started,
            pre_archive_utc_elapsed_seconds=(datetime.now(timezone.utc) - wall).total_seconds(),
            peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, full_runtime_location='ARCHIVE_CHECK.json'))
        manifest = {p.relative_to(raw).as_posix(): sha(p) for p in sorted(raw.rglob('*')) if p.is_file()}
        write(out / 'raw-manifest.json', manifest)
        archive = out / 'run-records.zip'
        with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
            for path in sorted(raw.rglob('*')):
                if path.is_file():
                    bundle.write(path, 'raw/' + path.relative_to(raw).as_posix())
            for path in sorted(out.iterdir()):
                if path.is_file() and path != archive:
                    bundle.write(path, 'report/' + path.name)
        with zipfile.ZipFile(archive) as bundle:
            assert bundle.testzip() is None
        write(out / 'ARCHIVE_CHECK.json', dict(status='PASS', crc='PASS', utc=utc(), sha256=sha(archive), bytes=archive.stat().st_size,
            raw_files=len(manifest), analysis_elapsed_seconds=time.perf_counter() - started,
            analysis_utc_elapsed_seconds=(datetime.now(timezone.utc) - wall).total_seconds(),
            peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024))
        print(json.dumps(dict(output=str(out), planned_inputs=len(rows), observed=len(observed), references=len(aliases), cells=len(cells), archive='PASS')), flush=True)
    except BaseException as exc:
        write(out / 'ANALYSIS_FAILURE.json', dict(status='FAILED', utc=utc(), error=repr(exc), traceback=traceback.format_exc(),
            instruction='Preserve failure; any repair requires a separate source and output version.'))
        raise


if __name__ == '__main__':
    main()
