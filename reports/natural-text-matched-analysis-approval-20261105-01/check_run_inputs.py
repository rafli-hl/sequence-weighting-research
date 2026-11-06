"""Each draw's inputs against the real-engine check, for the results report of the matched-progress confirmation, N7. Owner-run, because it reads under work/runs/, and after the sealed analysis. Native Windows Python 3.12, -I -B. Writes only RUN_INPUTS_CHECK.json in reports/natural-text-matched-run-checks-20261104-01.

  python.exe -I -B check_run_inputs.py

Under work/runs/ it opens the six draws' INPUTS.json and nothing else: an audit hook in this process stops any other open or listing there. INPUTS.json holds seeds, hashes, weights and the plan's arms and readouts, and no loss, p* or gain. It refuses to start unless the sealed analysis has written its output, so that this is no look at the data before the analysis, and unless its own output does not exist yet, so that it runs once.

From each INPUTS.json: weights, orders and pool orders against the real-Torch check (INPUTS_CHECK.json); the list of weights itself, which is what the fits use, rehashed here against the same check; tied values, counted from the run's own weights, against the same check and its limit; seeds against the registry's row; articles and sequence indices against the partition; validation and pool against N6's native hashes, since the protocol says they are N6's. The six training hashes have no reference, and only their being distinct is checked. Prints statuses and counts only. Exit 0 if every comparison holds, 1 if any differs. A difference changes no label: it goes to the owner before the report."""
import hashlib, json, os, re, struct, sys, time
sys.dont_write_bytecode = True
from pathlib import Path

ROOT = Path(r'D:\sequence-weighting-research')
RUNS = dict(M1=ROOT / 'work/runs/natural-text-matched-m1-20261104-01', M2=ROOT / 'work/runs/natural-text-matched-m2-20261104-01')
RUN_OF = dict(m01='M1', m02='M1', m03='M1', m04='M2', m05='M2', m06='M2'); DRAWS = tuple(RUN_OF)
ANALYSIS = ROOT / 'reports/natural-text-matched-analysis-20261105-01/ANALYSIS.json'; OUT = ROOT / 'reports/natural-text-matched-run-checks-20261104-01/RUN_INPUTS_CHECK.json'
ENGINE = ROOT / 'reports/natural-text-matched-engine-check-result-20261104-01/INPUTS_CHECK.json'; ENGINE_SHA256 = '022591d909988e2fd3dddb65e202f54fe3cf12897956a6602d076d9feff35d27'
REGISTRY = ROOT / 'reports/natural-text-matched-seed-registry-20261104-01/REGISTRY.json'; REGISTRY_SHA256 = 'bee578826fbdb5e66fbb36d577e45929af756e05b12b62d6cd141b4b5da7ea64'
PARTITION = ROOT / 'reports/natural-text-matched-seed-registry-20261104-01/PARTITION.json'; PARTITION_SHA256 = 'b7eb3d3ba200b86046c6d731d2f0200ff657b6c2aaeebd43423cd4aec530e33b'
N6_EXPECTED = ROOT / 'reports/natural-text-peak-preparation-20261103-01/ENGINE_CHECK_EXPECTED.json'; N6_EXPECTED_SHA256 = 'fa1cf6c41b53194eb54eaccc7b3aebe0aa17e62debb6817c0ef82bd43b053fc1'
N = 16384; ITEMS = ('n_train', 'weights', 'weights_list', 'orders', 'pool_orders', 'tied_values', 'seeds', 'articles', 'sequence_indices', 'validation', 'pool')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(); load = lambda p: json.loads(Path(p).read_bytes())


class RuleBroken(BaseException):
    """Not an Exception, so that nothing on the way can catch it."""


def norm(p): return os.path.abspath(os.fsdecode(p)).replace('\\', '/').lower()


def list_hash(weights):
    """text_engine.tensor_hash of a one-dimensional float32 tensor, from the list of floats, without Torch: SHA-256 over str((shape, dtype)) and the raw bytes."""
    n = len(weights); return hashlib.sha256(str(((n,), 'torch.float32')).encode('utf-8') + struct.pack(f'<{n}f', *weights)).hexdigest()


def install_guard(allowed):
    """From here on, in this process: under a work/runs folder, only the files in `allowed` can be opened, and nothing can be listed or changed."""
    allowed = {norm(p) for p in allowed}; events = ('open', 'os.listdir', 'os.scandir', 'glob.glob', 'os.mkdir', 'os.rename', 'os.remove', 'os.rmdir', 'os.truncate', 'os.utime', 'os.chmod', 'os.link', 'os.symlink', 'shutil.copyfile', 'shutil.copytree', 'shutil.move', 'shutil.rmtree')
    def hook(event, args):
        if event in events and args and isinstance(args[0], (str, bytes, os.PathLike)):
            s = norm(args[0])
            if re.search(r'/work/runs(/|$)', s) and not (event == 'open' and s in allowed): raise RuleBroken(f'This check opens only the six INPUTS.json under work/runs: {event} {s}')
    sys.addaudithook(hook)


def compare(inputs, engine, registry, partition, n6, n=N):
    """Pure. inputs: {draw: its INPUTS.json}. Returns the record's fields: per draw, each item equal or differs, with the hashes and tied values."""
    seeds = {row['group']: {k: v for k, v in row.items() if k != 'group'} for row in registry['groups']}; n6_validation = {v['validation'] for v in n6['draws'].values()}; n6_pool = {v['pool'] for v in n6['draws'].values()}; draws = {}; differences = []
    if len(n6_validation) != 1 or len(n6_pool) != 1: raise ValueError('The N6 record does not hold one validation set and one pool')
    for d in DRAWS:
        inp = inputs[d]; h = inp['tensor_hashes']; c = engine['draws'][d]; g = partition['groups'][d]; ties = len(inp['weights']) - len(set(inp['weights'])); idx = hashlib.sha256(json.dumps(g['sequences'][:n]).encode()).hexdigest(); listed = list_hash(inp['weights'])
        same = dict(n_train=inp['n_train'] == n, weights=h['weights'] == c['weights_hash'], weights_list=listed == c['weights_hash'], orders=h['orders'] == c['orders_hash'], pool_orders=h['pool_orders'] == c['pool_orders_hash'], tied_values=ties == c['tied_values'] and ties <= c['limit'], seeds=inp['seeds'] == seeds[d], articles=inp['articles'] == g['articles'], sequence_indices=inp['sequence_indices_sha256'] == idx, validation=h['validation'] in n6_validation, pool=h['pool'] in n6_pool)
        draws[d] = dict(items={k: 'equal' if same[k] else 'differs' for k in ITEMS}, tied_values_in_the_run=ties, tied_values_in_the_engine_check=c['tied_values'], limit=c['limit'], hashes=dict(weights=h['weights'], weights_list=listed, orders=h['orders'], pool_orders=h['pool_orders'], train=h['train'], validation=h['validation'], pool=h['pool'], sequence_indices=inp['sequence_indices_sha256']))
        differences += [dict(draw=d, item=k) for k in ITEMS if not same[k]]
    train = [draws[d]['hashes']['train'] for d in DRAWS]; distinct = len(set(train)) == len(train)
    if not distinct: differences.append(dict(draw='all', item='the six training hashes are not distinct'))
    return dict(status='PASS' if not differences else 'FAIL', comparisons=len(DRAWS) * len(ITEMS) + 1, differences=differences, training_hashes_distinct=distinct, draws=draws)


def main():
    files = {d: RUNS[RUN_OF[d]] / d / 'INPUTS.json' for d in DRAWS}; install_guard(files.values())
    if not ANALYSIS.is_file(): raise SystemExit('The sealed analysis has not written its output: this check comes after it')
    if OUT.exists(): raise SystemExit(f'{OUT.name} exists: this check runs once')
    for path, want in ((ENGINE, ENGINE_SHA256), (REGISTRY, REGISTRY_SHA256), (PARTITION, PARTITION_SHA256), (N6_EXPECTED, N6_EXPECTED_SHA256)):
        if sha(path) != want: raise SystemExit(f'A saved record changed: {path.name}')
    result = compare({d: load(p) for d, p in files.items()}, load(ENGINE), load(REGISTRY), load(PARTITION), load(N6_EXPECTED))
    rec = dict(schema=1, purpose="Each draw's inputs against the real-engine check, from the six INPUTS.json only; no loss, p* or gain (owner-run, after the sealed analysis)", checked_local=time.strftime('%Y-%m-%d %H:%M:%S'), check_sha256=sha(__file__), analysis_json_sha256=sha(ANALYSIS), inputs_sha256={d: sha(p) for d, p in files.items()}, engine_check_sha256=ENGINE_SHA256, **result, not_opened='Under work/runs/: everything but the six INPUTS.json.')
    with OUT.open('xb') as f: f.write((json.dumps(rec, indent=1) + '\n').encode('utf-8'))
    print(json.dumps(dict(status=rec['status'], comparisons=rec['comparisons'], differences=rec['differences'], tied_values={d: rec['draws'][d]['tied_values_in_the_run'] for d in DRAWS}), indent=1)); print(f'Written: {OUT} sha256 {sha(OUT)}')
    return 0 if rec['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
