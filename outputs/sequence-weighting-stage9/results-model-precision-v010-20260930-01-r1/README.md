# Stage 9 (v0.10)

Bounded CPU audit of complete saved Stage 4 fixed30 and Stage 5–6 R/random policy
cohorts. Read PROTOCOL_STAGE9.md before running. No training, inference, new
selection or original-p replacement. Use the existing WSL environment from the
current project root; historical absolute paths remain provenance only.

```bash
work/.venv-wsl/bin/python outputs/sequence-weighting-stage9/stage9.py --run-id model-precision-v010-20260930-01 --phase inventory
work/.venv-wsl/bin/python outputs/sequence-weighting-stage9/check_stage9.py --output work/stage9-checks-20260930-01.json
work/.venv-wsl/bin/python outputs/sequence-weighting-stage9/analysis_checks.py --output work/stage9-analysis-checks-20260930-01.json
# Independent source-bound design review must exist before preparation.
work/.venv-wsl/bin/python outputs/sequence-weighting-stage9/stage9.py --run-id model-precision-v010-20260930-01 --phase prepare
work/.venv-wsl/bin/python outputs/sequence-weighting-stage9/stage9.py --run-id model-precision-v010-20260930-01 --phase experiment
work/.venv-wsl/bin/python outputs/sequence-weighting-stage9/audit_stage9.py --run-id model-precision-v010-20260930-01
work/.venv-wsl/bin/python outputs/sequence-weighting-stage9/analyze_stage9.py --run-id model-precision-v010-20260930-01
```

Every output is create-only. Failed/partial evidence stays in place; never reuse
an existing run or result directory. Decimal80/110 full profiles, aliases,
native checkpoints, original constituent losses, provenance, full-data pairing,
runtime, memory and failures are retained. Only equivalent Python scripts are
executed; no notebook execution is claimed.
