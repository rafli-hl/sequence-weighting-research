#!/usr/bin/env bash
# SOURCE ONLY. Manual Ubuntu invocation after independent exact-source acceptance.
# The agent must not launch WSL or execute this script in the preparation phase.
set -euo pipefail
cd /mnt/d/codex/sequence-weighting-research
V0136_BUNDLE="$PWD/outputs/sequence-weighting-compensation-calibration-v0136"
V0136_PY="$PWD/work/.venv-wsl/bin/python"
V0136_MODE="${1:?Use runtime or audit}"
V0136_RECEIPTS="$V0136_BUNDLE/receipts"
mkdir -p "$V0136_RECEIPTS"
V0136_TARGET="$V0136_RECEIPTS/outer-$V0136_MODE"
test ! -e "$V0136_RECEIPTS/FAILED.json"
test ! -e "$V0136_TARGET.started.json"
test ! -e "$V0136_TARGET.pgid"
test ! -e "$V0136_TARGET.pgid.pending"
test ! -e "$V0136_TARGET.go"
test ! -e "$V0136_TARGET.cancel"
test -f "$V0136_BUNDLE/reviews/SOURCE_REVIEW.json"
test -f "$V0136_BUNDLE/reviews/CALIBRATION_RUNTIME_APPROVAL.json"
if [[ "$V0136_MODE" == runtime ]]; then
  test ! -e "$PWD/work/runs/compensation-calibration-v0136-20261005-01"
  # Fresh study; no prior runtime attempt charge.
  V0136_WORK_LIMIT=890
  V0136_TOTAL_LIMIT=900
  V0136_COMMAND=(bash "$V0136_BUNDLE/runtime_phases.sh")
elif [[ "$V0136_MODE" == audit ]]; then
  test -e "$V0136_RECEIPTS/outer-runtime.exit.json"
  test -e "$V0136_RECEIPTS/fit.postwrite.json"
  test ! -e "$V0136_BUNDLE/results-fresh-compensation-calibration-v0136-20261005-01"
  V0136_WORK_LIMIT=290
  V0136_TOTAL_LIMIT=300
  V0136_COMMAND=("$V0136_PY" -B -u "$V0136_BUNDLE/supervise.py" audit --review "$V0136_BUNDLE/reviews/SOURCE_REVIEW.json")
else
  exit 2
fi
export PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# GNU time measures watchdog + worker termination. The envelope reserves 5 s
# after timeout's TERM/KILL window for the final shell receipts, inside the cap.
V0136_START_NS=$(date +%s%N)
printf '{"mode":"%s","start_utc":"%s","start_ns":%s,"total_limit_seconds":%s}\n' \
  "$V0136_MODE" "$(date -u +%FT%TZ)" "$V0136_START_NS" "$V0136_TOTAL_LIMIT" > "$V0136_TARGET.started.json"
# Register the timeout group BEFORE exec of any scientific phase. Registration
# belongs to the outer launcher, not to a supervisor/worker launch receipt.
V0136_LAUNCHER_GROUP=$(ps -o pgid= -p "$$")
V0136_LAUNCHER_GROUP=${V0136_LAUNCHER_GROUP//[[:space:]]/}
V0136_GROUP=null
V0136_REGISTERED=false
V0136_TERMINATION_CONFIRMED=false
V0136_SURVIVORS=false
V0136_CLEANUP_REASON=none
V0136_CLEANUP_DONE=false
V0136_CLEANUP_STARTED=false
V0136_TIME_PID=null
V0136_WRAPPER_REAPED=false
V0136_CANCEL=0
v0136_cancel() {
  V0136_CANCEL=$1
  : > "$V0136_TARGET.cancel"
  if [[ ! -e "$V0136_RECEIPTS/FAILED.json" ]]; then
    printf '{"mode":"%s","exit_code":%s,"reason":"outer cancellation/start-gate failure; do not retry"}\n' \
      "$V0136_MODE" "$V0136_CANCEL" > "$V0136_RECEIPTS/FAILED.json"
  fi
  # A signal after cleanup/acceptance checks must still force a failed return.
  if [[ "$V0136_CLEANUP_DONE" == true ]]; then exit "$V0136_CANCEL"; fi
  # Do not rely on a future wait being interrupted: a signal can arrive between
  # its condition and the wait call. Once $! is captured, clean directly in the
  # trap. Earlier signals only record cancellation; cleanup signals cannot recurse.
  if [[ "$V0136_TIME_PID" != null && "$V0136_CLEANUP_STARTED" != true ]]; then
    v0136_cleanup_group
    exit "$V0136_CANCEL"
  fi
}
v0136_group_present() {
  local groups candidate
  if ! groups=$(ps -eo pgid=); then return 2; fi
  while read -r candidate; do
    if [[ "$candidate" == "$V0136_GROUP" ]]; then return 0; fi
  done <<< "$groups"
  return 1
}
v0136_cleanup_group() {
  local presence term_end confirm_end now wrapper_state
  V0136_CLEANUP_STARTED=true
  now=$(date +%s%N)
  term_end=$((now+2000000000))
  confirm_end=$((now+3000000000))
  if (( term_end > V0136_START_NS+(V0136_TOTAL_LIMIT-3)*1000000000 )); then
    term_end=$((V0136_START_NS+(V0136_TOTAL_LIMIT-3)*1000000000))
  fi
  if (( confirm_end > V0136_START_NS+(V0136_TOTAL_LIMIT-2)*1000000000 )); then
    confirm_end=$((V0136_START_NS+(V0136_TOTAL_LIMIT-2)*1000000000))
  fi
  # A cancellation can precede registration. The closed GO gate prevents phase
  # exec; use the SAME cleanup allowance to collect the late group registration.
  while [[ ! -f "$V0136_TARGET.pgid" && "$V0136_TIME_PID" != null ]] && (( $(date +%s%N) < term_end )); do
    if ! kill -0 "$V0136_TIME_PID" 2>/dev/null; then break; fi
    sleep .05
  done
  if [[ -f "$V0136_TARGET.pgid" ]]; then
    read -r V0136_GROUP < "$V0136_TARGET.pgid"
  fi
  if [[ ! "$V0136_GROUP" =~ ^[0-9]+$ ]] || (( V0136_GROUP <= 1 )) || [[ "$V0136_GROUP" == "$V0136_LAUNCHER_GROUP" ]]; then
    V0136_GROUP=null
    V0136_CLEANUP_REASON=missing_or_unsafe_group_registration
  else
    V0136_REGISTERED=true
    if v0136_group_present; then presence=0; else presence=$?; fi
    if (( presence == 1 )); then
      V0136_TERMINATION_CONFIRMED=true
    else
      V0136_SURVIVORS=true
      V0136_CLEANUP_REASON=surviving_group_or_failed_probe
      kill -TERM -- "-$V0136_GROUP" 2>/dev/null || true
      while (( $(date +%s%N) < term_end )); do
        if v0136_group_present; then presence=0; else presence=$?; fi
        if (( presence == 1 )); then V0136_TERMINATION_CONFIRMED=true; break; fi
        if (( presence == 2 )); then break; fi
        sleep .05
      done
      if [[ "$V0136_TERMINATION_CONFIRMED" != true ]]; then
        kill -KILL -- "-$V0136_GROUP" 2>/dev/null || true
        while (( $(date +%s%N) < confirm_end )); do
          if v0136_group_present; then presence=0; else presence=$?; fi
          if (( presence == 1 )); then V0136_TERMINATION_CONFIRMED=true; break; fi
          if (( presence == 2 )); then break; fi
          sleep .05
        done
      fi
    fi
  fi
  # Reap only after observing wrapper exit/zombie, so this wait cannot become a
  # new unbounded foreground wait. Group cleanup and reaping share the 3 s cap.
  while [[ "$V0136_TIME_PID" != null && "$V0136_WRAPPER_REAPED" != true ]]; do
    if wrapper_state=$(ps -o stat= -p "$V0136_TIME_PID"); then
      wrapper_state=${wrapper_state//[[:space:]]/}
      if [[ "$wrapper_state" != Z* ]]; then
        if (( $(date +%s%N) >= confirm_end-200000000 )); then kill -KILL "$V0136_TIME_PID" 2>/dev/null || true; fi
        if (( $(date +%s%N) >= confirm_end )); then break; fi
        sleep .05
        continue
      fi
    else
      # A missing PID must also pass kill -0; failed ps alone is not evidence.
      if kill -0 "$V0136_TIME_PID" 2>/dev/null; then break; fi
    fi
    if wait "$V0136_TIME_PID"; then presence=0; else presence=$?; fi
    if (( presence != 127 )) && ! kill -0 "$V0136_TIME_PID" 2>/dev/null; then V0136_WRAPPER_REAPED=true; fi
    break
  done
  printf '{"process_group_id":%s,"registered_before_phase_exec":%s,"survivors_at_outer_return":%s,"termination_confirmed":%s,"timing_wrapper_pid":%s,"timing_wrapper_reaped":%s,"cancellation_exit_code":%s,"cleanup_reason":"%s","elapsed_ns_after_cleanup":%s}\n' \
    "$V0136_GROUP" "$V0136_REGISTERED" "$V0136_SURVIVORS" "$V0136_TERMINATION_CONFIRMED" \
    "$V0136_TIME_PID" "$V0136_WRAPPER_REAPED" "$V0136_CANCEL" "$V0136_CLEANUP_REASON" \
    "$(($(date +%s%N)-V0136_START_NS))" > "$V0136_TARGET.containment.json"
  V0136_CLEANUP_DONE=true
}
# Catch cancellation/unexpected shell exits as well as the ordinary wait return.
trap 'v0136_cancel 130' INT
trap 'v0136_cancel 143' TERM
trap 'V0136_TRAP_EXIT=$?; if [[ "$V0136_CLEANUP_DONE" != true ]]; then : > "$V0136_TARGET.cancel"; v0136_cleanup_group; if [[ ! -e "$V0136_RECEIPTS/FAILED.json" ]]; then printf "{\"mode\":\"%s\",\"exit_code\":%s,\"reason\":\"outer launcher interrupted; retained containment receipt\"}\n" "$V0136_MODE" "$V0136_TRAP_EXIT" > "$V0136_RECEIPTS/FAILED.json"; fi; fi' EXIT
set +e
if (( V0136_CANCEL == 0 )); then
/usr/bin/time -f 'elapsed_seconds=%e\nexit_code=%x\nmax_rss_kib=%M' -o "$V0136_TARGET.time.txt" \
  timeout --signal=TERM --kill-after=5s "${V0136_WORK_LIMIT}s" \
  bash -c 'set -euo pipefail; set -o noclobber; receipt=$1; launcher_group=$2; go=$3; cancel=$4; shift 4; shell_pid=$BASHPID; group=$(ps -o pgid= -p "$shell_pid"); group=${group//[[:space:]]/}; [[ "$group" =~ ^[0-9]+$ ]]; (( group > 1 )); [[ "$group" != "$launcher_group" ]]; printf "%s\n" "$group" > "$receipt.pending"; ln "$receipt.pending" "$receipt"; while [[ ! -e "$go" ]]; do [[ ! -e "$cancel" ]] || exit 143; sleep .05; done; [[ ! -e "$cancel" ]] || exit 143; exec "$@"' \
  v0133-register "$V0136_TARGET.pgid" "$V0136_LAUNCHER_GROUP" "$V0136_TARGET.go" "$V0136_TARGET.cancel" "${V0136_COMMAND[@]}" \
  > "$V0136_TARGET.stdout.log" 2> "$V0136_TARGET.stderr.log" &
V0136_TIME_PID=$!
# Capture $! before handling cancellation. The trap records cancellation and
# closes the gate; it never exits in the launch/PID-assignment race.
while [[ ! -f "$V0136_TARGET.pgid" ]] && (( V0136_CANCEL == 0 )); do
  if ! kill -0 "$V0136_TIME_PID" 2>/dev/null; then break; fi
  if (( $(date +%s%N) >= V0136_START_NS+V0136_WORK_LIMIT*1000000000 )); then v0136_cancel 125; break; fi
  sleep .05
done
if (( V0136_CANCEL == 0 )) && [[ -f "$V0136_TARGET.pgid" ]]; then
  read -r V0136_GROUP < "$V0136_TARGET.pgid"
  if [[ "$V0136_GROUP" =~ ^[0-9]+$ ]] && (( V0136_GROUP > 1 )) && [[ "$V0136_GROUP" != "$V0136_LAUNCHER_GROUP" ]]; then
    : > "$V0136_TARGET.go"
  else
    v0136_cancel 125
  fi
fi
if (( V0136_CANCEL == 0 )); then
  wait "$V0136_TIME_PID"
  V0136_EXIT=$?
  if (( V0136_CANCEL == 0 )); then V0136_WRAPPER_REAPED=true; fi
else
  V0136_EXIT=$V0136_CANCEL
fi
else
  V0136_EXIT=$V0136_CANCEL
  : > "$V0136_TARGET.stdout.log"
  : > "$V0136_TARGET.stderr.log"
fi
set -e
if (( V0136_CANCEL != 0 )); then V0136_EXIT=$V0136_CANCEL; fi
v0136_cleanup_group
# Even with eventual cleanup, surviving workers at leader return indicate failure.
if [[ "$V0136_REGISTERED" != true || "$V0136_TERMINATION_CONFIRMED" != true || "$V0136_SURVIVORS" == true || "$V0136_WRAPPER_REAPED" != true ]] || (( V0136_CANCEL != 0 )); then
  V0136_EXIT=125
fi
V0136_CONTAINMENT_HASH=$(sha256sum "$V0136_TARGET.containment.json")
V0136_CONTAINMENT_HASH=${V0136_CONTAINMENT_HASH%% *}
V0136_END_NS=$(date +%s%N)
V0136_ELAPSED_NS=$((V0136_END_NS-V0136_START_NS))
if (( V0136_ELAPSED_NS >= V0136_TOTAL_LIMIT*1000000000 )); then V0136_EXIT=125; fi
if (( V0136_EXIT != 0 )); then
  if [[ ! -e "$V0136_RECEIPTS/FAILED.json" ]]; then
    printf '{"mode":"%s","exit_code":%s,"reason":"outer watchdog or phase failure; do not retry"}\n' \
      "$V0136_MODE" "$V0136_EXIT" > "$V0136_RECEIPTS/FAILED.json"
  fi
fi
V0136_STDOUT_SHA=$(sha256sum "$V0136_TARGET.stdout.log"); V0136_STDOUT_SHA=${V0136_STDOUT_SHA%% *}
V0136_STDERR_SHA=$(sha256sum "$V0136_TARGET.stderr.log"); V0136_STDERR_SHA=${V0136_STDERR_SHA%% *}
printf '{"mode":"%s","exit_code":%s,"elapsed_ns_before_receipt":%s,"end_utc":"%s","stdout_sha256":"%s","stderr_sha256":"%s","time_receipt":"%s","containment_sha256":"%s","timing_note":"includes watchdog plus outer-owned group cleanup; all grace and receipts remain inside unchanged caps"}\n' \
  "$V0136_MODE" "$V0136_EXIT" "$V0136_ELAPSED_NS" "$(date -u +%FT%TZ)" "$V0136_STDOUT_SHA" "$V0136_STDERR_SHA" \
  "$(basename "$V0136_TARGET.time.txt")" "$V0136_CONTAINMENT_HASH" > "$V0136_TARGET.exit.json"
printf '{"after_exit_receipt_ns":%s,"start_ns":%s}\n' "$(date +%s%N)" "$V0136_START_NS" > "$V0136_TARGET.postwrite.json"
exit "$V0136_EXIT"
