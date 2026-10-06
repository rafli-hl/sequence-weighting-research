"""Analysis and raw-array audit for the prospective diagnostic; never trains."""
import math
import statistics
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
import torch
from run import (ROOT, OLD, NEW, CORPORA, CAPS, SEEDS, EPOCHS, sha, read, write,
                 check_bound, source_hashes, plan, tensor_hash)
from engine import diagnostics

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
    saved = read(NEW / 'plan.json')
    if saved['source_sha256'] != source_hashes():
        raise RuntimeError('Source drift since launch')
    expected = plan()
    if saved['rows'] != expected or len(expected) != 30:
        raise RuntimeError('Plan/input drift')
    observations, failures = [], []
    for row in expected:
        if time.monotonic() - start > MAX_SECONDS:
            raise RuntimeError('Analysis/audit 10-minute cap')
        folder = NEW / 'runs' / row['name']
        result = read(folder / 'result.json')
        assert result['status'] == 'complete' and result['row'] == row
        assert result['source_sha256'] == saved['source_sha256']
        for key in ('history', 'arrays', 'updates', 'F10'):
            check_bound(result[key])
        for item in row['inputs'].values():
            check_bound(item)
        history = read(folder / 'history.json')
        arrays = torch.load(folder / 'sequence_losses.pt', weights_only=True)
        updates = read(folder / 'updates.json')
        assert [h['epoch'] for h in history] == list(EPOCHS)
        assert [a['epoch'] for a in arrays] == list(EPOCHS)
        assert len(updates) == 160 and all(math.isfinite(u['gradient_norm']) for u in updates)
        assert all(u['epoch'] in range(1, 11) and u['update'] in range(16) for u in updates)
        assignment = torch.load(check_bound(row['inputs']['assignment']), weights_only=True)
        w = assignment['weights']
        initial = arrays[0]['train']
        for h, a in zip(history, arrays):
            assert_metrics(h['metrics'], a)
            if h['epoch']:
                recomputed = diagnostics(w, initial, a['train'])
                fit_equal(recomputed['fit'], h['diagnostic']['fit'])
                for component in ('shared', 'group', 'instance'):
                    fit_equal(recomputed['component_fits'][component], h['diagnostic']['component_fits'][component])
        control_history = read(check_bound(row['inputs']['control_history']))
        control_arrays = torch.load(check_bound(row['inputs']['control_arrays']), weights_only=True)
        ch = next(h for h in control_history if h['epoch'] == 10)
        ca = next(a for a in control_arrays if a['epoch'] == 10)
        assert_metrics({'train': ch['train'], 'validation': ch['validation'], 'test': ch['test']}, ca)
        control_diag = diagnostics(w, initial, ca['train'])
        fit_equal(control_diag['fit'], ch['fit'])
        assert control_arrays[0]['epoch'] == 0
        f10 = torch.load(folder / 'epoch-10.pt', weights_only=True)
        assert set(f10) == set(torch.load(check_bound(row['inputs']['baseline']), weights_only=True))
        no = history[-1]['metrics']
        old_initial = torch.load(check_bound(row['inputs']['initial']), weights_only=True)
        for split in ('train', 'validation', 'test'):
            for key in ('loss', 'component_loss', 'component_accuracy'):
                assert torch.equal(arrays[0][split][key], old_initial[split][key])
        observations.append({'width': row['width'], 'corpus': row['corpus'], 'seed': row['seed'],
            'validation_nll_clip_minus_noclip': ch['validation']['loss'] - no['validation']['loss'],
            'own_baseline_test_gain_noclip': float(old_initial['test']['loss'].mean()) - no['test']['loss'],
            'p_clip': ch['fit']['p'], 'p_noclip': history[-1]['diagnostic']['fit']['p'],
            'fit_clip': ch['fit'], 'fit_noclip': history[-1]['diagnostic']['fit'],
            'control_clip_fraction': ch['clipping'], 'gradient_norms_noclip': [u['gradient_norm'] for u in updates],
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
    out = ROOT / 'outputs/g1-clipping-diagnostic-v0129/results'
    out.mkdir(parents=True, exist_ok=False)
    write(out / 'AUDIT_AND_ANALYSIS.json', {'status': 'RAW_ARRAY_AUDIT_PASS',
        'coverage': {'planned': 30, 'completed': len(observations), 'audited': len(observations),
                     'epochs_per_run': list(EPOCHS), 'updates_per_run': 160, 'failures': failures},
        'source_sha256': saved['source_sha256'], 'observations': observations,
        'primary': primary, 'test_gain': gain, 'practical_criterion_met': criterion,
        'K_pairs': contrasts, 'delta_K': delta_k, 'analysis_seconds': time.monotonic() - start})


if __name__ == '__main__':
    main()
