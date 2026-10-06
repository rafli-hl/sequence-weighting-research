"""Stage9: source-bound CPU precision audit of saved model gains."""
import argparse
from collections import Counter
import hashlib
import json
import os
import platform
import resource
import shutil
import subprocess
import sys
import time
sys.dont_write_bytecode = True
import numpy as np
import torch
from common_stage9 import (ROOT,HERE,SOURCES,Budget,array_sha,tensor_array_sha,
    configuration,historical_paths,read,sha,utc,verify_inputs,verify_source,write)
from inputs_stage4 import collect as collect4
from inputs_stage56 import collect as collect56
from precision_math import GRID,build_cache,evaluate


def inventory():
    references,files=[],set()
    for result in [collect4(ROOT),collect56(ROOT)]:
        references.extend(result['references']); files.update(result['source_files'])
    references.sort(key=lambda r:r['reference_id'])
    assert len(references)==len({r['reference_id'] for r in references})==324
    assert len({r['native_id'] for r in references})==207
    profiles,arrays={},{}
    for ref in references:
        a=ref.pop('arrays'); ref.setdefault('arm','random')
        assert set(a)=={'weights','initial_loss','current_loss','gains'}
        assert all(x.shape==(512,) and np.isfinite(x).all() for x in a.values())
        assert all(a[k].dtype==np.dtype('float32') for k in ['weights','initial_loss','current_loss'])
        assert a['gains'].dtype==np.dtype('float64') and (a['weights']>0).all()
        assert np.array_equal(a['gains'],np.subtract(a['initial_loss'],a['current_loss'],dtype=np.float32).astype(np.float64))
        ref['array_hashes']={k:tensor_array_sha(v) for k,v in a.items()}
        wh,gh=array_sha(a['weights']),array_sha(a['gains'])
        identity=hashlib.sha256(np.asarray(a['weights'],dtype='<f8').tobytes()+np.asarray(a['gains'],dtype='<f8').tobytes()).hexdigest()
        sid='input-'+identity[:24]
        ref.update(source_id=sid,profile_id=sid,weights_sha256=wh,gains_sha256=gh,weightgroup=wh)
        fit=ref['original_fit']; oldp=fit.get('p'); oldobj=fit.get('objective'); reason=fit.get('reason')
        expected='nonpositive_total_gain' if reason=='no_adaptation' else reason
        # No numerical objective or new estimator decision is evaluated here.
        if sid not in profiles:
            profiles[sid]=dict(source_id=sid,input_sha256=identity,n=512,weightgroup=wh,
                weights_sha256=wh,gains_sha256=gh,original_p=oldp,original_objective=oldobj,
                original_reason=reason,expected_guard=expected,reference_ids=[],native_ids=[])
            arrays[sid]=a
        p=profiles[sid]
        assert p['input_sha256']==identity
        assert (p['original_p'],p['original_objective'],p['original_reason'],p['expected_guard'])==(oldp,oldobj,reason,expected)
        assert np.array_equal(arrays[sid]['weights'],a['weights']) and np.array_equal(arrays[sid]['gains'],a['gains'])
        p['reference_ids'].append(ref['reference_id']); p['native_ids'].append(ref['native_id'])
    profiles=[profiles[k] for k in sorted(profiles)]
    for p in profiles: p['native_ids']=sorted(set(p['native_ids']))
    assert len(profiles)==186 and len({p['weightgroup'] for p in profiles})==9
    manifest={name:sha(ROOT/name) for name in sorted(files)}
    signature=hashlib.sha256(json.dumps(dict(references=references,profiles=profiles,origin_manifest=manifest),
        sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()
    summary=dict(status='PASS',utc=utc(),policy_references=len(references),native_checkpoints=207,
        unique_inputs=len(profiles),weight_groups=9,source_files=len(manifest),
        source_bytes=sum((ROOT/p).stat().st_size for p in manifest),input_signature=signature,
        cohort_counts=dict(Counter(r['cohort'] for r in references)),
        original_reason_counts=dict(Counter(str(r['original_fit'].get('reason')) for r in references)),
        native_by_stage={str(stage):len({r['native_id'] for r in references if r['stage']==stage}) for stage in [4,5,6]},
        unique_by_stage={str(stage):len({r['source_id'] for r in references if r['stage']==stage}) for stage in [4,5,6]},
        measured_objective_profiles_read_or_computed=False,
        loader_sha256={name:sha(HERE/name) for name in ['inputs_stage4.py','inputs_stage56.py','stage9.py','common_stage9.py']})
    return references,profiles,arrays,manifest,summary


def verify_full_pairing(raw,references):
    datasets,orders,weights,initials={},{},{},{}
    snapshots=raw/'inputs/source-files'
    for ref in references:
        key=(ref['stage'],ref['data_seed'])
        path=ref['source_paths']['dataset']
        if key not in datasets:
            original=torch.load(ROOT/path,map_location='cpu',weights_only=True)
            copied=torch.load(snapshots/path,map_location='cpu',weights_only=True)
            assert set(original)==set(copied)
            for split in original:
                assert len(original[split])==len(copied[split])==2
                for x,y in zip(original[split],copied[split]):
                    assert x.dtype==y.dtype and x.shape==y.shape and torch.equal(x,y)
                tokens=original[split][0]; copytokens=copied[split][0]
                assert torch.equal(tokens[:,:-1],copytokens[:,:-1])
                assert torch.equal(tokens[:,1:],copytokens[:,1:])
            datasets[key]=path
        assert datasets[key]==path
        assignment=torch.load(snapshots/ref['source_paths']['assignment'],map_location='cpu',weights_only=True)
        pair=(ref['stage'],ref['data_seed'],ref['seed'])
        if pair in weights: assert torch.equal(weights[pair],assignment['weights'])
        else: weights[pair]=assignment['weights']
        if pair in orders:
            n=min(len(orders[pair]),len(assignment['orders']))
            assert torch.equal(orders[pair][:n],assignment['orders'][:n])
        else: orders[pair]=assignment['orders']
        initkey=(ref['stage'],ref['variant'],ref['width'],ref['data_seed'],ref['seed'])
        inithash=ref['array_hashes']['initial_loss']
        if initkey in initials: assert initials[initkey]==inithash
        else: initials[initkey]=inithash
    return dict(status='PASS',datasets=len(datasets),weight_order_pairs=len(weights),
        initial_groups=len(initials),full_tokens_labels_kinds_checked=True,
        source_and_snapshot_tensor_equality=True,paired_batch_order_prefix_equality=True,
        pairing_scope='Within each stage/data/model-seed; initialization equal only within variant/capacity')


def prepare(raw,checks_path,analysis_path,review_path,inventory_path):
    clock=Budget(1800)
    assert not raw.exists(),'Refusing existing run'
    manifest={name:sha(HERE/name) for name in SOURCES}
    for path in [checks_path,analysis_path,review_path]:
        evidence=read(path); assert evidence['status']=='PASS'
        assert evidence['source_sha256']
        for name,digest in evidence['source_sha256'].items(): assert manifest[name]==digest,name
    assert read(checks_path)['source_sha256']==manifest
    refs,profiles,arrays,origins,summary=inventory(); clock.check()
    earlier=read(inventory_path)
    assert earlier['status']=='PASS' and earlier['input_signature']==summary['input_signature']
    cfg=configuration(raw.name)
    assert summary['source_bytes']<=cfg['max_snapshot_bytes']
    assert shutil.disk_usage(ROOT).free>=cfg['min_free_bytes']
    raw.mkdir(parents=True); (raw/'source').mkdir(); (raw/'inputs/arrays').mkdir(parents=True)
    for name in SOURCES: shutil.copy2(HERE/name,raw/'source'/name)
    write(raw/'source_manifest.json',manifest)
    for path,name in [(checks_path,'CHECKS.json'),(analysis_path,'ANALYSIS_CHECKS.json'),
                      (review_path,'DESIGN_REVIEW.json'),(inventory_path,'INVENTORY.json')]:
        shutil.copy2(path,raw/name)
    write(raw/'config.json',cfg)
    write(raw/'inputs/references.json',refs); write(raw/'inputs/profiles.json',profiles)
    write(raw/'inputs/origin_manifest.json',origins)
    for name,digest in origins.items():
        clock.check(); target=raw/'inputs/source-files'/name
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/name,target)
        assert sha(target)==sha(ROOT/name)==digest,name
    for sid,values in arrays.items(): np.savez(raw/'inputs/arrays'/f'{sid}.npz',**values)
    write(raw/'inputs/PAIRING.json',verify_full_pairing(raw,refs)); clock.check()
    # Independent extraction checks only original arrays/metadata here, before
    # FREEZE; numerical profile evaluation remains in the subsequent phases.
    from audit_stage9 import provenance
    write(raw/'inputs/PROVENANCE_CHECK.json',dict(status='PASS',**provenance(raw,clock)))
    inputs={p.relative_to(raw).as_posix():sha(p) for p in sorted((raw/'inputs').rglob('*')) if p.is_file()}
    write(raw/'input_manifest.json',inputs)
    historical={}
    for path in historical_paths():
        clock.check(); historical[path.relative_to(ROOT).as_posix()]=sha(path)
    write(raw/'historical_manifest.json',historical)
    lock=subprocess.run([sys.executable,'-m','pip','freeze'],capture_output=True,text=True,check=True)
    (raw/'environment-lock.txt').write_text(lock.stdout,encoding='utf-8')
    elapsed,utc_elapsed=clock.check()
    write(raw/'runtime.json',dict(utc=utc(),python=sys.version,numpy=np.__version__,torch=torch.__version__,
        platform=platform.platform(),executable=sys.executable,cpu_count=os.cpu_count(),
        preparation_elapsed_seconds=elapsed,preparation_utc_elapsed_seconds=utc_elapsed,
        preparation_peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        free_disk_bytes=shutil.disk_usage(ROOT).free,source_snapshot_bytes=summary['source_bytes']))
    verify_source(raw)
    write(raw/'FREEZE.json',dict(status='PASS',utc=utc(),source_sha256=manifest,
        config_sha256=sha(raw/'config.json'),input_manifest_sha256=sha(raw/'input_manifest.json'),
        checks_sha256=sha(raw/'CHECKS.json'),analysis_checks_sha256=sha(raw/'ANALYSIS_CHECKS.json'),
        design_review_sha256=sha(raw/'DESIGN_REVIEW.json'),inventory_sha256=sha(raw/'INVENTORY.json'),
        input_signature=summary['input_signature'],historical_files=len(historical),
        historical_manifest_sha256=sha(raw/'historical_manifest.json'),
        historical_coverage='all prior stage outputs excluding caches; prior raw top-level/source/analysis-source files; selected raw arrays additionally bound by origin manifest; model binaries not rehashed',
        new_objective_profiles_computed=False))
    print(json.dumps(dict(status='FROZEN',cases=len(profiles),references=len(refs),historical_files=len(historical))),flush=True)


def experiment(raw):
    assert not (raw/'START.json').exists(),'No implicit resume'
    clock=Budget()  # includes input/source verification and all cache construction
    verify_source(raw); profiles=verify_inputs(raw); clock.check()
    write(raw/'START.json',dict(utc=clock.started_utc,source_and_inputs_verified=True))
    (raw/'cases').mkdir(); count=0; case_hashes={}; groups=0; sid=None; group=None
    try:
        with (raw/'profiles.jsonl').open('x',encoding='utf-8') as stream:
            for group in sorted({p['weightgroup'] for p in profiles}):
                clock.check(); selected=[p for p in profiles if p['weightgroup']==group]
                with np.load(raw/'inputs/arrays'/f"{selected[0]['source_id']}.npz",allow_pickle=False) as z:
                    w=z['weights'].astype(np.float64).tolist()
                cache=build_cache(w,GRID); clock.check()
                for old in selected:
                    clock.check(); case_start=time.perf_counter(); sid=old['source_id']
                    with np.load(raw/'inputs/arrays'/f'{sid}.npz',allow_pickle=False) as z:
                        assert array_sha(z['weights'])==old['weights_sha256']
                        gains=z['gains'].tolist(); assert array_sha(gains)==old['gains_sha256']
                    values=evaluate(w,gains,old['original_p'],cache)
                    row=dict(old,**values,elapsed_seconds=time.perf_counter()-case_start)
                    stream.write(json.dumps(row,allow_nan=False)+'\n'); stream.flush()
                    write(raw/'cases'/f'{sid}.json',row)
                    case_hashes[f'cases/{sid}.json']=sha(raw/'cases'/f'{sid}.json')
                    assert values['legacy_reason']==old['expected_guard']
                    if old['original_p'] is not None:
                        assert values['original_point']['legacy_J']==old['original_objective']
                    count+=1
                groups+=1
                print(json.dumps(dict(cases=count,weight_groups=groups,elapsed_seconds=clock.check()[0])),flush=True)
        assert count==186 and groups==9
        write(raw/'case_manifest.json',case_hashes); verify_source(raw); verify_inputs(raw)
        elapsed,utc_elapsed=clock.check()
        write(raw/'COMPLETE.json',dict(status='COMPLETE',utc=utc(),cases=count,blocks=groups,
            policy_references=324,native_checkpoints=207,weight_groups=groups,
            elapsed_seconds=elapsed,utc_elapsed_seconds=utc_elapsed,
            peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
            profiles_sha256=sha(raw/'profiles.jsonl'),failed_cases=[],training=False,original_estimates_modified=False))
        print(json.dumps(read(raw/'COMPLETE.json')),flush=True)
    except BaseException as exc:
        from datetime import datetime,timezone
        write(raw/'FAILURE.json',dict(status='FAILED',utc=utc(),completed_cases=count,error=repr(exc),
            active_source_id=sid,active_weightgroup=group,case_manifest=case_hashes,
            elapsed_seconds=time.perf_counter()-clock.start,
            utc_elapsed_seconds=(datetime.now(timezone.utc)-clock.started).total_seconds(),
            peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
        raise


def main():
    p=argparse.ArgumentParser(); p.add_argument('--run-id',required=True)
    p.add_argument('--phase',choices=['inventory','prepare','experiment'],required=True)
    p.add_argument('--checks',default='work/stage9-checks-20260930-01.json')
    p.add_argument('--analysis-checks',default='work/stage9-analysis-checks-20260930-01.json')
    p.add_argument('--review',default='work/stage9-design-review-20260930-01.json')
    p.add_argument('--inventory',default='work/stage9-inventory-20260930-01.json'); a=p.parse_args()
    assert a.run_id.startswith('model-precision-v010-') and '/' not in a.run_id and '\\' not in a.run_id
    raw=ROOT/'work/runs'/a.run_id
    if a.phase=='inventory':
        *_,summary=inventory(); write(ROOT/a.inventory,summary); print(json.dumps(summary),flush=True)
    elif a.phase=='prepare': prepare(raw,ROOT/a.checks,ROOT/a.analysis_checks,ROOT/a.review,ROOT/a.inventory)
    else: experiment(raw)


if __name__=='__main__': main()
