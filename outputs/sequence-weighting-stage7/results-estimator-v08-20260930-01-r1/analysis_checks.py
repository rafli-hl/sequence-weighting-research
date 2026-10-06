"""Outcome-independent unit fixtures for Stage7 summaries and pairing."""
import argparse
import copy
import json
import math
from pathlib import Path
from analyze_stage7 import summarize_group,summarize,scale_comparisons,quantile,write,utc,sha,HERE


def row(replicate,p,truth=1.,scale=1.,reason=None,family='recovery',control=None):
    return dict(id=f'{replicate}-{scale}-{family}-{control}',block_id=f'b{replicate}',array_index=replicate,
        family=family,n=128,replicate=replicate,truth_p=truth,sigma=0.,scale=scale,c=None,control=control,
        seed_weights=100+replicate,seed_noise=200+replicate,weights_sha256=f'weights-{replicate}',gains_sha256='fictitious',
        p=p,reason=reason,objective=None if p is None else .01,at_upper_bound=p is not None and p>=7.999,
        at_lower_bound=p is not None and p<=.001,total_gain=1.,total_gain_fsum=1.,negative_gain_fraction=0.,cancellation_ratio=1.,fit_seconds=.01)


def checks():
    rows=[row(0,1.),row(1,None,reason='nonpositive_total_gain'),row(2,3.)]
    group=summarize_group(rows,3)
    assert group['defined']==2 and group['undefined']==1
    assert group['undefined_by_reason']=={'nonpositive_total_gain':1}
    assert group['conditional_estimate']['mean']==2.
    assert group['conditional_error']['bias']==1 and math.isclose(group['conditional_error']['rmse'],math.sqrt(2))
    assert group['conditional_error']['mae']==1
    assert group['unconditional_recovery_mean'] is None and group['unconditional_recovery_rmse'] is None
    assert group['unconditional_recovery_reason']=='contains_undefined_fits'
    complete=[row(0,1.),row(1,2.),row(2,3.)]; stats=summarize_group(complete,3)
    assert stats['unconditional_recovery_mean']==2 and math.isclose(stats['unconditional_recovery_rmse'],math.sqrt(5/3))
    assert quantile([0.,10.,20.,30.],.25)==7.5
    zero=[row(i,None,truth=None,reason='nonpositive_total_gain',family='control',control='zero_gain') for i in range(3)]
    for r in zero: r.update(total_gain=0.,total_gain_fsum=0.,cancellation_ratio=None)
    undefined=summarize_group(zero,3)
    assert undefined['defined']==0 and undefined['conditional_estimate']['mean'] is None
    assert undefined['cancellation_undefined']==3 and undefined['conditional_error']['rmse'] is None
    assert undefined['unconditional_recovery_reason']=='no_identifiable_truth'
    no_truth=[row(i,8.,truth=None,family='cancellation') for i in range(3)]
    for r in no_truth: r.update(c=0.,generator_p=.2)
    unknown=summarize_group(no_truth,3)
    assert unknown['upper_boundary_count']==3 and unknown['conditional_estimate']['mean']==8
    assert unknown['conditional_error']['bias'] is None and unknown['unconditional_recovery_mean'] is None
    outside=summarize_group([row(i,8.,truth=10.,family='control',control='outside_range') for i in range(3)],3)
    assert outside['truth_relation']=='outside_search_interval' and outside['conditional_error']['rmse'] is None
    assert outside['conditional_misspecification_error']['rmse']==2 and outside['unconditional_recovery_rmse'] is None
    assert outside['upper_boundary_rate_all']==1
    both_generators=no_truth+[dict(r,generator_p=1.) for r in no_truth]
    assert len(summarize(both_generators,3))==2
    tiny=[row(i,None,scale=1e-14,reason='nonpositive_total_gain') for i in range(3)]
    for r in tiny: r.update(total_gain=5e-12,total_gain_fsum=5.001e-12)
    t=summarize_group(tiny,3)
    assert t['guard_positive_undefined_count']==3 and t['guard_nonpositive_undefined_count']==0
    assert t['total_gain_sum_minus_fsum']['mean']<0
    paired=[]
    for rep in range(3):
        paired.extend([row(rep,1.+rep),row(rep,1.+rep+1e-6,scale=1e-8),
                       row(rep,None,scale=1e-14,reason='nonpositive_total_gain')])
    comparisons,pairs=scale_comparisons(paired,3)
    assert len(comparisons)==2 and len(pairs)==6
    unavailable=next(x for x in comparisons if x['scale']==1e-14)
    available=next(x for x in comparisons if x['scale']==1e-8)
    assert unavailable['both_defined']==0 and unavailable['target_guard_count']==3
    assert unavailable['conditional_absolute_difference']['mean'] is None and unavailable['unconditional_absolute_difference_mean'] is None
    assert available['both_defined']==3 and math.isclose(available['conditional_absolute_difference']['mean'],1e-6,rel_tol=1e-9)
    mixed=copy.deepcopy(paired)
    for r in mixed:
        if r['replicate']==0 and r['scale']==1e-8: r.update(p=None,objective=None,reason='nonpositive_total_gain')
    mixed_comparisons,_=scale_comparisons(mixed,3)
    m=next(x for x in mixed_comparisons if x['scale']==1e-8)
    assert m['both_defined']==2 and m['unconditional_absolute_difference_mean'] is None
    broken=copy.deepcopy(paired); broken[1]['weights_sha256']='different'
    try: scale_comparisons(broken,3)
    except AssertionError: pass
    else: raise AssertionError('Pairing mismatch not detected')
    assert len(summarize(paired,3))==3
    json.dumps([group,stats,undefined,unknown,outside,comparisons],allow_nan=False)
    return dict(status='PASS',utc=utc(),measured_outcomes_read=False,checks=[
        'undefined reasons retained and unconditional recovery suppressed',
        'conditional bias/RMSE/MAE and linear quantiles known exactly',
        'zero/all-undefined and no-truth outcomes never assigned recovery errors',
        'outside-range truth explicitly constrained misspecification',
        'generator_p keeps null-truth cancellation conditions distinct; positive guard and fsum differences retained',
        'matched scale pairs verify weights/seeds and retain missing pairs',
        'conditional paired differences and unconditional undefined propagation',
        'mismatched pairs rejected and all outputs serialize without NaN'])


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',required=True); args=parser.parse_args()
    path=Path(args.output); assert not path.exists(),'Preserve prior fixture output'
    result=checks(); result['source_sha256']={name:sha(HERE/name) for name in ['analyze_stage7.py','analysis_checks.py']}
    write(path,result); print(result,flush=True)


if __name__=='__main__': main()
