"""Stage 7 v0.8: frozen local CPU estimator Monte Carlo; no model training."""
import argparse
import hashlib
import json
import math
import os
import platform
import random
import resource
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
import numpy as np
from core import exponent

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES = ['core.py', 'stage7.py', 'check_stage7.py', 'audit_stage7.py',
           'analyze_stage7.py', 'analysis_checks.py', 'PROTOCOL_STAGE7.md',
           'README.md', 'SYNTHESIS_STAGE4_6.md']
RUN_ID = 'estimator-v08-20260930-01'
NS = [128, 512]
REPLICATES = 64
BUDGET_SECONDS = 1800


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def array_sha(values):
    return hashlib.sha256(np.asarray(values, dtype='<f8').tobytes()).hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def configs():
    out = []
    for p in [0., .2, 1., 4.]:
        for sigma in [0., .5, 2., 8.]:
            for scale in [1., 1e-8, 1e-14]:
                out.append(dict(family='recovery', truth_p=p, sigma=sigma,
                                scale=scale, c=None, control=None))
    for p in [.2, 1.]:
        for c in [1., .1, .01, 1e-12, 0., -.01]:
            out.append(dict(family='cancellation', truth_p=p if c > 0 else None,
                            sigma=1., scale=1., c=c, control=None, generator_p=p))
    for control, p in [('upper_boundary', 8.), ('outside_range', 10.),
                       ('uniform_weights', None), ('zero_gain', None),
                       ('negative_gain', None)]:
        out.append(dict(family='control', truth_p=p, sigma=0., scale=1.,
                        c=None, control=control))
    return out


def draw(n, replicate):
    ni = NS.index(n)
    seed_weights = 730000001 + ni * 10000 + replicate
    seed_noise = 740000001 + ni * 10000 + replicate
    rw, rz = random.Random(seed_weights), random.Random(seed_noise)
    weights = [math.exp(rw.uniform(math.log(.01), math.log(10.))) for _ in range(n)]
    wm = sum(weights) / n
    weights = [v / wm for v in weights]
    z = [rz.gauss(0., 1.) for _ in range(n)]
    zm = math.fsum(z) / n
    centered = [v - zm for v in z]
    rms = math.sqrt(math.fsum(v*v for v in centered) / n)
    centered = [v / rms for v in centered]
    return weights, z, centered, seed_weights, seed_noise


def response(weights, p):
    q = [math.exp(p * math.log(w)) for w in weights]
    qm = sum(q) / len(q)
    return [v / qm for v in q]


def generate(weights, z, centered, config):
    c = config
    p = c.get('generator_p', c['truth_p'])
    if c['family'] == 'recovery':
        q = response(weights, p)
        return weights, [c['scale'] * (v + c['sigma'] * e) for v, e in zip(q, z)]
    if c['family'] == 'cancellation':
        q = response(weights, p)
        return weights, [c['c'] * v + e for v, e in zip(q, centered)]
    if c['control'] == 'uniform_weights':
        return [1.] * len(weights), [1.] * len(weights)
    if c['control'] == 'zero_gain':
        return weights, [0.] * len(weights)
    if c['control'] == 'negative_gain':
        return weights, [-v for v in response(weights, 1.)]
    return weights, response(weights, p)


def metrics(weights, gains):
    t = time.perf_counter()
    fitted = exponent(weights, gains)
    elapsed = time.perf_counter() - t
    total = sum(gains)
    absolute = math.fsum(abs(v) for v in gains)
    return dict(p=fitted['p'], reason=fitted.get('reason'),
                objective=fitted.get('objective'), at_upper_bound=fitted.get('at_upper_bound', False),
                at_lower_bound=fitted['p'] is not None and fitted['p'] <= .001,
                total_gain=total, total_gain_fsum=math.fsum(gains),
                negative_gain_fraction=sum(v < 0 for v in gains)/len(gains),
                cancellation_ratio=abs(total)/absolute if absolute else None,
                fit_seconds=elapsed)


def historical_paths():
    # Explicit coverage: all versioned output artifacts, plus raw top-level
    # records/source snapshots. Full historical model/sequence arrays are read-only
    # but are not rehashed by this CPU estimator study.
    paths = []
    for folder in sorted((ROOT / 'outputs').glob('sequence-weighting-*')):
        if folder == HERE:
            continue
        paths.extend(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for folder in sorted((ROOT / 'work' / 'runs').iterdir()):
        if not folder.is_dir() or folder.name.startswith('estimator-v08-'):
            continue
        paths.extend(p for p in folder.iterdir() if p.is_file())
        for name in ['source', 'analysis-source']:
            if (folder / name).exists():
                paths.extend(p for p in (folder / name).rglob('*') if p.is_file())
    return sorted(set(paths))


def source_check(raw):
    manifest = read(raw / 'source_manifest.json')
    for name, digest in manifest.items():
        assert sha(HERE / name) == digest, name
        assert sha(raw / 'source' / name) == digest, name
    assert manifest['core.py'] == sha(ROOT / 'outputs/sequence-weighting-stage6/core.py')
    return manifest


def prepare(raw, checks_path, analysis_checks_path, review_path):
    assert not raw.exists(), 'Refusing to overwrite an existing run'
    for path in [checks_path, analysis_checks_path, review_path]:
        assert read(path)['status'] == 'PASS', str(path)
    manifest = {name: sha(HERE / name) for name in SOURCES}
    for path in [analysis_checks_path, review_path]:
        scoped_hashes = read(path).get('source_sha256')
        assert scoped_hashes, 'Review/check evidence must be bound to source hashes'
        for name, digest in scoped_hashes.items():
            assert manifest[name] == digest, f'Stale scoped review: {name}'
    checks = read(checks_path)
    assert checks['source_sha256'] == manifest, 'Checks must match all frozen source'
    raw.mkdir(parents=True)
    (raw / 'source').mkdir()
    for name in SOURCES:
        shutil.copy2(HERE / name, raw / 'source' / name)
    write(raw / 'source_manifest.json', manifest)
    for path, name in [(checks_path, 'CHECKS.json'), (analysis_checks_path, 'ANALYSIS_CHECKS.json'),
                       (review_path, 'DESIGN_REVIEW.json')]:
        shutil.copy2(path, raw / name)
    config = dict(version='v0.8', run_id=raw.name, ns=NS, replicates=REPLICATES,
                  conditions=configs(), conditions_per_draw=65, draw_blocks=128,
                  planned_fits=8320, budget_seconds=BUDGET_SECONDS,
                  cpu_processes=1, training=False, selection='none; all prespecified cells retained')
    write(raw / 'config.json', config)
    history = {p.relative_to(ROOT).as_posix(): sha(p) for p in historical_paths()}
    write(raw / 'historical_manifest.json', history)
    lock = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], check=True, capture_output=True, text=True)
    (raw / 'environment-lock.txt').write_text(lock.stdout, encoding='utf-8')
    write(raw / 'runtime.json', dict(utc=utc(), python=sys.version, numpy=np.__version__,
                                   platform=platform.platform(), executable=sys.executable,
                                   cpu_count=os.cpu_count(), free_disk_bytes=shutil.disk_usage(ROOT).free))
    assert shutil.disk_usage(ROOT).free >= 1024**3
    write(raw / 'FREEZE.json', dict(status='PASS', utc=utc(), source_sha256=manifest,
                                  config_sha256=sha(raw / 'config.json'),
                                  checks_sha256=sha(raw / 'CHECKS.json'),
                                  analysis_checks_sha256=sha(raw / 'ANALYSIS_CHECKS.json'),
                                  design_review_sha256=sha(raw / 'DESIGN_REVIEW.json'),
                                  historical_files=len(history), outcomes_generated=False))
    print(json.dumps(dict(status='FROZEN', raw=str(raw), historical_files=len(history))), flush=True)


def experiment(raw):
    source_check(raw)
    assert read(raw / 'FREEZE.json')['config_sha256'] == sha(raw / 'config.json')
    assert read(raw / 'config.json')['conditions'] == configs()
    assert not (raw / 'START.json').exists(), 'No implicit resume or overwrite'
    start_clock, start_utc = time.perf_counter(), datetime.now(timezone.utc)
    write(raw / 'START.json', dict(utc=start_utc.isoformat(), source_verified=True))
    (raw / 'blocks').mkdir()
    count, block_manifest = 0, {}
    try:
        with (raw / 'results.jsonl').open('x', encoding='utf-8') as out:
            for n in NS:
                for replicate in range(REPLICATES):
                    block_id = f'n{n}-r{replicate:03d}'
                    w, z, centered, sw, sn = draw(n, replicate)
                    cells = [generate(w, z, centered, c) for c in configs()]
                    block_path = raw / 'blocks' / f'{block_id}.npz'
                    np.savez_compressed(block_path, weights=np.asarray(w, dtype='<f8'),
                                        noise=np.asarray(z, dtype='<f8'), centered_noise=np.asarray(centered, dtype='<f8'),
                                        gains=np.asarray([g for _, g in cells], dtype='<f8'))
                    block_manifest[block_path.relative_to(raw).as_posix()] = sha(block_path)
                    for index, (config, (weights, gains)) in enumerate(zip(configs(), cells)):
                        elapsed = time.perf_counter() - start_clock
                        utc_elapsed = (datetime.now(timezone.utc) - start_utc).total_seconds()
                        if max(elapsed, utc_elapsed) > BUDGET_SECONDS:
                            raise RuntimeError('Prespecified CPU budget reached; partial data preserved')
                        row = dict(config, id=f'{block_id}-c{index:02d}', block_id=block_id,
                                   array_index=index, n=n, replicate=replicate,
                                   seed_weights=sw, seed_noise=sn,
                                   weights_sha256=array_sha(weights), gains_sha256=array_sha(gains),
                                   **metrics(weights, gains))
                        out.write(json.dumps(row, allow_nan=False) + '\n')
                        out.flush()
                        count += 1
                    if (replicate + 1) % 8 == 0:
                        print(json.dumps(dict(fits=count, planned=8320, n=n, replicate=replicate,
                                              elapsed_seconds=time.perf_counter()-start_clock)), flush=True)
        source_check(raw)
        write(raw / 'block_manifest.json', block_manifest)
        results_digest = sha(raw / 'results.jsonl')
        elapsed = time.perf_counter() - start_clock
        utc_elapsed = (datetime.now(timezone.utc)-start_utc).total_seconds()
        if max(elapsed, utc_elapsed) > BUDGET_SECONDS:
            raise RuntimeError('Final CPU budget check failed; partial data preserved')
        write(raw / 'COMPLETE.json', dict(status='COMPLETE', utc=utc(), fits=count,
              draw_blocks=len(block_manifest), elapsed_seconds=elapsed,
              utc_elapsed_seconds=utc_elapsed,
              peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
              results_sha256=results_digest, failed_runs=[], training=False))
        print(json.dumps(read(raw / 'COMPLETE.json')), flush=True)
    except BaseException as exc:
        write(raw / 'FAILURE.json', dict(status='FAILED', utc=utc(), completed_fits=count,
                                       error=repr(exc), block_manifest=block_manifest))
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--phase', choices=['prepare', 'experiment'], required=True)
    parser.add_argument('--checks', default='work/stage7-checks-20260930-01.json')
    parser.add_argument('--analysis-checks', default='work/stage7-analysis-checks-20260930-01.json')
    parser.add_argument('--review', default='work/stage7-design-review-20260930-01.json')
    args = parser.parse_args()
    assert args.run_id and Path(args.run_id).name == args.run_id and '/' not in args.run_id and '\\' not in args.run_id
    assert args.run_id not in ['.', '..']
    raw = ROOT / 'work/runs' / args.run_id
    if args.phase == 'prepare':
        prepare(raw, ROOT / args.checks, ROOT / args.analysis_checks, ROOT / args.review)
    else:
        experiment(raw)


if __name__ == '__main__':
    main()
