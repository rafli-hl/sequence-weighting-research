# Stage 2 v0.3

Completed and audited run: `work/runs/generalization-v03-20260928-01/`.
Final report: `results-generalization-v03-20260928-01-r2/REPORT.md`.
All 216 tuning and 90 confirmation runs succeeded; no job remains active.

The immutable training source/protocol copies and their SHA256 manifest live
in that run directory. `stage2.py` performs the benchmark, capacity-specific
validation tuning, selection freeze and fresh confirmation. `analyze_stage2.py`
independently audits the completed records, writes the scientific report and
figures, then creates a compact CRC-checked archive. Full trained models remain
in the raw run directory, with hashes in the report's raw manifest.

From PowerShell at the project root, substitute a new unique run-id to reproduce:

```powershell
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage2/stage2.py --run-id generalization-v03-NEW --phase benchmark
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage2/stage2.py --run-id generalization-v03-NEW --phase experiment
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage2/analyze_stage2.py --run-id generalization-v03-NEW
```

The runtime gate must pass before experiment. An existing benchmark directory
is never overwritten. Experiment resumption accepts complete runs with the
same frozen source; incomplete runs are retained and block automatic reuse.
Do not launch a second experiment process on the same directory or GPU.
Analysis requires COMPLETE.json and creates a new result directory; it refuses
to replace a previous analysis directory.

For this study, a second analysis invocation preserved the first directory and
created an r2 presentation revision, reusing its passed audit and asserting an
unchanged scientific summary. `PRESENTATION_REVISION.json` records the changes
and prior archive hash. Existing r2 output is never overwritten.

Read `PROTOCOL_STAGE2.md` for seeds, selection rules and interpretation criteria;
`LITERATURE_CHECK.md` for the fresh primary-source positioning check.
