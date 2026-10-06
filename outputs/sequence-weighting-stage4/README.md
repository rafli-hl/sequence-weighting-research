# Stage 4 v0.5 — controlled pretraining

Authorized local continuation of NEXT_EXPERIMENT.md, 29 September 2026.
Run: `work/runs/baseline-v05-20260929-01/`.
Read PROTOCOL_STAGE4.md for conditions, selection and frozen comparisons.

## Completion, 29 September 2026

All 144 tuning and 270 confirmation runs, 99 pretrained models, integrity audit,
diagnostics, four-figure visual review and archives are complete. No active job.
Final report: `results-baseline-v05-20260929-01-r2/REPORT.md`.
Its primary integrity audit is PASS. Diagnostic status is
PASS_AFTER_DOCUMENTED_NUMERICAL_REPAIR: one absolute Gram check failed by one
float64 ULP at large scale and was verified at 70-digit precision and against
a roundoff bound. See NUMERICAL_REPAIR.md; primary estimates/selection unchanged.

The original `results-baseline-v05-20260929-01/` is a preserved partial analysis,
not the final report. `results-baseline-v05-20260929-01-analysis-r1/` contains the
full repaired analysis. Final r2 clarifies timing and fit/undefined presentation;
all scientific files and figures match r1. Archives retain the earlier frozen
README snapshot. This completion note was added afterward.

Baseline intervention passes, but the epoch 30 U peak has poor fits (2/9 middle
estimates at the upper bound). It disappears by the frozen epoch 60 criterion;
selected U has undefined values and fails the combined generalization gate.
No novelty or exact large-LM replication is established.

S: shared-only pretraining; M: mixed context with shared-only loss; U: identical
mixed context/shared loss plus a fixed uniform-answer auxiliary loss. U−M at
fixed adaptation is the primary intervention. Own validation-tuned policies are
reported separately. All gains are signed and uniform p* is undefined.

## Frozen training reproduction

Reproduction requires a new unique run ID and the retained project environment:

```powershell
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage4/stage4.py --run-id baseline-v05-NEW --phase prepare
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage4/stage4.py --run-id baseline-v05-NEW --phase experiment
```

The original frozen analyzer is analyze_stage4.py; it may encounter the retained
strict numerical check above. The documented completed-run analysis sequence was
probe_roundoff.py (with --run-id), check_roundoff.py (regression on this saved
case), analyze_stage4_r1.py (with --run-id), then finalize_stage4.py (with --run-id).
Regression fixtures and NUMERICAL_CHECKS.json refer to the preserved current
project/run. A new analysis must produce its own probe/check evidence and unique
output directory; do not copy the current numerical evidence as proof of a new
run. Source snapshots are in raw analysis-source/ and analysis-repair-source/.

Preparation snapshots source/protocol and mathematical/data checks. Experiment
runs fresh tuning, freezes deterministic validation selection, then executes
deduplicated confirmation. Existing run directories refuse implicit overwrites
or resume. Preserve failures and inspect before any versioned repair. Full
models remain in raw runs; compact archive includes their hashes. No notebook
execution, cloud training or publication is implied.
