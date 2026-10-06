"""Independent, CPU-only reconstruction audit for the frozen Stage 7 study.

No runner generator, configuration builder or metrics helper is called here.
The unchanged historical core.exponent is the sole shared estimator definition.
Intermediate simulation arrays are regenerated in their specified operation
order, allowing byte-for-byte validation rather than tolerance-based matching.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
import resource
import sys
import time
import traceback
sys.dont_write_bytecode = True
import numpy as np
from core import exponent

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LIMIT_SECONDS = 1800
SOURCE_NAMES = ['core.py', 'stage7.py', 'check_stage7.py', 'audit_stage7.py',
                'analyze_stage7.py', 'analysis_checks.py', 'PROTOCOL_STAGE7.md',
                'README.md', 'SYNTHESIS_STAGE4_6.md']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while True:
            block = stream.read(1024*1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def array_hash(values):
    encoded = np.array(values, dtype=np.dtype('<f8')).tobytes(order='C')
    return hashlib.sha256(encoded).hexdigest()


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def condition_schedule():
    """Literal preregistered schedule, independent of stage7.configs()."""
    conditions = []
    for power in (0., .2, 1., 4.):
        for noise_sd in (0., .5, 2., 8.):
            for amplitude in (1., 1e-8, 1e-14):
                conditions.append(dict(family='recovery', truth_p=power, sigma=noise_sd,
                                       scale=amplitude, c=None, control=None))
    for power in (.2, 1.):
        for coefficient in (1., .1, .01, 1e-12, 0., -.01):
            conditions.append(dict(family='cancellation', truth_p=power if coefficient > 0 else None,
                                   sigma=1., scale=1., c=coefficient, control=None,
                                   generator_p=power))
    for label, power in (('upper_boundary', 8.), ('outside_range', 10.),
                         ('uniform_weights', None), ('zero_gain', None), ('negative_gain', None)):
        conditions.append(dict(family='control', truth_p=power, sigma=0.,
                               scale=1., c=None, control=label))
    assert len(conditions) == 65
    return conditions


def independent_draw(size, replicate):
    """Recreate both stdlib streams and the prespecified float64 arithmetic."""
    # Audit() fixes measured replicates to 0..63. Larger indices permit
    # outcome-independent regeneration fixtures on separate streams.
    assert size in [128, 512] and isinstance(replicate, int) and replicate >= 0
    offset = 0 if size == 128 else 10000
    weight_seed, noise_seed = 730000001+offset+replicate, 740000001+offset+replicate
    weights_rng = random.Random(weight_seed)
    normal_rng = random.Random(noise_seed)
    unnormalized = [math.exp(weights_rng.uniform(math.log(.01), math.log(10.)))
                    for _ in range(size)]
    normalizer = sum(unnormalized)/size
    weights = [value/normalizer for value in unnormalized]
    noise = [normal_rng.gauss(0., 1.) for _ in range(size)]
    noise_mean = math.fsum(noise)/size
    centered = [value-noise_mean for value in noise]
    rms = math.sqrt(math.fsum(value*value for value in centered)/size)
    normalized_noise = [value/rms for value in centered]
    assert all(math.isfinite(x) and x > 0 for x in weights)
    assert len(set(weights)) == size
    assert abs(math.fsum(normalized_noise)/size) < 1e-14
    assert abs(math.fsum(value*value for value in normalized_noise)/size-1.) < 1e-14
    return weights, noise, normalized_noise, weight_seed, noise_seed


def independent_gain(weights, noise, centered, condition):
    def power_response(power):
        unnormalized = [math.exp(power*math.log(weight)) for weight in weights]
        denominator = sum(unnormalized)/len(weights)
        return [value/denominator for value in unnormalized]
    family = condition['family']
    if family == 'recovery':
        response = power_response(condition['truth_p'])
        gain = [condition['scale']*(response[i]+condition['sigma']*noise[i])
                for i in range(len(weights))]
    elif family == 'cancellation':
        response = power_response(condition['generator_p'])
        gain = [condition['c']*response[i]+centered[i] for i in range(len(weights))]
    elif condition['control'] == 'uniform_weights':
        return [1.]*len(weights), [1.]*len(weights)
    elif condition['control'] == 'zero_gain':
        gain = [0.]*len(weights)
    elif condition['control'] == 'negative_gain':
        gain = [-value for value in power_response(1.)]
    else:
        gain = power_response(condition['truth_p'])
    assert all(math.isfinite(value) for value in gain)
    return weights, gain


def historical_inventory():
    """The explicitly limited coverage in PROTOCOL_STAGE7, not old full audits."""
    inventory = set()
    outputs = ROOT/'outputs'
    for folder in outputs.iterdir():
        if not folder.is_dir() or not folder.name.startswith('sequence-weighting-') or folder == HERE:
            continue
        for path in folder.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                inventory.add(path.relative_to(ROOT).as_posix())
    for folder in (ROOT/'work/runs').iterdir():
        if not folder.is_dir() or folder.name.startswith('estimator-v08-'):
            continue
        for path in folder.iterdir():
            if path.is_file():
                inventory.add(path.relative_to(ROOT).as_posix())
        for snapshot in ('source', 'analysis-source'):
            for path in (folder/snapshot).rglob('*'):
                if path.is_file():
                    inventory.add(path.relative_to(ROOT).as_posix())
    return inventory


def audit(raw):
    raw = Path(raw)
    start_clock = time.perf_counter()
    start_utc = datetime.now(timezone.utc)
    def budget():
        elapsed_clock = time.perf_counter()-start_clock
        elapsed_utc = (datetime.now(timezone.utc)-start_utc).total_seconds()
        if max(elapsed_clock, elapsed_utc) > LIMIT_SECONDS:
            raise RuntimeError('Prespecified independent CPU audit budget exhausted')
    assert not (raw/'FAILURE.json').exists(), 'Simulation failure is retained and cannot be marked complete'
    complete = read(raw/'COMPLETE.json')
    assert complete['status'] == 'COMPLETE' and complete['fits'] == 8320 and complete['draw_blocks'] == 128
    assert complete['failed_runs'] == [] and complete['training'] is False
    assert 0 < complete['elapsed_seconds'] <= LIMIT_SECONDS
    assert 0 < complete['utc_elapsed_seconds'] <= LIMIT_SECONDS
    assert math.isfinite(complete['peak_rss_mib']) and complete['peak_rss_mib'] > 0
    manifest = read(raw/'source_manifest.json')
    assert set(manifest) == set(SOURCE_NAMES)
    assert {path.name for path in (raw/'source').iterdir() if path.is_file()} == set(SOURCE_NAMES)
    for filename, digest in manifest.items():
        assert file_hash(HERE/filename) == file_hash(raw/'source'/filename) == digest, filename
    assert manifest['core.py'] == file_hash(ROOT/'outputs/sequence-weighting-stage6/core.py')
    freeze, started = read(raw/'FREEZE.json'), read(raw/'START.json')
    assert freeze['status'] == 'PASS' and freeze['outcomes_generated'] is False
    assert freeze['source_sha256'] == manifest and started['source_verified'] is True
    freeze_utc, started_utc, ended_utc = (datetime.fromisoformat(item['utc']) for item in [freeze, started, complete])
    assert freeze_utc < started_utc < ended_utc < start_utc
    timestamp_duration = (ended_utc-started_utc).total_seconds()
    assert 0 < timestamp_duration <= LIMIT_SECONDS
    assert abs(timestamp_duration-complete['utc_elapsed_seconds']) < 1.
    for filename, field in [('config.json', 'config_sha256'), ('CHECKS.json', 'checks_sha256'),
                            ('ANALYSIS_CHECKS.json', 'analysis_checks_sha256'),
                            ('DESIGN_REVIEW.json', 'design_review_sha256')]:
        assert file_hash(raw/filename) == freeze[field]
    checks = read(raw/'CHECKS.json')
    assert checks['status'] == 'PASS' and checks['source_sha256'] == manifest
    analysis_checks = read(raw/'ANALYSIS_CHECKS.json')
    design_review = read(raw/'DESIGN_REVIEW.json')
    assert analysis_checks['status'] == 'PASS' and design_review['status'] == 'PASS'
    review_hashes = design_review['source_sha256']
    assert isinstance(review_hashes, dict) and review_hashes
    assert all(name in manifest and digest == manifest[name] for name, digest in review_hashes.items())
    analysis_hashes = analysis_checks.get('source_sha256', {})
    if 'source_sha256' in analysis_checks:
        assert isinstance(analysis_hashes, dict) and analysis_hashes
        assert all(name in manifest and digest == manifest[name] for name, digest in analysis_hashes.items())
    runtime = read(raw/'runtime.json')
    assert runtime['free_disk_bytes'] >= 1024**3
    assert runtime['numpy'] == np.__version__ and runtime['python'] == sys.version
    conditions = condition_schedule()
    config = read(raw/'config.json')
    assert config == dict(version='v0.8', run_id=raw.name, ns=[128, 512], replicates=64,
                          conditions=conditions, conditions_per_draw=65, draw_blocks=128,
                          planned_fits=8320, budget_seconds=1800, cpu_processes=1,
                          training=False, selection='none; all prespecified cells retained')
    historical = read(raw/'historical_manifest.json')
    assert set(historical) == historical_inventory(), 'Historical coverage inventory changed'
    assert len(historical) == freeze['historical_files']
    for name, digest in historical.items():
        budget()
        assert file_hash(ROOT/name) == digest, f'Historical file changed: {name}'
    print(f'Historical limited-coverage hashes PASS ({len(historical)} files).', flush=True)
    assert file_hash(raw/'results.jsonl') == complete['results_sha256']
    lines = (raw/'results.jsonl').read_text(encoding='utf-8').splitlines()
    assert len(lines) == 8320 and all(lines)
    rows = [json.loads(line) for line in lines]
    assert len({row['id'] for row in rows}) == 8320
    block_manifest = read(raw/'block_manifest.json')
    expected_blocks = {f'blocks/n{size}-r{replicate:03d}.npz' for size in [128, 512] for replicate in range(64)}
    assert set(block_manifest) == expected_blocks
    assert {path.relative_to(raw).as_posix() for path in (raw/'blocks').iterdir()} == expected_blocks
    family_counts, reason_counts = Counter(), Counter()
    positive_guard, defined, lower, upper, offset = 0, 0, 0, 0, 0
    expected_metric_keys = {'p', 'reason', 'objective', 'at_upper_bound', 'at_lower_bound',
                            'total_gain', 'total_gain_fsum', 'negative_gain_fraction',
                            'cancellation_ratio', 'fit_seconds'}
    for size in [128, 512]:
        for replicate in range(64):
            budget()
            block_id = f'n{size}-r{replicate:03d}'
            block_name = f'blocks/{block_id}.npz'
            assert file_hash(raw/block_name) == block_manifest[block_name]
            weights, noise, centered, weight_seed, noise_seed = independent_draw(size, replicate)
            cells = [independent_gain(weights, noise, centered, condition) for condition in conditions]
            regenerated = {'weights': weights, 'noise': noise, 'centered_noise': centered,
                           'gains': [gains for _, gains in cells]}
            with np.load(raw/block_name, allow_pickle=False) as arrays:
                assert set(arrays.files) == set(regenerated)
                loaded = {name: arrays[name] for name in arrays.files}
                for name, values in regenerated.items():
                    expected = np.array(values, dtype='<f8')
                    saved = loaded[name]
                    assert saved.dtype == np.dtype('<f8') and saved.shape == expected.shape
                    assert np.isfinite(saved).all()
                    assert saved.tobytes(order='C') == expected.tobytes(order='C'), f'Array mismatch: {block_id}/{name}'
                for index, (condition, (fit_weights, gains)) in enumerate(zip(conditions, cells)):
                    budget()
                    row = rows[offset]
                    metadata = dict(condition, id=f'{block_id}-c{index:02d}', block_id=block_id,
                                    array_index=index, n=size, replicate=replicate,
                                    seed_weights=weight_seed, seed_noise=noise_seed,
                                    weights_sha256=array_hash(fit_weights), gains_sha256=array_hash(gains))
                    assert set(row) == set(metadata)|expected_metric_keys
                    assert all(row[key] == value for key, value in metadata.items()), row['id']
                    assert array_hash(loaded['gains'][index]) == row['gains_sha256']
                    fitted = exponent(fit_weights, gains)
                    total = sum(gains)
                    total_fsum = math.fsum(gains)
                    absolute = math.fsum(abs(value) for value in gains)
                    expected_reason = ('constant_weights' if max(fit_weights)-min(fit_weights) < 1e-12 else
                                       'nonpositive_total_gain' if total <= 1e-10 else None)
                    assert fitted.get('reason') == expected_reason
                    assert row['p'] == fitted['p'] and row['reason'] == expected_reason
                    assert row['objective'] == fitted.get('objective')
                    assert row['total_gain'] == total and row['total_gain_fsum'] == total_fsum
                    assert row['negative_gain_fraction'] == sum(value < 0 for value in gains)/size
                    assert row['cancellation_ratio'] == (abs(total)/absolute if absolute else None)
                    assert row['at_upper_bound'] == fitted.get('at_upper_bound', False)
                    assert row['at_lower_bound'] == (fitted['p'] is not None and fitted['p'] <= .001)
                    assert math.isfinite(row['fit_seconds']) and row['fit_seconds'] >= 0
                    if row['p'] is None:
                        assert row['objective'] is None and row['reason'] is not None
                        assert row['at_upper_bound'] is False and row['at_lower_bound'] is False
                        reason_counts[row['reason']] += 1
                        positive_guard += int(row['reason'] == 'nonpositive_total_gain' and 0 < total <= 1e-10)
                    else:
                        assert 0 <= row['p'] <= 8 and math.isfinite(row['objective']) and row['objective'] >= 0
                        defined += 1
                        upper += int(row['at_upper_bound'])
                        lower += int(row['at_lower_bound'])
                    family_counts[row['family']] += 1
                    offset += 1
            if (replicate+1) % 16 == 0:
                print(f'AUDIT refits {offset}/8320; n={size}, replicate={replicate}', flush=True)
    assert offset == 8320 and dict(family_counts) == {'recovery': 6144, 'cancellation': 1536, 'control': 640}
    assert defined+sum(reason_counts.values()) == 8320
    for filename, digest in manifest.items():
        assert file_hash(HERE/filename) == file_hash(raw/'source'/filename) == digest
    assert file_hash(raw/'results.jsonl') == complete['results_sha256']
    budget()
    audit_elapsed = time.perf_counter()-start_clock
    audit_utc_elapsed = (datetime.now(timezone.utc)-start_utc).total_seconds()
    assert max(audit_elapsed, audit_utc_elapsed) <= LIMIT_SECONDS
    return dict(status='PASS', utc=datetime.now(timezone.utc).isoformat(), run_id=raw.name,
        fits=8320, draw_blocks=128, independent_replicates_per_condition=64,
        conditions_per_draw=65, family_counts=dict(family_counts), defined_fits=defined,
        undefined_fits=sum(reason_counts.values()), undefined_reasons=dict(reason_counts),
        guard_positive_total_count=positive_guard, upper_boundary_fits=upper, lower_boundary_fits=lower,
        source_sha256=manifest, core_byte_identical_to_stage6=True,
        design_review_source_files_checked=sorted(review_hashes),
        analysis_check_source_files_checked=sorted(analysis_hashes),
        results_sha256=complete['results_sha256'], block_manifest_sha256=file_hash(raw/'block_manifest.json'),
        source_manifest_sha256=file_hash(raw/'source_manifest.json'), config_sha256=freeze['config_sha256'],
        historical_manifest_sha256=file_hash(raw/'historical_manifest.json'),
        historical_files_unchanged=len(historical),
        historical_coverage='All prior versioned output files and raw top-level records/source snapshots; not a fresh full audit of historical model/sequence arrays.',
        simulation_elapsed_seconds=complete['elapsed_seconds'],
        simulation_utc_elapsed_seconds=complete['utc_elapsed_seconds'],
        simulation_timestamp_interval_seconds=timestamp_duration,
        elapsed_seconds=audit_elapsed, utc_elapsed_seconds=audit_utc_elapsed,
        timer_difference_seconds=audit_utc_elapsed-audit_elapsed,
        budget_seconds=LIMIT_SECONDS, both_budget_timers_pass=True,
        peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        failed_rows=[], training=False, gpu_used=False, checks=[
            'exact frozen source/config/checks and freeze before simulations',
            'unchanged Stage6 core estimator; no runner generator/config/metrics helper used',
            'independent complete literal condition/draw schedule and fresh separate RNG streams',
            'all base weights, Gaussian/centered noise and gain arrays regenerated byte for byte',
            'all NPZ file hashes and little-endian float64 row-array hashes verified',
            'all 8320 original-estimator refits, guard reasons, signed totals and diagnostics reconstructed',
            'paired weights/noise within each base draw and all missing/null targets preserved',
            '128 independent base draws, 64 replicates per condition; no pooling conditions as independent draws',
            'exact limited historical coverage inventory and its file hashes unchanged',
            'simulation and independent audit both satisfy their own 1800-second dual-clock ceiling'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    assert args.run_id and Path(args.run_id).name == args.run_id
    assert '/' not in args.run_id and '\\' not in args.run_id and args.run_id not in ['.', '..']
    raw = ROOT/'work/runs'/args.run_id
    assert raw.resolve().parent == (ROOT/'work/runs').resolve()
    assert not (raw/'AUDIT.json').exists() and not (raw/'AUDIT_FAILURE.json').exists(), 'Refuse audit overwrite/retry'
    try:
        evidence = audit(raw)
        write_new(raw/'AUDIT.json', evidence)
        print(json.dumps(dict(status=evidence['status'], fits=evidence['fits'], draw_blocks=evidence['draw_blocks'],
                              elapsed_seconds=evidence['elapsed_seconds'])), flush=True)
    except BaseException as exc:
        write_new(raw/'AUDIT_FAILURE.json', dict(status='FAILED', utc=datetime.now(timezone.utc).isoformat(),
                                                error=repr(exc), traceback=traceback.format_exc(), no_implicit_retry=True))
        raise


if __name__ == '__main__':
    main()
