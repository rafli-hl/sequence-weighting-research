"""Prospective v0133 utilities. No research executes on import."""
import hashlib
import json
import math
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT / 'work/runs/clipping-interaction-v0133-20261004-02'
OUT = HERE / 'results-fresh-clipping-interaction-v0133-20261004-02'
FAILED_BUNDLE = ROOT / 'outputs/sequence-weighting-clipping-interaction-v0133'
PREVIOUS_RUNTIME_CHARGE = 2
RUNTIME_LIMIT = 1800 - PREVIOUS_RUNTIME_CHARGE
ARMS = ('Uclip', 'Iclip', 'Unoclip', 'Inoclip')
ARM_POLICY = {'Uclip': ('uniform', 1.), 'Iclip': ('instance', 1.),
              'Unoclip': ('uniform', None), 'Inoclip': ('instance', None)}
PLANNING = ROOT / 'outputs/sequence-weighting-clipping-interaction-v0133-planning/PROPOSED_PROTOCOL.md'
CORPORA = (91420101, 91420102, 91420103, 91420104, 91420105)
PRESEEDS = (91430101, 91430102, 91430103, 91430104, 91430105)
MODEL_SEEDS = ((91440101,91440151),(91440201,91440251),(91440301,91440351),
               (91440401,91440451),(91440501,91440551))
MAX_BYTES = 512 * 2**20
ARCHIVE_RESERVE = 64 * 2**20
RECEIPT_RESERVE = 16 * 2**20
FREE_RESERVE = 2 * 2**30
WRITE_LIMIT = MAX_BYTES - ARCHIVE_RESERVE - RECEIPT_RESERVE

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def utc():
    return datetime.now(timezone.utc).isoformat()

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(2**20), b''):
            h.update(chunk)
    return h.hexdigest()

def finite(value):
    if isinstance(value, float):
        require(math.isfinite(value), 'Nonfinite numeric record')
    elif isinstance(value, dict):
        for child in value.values(): finite(child)
    elif isinstance(value, (list, tuple)):
        for child in value: finite(child)

def write(path, value):
    finite(value)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')

def allocated(path):
    st = path.stat()
    return max(st.st_size, ((st.st_size + 4095)//4096)*4096,
               getattr(st, 'st_blocks', 0)*512)

def storage():
    return allocated(PLANNING) + sum(allocated(p) for folder in (HERE, RUN, FAILED_BUNDLE) if folder.exists()
               for p in folder.rglob('*') if p.is_file())

def resources(limit=WRITE_LIMIT):
    used = storage()
    free = shutil.disk_usage(ROOT).free
    require(used <= limit, 'v0133 storage cap/reserve violated')
    require(free >= FREE_RESERVE, '2 GiB free-space reserve violated')
    return dict(allocated_bytes=used, free_bytes=free)

def verify_manifest():
    require(sha(PLANNING)=='0c5cde22d42db88e7218f29c783e96d20dd4478401ec711cfdbf7c799b44e1d1',
            'Accepted planning protocol drift')
    manifest = read(HERE/'SOURCE_MANIFEST.json')
    require(manifest['version'] == 'v0133', 'Wrong manifest version')
    for row in manifest['files']:
        p = HERE / row['path']
        require(p.is_file() and sha(p) == row['sha256'], 'Source drift: '+row['path'])
    return sha(HERE/'SOURCE_MANIFEST.json')

def verify_review(path):
    path = Path(path).resolve()
    require(path.is_relative_to(HERE/'reviews'), 'Review must be within counted bundle reviews')
    obj = read(path)
    require(obj['status'] == 'PASS_V0133_SOURCE' and obj['independent'] is True,
            'Independent source review has not passed')
    require(bool(obj['reviewer_identity']), 'Missing independent reviewer identity')
    require(obj['manifest_sha256'] == verify_manifest(), 'Review does not bind current source')
    require(bool(obj.get('freshness_reconciliation')), 'Missing semantic freshness reconciliation')
    require(obj['runtime_seconds'] == 1800 and obj['audit_seconds'] == 600 and
            obj['storage_bytes'] == MAX_BYTES and obj['free_reserve_bytes'] == FREE_RESERVE,
            'Review constraints mismatch')
    require(obj['previous_runtime_charge_seconds']==PREVIOUS_RUNTIME_CHARGE and
            obj['runtime_remaining_seconds']==RUNTIME_LIMIT, 'Review attempt accounting mismatch')
    return dict(path=path.relative_to(HERE).as_posix(), sha256=sha(path))

def pairs():
    return [(i, d, s, PRESEEDS[i]) for i,d in enumerate(CORPORA) for s in MODEL_SEEDS[i]]

def pair_name(d, s):
    return f'd{d}-s{s}'

def binding(folder):
    return {p.relative_to(folder).as_posix(): sha(p)
            for p in sorted(folder.rglob('*')) if p.is_file()}

def check_binding(folder, expected):
    require(binding(folder) == expected, 'Missing, extra, or changed immutable inputs')

class Guard:
    def __init__(self, admission):
        self.admission = read(admission)
        self.start = self.admission['monotonic_start']
        self.utc_start = datetime.fromisoformat(self.admission['utc_start']).timestamp()
        require(self.admission['manifest_sha256']==verify_manifest(), 'Admission source drift')
        review=self.admission['review']
        require(sha(HERE/review['path'])==review['sha256'], 'Admission review changed')
        verify_review(HERE/review['path'])
    def check(self, disk=False):
        elapsed = max(time.monotonic()-self.start, time.time()-self.utc_start)
        require(elapsed < self.admission['work_seconds'], 'Phase work deadline exceeded')
        require(not (HERE/'receipts/FAILED.json').exists(), 'Failure latch exists')
        if disk: resources()
        return elapsed
