"""Stage 4 independent audit, frozen comparisons and scientific report."""
import argparse
import csv
import json
import math
import os
import shutil
import statistics as st
import sys
import time
import zipfile
from pathlib import Path
sys.dont_write_bytecode=True
import torch
from stage4 import (ROOT,HERE,CAPS,EPOCHS,GRID,TUNE,CONFIRM,VARIANTS,SOURCES,LIMIT_SECONDS,
                    data,pre_data,weights,orders,tensor_hash,read,write,sha,utc)
from diagnostics import fit,contrast
from diagnostics_roundoff import decompose


def desc(values):
    v=[x for x in values if x is not None]; complete=bool(values) and len(v)==len(values)
    return dict(n=len(values),undefined=len(values)-len(v),positive=sum(x>0 for x in v),
        negative=sum(x<0 for x in v),zero=sum(x==0 for x in v),
        mean=st.mean(v) if complete else None,sd=st.stdev(v) if complete and len(v)>1 else 0 if complete else None,
        minimum=min(v) if complete else None,maximum=max(v) if complete else None)


def replicated(values):
    corpora=[dict(data_seed=d,**desc([x['value'] for x in values if x['data_seed']==d])) for d in sorted({x['data_seed'] for x in values})]
    means=[x['mean'] for x in corpora]
    sign='undefined' if any(x is None for x in means) else 'positive' if all(x>0 for x in means) else 'negative' if all(x<0 for x in means) else 'zero' if all(x==0 for x in means) else 'mixed'
    return dict(values=values,all_pairs=desc([x['value'] for x in values]),corpora=corpora,
                between_corpora=desc(means),corpus_mean_sign=sign)


def verdict(stats):
    if stats['all_pairs']['undefined']: return 'inconclusive_undefined'
    if stats['all_pairs']['positive']==9: return 'survives'
    if all(x['mean']<=0 for x in stats['corpora']): return 'disappears'
    return 'mixed/inconclusive'


def arithmetic(items):
    return None if any(x is None for x,c in items) else sum(x*c for x,c in items)


def csvwrite(path,rows):
    if not rows: return
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        w.writeheader(); w.writerows(rows)


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,r))+' |' for r in rows])


def fmt(x): return 'undefined' if x is None else f'{x:.6f}'


def independent_schedule(root):
    # Rebuild the schedule directly, without invoking the runner's selection.
    def make(phase,v,w,l,d,s,p,i,arm):
        return dict(name=f'{phase}-{v}-w{w}-d{d}-s{s}-g{i:02d}-{arm}',phase=phase,variant=v,width=w,layers=l,
            data_seed=d,seed=s,pretrain_seed=p,grid_index=i,**GRID[i],epochs=60,arm=arm)
    tuning=[make('tune',v,w,l,d,s,p,i,a) for w,l in CAPS for d,s,p in TUNE for v in VARIANTS
            for i in range(4) for a in ['random','uniform']]
    assert tuning==read(root/'tuning_schedule.json') and len(tuning)==144
    sel=read(root/'selection.json'); vals=[]
    for c in tuning:
        path=root/'runs'/c['name']/'history.json'
        assert sha(path)==sel['input_hashes'][str(path.relative_to(root))]
        for h in read(path):
            vals.append(dict(variant=c['variant'],width=c['width'],data_seed=c['data_seed'],seed=c['seed'],
                grid_index=c['grid_index'],arm=c['arm'],epoch=h['epoch'],validation_nll=h['validation']['loss']))
    assert vals==sel['inputs']
    for v in VARIANTS:
        for w,l in CAPS:
            candidates=[]
            for i,g in enumerate(GRID):
                for e in EPOCHS:
                    scores=[x['validation_nll'] for x in vals if x['variant']==v and x['width']==w and x['grid_index']==i and x['epoch']==e]
                    assert len(scores)==4
                    candidates.append(dict(grid_index=i,**g,epoch=e,validation_nll=sum(scores)/len(scores),scores=scores))
            assert candidates==sel['all_scores'][f'{v}-{w}']
            assert min(candidates,key=lambda x:(x['validation_nll'],x['epoch'],x['lr'],x['wd']))==sel['decisions'][v][str(w)]
    confirm=[make('confirm',v,w,l,d,s,p,i,a) for w,l in CAPS for d,s,p in CONFIRM for v in VARIANTS
             for i in sorted({0,sel['decisions'][v][str(w)]['grid_index']}) for a in ['random','uniform']]
    assert confirm==sel['run_schedule'] and len(confirm)==sel['planned_confirmation']<=324
    assert not sel['test_used'] and not sel['confirmation_used']
    return sel,tuning+confirm


def audit(root):
    assert (root/'COMPLETE.json').exists()
    assert not list((root/'runs').glob('*/failure.json'))
    source=read(root/'source_manifest.json')
    assert source=={n:sha(HERE/n) for n in SOURCES}
    assert all(sha(root/'source'/n)==h for n,h in source.items())
    historical=read(root/'historical_manifest.json')
    for n,h in historical.items(): assert sha(ROOT/n)==h,f'Historical change {n}'
    print(f'Historical hashes PASS ({len(historical)} files).',flush=True)
    sel,schedule=independent_schedule(root)
    expected={c['name']:c for c in schedule}
    actual={p.parent.name for p in (root/'runs').glob('*/result.json')}
    assert actual==set(expected)
    events=[json.loads(x) for x in (root/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    frozen=[x for x in events if x['kind']=='selection_frozen']; assert len(frozen)==1
    assert frozen[0]['sha256']==sha(root/'selection.json')
    tests=[x for x in events if x['kind']=='test_evaluation']
    assert len(tests)==5*sel['planned_confirmation']
    assert {(x['name'],x['epoch']) for x in tests}=={(c['name'],e) for c in sel['run_schedule'] for e in EPOCHS}
    assert all(x['utc']>frozen[0]['utc'] and x['selection_sha256']==sha(root/'selection.json') for x in tests)
    assert all(x['utc']>frozen[0]['utc'] for x in events if x['kind']=='run_start' and x['name'].startswith('confirm'))
    assert all(x['utc']<frozen[0]['utc'] for x in events if x['kind']=='run_complete' and x['name'].startswith('tune'))
    corpus_meta={}
    for folder in (root/'corpora').iterdir():
        kind,seed=folder.name.split('-'); seed=int(seed)
        ds=torch.load(folder/'dataset.pt',weights_only=True); dm=read(folder/'metadata.json')
        regen,meta=data(seed) if kind=='adapt' else pre_data(seed,'S' if kind=='preshared' else 'M')
        assert dm['sequence_keys_by_split']==meta['sequence_keys_by_split']
        assert sha(folder/'dataset.pt')==dm['file_sha256']
        for split,pair in ds.items():
            assert all(torch.equal(a,b) for a,b in zip(pair,regen[split]))
            assert tensor_hash(*pair)==dm['tensor_sha256'][split]
            if kind=='adapt' and split!='test':
                hidden,_=data(seed,include_test=False)
                assert all(torch.equal(a,b) for a,b in zip(pair,hidden[split]))
            if kind=='premixed':
                alternate,_=pre_data(seed,'U')
                assert all(torch.equal(a,b) for a,b in zip(pair,alternate[split]))
        keys=sum(dm['sequence_keys_by_split'].values(),[]); assert len(keys)==len(set(keys))
        corpus_meta[folder.name]=dm
    assert len(corpus_meta)==15
    baseline_meta={}; cold_models={}
    for folder in (root/'baselines').iterdir():
        b=read(folder/'result.json'); assert b['source_sha256']==source
        assert sha(folder/'pretrained.pt')==b['checkpoint_sha256'] and sha(folder/'cold.pt')==b['cold_sha256']
        cold=torch.load(folder/'cold.pt',weights_only=True)
        assert {k:tensor_hash(v) for k,v in cold.items()}==b['cold_tensor_sha256']
        key=(b['width'],b['seed'])
        if key in cold_models: assert all(torch.equal(cold[k],cold_models[key][k]) for k in cold)
        else: cold_models[key]=cold
        order=torch.load(folder/'orders.pt',weights_only=True)
        assert torch.equal(order,orders(b['seed'],2048,4)) and tensor_hash(order)==b['batch_order_sha256']
        prefix='preshared' if b['variant']=='S' else 'premixed'
        assert b['data']==corpus_meta[f'{prefix}-{b["data_seed"]}']
        losses=torch.load(folder/'sequence_losses.pt',weights_only=True)
        for h,rec in zip(b['history'],losses):
            for split in ['train','validation']:
                assert abs(float(rec[split]['loss'].mean())-h[split]['loss'])<1e-7
        assert len(b['history'])==len(losses)==4
        baseline_meta[folder.name]=b
    assert len(baseline_meta)==99
    del cold_models
    results={}; records={}; initial={}; crossed={}; pair_checks=0
    for name in sorted(actual):
        folder=root/'runs'/name; r=read(folder/'result.json'); c=r['config']
        assert c==read(folder/'config.json') and all(c[k]==v for k,v in expected[name].items())
        assert c['source_sha256']==source
        assert c['selection_sha256']==(sha(root/'selection.json') if c['phase']=='confirm' else None)
        dm=corpus_meta[f'adapt-{c["data_seed"]}']; assert c['data_sha256']==dm['tensor_sha256']
        b=baseline_meta[f'{c["variant"]}-w{c["width"]}-s{c["seed"]}-d{c["pretrain_seed"]}']
        assert c['baseline_sha256']==b['checkpoint_sha256']
        assert set(sum(dm['sequence_keys_by_split'].values(),[])).isdisjoint(sum(b['data']['sequence_keys_by_split'].values(),[]))
        assignment=torch.load(folder/'assignment.pt',weights_only=True)
        rec=torch.load(folder/'sequence_losses.pt',weights_only=True)
        assert torch.equal(assignment['weights'],weights(c['seed'],c['arm'])) and torch.equal(rec['weights'],assignment['weights'])
        assert torch.equal(assignment['orders'],orders(c['seed']))
        assert tensor_hash(assignment['weights'])==c['weight_sha256'] and tensor_hash(assignment['orders'])==c['batch_order_sha256']
        assert [h['epoch'] for h in r['history']]==[0]+EPOCHS
        assert [h['epoch'] for h in rec['checkpoints']]==[0]+EPOCHS
        assert [h['epoch'] for h in r['epoch_stats']]==list(range(1,61))
        for h,cp in zip(r['history'],rec['checkpoints']):
            splits=['train','validation']+(['test'] if c['phase']=='confirm' and h['epoch'] else [])
            if 'test' not in splits: assert h['test'] is None and cp['test'] is None
            for split in splits:
                assert torch.isfinite(cp[split]['loss']).all()
                assert abs(float(cp[split]['loss'].mean())-h[split]['loss'])<1e-7
                for j,typ in enumerate(['shared','group','instance']):
                    for metric,field in [('loss','component_loss'),('accuracy','component_accuracy')]:
                        assert abs(float(cp[split][field][:,j].mean())-h[split][typ][metric])<1e-7
            if h['epoch']:
                ff=fit(rec['weights'],rec['checkpoints'][0]['train']['loss']-cp['train']['loss'])
                assert ff==h['p_star']
                assert sha(folder/f'model-e{h["epoch"]:02d}.pt')==r['checkpoint_sha256'][str(h['epoch'])]
                assert h['clipping_cumulative']==sum(z['gradient_clip_fraction'] for z in r['epoch_stats'][:h['epoch']])/h['epoch']
            else: assert h['p_star']['p'] is None
        key=(c['variant'],c['width'],c['data_seed'],c['seed'])
        if key in initial:
            previous,prevconfig=initial[key]
            assert c['baseline_sha256']==prevconfig['baseline_sha256']
            for split in ['train','validation']:
                for field in ['loss','component_loss','component_accuracy']:
                    assert torch.equal(rec['checkpoints'][0][split][field],previous[split][field])
            pair_checks+=1
        else: initial[key]=(rec['checkpoints'][0],c)
        key=(c['data_seed'],c['seed'],c['arm']); value=(c['data_sha256'],c['weight_sha256'],c['batch_order_sha256'])
        if key in crossed: assert value==crossed[key]
        else: crossed[key]=value
        results[name]=r
        if c['phase']=='confirm': records[name]=rec
    complete=read(root/'COMPLETE.json')
    assert complete['elapsed_seconds']<=LIMIT_SECONDS and complete['tuning_runs']==144
    assert complete['confirmation_runs']==sel['planned_confirmation'] and len(actual)<=468
    evidence=dict(status='PASS',utc=utc(),tuning_runs=144,confirmation_runs=sel['planned_confirmation'],
        pretraining=99,model_checkpoints=5*len(actual),test_evaluations=len(tests),baseline_pair_checks=pair_checks,
        historical_files_unchanged=len(historical),failed_runs=[],selection_sha256=sha(root/'selection.json'),checks=[
        'historical hashes/source snapshots unchanged','fresh validation-only selection independently reconstructed',
        'exact deduplicated schedule','all tests preregistered and after selection; none in tuning/epoch0',
        'full corpus regeneration, M/U equality and test-toggle invariance','all phase/split keys disjoint',
        'full cold model tensors equal across conditions','pretrained checkpoint and full initial losses equal within condition',
        'weights and orders identical across conditions/capacities/configurations','all model hashes checked',
        'all scalar/component metrics and primary p* reconstructed','three-hour cap respected'])
    return evidence,sel,results,records


def flat_rows(results):
    rows=[]
    for r in results.values():
        c=r['config']
        for h in r['history']:
            x={k:c[k] for k in ['name','phase','variant','width','data_seed','seed','pretrain_seed','grid_index','arm','lr','wd','parameters']}
            x.update(epoch=h['epoch'],p=h['p_star']['p'],p_reason=h['p_star'].get('reason'),objective=h['p_star'].get('objective'),
                total_gain=h['total_gain'],negative_gain_fraction=h['negative_gain_fraction'],clipping=h.get('clipping_cumulative'),
                lower_boundary=h['p_star'].get('at_lower_bound',False),upper_boundary=h['p_star'].get('at_upper_bound',False),
                initial_validation_nll=r['history'][0]['validation']['loss'])
            for split in ['train','validation','test']:
                x[f'{split}_nll']=None if h[split] is None else h[split]['loss']
                for typ in ['shared','group','instance']:
                    for metric in ['loss','accuracy']:
                        x[f'{split}_{typ}_{metric}']=None if h[split] is None else h[split][typ][metric]
            rows.append(x)
    return rows


def policy_analysis(sel,rows):
    index={(r['variant'],r['width'],r['data_seed'],r['seed'],r['arm'],r['grid_index'],r['epoch']):r for r in rows if r['phase']=='confirm'}
    cells={}; selected_rows=[]; values={}; kvals={}; fingerprints={}
    metrics=['p','objective','train_nll','validation_nll','test_nll','train_instance_accuracy','clipping','total_gain','negative_gain_fraction']
    for v in VARIANTS:
        for policy in ['F','T']:
            for sched in [f'C{e}' for e in EPOCHS]+['ET']:
                configs={w:0 if policy=='F' else sel['decisions'][v][str(w)]['grid_index'] for w,l in CAPS}
                epochs={w:sel['decisions'][v][str(w)]['epoch'] if sched=='ET' else int(sched[1:]) for w,l in CAPS}
                key=f'{v}_{policy}_{sched}'; fingerprint=(v,tuple((w,configs[w],epochs[w]) for w,l in CAPS))
                alias=fingerprints.get(fingerprint); fingerprints.setdefault(fingerprint,key); arms={}
                for arm in ['random','uniform']:
                    kk=[]; selected=[]
                    for d,s,p in CONFIRM:
                        group=[index[v,w,d,s,arm,configs[w],epochs[w]] for w,l in CAPS]
                        k=contrast(*[r['p'] for r in group]); kvals[key,arm,d,s]=k
                        kk.append(dict(data_seed=d,seed=s,value=k)); selected.extend(group)
                        for r in group:
                            values[key,arm,d,s,r['width']]=r
                            selected_rows.append(dict(cell=key,**r))
                    stats=replicated(kk); gen=[]; capacity=[]
                    for d in sorted({x[0] for x in CONFIRM}):
                        groups=[[r for r in selected if r['width']==w and r['data_seed']==d] for w,l in CAPS]
                        te=[st.mean(r['test_nll'] for r in g) for g in groups]
                        va=[st.mean(r['validation_nll'] for r in g) for g in groups]
                        v0=[st.mean(r['initial_validation_nll'] for r in g) for g in groups]
                        gen.append(dict(data_seed=d,test_nll=te,validation_nll=va,initial_validation_nll=v0,
                            test_monotonic=te[0]>te[1]>te[2],validation_improves=all(a<=b for a,b in zip(va,v0))))
                    for w,l in CAPS:
                        g=[r for r in selected if r['width']==w]
                        capacity.append(dict(width=w,epoch=epochs[w],grid_index=configs[w],
                            **{metric:desc([r[metric] for r in g]) for metric in metrics}))
                    arms[arm]=dict(peak=stats,verdict=verdict(stats) if arm=='random' else 'undefined_uniform',capacity=capacity,
                        generalization=gen,generalization_met=all(g['test_monotonic'] and g['validation_improves'] for g in gen))
                cells[key]=dict(variant=v,policy=policy,schedule=sched,alias_of=alias,arms=arms)
    definitions={'primary_U_minus_M_F_C30':[('U_F_C30',1),('M_F_C30',-1)],
        'secondary_U_minus_M_F_C60':[('U_F_C60',1),('M_F_C60',-1)],
        'context_M_minus_S_F_C30':[('M_F_C30',1),('S_F_C30',-1)],
        'selected_policy_U_minus_M':[('U_T_ET',1),('M_T_ET',-1)]}
    for v in VARIANTS:
        definitions.update({f'{v}_optimizer_C30':[(f'{v}_T_C30',1),(f'{v}_F_C30',-1)],
            f'{v}_duration_F':[(f'{v}_F_ET',1),(f'{v}_F_C30',-1)],
            f'{v}_duration_T':[(f'{v}_T_ET',1),(f'{v}_T_C30',-1)],
            f'{v}_interaction':[(f'{v}_T_ET',1),(f'{v}_T_C30',-1),(f'{v}_F_ET',-1),(f'{v}_F_C30',1)]})
    effects={}; effect_rows=[]
    for label,terms in definitions.items():
        effects[label]=replicated([dict(data_seed=d,seed=s,value=arithmetic([(kvals[key,'random',d,s],coef) for key,coef in terms])) for d,s,p in CONFIRM])
        for arm in ['random','uniform']:
            for w,l in CAPS:
                for metric in metrics:
                    for d,s,p in CONFIRM:
                        effect_rows.append(dict(effect=label,arm=arm,width=w,metric=metric,data_seed=d,seed=s,
                            value=arithmetic([(values[key,arm,d,s,w][metric],coef) for key,coef in terms])))
    return dict(cells=cells,effects=effects),selected_rows,effect_rows


def baseline_analysis(rows):
    baselines=[r for r in rows if r['phase']=='confirm' and r['grid_index']==0 and r['arm']=='random' and r['epoch']==0]
    assert len(baselines)==81
    summary=[]; checks=[]
    for v in VARIANTS:
        for w,l in CAPS:
            g=[r for r in baselines if r['variant']==v and r['width']==w]
            summary.append(dict(variant=v,width=w,**{k:desc([r[k] for r in g]) for k in
                ['train_nll','validation_nll','validation_shared_accuracy','validation_shared_loss','validation_group_loss','validation_instance_loss']}))
    for w,l in CAPS:
        for d in sorted({x[0] for x in CONFIRM}):
            groups={v:[r for r in baselines if r['variant']==v and r['width']==w and r['data_seed']==d] for v in ['M','U']}
            changes={t:st.mean(r[f'validation_{t}_loss'] for r in groups['U'])-st.mean(r[f'validation_{t}_loss'] for r in groups['M']) for t in ['shared','group','instance']}
            shared=st.mean(r['validation_shared_accuracy'] for r in groups['U'])
            checks.append(dict(width=w,data_seed=d,U_minus_M=changes,U_shared_accuracy=shared,
                group_improved=changes['group']<0,instance_improved=changes['instance']<0,shared_gate=shared>=.95))
    return dict(summary=summary,checks=checks,manipulation_pass=all(x['group_improved'] and x['instance_improved'] and x['shared_gate'] for x in checks)),baselines


def diagnostic_analysis(results,records):
    all_diag=[]; counts={}; flat=[]; index={}
    for name,rec in records.items():
        c=results[name]['config']; index[c['variant'],c['width'],c['data_seed'],c['seed'],c['arm'],c['grid_index']]=rec
        for cp in rec['checkpoints'][1:]:
            diag=decompose(rec['weights'],rec['checkpoints'][0]['train'],cp['train'])
            assert diag['primary']==next(h['p_star'] for h in results[name]['history'] if h['epoch']==cp['epoch'])
            all_diag.append(dict(name=name,variant=c['variant'],width=c['width'],data_seed=c['data_seed'],seed=c['seed'],
                                 arm=c['arm'],grid_index=c['grid_index'],epoch=cp['epoch'],**diag))
            measures={'primary':diag['primary'],'group_instance':diag['group_instance_only'],'oracle':diag['oracle_reference'],
                **{t:x['fit'] for t,x in diag['components'].items()}}
            for metric,f in measures.items():
                key=f'{c["variant"]}|{c["arm"]}|{metric}|{f.get("reason","defined")}'
                counts[key]=counts.get(key,0)+1
                flat.append(dict(name=name,variant=c['variant'],width=c['width'],data_seed=c['data_seed'],seed=c['seed'],
                    arm=c['arm'],grid_index=c['grid_index'],epoch=cp['epoch'],metric=metric,**f))
    crossed=[]; cross_cells={}
    for e in [30,60]:
        for ref in ['M','U']:
            for trained in ['M','U']:
                key=f'e{e}_reference{ref}_trajectory{trained}'; kk=[]; fitted_rows=[]
                for d,s,p in CONFIRM:
                    ps=[]
                    for w,l in CAPS:
                        a=index[ref,w,d,s,'random',0]; b=index[trained,w,d,s,'random',0]
                        assert torch.equal(a['weights'],b['weights'])
                        cp=next(x for x in b['checkpoints'] if x['epoch']==e)
                        ff=fit(b['weights'],a['checkpoints'][0]['train']['loss']-cp['train']['loss'])
                        if ref==trained:
                            rr=results[f'confirm-{ref}-w{w}-d{d}-s{s}-g00-random']
                            assert ff==next(h for h in rr['history'] if h['epoch']==e)['p_star']
                        ps.append(ff['p']); row=dict(cell=key,epoch=e,reference=ref,trajectory=trained,width=w,data_seed=d,seed=s,**ff)
                        fitted_rows.append(row); crossed.append(row)
                    kk.append(dict(data_seed=d,seed=s,value=contrast(*ps)))
                cross_cells[key]=dict(peak=replicated(kk),capacity=[dict(width=w,p=desc([r['p'] for r in fitted_rows if r['width']==w]),
                    mean_gain=desc([r['mean_gain'] for r in fitted_rows if r['width']==w])) for w,l in CAPS])
    cross_effects={}; cross_capacity=[]
    for e in [30,60]:
        mm=f'e{e}_referenceM_trajectoryM'; um=f'e{e}_referenceU_trajectoryM'
        mu=f'e{e}_referenceM_trajectoryU'; uu=f'e{e}_referenceU_trajectoryU'
        terms={'reference':[(um,1),(mm,-1)],'trajectory':[(mu,1),(mm,-1)],
               'interaction':[(uu,1),(um,-1),(mu,-1),(mm,1)],'total':[(uu,1),(mm,-1)]}
        for label,tt in terms.items():
            vv=[]
            for d,s,p in CONFIRM:
                kvals=[(next(r['value'] for r in cross_cells[key]['peak']['values'] if r['data_seed']==d and r['seed']==s),coef) for key,coef in tt]
                vv.append(dict(data_seed=d,seed=s,value=arithmetic(kvals)))
                for w,l in CAPS:
                    for metric in ['p','mean_gain']:
                        vals=[(next(r[metric] for r in crossed if r['cell']==key and r['data_seed']==d and r['seed']==s and r['width']==w),coef) for key,coef in tt]
                        cross_capacity.append(dict(epoch=e,effect=label,width=w,metric=metric,data_seed=d,seed=s,value=arithmetic(vals)))
            cross_effects[f'e{e}_{label}']=replicated(vv)
    return dict(all=all_diag,undefined_counts=counts,identity_max_abs_error=max(x['identity_max_abs_error'] for x in all_diag),
        reference_cells=cross_cells,reference_effects=cross_effects),flat,crossed,cross_capacity


def figures(out,summary,base,diag):
    os.environ['MPLCONFIGDIR']=str(ROOT/'work/.matplotlib')
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    colors={'S':'#667787','M':'#bd7040','U':'#117f90'}; xs=list(range(3)); labels=['113k','622k','3.21M']
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for v in VARIANTS:
        g=[x for x in base['summary'] if x['variant']==v]
        axes[0].plot(xs,[x['validation_nll']['mean'] for x in g],'o-',label=v,color=colors[v])
        axes[1].plot(xs,[100*x['validation_shared_accuracy']['mean'] for x in g],'o-',label=v,color=colors[v])
    axes[0].set(title='Initial mixed-task validation loss',ylabel='NLL (nats / answer token)')
    axes[1].set(title='Shared rule retention before adaptation',ylabel='Shared validation accuracy (%)',ylim=(0,103))
    axes[1].axhline(95,color='#aaaaaa',ls=':',label='95% manipulation gate')
    for ax in axes: ax.set(xticks=xs,xticklabels=labels,xlabel='Capacity'); ax.legend(frameon=False)
    fig.suptitle('S: shared-only context  |  M: mixed, shared loss  |  U: M + uniform auxiliary loss',fontsize=11)
    fig.tight_layout(); fig.savefig(out/'baseline.png',dpi=180); plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
    for ax,e in zip(axes,[30,60]):
        for v in VARIANTS:
            cell=summary['cells'][f'{v}_F_C{e}']['arms']['random']
            ax.plot(xs,[np.nan if c['p']['mean'] is None else c['p']['mean'] for c in cell['capacity']],'o-',label=v,color=colors[v])
        ax.set(title=f'Common epoch {e}',ylabel='Original signed-gain p*',xticks=xs,xticklabels=labels,xlabel='Capacity')
        ax.legend(frameon=False)
    fig.suptitle('Matched adaptation: LR 1e-4, WD 0.1, clip 1; 3 corpora × 3 model/weight seeds',fontsize=11)
    fig.tight_layout(); fig.savefig(out/'matched.png',dpi=180); plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for v in VARIANTS:
        cell=summary['cells'][f'{v}_T_ET']['arms']['random']
        axes[0].plot(xs,[np.nan if c['p']['mean'] is None else c['p']['mean'] for c in cell['capacity']],'o-',label=v,color=colors[v])
        for arm,style in [('random','-'),('uniform','--')]:
            cc=summary['cells'][f'{v}_T_ET']['arms'][arm]
            axes[1].plot(xs,[c['test_nll']['mean'] for c in cc['capacity']],marker='o',ls=style,label=f'{v}, {arm}',color=colors[v])
    axes[0].set(title='Own validation-selected policies',ylabel='Original signed-gain p*')
    axes[1].set(title='Held-out performance',ylabel='Test NLL (nats / answer token)')
    for ax in axes: ax.set(xticks=xs,xticklabels=labels,xlabel='Capacity'); ax.legend(frameon=False,fontsize=8)
    fig.suptitle('Selected-policy comparison changes both pretrained state and adaptation settings',fontsize=11)
    fig.tight_layout(); fig.savefig(out/'selected.png',dpi=180); plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
    for ax,e in zip(axes,[30,60]):
        for ref in ['M','U']:
            for trained,style in [('M','-'),('U','--')]:
                cell=diag['reference_cells'][f'e{e}_reference{ref}_trajectory{trained}']
                ax.plot(xs,[c['mean_gain']['mean'] for c in cell['capacity']],marker='o',ls=style,color=colors[ref],label=f'Reference {ref}, trajectory {trained}')
        ax.axhline(0,color='#888888',lw=1); ax.set(title=f'F, common epoch {e}',ylabel='Mean signed gain (nats / answer token)',xticks=xs,xticklabels=labels,xlabel='Capacity')
        ax.legend(frameon=False,fontsize=8)
    fig.suptitle('Reference-only sensitivity: nonpositive total gain gives undefined p*',fontsize=11)
    fig.tight_layout(); fig.savefig(out/'reference.png',dpi=180); plt.close(fig)


def report(root,out,sel,summary,base,diag,audit_result,results):
    keys=[f'{v}_{p}_{s}' for v in VARIANTS for p,s in [('F','C30'),('F','C60'),('T','C30'),('F','ET'),('T','ET')]]
    cells=summary['cells']; effects=summary['effects']
    primary=effects['primary_U_minus_M_F_C30']
    cell_table=table(['Cell','Mean K','SD corpus means','Positive / 9','Undefined / 9','Peak','Gen random','Gen uniform'],[
        [k,fmt(cells[k]['arms']['random']['peak']['between_corpora']['mean']),fmt(cells[k]['arms']['random']['peak']['between_corpora']['sd']),
         cells[k]['arms']['random']['peak']['all_pairs']['positive'],cells[k]['arms']['random']['peak']['all_pairs']['undefined'],
         cells[k]['arms']['random']['verdict'],cells[k]['arms']['random']['generalization_met'],cells[k]['arms']['uniform']['generalization_met']] for k in keys])
    choices=table(['Condition','Width','LR','WD','Clip','Epoch','Tuning validation NLL'],[
        [v,w,c['lr'],c['wd'],c['clip'],c['epoch'],fmt(c['validation_nll'])] for v in VARIANTS for w,c in sel['decisions'][v].items()])
    baseline_table=table(['Condition','Width','Initial val NLL','Shared NLL','Group NLL','Instance NLL','Shared accuracy'],[
        [r['variant'],r['width'],fmt(r['validation_nll']['mean']),fmt(r['validation_shared_loss']['mean']),
         fmt(r['validation_group_loss']['mean']),fmt(r['validation_instance_loss']['mean']),f'{100*r["validation_shared_accuracy"]["mean"]:.2f}%'] for r in base['summary']])
    effect_table=table(['Effect on K','Mean','SD corpus means','Corpus-mean sign'],[
        [k,fmt(v['between_corpora']['mean']),fmt(v['between_corpora']['sd']),v['corpus_mean_sign']] for k,v in effects.items()])
    cross_table=table(['Reference cell','Mean K','Undefined K / 9']+['p* '+str(w) for w,l in CAPS],[
        [k,fmt(v['peak']['between_corpora']['mean']),v['peak']['all_pairs']['undefined']]+[fmt(c['p']['mean']) for c in v['capacity']]
        for k,v in diag['reference_cells'].items()])
    cross_effects=table(['Reference diagnostic effect on K','Mean','Undefined / 9'],[
        [k,fmt(v['between_corpora']['mean']),v['all_pairs']['undefined']] for k,v in diag['reference_effects'].items()])
    perf=table(['Cell','Arm','Width','Epoch','p*','Fit objective','Train','Validation','Test','Instance acc','Clipping'],[
        [k,arm,c['width'],c['epoch'],fmt(c['p']['mean']),fmt(c['objective']['mean']),fmt(c['train_nll']['mean']),
         fmt(c['validation_nll']['mean']),fmt(c['test_nll']['mean']),f'{100*c["train_instance_accuracy"]["mean"]:.2f}%',
         f'{100*c["clipping"]["mean"]:.1f}%'] for k in [f'{v}_{p}_{s}' for v in VARIANTS for p,s in [('F','C30'),('T','ET')]]
         for arm in ['random','uniform'] for c in cells[k]['arms'][arm]['capacity']])
    n=sel['planned_confirmation']; complete=read(root/'COMPLETE.json')
    group_ok=sum(x['group_improved'] and x['instance_improved'] for x in base['checks'])
    shared_ok=sum(x['shared_gate'] for x in base['checks'])
    text=f'''# Stage 4 v0.5: intervensi pretraining dan referensi gain

144 run tuning baru dan {n} run konfirmasi selesai; 99 model pretrained.
Tiga corpus konfirmasi × tiga seed model/bobot, tiga kapasitas, dua arm.
Audit integritas **PASS**; tidak ada kegagalan run. Formula perbandingan,
data seeds, grid dan evaluasi test dibekukan sebelum training. Seleksi hanya
memakai validation NLL dari dua pasangan corpus/model tuning yang terpisah.

## 1. Jawaban utama: pretraining pada adaptasi yang sama

Pada optimizer F dan epoch 30, perubahan mean K untuk U−M adalah
**{fmt(primary['between_corpora']['mean'])}**, dengan tanda mean corpus
**{primary['corpus_mean_sign']}**. Verdict M adalah
**{cells['M_F_C30']['arms']['random']['verdict']}**, dan U adalah
**{cells['U_F_C30']['arms']['random']['verdict']}**.
K = p* menengah − max(p* kecil,p* besar). Nilai undefined tidak dibuang.

S memakai pretraining shared-only sebelumnya. M dan U memakai token mixed yang
persis sama; M mengoptimalkan shared CE, sedangkan U menambahkan CE target
uniform pada 16 jawaban di posisi group/instance, koefisien tetap 1. Cold
checkpoint dan urutan batch sama. F memakai LR1e-4, WD.1, clipping1.
U−M pada F/C30 menguji intervensi objective pretraining pada adaptasi tetap.
Intervensi dapat mengubah representasi maupun baseline loss; ia tidak
mengidentifikasi efek murni satu angka baseline. S−M juga mengubah konteks dan
jumlah shared-token supervision sehingga merupakan perbandingan kontekstual.

![Matched adaptation](matched.png)

{cell_table}

F/T adalah optimizer tetap/terpilih per kondisi. C30/C60 memakai epoch sama
antar kapasitas; ET memakai vektor epoch yang dipilih untuk kondisi itu.
Alias sel identik tercatat dalam policy-summary.json, bukan replikasi tambahan.
Survives berarti 9/9 kontras terdefinisi dan positif; disappears berarti semua
terdefinisi dan ketiga mean corpus <=0; selain itu mixed atau undefined.
SD mengacu pada tiga mean corpus. Ini hasil deskriptif, tanpa klaim signifikansi.

## 2. Apakah intervensi memperbaiki baseline yang dituju?

Manipulation check keseluruhan: **{base['manipulation_pass']}**. U menurunkan
kedua component NLL group/instance dibanding M pada **{group_ok}/9** sel
kapasitas/corpus; shared accuracy U >=95% pada **{shared_ok}/9** sel.
Kedua syarat dilaporkan terpisah dan kegagalan tidak memicu seleksi atau retry.

{baseline_table}

Komponen memiliki empat jawaban masing-masing, sehingga mixed NLL adalah mean
ketiganya. Uniform-answer NLL ideal pada group/instance adalah log(16)=2.772589.
NLL yang lebih rendah bukan bukti lengkap kalibrasi probabilitas. S/M/U tetap
memakai empat epoch pretraining; tidak ada tuning strength atau durasi pretraining.

![Baseline](baseline.png)

## 3. Tuning baru, optimizer dan durasi

{choices}

Grid terbatas pada LR {{1e-4,3e-4}}, WD {{.1,1}}, clip1 dan epoch {{1,3,10,30,60}}.
Skor adalah mean validation NLL kedua arm dan dua tuning pairs. Tie rule: skor
presisi penuh, epoch awal, LR naik, WD naik. Epoch0 hanya menjadi pemeriksaan
improvement. Hasil terbaik dalam grid ini tidak berarti optimum global.
Perbandingan U−M pada T/ET adalah efek total kebijakan yang turut mengubah
optimizer/durasi, sehingga berbeda dari perbandingan adaptasi tetap di atas.

{effect_table}

Dalam tiap kondisi, interaction=(T_ET−T_C30)−(F_ET−F_C30). Seluruh sembilan
nilai dan tiga mean corpus ada di policy-summary.json. Efek per kapasitas untuk
p*, loss, memorisasi, fit, clipping dan signed gains ada di per-capacity-effects.csv.

![Selected policies](selected.png)

## 4. Referensi loss saja: sensitivitas aritmetis

Pada trajectory F yang sama, hitung ulang gain dari baseline awal M atau U.
Diagonal memakai baseline model itu sendiri dan persis cocok dengan p* utama.
Off-diagonal hanya mengganti referensi per-sequence loss, bukan menjalankan
model baru. Propagasi undefined dapat membuat dekomposisi K tidak teridentifikasi.

{cross_table}

{cross_effects}

Efek reference menahan trajectory M; efek trajectory menahan reference M.
Interaksi adalah selisih kedua efek bersilang. Rincian p* dan signed mean gain
per kapasitas/pasangan tersedia di reference-sensitivity.csv dan
reference-capacity-effects.csv. Jangan menjumlahkan hanya komponen yang terdefinisi
untuk membuat kesimpulan total ketika komponen lain undefined.

![Reference sensitivity](reference.png)

Seluruh checkpoint konfirmasi juga menyimpan p* komponen, group+instance-only,
referensi oracle [0,log16,log16], signed mass, centered cumulative RMS dan Gram
cross-terms. Estimator primer tetap memakai seluruh gain bertanda terhadap
baseline pretrained asli. Maksimum galat identitas gain komponen:
{diag['identity_max_abs_error']:.9g}, di bawah toleransi frozen 2e-6.
Undefined dan boundary fits per kondisi/arm/metric tersimpan di diagnostics.csv
dan diagnostics.json; uniform p* selalu undefined, termasuk diagnostik.

## 5. Generalisasi, memorisasi, dan fit

{perf}

Kriteria generalisasi mensyaratkan test NLL turun ketat dengan kapasitas dan
validation <=epoch0 pada setiap kapasitas, dalam **setiap** corpus. Tabel sel
di atas melaporkan random dan uniform secara terpisah; hasil per corpus ada
di policy-summary.json. Tidak ada evaluasi test saat tuning atau pada epoch0.
Fit objective, negative-gain fraction dan boundary flags bukan kriteria seleksi.
Memorisasi dan clipping harus dibaca bersama p*, bukan bukti mekanisme kausal
clipping. Data akhir lengkap ada di all-checkpoints.csv.

## 6. Integritas, sumber daya dan reproduksi

Audit memeriksa {audit_result['historical_files_unchanged']} file historis tanpa
perubahan, {audit_result['model_checkpoints']} checkpoint adaptasi dan tepat
{audit_result['test_evaluations']} evaluasi test yang dibekukan sebelumnya.
Cold-model tensors sama lintas kondisi; pretrained model/loss awal sama lintas
arm/config dalam tiap kondisi. Full tokens/targets/type masks, bobot, batch
orders, source hashes, seleksi dan scalar metrics/p* direkonstruksi.

Training wall time {complete['elapsed_seconds']/60:.1f} menit mencakup pretraining,
setup, evaluasi dan penyimpanan; tidak mencakup persiapan, audit dan laporan.
Puncak alokasi adaptasi {max(r['peak_allocated_mib'] for r in results.values()):.2f} MiB;
reserved {max(r['peak_reserved_mib'] for r in results.values()):.2f} MiB.
Memori ini pengukuran PyTorch, bukan seluruh driver/desktop. Batas tiga jam
dan 468 run dipenuhi. Semua output lokal; tidak ada upload/publikasi.

Raw: `work/runs/{root.name}/`. Arsip ringkas memuat protokol, kode, data,
per-sequence loss, assignments, keputusan tuning, audit, laporan dan gambar.
Model binaries tetap lokal dengan hash di raw-manifest.json. Lingkungan ada
di environment-lock.txt. Notebook tidak dijalankan; skrip menghasilkan hasil.

## 7. Posisi ilmiah dan batas klaim

Hasil menguji intervensi objective pretraining dan ketergantungan gain pada
referensinya dalam tugas sintetis. Tiga kapasitas tidak cukup untuk perpindahan
antara dua puncak interior. Tiga corpus konfirmasi dan dua tuning pairs memberi
bukti terbatas. Manipulasi dapat mengubah representasi, kemampuan shared, dan
dinamika adaptasi sekaligus. Reference swapping membantu diagnosis aritmetis;
tidak membuktikan mediasi kausal baseline loss.

[Jane Street](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/)
memotivasi metrik dan pertanyaan scaling, tetapi eksperimen ini bukan replikasi
LM besar/private text mereka. Uniform-target regularization berkaitan dengan
[Pereyra et al.](https://arxiv.org/abs/1701.06548); pengukuran kalibrasi formal
berbeda dari NLL, seperti dibahas [Guo et al.](https://proceedings.mlr.press/v70/guo17a.html).
LITERATURE_CHECK.md mencatat sumber primer yang diperiksa kembali. Tidak ada
klaim novelty, kelayakan venue atau jaminan publikasi.
'''
    (out/'REPORT.md').write_text(text,encoding='utf-8')


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run-id',required=True); ap.add_argument('--wait',action='store_true')
    args=ap.parse_args(); root=ROOT/'work/runs'/args.run_id; out=HERE/f'results-{args.run_id}-analysis-r1'
    assert not out.exists(),'Preserve completed/partial analysis directory'
    torch.set_num_threads(4)
    if args.wait:
        print('Waiting for COMPLETE.json; CPU analysis only.',flush=True)
        while not (root/'COMPLETE.json').exists():
            if list((root/'runs').glob('*/failure.json')): raise RuntimeError('Training failure; preserve records')
            time.sleep(30)
    evidence,sel,results,records=audit(root); print('Primary audit PASS; frozen analyses begin.',flush=True)
    out.mkdir(); write(out/'AUDIT.json',evidence)
    rows=flat_rows(results); csvwrite(out/'all-checkpoints.csv',rows)
    summary,cell_rows,effect_rows=policy_analysis(sel,rows)
    write(out/'policy-summary.json',summary); csvwrite(out/'policy-cells.csv',cell_rows); csvwrite(out/'per-capacity-effects.csv',effect_rows)
    base,baseline_rows=baseline_analysis(rows); write(out/'baseline-summary.json',base); csvwrite(out/'baseline-records.csv',baseline_rows)
    initial_out=HERE/f'results-{args.run_id}'
    unchanged_names=['all-checkpoints.csv','policy-summary.json','policy-cells.csv','per-capacity-effects.csv',
                     'baseline-summary.json','baseline-records.csv']
    assert all(sha(out/name)==sha(initial_out/name) for name in unchanged_names)
    old_audit=read(initial_out/'AUDIT.json')
    assert {k:v for k,v in old_audit.items() if k!='utc'}=={k:v for k,v in evidence.items() if k!='utc'}
    diag,diag_rows,cross_rows,cross_effect_rows=diagnostic_analysis(results,records)
    write(out/'diagnostics.json',diag); csvwrite(out/'diagnostics.csv',diag_rows)
    csvwrite(out/'reference-sensitivity.csv',cross_rows); csvwrite(out/'reference-capacity-effects.csv',cross_effect_rows)
    fallbacks=[dict(name=x['name'],epoch=x['epoch'],**x['allocation']['gram_identity_check']) for x in diag['all']
        if x['allocation']['defined'] and not x['allocation']['gram_identity_check']['original_strict_pass']]
    write(out/'DIAGNOSTIC_AUDIT.json',dict(status='PASS_AFTER_DOCUMENTED_NUMERICAL_REPAIR',
        gain_identity_max_abs_error=diag['identity_max_abs_error'],original_strict_failures=fallbacks,
        checkpoints=len(records)*5,reference_diagonal_equals_primary=True,primary_definition_unchanged=True,
        every_primary_fit_matches_saved_training_result=True))
    write(out/'ANALYSIS_REPAIR.json',dict(utc=utc(),initial_failed_analysis=str(initial_out.relative_to(ROOT)),
        summaries_bytewise_unchanged={name:sha(out/name) for name in unchanged_names},
        original_audit_unchanged_except_timestamp=True,original_strict_failure_count=len(fallbacks),
        repaired_helper_sha256=sha(HERE/'diagnostics_roundoff.py'),repair_source_sha256=sha(Path(__file__))))
    figures(out,summary,base,diag); report(root,out,sel,summary,base,diag,evidence,results)
    text=(out/'REPORT.md').read_text(encoding='utf-8')
    text=text.replace('\n\n','\n\n**Catatan analisis:** audit utama lulus pada analisis awal, tetapi satu pemeriksaan '
        'Gram float64 melewati toleransi absolut 1e-12. Hasil ini memakai perbaikan verifikasi numerik '
        'yang didokumentasikan dalam NUMERICAL_REPAIR.md; kegagalan awal tetap disimpan. '
        'Tidak ada training ulang atau perubahan estimator/seleksi.\n\n',1)
    uf30=[r for r in rows if r['phase']=='confirm' and r['variant']=='U' and r['grid_index']==0 and
          r['arm']=='random' and r['width']==128 and r['epoch']==30]
    upper=sum(r['upper_boundary'] for r in uf30)
    chosen=[r for r in cell_rows if r['cell']=='U_T_ET' and r['arm']=='random']
    caution=(f'Pada U/F/C30, **{upper}/9** fit kapasitas menengah menyentuh batas pencarian p*=8. '
        f'Mean objective fit-nya {st.mean(r["objective"] for r in uf30):.6f}, dibanding '
        f'{summary["cells"]["M_F_C30"]["arms"]["random"]["capacity"][1]["objective"]["mean"]:.6f} pada M. '
        'Karena fit U jauh lebih buruk dan beberapa nilai dibatasi pencarian, puncak deskriptif ini '
        'tidak boleh dianggap bukti mekanisme pangkat yang cocok dengan baik. '
        f'Pada U/T/ET, {sum(r["p"] is None for r in chosen)}/27 p* kapasitas/pasangan undefined dan '
        f'{sum(r["upper_boundary"] for r in chosen)}/27 menyentuh batas atas. '
        'Tidak ada nilai yang dihapus atau rentang pencarian yang diperluas.\n\n')
    text=text.replace('## 5. Generalisasi, memorisasi, dan fit\n\n','## 5. Generalisasi, memorisasi, dan fit\n\n'+caution,1)
    (out/'REPORT.md').write_text(text,encoding='utf-8')
    for name in ['NUMERICAL_REPAIR.md','diagnostics_roundoff.py','probe_roundoff.py','check_roundoff.py',
                 f'roundoff-probe-{args.run_id}.json','NUMERICAL_CHECKS.json']:
        shutil.copy2(HERE/name,out/name)
    shutil.copy2(HERE/'LITERATURE_CHECK.md',out/'LITERATURE_CHECK.md'); shutil.copy2(Path(__file__),out/'analyze_stage4_r1.py')
    write(out/'analysis-provenance.json',dict(utc=utc(),source_sha256=sha(Path(__file__)),protocol_sha256=sha(HERE/'PROTOCOL_STAGE4.md')))
    write(out/'raw-manifest.json',{str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()})
    archive=out/'run-records.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file() and p.name not in ['cold.pt','pretrained.pt'] and not p.name.startswith('model-e'):
                z.write(p,'raw/'+str(p.relative_to(root)))
        for p in out.iterdir():
            if p.is_file() and p!=archive: z.write(p,'report/'+p.name)
        z.write(HERE/'README.md','README.md')
    with zipfile.ZipFile(archive) as z: assert z.testzip() is None
    write(out/'ARCHIVE_CHECK.json',dict(sha256=sha(archive),bytes=archive.stat().st_size,crc='PASS'))
    print(json.dumps(dict(output=str(out),audit='PASS',diagnostics='PASS',archive='PASS',
        primary_effect=summary['effects']['primary_U_minus_M_F_C30']['between_corpora'],manipulation=base['manipulation_pass'])),flush=True)


if __name__=='__main__': main()
