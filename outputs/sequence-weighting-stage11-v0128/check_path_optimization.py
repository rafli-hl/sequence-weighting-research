"""Focused v0122 regression fixtures; imported by the bounded fixture runner."""
from pathlib import Path
import hashlib
import importlib.util
import time
from unittest.mock import patch
import preparation


def check_path_optimization(root, checks):
    root.mkdir(parents=True, exist_ok=False)
    source, copied, evidence = root/'live', root/'copy', root/'evidence'
    for folder in (source, copied, evidence):
        folder.mkdir()
    for folder in (source, copied):
        (folder/'bound.py').write_bytes(b'# known source\n')
    sources = {'bound.py': preparation.file_sha256(source/'bound.py')}
    bindings = []
    for i in range(32):
        path = evidence/f'{i}.bin'
        path.write_bytes(bytes([i])*7)
        bindings.append(dict(path=path.name, sha256=preparation.file_sha256(path), bytes=7))
    arguments = dict(source_root=source, evidence_root=evidence, copied_source_root=copied)
    prior_path = Path(__file__).resolve().parent.parent/'sequence-weighting-stage11-v0121'/'preparation.py'
    spec = importlib.util.spec_from_file_location('retained_preparation_v0121', prior_path)
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    original_resolve = Path.resolve
    roots = {source, copied, evidence}
    observations = {}
    for label, module in [('retained_v0121', previous), ('optimized_v0122', preparation)]:
        calls = []
        def resolve(path, *args, **kwargs):
            calls.append(path)
            return original_resolve(path, *args, **kwargs)
        started = time.perf_counter()
        with patch.object(Path, 'resolve', resolve):
            result = module.verify_bindings(sources, bindings, **arguments)
        observations[label] = dict(result=result, seconds=time.perf_counter()-started,
            root_resolutions=sum(path in roots for path in calls),
            target_resolutions=sum(path not in roots for path in calls))
    assert observations['retained_v0121']['result'] == observations['optimized_v0122']['result']
    assert observations['retained_v0121']['root_resolutions'] == 34
    assert observations['optimized_v0122']['root_resolutions'] == 3
    assert observations['retained_v0121']['target_resolutions'] == observations['optimized_v0122']['target_resolutions'] == 34

    def rejected(operation):
        try:
            operation()
        except (RuntimeError, OSError, ValueError):
            return
        raise AssertionError('Invalid binding was accepted')

    # Fresh content checks on each pass; a successful prior pass is never reused.
    (evidence/'0.bin').write_bytes(b'mutated')
    for module in (previous, preparation):
        rejected(lambda: module.verify_bindings(sources, bindings, **arguments))
    (evidence/'0.bin').write_bytes(bytes([0])*7)
    wrong_size = [dict(item) for item in bindings]
    wrong_size[0]['bytes'] = 8
    for module in (previous, preparation):
        rejected(lambda: module.verify_bindings(sources, wrong_size, **arguments))
    missing = [dict(bindings[0], path='absent.bin')]
    for module in (previous, preparation):
        rejected(lambda: module.verify_bindings(sources, missing, **arguments))
        rejected(lambda: module.inside(evidence, '../outside.bin'))
        rejected(lambda: module.inside(evidence, str(evidence.resolve()/'0.bin')))

    # Live targets and roots remain protected against symlink changes.
    outside = root/'outside'
    outside.mkdir()
    (outside/'0.bin').write_bytes(bytes([0])*7)
    link = evidence/'link.bin'
    link.symlink_to(evidence/'0.bin')
    canonical = evidence.resolve()
    assert preparation.inside(evidence, 'link.bin', resolved_base=canonical) == (evidence/'0.bin').resolve()
    link.unlink()
    link.symlink_to(outside/'0.bin')
    rejected(lambda: preparation.inside(evidence, 'link.bin', resolved_base=canonical))
    alias = root/'root-alias'
    alias.symlink_to(evidence, target_is_directory=True)
    pinned = alias.resolve()
    alias.unlink()
    alias.symlink_to(outside, target_is_directory=True)
    rejected(lambda: preparation.inside(alias, '0.bin', resolved_base=pinned))

    case = root/'snapshot-case'
    case.mkdir()
    for i in range(16):
        (case/f'{i}.json').write_text('{}\n', encoding='utf-8')
    clock = [0.]
    guard = preparation.Preparation(case, 0., 0., planned=[f'{i}.json' for i in range(16)],
        monotonic=lambda: clock[0], wall=lambda: clock[0], source_root=source, evidence_root=evidence)
    guard.metadata_capture_complete = True
    calls = []
    def resolve(path, *args, **kwargs):
        calls.append(path)
        return original_resolve(path, *args, **kwargs)
    with patch.object(Path, 'resolve', resolve):
        snapshot = guard.snapshot()
    assert sum(path == case for path in calls) == 1
    assert sum(path != case for path in calls) == 16
    assert len(snapshot['completed_artifacts']) == 16 and not snapshot['missing_artifacts']
    clock[0] = 2.
    guard.check('known-two-second-gap')
    assert guard.phase_samples[-1]['monotonic_delta_seconds'] == 2.
    assert guard.phase_samples[-1]['utc_delta_seconds'] == 2.
    assert snapshot['phase_samples'] != guard.phase_samples
    guard.phase_sample_limit = len(guard.phase_samples)
    rejected(lambda: guard.check('over-telemetry-capacity'))
    assert len(guard.phase_samples) == guard.phase_sample_limit
    guard.phase_sample_limit = 2048
    real_snapshot = guard.snapshot
    def late_snapshot(**kwargs):
        result = real_snapshot(**kwargs)
        if kwargs.get('status') == 'PROVISIONAL':
            clock[0] = 61.
        return result
    with patch.object(guard, 'snapshot', late_snapshot):
        rejected(lambda: guard.finish(dict(fixture_only=True)))
    failed = preparation.read_json(case/'PREPARATION_FAILURE.json')
    assert failed['phase'] == 'after_provisional_snapshot'
    assert failed['elapsed_seconds'] == 61.
    assert failed['phase_samples'][-1]['phase'] == 'after_provisional_snapshot'
    assert not (case/'FREEZE.json').exists()
    rejected(lambda: preparation.assert_launchable(case, source_root=source, evidence_root=evidence))
    preparation.write_json(root/'PATH_OPTIMIZATION.json', dict(status='PASS',
        observations=observations, snapshot_root_resolutions=1, snapshot_target_resolutions=16,
        no_hash_or_target_resolution_cache=True, symlink_escape_and_retarget_rejected=True,
        late_snapshot_prevents_provisional_write=True, bounded_phase_timing=True,
        timing_is_fixture_observation_not_research_freeze_prediction=True,
        baseline_sha256=hashlib.sha256(prior_path.read_bytes()).hexdigest()))
    checks.extend([
        'Cached roots reduce 34 root resolutions to 3 while preserving all 34 live target resolutions and binding results',
        'Missing files, altered hashes, wrong sizes, absolute/traversal paths and live symlink escapes/retargets reject',
        'Artifact snapshots retain every existence check with one root resolution; phase telemetry is bounded and copied',
        'Elapsed-time overrun inside snapshot fails before provisional write and keeps launch blocked'])
