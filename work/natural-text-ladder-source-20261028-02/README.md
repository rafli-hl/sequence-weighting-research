# Natural-text capacity ladder: disabled source

- **Design:** `PROTOCOL.md`: revision 05, the second and final attempt (owner ruling of 28 Oct 2026, section 12). It is revision 04 with operational changes only: new -02 Run B folders, a Windows-side GPU check, and an analysis that refuses attempt 1.
- **Seed policy:** `reports/natural-text-ladder-seed-registry-20261028-01/SEED_REGISTRY_POLICY.md`.
- **Preparation, budget, fixtures and review:** `reports/natural-text-ladder-preparation-20261028-01/` (revision 04) and `reports/natural-text-ladder-revision-05-20261028-01/` (revision 05).

## Files

**Pure modules (stdlib)**
- `text_plan.py`: the frozen constants: tokenizer, text hashes, article rule, draws, run layouts (A, B, B1, B2), recipe, readouts, the two-lines minimum widths per line, and limits. Cannot launch.
- `text_data.py`: the article split, chunking, stride selections, the seeded article partition with the N fallback, and the corpus-manifest check.
- `text_registry.py`: the exclusion census, the single outcome-blind seed draw (which requires the corpus manifest) and validation.

**Run steps**
- `prepare_corpus.py`: the corpus and tokenizer step (WSL, locked `tokenizers`). It verifies the text hashes, trains the tokenizer twice and requires identical bytes, and writes the sequences and the checked manifest.
- `text_worker.py`: the WSL/CUDA worker for Run A (benchmark and tuning group) and Run B, or its split B1 and B2 (benchmark and draws). Run B stops before any training with FALLBACK_TO_SPLIT if its own benchmark puts ten draws over 6 h and five within it.
  - It refuses unless run from an enabled one-use activation with an IDLE Windows pre-start GPU check.
  - Before every draw, it asks the owner script for a GPU check and records the verdict (revision 05).
- `select_lr.py`: the per-width learning-rate selection from Run A, which reads validation rows only, and the Run B plan from Run A's timing forecast.
- `text_analysis.py`: the frozen analysis (Primary A, peak shift; Primary B, curvature, vertex, two lines with a clamped data-located break and the per-point rise and fall; saturation rule; secondaries), on Run B or on Run B1 and Run B2. Stdlib. It refuses attempt 1 (revision 05).
- `TEXT_OWNER_RUN.ps1`: the one-use owner entry for Run B, B1 or B2; it never runs from this directory.
- `gpu_check.ps1` and `GPU_CHECK.json`: the Windows-side nvidia-smi checks and their sealed thresholds, dot-sourced by the owner entry (revision 05). While the worker runs, progress goes to `OWNER_PROGRESS.log` in the activation folder, not to the console.

**Framework (WSL only)**
- `text_model.py`, `text_engine.py`: the model and torch functions.
- `text_framework_setup.py`: the Linux-only Torch/CUDA admission, pinned by `ORIGINAL_ENVIRONMENT.json` (a byte copy).

**Copies**
- `vendor/core.py`: a byte copy of the confirmation's estimator.

## Status

SEALED_DISABLED: `AUTHORIZATION.json` is disabled.
- **Exist and are reused (revision 04):** the corpus, the registry, Run A and the learning-rate selection.
- **Do not exist:** any revision 05 activation or run.
