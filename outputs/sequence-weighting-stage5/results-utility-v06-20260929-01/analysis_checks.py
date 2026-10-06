"""Outcome-independent fixtures for the Stage5 frozen analysis; no run results read."""
import argparse
import copy
import json
import tempfile
from pathlib import Path
import torch
from stage5 import selection_key, utc, write, ROOT, CAPS, EPOCHS, CONFIRM, tuning_schedule, select
from diagnostics import fit, contrast
from diagnostics_roundoff import decompose
from analyze_stage5 import (desc, replicated, peak_verdict, signed_mass, utility_gate, scaling_gate,
                           initial_rows, policy_analysis, audit_gates)
from analyze_stage5 import diagnostic_decompose
from audit_stage5 import reconstruct_candidates


def validate():
    zero=dict(validation_nll=1.,epoch=0,lr=None,wd=None,grid_index=None)
    tied=dict(validation_nll=1.,epoch=1,lr=1e-5,wd=.1,grid_index=0)
    assert min([tied,zero],key=selection_key)==zero
    improved=dict(tied,validation_nll=.999)
    assert min([improved,zero],key=selection_key)==improved
    assert min([dict(tied,wd=1.),tied],key=selection_key)==tied
    assert min([dict(tied,lr=3e-5),tied],key=selection_key)==tied
    assert desc([1.,None,3.])['mean'] is None and desc([None])['undefined']==1
    assert contrast(.1,None,.2) is None
    values=[dict(data_seed=d,seed=s,value=float(d)) for d in [1,2,3] for s in [1,2,3]]
    summary=replicated(values)
    assert summary['all_pairs']['n']==9 and summary['between_corpora']['n']==3
    assert summary['between_corpora']['mean']==2 and summary['between_corpora']['sd']==1
    assert peak_verdict(summary)=='survives'
    missing=copy.deepcopy(values); missing[0]['value']=None
    assert replicated(missing)['between_corpora']['mean'] is None
    assert peak_verdict(replicated(missing))=='inconclusive_undefined'
    negative=[dict(x,value=-x['value']) for x in values]
    assert peak_verdict(replicated(negative))=='disappears'
    w=torch.tensor([.1,.2,1.,3.]); gain=torch.tensor([1.,-1.,2.,-2.])
    mass=signed_mass(gain)
    assert mass['positive_mass']==mass['negative_absolute_mass']==3. and mass['cancellation_ratio']==0
    assert signed_mass(torch.zeros(4))['cancellation_ratio'] is None
    assert fit(w,torch.zeros(4))['p'] is None and fit(torch.ones(4),torch.ones(4))['p'] is None
    initial_c=torch.tensor([[.1,3.,4.],[.2,3.1,4.2],[.1,3.,4.],[.2,3.2,4.1]])
    record=dict(component_loss=initial_c,loss=initial_c.mean(1))
    noadapt=decompose(w,record,record)
    assert noadapt['primary']['p'] is None and noadapt['primary']['total_gain']==0
    assert not noadapt['allocation']['defined']
    initial=dict(loss=torch.ones(4),component_loss=torch.ones(4,3))
    current=dict(loss=torch.ones(4),component_loss=torch.ones(4,3)-1e-7)
    guarded=diagnostic_decompose(w,initial,current)
    assert guarded['primary']['p'] is None and guarded['primary']['total_gain']==0
    assert guarded['allocation']['defined'] and guarded['allocation']['primary_cumulative_roundoff_max'] is None
    assert guarded['allocation']['original_comparison_finite'] is False
    json.dumps(guarded,allow_nan=False)
    rows=[dict(data_seed=d,seed=s,width=w,epoch=0,initial_test_nll=loss,test_nll=loss,
               initial_validation_nll=loss,validation_nll=loss)
          for d in [1,2,3] for s in [1,2,3] for w,loss in [(64,3.),(128,2.),(256,1.)]]
    assert scaling_gate(rows)['met'] and not utility_gate([r for r in rows if r['width']==64])['met']
    improved=[dict(r,epoch=1,test_nll=r['test_nll']-.1,validation_nll=r['validation_nll']-.1) for r in rows]
    assert utility_gate([r for r in improved if r['width']==64])['met']
    invalid=[dict(r,validation_nll=r['initial_validation_nll']+.1) for r in improved]
    assert not utility_gate([r for r in invalid if r['width']==64])['met'] and not scaling_gate(invalid)['met']
    failed_corpus=[dict(r,test_nll=r['initial_test_nll']+.01) if r['data_seed']==3 else r for r in improved]
    assert not utility_gate([r for r in failed_corpus if r['width']==64])['met']
    with tempfile.TemporaryDirectory(prefix='stage5-analysis-fixture-',dir=ROOT/'work') as temp:
        root=Path(temp)
        for scenario in ['different','zero_ties','optimizer_ties']:
            for c in tuning_schedule():
                folder=root/'runs'/c['name']; folder.mkdir(parents=True,exist_ok=True)
                history=[]
                for epoch in [0]+EPOCHS:
                    loss=2. if epoch==0 or scenario=='zero_ties' else 3.
                    if scenario=='different' and c['variant']=='U':
                        if c['grid_index']==0 and epoch==1: loss=1. if c['arm']=='random' else 4.
                        if c['grid_index']==1 and epoch==3: loss=1.5 if c['arm']=='random' else 0.
                    if scenario=='optimizer_ties' and epoch in [1,3]: loss=1.
                    history.append(dict(epoch=epoch,validation=dict(loss=loss)))
                write(folder/'history.json',history)
            selection=select(root)
            reconstructed=reconstruct_candidates(selection['inputs'])
            assert reconstructed==(selection['decisions'],selection['all_scores'])
            if scenario=='zero_ties':
                zero_selection=selection
                assert not selection['run_schedule']
                assert all(c['epoch']==0 for variants in selection['decisions'].values() for caps in variants.values() for c in caps.values())
            if scenario=='optimizer_ties':
                assert all(c['epoch']==1 and c['grid_index']==0 for variants in selection['decisions'].values() for caps in variants.values() for c in caps.values())
        # Exercise the entire canonical-zero policy assembly, including arm/policy aliases.
        initials={}
        for variant in ['M','U']:
            for w,l in CAPS:
                for d,s,p in CONFIRM:
                    name=f'{variant}-w{w}-d{d}-s{s}'; loss={64:3.,128:2.,256:1.}[w]
                    metrics={split:dict(loss=loss,**{kind:dict(loss=loss,accuracy=.5) for kind in ['shared','group','instance']})
                             for split in ['train','validation','test']}
                    initials[name]=dict(variant=variant,width=w,data_seed=d,seed=s,pretrain_seed=p,parameters=100,metrics=metrics)
        baseline=initial_rows(initials)
        zero_diags=[dict(name=r['name']+'-'+arm,epoch=0,mean_gain=0.,positive_mass=0.,negative_absolute_mass=0.,absolute_mass=0.,cancellation_ratio=None)
                    for r in baseline for arm in ['random','uniform']]
        policies,selected=policy_analysis(zero_selection,[],baseline,zero_diags)
        assert len(baseline)==54 and len(selected)==216 and audit_gates(policies,selected)['status']=='PASS'
        assert policies['cells']['M_J']['alias_of']=='M_R' and policies['cells']['U_J']['alias_of']=='U_R'
        assert all(not arm['useful_adaptation_met'] and arm['scaling']['met'] and arm['peak']['all_pairs']['undefined']==9
                   for cell in policies['cells'].values() for arm in cell['arms'].values())
    return dict(status='PASS',utc=utc(),measured_outcomes_read=False,checks=[
        'canonical zero winner and full-precision/tie ordering','undefined propagation and three-corpus statistics',
        'signed positive/negative cancellation and zero denominator','uniform/no-adaptation p undefined',
        'canonical zero component/Gram diagnostic','scaling can pass when utility fails at epoch zero',
        'zero primary total with positive rounded component total preserves null normalized comparison',
        'positive utility requires nonzero updates, all corpus gains and validation gate',
        'independent audit reconstructs runner choices/candidates on three fictitious scenarios',
        'all-zero canonical policy and arm aliases retain 54 initial cells and propagate undefined'])


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output'); args=parser.parse_args()
    if args.output: assert not Path(args.output).exists(), 'Preserve prior checks'
    result=validate()
    if args.output: write(Path(args.output),result)
    print(result,flush=True)


if __name__=='__main__': main()
