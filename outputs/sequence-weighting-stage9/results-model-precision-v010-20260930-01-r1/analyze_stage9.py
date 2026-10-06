"""Frozen Stage9 descriptive analysis; no fit, selection, or p* replacement."""
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
from common_stage9 import ROOT, HERE, SOURCES, read, sha, write, utc, verify_source, verify_inputs
from metrics import METHODS, PRECISION, decimal_stats, fmt, profile_metrics

LABELS = {'legacy_J': 'Legacy J64', 'naive_D64': 'Naive D64', 'stable_D64': 'Factored D64'}
COLORS = {'legacy_J': '#70508b', 'naive_D64': '#bf582f', 'stable_D64': '#2374a6'}
COHORTS = ['S4_fixed30', 'S5_R', 'S6_P1_R', 'S6_P2_R', 'S6_P3_R', 'S6_P4_R']
COHORT_LABELS = ['Stage4 fixed epoch30', 'Stage5 R', 'Stage6 P1 R', 'Stage6 P2 R', 'Stage6 P3 R', 'Stage6 P4 R']


def counts(values):
    return dict(sorted(Counter(values).items(), key=lambda item: str(item[0])))


def summarize_profiles(profiles):
    """The caller declares the counting unit; duplicates deliberately remain."""
    both = [p for p in profiles if p['both_defined']]
    refs = [p for p in profiles if p['reference_defined']]
    result = dict(total=len(profiles), unique_inputs=len({p['source_id'] for p in profiles}),
        legacy_defined=sum(p['legacy_defined'] for p in profiles), reference_defined=len(refs), both_defined=len(both),
        domain_mismatches=sum(p['domain_mismatch'] for p in profiles),
        legacy_undefined_reasons=counts(p['legacy_reason'] for p in profiles if not p['legacy_defined']),
        hp_undefined_reasons=counts(p['hp_reason'] for p in profiles if not p['reference_defined']),
        reference_classification_unresolved=sum(p['reference_classification_unresolved'] for p in profiles),
        reference_argmin_frequencies=counts(p['reference']['argmin_index'] for p in refs),
        reference_exact_minimum_tie_profiles=sum(p['reference']['exact_minimum_count'] > 1 for p in refs),
        reference_band_minimum_tie_profiles=sum(p['reference']['minimum_set_size'] > 1 for p in refs),
        reference_exact_pair_ties=sum(p['pairwise']['reference_exact_ties'] for p in refs),
        reference_nonexact_near_pair_ties=sum(p['pairwise']['reference_nonexact_near_ties'] for p in refs),
        reference_strict_pairs=sum(p['pairwise']['reference_strict_pairs'] for p in refs), methods={})
    for field in ['contrast_scale', 'contrast_span', 'top_two_gap', 'tau']:
        result['reference_' + field] = decimal_stats([p['reference'][field] if p['reference'] else None for p in profiles])
    result['normalization_difference'] = {field: decimal_stats([p['normalization_difference'][field] for p in profiles])
        for field in ['legacy_minus_hp', 'fsum_minus_hp', 'legacy_relative_to_hp', 'fsum_relative_to_hp']}
    signed = [p['original_point']['signed_HP_gap_vs_grid_min'] if p['original_point'] else None for p in profiles]
    result['original_point_signed_gap'] = decimal_stats(signed)
    result['original_point_below_grid_count'] = sum(Decimal(v) < 0 for v in signed if v is not None)
    result['original_point_equal_grid_count'] = sum(Decimal(v) == 0 for v in signed if v is not None)
    for name in METHODS:
        available = [p['methods'][name] for p in profiles if p['methods'][name]['available']]
        comparisons = [p['methods'][name] for p in both]
        fields = ['raw_exact_ties_all_pairs', 'strict_agreements', 'strict_reversals',
                  'float_ties_against_reference_strict', 'float_strict_on_reference_nonstrict',
                  'float_ties_on_reference_nonstrict']
        pairs = {field: sum(m['pairwise'][field] for m in comparisons) for field in fields}
        denominator = sum(p['pairwise']['reference_strict_pairs'] for p in both)
        exact = sum(m['exact_argmin_agreement'] for m in comparisons)
        band = sum(m['reference_minset_agreement'] for m in comparisons)
        result['methods'][name] = dict(available=len(available), comparable=len(comparisons),
            argmin_frequencies=counts(m['argmin_index'] for m in available),
            exact_minimum_tie_profiles=sum(m['exact_minimum_count'] > 1 for m in available),
            raw_exact_ties_all_pairs_available=sum(m['raw_exact_ties_all_pairs'] for m in available),
            exact_argmin_agreements=exact, reference_minset_agreements=band,
            exact_argmin_agreement_rate_conditional=exact / len(comparisons) if comparisons else None,
            reference_minset_agreement_rate_conditional=band / len(comparisons) if comparisons else None,
            any_strict_reversal_profiles=sum(m['pairwise']['strict_reversals'] > 0 for m in comparisons),
            any_float_tie_on_reference_strict_profiles=sum(m['pairwise']['float_ties_against_reference_strict'] > 0 for m in comparisons),
            pairwise=dict(reference_strict_denominator=denominator,
                possible_pairs=sum(p['pairwise']['total_pairs'] for p in both),
                float_tie_rate_on_reference_strict=pairs['float_ties_against_reference_strict'] / denominator if denominator else None,
                strict_reversal_rate=pairs['strict_reversals'] / denominator if denominator else None, **pairs),
            reference_regret=decimal_stats([p['methods'][name]['reference_regret'] for p in profiles]),
            reference_regret_excess_over_tau=decimal_stats([p['methods'][name]['reference_regret_excess_over_tau'] for p in profiles]),
            error={field: decimal_stats([p['methods'][name]['error'][field] if p['methods'][name]['error'] else None for p in profiles])
                   for field in ['max_abs_error', 'relative_to_contrast_scale', 'relative_to_contrast_span']})
    return result


def signed_context(gains):
    with localcontext() as ctx:
        ctx.prec = PRECISION
        values = [Decimal.from_float(float(v)) for v in gains]
        positive = sum((v for v in values if v > 0), Decimal(0))
        negative = -sum((v for v in values if v < 0), Decimal(0))
        total = positive - negative
        absolute = positive + negative
        return dict(signed_total_exact=str(total), positive_mass=str(positive), negative_mass_magnitude=str(negative),
            absolute_mass=str(absolute), signed_total_over_absolute_mass=str(total / absolute) if absolute else None,
            absolute_total_over_absolute_mass=str(abs(total) / absolute) if absolute else None,
            negative_gain_fraction=sum(v < 0 for v in values) / len(values), zero_gain_fraction=sum(v == 0 for v in values) / len(values),
            total_gain_legacy=sum(float(v) for v in gains), total_gain_fsum=math.fsum(float(v) for v in gains))


def context(reference, gain_context):
    h, h0, fit = reference['history'], reference['initial_history'], reference['original_fit']
    result = dict(copy.deepcopy(gain_context), original_p=fit.get('p'), original_objective=fit.get('objective'),
        original_policy_reason=fit.get('reason'), original_at_lower_bound=fit.get('at_lower_bound'),
        original_at_upper_bound=fit.get('at_upper_bound'), canonical_zero=reference['canonical_zero'],
        clipping_applicable=reference['epoch'] > 0, clipping_cumulative=h.get('clipping_cumulative'),
        gradient_clip_fraction=h.get('gradient_clip_fraction'), gradient_norm_mean=h.get('gradient_norm_mean'),
        gradient_norm_max=h.get('gradient_norm_max'), saved_total_gain=h.get('total_gain'),
        saved_negative_gain_fraction=h.get('negative_gain_fraction'))
    for split in ['train', 'validation', 'test']:
        for component in [None, 'shared', 'group', 'instance']:
            now = h[split] if component is None else h[split][component]
            initial = h0[split] if component is None else h0[split][component]
            prefix = split if component is None else split + '_' + component
            result[prefix + '_loss'] = now['loss']
            result[prefix + '_initial_loss'] = initial['loss']
            result[prefix + '_loss_gain'] = initial['loss'] - now['loss']
            if component is not None:
                result[prefix + '_accuracy'] = now['accuracy']
                result[prefix + '_initial_accuracy'] = initial['accuracy']
                result[prefix + '_accuracy_gain'] = now['accuracy'] - initial['accuracy']
    return result


def join_references(references, profiles, gain_contexts):
    by_id = {p['source_id']: p for p in profiles}
    assert len(by_id) == len(profiles)
    rows = []
    for reference in references:
        key = reference.get('profile_id', reference.get('source_id'))
        assert key in by_id
        row = copy.deepcopy(by_id[key])
        row['policy_reference'] = copy.deepcopy(reference)
        row['context'] = context(reference, gain_contexts[key])
        row['reference_id'] = reference['reference_id']
        row['native_id'] = reference['native_id']
        row['cohort'], row['variant'], row['width'] = reference['cohort'], reference['variant'], reference['width']
        rows.append(row)
    assert len({r['reference_id'] for r in rows}) == len(rows)
    assert set(by_id) == {r['source_id'] for r in rows}
    return rows


def summarize_references(rows, enforce_design=True):
    groups = defaultdict(list)
    for row in rows:
        groups[row['cohort'], row['variant'], row['width']].append(row)
    expected = {(c, v, w) for c in COHORTS for v in ['M', 'U'] for w in [64, 128, 256]}
    if enforce_design:
        assert set(groups) == expected
    result = []
    for key in sorted(groups, key=lambda k: (COHORTS.index(k[0]), k[1], k[2])):
        group = groups[key]
        if enforce_design:
            assert len(group) == 9
            assert len({(r['policy_reference']['data_seed'], r['policy_reference']['seed']) for r in group}) == 9
            assert len({r['policy_reference']['data_seed'] for r in group}) == 3
        cell = summarize_profiles(group)
        cell.update(condition=dict(cohort=key[0], variant=key[1], width=key[2]),
            counting_unit='policy reference; reused inputs retained', native_checkpoints=len({r['native_id'] for r in group}),
            dataset_seeds=sorted({r['policy_reference']['data_seed'] for r in group}),
            model_weight_seeds=sorted({r['policy_reference']['seed'] for r in group}),
            original_policy_undefined_reasons=counts(r['context']['original_policy_reason'] for r in group if r['context']['original_p'] is None),
            original_p_defined=sum(r['context']['original_p'] is not None for r in group),
            canonical_zero_references=sum(r['context']['canonical_zero'] for r in group),
            original_at_upper_bound=sum(r['context']['original_at_upper_bound'] is True for r in group),
            original_at_lower_bound=sum(r['context']['original_at_lower_bound'] is True for r in group),
            context={field: decimal_stats([r['context'][field] for r in group]) for field in group[0]['context']
                     if field not in ['original_policy_reason', 'canonical_zero', 'clipping_applicable',
                                      'original_at_lower_bound', 'original_at_upper_bound']},
            source_ids=[r['source_id'] for r in group], reference_ids=[r['reference_id'] for r in group])
        result.append(cell)
    return result


def flatten(value, prefix=''):
    result = {}
    for key, item in value.items():
        label = f'{prefix}_{key}' if prefix else str(key)
        if isinstance(item, dict):
            result.update(flatten(item, label))
        elif isinstance(item, list):
            result[label] = json.dumps(item, allow_nan=False)
        else:
            result[label] = item
    return result


def csvwrite(path, rows):
    with path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(key for row in rows for key in row)))
        writer.writeheader()
        writer.writerows(rows)


def jsonlines(path, rows):
    with path.open('x', encoding='utf-8') as stream:
        for row in rows:
            stream.write(json.dumps(row, allow_nan=False) + '\n')


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
        ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows])


def figures(out, profiles, aliases, cells):
    mpl = ROOT / 'work/.matplotlib'
    mpl.mkdir(parents=True, exist_ok=True)
    os.environ['MPLCONFIGDIR'] = str(mpl)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.lines import Line2D
    plt.rcParams.update({'figure.dpi': 140, 'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False})
    evidence = {}

    def limits(ax, key, xs, ys):
        if xs:
            xlim, ylim = ax.get_xlim(), ax.get_ylim()
            assert all(xlim[0] <= x <= xlim[1] for x in xs), key
            assert all(ylim[0] <= y <= ylim[1] for y in ys), key
        evidence[key] = dict(points=len(xs), xlim=list(ax.get_xlim()), ylim=list(ax.get_ylim()))

    def scaled(ax, axis, values):
        if not values:
            return
        nonzero = [abs(v) for v in values if v]
        threshold = max(1e-300, 10. ** (math.floor(math.log10(min(nonzero))) - 1)) if nonzero else 1.
        getattr(ax, 'set_' + axis + 'scale')('symlog', linthresh=threshold)
        # Boundary ticks next to zero are redundant at this figure size.
        tick_getter, tick_setter = getattr(ax, 'get_' + axis + 'ticks'), getattr(ax, 'set_' + axis + 'ticks')
        ticks = [v for v in tick_getter() if v == 0 or abs(v) > threshold * 1.01]
        tick_setter(ticks)

    fig, axes = plt.subplots(2, 3, figsize=(15, 8), layout='constrained')
    x = np.arange(6)
    for i, cohort in enumerate(COHORTS):
        ax = axes.flat[i]
        group = [next(c for c in cells if c['condition'] == dict(cohort=cohort, variant=v, width=w))
                 for v in ['M', 'U'] for w in [64, 128, 256]]
        for j, name in enumerate(METHODS):
            points = [(k + (j - 1) * .12, c['methods'][name]['exact_argmin_agreement_rate_conditional'])
                      for k, c in enumerate(group) if c['methods'][name]['exact_argmin_agreement_rate_conditional'] is not None]
            if points:
                xx, yy = zip(*points)
                ax.scatter(xx, yy, color=COLORS[name], marker=['o', 'x', '+'][j], s=42, label=LABELS[name])
        for k, cell in enumerate(group):
            ax.text(k, .12, f"{cell['both_defined']}/9", ha='center', va='bottom', transform=ax.get_xaxis_transform(), fontsize=8)
        ax.set(title=COHORT_LABELS[i], ylabel='Exact grid-choice match / comparable', xticks=x,
               xticklabels=['M64', 'M128', 'M256', 'U64', 'U128', 'U256'], ylim=(-.06, 1.10), xlim=(-.5, 5.5))
        ax.set_yticks([0, .25, .5, .75, 1])
        ax.grid(axis='y', alpha=.18)
    fig.legend(handles=[Line2D([0], [0], color=COLORS[n], marker=['o', 'x', '+'][j], linestyle='', label=LABELS[n])
                        for j, n in enumerate(METHODS)], loc='outside lower center', ncol=3, frameon=False)
    fig.suptitle('All policy references: exact grid agreement conditional on availability; labels show comparable / 9\nPanel reuse repeats numerical inputs; these points are not independent dataset replications')
    fig.savefig(out / 'grid-agreement.png')
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), layout='constrained')
    for ax, name in zip(axes, METHODS):
        chosen = [p for p in profiles if p['both_defined']]
        xs = [float(p['reference']['top_two_gap']) for p in chosen]
        ys = [float(p['methods'][name]['error']['max_abs_error']) for p in chosen]
        ax.scatter(xs, ys, color=COLORS[name], s=17, alpha=.6)
        scaled(ax, 'x', xs)
        scaled(ax, 'y', ys)
        ax.set(title=f'{LABELS[name]}: {len(xs)} distinct inputs', xlabel='Reference top-two grid gap (symlog)',
               ylabel='Maximum absolute grid error (symlog)')
        ax.grid(alpha=.15)
        limits(ax, name, xs, ys)
    fig.suptitle('Every comparable numerical input; J64 error uses reference J, both D64 errors use reference D\nError size and the nearest grid gap have different meanings; original continuous estimates are retained')
    fig.savefig(out / 'contrast-errors.png')
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), layout='constrained')
    chosen = [p for p in profiles if p['original_point'] and p['gain_context']['absolute_total_over_absolute_mass'] is not None]
    xs = [float(p['gain_context']['absolute_total_over_absolute_mass']) for p in chosen]
    ys = [float(p['original_point']['signed_HP_gap_vs_grid_min']) for p in chosen]
    axes[0].scatter(xs, ys, s=18, alpha=.6, color='#70508b')
    scaled(axes[0], 'y', ys)
    axes[0].axhline(0, lw=.7, color='black')
    axes[0].set(title=f'Stored continuous point: {len(xs)} inputs', xlabel='|Signed total| / absolute gain mass',
                ylabel='Signed reference gap vs grid min (symlog)')
    limits(axes[0], 'point_gap', xs, ys)
    for variant, color in [('M', '#2374a6'), ('U', '#bf582f')]:
        chosen = [r for r in aliases if r['variant'] == variant]
        x1 = [r['context']['train_instance_accuracy'] for r in chosen]
        y1 = [r['context']['test_loss_gain'] for r in chosen]
        axes[1].scatter(x1, y1, s=14, alpha=.35, color=color, label=variant)
        selected = [r for r in chosen if r['context']['clipping_cumulative'] is not None and r['context']['original_objective'] is not None]
        x2 = [r['context']['clipping_cumulative'] for r in selected]
        y2 = [r['context']['original_objective'] for r in selected]
        axes[2].scatter(x2, y2, s=14, alpha=.35, color=color, label=variant)
    axes[1].axhline(0, lw=.7, color='black')
    axes[1].set(title=f'Historical losses: {len(aliases)} policy references', xlabel='Training instance-token accuracy',
                ylabel='Saved test NLL gain (initial - selected)')
    plotted = [r for r in aliases if r['context']['clipping_cumulative'] is not None and r['context']['original_objective'] is not None]
    scaled(axes[2], 'y', [r['context']['original_objective'] for r in plotted])
    axes[2].set(title=f'Clipping and original fit: {len(plotted)} references', xlabel='Saved cumulative clipping fraction',
                ylabel='Stored original fit objective (symlog)')
    axes[1].legend(frameon=False)
    axes[2].legend(frameon=False)
    for ax in axes:
        ax.grid(alpha=.15)
    limits(axes[1], 'memorization_test', [r['context']['train_instance_accuracy'] for r in aliases], [r['context']['test_loss_gain'] for r in aliases])
    limits(axes[2], 'clipping_fit', [r['context']['clipping_cumulative'] for r in plotted], [r['context']['original_objective'] for r in plotted])
    fig.suptitle('Preserved model context, without new selection or utility testing\nZero adaptation retains zero loss gains and undefined p*; unavailable clipping/fit coordinates are excluded only from that plot')
    fig.savefig(out / 'model-context.png')
    plt.close(fig)
    write(out / 'PLOT_CHECKS.json', dict(status='PASS', limits=evidence, visual_review='pending',
        all_available_points_shown=True, rounding_to_binary64_is_plot_only=True, policy_references_may_repeat_inputs=True,
        symlog_rule='Linear threshold is one decade below the smallest nonzero absolute plotted value; floor 1e-300; all-zero threshold 1; omit redundant threshold ticks.'))


def report(raw, out, profiles, aliases, cells, unique, alias_summary, audit, complete):
    text = '# Stage 9 v0.10 — objective precision on preserved model gains\n\n'
    text += f"Run `{raw.name}` audits **{len(aliases)} policy references**, **{len({r['native_id'] for r in aliases})} saved native checkpoints**, and **{len(profiles)} distinct weight/gain input pairs**. "
    text += 'Stage4 contributes its fixed epoch30 random-weight cohort; Stage5 and all four Stage6 panels contribute the previously selected capacity-specific R policies. All M/U variants, capacities, data seeds, model/weight seeds, selected zero-adaptation cases and mathematical guards are retained.\n\n'
    text += '## Measured numerical results\n\n'
    text += f"Independent audit: **{audit['status']}**. {unique['both_defined']} of {len(profiles)} distinct inputs have both objectives available; "
    text += f"{unique['domain_mismatches']} have differing legacy/reference eligibility and {unique['reference_classification_unresolved']} have unresolved reference classification. "
    text += 'The table counts distinct numerical inputs and preserves the comparable denominator.\n\n'
    text += table(['Method', 'Comparable', 'Exact argmin matches', 'Reference-band matches', 'Tied method minima', 'Any strict reversal'], [
        [LABELS[n], unique['methods'][n]['comparable'], unique['methods'][n]['exact_argmin_agreements'],
         unique['methods'][n]['reference_minset_agreements'], unique['methods'][n]['exact_minimum_tie_profiles'],
         unique['methods'][n]['any_strict_reversal_profiles']] for n in METHODS]) + '\n\n'
    text += 'Grid agreement measures fidelity of these objective evaluations to checked high-precision arithmetic. It does not validate the continuous search, identify a true exponent, establish a capacity peak, or improve adaptation utility. The original p*, K summaries, model selections and Stage6 failed utility gate remain unchanged.\n\n'
    text += '## Frozen inputs and arithmetic\n\n'
    text += 'The cohort is fixed from the original designs and validation decisions before these profiles were evaluated. Selection does not use p*, fit quality, test scores or visible peaks. Gains reproduce the historical operation order: subtract saved float32 initial/current per-sequence losses, then promote that float32 result to float64. Weights are the saved float32 assignments promoted exactly to binary64. Deduplication uses both exact weight and gain bytes; all policy aliases and their full losses remain separately recorded.\n\n'
    text += 'The fixed diagnostic grid contains 161 binary64 values i/20 from 0 to 8 with anchor 0. Legacy J64 follows the original objective arithmetic; naive D64 subtracts the anchor objective; factored D64 uses the declared algebraic contrast and accumulation. These methods share the historical Python-sum denominator. Decimal80 evaluates exact promoted inputs using high-precision sums, logs and exponentials; an independent Decimal110 implementation checks every eligible grid and stored-p point. Factoring changes both algebra and accumulation.\n\n'
    text += 'Frozen convergence bounds are 1e-50·max(1,|J110|) for J and 1e-50·max(1,max|D110|) for D. Ranking uses D80 with τ=2e-50·max(1,max|D80|). The first strict minimum index resolves method ties; reference-band membership permits D80≤min(D80)+τ. Reference-strict pairs have separation greater than τ. All exact ties, near ties, float ties, reversals and unresolved precision-boundary classifications are retained.\n\n'
    text += '## Cohort coverage and policy-reference counts\n\n'
    text += 'Each row has nine policy references from three data seeds × three model/weight seeds. Seeds on one corpus are paired runs, not independent dataset replications. Stage6 panels reuse selected checkpoints. These 36 cells are descriptive views with repeated inputs; the global numerical summary above deduplicates them.\n\n'
    text += table(['Cohort', 'Variant', 'Width', 'Distinct inputs /9', 'Both /9', 'Original p defined /9', 'Zero adaptation', 'Legacy exact/band', 'Naive exact/band', 'Factored exact/band'], [
        [c['condition']['cohort'], c['condition']['variant'], c['condition']['width'], c['unique_inputs'], c['both_defined'],
         c['original_p_defined'], c['canonical_zero_references']] +
        [f"{c['methods'][n]['exact_argmin_agreements']}/{c['methods'][n]['reference_minset_agreements']}" for n in METHODS] for c in cells]) + '\n\n'
    text += '![Grid agreement](grid-agreement.png)\n\n'
    text += 'Original policy reasons and mathematical guards remain separate. An epoch0 selection has historical reason `no_adaptation`; its exactly zero gain vector has mathematical reason `nonpositive_total_gain`. Neither becomes a measured p*=0. The historical guard includes constant weights (range below 1e-12) and total gain ≤1e-10, including tiny positive totals; these inputs remain undefined.\n\n'
    text += table(['Counting unit', 'Total', 'Comparable', 'Legacy undefined reasons', 'Reference undefined reasons'], [
        ['Distinct weight/gain pairs', unique['total'], unique['both_defined'], json.dumps(unique['legacy_undefined_reasons']), json.dumps(unique['hp_undefined_reasons'])],
        ['Policy references (reused inputs)', alias_summary['total'], alias_summary['both_defined'], json.dumps(alias_summary['legacy_undefined_reasons']), json.dumps(alias_summary['hp_undefined_reasons'])]]) + '\n\n'
    text += '## Errors, regret and continuous-point diagnostics\n\n'
    text += table(['Method', 'Max absolute grid error', 'Max grid regret', 'Max regret beyond τ', 'Max error / reference span'], [
        [LABELS[n], fmt(unique['methods'][n]['error']['max_abs_error']['conditional_maximum']),
         fmt(unique['methods'][n]['reference_regret']['conditional_maximum']),
         fmt(unique['methods'][n]['reference_regret_excess_over_tau']['conditional_maximum']),
         fmt(unique['methods'][n]['error']['relative_to_contrast_span']['conditional_maximum'])] for n in METHODS]) + '\n\n'
    text += 'Binary64 errors are computed after exact Decimal.from_float promotion; all differences and summaries use precision110 and retain Decimal strings. Error is also normalized by max(1,max|D80|) and the reference contrast span. Span-normalized values are undefined for zero span. Conditional summaries display available inputs; unconditional means are null whenever any required value is undefined. No imputation or fit-quality exclusion is applied.\n\n'
    text += '![Contrast errors](contrast-errors.png)\n\n'
    text += f"The stored continuous point is available for {unique['original_point_signed_gap']['defined']} distinct inputs, of which {unique['original_point_below_grid_count']} lie below the finite grid minimum in reference contrast. "
    text += 'Its signed gap can be negative and it is never inserted into the grid candidate set. This diagnostic cannot certify a continuous optimum or establish recovery. Raw grid regret is nonnegative; regret beyond τ is max(0,regret−τ). A small objective error alone cannot certify ranking when the relevant separation is smaller.\n\n'
    text += '## Preserved model context\n\n'
    text += 'The table reports historical saved metrics, with positive NLL gain meaning lower selected loss. Training instance-token accuracy describes memorization; it is distinct from held-out utility. Clipping is undefined when no training updates were selected. Original upper/lower-bound flags and objective values remain unchanged.\n\n'
    text += table(['Cohort', 'Variant', 'Width', 'Mean train NLL gain', 'Mean validation NLL gain', 'Mean test NLL gain', 'Mean train instance accuracy', 'Mean clipping (available)', 'Original lower/upper bounds'], [
        [c['condition']['cohort'], c['condition']['variant'], c['condition']['width']] +
        [fmt(c['context'][f]['conditional_mean']) for f in ['train_loss_gain', 'validation_loss_gain', 'test_loss_gain', 'train_instance_accuracy', 'clipping_cumulative']] +
        [f"{c['original_at_lower_bound']}/{c['original_at_upper_bound']}"] for c in cells]) + '\n\n'
    text += '![Model context](model-context.png)\n\n'
    text += 'Every policy-reference record preserves the complete selected and initial loss/accuracy histories, original fit metadata, selection decision and source paths. Signed total, positive/negative mass, absolute mass, cancellation ratio, negative/zero-gain fractions and legacy/fsum totals are stored alongside the numerical diagnostics. Historical Torch reductions need not equal Python sequential sums; their distinct values are preserved.\n\n'
    text += '## Interpretation limits and provenance\n\n'
    text += 'This bounded CPU audit uses previously saved arrays; it performs no model training, inference, new continuous optimization, validation retuning, p* replacement, K recomputation or utility-gate revision. Agreement on these arrays cannot show that a peak is causal, rule out sampling or optimization effects, rescue the failed Stage6 usefulness result, or imply exact large-LM replication. Three capacities cannot establish movement between two interior peaks. One Pythia size/seed does not establish a scaling curve. No novelty or publication claim is made.\n\n'
    text += 'The saved loss arrays, full token/label data, pairing records, selected decisions and original files are hashed and audited. Missing historical intermediate model binaries are not regenerated; this is an audit of retained arrays. Original sources and records remain immutable. Each precision phase records runtime/memory and has its preregistered CPU budget.\n\n'
    text += f"Protocol SHA256: `{sha(HERE / 'PROTOCOL_STAGE9.md')}`. Raw profiles SHA256: `{sha(raw / 'profiles.jsonl')}`. "
    text += 'The archive includes frozen source, copied input provenance, full 80/110-digit profiles, guard failures, classification evidence, fixtures, all analysis tables and figures. Archive CRC and SHA256 are verified. Visual inspection is recorded separately.\n\n'
    text += 'Completion record:\n\n```json\n' + json.dumps(complete, indent=2, allow_nan=False) + '\n```\n'
    (out / 'REPORT.md').write_text(text, encoding='utf-8')


def main():
    started, wall = time.perf_counter(), datetime.now(timezone.utc)
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id and args.run_id not in ['.', '..'] and '/' not in args.run_id and '\\' not in args.run_id
    raw = ROOT / 'work/runs' / args.run_id
    out = HERE / f'results-{args.run_id}'
    assert not out.exists(), 'Preserve completed or partial analysis'
    complete, audit = read(raw / 'COMPLETE.json'), read(raw / 'AUDIT.json')
    assert complete['status'] == 'COMPLETE' and audit['status'] == 'PASS'
    verify_source(raw)
    verify_inputs(raw)
    source = read(raw / 'source_manifest.json')
    assert audit['source_sha256'] == source
    assert sha(raw / 'profiles.jsonl') == complete['profiles_sha256'] == audit['profiles_sha256']
    classifications_file = raw / audit['classification_evidence_file']
    assert classifications_file.resolve().parent == raw.resolve()
    assert sha(classifications_file) == audit['classification_evidence_sha256']
    classifications = read(classifications_file)['cases']
    by_id = {c['source_id']: c for c in classifications}
    assert sha(raw / 'audit_profile_manifest.json') == audit['audit_profile_manifest_sha256']
    audit_manifest = read(raw / 'audit_profile_manifest.json')
    assert set(audit_manifest) == {f'audit_profiles/{key}.json' for key in by_id}
    assert set(audit_manifest) == {p.relative_to(raw).as_posix() for p in (raw / 'audit_profiles').iterdir() if p.is_file()}
    for path, digest in audit_manifest.items():
        assert sha(raw / path) == digest
        independent = read(raw / path)
        key = independent['source_id']
        assert path == f'audit_profiles/{key}.json' and independent['hp_dps'] == 110
        assert independent['classification'] == by_id[key]
    rows = [json.loads(line) for line in (raw / 'profiles.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    references = read(raw / 'inputs/references.json')
    config = read(raw / 'config.json')
    grid = config['grid']
    assert grid == [i / 20 for i in range(161)]
    assert len(rows) == len(by_id) == 186 and len(references) == 324
    assert {r['source_id'] for r in rows} == set(by_id)
    out.mkdir()
    try:
        import numpy as np
        profiles, gain_contexts = [], {}
        for row in rows:
            p = profile_metrics(row, grid, by_id[row['source_id']])
            for key in ['source_array_index', 'block_id', 'replicate', 'generator_p', 'c', 'truth_p', 'seed_weights', 'seed_noise']:
                p.pop(key, None)
            with np.load(raw / 'inputs/arrays' / (row['source_id'] + '.npz')) as arrays:
                gain_contexts[row['source_id']] = signed_context(arrays['gains'])
            p['gain_context'] = gain_contexts[row['source_id']]
            profiles.append(p)
        assert sum(p['reference_classification_unresolved'] for p in profiles) == audit['unresolved_reference_count']
        aliases = join_references(references, profiles, gain_contexts)
        assert len({r['native_id'] for r in aliases}) == 207
        cells = summarize_references(aliases)
        unique, alias_summary = summarize_profiles(profiles), summarize_profiles(aliases)
        jsonlines(out / 'profile-metrics.jsonl', profiles)
        jsonlines(out / 'policy-reference-metrics.jsonl', aliases)
        csvwrite(out / 'profile-metrics.csv', [flatten(p) for p in profiles])
        # Full histories/configs remain in JSONL; this CSV is the compact human-auditable join.
        csvwrite(out / 'policy-reference-metrics.csv', [flatten({k: v for k, v in r.items() if k != 'policy_reference'}) for r in aliases])
        write(out / 'summaries.json', dict(counting_units='Global unique input pairs and policy aliases are separate; grid pairs and reused panels are not IID trials',
            unique_inputs=unique, policy_references=alias_summary, cells=cells))
        csvwrite(out / 'summaries.csv', [flatten(c) for c in cells])
        write(out / 'SUMMARY_AUDIT.json', dict(status='PASS', utc=utc(), profiles=len(profiles), policy_references=len(aliases),
            native_checkpoints=207, cells=len(cells), grid_points=len(grid), grid_pairs_per_profile=len(grid) * (len(grid) - 1) // 2,
            original_p_preserved=True, decimal_calculation_precision=PRECISION,
            classification_unresolved=unique['reference_classification_unresolved'], no_filter_or_replacement=True))
        figures(out, profiles, aliases, cells)
        report(raw, out, profiles, aliases, cells, unique, alias_summary, audit, complete)
        for name in source:
            shutil.copy2(raw / 'source' / name, out / name)
        shutil.copy2(raw / 'AUDIT.json', out / 'AUDIT.json')
        write(out / 'analysis-provenance.json', dict(utc=utc(), source_sha256=source,
            profiles_sha256=audit['profiles_sha256'], classification_evidence_sha256=audit['classification_evidence_sha256'],
            audit_profile_manifest_sha256=audit['audit_profile_manifest_sha256'], independently_saved_110_profiles_verified=len(audit_manifest), visual_review='pending'))
        write(out / 'ANALYSIS_RUNTIME.json', dict(utc=utc(), pre_archive_elapsed_seconds=time.perf_counter() - started,
            pre_archive_utc_elapsed_seconds=(datetime.now(timezone.utc) - wall).total_seconds(),
            peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, full_runtime_location='ARCHIVE_CHECK.json'))
        manifest = {p.relative_to(raw).as_posix(): sha(p) for p in sorted(raw.rglob('*')) if p.is_file()}
        write(out / 'raw-manifest.json', manifest)
        archive = out / 'run-records.zip'
        with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for path in sorted(raw.rglob('*')):
                if path.is_file():
                    z.write(path, 'raw/' + path.relative_to(raw).as_posix())
            for path in sorted(out.iterdir()):
                if path.is_file() and path != archive:
                    z.write(path, 'report/' + path.name)
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
        write(out / 'ARCHIVE_CHECK.json', dict(status='PASS', crc='PASS', utc=utc(), sha256=sha(archive), bytes=archive.stat().st_size,
            raw_files=len(manifest), analysis_elapsed_seconds=time.perf_counter() - started,
            analysis_utc_elapsed_seconds=(datetime.now(timezone.utc) - wall).total_seconds(),
            peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024))
        print(json.dumps(dict(output=str(out), profiles=len(profiles), references=len(aliases), cells=len(cells), audit='PASS', archive='PASS')), flush=True)
    except BaseException as exc:
        write(out / 'ANALYSIS_FAILURE.json', dict(status='FAILED', utc=utc(), error=repr(exc), traceback=traceback.format_exc(),
            instruction='Preserve partial analysis; source changes require a separately versioned repair.'))
        raise


if __name__ == '__main__':
    main()
