"""Frozen30-state panel; gradients only, no optimizer or parameter update."""
import time
import argparse
import gc
import json
import math
from pathlib import Path
import torch
from torch.nn import functional as F
from common import (HERE, RUN, STATES, EPS, Guard, require, write, finite, sha, utc,
                    verify_manifest, verify_inputs, binding)
from inputs import environment, load_pair, load_model, tensor_hash, state_binding

METRICS=('validation_gradient_norm','uniform_gradient_norm','extra_gradient_norm',
         'dot_validation_extra','cosine','local_descent_slope','extra_to_uniform_norm',
         'projection_relative_uniform','extra_batch_population_variance',
         'uniform_batch_population_variance','extra_batch_rms','uniform_batch_rms',
         'extra_rms_to_uniform_norm','extra_to_uniform_batch_rms','extra_signal_to_dispersion')

def components(obj,tokens,kinds):
    logits=obj(tokens[:,:-1]); targets=tokens[:,1:]
    nll=F.cross_entropy(logits.reshape(-1,84),targets.reshape(-1),reduction='none').reshape(len(tokens),40)
    values=[]
    for j in range(3):
        mask=kinds==j; count=mask.sum(1)
        require((count==4).all().item(),'Four-token component reduction')
        values.append((nll*mask).sum(1)/count)
    return torch.stack(values,1)

def vector(scalar,parameters,retain=False):
    require(torch.isfinite(scalar).item(),'Nonfinite objective')
    values=torch.autograd.grad(scalar,parameters,retain_graph=retain,create_graph=False,allow_unused=False)
    result=torch.cat([v.detach().reshape(-1) for v in values]).to(torch.float64)
    require(torch.isfinite(result).all().item(),'Nonfinite gradient')
    require(all(p.grad is None for p in parameters),'Gradient accumulation on parameter')
    return result

def ratio(top,bottom,reason,guards,key):
    if bottom<=EPS: guards[key]=reason; return None
    return top/bottom

def squared_variance(mean_square,mean_norm_square):
    raw=mean_square-mean_norm_square
    allowance=1e-12*max(mean_square,mean_norm_square,1e-30)
    require(raw>=-allowance,'Invalid negative gradient variance')
    return max(0.,raw),raw,raw<0

def strict_mean(values):
    return None if any(v is None for v in values) else math.fsum(values)/len(values)

def aggregate(rows):
    corpus=[]; cohort=[]; changes=[]
    for state in STATES:
        for d in range(91420101,91420106):
            chosen=[r for r in rows if r['state']==state and r['data_seed']==d]
            require(len(chosen)==2,'Two nested seeds required')
            corpus.append(dict(state=state,data_seed=d,seed_count=2,
                metrics={k:strict_mean([r['metrics'][k] for r in chosen]) for k in METRICS},
                defined_seed_counts={k:sum(r['metrics'][k] is not None for r in chosen) for k in METRICS}))
        chosen=[r for r in corpus if r['state']==state]; result={}
        for k in METRICS:
            values=[r['metrics'][k] for r in chosen]; mean=strict_mean(values)
            result[k]=dict(mean=mean,defined_corpora=sum(v is not None for v in values),
                corpus_sd=None if mean is None else math.sqrt(math.fsum((v-mean)**2 for v in values)/4),
                minimum=None if mean is None else min(values),maximum=None if mean is None else max(values),
                negative_corpora=sum(v is not None and v<0 for v in values),
                positive_corpora=sum(v is not None and v>0 for v in values),
                zero_corpora=sum(v is not None and v==0 for v in values))
        cohort.append(dict(state=state,independent_corpus_count=5,metrics=result))
    for state in STATES[1:]:
        for d in range(91420101,91420106):
            selected=[r for r in rows if r['state']==state and r['data_seed']==d]
            differences={k:[] for k in METRICS}
            for final in selected:
                initial=next(r for r in rows if r['state']=='initial' and r['data_seed']==d and r['seed']==final['seed'])
                for k in METRICS:
                    a=final['metrics'][k]; b=initial['metrics'][k]
                    differences[k].append(None if a is None or b is None else a-b)
            changes.append(dict(state=state,data_seed=d,contrast='F10 minus SAME-seed initial',
                                metrics={k:strict_mean(v) for k,v in differences.items()}))
    return corpus,cohort,changes

def state_panel(row,data,weights,order,guard,progress):
    start=time.monotonic(); obj,named=load_model(row); parameters=tuple(p for _,p in named)
    before=state_binding(obj); torch.cuda.reset_peak_memory_stats()
    reference=torch.zeros(621696,dtype=torch.float64,device='cuda'); val_loss=0.
    tokens,kinds=data['validation']
    for lo in range(0,256,32):
        guard.check(); obj.zero_grad(set_to_none=True)
        values=components(obj,tokens[lo:lo+32].cuda(),kinds[lo:lo+32].cuda())
        loss=values[:,1].mean(); reference.add_(vector(loss,parameters),alpha=1/8)
        val_loss+=float(loss.detach())/8
    vnorm=float(torch.linalg.vector_norm(reference))
    uniform=torch.zeros_like(reference); extra=torch.zeros_like(reference)
    rows=[]; uniform_squares=[]; extra_squares=[]; u_loss=0.; d_loss=0.
    tokens,kinds=data['train']
    for batch in range(16):
        guard.check(); obj.zero_grad(set_to_none=True)
        ids=order[batch*32:(batch+1)*32]
        values=components(obj,tokens[ids].cuda(),kinds[ids].cuda())
        unweighted=values.sum(1).mean()/3
        additional=((weights[ids].cuda()-1)*values[:,2]).mean()/3
        gu=vector(unweighted,parameters,retain=True); gd=vector(additional,parameters)
        usq=float(torch.dot(gu,gu)); dsq=float(torch.dot(gd,gd)); dot=float(torch.dot(reference,gd))
        uniform.add_(gu,alpha=1/16); extra.add_(gd,alpha=1/16)
        uniform_squares.append(usq); extra_squares.append(dsq)
        uvalue=float(unweighted.detach()); dvalue=float(additional.detach())
        u_loss+=uvalue/16; d_loss+=dvalue/16
        batch_row=dict(panel_id=row['panel_id'],data_seed=row['data_seed'],seed=row['seed'],state=row['state'],
            batch=batch,ids_sha256=tensor_hash(ids),uniform_gradient_norm=math.sqrt(usq),
            extra_gradient_norm=math.sqrt(dsq),validation_gradient_norm=vnorm,dot_validation_extra=dot,
            local_descent_slope=-dot,uniform_objective=uvalue,extra_objective=dvalue)
        finite(batch_row)
        progress.write((json.dumps(batch_row,allow_nan=False)+'\n').encode('utf-8')); progress.flush()
        require(progress.tell()<=2**20,'Progress scalar log cap')
        rows.append(batch_row)
        del values,gu,gd,unweighted,additional
    unorm=float(torch.linalg.vector_norm(uniform)); dnorm=float(torch.linalg.vector_norm(extra))
    dot=float(torch.dot(reference,extra)); guards={}
    vu,raw_u,rounded_u=squared_variance(math.fsum(uniform_squares)/16,unorm**2)
    vd,raw_d,rounded_d=squared_variance(math.fsum(extra_squares)/16,dnorm**2)
    cosine=None
    if vnorm<=EPS or dnorm<=EPS: guards['cosine']='validation_or_extra_norm_le_1e-12'
    else: cosine=dot/(vnorm*dnorm)
    projection=None
    if vnorm<=EPS or unorm<=EPS: guards['projection_relative_uniform']='validation_or_uniform_norm_le_1e-12'
    else: projection=dot/(vnorm*unorm)
    metrics=dict(validation_gradient_norm=vnorm,uniform_gradient_norm=unorm,extra_gradient_norm=dnorm,
        dot_validation_extra=dot,cosine=cosine,local_descent_slope=-dot,
        extra_to_uniform_norm=ratio(dnorm,unorm,'uniform_norm_le_1e-12',guards,'extra_to_uniform_norm'),
        projection_relative_uniform=projection,extra_batch_population_variance=vd,
        uniform_batch_population_variance=vu,extra_batch_rms=math.sqrt(vd),uniform_batch_rms=math.sqrt(vu),
        extra_rms_to_uniform_norm=ratio(math.sqrt(vd),unorm,'uniform_norm_le_1e-12',guards,'extra_rms_to_uniform_norm'),
        extra_to_uniform_batch_rms=ratio(math.sqrt(vd),math.sqrt(vu),'uniform_batch_rms_le_1e-12',guards,'extra_to_uniform_batch_rms'),
        extra_signal_to_dispersion=ratio(dnorm,math.sqrt(vd),'extra_batch_rms_le_1e-12',guards,'extra_signal_to_dispersion'))
    for item in rows:
        bg={}; bn=item['extra_gradient_norm']
        item['cosine']=None if vnorm<=EPS or bn<=EPS else item['dot_validation_extra']/(vnorm*bn)
        if item['cosine'] is None: bg['cosine']='validation_or_extra_norm_le_1e-12'
        item['extra_to_uniform_population_norm']=ratio(bn,unorm,'uniform_norm_le_1e-12',bg,'extra_to_uniform_population_norm')
        item['guards']=bg
    require(state_binding(obj)==before,'Diagnostic changed parameter state')
    require(all(p.grad is None for p in parameters),'Residual accumulated gradients')
    guard.check(disk=True)
    result=dict(panel_id=row['panel_id'],data_seed=row['data_seed'],seed=row['seed'],state=row['state'],
        checkpoint_sha256=row['checkpoint_sha256'],metrics=metrics,guards=guards,
        validation_group_nll=val_loss,uniform_training_objective=u_loss,extra_training_objective=d_loss,
        raw_population_variance=dict(uniform=raw_u,extra=raw_d),
        variance_roundoff_corrected=dict(uniform=rounded_u,extra=rounded_d),
        batch_sign_counts=dict(negative=sum(b['cosine'] is not None and b['dot_validation_extra']<0 for b in rows),
            positive=sum(b['cosine'] is not None and b['dot_validation_extra']>0 for b in rows),
            zero=sum(b['cosine'] is not None and b['dot_validation_extra']==0 for b in rows),
            undefined=sum(b['cosine'] is None for b in rows)),
        batch_count=16,parameter_state_unchanged=True,parameter_layout=[dict(name=n,shape=list(p.shape),numel=p.numel()) for n,p in named],
        elapsed_seconds=time.monotonic()-start,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20)
    finite(result); del obj,parameters,reference,uniform,extra; gc.collect(); torch.cuda.empty_cache()
    return result,rows

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('phase',choices=('diagnose',))
    parser.add_argument('--admission',required=True,type=Path); args=parser.parse_args()
    guard=Guard(args.admission); require(guard.obj['phase']=='diagnose','Wrong worker phase admission')
    guard.check(disk=True); inputs=verify_inputs(guard)
    require(not RUN.exists(),'No overwrite/resume'); RUN.mkdir(parents=True)
    write(RUN/'DESIGN_FREEZE.json',dict(version='v0134',utc=utc(),manifest_sha256=verify_manifest(),
        input_bindings_sha256=sha(HERE/'INPUT_BINDINGS.json'),panel=inputs['panel'],
        protocol_sha256=sha(HERE/'FROZEN_PROTOCOL.md'),outcomes_generated=False))
    write(RUN/'ENVIRONMENT.json',environment()); guard.check()
    panels=[]; batches=[]; data=None; weights=None; order=None; pair=None
    with (RUN/'progress.jsonl').open('xb') as progress:
        for row in inputs['panel']:
            guard.check(disk=True)
            if pair!=(row['data_seed'],row['seed']):
                data,weights,order=load_pair(row); pair=(row['data_seed'],row['seed'])
            panel,records=state_panel(row,data,weights,order,guard,progress)
            write(RUN/'states'/(row['panel_id']+'.json'),panel)
            write(RUN/'batches'/(row['panel_id']+'.json'),records)
            panels.append(panel); batches.extend(records); print(row['panel_id'],'saved',flush=True)
    require(len(panels)==30 and len(batches)==480,'Complete frozen panel required')
    corpus,cohort,changes=aggregate(panels)
    for name,value in (('PANEL.json',panels),('BATCHES.json',batches),('CORPUS_SUMMARY.json',corpus),
                       ('COHORT_SUMMARY.json',dict(states=cohort,matched_state_changes=changes))): write(RUN/name,value)
    verify_inputs(guard); guard.check(disk=True)
    write(RUN/'ARTIFACT_MANIFEST.json',binding(RUN))
    write(RUN/'DIAGNOSE_COMPLETE.json',dict(utc=utc(),panel_states=30,batch_rows=480,
        manifest_sha256=verify_manifest(),artifact_manifest_sha256=sha(RUN/'ARTIFACT_MANIFEST.json')))

if __name__=='__main__': main()
