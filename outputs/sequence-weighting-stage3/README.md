# Stage 3 v0.4

**Complete, 29 September 2026.** Integrity and diagnostic audits and archive
CRC pass. No training or analysis process remains active. Final report and
four visually checked figures: `results-controls-v04-20260929-01/REPORT.md`.
108 runs took 20.2 minutes including pretraining/evaluation/serialization.

Joint-selected optimizer at common epoch 30 retains the middle peak in 9/9
pairs; at selected epochs 30/10/10 it retains 1/9, with negative means in all
three corpora. Random-only selection retains 0/9. The optimizer-by-duration
interaction is -.097161 in K. Both selected policies meet random-arm monotonic
generalization in only 1/3 corpora; uniform controls meet it in all 3/3. Baseline
diagnostics show substantial dependence on the reference used to define gain.
See the report and HANDOFF.md section 11 for precise scope and limitations.

This completion note was added after analysis/archive creation. The frozen
pre-analysis README and implementation remain in raw `analysis-source/` and
the compact archive. Training source and analysis code have not been changed.

Run directory: `work/runs/controls-v04-20260929-01/`.
Frozen protocol: `PROTOCOL_STAGE3.md` and raw `source/` copy. There are 108
unique adaptation runs after deterministic deduplication, plus 27 pretrained
checkpoints. All training stays on local WSL CUDA.

To reproduce, use a new run ID and retain the Stage 2 tuning inputs:

```powershell
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage3/stage3.py --run-id controls-v04-NEW --phase prepare
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage3/stage3.py --run-id controls-v04-NEW --phase experiment
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage3/analyze_stage3.py --run-id controls-v04-NEW --wait
```

Preparation freezes source/protocol, verifies tensor/diagnostic invariants,
extracts only old tuning validation scores, freezes both policies and schedule,
and records historical hashes. Experiment refuses implicit resume/overwrite
and stops on a failure or the two-hour wall-time cap. Analysis can wait using
CPU only, audits all records, computes the frozen diagnostics, and creates a
new report directory and compact archive.

F = historical fixed optimizer evaluated on fresh corrected data. J = joint
random+uniform validation selection. R = random-only validation selection.
J and R both select epochs 30/10/10; R changes only middle-capacity WD from .1
to 1. Optimizer-by-duration crossings are still reported explicitly.

Primary p* is never replaced with a component or alternative-reference metric.
The analyzer preserves its exact Stage 2 retrospective inputs under the new
raw `retrospective/` directory. Full new model checkpoints stay locally; the
compact archive includes their hashes.
