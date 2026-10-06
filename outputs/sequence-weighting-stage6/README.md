# Stage 6 v0.7 — selection stability

Authorized local follow-up to Stage 5. Read PROTOCOL_STAGE6.md for the frozen
design and scientific limits. Four fresh two-pair tuning panels select policies
independently; three new confirmation corpora are shared and paired across all
policies. This is four tuning panels and three confirmation corpora, not twelve
independent confirmation datasets. M/U, R/J, the bounded grid and epoch 0 remain.

Run ID: `stability-v07-20260929-01`. Raw: `work/runs/` under the project root.
Maximum 576 tuning +648 confirmation runs, 102 pretrained models, three-hour
training ceiling checked against both clocks. Local Ubuntu WSL GPU only.

Every measured per-sequence checkpoint and model tensor hash is retained.
Only epoch 30 adapted full binaries and all cold/pretrained binaries are saved.
Intermediate hashes cannot independently verify absent binaries. This storage
policy is fixed before outcomes; no historical file is removed.

## Completed run

The authorized run is now complete (29 September 2026): 576 tuning +216
confirmation trajectories, 102 pretrained models and 1,350 test evaluations,
without failures. Final report: `results-stability-v07-20260929-01/REPORT.md`.
All independent audits, four-figure visual review and archive SHA/CRC checks
passed; no numerical fallback or presentation revision was needed. No process
remains active. Completion review: FINAL_REVIEW-stability-v07-20260929-01.json.

Primary U/R largest abstention is 3/4 panels, middle usefulness 0/4 and small
usefulness 4/4. All primary peak verdicts remain undefined. See the report for
the adapted negative-gain case, boundary fits and shared-corpus limitations.
Root handoff and this completion note were updated after archiving; the archive
retains the earlier README as provenance. No Stage 7 run has been launched.

## Reproduction

Use a unique new run ID; existing raw/result directories refuse overwrite.
Before training, snapshot analyze_stage6.py, analysis_core.py, analysis_checks.py,
audit_stage6.py and ANALYSIS_CLARIFICATIONS.md in raw `analysis-source/`, with
their filename-to-SHA256 map in `analysis_source_manifest.json`. Include any
additional analysis provenance files in that same map. Run outcome-independent
analysis checks and write raw `ANALYSIS_CHECKS.json`. Preserve a timestamped
ANALYSIS_FREEZE.json before launching the experiment. Source checks are enforced.

```powershell
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage6/stage6.py --run-id stability-v07-NEW --phase prepare
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage6/stage6.py --run-id stability-v07-NEW --phase experiment
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage6/analyze_stage6.py --run-id stability-v07-NEW --wait
```

Completion requires independent audits, all panel/corpus results, report and
figure visual review, archive checks and updated handoff. No notebook execution,
cloud training, upload or publication.
