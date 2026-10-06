"""Stage10 input provenance, copied from the frozen Stage9 independent audit."""
from collections import defaultdict
from pathlib import Path
import numpy as np
import torch
from common_stage10 import ROOT,read,sha,array_sha,tensor_array_sha
DESIGNS = {
    4: dict(run='baseline-v05-20260929-01', report='results-baseline-v05-20260929-01-r2',
            corpora=[(41843, 95201), (43997, 95202), (46219, 95203)],
            seeds=[601, 602, 603], panels=[None], references=54, native=54),
    5: dict(run='utility-v06-20260929-01', report='results-utility-v06-20260929-01-r1',
            corpora=[(52919, 96201), (55049, 96202), (57163, 96203)],
            seeds=[801, 802, 803], panels=[None], references=54, native=54),
    6: dict(run='stability-v07-20260929-01', report='results-stability-v07-20260929-01',
            corpora=[(61103, 97201), (61211, 97202), (61319, 97203)],
            seeds=[1001, 1002, 1003], panels=['P1', 'P2', 'P3', 'P4'],
            references=216, native=99),
}


def tensor_hash(tensor):
    import hashlib
    value = hashlib.sha256()
    value.update(str((tuple(tensor.shape), str(tensor.dtype))).encode())
    value.update(tensor.contiguous().numpy().tobytes())
    return value.hexdigest()


def provenance(raw, timer):
    """Reconstruct every reference independently of the cohort extractors."""
    references = read(raw/'inputs/references.json')
    inputs = read(raw/'inputs/profiles.json')
    assert len(references) == 324 and len({r['reference_id'] for r in references}) == 324
    assert len({r['native_id'] for r in references}) == 207
    origin = read(raw/'inputs/origin_manifest.json')
    for name, digest in origin.items():
        timer.check()
        assert sha(ROOT/name) == digest == sha(raw/'inputs/source-files'/name), name

    def snapshot(name):
        assert name in origin, ('unbound source path', name)
        return raw/'inputs/source-files'/name

    historical_bindings = 0
    for stage, design in DESIGNS.items():
        path = f"outputs/sequence-weighting-stage{stage}/{design['report']}/raw-manifest.json"
        old_manifest = read(snapshot(path))
        prefix = f"work/runs/{design['run']}/"
        for name, digest in origin.items():
            if name.startswith(prefix):
                assert old_manifest[name[len(prefix):]] == digest, ('unbound historical raw file', name)
                historical_bindings += 1

    cache = {}
    def load(name):
        if name not in cache:
            cache[name] = torch.load(snapshot(name), weights_only=True, map_location='cpu')
        return cache[name]

    by_id = {p['source_id']: p for p in inputs}
    assert len(by_id) == len(inputs) == 186
    mapped = defaultdict(list)
    native_map = {}
    native_arrays = {}
    checked_data = {}
    paired_weights = {}
    paired_orders = {}
    paired_baselines = {}
    arrays_checked, pairing_checks = 0, 0
    actual_design = set()
    for ref in references:
        timer.check()
        stage, panel = ref['stage'], ref['panel']
        actual_design.add((stage, panel, ref['variant'], ref['width'], ref['data_seed'], ref['seed']))
        assert stage in DESIGNS and ref['variant'] in ['M', 'U']
        assert ref['config']['arm'] == 'random'
        assert ref['corpus_path'] == ref['source_paths']['dataset']
        paths = ref['source_paths']
        assert all(name in origin for name in ref['source_files'])
        selection = read(snapshot(paths['selection']))
        if stage == 4:
            assert panel is None and ref['policy'] == 'fixed' and ref['cohort'] == 'S4_fixed30'
            assert ref['epoch'] == 30 and ref['grid_index'] == 0 and not ref['canonical_zero']
            expected_name = f"confirm-{ref['variant']}-w{ref['width']}-d{ref['data_seed']}-s{ref['seed']}-g00-random"
            assert ref['source_name'] == expected_name
            selected = [c for c in selection['run_schedule'] if c['name'] == expected_name]
            assert len(selected) == 1 and selected[0]['phase'] == 'confirm'
            assert ref['decision'] is None
        else:
            assert ref['policy'] == 'R'
            assert ref['cohort'] == ('S5_R' if stage == 5 else f'S6_{panel}_R')
            decisions = selection['decisions'] if stage == 5 else selection['decisions'][panel]
            decision = decisions['R'][ref['variant']][str(ref['width'])]
            assert ref['decision'] == decision
            assert ref['epoch'] == decision['epoch'] and ref['grid_index'] == decision['grid_index']
            assert ref['canonical_zero'] == (decision['epoch'] == 0)
            assert (ref['grid_index'] is None) == ref['canonical_zero']
        assert dict(DESIGNS[stage]['corpora'])[ref['data_seed']] == ref['pretrain_seed']

        historical = read(snapshot(paths['result']))
        records = load(paths['sequence'])
        assignment = load(paths['assignment'])
        weights = assignment['weights']
        assert weights.dtype == torch.float32 and weights.shape == (512,)
        assert torch.isfinite(weights).all() and (weights > 0).all()
        weight_key = (stage, ref['seed'])
        if weight_key in paired_weights:
            assert torch.equal(weights, paired_weights[weight_key])
        else:
            paired_weights[weight_key] = weights
        assert assignment['orders'].dtype == torch.int64
        assert assignment['orders'].ndim == 2 and assignment['orders'].shape[1] == 512
        order_key = (stage, ref['data_seed'], ref['seed'])
        if order_key in paired_orders:
            other_order = paired_orders[order_key]
            common_length = min(len(other_order), len(assignment['orders']))
            assert torch.equal(other_order[:common_length], assignment['orders'][:common_length])
        else:
            paired_orders[order_key] = assignment['orders']
        if ref['canonical_zero']:
            assert ref['original_fit'] == dict(p=None, reason='no_adaptation')
            initial = current = records['train']['loss']
            assert ref['history'] == ref['initial_history']
            assert ref['history']['epoch'] == 0
            assert all(ref['history'][name] == values for name, values in historical['metrics'].items())
            assert sha(snapshot(paths['sequence'])) == historical['sequence_file_sha256']
            donor_config = read(snapshot(str(Path(paths['assignment']).parent/'config.json')))
            assert donor_config['seed'] == ref['seed'] and donor_config['width'] == ref['width']
            assert donor_config['data_seed'] == ref['data_seed'] and donor_config['arm'] == 'random'
            assert tensor_hash(weights) == donor_config['weight_sha256'] == ref['config']['weight_sha256']
            assert donor_config['selection_sha256'] == sha(snapshot(paths['selection']))
            assert tensor_hash(assignment['orders']) == donor_config['batch_order_sha256']
        else:
            assert torch.equal(weights, records['weights'])
            assert historical['status'] == 'complete' and historical['config'] == ref['config']
            assert ref['config']['name'] == ref['source_name'] and ref['config']['phase'] == 'confirm'
            assert ref['config']['variant'] == ref['variant'] and ref['config']['width'] == ref['width']
            assert ref['config']['data_seed'] == ref['data_seed'] and ref['config']['seed'] == ref['seed']
            assert ref['config']['pretrain_seed'] == ref['pretrain_seed']
            assert ref['config']['selection_sha256'] == sha(snapshot(paths['selection']))
            checkpoints = {c['epoch']: c for c in records['checkpoints']}
            assert len(checkpoints) == len(records['checkpoints'])
            initial = checkpoints[0]['train']['loss']
            current = checkpoints[ref['epoch']]['train']['loss']
            histories = {h['epoch']: h for h in historical['history']}
            assert ref['history'] == histories[ref['epoch']] and ref['initial_history'] == histories[0]
            assert ref['original_fit'] == ref['history']['p_star']
            assert tensor_hash(weights) == ref['config']['weight_sha256']
            assert tensor_hash(assignment['orders']) == ref['config']['batch_order_sha256']
        assert initial.dtype == current.dtype == torch.float32
        assert initial.shape == current.shape == (512,)
        assert torch.isfinite(initial).all() and torch.isfinite(current).all()
        gains = (initial-current).double()  # Historical subtraction before promotion.
        arrays = dict(weights=weights.numpy(), initial_loss=initial.numpy(),
                      current_loss=current.numpy(), gains=gains.numpy())
        assert {name: tensor_array_sha(array) for name, array in arrays.items()} == ref['array_hashes']
        if not ref['canonical_zero']:
            assert float(gains.sum()) == ref['history']['total_gain'] == ref['original_fit']['total_gain']
            assert float(gains.mean()) == ref['original_fit']['mean_gain']
            assert float((gains < 0).double().mean()) == ref['original_fit']['negative_gain_fraction']
        else:
            assert torch.count_nonzero(gains) == 0
        assert float(initial.mean()) == ref['initial_history']['train']['loss']
        assert float(current.mean()) == ref['history']['train']['loss']

        baseline = read(snapshot(paths['baseline_metadata']))
        for field in ['variant', 'width', 'seed']:
            assert baseline[field] == ref[field]
        assert baseline['data_seed'] == ref['pretrain_seed']
        assert baseline['checkpoint_sha256'] == ref['config']['baseline_sha256']
        assert baseline['source_sha256'] == ref['config']['source_sha256']
        baseline_key = (stage, ref['variant'], ref['width'], ref['seed'], ref['pretrain_seed'])
        if baseline_key in paired_baselines:
            assert paired_baselines[baseline_key] == baseline['checkpoint_sha256']
        else:
            paired_baselines[baseline_key] = baseline['checkpoint_sha256']

        dataset = load(paths['dataset'])
        metadata = read(snapshot(paths['dataset_metadata']))
        assert sha(snapshot(paths['dataset'])) == metadata['file_sha256']
        import hashlib
        tensor_digests = {}
        for split, values in dataset.items():
            h = hashlib.sha256()
            for tensor in values:
                h.update(str((tuple(tensor.shape), str(tensor.dtype))).encode())
                h.update(tensor.contiguous().numpy().tobytes())
            tensor_digests[split] = h.hexdigest()
        assert tensor_digests == metadata['tensor_sha256']
        key = (stage, ref['data_seed'])
        assert set(dataset) == {'train', 'validation', 'test'}
        if key in checked_data:
            other = checked_data[key]
            for split in dataset:
                assert len(dataset[split]) == len(other[split])
                assert all(torch.equal(a, b) for a, b in zip(dataset[split], other[split]))
                pairing_checks += 1
        else:
            live_dataset = torch.load(ROOT/paths['dataset'], weights_only=True, map_location='cpu')
            assert set(live_dataset) == set(dataset)
            for split in dataset:
                assert len(live_dataset[split]) == len(dataset[split])
                assert all(torch.equal(a, b) for a, b in zip(live_dataset[split], dataset[split]))
            checked_data[key] = dataset

        source_id = ref['source_id']
        profile = by_id[source_id]
        assert profile['n'] == 512
        assert array_sha(weights.numpy()) == profile['weights_sha256']
        assert array_sha(gains.numpy()) == profile['gains_sha256']
        assert profile['original_p'] == ref['original_fit']['p']
        assert profile['original_objective'] == ref['original_fit'].get('objective')
        assert profile['original_reason'] == ref['original_fit'].get('reason')
        guard = ('constant_weights' if float(weights.max())-float(weights.min()) < 1e-12
                 else 'nonpositive_total_gain' if sum(gains.tolist()) <= 1e-10 else None)
        assert profile['expected_guard'] == guard
        with np.load(raw/'inputs/arrays'/f'{source_id}.npz', allow_pickle=False) as stored:
            assert set(stored.files) == set(arrays)
            assert np.array_equal(stored['weights'], weights.numpy())
            assert np.array_equal(stored['gains'], gains.numpy())
            assert stored['weights'].dtype == stored['initial_loss'].dtype == stored['current_loss'].dtype == np.dtype('float32')
            assert stored['gains'].dtype == np.dtype('float64')
            assert np.array_equal((stored['initial_loss']-stored['current_loss']).astype('float64'), stored['gains'])
        if ref['native_id'] in native_map:
            assert native_map[ref['native_id']] == source_id
            assert native_arrays[ref['native_id']] == ref['array_hashes']
        native_map[ref['native_id']] = source_id
        native_arrays[ref['native_id']] = ref['array_hashes']
        mapped[source_id].append(ref)
        arrays_checked += 1

    expected_design = {(stage, panel, variant, width, data, seed)
        for stage, design in DESIGNS.items() for panel in design['panels']
        for variant in ['M', 'U'] for width in [64, 128, 256]
        for data, _ in design['corpora'] for seed in design['seeds']}
    assert actual_design == expected_design and len(actual_design) == 324
    for stage, design in DESIGNS.items():
        stage_refs = [r for r in references if r['stage'] == stage]
        assert len(stage_refs) == design['references']
        assert len({r['native_id'] for r in stage_refs}) == design['native']
    assert set(mapped) == set(by_id)
    for source_id, group in mapped.items():
        profile = by_id[source_id]
        assert sorted(profile['reference_ids']) == sorted(r['reference_id'] for r in group)
        assert sorted(profile['native_ids']) == sorted({r['native_id'] for r in group})
        with np.load(raw/'inputs/arrays'/f'{source_id}.npz', allow_pickle=False) as stored:
            hashes = {key: tensor_array_sha(stored[key]) for key in stored.files}
        assert any(hashes == ref['array_hashes'] for ref in group), 'Representative loss arrays are not a selected reference'
    assert len({(p['weights_sha256'], p['gains_sha256']) for p in inputs}) == len(inputs)
    return dict(references=324, native_checkpoints=207, unique_arrays=len(inputs),
                arrays_reconstructed=arrays_checked, full_split_pairing_checks=pairing_checks,
                corpus_datasets=len(checked_data), origin_files=len(origin),
                original_raw_manifest_bindings=historical_bindings)


