"""Independent token-reduction/full-population audit; never imports diagnose."""
import argparse
import gc
import math
import statistics
from pathlib import Path
import torch
from common import (HERE, ROOT, RUN, OUT, STATES, EPS, Guard, require, read, write, sha,
                    utc, verify_manifest, verify_inputs, binding, finite)
from inputs import environment, load_pair, load_model, tensor_hash, state_binding

KEYS=('validation_gradient_norm','uniform_gradient_norm','extra_gradient_norm',
      'dot_validation_extra','cosine','local_descent_slope','extra_to_uniform_norm',
      'projection_relative_uniform','extra_batch_population_variance',
      'uniform_batch_population_variance','extra_batch_rms','uniform_batch_rms',
      'extra_rms_to_uniform_norm','extra_to_uniform_batch_rms','extra_signal_to_dispersion')

class Checks:
    def __init__(self): self.groups={}; self.count=0
    def add(self,name,error,allowed):
        require(math.isfinite(error) and math.isfinite(allowed) and allowed>0,'Invalid audit comparison')
        value=self.groups.setdefault(name,dict(checks=0,max_absolute_error=0.,max_tolerance_fraction=0.))
        value['checks']+=1; self.count+=1
        value['max_absolute_error']=max(value['max_absolute_error'],error)
        value['max_tolerance_fraction']=max(value['max_tolerance_fraction'],error/allowed)
        require(error<=allowed,'Audit tolerance failed: '+name+' error='+str(error)+' allowed='+str(allowed))
    def scalar(self,name,observed,reference,atol=2e-6,rtol=2e-4):
        if observed is None or reference is None:
            require(observed is None and reference is None,'Undefined scalar mismatch: '+name); return
        self.add(name,abs(observed-reference),atol+rtol*abs(reference))
    def vector(self,name,observed,reference,atol=2e-6,rtol=2e-4):
        require(observed.shape==reference.shape and torch.isfinite(observed).all().item() and
                torch.isfinite(reference).all().item(),'Gradient vector shape/nonfinite')
        self.add(name,float((observed-reference).abs().max()),atol+rtol*float(reference.abs().max()))

def derivative(value,params,keep=False):
    require(torch.isfinite(value).item(),'Nonfinite independent objective')
    parts=torch.autograd.grad(value,params,retain_graph=keep,allow_unused=False,create_graph=False)
    vec=torch.cat(tuple(g.reshape(-1).detach() for g in parts)).double()
    require(torch.isfinite(vec).all().item() and all(p.grad is None for p in params),'Invalid/residual gradient')
    return vec

def token_nll(obj,tokens):
    logits=obj(tokens[:,:-1]); targets=tokens[:,1:]
    return -logits.log_softmax(-1).gather(-1,targets.unsqueeze(-1)).squeeze(-1)

def train_roots(nll,labels,weights):
    count=len(nll)
    # Uniform is the mean of all12 answer-token NLLs per sequence, independent
    # of diagnostic's three component means. Delta is direct token coefficients.
    uniform=nll.masked_select(labels>=0).mean()
    instance=(labels==2).to(nll.dtype)
    coefficients=(weights-1).unsqueeze(1)*instance/(12*count)
    extra=(nll*coefficients).sum()
    weighted=(nll*((labels>=0).to(nll.dtype)/(12*count)+coefficients)).sum()
    return uniform,weighted,extra

def magnitude(vec): return math.sqrt(float((vec*vec).sum()))

def nullable(top,bottom,label,guards,key):
    if bottom<=EPS: guards[key]=label; return None
    return top/bottom

def summary(gnv,gnu,gnd,dot,vdelta,vuniform):
    guards={}; cosine=None; projection=None
    if gnv<=EPS or gnd<=EPS: guards['cosine']='validation_or_extra_norm_le_1e-12'
    else: cosine=dot/(gnv*gnd)
    if gnv<=EPS or gnu<=EPS: guards['projection_relative_uniform']='validation_or_uniform_norm_le_1e-12'
    else: projection=dot/(gnv*gnu)
    sd=math.sqrt(vdelta); su=math.sqrt(vuniform)
    metrics=dict(validation_gradient_norm=gnv,uniform_gradient_norm=gnu,extra_gradient_norm=gnd,
        dot_validation_extra=dot,cosine=cosine,local_descent_slope=-dot,
        extra_to_uniform_norm=nullable(gnd,gnu,'uniform_norm_le_1e-12',guards,'extra_to_uniform_norm'),
        projection_relative_uniform=projection,extra_batch_population_variance=vdelta,
        uniform_batch_population_variance=vuniform,extra_batch_rms=sd,uniform_batch_rms=su,
        extra_rms_to_uniform_norm=nullable(sd,gnu,'uniform_norm_le_1e-12',guards,'extra_rms_to_uniform_norm'),
        extra_to_uniform_batch_rms=nullable(sd,su,'uniform_batch_rms_le_1e-12',guards,'extra_to_uniform_batch_rms'),
        extra_signal_to_dispersion=nullable(gnd,sd,'extra_batch_rms_le_1e-12',guards,'extra_signal_to_dispersion'))
    return metrics,guards

def fixtures(checks):
    # Analytic coefficient construction does not use autograd or component means.
    labels=torch.tensor([[-1]+[0]*4+[1]*4+[2]*4]*2)
    targets=torch.arange(26).reshape(2,13)%3
    logits=(torch.arange(78,dtype=torch.float64).reshape(2,13,3)/200).requires_grad_()
    weights=torch.tensor([.5,1.5],dtype=torch.float64)
    base=(labels>=0).double()/24
    delta=(labels==2).double()*(weights-1).unsqueeze(1)/24
    group=(labels==1).double()/8
    coefficients={'U':base,'I':base+delta,'D':delta,'V':group}
    target=torch.zeros_like(logits).scatter_(-1,targets.unsqueeze(-1),1.)
    analytic_residual=logits.detach().softmax(-1)-target
    direction=torch.linspace(-.4,.5,78,dtype=torch.float64).reshape_as(logits)
    gradients={}
    for key,coef in coefficients.items():
        def value(x): return (-(x.log_softmax(-1).gather(-1,targets.unsqueeze(-1)).squeeze(-1))*coef).sum()
        gradient=torch.autograd.grad(value(logits),logits)[0]; gradients[key]=gradient
        checks.vector('fixture_analytic_softmax_'+key,gradient,analytic_residual*coef.unsqueeze(-1),atol=1e-12,rtol=0)
        eta=1e-5
        slope=float((value(logits.detach()+eta*direction)-value(logits.detach()-eta*direction))/(2*eta))
        checks.scalar('fixture_centered_difference_'+key,slope,float((gradient*direction).sum()),atol=1e-8,rtol=0)
        require(torch.equal(gradient[labels==-1],torch.zeros_like(gradient[labels==-1])),'Ignored context derivative')
    checks.vector('fixture_I_minus_U',gradients['I']-gradients['U'],gradients['D'],atol=1e-12,rtol=0)
    zero_root=(-(logits.log_softmax(-1).gather(-1,targets.unsqueeze(-1)).squeeze(-1))*torch.zeros_like(delta)).sum()
    zero_extra=torch.autograd.grad(zero_root,logits)[0]
    checks.vector('fixture_uniform_weights_zero_extra',zero_extra,torch.zeros_like(zero_extra),atol=1e-12,rtol=0)
    omitted_third=delta*3
    checks.vector('fixture_one_third_scaling',analytic_residual*omitted_third.unsqueeze(-1),gradients['D']*3,atol=1e-12,rtol=0)
    theta=torch.tensor([1.,-2.],dtype=torch.float64,requires_grad=True)
    val=.5*theta[0].square(); gv=torch.autograd.grad(val,theta)[0]
    for sign in (-1.,1.,0.):
        extra=sign*theta[0]; gd=torch.autograd.grad(extra,theta)[0]
        dot=float((gv*gd).sum()); step=theta.detach()-1e-6*gd
        observed=float((.5*step[0].square()-val.detach())/1e-6)
        checks.scalar('fixture_ordinary_descent_sign',observed,-dot,atol=1e-6,rtol=0)
        require((sign==-1 and observed>0) or (sign==1 and observed<0) or (sign==0 and observed==0),
                'Ordinary-descent sign convention')
    metrics,guards=summary(0.,0.,0.,0.,0.,0.)
    require(metrics['cosine'] is None and metrics['extra_to_uniform_norm'] is None and
            metrics['extra_signal_to_dispersion'] is None and len(guards)==6,'Zero-norm undefined guards')
    require(metrics['dot_validation_extra']==0 and metrics['local_descent_slope']==0,'Zero dot preservation')
    fake=[]
    for state in STATES:
        for ci in range(5):
            for offset in (1,51):
                values={k:1. for k in KEYS}
                if state=='initial' and ci==0 and offset==1: values['cosine']=None
                fake.append(dict(state=state,data_seed=91420101+ci,seed=91440100+ci*100+offset,metrics=values))
    test_corpus,test_cohort,_=independent_aggregation(fake)
    require(test_corpus[0]['metrics']['cosine'] is None and test_corpus[0]['defined_seed_counts']['cosine']==1 and
            test_cohort[0]['metrics']['cosine']['mean'] is None and
            test_cohort[0]['metrics']['cosine']['defined_corpora']==4,'Strict null aggregation')
    try: finite(float('nan'))
    except RuntimeError: pass
    else: raise RuntimeError('Nonfinite scalar was not rejected')
    return dict(status='PASS',analytic_softmax=True,ignored_context=True,one_third_scaling=True,
        full_validation_group_normalization=True,centered_logit_differences=True,
        ordinary_descent_adverse_favorable_zero=True,uniform_weights_zero_extra=True,
        zero_norm_undefined=True,strict_null_aggregation=True,
        nonfinite_rejected=True)

def independent_aggregation(rows):
    def mean(values): return None if None in values else statistics.mean(values)
    corpus=[]; cohort=[]; changes=[]
    for state in STATES:
        for d in range(91420101,91420106):
            selected=[r for r in rows if r['state']==state and r['data_seed']==d]
            require(len(selected)==2,'Audit two seeds per corpus')
            corpus.append(dict(state=state,data_seed=d,seed_count=2,
                metrics={k:mean([r['metrics'][k] for r in selected]) for k in KEYS},
                defined_seed_counts={k:len([r for r in selected if r['metrics'][k] is not None]) for k in KEYS}))
        selected=[r for r in corpus if r['state']==state]; result={}
        for key in KEYS:
            values=[r['metrics'][key] for r in selected]; defined=[v for v in values if v is not None]
            valid=len(defined)==5
            result[key]=dict(mean=mean(values),defined_corpora=len(defined),
                corpus_sd=statistics.stdev(values) if valid else None,
                minimum=min(values) if valid else None,maximum=max(values) if valid else None,
                negative_corpora=len([v for v in defined if v<0]),positive_corpora=len([v for v in defined if v>0]),
                zero_corpora=len([v for v in defined if v==0]))
        cohort.append(dict(state=state,independent_corpus_count=5,metrics=result))
    for state in STATES[1:]:
        for d in range(91420101,91420106):
            selected=[r for r in rows if r['state']==state and r['data_seed']==d]; contrasts={k:[] for k in KEYS}
            for row in selected:
                start=next(r for r in rows if r['state']=='initial' and r['data_seed']==d and r['seed']==row['seed'])
                for key in KEYS:
                    a=row['metrics'][key]; b=start['metrics'][key]
                    contrasts[key].append(None if a is None or b is None else a-b)
            changes.append(dict(state=state,data_seed=d,contrast='F10 minus SAME-seed initial',
                                metrics={k:mean(v) for k,v in contrasts.items()}))
    return corpus,cohort,changes

def compare_tree(checks,name,old,new):
    if isinstance(new,dict):
        require(isinstance(old,dict) and set(old)==set(new),'Summary keys: '+name)
        for key,value in new.items(): compare_tree(checks,name+'/'+key,old[key],value)
    elif isinstance(new,list):
        require(isinstance(old,list) and len(old)==len(new),'Summary rows: '+name)
        for i,value in enumerate(new): compare_tree(checks,name+'/'+str(i),old[i],value)
    elif isinstance(new,float): checks.scalar('aggregation',old,new,atol=2e-4 if 'cosine' in name or 'projection' in name else 2e-6)
    else: require(old==new,'Summary discrete/null: '+name)

def audit_state(row,data,weights,order,guard,checks):
    saved=read(RUN/'states'/(row['panel_id']+'.json')); batch_saved=read(RUN/'batches'/(row['panel_id']+'.json'))
    require(saved['panel_id']==row['panel_id'] and saved['checkpoint_sha256']==row['checkpoint_sha256'] and
            saved['parameter_state_unchanged'] is True and len(batch_saved)==16,'Saved state identity/count')
    require(saved['data_seed']==row['data_seed'] and saved['seed']==row['seed'] and saved['state']==row['state'] and
            saved['batch_count']==16,'Saved state cohort metadata')
    obj,named=load_model(row); params=tuple(p for _,p in named); before=state_binding(obj)
    require(saved['parameter_layout']==[dict(name=n,shape=list(p.shape),numel=p.numel()) for n,p in named],
            'Saved gradient coordinate layout')
    vx,vk=(x.cuda() for x in data['validation']); guard.check()
    vloss=token_nll(obj,vx).masked_select(vk==1).mean(); gv=derivative(vloss,params)
    val_value=float(vloss.detach()); del vx,vk,vloss
    tx,tk=(x.cuda() for x in data['train']); guard.check()
    nll=token_nll(obj,tx); uroot,iroot,droot=train_roots(nll,tk,weights.cuda())
    gu=derivative(uroot,params,keep=True); gi=derivative(iroot,params,keep=True); gd=derivative(droot,params)
    checks.vector('real_I_minus_U',gi-gu,gd)
    u_value=float(uroot.detach()); d_value=float(droot.detach()); del tx,tk,nll,uroot,iroot,droot,gi
    vn=magnitude(gv); un=magnitude(gu); dn=magnitude(gd); dot=float((gv*gd).sum())
    means_u=torch.zeros_like(gu); means_d=torch.zeros_like(gd); centered_u=[]; centered_d=[]; independent_batches=[]
    for batch in range(16):
        guard.check(); obj.zero_grad(set_to_none=True)
        ids=order.narrow(0,batch*32,32)
        x=data['train'][0][ids].cuda(); labels=data['train'][1][ids].cuda()
        nll=token_nll(obj,x); uroot,unused,droot=train_roots(nll,labels,weights[ids].cuda())
        bu=derivative(uroot,params,keep=True); bd=derivative(droot,params)
        means_u.add_(bu/16); means_d.add_(bd/16)
        centered_u.append(float(((bu-gu)**2).sum())); centered_d.append(float(((bd-gd)**2).sum()))
        bn=magnitude(bd); bdot=float((gv*bd).sum()); bg={}
        cosine=None if vn<=EPS or bn<=EPS else bdot/(vn*bn)
        if cosine is None: bg['cosine']='validation_or_extra_norm_le_1e-12'
        ratio=nullable(bn,un,'uniform_norm_le_1e-12',bg,'extra_to_uniform_population_norm')
        item=dict(panel_id=row['panel_id'],data_seed=row['data_seed'],seed=row['seed'],state=row['state'],batch=batch,
            ids_sha256=tensor_hash(ids),uniform_gradient_norm=magnitude(bu),extra_gradient_norm=bn,
            validation_gradient_norm=vn,dot_validation_extra=bdot,local_descent_slope=-bdot,
            uniform_objective=float(uroot.detach()),extra_objective=float(droot.detach()),cosine=cosine,
            extra_to_uniform_population_norm=ratio,guards=bg)
        old=batch_saved[batch]
        require(set(old)==set(item),'Batch scalar schema')
        for key,value in item.items():
            if isinstance(value,float) or value is None:
                checks.scalar('batch_'+key,old[key],value,atol=2e-4 if key=='cosine' else 2e-6)
            else: require(old[key]==value,'Batch identity/guard mismatch: '+key)
        independent_batches.append(item); del x,labels,nll,uroot,unused,droot,bu,bd
    checks.vector('real_full_vs_batch_uniform',means_u,gu); checks.vector('real_full_vs_batch_delta',means_d,gd)
    vd=statistics.mean(centered_d); vu=statistics.mean(centered_u)
    metrics,guards=summary(vn,un,dn,dot,vd,vu)
    require(set(saved['metrics'])==set(metrics) and saved['guards']==guards,'State scalar/undefined schema')
    for key,value in metrics.items():
        checks.scalar('state_'+key,saved['metrics'][key],value,atol=2e-4 if key in ('cosine','projection_relative_uniform') else 2e-6)
    for key,value in (('validation_group_nll',val_value),('uniform_training_objective',u_value),('extra_training_objective',d_value)):
        checks.scalar('state_'+key,saved[key],value)
    for label,expected in (('uniform',vu),('extra',vd)):
        raw=saved['raw_population_variance'][label]; corrected=saved['variance_roundoff_corrected'][label]
        require(corrected==(raw<0),'Variance roundoff provenance')
        norm_key='uniform_gradient_norm' if label=='uniform' else 'extra_gradient_norm'
        scale=max(statistics.mean(b[norm_key]**2 for b in independent_batches),un**2 if label=='uniform' else dn**2,1e-30)
        require(raw>=-1e-12*scale,'Saved negative variance beyond roundoff allowance')
        checks.scalar('variance_raw_'+label,raw,expected)
    sign_counts=dict(negative=sum(b['cosine'] is not None and b['dot_validation_extra']<0 for b in independent_batches),
        positive=sum(b['cosine'] is not None and b['dot_validation_extra']>0 for b in independent_batches),
        zero=sum(b['cosine'] is not None and b['dot_validation_extra']==0 for b in independent_batches),
        undefined=sum(b['cosine'] is None for b in independent_batches))
    require(saved['batch_sign_counts']==sign_counts,'Batch sign/undefined counts')
    require(state_binding(obj)==before and all(p.grad is None for p in params),'Audit parameter/gradient mutation')
    guard.check(disk=True)
    result=dict(panel_id=row['panel_id'],data_seed=row['data_seed'],seed=row['seed'],state=row['state'],
        checkpoint_sha256=row['checkpoint_sha256'],metrics=metrics,guards=guards,
        validation_group_nll=val_value,uniform_training_objective=u_value,extra_training_objective=d_value,
        batch_sign_counts=sign_counts,parameter_state_unchanged=True)
    del obj,params,gv,gu,gd,means_u,means_d; gc.collect(); torch.cuda.empty_cache()
    return result,independent_batches

def report(cohort,corpus):
    def show(value): return 'undefined' if value is None else format(value,'.9g')
    lines=['# v0134 fixed gradient panel','',
        'Descriptive existing-checkpoint association; five corpus replication units.',
        'No mechanism, mediation, significance or AdamW-update claim. Final acceptance also requires the outer panel receipts.','',
        '| State | Mean cosine | Corpus SD | Defined cosine corpora | Negative cosine corpora | Extra/uniform norm | Extra/uniform batch RMS |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for row in cohort:
        m=row['metrics']; cosine=m['cosine']
        lines.append('| '+row['state']+' | '+show(cosine['mean'])+' | '+show(cosine['corpus_sd'])+' | '+
            str(cosine['defined_corpora'])+'/5 | '+str(cosine['negative_corpora'])+'/5 | '+show(m['extra_to_uniform_norm']['mean'])+' | '+
            show(m['extra_to_uniform_batch_rms']['mean'])+' |')
    lines+=['','| State | Corpus | Cosine | Defined seeds | Extra/uniform norm | Extra/uniform batch RMS |',
        '|---|---:|---:|---:|---:|---:|']
    for row in corpus:
        m=row['metrics']
        lines.append('| '+row['state']+' | '+str(row['data_seed'])+' | '+show(m['cosine'])+' | '+
            str(row['defined_seed_counts']['cosine'])+'/2 | '+show(m['extra_to_uniform_norm'])+' | '+
            show(m['extra_to_uniform_batch_rms'])+' |')
    lines+=['','Every seed, batch, undefined case and all15 corpus-state rows remain in the JSON outputs.',
        'Negative dot means theta-eta*extra_gradient locally worsens validation group NLL.',
        'No historical optimizer moments or intermediate optimization replay is available.','',
        'Extra-component dispersion is not total weighted-gradient variance; uniform/extra covariance also matters.','',
        'Prospective interpretation: adverse initial alignment may motivate an interference intervention;',
        'little directional conflict with larger relative dispersion may motivate a variance intervention.',
        'F10-only association may be consequence. Mixed/weak/undefined/favorable initial patterns close this panel;',
        'do not search states, layers, batches or examples. Any follow-up needs separate design and approval.','',
        'See FROZEN_PROTOCOL.md for definitions, population normalization, audits, guards and all limits.']
    return '\n'.join(lines)+'\n'

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('phase',choices=('audit',))
    parser.add_argument('--admission',required=True,type=Path); args=parser.parse_args()
    guard=Guard(args.admission); require(guard.obj['phase']=='audit','Wrong worker phase admission')
    guard.check(disk=True); inputs=verify_inputs(guard)
    done=read(RUN/'DIAGNOSE_COMPLETE.json')
    require(done['manifest_sha256']==verify_manifest() and done['panel_states']==30 and done['batch_rows']==480 and
            done['artifact_manifest_sha256']==sha(RUN/'ARTIFACT_MANIFEST.json'),'Diagnostic completion binding')
    require(binding(RUN,exclude=('ARTIFACT_MANIFEST.json','DIAGNOSE_COMPLETE.json'))==read(RUN/'ARTIFACT_MANIFEST.json'),
            'Diagnostic artifacts changed')
    require(not OUT.exists(),'No audit overwrite/resume'); OUT.mkdir(parents=True)
    env=environment(); guard.check(); checks=Checks(); fixture_status=fixtures(checks); guard.check()
    rows=[]; batches=[]; pair=None; data=None; weights=None; order=None
    for row in inputs['panel']:
        guard.check(disk=True)
        if pair!=(row['data_seed'],row['seed']):
            data,weights,order=load_pair(row); pair=(row['data_seed'],row['seed'])
        value,records=audit_state(row,data,weights,order,guard,checks)
        rows.append(value); batches.extend(records); print(row['panel_id'],'audit checked',flush=True)
    require(len(rows)==30 and len(batches)==480,'Full independent audit coverage')
    corpus,cohort,changes=independent_aggregation(rows)
    compare_tree(checks,'corpus',read(RUN/'CORPUS_SUMMARY.json'),corpus)
    compare_tree(checks,'cohort',read(RUN/'COHORT_SUMMARY.json'),dict(states=cohort,matched_state_changes=changes))
    for name,value in (('PAIRS.json',rows),('BATCHES.json',batches),('CORPUS_SUMMARY.json',corpus),
                       ('COHORT_SUMMARY.json',dict(states=cohort,matched_state_changes=changes))): write(OUT/name,value)
    with (OUT/'PANEL_REPORT.md').open('x',encoding='utf-8') as stream: stream.write(report(cohort,corpus))
    verify_inputs(guard); guard.check(disk=True)
    write(OUT/'AUDIT.json',dict(status='PASS_GRADIENT_REDUCTION_AND_PANEL_AUDIT',utc=utc(),
        manifest_sha256=verify_manifest(),input_bindings_sha256=sha(HERE/'INPUT_BINDINGS.json'),
        full_population_states=30,independent_batch_gradient_rows=480,corpus_state_rows=15,
        independent_corpus_count=5,fixtures=fixture_status,discrepancy_check_count=checks.count,
        discrepancy_maxima=checks.groups,environment=env,output_hashes=binding(OUT),
        limitations=['Shared trusted forward implementation and PyTorch autograd',
            'Existing-state gradients are associations, not mediation or actual AdamW updates',
            'No optimizer moments, intermediate optimization replay or test evaluation',
            'No retained gradient vectors; audit checks independently recomputed scalar panel and algebra',
            'Extra-component variance alone does not determine total weighted-gradient variance',
            'Numerical PASS requires successful inclusive outer panel receipts']))

if __name__=='__main__': main()
