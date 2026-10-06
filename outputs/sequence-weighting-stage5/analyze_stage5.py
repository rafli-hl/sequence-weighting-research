"""Stage 5 frozen descriptive analysis: utility, zero aliases, signed fits, audit."""
import argparse
import csv
import json
import math
import shutil
import statistics as st
import sys
import time
import traceback
import zipfile
from pathlib import Path
sys.dont_write_bytecode = True
import torch
from stage5 import ROOT, HERE, CAPS, EPOCHS, CONFIRM, VARIANTS, POLICIES, weights, read, write, sha, utc
from diagnostics import contrast
from diagnostics_roundoff import decompose


def desc(values):
    finite = [x for x in values if x is not None]
    assert all(math.isfinite(x) for x in finite)
    complete = bool(values) and len(finite) == len(values)
    return dict(n=len(values), undefined=len(values)-len(finite), positive=sum(x > 0 for x in finite),
        negative=sum(x < 0 for x in finite), zero=sum(x == 0 for x in finite),
        mean=st.mean(finite) if complete else None,
        sd=st.stdev(finite) if complete and len(finite) > 1 else 0. if complete else None,
        minimum=min(finite) if complete else None, maximum=max(finite) if complete else None)


def replicated(values):
    groups = [dict(data_seed=d, **desc([x['value'] for x in values if x['data_seed'] == d]))
              for d in sorted({x['data_seed'] for x in values})]
    return dict(values=values, all_pairs=desc([x['value'] for x in values]), corpora=groups,
                between_corpora=desc([x['mean'] for x in groups]))


def peak_verdict(stats):
    if stats['all_pairs']['undefined']: return 'inconclusive_undefined'
    if stats['all_pairs']['n'] == 9 and stats['all_pairs']['positive'] == 9: return 'survives'
    if all(x['mean'] <= 0 for x in stats['corpora']): return 'disappears'
    return 'mixed/inconclusive'


def signed_mass(gain):
    g = gain.double()
    absolute = float(g.abs().sum())
    return dict(total_gain=float(g.sum()), mean_gain=float(g.mean()),
        positive_mass=float(g[g > 0].sum()), negative_absolute_mass=float(-g[g < 0].sum()),
        absolute_mass=absolute, negative_gain_fraction=float((g < 0).double().mean()),
        cancellation_ratio=None if absolute == 0 else abs(float(g.sum()))/absolute)


def diagnostic_decompose(w, initial, current):
    result=decompose(w,initial,current)
    # The preserved helper may divide by a zero primary gain while the separately
    # rounded component gains have positive total. The primary normalization is
    # undefined under its existing guard; component allocation is still retained.
    if result['allocation']['defined'] and result['primary']['total_gain']<=1e-10:
        original=result['allocation']['primary_cumulative_roundoff_max']
        result['allocation']['primary_cumulative_roundoff_max']=None
        result['allocation']['primary_cumulative_comparison_reason']='primary_normalization_undefined_at_original_gain_guard'
        result['allocation']['original_comparison_finite']=math.isfinite(original)
    return result


def difference(a, b):
    return None if a is None or b is None else a-b


def fmt(value): return 'undefined' if value is None else f'{value:.6f}'


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(str(x) for x in row)+' |' for row in rows])


def csvwrite(path, rows):
    if not rows: return
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        writer.writeheader(); writer.writerows(rows)


def metric_fields(metrics):
    row = {}
    for split in ['train', 'validation', 'test']:
        value = metrics.get(split)
        row[f'{split}_nll'] = None if value is None else value['loss']
        for typ in ['shared', 'group', 'instance']:
            for metric in ['loss', 'accuracy']:
                row[f'{split}_{typ}_{metric}'] = None if value is None else value[typ][metric]
    return row


def initial_rows(initial_results):
    rows = []
    for name, r in sorted(initial_results.items()):
        row = {k:r[k] for k in ['variant', 'width', 'data_seed', 'seed', 'pretrain_seed', 'parameters']}
        row.update(name=name, phase='confirm', epoch=0, grid_index=None, lr=None, wd=None,
            p=None, p_reason='no_adaptation', objective=None, lower_boundary=False, upper_boundary=False,
            clipping=None, total_gain=0., mean_gain=0., negative_gain_fraction=0., positive_mass=0.,
            negative_absolute_mass=0., absolute_mass=0., cancellation_ratio=None,
            initial_validation_nll=r['metrics']['validation']['loss'], initial_test_nll=r['metrics']['test']['loss'],
            **metric_fields(r['metrics']))
        rows.append(row)
    return rows


def flat_rows(results, initials):
    rows = []
    for name, r in sorted(results.items()):
        c = r['config']
        initial_name = f'{c["variant"]}-w{c["width"]}-d{c["data_seed"]}-s{c["seed"]}'
        for h in r['history']:
            row = {k:c[k] for k in ['name', 'phase', 'variant', 'width', 'data_seed', 'seed', 'pretrain_seed',
                                    'grid_index', 'arm', 'lr', 'wd', 'parameters']}
            row.update(epoch=h['epoch'], p=h['p_star']['p'], p_reason=h['p_star'].get('reason'),
                objective=h['p_star'].get('objective'), total_gain=h['total_gain'],
                negative_gain_fraction=h['negative_gain_fraction'], clipping=h.get('clipping_cumulative'),
                lower_boundary=h['p_star'].get('at_lower_bound', False), upper_boundary=h['p_star'].get('at_upper_bound', False),
                initial_validation_nll=r['history'][0]['validation']['loss'],
                initial_test_nll=initials[initial_name]['metrics']['test']['loss'] if c['phase']=='confirm' else None,
                **metric_fields(h))
            rows.append(row)
    return rows


def diagnostics_analysis(results, records, initial_results, initial_records):
    all_items = []; rows = []; max_error = 0.; strict_failures = []
    def add(name, c, epoch, w, initial, current, expected=None, canonical=False):
        nonlocal max_error
        diag = diagnostic_decompose(w, initial, current)
        if expected is not None: assert diag['primary'] == expected
        if canonical: assert diag['primary']['p'] is None and diag['primary']['total_gain'] == 0
        mass = signed_mass(initial['loss']-current['loss'])
        assert mass['total_gain'] == diag['primary']['total_gain']
        max_error = max(max_error, diag['identity_max_abs_error'])
        item = dict(name=name, epoch=epoch, variant=c['variant'], width=c['width'], data_seed=c['data_seed'],
                    seed=c['seed'], arm=c['arm'], canonical_zero=canonical, signed_gain=mass, **diag)
        all_items.append(item)
        if diag['allocation']['defined'] and not diag['allocation']['gram_identity_check']['original_strict_pass']:
            strict_failures.append(dict(name=name, epoch=epoch, **diag['allocation']['gram_identity_check']))
        row = {k:item[k] for k in ['name', 'epoch', 'variant', 'width', 'data_seed', 'seed', 'arm', 'canonical_zero']}
        row.update(**mass, primary_p=diag['primary']['p'], primary_objective=diag['primary'].get('objective'),
                   primary_reason=diag['primary'].get('reason'),
                   primary_lower_boundary=diag['primary']['at_lower_bound'], primary_upper_boundary=diag['primary']['at_upper_bound'],
                   identity_max_abs_error=diag['identity_max_abs_error'])
        fits = {k:v['fit'] for k,v in diag['components'].items()}
        fits.update(group_instance=diag['group_instance_only'], oracle=diag['oracle_reference'])
        for key, fit in fits.items():
            row.update({f'{key}_{field}':fit.get(field) for field in ['p', 'reason', 'objective', 'total_gain', 'negative_gain_fraction',
                                                                       'at_lower_bound', 'at_upper_bound']})
        rows.append(row)
    for name, initial in sorted(initial_records.items()):
        r = initial_results[name]
        for arm in ['random', 'uniform']:
            add(name+'-'+arm, dict(r, arm=arm), 0, weights(r['seed'], arm), initial['train'], initial['train'], canonical=True)
    for name, rec in sorted(records.items()):
        r = results[name]; initial = rec['checkpoints'][0]['train']
        assert [x['epoch'] for x in rec['checkpoints']] == [0]+EPOCHS
        for cp, h in zip(rec['checkpoints'][1:], r['history'][1:]):
            add(name, r['config'], cp['epoch'], rec['weights'], initial, cp['train'], h['p_star'])
    audit = dict(status='PASS_WITH_PRESPECIFIED_ROUNDOFF_VERIFICATION',
        original_strict_failures=strict_failures, gain_identity_max_abs_error=max_error,
        canonical_zero_cells=len(initial_results), canonical_zero_weight_views=2*len(initial_results),
        adapted_checkpoints=len(records)*len(EPOCHS), all_primary_fits_equal_saved_training=True,
        undefined_zero_gain_and_uniform_preserved=True,
        undefined_primary_cumulative_comparisons=[dict(name=x['name'],epoch=x['epoch'],reason=x['allocation']['primary_cumulative_comparison_reason'])
            for x in all_items if 'primary_cumulative_comparison_reason' in x['allocation']])
    return dict(all=all_items, audit=audit), rows


def utility_gate(rows):
    corpora = []
    for d in sorted({r['data_seed'] for r in rows}):
        group = [r for r in rows if r['data_seed'] == d]
        delta = st.mean(r['initial_test_nll']-r['test_nll'] for r in group)
        val = st.mean(r['validation_nll'] for r in group)
        initial = st.mean(r['initial_validation_nll'] for r in group)
        corpora.append(dict(data_seed=d, mean_delta_test=delta, mean_validation_nll=val,
            mean_initial_validation_nll=initial, positive_test_gain=delta > 0,
            validation_improves=val <= initial, nonzero_updates=all(r['epoch'] > 0 for r in group)))
    return dict(corpora=corpora, all_corpora_positive=all(x['positive_test_gain'] for x in corpora),
        all_corpora_validation_improves=all(x['validation_improves'] for x in corpora),
        nonzero_updates=all(x['nonzero_updates'] for x in corpora),
        met=all(x['positive_test_gain'] and x['validation_improves'] and x['nonzero_updates'] for x in corpora))


def scaling_gate(rows):
    corpora = []
    for d in sorted({r['data_seed'] for r in rows}):
        groups = [[r for r in rows if r['data_seed'] == d and r['width'] == w] for w,l in CAPS]
        test = [st.mean(r['test_nll'] for r in g) for g in groups]
        validation = [st.mean(r['validation_nll'] for r in g) for g in groups]
        baseline = [st.mean(r['initial_validation_nll'] for r in g) for g in groups]
        corpora.append(dict(data_seed=d, test_nll=test, validation_nll=validation, initial_validation_nll=baseline,
            test_monotonic=test[0] > test[1] > test[2], validation_improves=all(x <= y for x,y in zip(validation, baseline))))
    return dict(corpora=corpora, met=all(x['test_monotonic'] and x['validation_improves'] for x in corpora))


def policy_analysis(selection, rows, baselines, diagnostic_rows):
    index = {(r['variant'],r['width'],r['data_seed'],r['seed'],r['arm'],r['grid_index'],r['epoch']):r
             for r in rows if r['phase']=='confirm' and r['epoch'] > 0}
    initial_index = {(r['variant'],r['width'],r['data_seed'],r['seed']):r for r in baselines}
    diagnostic_index = {(r['name'],r['epoch']):r for r in diagnostic_rows}
    cells = {}; selected_rows = []; fingerprints = {}; contrasts = {}
    metrics = ['p','objective','train_nll','validation_nll','test_nll','initial_test_nll','delta_test','delta_validation',
               'train_shared_accuracy','train_group_accuracy','train_instance_accuracy','train_instance_loss',
               'clipping','total_gain','mean_gain','positive_mass','negative_absolute_mass','negative_gain_fraction','cancellation_ratio']
    for policy in POLICIES:
        for variant in VARIANTS:
            key = f'{variant}_{policy}'
            choices = selection['decisions'][policy][variant]
            fingerprint = (variant, tuple((w,choices[str(w)]['grid_index'],choices[str(w)]['epoch']) for w,l in CAPS))
            alias = fingerprints.get(fingerprint); fingerprints.setdefault(fingerprint, key)
            arms = {}
            for arm in ['random','uniform']:
                selected = []
                for d,s,p in CONFIRM:
                    for w,l in CAPS:
                        choice = choices[str(w)]
                        if choice['epoch'] == 0:
                            r = dict(initial_index[variant,w,d,s], arm=arm, canonical_zero=True)
                            diag = diagnostic_index[r['name']+'-'+arm,0]
                        else:
                            r = dict(index[variant,w,d,s,arm,choice['grid_index'],choice['epoch']], canonical_zero=False)
                            diag = diagnostic_index[r['name'],r['epoch']]
                        r.update({metric:diag[metric] for metric in ['mean_gain','positive_mass','negative_absolute_mass',
                                  'absolute_mass','cancellation_ratio']})
                        r.update(cell=key, policy=policy, delta_test=r['initial_test_nll']-r['test_nll'],
                                 delta_validation=r['initial_validation_nll']-r['validation_nll'])
                        if r['epoch']==0:
                            assert r['delta_test']==r['delta_validation']==r['total_gain']==0 and r['p'] is None
                            assert r['clipping'] is None and r['cancellation_ratio'] is None
                        selected.append(r); selected_rows.append(r)
                capacity = []
                for w,l in CAPS:
                    group = [r for r in selected if r['width']==w]
                    stats = {metric:replicated([dict(data_seed=r['data_seed'],seed=r['seed'],value=r[metric]) for r in group])
                             for metric in metrics}
                    capacity.append(dict(width=w, selection=choices[str(w)], utility=utility_gate(group),
                        undefined_p=sum(r['p'] is None for r in group), lower_boundary=sum(r['lower_boundary'] for r in group),
                        upper_boundary=sum(r['upper_boundary'] for r in group), **stats))
                kvals = []
                for d,s,p in CONFIRM:
                    group = [next(r for r in selected if r['data_seed']==d and r['seed']==s and r['width']==w) for w,l in CAPS]
                    kvals.append(dict(data_seed=d,seed=s,value=contrast(*[r['p'] for r in group])))
                peak = replicated(kvals)
                arms[arm] = dict(capacity=capacity, useful_adaptation_met=all(x['utility']['met'] for x in capacity),
                    scaling=scaling_gate(selected), peak=peak, peak_verdict='undefined_uniform' if arm=='uniform' else peak_verdict(peak))
            cells[key] = dict(variant=variant, policy=policy, alias_of=alias, arms=arms)
    for policy in POLICIES:
        for arm in ['random','uniform']:
            a = cells[f'U_{policy}']['arms'][arm]; b = cells[f'M_{policy}']['arms'][arm]
            key = f'U_minus_M_{policy}_{arm}'
            contrasts[key] = dict(peak=replicated([dict(data_seed=d,seed=s,value=difference(x['value'],y['value']))
                for (d,s,p),x,y in zip(CONFIRM,a['peak']['values'],b['peak']['values'])]), capacity=[])
            for ca,cb in zip(a['capacity'],b['capacity']):
                contrasts[key]['capacity'].append(dict(width=ca['width'],delta_test=replicated([
                    dict(data_seed=x['data_seed'],seed=x['seed'],value=difference(x['value'],y['value']))
                    for x,y in zip(ca['delta_test']['values'],cb['delta_test']['values'])])))
    return dict(primary='U_R/random delta_test per capacity; global requires all three', cells=cells,
                descriptive_U_minus_M=contrasts, replication_unit='three independent data corpora; three model seeds nested per corpus'), selected_rows


def audit_gates(summary, selected):
    # Independently express each boolean gate from the flattened policy records.
    for cell, value in summary['cells'].items():
        for arm, stats in value['arms'].items():
            rows = [r for r in selected if r['cell']==cell and r['arm']==arm]
            usefulness = []
            for cap in stats['capacity']:
                groups = [[r for r in rows if r['data_seed']==d and r['width']==cap['width']] for d in sorted({r['data_seed'] for r in rows})]
                # Recompute paired differences, preserving the frozen strict-zero semantics.
                expected = all(all(r['epoch']>0 for r in g) and st.mean(r['initial_test_nll']-r['test_nll'] for r in g)>0 and
                    st.mean(r['validation_nll'] for r in g)<=st.mean(r['initial_validation_nll'] for r in g) for g in groups)
                assert cap['utility']['met']==expected
                usefulness.append(expected)
            assert stats['useful_adaptation_met']==all(usefulness)
            scaled=[]
            for d in sorted({r['data_seed'] for r in rows}):
                g=[[r for r in rows if r['width']==w and r['data_seed']==d] for w,l in CAPS]
                t=[st.mean(r['test_nll'] for r in group) for group in g]
                scaled.append(all(t[i]>t[i+1] for i in [0,1]) and all(
                    st.mean(r['validation_nll'] for r in group)<=st.mean(r['initial_validation_nll'] for r in group) for group in g))
            assert stats['scaling']['met']==all(scaled)
            k=[contrast(*[next(r['p'] for r in rows if r['width']==w and r['data_seed']==d and r['seed']==s)
                         for w,l in CAPS]) for d,s,p in CONFIRM]
            assert k==[x['value'] for x in stats['peak']['values']]
    return dict(status='PASS', checks=['paired utility and zero-update gates','separate scaling gate','signed K and undefined propagation'])


def baseline_analysis(rows):
    summary=[]; checks=[]
    for variant in VARIANTS:
        for w,l in CAPS:
            group=[r for r in rows if r['variant']==variant and r['width']==w]
            summary.append(dict(variant=variant,width=w,**{metric:replicated([
                dict(data_seed=r['data_seed'],seed=r['seed'],value=r[metric]) for r in group]) for metric in
                ['train_nll','validation_nll','test_nll','validation_shared_accuracy','validation_shared_loss',
                 'validation_group_loss','validation_instance_loss']}))
    for w,l in CAPS:
        for d in sorted({r['data_seed'] for r in rows}):
            groups={v:[r for r in rows if r['variant']==v and r['width']==w and r['data_seed']==d] for v in VARIANTS}
            means={v:{metric:st.mean(r[metric] for r in groups[v]) for metric in
                ['validation_group_loss','validation_instance_loss','validation_shared_accuracy']} for v in VARIANTS}
            passed=means['U']['validation_group_loss']<means['M']['validation_group_loss'] and \
                means['U']['validation_instance_loss']<means['M']['validation_instance_loss'] and means['U']['validation_shared_accuracy']>=.95
            checks.append(dict(width=w,data_seed=d,values=means,passed=passed))
    return dict(summary=summary,checks=checks,manipulation_pass=all(x['passed'] for x in checks))


def figures(out, summary, baseline, selection):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':160})
    widths=[w for w,l in CAPS]; x=np.arange(3); colors={'M':'#315b96','U':'#bd4e26'}
    fig, axes=plt.subplots(2,2,figsize=(12,8),sharey='row',layout='constrained')
    for row,variant in enumerate(['U','M']):
        for col,policy in enumerate(POLICIES):
            ax=axes[row,col]
            for arm in ['random','uniform']:
                caps=summary['cells'][f'{variant}_{policy}']['arms'][arm]['capacity']
                means=[c['delta_test']['between_corpora']['mean'] for c in caps]
                sd=[c['delta_test']['between_corpora']['sd'] for c in caps]
                ax.errorbar(x,means,yerr=sd,marker='o',color=colors[variant],linestyle='-' if arm=='random' else '--',
                            capsize=3,label=f'{variant} {arm}')
            ax.axhline(0,color='black',lw=.8); ax.set_xticks(x,widths); ax.set_xlabel('Width (layers 2 / 3 / 4)')
            ax.set_title(f'{variant} / {policy}: '+('random validation, primary selector' if policy=='R' else 'joint validation, secondary selector'))
            ax.legend(fontsize=9)
        axes[row,0].set_ylabel('Initial test NLL − selected test NLL\nPositive means improvement')
    fig.suptitle('Usefulness against the same pretrained baseline — mean ± SD across 3 corpora')
    fig.savefig(out/'utility.png'); plt.close(fig)
    fig, axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for col,policy in enumerate(POLICIES):
        for variant in VARIANTS:
            caps=summary['cells'][f'{variant}_{policy}']['arms']['random']['capacity']
            for row,metric in enumerate(['p','objective']):
                ax=axes[row,col]
                means=[c[metric]['between_corpora']['mean'] for c in caps]
                ax.plot(x,[np.nan if z is None else z for z in means],'-o',color=colors[variant],label=variant)
                for i,c in enumerate(caps):
                    vals=[q['value'] for q in c[metric]['values'] if q['value'] is not None]
                    ax.scatter(np.full(len(vals),i)+(-.045 if variant=='M' else .045),vals,s=13,alpha=.35,color=colors[variant])
                    if metric=='p' and c['undefined_p']:
                        ax.annotate(f'{variant}: {c["undefined_p"]}/9 undefined',xy=(i,.12 if variant=='M' else .035),
                            xycoords=('data','axes fraction'),ha='center',fontsize=8,color=colors[variant])
                ax.set_xticks(x,widths); ax.set_xlabel('Width'); ax.set_title(f'{policy}: random arm')
        axes[0,col].set_ylim(-.35,8.65); axes[0,col].axhline(8,ls=':',lw=.8,color='gray')
        axes[0,col].set_ylabel('p* (search interval 0..8)'); axes[0,col].legend()
        axes[1,col].set_yscale('symlog',linthresh=.001); axes[1,col].set_ylabel('Fit objective (symlog; lower is better)')
    fig.suptitle('Selected signed-gain fits — dots are paired seeds; missing means retain undefined values')
    fig.savefig(out/'selected-fits.png'); plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4),layout='constrained')
    configs=[(p,v) for p in POLICIES for v in VARIANTS]
    epochs=np.array([[selection['decisions'][p][v][str(w)]['epoch'] for w,l in CAPS] for p,v in configs])
    im=ax.imshow(epochs,cmap='Blues',vmin=0,vmax=30,aspect='auto')
    for i,(p,v) in enumerate(configs):
        for j,(w,l) in enumerate(CAPS):
            c=selection['decisions'][p][v][str(w)]
            label='epoch 0\nNO ADAPTATION' if c['epoch']==0 else f'epoch {c["epoch"]}\nLR {c["lr"]:g} / WD {c["wd"]:g}'
            ax.text(j,i,label,ha='center',va='center',fontsize=10,color='white' if c['epoch']>18 else 'black')
    ax.set_xticks(x,[f'width {w}' for w in widths]); ax.set_yticks(range(4),[f'{v} / {p}' for p,v in configs])
    ax.set_title('Frozen validation decisions — identical policies reuse the same models')
    fig.colorbar(im,ax=ax,label='Selected epoch'); fig.savefig(out/'selection.png'); plt.close(fig)
    fig,axes=plt.subplots(1,4,figsize=(14,4.3),layout='constrained')
    for ax,metric,title in zip(axes,['validation_shared_loss','validation_group_loss','validation_instance_loss','validation_shared_accuracy'],
                                ['Shared validation NLL','Group validation NLL','Instance validation NLL','Shared validation accuracy']):
        for variant in VARIANTS:
            caps=[next(c for c in baseline['summary'] if c['variant']==variant and c['width']==w) for w,l in CAPS]
            ax.plot(x,[c[metric]['between_corpora']['mean'] for c in caps],'-o',color=colors[variant],label=variant)
        if 'group' in metric or 'instance' in metric: ax.axhline(math.log(16),color='gray',ls=':',label='log(16)')
        if 'accuracy' in metric: ax.axhline(.95,color='gray',ls=':',label='95% gate'); ax.set_ylim(.9,1.01)
        ax.set_xticks(x,widths); ax.set_xlabel('Width'); ax.set_title(title); ax.legend(fontsize=8)
    fig.suptitle('Initial baseline manipulation — mean of three corpus means')
    fig.savefig(out/'baseline.png'); plt.close(fig)


def report(root, out, selection, summary, baseline, diagnostic, evidence, results, initial_results):
    primary=summary['cells']['U_R']['arms']['random']; complete=read(root/'COMPLETE.json')
    timers=dict(perf_counter_seconds=complete['elapsed_seconds'],utc_seconds=complete['utc_elapsed_seconds'])
    timings=f"perf_counter {timers['perf_counter_seconds']/60:.2f} menit; UTC {timers['utc_seconds']/60:.2f} menit"
    text='# Stage 5 v0.6 — adaptasi berguna dibanding tanpa adaptasi\n\n'
    text+=f'Run `{root.name}`. Training lokal selesai: **144 tuning + {selection["planned_confirmation"]} konfirmasi**, '
    text+='**66 pretrained models**, dan **54 evaluasi awal test**. Protokol/seleksi dibekukan sebelum hasil konfirmasi.\n\n'
    text+='## 1. Jawaban utama dan batas interpretasi\n\n'
    text+=f'Kriteria global adaptasi berguna untuk **U / R / random**: **{primary["useful_adaptation_met"]}**. '
    text+='Setiap kapasitas harus memakai update nonzero, memiliki penurunan test NLL positif pada ketiga rerata korpus, dan validation NLL tidak lebih buruk dari baseline pada setiap korpus. '
    text+='Delta = test NLL model awal − test NLL model terpilih; nilai positif berarti perbaikan.\n\n'
    text+=f"Pada kebijakan utama, p* undefined pada **{sum(c['undefined_p'] for c in primary['capacity'])}/27** pasangan kapasitas/seed, "
    text+=f"dan **{sum(c['upper_boundary'] for c in primary['capacity'])}/27** mencapai batas atas p*=8. "
    text+='Mean objective fit kecil/menengah/besar: '+', '.join(fmt(c['objective']['between_corpora']['mean']) for c in primary['capacity'])+'. '
    text+='Fit dibatasi pencarian atau tidak terdefinisi tidak membuktikan mekanisme pangkat; keputusan utility ditentukan oleh perbaikan held-out terhadap baseline sendiri.\n\n'
    text+=table(['Lebar','Epoch','Δ test mean','SD antar korpus','Rentang korpus','Update >0','3 korpus Δ>0','3 korpus val≤awal','Berguna'],[
        [c['width'],c['selection']['epoch'],fmt(c['delta_test']['between_corpora']['mean']),fmt(c['delta_test']['between_corpora']['sd']),
         f"{fmt(c['delta_test']['between_corpora']['minimum'])} … {fmt(c['delta_test']['between_corpora']['maximum'])}",
         c['utility']['nonzero_updates'],c['utility']['all_corpora_positive'],c['utility']['all_corpora_validation_improves'],c['utility']['met']]
        for c in primary['capacity']])+'\n\n'
    text+='Ketiga korpus adalah unit replikasi; tiga seed model/bobot per korpus adalah pasangan bersarang. Sembilan pasangan lengkap dan tiga rerata korpus disimpan di `policy-summary.json` dan `policy-cells.csv`. '
    text+='Pemilihan epoch 0 menghasilkan delta tepat nol dan p* undefined. Itu tidak memenuhi bukti belajar berguna.\n\n![Test utility](utility.png)\n\n'
    text+='## 2. Keputusan validation yang dibekukan\n\n'
    text+='R memilih mean validation random; J memilih mean gabungan random/uniform. Kandidat epoch 0 kanonik dibandingkan dengan enam optimizer × enam epoch. '
    text+='Tie: full precision score, epoch terdini, LR lalu WD terkecil. Tidak ada test, p*, peak, atau fit yang dipakai untuk memilih.\n\n'
    text+=table(['Kondisi','Selektor','Lebar','Grid','LR','WD','Epoch','Validation tuning'],[
        [v,p,w,selection['decisions'][p][v][str(w)]['grid_index'],selection['decisions'][p][v][str(w)]['lr'],
         selection['decisions'][p][v][str(w)]['wd'],selection['decisions'][p][v][str(w)]['epoch'],
         fmt(selection['decisions'][p][v][str(w)]['validation_nll'])] for p in POLICIES for v in VARIANTS for w,l in CAPS])+'\n\n'
    text+='Epoch 0 tidak memiliki optimizer. Kebijakan identik mengacu ke hasil yang sama, bukan replikasi tambahan. '
    text+='Confirmation melatih union konfigurasi nonzero yang terpilih sampai 30 epoch; checkpoint lainnya hanya deskriptif.\n\n![Selections](selection.png)\n\n'
    text+='## 3. Semua kebijakan: utility, scaling dan puncak terpisah\n\n'
    text+=table(['Kebijakan','Arm','Alias','Global useful','Scaling gate','K mean','K undefined/9','K positif/9','Verdict'],[
        [key,arm,cell['alias_of'] or '—',a['useful_adaptation_met'],a['scaling']['met'],fmt(a['peak']['between_corpora']['mean']),
         a['peak']['all_pairs']['undefined'],a['peak']['all_pairs']['positive'],a['peak_verdict']]
        for key,cell in summary['cells'].items() for arm,a in cell['arms'].items()])+'\n\n'
    text+='Scaling mensyaratkan test NLL turun ketat pada tiga kapasitas dan validation≤awal pada setiap kapasitas di setiap korpus. '
    text+='Baseline tanpa update boleh memenuhi scaling; utility tetap memerlukan perbaikan terhadap model awalnya sendiri. '
    text+='K = p* tengah − max(p* kecil, p* besar). Undefined dipropagasikan ke rerata/kontras, tidak dibuang. Uniform selalu memiliki p* undefined.\n\n'
    text+='## 4. Fit, cancellation dan memorisasi\n\n'
    text+='Puncak adalah hasil deskriptif estimator signed-gain dengan rentang pencarian [0,8]. Nilai batas, gain total kecil, cancellation kuat dan objective buruk membatasi interpretasi mekanisme. '
    text+='Tidak ada threshold kualitas fit tambahan yang dipakai sebagai filter atau untuk memilih model. Semua nilai dipertahankan.\n\n'
    text+=table(['Kebijakan','Lebar','p* mean','Undefined/9','Batas bawah/9','Batas atas/9','Fit objective mean','Cancellation ratio mean','Gain mean'],[
        [key,c['width'],fmt(c['p']['between_corpora']['mean']),c['undefined_p'],c['lower_boundary'],c['upper_boundary'],
         fmt(c['objective']['between_corpora']['mean']),fmt(c['cancellation_ratio']['between_corpora']['mean']),fmt(c['mean_gain']['between_corpora']['mean'])]
        for key,cell in summary['cells'].items() for c in cell['arms']['random']['capacity']])+'\n\n'
    text+='Rasio cancellation = |Σ gain| / Σ |gain|, undefined bila semua gain nol. Gain memakai pengurangan loss float32 asli sebelum konversi estimator ke float64. '
    text+='Garis mean pada gambar tidak ditampilkan jika satu pasangan saja undefined; titik terdefinisi tetap ditampilkan sebagai diagnostik, bukan rerata yang mengecualikan kegagalan.\n\n![Selected fits](selected-fits.png)\n\n'
    text+=table(['Kebijakan','Arm','Lebar','Train NLL','Validation NLL','Test NLL','Train instance accuracy','Clipping fraction'],[
        [key,arm,c['width'],fmt(c['train_nll']['between_corpora']['mean']),fmt(c['validation_nll']['between_corpora']['mean']),
         fmt(c['test_nll']['between_corpora']['mean']),fmt(c['train_instance_accuracy']['between_corpora']['mean']),fmt(c['clipping']['between_corpora']['mean'])]
        for key,cell in summary['cells'].items() for arm,a in cell['arms'].items() for c in a['capacity']])+'\n\n'
    text+='Clipping undefined pada epoch 0 karena tidak ada update. Semua checkpoint, loss/accuracy komponen, massa positif/negatif, '
    text+='komponen/group+instance/oracle-reference p*, signed allocation dan Gram tersimpan dalam CSV/JSON pendamping. Oracle-reference adalah diagnostik berlabel, bukan pengganti estimator utama.\n\n'
    text+='## 5. Manipulasi baseline\n\n'
    text+=f"Manipulation check semua kapasitas/korpus: **{baseline['manipulation_pass']}**; "
    text+=f"{sum(x['passed'] for x in baseline['checks'])}/{len(baseline['checks'])} lulus. U harus menurunkan initial group dan instance validation NLL dibanding M, dengan shared accuracy≥95%.\n\n"
    text+=table(['Lebar','Korpus','U group NLL','M group NLL','U instance NLL','M instance NLL','U shared accuracy','Lulus'],[
        [x['width'],x['data_seed'],fmt(x['values']['U']['validation_group_loss']),fmt(x['values']['M']['validation_group_loss']),
         fmt(x['values']['U']['validation_instance_loss']),fmt(x['values']['M']['validation_instance_loss']),
         fmt(x['values']['U']['validation_shared_accuracy']),x['passed']] for x in baseline['checks']])+'\n\n'
    text+='M/U memakai token, cold state, assignment dan batch order yang sama. U menambah auxiliary uniform-target CE; intervensi dapat mengubah representasi dan dinamika belajar. '
    text+='Karena itu U−M tidak mengisolasi efek satu angka baseline, dan check ini bukan penilaian kalibrasi probabilitas lengkap.\n\n![Baseline checks](baseline.png)\n\n'
    text+='## 6. Audit, kegagalan dan runtime\n\n'
    text+=f"Audit integritas independen: **{evidence['status']}**. Audit utility/scaling/K: **PASS**. "
    text+='Source beku, corpus penuh, equality token/label/cold state, checkpoint, assignment/order, candidate/tie/schedule, epoch0 aliases dan test sesudah selection diaudit.\n\n'
    strict=diagnostic['audit']['original_strict_failures']
    text+=f'Original Gram absolute-check failures: **{len(strict)}**. '
    text+='Setiap kegagalan strict tetap dicatat; verifikasi 70 digit dan batas akumulasi float64 yang dipraspesifikasikan harus lulus. '
    text+='Toleransi lainnya tidak dilonggarkan. Nilai fit/p* dan seleksi tidak diubah oleh verifikasi numerik. Detail di `DIAGNOSTIC_AUDIT.json`.\n\n'
    text+=f"Perbandingan cumulative component-vs-primary undefined akibat guard total gain primer: **{len(diagnostic['audit']['undefined_primary_cumulative_comparisons'])}**. "
    text+='Nilai tersebut disimpan null beserta alasan; komponen dan fit aslinya dipertahankan. Klarifikasi serialisasi ini dibekukan sebelum training dalam `ANALYSIS_CLARIFICATIONS.md`.\n\n'
    text+=f'Waktu training tercatat: **{timings}**. Selisih UTC − perf_counter = {timers["utc_seconds"]-timers["perf_counter_seconds"]:.6f} detik; penyebab selisih tidak disimpulkan. '
    text+='Budget 180 menit diperiksa menggunakan timer yang lebih besar. CPU audit/report di luar budget training.\n\n'
    adapt=list(results.values()); pre=[read(p) for p in sorted((root/'baselines').glob('*/result.json'))]; ini=list(initial_results.values())
    text+=table(['Tahap','Model/evaluasi/run','Peak allocated MiB','Peak reserved MiB'],[
        [label,len(group),fmt(max(r['peak_allocated_mib'] for r in group)),fmt(max(r['peak_reserved_mib'] for r in group))]
        for label,group in [('Pretraining',pre),('Initial evaluation',ini),('Adaptation',adapt)]])+'\n\n'
    text+='Tidak ada retry implisit, seed pengganti, cloud, upload, atau publikasi. Semua raw run ada di `work/runs/'+root.name+'`; model penuh tetap lokal. '
    text+='`raw-manifest.json` menyimpan SHA semua file raw; archive ringkas mempertahankan data, losses, weights/orders, source, checks dan report, dengan model biner besar dikecualikan dan hash tetap tersedia.\n\n'
    text+='## 7. Batas ilmiah dan provenance\n\n'
    text+='Hanya dua corpus/model tuning dan tiga korpus konfirmasi, tiga kapasitas, satu keluarga task sintetis, grid LR/WD terbatas, dan horizon 30 epoch. '
    text+='Tidak ada klaim optimum global, exact large-LM replication, pergeseran antara dua peak interior, novelty, atau jaminan venue/publikasi. '
    text+='Tidak ada notebook yang diklaim dieksekusi: script setara dijalankan. Arah eksperimen berikutnya harus ditetapkan sebagai protokol baru sebelum melihat hasil baru.\n\n'
    text+=f"Protocol SHA256: `{sha(HERE/'PROTOCOL_STAGE5.md')}`. Selection SHA256: `{sha(root/'selection.json')}`. "
    text+='Manifest source training dan analisis, environment lock, audit dan semua keputusan tersedia dalam raw archive. '
    text+='Stage4 memotivasi desain ini; hasil Stage4 tidak diperlakukan sebagai konfirmasi Stage5.\n'
    text+='\nPenyelarasan metode diperiksa terhadap [studi Jane Street](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/) '
    text+='dan [catatan estimatornya](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/sequence-weighting-note.pdf): '
    text+='bobot log-uniform, pemilihan validation, dan gain bertanda terhadap baseline menjadi acuan. '
    text+='[Pereyra et al.](https://arxiv.org/abs/1701.06548) menyediakan konteks prior untuk regularisasi kepercayaan output; '
    text+='U tidak diklaim identik atau baru. Batas pemeriksaan sumber tercatat dalam `LITERATURE_CHECK.md`.\n'
    (out/'REPORT.md').write_text(text,encoding='utf-8')


def verify_analysis_source(root):
    manifest=read(root/'analysis_source_manifest.json')
    required={'analyze_stage5.py','analysis_checks.py','audit_stage5.py'}
    assert required <= set(manifest)
    for name,digest in manifest.items():
        assert sha(root/'analysis-source'/name)==digest and sha(HERE/name)==digest, name
    checks=read(root/'ANALYSIS_CHECKS.json'); assert checks['status']=='PASS'
    return dict(status='PASS',source_sha256=manifest,fixture_checks=checks)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--run-id',required=True); parser.add_argument('--wait',action='store_true')
    args=parser.parse_args(); assert Path(args.run_id).name==args.run_id
    root=ROOT/'work/runs'/args.run_id; out=HERE/f'results-{args.run_id}'
    assert not out.exists(),'Preserve completed or partial analysis directory'
    torch.set_num_threads(4)
    if args.wait:
        print('Waiting for training completion; no measured outcomes inspected.',flush=True)
        while not (root/'COMPLETE.json').exists():
            if (root/'EXPERIMENT_FAILURE.json').exists() or list(root.rglob('failure.json')):
                raise RuntimeError('Training failure; preserve records')
            time.sleep(10)
    assert (root/'COMPLETE.json').exists()
    out.mkdir()
    try:
        source=verify_analysis_source(root); write(out/'ANALYSIS_SOURCE_AUDIT.json',source)
        from audit_stage5 import audit
        evidence,selection,results,records,initial_results,initial_records=audit(root)
        write(out/'AUDIT.json',evidence); print('Independent primary integrity audit PASS.',flush=True)
        rows=flat_rows(results,initial_results); baselines=initial_rows(initial_results)
        csvwrite(out/'all-checkpoints.csv',rows); csvwrite(out/'canonical-initial.csv',baselines)
        diagnostic,diag_rows=diagnostics_analysis(results,records,initial_results,initial_records)
        write(out/'diagnostics.json',diagnostic); write(out/'DIAGNOSTIC_AUDIT.json',diagnostic['audit']); csvwrite(out/'diagnostics.csv',diag_rows)
        summary,selected=policy_analysis(selection,rows,baselines,diag_rows)
        write(out/'policy-summary.json',summary); csvwrite(out/'policy-cells.csv',selected)
        write(out/'GATE_AUDIT.json',audit_gates(summary,selected))
        baseline=baseline_analysis(baselines); write(out/'baseline-summary.json',baseline)
        figures(out,summary,baseline,selection); report(root,out,selection,summary,baseline,diagnostic,evidence,results,initial_results)
        write(out/'analysis-provenance.json',dict(utc=utc(),source_sha256=source['source_sha256'],
            protocol_sha256=sha(HERE/'PROTOCOL_STAGE5.md'),selection_sha256=sha(root/'selection.json'),
            visual_review='pending human/agent image inspection; not asserted by this script'))
        for name in source['source_sha256']: shutil.copy2(HERE/name,out/name)
        for name in ['README.md','PROTOCOL_STAGE5.md']:
            shutil.copy2(HERE/name,out/name)
        print('Scientific report and figures generated; hashing raw records and building compact archive.',flush=True)
        manifest={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
        write(out/'raw-manifest.json',manifest)
        archive=out/'run-records.zip'; omitted=[]
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for p in sorted(root.rglob('*')):
                if not p.is_file(): continue
                rel=str(p.relative_to(root))
                if p.name in ['cold.pt','pretrained.pt'] or (p.name.startswith('model-e') and p.suffix=='.pt'):
                    omitted.append(rel); continue
                z.write(p,'raw/'+rel)
            write(out/'archive-omissions.json',dict(reason='Model binaries remain local; SHA256 retained in raw-manifest',files=omitted))
            for p in sorted(out.iterdir()):
                if p.is_file() and p!=archive: z.write(p,'report/'+p.name)
        with zipfile.ZipFile(archive) as z: assert z.testzip() is None
        write(out/'ARCHIVE_CHECK.json',dict(utc=utc(),sha256=sha(archive),bytes=archive.stat().st_size,crc='PASS',
            raw_files=len(manifest),omitted_model_binaries=len(omitted),retained_raw_files=len(manifest)-len(omitted)))
        print(json.dumps(dict(output=str(out),audit='PASS',archive='PASS',
            primary_global_useful=summary['cells']['U_R']['arms']['random']['useful_adaptation_met'],
            strict_gram_failures=len(diagnostic['audit']['original_strict_failures']))),flush=True)
    except Exception:
        write(out/'ANALYSIS_FAILURE.json',dict(utc=utc(),traceback=traceback.format_exc(),
            instruction='Preserve partial outputs; diagnose any scientific/numeric change under a new source/output version.'))
        raise


if __name__=='__main__': main()
