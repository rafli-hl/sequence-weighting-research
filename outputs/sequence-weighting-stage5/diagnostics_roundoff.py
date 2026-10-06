"""Post-failure numerical verification; original strict failure stays explicit."""
import math
from decimal import Decimal,localcontext
import torch
from diagnostics import fit


def gram_check(centered,gram,objective):
    observed=float(gram.sum()); error=abs(observed-objective)
    scale=max(1.,float(gram.abs().sum()),abs(objective))
    result=dict(original_absolute_tolerance=1e-12,original_absolute_error=error,
        original_strict_pass=error<1e-12,scale_normalized_error=error/scale,
        ulps_at_scale=error/math.ulp(scale),verification='original_absolute_check')
    if result['original_strict_pass']: return result
    n=len(centered)
    with localcontext() as ctx:
        ctx.prec=70
        cc=[[Decimal.from_float(x) for x in row] for row in centered.tolist()]
        direct=sum(sum(row)**2 for row in cc)/Decimal(n)
        exact_gram=[[sum(row[i]*row[j] for row in cc)/Decimal(n) for j in range(3)] for i in range(3)]
        expanded=sum(sum(row) for row in exact_gram)
        identity_error=abs(direct-expanded)
        assert identity_error<Decimal('1e-50')
        gram_roundoff=abs(Decimal.from_float(observed)-expanded)
        objective_roundoff=abs(Decimal.from_float(objective)-direct)
    # Conservative accumulation bound from row count and float64 epsilon, not p* or selection.
    factor=8*n*torch.finfo(torch.float64).eps
    bound=factor/(1-factor)*scale
    assert float(gram_roundoff)<=bound and float(objective_roundoff)<=bound
    result.update(verification='70_digit_recomputation_and_float64_roundoff_bound',
        decimal_identity_error=float(identity_error),decimal_precision=70,
        gram_roundoff=float(gram_roundoff),objective_roundoff=float(objective_roundoff),roundoff_bound=bound)
    return result


def decompose(w,initial,current):
    primary_gain=initial['loss']-current['loss']
    component_gain=initial['component_loss'].double()-current['component_loss'].double()
    error=float((component_gain.mean(1)-primary_gain.double()).abs().max())
    assert error<2e-6,error
    result=dict(primary=fit(w,primary_gain),identity_max_abs_error=error,components={})
    for j,name in enumerate(['shared','group','instance']):
        result['components'][name]=dict(baseline_nll=float(initial['component_loss'][:,j].double().mean()),
            current_nll=float(current['component_loss'][:,j].double().mean()),fit=fit(w,component_gain[:,j]))
    result['group_instance_only']=fit(w,component_gain[:,1:].mean(1))
    result['oracle_reference']=fit(w,2*math.log(16)/3-current['loss'].double())
    total=float(component_gain.sum())
    if total<=3e-10 or float(w.max()-w.min())<1e-12:
        result['allocation']=dict(defined=False,reason='nonpositive_total_gain_or_uniform_weights')
    else:
        idx=w.argsort(); cg=component_gain[idx]; n=len(w)
        q0=torch.arange(1,n+1,dtype=torch.float64)/n
        mass=cg.sum(0)/total; cumulative=cg.cumsum(0)/total
        centered=cumulative-q0[:,None]*mass[None,:]; q=cg.sum(1).cumsum(0)/total
        assert torch.allclose(cumulative.sum(1),q,atol=1e-12,rtol=0)
        assert torch.allclose(centered.sum(1),q-q0,atol=1e-12,rtol=0)
        gram=centered.T@centered/n; objective=float(((q-q0)**2).mean())
        check=gram_check(centered,gram,objective)
        original_q=primary_gain.double()[idx].cumsum(0)/primary_gain.double().sum()
        result['allocation']=dict(defined=True,signed_mass_share=mass.tolist(),centered_rms=gram.diag().sqrt().tolist(),
            signed_cross_terms=gram.tolist(),total_centered_objective=objective,
            primary_cumulative_roundoff_max=float((original_q-q).abs().max()),gram_identity_check=check)
    return result
