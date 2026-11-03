# Peak confirmation: disabled source

**Design:** `PROTOCOL.md`; owner decisions 20261103-03 and -04.

**Preparation, fixture tests and review:** `reports/natural-text-peak-preparation-20261103-01/`.

## Files

**New:**
- `peak_plan.py`: the frozen constants: paths, pins, groups and runs, arms, contrasts, labels, stated power;
- `peak_worker.py`: the WSL/CUDA worker for Runs C1 and C2;
- `peak_analysis.py`: the frozen analysis (stdlib): the primary, the control, the secondary, NOT_OVERFIT, the readings;
- `PEAK_OWNER_RUN.ps1`: the one-use owner entry of a run, derived from the few-epoch script. It never runs from this directory;
- `PROTOCOL.md`, `README.md`.

**Byte copies of the registry source** (subject `a58795a4…`): `peak_registry.py`, `peak_data.py`, `fewepoch_data.py`, `fewepoch_plan.py`, `wt103_corpus.py`, `acquire_plan.py`, `acquire_common.py`, `a1_download.py`, `a2_rows.py`, `text_data.py`, `text_plan.py`.

**Byte copies of the few-epoch source** (subject `62f05466…`):
- `fewepoch_registry.py`, `fewepoch_worker.py`, `fewepoch_analysis.py`, used as libraries: their run entries are not used;
- `text_engine.py`, `text_worker.py`, `text_analysis.py`, `text_model.py`, `text_framework_setup.py`, `text_registry.py`, `vendor/core.py`;
- `ORIGINAL_ENVIRONMENT.json`, `gpu_check.ps1`, `GPU_CHECK.json`, `power_gate.ps1`.

## Status

**SEALED_DISABLED:** `AUTHORIZATION.json` is disabled. The corpus and the seeds exist; no activation or run of this study exists.
