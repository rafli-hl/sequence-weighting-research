"""Independent schedule/integrity audit and descriptive Stage 2 reporting."""
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

sys.dont_write_bytecode = True
from stage2 import (HERE, ROOT, CAPS, GRID, TUNE, CONFIRM, EPOCHS, data, weights,
                    orders, tensor_hash, sha, read, write, utc, exponent)
import torch


def mean(xs):
    return st.mean(xs)


def sd(xs):
    return st.stdev(xs) if len(xs) > 1 else 0.


def fmt(value):
    return 'undefined' if value is None else f'{value:.6f}'


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str, row))+' |' for row in rows])


def csvwrite(path, rows):
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def audit(root):
    assert (root/'COMPLETE.json').exists(), 'Experiment incomplete'
    failures = list(root.rglob('failure.json'))
    assert not failures, f'Failures require explicit incomplete-study analysis: {failures}'
    manifest = read(root/'source_manifest.json')
    assert all(sha(HERE/n) == h == sha(root/'source'/n) for n, h in manifest.items())
    historical = [x for x in read(ROOT/'migration/source-files.json') if
                  x['path'].startswith(('outputs/sequence-weighting-pilot/','work/runs/'))]
    assert historical
    for item in historical:
        assert sha(ROOT/item['path']) == item['sha256'], f'Historical record changed: {item["path"]}'
    selection = read(root/'selection.json')
    # Reconstruct from raw validation records without calling the runner's selector.
    for width,_ in CAPS:
        reconstructed = []
        initial_values = []
        for index,setting in enumerate(GRID):
            histories = []
            for d,s,_ in TUNE:
                for arm in ['random','uniform']:
                    folder = root/'runs'/f'tune-w{width}-d{d}-s{s}-g{index:02d}-{arm}'
                    histories.append({h['epoch']:h['validation']['loss'] for h in read(folder/'history.json')})
            if index==0:
                initial_values = [h[0] for h in histories]
            for epoch in EPOCHS:
                scores = [h[epoch] for h in histories]
                reconstructed.append(dict(grid_index=index,**setting,epoch=epoch,
                                          validation_nll=sum(scores)/4,individual_validation_nll=scores))
        decision = selection['decisions'][str(width)]
        assert decision['candidates'] == reconstructed
        ordered = sorted(reconstructed,key=lambda x:(x['validation_nll'],x['epoch'],x['lr'],x['wd'],
                                                     1 if x['clip'] is None else 0))
        assert decision['selected'] == ordered[0]
        assert decision['epoch0_validation_nll'] == sum(initial_values)/4
        assert decision['adapted_worse_than_epoch0'] == (ordered[0]['validation_nll']>sum(initial_values)/4)
    expected = {'benchmark-w256-d42424-s99-g00-random'}
    for width, _ in CAPS:
        for i in range(18):
            expected.update(f'tune-w{width}-d{d}-s{s}-g{i:02d}-{a}' for d,s,_ in TUNE for a in ['random','uniform'])
        i = selection['decisions'][str(width)]['selected']['grid_index']
        expected.update(f'confirm-w{width}-d{d}-s{s}-g{i:02d}-{a}' for d,s,_ in CONFIRM for a in ['random','uniform'])
    actual = {p.parent.name for p in (root/'runs').glob('*/result.json')}
    assert actual == expected, (actual-expected, expected-actual)
    events = [json.loads(s) for s in (root/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    freeze = [x for x in events if x['kind'] == 'selection_frozen']
    assert len(freeze) == 1 and freeze[0]['sha256'] == sha(root/'selection.json')
    test_events = [x for x in events if x['kind'] == 'test_evaluation']
    assert len(test_events) == 90
    assert all(x['utc'] > freeze[0]['utc'] for x in test_events)
    assert len({x['name'] for x in test_events}) == 90
    assert all(x['utc'] > freeze[0]['utc'] for x in events
               if x['kind'] == 'run_start' and x['phase'] == 'confirm')
    corpora, baseline_results, result_map, record_map = {}, {}, {}, {}
    for folder in sorted((root/'corpora').iterdir()):
        pre = folder.name.startswith('pre-')
        dseed = int(folder.name.split('-')[1])
        saved = torch.load(folder/'dataset.pt', weights_only=True)
        fresh, meta = data(dseed, pretrain=pre)
        dm = read(folder/'metadata.json')
        assert sha(folder/'dataset.pt') == dm['file_sha256']
        assert dm['sequence_keys_by_split'] == meta['sequence_keys_by_split']
        hidden, _ = data(dseed, pretrain=pre, include_test=False)
        for name, pair in saved.items():
            assert all(torch.equal(a,b) for a,b in zip(pair, fresh[name]))
            assert tensor_hash(*pair) == dm['tensor_sha256'][name]
            if name != 'test':
                assert all(torch.equal(a,b) for a,b in zip(pair, hidden[name]))
        keys = sum(dm['sequence_keys_by_split'].values(), [])
        assert len(keys) == len(set(keys))
        corpora[folder.name] = dm
    assert len(list((root/'baselines').iterdir())) == 52
    for folder in (root/'baselines').iterdir():
        r = read(folder/'result.json')
        assert r['source_sha256'] == manifest
        assert sha(folder/'pretrained.pt') == r['checkpoint_sha256']
        assert sha(folder/'cold.pt') == r['cold_sha256']
        order = torch.load(folder/'orders.pt', weights_only=True)
        assert torch.equal(order, orders(r['seed'], 2048, 4))
        assert tensor_hash(order) == r['batch_order_sha256']
        baseline_results[folder.name] = r
    for name in sorted(actual):
        folder = root/'runs'/name
        r = read(folder/'result.json')
        c = r['config']
        assert c == read(folder/'config.json') and c['source_sha256'] == manifest
        assert name == f'{c["phase"]}-w{c["width"]}-d{c["data_seed"]}-s{c["seed"]}-g{c["grid_index"]:02d}-{c["arm"]}'
        if c['phase'] != 'benchmark':
            assert all(c[k] == GRID[c['grid_index']][k] for k in ['lr','wd','clip'])
            assert (c['data_seed'],c['seed'],c['pretrain_seed']) in (TUNE if c['phase']=='tune' else CONFIRM)
        assignment = torch.load(folder/'assignment.pt', weights_only=True)
        rec = torch.load(folder/'sequence_losses.pt', weights_only=True)
        assert torch.equal(assignment['weights'], weights(c['seed'], c['arm']))
        assert torch.equal(assignment['orders'], orders(c['seed']))
        assert tensor_hash(assignment['weights']) == c['weight_sha256']
        assert tensor_hash(assignment['orders']) == c['batch_order_sha256']
        assert torch.equal(rec['weights'], assignment['weights'])
        dm = corpora[f'adapt-{c["data_seed"]}']
        pm = corpora[f'pre-{c["pretrain_seed"]}']
        assert c['data_sha256'] == dm['tensor_sha256']
        assert set(sum(dm['sequence_keys_by_split'].values(), [])).isdisjoint(
                   sum(pm['sequence_keys_by_split'].values(), []))
        pre = baseline_results[f'w{c["width"]}-s{c["seed"]}-d{c["pretrain_seed"]}']
        assert c['baseline_sha256'] == pre['checkpoint_sha256']
        assert [x['epoch'] for x in r['history']] == [0]+EPOCHS
        assert [x['epoch'] for x in rec['checkpoints']] == [0]+EPOCHS
        assert [x['epoch'] for x in r['epoch_stats']] == list(range(1,61))
        initial = rec['checkpoints'][0]['train']['loss']
        for h, cp in zip(r['history'], rec['checkpoints']):
            for split in ['train', 'validation']:
                assert abs(float(cp[split]['loss'].mean())-h[split]['loss']) < 1e-7
                assert torch.isfinite(cp[split]['loss']).all()
            gain = initial-cp['train']['loss']
            assert abs(float(gain.double().sum())-h['total_gain']) < 1e-6
            if h['epoch']:
                # Recompute all fits from retained signed sequence gains.
                fit = exponent(rec['weights'].tolist(), gain.tolist())
                assert fit['p'] == h['p_star']['p']
                if fit['p'] is not None:
                    assert abs(fit['objective']-h['p_star']['objective']) < 1e-12
                assert abs(float((gain<0).float().mean())-h['negative_gain_fraction']) < 1e-7
                observed_clip = sum(x['gradient_clip_fraction'] for x in r['epoch_stats'][:h['epoch']])/h['epoch']
                assert observed_clip == h['gradient_clip_fraction_cumulative']
        assert sha(folder/'final.pt') == r['model_sha256']['final']
        if c['phase'] == 'confirm':
            chosen = selection['decisions'][str(c['width'])]['selected']
            assert all(c[k] == chosen[k] for k in ['lr','wd','clip','grid_index'])
            assert c['selected_epoch'] == r['test_epoch'] == chosen['epoch']
            assert c['selection_sha256'] == sha(root/'selection.json')
            te = next(x for x in test_events if x['name'] == name)
            assert te['epoch'] == chosen['epoch'] and te['selection_sha256'] == c['selection_sha256']
            assert abs(float(rec['test']['loss'].mean())-r['final_test']['loss']) < 1e-7
            assert sha(folder/'selected.pt') == r['model_sha256']['selected']
        else:
            assert r['final_test'] is None and rec['test'] is None
            assert c['selection_sha256'] is None
        result_map[name], record_map[name] = r, rec
    pairs = 0
    for name, r in result_map.items():
        c = r['config']
        if c['arm'] != 'random' or c['phase'] == 'benchmark':
            continue
        un = name.removesuffix('random')+'uniform'
        u = result_map[un]
        assert c['baseline_sha256'] == u['config']['baseline_sha256']
        assert c['data_sha256'] == u['config']['data_sha256']
        assert c['batch_order_sha256'] == u['config']['batch_order_sha256']
        for split in ['train','validation']:
            assert r['history'][0][split] == u['history'][0][split]
            for key in ['loss','component_loss','component_accuracy']:
                assert torch.equal(record_map[name]['checkpoints'][0][split][key],
                                   record_map[un]['checkpoints'][0][split][key])
        pairs += 1
    assert pairs == 153
    # Across capacities, same corpus, weights and all actual epoch orders.
    groups = {}
    for r in result_map.values():
        c = r['config']
        if c['phase'] == 'benchmark':
            continue
        key = (c['phase'], c['data_seed'], c['seed'], c['arm'])
        values = (c['data_sha256'], c['weight_sha256'], c['batch_order_sha256'])
        if key in groups:
            assert values == groups[key]
        groups[key] = values
    evidence = dict(status='PASS', utc=utc(), expected_adaptation_runs=307, tuning=216, confirmation=90,
                    benchmark_excluded=1, pretraining_checkpoints=52, paired_arm_checks=pairs,
                    test_evaluations=len(test_events), failed_runs=[], source_manifest=manifest,
                    historical_files_rechecked=len(historical),
                    selection_sha256=sha(root/'selection.json'), checks=[
                    'complete exact schedule, no failed runs', 'all saved source/checkpoint hashes',
                    'historical Stage 0/1 records match migration SHA256 manifest',
                    'full corpus token/label regeneration and test-toggle invariance',
                    'split and pretraining keys disjoint', 'all actual weight/order tensors regenerate',
                    'paired full initial losses/components/accuracy identical',
                    'data/weights/orders identical across capacities',
                    'selection independently reconstructed from validation',
                    'selection freeze precedes every confirmation and test call',
                    'test exactly once at selected checkpoint, absent in tuning',
                    'all saved metrics/fit estimates agree with retained signed sequence losses'])
    return evidence, list(result_map.values()), record_map


def summarize(results):
    rows, primary = [], []
    for r in results:
        c = r['config']
        for h in r['history']:
            row = {k:c[k] for k in ['name','phase','width','layers','parameters','data_seed','seed','arm','lr','wd','clip']}
            row.update(epoch=h['epoch'], p=h['p_star']['p'], objective=h['p_star'].get('objective'),
                       total_gain=h['total_gain'], negative_gain_fraction=h['negative_gain_fraction'],
                       lower_boundary=h['p_star'].get('at_lower_bound', False),
                       upper_boundary=h['p_star'].get('at_upper_bound', False),
                       train_nll=h['train']['loss'], validation_nll=h['validation']['loss'],
                       epoch0_validation_nll=r['history'][0]['validation']['loss'],
                       test_nll=r['final_test']['loss'] if c['phase']=='confirm' and h['epoch']==c['selected_epoch'] else None,
                       shared_accuracy=h['train']['shared']['accuracy'],
                       group_accuracy=h['train']['group']['accuracy'],
                       instance_accuracy=h['train']['instance']['accuracy'],
                       clipping=h.get('gradient_clip_fraction_cumulative'),
                       p_reason=h['p_star'].get('reason'))
            for component in ['shared','group','instance']:
                row[f'train_{component}_nll'] = h['train'][component]['loss']
                row[f'validation_{component}_nll'] = h['validation'][component]['loss']
                row[f'validation_{component}_accuracy'] = h['validation'][component]['accuracy']
                evaluated = c['phase']=='confirm' and h['epoch']==c['selected_epoch']
                row[f'test_{component}_nll'] = r['final_test'][component]['loss'] if evaluated else None
                row[f'test_{component}_accuracy'] = r['final_test'][component]['accuracy'] if evaluated else None
            rows.append(row)
            if c['phase']=='confirm' and h['epoch']==c['selected_epoch']:
                primary.append(row)
    contrasts = []
    for d, s, _ in CONFIRM:
        rr = sorted([x for x in primary if x['data_seed']==d and x['seed']==s and x['arm']=='random'], key=lambda x:x['width'])
        pp = [x['p'] for x in rr]
        delta = pp[1]-max(pp[0],pp[2]) if all(x is not None for x in pp) else None
        contrasts.append(dict(data_seed=d, seed=s, p_small=pp[0], p_middle=pp[1], p_large=pp[2], contrast=delta))
    corpus_stats, generalization = [], []
    for d in sorted({x['data_seed'] for x in primary}):
        values = [x['contrast'] for x in contrasts if x['data_seed']==d]
        defined = all(x is not None for x in values)
        corpus_stats.append(dict(data_seed=d, mean=mean(values) if defined else None,
                                 within_corpus_sd=sd(values) if defined else None,
                                 positive=sum(x is not None and x>0 for x in values), n=5))
        for arm in ['random','uniform']:
            rr = [[x for x in primary if x['data_seed']==d and x['arm']==arm and x['width']==w] for w,_ in CAPS]
            test = [mean([x['test_nll'] for x in a]) for a in rr]
            val = [mean([x['validation_nll'] for x in a]) for a in rr]
            val0 = [mean([x['epoch0_validation_nll'] for x in a]) for a in rr]
            generalization.append(dict(data_seed=d, arm=arm, test_nll=test, validation_nll=val,
                                        epoch0_validation_nll=val0,
                                        test_improves_with_capacity=test[0]>test[1]>test[2],
                                        adapted_no_worse_than_epoch0=all(a<=b for a,b in zip(val,val0))))
    defined = all(x['contrast'] is not None for x in contrasts)
    if defined and all(x['contrast']>0 for x in contrasts) and all(x['mean']>0 for x in corpus_stats):
        verdict = 'survives'
    elif defined and all(x['mean']<=0 for x in corpus_stats):
        verdict = 'disappears'
    else:
        verdict = 'inconclusive/mixed'
    agg = []
    for arm in ['random','uniform']:
        for width,_ in CAPS:
            a = [x for x in primary if x['arm']==arm and x['width']==width]
            ps = [x['p'] for x in a]
            agg.append(dict(arm=arm, width=width, parameters=a[0]['parameters'], epoch=a[0]['epoch'],
                            p_mean=mean(ps) if all(x is not None for x in ps) else None,
                            **{k:mean([x[k] for x in a]) for k in ['train_nll','validation_nll','test_nll',
                              'epoch0_validation_nll','instance_accuracy','clipping','total_gain','negative_gain_fraction']}))
    means = [x['mean'] for x in corpus_stats]
    reasons = {}
    for row in rows:
        if row['p'] is None:
            reasons[row['p_reason']] = reasons.get(row['p_reason'], 0)+1
    fixed = []
    for epoch in EPOCHS:
        values = []
        for d,s,_ in CONFIRM:
            a = sorted([x for x in rows if x['phase']=='confirm' and x['arm']=='random'
                        and x['data_seed']==d and x['seed']==s and x['epoch']==epoch],key=lambda x:x['width'])
            ps = [x['p'] for x in a]
            values.append(dict(data_seed=d,seed=s,contrast=ps[1]-max(ps[0],ps[2]) if all(p is not None for p in ps) else None))
        cm = []
        for d in sorted({x['data_seed'] for x in values}):
            vv = [x['contrast'] for x in values if x['data_seed']==d]
            cm.append(dict(data_seed=d,mean=mean(vv) if all(v is not None for v in vv) else None))
        fixed.append(dict(epoch=epoch, positive=sum(x['contrast'] is not None and x['contrast']>0 for x in values),
                          undefined=sum(x['contrast'] is None for x in values),corpus_means=cm,contrasts=values))
    summary = dict(verdict=verdict, all_contrasts_defined=defined,
                   positive_contrasts=sum(x['contrast'] is not None and x['contrast']>0 for x in contrasts),
                   contrasts=contrasts, corpus_stats=corpus_stats, generalization=generalization,
                   generalization_criterion_met=all(x['test_improves_with_capacity'] and x['adapted_no_worse_than_epoch0']
                                                   for x in generalization if x['arm']=='random'),
                   across_corpus_mean=mean(means) if defined else None,
                   across_corpus_sd=sd(means) if defined else None,
                   across_corpus_range=[min(means),max(means)] if defined else None,
                   aggregates=agg, primary_random_undefined=sum(x['p'] is None for x in primary if x['arm']=='random'),
                   primary_random_lower_boundary=sum(x['lower_boundary'] for x in primary if x['arm']=='random'),
                   primary_random_upper_boundary=sum(x['upper_boundary'] for x in primary if x['arm']=='random'),
                   all_checkpoint_undefined_by_reason=reasons,secondary_fixed_epoch_contrasts=fixed)
    return summary, rows, primary


def plots(out, summary, rows, primary, records):
    os.environ['MPLCONFIGDIR'] = str(ROOT/'work/.matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False})
    colors = ['#176b87','#b25d34','#537b43']
    ds = sorted({x['data_seed'] for x in primary})
    fig, axes = plt.subplots(1,3,figsize=(13,4.2))
    for d,col in zip(ds,colors):
        a = [[x for x in primary if x['data_seed']==d and x['arm']=='random' and x['width']==w] for w,_ in CAPS]
        for ax,key,title in zip(axes,['p','validation_nll','test_nll'],['Selected sequence-weight exponent','Selected validation loss','Selected test loss']):
            yy = [mean([x[key] for x in group]) if all(x[key] is not None for x in group) else math.nan for group in a]
            ax.plot([0,1,2],yy,'o-',color=col,label=f'Corpus {d}')
            ax.set(title=title,xticks=[0,1,2],xticklabels=['0.113','0.622','3.213'],xlabel='Parameters (millions)',
                   ylabel='p* (unitless)' if key=='p' else 'NLL (nats / answer token)')
    axes[0].legend(frameon=False,fontsize=8)
    fig.suptitle('Random weights: frozen selected policy; mean of 5 model/weight seeds per corpus',fontsize=12)
    fig.tight_layout()
    fig.savefig(out/'selected-policy.png',dpi=180)
    plt.close(fig)
    fig,ax = plt.subplots(figsize=(8,4.5))
    for j,(d,col) in enumerate(zip(ds,colors)):
        cc = [x for x in summary['contrasts'] if x['data_seed']==d]
        ax.scatter([j+(k-2)*.06 for k in range(5)], [x['contrast'] if x['contrast'] is not None else math.nan for x in cc], color=col)
        cs = next(x for x in summary['corpus_stats'] if x['data_seed']==d)
        if cs['mean'] is not None:
            ax.plot([j-.2,j+.2],[cs['mean']]*2,color='black',lw=2)
    ax.axhline(0,color='gray',ls='--',lw=1)
    ax.set(xticks=range(3),xticklabels=ds,xlabel='Confirmation corpus seed (dataset replication)',
           ylabel='p* middle − max(p* endpoints)',title='Paired contrasts at selected epochs\nPoints: model/weight seeds; bars: corpus means')
    fig.tight_layout(); fig.savefig(out/'paired-contrasts.png',dpi=180); plt.close(fig)
    fig,axes = plt.subplots(1,3,figsize=(13,4.2))
    for ax,d in zip(axes,ds):
        for e,col in zip([1,3,10,30,60],['#888888','#176b87','#9a7b26','#537b43','#b25d34']):
            rr = [[x for x in rows if x['phase']=='confirm' and x['data_seed']==d and x['arm']=='random' and x['width']==w and x['epoch']==e] for w,_ in CAPS]
            yy = [mean([x['p'] for x in a]) if all(x['p'] is not None for x in a) else math.nan for a in rr]
            ax.plot(range(3),yy,'o-',color=col,label=f'Epoch {e}')
        ax.set(title=f'Corpus {d}',xticks=range(3),xticklabels=['0.113','0.622','3.213'],
               xlabel='Parameters (millions)',ylabel='Mean p* (unitless)')
    axes[-1].legend(frameon=False,fontsize=8)
    fig.suptitle('Secondary matched-epoch trajectories under each capacity’s selected optimizer',fontsize=12)
    fig.tight_layout(); fig.savefig(out/'trajectories.png',dpi=180); plt.close(fig)
    fig,axes = plt.subplots(1,3,figsize=(13,4.2))
    for ax,(width,_) in zip(axes,CAPS):
        r = next(x for x in primary if x['data_seed']==57721 and x['seed']==201 and x['arm']=='random' and x['width']==width)
        rec = records[r['name']]
        cp = next(x for x in rec['checkpoints'] if x['epoch']==r['epoch'])
        gain = (rec['checkpoints'][0]['train']['loss']-cp['train']['loss']).double().numpy()
        w = rec['weights'].double().numpy(); ix = np.argsort(w)
        if gain.sum()>1e-10 and r['p'] is not None:
            fit = w**r['p']; xx = np.arange(1,513)/512
            ax.plot(xx,np.cumsum(gain[ix]/gain.sum()),label='Signed observed gains')
            ax.plot(xx,np.cumsum(fit[ix]/fit.sum()),ls='--',label='Fitted powered weights')
        ax.set(title=f'Width {width} · epoch {r["epoch"]}',xlabel='Sequence weight percentile (fraction)',ylabel='Cumulative normalized gain')
    axes[0].legend(frameon=False,fontsize=8)
    fig.suptitle('Fit diagnostic: fixed corpus 57721, model/weight seed 201',fontsize=12)
    fig.tight_layout(); fig.savefig(out/'gain-fit.png',dpi=180); plt.close(fig)


def report(root, out, summary, results):
    selection = read(root/'selection.json')
    verdict = {'survives':'bertahan', 'disappears':'menghilang', 'inconclusive/mixed':'belum konklusif / campuran'}[summary['verdict']]
    ss = [selection['decisions'][str(w)] for w,_ in CAPS]
    selection_table = table(['Width/layers','LR','WD','Clip','Epoch','Tuning val NLL','Epoch 0 val NLL'],
        [[f'{w}/{l}',r['selected']['lr'],r['selected']['wd'],r['selected']['clip'],r['selected']['epoch'],
          f'{r["selected"]["validation_nll"]:.6f}',f'{r["epoch0_validation_nll"]:.6f}'] for (w,l),r in zip(CAPS,ss)])
    aggregate_table = table(['Arm','Parameters','Epoch','p* mean','Train NLL','Val NLL','Test NLL','Instance train accuracy','Clipping'],
        [[a['arm'],a['parameters'],a['epoch'],'undefined' if a['p_mean'] is None else f'{a["p_mean"]:.6f}',
          f'{a["train_nll"]:.5f}',f'{a["validation_nll"]:.5f}',f'{a["test_nll"]:.5f}',
          f'{100*a["instance_accuracy"]:.2f}%',f'{100*a["clipping"]:.1f}%'] for a in summary['aggregates']])
    contrast_table = table(['Corpus','Model/weight seed','p* small','p* middle','p* large','Middle minus max endpoint'],
        [[x['data_seed'],x['seed']]+['undefined' if x[k] is None else f'{x[k]:.6f}' for k in ['p_small','p_middle','p_large','contrast']]
         for x in summary['contrasts']])
    corpus_table = table(['Corpus','Mean contrast','Within-corpus SD','Positive / 5'],
        [[x['data_seed'],fmt(x['mean']),fmt(x['within_corpus_sd']),x['positive']] for x in summary['corpus_stats']])
    gen_table = table(['Corpus','Arm','Test decreases with capacity','Selected val no worse than epoch 0'],
        [[x['data_seed'],x['arm'],x['test_improves_with_capacity'],x['adapted_no_worse_than_epoch0']] for x in summary['generalization']])
    times = [r['elapsed_seconds'] for r in results]
    events = [json.loads(x) for x in (root/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    from datetime import datetime
    start = next(x['utc'] for x in events if x['kind']=='grid_started')
    finish = next(x['utc'] for x in events if x['kind']=='experiment_complete')
    elapsed = (datetime.fromisoformat(finish)-datetime.fromisoformat(start)).total_seconds()
    primary_rs = [r for r in results if r['config']['phase']=='confirm' and r['config']['arm']=='random']
    hh = [next(h for h in r['history'] if h['epoch']==r['config']['selected_epoch']) for r in primary_rs]
    objective = [h['p_star']['objective'] for h in hh if h['p_star']['p'] is not None]
    fixed_table = table(['Epoch','Kontras positif / 15','Undefined','Mean kontras per corpus'],
        [[x['epoch'],x['positive'],x['undefined'],', '.join(f'{c["data_seed"]}: {fmt(c["mean"])}' for c in x['corpus_means'])]
         for x in summary['secondary_fixed_epoch_contrasts']])
    if summary['verdict']=='disappears':
        recommendation = ('Hasil mendukung pembingkaian paper sebagai batas ketahanan puncak terhadap seleksi '
                          'validasi dalam tugas sintetis ini. Jangan menjadikannya klaim replikasi kurva Jane Street. '
                          'Prioritas tindak lanjut adalah kontrol optimizer/durasi pada corpus identik untuk '
                          'memisahkan kontribusi early stopping dan perubahan regularisasi. Perluasan teks '
                          'besar dan kompensasi inverse-exponent belum dibenarkan oleh hasil ini.')
    elif summary['verdict']=='survives' and summary['generalization_criterion_met']:
        recommendation = ('Kelangsungan puncak beserta kriteria generalisasi memberi dasar untuk mempertimbangkan '
                          'kapasitas interior keempat dan replikasi corpus tambahan dalam protokol baru. '
                          'Perluasan teks kecil lintas kapasitas dapat dirancang sesudah itu; hasil sekarang '
                          'belum membuktikan mekanisme pada LM besar atau novelty paper.')
    else:
        recommendation = ('Paper sebaiknya menekankan keterbatasan generalisasi dan variasi lintas corpus, '
                          'dengan hasil primer dan trajectory sekunder dipisahkan. Prioritas berikut adalah '
                          'kontrol optimizer/durasi pada corpus identik serta replikasi corpus tambahan '
                          'dengan aturan keputusan yang dibekukan. Jangan memperluas grid demi mencari '
                          'puncak yang diinginkan atau langsung meningkatkan biaya eksperimen teks.')
    content = f'''# Stage 2: capacity-specific validation tuning

Hasil: **puncak p* {verdict} pada kebijakan konfigurasi dan durasi pilihan
validasi**, menurut aturan deskriptif yang dibekukan.
Kontras positif: **{summary['positive_contrasts']}/15** pasangan corpus/seed.
Kriteria generalisasi primer **{'terpenuhi' if summary['generalization_criterion_met'] else 'tidak terpenuhi'}**.
Ini hasil tugas sintetis dengan grid terbatas, bukan replikasi eksak LM besar.

**Batas interpretasi utama:** hasil primer membandingkan kapasitas pada epoch
berbeda (lihat tabel seleksi). Diagnostik dengan epoch yang sama tetap dapat
memiliki puncak; tabel trajectory di bawah menunjukkan hasil lengkapnya.
Karena itu hasil ini tidak berarti tuning regularisasi saja menghilangkan
puncak, dan tidak membuktikan efek kausal durasi secara terpisah dari optimizer.

## Desain dan eksekusi

216 run tuning, 90 run konfirmasi, satu benchmark engineering terpisah,
52 checkpoint pretraining. Semua selesai; tidak ada run gagal. Training lokal
RTX 3050 Laptop melalui Ubuntu WSL 2, float32. Kode/protokol dibekukan sebelum
benchmark dan selection.json dibekukan sebelum konfirmasi. Test hanya sekali
per run konfirmasi, pada epoch terpilih. Notebook tidak dieksekusi; skrip yang
menjalankan eksperimen.

Dua replikasi tuning masing-masing memakai satu corpus dan satu seed model;
keduanya tidak disilangkan. Konfirmasi memakai tiga corpus independen dengan
lima seed model/bobot per corpus. Seed model/bobot bukan 15 replikasi dataset.
Semua arm memiliki token/label, checkpoint awal, dan urutan batch berpasangan;
bobot acak identik lintas kapasitas. Data lengkap dihasilkan sebelum toggle tes.

## Pemilihan hanya berdasarkan validasi

{selection_table}

Rata-rata dua arm × dua replikasi tuning menjadi skor seleksi. Tie rule:
skor presisi penuh, epoch lebih awal, LR naik, WD naik, clip 1 sebelum disabled.
Epoch 0 adalah pembanding wajib; kandidat adaptasi adalah epoch 1/3/10/30/60.
Kapasitas dengan pilihan adaptasi lebih buruk dari epoch 0:
{[w for (w,_),r in zip(CAPS,ss) if r['adapted_worse_than_epoch0']]}.
Tidak ada p*, test loss atau bentuk kurva dalam kriteria seleksi.

## Hasil pada kebijakan terpilih

{aggregate_table}

Angka tabel adalah mean 15 run per arm/kapasitas, dengan jumlah seed sama di
setiap corpus. Ini perbandingan kebijakan: durasi bisa berbeda antar kapasitas.
Uniform p* tidak teridentifikasi. CSV menyimpan seluruh komponen, gain, fit,
clipping dan checkpoint agar angka rata-rata tidak menutupi hasil individual.

![Kebijakan terpilih](selected-policy.png)

{contrast_table}

{corpus_table}

Mean kontras antar corpus: {fmt(summary['across_corpus_mean'])}; SD antar corpus:
{fmt(summary['across_corpus_sd'])}; rentang: {', '.join(fmt(x) for x in summary['across_corpus_range']) if summary['across_corpus_range'] else 'undefined'}.
SD dalam corpus di atas mengukur variasi model/bobot pada data yang sama.
Tiga corpus terlalu sedikit untuk klaim signifikansi; tidak ada bootstrap
sequence yang diperlakukan sebagai replikasi dataset.

![Kontras berpasangan](paired-contrasts.png)

## Generalisasi, memorisasi dan kualitas fit

{gen_table}

Aturan primer mewajibkan test NLL random menurun ketat pada ketiga kapasitas
di setiap corpus serta mean validation NLL terpilih tidak lebih buruk dari
epoch 0 pada setiap kapasitas/corpus. Nilai lengkapnya ada di summary.json.
Baseline test tidak dijadwalkan, sehingga tidak ada klaim perbaikan test
terhadap epoch 0. Kontrol uniform dilaporkan terpisah.

p* random primer undefined: {summary['primary_random_undefined']}/45;
boundary bawah (p<=.001): {summary['primary_random_lower_boundary']}/45;
boundary atas (p>=7.999): {summary['primary_random_upper_boundary']}/45.
Rentang objective fit: {min(objective) if objective else None} sampai {max(objective) if objective else None}.
Rentang total gain bertanda: {min(h['total_gain'] for h in hh)} sampai {max(h['total_gain'] for h in hh)}.
Rentang fraksi gain negatif: {min(h['negative_gain_fraction'] for h in hh)} sampai {max(h['negative_gain_fraction'] for h in hh)}.
Jumlah seluruh checkpoint dengan p* undefined menurut alasan:
{json.dumps(summary['all_checkpoint_undefined_by_reason'])}. Termasuk epoch 0,
kontrol uniform, tuning, konfirmasi dan benchmark engineering; benchmark tidak
masuk inferensi primer. Tidak ada undefined yang disubstitusi menjadi nol.
Gain negatif dipertahankan. Objective kecil tidak otomatis membuktikan model
mekanisme benar. Pilihan clipping dalam grid bukan intervensi kausal tersendiri.

![Fit pada corpus/seed tetap](gain-fit.png)

## Diagnostik sekunder

![Trajectory dengan epoch yang sama](trajectories.png)

{fixed_table}

Trajektori memakai optimizer terpilih setiap kapasitas, dengan epoch sama.
Model boleh dilatih setelah epoch pengujian hanya untuk diagnostik yang sudah
dijadwalkan; tidak ada pemilihan ulang atau test tambahan. Historical v0.2
adalah pembanding lintas studi, bukan kontrol dengan tensor identik. Belum ada
kontrol baru yang menyamakan semua optimizer v0.2 pada corpus Stage 2.

## Runtime, audit dan reproduksi

Wall time grid sampai konfirmasi selesai: {elapsed:.1f} detik ({elapsed/60:.1f} menit),
termasuk pretraining yang diperlukan, evaluasi dan serialisasi dalam interval
tersebut; tidak termasuk persiapan, benchmark dan audit. Jumlah waktu per-run
(termasuk benchmark, dan pretraining pada pemanggilan pertama): {sum(times):.1f} detik.
Puncak alokasi adaptasi: {max(r['peak_allocated_mib'] for r in results):.2f} MiB;
reserved: {max(r['peak_reserved_mib'] for r in results):.2f} MiB. Ini memori
PyTorch, bukan seluruh penggunaan desktop/driver.

AUDIT.json memverifikasi 307 run dan 52 checkpoint, pairing penuh, semua hash,
rekonstruksi seleksi, urutan freeze/test, seluruh p* dari gain bertanda dan
ketiadaan test saat tuning. raw-manifest.json mencatat hash seluruh file raw,
termasuk model penuh yang tidak dimasukkan ke arsip ringkas. run-records.zip
menyimpan kode, protokol, lingkungan, corpus, assignment/order, semua loss,
keputusan seleksi, laporan dan gambar. Model penuh tetap di:
`work/runs/{root.name}/`.

Reproduksi memerlukan environment-lock.txt dan CUDA WSL lokal. Gunakan source
Stage 2 dengan run-id baru: jalankan fase benchmark, lalu fase experiment bila
gate lolos, kemudian analyze_stage2.py. Jangan menimpa direktori ini.

## Posisi paper dan batas kesimpulan

{recommendation}

[Pemeriksaan sumber primer terbaru](../LITERATURE_CHECK.md) membatasi novelty:
hubungan bobot, regularisasi, durasi dan memorisasi sudah terkait literatur.
Jane Street memilih hyperparameter untuk validasi dan melaporkan peningkatan
held-out dengan skala; perbedaan kondisi itu harus tetap eksplisit.

Tiga kapasitas hanya memiliki satu titik interior. Pilihan dalam grid bukan
optimum global. Tidak ada dropout baru atau perubahan proporsi pola. Model dan
bobot menggunakan seed yang terkait. Tiga corpus mendukung deskripsi lintas
data yang lebih baik dari Stage 1, tetapi belum cukup untuk klaim universal.
Pretraining sintetis hanya mempelajari shared-rule; baseline validation NLL
pada mixed task berbeda antar kapasitas. Ini batas tambahan untuk menyamakan
mekanisme dengan fine-tuning LM pretrained pada teks umum.
Satu Pythia size/seed dari Stage 1 tetap tidak membentuk kurva scaling. Tidak
ada publikasi, upload, pengeluaran cloud, klaim venue atau janji publikasi.
'''
    (out/'REPORT.md').write_text(content, encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run-id', required=True)
    ap.add_argument('--wait-for-training', action='store_true')
    args = ap.parse_args()
    root = ROOT/'work/runs'/args.run_id
    initial_out = HERE/f'results-{args.run_id}'
    out = initial_out
    reuse = (initial_out/'ARCHIVE_CHECK.json').exists()
    if reuse:
        # A presentation revision preserves the complete original analysis.
        out = HERE/f'results-{args.run_id}-r2'
    assert not out.exists(), 'Analysis output already exists; preserve it'
    if args.wait_for_training:
        print('Waiting for COMPLETE.json; analysis uses CPU only.', flush=True)
        while not (root/'COMPLETE.json').exists():
            failures = list((root/'runs').glob('*/failure.json'))
            if failures:
                raise RuntimeError(f'Training failed; records retained: {failures}')
            time.sleep(30)
    if reuse:
        print('Reusing passed audit for presentation revision; no training or new selection.', flush=True)
        previous = read(initial_out/'ARCHIVE_CHECK.json')
        assert sha(initial_out/'run-records.zip') == previous['sha256']
        evidence = read(initial_out/'AUDIT.json')
        assert evidence['status']=='PASS'
        results = [read(p) for p in sorted((root/'runs').glob('*/result.json'))]
        records = {r['config']['name']:torch.load(root/'runs'/r['config']['name']/'sequence_losses.pt',weights_only=True)
                   for r in results}
    else:
        print('Starting complete scientific integrity audit.', flush=True)
        evidence, results, records = audit(root)
    out.mkdir(exist_ok=False)
    write(out/'AUDIT.json', evidence)
    summary, rows, primary = summarize(results)
    if reuse:
        assert summary == read(initial_out/'summary.json'), 'Presentation revision changed scientific summary'
        write(out/'PRESENTATION_REVISION.json', dict(utc=utc(), initial_analysis=str(initial_out.relative_to(ROOT)),
              initial_archive_sha256=previous['sha256'], scientific_summary_unchanged=True,
              changes=['wrap contrast plot title', 'shorten fit panel titles',
                       'round narrative/table summaries; full precision retained in JSON/CSV',
                       'clarify selected-duration versus fixed-epoch interpretation and shared-only pretraining limit']))
    write(out/'summary.json', summary)
    csvwrite(out/'all-checkpoints.csv', rows)
    csvwrite(out/'selected-checkpoints.csv', primary)
    csvwrite(out/'paired-contrasts.csv', summary['contrasts'])
    plots(out, summary, rows, primary, records)
    report(root, out, summary, results)
    write(out/'analysis-provenance.json', dict(utc=utc(), source_sha256=sha(Path(__file__)), run_id=args.run_id))
    (out/'analyze_stage2.py').write_bytes(Path(__file__).read_bytes())
    raw_manifest = read(initial_out/'raw-manifest.json') if reuse else {
                   str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
    write(out/'raw-manifest.json', raw_manifest)
    archive = out/'run-records.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(root.rglob('*')):
            if p.is_file() and p.name not in ['cold.pt','pretrained.pt','final.pt','selected.pt']:
                z.write(p,'raw/'+str(p.relative_to(root)))
        for p in sorted(out.iterdir()):
            if p.is_file() and p != archive:
                z.write(p,'report/'+p.name)
        z.write(HERE/'LITERATURE_CHECK.md','LITERATURE_CHECK.md')
        z.write(HERE/'README.md','README.md')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    write(out/'ARCHIVE_CHECK.json', dict(sha256=sha(archive), bytes=archive.stat().st_size, crc='PASS'))
    print(json.dumps(dict(output=str(out), audit=evidence['status'], verdict=summary['verdict'],
                          generalization=summary['generalization_criterion_met'],
                          positive_contrasts=summary['positive_contrasts'])), flush=True)


if __name__ == '__main__':
    main()
