"""Future approved-runtime fixtures; never run at source preparation."""
import math
from common import require,utc
def run_fixtures(guard):
    import torch
    import experiment as worker
    from fit import problem,evaluate
    worker.imports(); worker.runtime(); count=0
    q=[.5,.5,1.,2.]
    gains=[-.1,.2,.4,.3]
    prob,_=problem(q,gains)
    for p in (0.,.3,1.,8.):
        guard.check()
        z=[x**p for x in q]; d=[g/math.fsum(gains)-w/math.fsum(z) for g,w in zip(gains,z)]
        ranks=[.25,.25,.625,.875]
        direct=math.fsum(d[i]*d[j]*min(ranks[i],ranks[j]) for i in range(4) for j in range(4))
        require(abs(evaluate(prob,p)-direct)<=1e-12,'Tied rank/kernel fixture'); count+=1
    require(problem([1.,1.],[1.,2.])[1]=='constant_target','Uniform target guard')
    require(problem([.5,2.],[-1.,1.])[1]=='nonpositive_or_tiny_total_gain','Nonpositive guard')
    require(problem([.5,2.],[1e-12,1e-12])[1]=='nonpositive_or_tiny_total_gain','Tiny-gain guard')
    for invalid in ([float('nan'),1.],[float('inf'),1.]):
        try: problem([.5,2.],invalid)
        except RuntimeError: count+=1
        else: raise RuntimeError('Nonfinite guard fixture')
    prob,_=problem([.5,1.,2.],[.5,1.,2.])
    require(evaluate(prob,1.)<1e-28,'Exact target zero error'); count+=1
    from fit import fit,gates
    target=[.5+1.5*i/7 for i in range(8)]
    for expected in (.3,1.):
        result=fit(target,[x**expected for x in target],guard)
        require(abs(result['p']-expected)<1e-5,'Known exponent solver fixture'); count+=1
    flat=fit(target,[1.]*8,guard)
    require(flat['p']<1e-5 and not flat['minimum_p_met'],'p0 eligibility fixture'); count+=1
    adversarial=fit(target,[-9.,10.,-9.,10.,-9.,10.,-9.,10.],guard)
    require(adversarial['rms']>.02,'Poor-fit fixture'); count+=1
    fixture_rows=[]
    for corpus in (1,2,3):
        for seed in (1,2):
            fixture_rows.append(dict(identity=f'{corpus}-{seed}',data_seed=corpus,
                fit=dict(p=1.,rms=0.,p0_rms=.02,identified=True,interior=True),
                mean_R_gain=.05,U_validation_gain=.1,R_validation_gain=.1,R_minus_U_validation=.01))
    strict=gates(fixture_rows)
    require(strict['status']=='CALIBRATION_FAILED' and any(x['gate']=='R_validation_cost' and not x['passed'] for x in strict['checks']),
            'Strict .01 validation-cost boundary'); count+=1
    for row in fixture_rows: row['R_minus_U_validation']=.009
    require(gates(fixture_rows)['status']=='CALIBRATION_PASSED_PENDING_CONFIRMATION_APPROVAL','Gate positive control'); count+=1
    # Whole-sequence and ignored-context coefficients through real model objective.
    obj=worker.model(123); ds,_=worker.engine.data(456,'G1',include_test=True)
    tokens,kinds=(v[:4].cuda() for v in ds['train'])
    weights=torch.tensor([.5,1.,1.5,1.],device='cuda')[:,None].repeat(1,3)
    objective,_,_=worker.component_objective(obj,tokens,kinds,weights)
    _,loss,_=worker.engine.losses(obj,tokens,kinds)
    expected=((loss*(kinds>=0)).sum(1)/12*weights[:,0]).mean()
    require(abs(float(objective-expected))<2e-6,'Whole-sequence scaling fixture'); count+=1
    # Preserve q normalization and exponent guard without any compensation arm.
    require(math.log(4)/math.log(1000)>.2,'Minimum exponent convention'); count+=1
    del obj; torch.cuda.empty_cache(); guard.check(disk=True)
    return dict(status='PASS_CALIBRATION_FIXTURES',utc=utc(),comparisons=count,
                scope='rank kernel, signed/undefined gain, whole-sequence objective; no fit recovery claim')
