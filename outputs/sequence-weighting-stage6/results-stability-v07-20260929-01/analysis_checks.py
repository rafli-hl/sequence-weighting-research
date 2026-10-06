"""Stage6 outcome-independent fixtures; measured result directories are never read."""
import argparse
import copy
import json
import math
import tempfile
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import torch
from stage6 import ROOT,CAPS,EPOCHS,PANELS,CONFIRM,tuning_schedule,select,selection_key,utc,write
from diagnostics import fit,contrast
from analysis_core import desc,replicated,peak_verdict,signed_mass,utility_gate,scaling_gate,diagnostic_decompose,initial_rows
from analyze_stage6 import crossed_stats,panel_analysis,figures
from audit_stage6 import reconstruct_candidates


def validate():
    zero=dict(validation_nll=1.,epoch=0,lr=None,wd=None,grid_index=None)
    tied=dict(validation_nll=1.,epoch=1,lr=1e-5,wd=.1,grid_index=0)
    assert min([zero,tied],key=selection_key)==zero
    assert min([dict(tied,validation_nll=.999),zero],key=selection_key)['epoch']==1
    assert min([dict(tied,wd=1.),tied],key=selection_key)==tied
    assert desc([1.,None,3.])['mean'] is None and contrast(.1,None,.2) is None
    values=[dict(data_seed=d,seed=s,value=float(d)) for d in [1,2,3] for s in [1,2,3]]
    stats=replicated(values)
    assert stats['all_pairs']['n']==9 and stats['between_corpora']['n']==3
    assert stats['between_corpora']['mean']==2 and stats['between_corpora']['sd']==1
    assert peak_verdict(stats)=='survives'
    values[0]['value']=None
    assert replicated(values)['between_corpora']['mean'] is None
    assert peak_verdict(replicated(values))=='inconclusive_undefined'
    w=torch.tensor([.1,.2,1.,3.]); mass=signed_mass(torch.tensor([1.,-1.,2.,-2.]))
    assert mass['positive_mass']==mass['negative_absolute_mass']==3. and mass['cancellation_ratio']==0
    assert signed_mass(torch.zeros(4))['cancellation_ratio'] is None
    assert fit(w,torch.zeros(4))['p'] is None and fit(torch.ones(4),torch.ones(4))['p'] is None
    record=dict(loss=torch.ones(4),component_loss=torch.ones(4,3))
    zero_diag=diagnostic_decompose(w,record,record)
    assert zero_diag['primary']['p'] is None and zero_diag['primary']['total_gain']==0
    guarded=diagnostic_decompose(w,record,dict(loss=torch.ones(4),component_loss=torch.ones(4,3)-1e-7))
    assert guarded['allocation']['defined'] and guarded['allocation']['primary_cumulative_roundoff_max'] is None
    assert not guarded['allocation']['original_comparison_finite']; json.dumps(guarded,allow_nan=False)
    utility_rows=[dict(data_seed=d,seed=s,width=w,epoch=0,initial_test_nll=loss,test_nll=loss,
        initial_validation_nll=loss,validation_nll=loss) for d in [1,2,3] for s in [1,2,3] for w,loss in [(64,3.),(128,2.),(256,1.)]]
    assert scaling_gate(utility_rows)['met'] and not utility_gate([r for r in utility_rows if r['width']==64])['met']
    learned=[dict(r,epoch=1,test_nll=r['test_nll']-.1,validation_nll=r['validation_nll']-.1) for r in utility_rows]
    assert utility_gate([r for r in learned if r['width']==64])['met']
    failed=[dict(r,validation_nll=r['initial_validation_nll']+.1) for r in learned]
    assert not utility_gate([r for r in failed if r['width']==64])['met']
    # Known additive crossed fixture: panel effect 0/10/20/30, corpus effect 0/1/2.
    crossed_rows=[dict(panel=f'P{p+1}',data_seed=100+d,seed=s,value=10*p+d,name=f'shared-d{d}-s{s}',epoch=0,canonical_zero=True)
        for p in range(4) for d in range(3) for s in [1,2,3]]
    crossed=crossed_stats(crossed_rows,'value')
    assert crossed['descriptive_grand_mean']==16
    assert math.isclose(crossed['between_panel_marginals']['sd'],math.sqrt(500/3))
    assert crossed['between_corpus_marginals']['sd']==1
    assert crossed['between_panel_marginals']['n']==4 and crossed['between_corpus_marginals']['n']==3
    assert len(crossed['raw_paired_values'])==36 and crossed['unique_source_checkpoints']==9
    damaged=copy.deepcopy(crossed_rows); damaged[0]['value']=None
    assert crossed_stats(damaged,'value')['descriptive_grand_mean'] is None
    with tempfile.TemporaryDirectory(prefix='stage6-analysis-fixture-',dir=ROOT/'work') as temp:
        root=Path(temp); schedule=tuning_schedule()
        for scenario in ['different','zero_ties','optimizer_ties']:
            for c in schedule:
                folder=root/'runs'/c['name']; folder.mkdir(parents=True,exist_ok=True)
                history=[]
                for epoch in [0]+EPOCHS:
                    loss=2. if epoch==0 or scenario=='zero_ties' else 3.
                    if scenario=='different' and c['variant']=='U':
                        if c['panel']=='P1':
                            if c['grid_index']==0 and epoch==1: loss=1. if c['arm']=='random' else 4.
                            if c['grid_index']==1 and epoch==3: loss=1.5 if c['arm']=='random' else 0.
                        if c['panel']=='P2' and c['grid_index']==2 and epoch==5: loss=.5
                        if c['panel']=='P4' and c['grid_index']==0 and epoch==1: loss=1.
                    if scenario=='optimizer_ties' and epoch in [1,3]: loss=1.
                    history.append(dict(epoch=epoch,validation=dict(loss=loss)))
                write(folder/'history.json',history)
            selection=select(root); decisions,candidates=reconstruct_candidates(selection['inputs'])
            assert (decisions,candidates)==(selection['decisions'],selection['all_scores'])
            if scenario=='different':
                assert selection['planned_confirmation']==162
                assert all(c['variant']=='U' and c['panel'] is None for c in selection['run_schedule'])
                altered=copy.deepcopy(selection['inputs'])
                for row in altered:
                    if row['panel']=='P2' and row['epoch']>0: row['validation_nll']=1.5
                changed,_=reconstruct_candidates(altered)
                assert changed['P2']!=decisions['P2']
                assert all(changed[p]==decisions[p] for p in ['P1','P3','P4'])
            if scenario=='zero_ties':
                zero_selection=selection; assert selection['run_schedule']==[]
                assert all(c['epoch']==0 for panel in decisions.values() for policy in panel.values() for caps in policy.values() for c in caps.values())
            if scenario=='optimizer_ties':
                assert all(c['epoch']==1 and c['grid_index']==0 for panel in decisions.values() for policy in panel.values() for caps in policy.values() for c in caps.values())
        initials={}
        for variant in ['M','U']:
            for width,layers in CAPS:
                for d,s,p in CONFIRM:
                    name=f'{variant}-w{width}-d{d}-s{s}'; loss={64:3.,128:2.,256:1.}[width]
                    metrics={split:dict(loss=loss,**{kind:dict(loss=loss,accuracy=.5) for kind in ['shared','group','instance']})
                             for split in ['train','validation','test']}
                    initials[name]=dict(variant=variant,width=width,data_seed=d,seed=s,pretrain_seed=p,parameters=100,metrics=metrics)
        baselines=initial_rows(initials)
        diags=[dict(name=r['name']+'-'+arm,epoch=0,mean_gain=0.,positive_mass=0.,negative_absolute_mass=0.,absolute_mass=0.,cancellation_ratio=None)
            for r in baselines for arm in ['random','uniform']]
        summary,selected,gates=panel_analysis(zero_selection,[],baselines,diags)
        assert len(baselines)==54 and len(selected)==864
        assert summary['primary']['largest_no_adaptation_count']==4 and summary['primary']['middle_useful_adaptation_count']==0
        assert all(g['status']=='PASS' for g in gates.values())
        assert all(row['no_adaptation_count']==4 and row['settings'][0]['count']==4 for row in summary['choice_frequencies'])
        assert summary['panels']['P2']['cells']['U_R']['alias_across_panels']=='P1/U_R'
        assert all(not arm['useful_adaptation_met'] and arm['scaling']['met'] and arm['peak']['all_pairs']['undefined']==9
            for panel in summary['panels'].values() for cell in panel['cells'].values() for arm in cell['arms'].values())
        assert all(group['delta_test']['descriptive_grand_mean']==0 and group['delta_test']['unique_source_checkpoints']==9 and
                   group['p']['descriptive_grand_mean'] is None for group in summary['crossed'].values())
        # Smoke-render the degenerate all-zero case so no missing means can break figures.
        figures(root,summary,zero_selection)
        assert all((root/name).stat().st_size>1000 for name in ['selection-panels.png','crossed-gains.png','utility-panels.png','selected-fits.png'])
    return dict(status='PASS',utc=utc(),measured_outcomes_read=False,checks=[
        'canonical zero and deterministic tie rules','signed cancellation and no-adaptation/uniform undefined',
        'preserved null primary-normalization clarification','utility distinct from scaling',
        'independent candidate reconstruction on three fictitious scenarios','changing one panel cannot change other panels',
        'cross-panel optimizer union deduplicated','known crossed marginals: 4 panels and 3 shared corpora, no pooled IID spread',
        'undefined crossed means propagate','all-zero policy aliases retain only 54 initial cells',
        'selection frequency and middle-utility recurrence counts','all-zero figures render without missing-value substitution'])


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',required=True); args=parser.parse_args()
    path=Path(args.output); assert not path.exists(),'Preserve prior fixture checks'
    result=validate(); write(path,result); print(result,flush=True)


if __name__=='__main__': main()
