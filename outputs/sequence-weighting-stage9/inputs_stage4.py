"""Read-only Stage 4 fixed-epoch cohort extraction; no estimator evaluation.

The cohort is defined solely by the frozen Stage 4 design. Historical primary
gains subtract saved float32 sequence losses before promotion to float64.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import torch


RUN_ID = 'baseline-v05-20260929-01'
CAPACITIES = [(64, 2), (128, 3), (256, 4)]
CORPORA = [(41843, 95201), (43997, 95202), (46219, 95203)]
SEEDS = [601, 602, 603]
VARIANTS = ['M', 'U']
EPOCHS = [0, 1, 3, 10, 30, 60]


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _tensor_hash(*tensors):
    """Historical engine.tensor_hash, including shape and torch dtype."""
    h = hashlib.sha256()
    for tensor in tensors:
        h.update(str((tuple(tensor.shape), str(tensor.dtype))).encode())
        h.update(tensor.contiguous().numpy().tobytes())
    return h.hexdigest()


def _load(path):
    return torch.load(path, weights_only=True, map_location='cpu')


def collect(project_root: Path) -> dict:
    """Return 54 native-reference arrays and their original source records.

    This reads and verifies retained artifacts only. It neither optimizes p nor
    calculates objective profiles. Model binaries are deliberately not copied.
    """
    project_root = Path(project_root).resolve()
    raw = project_root / 'work/runs' / RUN_ID
    source = project_root / 'outputs/sequence-weighting-stage4'
    report = source / f'results-{RUN_ID}-r2'
    raw_manifest = _read(report / 'raw-manifest.json')
    training_manifest = _read(raw / 'source_manifest.json')
    files = set()
    verified = {}

    def add(path, expected=None):
        path = Path(path).resolve()
        relative = path.relative_to(project_root).as_posix()
        assert path.is_file(), relative
        if path.is_relative_to(raw):
            key = path.relative_to(raw).as_posix()
            assert key in raw_manifest, ('missing historical file hash', key)
            saved = raw_manifest[key]
            assert expected is None or saved == expected, relative
            expected = saved
        if expected is not None:
            if relative not in verified:
                verified[relative] = _sha(path)
            assert verified[relative] == expected, ('file hash mismatch', relative)
        files.add(relative)
        return relative

    common = set()
    for name in ['source_manifest.json', 'selection.json', 'COMPLETE.json',
                 'VALIDATION.json', 'runtime.json', 'events.jsonl']:
        common.add(add(raw / name))
    for name, digest in training_manifest.items():
        common.add(add(raw / 'source' / name, digest))
        common.add(add(source / name, digest))
    # Preserve both original and repaired verification provenance. The repair
    # did not alter primary gains, p*, or checkpoint selections.
    for directory in ['analysis-source', 'analysis-repair-source']:
        for path in sorted((raw / directory).iterdir()):
            if path.is_file():
                common.add(add(path))
    for name in ['raw-manifest.json', 'AUDIT.json', 'DIAGNOSTIC_AUDIT.json',
                 'REPORT.md', 'analysis-provenance.json', 'NUMERICAL_REPAIR.md',
                 'ANALYSIS_REPAIR.json', 'diagnostics.json', 'diagnostics.csv',
                 'all-checkpoints.csv', 'policy-summary.json', 'policy-cells.csv']:
        common.add(add(report / name))
    common.add(add(source / f'FINAL_REVIEW-{RUN_ID}.json'))
    audit = _read(report / 'AUDIT.json')
    assert audit['status'] == 'PASS' and audit['failed_runs'] == []
    selection_sha = _sha(raw / 'selection.json')
    assert audit['selection_sha256'] == selection_sha
    diagnostic_audit = _read(report / 'DIAGNOSTIC_AUDIT.json')
    assert diagnostic_audit['status'] == 'PASS_AFTER_DOCUMENTED_NUMERICAL_REPAIR'
    assert diagnostic_audit['every_primary_fit_matches_saved_training_result']
    assert diagnostic_audit['primary_definition_unchanged']
    schedule = _read(raw / 'selection.json')['run_schedule']
    selected_schedule = {
        c['name'] for c in schedule
        if c['phase'] == 'confirm' and c['variant'] in VARIANTS
        and c['arm'] == 'random' and c['grid_index'] == 0
    }
    assert len(selected_schedule) == 54

    corpus_cache = {}

    def corpus(kind, seed):
        key = (kind, seed)
        if key not in corpus_cache:
            folder = raw / 'corpora' / f'{kind}-{seed}'
            paths = {add(folder / 'metadata.json')}
            metadata = _read(folder / 'metadata.json')
            paths.add(add(folder / 'dataset.pt', metadata['file_sha256']))
            dataset = _load(folder / 'dataset.pt')
            assert {split: _tensor_hash(*pair) for split, pair in dataset.items()} == metadata['tensor_sha256']
            corpus_cache[key] = (metadata, paths)
        return corpus_cache[key]

    references = []
    for variant in VARIANTS:
        for width, layers in CAPACITIES:
            for data_seed, pretrain_seed in CORPORA:
                for seed in SEEDS:
                    name = f'confirm-{variant}-w{width}-d{data_seed}-s{seed}-g00-random'
                    assert name in selected_schedule
                    folder = raw / 'runs' / name
                    own = set(common)
                    for filename in ['config.json', 'result.json', 'history.json',
                                     'epoch_stats.json', 'assignment.pt', 'sequence_losses.pt']:
                        own.add(add(folder / filename))
                    config = _read(folder / 'config.json')
                    result = _read(folder / 'result.json')
                    expected = dict(name=name, phase='confirm', variant=variant,
                                    width=width, layers=layers, data_seed=data_seed,
                                    seed=seed, pretrain_seed=pretrain_seed, grid_index=0,
                                    lr=.0001, wd=.1, clip=1., epochs=60, arm='random')
                    assert all(config[k] == v for k, v in expected.items())
                    assert result['config'] == config and result['status'] == 'complete'
                    assert config['source_sha256'] == training_manifest
                    assert config['selection_sha256'] == selection_sha
                    histories = _read(folder / 'history.json')
                    assert histories == result['history']
                    assert [h['epoch'] for h in histories] == EPOCHS
                    assert _read(folder / 'epoch_stats.json') == result['epoch_stats']
                    history = next(h for h in histories if h['epoch'] == 30)
                    initial_history = histories[0]

                    dm, paths = corpus('adapt', data_seed)
                    own.update(paths)
                    assert config['data_sha256'] == dm['tensor_sha256']
                    assert dm['ntrain'] == 512 and dm['nval'] == 256 and dm['ntest'] == 512
                    pm, paths = corpus('premixed', pretrain_seed)
                    own.update(paths)
                    baseline = raw / 'baselines' / f'{variant}-w{width}-s{seed}-d{pretrain_seed}'
                    for filename in ['result.json', 'orders.pt', 'sequence_losses.pt']:
                        own.add(add(baseline / filename))
                    bm = _read(baseline / 'result.json')
                    assert bm['variant'] == variant and bm['width'] == width and bm['layers'] == layers
                    assert bm['seed'] == seed and bm['data_seed'] == pretrain_seed
                    assert bm['source_sha256'] == training_manifest and bm['data'] == pm
                    assert bm['checkpoint_sha256'] == config['baseline_sha256']
                    assert _tensor_hash(_load(baseline / 'orders.pt')) == bm['batch_order_sha256']

                    assignment = _load(folder / 'assignment.pt')
                    records = _load(folder / 'sequence_losses.pt')
                    weights = records['weights']
                    assert weights.dtype == torch.float32 and tuple(weights.shape) == (512,)
                    assert torch.isfinite(weights).all() and (weights > 0).all()
                    assert torch.equal(weights, assignment['weights'])
                    assert _tensor_hash(weights) == config['weight_sha256']
                    assert _tensor_hash(assignment['orders']) == config['batch_order_sha256']
                    assert assignment['orders'].dtype == torch.int64
                    assert tuple(assignment['orders'].shape) == (60, 512)
                    checkpoints = records['checkpoints']
                    assert [cp['epoch'] for cp in checkpoints] == EPOCHS
                    initial = checkpoints[0]['train']['loss']
                    current = next(cp for cp in checkpoints if cp['epoch'] == 30)['train']['loss']
                    for values in [initial, current]:
                        assert values.dtype == torch.float32 and tuple(values.shape) == (512,)
                        assert torch.isfinite(values).all()
                    # Do not promote either loss before this subtraction.
                    gains = (initial - current).double()
                    saved_fit = history['p_star']
                    assert float(gains.sum()) == saved_fit['total_gain'] == history['total_gain']
                    assert float(gains.mean()) == saved_fit['mean_gain']
                    assert float((gains < 0).double().mean()) == saved_fit['negative_gain_fraction']
                    assert float(initial.mean()) == initial_history['train']['loss']
                    assert float(current.mean()) == history['train']['loss']
                    arrays = {key: value.detach().cpu().numpy().copy() for key, value in
                              [('weights', weights), ('initial_loss', initial),
                               ('current_loss', current), ('gains', gains)]}
                    assert arrays['gains'].dtype == np.dtype('float64')
                    references.append(dict(
                        reference_id=f's4-fixed30-{variant}-w{width}-d{data_seed}-s{seed}',
                        stage=4, cohort='S4_fixed30', panel=None, policy='fixed',
                        variant=variant, width=width, data_seed=data_seed, seed=seed,
                        pretrain_seed=pretrain_seed, epoch=30, grid_index=0,
                        native_id=f's4/{name}/e30', source_name=name,
                        original_fit=saved_fit, history=history,
                        initial_history=initial_history, config=config, decision=None,
                        corpus_path=(raw / 'corpora' / f'adapt-{data_seed}' / 'dataset.pt').relative_to(project_root).as_posix(),
                        canonical_zero=False,
                        source_paths={
                            key: path.relative_to(project_root).as_posix()
                            for key, path in {
                                'sequence': folder / 'sequence_losses.pt',
                                'result': folder / 'result.json',
                                'assignment': folder / 'assignment.pt',
                                'dataset': raw / 'corpora' / f'adapt-{data_seed}' / 'dataset.pt',
                                'dataset_metadata': raw / 'corpora' / f'adapt-{data_seed}' / 'metadata.json',
                                'baseline_metadata': baseline / 'result.json',
                                'selection': raw / 'selection.json',
                            }.items()},
                        source_files=sorted(own), arrays=arrays))
    assert len(references) == 54
    assert {r['source_name'] for r in references} == selected_schedule
    assert len({r['reference_id'] for r in references}) == 54
    assert len({r['native_id'] for r in references}) == 54
    return dict(references=references, source_files=sorted(files))
