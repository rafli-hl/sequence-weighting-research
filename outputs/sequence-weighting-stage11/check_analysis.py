"""Outcome-independent Stage 11 policy/summary fixtures; no model execution."""
import argparse
import copy
import hashlib
import json
import math
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from config import CAPS, CONDITIONS, ARMS, EPOCHS, GRID, F_INDEX, TUNE, CONFIRM
from policies import tuning_schedule, confirmation_schedule, select
from analysis import summarize, paired_summary


def expect_error(function):
    try:
        function()
    except (ValueError, KeyError):
        return
    raise AssertionError('Invalid fixture was accepted')


def decisions(epoch=10, index=F_INDEX):
    return {c: {str(w): dict(condition=c, width=w, epoch=epoch,
        grid_index=None if epoch == 0 else index,
        **(dict(lr=None, wd=None, clip=None) if epoch == 0 else GRID[index]))
        for w, _ in CAPS} for c in CONDITIONS}


def tuning_rows():
    # Intentionally construct the design independently of tuning_schedule().
    rows = []
    for condition in CONDITIONS:
        for width, _ in CAPS:
            for data_seed, seed, _ in TUNE:
                for grid_index in range(len(GRID)):
                    for arm in ARMS:
                        for epoch in [0] + EPOCHS:
                            val = 2. if epoch == 0 else 3. + grid_index + epoch / 100
                            rows.append(dict(condition=condition, width=width, data_seed=data_seed,
                                seed=seed, grid_index=grid_index, arm=arm, epoch=epoch,
                                validation_nll=val, test_nll=-1000 * epoch,
                                p_star=8 if epoch else 0))
    return rows


def metrics(loss):
    return dict(loss=loss, shared=dict(loss=loss, accuracy=.8),
                group=dict(loss=loss, accuracy=.6), instance=dict(loss=loss, accuracy=.1))


def saved_records(selected):
    # Independently construct scalar records from the literal protocol identities.
    records = []
    for c in CONDITIONS:
        for width, _ in CAPS:
            for data_seed in sorted({d for d, _, _ in CONFIRM}):
                for seed in sorted(s for d, s, _ in CONFIRM if d == data_seed):
                    baseline = 4. + (0 if c == 'G16' else .25)
                    identity = dict(condition=c, width=width, data_seed=data_seed, seed=seed)
                    records.append(dict(identity, grid_index=None, arm=None, epoch=0,
                        train=metrics(baseline), validation=metrics(baseline), test=metrics(baseline),
                        fit=dict(p=None, reason='no_adaptation'), group_fit=dict(p=None, reason='no_adaptation'),
                        clipping=None))
                    chosen = selected[c][str(width)]
                    indices = [F_INDEX]
                    if chosen['epoch'] and chosen['grid_index'] != F_INDEX:
                        indices.append(chosen['grid_index'])
                    for index in indices:
                        for arm in ARMS:
                            for epoch in EPOCHS:
                                gain = (0.5 if c == 'G16' else 1.) + width / 1024
                                p = {64: .1, 128: .5, 256: .2}[width]
                                fit = dict(p=p, objective=.001) if arm == 'random' else dict(p=None, reason='constant_weights')
                                group_fit = dict(p=.4 if c == 'G16' else .2, objective=.002) if arm == 'random' else dict(p=None, reason='constant_weights')
                                records.append(dict(identity, grid_index=index, arm=arm, epoch=epoch,
                                    train=metrics(baseline-gain), validation=metrics(baseline-gain),
                                    test=metrics(baseline-gain), fit=fit, group_fit=group_fit, clipping=.25))
    return records


def run_checks():
    checks = []
    schedule = tuning_schedule()
    assert len(schedule) == 72 and len({r['name'] for r in schedule}) == 72
    actual = {(r['condition'], r['width'], r['data_seed'], r['seed'], r['grid_index'], r['arm']) for r in schedule}
    literal = {(c, w, d, s, i, a) for c in CONDITIONS for w,_ in CAPS
               for d,s,_ in TUNE for i in range(len(GRID)) for a in ARMS}
    assert actual == literal
    checks.append('Literal 72-trajectory tuning schedule, unique names and identities')

    zero = decisions(0)
    assert len(confirmation_schedule(zero)) == 120
    assert all(r['grid_index'] == F_INDEX for r in confirmation_schedule(zero))
    assert len(confirmation_schedule(decisions())) == 120
    assert len(confirmation_schedule(decisions(3, 0))) == 240
    checks.append('F always retained under all-zero selection; union deduplicates 120..240 trajectories')

    rows = tuning_rows()
    result = select(rows)
    assert result['canonical_initial_pairs'] == 12
    assert result['nonzero_rows'] == 432 and result['supplied_initial_copies'] == 72
    assert result['candidate_count'] == 114
    assert all(x['epoch'] == 0 for c in result['decisions'].values() for x in c.values())
    modified = copy.deepcopy(rows)
    for r in modified:
        if r['condition'] == 'G1' and r['width'] == 128 and r['arm'] == 'random' and r['epoch'] in (1,3):
            r['validation_nll'] = 1.
        if r['arm'] == 'uniform' and r['epoch']:
            r['validation_nll'] = -10000.
        r['test_nll'], r['p_star'] = random.Random(r['epoch']).random(), -1e90
    picked = select(modified)
    assert picked['decisions']['G1']['128']['epoch'] == 1
    assert picked['decisions']['G1']['128']['grid_index'] == 0
    assert picked['decisions']['G16']['128']['epoch'] == 0
    shuffled = copy.deepcopy(modified)
    random.Random(921).shuffle(shuffled)
    assert select(shuffled) == picked
    checks.append('Canonical zero, condition separation, exact epoch/LR ties, input-order invariance; uniform/test/p excluded')

    bad = copy.deepcopy(rows); bad[0]['validation_nll'] += 1e-6
    expect_error(lambda: select(bad))
    expect_error(lambda: select(rows + [rows[0]]))
    expect_error(lambda: select(rows[:-1]))
    bad = copy.deepcopy(rows); bad[1]['validation_nll'] = math.nan
    expect_error(lambda: select(bad))
    canonical_only = [r for r in rows if r['epoch']]
    for c in CONDITIONS:
        for w,_ in CAPS:
            for d,s,_ in TUNE:
                canonical_only.append(dict(condition=c,width=w,data_seed=d,seed=s,
                    grid_index=None,arm=None,epoch=0,validation_nll=2.))
    assert select(canonical_only)['decisions'] == result['decisions']
    checks.append('Reject inconsistent zero copies, duplicate/missing/nonfinite inputs; accept exact canonical baselines')

    entries = [dict(data_seed=d,seed=s,value=float(k))
               for k,(d,s,_) in enumerate(CONFIRM)]
    paired = paired_summary(entries)
    assert [r['mean'] for r in paired['corpora']] == [.5,2.5,4.5,6.5,8.5]
    assert paired['between_corpora']['mean'] == 4.5
    assert math.isclose(paired['between_corpora']['sd'], math.sqrt(10))
    partial = copy.deepcopy(entries); partial[0]['value'] = None
    partial_summary = paired_summary(partial)
    assert partial_summary['between_corpora']['mean'] is None
    assert partial_summary['between_corpora']['defined'] == 4
    assert partial_summary['all_pairs']['defined'] == 9
    expect_error(lambda: paired_summary(entries[:-1]))
    checks.append('Five corpus means with nested seeds; missing/null propagates without denominator reduction')

    chosen = decisions()
    records = saved_records(chosen)
    summary = summarize(records, chosen)
    assert summary['counting_units']['planned_native_checkpoints'] == 780
    assert summary['counting_units']['policy_references'] == 840
    assert summary['counting_units']['status_counts'] == {'complete':780}
    assert summary['primary_F10_group_contrast']['between_corpora']['mean'] == .5
    assert summary['primary_F10_G1_absolute_group_gain']['between_corpora']['mean'] == 1.125
    assert summary['readiness']['mechanism_ready'] is True
    assert summary['readiness']['capacity_ready'] is True
    assert math.isclose(summary['K']['F10']['G1']['random']['between_corpora']['mean'], .3)
    assert summary['K']['F10']['G1']['uniform']['between_corpora']['mean'] is None
    assert summary['matched_F']['10']['random']['128']['group_p_G16_minus_G1']['between_corpora']['mean'] == .2
    checks.append('Known matched absolute/relative group gains; complete R utility, scaling, K and directional group p')

    # Less forgetting is a positive relative response but not positive learning.
    forget = copy.deepcopy(records)
    for r in forget:
        if r['epoch'] == 10 and r['arm'] == 'random' and r['width'] == 128:
            baseline = 4. if r['condition'] == 'G16' else 4.25
            r['test']['group']['loss'] = baseline + (2. if r['condition'] == 'G16' else 1.)
    forgetting = summarize(forget, chosen)
    assert forgetting['readiness']['relative_response_positive'] is True
    assert forgetting['readiness']['absolute_G1_group_gain_positive'] is False
    assert forgetting['readiness']['selected_G1_middle_utility'] is True
    assert forgetting['readiness']['mechanism_ready'] is False
    checks.append('Positive relative effect from less forgetting does not satisfy absolute group-learning gate')

    # Utility can pass without scaling; changing p cannot alter readiness.
    nonscaling = copy.deepcopy(records)
    for r in nonscaling:
        if r['epoch'] and r['condition'] == 'G1' and r['width'] == 256:
            r['test']['loss'] = 4.
            if r['arm'] == 'random':
                r['fit'] = dict(p=None,reason='nonpositive_total_gain')
                r['group_fit'] = dict(p=8.,objective=10.)
    different = summarize(nonscaling, chosen)
    assert different['selected_global_utility']['G1']['random'] is True
    assert different['scaling']['R']['G1']['random']['met'] is False
    assert different['readiness']['mechanism_ready'] is True
    assert different['K']['R']['G1']['random']['between_corpora']['mean'] is None
    assert different['cells']['R']['G1']['random']['256']['group_fit_counts']['at_upper_bound'] == 10
    checks.append('Utility separate from scaling; p/fit guards and boundary outcomes never alter readiness')

    # Zero policy must use each condition's own baseline, not any adapted row.
    zero_result = summarize(records, zero)
    assert zero_result['cells']['R']['G1']['random']['128']['delta_test']['between_corpora']['mean'] == 0.
    assert zero_result['cells']['R']['G1']['random']['128']['utility']['met'] is False
    assert zero_result['cells']['R']['G1']['random']['128']['fit_counts']['reasons'] == {'no_adaptation':10}
    assert zero_result['cells']['R']['G1']['uniform']['128']['fit_counts']['reasons'] == {'no_adaptation':10}
    assert all(r['fit']['uniform_unidentifiable'] for r in zero_result['policy_rows']
               if r['branch']=='R' and r['arm']=='uniform')
    assert zero_result['cells']['R']['G1']['random']['128']['clipping']['all_pairs']['undefined'] == 10
    checks.append('Epoch-zero exact own-baseline utility, undefined p/clipping, no_adaptation preserved and uniform flag')

    first_d, first_s, _ = CONFIRM[0]
    missing = [r for r in records if not (r['condition']=='G1' and r['width']==128 and
               r['data_seed']==first_d and r['seed']==first_s and r['arm']=='random' and r['epoch']==10)]
    incomplete = summarize(missing, chosen)
    assert incomplete['counting_units']['planned_native_checkpoints'] == 780
    assert incomplete['counting_units']['status_counts']['not_run'] == 1
    assert incomplete['primary_F10_group_contrast']['all_pairs']['defined'] == 9
    assert incomplete['primary_F10_group_contrast']['between_corpora']['mean'] is None
    assert incomplete['readiness']['mechanism_ready'] is None
    assert len(incomplete['policy_rows']) == 840
    failed = copy.deepcopy(records)
    for r in failed:
        if r['condition']=='G1' and r['width']==128 and r['data_seed']==first_d and r['seed']==first_s and r['arm']=='random' and r['epoch']==10:
            r['status']='failed'
    rejected = summarize(failed, chosen)
    assert rejected['readiness']['mechanism_ready'] is None
    assert rejected['cells']['R']['G1']['random']['128']['clipping']['all_pairs']['undefined'] == 1
    expect_error(lambda: summarize(records + [records[0]],chosen))
    all_missing = summarize([],chosen)
    assert all_missing['counting_units']['status_counts'] == {'not_run':780}
    assert all_missing['readiness']['mechanism_ready'] is None
    checks.append('Missing and failed rows retained with all planned aliases; all-unrun summaries remain nullable')
    return checks


def main():
    start = time.perf_counter()
    started_utc = datetime.now(timezone.utc)
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    checks = run_checks()
    here = Path(__file__).resolve().parent
    result = dict(status='PASS',utc=datetime.now(timezone.utc).isoformat(),checks=checks,
        started_utc=started_utc.isoformat(),elapsed_seconds=time.perf_counter()-start,
        utc_elapsed_seconds=(datetime.now(timezone.utc)-started_utc).total_seconds(),
        source_sha256={name:hashlib.sha256((here/name).read_bytes()).hexdigest()
                       for name in ('config.py','policies.py','analysis.py','check_analysis.py')},
        outcomes='Only hand-constructed scalar fixtures; no research data or model execution')
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x',encoding='utf-8') as f:
            f.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__ == '__main__':
    main()
