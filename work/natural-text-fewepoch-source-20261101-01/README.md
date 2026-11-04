# Few-epoch, data-rich width ladder: disabled source

**Design:** `PROTOCOL.md`; owner decisions 20261101-01 and -02.

**Pins.** The corpus, registry and partition pins in `fewepoch_plan.py` are set, each in a pin-only revision with a check.

**Preparation, fixture tests and review:** `reports/natural-text-fewepoch-preparation-20261101-01/`.

## Files

**New:**
- `fewepoch_plan.py`: the frozen constants (pure): paths, pins, groups and runs, widths, readouts, the rate grid, limits, the primaries, Holm, labels, predictions and stated power;
- `fewepoch_data.py`: the partition rule, sealed with the seed policy;
- `fewepoch_registry.py`: the seed registry tool (derived from the late-turn registry tool);
- `fewepoch_worker.py`: the WSL/CUDA worker for Runs A, A2N, B1 and B2;
- `fewepoch_analysis.py`: the frozen analysis (stdlib): M, FALL and RISE under Holm, NOT_OVERFIT, the saturation rule, the readings and the secondaries;
- `FEWEPOCH_OWNER_RUN.ps1`: the one-use owner entry of a run, with the power gate and power log. It never runs from this directory;
- `text_engine.py`: the late-turn engine, with the tied-weight limit in `weights()` (owner decision 20261102-03);
- `vendor/core.py`: the late-turn estimator, with its docstring extended for tied weights and its code unchanged.

**Byte copies of the late-turn source** (subject 9286f324…):
- `text_plan.py`, `text_data.py`, `text_registry.py`, `text_model.py`, `text_framework_setup.py`;
- `text_worker.py`, `text_analysis.py`;
- `ORIGINAL_ENVIRONMENT.json`, `gpu_check.ps1`, `GPU_CHECK.json`, `power_gate.ps1`.

**Byte copies of the acquisition source:** `wt103_corpus.py`, `acquire_plan.py`, `acquire_common.py`, `a1_download.py`, `a2_rows.py`. The corpus manifest's code check binds their hashes.

## Status

**SEALED_DISABLED:** `AUTHORIZATION.json` is disabled. The corpus and the seeds exist; no activation or run of this study exists.
