"""Analysis and raw-array audit for the prospective diagnostic; never trains."""
import math
import statistics
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
import torch
from run import (ROOT, OLD, NEW, OUT, CORPORA, CAPS, SEEDS, EPOCHS, sha, read, write,
                 check_bound, source_hashes, verify_approved_manifest, setup_runtime, tensor_hash)
from independent_audit import check_budget, audit_gain, reevaluate_f10

MAX_SECONDS = 600
TOL = 2e-6


def close(a, b, tolerance=TOL):
    return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tolerance


def assert_metrics(metrics, arrays):
    for split in ('train', 'validation', 'test'):
        r = arrays[split]
        m = metrics[split]
        assert close(float(r['loss'].mean()), m['loss'])
        for i, component in enumerate(('shared', 'group', 'instance')):
            assert close(float(r['component_loss'][:, i].mean()), m[component]['loss'])
            assert close(float(r['component_accuracy'][:, i].mean()), m[component]['accuracy'])
        assert len(r['loss']) == {'train': 512, 'validation': 256, 'test': 512}[split]
        assert torch.isfinite(r['loss']).all() and torch.isfinite(r['component_loss']).all()


def fit_equal(a, b):
    for key in ('p', 'objective', 'total_gain', 'negative_gain_fraction'):
        x, y = a.get(key), b.get(key)
        if x is None or y is None:
            assert x is None and y is None
        else:
            assert close(x, y, 1e-8), key
    assert a.get('reason') == b.get('reason')


def mean_complete(values):
    return None if any(v is None for v in values) else math.fsum(values) / len(values)


def aggregate(rows):
    by_corpus = []
    for corpus in CORPORA:
        values = [r['value'] for r in rows if r['corpus'] == corpus]
        assert len(values) == 2
        by_corpus.append({'corpus': corpus, 'nested': values, 'mean': mean_complete(values)})
    values = [r['mean'] for r in by_corpus]
    return {'pairs': rows, 'corpora': by_corpus, 'mean': mean_complete(values),
            'sd': None if any(v is None for v in values) else statistics.stdev(values),
            'range': None if any(v is None for v in values) else [min(values), max(values)]}


def main():
    start = time.monotonic()
    if not (NEW / 'TRAINING_COMPLETE.json').exists() or (NEW / 'FAILURE.json').exists():
        raise RuntimeError('Training completion required and failure forbidden')
    completed = read(NEW / 'TRAINING_COMPLETE.json')
    if completed['status'] != 'complete' or completed['rows'] != 30 or completed['elapsed_seconds_before_receipt'] >= 1200:
        raise RuntimeError('Invalid training completion receipt')
    saved = read(NEW / 'plan.json')
    if saved['source_sha256'] != source_hashes():
        raise RuntimeError('Source drift since launch')
    if verify_approved_manifest(saved['anchors']['approved_manifest_sha256']) != saved['anchors']:
        raise RuntimeError('Approved anchors changed')
    if setup_runtime() != saved['runtime']:
        raise RuntimeError('Training runtime drift')
    expected = saved['rows']
    if len(expected) != 30 or len({r['name'] for r in expected}) != 30:
        raise RuntimeError('Frozen plan inventory invalid')
    observations, failures = [], []
    for row in expected:
        check_budget(start)
        folder = NEW / 'runs' / row['name']
        result = read(folder / 'result.json')
        assert result['status'] == 'complete' and result['row'] == row
        assert result['source_sha256'] == saved['source_sha256']
        for key, filename in (('history','history.json'),('arrays','sequence_losses.pt'),
                              ('updates','updates.json'),('F10','epoch-10.pt')):
            assert check_bound(result[key]) == (folder / filename).resolve()
        paths = {key: check_bound(item) for key,item in row['inputs'].items()}
        history = read(check_bound(result['history']))
        arrays = torch.load(check_bound(result['arrays']), weights_only=True)
        updates = read(check_bound(result['updates']))
        assert [h['epoch'] for h in history] == list(EPOCHS)
        assert [a['epoch'] for a in arrays] == list(EPOCHS)
        assert [(u['epoch'],u['update']) for u in updates] == [(e,i) for e in range(1,11) for i in range(16)]
        assert all(math.isfinite(u['gradient_norm']) and u['gradient_norm'] >= 0 and
                   math.isfinite(u['objective']) for u in updates)
        assignment = torch.load(paths['assignment'], weights_only=True)
        w = assignment['weights']
        assert tensor_hash(w) == row['expected_weight_hash']
        assert tensor_hash(assignment['orders']) == row['expected_order_hash']
        datasets = {split: torch.load(paths[split], weights_only=True) for split in ('train','validation','test')}
        for split, pair in datasets.items():
            assert tensor_hash(*pair) == row['expected_data_hashes'][split]
        initial = arrays[0]['train']
        audit_counts = []
        for h, a in zip(history, arrays):
            assert_metrics(h['metrics'], a)
            if h['epoch']:
                audit_counts.append(audit_gain(w, initial, a['train'], h['diagnostic']))
        control_history = read(paths['control_history'])
        control_arrays = torch.load(paths['control_arrays'], weights_only=True)
        ch = next(h for h in control_history if h['epoch'] == 10)
        ca = next(a for a in control_arrays if a['epoch'] == 10)
        assert_metrics({'train': ch['train'], 'validation': ch['validation'], 'test': ch['test']}, ca)
        control_audit = audit_gain(w, initial, ca['train'], ch['diagnostic'])
        assert control_arrays[0]['epoch'] == 0
        reevaluate_f10(row, check_bound(result['F10']), datasets, arrays[-1], start)
        no = history[-1]['metrics']
        old_initial = torch.load(paths['initial'], weights_only=True)
        for split in ('train', 'validation', 'test'):
            for key in ('loss', 'component_loss', 'component_accuracy'):
                assert torch.equal(arrays[0][split][key], old_initial[split][key])
        observations.append({'width': row['width'], 'corpus': row['corpus'], 'seed': row['seed'],
            'validation_nll_clip_minus_noclip': ch['validation']['loss'] - no['validation']['loss'],
            'own_baseline_test_gain_noclip': float(old_initial['test']['loss'].mean()) - no['test']['loss'],
            'p_clip': ch['fit']['p'], 'p_noclip': history[-1]['diagnostic']['fit']['p'],
            'fit_clip': ch['fit'], 'fit_noclip': history[-1]['diagnostic']['fit'],
            'control_clip_fraction': ch['clipping'], 'gradient_norms_noclip': [u['gradient_norm'] for u in updates],
            'new_fit_audit': audit_counts, 'control_fit_audit': control_audit,
            'metrics_noclip': {str(h['epoch']): h['metrics'] for h in history},
            'component_gains_noclip': {k: old_initial['test']['component_loss'][:, i].mean().item() -
                no['test'][k]['loss'] for i, k in enumerate(('shared', 'group', 'instance'))},
            'result_sha256': sha(folder / 'result.json')})
    assert len(observations) == 30
    primary = aggregate([{'corpus': r['corpus'], 'seed': r['seed'],
                          'value': r['validation_nll_clip_minus_noclip']}
                         for r in observations if r['width'] == 128])
    gain = aggregate([{'corpus': r['corpus'], 'seed': r['seed'],
                       'value': r['own_baseline_test_gain_noclip']}
                      for r in observations if r['width'] == 128])
    criterion = (primary['mean'] is not None and primary['mean'] >= .01 and
                 all(x['mean'] is not None and x['mean'] > 0 for x in primary['corpora']) and
                 all(x['mean'] is not None and x['mean'] > 0 for x in gain['corpora']))
    contrasts = []
    for corpus in CORPORA:
        for seed in SEEDS:
            members = {r['width']: r for r in observations if r['corpus'] == corpus and r['seed'] == seed}
            assert set(members) == set(CAPS)
            ps = [members[w]['p_clip'] for w in CAPS]
            pn = [members[w]['p_noclip'] for w in CAPS]
            kc = None if any(p is None for p in ps) else ps[1] - max(ps[0], ps[2])
            kn = None if any(p is None for p in pn) else pn[1] - max(pn[0], pn[2])
            contrasts.append({'corpus': corpus, 'seed': seed, 'K_clip': kc, 'K_noclip': kn,
                              'delta_K_noclip_minus_clip': None if kc is None or kn is None else kn - kc})
    delta_k = aggregate([{'corpus': r['corpus'], 'seed': r['seed'],
                          'value': r['delta_K_noclip_minus_clip']} for r in contrasts])
    check_budget(start)
    OUT.mkdir(parents=True, exist_ok=False)
    write(OUT / 'AUDIT_AND_ANALYSIS.json', {'status': 'CANDIDATE_RAW_ARRAY_AUDIT_PASS_PENDING_INDEPENDENT_REVIEW',
        'coverage': {'planned': 30, 'completed': len(observations), 'audited': len(observations),
                     'epochs_per_run': list(EPOCHS), 'updates_per_run': 160, 'failures': failures},
        'source_sha256': saved['source_sha256'], 'observations': observations,
        'primary': primary, 'test_gain': gain, 'practical_criterion_met': criterion,
        'K_pairs': contrasts, 'delta_K': delta_k, 'analysis_seconds': time.monotonic() - start})
    try:
        check_budget(start)
    except BaseException:
        (OUT / 'AUDIT_AND_ANALYSIS.json').unlink()
        raise


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        OUT.mkdir(parents=True, exist_ok=True)
        write(OUT / 'AUDIT_FAILURE.json', {'status': 'NONPASSING_PARTIAL', 'error': repr(exc)})
        raise
