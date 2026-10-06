"""Standard-library preparation transaction; no model imports or computations.

The caller captures both start clocks before importing this module. Completion
is valid only with a checked terminal receipt and no in-progress/failure marker.
Recorded times are checkpoints, not an unmeasured claim about process exit.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import time

TERMINAL_ARTIFACTS = ('FREEZE.json', 'PREPARATION_COMPLETE.json',
                      'PREPARATION_CHECKPOINT.json')


def write_json(path, payload):
    """Durable replacement; interrupted writes leave the in-progress gate closed."""
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def file_sha256(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def inside(base, relative, *, resolved_base=None):
    # Cache only the allowed root within one validation pass. Resolve each live
    # target afresh: retargeted symlinks must still fail containment.
    base = Path(base)
    canonical = base.resolve() if resolved_base is None else resolved_base
    relative = Path(relative)
    require(not relative.is_absolute(), 'Binding must be relative: ' + str(relative))
    path = (base / relative).resolve()
    require(path.is_relative_to(canonical), 'Binding escapes root: ' + str(relative))
    return path


def evidence_items(evidence):
    if isinstance(evidence, dict):
        return [evidence] if 'path' in evidence else list(evidence.values())
    return list(evidence)


def verify_bindings(source_sha256, evidence, *, source_root, evidence_root,
                    copied_source_root=None):
    """Reusable exact hash/size validation, including optional copied sources."""
    canonical_source = Path(source_root).resolve()
    canonical_evidence = Path(evidence_root).resolve()
    canonical_copy = (Path(copied_source_root).resolve()
                      if copied_source_root is not None else None)
    for name, digest in source_sha256.items():
        require(file_sha256(inside(source_root, name, resolved_base=canonical_source)) == digest,
                'Current preparation source changed: ' + name)
        if copied_source_root is not None:
            require(file_sha256(inside(copied_source_root, name, resolved_base=canonical_copy)) == digest,
                    'Copied preparation source changed: ' + name)
    for binding in evidence_items(evidence):
        path = inside(evidence_root, binding['path'], resolved_base=canonical_evidence)
        require(file_sha256(path) == binding['sha256'],
                'Preparation evidence changed: ' + binding['path'])
        if 'bytes' in binding:
            require(path.stat().st_size == binding['bytes'],
                    'Preparation evidence size changed: ' + binding['path'])
    return dict(source_count=len(source_sha256), evidence_count=len(evidence_items(evidence)))


class Preparation:
    def __init__(self, root, start_mono, start_wall, limit=180,
                 source_sha256=None, evidence=None, planned=None, *,
                 monotonic=time.perf_counter, wall=time.time, writer=None,
                 source_root=None, evidence_root=None):
        self.root = Path(root)
        self.start_mono, self.start_wall, self.limit = start_mono, start_wall, limit
        self.monotonic, self.wall = monotonic, wall
        self.writer = writer or write_json
        self.source_root = Path(source_root or Path(__file__).resolve().parent)
        self.evidence_root = Path(evidence_root or Path(__file__).resolve().parents[2])
        self.source_sha256 = source_sha256 or {}
        self.evidence = evidence if evidence is not None else []
        self.planned = list(planned or [])
        self.metadata_capture_complete = False
        self.phase = 'initialize'
        self.phase_samples = []
        self.phase_sample_limit = 2048
        require(self.root.is_dir(), 'Caller must reserve a unique preparation directory')
        require(not any((self.root / name).exists() for name in (
            'PREPARATION_IN_PROGRESS.json', 'PREPARATION_FAILURE.json',
            'FREEZE.json', 'PREPARATION_COMPLETE.json', 'PREPARATION_CHECKPOINT.json')),
            'Preparation cannot retry or resume an existing attempt')
        try:
            require(math.isfinite(limit) and 0 < limit <= 180,
                    'Preparation allowance must be positive and at most 180 seconds')
            self._write('PREPARATION_IN_PROGRESS.json', self.snapshot(status='IN_PROGRESS'))
            self.check('after_in_progress_write')
        except BaseException as exc:
            self.failure(exc)
            raise

    def timing(self):
        mono, utc = self.monotonic() - self.start_mono, self.wall() - self.start_wall
        require(math.isfinite(mono) and math.isfinite(utc), 'Nonfinite preparation clock')
        elapsed = max(0., mono, utc)
        return dict(monotonic_started=self.start_mono, utc_started=self.start_wall,
                    monotonic_elapsed_seconds=mono, utc_elapsed_seconds=utc,
                    elapsed_seconds=elapsed, remaining_seconds=self.limit - elapsed,
                    limit_seconds=self.limit, clock_basis='max(0, monotonic, UTC elapsed)')

    def snapshot(self, **extra):
        planned = sorted(set(str(p) for p in self.planned))
        canonical_root = self.root.resolve()
        completed = [p for p in planned
                     if inside(self.root, p, resolved_base=canonical_root).is_file()]
        missing_terminal = [p for p in TERMINAL_ARTIFACTS if not (self.root / p).is_file()]
        return dict(schema_version=2, phase=self.phase, **self.timing(),
                    phase_samples=[dict(sample) for sample in self.phase_samples],
                    phase_sample_limit=self.phase_sample_limit,
                    phase_timing_scope='Intervals between named checks; no attribution to one operation',
                    metadata_capture_complete=self.metadata_capture_complete,
                    artifact_plan_coverage='complete' if self.metadata_capture_complete else 'partial_or_not_yet_captured',
                    source_sha256=dict(self.source_sha256), evidence=self.evidence,
                    planned_artifacts=planned, completed_artifacts=completed,
                    missing_artifacts=sorted(set(planned) - set(completed)),
                    planned_terminal_artifacts=list(TERMINAL_ARTIFACTS),
                    missing_terminal_artifacts=missing_terminal, **extra)

    def check(self, phase):
        self.phase = phase
        timing = self.timing()
        require(len(self.phase_samples) < self.phase_sample_limit,
                'Bounded phase timing capacity exceeded')
        previous = self.phase_samples[-1] if self.phase_samples else None
        self.phase_samples.append(dict(phase=phase,
            monotonic_elapsed_seconds=timing['monotonic_elapsed_seconds'],
            utc_elapsed_seconds=timing['utc_elapsed_seconds'],
            elapsed_seconds=timing['elapsed_seconds'],
            monotonic_delta_seconds=timing['monotonic_elapsed_seconds'] -
                (previous['monotonic_elapsed_seconds'] if previous else 0.),
            utc_delta_seconds=timing['utc_elapsed_seconds'] -
                (previous['utc_elapsed_seconds'] if previous else 0.)))
        require(timing['elapsed_seconds'] <= self.limit,
                'Preparation exceeded its separate 180-second allowance at ' + phase)
        return timing

    def _write(self, name, payload):
        self.writer(self.root / name, payload)

    def failure(self, exc):
        """Persist the original failure even when an injected success writer fails."""
        record = self.snapshot(status='FAILED', error_type=type(exc).__name__, error=str(exc))
        # Keep/create both gates. If storage itself fails, an existing in-progress
        # marker or missing terminal receipt still rejects launch.
        try:
            write_json(self.root / 'PREPARATION_FAILURE.json', record)
        finally:
            if not (self.root / 'PREPARATION_IN_PROGRESS.json').exists():
                write_json(self.root / 'PREPARATION_IN_PROGRESS.json', record)
        return record

    def finish(self, payload):
        try:
            require(self.metadata_capture_complete, 'Preparation metadata capture is incomplete')
            self.check('before_binding_verification')
            verify_bindings(self.source_sha256, self.evidence,
                            source_root=self.source_root, evidence_root=self.evidence_root,
                            copied_source_root=self.root / 'source')
            self.check('after_binding_verification')
            self.check('before_artifact_snapshot')
            require(not self.snapshot()['missing_artifacts'], 'Planned preparation artifacts are missing')
            self.check('after_artifact_snapshot')
            self.check('before_provisional_freeze_write')
            frozen = dict(payload, provisional=True, preparation=self.snapshot(status='PROVISIONAL'))
            self.check('after_provisional_snapshot')
            self._write('FREEZE.json', frozen)
            self.check('after_provisional_freeze_write')
            self.check('before_final_freeze_write')
            frozen.update(provisional=False, preparation=self.snapshot(status='FINAL_FREEZE'))
            self.check('after_final_snapshot')
            self._write('FREEZE.json', frozen)
            self.check('after_final_freeze_write')
            self.check('before_completion_write')
            receipt = self.snapshot(status='COMPLETE', provisional=False,
                                    freeze_sha256=file_sha256(self.root / 'FREEZE.json'))
            self.check('after_completion_snapshot')
            self._write('PREPARATION_COMPLETE.json', receipt)
            self.check('after_completion_write')
            self.check('before_checkpoint_write')
            checkpoint = self.snapshot(status='PASS_POSTWRITE_CHECKPOINT', provisional=False,
                freeze_sha256=receipt['freeze_sha256'],
                completion_sha256=file_sha256(self.root / 'PREPARATION_COMPLETE.json'))
            self.check('after_checkpoint_snapshot')
            self._write('PREPARATION_CHECKPOINT.json', checkpoint)
            self.check('after_checkpoint_write')
            # Last content write has been measured while the gate remained closed.
            # Activation itself is also checked; late failure recreates the gate.
            (self.root / 'PREPARATION_IN_PROGRESS.json').unlink()
            self.check('after_activation')
            return receipt
        except BaseException as exc:
            self.failure(exc)
            raise


def assert_launchable(root, *, source_root=None, evidence_root=None):
    """Fail closed before importing/loading a model, even if FREEZE exists."""
    root = Path(root)
    require(not (root / 'PREPARATION_FAILURE.json').exists(), 'Preparation has a failure marker')
    require(not (root / 'PREPARATION_IN_PROGRESS.json').exists(), 'Preparation is incomplete')
    frozen = read_json(root / 'FREEZE.json')
    receipt = read_json(root / 'PREPARATION_COMPLETE.json')
    checkpoint = read_json(root / 'PREPARATION_CHECKPOINT.json')
    require(frozen.get('provisional') is False, 'Provisional FREEZE is not launchable')
    require(receipt.get('status') == 'COMPLETE' and receipt.get('provisional') is False,
            'Missing nonprovisional completion receipt')
    require(checkpoint.get('status') == 'PASS_POSTWRITE_CHECKPOINT'
            and checkpoint.get('provisional') is False, 'Missing postwrite checkpoint')
    digest = file_sha256(root / 'FREEZE.json')
    require(receipt['freeze_sha256'] == checkpoint['freeze_sha256'] == digest,
            'Preparation FREEZE hash changed')
    require(checkpoint['completion_sha256'] == file_sha256(root / 'PREPARATION_COMPLETE.json'),
            'Preparation completion receipt changed')
    for record in (frozen['preparation'], receipt, checkpoint):
        require(record.get('metadata_capture_complete') is True,
                'Preparation metadata capture is incomplete')
        require(record['limit_seconds'] > 0 and record['limit_seconds'] <= 180,
                'Invalid preparation allowance')
        clocks = [record['monotonic_elapsed_seconds'], record['utc_elapsed_seconds']]
        require(all(math.isfinite(value) for value in clocks), 'Nonfinite saved preparation clock')
        require(record['elapsed_seconds'] == max(0., *clocks) <= record['limit_seconds'],
                'Preparation checkpoint exceeded allowance')
        require(not record['missing_artifacts'], 'Preparation checkpoint has missing artifacts')
        for key in ('source_sha256', 'evidence', 'planned_artifacts'):
            require(record[key] == receipt[key], 'Preparation metadata disagreement: ' + key)
    canonical_root = root.resolve()
    for relative in receipt['planned_artifacts']:
        require(inside(root, relative, resolved_base=canonical_root).is_file(), 'Prepared artifact disappeared: ' + relative)
    # Each snapshot reports terminal files missing at that observation point,
    # including its own not-yet-written file. Launch checks actual completion.
    for record in (frozen['preparation'], receipt, checkpoint):
        require(record['planned_terminal_artifacts'] == list(TERMINAL_ARTIFACTS),
                'Preparation terminal artifact plan changed')
    for relative in TERMINAL_ARTIFACTS:
        require((root / relative).is_file(), 'Preparation terminal artifact missing: ' + relative)
    verify_bindings(receipt['source_sha256'], receipt['evidence'],
                    source_root=source_root or Path(__file__).resolve().parent,
                    evidence_root=evidence_root or Path(__file__).resolve().parents[2],
                    copied_source_root=root / 'source')
    return frozen, receipt
