"""Outcome-independent Stage10 analysis fixtures, including rendered partial reports."""
import argparse
import copy
import json
import sys
from decimal import Decimal, localcontext
from pathlib import Path
sys.dont_write_bytecode = True
from analyze_stage10 import (COHORTS, FLAGS, VALUE_FIELDS, materialize, summarize, join_context,
    cells_for, decimal_stats, flatten, figures, report, jsonlines, csvwrite)
from common_stage10 import ROOT, HERE, SOURCES, sha, read, write, utc


def fixture_design():
    """Literal synthetic cohort design; never reads saved model data or Stage10 results."""
    planned = []
    for i in range(186):
        guard = 'nonpositive_total_gain' if i < 6 else 'constant_weights' if i == 6 else None
        planned.append(dict(source_id=f'synthetic-input-{i:03}', n=512, weightgroup=f'synthetic-weights-{i % 9}',
            original_p=None if guard else .25, original_objective=None if guard else .01,
            original_reason='no_adaptation' if i < 6 else guard, expected_guard=guard,
            reference_ids=[], native_ids=[]))
    refs, historical = [], []
    for cohort in COHORTS:
        for variant in ['M', 'U']:
            for width in [64, 128, 256]:
                for data_seed in [101, 102, 103]:
                    for seed in [201, 202, 203]:
                        k = len(refs)
                        meta = planned[k % 186]
                        native = f'synthetic-native-{k % 207:03}'
                        ref = dict(reference_id=f'synthetic-reference-{k:03}', source_id=meta['source_id'],
                            profile_id=meta['source_id'], native_id=native, cohort=cohort, variant=variant,
                            width=width, data_seed=data_seed, seed=seed, synthetic=True)
                        refs.append(ref)
                        meta['reference_ids'].append(ref['reference_id'])
                        if native not in meta['native_ids']:
                            meta['native_ids'].append(native)
                        initial_missing = cohort == 'S4_fixed30'
                        guard = meta['expected_guard'] is not None
                        context = dict(train_loss=1., train_initial_loss=2., train_loss_gain=1.,
                            validation_loss=1.75, validation_initial_loss=2., validation_loss_gain=.25,
                            test_loss=2.25, test_initial_loss=None if initial_missing else 2.,
                            test_loss_gain=None if initial_missing else -.25,
                            train_instance_accuracy=.75, train_instance_accuracy_gain=.5,
                            clipping_cumulative=None if guard else .5, clipping_applicable=not guard,
                            canonical_zero=meta['original_reason'] == 'no_adaptation',
                            original_p=meta['original_p'], original_objective=meta['original_objective'],
                            original_policy_reason=meta['original_reason'],
                            original_at_lower_bound=False if not guard else None,
                            original_at_upper_bound=False if not guard else None,
                            signed_total_exact='0' if guard else '3', negative_mass_magnitude='1',
                            signed_total_over_absolute_mass=None if guard else '.6')
                        for part in ['shared', 'group', 'instance']:
                            context.update({f'test_{part}_loss': 2., f'test_{part}_accuracy': .25,
                                f'test_{part}_initial_loss': None if initial_missing else 2.25,
                                f'test_{part}_loss_gain': None if initial_missing else .25,
                                f'test_{part}_initial_accuracy': None if initial_missing else .125,
                                f'test_{part}_accuracy_gain': None if initial_missing else .125})
                        historical.append(dict(reference_id=ref['reference_id'], source_id=meta['source_id'],
                            policy_reference=copy.deepcopy(ref), context=context))
    return planned, refs, historical


def observed_row(metadata, i):
    flags = {field: None for field in FLAGS}
    flags.update(unresolved=False, reasons=[])
    row = dict(copy.deepcopy(metadata), primary_reason=metadata['expected_guard'],
        reference_reason=metadata['expected_guard'], status='guard', classification=flags,
        values=None, neighborhood=[], elapsed_seconds=.01)
    if metadata['expected_guard'] is not None:
        return row
    flags.update(precision_converged=True, search_objective_agreement=True, parameter_agreement=True,
        original_objective_agreement=True, original_parameter_agreement=True,
        original_better_than_search=False, weak_neighborhood=False)
    sign = -1 if i % 2 else 1
    row.update(status='compared', values=dict(primary_p='.25000000000001', reference_p='.25', original_p_exact='.25',
        J_primary_110='.010000000000000000000001', J_reference_110='.01', J_original_110='.01',
        search_signed_gap=str(Decimal(sign) * Decimal('1e-24')), original_signed_gap='0',
        search_parameter_delta=str(Decimal(sign) * Decimal('1e-14')), original_parameter_delta='0',
        reference_mesh_span='.3', search_objective_tolerance='1e-18', original_objective_tolerance='1e-12',
        parameter_tolerance='1e-6'), neighborhood=[dict(p='.251', J='.0100001', signed_gap='.0000001')])
    # Deliberately exercise each unresolved reporting path without invoking any search.
    if i == 13:
        flags.update(original_better_than_search=True, original_objective_agreement=False,
            unresolved=True, reasons=['original_better_than_search'])
        row['values']['original_signed_gap'] = '-1e-10'
    elif i == 14:
        flags.update(search_objective_agreement=False, unresolved=True, reasons=['search_objective_disagreement'])
        row['values']['search_signed_gap'] = '-1e-8'
    elif i == 15:
        flags.update(precision_converged=False, unresolved=True, reasons=['precision_not_converged'])
    elif i == 16:
        flags.update({field: None for field in FLAGS})
        flags.update(unresolved=True, reasons=['domain_mismatch'])
        row.update(reference_reason='nonpositive_total_gain', values=None)
    if flags['unresolved']:
        row['status'] = 'unresolved'
    return row


def rejects(callback):
    try:
        callback()
    except (AssertionError, KeyError):
        return
    raise AssertionError('Malformed input unexpectedly accepted')


def checks(directory):
    directory.mkdir(parents=True)
    planned, refs, historical = fixture_design()
    original = copy.deepcopy((planned, refs, historical))
    observed = [observed_row(meta, i) for i, meta in enumerate(planned)]
    rows = materialize(planned, observed, 'COMPLETE')
    aliases = join_context(rows, refs, historical)
    cells = cells_for(aliases)
    unique, alias_summary = summarize(rows), summarize(aliases)
    assert len(rows) == 186 and len(aliases) == 324 and len(cells) == 36
    assert len({r['native_id'] for r in aliases}) == 207
    assert unique['status_counts'] == dict(compared=175, guard=7, unresolved=4, not_run=0)
    assert unique['original_defined'] == 179
    assert unique['expected_guard_reasons'] == {'nonpositive_total_gain': 6, 'constant_weights': 1}
    assert unique['original_undefined_reasons'] == {'no_adaptation': 6, 'constant_weights': 1}
    assert unique['classification']['unresolved']['available'] == 186
    assert unique['classification']['precision_converged']['available'] == 178
    assert unique['classification']['precision_converged']['false'] == 1
    assert unique['classification']['precision_converged']['unconditional_true_rate'] is None
    assert unique['values']['original_signed_gap']['negative'] == 1
    assert unique['values']['original_signed_gap']['zero'] == 177
    assert unique['values']['original_signed_gap']['unconditional_mean'] is None
    assert alias_summary['total'] == 324 and alias_summary['unique_inputs'] == 186
    assert sum(c['total'] for c in cells) == 324
    assert all(c['total'] == 9 and len(c['dataset_seeds']) == 3 and len(c['model_weight_seeds']) == 3 for c in cells)
    assert sum(a['context']['test_loss'] is not None for a in aliases) == 324
    assert sum(a['context']['test_loss_gain'] is None for a in aliases) == 54
    for cell in cells:
        initial_missing = cell['condition']['cohort'] == 'S4_fixed30'
        context = cell['historical_context']
        assert context['test_loss']['defined'] == 9
        assert context['test_initial_loss']['undefined'] == (9 if initial_missing else 0)
        assert context['test_loss_gain']['defined'] == (0 if initial_missing else 9)
        assert context['test_loss_gain']['unconditional_mean'] == (None if initial_missing else '-0.25')
        for part in ['shared', 'group', 'instance']:
            for suffix in ['initial_loss', 'loss_gain', 'initial_accuracy', 'accuracy_gain']:
                assert context[f'test_{part}_{suffix}']['undefined'] == (9 if initial_missing else 0)
        assert context['train_loss_gain']['unconditional_mean'] == '1'
        assert context['validation_loss_gain']['unconditional_mean'] == '0.25'
    assert (planned, refs, historical) == original, 'Joins must not mutate saved histories or planned metadata'
    assert all(row['global_optimality_certified'] is False for row in rows + aliases)

    partial = materialize(planned, observed[:-6], 'BUDGET_EXHAUSTED')
    partial_aliases = join_context(partial, refs, historical)
    partial_cells = cells_for(partial_aliases)
    ps = summarize(partial)
    assert ps['status_counts']['not_run'] == 6
    assert ps['classification']['unresolved']['true'] == 10
    assert ps['unresolved_reasons']['not_run_after_BUDGET_EXHAUSTED'] == 6
    assert len(partial_aliases) == 324 and len(partial_cells) == 36
    assert all(row['values'] is None for row in partial if row['status'] == 'not_run')
    assert sum(row['context']['test_loss_gain'] is None for row in partial_aliases) == 54
    missing_aliases = [row for row in partial_aliases if row['status'] == 'not_run']
    assert len(missing_aliases) == 6 and all(row['context']['test_loss'] is not None for row in missing_aliases)
    empty = materialize(planned, [], 'FAILED')
    empty_aliases = join_context(empty, refs, historical)
    es = summarize(empty)
    assert es['status_counts']['not_run'] == 186
    assert es['classification']['search_objective_agreement']['available'] == 0
    assert es['classification']['search_objective_agreement']['conditional_true_rate'] is None
    assert es['values']['reference_p']['defined'] == 0
    assert es['values']['reference_p']['conditional_mean'] is None
    assert len(empty_aliases) == 324 and len(cells_for(empty_aliases)) == 36

    with localcontext() as ctx:
        ctx.prec = 110
        high = '1.0000000000000000000000000000000000000000000000000000000000001'
        tiny = decimal_stats([high, '1', None])
        assert Decimal(tiny['conditional_mean']) > 1 and Decimal(tiny['conditional_sd']) > 0
        assert tiny['unconditional_mean'] is None and tiny['defined'] == 2 and tiny['total'] == 3
        signed = decimal_stats(['-2e-80', '1e-80', None])
        assert Decimal(signed['conditional_mean']) == Decimal('-5e-81')
        assert Decimal(signed['conditional_median']) == Decimal('-5e-81')
    assert decimal_stats([])['unconditional_mean'] is None
    assert decimal_stats([None])['conditional_mean'] is None
    assert decimal_stats(['1'])['conditional_sd'] is None
    assert decimal_stats(['1', '1'])['conditional_sd'] == '0'

    rejects(lambda: materialize(planned, observed + [observed[0]], 'COMPLETE'))
    unknown = copy.deepcopy(observed[0]); unknown['source_id'] = 'unplanned'
    rejects(lambda: materialize(planned, [unknown], 'FAILED'))
    invalid = copy.deepcopy(observed[7]); invalid['classification']['unresolved'] = 0
    rejects(lambda: materialize(planned, [invalid], 'FAILED'))
    invalid = copy.deepcopy(observed[7]); del invalid['values']['search_signed_gap']
    rejects(lambda: materialize(planned, [invalid], 'FAILED'))
    invalid = copy.deepcopy(observed[7]); invalid['original_p'] = .5
    rejects(lambda: materialize(planned, [invalid], 'FAILED'))
    bad_history = copy.deepcopy(historical); bad_history[0]['policy_reference']['seed'] = -1
    rejects(lambda: join_context(rows, refs, bad_history))
    rejects(lambda: cells_for(aliases[:-1]))

    jsonlines(directory / 'synthetic-inputs.jsonl', partial)
    csvwrite(directory / 'synthetic-inputs.csv', [flatten(row) for row in partial])
    write(directory / 'synthetic-summaries.json', dict(unique=ps, aliases=summarize(partial_aliases), cells=partial_cells))
    figure_checks = {}
    for name, fr, fc in [('partial', partial, partial_cells), ('empty', empty, cells_for(empty_aliases))]:
        target = directory / name; target.mkdir()
        figures(target, fr, fc)
        evidence = read(target / 'PLOT_CHECKS.json')
        assert evidence['status'] == 'PASS' and evidence['all_available_points_shown']
        for field in ['search_signed_gap', 'original_signed_gap', 'search_parameter_delta', 'original_parameter_delta']:
            item = evidence['data_limits'][field]
            assert item['points'] + item['unavailable'] == 186
            assert item['points'] == sum((r.get('values') or {}).get(field) is not None for r in fr)
            if 'parameter' in field:
                assert item['tolerance_lines'] == [-1e-6, 1e-6]
                assert item['ylim'][0] < -1e-6 and item['ylim'][1] > 1e-6
                assert max(abs(v) for v in item['ylim']) < .01, 'Tick locator must not expand scientific data bounds'
        assert evidence['data_limits']['cohort_coverage']['references'] == 324
        figure_checks[name] = evidence
    # Exercise the report path with missing comparisons and null historical test metrics.
    raw = directory / 'synthetic-raw'; raw.mkdir()
    jsonlines(raw / 'results.jsonl', observed[:-6])
    report(raw, directory / 'partial', ps, summarize(partial_aliases), partial_cells,
        dict(status='BUDGET_EXHAUSTED', elapsed_seconds=3600., utc_elapsed_seconds=3600.), dict(status='PARTIAL'))
    text = (directory / 'partial/REPORT.md').read_text(encoding='utf-8')
    assert 'width 1e-12' in text and 'width 1e-10' not in text
    assert 'BUDGET_EXHAUSTED' in text and 'Neither search provides a global-optimality certificate.' in text
    assert '270/324 test gains' in text
    (directory / 'partial/REPORT.md').write_text('# SYNTHETIC FIXTURE — NOT MEASURED RESULTS\n\n' + text, encoding='utf-8')
    json.dumps([unique, alias_summary, cells, ps, partial_aliases, es], allow_nan=False)
    return dict(status='PASS', utc=utc(), measured_outcomes_read=False,
        synthetic_fixture_directory=directory.relative_to(ROOT).as_posix(),
        checks=['186 planned inputs, 207 synthetic native checkpoints, 324 aliases and all 36 nine-reference cells retained',
            'guard reasons remain distinct from historical no_adaptation; undefined values remain null',
            'signed negative objective gaps and parameter deltas survive aggregation',
            'precision, objective, parameter and unresolved classifications have separate availability denominators',
            'partial and empty runs retain every planned input and full historical context',
            'all 54 Stage4 initial-test metrics and gains remain null; all 324 selected-test metrics retained',
            'Decimal110 summaries preserve differences below binary64 resolution and signed tiny gaps',
            'duplicate, unplanned, malformed, changed-original and mismatched full-reference records rejected',
            'synthetic complete/partial/no-comparison summaries serialize without NaN or fabricated zeros',
            'six synthetic figures rendered with full point coverage, bounded axes and both signed parameter tolerances',
            'full partial-report path accepts missing numerical comparisons and unavailable test gain'],
        figure_checks=figure_checks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    assert output.is_relative_to(ROOT) and not output.exists(), 'Keep create-only fixture evidence in the project'
    output.parent.mkdir(parents=True, exist_ok=True)
    directory = output.parent / (output.stem + '-fixtures')
    assert not directory.exists(), 'Preserve prior fixtures'
    result = checks(directory)
    result['source_sha256'] = {name: sha(HERE / name) for name in SOURCES}
    write(output, result)
    print(json.dumps(dict(status=result['status'], output=str(output), checks=len(result['checks']),
        synthetic_fixture_directory=result['synthetic_fixture_directory'])), flush=True)


if __name__ == '__main__':
    main()
