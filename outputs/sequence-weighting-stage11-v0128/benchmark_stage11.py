"""Bounded engineering-only CUDA/resource fixture; never research seed selection."""
import argparse
import gc
import hashlib
import io
import json
import math
import shutil
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PROCESS_START = time.perf_counter()
PROCESS_UTC = datetime.now(timezone.utc)
sys.dont_write_bytecode = True
import torch

from config import CAPS, PARAMETERS, ROOT, TRAIN_SECONDS, NEW_STORAGE_BYTES, FREE_START_BYTES
from engine import (paired_data, pre_data, weights, orders, train_epoch, evaluate,
                    pretraining_objective, cpu_state, tensor_hash, diagnostics)
from model import Model

HERE = Path(__file__).resolve().parent
FIXTURE_DATA = 1700201
FIXTURE_PRETRAIN = 1700203
FIXTURE_MODEL = 1700207
SOURCE_NAMES = ['config.py', 'core.py', 'model.py', 'engine.py', 'benchmark_stage11.py']


def elapsed():
    return max(time.perf_counter() - PROCESS_START, (datetime.now(timezone.utc) - PROCESS_UTC).total_seconds())


def check_budget(limit):
    if elapsed() > limit:
        raise TimeoutError(f'Engineering preparation budget exhausted at {elapsed():.3f}s /{limit}s')


def timed(operation, limit, cuda=False):
    check_budget(limit)
    if cuda:
        torch.cuda.synchronize()
    start = time.perf_counter()
    result = operation()
    if cuda:
        torch.cuda.synchronize()
    duration = time.perf_counter() - start
    check_budget(limit)
    return result, duration


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save_json(path, value):
    with path.open('w', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def u_steps(model, optimizer, dataset, batch_order, count=16):
    model.train()
    for ids in batch_order[:count * 32].split(32):
        tokens, kinds = (value[ids].cuda() for value in dataset)
        objective = pretraining_objective(model(tokens[:, :-1]), tokens, kinds)
        optimizer.zero_grad(set_to_none=True)
        objective.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 5.)
        if not torch.isfinite(norm):
            raise FloatingPointError('Nonfinite fixture gradient')
        optimizer.step()
        float(norm)


def synthetic_records(n):
    component = torch.full((n, 3), 3., dtype=torch.float32)
    return {'loss': component.mean(1), 'component_loss': component,
            'component_accuracy': torch.zeros(n, 3)}


def run(output, artifact_dir, limit):
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; no CPU benchmark fallback')
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    artifact_dir.mkdir(parents=True, exist_ok=False)
    free_before = shutil.disk_usage(ROOT).free
    (paired, _), data_seconds = timed(lambda: paired_data(FIXTURE_DATA), limit)
    (pre, _), pre_data_seconds = timed(lambda: pre_data(FIXTURE_PRETRAIN), limit)
    ds = paired['G16']
    w, order = weights(FIXTURE_MODEL, 'random'), orders(FIXTURE_MODEL, epochs=2)

    # Known construction measures diagnostics cost without any learned-model loss.
    synthetic_initial = synthetic_records(512)
    power = w.pow(.7); power /= power.max()
    component_gain = power[:, None] * torch.tensor([.08, .12, .16])[None, :]
    synthetic_current = dict(synthetic_initial)
    synthetic_current['component_loss'] = synthetic_initial['component_loss'] - component_gain
    synthetic_current['loss'] = synthetic_current['component_loss'].mean(1)
    diag, diagnostic_seconds = timed(lambda: diagnostics(w, synthetic_initial, synthetic_current), limit)
    assert all(diag['component_fits'][name]['p'] is not None for name in ('shared', 'group', 'instance'))
    history = [dict(epoch=epoch, diagnostic=diag, train={'loss': 3.}, validation={'loss': 3.},
                    test={'loss': 3.}, fit=diag['fit'], group_fit=diag['group_fit'])
               for epoch in (1, 3, 5, 10, 20, 30)]
    history_path = artifact_dir / 'fixture-history.json'
    _, history_seconds = timed(lambda: save_json(history_path, history), limit)
    # Independent tensor objects prevent torch.save aliasing from underestimating bytes.
    arrays = [dict(epoch=epoch, train=synthetic_records(512), validation=synthetic_records(256),
                   test=synthetic_records(512)) for epoch in (1, 3, 5, 10, 20, 30)]
    arrays_path = artifact_dir / 'fixture-arrays.pt'
    _, arrays_seconds = timed(lambda: torch.save(arrays, arrays_path), limit)
    zip_path = artifact_dir / 'fixture-nonmodel.zip'
    def archive_fixture():
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(history_path, history_path.name)
            archive.write(arrays_path, arrays_path.name)
        with zipfile.ZipFile(zip_path) as archive:
            if archive.testzip() is not None:
                raise AssertionError('Fixture archive CRC failure')
    _, archive_seconds = timed(archive_fixture, limit)

    capacities = []
    for width, layers in CAPS:
        check_budget(limit)
        torch.manual_seed(FIXTURE_MODEL)
        torch.cuda.manual_seed_all(FIXTURE_MODEL)
        model = Model(width, layers, 40).cuda()
        assert sum(p.numel() for p in model.parameters()) == PARAMETERS[width]
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=.1)
        torch.cuda.reset_peak_memory_stats()
        # Warmup includes optimizer-state allocation; no reported research outcome.
        train_epoch(model, optimizer, ds['train'], w, order[0][:32], 1.)
        torch.cuda.synchronize()
        _, adaptation_epoch_seconds = timed(lambda: train_epoch(model, optimizer, ds['train'], w, order[1], 1.), limit, True)
        pre_order = orders(FIXTURE_MODEL, n=2048, epochs=1)[0]
        _, pretraining_batch_sample_seconds = timed(lambda: u_steps(model, optimizer, pre['train'], pre_order, 16), limit, True)
        evaluation = {}
        for size, dataset in [(256, ds['validation']), (512, ds['train']), (2048, pre['train'])]:
            _, seconds = timed(lambda dataset=dataset: evaluate(model, dataset), limit, True)
            evaluation[str(size)] = seconds
        state, state_copy_seconds = timed(lambda: cpu_state(model), limit, True)
        _, state_hash_seconds = timed(lambda: {key: tensor_hash(value) for key, value in cpu_state(model).items()}, limit, True)
        state_path = artifact_dir / f'fixture-w{width}.pt'
        _, state_save_seconds = timed(lambda: torch.save(state, state_path), limit)
        _, state_file_hash_seconds = timed(lambda: file_sha(state_path), limit)
        capacities.append(dict(width=width, layers=layers, parameters=PARAMETERS[width],
            adaptation_epoch_seconds=adaptation_epoch_seconds,
            adaptation_step_seconds=adaptation_epoch_seconds / 16,
            pretraining_step_seconds=pretraining_batch_sample_seconds / 16,
            evaluate_seconds=evaluation, state_copy_seconds=state_copy_seconds,
            state_hash_seconds=state_hash_seconds, state_save_seconds=state_save_seconds,
            state_file_hash_seconds=state_file_hash_seconds, serialized_state_bytes=state_path.stat().st_size,
            peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
            peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20))
        del model, optimizer, state
        gc.collect()
        torch.cuda.empty_cache()

    # Per-capacity maxima:104 trajectories,12 U pretrains,24 canonical initials,
    # 80 confirmation trajectories,20 confirmation initial tests.
    components = {'adaptation': 0., 'pretraining': 0., 'evaluation': 0.,
                  'model_state_and_file_io': 0.}
    state_bytes = 0
    for sample in capacities:
        components['adaptation'] += sample['adaptation_step_seconds'] * (104 * 30 * 16)
        components['pretraining'] += sample['pretraining_step_seconds'] * (12 * 4 * 64)
        eval_time = sample['evaluate_seconds']
        components['evaluation'] += (104 * 6 + 24) * (eval_time['512'] + eval_time['256'])
        components['evaluation'] += (80 * 6 + 20) * eval_time['512']
        components['evaluation'] += 12 * 4 * (eval_time['2048'] + eval_time['256'])
        # Includes624 declared checkpoints,24 initial binds,24 cold/pretrained,
        # and104 repeated checkpoint loads/hash validations per capacity.
        components['model_state_and_file_io'] += 776 * sample['state_hash_seconds']
        components['model_state_and_file_io'] += 216 * (sample['state_copy_seconds'] + sample['state_save_seconds'])
        components['model_state_and_file_io'] += 424 * sample['state_file_hash_seconds']
        state_bytes += 216 * sample['serialized_state_bytes']
    components['cpu_diagnostics'] = 1872 * diagnostic_seconds
    # Use six full-history/full-array writes per trajectory: conservative vs
    # actual growing histories; add36 pretrain rewrites with dataset size factor2.
    components['json_and_array_serialization'] = (312 * 6 + 36 * 4 * 2) * (history_seconds + arrays_seconds)
    components['data_and_selection_misc'] = 7 * (data_seconds + pre_data_seconds) + 60.
    measured_projection_seconds = sum(components.values())
    projected_training_seconds = measured_projection_seconds * 1.25

    # Full fixture history contains four512-residual vectors for every checkpoint.
    # Reserve40% for varying number formatting/metrics and double array file size
    # to cover pretraining, baseline, tensor container and ancillary metadata.
    raw_history_bytes = math.ceil(312 * history_path.stat().st_size * 1.4)
    raw_array_bytes = math.ceil(312 * arrays_path.stat().st_size * 2.)
    other_raw_reserve = 64 * 2**20
    archive_reserve = 256 * 2**20
    new_storage_bytes = state_bytes + raw_history_bytes + raw_array_bytes + other_raw_reserve + archive_reserve
    gates = {'time': projected_training_seconds <= TRAIN_SECONDS,
             'storage': new_storage_bytes <= NEW_STORAGE_BYTES,
             'free_start': free_before >= FREE_START_BYTES,
             'engineering_budget': elapsed() <= limit}
    return dict(status='PASS' if all(gates.values()) else 'RESOURCE_GATE_FAIL', gates=gates,
        capacities=capacities, projection_safety_multiplier=1.25,
        projection_components_seconds=components, projected_training_seconds=projected_training_seconds,
        measured_projection_seconds=measured_projection_seconds,
        storage=dict(serialized_model_bytes=state_bytes, raw_history_bytes=raw_history_bytes,
                     raw_array_bytes=raw_array_bytes, other_raw_reserve_bytes=other_raw_reserve,
                     archive_reserve_bytes=archive_reserve, total_bytes=new_storage_bytes,
                     ceiling_bytes=NEW_STORAGE_BYTES, free_bytes_before=free_before),
        archive_reserve_bytes=archive_reserve,
        cpu_fixture=dict(diagnostic_seconds=diagnostic_seconds, history_json_seconds=history_seconds,
                         arrays_save_seconds=arrays_seconds, archive_crc_seconds=archive_seconds,
                         history_bytes=history_path.stat().st_size, arrays_bytes=arrays_path.stat().st_size,
                         fixture_archive_bytes=zip_path.stat().st_size),
        schedule_counts=dict(tuning_trajectories=72, confirmation_trajectories_maximum=240,
            adaptation_updates_maximum=149760, pretraining_updates=9216, pretrained_models=36,
            adaptation_train_evaluations=1944, adaptation_validation_evaluations=1944,
            pretraining_train_evaluations=144, pretraining_validation_evaluations=144,
            confirmation_test_evaluations_maximum=1500, numerical_diagnostic_calls_maximum=1872,
            required_model_binaries_maximum=648),
        gpu=torch.cuda.get_device_name(0), torch_version=torch.__version__,
        fixture_only=True, research_training=False, research_seed_or_outcome_used=False,
        benchmark_seed_selection='Fixed engineering seeds, independent of config tuning/confirmation seeds',
        fixture_seeds={'data': FIXTURE_DATA, 'pretraining': FIXTURE_PRETRAIN, 'model': FIXTURE_MODEL},
        automatic_retry=False, artifact_directory=str(artifact_dir))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--work-dir', type=Path)
    parser.add_argument('--budget-seconds', type=float, default=120.)
    args = parser.parse_args()
    if not 0 < args.budget_seconds <= 300:
        raise ValueError('Engineering budget must be within(0,300]seconds')
    if args.output.exists():
        raise FileExistsError(args.output)
    artifact_dir = args.work_dir or args.output.parent / (args.output.stem + '-artifacts')
    try:
        result = run(args.output, artifact_dir, args.budget_seconds)
    except Exception:
        result = {'status': 'FAIL', 'error': traceback.format_exc(), 'fixture_only': True,
                  'research_training': False, 'artifact_directory': str(artifact_dir), 'automatic_retry': False}
    result.update(utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=elapsed(),
                  engineering_budget_seconds=args.budget_seconds,
                  source_sha256={name: file_sha(HERE / name) for name in SOURCE_NAMES})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps({key: result.get(key) for key in ('status', 'elapsed_seconds', 'projected_training_seconds', 'gates')}))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
