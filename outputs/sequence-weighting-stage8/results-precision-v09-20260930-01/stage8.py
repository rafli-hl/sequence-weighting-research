"""Stage8: frozen local precision diagnostic on immutable Stage7 arrays."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
import time
sys.dont_write_bytecode = True
import numpy as np
from precision_math import GRID, DPS, build_cache, evaluate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT_RUN = ROOT/'work/runs/estimator-v08-20260930-01'
SOURCES = ['core.py','precision_math.py','stage8.py','check_stage8.py','audit_stage8.py',
           'analyze_stage8.py','analysis_checks.py','PROTOCOL_STAGE8.md','README.md']
BUDGET_SECONDS = 3600


def utc(): return datetime.now(timezone.utc).isoformat()


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def array_sha(x): return hashlib.sha256(np.asarray(x,dtype='<f8').tobytes()).hexdigest()


def write(path,value):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2,allow_nan=False); f.write('\n')


def configuration(run_id):
    return dict(version='v0.9',run_id=run_id,parent_run=PARENT_RUN.name,
        family='cancellation',ns=[128,512],generator_ps=[.2,1.],
        cs=[1.,.1,.01,1e-12,0.,-.01],replicates=list(range(64)),
        cases=1536,blocks=128,grid=GRID,grid_size=161,anchor_p=0.,
        primary_precision=80,audit_precision=110,convergence_relative_tolerance='1e-50',
        reference_tie_factor='2e-50',budget_seconds=BUDGET_SECONDS,
        audit_budget_seconds=BUDGET_SECONDS,selection='design indices only; all cases retained',
        original_p_role='reference evaluation only; original continuous estimates unchanged')


def historical_paths():
    paths=[]
    for folder in sorted((ROOT/'outputs').glob('sequence-weighting-*')):
        if folder==HERE: continue
        paths.extend(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for folder in sorted((ROOT/'work/runs').iterdir()):
        if not folder.is_dir() or folder.name.startswith('precision-v09-'): continue
        paths.extend(p for p in folder.iterdir() if p.is_file())
        for name in ['source','analysis-source']:
            paths.extend(p for p in (folder/name).rglob('*') if p.is_file())
    return sorted(set(paths))


def verify_source(raw):
    manifest=read(raw/'source_manifest.json')
    for name,digest in manifest.items():
        assert sha(HERE/name)==sha(raw/'source'/name)==digest,name
    assert manifest['core.py']==sha(ROOT/'outputs/sequence-weighting-stage7/core.py')
    return manifest


def prepare(raw,checks_path,analysis_path,review_path):
    assert not raw.exists(),'Refusing existing run'
    manifest={name:sha(HERE/name) for name in SOURCES}
    for path in [checks_path,analysis_path,review_path]:
        evidence=read(path); assert evidence['status']=='PASS'
        assert evidence['source_sha256']
        for name,digest in evidence['source_sha256'].items(): assert manifest[name]==digest,name
    assert read(checks_path)['source_sha256']==manifest
    assert shutil.disk_usage(ROOT).free>=1024**3
    parent_complete=read(PARENT_RUN/'COMPLETE.json')
    parent_audit=read(PARENT_RUN/'AUDIT.json'); assert parent_audit['status']=='PASS'
    assert sha(PARENT_RUN/'results.jsonl')==parent_complete['results_sha256']==parent_audit['results_sha256']
    rows=[json.loads(line) for line in (PARENT_RUN/'results.jsonl').read_text(encoding='utf-8').splitlines()]
    selected=[r for r in rows if r['family']=='cancellation' and r['n'] in [128,512]
              and r['generator_p'] in [.2,1.] and r['c'] in [1.,.1,.01,1e-12,0.,-.01]
              and r['replicate'] in range(64)]
    assert len(selected)==1536 and len({r['block_id'] for r in selected})==128
    raw.mkdir(parents=True); (raw/'source').mkdir(); (raw/'inputs/blocks').mkdir(parents=True)
    for name in SOURCES: shutil.copy2(HERE/name,raw/'source'/name)
    write(raw/'source_manifest.json',manifest)
    for path,name in [(checks_path,'CHECKS.json'),(analysis_path,'ANALYSIS_CHECKS.json'),(review_path,'DESIGN_REVIEW.json')]:
        shutil.copy2(path,raw/name)
    write(raw/'config.json',configuration(raw.name))
    write(raw/'inputs/selected_rows.json',selected)
    for name in ['COMPLETE.json','AUDIT.json','config.json','source_manifest.json','block_manifest.json']:
        shutil.copy2(PARENT_RUN/name,raw/'inputs'/f'parent_{name}')
    parent_blocks=read(PARENT_RUN/'block_manifest.json')
    for block in sorted({r['block_id'] for r in selected}):
        source=PARENT_RUN/'blocks'/f'{block}.npz'
        assert sha(source)==parent_blocks[f'blocks/{block}.npz']
        shutil.copy2(source,raw/'inputs/blocks'/source.name)
    input_manifest={p.relative_to(raw).as_posix():sha(p) for p in sorted((raw/'inputs').rglob('*')) if p.is_file()}
    write(raw/'input_manifest.json',input_manifest)
    historical={p.relative_to(ROOT).as_posix():sha(p) for p in historical_paths()}
    write(raw/'historical_manifest.json',historical)
    lock=subprocess.run([sys.executable,'-m','pip','freeze'],capture_output=True,text=True,check=True)
    (raw/'environment-lock.txt').write_text(lock.stdout,encoding='utf-8')
    write(raw/'runtime.json',dict(utc=utc(),python=sys.version,numpy=np.__version__,platform=platform.platform(),
         executable=sys.executable,cpu_count=os.cpu_count(),free_disk_bytes=shutil.disk_usage(ROOT).free))
    write(raw/'FREEZE.json',dict(status='PASS',utc=utc(),source_sha256=manifest,
         config_sha256=sha(raw/'config.json'),input_manifest_sha256=sha(raw/'input_manifest.json'),
         checks_sha256=sha(raw/'CHECKS.json'),analysis_checks_sha256=sha(raw/'ANALYSIS_CHECKS.json'),
         design_review_sha256=sha(raw/'DESIGN_REVIEW.json'),historical_files=len(historical),
         new_objective_profiles_computed=False))
    print(json.dumps(dict(status='FROZEN',cases=1536,blocks=128,historical_files=len(historical))),flush=True)


def experiment(raw):
    verify_source(raw)
    freeze=read(raw/'FREEZE.json'); assert sha(raw/'config.json')==freeze['config_sha256']
    assert read(raw/'config.json')==configuration(raw.name)
    assert sha(raw/'input_manifest.json')==freeze['input_manifest_sha256']
    for name,digest in read(raw/'input_manifest.json').items(): assert sha(raw/name)==digest,name
    assert not (raw/'START.json').exists(),'No implicit resume'
    start=time.perf_counter(); started=datetime.now(timezone.utc)
    write(raw/'START.json',dict(utc=started.isoformat(),source_and_inputs_verified=True))
    (raw/'cases').mkdir()
    def budget():
        a=time.perf_counter()-start; b=(datetime.now(timezone.utc)-started).total_seconds()
        if max(a,b)>BUDGET_SECONDS: raise RuntimeError('Prespecified CPU budget exhausted; partial records preserved')
        return a,b
    count,block_hashes=0,{}
    selected=read(raw/'inputs/selected_rows.json')
    try:
        with (raw/'profiles.jsonl').open('x',encoding='utf-8') as stream:
            for block in sorted({r['block_id'] for r in selected}):
                budget()
                with np.load(raw/'inputs/blocks'/f'{block}.npz',allow_pickle=False) as z:
                    w=z['weights'].tolist(); gs=z['gains'].copy()
                cache=build_cache(w,GRID)  # clock includes all measured cache construction
                budget(); block_rows=[]
                for old in [r for r in selected if r['block_id']==block]:
                    budget(); case_start=time.perf_counter()
                    gains=gs[old['array_index']].tolist()
                    assert array_sha(w)==old['weights_sha256'] and array_sha(gains)==old['gains_sha256']
                    values=evaluate(w,gains,old['p'],cache)
                    assert values['legacy_reason']==old['reason']
                    if old['p'] is not None: assert values['original_point']['legacy_J']==old['objective']
                    row={key:old[key] for key in ['block_id','n','replicate','generator_p','c','truth_p',
                           'seed_weights','seed_noise','weights_sha256','gains_sha256']}
                    row.update(source_id=old['id'],source_array_index=old['array_index'],
                               original_p=old['p'],original_reason=old['reason'],original_objective=old['objective'],
                               **values,elapsed_seconds=time.perf_counter()-case_start)
                    stream.write(json.dumps(row,allow_nan=False)+'\n'); stream.flush()
                    block_rows.append(row); count+=1
                write(raw/'cases'/f'{block}.json',block_rows)
                block_hashes[f'cases/{block}.json']=sha(raw/'cases'/f'{block}.json')
                if len(block_hashes)%8==0:
                    print(json.dumps(dict(cases=count,blocks=len(block_hashes),elapsed_seconds=budget()[0])),flush=True)
        write(raw/'case_manifest.json',block_hashes); verify_source(raw)
        digest=sha(raw/'profiles.jsonl'); elapsed,utc_elapsed=budget()
        write(raw/'COMPLETE.json',dict(status='COMPLETE',utc=utc(),cases=count,blocks=len(block_hashes),
             elapsed_seconds=elapsed,utc_elapsed_seconds=utc_elapsed,
             peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
             profiles_sha256=digest,failed_cases=[],training=False,original_estimates_modified=False))
        print(json.dumps(read(raw/'COMPLETE.json')),flush=True)
    except BaseException as exc:
        write(raw/'FAILURE.json',dict(status='FAILED',utc=utc(),completed_cases=count,error=repr(exc),case_manifest=block_hashes))
        raise


def main():
    p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True)
    p.add_argument('--phase',choices=['prepare','experiment'],required=True)
    p.add_argument('--checks',default='work/stage8-checks-20260930-01.json')
    p.add_argument('--analysis-checks',default='work/stage8-analysis-checks-20260930-01.json')
    p.add_argument('--review',default='work/stage8-design-review-20260930-01.json'); a=p.parse_args()
    assert a.run_id and a.run_id not in ['.','..'] and '/' not in a.run_id and '\\' not in a.run_id
    assert a.run_id.startswith('precision-v09-'),'Use the versioned precision-v09- run prefix'
    raw=ROOT/'work/runs'/a.run_id
    if a.phase=='prepare': prepare(raw,ROOT/a.checks,ROOT/a.analysis_checks,ROOT/a.review)
    else: experiment(raw)


if __name__=='__main__': main()
