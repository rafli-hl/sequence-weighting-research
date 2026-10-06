# v0133-r1 import correction - source candidate, no revision execution

Read REVISION_RECORD.md, FAILED_ATTEMPT_BINDINGS.json, FROZEN_PROTOCOL.md,
FRESHNESS_RECONCILIATION.json and REVIEW_REQUEST.md. The original failed v0133
attempt, latch, receipts and attestation remain intact in their original bundle.
This distinct revision adds one import and uses attempt 20261004-02 paths.
The same scientific design and unused fresh seeds are retained. Runtime remaining
is1798 seconds after a conservative2-second charge; audit remains600 seconds.
Both failed and candidate bundles count against the unchanged512MiB cap.
No Python, tests, WSL, generation, training or audit ran in this revision.

After independent exact-manifest acceptance AND separate user launch approval,
an operator in a manually opened Ubuntu session may use these phase-labeled
commands. This agent must not launch or retry denied WSL access. Keep the existing
venv; no install, environment migration, cloud fallback or policy changes.

Source identity (read-only):

```bash
cd /mnt/d/codex/sequence-weighting-research/outputs/sequence-weighting-clipping-interaction-v0133-r1
sha256sum -c SOURCE_MANIFEST.sha256
cat reviews/SOURCE_REVIEW.json
```

Runtime preparation → pretraining → adaptation, one1798-second remaining envelope:

```bash
cd /mnt/d/codex/sequence-weighting-research
bash outputs/sequence-weighting-clipping-interaction-v0133-r1/manual_launch.sh runtime
runtime_exit=$?
printf 'runtime exit: %s\n' "$runtime_exit"
cat outputs/sequence-weighting-clipping-interaction-v0133-r1/receipts/outer-runtime.time.txt
cat outputs/sequence-weighting-clipping-interaction-v0133-r1/receipts/outer-runtime.exit.json
```

The reviewed runtime_phases.sh runs these exact phase commands sequentially
inside that same outer watchdog; do not use them as standalone substitutes:

```bash
work/.venv-wsl/bin/python -B -u outputs/sequence-weighting-clipping-interaction-v0133-r1/supervise.py prepare --review outputs/sequence-weighting-clipping-interaction-v0133-r1/reviews/SOURCE_REVIEW.json
work/.venv-wsl/bin/python -B -u outputs/sequence-weighting-clipping-interaction-v0133-r1/supervise.py pretrain --review outputs/sequence-weighting-clipping-interaction-v0133-r1/reviews/SOURCE_REVIEW.json
work/.venv-wsl/bin/python -B -u outputs/sequence-weighting-clipping-interaction-v0133-r1/supervise.py adapt --review outputs/sequence-weighting-clipping-interaction-v0133-r1/reviews/SOURCE_REVIEW.json
```

Separate independent audit, only after a successful runtime gate,600 seconds:

```bash
cd /mnt/d/codex/sequence-weighting-research
bash outputs/sequence-weighting-clipping-interaction-v0133-r1/manual_launch.sh audit
audit_exit=$?
printf 'audit exit: %s\n' "$audit_exit"
cat outputs/sequence-weighting-clipping-interaction-v0133-r1/receipts/outer-audit.time.txt
cat outputs/sequence-weighting-clipping-interaction-v0133-r1/receipts/outer-audit.exit.json
cat outputs/sequence-weighting-clipping-interaction-v0133-r1/receipts/audit.exit.json
```

Expected successful prints: runtime exit:0 / audit exit:0. Exit alone is not
scientific acceptance. Each inner phase automatically saves admission, worker
admission, command/PID, stdout/stderr, exit and postwrite receipts, source/review/
log hashes, UTC/monotonic timing and child-exit status. Outer runtime/audit save
started/time/stdout/stderr/exit/postwrite receipts plus a hash-bound containment
receipt. The outer launcher registers the timeout group before phase exec and
retains cleanup after supervisor/leader death; it terminates surviving members
and confirms group disappearance before returning. GNU time runs asynchronously;
the launcher uses interruptible Bash wait. Before phase exec, group registration
and an outer GO gate are required. Cancellation persistently closes that gate,
cleans the registered group and reaps the timing wrapper; pre-registration
cancellation cannot release a phase after cleanup. Deadline cleanup stays inside
the existing grace/caps. Missing or unconfirmed containment is a failure, never
acceptance. FAILED.json or an existing
phase admission blocks continuation/retry. Require all inclusive timing, log
hashes, completion bindings and exits; preserve any failed/partial evidence.

Anticipated run: work/runs/clipping-interaction-v0133-20261004-02. Immutable
inputs and manifests; ten pretrained checkpoints, pretraining arrays/traces,
shared initial train/test arrays; forty F10 checkpoints, final arrays and160-row
update traces each, including actual step/relative norms. Anticipated output:
results-fresh-clipping-interaction-v0133-20261004-02/PAIRS.json,
CORPUS_SUMMARY.json, CORPUS_CONTRASTS.csv, ALLOCATION.json, AUDIT.json. Summary
includes continuous D, both conditional contrasts, adequacy, corpus dispersion,
criterion flags and every seed/corpus; AUDIT.json includes discrepancy maxima.
No result folder, receipts, data or checkpoint is supplied now.

SOURCE_REVIEW_TEMPLATE.json is intentionally nonlaunchable. Only an independent
reviewer may create reviews/SOURCE_REVIEW.json with PASS_V0133_SOURCE, their
identity and exact manifest binding. The preparer does not create PASS. The
archived Windows source-census/reconciliation recipes document source preparation;
they are not operational entrypoints and must not be rerun to bypass guards.
No benchmark, automatic seed expansion, tuning, retries or archives are added.
