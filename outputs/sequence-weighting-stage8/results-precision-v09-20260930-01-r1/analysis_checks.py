"""Stage8 outcome-independent rank/tie/regret/Decimal fixtures."""
import argparse
import copy
import json
from decimal import Decimal,localcontext
from pathlib import Path
from analyze_stage8 import HERE,sha,utc,write,profile_metrics,summarize_cell,decimal_stats,d64


def profile(rep=0):
    return dict(source_id=f'fixture-{rep}',block_id=f'fixture-block-{rep}',n=128,replicate=rep,generator_p=.2,c=1.,truth_p=.2,
        seed_weights=rep,seed_noise=100+rep,weights_sha256='synthetic',gains_sha256='synthetic',original_p=.075,
        original_reason=None,original_objective=1.,legacy_reason=None,hp_reason=None,total_gain_legacy=128.,
        total_gain_fsum=128.,total_gain_hp='128',hp_dps=80,hp_identity_max_abs_error='0',legacy_J=[3.,2.,1.],naive_D64=[0.,-1.,-2.],
        stable_D64=[0.,1.,2.],hp_J=['0','1','2'],hp_D=['0','1','2'],
        original_point=dict(p=.075,legacy_J=1.,naive_D64=-2.,stable_D64=-.1,hp_J='-.1',hp_D='-.1'),elapsed_seconds=0.)


def checks():
    grid=[0.,.05,.1]; item=profile(); m=profile_metrics(item,grid)
    assert m['reference']['argmin_index']==0 and m['reference']['top_two_gap']=='1'
    assert m['methods']['legacy_J']['argmin_index']==2
    assert m['methods']['legacy_J']['pairwise']['strict_reversals']==3
    assert m['methods']['stable_D64']['pairwise']['strict_agreements']==3
    assert m['methods']['legacy_J']['reference_regret']=='2'
    assert m['original_point']['signed_HP_gap_vs_grid_min']=='-0.1'
    assert m['original_point']['lower_than_grid_min'] and m['reference']['minimum_set_indices']==[0]
    # Large common J with representable reference contrasts lost by float subtraction.
    with localcontext() as ctx:
        ctx.prec=110
        reference=[Decimal('1e20')-Decimal(i)*Decimal('1e-30') for i in range(3)]
        tied=profile(); tied.update(legacy_J=[1e20]*3,naive_D64=[0.]*3,stable_D64=[0.,-1e-30,-2e-30],
            hp_J=[str(v) for v in reference],hp_D=['0','-1e-30','-2e-30'],original_point=None,original_p=None)
        tied_metrics=profile_metrics(tied,grid)
        assert tied_metrics['reference']['argmin_index']==2
        assert tied_metrics['methods']['legacy_J']['exact_minimum_count']==3
        assert tied_metrics['methods']['legacy_J']['pairwise']['float_ties_against_reference_strict']==3
        assert Decimal(tied_metrics['methods']['legacy_J']['error']['max_abs_error'])==Decimal('2e-30')
        assert tied_metrics['methods']['stable_D64']['exact_argmin_agreement']
        assert not tied_metrics['methods']['legacy_J']['reference_minset_agreement']
    near=profile(); near.update(hp_D=['0','1e-51','1'],hp_J=['0','1e-51','1'],legacy_J=[0.,0.,1.],
        naive_D64=[0.,-1e-51,1.],stable_D64=[0.,1e-51,1.],original_p=None,original_point=None)
    near_m=profile_metrics(near,grid,dict(source_id=near['source_id'],unresolved=True))
    assert near_m['reference']['minimum_set_indices']==[0,1]
    assert near_m['pairwise']['reference_nonexact_near_ties']==1 and near_m['pairwise']['reference_strict_pairs']==2
    assert not near_m['methods']['naive_D64']['exact_argmin_agreement'] and near_m['methods']['naive_D64']['reference_minset_agreement']
    assert Decimal(near_m['methods']['naive_D64']['reference_regret_excess_over_tau'])==0
    assert near_m['reference_classification_unresolved']
    flat=profile(); flat.update(hp_D=['0','0','0'],hp_J=['1','1','1'],legacy_J=[1.,1.,1.],
        naive_D64=[0.,0.,0.],stable_D64=[0.,0.,0.],original_p=None,original_point=None)
    flat_m=profile_metrics(flat,grid)
    assert flat_m['reference']['exact_minimum_count']==3 and flat_m['pairwise']['reference_exact_ties']==3
    assert flat_m['methods']['legacy_J']['error']['relative_to_contrast_span'] is None
    undefined=profile(1); undefined.update(legacy_reason='nonpositive_total_gain',hp_reason='nonpositive_total_gain',
        legacy_J=None,naive_D64=None,stable_D64=None,hp_J=None,hp_D=None,original_p=None,original_point=None)
    missing=profile_metrics(undefined,grid)
    assert not missing['both_defined'] and missing['reference'] is None and missing['methods']['legacy_J']['reference_regret'] is None
    cell=summarize_cell([m,missing],2)
    assert cell['total']==2 and cell['both_defined']==1 and cell['legacy_undefined_reasons']=={'nonpositive_total_gain':1}
    assert cell['methods']['legacy_J']['reference_regret']['conditional_mean']=='2'
    assert cell['methods']['legacy_J']['reference_regret']['unconditional_mean'] is None
    domain=copy.deepcopy(undefined); domain.update(hp_reason=None,hp_J=['0','1','2'],hp_D=['0','1','2'])
    mismatch=profile_metrics(domain,grid)
    assert mismatch['domain_mismatch'] and mismatch['reference_defined'] and not mismatch['legacy_defined']
    # Decimal.from_float captures the actual binary number, not its short display string.
    assert d64(.1)!=Decimal('.1')
    assert str(d64(.1)).startswith('0.100000000000000005551115123125')
    precise=decimal_stats(['1.0000000000000000000000000000000000000000000000000000000000001','1'])
    assert Decimal(precise['conditional_mean'])>1
    assert Decimal(precise['conditional_sd'])>0
    rounded=profile(); rounded.update(total_gain_legacy=.1,total_gain_fsum=.1,total_gain_hp='0.1')
    rounded_m=profile_metrics(rounded,grid)
    with localcontext() as ctx:
        ctx.prec=110
        expected=d64(.1)-Decimal('0.1')
        assert Decimal(rounded_m['normalization_difference']['legacy_minus_hp'])==expected>0
        rounded_cell=summarize_cell([rounded_m],1)
        assert Decimal(rounded_cell['normalization_difference']['legacy_minus_hp']['conditional_mean'])==expected
    zero_total=profile(); zero_total.update(total_gain_legacy=0.,total_gain_fsum=0.,total_gain_hp='0')
    assert profile_metrics(zero_total,grid)['normalization_difference']['legacy_relative_to_hp'] is None
    json.dumps([m,tied_metrics,near_m,flat_m,missing,cell,mismatch,precise],allow_nan=False)
    return dict(status='PASS',utc=utc(),measured_outcomes_read=False,checks=[
        'first-index strict minima and exact tie sets','reference-strict reversals and float ties retain pair denominators',
        'large common objective preserves sub-float errors through Decimal arithmetic',
        'frozen reference band distinguishes exact agreement from near-minimum agreement',
        'zero span is undefined for span normalization','stored continuous point has signed gap and is not a grid candidate',
        'undefined and domain-mismatch cases propagate without filtering','unresolved reference classification remains explicit',
        'Decimal.from_float exact promotion and 110-digit summary arithmetic',
        'gain-total signed rounding differences, cell summaries and zero-total relative null'])


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',required=True); args=parser.parse_args()
    path=Path(args.output); assert not path.exists(),'Preserve prior fixture checks'
    result=checks(); result['source_sha256']={name:sha(HERE/name) for name in ['analyze_stage8.py','analysis_checks.py']}
    write(path,result); print(result,flush=True)


if __name__=='__main__': main()
