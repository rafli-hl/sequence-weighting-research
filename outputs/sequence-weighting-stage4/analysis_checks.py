"""Small outcome-independent checks of missingness, paired contrasts and aliases."""
import ast
import math
from analyze_stage4 import desc,replicated,arithmetic,verdict,policy_analysis
from stage4 import HERE,ROOT,CAPS,CONFIRM,VARIANTS,write,utc

for path in HERE.glob('*.py'): ast.parse(path.read_text(encoding='utf-8'))
assert desc([1,None,3])['mean'] is None and desc([1,None,3])['undefined']==1
assert arithmetic([(None,1),(2,-1)]) is None
values=[dict(data_seed=d,seed=s,value=float(i)) for i,(d,s,p) in enumerate(CONFIRM)]
stats=replicated(values)
assert stats['between_corpora']['n']==3 and stats['between_corpora']['mean']==4
assert stats['between_corpora']['sd']==3
# Hand-constructed paired 2x2 arithmetic: optimizer effect differs with duration.
assert arithmetic([(12,1),(7,-1),(4,-1),(2,1)])==3

# A fictitious fixture uses no measured outcome or real per-sequence loss.
decisions={v:{str(w):dict(grid_index=0,epoch=10) for w,l in CAPS} for v in VARIANTS}
rows=[]
for v in VARIANTS:
    for w,l in CAPS:
        for d,s,p in CONFIRM:
            for arm in ['random','uniform']:
                for e in [1,3,10,30,60]:
                    rank=[64,128,256].index(w)
                    exponent=([.1,.3,.2][rank]+(.02 if v=='U' and w==128 else 0)) if arm=='random' else None
                    rows.append(dict(phase='confirm',variant=v,width=w,data_seed=d,seed=s,arm=arm,grid_index=0,epoch=e,
                        p=exponent,objective=.01,train_nll=2.,validation_nll=2.-rank/10,test_nll=2.-rank/10,
                        initial_validation_nll=3.,train_instance_accuracy=.2,clipping=1.,total_gain=1.,negative_gain_fraction=.1))
summary,_,_=policy_analysis(dict(decisions=decisions),rows)
effect=summary['effects']['primary_U_minus_M_F_C30']['between_corpora']['mean']
assert math.isclose(effect,.02,abs_tol=1e-14)
assert summary['cells']['U_F_C30']['arms']['random']['verdict']=='survives'
assert summary['cells']['U_T_ET']['alias_of']=='U_F_C10'
assert summary['cells']['U_T_ET']['arms']['uniform']['verdict']=='undefined_uniform'
assert summary['cells']['U_T_ET']['arms']['random']['generalization_met']
assert summary['effects']['U_interaction']['between_corpora']['mean']==0
write(ROOT/'work/runs/baseline-v05-20260929-01/ANALYSIS_CHECKS.json',dict(status='PASS',utc=utc(),
    no_experimental_outcomes_used=True,checks=['all sources parse','undefined propagation','3 corpus replications not 9 datasets',
    'known paired factorial arithmetic','known intervention contrast on synthetic fixture','identical policy aliases',
    'uniform undefined and generalization gate']))
print('PASS: outcome-independent analysis checks',flush=True)
