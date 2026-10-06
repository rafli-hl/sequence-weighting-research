"""Two phases inside one600-second reviewed outer envelope, no retries."""
import time
START=time.monotonic()
WALL=time.time()
import argparse
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path
from common import (HERE,RUN,OUT,TOTAL_SECONDS,require,read,write,sha,utc,resources,
                    verify_manifest,verify_review)
sys.dont_write_bytecode=True

def interrupted(number,frame): raise RuntimeError('Supervisor interrupted '+str(number))
signal.signal(signal.SIGINT,interrupted)
signal.signal(signal.SIGTERM,interrupted)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('phase',choices=('diagnose','audit'))
    parser.add_argument('--review',required=True,type=Path); args=parser.parse_args()
    receipts=HERE/'receipts'; receipts.mkdir(exist_ok=True); prefix=receipts/args.phase
    latch=receipts/'FAILED.json'
    require(not latch.exists() and not prefix.with_suffix('.admission.json').exists(),'Terminal/no-retry admission')
    initial=dict(phase=args.phase,utc_start=utc(),monotonic_start=START,wall_start=WALL,pid=os.getpid())
    write(prefix.with_suffix('.admission.json'),initial)
    process=None; reason=None; status='FAILED'; prior=0.; source=None; pumps=[]; errors=[]
    stdout=prefix.with_suffix('.stdout.log'); stderr=prefix.with_suffix('.stderr.log')
    def pump(stream,path):
        size=0
        try:
            with path.open('xb') as target:
                while True:
                    chunk=stream.read(4096)
                    if not chunk: break
                    size+=len(chunk); require(size<=256*2**10,'Phase log cap')
                    target.write(chunk); target.flush()
        except BaseException as error: errors.append(repr(error))
    try:
        source=verify_manifest(); review=verify_review(args.review); resources()
        outer=read(receipts/'outer-panel.started.json')
        require(outer['mode']=='panel' and outer['total_limit_seconds']==TOTAL_SECONDS and
                (receipts/'outer-panel.go').exists() and not (receipts/'outer-panel.cancel').exists(),
                'Phase must run inside admitted outer envelope')
        require(os.getpgrp()==int((receipts/'outer-panel.pgid').read_text().strip()),'Phase escaped registered group')
        if args.phase=='diagnose':
            require(not RUN.exists() and not OUT.exists(),'Run/output already exists')
        else:
            previous=read(receipts/'diagnose.exit.json'); post=read(receipts/'diagnose.postwrite.json')
            require(previous['status']=='COMPLETE' and previous['exit_code']==0 and previous['child_exit_confirmed'] and
                    previous['manifest_sha256']==source and post['receipt_sha256']==sha(receipts/'diagnose.exit.json'),
                    'Audit needs successful bound diagnostic predecessor')
            require((RUN/'DIAGNOSE_COMPLETE.json').is_file() and not OUT.exists(),'Audit admission inputs/output')
            prior=post['elapsed_seconds']+1.
        remaining=TOTAL_SECONDS-prior; work=remaining-15
        require(work>max(time.monotonic()-START,time.time()-WALL),'No budget after termination reserve')
        admission=dict(initial,work_seconds=work,phase_total_seconds=remaining,
            prior_charged_seconds=prior,manifest_sha256=source,review=review)
        write(prefix.with_suffix('.worker-admission.json'),admission)
        script=HERE/('diagnose.py' if args.phase=='diagnose' else 'audit.py')
        command=[sys.executable,'-B','-u',str(script),args.phase,'--admission',str(prefix.with_suffix('.worker-admission.json'))]
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=False,
            cwd=str(HERE),env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1'))
        for stream,path in ((process.stdout,stdout),(process.stderr,stderr)):
            thread=threading.Thread(target=pump,args=(stream,path),daemon=True); thread.start(); pumps.append(thread)
        write(prefix.with_suffix('.launch.json'),dict(command=command,child_pid=process.pid,
            manifest_sha256=source,utc=utc(),registered_group=os.getpgrp()))
        while process.poll() is None:
            require(max(time.monotonic()-START,time.time()-WALL)<work,'Phase work deadline')
            require(not errors,'Log writer failed: '+str(errors)); resources(); time.sleep(.5)
        for thread in pumps: thread.join(timeout=1)
        require(not any(t.is_alive() for t in pumps) and not errors,'Incomplete log capture')
        require(process.returncode==0,'Worker exited '+str(process.returncode))
        complete=RUN/'DIAGNOSE_COMPLETE.json' if args.phase=='diagnose' else OUT/'AUDIT.json'
        require(complete.is_file(),'Missing worker completion')
        require(verify_manifest()==source,'Source drift after worker'); resources(); status='COMPLETE'
    except BaseException as error:
        reason=repr(error)
        if process is not None and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                try: process.wait(timeout=1)
                except subprocess.TimeoutExpired: reason+='; child exit unconfirmed'
        for thread in pumps: thread.join(timeout=1)
        if not latch.exists(): write(latch,dict(utc=utc(),phase=args.phase,reason=reason))
    elapsed=max(time.monotonic()-START,time.time()-WALL); bound=TOTAL_SECONDS-prior
    if elapsed>=bound:
        status='FAILED'; reason=(reason or '')+'; inclusive phase cap'
        if not latch.exists(): write(latch,dict(utc=utc(),phase=args.phase,reason=reason))
    receipt=dict(initial,utc_end=utc(),elapsed_seconds=elapsed,prior_charged_seconds=prior,
        cumulative_panel_seconds=prior+elapsed,phase_total_limit_seconds=bound,status=status,reason=reason,
        exit_code=None if process is None else process.returncode,
        child_exit_confirmed=process is None or process.poll() is not None,manifest_sha256=source,
        stdout_sha256=sha(stdout) if stdout.exists() else None,stderr_sha256=sha(stderr) if stderr.exists() else None)
    write(prefix.with_suffix('.exit.json'),receipt)
    final=max(time.monotonic()-START,time.time()-WALL)
    write(prefix.with_suffix('.postwrite.json'),dict(utc=utc(),elapsed_seconds=final,cumulative_panel_seconds=prior+final,
        receipt_sha256=sha(prefix.with_suffix('.exit.json')),
        timing_note='After exit/log binding;1s conservative phase handoff charge plus outer inclusive receipts.'))
    if final+1>=bound:
        status='FAILED'
        if not latch.exists(): write(latch,dict(utc=utc(),phase=args.phase,reason='Terminal timing cap'))
    try: resources(terminal=True)
    except BaseException as error:
        status='FAILED'
        if not latch.exists(): write(latch,dict(utc=utc(),phase=args.phase,reason='Terminal resources '+repr(error)))
    print(status,args.phase,final,flush=True)
    return 0 if status=='COMPLETE' and not latch.exists() else 1

if __name__=='__main__': sys.exit(main())
