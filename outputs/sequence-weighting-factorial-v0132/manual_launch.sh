#!/usr/bin/env bash
# SOURCE ONLY. Manual Ubuntu invocation after independent exact-source acceptance.
# The agent must not launch WSL or execute this script in the preparation phase.
set -euo pipefail
cd /mnt/d/codex/sequence-weighting-research
V0132_BUNDLE="$PWD/outputs/sequence-weighting-factorial-v0132"
V0132_PY="$PWD/work/.venv-wsl/bin/python"
V0132_MODE="${1:?Use runtime or audit}"
V0132_RECEIPTS="$V0132_BUNDLE/receipts"
mkdir -p "$V0132_RECEIPTS"
V0132_TARGET="$V0132_RECEIPTS/outer-$V0132_MODE"
test ! -e "$V0132_RECEIPTS/FAILED.json"
test ! -e "$V0132_TARGET.started.json"
test -f "$V0132_BUNDLE/reviews/SOURCE_REVIEW.json"
if [[ "$V0132_MODE" == runtime ]]; then
  test ! -e "$PWD/work/runs/factorial-v0132-20261004-01"
  V0132_WORK_LIMIT=1790
  V0132_TOTAL_LIMIT=1800
  V0132_COMMAND=(bash "$V0132_BUNDLE/runtime_phases.sh")
elif [[ "$V0132_MODE" == audit ]]; then
  test -e "$V0132_RECEIPTS/outer-runtime.exit.json"
  test -e "$V0132_RECEIPTS/adapt.postwrite.json"
  test ! -e "$V0132_BUNDLE/results-fresh-factorial-v0132-20261004-01"
  V0132_WORK_LIMIT=590
  V0132_TOTAL_LIMIT=600
  V0132_COMMAND=("$V0132_PY" -B -u "$V0132_BUNDLE/supervise.py" audit --review "$V0132_BUNDLE/reviews/SOURCE_REVIEW.json")
else
  exit 2
fi
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# GNU time measures watchdog + worker termination. The envelope reserves 5 s
# after timeout's TERM/KILL window for the final shell receipts, inside the cap.
V0132_START_NS=$(date +%s%N)
printf '{"mode":"%s","start_utc":"%s","start_ns":%s,"total_limit_seconds":%s}\n' \
  "$V0132_MODE" "$(date -u +%FT%TZ)" "$V0132_START_NS" "$V0132_TOTAL_LIMIT" > "$V0132_TARGET.started.json"
set +e
/usr/bin/time -f 'elapsed_seconds=%e\nexit_code=%x\nmax_rss_kib=%M' -o "$V0132_TARGET.time.txt" \
  timeout --signal=TERM --kill-after=5s "${V0132_WORK_LIMIT}s" "${V0132_COMMAND[@]}" \
  > "$V0132_TARGET.stdout.log" 2> "$V0132_TARGET.stderr.log"
V0132_EXIT=$?
set -e
V0132_END_NS=$(date +%s%N)
V0132_ELAPSED_NS=$((V0132_END_NS-V0132_START_NS))
if (( V0132_ELAPSED_NS >= V0132_TOTAL_LIMIT*1000000000 )); then V0132_EXIT=125; fi
if (( V0132_EXIT != 0 )); then
  if [[ ! -e "$V0132_RECEIPTS/FAILED.json" ]]; then
    printf '{"mode":"%s","exit_code":%s,"reason":"outer watchdog or phase failure; do not retry"}\n' \
      "$V0132_MODE" "$V0132_EXIT" > "$V0132_RECEIPTS/FAILED.json"
  fi
fi
V0132_STDOUT_SHA=$(sha256sum "$V0132_TARGET.stdout.log"); V0132_STDOUT_SHA=${V0132_STDOUT_SHA%% *}
V0132_STDERR_SHA=$(sha256sum "$V0132_TARGET.stderr.log"); V0132_STDERR_SHA=${V0132_STDERR_SHA%% *}
printf '{"mode":"%s","exit_code":%s,"elapsed_ns_before_receipt":%s,"end_utc":"%s","stdout_sha256":"%s","stderr_sha256":"%s","time_receipt":"%s","timing_note":"includes watchdog and child termination; last shell receipt IO is inside the 5-second envelope reserve"}\n' \
  "$V0132_MODE" "$V0132_EXIT" "$V0132_ELAPSED_NS" "$(date -u +%FT%TZ)" "$V0132_STDOUT_SHA" "$V0132_STDERR_SHA" \
  "$(basename "$V0132_TARGET.time.txt")" > "$V0132_TARGET.exit.json"
printf '{"after_exit_receipt_ns":%s,"start_ns":%s}\n' "$(date +%s%N)" "$V0132_START_NS" > "$V0132_TARGET.postwrite.json"
exit "$V0132_EXIT"
