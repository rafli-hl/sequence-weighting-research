"""Prospective signed-gain cumulative fit; no computation on import."""
import math
from common import require
GRID_N=1024
PROFILE_DELTA_RMS=.002
PARAM_TOL=1e-5
OBJECTIVE_ABS=1e-10
OBJECTIVE_REL=1e-8
MIN_P=math.log(4)/math.log(1000)

def problem(q,gains):
    q=[float(x) for x in q]; g=[float(x) for x in gains]
    require(len(q)==len(g)>1 and all(math.isfinite(x) and x>0 for x in q),'Invalid target')
    require(all(math.isfinite(x) for x in g),'Nonfinite gain')
    if max(q)-min(q)<1e-12: return None,'constant_target'
    if math.fsum(g)<=1e-10: return None,'nonpositive_or_tiny_total_gain'
    order=sorted(range(len(q)),key=lambda i:(q[i],i))
    qs=[q[i] for i in order]; gs=[g[i]/math.fsum(g) for i in order]
    ranks=[]; start=0
    while start<len(qs):
        end=start+1
        while end<len(qs) and qs[end]==qs[start]: end+=1
        ranks.extend([(start+end)/2/len(qs)]*(end-start)); start=end
    return (qs,gs,ranks),None

def evaluate(problem,p):
    q,g,ranks=problem
    z=[p*math.log(x) for x in q]; pivot=max(z)
    z=[math.exp(x-pivot) for x in z]; denom=math.fsum(z)
    d=[a-b/denom for a,b in zip(g,z)]
    # Integrate squared suffix masses over the exact min-rank kernel.
    suffix=math.fsum(d); previous=0.; terms=[]
    for rank,residual in zip(ranks,d):
        terms.append((rank-previous)*suffix*suffix)
        suffix-=residual; previous=rank
    value=math.fsum(terms)
    require(math.isfinite(value) and value>=0,'Invalid cumulative objective')
    return value

def profile_identified(profile,p,best):
    rms=math.sqrt(best); near=[x for x,j in profile if math.sqrt(j)<=rms+PROFILE_DELTA_RMS]
    near.append(p)
    return min(near)>=.75*p and max(near)<=1.25*p

def fit(q,gains,guard):
    prob,reason=problem(q,gains)
    if reason: return dict(p=None,reason=reason,profile=[],objective=None,rms=None,identified=False)
    grid=[8*i/GRID_N for i in range(GRID_N+1)]
    profile=[]
    for i,p in enumerate(grid):
        if i%16==0: guard.check()
        profile.append([p,evaluate(prob,p)])
    candidates=[profile[0],profile[-1]]
    phi=(math.sqrt(5)-1)/2
    flat=max(j for _,j in profile)-min(j for _,j in profile)<=1e-12
    for j in (() if flat else range(1,GRID_N)):
        if profile[j][1]<=profile[j-1][1] and profile[j][1]<=profile[j+1][1]:
            lo,hi=grid[j-1],grid[j+1]
            a=hi-phi*(hi-lo); b=lo+phi*(hi-lo)
            fa,fb=evaluate(prob,a),evaluate(prob,b)
            for k in range(64):
                guard.check()
                if hi-lo<=1e-10: break
                if fa<fb: hi,b,fb=b,a,fa; a=hi-phi*(hi-lo); fa=evaluate(prob,a)
                else: lo,a,fa=a,b,fb; b=lo+phi*(hi-lo); fb=evaluate(prob,b)
            p=(lo+hi)/2; candidates.append([p,evaluate(prob,p)])
    p,best=min(candidates,key=lambda row:(row[1],row[0]))
    # Profile criterion is finite-grid identification, not statistical confidence.
    offsets=[max(0.,.75*p),min(8.,1.25*p)]
    edge_identified=all(math.sqrt(evaluate(prob,x))>math.sqrt(best)+PROFILE_DELTA_RMS for x in offsets)
    identified=profile_identified(profile+candidates,p,best) and edge_identified
    interior=1e-6<p<8-1e-6
    return dict(p=p,reason=None,objective=best,rms=math.sqrt(best),
        p0_rms=math.sqrt(evaluate(prob,0)),profile=profile,candidates=candidates,
        mean_gain=math.fsum(float(x) for x in gains)/len(gains),
        identified=identified,interior=interior,minimum_p_met=p>=MIN_P,
        profile_delta_rms=PROFILE_DELTA_RMS,profile_edges=offsets,
        profile_edge_objectives=[evaluate(prob,x) for x in offsets])

def gates(rows):
    require(len(rows)==6,'Six nested calibration rows required')
    corpus=[]; checks=[]
    def add(identity,name,value,threshold,passed):
        checks.append(dict(identity=identity,gate=name,value=value,threshold=threshold,passed=bool(passed)))
    for row in rows:
        f=row['fit']; ident=row['identity']
        add(ident,'mean_R_gain',row['mean_R_gain'],.05,row['mean_R_gain']>=.05)
        add(ident,'defined_interior_identified',f['p'],None,f['p'] is not None and f['interior'] and f['identified'])
        add(ident,'minimum_p',f['p'],MIN_P,f['p'] is not None and f['p']>=MIN_P)
        add(ident,'fit_RMS',f['rms'],.02,f['rms'] is not None and f['rms']<=.02)
    for d in sorted(set(row['data_seed'] for row in rows)):
        pair=[row for row in rows if row['data_seed']==d]; require(len(pair)==2,'Nested pair')
        exponents=[row['fit']['p'] for row in pair]
        p=None if any(x is None for x in exponents) else math.fsum(exponents)/2
        improvement=None if any(row['fit']['p'] is None for row in pair) else math.fsum(row['fit']['p0_rms']-row['fit']['rms'] for row in pair)/2
        ug=math.fsum(row['U_validation_gain'] for row in pair)/2
        rg=math.fsum(row['R_validation_gain'] for row in pair)/2
        cost=math.fsum(row['R_minus_U_validation'] for row in pair)/2
        add(str(d),'fit_improvement_vs_p0',improvement,.01,improvement is not None and improvement>.01)
        add(str(d),'U_validation_gain',ug,0,ug>0)
        add(str(d),'R_validation_gain',rg,0,rg>0)
        add(str(d),'R_validation_cost',cost,.01,cost<.01)
        corpus.append(dict(data_seed=d,p=p,fit_improvement=improvement,U_validation_gain=ug,R_validation_gain=rg,R_validation_cost=cost))
    pcal=None if any(row['p'] is None for row in corpus) else math.fsum(row['p'] for row in corpus)/3
    loo=[]
    for row in rows:
        p=row['fit']['p']; stable=pcal is not None and p is not None and abs(p-pcal)<=.25*pcal
        add(row['identity'],'seed_stability',p,.25*pcal if pcal is not None else None,stable)
    for i,c in enumerate(corpus):
        others=[x['p'] for j,x in enumerate(corpus) if j!=i]
        p=None if any(x is None for x in others) else math.fsum(others)/2
        loo.append(dict(omitted_corpus=c['data_seed'],p=p))
        add(str(c['data_seed']),'leave_one_corpus_out_stability',p,.25*pcal if pcal is not None else None,pcal is not None and p is not None and abs(p-pcal)<=.25*pcal)
    passed=all(x['passed'] for x in checks)
    return dict(status='CALIBRATION_PASSED_PENDING_CONFIRMATION_APPROVAL' if passed else 'CALIBRATION_FAILED',
                pcal=pcal,corpus=corpus,leave_one_out=loo,checks=checks,
                confirmation_authorized=False,confirmation_implementation_present=False)
