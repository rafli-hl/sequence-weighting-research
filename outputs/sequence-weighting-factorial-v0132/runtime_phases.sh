#!/usr/bin/env bash
# Source only. Called inside the single 30-minute outer watchdog after review.
set -euo pipefail
cd /mnt/d/codex/sequence-weighting-research
V0132_BUNDLE="$PWD/outputs/sequence-weighting-factorial-v0132"
V0132_PY="$PWD/work/.venv-wsl/bin/python"
V0132_REVIEW="$V0132_BUNDLE/reviews/SOURCE_REVIEW.json"
test -f "$V0132_REVIEW"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
"$V0132_PY" -B -u "$V0132_BUNDLE/supervise.py" prepare --review "$V0132_REVIEW"
"$V0132_PY" -B -u "$V0132_BUNDLE/supervise.py" pretrain --review "$V0132_REVIEW"
"$V0132_PY" -B -u "$V0132_BUNDLE/supervise.py" adapt --review "$V0132_REVIEW"
