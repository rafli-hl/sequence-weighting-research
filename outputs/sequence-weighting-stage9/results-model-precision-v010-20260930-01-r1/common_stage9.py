"""Frozen Stage9 I/O, configuration and provenance infrastructure."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES = ['core.py','precision_math.py','reference_math.py','metrics.py',
    'inputs_stage4.py','inputs_stage56.py','common_stage9.py','stage9.py',
    'audit_stage9.py','analyze_stage9.py','check_stage9.py','analysis_checks.py',
    'PROTOCOL_STAGE9.md','README.md','DERIVATION.json']
BUDGET = 3600


def utc(): return datetime.now(timezone.utc).isoformat()


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def array_sha(values):
    return hashlib.sha256(np.asarray(values,dtype='<f8').tobytes(order='C')).hexdigest()


def tensor_array_sha(values):
    values = np.asarray(values)
    h = hashlib.sha256()
    h.update(json.dumps(dict(dtype=values.dtype.str,shape=list(values.shape)),
        sort_keys=True,separators=(',',':')).encode('utf-8'))
    h.update(values.tobytes(order='C'))
    return h.hexdigest()


class Budget:
    def __init__(self, seconds=BUDGET):
        self.limit = seconds
        self.started = datetime.now(timezone.utc)
        self.started_utc = self.started.isoformat()
        self.start = time.perf_counter()

    def check(self):
        elapsed = time.perf_counter()-self.start
        utc_elapsed = (datetime.now(timezone.utc)-self.started).total_seconds()
        if max(elapsed,utc_elapsed)>self.limit:
            raise RuntimeError('Prespecified CPU budget exhausted; partial records preserved')
        return elapsed,utc_elapsed


def configuration(run_id):
    return dict(version='v0.10',run_id=run_id,stages=[4,5,6],
        cohorts=['S4_fixed30','S5_R','S6_P1_R','S6_P2_R','S6_P3_R','S6_P4_R'],
        variants=['M','U'],widths=[64,128,256],arm='random',policy_references=324,
        native_checkpoints=207,cases=186,weight_groups=9,n=512,
        grid=[i/20 for i in range(161)],grid_size=161,anchor_p=0.,
        primary_precision=80,audit_precision=110,convergence_relative_tolerance='1e-50',
        reference_tie_factor='2e-50',budget_seconds=BUDGET,audit_budget_seconds=BUDGET,
        preparation_budget_seconds=1800,max_snapshot_bytes=1024**3,min_free_bytes=2*1024**3,
        input_operation='float32 initial loss minus float32 current loss; then float64 promotion',
        deduplication='exact promoted weight and gain bytes; retain every policy alias and native checkpoint',
        selection='complete frozen-design cohorts and existing validation decisions only',
        original_p_role='stored-point evaluation only; no reoptimization, replacement or selection',
        training=False,gpu=False,adaptive_precision=False,adaptive_grid=False)


def verify_source(raw):
    manifest=read(raw/'source_manifest.json')
    assert set(manifest)==set(SOURCES)
    for name,digest in manifest.items():
        assert sha(HERE/name)==sha(raw/'source'/name)==digest,name
    for stage in range(4,9):
        assert manifest['core.py']==sha(ROOT/f'outputs/sequence-weighting-stage{stage}/core.py')
    assert manifest['precision_math.py']==sha(ROOT/'outputs/sequence-weighting-stage8/precision_math.py')
    return manifest


def verify_inputs(raw):
    freeze=read(raw/'FREEZE.json')
    assert sha(raw/'config.json')==freeze['config_sha256']
    assert read(raw/'config.json')==configuration(raw.name)
    assert sha(raw/'input_manifest.json')==freeze['input_manifest_sha256']
    assert sha(raw/'INVENTORY.json')==freeze['inventory_sha256']
    assert sha(raw/'historical_manifest.json')==freeze['historical_manifest_sha256']
    for name,digest in read(raw/'input_manifest.json').items():
        assert sha(raw/name)==digest,name
    for filename,key in [('CHECKS.json','checks_sha256'),('ANALYSIS_CHECKS.json','analysis_checks_sha256'),
                         ('DESIGN_REVIEW.json','design_review_sha256')]:
        assert sha(raw/filename)==freeze[key]
    return read(raw/'inputs/profiles.json')


def historical_paths():
    paths=[]
    for folder in sorted((ROOT/'outputs').glob('sequence-weighting-*')):
        if folder==HERE: continue
        paths.extend(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for folder in sorted((ROOT/'work/runs').iterdir()):
        if not folder.is_dir() or folder.name.startswith('model-precision-v010-'): continue
        paths.extend(p for p in folder.iterdir() if p.is_file())
        for name in ['source','analysis-source','analysis-repair-source']:
            paths.extend(p for p in (folder/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return sorted(set(paths))
