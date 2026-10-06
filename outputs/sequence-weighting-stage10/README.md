# Stage 10: continuous-search agreement

Bounded local CPU diagnostic over the complete saved Stage 9 input cohorts.
Read [PROTOCOL_STAGE10.md](PROTOCOL_STAGE10.md) for the frozen design and
limitations. This stage compares independent 80-/110-digit searches with the
saved original p; historical estimates and validation decisions are retained.

## Execution

Run from the project root in PowerShell using the existing Ubuntu WSL runtime.
Finish source fixtures, analysis fixtures and independent design review before
preparation; their recorded source hashes must match the final files.

```powershell
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage10/check_stage10.py
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage10/analysis_checks.py --output outputs/sequence-weighting-stage10/ANALYSIS_CHECKS.json
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage10/stage10.py --run-id search-v011-20260930-01 --phase prepare
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage10/stage10.py --run-id search-v011-20260930-01 --phase experiment
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage10/analyze_stage10.py --run-id search-v011-20260930-01
```

The raw directory is `work/runs/search-v011-20260930-01/`. The report directory
is `outputs/sequence-weighting-stage10/results-search-v011-20260930-01/`.
Directories are create-only. Do not rerun a frozen experiment into its existing
directory or edit frozen files. The single numerical runtime budget is 3,600
seconds across verification, cache construction, both searches and comparisons.
After a failure or exhausted budget, retain evidence and report all planned
inputs; no automatic retry is part of this stage.

## Source map

- `core.py`: unchanged historical implementation, preserved for provenance.
- `inputs.py`: copied Stage 9 independent provenance reconstruction.
- `search_math.py`: Decimal80 derivative search on the full j/64 mesh.
- `independent_math.py`: separate Decimal110 objective search on j/128.
- `common_stage10.py`: literal design, hashes and shared runtime budget.
- `stage10.py`: preparation, freeze and bounded experiment driver.
- `audit_stage10.py`: candidate structure, arithmetic and search comparisons.
- `check_stage10.py`: outcome-independent numerical/provenance fixtures.
- `analyze_stage10.py`, `analysis_checks.py`: complete-denominator reporting
  and report fixtures, including retained null context.
- `DERIVATION.json`: immutable parent-source provenance.

All 186 unique numerical inputs, 207 native checkpoints and 324 policy aliases
are retained. Finite subdivision and local refinement do not establish a
global optimum. Objective agreement and parameter agreement are separate
diagnostics; neither establishes statistical recovery or model utility.
