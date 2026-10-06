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
