"""A2: the WikiText-103 training rows (native Windows; pyarrow). Owner-run after A1, under the same approval.

  python.exe -I -B a2_rows.py --approval-id <ID> --expected-subject <SUBJECT>

Method check first: the same extraction (the `text` column, in file order) of the local WikiText-2 train, validation and
test parquet files must equal, row for row, the pinned WikiText-2 rows files the natural-text corpus was built from. Then
both WikiText-103 training files are re-hashed against A1's record, streamed in file order (parquet batches; the rows are
never all held in memory), and their rows (1,801,350, as pinned) are written as gzip JSON lines (one JSON string per row, UTF-8,
fixed gzip timestamp) to train-rows.jsonl.gz.part, renamed to train-rows.jsonl.gz only when complete, with A2_RECORD.json. A
part file left by an interrupted attempt, or a rows file without A2_RECORD.json, is kept as train-rows.jsonl.gz.failed-<k>
and the step proceeds; the row count is checked before the rename (review 1, finding 4, and its confirmation, N1). Nothing is written on a refusal. Fixture mode (tests only) needs a FIXTURE id and a target outside the root.
"""
import argparse, gzip, hashlib, json, os, platform, sys
sys.dont_write_bytecode = True
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import acquire_plan as ap
import acquire_common as ac
import text_plan


def iter_texts(path):
    """The `text` column of a parquet file, in row order, as Python strings, streamed in batches."""
    import pyarrow.parquet as pq
    for batch in pq.ParquetFile(str(path)).iter_batches(columns=['text'], batch_size=65536):
        for t in batch.column(0).to_pylist():
            if not isinstance(t, str): raise SystemExit('A row is not a string: ' + Path(path).name)
            yield t


def extract(path): return list(iter_texts(path))


def pq_rows(path):
    import pyarrow.parquet as pq
    return pq.ParquetFile(str(path)).metadata.num_rows


def method_check(root):
    """The extraction reproduces the pinned WikiText-2 rows files from the local WikiText-2 parquet files."""
    out = {}
    for split, (rel, pin) in ap.WT2_PARQUET.items():
        h, _ = ac.sha_file(Path(root) / rel)
        if h != pin: raise SystemExit('Local WikiText-2 parquet differs from its pin: ' + rel)
        rows_rel, rows_pin = text_plan.TEXT_ASSETS[split]; raw = (Path(root) / rows_rel).read_bytes()
        if ac.sha(raw) != rows_pin: raise SystemExit('WikiText-2 rows file differs from its pin: ' + rows_rel)
        if extract(Path(root) / rel) != [r['text'] for r in json.loads(raw)]: raise SystemExit('The extraction does not reproduce the WikiText-2 rows: ' + split)
        out[split] = len(json.loads(raw))
    return out


def write_rows(path, rows, expected=None):
    """Deterministic gzip JSON lines from an iterable of rows, written to <path>.part and renamed into place only when complete
    and, if `expected` is given, only if the row count equals it. Returns (gzip sha256, gzip bytes, sha256 of the uncompressed
    lines, rows)."""
    plain = hashlib.sha256(); count = 0; part = Path(str(path) + '.part')
    with open(part, 'xb') as raw, gzip.GzipFile(filename='', mode='wb', compresslevel=ap.GZIP_LEVEL, fileobj=raw, mtime=0) as g:
        for t in rows:
            line = (json.dumps(t, ensure_ascii=False) + '\n').encode('utf-8'); plain.update(line); g.write(line); count += 1
    if expected is not None and count != expected: raise SystemExit(f'Rows written: {count}, pinned {expected}; the part file is kept and nothing is renamed')
    os.replace(part, path)
    h, n = ac.sha_file(path)
    return h, n, plain.hexdigest(), count


def read_rows(path):
    """The rows back from train-rows.jsonl.gz (A3 and the tests)."""
    with gzip.open(path, 'rt', encoding='utf-8', newline='\n') as g: return [json.loads(line) for line in g]


def run(approval_id, expected_subject, fixture=False, target=None, here=HERE, root=ac.ROOT, expected_rows=ap.TRAIN_ROWS):
    ac.check_approval(approval_id, fixture)
    ac.check_source(here, expected_subject)
    assets = ac.place(fixture, target, ap.ASSETS, root)
    a1, a1_sha = ac.read_record(assets / 'A1_RECORD.json', 'A1', approval_id, expected_subject)
    if (assets / 'A2_RECORD.json').exists(): raise SystemExit('A2 has already completed; no second extraction')
    pins = {d['name']: d for d in ap.DOWNLOADS}
    if [f['name'] for f in a1['files']] != [d['name'] for d in ap.DOWNLOADS]: raise SystemExit('A1 record files differ from the plan')
    for f in a1['files']:
        h, n = ac.sha_file(assets / 'dataset' / f['name'])
        if (n, h) != (pins[f['name']]['bytes'], pins[f['name']]['sha256']) or (n, h) != (f['bytes'], f['sha256']): raise SystemExit('Downloaded file differs from its pin: ' + f['name'])
    check = method_check(root)
    import pyarrow
    count = sum(pq_rows(assets / 'dataset' / d['name']) for d in ap.DOWNLOADS)
    if count != expected_rows: raise SystemExit(f'WikiText-103 training rows: {count}, pinned {expected_rows}')
    kept = []
    for stale in (Path(str(assets / ap.ROWS_FILE) + '.part'), assets / ap.ROWS_FILE):          # an interrupted earlier attempt (review 1, finding 4; N1)
        if stale.exists():
            k = 1 + sum(1 for _ in assets.glob(ap.ROWS_FILE + '.failed-*')); name = f'{ap.ROWS_FILE}.failed-{k}'; os.replace(stale, assets / name); kept.append(name)
    gz_sha, gz_bytes, plain_sha, written = write_rows(assets / ap.ROWS_FILE, (t for d in ap.DOWNLOADS for t in iter_texts(assets / 'dataset' / d['name'])), expected_rows)
    record = dict(step='A2', status='COMPLETE', approval_id=approval_id, fixture=bool(fixture), source_subject_sha256=expected_subject, a1_record_sha256=a1_sha,
                  rows=written, interrupted_attempts_kept=kept, rows_file=dict(path=ap.ROWS_FILE, bytes=gz_bytes, sha256=gz_sha, uncompressed_lines_sha256=plain_sha, format='gzip JSON lines, one JSON string per row, file order'),
                  method_check=dict(status='PASS', wikitext2_rows=check, rule='extract(parquet) equals the pinned WikiText-2 rows files, row for row'),
                  pyarrow=pyarrow.__version__, python=platform.python_version(), finished_utc=ac.utc())
    digest = ac.write_new(assets / 'A2_RECORD.json', record)
    return dict(record, record_sha256=digest)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--approval-id', required=True); p.add_argument('--expected-subject', required=True)
    p.add_argument('--fixture', action='store_true'); p.add_argument('--target')
    a = p.parse_args()
    r = run(a.approval_id, a.expected_subject, a.fixture, Path(a.target) if a.target else None)
    print(json.dumps(dict(status=r['status'], rows=r['rows'], rows_file=r['rows_file'], record_sha256=r['record_sha256']), indent=1))
