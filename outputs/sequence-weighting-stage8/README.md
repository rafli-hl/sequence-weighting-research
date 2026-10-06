# Stage 8 v0.9 — fixed-input objective precision

Read PROTOCOL_STAGE8.md. This authorized CPU follow-up evaluates all retained
Stage 7 cancellation cases at a frozen grid. Original fits and data stay intact.
80-digit calculations are checked independently at 110 digits. Guard controls,
ties, ranking changes and every failure remain recorded. This is a numerical
diagnostic on reused data, without new model-generalization evidence.

Run through Ubuntu WSL from the project root with work/.venv-wsl/bin/python.
Use unique run IDs beginning precision-v09-; every phase refuses an existing destination/marker.
Order: analysis_checks.py --output <new-check-path>; check_stage8.py --output
<new-check-path>; stage8.py --run-id <new-id> --phase prepare --checks <current
runner-check-path> --analysis-checks <current source-bound analysis-check-path>
--review <current design-review-path>; then stage8.py --phase experiment with
that run ID, audit_stage8.py --run-id, and analyze_stage8.py --run-id.

All source and input hashes freeze before new objective profiles. A completed
experiment marker does not replace independent audit and figure/archive review.
Do not edit frozen files, including this README, after preparation. Put completion
notes in root documentation and a separate final-review record. Any presentation
revision must preserve original outputs and verify identical numerical records.
