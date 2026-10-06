"""Decimal and ranking metrics preserved from frozen Stage8 analysis source."""
from decimal import Decimal, localcontext
from collections import Counter
import math
PRECISION=110
METHODS=['legacy_J','naive_D64','stable_D64']

def d64(value): return Decimal.from_float(float(value))


def fmt(value): return 'undefined' if value is None else format(Decimal(str(value)),'.6g')


def quantile_decimal(values,q):
    if not values: return None
    values=sorted(values); index=Decimal(len(values)-1)*Decimal(str(q)); lo=int(index); hi=min(lo+1,len(values)-1)
    return values[lo]+(values[hi]-values[lo])*(index-lo)


def decimal_stats(values,total=None):
    numbers=[Decimal(v) for v in values if v is not None]
    assert all(v.is_finite() for v in numbers)
    denominator=len(values) if total is None else total
    with localcontext() as ctx:
        ctx.prec=PRECISION
        mean=sum(numbers,Decimal(0))/len(numbers) if numbers else None
        sd=(sum((x-mean)**2 for x in numbers)/(len(numbers)-1)).sqrt() if len(numbers)>1 else None
        result=dict(total=denominator,defined=len(numbers),undefined=denominator-len(numbers),
            conditional_mean=None if mean is None else str(mean),conditional_sd=None if sd is None else str(sd),
            conditional_minimum=str(min(numbers)) if numbers else None,conditional_maximum=str(max(numbers)) if numbers else None,
            conditional_median=None if not numbers else str(quantile_decimal(numbers,.5)),
            unconditional_mean=str(mean) if mean is not None and len(numbers)==denominator else None)
    return result


def rank_info(values,grid):
    minimum=min(values); indices=[i for i,value in enumerate(values) if value==minimum]
    return dict(argmin_index=indices[0],argmin_p=grid[indices[0]],exact_minimum_indices=indices,
                exact_minimum_count=len(indices),raw_exact_ties_all_pairs=sum(n*(n-1)//2 for n in Counter(values).values()))


def pairwise_counts(reference,methods,tau):
    total=len(reference)*(len(reference)-1)//2
    result=dict(total_pairs=total,reference_exact_ties=0,reference_nonexact_near_ties=0,reference_strict_pairs=0,
        methods={name:dict(raw_exact_ties_all_pairs=0,strict_agreements=0,strict_reversals=0,
            float_ties_against_reference_strict=0,float_strict_on_reference_nonstrict=0,
            float_ties_on_reference_nonstrict=0) for name in methods})
    for i in range(len(reference)):
        for j in range(i+1,len(reference)):
            difference=reference[i]-reference[j]
            strict=abs(difference)>tau
            if strict: result['reference_strict_pairs']+=1
            elif difference==0: result['reference_exact_ties']+=1
            else: result['reference_nonexact_near_ties']+=1
            for name,values in methods.items():
                counts=result['methods'][name]; comparison=(values[i]>values[j])-(values[i]<values[j])
                if comparison==0: counts['raw_exact_ties_all_pairs']+=1
                if strict:
                    if comparison==0: counts['float_ties_against_reference_strict']+=1
                    elif (comparison>0)==(difference>0): counts['strict_agreements']+=1
                    else: counts['strict_reversals']+=1
                elif comparison==0: counts['float_ties_on_reference_nonstrict']+=1
                else: counts['float_strict_on_reference_nonstrict']+=1
    assert result['reference_exact_ties']+result['reference_nonexact_near_ties']+result['reference_strict_pairs']==total
    for counts in result['methods'].values():
        assert counts['strict_agreements']+counts['strict_reversals']+counts['float_ties_against_reference_strict']==result['reference_strict_pairs']
        assert counts['float_strict_on_reference_nonstrict']+counts['float_ties_on_reference_nonstrict']==total-result['reference_strict_pairs']
    return result


def normalized_error(error,contrast_scale,span):
    return dict(max_abs_error=str(error),relative_to_contrast_scale=str(error/contrast_scale),
                relative_to_contrast_span=str(error/span) if span>0 else None)


def profile_metrics(row,grid,classification=None):
    with localcontext() as ctx:
        ctx.prec=PRECISION
        legacy_defined=row['legacy_reason'] is None; reference_defined=row['hp_reason'] is None
        assert all((row[name] is not None)==legacy_defined for name in METHODS)
        assert all((row[name] is not None)==reference_defined for name in ['hp_J','hp_D'])
        result={key:row.get(key) for key in ['source_id','source_array_index','block_id','n','replicate','generator_p','c','truth_p',
            'seed_weights','seed_noise','weights_sha256','gains_sha256','original_p','original_reason','original_objective',
            'legacy_reason','hp_reason','total_gain_legacy','total_gain_fsum','total_gain_hp','hp_dps','hp_identity_max_abs_error']}
        assert row['hp_dps']==80
        hp_total=Decimal(row['total_gain_hp'])
        legacy_difference=d64(row['total_gain_legacy'])-hp_total
        fsum_difference=d64(row['total_gain_fsum'])-hp_total
        result['normalization_difference']=dict(legacy_minus_hp=str(legacy_difference),fsum_minus_hp=str(fsum_difference),
            legacy_relative_to_hp=str(abs(legacy_difference)/abs(hp_total)) if hp_total else None,
            fsum_relative_to_hp=str(abs(fsum_difference)/abs(hp_total)) if hp_total else None)
        result.update(legacy_defined=legacy_defined,reference_defined=reference_defined,
            both_defined=legacy_defined and reference_defined,domain_mismatch=legacy_defined!=reference_defined,
            reference_validation=classification or {},reference_classification_unresolved=bool((classification or {}).get('unresolved',False)),
            reference=None,methods={},pairwise=None,original_point=None)
        method_values={}
        if legacy_defined:
            for name in METHODS:
                values=row[name]; assert len(values)==len(grid) and all(math.isfinite(v) for v in values)
                method_values[name]=values
                result['methods'][name]=dict(available=True,**rank_info(values,grid),exact_argmin_agreement=None,
                    reference_minset_agreement=None,reference_regret=None,reference_regret_excess_over_tau=None,
                    error=None,pairwise=None)
        else:
            result['methods']={name:dict(available=False,argmin_index=None,argmin_p=None,exact_minimum_indices=None,
                exact_minimum_count=None,raw_exact_ties_all_pairs=None,exact_argmin_agreement=None,reference_minset_agreement=None,
                reference_regret=None,reference_regret_excess_over_tau=None,error=None,pairwise=None) for name in METHODS}
        if reference_defined:
            ref=[Decimal(value) for value in row['hp_D']]; ref_J=[Decimal(value) for value in row['hp_J']]
            assert len(ref)==len(ref_J)==len(grid) and all(v.is_finite() for v in ref+ref_J)
            scale=max(Decimal(1),max(abs(value) for value in ref)); tau=Decimal('2e-50')*scale
            minimum=min(ref); span=max(ref)-minimum; sorted_values=sorted(ref)
            minset=[i for i,value in enumerate(ref) if value<=minimum+tau]
            info=rank_info(ref,grid)
            result['reference']=dict(**info,minimum_D=str(minimum),contrast_scale=str(scale),contrast_span=str(span),
                top_two_gap=str(sorted_values[1]-sorted_values[0]),tau=str(tau),minimum_set_indices=minset,
                minimum_set_size=len(minset),ranking_reference='Decimal80 D grid, independently validated at Decimal110',
                strict_order_is_resolution_limited=True)
            pairs=pairwise_counts(ref,method_values,tau)
            result['pairwise']={key:value for key,value in pairs.items() if key!='methods'}
            for name,values in method_values.items():
                info=result['methods'][name]; chosen=info['argmin_index']; regret=ref[chosen]-minimum
                assert regret>=0
                reference_for_error=ref_J if name=='legacy_J' else ref
                maximum=max(abs(d64(value)-target) for value,target in zip(values,reference_for_error))
                info.update(exact_argmin_agreement=chosen==result['reference']['argmin_index'],
                    reference_minset_agreement=chosen in minset,reference_regret=str(regret),
                    reference_regret_excess_over_tau=str(max(Decimal(0),regret-tau)),
                    error=normalized_error(maximum,scale,span),pairwise=pairs['methods'][name])
                assert info['raw_exact_ties_all_pairs']==info['pairwise']['raw_exact_ties_all_pairs']
            if row['original_point'] is not None and row['original_point']['hp_D'] is not None:
                point=row['original_point']; assert point['p']==row['original_p']
                hp_D=Decimal(point['hp_D']); hp_J=Decimal(point['hp_J'])
                point_errors={}
                for name in METHODS:
                    value=point[name]
                    point_errors[name]=None if value is None else normalized_error(abs(d64(value)-(hp_J if name=='legacy_J' else hp_D)),scale,span)
                result['original_point']=dict(p=point['p'],hp_D=str(hp_D),signed_HP_gap_vs_grid_min=str(hp_D-minimum),
                    lower_than_grid_min=hp_D<minimum,point_errors=point_errors,
                    interpretation='Signed diagnostic gap for the stored continuous estimate; not a continuous optimum or grid candidate')
        return result

