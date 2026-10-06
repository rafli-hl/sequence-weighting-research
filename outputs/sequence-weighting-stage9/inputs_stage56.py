"""Read retained Stage 5/6 primary selections without fitting any estimator.

Selection is entirely design based: R, random arm, M/U, all confirmation cells,
and every Stage 6 tuning panel.  Repeated policy references retain a common
native_id; byte-level numerical deduplication belongs to the Stage 9 caller.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import random
from pathlib import Path

import torch


DESIGNS = {
    5: dict(run='utility-v06-20260929-01',
            report='results-utility-v06-20260929-01-r1',
            corpora=((52919, 96201), (55049, 96202), (57163, 96203)),
            seeds=(801, 802, 803), panels=(None,), references=54, native=54),
    6: dict(run='stability-v07-20260929-01',
            report='results-stability-v07-20260929-01',
            corpora=((61103, 97201), (61211, 97202), (61319, 97203)),
            seeds=(1001, 1002, 1003), panels=('P1', 'P2', 'P3', 'P4'),
            references=216, native=99),
}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tensor_hash(t):
    h = hashlib.sha256()
    h.update(str((tuple(t.shape), str(t.dtype))).encode())
    h.update(t.contiguous().numpy().tobytes())
    return h.hexdigest()


def frozen_weights(engine_path, expected_sha):
    """Execute only the historical pure weights function from verified source."""
    assert sha(engine_path) == expected_sha
    tree = ast.parse(engine_path.read_text(encoding='utf-8'))
    functions = [x for x in tree.body if isinstance(x, ast.FunctionDef)
                 and x.name == 'weights']
    assert len(functions) == 1
    module = ast.Module(body=[functions[0]], type_ignores=[])
    namespace = dict(torch=torch, random=random, math=math)
    exec(compile(module, str(engine_path), 'exec'), namespace)
    return namespace['weights']


def collect(project_root: Path) -> dict:
    project_root = Path(project_root).resolve()
    all_references = []
    all_files = set()

    def relative(path):
        path = Path(path).resolve()
        assert path.is_file(), str(path)
        return path.relative_to(project_root).as_posix()

    for stage, design in DESIGNS.items():
        raw = project_root / 'work' / 'runs' / design['run']
        report = (project_root / 'outputs' / f'sequence-weighting-stage{stage}'
                  / design['report'])
        selection = read(raw / 'selection.json')
        selection_hash = sha(raw / 'selection.json')
        raw_manifest = read(report / 'raw-manifest.json')
        source_manifest = read(raw / 'source_manifest.json')
        analysis_manifest = read(raw / 'analysis_source_manifest.json')
        global_files = {relative(raw / name) for name in (
            'selection.json', 'source_manifest.json', 'analysis_source_manifest.json',
            'COMPLETE.json', 'ANALYSIS_CHECKS.json', 'ANALYSIS_FREEZE.json',
            'DESIGN_REVIEW.json', 'VALIDATION.json', 'SELECTION_CHECKS.json')}
        for dirname, manifest in [('source', source_manifest),
                                  ('analysis-source', analysis_manifest)]:
            for name, digest in manifest.items():
                path = raw / dirname / name
                assert sha(path) == digest, str(path)
                global_files.add(relative(path))
        for name in ('AUDIT.json', 'ANALYSIS_SOURCE_AUDIT.json',
                     'DIAGNOSTIC_AUDIT.json', 'GATE_AUDIT.json',
                     'diagnostics.json', 'diagnostics.csv', 'policy-cells.csv',
                     'raw-manifest.json', 'analysis-provenance.json'):
            global_files.add(relative(report / name))
        assert read(report / 'AUDIT.json')['status'] == 'PASS'
        assert read(report / 'AUDIT.json')['selection_sha256'] == selection_hash
        diagnostics = {(x['name'], x['epoch']): x
                       for x in read(report / 'diagnostics.json')['all']}
        historical_weights = frozen_weights(raw / 'source' / 'engine.py',
                                            source_manifest['engine.py'])
        cache = {}

        def load(path):
            if path not in cache:
                cache[path] = torch.load(path, map_location='cpu', weights_only=True)
            return cache[path]

        stage_references = []
        for panel in design['panels']:
            decisions = selection['decisions'] if panel is None else selection['decisions'][panel]
            for variant in ('M', 'U'):
                for width in (64, 128, 256):
                    decision = decisions['R'][variant][str(width)]
                    epoch = decision['epoch']
                    grid = decision['grid_index']
                    assert (epoch == 0) == (grid is None)
                    for data_seed, pretrain_seed in design['corpora']:
                        for seed in design['seeds']:
                            initial_name = f'{variant}-w{width}-d{data_seed}-s{seed}'
                            initial_folder = raw / 'initial-evaluations' / initial_name
                            initial_result = read(initial_folder / 'result.json')
                            canonical = load(initial_folder / 'sequence_losses.pt')
                            assert initial_result['selection_sha256'] == selection_hash
                            assert initial_result['source_sha256'] == source_manifest
                            assert initial_result['pretrain_seed'] == pretrain_seed
                            assert sha(initial_folder / 'sequence_losses.pt') == initial_result['sequence_file_sha256']
                            files = set(global_files)
                            files.update(relative(initial_folder / name)
                                         for name in ('result.json', 'sequence_losses.pt'))
                            corpus_folder = raw / 'corpora' / f'adapt-{data_seed}'
                            corpus_path = relative(corpus_folder / 'dataset.pt')
                            files.update((corpus_path, relative(corpus_folder / 'metadata.json')))
                            metadata = read(corpus_folder / 'metadata.json')
                            assert metadata['tensor_sha256'] == initial_result['data_sha256']
                            assert sha(corpus_folder / 'dataset.pt') == metadata['file_sha256']
                            baseline = raw / 'baselines' / f'{variant}-w{width}-s{seed}-d{pretrain_seed}'
                            files.add(relative(baseline / 'result.json'))
                            initial_history = dict(epoch=0,
                                **copy.deepcopy(initial_result['metrics']),
                                p_star=dict(p=None, reason='no_adaptation'),
                                total_gain=0., negative_gain_fraction=0.)
                            donor_path = None
                            if epoch == 0:
                                name = initial_name
                                initial_loss = current_loss = canonical['train']['loss']
                                donors = sorted((raw / 'runs').glob(
                                    f'confirm-M-w{width}-d{data_seed}-s{seed}-g*-random/assignment.pt'))
                                assert donors
                                donor = donors[0]
                                donor_path = relative(donor)
                                assignment = load(donor)
                                donor_config = read(donor.parent / 'config.json')
                                assert donor_config['selection_sha256'] == selection_hash
                                assert donor_config['source_sha256'] == source_manifest
                                weights = assignment['weights']
                                assert tensor_hash(weights) == donor_config['weight_sha256']
                                assert tensor_hash(assignment['orders']) == donor_config['batch_order_sha256']
                                files.update((donor_path, relative(donor.parent / 'config.json')))
                                config = dict(copy.deepcopy(initial_result), phase='confirm',
                                    arm='random', grid_index=None, lr=None, wd=None, clip=None,
                                    epochs=0, canonical_zero=True, weight_donor=donor_path,
                                    weight_sha256=tensor_hash(weights))
                                history = copy.deepcopy(initial_history)
                                diagnostic = diagnostics[(name + '-random', 0)]
                            else:
                                name = f'confirm-{variant}-w{width}-d{data_seed}-s{seed}-g{grid:02d}-random'
                                folder = raw / 'runs' / name
                                result = read(folder / 'result.json')
                                config = read(folder / 'config.json')
                                histories = read(folder / 'history.json')
                                assert result['status'] == 'complete'
                                assert result['config'] == config and result['history'] == histories
                                assert config['source_sha256'] == source_manifest
                                assert config['selection_sha256'] == selection_hash
                                assert config['data_sha256'] == metadata['tensor_sha256']
                                assert config['pretrain_seed'] == pretrain_seed
                                records = load(folder / 'sequence_losses.pt')
                                weights = records['weights']
                                assignment = load(folder / 'assignment.pt')
                                assert torch.equal(weights, assignment['weights'])
                                assert tensor_hash(weights) == config['weight_sha256']
                                assert tensor_hash(assignment['orders']) == config['batch_order_sha256']
                                checkpoints = {cp['epoch']: cp for cp in records['checkpoints']}
                                for split in ('train', 'validation', 'test'):
                                    for field, tensor in canonical[split].items():
                                        assert torch.equal(tensor, checkpoints[0][split][field])
                                initial_loss = checkpoints[0]['train']['loss']
                                current_loss = checkpoints[epoch]['train']['loss']
                                history = next(h for h in histories if h['epoch'] == epoch)
                                assert histories[0] == initial_history
                                initial_history = histories[0]
                                assert config['lr'] == decision['lr'] and config['wd'] == decision['wd']
                                files.update(relative(folder / filename) for filename in (
                                    'result.json', 'config.json', 'history.json', 'assignment.pt',
                                    'sequence_losses.pt', 'epoch_stats.json'))
                                diagnostic = diagnostics[(name, epoch)]
                                assert diagnostic['primary'] == history['p_star']
                            assert torch.equal(weights, historical_weights(seed, 'random'))
                            assert weights.dtype == initial_loss.dtype == current_loss.dtype == torch.float32
                            assert weights.shape == initial_loss.shape == current_loss.shape == (512,)
                            gains = (initial_loss - current_loss).double()
                            cohort = f'S{stage}_R' if panel is None else f'S6_{panel}_R'
                            reference_id = f's{stage}/{panel or "single"}/{variant}/w{width}/d{data_seed}/s{seed}/R/random'
                            selected_folder = initial_folder if epoch == 0 else folder
                            source_paths = dict(
                                sequence=relative(selected_folder / 'sequence_losses.pt'),
                                result=relative(selected_folder / 'result.json'),
                                assignment=donor_path if epoch == 0 else relative(folder / 'assignment.pt'),
                                dataset=corpus_path,
                                dataset_metadata=relative(corpus_folder / 'metadata.json'),
                                baseline_metadata=relative(baseline / 'result.json'),
                                selection=relative(raw / 'selection.json'))
                            reference = dict(reference_id=reference_id, stage=stage, cohort=cohort,
                                panel=panel, policy='R', arm='random', variant=variant, width=width,
                                data_seed=data_seed, seed=seed, pretrain_seed=pretrain_seed,
                                epoch=epoch, grid_index=grid, native_id=f's{stage}/{name}/e{epoch:02d}',
                                source_name=name, original_fit=copy.deepcopy(history['p_star']),
                                history=copy.deepcopy(history), initial_history=copy.deepcopy(initial_history),
                                config=copy.deepcopy(config), decision=copy.deepcopy(decision),
                                corpus_path=corpus_path, source_files=sorted(files),
                                source_paths=source_paths, canonical_zero=epoch == 0,
                                weight_donor=donor_path,
                                weight_provenance=dict(method='saved_tensor_verified_against_frozen_pure_weights_function',
                                    engine_path=relative(raw / 'source' / 'engine.py'),
                                    engine_sha256=source_manifest['engine.py']),
                                diagnostics=copy.deepcopy(diagnostic),
                                arrays=dict(weights=weights.numpy().copy(),
                                    initial_loss=initial_loss.numpy().copy(),
                                    current_loss=current_loss.numpy().copy(), gains=gains.numpy().copy()))
                            stage_references.append(reference)
                            all_files.update(files)
        assert len(stage_references) == design['references']
        assert len({r['native_id'] for r in stage_references}) == design['native']
        # Bind every retained raw input to its original completed report, not
        # merely to a newly calculated hash of the current file. Deduplicate
        # checks because panel aliases deliberately reuse native checkpoints.
        stage_files = {p for r in stage_references for p in r['source_files']}
        for relative_path in sorted(stage_files):
            path = project_root / relative_path
            if path.is_relative_to(raw):
                key = path.relative_to(raw).as_posix()
                assert key in raw_manifest, ('missing historical file hash', stage, key)
                assert sha(path) == raw_manifest[key], ('historical file hash mismatch', stage, key)
        all_references.extend(stage_references)
    assert len(all_references) == len({r['reference_id'] for r in all_references}) == 270
    return dict(references=all_references, source_files=sorted(all_files))
