"""Audit and report v0.4 under the frozen Stage 3 comparison/diagnostic protocol."""
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
from collections import defaultdict
from pathlib import Path
sys.dont_write_bytecode=True
import torch
from stage3 import ROOT,HERE,OLD,OLD_REPORT,CAPS,GRID,EPOCHS,TUNE,REPS,SOURCES
from engine import read,write,sha,utc,data,weights,orders,tensor_hash
from diagnostics import fit,decompose,contrast,difference,interaction


def desc(values):
    defined=[x for x in values if x is not None]
    complete=len(defined)==len(values) and bool(values)
    return dict(n=len(values),undefined=len(values)-len(defined),positive=sum(x>0 for x in defined),
                negative=sum(x<0 for x in defined),zero=sum(x==0 for x in defined),
                mean=st.mean(defined) if complete else None,
                sd=st.stdev(defined) if complete and len(defined)>1 else 0. if complete else None,
                minimum=min(defined) if complete else None,maximum=max(defined) if complete else None)


def replicated(values,key='value'):
    corpora=[]
    for d in sorted({x['data_seed'] for x in values}):
        stats=desc([x[key] for x in values if x['data_seed']==d])
        corpora.append(dict(data_seed=d,**stats))
    means=[x['mean'] for x in corpora]
    consistent='undefined' if any(x is None for x in means) else (
        'positive' if all(x>0 for x in means) else 'negative' if all(x<0 for x in means)
        else 'zero' if all(x==0 for x in means) else 'mixed')
    return dict(all_pairs=desc([x[key] for x in values]),corpora=corpora,
                between_corpora=desc(means),corpus_mean_sign=consistent,values=values)


def csvwrite(path,rows):
    if not rows: return
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(rows)


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])


def fmt(x): return 'undefined' if x is None else f'{x:.6f}'


def independent_selection(root,sel):
    vals=[]
    for width,_ in CAPS:
        for i in range(18):
            for d,s,_ in TUNE:
                for arm in ['random','uniform']:
                    path=OLD/'runs'/f'tune-w{width}-d{d}-s{s}-g{i:02d}-{arm}'/'history.json'
                    assert sha(path)==sel['input_hashes'][str(path.relative_to(ROOT))]
                    vals.extend(dict(width=width,grid_index=i,data_seed=d,seed=s,arm=arm,
                                     epoch=h['epoch'],validation_nll=h['validation']['loss']) for h in read(path))
    assert vals==sel['inputs']
    for policy,arms in [('J',{'random','uniform'}),('R',{'random'})]:
        for width,_ in CAPS:
            candidates=[]
            for i,setting in enumerate(GRID):
                for e in EPOCHS:
                    scores=[x['validation_nll'] for x in vals if x['width']==width and x['grid_index']==i
                            and x['epoch']==e and x['arm'] in arms]
                    candidates.append(dict(grid_index=i,**setting,epoch=e,validation_nll=sum(scores)/len(scores),scores=scores))
            candidates.sort(key=lambda x:(x['validation_nll'],x['epoch'],x['lr'],x['wd'],int(x['clip'] is None)))
            assert candidates[0]==sel['policies'][policy][str(width)]
            assert sorted(sel['all_scores'][f'{policy}-{width}'],key=lambda x:(x['validation_nll'],x['epoch'],
                x['lr'],x['wd'],int(x['clip'] is None)))==candidates
    expected=[]
    for w,l in CAPS:
        indices=sorted({sel['policies'][p][str(w)]['grid_index'] for p in ['F','J','R']})
        assert indices==sel['unique_configs'][str(w)]
        for d,s,p in REPS:
            for i in indices:
                for arm in ['random','uniform']:
                    expected.append(dict(name=f'confirm-w{w}-d{d}-s{s}-g{i:02d}-{arm}',width=w,layers=l,
                        data_seed=d,seed=s,pretrain_seed=p,grid_index=i,**GRID[i],arm=arm,
                        policies=[policy for policy in ['F','J','R'] if sel['policies'][policy][str(w)]['grid_index']==i],
                        epochs=60,test_epochs=EPOCHS))
    assert expected==sel['run_schedule'] and len(expected)==sel['planned_runs']
    assert sel['planned_runs']<=144 and not sel['test_used'] and not sel['confirmation_used']


def audit(root):
    assert (root/'COMPLETE.json').exists()
    failures=list((root/'runs').glob('*/failure.json'))
    assert not failures, failures
    manifest=read(root/'source_manifest.json')
    assert manifest=={name:sha(HERE/name) for name in SOURCES}
    assert all(sha(root/'source'/n)==h for n,h in manifest.items())
    historical=read(root/'historical_manifest.json')
    for name,h in historical.items(): assert sha(ROOT/name)==h, f'Historical file changed: {name}'
    sel=read(root/'selection.json'); independent_selection(root,sel)
    expected={c['name']:c for c in sel['run_schedule']}
    actual={p.parent.name for p in (root/'runs').glob('*/result.json')}
    assert actual==set(expected)
    events=[json.loads(x) for x in (root/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    frozen=[x for x in events if x['kind']=='selection_frozen']
    assert len(frozen)==1 and frozen[0]['sha256']==sha(root/'selection.json')
    tests=[x for x in events if x['kind']=='test_evaluation']
    assert {(x['name'],x['epoch']) for x in tests}=={(name,e) for name in expected for e in EPOCHS}
    assert len(tests)==5*sel['planned_runs']
    assert all(x['utc']>frozen[0]['utc'] and x['selection_sha256']==sha(root/'selection.json') for x in tests)
    assert all(x['utc']>frozen[0]['utc'] for x in events if x['kind']=='run_start')
    corpora={}
    for folder in (root/'corpora').iterdir():
        pre=folder.name.startswith('pre-'); seed=int(folder.name.split('-')[1])
        saved=torch.load(folder/'dataset.pt',weights_only=True)
        regenerated,meta=data(seed,pretrain=pre); hidden,_=data(seed,pretrain=pre,include_test=False)
        dm=read(folder/'metadata.json')
        assert dm['sequence_keys_by_split']==meta['sequence_keys_by_split']
        assert dm['file_sha256']==sha(folder/'dataset.pt')
        for split,pair in saved.items():
            assert all(torch.equal(a,b) for a,b in zip(pair,regenerated[split]))
            assert tensor_hash(*pair)==dm['tensor_sha256'][split]
            if split!='test': assert all(torch.equal(a,b) for a,b in zip(pair,hidden[split]))
        keys=sum(dm['sequence_keys_by_split'].values(),[])
        assert len(keys)==len(set(keys)); corpora[folder.name]=dm
    assert len(corpora)==6
    baselines={}
    for folder in (root/'baselines').iterdir():
        r=read(folder/'result.json')
        assert r['source_sha256']==manifest
        assert sha(folder/'pretrained.pt')==r['checkpoint_sha256']
        assert sha(folder/'cold.pt')==r['cold_sha256']
        oo=torch.load(folder/'orders.pt',weights_only=True)
        assert torch.equal(oo,orders(r['seed'],2048,4)) and tensor_hash(oo)==r['batch_order_sha256']
        baselines[folder.name]=r
    assert len(baselines)==27
    results={}; records={}; initial_groups={}; cross_groups={}; pair_checks=0
    for name in sorted(actual):
        folder=root/'runs'/name; r=read(folder/'result.json'); c=r['config']
        assert c==read(folder/'config.json') and all(c[k]==v for k,v in expected[name].items())
        assert c['source_sha256']==manifest and c['selection_sha256']==sha(root/'selection.json')
        dm=corpora[f'adapt-{c["data_seed"]}']; pm=corpora[f'pre-{c["pretrain_seed"]}']
        assert set(sum(dm['sequence_keys_by_split'].values(),[])).isdisjoint(sum(pm['sequence_keys_by_split'].values(),[]))
        assert c['data_sha256']==dm['tensor_sha256']
        b=baselines[f'w{c["width"]}-s{c["seed"]}-d{c["pretrain_seed"]}']
        assert c['baseline_sha256']==b['checkpoint_sha256']
        a=torch.load(folder/'assignment.pt',weights_only=True)
        rec=torch.load(folder/'sequence_losses.pt',weights_only=True)
        assert torch.equal(a['weights'],weights(c['seed'],c['arm'])) and torch.equal(a['weights'],rec['weights'])
        assert torch.equal(a['orders'],orders(c['seed']))
        assert tensor_hash(a['weights'])==c['weight_sha256'] and tensor_hash(a['orders'])==c['batch_order_sha256']
        assert [x['epoch'] for x in r['history']]==[0]+EPOCHS
        assert [x['epoch'] for x in rec['checkpoints']]==[0]+EPOCHS
        assert [x['epoch'] for x in r['epoch_stats']]==list(range(1,61))
        for h,cp in zip(r['history'],rec['checkpoints']):
            for split in ['train','validation']+(['test'] if h['epoch'] else []):
                assert torch.isfinite(cp[split]['loss']).all()
                assert abs(float(cp[split]['loss'].mean())-h[split]['loss'])<1e-7
                for j,component in enumerate(['shared','group','instance']):
                    assert abs(float(cp[split]['component_loss'][:,j].mean())-h[split][component]['loss'])<1e-7
                    assert abs(float(cp[split]['component_accuracy'][:,j].mean())-h[split][component]['accuracy'])<1e-7
            if h['epoch']==0:
                assert cp['test'] is None and h['test'] is None and h['p_star']['p'] is None
            else:
                ff=fit(rec['weights'],rec['checkpoints'][0]['train']['loss']-cp['train']['loss'])
                assert ff==h['p_star']
                assert sha(folder/f'model-e{h["epoch"]:02d}.pt')==r['checkpoint_sha256'][str(h['epoch'])]
                assert h['clipping_cumulative']==sum(x['gradient_clip_fraction'] for x in r['epoch_stats'][:h['epoch']])/h['epoch']
        key=(c['width'],c['data_seed'],c['seed'])
        initial=rec['checkpoints'][0]
        if key in initial_groups:
            prev,prevc=initial_groups[key]
            assert c['baseline_sha256']==prevc['baseline_sha256']
            assert c['batch_order_sha256']==prevc['batch_order_sha256']
            for split in ['train','validation']:
                for field in ['loss','component_loss','component_accuracy']:
                    assert torch.equal(initial[split][field],prev[split][field])
            pair_checks+=1
        else: initial_groups[key]=(initial,c)
        key=(c['data_seed'],c['seed'],c['arm'])
        value=(c['data_sha256'],c['weight_sha256'],c['batch_order_sha256'])
        if key in cross_groups: assert value==cross_groups[key]
        else: cross_groups[key]=value
        results[name]=r; records[name]=rec
    complete=read(root/'COMPLETE.json')
    assert complete['completed_runs']==len(actual) and complete['elapsed_seconds']<=7200
    evidence=dict(status='PASS',utc=utc(),runs=len(actual),pretraining=27,test_evaluations=len(tests),
        baseline_pair_checks=pair_checks,historical_files_unchanged=len(historical),failed_runs=[],
        selection_sha256=sha(root/'selection.json'),checks=[
        'source/protocol snapshots immutable','historical v0.1/v0.2/v0.3 hashes unchanged',
        'selection reconstructed independently using only tuning validation NLL','exact deduplicated run schedule',
        'full corpus regeneration and test-toggle tokens/labels/types equal','disjoint phase/split keys',
        'weight/order tensors regenerate and pair across capacities/configurations',
        'full initial losses and checkpoint hashes equal across arms AND configurations',
        'all saved model hashes verified','test exactly once at each preregistered epoch after freeze',
        'every saved scalar/component metric and original p* reconstructed','compute cap respected'])
    return evidence,sel,results,records


def flat_rows(results):
    rows=[]
    for name,r in results.items():
        c=r['config']
        for h in r['history']:
            x={k:c[k] for k in ['name','width','layers','parameters','data_seed','seed','pretrain_seed','grid_index','lr','wd','clip','arm']}
            x.update(epoch=h['epoch'],p=h['p_star']['p'],p_reason=h['p_star'].get('reason'),
                objective=h['p_star'].get('objective'),total_gain=h['total_gain'],negative_gain_fraction=h['negative_gain_fraction'],
                lower_boundary=h['p_star'].get('at_lower_bound',False),upper_boundary=h['p_star'].get('at_upper_bound',False),
                clipping=h.get('clipping_cumulative'),epoch0_validation_nll=r['history'][0]['validation']['loss'])
            for split in ['train','validation','test']:
                x[f'{split}_nll']=h[split]['loss'] if h[split] is not None else None
                for typ in ['shared','group','instance']:
                    for metric in ['loss','accuracy']:
                        x[f'{split}_{typ}_{metric}']=h[split][typ][metric] if h[split] is not None else None
            rows.append(x)
    return rows


def policy_analysis(sel,rows):
    index={(x['width'],x['data_seed'],x['seed'],x['arm'],x['grid_index'],x['epoch']):x for x in rows}
    schedules={f'C{e}':{str(w):e for w,_ in CAPS} for e in EPOCHS}
    schedules.update(sel['schedules'])
    cells={}; cell_rows=[]; k_index={}; value_index={}; fingerprints={}
    for policy in ['F','J','R']:
        for schedule,epochs in schedules.items():
            fingerprint=tuple((w,sel['policies'][policy][str(w)]['grid_index'],epochs[str(w)]) for w,_ in CAPS)
            key=f'{policy}_{schedule}'
            alias=fingerprints.get(fingerprint)
            fingerprints.setdefault(fingerprint,key)
            variants={}
            for arm in ['random','uniform']:
                ks=[]; all_runs=[]; generalization=[]
                for d,s,_ in REPS:
                    selected=[]
                    for w,_ in CAPS:
                        row=index[w,d,s,arm,sel['policies'][policy][str(w)]['grid_index'],epochs[str(w)]]
                        selected.append(row)
                        cell_rows.append(dict(policy=policy,schedule=schedule,**row))
                        value_index[key,arm,d,s,w]=row
                    kval=contrast(*[x['p'] for x in selected])
                    k_index[key,arm,d,s]=kval
                    ks.append(dict(data_seed=d,seed=s,value=kval))
                    all_runs.extend(selected)
                stats=replicated(ks)
                if arm=='uniform': verdict='undefined_uniform'
                elif stats['all_pairs']['undefined']: verdict='inconclusive_undefined'
                elif stats['all_pairs']['positive']==9: verdict='survives'
                elif all(c['mean']<=0 for c in stats['corpora']): verdict='disappears'
                else: verdict='mixed/inconclusive'
                for d in sorted({x['data_seed'] for x in all_runs}):
                    grouped=[[x for x in all_runs if x['width']==w and x['data_seed']==d] for w,_ in CAPS]
                    test=[st.mean(x['test_nll'] for x in g) for g in grouped]
                    val=[st.mean(x['validation_nll'] for x in g) for g in grouped]
                    v0=[st.mean(x['epoch0_validation_nll'] for x in g) for g in grouped]
                    generalization.append(dict(data_seed=d,test_nll=test,validation_nll=val,baseline_validation_nll=v0,
                        test_monotonic=test[0]>test[1]>test[2],validation_improves=all(a<=b for a,b in zip(val,v0))))
                capacity=[]
                for w,_ in CAPS:
                    group=[x for x in all_runs if x['width']==w]
                    keys=['p','objective','train_nll','validation_nll','test_nll','train_instance_accuracy','clipping','total_gain','negative_gain_fraction']
                    capacity.append(dict(width=w,epoch=epochs[str(w)],parameters=group[0]['parameters'],
                                         **{k:desc([x[k] for x in group]) for k in keys}))
                variants[arm]=dict(peak=stats,verdict=verdict,generalization=generalization,capacity=capacity,
                    generalization_met=all(x['test_monotonic'] and x['validation_improves'] for x in generalization))
            cells[key]=dict(policy=policy,schedule=schedule,alias_of=alias,arms=variants)
    definitions={
      'Q1_optimizer_C30': [('J_C30',1),('F_C30',-1)],
      'Q1_optimizer_EJ': [('J_EJ',1),('F_EJ',-1)],
      'Q1_duration_F': [('F_EJ',1),('F_C30',-1)],
      'Q1_duration_J': [('J_EJ',1),('J_C30',-1)],
      'Q1_interaction': [('J_EJ',1),('J_C30',-1),('F_EJ',-1),('F_C30',1)],
      'Q2_configuration_EJ': [('R_EJ',1),('J_EJ',-1)],
      'Q2_duration_J': [('J_ER',1),('J_EJ',-1)],
      'Q2_interaction': [('R_ER',1),('R_EJ',-1),('J_ER',-1),('J_EJ',1)],
      'Q2_total': [('R_ER',1),('J_EJ',-1)]}
    effects={}; effect_rows=[]
    def calc(values): return None if any(v is None for v,_ in values) else sum(v*c for v,c in values)
    for label,terms in definitions.items():
        vals=[dict(data_seed=d,seed=s,value=calc([(k_index[cell,'random',d,s],coef) for cell,coef in terms])) for d,s,_ in REPS]
        effects[label]=replicated(vals)
        for arm in ['random','uniform']:
            for w,_ in CAPS:
                for metric in ['p','train_nll','validation_nll','test_nll','train_instance_accuracy','clipping']:
                    for d,s,_ in REPS:
                        value=calc([(value_index[cell,arm,d,s,w][metric],coef) for cell,coef in terms])
                        effect_rows.append(dict(effect=label,arm=arm,width=w,metric=metric,data_seed=d,seed=s,value=value))
    grouped_effects={}
    for key in sorted({(x['effect'],x['arm'],x['width'],x['metric']) for x in effect_rows}):
        g=[x for x in effect_rows if (x['effect'],x['arm'],x['width'],x['metric'])==key]
        grouped_effects['|'.join(map(str,key))]=replicated(g)
    return dict(cells=cells,effects=effects,per_capacity_effects=grouped_effects),cell_rows,effect_rows


def diagnostic_analysis(root,sel,results,records):
    output=[]; inputs={}; old_records={}
    for name,rec in records.items():
        old_records[('fresh_confirmation',name)]=(results[name]['config'],rec)
    retrospective=root/'retrospective'
    retrospective.mkdir(exist_ok=False)
    for file in sorted((OLD/'runs').glob('confirm-*/result.json')):
        name=file.parent.name
        rr=read(file); rec=torch.load(file.parent/'sequence_losses.pt',weights_only=True)
        old_records['stage2_retrospective',name]=(rr['config'],rec)
        folder=retrospective/name; folder.mkdir()
        for p in [file,file.parent/'sequence_losses.pt']:
            inputs[str(p.relative_to(ROOT))]=sha(p); shutil.copy2(p,folder/p.name)
    baseline_rows=[]
    for width,_ in CAPS:
        for d,s,_ in TUNE:
            folder=OLD/'runs'/f'tune-w{width}-d{d}-s{s}-g00-random'
            r=read(folder/'result.json')
            rec=torch.load(folder/'sequence_losses.pt',weights_only=True)
            dest=retrospective/folder.name; dest.mkdir()
            for p in [folder/'result.json',folder/'sequence_losses.pt']:
                inputs[str(p.relative_to(ROOT))]=sha(p); shutil.copy2(p,dest/p.name)
            h=r['history'][0]
            for split in ['train','validation']:
                baseline_rows.append(dict(source='stage2_tuning_retrospective',width=width,data_seed=d,seed=s,split=split,
                    nll=h[split]['loss'],**{typ:h[split][typ]['loss'] for typ in ['shared','group','instance']}))
    seen_baselines=set()
    for (source,name),(config,rec) in old_records.items():
        initial=rec['checkpoints'][0]
        if source=='fresh_confirmation':
            basekey=(config['width'],config['data_seed'],config['seed'])
            if basekey not in seen_baselines:
                seen_baselines.add(basekey)
                h=results[name]['history'][0]
                for split in ['train','validation']:
                    baseline_rows.append(dict(source=source,width=config['width'],data_seed=config['data_seed'],seed=config['seed'],split=split,
                        nll=h[split]['loss'],**{typ:h[split][typ]['loss'] for typ in ['shared','group','instance']}))
        for cp in rec['checkpoints'][1:]:
            diag=decompose(rec['weights'],initial['train'],cp['train'])
            output.append(dict(source=source,name=name,width=config['width'],data_seed=config['data_seed'],seed=config['seed'],
                               arm=config.get('arm',config.get('weighting')),grid_index=config.get('grid_index'),epoch=cp['epoch'],**diag))
    assert len([x for x in output if x['source']=='fresh_confirmation'])==sel['planned_runs']*5
    assert len([x for x in output if x['source']=='stage2_retrospective'])==450
    write(root/'retrospective_sources.json',inputs)
    diagnostics_index={(x['name'],x['epoch']):x for x in output if x['source']=='fresh_confirmation'}
    selected={}; diagnostic_rows=[]
    for policy in ['F','J','R']:
        for schedule in ['EJ','C30','C60']:
            chosen=[]
            for w,_ in CAPS:
                for d,s,_ in REPS:
                    i=sel['policies'][policy][str(w)]['grid_index']
                    e=sel['schedules']['EJ'][str(w)] if schedule=='EJ' else int(schedule[1:])
                    name=f'confirm-w{w}-d{d}-s{s}-g{i:02d}-random'
                    chosen.append(diagnostics_index[name,e])
            selected[f'{policy}_{schedule}']=[]
            for w,_ in CAPS:
                g=[x for x in chosen if x['width']==w]
                entry=dict(width=w,n=len(g),primary_p=desc([x['primary']['p'] for x in g]),
                           group_instance_p=desc([x['group_instance_only']['p'] for x in g]),
                           oracle_p=desc([x['oracle_reference']['p'] for x in g]),
                           oracle_gain=desc([x['oracle_reference']['mean_gain'] for x in g]),components={})
                for j,component in enumerate(['shared','group','instance']):
                    entry['components'][component]=dict(
                        baseline_nll=desc([x['components'][component]['baseline_nll'] for x in g]),
                        current_nll=desc([x['components'][component]['current_nll'] for x in g]),
                        mean_gain=desc([x['components'][component]['fit']['mean_gain'] for x in g]),
                        p=desc([x['components'][component]['fit']['p'] for x in g]),
                        signed_mass_share=desc([x['allocation']['signed_mass_share'][j] if x['allocation']['defined'] else None for x in g]),
                        centered_rms=desc([x['allocation']['centered_rms'][j] if x['allocation']['defined'] else None for x in g]))
                selected[f'{policy}_{schedule}'].append(entry)
    counts={}
    for x in output:
        measures={'primary':x['primary'],'group_instance':x['group_instance_only'],'oracle_reference':x['oracle_reference'],
                  **{k:v['fit'] for k,v in x['components'].items()}}
        for metric,z in measures.items():
            reason=z.get('reason','defined')
            key=f'{x["source"]}|{x["arm"]}|{metric}|{reason}'
            counts[key]=counts.get(key,0)+1
            diagnostic_rows.append(dict(source=x['source'],name=x['name'],width=x['width'],data_seed=x['data_seed'],seed=x['seed'],
                                        arm=x['arm'],epoch=x['epoch'],metric=metric,**z))
    return dict(all=output,selected=selected,undefined_counts=counts,baseline_rows=baseline_rows,
                identity_max_abs_error=max(x['identity_max_abs_error'] for x in output)),diagnostic_rows


def figures(out,summary,baseline):
    os.environ['MPLCONFIGDIR']=str(ROOT/'work/.matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    colors={'F':'#556678','J':'#147e9b','R':'#b56939'}
    labels={'F':'F: fixed v0.2 optimizer','J':'J: joint validation selection','R':'R: random-only selection'}
    fig,axes=plt.subplots(1,2,figsize=(10,4.5),sharey=True)
    for ax,schedule in zip(axes,['C30','EJ']):
        for policy in ['F','J']:
            cell=summary['cells'][f'{policy}_{schedule}']['arms']['random']
            y=[x['p']['mean'] for x in cell['capacity']]
            ax.plot(range(3),y,'o-',color=colors[policy],label=labels[policy])
        ax.set(title='Common epoch 30' if schedule=='C30' else 'Frozen epochs 30 / 10 / 10',
               xticks=range(3),xticklabels=['113k','622k','3.21M'],xlabel='Capacity (parameters)',ylabel='Mean p* (unitless)')
        ax.legend(frameon=False,fontsize=8)
    fig.suptitle('Optimizer × duration: random weights, 3 corpora × 3 model/weight seeds',fontsize=11)
    fig.tight_layout(); fig.savefig(out/'optimizer-duration.png',dpi=180); plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4.5))
    for policy in ['J','R']:
        cell=summary['cells'][f'{policy}_EJ']['arms']['random']
        axes[0].plot(range(3),[x['p']['mean'] for x in cell['capacity']],'o-',color=colors[policy],label=labels[policy])
        for arm,style in [('random','-'),('uniform','--')]:
            cc=summary['cells'][f'{policy}_EJ']['arms'][arm]
            axes[1].plot(range(3),[x['test_nll']['mean'] for x in cc['capacity']],marker='o',ls=style,
                         color=colors[policy],label=f'{policy}, {arm}')
    for ax in axes:
        ax.set(xticks=range(3),xticklabels=['113k','622k','3.21M'],xlabel='Capacity (parameters)')
        ax.legend(frameon=False,fontsize=8)
    axes[0].set(title='Selection objective: original exponent',ylabel='Mean p* (unitless)')
    axes[1].set(title='Held-out performance by arm',ylabel='Test NLL (nats / answer token)')
    fig.suptitle('J and R select the same epoch vector; only the middle-capacity WD differs',fontsize=11)
    fig.tight_layout(); fig.savefig(out/'selection-objective.png',dpi=180); plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4.5),sharey=True)
    for ax,source,title in zip(axes,['stage2_tuning_retrospective','fresh_confirmation'],
                               ['Stage 2 tuning: retrospective','Stage 3: fresh confirmation']):
        bottom=np.zeros(3)
        for typ,color in zip(['shared','group','instance'],['#88949e','#147e9b','#b56939']):
            yy=np.array([st.mean(x[typ]/3 for x in baseline if x['source']==source and x['split']=='validation' and x['width']==w) for w,_ in CAPS])
            ax.bar(range(3),yy,bottom=bottom,label=typ,color=color); bottom+=yy
        ax.set(title=title,xticks=range(3),xticklabels=['113k','622k','3.21M'],
               xlabel='Capacity (parameters)',ylabel='Baseline validation NLL\n(component contribution, nats / answer token)')
        ax.legend(frameon=False,fontsize=8)
    fig.suptitle('Shared-only pretraining evaluated on the mixed task; each component weighted 1/3',fontsize=11)
    fig.tight_layout(); fig.savefig(out/'baseline-components.png',dpi=180); plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(12,4.3),sharey=True)
    for ax,policy in zip(axes,['F','J','R']):
        for e,color in zip([1,3,10,30,60],['#999999','#307991','#9f8c38','#4e824a','#b56939']):
            cc=summary['cells'][f'{policy}_C{e}']['arms']['random']
            ax.plot(range(3),[x['p']['mean'] for x in cc['capacity']],'o-',color=color,label=f'Epoch {e}')
        ax.set(title=labels[policy],xticks=range(3),xticklabels=['113k','622k','3.21M'],xlabel='Capacity (parameters)',ylabel='Mean p* (unitless)')
    axes[-1].legend(frameon=False,fontsize=8)
    fig.suptitle('Fixed secondary trajectories: all epochs declared before confirmation',fontsize=11)
    fig.tight_layout(); fig.savefig(out/'trajectories.png',dpi=180); plt.close(fig)


def report(root,out,sel,summary,diagnostics,audit_result,results):
    primary=['F_C30','F_EJ','J_C30','J_EJ','J_ER','R_EJ','R_ER']
    cell_table=table(['Cell','Alias','Mean K','Between-corpus SD','Positive / 9','Peak verdict','Random generalization'],
        [[key,summary['cells'][key]['alias_of'] or '-',fmt(summary['cells'][key]['arms']['random']['peak']['between_corpora']['mean']),
          fmt(summary['cells'][key]['arms']['random']['peak']['between_corpora']['sd']),
          summary['cells'][key]['arms']['random']['peak']['all_pairs']['positive'],
          summary['cells'][key]['arms']['random']['verdict'],summary['cells'][key]['arms']['random']['generalization_met']] for key in primary])
    effects_table=table(['Effect on K','Mean','Between-corpus SD','Corpus-mean sign'],
        [[key,fmt(v['between_corpora']['mean']),fmt(v['between_corpora']['sd']),v['corpus_mean_sign']] for key,v in summary['effects'].items()])
    choice_table=table(['Policy','Width','LR','WD','Clip','Selected epoch'],
        [[p,w,c['lr'],c['wd'],c['clip'],c['epoch'] if p!='F' else 'fixed trajectories']
         for p in ['F','J','R'] for w,c in sel['policies'][p].items()])
    perf_rows=[]
    for key in ['F_C30','F_EJ','J_C30','J_EJ','R_ER']:
        for arm in ['random','uniform']:
            for c in summary['cells'][key]['arms'][arm]['capacity']:
                perf_rows.append([key,arm,c['width'],c['epoch'],fmt(c['p']['mean']),fmt(c['train_nll']['mean']),
                    fmt(c['validation_nll']['mean']),fmt(c['test_nll']['mean']),
                    f'{100*c["train_instance_accuracy"]["mean"]:.2f}%',f'{100*c["clipping"]["mean"]:.1f}%'])
    perf_table=table(['Cell','Arm','Width','Epoch','p*','Train NLL','Validation NLL','Test NLL','Instance train acc','Clipping'],perf_rows)
    baseline_summary=[]
    for source in ['stage2_tuning_retrospective','fresh_confirmation']:
        for w,_ in CAPS:
            g=[x for x in diagnostics['baseline_rows'] if x['source']==source and x['width']==w and x['split']=='validation']
            baseline_summary.append([source,w,fmt(st.mean(x['nll'] for x in g))]+
                                    [fmt(st.mean(x[t] for x in g)) for t in ['shared','group','instance']])
    baseline_table=table(['Source','Width','Total val NLL','Shared NLL','Group NLL','Instance NLL'],baseline_summary)
    dg_rows=[]
    for c in diagnostics['selected']['J_EJ']:
        for typ,v in c['components'].items():
            dg_rows.append([c['width'],typ,fmt(v['baseline_nll']['mean']),fmt(v['current_nll']['mean']),
                fmt(v['mean_gain']['mean']),fmt(v['signed_mass_share']['mean']),fmt(v['centered_rms']['mean']),
                fmt(v['p']['mean']),v['p']['undefined']])
    dg_table=table(['Width','Component','Initial train NLL','Current NLL','Signed mean gain','Gain mass share','Centered cumulative RMS','Component p*','Undefined / 9'],dg_rows)
    sensitivity_table=table(['Cell','Width','Original p*','Group+instance p*','Oracle-ref p*','Oracle undefined / 9','Oracle mean gain'],
        [[cell,c['width'],fmt(c['primary_p']['mean']),fmt(c['group_instance_p']['mean']),fmt(c['oracle_p']['mean']),
          c['oracle_p']['undefined'],fmt(c['oracle_gain']['mean'])] for cell in ['J_EJ','J_C30','J_C60'] for c in diagnostics['selected'][cell]])
    q1=summary['effects']; q2=summary['cells']['R_ER']['arms']['random']
    q1_text=(f'Pada data baru, perubahan jadwal C30 → EJ menghasilkan mean perubahan K '
             f'{fmt(q1["Q1_duration_F"]["between_corpora"]["mean"])} dengan optimizer F dan '
             f'{fmt(q1["Q1_duration_J"]["between_corpora"]["mean"])} dengan J. '
             f'Interaksi optimizer×durasi adalah {fmt(q1["Q1_interaction"]["between_corpora"]["mean"])} '
             f'(tanda mean corpus: {q1["Q1_interaction"]["corpus_mean_sign"]}).')
    q1_text += (' Dengan epoch 30 yang sama, F/J memberi verdict '
                f'{summary["cells"]["F_C30"]["arms"]["random"]["verdict"]} / '
                f'{summary["cells"]["J_C30"]["arms"]["random"]["verdict"]}; '
                'pada jadwal 30/10/10 verdict-nya '
                f'{summary["cells"]["F_EJ"]["arms"]["random"]["verdict"]} / '
                f'{summary["cells"]["J_EJ"]["arms"]["random"]["verdict"]}. '
                'Ini memisahkan perubahan checkpoint pada trajectory yang sama dari perubahan '
                'konfigurasi optimizer dalam eksperimen terkontrol ini.')
    q2_text=(f'Seleksi random-only menghasilkan verdict {q2["verdict"]}, '
             f'{q2["peak"]["all_pairs"]["positive"]}/9 kontras positif. '
             f'Perubahan total K terhadap joint selection: {fmt(q1["Q2_total"]["between_corpora"]["mean"])}. '
             'EJ=ER persis, sehingga efek perubahan jadwal dan interaksinya pada perbandingan tujuan seleksi '
             'adalah nol karena desain terpilih identik. Perbedaan yang tersisa adalah konfigurasi, '
             'khususnya WD 0,1 → 1 pada kapasitas menengah dengan LR dan clipping tetap.')
    complete=read(root/'COMPLETE.json')
    oracle_undefined=sum(c['oracle_p']['undefined'] for c in diagnostics['selected']['J_EJ'])
    baseline_text=(f'Pada J/EJ, referensi oracle/uniform alternatif menghasilkan p* undefined pada '
                   f'{oracle_undefined}/27 pasangan kapasitas/corpus/seed. '
                   'Bandingkan aggregate gain terhadap referensi itu dengan gain terhadap pretrained baseline '
                   'sebelum menafsirkan besarnya loss reduction sebagai pembelajaran pola spesifik. '
                   'Ini sensitivitas terhadap referensi, bukan efek kausal mengubah pretraining.')
    text=f'''# Stage 3 v0.4: optimizer, durasi, tujuan seleksi, dan baseline

108 run konfirmasi berpasangan dan 27 checkpoint pretraining selesai tanpa
kegagalan. Tiga corpus baru × tiga seed model/bobot; enam konfigurasi unik
lintas tiga kapasitas, dengan random dan uniform. Tidak ada grid tuning baru.
Audit integritas **PASS**. Semua angka di bawah berasal dari protokol yang
dibekukan sebelum konfirmasi; diagnostik Stage 2 diberi label retrospektif.

## 1. Optimizer dan durasi

{q1_text}

F adalah LR 1e-4, WD 0,1, clipping 1 pada semua kapasitas. J adalah konfigurasi
pilihan joint validation Stage 2. C30 berarti epoch 30/30/30; EJ berarti 30/10/10.
K = p* menengah − max(p* kecil,p* besar). Optimizer dan jadwal disilangkan pada
corpus, checkpoint awal, bobot, dan batch order identik. Kontras ini tidak
menyamakan intervensi gabungan LR/WD dengan efek regularisasi saja.

{cell_table}

Alias menandai sel yang memakai trajectory dan checkpoint persis sama. Sel-sel
itu tidak dihitung sebagai replikasi tambahan. F/J identik pada kapasitas kecil.

![Optimizer dan durasi](optimizer-duration.png)

{effects_table}

Seluruh 9 kontras dan mean/SD dalam tiap corpus tersedia di policy-summary.json
dan policy-cells.csv. SD pada tabel efek adalah SD tiga mean corpus, bukan
ketidakpastian dari sembilan dataset. Tiga corpus belum mendukung klaim
signifikansi. Efek konsisten berarti ketiga mean corpus bertanda sama; nol,
mixed, dan undefined tetap ditampilkan.

## 2. Tujuan seleksi validasi

{q2_text}

{choice_table}

J dan R dihitung dari **dua replikasi tuning Stage 2 yang digunakan ulang**.
J meminimalkan mean validation NLL random+uniform; R memakai random saja.
Tie rule: skor presisi penuh, epoch lebih awal, LR naik, WD naik, clip 1 sebelum
disabled. Hash semua input/keputusan, kandidat dan jadwal tersimpan dalam
selection.json. Tidak ada test, p* atau hasil konfirmasi dalam seleksi.

![Tujuan seleksi](selection-objective.png)

Efek kebijakan ini bersyarat pada dua replikasi tuning tersebut. Hasil tidak
membuktikan bahwa satu tujuan seleksi selalu lebih baik atau bahwa optimum
global ditemukan. Per-capacity paired effects untuk p*, train/validation/test
NLL, memorisasi dan clipping tersedia di per-capacity-effects.csv dan JSON.

## 3. Audit baseline pretraining

{baseline_text}

{baseline_table}

Komponen NLL pada tabel adalah rata-rata per answer token komponen masing-masing;
total mixed NLL adalah mean ketiganya. Angka Stage 2 memakai enam baseline
tuning yang dideduplikasi, sehingga cocok dengan konteks 3,23/4,19/5,45.
Pretraining shared-only tidak mengoptimalkan group dan instance mixed task.
Referensi uniform atas 16 jawaban memiliki NLL log(16)=2,772589 per komponen.

![Komponen baseline](baseline-components.png)

Berikut alokasi gain pada J/EJ, random, konfirmasi baru. Signed mass share
dapat negatif; gain komponen tidak dipotong. RMS mengukur bentuk kontribusi
kumulatif terhadap penyimpangan dari alokasi uniform. Cross-terms lengkap
disimpan dalam diagnostics.json karena kontribusi tidak independen.

{dg_table}

{sensitivity_table}

Referensi alternatif [0,log(16),log(16)] adalah oracle shared-rule dan prediksi
uniform untuk group/instance, **bukan checkpoint pretrained lain**. Nilai
undefined berarti estimator tidak teridentifikasi atau aggregate gain tidak
positif; nilai itu tidak dibuang atau diubah menjadi nol. Mean diagnostik hanya
ditampilkan bila semua sembilan nilai terdefinisi. p* primer tetap estimator
asli terhadap baseline pretrained dan memakai gain bertanda.

Identitas gain total = mean tiga gain komponen diperiksa; maksimum selisih
float32 adalah {diagnostics['identity_max_abs_error']:.9g}. Alokasi kumulatif
dan matriks cross-term juga direkonstruksi. Diagnostik mencakup seluruh 540
checkpoint adaptasi Stage 3 dan 450 checkpoint Stage 2 retrospektif. Baseline
dan perubahan referensi dapat memengaruhi interpretasi gain/p*, tetapi ini
bukan intervensi pretraining yang mengidentifikasi sebab kausal puncak.

## 4. Generalisasi, memorisasi, dan clipping

{perf_table}

Kriteria generalisasi diterapkan per corpus: test NLL harus menurun ketat
dengan kapasitas dan validation NLL tidak lebih buruk dari epoch 0 pada setiap
kapasitas. Hasil masing-masing corpus dan arm ada di policy-summary.json.
Tidak ada evaluasi test epoch 0 atau seleksi ulang dari konfirmasi.
Uniform p* selalu undefined. Semua undefined/boundary fits, termasuk komponen
dan referensi alternatif, disimpan di diagnostics.json dan diagnostics.csv.

![Trajectory epoch bersama](trajectories.png)

## 5. Integritas, runtime, reproduksi

Training-stage wall time {complete['elapsed_seconds']:.1f} detik
({complete['elapsed_seconds']/60:.1f} menit), termasuk pretraining, evaluasi dan
serialisasi di interval tersebut; tidak termasuk persiapan/audit/laporan.
Puncak alokasi adaptasi {max(r['peak_allocated_mib'] for r in results.values()):.2f} MiB;
reserved {max(r['peak_reserved_mib'] for r in results.values()):.2f} MiB.
Ini memori PyTorch, bukan seluruh desktop/driver. Batas dua jam dan 144 run
dipenuhi; jumlah aktual 108 didapat melalui deduplikasi sebelum training.

Audit memeriksa {audit_result['historical_files_unchanged']} file historis,
108 run, 27 pretrained checkpoints, 540 model checkpoint adaptasi dan tepat
540 evaluasi test setelah freeze. Source/tensor/order/weight/checkpoint hashes,
pairing across-arm dan across-config, split/toggle equality, pemilihan validasi
independen, seluruh scalar metric dan p* asli direkonstruksi. Tidak ada run gagal.

Raw: `work/runs/{root.name}/`. Arsip ringkas menyimpan protokol/source,
input tuning dan keputusan, data, assignment/order, per-sequence losses,
retrospective evidence, audit, laporan dan gambar. Model penuh dikecualikan
dari ZIP tetapi tersedia lokal dengan hash. environment-lock.txt mencatat
runtime aktual. Notebook tidak dijalankan; skrip ekuivalen menjalankan studi.

## 6. Posisi paper dan batas klaim

Kontribusi kandidat adalah kontrol atas kebijakan optimizer/durasi/seleksi dan
audit baseline pada tugas terstruktur. Efek terukur berlaku untuk konfigurasi
dan corpus dalam protokol ini. Tiga kapasitas hanya memberi satu titik interior;
tidak ada bukti perpindahan antara dua lokasi puncak interior. Tiga corpus dan
dua replikasi tuning yang digunakan ulang membatasi generalisasi inferensi.

[Jane Street](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/)
menggunakan tuning held-out dan regularisasi kuat pada LM pretrained; hasil
sintetis ini tidak setara dengan setting itu. Estimator signed-gain mengikuti
[technical note](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/sequence-weighting-note.pdf).
Hubungan pembobotan dengan durasi dan regularisasi sudah terkait
[Byrd & Lipton, ICML 2019](https://proceedings.mlr.press/v97/byrd19a.html) dan
[Xu, Ye & Ruan, 2021](https://arxiv.org/abs/2103.15209). Rincian recheck sumber
primer ada di LITERATURE_CHECK.md. Tidak ada klaim novelty/venue atau publikasi.
'''
    (out/'REPORT.md').write_text(text,encoding='utf-8')


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run-id',required=True); ap.add_argument('--wait',action='store_true')
    args=ap.parse_args(); root=ROOT/'work/runs'/args.run_id; out=HERE/f'results-{args.run_id}'
    assert not out.exists(), 'Preserve previous report'
    if args.wait:
        print('Waiting for training completion; CPU analysis only.',flush=True)
        while not (root/'COMPLETE.json').exists():
            if list((root/'runs').glob('*/failure.json')): raise RuntimeError('Training failed; preserve records')
            time.sleep(30)
    print('Auditing complete Stage 3 and historical hashes.',flush=True)
    evidence,sel,results,records=audit(root)
    out.mkdir()
    write(out/'AUDIT.json',evidence)
    rows=flat_rows(results); csvwrite(out/'all-checkpoints.csv',rows)
    summary,cell_rows,effect_rows=policy_analysis(sel,rows)
    write(out/'policy-summary.json',summary); csvwrite(out/'policy-cells.csv',cell_rows); csvwrite(out/'per-capacity-effects.csv',effect_rows)
    print('Primary audit passed; computing frozen baseline diagnostics.',flush=True)
    diag,diag_rows=diagnostic_analysis(root,sel,results,records)
    write(out/'diagnostics.json',diag); csvwrite(out/'diagnostics.csv',diag_rows); csvwrite(out/'baseline-components.csv',diag['baseline_rows'])
    write(out/'DIAGNOSTIC_AUDIT.json',dict(status='PASS',gain_identity_max_abs_error=diag['identity_max_abs_error'],
        fresh_checkpoints=sel['planned_runs']*5,retrospective_checkpoints=450,primary_definition_unchanged=True))
    figures(out,summary,diag['baseline_rows']); report(root,out,sel,summary,diag,evidence,results)
    shutil.copy2(HERE/'LITERATURE_CHECK.md',out/'LITERATURE_CHECK.md')
    shutil.copy2(Path(__file__),out/'analyze_stage3.py')
    write(out/'analysis-provenance.json',dict(utc=utc(),source_sha256=sha(Path(__file__)),
          frozen_diagnostics_sha256=sha(HERE/'diagnostics.py'),protocol_sha256=sha(HERE/'PROTOCOL_STAGE3.md')))
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
    print(json.dumps(dict(output=str(out),audit='PASS',diagnostics='PASS',
        cells={k:summary['cells'][k]['arms']['random']['verdict'] for k in ['F_C30','F_EJ','J_C30','J_EJ','R_ER']})),flush=True)


if __name__=='__main__': main()
