# Stage 5 v0.6 — useful adaptation with epoch0 selection

Authorized local continuation of NEXT_EXPERIMENT.md on 29 September 2026.
Protocol/training snapshot: `work/runs/utility-v06-20260929-01/source/`.
Read PROTOCOL_STAGE5.md for the frozen estimands, rules, counts and limitations.

M/U pretraining is unchanged from Stage4. The new bounded adaptation grid includes
smaller learning rates and a canonical no-adaptation candidate. R selects by
random-arm validation (primary); J selects jointly (secondary). Confirmation
contains fresh corpora/seeds, both weighting arms, and mandatory paired epoch0
test evaluations after selection. Useful adaptation, monotonic scaling and p*
peak status are distinct outcomes. Epoch0 never supplies an artificial p*=0.

## Completed run

`utility-v06-20260929-01` is complete: 144 tuning + 144 confirmation adaptation
runs, 66 pretrained models, 1,728 adapted checkpoints and 918 test evaluations
(54 initial + 864 adapted), with no training failure. No process remains active.
Final report: `results-utility-v06-20260929-01-r1/REPORT.md`.

Integrity, gate and frozen analysis-source audits PASS. Diagnostic audit reports
zero original strict Gram failures; its prespecified numerical fallback was not
needed. All four final figures were visually reviewed. Both original and r1
archives pass SHA/CRC checks. finalize_stage5.py created presentation r1 with
unchanged scientific files; the original report and archive remain preserved.
FINAL_REVIEW-utility-v06-20260929-01.json records the final review. This completion
note and root handoff updates were written after archiving; archived README
copies retain their historical contents.

Primary U/R random chooses epochs 10/3/0 and improves mean test NLL by
.030936/.001879/0 at widths 64/128/256. Global utility fails because largest
capacity chooses no adaptation; scaling passes separately. All nine primary K
contrasts are undefined. The small middle benefit is not positive for every
individual seed pair. See the final report for all policies and limitations.
NEXT_EXPERIMENT.md records a selection-stability recommendation; no new protocol
or run has been launched.

## Reproduction

Use a new unique run ID and the retained local WSL environment. Existing run and
result directories refuse overwrite/resume. Do not launch duplicate GPU jobs.

```powershell
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage5/stage5.py --run-id utility-v06-NEW --phase prepare
```

Before training, snapshot analyze_stage5.py, analysis_checks.py, audit_stage5.py,
LITERATURE_CHECK.md and ANALYSIS_CLARIFICATIONS.md under raw `analysis-source/`,
with filename-to-SHA256 mapping saved as
`analysis_source_manifest.json`. Run the outcome-independent analysis checks to
write raw `ANALYSIS_CHECKS.json`. The experiment enforces these checks and hashes.

```powershell
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage5/stage5.py --run-id utility-v06-NEW --phase experiment
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage5/analyze_stage5.py --run-id utility-v06-NEW --wait
```

Training allows144 tuning and<=216 confirmation trajectories,66 pretrained
models and a three-hour ceiling enforced using both perf_counter and UTC elapsed.
All raw losses/configurations/seeds/hash records stay local. Full model binaries
remain in raw; compact archives retain their hashes. The prior numerical Gram
verification fallback is prespecified here; strict failures are still reported.
Completion needs training, independent audits, report/visual review, archive
SHA/CRC and updated handoff. No notebook execution, cloud training or publication.
