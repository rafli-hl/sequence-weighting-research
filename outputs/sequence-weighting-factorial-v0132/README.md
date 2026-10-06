# New fresh factorial v0132 — source prepared, independent review pending

This bundle is the requested new experiment. It contains no measured experiment
result. Historical clipping v0130 and reanalysis v0131 are complete background.
Existing source and data remain unchanged. Only Windows source reads/writes and
hash inventory were used; no Python, tests, WSL or research execution occurred.

Read PROTOCOL.md and REVIEW_REQUEST.md. SOURCE_MANIFEST.json freezes all payload
hashes and vendor provenance; SOURCE_MANIFEST.sha256 binds the manifest itself.
SEED_CENSUS.json contains the Windows absence census, with an explicit semantic
freshness review gate. Current blocker: no independent exact-source acceptance;
execution feasibility and the later runtime are unmeasured.

## Manual Ubuntu commands — do not execute during source preparation

The following are complete commands for an already open, manually controlled
Ubuntu session after independent review. They do not request that this agent
launch WSL or bypass the previous agent-access denial. Keep the existing venv.
An independent reviewer must first supply the real reviews/SOURCE_REVIEW.json;
the template is deliberately nonlaunchable. No command installs packages,
changes security policy, regenerates old results or retries a failed run.

Source identity inspection (shell reads only, after review):

```bash
cd /mnt/d/codex/sequence-weighting-research/outputs/sequence-weighting-factorial-v0132
sha256sum -c SOURCE_MANIFEST.sha256
sha256sum common.py experiment.py audit.py supervise.py PROTOCOL.md runtime_phases.sh manual_launch.sh
cat reviews/SOURCE_REVIEW.json
```

One continuous, globally capped runtime invocation:

```bash
cd /mnt/d/codex/sequence-weighting-research
bash outputs/sequence-weighting-factorial-v0132/manual_launch.sh runtime
```

That invocation runs these complete phase commands in order under the SAME
outer 1800-second envelope. They are shown for review and accounting, not as
alternative standalone launches:

```bash
cd /mnt/d/codex/sequence-weighting-research
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
work/.venv-wsl/bin/python -B -u outputs/sequence-weighting-factorial-v0132/supervise.py prepare --review outputs/sequence-weighting-factorial-v0132/reviews/SOURCE_REVIEW.json
work/.venv-wsl/bin/python -B -u outputs/sequence-weighting-factorial-v0132/supervise.py pretrain --review outputs/sequence-weighting-factorial-v0132/reviews/SOURCE_REVIEW.json
work/.venv-wsl/bin/python -B -u outputs/sequence-weighting-factorial-v0132/supervise.py adapt --review outputs/sequence-weighting-factorial-v0132/reviews/SOURCE_REVIEW.json
```

Separate audit, after successful runtime, performed by the independent operator:

```bash
cd /mnt/d/codex/sequence-weighting-research
bash outputs/sequence-weighting-factorial-v0132/manual_launch.sh audit
```

Its phase command, inside the separate 600-second envelope:

```bash
cd /mnt/d/codex/sequence-weighting-research
work/.venv-wsl/bin/python -B -u outputs/sequence-weighting-factorial-v0132/supervise.py audit --review outputs/sequence-weighting-factorial-v0132/reviews/SOURCE_REVIEW.json
```

For each phase, receipts/<phase>.admission.json, .worker-admission.json, .launch.json,
.stdout.log, .stderr.log, .exit.json and .postwrite.json retain admission, command,
PID, UTC/monotonic timing, exit and source/log hashes. Outer runtime/audit retain
.started.json, .time.txt (GNU time elapsed/exit/max RSS), .stdout.log, .stderr.log,
.exit.json and .postwrite.json. Receipts/FAILED.json permanently blocks further
phases. Check both outer and inner exit codes and postwrite timing; a worker
completion marker alone is insufficient. Watchdog/cancellation failures preserve
partial evidence. Do not remove the latch, reuse directories or invoke a worker
directly to get around a stop.

## Anticipated outputs — none exist yet

- work/runs/factorial-v0132-20261004-01/DESIGN_FREEZE.json and SEED_VERIFICATION.json.
- inputs/: five fresh adaptation corpora, five fresh pretraining corpora, ten
  assignments, metadata and INPUT_MANIFEST.json; PREPARE_COMPLETE.json.
- baselines/: ten pretrained.pt, pretraining trace/arrays, shared initial train
  arrays/records; BASELINE_MANIFEST.json and PRETRAIN_COMPLETE.json.
- trajectories/: forty F10.pt, F10-arrays.pt, update-trace.json and record.json;
  TRAJECTORY_MANIFEST.json and ADAPT_COMPLETE.json.
- results-fresh-factorial-v0132-20261004-01/: PAIRS.json (ten paired rows),
  CORPUS_SUMMARY.json, CORPUS_CONTRASTS.csv (five equally weighted corpus rows),
  ALLOCATION.json and AUDIT.json; all secondary component metrics retained.
- reviews/: real independent source acceptance and later independent result
  attestation, both bound to exact evidence. Neither PASS is supplied here.

No p* fit, publication, archive, capacity/tuning grid or automatic expansion is
part of these commands. Runtime and audit estimates remain uncertain; stop and
report if the requested exact design cannot fit its original caps.
