# Late-turn confirmation: disabled source

**Design:** `PROTOCOL.md`. Owner decisions 20261031-02 (the design) and 20261031-03 (the seed-draw approval; the choice between option a and option b on the 10 text-check articles is open, and this source proceeds under option a).

**Review:** revised after scoped review 1 (subject d3d7d63a…).

**Seeds:** drawn once by the owner, in `reports/natural-text-lateturn-seed-registry-20261031-01` (REGISTRY.json b9b6a882…).

**Preparation, fixture tests and review:** `reports/natural-text-lateturn-preparation-20261031-01/`.

## Files

**New:**
- `lateturn_plan.py`: the frozen constants (pure):
  - the registry, seen-registry, corpus and partition pins;
  - the draws, widths and the one rate;
  - the 2.5 GiB guard and the 2.25 GiB limit;
  - the limits, the primaries, their sequence, labels, predictions and stated power.
- `lateturn_worker.py`: the WSL/CUDA worker. It runs:
  - admission only from the activation's own copy, with the registry, the seen and fresh partitions and the disjointness re-derived;
  - the per-width start-up benchmark, with no fallback;
  - the cap on this run's stage counts;
  - the four draws, each width pre-trained and adapted, then its state hashed and deleted.
- `lateturn_analysis.py`: the frozen analysis (stdlib): P1, P3 and P2 in the fixed sequence, the saturation rule, the readings and the secondaries.
- `LATETURN_OWNER_RUN.ps1`: the one-use owner entry, with the power gate and power log. It never runs from this directory.

**Byte copies:**
- **Of the one-rate study's revision 02 source** (subject 52ad8783…), which are revision 05's files plus `power_gate.ps1`:
  - `text_plan.py`, `text_data.py`, `text_registry.py`;
  - `text_engine.py`, `text_model.py`, `text_framework_setup.py`;
  - `text_worker.py`, `text_analysis.py`, `prepare_corpus.py`, `vendor/core.py`;
  - `ORIGINAL_ENVIRONMENT.json`, `gpu_check.ps1`, `GPU_CHECK.json`, `power_gate.ps1`.
- **Of the late-turn registry source** (subject 49398ed5…, the code the seeds were drawn with): `lateturn_data.py` and `lateturn_registry.py`.

`prepare_corpus.py` is not run. It is included because the corpus manifest check binds its hash.

## Status

**SEALED_DISABLED:** `AUTHORIZATION.json` is disabled. No activation or run of this study exists.
