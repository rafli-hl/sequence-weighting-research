"""Independent derivative search and decimal/kernel checks; imports no candidate fit."""
import math
from decimal import Decimal,localcontext
import numpy as np
from common import require
MIN_P=math.log(4)/math.log(1000)
def audit_fit(q,gains,candidate,guard):
    q=np.asarray(q,dtype=np.float64); g=np.asarray(gains,dtype=np.float64)
    require(q.shape==g.shape and np.isfinite(q).all() and np.isfinite(g).all() and (q>0).all(),'Audit target/gain shape')
    reason='constant_target' if q.max()-q.min()<1e-12 else 'nonpositive_or_tiny_total_gain' if math.fsum(g)<=1e-10 else None
    if reason:
        require(candidate['p'] is None and candidate['reason']==reason,'Guard classification mismatch')
        return dict(p=None,reason=reason,rms=None,identified=False,interior=False,p0_rms=None,profile=[])
    indices=np.argsort(q,kind='stable'); x=q[indices]; y=g[indices]; logs=np.log(x)
    ranks=np.empty(len(x)); i=0
    while i<len(x):
        j=i+1
        while j<len(x) and x[j]==x[i]: j+=1
        ranks[i:j]=(i+j)/(2*len(x)); i=j
    delta=np.diff(np.concatenate(([0.],ranks))); normalized=y/math.fsum(y)
    def values(p):
        z=np.exp(float(p)*logs-max(float(p)*logs)); mass=z/math.fsum(z)
        residual=normalized-mass
        suffix=np.cumsum(residual[::-1])[::-1]
        derivative=-mass*(logs-np.dot(mass,logs))
        dsuffix=np.cumsum(derivative[::-1])[::-1]
        return float(np.dot(delta,suffix*suffix)),float(2*np.dot(delta,suffix*dsuffix))
    grid=np.linspace(0.,8.,1025); profile=[]; derivatives=[]
    for j,p in enumerate(grid):
        if j%16==0: guard.check()
        value,derivative=values(p); profile.append([float(p),value]); derivatives.append(derivative)
    candidates=[profile[0],profile[-1]]
    for j in range(1024):
        if derivatives[j]==0: candidates.append(profile[j])
        if derivatives[j]*derivatives[j+1]<0:
            lo,hi=float(grid[j]),float(grid[j+1]); sign=derivatives[j]
            for _ in range(40):
                guard.check(); mid=(lo+hi)/2; _,dm=values(mid)
                if dm==0 or hi-lo<1e-10: lo=hi=mid; break
                if sign*dm>0: lo=mid
                else: hi=mid
            p=(lo+hi)/2; candidates.append([p,values(p)[0]])
    p,best=min(candidates,key=lambda a:(a[1],a[0]))
    require(candidate['p'] is not None and abs(candidate['p']-p)<=1e-5,'Bounded-search parameter disagreement')
    require(abs(candidate['objective']-best)<=1e-10+1e-8*abs(best),'Search objective disagreement')
    # Independent direct dense min-rank kernel, not prefix identity alone.
    K=np.minimum.outer(ranks,ranks); z=np.exp(p*logs-max(p*logs)); d=normalized-z/math.fsum(z)
    direct=float(d@K@d)
    require(abs(direct-best)<=1e-10+1e-8*abs(best),'Direct kernel disagreement')
    def decimal_value(point,precision):
        with localcontext() as ctx:
            ctx.prec=precision
            xd=[Decimal.from_float(float(a)) for a in x]; yd=[Decimal.from_float(float(a)) for a in y]
            power=Decimal.from_float(float(point)); weights=[(power*a.ln()).exp() for a in xd]
            ds=[a/sum(yd)-b/sum(weights) for a,b in zip(yd,weights)]
            suffix=Decimal(0); val=Decimal(0)
            for j in range(len(ds)-1,-1,-1):
                suffix+=ds[j]
                step=Decimal.from_float(float(ranks[j]))-(Decimal.from_float(float(ranks[j-1])) if j else Decimal(0))
                val+=step*suffix*suffix
            return +val
    probes=sorted(set([0.,p,float(candidate['p']),max(0.,.75*p),min(8.,1.25*p),8.]))
    checked=[]
    for point in probes:
        guard.check(); a=decimal_value(point,35); b=decimal_value(point,60)
        require(abs(a-b)<=Decimal('1e-28')*max(Decimal(1),abs(b)),'Decimal precision unresolved')
        require(abs(values(point)[0]-float(b))<=1e-10+1e-8*abs(float(b)),'Decimal objective disagreement')
        checked.append(dict(p=point,decimal35=str(a),decimal60=str(b)))
    near=[v for v,j in profile+candidates if math.sqrt(j)<=math.sqrt(best)+.002]+[p]
    edges=[max(0.,.75*p),min(8.,1.25*p)]
    identified=min(near)>=.75*p and max(near)<=1.25*p and all(math.sqrt(values(v)[0])>math.sqrt(best)+.002 for v in edges)
    require(identified==candidate['identified'],'Profile identification mismatch')
    for cp,cj in candidate['profile']:
        require(abs(cj-values(cp)[0])<=1e-10+1e-8*abs(cj),'Full candidate profile disagreement')
    return dict(p=p,reason=None,rms=math.sqrt(best),p0_rms=math.sqrt(values(0)[0]),
        objective=best,identified=identified,interior=1e-6<p<8-1e-6,profile=profile,
        candidates=candidates,decimal_checks=checked)

def audit_gates(rows):
    # Independently form equal nested/corpus estimands and boolean gate records.
    seed_records=[]; corpus_records=[]
    for r in rows:
        f=r['fit']; p=f['p']; gain=r['mean_R_gain']
        flags=dict(mean_gain=gain>=.05,interior_identified=p is not None and f['interior'] and f['identified'],
                   minimum_p=p is not None and p>=MIN_P,fit_RMS=f['rms'] is not None and f['rms']<=.02)
        seed_records.append(dict(identity=r['identity'],data_seed=r['data_seed'],p=p,gates=flags))
    for d in sorted({r['data_seed'] for r in rows}):
        group=[r for r in rows if r['data_seed']==d]; require(len(group)==2,'Audit nested count')
        ps=[r['fit']['p'] for r in group]
        cp=sum(ps)/2 if all(p is not None for p in ps) else None
        imp=sum(r['fit']['p0_rms']-r['fit']['rms'] for r in group)/2 if cp is not None else None
        ug=sum(r['U_validation_gain'] for r in group)/2; rg=sum(r['R_validation_gain'] for r in group)/2
        cost=sum(r['R_minus_U_validation'] for r in group)/2
        corpus_records.append(dict(data_seed=d,p=cp,improvement=imp,U_validation_gain=ug,
            R_validation_gain=rg,cost=cost,gates=dict(improvement=imp is not None and imp>.01,U_gain=ug>0,R_gain=rg>0,cost=cost<.01)))
    pcal=sum(c['p'] for c in corpus_records)/3 if all(c['p'] is not None for c in corpus_records) else None
    for r in seed_records:
        r['gates']['seed_stability']=pcal is not None and r['p'] is not None and abs(r['p']-pcal)<=.25*pcal
    for c in corpus_records:
        others=[x['p'] for x in corpus_records if x['data_seed']!=c['data_seed']]
        value=sum(others)/2 if all(x is not None for x in others) else None
        c['leave_one_out']=value
        c['gates']['LOO_stability']=pcal is not None and value is not None and abs(value-pcal)<=.25*pcal
    passed=all(all(r['gates'].values()) for r in seed_records+corpus_records)
    return dict(status='CALIBRATION_PASSED_PENDING_CONFIRMATION_APPROVAL' if passed else 'CALIBRATION_FAILED',
        pcal=pcal,seed_records=seed_records,corpus_records=corpus_records,confirmation_authorized=False)
