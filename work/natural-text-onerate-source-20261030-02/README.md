# Natural-text one-rate ladder extension: disabled source

**Design:** `PROTOCOL.md`. Owner decisions 20261030-01 (the study) and 20261030-02 (the ladder top and the start-up memory fallback).

**Revision 02, the final attempt** (owner ruling 20261030-03; PROTOCOL.md section 11). Attempt 1 (revision 01) failed in d06 when the charger was unplugged; it is never analysed. Revision 02 adds a power gate and a power log, and changes nothing in the science.

**Preparation, budget, power fixtures, native tests and review:** `reports/natural-text-onerate-preparation-20261030-01/` (revision 01) and `reports/natural-text-onerate-revision-02-20261030-01/` (revision 02).

## Files

**New:**
- `onerate_plan.py`: the frozen constants (pure). It holds:
  - the ladder, the one rate and which widths are new, adapted or reused;
  - the Run B pins;
  - the 2.5 GiB guard and the 2.25 GiB limit;
  - the limits, the primaries' widths, labels and predictions.
- `onerate_worker.py`: the WSL/CUDA worker. It runs:
  - admission, only from the activation's own copy, with every Run B file the run or the analysis reads checked against its pinned inventory;
  - the per-width start-up benchmark with the memory fallback;
  - the cap on this run's stage counts;
  - the ten draws, with inputs paired to Run B;
  - the hashing and deletion of every model state, also on a failure the worker observes.
- `onerate_analysis.py`: the frozen analysis (stdlib): the three primaries with revision 05's eligibility and saturation rules, the reading and the secondaries.
- `ONERATE_OWNER_RUN.ps1`: the one-use owner entry, which never runs from this directory.
- `power_gate.ps1` (revision 02): the Windows power reading, the combined GPU and power check before every draw, and the wait loop with the power log.

**Byte copies of revision 05** (subject 2ac27fe7…; the sealer checks every byte):
- `text_plan.py`, `text_data.py`, `text_registry.py`;
- `text_engine.py`, `text_model.py`, `text_framework_setup.py`;
- `text_worker.py`, `text_analysis.py`, `prepare_corpus.py`, `vendor/core.py`;
- `ORIGINAL_ENVIRONMENT.json`, `gpu_check.ps1`, `GPU_CHECK.json`.

`prepare_corpus.py` is not run. It is included because the corpus manifest check binds its hash.

## Status

**SEALED_DISABLED:** `AUTHORIZATION.json` is disabled.
- **Reused:** the corpus, the registry, the partition, Run B, and the probe result.
- **Do not exist:** any activation or run of revision 02. Attempt 1's folders (revision 01) are preserved and never analysed.
