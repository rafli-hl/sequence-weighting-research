<a name="stage-5-v06--useful-adaptation-with-epoch0-selection"></a>

# Stage 5 v0.6 — useful adaptation with epoch 0 selection

Authorized local continuation of NEXT_EXPERIMENT.md on 29 September 2026.
Protocol/training snapshot: `work/runs/utility-v06-20260929-01/source/`.
Read PROTOCOL_STAGE5.md for the frozen estimands, rules, counts and limitations.

M/U pretraining is unchanged from Stage 4. The new bounded adaptation grid includes
smaller learning rates and a canonical no-adaptation candidate. R selects by
random-arm validation (primary); J selects jointly (secondary). Confirmation
contains fresh corpora/seeds, both weighting arms, and mandatory paired epoch 0
test evaluations after selection. Useful adaptation, monotonic scaling and p*
peak status are distinct outcomes. Epoch 0 never supplies an artificial p*=0.

## Reproduction

Use a new unique run ID and the retained local WSL environment. Existing run and
result directories refuse overwrite/resume. Do not launch duplicate GPU jobs.

```powershell
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage5/stage5.py --run-id utility-v06-NEW --phase prepare
```

Before training, snapshot analyze_stage5.py, analysis_checks.py and audit_stage5.py
under raw `analysis-source/`, with filename-to-SHA256 mapping saved as
`analysis_source_manifest.json`. Run the outcome-independent analysis checks to
write raw `ANALYSIS_CHECKS.json`. The experiment enforces these checks and hashes.

```powershell
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage5/stage5.py --run-id utility-v06-NEW --phase experiment
wsl.exe -d Ubuntu --cd /mnt/d/codex/sequence-weighting-research -- work/.venv-wsl/bin/python outputs/sequence-weighting-stage5/analyze_stage5.py --run-id utility-v06-NEW --wait
```

Training allows 144 tuning and<=216 confirmation trajectories, 66 pretrained
models and a three-hour ceiling enforced using both perf_counter and UTC elapsed.
All raw losses/configurations/seeds/hash records stay local. Full model binaries
remain in raw; compact archives retain their hashes. The prior numerical Gram
verification fallback is prespecified here; strict failures are still reported.
Completion needs training, independent audits, report/visual review, archive
SHA/CRC and updated handoff. No notebook execution, cloud training or publication.
