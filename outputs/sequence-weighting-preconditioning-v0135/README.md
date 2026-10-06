# v0135 source candidate

Distinct four-arm fresh-data preconditioning experiment. Preparation only;
no fixtures, Python, WSL, datasets, training or audit execution occurred.
Read FROZEN_PROTOCOL.md, FRESHNESS_RECONCILIATION.json, STORAGE_BUDGET.json and
REVIEW_REQUEST.md. Historical studies and failed attempts remain unchanged.

Bundle: outputs/sequence-weighting-preconditioning-v0135.
Future run: work/runs/preconditioning-v0135-20261005-01.
Future results: results-fresh-preconditioning-v0135-20261005-01 inside bundle.
Source review: reviews/SOURCE_REVIEW.json; currently absent. Its template is
deliberately pending and cannot authorize launch. Runtime approval is separate.

Only after independent exact-source acceptance AND separate user numerical approval,
an operator may use the following full commands in a manually opened Ubuntu shell.
The agent must not retry denied WSL access. Existing work/.venv-wsl only; no installs,
driver/security changes, environment replacement or CPU fallback.

Read-only source identity:

```bash
cd /mnt/d/codex/sequence-weighting-research/outputs/sequence-weighting-preconditioning-v0135
sha256sum -c SOURCE_MANIFEST.sha256
cat reviews/SOURCE_REVIEW.json
```

Phase A: single inclusive 1,800 s runtime envelope. It automatically runs preparation,
pretraining fixtures, ten pretrainings and forty F10 adaptations sequentially.

```bash
cd /mnt/d/codex/sequence-weighting-research
bash outputs/sequence-weighting-preconditioning-v0135/manual_launch.sh runtime
runtime_exit=$?
printf 'runtime exit: %s\n' "$runtime_exit"
cat outputs/sequence-weighting-preconditioning-v0135/receipts/outer-runtime.time.txt
cat outputs/sequence-weighting-preconditioning-v0135/receipts/outer-runtime.exit.json
cat outputs/sequence-weighting-preconditioning-v0135/receipts/outer-runtime.containment.json
cat outputs/sequence-weighting-preconditioning-v0135/receipts/outer-runtime.postwrite.json
cat outputs/sequence-weighting-preconditioning-v0135/receipts/prepare.exit.json
cat outputs/sequence-weighting-preconditioning-v0135/receipts/pretrain.exit.json
cat outputs/sequence-weighting-preconditioning-v0135/receipts/adapt.exit.json
```

Phase B: separate inclusive 600 s independent numerical audit. Run once only after
Phase A exit 0 and saved successful runtime receipts; failure or uncertain cleanup
blocks this phase. Do not use missing receipts as permission to rerun.

```bash
cd /mnt/d/codex/sequence-weighting-research
bash outputs/sequence-weighting-preconditioning-v0135/manual_launch.sh audit
audit_exit=$?
printf 'audit exit: %s\n' "$audit_exit"
cat outputs/sequence-weighting-preconditioning-v0135/receipts/outer-audit.time.txt
cat outputs/sequence-weighting-preconditioning-v0135/receipts/outer-audit.exit.json
cat outputs/sequence-weighting-preconditioning-v0135/receipts/outer-audit.containment.json
cat outputs/sequence-weighting-preconditioning-v0135/receipts/outer-audit.postwrite.json
cat outputs/sequence-weighting-preconditioning-v0135/receipts/audit.exit.json
cat outputs/sequence-weighting-preconditioning-v0135/results-fresh-preconditioning-v0135-20261005-01/AUDIT.json
cat outputs/sequence-weighting-preconditioning-v0135/results-fresh-preconditioning-v0135-20261005-01/CORPUS_SUMMARY.json
```

For an approved unattended runtime-then-audit sequence, one conditional invocation
covers both envelopes without launching audit after runtime failure:

```bash
cd /mnt/d/codex/sequence-weighting-research
bash outputs/sequence-weighting-preconditioning-v0135/manual_launch.sh runtime
runtime_exit=$?
printf 'runtime exit: %s\n' "$runtime_exit"
if [ "$runtime_exit" -eq 0 ]; then
  bash outputs/sequence-weighting-preconditioning-v0135/manual_launch.sh audit
  audit_exit=$?
  printf 'audit exit: %s\n' "$audit_exit"
else
  printf 'Runtime failed: preserve evidence; do not retry.\n'
fi
```

Exact inner phase commands (documentation only, never standalone substitutes):

```bash
work/.venv-wsl/bin/python -B -u outputs/sequence-weighting-preconditioning-v0135/supervise.py prepare --review outputs/sequence-weighting-preconditioning-v0135/reviews/SOURCE_REVIEW.json
work/.venv-wsl/bin/python -B -u outputs/sequence-weighting-preconditioning-v0135/supervise.py pretrain --review outputs/sequence-weighting-preconditioning-v0135/reviews/SOURCE_REVIEW.json
work/.venv-wsl/bin/python -B -u outputs/sequence-weighting-preconditioning-v0135/supervise.py adapt --review outputs/sequence-weighting-preconditioning-v0135/reviews/SOURCE_REVIEW.json
work/.venv-wsl/bin/python -B -u outputs/sequence-weighting-preconditioning-v0135/supervise.py audit --review outputs/sequence-weighting-preconditioning-v0135/reviews/SOURCE_REVIEW.json
```

Each supervisor requires the active registered outer group/GO. Successful labels:
`runtime exit: 0`, then `audit exit: 0`. They are necessary, not sufficient:
require bound source/review/input/completion/output/log hashes, zero worker exits,
children exited, group disappearance, wrapper reaped, cancellation 0, no failure
latch, inclusive postwrite<1,800 s/<600 s,<=512 MiB and>=2 GiB free. Final independent
result review must accept audit scope and scientific claims. Outcome direction
never changes numerical acceptance or permits retry.

Anticipated RUN: DESIGN_FREEZE, SEED_VERIFICATION, ENVIRONMENT, OPTIMIZER_FIXTURES;
inputs with five adaptation/five pretraining datasets and ten assignments;
INPUT_MANIFEST, ten baselines/checkpoints/initial and pretraining arrays/traces;
BASELINE_MANIFEST, forty trajectory F10 checkpoints/arrays/160-row traces/records;
eight prescribed step snapshots; TRAJECTORY_MANIFEST and phase completion markers.
OUT: PAIRS.json,CORPUS_SUMMARY.json,CORPUS_CONTRASTS.csv,ALLOCATION.json,AUDIT.json.
Receipts: phase admissions/worker admissions/launch IDs/command/logs/exit/postwrite,
outer started/atomic pgid/pending/GO/cancel if present/GNU time/containment/exit/postwrite.
Any partial attempt, deadline, broken pairing, missing input, numeric failure or
resource breach is terminal. Preserve all evidence; no resume, regeneration or retry.
