"""Supervise and retain all changed preparation fixture attempts (180 s total)."""
import time
START_MONO=time.perf_counter()
START_WALL=time.time()
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LIMIT=180.


def write(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--attempt',required=True)
    args=parser.parse_args()
    if not args.attempt.isalnum():
        raise ValueError('Alphanumeric unique attempt name required')
    ledger=HERE/'fixture-attempts'
    ledger.mkdir(exist_ok=True)
    # Preserve the existing 180-second total across v0121 and v0122.
    prior=0.
    prior_ledger=HERE.parent/'sequence-weighting-stage11-v0121'/'fixture-attempts'
    if not prior_ledger.is_dir():
        raise RuntimeError('Historical fixture ledger missing; fail closed')
    for path in [*prior_ledger.iterdir(), *ledger.iterdir()]:
        if not path.is_dir():
            continue
        if not (path/'ATTEMPT.json').exists():
            raise RuntimeError('Previous fixture attempt unfinished; fail closed')
        saved=json.loads((path/'ATTEMPT.json').read_text(encoding='utf-8'))
        if saved['status']=='BUDGET_EXCEEDED':
            raise RuntimeError('Earlier fixture attempt exhausted its accounting allowance')
        charge=saved['charged_seconds']
        if not isinstance(charge,(int,float)) or not 0 <= charge <= LIMIT:
            raise RuntimeError('Invalid historical fixture charge')
        prior+=charge
    if prior>=LIMIT:
        raise RuntimeError('Cumulative fixture budget exhausted')
    folder=ledger/args.attempt
    folder.mkdir(exist_ok=False)
    sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.iterdir()
             if p.is_file() and p.suffix in {'.py','.md'}}
    write(folder/'STARTED.json',dict(start_monotonic=START_MONO,start_unix=START_WALL,
                                   prior_seconds=prior,limit_seconds=LIMIT,source_sha256=sources))
    status='FAILED';error=None;code=None
    try:
        remaining=LIMIT-prior-1.-max(time.perf_counter()-START_MONO,time.time()-START_WALL)
        if remaining<=0:
            raise TimeoutError('Fixture allowance exhausted during setup')
        with (folder/'stdout.txt').open('w',encoding='utf-8') as stdout, \
             (folder/'stderr.txt').open('w',encoding='utf-8') as stderr:
            result=subprocess.run([sys.executable,str(HERE/'check_preparation.py'),
                '--output',str(folder/'CHECKS.json'),'--artifacts-dir',str(folder/'artifacts'),
                '--prior-fixture-seconds',str(prior)],cwd=ROOT,stdout=stdout,stderr=stderr,
                timeout=remaining,check=False)
        code=result.returncode
        status='PASS' if code==0 else 'FAILED'
        if status=='PASS':
            report=json.loads((folder/'CHECKS.json').read_text(encoding='utf-8'))
            if report['status']!='PASS' or report['source_sha256']!=sources:
                raise RuntimeError('Fixture success report missing, failed or source-mismatched')
    except BaseException as exc:
        error=repr(exc)
        status='FAILED'
    elapsed_mono=time.perf_counter()-START_MONO
    elapsed_wall=time.time()-START_WALL
    elapsed=max(elapsed_mono,elapsed_wall)
    if prior+elapsed>LIMIT:
        status='BUDGET_EXCEEDED'
    current={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.iterdir()
             if p.is_file() and p.suffix in {'.py','.md'}}
    if current!=sources:
        status='SOURCE_CHANGED_DURING_CHECKS'
    # One second is a charged reserve, not a measured duration. The post-write
    # guard below enforces that this reserve covers remaining supervisor work.
    charged=max(time.perf_counter()-START_MONO,time.time()-START_WALL)+1.
    if prior+charged>LIMIT:
        status='BUDGET_EXCEEDED'
    record=dict(status=status,returncode=code,error=error,elapsed_seconds=elapsed,
        monotonic_seconds=elapsed_mono,utc_seconds=elapsed_wall,
        charged_seconds=charged,bookkeeping_reserve_seconds=1.,
        cumulative_seconds=prior+charged,limit_seconds=LIMIT,source_sha256=sources,
        timing_observation='after subprocess termination; before supervisor record write',
        research_models_computed=False)
    write(folder/'ATTEMPT.json',record)
    final=max(time.perf_counter()-START_MONO,time.time()-START_WALL)
    if prior+final>LIMIT or final>charged:
        record.update(status='BUDGET_EXCEEDED',elapsed_seconds=final,
                      charged_seconds=max(final,charged),cumulative_seconds=prior+max(final,charged))
        write(folder/'ATTEMPT.json',record)
        status='BUDGET_EXCEEDED'
    print(json.dumps({key:record[key] for key in
        ['status','returncode','error','elapsed_seconds','charged_seconds','cumulative_seconds']}),flush=True)
    if status!='PASS':
        raise SystemExit(1)


if __name__=='__main__':
    main()
