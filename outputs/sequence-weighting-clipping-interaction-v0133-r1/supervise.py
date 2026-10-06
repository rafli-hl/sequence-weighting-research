"""Manual Ubuntu phase supervisor: hard cumulative cap, no retries/resume."""
import time
START = time.monotonic()
WALL_START = time.time()
import argparse
import os
import signal
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
sys.dont_write_bytecode = True
from common import (HERE, RUN, OUT, require, read, write, sha, utc, resources,
                    verify_manifest, verify_review, RECEIPT_RESERVE, MAX_BYTES, RUNTIME_LIMIT)

def stop_signal(number, frame):
    raise RuntimeError('Supervisor interrupted by signal '+str(number))

signal.signal(signal.SIGTERM,stop_signal)
signal.signal(signal.SIGINT,stop_signal)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('prepare','pretrain','adapt','audit'))
    parser.add_argument('--review', required=True, type=Path)
    args = parser.parse_args()
    receipts = HERE/'receipts'
    receipts.mkdir(exist_ok=True)
    latch = receipts/'FAILED.json'
    prefix = receipts/args.phase
    require(not latch.exists(), 'Terminal failure; no retries or regeneration')
    require(not prefix.with_suffix('.admission.json').exists(), 'Phase already attempted; no resume')
    # Admission is written before validation; a rejected admission is terminal too.
    admission_path = prefix.with_suffix('.admission.json')
    initial = dict(phase=args.phase, utc_start=datetime.fromtimestamp(WALL_START,timezone.utc).isoformat(),
                   monotonic_start=START, wall_start=WALL_START, pid=os.getpid())
    write(admission_path, initial)
    process = None
    reason = None
    status = 'FAILED'
    work_seconds = 0
    source_sha = None
    prior = 0
    stdout_path = prefix.with_suffix('.stdout.log')
    stderr_path = prefix.with_suffix('.stderr.log')
    pumps = []
    pipe_errors = []
    def pump(stream, path):
        count = 0
        try:
            with path.open('xb') as target:
                while True:
                    chunk = stream.read(4096)
                    if not chunk: break
                    count += len(chunk)
                    require(count <= 2*2**20, 'Phase log cap exceeded')
                    target.write(chunk)
                    target.flush()
        except BaseException as error:
            pipe_errors.append(str(error))
    try:
        source_sha = verify_manifest()
        review = verify_review(args.review)
        resources()
        runtime_phases = ('prepare','pretrain','adapt')
        if args.phase in runtime_phases:
            index = runtime_phases.index(args.phase)
            for phase in runtime_phases[:index]:
                receipt = read(receipts/(phase+'.exit.json'))
                require(receipt['status']=='COMPLETE' and receipt['exit_code']==0,
                        'Missing successful predecessor receipt')
                require(receipt['manifest_sha256']==source_sha, 'Predecessor source drift')
                post=read(receipts/(phase+'.postwrite.json'))
                require(post['receipt_sha256']==sha(receipts/(phase+'.exit.json')), 'Receipt binding changed')
                prior += post['elapsed_seconds'] + 1.0
            if index == 0:
                require(not RUN.exists() and not OUT.exists(), 'Run/output already exists')
            else:
                require(RUN.exists(), 'Missing run inputs')
            remaining = RUNTIME_LIMIT-prior
        else:
            outer=read(receipts/'outer-runtime.exit.json')
            containment=read(receipts/'outer-runtime.containment.json')
            require(outer['containment_sha256']==sha(receipts/'outer-runtime.containment.json') and
                    containment['registered_before_phase_exec'] is True and
                    containment['survivors_at_outer_return'] is False and containment['termination_confirmed'] is True and
                    containment['timing_wrapper_reaped'] is True and containment['cancellation_exit_code']==0,
                    'Missing independently confirmed runtime group termination')
            outer_post=read(receipts/'outer-runtime.postwrite.json')
            require(outer['exit_code']==0 and outer['elapsed_ns_before_receipt']<RUNTIME_LIMIT*10**9 and
                    outer_post['after_exit_receipt_ns']-outer_post['start_ns']<RUNTIME_LIMIT*10**9,
                    'Missing successful inclusive outer runtime receipts')
            receipt = read(receipts/'adapt.exit.json')
            require(receipt['status']=='COMPLETE' and receipt['exit_code']==0,
                    'Audit requires successful adaptation receipt')
            require(not OUT.exists(), 'Audit output already exists')
            remaining = 600
        # Reserve 15 seconds INSIDE the phase/cumulative allowance for termination
        # and receipt I/O; no subprocess start if insufficient allowance remains.
        work_seconds = remaining-15
        require(work_seconds > max(time.monotonic()-START,time.time()-WALL_START),
                'No runtime remaining after startup and termination reserve')
        admitted = dict(initial, work_seconds=work_seconds, phase_total_seconds=remaining,
                        prior_charged_seconds=prior, manifest_sha256=source_sha, review=review)
        work_admission = prefix.with_suffix('.worker-admission.json')
        write(work_admission, admitted)
        script = HERE/('audit.py' if args.phase=='audit' else 'experiment.py')
        command = [sys.executable,'-B','-u',str(script),args.phase,
                   '--admission',str(work_admission)]
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
        # Inherit the registered timeout group. The outer launcher owns group
        # cleanup/confirmation even after timeout returns on supervisor death.
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=False, env=environment, cwd=str(HERE))
        for stream, path in ((process.stdout,stdout_path),(process.stderr,stderr_path)):
            thread = threading.Thread(target=pump,args=(stream,path),daemon=True)
            thread.start(); pumps.append(thread)
        write(prefix.with_suffix('.launch.json'), dict(command=command, child_pid=process.pid,
                                                     utc=utc(),manifest_sha256=source_sha))
        while process.poll() is None:
            elapsed = max(time.monotonic()-START, time.time()-WALL_START)
            require(elapsed < work_seconds, 'Work deadline reached')
            require(not pipe_errors, 'Log writer failed: '+str(pipe_errors))
            resources()
            time.sleep(.5)
        for thread in pumps: thread.join(timeout=1)
        require(not any(t.is_alive() for t in pumps) and not pipe_errors, 'Log completion failed')
        require(process.returncode==0, 'Worker exited '+str(process.returncode))
        completion = OUT/'AUDIT.json' if args.phase=='audit' else RUN/(args.phase.upper()+'_COMPLETE.json')
        require(completion.is_file(), 'Missing worker completion marker')
        require(verify_manifest()==source_sha, 'Source drift at phase exit')
        resources()
        status = 'COMPLETE'
    except BaseException as error:
        reason = repr(error)
        if process is not None and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                try: process.wait(timeout=1)
                except subprocess.TimeoutExpired: reason += '; child termination unconfirmed'
        for thread in pumps: thread.join(timeout=1)
        if not latch.exists(): write(latch,dict(utc=utc(),phase=args.phase,reason=reason))
    elapsed = max(time.monotonic()-START,time.time()-WALL_START)
    bound = 600 if args.phase=='audit' else RUNTIME_LIMIT-prior
    if elapsed >= bound:
        status='FAILED'; reason=(reason or '')+'; inclusive phase cap exceeded'
        if not latch.exists(): write(latch,dict(utc=utc(),phase=args.phase,reason=reason))
    receipt = dict(initial, utc_end=utc(), elapsed_seconds=elapsed,
                   prior_charged_seconds=prior, cumulative_runtime_seconds=None if args.phase=='audit' else prior+elapsed,
                   phase_total_limit_seconds=bound, status=status, reason=reason,
                   exit_code=None if process is None else process.returncode,
                   child_exit_confirmed=process is None or process.poll() is not None,
                   manifest_sha256=source_sha,
                   stdout_sha256=sha(stdout_path) if stdout_path.exists() else None,
                   stderr_sha256=sha(stderr_path) if stderr_path.exists() else None)
    write(prefix.with_suffix('.exit.json'),receipt)
    # This postwrite receipt supplies an inclusive sample after the full exit receipt.
    final_elapsed=max(time.monotonic()-START,time.time()-WALL_START)
    post = dict(utc=utc(),elapsed_seconds=final_elapsed,
                cumulative_runtime_seconds=None if args.phase=='audit' else prior+final_elapsed,
                receipt_sha256=sha(prefix.with_suffix('.exit.json')),
                timing_note='Sample after exit/log hashes; excludes this tiny postwrite write and interpreter teardown, covered by retained 15-second reserve.')
    write(prefix.with_suffix('.postwrite.json'),post)
    if final_elapsed+1.0>=bound or resources(limit=MAX_BYTES-64*2**20)['allocated_bytes']>MAX_BYTES-64*2**20:
        if not latch.exists(): write(latch,dict(utc=utc(),phase=args.phase,reason='Terminal resource cap'))
        status='FAILED'
    print(status, args.phase, final_elapsed, flush=True)
    return 0 if status=='COMPLETE' and not latch.exists() else 1

if __name__=='__main__':
    sys.exit(main())
