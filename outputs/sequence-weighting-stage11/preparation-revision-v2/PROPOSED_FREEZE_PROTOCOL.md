# Proposed preparation revision v2 — not implemented or executed

## Why the current attempt stopped

Stage 11 implementation, scientific fixtures and the GPU resource benchmark
passed independent review. The v1 freeze command then exceeded its cumulative
300-second preparation allowance and stopped before writing `FREEZE.json`.
The failed directory `work/runs/rule-tying-v012-20260930-01/` is preserved.
It contains generated input tensors and source copies, but no research training,
pretrained research checkpoint, selected policy or model outcome.

The prior accounting was 290.557594982 seconds, including a disclosed 60-second
allowance for uninstrumented fixture/import timing. That allowance is not a
measured duration or proved upper bound. The freeze had less than 9.443 seconds
of accounting headroom. Its exact process elapsed was not saved in the failure
record; the 7.181598-second event-to-failure interval excludes module startup.
The explicit guard establishes that its combined accounted time exceeded 300
seconds. Do not replace that failed status with the successful resource estimate.

## Proposed change for a subsequent preparation attempt

Create a separate v0.12.1 source directory and a new run ID. Preserve the v1
sources, review, fixtures, generated inputs and failure. The change is limited
to preparation accounting and failure instrumentation:

1. Keep every v1 engineering attempt and cost in the historical ledger. Never
   describe the new allowance as successful completion within the old 300 seconds.
2. Define a separate **60-second maximum freeze-preparation process**, measured
   from before imports with both UTC and monotonic clocks, using the larger
   elapsed value. Include source/evidence/parent hash checks, environment capture,
   complete input generation, assignments, support counts, manifests and the
   final freeze writes. The limit is a proposed new engineering allowance,
   explicitly requiring a new source-bound review before use.
3. Save elapsed time, remaining allowance, phase, all planned missing artifacts
   and the exact source hashes on every success and failure. Check the ceiling
   after the final writes; if exceeded, retain a failure marker and make the run
   unlaunchable even if a provisional freeze file exists.
4. Reuse unchanged engine/policy/analysis fixture evidence only after verifying
   exact dependency hashes. Verify the changed timing and fail-closed paths with
   known clock fixtures, without regenerating model research outcomes. Record
   those checks separately from the subsequent 60-second freeze process.
5. Verify newly generated data/weight/order tensor equality against the v1
   failed preparation where available, without treating file serialization bytes
   as tensor identity. No resampling of seeds, weights or corpora.
6. Stop on time, source, pairing or storage failure. No automatic retry, resume
   or further budget increase. A successful new freeze is required before any
   research training.

This proposal does not change the research seeds, G1/G16 construction, shared U
pretraining, LR grid, model capacities, epochs, F/R policies, sample counts,
estimands, signed-gain guards, utility criteria or replication units. The
**5,400-second training ceiling, 4 GiB raw-plus-archive ceiling and 2 GiB free
reserve remain unchanged**. The existing resource projection (~3,160 seconds,
~3.82 GiB) remains an engineering estimate and does not justify bypassing guards.

This document is a prospective revision following a recorded preparation
failure. It is not approval to edit/resume the failed run, an active freeze,
or a research result. The immediate next work is implementation and independent
review of this narrow revision before a new preparation attempt.
