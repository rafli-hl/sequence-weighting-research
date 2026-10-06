#!/usr/bin/env bash
# Source only. Called inside the single 30-minute outer watchdog after review.
set -euo pipefail
cd /mnt/d/codex/sequence-weighting-research
V0133_BUNDLE="$PWD/outputs/sequence-weighting-clipping-interaction-v0133-r1"
V0133_PY="$PWD/work/.venv-wsl/bin/python"
V0133_REVIEW="$V0133_BUNDLE/reviews/SOURCE_REVIEW.json"
test -f "$V0133_REVIEW"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
"$V0133_PY" -B -u "$V0133_BUNDLE/supervise.py" prepare --review "$V0133_REVIEW"
"$V0133_PY" -B -u "$V0133_BUNDLE/supervise.py" pretrain --review "$V0133_REVIEW"
"$V0133_PY" -B -u "$V0133_BUNDLE/supervise.py" adapt --review "$V0133_REVIEW"
