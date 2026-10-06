"""One bounded local CPU search diagnostic; immutable preparation and run files."""
import argparse
from collections import Counter
import json
import os
import platform
import resource
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
sys.dont_write_bytecode=True
import numpy as np
import torch
from common_stage10 import (ROOT,HERE,PARENT,PARENT_SOURCE,PARENT_REPORT,SOURCES,Budget,
    BudgetExceeded,array_sha,configuration,historical_paths,read,sha,utc,verify_inputs,verify_source,write)
from inputs import provenance
import search_math
import independent_math
from audit_stage10 import compare

PARENT_REVIEW='FINAL_REVIEW-model-precision-v010-20260930-01-r2.json'
PARENT_REVIEW_SHA='1189da54667d52bbc5613869cc0d2ffaefc74506defa0c3310a67a212f6f72d0'


def prepare(raw,checks_path,analysis_path,review_path):
    timer=Budget(1800); cfg=configuration(raw.name)
    assert not raw.exists(),'Refusing existing run; preserve partial attempts'
    manifest={name:sha(HERE/name) for name in SOURCES}
    for path in [checks_path,analysis_path,review_path]:
        evidence=read(path); assert evidence['status']=='PASS'
        assert evidence['source_sha256']
        for name,digest in evidence['source_sha256'].items(): assert manifest[name]==digest,name
    assert read(checks_path)['source_sha256']==read(review_path)['source_sha256']==manifest
    assert sha(PARENT_SOURCE/PARENT_REVIEW)==PARENT_REVIEW_SHA
    final=read(PARENT_SOURCE/PARENT_REVIEW); assert final['status']=='PASS'
    assert read(PARENT/'AUDIT.json')['status']=='PASS'
    parent_manifest=read(PARENT_REPORT/'raw-manifest.json')
    for name,digest in parent_manifest.items():
        timer.check(); assert sha(PARENT/name)==digest,name
    assert sha(PARENT_REPORT/'run-records.zip')==final['archive_sha256']
    with zipfile.ZipFile(PARENT_REPORT/'run-records.zip') as bundle:
        for name in ['policy-reference-metrics.jsonl','profile-metrics.jsonl','analysis-provenance.json','raw-manifest.json']:
            timer.check()
            assert bundle.read('report/'+name)==(PARENT_REPORT/name).read_bytes(),name
    parent_inputs=read(PARENT/'input_manifest.json')
    assert sha(PARENT/'input_manifest.json')==read(PARENT/'FREEZE.json')['input_manifest_sha256']
    assert all(name.startswith('inputs/') for name in parent_inputs)
    size=sum((PARENT/name).stat().st_size for name in parent_inputs)
    assert size<=cfg['max_snapshot_bytes'] and shutil.disk_usage(ROOT).free>=cfg['min_free_bytes']
    raw.mkdir(parents=True); (raw/'source').mkdir()
    for name in SOURCES: shutil.copy2(HERE/name,raw/'source'/name)
    write(raw/'source_manifest.json',manifest); write(raw/'config.json',cfg)
    for path,name in [(checks_path,'CHECKS.json'),(analysis_path,'ANALYSIS_CHECKS.json'),(review_path,'DESIGN_REVIEW.json')]:
        shutil.copy2(path,raw/name)
    for name,digest in parent_inputs.items():
        timer.check(); target=raw/name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(PARENT/name,target); assert sha(target)==digest
    bindings={}
    def copy_bound(source,target):
        timer.check(); target=raw/target; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target); digest=sha(source); assert sha(target)==digest
        bindings[target.relative_to(raw).as_posix()]=dict(source=source.relative_to(ROOT).as_posix(),sha256=digest)
    for source,name in [(PARENT_REPORT/'policy-reference-metrics.jsonl','stage9_policy_context.jsonl'),
                        (PARENT_REPORT/'profile-metrics.jsonl','stage9_profile_context.jsonl')]:
        copy_bound(source,'inputs/'+name)
    for name in ['FREEZE.json','COMPLETE.json','AUDIT.json','source_manifest.json','input_manifest.json']:
        copy_bound(PARENT/name,'inputs/parent/'+name)
    for name in read(PARENT/'source_manifest.json'):
        copy_bound(PARENT/'source'/name,'inputs/parent/source/'+name)
    for source,name in [(PARENT_SOURCE/PARENT_REVIEW,'FINAL_REVIEW.json'),
                        (PARENT_REPORT/'raw-manifest.json','raw-manifest.json'),
                        (PARENT_REPORT/'analysis-provenance.json','analysis-provenance.json')]:
        copy_bound(source,'inputs/parent/'+name)
    write(raw/'inputs/PARENT_BINDINGS.json',bindings)
    # Reconstruct every alias, dataset token/label, initialization and float32 subtraction.
    write(raw/'inputs/STAGE10_PROVENANCE.json',dict(status='PASS',**provenance(raw,timer)))
    assert sum(p.stat().st_size for p in (raw/'inputs').rglob('*') if p.is_file())<=cfg['max_snapshot_bytes']
    inputs={p.relative_to(raw).as_posix():sha(p) for p in sorted((raw/'inputs').rglob('*')) if p.is_file()}
    write(raw/'input_manifest.json',inputs)
    historical={}
    for path in historical_paths():
        timer.check(); historical[path.relative_to(ROOT).as_posix()]=sha(path)
    write(raw/'historical_manifest.json',historical)
    lock=subprocess.run([sys.executable,'-m','pip','freeze'],capture_output=True,text=True,check=True)
    (raw/'environment-lock.txt').write_text(lock.stdout,encoding='utf-8')
    elapsed,wall=timer.check()
    write(raw/'runtime.json',dict(utc=utc(),python=sys.version,numpy=np.__version__,torch=torch.__version__,
        platform=platform.platform(),executable=sys.executable,cpu_count=os.cpu_count(),
        preparation_elapsed_seconds=elapsed,preparation_utc_elapsed_seconds=wall,
        preparation_peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        copied_input_bytes=sum((raw/name).stat().st_size for name in inputs),free_disk_bytes=shutil.disk_usage(ROOT).free))
    verify_source(raw)
    write(raw/'FREEZE.json',dict(status='PASS',utc=utc(),source_sha256=manifest,
        config_sha256=sha(raw/'config.json'),input_manifest_sha256=sha(raw/'input_manifest.json'),
        historical_manifest_sha256=sha(raw/'historical_manifest.json'),historical_files=len(historical),
        historical_coverage='all prior outputs excluding caches; prior raw top-level and frozen source; selected model arrays bound by provenance; not all model binaries',
        checks_sha256=sha(raw/'CHECKS.json'),analysis_checks_sha256=sha(raw/'ANALYSIS_CHECKS.json'),
        design_review_sha256=sha(raw/'DESIGN_REVIEW.json'),new_objective_profiles_computed=False))
    print(json.dumps(dict(status='FROZEN',run_id=raw.name,inputs=186,references=324,source_files=len(manifest))),flush=True)


def experiment(raw):
    assert (raw/'FREEZE.json').exists() and not (raw/'START.json').exists(),'No implicit resume'
    timer=Budget(); write(raw/'START.json',dict(utc=timer.started_utc,shared_budget_seconds=timer.limit))
    for name in ['primary','reference','comparison']: (raw/name).mkdir()
    completed=[]; rows=[]; group=None; sid=None; error=None; verified=False; prov=None
    status='FAILED'
    with (raw/'results.jsonl').open('x',encoding='utf-8') as stream:
        try:
            source=verify_source(raw); profiles=verify_inputs(raw); timer.check()
            prov=provenance(raw,timer); verified=True
            for group in sorted({p['weightgroup'] for p in profiles}):
                timer.check(); selected=[p for p in profiles if p['weightgroup']==group]
                with np.load(raw/'inputs/arrays'/f"{selected[0]['source_id']}.npz",allow_pickle=False) as z:
                    w=z['weights'].astype(np.float64).tolist()
                group_start=time.perf_counter()
                pcache=search_math.build_cache(w,budget=timer.check)
                rcache=independent_math.build_cache(w,budget=timer.check)
                print(json.dumps(dict(group=group,cache_elapsed_seconds=time.perf_counter()-group_start,completed=len(completed))),flush=True)
                for old in selected:
                    timer.check(); begin=time.perf_counter(); sid=old['source_id']
                    with np.load(raw/'inputs/arrays'/f'{sid}.npz',allow_pickle=False) as z:
                        assert array_sha(z['weights'])==old['weights_sha256']==array_sha(w)
                        gains=z['gains'].tolist(); assert array_sha(gains)==old['gains_sha256']
                    primary=search_math.evaluate(w,gains,old['original_p'],pcache,budget=timer.check)
                    write(raw/'primary'/f'{sid}.json',primary)
                    reference=independent_math.evaluate(w,gains,old['original_p'],rcache,budget=timer.check)
                    write(raw/'reference'/f'{sid}.json',reference)
                    row=compare(old,primary,reference,gains,pcache,rcache,budget=timer.check)
                    row['elapsed_seconds']=time.perf_counter()-begin
                    write(raw/'comparison'/f'{sid}.json',row)
                    compact={k:v for k,v in row.items() if k!='point_checks'}
                    stream.write(json.dumps(compact,allow_nan=False)+'\n'); stream.flush(); os.fsync(stream.fileno())
                    completed.append(sid); rows.append(compact)
                    print(json.dumps(dict(completed=len(completed),planned=186,source_id=sid,status=row['status'],elapsed_seconds=timer.elapsed()[0])),flush=True)
                del pcache,rcache
            verify_source(raw); verify_inputs(raw); timer.check()
            assert len(completed)==186; status='COMPLETE'
        except BaseException as exc:
            status='BUDGET_EXHAUSTED' if isinstance(exc,BudgetExceeded) else 'FAILED'
            error=dict(error=repr(exc),traceback=traceback.format_exc())
    # Administrative sealing/reporting below performs no numerical search.
    elapsed,wall=timer.elapsed(); planned=read(raw/'inputs/profiles.json')
    case_manifest={p.relative_to(raw).as_posix():sha(p) for name in ['primary','reference','comparison']
                   for p in sorted((raw/name).glob('*.json'))}
    write(raw/'case_manifest.json',case_manifest)
    resultsha=sha(raw/'results.jsonl')
    write(raw/'END.json',dict(status=status,utc=utc(),run_id=raw.name,elapsed_seconds=elapsed,
        utc_elapsed_seconds=wall,shared_budget_seconds=timer.limit,completed_cases=len(completed),
        planned_cases=186,completed_source_ids=completed,remaining_source_ids=[p['source_id'] for p in planned if p['source_id'] not in completed],
        active_weightgroup=group,active_source_id=sid,error=error,results_sha256=resultsha,
        peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,automatic_retry=False))
    # Verify immutable storage, without adding numerical computations after the ceiling.
    storage_errors=[]
    try:
        source=verify_source(raw); verify_inputs(raw)
        for name,digest in read(raw/'historical_manifest.json').items(): assert sha(ROOT/name)==digest,name
        for name,digest in case_manifest.items(): assert sha(raw/name)==digest,name
        for row in rows:
            full=read(raw/'comparison'/f"{row['source_id']}.json")
            assert row=={k:v for k,v in full.items() if k!='point_checks'}
    except BaseException as exc: storage_errors.append(repr(exc))
    write(raw/'AUDIT.json',dict(status='FAIL' if storage_errors or not verified else 'PASS' if status=='COMPLETE' else 'PARTIAL',
        utc=utc(),results_sha256=resultsha,source_sha256=read(raw/'source_manifest.json'),
        case_manifest_sha256=sha(raw/'case_manifest.json'),provenance=prov,storage_errors=storage_errors,
        completed_cases=len(completed),planned_cases=186,status_counts=dict(Counter(r['status'] for r in rows)),
        unresolved_source_ids=[r['source_id'] for r in rows if r['classification']['unresolved']],
        precision_checks=sum(len(read(raw/'comparison'/f'{sid}.json')['point_checks']) for sid in completed),
        shared_numerical_budget_enforced=True,global_optimality_certified=False))
    print(json.dumps(dict(status=status,completed=len(completed),elapsed_seconds=elapsed,error=error)),flush=True)
    if storage_errors or not verified: raise RuntimeError('Storage/provenance audit failed; inspect AUDIT.json')


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--run-id',required=True)
    parser.add_argument('--phase',choices=['prepare','experiment'],required=True)
    parser.add_argument('--checks',type=__import__('pathlib').Path,default=HERE/'CHECKS.json')
    parser.add_argument('--analysis-checks',type=__import__('pathlib').Path,default=HERE/'ANALYSIS_CHECKS.json')
    parser.add_argument('--review',type=__import__('pathlib').Path,default=HERE/'DESIGN_REVIEW.json')
    args=parser.parse_args(); assert args.run_id.startswith('search-v011-') and '/' not in args.run_id and '\\' not in args.run_id
    raw=ROOT/'work/runs'/args.run_id
    if args.phase=='prepare': prepare(raw,args.checks,args.analysis_checks,args.review)
    else: experiment(raw)


if __name__=='__main__': main()
