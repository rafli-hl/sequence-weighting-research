"""v0135 operational identities and fail-closed guards; no research on import."""
import hashlib
import json
import math
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT/'work/runs/preconditioning-v0135-20261005-01'
OUT = HERE/'results-fresh-preconditioning-v0135-20261005-01'
RUNTIME_LIMIT = 1800
AUDIT_LIMIT = 600
ARMS = ('U-Adam','I-Adam','U-isotropic','I-isotropic')
ARM_POLICY = {'U-Adam':('uniform','adam'), 'I-Adam':('instance','adam'),
              'U-isotropic':('uniform','isotropic'), 'I-isotropic':('instance','isotropic')}
CORPORA = (91520101,91520102,91520103,91520104,91520105)
PRESEEDS = (91530101,91530102,91530103,91530104,91530105)
MODEL_SEEDS = ((91540101,91540151),(91540201,91540251),(91540301,91540351),
               (91540401,91540451),(91540501,91540551))
MAX_BYTES = 512*2**20
ARCHIVE_RESERVE = 64*2**20
RECEIPT_RESERVE = 16*2**20
WRITE_LIMIT = 432*2**20
FREE_RESERVE = 2*2**30
EPS_NORM = 1e-12
PARAMETERS = 621696
SNAPSHOT_PAIR = (CORPORA[0], MODEL_SEEDS[0][0])
SNAPSHOT_STEPS = (1,160)

def require(ok, reason):
    if not ok: raise RuntimeError(reason)

def utc(): return datetime.now(timezone.utc).isoformat()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(2**20),b''): h.update(block)
    return h.hexdigest()

def finite(value):
    if isinstance(value,float): require(math.isfinite(value),'Nonfinite record')
    elif isinstance(value,dict):
        for child in value.values(): finite(child)
    elif isinstance(value,(list,tuple)):
        for child in value: finite(child)

def write(path,value):
    finite(value); path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False); stream.write('\n')

def allocated(path):
    st=path.stat()
    return max(st.st_size,((st.st_size+4095)//4096)*4096,getattr(st,'st_blocks',0)*512)

def storage():
    return sum(allocated(p) for folder in (HERE,RUN) if folder.exists()
               for p in folder.rglob('*') if p.is_file())

def resources(limit=WRITE_LIMIT):
    used=storage(); free=shutil.disk_usage(ROOT).free
    require(used<=limit,'v0135 additional allocation/reserve cap')
    require(free>=FREE_RESERVE,'2 GiB free-space reserve')
    return dict(allocated_bytes=used,free_bytes=free)

def verify_manifest():
    obj=read(HERE/'SOURCE_MANIFEST.json'); require(obj['version']=='v0135','Source version')
    for row in obj['files']:
        p=HERE/row['path']
        require(p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],
                'Source drift: '+row['path'])
    return sha(HERE/'SOURCE_MANIFEST.json')

def verify_review(path):
    path=Path(path).resolve(); require(path.is_relative_to(HERE/'reviews'),'Review outside counted bundle')
    obj=read(path)
    require(obj['status']=='PASS_V0135_SOURCE' and obj['independent'] is True and bool(obj['reviewer_identity']),
            'Independent source review pending')
    require(obj['manifest_sha256']==verify_manifest(),'Review source binding')
    require(obj['freshness_sha256']==sha(HERE/'FRESHNESS_RECONCILIATION.json') and
            obj['census_sha256']==sha(HERE/'SEED_CENSUS.json') and bool(obj['freshness_reconciliation']),
            'Semantic freshness review binding')
    require(obj['runtime_seconds']==RUNTIME_LIMIT and obj['audit_seconds']==AUDIT_LIMIT and
            obj['storage_bytes']==MAX_BYTES and obj['normal_write_bytes']==WRITE_LIMIT and
            obj['free_reserve_bytes']==FREE_RESERVE,'Review constraints')
    return dict(path=path.relative_to(HERE).as_posix(),sha256=sha(path))

def pairs(): return [(i,d,s,PRESEEDS[i]) for i,d in enumerate(CORPORA) for s in MODEL_SEEDS[i]]
def pair_name(d,s): return f'd{d}-s{s}'
def binding(folder):
    return {p.relative_to(folder).as_posix():sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}
def check_binding(folder,expected): require(binding(folder)==expected,'Missing, extra or changed immutable files')

class Guard:
    def __init__(self,admission):
        self.admission=read(admission); self.start=self.admission['monotonic_start']
        self.utc_start=datetime.fromisoformat(self.admission['utc_start']).timestamp()
        require(self.admission['manifest_sha256']==verify_manifest(),'Admission source drift')
        review=self.admission['review']; require(sha(HERE/review['path'])==review['sha256'],'Review drift')
        verify_review(HERE/review['path'])
    def check(self,disk=False):
        elapsed=max(time.monotonic()-self.start,time.time()-self.utc_start)
        require(elapsed<self.admission['work_seconds'],'Phase work deadline')
        require(not (HERE/'receipts/FAILED.json').exists(),'Terminal failure latch')
        if disk: resources()
        return elapsed
