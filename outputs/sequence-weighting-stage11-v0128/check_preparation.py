"""Deterministic preparation-v2 fixtures; no model or research input generation.

Every fixture directory and attempt record is retained. The root supervisor
also enforces the cumulative 180-second changed-fixture allowance. Imports are
included in this script's own UTC/monotonic accounting.
"""
import time
PROCESS_START_MONO = time.perf_counter()
PROCESS_START_WALL = time.time()

import argparse
import copy
import hashlib
import json
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
sys.dont_write_bytecode = True

import torch
import preparation
import revision_evidence
from artifacts import bind, read, sha, source_manifest
from config import HERE, ROOT


class Clock:
    """A deterministic two-clock source, independent of wall-clock execution."""
    def __init__(self, mono=0., wall=0.):
        self.mono, self.utc = mono, wall

    def monotonic(self):
        return self.mono

    def wall(self):
        return self.utc


class InjectedFailure(RuntimeError):
    pass


def require_error(function, text=None, types=(RuntimeError, AssertionError, ValueError, OSError)):
    try:
        function()
    except types as exc:
        if text is not None and text not in str(exc):
            raise AssertionError(f'Expected error containing {text!r}; got {exc!r}') from exc
        return dict(type=type(exc).__name__, error=str(exc))
    raise AssertionError('Invalid preparation/launch was accepted')


def actual_timing(prior):
    mono = time.perf_counter() - PROCESS_START_MONO
    wall = time.time() - PROCESS_START_WALL
    elapsed = max(mono, wall)
    return dict(monotonic_seconds=mono, utc_seconds=wall, elapsed_seconds=elapsed,
                prior_fixture_seconds=prior, cumulative_fixture_seconds=prior+elapsed,
                allowance_seconds=180., remaining_seconds=180.-prior-elapsed,
                includes_imports=True)


def actual_check(prior, phase):
    timing = actual_timing(prior)
    if timing['cumulative_fixture_seconds'] > 180:
        raise RuntimeError(f'Cumulative changed-fixture allowance exceeded at {phase}')
    return timing


def save(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    preparation.write_json(path, value)


def fixture_reuse_world(root):
    """Small real files with production binding checks; no historical mutation."""
    root.mkdir(parents=True, exist_ok=False)
    old, new, failed = root/'old', root/'new', root/'failed'
    old.mkdir(); new.mkdir(); (failed/'source').mkdir(parents=True)
    for name in revision_evidence.UNCHANGED:
        contents = ('# fixture dependency '+name+'\n').encode()
        (old/name).write_bytes(contents); (new/name).write_bytes(contents)
    old_runner = 'def scientific():\n    return 1\n\ndef run(args):\n    root = args.root\n    return root\n'
    new_runner = 'def scientific():\n    return 1\n\ndef run(args):\n    root = args.root\n    assert_launchable(root)\n    return root\n'
    (old/'stage11.py').write_text(old_runner,encoding='utf-8')
    (new/'stage11.py').write_text(new_runner,encoding='utf-8')
    parent = root/'historical-parent.py'; parent.write_text('# retained parent\n',encoding='utf-8')
    parent_record = dict(files=[dict(parent_path=parent.relative_to(ROOT).as_posix(),parent_sha256=sha(parent))])
    for folder in (old,new):
        save(folder/'PARENT_SOURCES.json',parent_record)
        save(folder/'RESOURCE_ACCEPTANCE.json',dict(fixture=True))
    evidence = root/'evidence.json'; save(evidence,dict(status='PASS',fixture=True))
    source_map = {name:sha(old/name) for name in revision_evidence.UNCHANGED+['stage11.py']}
    save(old/'INDEPENDENT_REVIEW.json',dict(status='PASS_IMPLEMENTATION_READY',
        source_sha256=source_map,evidence=[bind(evidence)]))
    save(failed/'PREPARATION_FAILURE.json',dict(error='Preserved fake historical stop'))
    save(old/'REVIEW_PREPARATION_FAILURE.json',dict(status='PASS_FAIL_CLOSED_PREPARATION_STOP',
        evidence=[bind(failed/'PREPARATION_FAILURE.json')],
        absent_artifacts=['FREEZE.json','RUN_STARTED.json']))
    save(old/'PREPARATION_ATTEMPTS.json',dict(fixture=True,old_limit_failed=True))
    (failed/'source'/'config.py').write_bytes((old/'config.py').read_bytes())
    save(failed/'source_manifest.json',{'config.py':sha(failed/'source'/'config.py')})
    save(failed/'support'/'counts.json',dict(count=3))
    save(failed/'INPUT_MANIFEST.json',dict(files=[bind(failed/'support'/'counts.json',failed)]))
    return old,new,failed,evidence


def check_reuse_and_tensors(root, checks, prior):
    for mode in ('unchanged','changed_dependency','changed_evidence','changed_parent'):
        actual_check(prior, 'reuse '+mode)
        old,new,failed,evidence = fixture_reuse_world(root/mode)
        if mode == 'changed_dependency':
            (new/'engine.py').write_text('# changed transitive dependency\n',encoding='utf-8')
        elif mode == 'changed_evidence':
            save(evidence,dict(status='PASS',fixture='changed after binding'))
        elif mode == 'changed_parent':
            (root/mode/'historical-parent.py').write_text('# changed parent\n',encoding='utf-8')
        with patch.object(revision_evidence,'OLD',old), patch.object(revision_evidence,'HERE',new), \
             patch.object(revision_evidence,'FAILED',failed):
            if mode == 'unchanged':
                result = revision_evidence.verify_reuse()
                assert result['status'] == 'PASS_EXACT_DEPENDENCY_REUSE'
                assert set(result['unchanged_source_sha256']) == set(revision_evidence.UNCHANGED)
            else:
                result = require_error(revision_evidence.verify_reuse)
        save(root/mode/'FIXTURE_RESULT.json',dict(mode=mode,result=result))
    checks.append('Exact dependency reuse passes unchanged files and rejects changed engine, evidence and historical parent')

    tensor_root = root/'nested-tensors'; tensor_root.mkdir(exist_ok=False)
    fixture = dict(corpora={'train':(torch.tensor([[0,1,2,3],[4,5,6,7]],dtype=torch.long),
                                    torch.tensor([[-1,0,1],[-1,1,2]],dtype=torch.long))},
                   assignments={'weights':torch.tensor([.5,1.5],dtype=torch.float32),
                                'orders':torch.tensor([[0,1],[1,0]],dtype=torch.long)})
    torch.save(fixture,tensor_root/'old-serialization.pt')
    torch.save(copy.deepcopy(fixture),tensor_root/'new-serialization.pt')
    left = torch.load(tensor_root/'old-serialization.pt',weights_only=True)
    right = torch.load(tensor_root/'new-serialization.pt',weights_only=True)
    assert revision_evidence.equal_nested(left,right) == 4
    mutations = {}
    for name in ('target_token_only','type_mask_only','weight_only','batch_order_only','dtype_only','shape_only'):
        changed = copy.deepcopy(fixture)
        if name == 'target_token_only': changed['corpora']['train'][0][0,3] += 1
        if name == 'type_mask_only': changed['corpora']['train'][1][0,2] = 2
        if name == 'weight_only': changed['assignments']['weights'][0] += .125
        if name == 'batch_order_only': changed['assignments']['orders'][0] = torch.tensor([1,0])
        if name == 'dtype_only': changed['assignments']['weights'] = changed['assignments']['weights'].double()
        if name == 'shape_only': changed['assignments']['orders'] = changed['assignments']['orders'].reshape(-1)
        torch.save(changed,tensor_root/(name+'.pt'))
        mutations[name] = require_error(lambda:revision_evidence.equal_nested(fixture,changed),'Tensor inequality:')
    save(tensor_root/'FIXTURE_RESULT.json',dict(equal_tensor_count=4,
        serialization_bytes_equal=sha(tensor_root/'old-serialization.pt')==sha(tensor_root/'new-serialization.pt'),
        serialization_hash_not_used_for_tensor_identity=True,rejected_mutations=mutations))
    checks.append('Recursive token/type/weight/order equality accepts tensors across serialization and rejects target-only, dtype and shape mutations')


def transaction(root, clock, writer=None):
    root.mkdir(parents=True,exist_ok=False)
    source_root, evidence_root = root/'live-source', root/'evidence'
    source_root.mkdir(); evidence_root.mkdir(); (root/'source').mkdir()
    for folder in (source_root,root/'source'):
        (folder/'fixture.py').write_text('# bound fixture source\n',encoding='utf-8')
    save(evidence_root/'fixture.json',dict(fixture=True,version=1))
    save(root/'payload.json',dict(input='fixture only'))
    sources = {'fixture.py':sha(source_root/'fixture.py')}
    evidence = [bind(evidence_root/'fixture.json',evidence_root)]
    guard = preparation.Preparation(root,0.,0.,limit=60,source_sha256=sources,
        evidence=evidence,planned=['payload.json'],monotonic=clock.monotonic,
        wall=clock.wall,writer=writer,source_root=source_root,evidence_root=evidence_root)
    guard.metadata_capture_complete=True
    return guard,source_root,evidence_root


def check_failure_record(root, guard):
    record = read(root/'PREPARATION_FAILURE.json')
    required = {'phase','monotonic_started','utc_started','monotonic_elapsed_seconds',
        'utc_elapsed_seconds','elapsed_seconds','remaining_seconds','limit_seconds',
        'clock_basis','source_sha256','evidence','planned_artifacts','completed_artifacts',
        'missing_artifacts','planned_terminal_artifacts','missing_terminal_artifacts',
        'error_type','error','status'}
    assert required <= set(record)
    assert record['status'] == 'FAILED' and record['error_type'] and record['error']
    assert record['phase'] == guard.phase
    assert record['elapsed_seconds'] == max(0.,record['monotonic_elapsed_seconds'],record['utc_elapsed_seconds'])
    assert record['remaining_seconds'] == record['limit_seconds']-record['elapsed_seconds']
    assert record['limit_seconds'] == 60
    assert record['source_sha256'] == guard.source_sha256 and record['evidence'] == guard.evidence
    assert record['planned_artifacts'] == sorted(set(guard.planned))
    assert set(record['completed_artifacts']) | set(record['missing_artifacts']) == set(guard.planned)
    assert not set(record['completed_artifacts']) & set(record['missing_artifacts'])
    assert record['completed_artifacts'] == sorted(p for p in guard.planned if (root/p).is_file())
    assert record['missing_artifacts'] == sorted(p for p in guard.planned if not (root/p).is_file())
    assert set(record['planned_terminal_artifacts']) == {'FREEZE.json','PREPARATION_COMPLETE.json','PREPARATION_CHECKPOINT.json'}
    assert record['missing_terminal_artifacts'] == [p for p in record['planned_terminal_artifacts'] if not (root/p).is_file()]
    assert (root/'PREPARATION_IN_PROGRESS.json').exists()
    require_error(lambda:preparation.assert_launchable(root,source_root=guard.source_root,
        evidence_root=guard.evidence_root),'failure marker')
    assert not (root/'RUN_STARTED.json').exists()
    return record


def check_clocks(root, checks, prior):
    for name,mono,utc,passes in [('exact_60',60.,60.,True),
                               ('utc_ahead_at_60',51.,60.,True),
                               ('monotonic_ahead_at_60',60.,51.,True),
                               ('utc_over_limit',59.,60.0001,False),
                               ('monotonic_over_limit',60.0001,59.,False),
                               ('utc_backwards_monotonic_safe',10.,-5.,True)]:
        actual_check(prior,'clock '+name)
        clock=Clock(); case=root/name
        guard,source_root,evidence_root=transaction(case,clock)
        clock.mono,clock.utc=mono,utc
        if passes:
            timing=guard.check('deterministic_boundary')
            assert timing['elapsed_seconds'] == max(0.,mono,utc)
            guard.finish(dict(fixture_only=True))
            frozen,receipt=preparation.assert_launchable(case,source_root=source_root,evidence_root=evidence_root)
            assert frozen['provisional'] is False and receipt['status']=='COMPLETE'
            assert receipt['elapsed_seconds'] == max(0.,mono,utc)
            assert receipt['remaining_seconds'] == 60-max(0.,mono,utc)
        else:
            try:
                guard.check('deterministic_boundary')
            except RuntimeError as exc:
                guard.failure(exc)
            else:
                raise AssertionError('Over-limit preparation accepted')
            check_failure_record(case,guard)
    checks.append('Exactly 60 seconds accepted; either clock over 60 rejected; UTC/monotonic disagreement and negative UTC retained')

    # Failure before a provisional record must disclose all missing planned files.
    clock=Clock(); case=root/'missing-before-freeze'
    guard,_,_=transaction(case,clock)
    guard.planned.append('not-created.json')
    require_error(lambda:guard.finish(dict(fixture_only=True)),'artifacts are missing')
    record=check_failure_record(case,guard)
    assert record['missing_artifacts']==['not-created.json']
    assert set(record['missing_terminal_artifacts']) == {'FREEZE.json','PREPARATION_COMPLETE.json','PREPARATION_CHECKPOINT.json'}
    assert not (case/'FREEZE.json').exists()
    checks.append('Pre-freeze failure preserves planned/completed/missing artifacts and all timing/source/evidence fields')


def check_transaction_failures(root, checks, prior):
    modes=[('before_provisional','FREEZE.json',1,'before'),
           ('after_provisional','FREEZE.json',1,'after'),
           ('before_final','FREEZE.json',2,'before'),
           ('after_final','FREEZE.json',2,'after'),
           ('late_provisional','FREEZE.json',1,'late_mono'),
           ('late_final','FREEZE.json',2,'late_utc'),
           ('late_completion','PREPARATION_COMPLETE.json',1,'late_utc'),
           ('late_checkpoint','PREPARATION_CHECKPOINT.json',1,'late_mono')]
    failed_with_freeze=[]
    for name,target,nth,when in modes:
        actual_check(prior,'transaction '+name)
        clock=Clock(); counts={}; case=root/name
        def writer(path,payload):
            counts[path.name]=counts.get(path.name,0)+1
            matches=path.name==target and counts[path.name]==nth
            if matches and when=='before':
                raise InjectedFailure('before '+name)
            preparation.write_json(path,payload)
            if matches and when=='after':
                raise InjectedFailure('after '+name)
            if matches and when=='late_mono': clock.mono=60.0001
            if matches and when=='late_utc': clock.utc=60.0001
        guard,_,_=transaction(case,clock,writer)
        error=require_error(lambda:guard.finish(dict(fixture_only=True)))
        record=check_failure_record(case,guard)
        assert counts[target]==nth
        if when.startswith('late'):
            assert record['elapsed_seconds']==60.0001 and record['remaining_seconds']<0
        else:
            assert record['error_type']=='InjectedFailure' and record['elapsed_seconds']==0
        if name=='before_provisional':
            assert not (case/'FREEZE.json').exists()
        elif name in ('after_provisional','before_final','late_provisional'):
            assert read(case/'FREEZE.json')['provisional'] is True
        else:
            assert read(case/'FREEZE.json')['provisional'] is False
        if (case/'FREEZE.json').exists(): failed_with_freeze.append(case)
        save(case/'FIXTURE_RESULT.json',dict(injection=name,target=target,occurrence=nth,
             when=when,error=error,launchable=False))
    checks.append('Injected before/after provisional/final writes and post receipt/checkpoint overruns persist failures and remain unlaunchable')

    clock=Clock(); case=root/'late_activation'
    guard,_,_=transaction(case,clock)
    original_unlink=Path.unlink
    def unlink(path,*args,**kwargs):
        result=original_unlink(path,*args,**kwargs)
        if path==case/'PREPARATION_IN_PROGRESS.json': clock.utc=60.0001
        return result
    with patch.object(Path,'unlink',unlink):
        require_error(lambda:guard.finish(dict(fixture_only=True)),'after_activation')
    record=check_failure_record(case,guard)
    assert record['phase']=='after_activation'
    assert read(case/'FREEZE.json')['provisional'] is False
    assert (case/'PREPARATION_COMPLETE.json').exists() and (case/'PREPARATION_CHECKPOINT.json').exists()
    failed_with_freeze.append(case)
    checks.append('Late activation overrun recreates the in-progress gate despite complete final artifacts')
    return failed_with_freeze


def check_launch_and_bindings(root, failed, checks, prior):
    for mode in ('current_source','copied_source','evidence','freeze_hash','receipt_hash'):
        actual_check(prior,'launch '+mode)
        clock=Clock(); case=root/mode
        guard,source_root,evidence_root=transaction(case,clock)
        guard.finish(dict(fixture_only=True))
        preparation.assert_launchable(case,source_root=source_root,evidence_root=evidence_root)
        if mode=='current_source':
            (source_root/'fixture.py').write_text('# changed current source\n',encoding='utf-8')
        elif mode=='copied_source':
            (case/'source'/'fixture.py').write_text('# changed copied source\n',encoding='utf-8')
        elif mode=='evidence':
            save(evidence_root/'fixture.json',dict(fixture=True,version=2))
        elif mode=='freeze_hash':
            frozen=read(case/'FREEZE.json'); frozen['fixture_only']='mutated'; save(case/'FREEZE.json',frozen)
        else:
            receipt=read(case/'PREPARATION_COMPLETE.json'); receipt['phase']='mutated'; save(case/'PREPARATION_COMPLETE.json',receipt)
        rejected=require_error(lambda:preparation.assert_launchable(case,source_root=source_root,evidence_root=evidence_root))
        save(case/'FIXTURE_RESULT.json',dict(mutation=mode,rejected=rejected))
    checks.append('Launcher revalidates current/copied sources, evidence and freeze/completion bindings')

    # Crash-like state: terminal files exist, but activation never cleared its
    # latch and no exception handler had an opportunity to write FAILURE.
    actual_check(prior,'latch-only launch rejection')
    latch_case=root/'latch-only-terminal-files'
    guard,source_root,evidence_root=transaction(latch_case,Clock())
    guard.finish(dict(fixture_only=True))
    save(latch_case/'PREPARATION_IN_PROGRESS.json',dict(status='SIMULATED_INTERRUPTED_ACTIVATION',fixture_only=True))
    assert not (latch_case/'PREPARATION_FAILURE.json').exists()
    assert all((latch_case/name).is_file() for name in preparation.TERMINAL_ARTIFACTS)
    require_error(lambda:preparation.assert_launchable(latch_case,source_root=source_root,
                  evidence_root=evidence_root),'incomplete',types=(RuntimeError,))

    # Exercise the actual scientific entry point: no GPU setup or model may run.
    actual_check(prior,'runner launch rejection')
    import stage11 as runner
    reached=[]
    def forbidden_setup():
        reached.append('runtime')
        raise AssertionError('Failed preparation reached runtime/model setup')
    for case in failed:
        with patch.object(runner,'run_path',return_value=case), \
             patch.object(runner,'setup_runtime',side_effect=forbidden_setup):
            require_error(lambda:runner.run(SimpleNamespace(run_id='fixture')),'failure marker',types=(RuntimeError,))
    with patch.object(runner,'run_path',return_value=latch_case), \
         patch.object(runner,'setup_runtime',side_effect=forbidden_setup):
        require_error(lambda:runner.run(SimpleNamespace(run_id='fixture')),'incomplete',types=(RuntimeError,))
    assert not reached
    import launch_stage11 as launcher
    fake_project=root/'launcher-project'
    for fake_run_id,case,error in [('rule-tying-v0122-fixture',failed[0],'failure marker'),
                                  ('rule-tying-v0122-latch',latch_case,'incomplete')]:
        target=fake_project/'work'/'runs'/fake_run_id
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(case,target)
        with patch.object(launcher,'ROOT',fake_project), \
             patch.object(sys,'argv',['launch_stage11.py','run','--run-id',fake_run_id]), \
             patch.object(runner,'run',side_effect=AssertionError('Rejected launcher reached scientific runner')):
            require_error(launcher.main,error,types=(RuntimeError,))
    require_error(runner.main,'launch_stage11.py',types=(SystemExit,))
    checks.append('Both launcher.main and stage11.run reject failed FREEZE before runtime; direct stage11.py entry is disabled')
    checks.append('Latch-only interrupted preparation rejects complete terminal files without a FAILURE marker in helper and both launch paths')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--artifacts-dir',type=Path,required=True)
    parser.add_argument('--prior-fixture-seconds',type=float,default=0.)
    args=parser.parse_args()
    if not 0 <= args.prior_fixture_seconds < 180:
        raise ValueError('Prior changed-fixture duration must be within [0,180)')
    if args.output.exists() or args.artifacts_dir.exists():
        raise FileExistsError('Fixture outputs/attempt directories must be unique and retained')
    args.artifacts_dir.mkdir(parents=True,exist_ok=False)
    started=dict(utc=datetime.fromtimestamp(PROCESS_START_WALL,timezone.utc).isoformat(),
                 monotonic_started=PROCESS_START_MONO,fixture_only=True,
                 prior_fixture_seconds=args.prior_fixture_seconds)
    save(args.artifacts_dir/'ATTEMPT_STARTED.json',started)
    checks=[]
    try:
        actual_check(args.prior_fixture_seconds,'after imports')
        from check_path_optimization import check_path_optimization
        check_path_optimization(args.artifacts_dir/'path-optimization', checks)
        actual_check(args.prior_fixture_seconds, 'after path optimization checks')
        check_clocks(args.artifacts_dir/'clocks',checks,args.prior_fixture_seconds)
        failed=check_transaction_failures(args.artifacts_dir/'transactions',checks,args.prior_fixture_seconds)
        check_launch_and_bindings(args.artifacts_dir/'launch',failed,checks,args.prior_fixture_seconds)
        check_reuse_and_tensors(args.artifacts_dir/'reuse',checks,args.prior_fixture_seconds)
        actual_check(args.prior_fixture_seconds,'before real dependency reuse')
        reuse=revision_evidence.verify_reuse()
        save(args.artifacts_dir/'REAL_DEPENDENCY_REUSE.json',reuse)
        checks.append('Real unchanged transitive dependencies and all preserved failed-run inputs pass exact hash binding')
        timing=actual_check(args.prior_fixture_seconds,'after all fixtures')
        result=dict(status='PASS',utc=datetime.now(timezone.utc).isoformat(),fixture_only=True,
            checks=checks,timing=timing,artifacts_dir=args.artifacts_dir.resolve().relative_to(ROOT).as_posix(),
            source_sha256=source_manifest(),source_binding_scope='Entire current top-level py/md source map',
            outcomes='Only deterministic clocks, small tensor fixtures and saved-file checks; no research input generation or models',
            historical_attempts_preserved=True)
        save(args.output,result)
        timing=actual_check(args.prior_fixture_seconds,'after result write')
        save(args.artifacts_dir/'ATTEMPT_COMPLETE.json',dict(status='PASS',timing=timing,
                                                           result_sha256=sha(args.output)))
        actual_check(args.prior_fixture_seconds,'after attempt completion write')
        print(json.dumps(dict(status='PASS',checks=len(checks),timing=actual_timing(args.prior_fixture_seconds))))
    except BaseException as exc:
        failure=dict(status='FAILED',utc=datetime.now(timezone.utc).isoformat(),error_type=type(exc).__name__,
            error=str(exc),traceback=traceback.format_exc(),completed_checks=checks,
            timing=actual_timing(args.prior_fixture_seconds),fixture_only=True,
            partial_result_exists=args.output.exists(),prior_attempts_preserved=True)
        save(args.artifacts_dir/'ATTEMPT_FAILURE.json',failure)
        raise


if __name__=='__main__':
    main()
