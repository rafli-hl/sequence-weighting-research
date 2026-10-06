"""Independent Stage 5 integrity audit; frozen before outcome inspection.

Selection is reconstructed from validation histories without calling runner
selection/schedule functions. This module never launches training or GPU work.
"""
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import torch
from stage5 import (ROOT, HERE, CAPS, EPOCHS, GRID, TUNE, CONFIRM, VARIANTS,
                    POLICIES, SOURCES, LIMIT_SECONDS, MAX_EPOCHS, data,
                    pre_data, weights, orders, tensor_hash, read, sha, utc)
from core import exponent
from model import Model


def design_checks():
    assert CAPS == [(64, 2), (128, 3), (256, 4)]
    assert EPOCHS == [1, 3, 5, 10, 20, 30] and MAX_EPOCHS == 30
    assert GRID == [dict(lr=lr, wd=wd, clip=1.)
                    for lr in [1e-5, 3e-5, 1e-4] for wd in [.1, 1.]]
    assert VARIANTS == ['M', 'U'] and POLICIES == ['R', 'J']
    assert TUNE == [(48371, 701, 96101), (50723, 702, 96102)]
    assert CONFIRM == [(d, s, p) for d, p in
                       [(52919, 96201), (55049, 96202), (57163, 96203)]
                       for s in [801, 802, 803]]
    assert LIMIT_SECONDS == 10800
    for position in [0, 1, 2]:
        assert set(x[position] for x in TUNE).isdisjoint(x[position] for x in CONFIRM)


def reconstruct_candidates(inputs):
    """Pure validation-only reconstruction; usable by synthetic fixture tests."""
    decisions, all_scores = {}, {}
    for policy in ['R', 'J']:
        decisions[policy] = {}
        for variant in ['M', 'U']:
            decisions[policy][variant] = {}
            for width, _ in CAPS:
                base_scores = []
                for data_seed, seed, _ in TUNE:
                    copies = [r['validation_nll'] for r in inputs
                              if (r['variant'], r['width'], r['data_seed'], r['seed'], r['epoch'])
                              == (variant, width, data_seed, seed, 0)]
                    assert len(copies) == 12 and len(set(copies)) == 1
                    base_scores.append(copies[0])
                candidates = [dict(grid_index=None, lr=None, wd=None, clip=None, epoch=0,
                                   validation_nll=sum(base_scores)/2, scores=base_scores)]
                for index, config in enumerate(GRID):
                    for epoch in EPOCHS:
                        scores = [r['validation_nll'] for r in inputs
                                  if (r['variant'], r['width'], r['grid_index'], r['epoch'])
                                  == (variant, width, index, epoch)
                                  and (policy == 'J' or r['arm'] == 'random')]
                        assert len(scores) == (4 if policy == 'J' else 2)
                        assert all(math.isfinite(s) for s in scores)
                        candidates.append(dict(grid_index=index, **config, epoch=epoch,
                                               validation_nll=sum(scores)/len(scores), scores=scores))
                assert len(candidates) == 37 and all(math.isfinite(x['validation_nll']) for x in candidates)
                ordered = sorted(candidates, key=lambda x: (x['validation_nll'], x['epoch'],
                                                            0. if x['lr'] is None else x['lr'],
                                                            0. if x['wd'] is None else x['wd']))
                decisions[policy][variant][str(width)] = ordered[0]
                all_scores[f'{policy}-{variant}-{width}'] = candidates
    return decisions, all_scores


def independent_schedule(root):
    design_checks()
    def make(phase, v, w, l, d, s, p, i, arm):
        return dict(name=f'{phase}-{v}-w{w}-d{d}-s{s}-g{i:02d}-{arm}', phase=phase,
                    variant=v, width=w, layers=l, data_seed=d, seed=s, pretrain_seed=p,
                    grid_index=i, **GRID[i], epochs=30, arm=arm)
    tuning = [make('tune', v, w, l, d, s, p, i, arm) for w, l in CAPS
              for d, s, p in TUNE for v in VARIANTS for i in range(6) for arm in ['random', 'uniform']]
    assert len(tuning) == 144 and tuning == read(root/'tuning_schedule.json')
    selection = read(root/'selection.json')
    inputs, input_hashes = [], {}
    for c in tuning:
        path = root/'runs'/c['name']/'history.json'
        input_hashes[str(path.relative_to(root))] = sha(path)
        history = read(path)
        assert [h['epoch'] for h in history] == [0]+EPOCHS
        assert all(h['test'] is None for h in history)
        for h in history:
            inputs.append(dict(variant=c['variant'], width=c['width'], data_seed=c['data_seed'],
                               seed=c['seed'], grid_index=c['grid_index'], arm=c['arm'],
                               epoch=h['epoch'], validation_nll=h['validation']['loss']))
    assert input_hashes == selection['input_hashes'] and inputs == selection['inputs']
    decisions, all_scores = reconstruct_candidates(inputs)
    assert decisions == selection['decisions'] and all_scores == selection['all_scores']
    confirmation = []
    for w, l in CAPS:
        for d, s, p in CONFIRM:
            for v in VARIANTS:
                indices = sorted({decisions[policy][v][str(w)]['grid_index'] for policy in POLICIES}-{None})
                for index in indices:
                    for arm in ['random', 'uniform']:
                        confirmation.append(make('confirm', v, w, l, d, s, p, index, arm))
    assert confirmation == selection['run_schedule']
    assert len(confirmation) == selection['planned_confirmation'] <= 216
    assert selection['baseline_test_evaluations'] == 54
    assert selection['test_used'] is False and selection['confirmation_used'] is False
    assert selection['tie_order'] == ['full precision validation NLL', 'earliest epoch', 'LR ascending', 'WD ascending']
    return selection, tuning+confirmation


def _equal_record(left, right):
    assert set(left) == set(right) == {'loss', 'component_loss', 'component_accuracy'}
    assert all(torch.equal(left[key], right[key]) for key in left)


def _metrics(record, metrics, count):
    assert set(record) == {'loss', 'component_loss', 'component_accuracy'}
    assert record['loss'].shape == (count,)
    assert record['component_loss'].shape == record['component_accuracy'].shape == (count, 3)
    assert all(x.dtype == torch.float32 and torch.isfinite(x).all() for x in record.values())
    assert torch.all((record['component_accuracy'] >= 0) & (record['component_accuracy'] <= 1))
    assert torch.all(record['loss'] >= 0) and torch.all(record['component_loss'] >= 0)
    assert abs(float(record['loss'].mean())-metrics['loss']) < 1e-7
    for j, kind in enumerate(['shared', 'group', 'instance']):
        for metric, field in [('loss', 'component_loss'), ('accuracy', 'component_accuracy')]:
            assert abs(float(record[field][:, j].mean())-metrics[kind][metric]) < 1e-7


def _resources(item):
    for key in ['elapsed_seconds', 'peak_allocated_mib', 'peak_reserved_mib']:
        assert math.isfinite(item[key]) and item[key] > 0
    assert item['peak_reserved_mib'] >= item['peak_allocated_mib']


def _fit(weights_tensor, initial, current):
    # Preserve the specified float32 subtraction, then fit signed float64 gains.
    gain = (initial-current).double()
    fitted = exponent(weights_tensor.tolist(), gain.tolist())
    fitted.update(total_gain=float(gain.sum()), mean_gain=float(gain.mean()),
                  negative_gain_fraction=float((gain < 0).double().mean()),
                  at_lower_bound=fitted['p'] is not None and fitted['p'] <= .001,
                  at_upper_bound=fitted['p'] is not None and fitted['p'] >= 7.999)
    return fitted


def _event_audit(root, selection, schedule, initial_names, baseline_names):
    events = [json.loads(line) for line in (root/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    kinds = Counter(event['kind'] for event in events)
    expected_kinds = {'protocol_source_frozen', 'experiment_started', 'pretraining_complete',
                      'run_start', 'run_complete', 'selection_frozen', 'baseline_test_evaluation',
                      'experiment_complete'}
    if selection['planned_confirmation']:
        expected_kinds.add('test_evaluation')
    assert set(kinds) == expected_kinds
    for name in ['protocol_source_frozen', 'experiment_started', 'selection_frozen', 'experiment_complete']:
        assert kinds[name] == 1
    def indices(kind): return [i for i, event in enumerate(events) if event['kind'] == kind]
    freeze = indices('selection_frozen')[0]
    assert indices('protocol_source_frozen')[0] < indices('experiment_started')[0] < freeze < indices('experiment_complete')[0]
    frozen = events[freeze]
    selection_hash = sha(root/'selection.json')
    assert frozen['sha256'] == selection_hash
    assert frozen['planned_confirmation'] == selection['planned_confirmation']
    assert events[indices('protocol_source_frozen')[0]]['sha256'] == read(root/'source_manifest.json')
    assert datetime.fromisoformat(selection['frozen_utc']) <= datetime.fromisoformat(frozen['utc'])
    for kind in ['run_start', 'run_complete']:
        actual = [events[i]['name'] for i in indices(kind)]
        assert actual == [c['name'] for c in schedule]
        assert all((i < freeze) == events[i]['name'].startswith('tune-') for i in indices(kind))
    starts = {events[i]['name']:i for i in indices('run_start')}
    completes = {events[i]['name']:i for i in indices('run_complete')}
    assert all(starts[name] < completes[name] for name in starts)
    pre = [events[i]['name'] for i in indices('pretraining_complete')]
    assert len(pre) == 66 and set(pre) == baseline_names
    tuning_pre = {f'{v}-w{w}-s{s}-d{p}' for w, _ in CAPS for _, s, p in TUNE for v in VARIANTS}
    assert all((i < freeze) == (events[i]['name'] in tuning_pre) for i in indices('pretraining_complete'))
    baseline_tests = [events[i] for i in indices('baseline_test_evaluation')]
    assert len(baseline_tests) == 54 and {x['name'] for x in baseline_tests} == initial_names
    assert all(x['epoch'] == 0 for x in baseline_tests)
    tests = [events[i] for i in indices('test_evaluation')]
    assert len(tests) == 6*selection['planned_confirmation']
    assert {(x['name'], x['epoch']) for x in tests} == {(c['name'], e) for c in selection['run_schedule'] for e in EPOCHS}
    for kind in ['baseline_test_evaluation', 'test_evaluation']:
        assert all(i > freeze and events[i]['selection_sha256'] == selection_hash
                   and datetime.fromisoformat(events[i]['utc']) > datetime.fromisoformat(frozen['utc']) for i in indices(kind))
    assert all(starts[x['name']] < i < completes[x['name']] for i, x in enumerate(events) if x['kind'] == 'test_evaluation')
    if tests:
        assert max(indices('baseline_test_evaluation')) < min(starts[c['name']] for c in selection['run_schedule'])
    return events, kinds


def audit(root):
    root = Path(root)
    assert (root/'COMPLETE.json').exists(), 'Training incomplete'
    assert not list(root.rglob('failure.json')), 'A recorded failure requires explicit diagnosis'
    source = read(root/'source_manifest.json')
    assert source == {name:sha(HERE/name) for name in SOURCES}
    assert all(sha(root/'source'/name) == digest for name, digest in source.items())
    assert read(root/'VALIDATION.json')['status'] == 'PASS'
    historical = read(root/'historical_manifest.json')
    for name, digest in historical.items():
        assert sha(ROOT/name) == digest, f'Historical change: {name}'
    print(f'Historical hashes PASS ({len(historical)} files).', flush=True)
    selection, schedule = independent_schedule(root)
    expected = {c['name']:c for c in schedule}
    assert len(expected) == len(schedule)
    assert {p.name for p in (root/'runs').iterdir() if p.is_dir()} == set(expected)
    assert {p.parent.name for p in (root/'runs').glob('*/result.json')} == set(expected)

    corpus_meta = {}
    corpus_names = {f'adapt-{d}' for d, _, _ in TUNE+CONFIRM} | {f'premixed-{p}' for _, _, p in TUNE+CONFIRM}
    assert {p.name for p in (root/'corpora').iterdir() if p.is_dir()} == corpus_names
    assert len(corpus_names) == 10
    for name in sorted(corpus_names):
        folder = root/'corpora'/name
        kind, seed = name.split('-'); seed = int(seed)
        saved = torch.load(folder/'dataset.pt', weights_only=True)
        meta = read(folder/'metadata.json')
        regenerated, regenerated_meta = data(seed) if kind == 'adapt' else pre_data(seed, 'M')
        assert {k:v for k, v in meta.items() if k not in ['file_sha256', 'tensor_sha256']} == regenerated_meta
        assert sha(folder/'dataset.pt') == meta['file_sha256']
        assert set(saved) == set(regenerated) == ({'train', 'validation', 'test'} if kind == 'adapt' else {'train', 'validation'})
        alternate, _ = data(seed, include_test=False) if kind == 'adapt' else pre_data(seed, 'U')
        for split, pair in saved.items():
            assert len(pair) == 2 and all(torch.equal(a, b) for a, b in zip(pair, regenerated[split]))
            assert tensor_hash(*pair) == meta['tensor_sha256'][split]
            if split in alternate:
                assert all(torch.equal(a, b) for a, b in zip(pair, alternate[split]))
        keys = sum(meta['sequence_keys_by_split'].values(), [])
        assert len(keys) == len(set(keys))
        corpus_meta[name] = meta

    baseline_names = {f'{v}-w{w}-s{s}-d{p}' for w, _ in CAPS for _, s, p in TUNE+CONFIRM for v in VARIANTS}
    assert len(baseline_names) == 66
    assert {p.name for p in (root/'baselines').iterdir() if p.is_dir()} == baseline_names
    baseline_meta, cold_models, parameter_counts = {}, {}, {}
    for name in sorted(baseline_names):
        folder = root/'baselines'/name
        b = read(folder/'result.json')
        assert name == f'{b["variant"]}-w{b["width"]}-s{b["seed"]}-d{b["data_seed"]}'
        assert b['source_sha256'] == source and (b['width'], b['layers']) in CAPS
        assert sha(folder/'pretrained.pt') == b['checkpoint_sha256'] and sha(folder/'cold.pt') == b['cold_sha256']
        cold = torch.load(folder/'cold.pt', weights_only=True)
        pretrained = torch.load(folder/'pretrained.pt', weights_only=True)
        assert {k:tensor_hash(v) for k, v in cold.items()} == b['cold_tensor_sha256']
        key = b['width'], b['seed']
        if key not in cold_models:
            with torch.random.fork_rng(devices=[]):
                torch.manual_seed(b['seed'])
                model = Model(b['width'], b['layers'], 40)
                cold_models[key] = model.state_dict()
                parameter_counts[b['width']] = sum(p.numel() for p in model.parameters())
        assert set(cold) == set(pretrained) == set(cold_models[key])
        assert all(torch.equal(cold[k], cold_models[key][k]) for k in cold)
        assert all(v.shape == cold[k].shape and v.dtype == torch.float32 and torch.isfinite(v).all() for k, v in pretrained.items())
        order = torch.load(folder/'orders.pt', weights_only=True)
        assert torch.equal(order, orders(b['seed'], 2048, 4)) and tensor_hash(order) == b['batch_order_sha256']
        assert b['data'] == corpus_meta[f'premixed-{b["data_seed"]}']
        records = torch.load(folder/'sequence_losses.pt', weights_only=True)
        assert [x['epoch'] for x in b['history']] == [x['epoch'] for x in records] == [1, 2, 3, 4]
        for history, record in zip(b['history'], records):
            for split, count in [('train', 2048), ('validation', 256)]:
                _metrics(record[split], history[split], count)
            assert math.isfinite(history['training_objective']) and history['training_objective'] >= 0
            assert math.isfinite(history['gradient_norm_mean']) and history['gradient_norm_mean'] >= 0
            assert 0 <= history['gradient_clip_fraction'] <= 1
        _resources(b)
        baseline_meta[name] = b
    del cold_models

    initial_names = {f'{v}-w{w}-d{d}-s{s}' for w, _ in CAPS for d, s, _ in CONFIRM for v in VARIANTS}
    assert len(initial_names) == 54
    assert {p.name for p in (root/'initial-evaluations').iterdir() if p.is_dir()} == initial_names
    initial_results, initial_records = {}, {}
    selection_hash = sha(root/'selection.json')
    for name in sorted(initial_names):
        folder = root/'initial-evaluations'/name
        r = read(folder/'result.json')
        assert name == r['name'] == f'{r["variant"]}-w{r["width"]}-d{r["data_seed"]}-s{r["seed"]}'
        assert (r['data_seed'], r['seed'], r['pretrain_seed']) in CONFIRM
        assert (r['width'], r['layers']) in CAPS and r['variant'] in VARIANTS
        assert r['parameters'] == parameter_counts[r['width']]
        b = baseline_meta[f'{r["variant"]}-w{r["width"]}-s{r["seed"]}-d{r["pretrain_seed"]}']
        dm = corpus_meta[f'adapt-{r["data_seed"]}']
        assert r['baseline_sha256'] == b['checkpoint_sha256'] and r['data_sha256'] == dm['tensor_sha256']
        assert set(sum(dm['sequence_keys_by_split'].values(), [])).isdisjoint(sum(b['data']['sequence_keys_by_split'].values(), []))
        assert r['source_sha256'] == source and r['selection_sha256'] == selection_hash
        assert sha(folder/'sequence_losses.pt') == r['sequence_file_sha256']
        records = torch.load(folder/'sequence_losses.pt', weights_only=True)
        assert set(records) == set(r['metrics']) == {'train', 'validation', 'test'}
        for split, count in [('train', 512), ('validation', 256), ('test', 512)]:
            _metrics(records[split], r['metrics'][split], count)
        _resources(r)
        initial_results[name], initial_records[name] = r, records

    results, records, first_initial, crossed = {}, {}, {}, {}
    pair_checks = 0
    for name in sorted(expected):
        folder = root/'runs'/name
        r = read(folder/'result.json'); c = r['config']
        assert r['status'] == 'complete' and c == read(folder/'config.json')
        assert all(c[k] == v for k, v in expected[name].items())
        assert c['source_sha256'] == source and c['parameters'] == parameter_counts[c['width']]
        assert c['selection_sha256'] == (selection_hash if c['phase'] == 'confirm' else None)
        dm = corpus_meta[f'adapt-{c["data_seed"]}']
        b = baseline_meta[f'{c["variant"]}-w{c["width"]}-s{c["seed"]}-d{c["pretrain_seed"]}']
        assert c['data_sha256'] == dm['tensor_sha256'] and c['baseline_sha256'] == b['checkpoint_sha256']
        assert set(sum(dm['sequence_keys_by_split'].values(), [])).isdisjoint(sum(b['data']['sequence_keys_by_split'].values(), []))
        assignment = torch.load(folder/'assignment.pt', weights_only=True)
        rec = torch.load(folder/'sequence_losses.pt', weights_only=True)
        assert torch.equal(assignment['weights'], weights(c['seed'], c['arm']))
        assert torch.equal(rec['weights'], assignment['weights'])
        assert torch.equal(assignment['orders'], orders(c['seed']))
        assert tensor_hash(assignment['weights']) == c['weight_sha256'] and tensor_hash(assignment['orders']) == c['batch_order_sha256']
        assert r['history'] == read(folder/'history.json') and r['epoch_stats'] == read(folder/'epoch_stats.json')
        assert [h['epoch'] for h in r['history']] == [cp['epoch'] for cp in rec['checkpoints']] == [0]+EPOCHS
        assert [h['epoch'] for h in r['epoch_stats']] == list(range(1, 31))
        assert set(r['checkpoint_sha256']) == {str(e) for e in EPOCHS}
        assert {p.name for p in folder.glob('model-*.pt')} == {f'model-e{e:02d}.pt' for e in EPOCHS}
        for stat in r['epoch_stats']:
            assert stat['updates'] == 16 and 0 <= stat['gradient_clip_fraction'] <= 1
            assert math.isfinite(stat['gradient_norm_max']) and 0 <= stat['gradient_norm_mean'] <= stat['gradient_norm_max']
        for history, checkpoint in zip(r['history'], rec['checkpoints']):
            splits = [('train', 512), ('validation', 256)]
            if c['phase'] == 'confirm': splits.append(('test', 512))
            else: assert history['test'] is None and checkpoint['test'] is None
            for split, count in splits:
                _metrics(checkpoint[split], history[split], count)
            epoch = history['epoch']
            if epoch:
                fitted = _fit(rec['weights'], rec['checkpoints'][0]['train']['loss'], checkpoint['train']['loss'])
                assert fitted == history['p_star']
                assert history['total_gain'] == fitted['total_gain'] and history['negative_gain_fraction'] == fitted['negative_gain_fraction']
                assert sha(folder/f'model-e{epoch:02d}.pt') == r['checkpoint_sha256'][str(epoch)]
                assert history['clipping_cumulative'] == sum(x['gradient_clip_fraction'] for x in r['epoch_stats'][:epoch])/epoch
                assert all(history[k] == v for k, v in r['epoch_stats'][epoch-1].items())
            else:
                assert history['p_star'] == dict(p=None, reason='no_adaptation')
                assert history['total_gain'] == history['negative_gain_fraction'] == 0.
                assert history.get('clipping_cumulative') is None
        key = c['variant'], c['width'], c['data_seed'], c['seed']
        if key in first_initial:
            previous, baseline_hash = first_initial[key]
            assert c['baseline_sha256'] == baseline_hash
            for split in ['train', 'validation']:
                _equal_record(rec['checkpoints'][0][split], previous[split])
            pair_checks += 1
        else: first_initial[key] = rec['checkpoints'][0], c['baseline_sha256']
        if c['phase'] == 'confirm':
            initial_name = f'{c["variant"]}-w{c["width"]}-d{c["data_seed"]}-s{c["seed"]}'
            assert c['baseline_sha256'] == initial_results[initial_name]['baseline_sha256']
            for split in ['train', 'validation', 'test']:
                _equal_record(rec['checkpoints'][0][split], initial_records[initial_name][split])
                assert r['history'][0][split] == initial_results[initial_name]['metrics'][split]
            records[name] = rec
        key = c['data_seed'], c['seed'], c['arm']
        value = c['data_sha256'], c['weight_sha256'], c['batch_order_sha256']
        if key in crossed: assert crossed[key] == value
        else: crossed[key] = value
        _resources(r)
        results[name] = r

    events, event_counts = _event_audit(root, selection, schedule, initial_names, baseline_names)
    complete = read(root/'COMPLETE.json')
    assert complete['tuning_runs'] == 144 and complete['confirmation_runs'] == selection['planned_confirmation']
    assert complete['pretraining_checkpoints'] == 66 and complete['baseline_test_evaluations'] == 54
    assert len(schedule) <= 360
    assert 0 < complete['elapsed_seconds'] <= LIMIT_SECONDS and 0 < complete['utc_elapsed_seconds'] <= LIMIT_SECONDS
    started = next(x['utc'] for x in events if x['kind'] == 'experiment_started')
    utc_interval = (datetime.fromisoformat(complete['utc'])-datetime.fromisoformat(started)).total_seconds()
    assert 0 < utc_interval <= LIMIT_SECONDS
    # START_UTC precedes the start event and COMPLETE.utc precedes its elapsed
    # computation by microseconds; a 1-second serialization allowance verifies
    # these independent UTC records without claiming exact timestamp equality.
    assert abs(utc_interval-complete['utc_elapsed_seconds']) < 1.
    evidence = dict(status='PASS', utc=utc(), tuning_runs=144,
        confirmation_runs=selection['planned_confirmation'], pretraining=66,
        model_checkpoints=6*len(schedule), test_evaluations=54+event_counts['test_evaluation'],
        adapted_test_evaluations=event_counts['test_evaluation'], baseline_test_evaluations=54,
        baseline_pair_checks=pair_checks, historical_files_unchanged=len(historical),
        failed_runs=[], selection_sha256=selection_hash, event_counts=dict(event_counts),
        elapsed_seconds=complete['elapsed_seconds'], utc_elapsed_seconds=complete['utc_elapsed_seconds'],
        utc_timestamp_interval_seconds=utc_interval,
        timer_difference_seconds=complete['utc_elapsed_seconds']-complete['elapsed_seconds'],
        budget_seconds=LIMIT_SECONDS, both_budget_timers_pass=True,
        peak_allocated_mib=max(r['peak_allocated_mib'] for r in results.values()),
        peak_reserved_mib=max(r['peak_reserved_mib'] for r in results.values()), checks=[
            'frozen training source and all historical hashes unchanged',
            'literal preregistered design, validation-only canonical-zero candidates and deterministic ties',
            'selected nonzero configuration union independently reconstructed; no extra trajectories',
            'full corpora regenerated; full M/U token/label equality and test-toggle invariance',
            'all split/phase key namespaces disjoint',
            'every cold model regenerated and full tensors equal across all applicable arms',
            'all pretrained/adapted model hashes; exact pretrained checkpoint reuse and initial losses',
            'paired full assignments and batch orders across configurations/conditions/capacities',
            '54 canonical epoch0 tests saved once and exact records reused in all trajectories',
            'all test events after selection; none in tuning; exact six-checkpoint confirmation schedule',
            'all scalar/component metrics and signed primary p* independently reconstructed',
            'all recorded runs/resources finite and complete; both clocks meet three-hour cap'])
    return evidence, selection, results, records, initial_results, initial_records
