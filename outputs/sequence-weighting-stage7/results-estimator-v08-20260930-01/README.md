# Stage 7 v0.8 — CPU estimator validity

Read PROTOCOL_STAGE7.md. This is the authorized NEXT_EXPERIMENT.md follow-up:
8,320 prescribed fits from 128 independent base draws, using the unchanged
Stage 6 exponent estimator. Signed gains, undefined and boundary fits are kept.
SYNTHESIS_STAGE4_6.md separates prior model evidence from estimator recovery.

Run locally from the project root through Ubuntu WSL with
work/.venv-wsl/bin/python. Use unique run IDs; every output refuses overwrite.
Preparation snapshots all source, protocol, outcome-independent checks and
design review before simulations. No GPU training is performed.

Order: analysis_checks.py --output work/stage7-analysis-checks-20260930-01.json;
check_stage7.py --output work/stage7-checks-20260930-01.json; then
stage7.py --run-id estimator-v08-20260930-01 --phase prepare and --phase experiment;
audit_stage7.py --run-id estimator-v08-20260930-01; finally
analyze_stage7.py --run-id estimator-v08-20260930-01.

Preparation also requires work/stage7-design-review-20260930-01.json with PASS.
Preserve failed/partial runs and use new IDs for separately declared reruns.
Raw: work/runs/<run-id>/. Analysis: this directory/results-<run-id>/.
A COMPLETE marker alone is not scientific acceptance: independent audit,
summary checks, figure review and archive verification are required.
