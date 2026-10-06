# v0134 source candidate: existing-checkpoint gradient panel

No v0134 numerical execution occurred. Read FROZEN_PROTOCOL.md, INPUT_BINDINGS.json,
REVIEW_REQUEST.md and SOURCE_PREPARATION_STATUS.md before independent source review.
The original v0133 failure and completed v0133-r1 source/results remain unchanged.
There are no v0134 data, gradients, evaluation results, numerical PASS or checkpoints.

INPUT_BINDINGS.json enumerates all 30 fixed states, 15 shared existing dataset/weight
containers and 106 total checkpoint/metadata/provenance file bindings. Five corpora
are the replication units. Existing train/validation tensors, saved random instance
weights and the first saved epoch's16 batches are reused exactly. Test tensors
carried in old .pt containers are discarded from the research view; no test NLL
or gradient, new corpus, layer/checkpoint/example search or optimizer step occurs.

The diagnostic estimates full validation group-gradient alignment with the extra
instance-weight gradient, its magnitude relative to uniform and fixed-batch
dispersion. Negative dot means ordinary descent along extra gradient locally
worsens validation group loss; it is not actual AdamW dynamics or mediation.
The audit independently computes full-population direct-token reductions and all
480 batch gradients, tests analytic sign/scaling/undefined cases and verifies
strict seed/corpus aggregation and parameter immutability. It shares only input/
environment guards, trusted forward source and PyTorch autograd with the diagnostic.

Combined numerical cap 600 seconds, including both phases, imports/input hashing,
logs, failure evidence and cleanup. No separate second 600-second audit allowance.
Additional 16 MiB, work cap 12 MiB plus 4 MiB terminal reserve; scalar/provenance only.
Count both preserved v0133 bundles/run/planning within 512 MiB with 80 MiB inherited
reserves, and retain 2 GiB free. Time estimates 2-6 min plus 1-3 min are unmeasured;
no benchmark, fallback, extension or automatic retry is authorized.

After a NEW independent exact-manifest review AND separate user numerical approval,
an operator in a manually opened Ubuntu session may use the following commands.
This agent must not launch WSL or retry the prior denied access. Keep the existing
venv/environment; no install, replacement environment or cloud migration.

Source identity, read-only:

```bash
cd /mnt/d/codex/sequence-weighting-research/outputs/sequence-weighting-gradient-alignment-v0134
sha256sum -c SOURCE_MANIFEST.sha256
cat reviews/SOURCE_REVIEW.json
```

One bounded panel command, phase 1 diagnostic followed by conditional phase 2 audit:

```bash
cd /mnt/d/codex/sequence-weighting-research
bash outputs/sequence-weighting-gradient-alignment-v0134/manual_launch.sh panel
panel_exit=$?
printf 'panel exit: %s\n' "$panel_exit"
cat outputs/sequence-weighting-gradient-alignment-v0134/receipts/outer-panel.time.txt
cat outputs/sequence-weighting-gradient-alignment-v0134/receipts/outer-panel.exit.json
cat outputs/sequence-weighting-gradient-alignment-v0134/receipts/outer-panel.containment.json
cat outputs/sequence-weighting-gradient-alignment-v0134/receipts/diagnose.exit.json
cat outputs/sequence-weighting-gradient-alignment-v0134/receipts/audit.exit.json
```

The reviewed panel_phases.sh runs these exact phase commands INSIDE that same
envelope. They are documentation, not standalone substitutes; supervisor admission
requires the active outer registration/GO/process group:

```bash
work/.venv-wsl/bin/python -B -u outputs/sequence-weighting-gradient-alignment-v0134/supervise.py diagnose --review outputs/sequence-weighting-gradient-alignment-v0134/reviews/SOURCE_REVIEW.json
work/.venv-wsl/bin/python -B -u outputs/sequence-weighting-gradient-alignment-v0134/supervise.py audit --review outputs/sequence-weighting-gradient-alignment-v0134/reviews/SOURCE_REVIEW.json
```

Expected successful outer print: `panel exit: 0`. Numerical audit alone is not
acceptance. Require zero exits, bound source/review/input/completion/log hashes,
child exits, outer group disappearance/wrapper reaping, zero cancellation,
inclusive outer postwrite<600 s and all storage/free-space checks. Audit numerical
PASS still needs independent result review; outcome direction is not an acceptance
condition. FAILED.json, any admission or existing run/output blocks retry/resume.
Preserve partial states, scalar progress journal, logs and uncertain cleanup evidence.

Future run: work/runs/gradient-alignment-v0134-20261004-01. Diagnostic outputs:
DESIGN_FREEZE.json, ENVIRONMENT.json, per-state and batch scalar files, progress.jsonl,
PANEL.json (30 rows), BATCHES.json (480), CORPUS_SUMMARY.json (15), COHORT_SUMMARY.json,
ARTIFACT_MANIFEST.json and DIAGNOSE_COMPLETE.json. No gradient or parameter archive.
Future result bundle: results-existing-gradient-panel-v0134-20261004-01/
PAIRS.json, BATCHES.json, CORPUS_SUMMARY.json, COHORT_SUMMARY.json, PANEL_REPORT.md,
AUDIT.json including discrepancy maxima, algebra fixtures and output hashes.

Receipt inventory: each phase admission, worker admission, command/PID/group,
stdout/stderr, exit/postwrite; outer started, atomic pgid/pending, GO, optional
cancel/failure, GNU time/logs, containment, exit/postwrite. The r1 outer containment
body is preserved with v0134 identity. It owns cleanup after supervisor death;
asynchronous GNU time and direct signal cleanup cover pre-wait/PID races. All
registration/TERM/KILL/confirmation/reaping grace remains inside the 600-second cap.

SOURCE_REVIEW_TEMPLATE.json is deliberately nonlaunchable. Only an independent
reviewer may write reviews/SOURCE_REVIEW.json with PASS_V0134_SOURCE and exact
source/input bindings. The preparer supplies no PASS. Mixed/weak/undefined/favorable
results close the fixed panel; no future causal intervention is authorized here.
