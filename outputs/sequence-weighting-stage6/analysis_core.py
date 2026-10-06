"""Stage 6 versioned analysis core; preserves Stage5 utility/fit definitions."""
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
from stage6 import ROOT, HERE, CAPS, EPOCHS, CONFIRM, VARIANTS, POLICIES, weights, read, write, sha, utc
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
            row.update(panel=c.get('panel'), epoch=h['epoch'], p=h['p_star']['p'], p_reason=h['p_star'].get('reason'),
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


