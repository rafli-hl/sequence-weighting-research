# Sequence weighting: local mechanism pilot

**Latest execution:** `PILOT_NOTES.md` has been executed. See
`results-mechanism-v02/REPORT.md` for 51 synthetic adaptation runs, 10 pretrained
checkpoints, two Pythia/WikiText runs, and the limits of the resulting claims.
Stage 1 uses `mechanism.py`, `mechanism_report.py`, and `text_check.py` with
`PROTOCOL_STAGE1.md` and `TEXT_PROTOCOL.md`. The notebook below remains the
original Stage 0 companion; it does not contain the Stage 1 study.

**Current status:** the local Ubuntu WSL 2 CUDA runtime works, and both paired
GPU feasibility runs completed. See `STATUS.md` and
`results-local-wsl-20260928/RESULTS.md`. Smart App Control remains enabled;
native Windows PyTorch remains blocked. The portable notebook has not been
executed end to end; the equivalent scripts were executed directly under WSL.

This executable pilot investigates the mechanism proposed in Jane Street's
**A study of sequence weighting at scale** (14 September 2026).

- Article: https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/
- Estimator: https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/sequence-weighting-note.pdf

## Scientific scope

The immediate objective is to verify that a causal Transformer, synthetic data,
and the effective sequence-weight exponent can be measured on an RTX 3050 Laptop
GPU with 4 GiB VRAM. Results from this pilot are exploratory. One model size and
one seed cannot establish a rise-then-fall curve or a scaling law.

The eventual paper question is whether learning shared versus idiosyncratic
patterns explains both the non-monotonic exponent and its movement with epochs.
The public article does not release its private benchmark, so this is a
controlled mechanism study, not an exact reproduction.

## Dataset

Each sequence contains a group identifier, a unique three-token example key,
and 12 queries. Query inputs do not repeat within the sequence. Each query has
a mode, an input token, and an answer token:

1. **Shared:** the answer is `(input + 1) mod 16` for every group and example.
2. **Group:** the answer follows a fixed random permutation specific to the group.
3. **Instance:** the answer is random and remains fixed when the training sequence
   is revisited. New test examples have independent random answers.

There are 16 groups and 84 vocabulary tokens. Sequence length is 41 tokens.
Training, validation, and test use disjoint example keys. Groups and their rules
are shared across splits; this explicitly tests within-group generalization,
not generalization to unseen groups. Chance accuracy for an answer conditional
on the 16-token answer vocabulary is 6.25%.

The mixed regime has four queries of each kind. Structured has six shared and
six group queries. Shared has 12 shared queries. Dataset randomness is fixed at
1729 independently of training randomness. Example keys, groups, and query
inputs are paired across regimes; query modes and their answers change as
specified by the experimental intervention.

## Training and estimator

- Causal Transformer trained from random initialization, float32, AdamW.
- Mean next-token cross-entropy at the **answer positions only**, then a scalar
  weight on each sequence. This is conditional sequence learning, not full-text
  next-token pretraining. This is an explicit departure from a general LM study.
- Fixed log-uniform sequence weights on `[0.01, 10]`, normalized once across the
  training corpus to mean 1. We never normalize weights separately per batch.
- Uniform-weight control uses the same initialization, examples, and per-epoch
  shuffle for a given seed. Its exponent is undefined, not zero.
- Three epochs; train and validation measured at each epoch; test measured only
  at the fixed final epoch. No checkpoint selection using test performance.
- Gains are measured relative to the **initial untrained model**, another
  departure from the pretrained model families in Jane Street's study.
- The estimator follows the normalized cumulative-discrepancy definition in
  the note. It uses sorting and cumulative sums instead of an N by N kernel
  matrix. Search range is `[0, 8]`; upper-bound hits are flagged. Nonpositive
  aggregate gain is reported as undefined. Signed individual gains are retained.

## Run on this workspace

From the workspace root in PowerShell:

```powershell
& outputs\sequence-weighting-pilot\run-local.ps1
```

This uses the existing Ubuntu WSL 2 distribution and `work/.venv-wsl`.
It checks CUDA, validates the pilot, runs the random/uniform pair, and builds
the report. The Windows environment `work/.venv` is retained for diagnostics;
its CUDA import is blocked and it is not used by this launcher.

Each output directory must be new to avoid overwriting a run. The program
requires working CUDA and will not silently substitute CPU training. Final
configurations, epoch metrics, per-sequence loss arrays, weights, and model
parameters are retained. Peak allocated and reserved memory describe PyTorch's
allocator, not total system or desktop GPU memory.

## Before a paper-scale experiment

1. Inspect this pilot for correct target alignment, learnability, finite gains,
   estimator behavior, timing, and available memory.
2. Fix a small hyperparameter search using validation, then freeze it. This
   pilot has not optimized regularization to held-out performance as the
   original study did.
3. Predefine a capacity ladder and data-complexity grid. Keep paired seeds and
   weight assignments across capacities. Record exploratory changes separately.
4. Use at least three training seeds, increasing repetitions when variance
   requires it. Sequence bootstraps alone do not capture training variability.
5. Add shared-rule pretraining before weighted adaptation to distinguish
   random-initialization effects from adaptation of a pretrained model.
6. Validate one setting on a public text dataset and an open pretrained model.

If no internal peak appears in the tested capacity range, report that range
honestly. It is neither evidence of a universal monotone law nor a refutation
of the original large-scale observation.
