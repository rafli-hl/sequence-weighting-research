# Capacity-shift follow-up (fresh-corpus test of the G16 peak shift under R) — disabled source

Design: `PROTOCOL.md` (revision 02, frozen 27 Oct 2026 after the first independent review and the owner decisions on its findings). Seed policy: `reports/capacity-shift-followup-seed-registry-20261027-01/SEED_REGISTRY_POLICY.md`. Preparation evidence, budget and fixtures: `reports/capacity-shift-followup-preparation-20261027-01/`. Derived from `work/capacity-ladder-source-20261026-01` (module names kept so the sealed analysis can be reused unchanged).

Files:
- `ladder_plan.py`: frozen constants and counts (G16, R/S_batch, eight depth-4 rungs, 40 epochs, twelve corpora). Pure; cannot launch.
- `ladder_registry.py`: exclusion census, the single outcome-blind draw and validation. Stdlib.
- `ladder_worker.py`: the WSL/CUDA worker. It runs the benchmark, applies the frozen cap formula, then runs twelve corpus stages. Lazy framework; refuses unless run from its enabled one-use activation.
- `framework_setup.py`: Linux-only Torch/CUDA admission (pins in `ORIGINAL_ENVIRONMENT.json`) and the cache redirect into the run. Byte copy.
- `ladder_analysis.py`: the sealed ladder analysis (byte copy); its loading, gain, fit and location functions are used by `shift_analysis.py`.
- `shift_analysis.py`: the frozen follow-up analysis (primary slope test and saturation rule, secondaries). Stdlib; run after the owner run, never during it.
- `FOLLOWUP_OWNER_RUN.ps1`: one-use owner entry; never runs from this directory.
- `vendor/`: byte copies of the confirmation's `core.py`, `engine.py`, `model.py`.

Status: SEALED_DISABLED. `AUTHORIZATION.json` is disabled. No registry has been drawn; no benchmark, activation, run, WSL process or training exists.
