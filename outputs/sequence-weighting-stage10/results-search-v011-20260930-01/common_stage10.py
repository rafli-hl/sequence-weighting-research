"""Stage10 immutable I/O, design and shared numerical runtime budget."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import time
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'work/runs/model-precision-v010-20260930-01'
PARENT_SOURCE=ROOT/'outputs/sequence-weighting-stage9'
PARENT_REPORT=PARENT_SOURCE/'results-model-precision-v010-20260930-01-r2'
SOURCES=['core.py','search_math.py','independent_math.py','common_stage10.py',
    'inputs.py','stage10.py','audit_stage10.py','check_stage10.py','analyze_stage10.py',
    'analysis_checks.py','PROTOCOL_STAGE10.md','README.md','DERIVATION.json']
BUDGET=3600


def utc(): return datetime.now(timezone.utc).isoformat()


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def write(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False); stream.write('\n')


def array_sha(values):
    return hashlib.sha256(np.asarray(values,dtype='<f8').tobytes(order='C')).hexdigest()


def tensor_array_sha(values):
    values=np.asarray(values); h=hashlib.sha256()
    h.update(json.dumps(dict(dtype=values.dtype.str,shape=list(values.shape)),sort_keys=True,separators=(',',':')).encode('utf-8'))
    h.update(values.tobytes(order='C'))
    return h.hexdigest()


class BudgetExceeded(RuntimeError): pass


class Budget:
    def __init__(self,seconds=BUDGET):
        self.limit=seconds; self.started=datetime.now(timezone.utc)
        self.started_utc=self.started.isoformat(); self.start=time.perf_counter()

    def elapsed(self):
        return time.perf_counter()-self.start,(datetime.now(timezone.utc)-self.started).total_seconds()

    def check(self):
        a,b=self.elapsed()
        if max(a,b)>self.limit: raise BudgetExceeded('Frozen shared numerical budget exhausted; no automatic retry')
        return a,b


def configuration(run_id):
    return dict(version='v0.11',run_id=run_id,parent_run=PARENT.name,
        cases=186,policy_references=324,native_checkpoints=207,weight_groups=9,n=512,
        primary_precision=80,reference_precision=110,
        primary_mesh_denominator=64,primary_mesh_points=513,
        reference_mesh_denominator=128,reference_mesh_points=1025,
        interval=['0','8'],bracket_width='1e-12',bisection_max_iterations=40,
        golden_max_iterations=80,precision_relative_tolerance='1e-50',
        search_objective_tolerance_factor='1e-18',original_objective_tolerance_factor='1e-12',
        parameter_tolerance='1e-6',neighborhood_step='.001',
        objective_scale='max(1, full reference mesh J span)',
        selection='all Stage9 inputs; original p excluded from every search candidate set',
        candidate_tie='exact objective then smallest exact Decimal p',
        global_optimality_certificate=False,shared_numerical_budget_seconds=BUDGET,
        preparation_budget_seconds=1800,max_snapshot_bytes=512*1024**2,min_free_bytes=2*1024**3,
        training=False,gpu=False,adaptive_precision=False,automatic_retry=False)


def verify_source(raw):
    manifest=read(raw/'source_manifest.json'); assert set(manifest)==set(SOURCES)
    if (raw/'FREEZE.json').exists(): assert manifest==read(raw/'FREEZE.json')['source_sha256']
    for name,digest in manifest.items(): assert sha(HERE/name)==sha(raw/'source'/name)==digest,name
    assert manifest['core.py']==sha(PARENT_SOURCE/'core.py')
    return manifest


def verify_inputs(raw):
    freeze=read(raw/'FREEZE.json')
    assert sha(raw/'config.json')==freeze['config_sha256']
    assert read(raw/'config.json')==configuration(raw.name)
    assert sha(raw/'input_manifest.json')==freeze['input_manifest_sha256']
    assert sha(raw/'historical_manifest.json')==freeze['historical_manifest_sha256']
    for name,digest in read(raw/'input_manifest.json').items(): assert sha(raw/name)==digest,name
    for file,key in [('CHECKS.json','checks_sha256'),('ANALYSIS_CHECKS.json','analysis_checks_sha256'),
                     ('DESIGN_REVIEW.json','design_review_sha256')]:
        assert sha(raw/file)==freeze[key]
    return read(raw/'inputs/profiles.json')


def historical_paths():
    paths=[]
    for folder in sorted((ROOT/'outputs').glob('sequence-weighting-*')):
        if folder==HERE: continue
        paths.extend(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for folder in sorted((ROOT/'work/runs').iterdir()):
        if not folder.is_dir() or folder.name.startswith('search-v011-'): continue
        paths.extend(p for p in folder.iterdir() if p.is_file())
        for name in ['source','analysis-source','analysis-repair-source']:
            paths.extend(p for p in (folder/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return sorted(set(paths))
