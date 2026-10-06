"""v0134 operational guards only; no numerical research on import."""
import hashlib
import json
import math
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT/'work/runs/gradient-alignment-v0134-20261004-01'
OUT = HERE/'results-existing-gradient-panel-v0134-20261004-01'
STATES = ('initial', 'Unoclip_F10', 'Inoclip_F10')
TOTAL_SECONDS = 600
LOCAL_CAP = 16*2**20
LOCAL_WORK_CAP = 12*2**20
COMBINED_CAP = 512*2**20
COMBINED_WORK_CAP = COMBINED_CAP-80*2**20
FREE_RESERVE = 2*2**30
EPS = 1e-12
PARENT_BUNDLE = ROOT/'outputs/sequence-weighting-clipping-interaction-v0133-r1'
PARENT_RUN = ROOT/'work/runs/clipping-interaction-v0133-20261004-02'
FAILED_BUNDLE = ROOT/'outputs/sequence-weighting-clipping-interaction-v0133'
PLANNING = ROOT/'outputs/sequence-weighting-clipping-interaction-v0133-planning/PROPOSED_PROTOCOL.md'

def require(ok, why):
    if not ok: raise RuntimeError(why)

def utc(): return datetime.now(timezone.utc).isoformat()

def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(2**20), b''): value.update(chunk)
    return value.hexdigest()

def finite(value):
    if isinstance(value,float): require(math.isfinite(value), 'Nonfinite scalar')
    elif isinstance(value,dict):
        for item in value.values(): finite(item)
    elif isinstance(value,(tuple,list)):
        for item in value: finite(item)

def write(path,value):
    finite(value); path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False); stream.write('\n')

def allocated(path):
    st=path.stat()
    return max(st.st_size, ((st.st_size+4095)//4096)*4096, getattr(st,'st_blocks',0)*512)

def folder_bytes(folder):
    return sum(allocated(p) for p in folder.rglob('*') if p.is_file()) if folder.exists() else 0

def resources(terminal=False):
    local=folder_bytes(HERE)+folder_bytes(RUN)
    require(PARENT_BUNDLE.is_dir() and PARENT_RUN.is_dir() and FAILED_BUNDLE.is_dir() and PLANNING.is_file(),
            'Missing preserved parent evidence')
    combined=local+folder_bytes(PARENT_BUNDLE)+folder_bytes(PARENT_RUN)+folder_bytes(FAILED_BUNDLE)+allocated(PLANNING)
    require(local <= (LOCAL_CAP if terminal else LOCAL_WORK_CAP), 'v0134 allocated storage/reserve cap')
    require(combined <= (COMBINED_CAP if terminal else COMBINED_WORK_CAP), 'Combined preserved-study storage cap')
    free=shutil.disk_usage(ROOT).free
    require(free >= FREE_RESERVE, '2 GiB free-space reserve')
    return dict(local_allocated_bytes=local,combined_allocated_bytes=combined,free_bytes=free)

def verify_manifest():
    obj=read(HERE/'SOURCE_MANIFEST.json'); require(obj['version']=='v0134','Wrong source version')
    for row in obj['files']:
        p=HERE/row['path']
        require(p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],
                'Source changed: '+row['path'])
    return sha(HERE/'SOURCE_MANIFEST.json')

def verify_review(path):
    path=Path(path).resolve(); require(path.is_relative_to(HERE/'reviews'),'Review outside counted bundle')
    obj=read(path)
    require(obj['status']=='PASS_V0134_SOURCE' and obj['independent'] is True and bool(obj['reviewer_identity']),
            'Independent source review pending')
    require(obj['manifest_sha256']==verify_manifest(), 'Review source binding')
    require(obj['combined_seconds']==TOTAL_SECONDS and obj['additional_storage_bytes']==LOCAL_CAP and
            obj['combined_storage_bytes']==COMBINED_CAP and obj['free_reserve_bytes']==FREE_RESERVE,
            'Review resource constraints')
    require(obj['input_bindings_sha256']==sha(HERE/'INPUT_BINDINGS.json'), 'Review panel input binding')
    return dict(path=path.relative_to(HERE).as_posix(),sha256=sha(path))

def verify_inputs(guard):
    obj=read(HERE/'INPUT_BINDINGS.json')
    require(obj['version']=='v0134' and len(obj['panel'])==30, 'Input panel identity/count')
    for row in obj['files']:
        guard.check(); p=ROOT/row['path']
        require(p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],
                'Missing/changed frozen input: '+row['path'])
    require(not (PARENT_BUNDLE/'receipts/FAILED.json').exists(), 'Parent successful cohort failure latch')
    return obj

def binding(folder,exclude=()):
    return {p.relative_to(folder).as_posix():sha(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and p.relative_to(folder).as_posix() not in exclude}

class Guard:
    def __init__(self,admission):
        self.obj=read(admission); self.start=self.obj['monotonic_start']; self.wall=self.obj['wall_start']
        require(self.obj['manifest_sha256']==verify_manifest(),'Admission source binding')
        review=self.obj['review']; require(sha(HERE/review['path'])==review['sha256'],'Admission review binding')
        verify_review(HERE/review['path'])
    def check(self,disk=False):
        elapsed=max(time.monotonic()-self.start,time.time()-self.wall)
        require(elapsed < self.obj['work_seconds'],'Phase deadline')
        require(not (HERE/'receipts/FAILED.json').exists(),'Terminal failure latch')
        if disk: resources()
        return elapsed
