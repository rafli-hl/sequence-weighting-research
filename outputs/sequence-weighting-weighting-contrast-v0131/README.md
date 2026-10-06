# v0131 source-only handoff

This distinct package performs a bounded exploratory **existing-data** analysis. The user approved preparation only. No command here has been run, and neither source review nor launch approval is implied by this file. Preserve all v0128 and v0130 files. The v0130 no-clip arm is deliberately excluded.

## Inventory and output contract

Read 60 matched G1/G16 × width 64/128/256 × five corpus × two nested-seed pairs, each with random and uniform v0128 clip-1 F10 controls (120 existing trajectories). All six saved epochs form 360 secondary pair rows. Primary is the ten G1 width-128 F10 pairs. No outcome-dependent choice, p* refit, model preparation, model evaluation, training, or GPU is needed. The full protocol is `PROTOCOL.md`.

An approved first run would create **only** `outputs/sequence-weighting-weighting-contrast-v0131/results-fixed-policy-v0131-20261003-01/` with `INPUT_BINDINGS.json`, `PAIRS.json`, `SUMMARY.json`, `COMPONENT_TABLE.csv`, `PAIRED_FIGURE.png`, and `ANALYSIS_COMPLETE.json`. Failure writes `FAILURE.json` and removes success. `COMPONENT_TABLE.csv` contains five corpus rows with total and shared/group/instance divided-by-three test contributions. `PAIRS.json` contains total and component training-gain quartile contrasts for all 60 F10 pairs; `SUMMARY.json` aggregates the ten primary G1 width-128 F10 pairs into five corpus means and descriptive mean/SD/range. Component training contrasts are in component NLL nats with no division by three; their average recovers the total. The paired figure shows both nested primary values/corpus means and stacked test component contributions. A separate reconciliation checks all 60 F10 quartile rows and every primary total/component quartile summary before creating `RECONCILIATION.json` or `RECONCILIATION_FAILURE.json`. Zero exit and source-bound independent output review are still required before scientific acceptance. A null or mixed contrast is a valid complete result.

Each phase has a five-minute full-process ceiling, implemented as 297 s work plus 3 s kill grace. Added source/results/logs/receipts and a 2-MiB terminal-receipt reserve must remain <=64 MiB; free space must stay >=2 GiB. Stop on missing or changed inputs, pair arithmetic, nonfinite values, limits, or nonzero exit. Do not regenerate inputs, resume, retry, raise caps or choose a different epoch because of a result. These budgets are prospective and unmeasured.

## Future Ubuntu commands, requiring separate review and launch authorization

Use the existing Ubuntu terminal from the D: project. Replace `REVIEWED_MANIFEST_SHA256` with the independently accepted exact hash after source review. Set `CUDA_VISIBLE_DEVICES` empty for CPU-only work. These commands have **not** been executed. The saved `status=$?` immediately follows each timeout and preserves the original process exit. Exit 124/137, any other nonzero code, missing terminal receipt, or failure marker blocks the next step.

```bash
cd /mnt/d/codex/sequence-weighting-research
export CUDA_VISIBLE_DEVICES=''
APPROVED_SHA='REVIEWED_MANIFEST_SHA256'
mkdir -p outputs/sequence-weighting-weighting-contrast-v0131/receipts
date -u +%FT%TZ > outputs/sequence-weighting-weighting-contrast-v0131/receipts/analysis-start.utc
/usr/bin/timeout --signal=INT --kill-after=3s 297s work/.venv-wsl/bin/python -B outputs/sequence-weighting-weighting-contrast-v0131/analyze.py --approved-manifest-sha256 "$APPROVED_SHA" > outputs/sequence-weighting-weighting-contrast-v0131/receipts/analysis.stdout 2> outputs/sequence-weighting-weighting-contrast-v0131/receipts/analysis.stderr
status=$?
date -u +%FT%TZ > outputs/sequence-weighting-weighting-contrast-v0131/receipts/analysis-end.utc
printf '%s\n' "$status" > outputs/sequence-weighting-weighting-contrast-v0131/receipts/analysis.exit
sha256sum outputs/sequence-weighting-weighting-contrast-v0131/receipts/analysis.stdout outputs/sequence-weighting-weighting-contrast-v0131/receipts/analysis.stderr > outputs/sequence-weighting-weighting-contrast-v0131/receipts/analysis.logs.sha256
wc -c outputs/sequence-weighting-weighting-contrast-v0131/receipts/analysis.stdout outputs/sequence-weighting-weighting-contrast-v0131/receipts/analysis.stderr > outputs/sequence-weighting-weighting-contrast-v0131/receipts/analysis.logs.bytes
test "$status" -eq 0
```

Expect one `complete fixed-policy weighting contrast; 60 pairs, 360 checkpoint comparisons` stdout line, `ANALYSIS_COMPLETE.json`, no `FAILURE.json`, and bounded disk/free-space readback. Only after reviewing that receipt and coverage should the separately bounded reconciliation be considered:

```bash
date -u +%FT%TZ > outputs/sequence-weighting-weighting-contrast-v0131/receipts/reconcile-start.utc
/usr/bin/timeout --signal=INT --kill-after=3s 297s work/.venv-wsl/bin/python -B outputs/sequence-weighting-weighting-contrast-v0131/reconcile.py --approved-manifest-sha256 "$APPROVED_SHA" > outputs/sequence-weighting-weighting-contrast-v0131/receipts/reconcile.stdout 2> outputs/sequence-weighting-weighting-contrast-v0131/receipts/reconcile.stderr
status=$?
date -u +%FT%TZ > outputs/sequence-weighting-weighting-contrast-v0131/receipts/reconcile-end.utc
printf '%s\n' "$status" > outputs/sequence-weighting-weighting-contrast-v0131/receipts/reconcile.exit
sha256sum outputs/sequence-weighting-weighting-contrast-v0131/receipts/reconcile.stdout outputs/sequence-weighting-weighting-contrast-v0131/receipts/reconcile.stderr > outputs/sequence-weighting-weighting-contrast-v0131/receipts/reconcile.logs.sha256
wc -c outputs/sequence-weighting-weighting-contrast-v0131/receipts/reconcile.stdout outputs/sequence-weighting-weighting-contrast-v0131/receipts/reconcile.stderr > outputs/sequence-weighting-weighting-contrast-v0131/receipts/reconcile.logs.bytes
test "$status" -eq 0
```

Expected reconciliation stdout is one `complete independent reconciliation; 360 paired checkpoints` line, `RECONCILIATION.json`, and no `RECONCILIATION_FAILURE.json`. Capture host start/end, actual exit, log hashes/sizes, output hashes, peak RSS, total new bytes and free-space readback for both phases. There is no native Windows `wsl.exe` route in this packet.
