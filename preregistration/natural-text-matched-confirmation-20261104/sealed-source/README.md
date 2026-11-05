# Matched-progress confirmation (N7): disabled source

**This package has not run.** The seeds have been drawn by the owner, but no activation exists, and no training or real-engine check of this study has happened. No loss, gain or p\* of this study exists.

**Design:** `PROTOCOL.md`, including every change from N6 (section 13).

**Owner decisions:** `reports/natural-text-ladder-owner-decisions-20261104-02/OWNER_DECISIONS.md`.

**Preparation, fixture tests and review:** `reports/natural-text-matched-preparation-20261104-01/`. **Seed policy:** `reports/natural-text-matched-seed-registry-20261104-01/SEED_REGISTRY_POLICY.md`.

## Files

**New:**
- `matched_plan.py`: the frozen constants: paths, pins, groups and runs, arms, readouts, the fixed sequence, labels, stated power;
- `matched_data.py`: the fresh pool and partition;
- `matched_registry.py`: the one-use registry tool, which the owner-run `run_seed_draw.py` calls;
- `matched_worker.py`: the WSL/CUDA worker for Runs M1 and M2;
- `matched_analysis.py`: the frozen analysis (stdlib): the matching rule, P1 and S1–S5, the readings;
- `MATCHED_OWNER_RUN.ps1`: the one-use owner entry of a run. It never runs from this directory;
- `PROTOCOL.md`, `README.md`.

**Byte copies of N6's source** (subject `0d9e8f9a…`): `peak_data.py`, `fewepoch_data.py`, `fewepoch_plan.py`, `fewepoch_registry.py`, `fewepoch_worker.py`, `fewepoch_analysis.py`, `wt103_corpus.py`, `acquire_plan.py`, `acquire_common.py`, `a1_download.py`, `a2_rows.py`, `text_data.py`, `text_plan.py`, `text_engine.py`, `text_worker.py`, `text_analysis.py`, `text_model.py`, `text_framework_setup.py`, `text_registry.py`, `vendor/core.py`, `ORIGINAL_ENVIRONMENT.json`, `gpu_check.ps1`, `GPU_CHECK.json`, `power_gate.ps1`.

## Status

**SEALED_DISABLED:** `AUTHORIZATION.json` is disabled. The seed registry and the partition exist, and `matched_plan.py` pins them; `SOURCE_SUBJECT.json` records them as DRAWN. The builder still refuses real mode without a passing real-engine check and the public registration of this subject.
