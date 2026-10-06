#!/usr/bin/env bash
# Source only. Both phases consume the SAME600-second outer allowance.
set -euo pipefail
cd /mnt/d/codex/sequence-weighting-research
V0134_BUNDLE="$PWD/outputs/sequence-weighting-gradient-alignment-v0134"
V0134_PY="$PWD/work/.venv-wsl/bin/python"
V0134_REVIEW="$V0134_BUNDLE/reviews/SOURCE_REVIEW.json"
test -f "$V0134_REVIEW"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# Phase1: frozen full existing-cohort gradient panel, no optimizer steps.
"$V0134_PY" -B -u "$V0134_BUNDLE/supervise.py" diagnose --review "$V0134_REVIEW"
# Phase2: independent bounded reductions/sign/scaling audit, only on phase1 exit0.
"$V0134_PY" -B -u "$V0134_BUNDLE/supervise.py" audit --review "$V0134_REVIEW"
