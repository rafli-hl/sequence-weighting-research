"""Outcome-independent numerical-summary and policy-alias fixtures for Stage9."""
import argparse
import copy
import json
from decimal import Decimal, localcontext
from pathlib import Path
from analyze_stage9 import (HERE, sha, utc, write, profile_metrics, summarize_profiles,
    summarize_references, signed_context, context, join_references, decimal_stats)
from metrics import d64


def profile(identifier='fixture-positive'):
    return dict(source_id=identifier, n=3, weights_sha256='fixture', gains_sha256=identifier,
        original_p=.075, original_reason=None, original_objective=1., legacy_reason=None, hp_reason=None,
        total_gain_legacy=3., total_gain_fsum=3., total_gain_hp='3', hp_dps=80, hp_identity_max_abs_error='0',
        legacy_J=[3., 2., 1.], naive_D64=[0., -1., -2.], stable_D64=[0., 1., 2.], hp_J=['0', '1', '2'], hp_D=['0', '1', '2'],
        original_point=dict(p=.075, legacy_J=1., naive_D64=-2., stable_D64=-.1, hp_J='-.1', hp_D='-.1'))


def reference(identifier, source, seed, zero=False):
    splits = {split: dict(loss=2., **{part: dict(loss=2., accuracy=.25)
        for part in ['shared', 'group', 'instance']}) for split in ['train', 'validation', 'test']}
    initial = dict(epoch=0, **copy.deepcopy(splits), p_star=dict(p=None, reason='no_adaptation'),
                   total_gain=0., negative_gain_fraction=0.)
    current = copy.deepcopy(initial)
    fit = dict(p=None, reason='no_adaptation') if zero else dict(p=.075, objective=1., at_lower_bound=False, at_upper_bound=False)
    if not zero:
        current.update(epoch=3, p_star=fit, total_gain=3., negative_gain_fraction=0., clipping_cumulative=.5,
                       gradient_clip_fraction=.25, gradient_norm_mean=1., gradient_norm_max=2.)
        current['train']['loss'] = 1.
        current['validation']['loss'] = 1.5
        current['test']['loss'] = 2.25
        current['train']['instance']['accuracy'] = .75
    return dict(reference_id=identifier, source_id=source, profile_id=source, native_id=identifier,
        cohort='S5_R', variant='M', width=64, data_seed=1, seed=seed, epoch=0 if zero else 3,
        canonical_zero=zero, history=current, initial_history=initial, original_fit=fit,
        config={}, decision={}, source_paths={})


def checks():
    grid = [0., .05, .1]
    m = profile_metrics(profile(), grid)
    assert m['reference']['argmin_index'] == 0
    assert m['methods']['legacy_J']['argmin_index'] == 2
    assert m['methods']['legacy_J']['pairwise']['strict_reversals'] == 3
    assert m['methods']['stable_D64']['pairwise']['strict_agreements'] == 3
    assert m['methods']['legacy_J']['reference_regret'] == '2'
    assert m['original_point']['signed_HP_gap_vs_grid_min'] == '-0.1'
    assert m['original_point']['lower_than_grid_min']
    with localcontext() as ctx:
        ctx.prec = 110
        tied = profile('fixture-tied')
        tied.update(legacy_J=[1e20] * 3, naive_D64=[0.] * 3, stable_D64=[0., -1e-30, -2e-30],
            hp_J=[str(Decimal('1e20') - Decimal(i) * Decimal('1e-30')) for i in range(3)],
            hp_D=['0', '-1e-30', '-2e-30'], original_p=None, original_point=None)
        tm = profile_metrics(tied, grid)
        assert tm['reference']['argmin_index'] == 2
        assert tm['methods']['legacy_J']['exact_minimum_count'] == 3
        assert tm['methods']['legacy_J']['pairwise']['float_ties_against_reference_strict'] == 3
        assert Decimal(tm['methods']['legacy_J']['error']['max_abs_error']) == Decimal('2e-30')
        assert tm['methods']['stable_D64']['exact_argmin_agreement']
        assert not tm['methods']['legacy_J']['reference_minset_agreement']
    near = profile('fixture-near')
    near.update(hp_D=['0', '1e-51', '1'], hp_J=['0', '1e-51', '1'], legacy_J=[0., 0., 1.],
                naive_D64=[0., -1e-51, 1.], stable_D64=[0., 1e-51, 1.], original_p=None, original_point=None)
    nm = profile_metrics(near, grid, dict(source_id=near['source_id'], unresolved=True))
    assert nm['reference']['minimum_set_indices'] == [0, 1]
    assert nm['pairwise']['reference_nonexact_near_ties'] == 1
    assert nm['pairwise']['reference_strict_pairs'] == 2
    assert not nm['methods']['naive_D64']['exact_argmin_agreement'] and nm['methods']['naive_D64']['reference_minset_agreement']
    assert Decimal(nm['methods']['naive_D64']['reference_regret_excess_over_tau']) == 0
    assert nm['reference_classification_unresolved']
    flat = profile('fixture-flat')
    flat.update(hp_D=['0', '0', '0'], hp_J=['1', '1', '1'], legacy_J=[1.] * 3,
                naive_D64=[0.] * 3, stable_D64=[0.] * 3, original_p=None, original_point=None)
    fm = profile_metrics(flat, grid)
    assert fm['reference']['exact_minimum_count'] == 3 and fm['pairwise']['reference_exact_ties'] == 3
    assert fm['methods']['legacy_J']['error']['relative_to_contrast_span'] is None
    undefined = profile('fixture-zero')
    undefined.update(legacy_reason='nonpositive_total_gain', hp_reason='nonpositive_total_gain', original_reason='no_adaptation',
        total_gain_legacy=0., total_gain_fsum=0., total_gain_hp='0', legacy_J=None, naive_D64=None,
        stable_D64=None, hp_J=None, hp_D=None, original_p=None, original_objective=None, original_point=None)
    missing = profile_metrics(undefined, grid)
    assert not missing['both_defined'] and missing['reference'] is None
    assert missing['methods']['legacy_J']['reference_regret'] is None
    assert missing['normalization_difference']['legacy_relative_to_hp'] is None
    unique = summarize_profiles([m, missing])
    assert unique['total'] == unique['unique_inputs'] == 2 and unique['both_defined'] == 1
    assert unique['methods']['legacy_J']['reference_regret']['conditional_mean'] == '2'
    assert unique['methods']['legacy_J']['reference_regret']['unconditional_mean'] is None
    domain = copy.deepcopy(undefined)
    domain.update(hp_reason=None, hp_J=['0', '1', '2'], hp_D=['0', '1', '2'])
    dm = profile_metrics(domain, grid)
    assert dm['domain_mismatch'] and dm['reference_defined'] and not dm['legacy_defined']
    assert d64(.1) != Decimal('.1')
    tiny = decimal_stats(['1.0000000000000000000000000000000000000000000000000000000000001', '1'])
    assert Decimal(tiny['conditional_mean']) > 1 and Decimal(tiny['conditional_sd']) > 0
    gain_contexts = {'fixture-positive': signed_context([2., -1., 2.]), 'fixture-zero': signed_context([0., 0., 0.])}
    assert gain_contexts['fixture-positive']['signed_total_exact'] == '3'
    assert gain_contexts['fixture-positive']['positive_mass'] == '4'
    assert gain_contexts['fixture-positive']['negative_mass_magnitude'] == '1'
    assert gain_contexts['fixture-positive']['absolute_total_over_absolute_mass'] == '0.6'
    assert gain_contexts['fixture-positive']['signed_total_over_absolute_mass'] == '0.6'
    assert gain_contexts['fixture-zero']['absolute_total_over_absolute_mass'] is None
    negative = signed_context([-2., 1., -2.])
    assert negative['signed_total_exact'] == '-3'
    assert negative['signed_total_over_absolute_mass'] == '-0.6'
    assert negative['absolute_total_over_absolute_mass'] == '0.6'
    refs = [reference('alias-a', 'fixture-positive', 1), reference('alias-b', 'fixture-positive', 2),
            reference('alias-zero', 'fixture-zero', 3, zero=True)]
    aliases = join_references(refs, [m, missing], gain_contexts)
    alias_summary = summarize_profiles(aliases)
    assert alias_summary['total'] == 3 and alias_summary['unique_inputs'] == 2 and alias_summary['both_defined'] == 2
    assert alias_summary['methods']['legacy_J']['exact_argmin_agreements'] == 0
    assert alias_summary['methods']['stable_D64']['exact_argmin_agreements'] == 2
    cells = summarize_references(aliases, enforce_design=False)
    assert len(cells) == 1 and cells[0]['native_checkpoints'] == 3
    assert cells[0]['original_policy_undefined_reasons'] == {'no_adaptation': 1}
    assert cells[0]['legacy_undefined_reasons'] == {'nonpositive_total_gain': 1}
    assert cells[0]['context']['original_p']['defined'] == 2 and cells[0]['context']['original_p']['undefined'] == 1
    assert cells[0]['context']['original_p']['unconditional_mean'] is None
    assert aliases[0]['context']['train_loss_gain'] == 1.
    assert aliases[0]['context']['test_loss_gain'] == -.25
    assert aliases[0]['context']['train_instance_accuracy_gain'] == .5
    assert aliases[2]['context']['test_loss_gain'] == 0. and aliases[2]['context']['clipping_cumulative'] is None
    assert not aliases[2]['context']['clipping_applicable'] and aliases[2]['context']['original_p'] is None
    assert aliases[0]['policy_reference']['original_fit'] == refs[0]['original_fit']
    assert aliases[0]['policy_reference']['history'] == refs[0]['history']
    assert m['source_id'] == aliases[0]['source_id'] == aliases[1]['source_id']
    json.dumps([m, tm, nm, fm, missing, dm, unique, aliases, cells], allow_nan=False)
    return dict(status='PASS', utc=utc(), measured_outcomes_read=False, checks=[
        'first-index minima, exact ties, reference bands, strict pair reversals and their denominators',
        'Decimal arithmetic preserves errors below binary64 display resolution and near-one summary differences',
        'signed original-point gaps never enter the grid candidate set',
        'zero span, nonpositive total, domain mismatch and unresolved classification retain nulls',
        'distinct numerical inputs are counted separately from duplicated policy references',
        'no-adaptation historical reason is distinct from the mathematical zero-gain guard',
        'positive/negative gain mass and signed cancellation use the exact saved promoted gains',
        'saved loss gain signs, memorization, clipping applicability and full histories survive joining',
        'conditional summaries retain denominators; undefined values prevent unconditional means'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    path = Path(args.output)
    assert not path.exists(), 'Preserve previous fixture results'
    result = checks()
    result['source_sha256'] = {name: sha(HERE / name) for name in ['analyze_stage9.py', 'analysis_checks.py', 'metrics.py', 'common_stage9.py']}
    write(path, result)
    print(json.dumps(result, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
