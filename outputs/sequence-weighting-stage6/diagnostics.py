"""Frozen signed-gain diagnostics; never a model-selection criterion."""
import math
import torch
from core import exponent


def fit(w, gain):
    gain = gain.double()
    result = exponent(w.tolist(), gain.tolist())
    result.update(total_gain=float(gain.sum()), mean_gain=float(gain.mean()),
                  negative_gain_fraction=float((gain < 0).double().mean()),
                  at_lower_bound=result['p'] is not None and result['p'] <= .001,
                  at_upper_bound=result['p'] is not None and result['p'] >= 7.999)
    return result


def decompose(w, initial, current):
    # Primary reproduces the saved float32 subtraction, before converting to float64.
    primary_gain = initial['loss']-current['loss']
    component_gain = initial['component_loss'].double()-current['component_loss'].double()
    reconstructed = component_gain.mean(1)
    error = float((reconstructed-primary_gain.double()).abs().max())
    assert error < 2e-6, error
    result = dict(primary=fit(w, primary_gain), identity_max_abs_error=error, components={})
    for j, name in enumerate(['shared','group','instance']):
        result['components'][name] = dict(
            baseline_nll=float(initial['component_loss'][:,j].double().mean()),
            current_nll=float(current['component_loss'][:,j].double().mean()),
            fit=fit(w, component_gain[:,j]))
    result['group_instance_only'] = fit(w, component_gain[:,1:].mean(1))
    oracle_gain = 2*math.log(16)/3-current['loss'].double()
    result['oracle_reference'] = fit(w, oracle_gain)
    # Equal query counts make component allocation an exact algebraic diagnostic.
    total = float(component_gain.sum())
    if total <= 3e-10 or float(w.max()-w.min()) < 1e-12:
        result['allocation'] = dict(defined=False,reason='nonpositive_total_gain_or_uniform_weights')
    else:
        idx = w.argsort()
        cg = component_gain[idx]
        n = len(w)
        q0 = torch.arange(1,n+1,dtype=torch.float64)/n
        mass = cg.sum(0)/total
        cumulative = cg.cumsum(0)/total
        centered = cumulative-q0[:,None]*mass[None,:]
        q = cg.sum(1).cumsum(0)/total
        assert torch.allclose(cumulative.sum(1),q,atol=1e-12,rtol=0)
        assert torch.allclose(centered.sum(1),q-q0,atol=1e-12,rtol=0)
        gram = centered.T@centered/n
        assert abs(float(gram.sum())-float(((q-q0)**2).mean()))<1e-12
        original_q = primary_gain.double()[idx].cumsum(0)/primary_gain.double().sum()
        result['allocation'] = dict(defined=True, signed_mass_share=mass.tolist(),
            centered_rms=gram.diag().sqrt().tolist(), signed_cross_terms=gram.tolist(),
            total_centered_objective=float(((q-q0)**2).mean()),
            primary_cumulative_roundoff_max=float((original_q-q).abs().max()))
    return result


def contrast(small, middle, large):
    return None if any(x is None for x in [small,middle,large]) else middle-max(small,large)


def difference(a,b):
    return None if a is None or b is None else a-b


def interaction(a11,a10,a01,a00):
    return difference(difference(a11,a10),difference(a01,a00))


def validate_diagnostics():
    w = torch.tensor([.1,.3,1.,3.])
    initc = torch.tensor([[.1,3.,4.],[.2,3.1,4.2],[.1,3.,4.],[.2,3.2,4.1]])
    finalc = initc-torch.tensor([[-.1,.3,.2],[-.2,.4,.5],[.1,.8,.7],[.1,1.,1.2]])
    initial = dict(component_loss=initc,loss=initc.mean(1))
    current = dict(component_loss=finalc,loss=finalc.mean(1))
    d = decompose(w,initial,current)
    assert d['components']['shared']['fit']['p'] is None
    assert d['allocation']['signed_mass_share'][0] < 0
    assert d['primary']['p'] is not None
    assert decompose(torch.ones(4),initial,current)['primary']['p'] is None
    assert contrast(.1,.3,.2) == .3-.2
    assert difference(None,1.) is None
    assert interaction(4.,2.,3.,1.) == 0.
