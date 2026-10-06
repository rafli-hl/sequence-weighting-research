# Stage 11 v0.12: group-rule sharing

This new implementation follows the reviewed G1/G16 proposal. Read
`PROTOCOL_STAGE11.md` and `IMPLEMENTATION_NOTES.md` for the prospective scientific
design and pre-outcome seed revision. `PARENT_SOURCES.json` records provenance.
Existing Stage 1–10 source and measurements remain unchanged.

The current task is implementation readiness and a pre-outcome freeze. A
run-specific `FREEZE.json` establishes frozen status; `RUN_STARTED.json` indicates
that research training actually began. Neither this README nor engineering
fixture outputs are research results.

## Entry points

Use `work/.venv-wsl/bin/python` from the project root through Ubuntu WSL.
All output paths must be new; scripts refuse silent overwrite or run resume.

```text
outputs/sequence-weighting-stage11/check_stage11.py --output NEW_ENGINE_CHECK.json
outputs/sequence-weighting-stage11/check_analysis.py --output NEW_ANALYSIS_CHECK.json
outputs/sequence-weighting-stage11/check_runner.py --output NEW_RUNNER_CHECK.json
outputs/sequence-weighting-stage11/check_report.py --output NEW_REPORT_FIXTURE_DIR
outputs/sequence-weighting-stage11/benchmark_stage11.py --output NEW_RESOURCE_CHECK.json --budget-seconds 120
outputs/sequence-weighting-stage11/stage11.py freeze --run-id NEW_RULE_TYING_ID --review IMPLEMENTATION_REVIEW.json
outputs/sequence-weighting-stage11/stage11.py run --run-id FROZEN_RULE_TYING_ID
outputs/sequence-weighting-stage11/analyze_stage11.py --run work/runs/FROZEN_RULE_TYING_ID --output NEW_RESULTS_DIR
```

The actual ID must match `rule-tying-v012-*`. Freeze requires independent
`PASS_IMPLEMENTATION_READY` acceptance with exact source/evidence hashes,
resource limits and cumulative preparation runtime. Tuning/confirmation IDs,
rules and selection are defined in `config.py` and `policies.py`.

The resource ceiling is 5,400 seconds for the complete training stage and 4 GiB
for the raw run plus compact archive, retaining a 2 GiB free reserve. Resource
fixtures measure unrelated engineering data only; they do not tune the research
grid. Canonical initial losses and test visibility are separate by condition
and phase. No p*, test score or visible peak enters hyperparameter selection.

After a future run, generated reports require independent metric/selection,
source/input, retained-binary, budget, archive SHA/CRC and visual checks before
experiment completion. Partial results and failures must remain visible. These
post-run checks are distinct from the current implementation acceptance.
