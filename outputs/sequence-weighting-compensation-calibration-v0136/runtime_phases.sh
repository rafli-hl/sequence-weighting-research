#!/usr/bin/env bash
# Source only. Called inside the single 15-minute outer watchdog after review.
set -euo pipefail
cd /mnt/d/codex/sequence-weighting-research
V0136_BUNDLE="$PWD/outputs/sequence-weighting-compensation-calibration-v0136"
V0136_PY="$PWD/work/.venv-wsl/bin/python"
V0136_REVIEW="$V0136_BUNDLE/reviews/SOURCE_REVIEW.json"
test -f "$V0136_REVIEW"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
"$V0136_PY" -B -u "$V0136_BUNDLE/supervise.py" prepare --review "$V0136_REVIEW"
"$V0136_PY" -B -u "$V0136_BUNDLE/supervise.py" pretrain --review "$V0136_REVIEW"
"$V0136_PY" -B -u "$V0136_BUNDLE/supervise.py" adapt --review "$V0136_REVIEW"
"$V0136_PY" -B -u "$V0136_BUNDLE/supervise.py" fit --review "$V0136_REVIEW"
