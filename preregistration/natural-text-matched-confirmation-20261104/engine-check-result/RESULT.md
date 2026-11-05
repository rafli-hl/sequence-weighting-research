# Matched-progress confirmation: result of the real-engine check

**Run by the owner,** under approval OWNER-20261104-MATCHED-ENGINE-01. **Result: PASS, both parts.** It is not a stage of any run and counts for nothing against the study. This reads no outcome.

**No corpus file was read.** The audit hook around each part saw no open or listing of any path holding `work/runs` (`GUARD_INPUTS.json`, `GUARD_SMOKE.json`), and `engine_check.py` names no corpus file. The hook sees Python-level opens in the check's own process. It does not see a stat, by which the check asks whether this study's activations and run folders exist, or the estimator's child process, which reads one temporary file of weights in the scratch folder.

**No study loss was computed.** No model saw study data. The inputs part builds no model: it hashes synthetic tokens and computes p\* on the real weights with synthetic gains, which is not a study result. The smoke test trains tiny models on synthetic tokens with test seeds. The sealed code computes their losses and writes them to `smoke-run/` in the scratch folder, where no step reads them. No record here holds a loss.

**Records:** `INPUTS_CHECK.json` (`022591d9…`), `SMOKE_CHECK.json` (`ecea6930…`), `GUARD_INPUTS.json` (`fcfeaec1…`) and `GUARD_SMOKE.json` (`745c3bf4…`), byte copies. `ENGINE_CHECK_VERIFICATION.json`: 25 of 25 checks, in code separate from the check. `OWNER_CONSOLE_OUTPUT.txt`: the owner's output. The scratch folder's `smoke-run/` holds synthetic losses, unopened, and is left for the owner.

**Both receipts bind** the check `8681f196…`, the subject `7ef133ad…`, Torch 2.7.0+cu126 and Python 3.12.3.

## Inputs (real Torch, CPU only; 20.0 s)

Real seed rows on synthetic tokens. The check compares the input hashes with those computed without Torch, the orders as permutations, and p\* on synthetic gains for bit-for-bit repeats.

| Draw | Tied values, real Torch | Native, numpy's mean | Limit |
|---|---|---|---|
| m01 | 3 | 3 | 16 |
| m02 | 4 | 4 | 16 |
| m03 | 1 | 0 | 16 |
| m04 | 1 | 1 | 16 |
| m05 | 1 | 1 | 16 |
| m06 | 1 | 1 | 16 |

Benchmark weights at 2048: 0 tied. **These real-Torch counts are the ones the results report must carry.**

**The one difference from the draw's disclosure** (added after the verifier ran, at the owner's instruction; `DISCLOSURE_FIGURES.md` is not edited): real Torch counted 1 tied value in m03, where the draw's numpy disclosure counted 0. The other five draws are equal: 3, 4, 1, 1, 1. Both counts are within the limit of 16. The disclosure says that real Torch's counts can differ by one or so, because the weights used are divided by Torch's mean and not numpy's, and only the limit is enforced.

## Smoke test (real Torch and CUDA; 46.9 s, on synthetic tokens and test seeds)

The sealed stage ran width 96 at 3e-4 and 1e-4 from one E0, and width 64 at 3e-4, to E3.5 with ten readouts. The two arms of width 96 differ by hash. **That is necessary and not sufficient,** because GPU training here is not set deterministic.

## What this does not reach

The real widths and N on the GPU, real stage times against the cap, the real corpus and the real manifest. The builder's real-mode input checks read the corpus under `work/runs/`, so they were not run here; they run when the owner builds the activation.

## Added after the scoped review (`review-03`)

These notes were added by hand after the verifier ran, as was the note on m03 above. Running `verify_engine_check.py` again would rewrite this file without them, so `PINNED_STATE_FILES.json` holds this file's hash. The review found the two statements above justified within their stated limits and these:

- **More limits of the hook.** It matches a path's text and does not resolve links, so a symlink alias, a `/proc/self/cwd` path or an open relative to a directory descriptor would not match. It does not list `sqlite3.connect`, `os.fork` or multiprocessing's `fork_exec`, so "every process" is as far as its list goes. The estimator's child also imports the sealed source, and the suite's at-import check shows nothing under `work/runs` there. The review searched the sealed source and found none of those calls.
- **"No step reads them" is looser than the code.** `check_stage` loads each `record.json`, tests that each loss field holds a number, and hashes each `arrays.f32`. No value leaves that function, and none reaches a receipt. These are synthetic losses on test seeds, so "No study loss was computed" is untouched. That statement rests on the hash-bound code, and it is not a measurement.
- **The m03 count, reproduced without Torch.** From the registry's seeds, the review found the float32 divisor behind each receipt's weights hash. Torch's float32 mean for m03 is 2 ulps below numpy's, so all 16,384 weights differ from the disclosure's and one pair merges; in the other five draws the weights are identical. The move in m03's p\* on synthetic gains is 1.6e-8. It matters to no later step.
- **The results report** should count the tied values from each run's `INPUTS.json` and compare those weights hashes with `INPUTS_CHECK.json`, because nothing does that yet.
