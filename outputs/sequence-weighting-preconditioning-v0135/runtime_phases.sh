#!/usr/bin/env bash
# Source only. Called inside the single 30-minute outer watchdog after review.
set -euo pipefail
cd /mnt/d/codex/sequence-weighting-research
V0135_BUNDLE="$PWD/outputs/sequence-weighting-preconditioning-v0135"
V0135_PY="$PWD/work/.venv-wsl/bin/python"
V0135_REVIEW="$V0135_BUNDLE/reviews/SOURCE_REVIEW.json"
test -f "$V0135_REVIEW"
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
"$V0135_PY" -B -u "$V0135_BUNDLE/supervise.py" prepare --review "$V0135_REVIEW"
"$V0135_PY" -B -u "$V0135_BUNDLE/supervise.py" pretrain --review "$V0135_REVIEW"
"$V0135_PY" -B -u "$V0135_BUNDLE/supervise.py" adapt --review "$V0135_REVIEW"
