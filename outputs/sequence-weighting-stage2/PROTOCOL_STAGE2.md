# Stage 2 v0.3: capacity-specific validation selection

Frozen before any v0.3 experimental outcomes are inspected. All training is
local WSL CUDA float32. Historical v0.1/v0.2 files remain evidence, not writable
outputs. The run directory contains a byte-identical protocol and source copy,
SHA256 manifest, UTC timestamps and append-only events.

## Question and estimand

Does the random-weight middle-capacity exponent excess survive independent
capacity-specific selection for validation generalization? Primary contrast is
p_middle - max(p_small,p_large), at each capacity's frozen selected epoch.
Different selected epochs define a policy comparison, not a fixed-time curve.
Matched epochs 1,3,10,30,60 are secondary diagnostics only.

## Fixed design

- Mixed task: 512 adaptation / 256 validation / 512 test examples, 4 shared,
  4 group and 4 instance answer queries. Width/layers: 64/2,128/3,256/4.
- Same v0.2 architecture and signed-gain estimator copied into Stage 2.
  Generate the complete adaptation corpus before filtering test visibility.
  Test full tokens, shifted answer targets and type masks across the toggle.
  Pretraining keys, adaptation, validation and test keys are disjoint.
- Shared pretraining: 2048 train / 256 validation, 4 epochs, LR .0003,
  WD .1, clip 5, batch 32. Reuse one checkpoint within corpus/capacity/model
  seed across all settings and arms. Reset AdamW for every adaptation run.
- Random weights: log-uniform [.01,10], RNG seed 1000+model_seed, normalize
  by corpus mean once. Uniform controls at every capacity. Identical tokens,
  masks, model initial state and epoch batch orders in paired arms. Model and
  weight seeds are deliberately coupled; they are not independent replications.
- Tuning: corpus/model/pretraining-data triples (31415,101,93101) and
  (16180,102,93102). This crosses neither tuning model seeds nor corpora;
  it is two joint tuning replications. Grid LR {3e-5,1e-4,3e-4},
  WD {.1,1,10}, clip {1,disabled}, both arms: 216 runs through 60 epochs.
- Confirmation: corpus/pretraining-data pairs (57721,93201),
  (14142,93202),(17320,93203), each with model/weight seeds 201..205,
  both arms and three capacities: 90 runs. No confirmation seed is used
  in tuning. Corpus seeds are the dataset replication units.
- All runs record epochs 0,1,3,10,30,60, per-sequence and component losses,
  component accuracy, weights, actual epoch orders, gradients/clipping,
  memory and wall time. Confirmation also saves the selected model state.

## Runtime gate, declared before benchmark

One excluded engineering benchmark: corpus/model/pretraining-data seeds
42424/99/93099, largest capacity, LR .0001, WD .1, clip 1, random, 60 epochs.
Only time/memory/success may be inspected before committing to the grid.
If 306 times benchmark end-to-end wall time exceeds four hours, stop before
tuning and freeze a separately versioned budget revision. No performance or
p* from this benchmark may guide design. No change is needed if it passes.

## Selection and failures

For each capacity minimize arithmetic mean unweighted validation NLL over
both arms and both tuning replications, for each grid setting and epoch in
{1,3,10,30,60}. Deterministic ordering: score (full saved precision), earliest
epoch, ascending LR, ascending WD, clip 1 before disabled. No tolerance ties.
Only validation values enter selection; p*, memorization and test never do.
Epoch 0 is a mandatory comparator, not an adaptation candidate. Report if
best adapted validation NLL exceeds epoch 0. This tests the best adapted
choice within a bounded grid; it does not assert a global optimum.

Save and hash selection.json before starting confirmation. Confirmation
evaluates test exactly once, at the frozen selected epoch. Training may then
continue to 60 for the preregistered trajectories, with no further test calls.
Report all failures; any incomplete tuning candidate is ineligible. A capacity
with no complete candidate stops confirmation. Missing/undefined primary
contrasts cannot be silently dropped or called survival. No retries with
different hyperparameters. Infrastructure failures preserve their directories.

## Decision and uncertainty

Strong descriptive survival requires every one of 15 paired primary contrasts
to be defined and positive, and all three corpus-mean contrasts positive.
Disappearance requires all contrasts defined and all three corpus-mean
contrasts nonpositive. Otherwise call the result inconclusive/mixed.
Always display every contrast and each corpus mean. Report between-corpus
mean/SD/range and within-corpus model/weight-seed SD separately. With only
three corpora, do not claim statistical significance or use a sequence bootstrap
as independent replication. Uniform and epoch-0 p* are undefined; signed
negative gains retained, total gain <=1e-10 undefined as in original estimator.
Record objective, p=0 / p=8 boundary flags, total gain and negative fraction.

Primary generalization criterion on random-arm confirmation: in every corpus,
mean selected test NLL strictly decreases with capacity, and mean selected
validation NLL at each capacity is no worse than its epoch-0 reference.
Report the corresponding uniform-arm diagnostics separately. No baseline test
evaluation is scheduled; no claim about test improvement over epoch 0.

## Deliverables and limits

Audit all schedules, tensor pairing/toggle invariance, keys, baseline/source/
data/weight/order hashes, selection reconstruction, test timing and failures.
Save compact reproducibility archive excluding model checkpoint binaries;
full models remain locally with hashes. Provide scientific report and figures,
fresh primary literature check, and update handoff/next-experiment status.
No upload/publication. No new text experiment. Three capacities cannot resolve
an interior-to-interior peak shift. Synthetic evidence is not exact LM replication.
Notebook has not been executed. No novelty or venue guarantee.
