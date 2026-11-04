# Capacity-shift follow-up: fresh-corpus test of the G16 peak shift under full weighting

Status: **PROPOSED; frozen on 27 October 2026 (revision 02, after the first independent review and the owner decisions on its findings 1–2); no outcome exists; nothing has been drawn or run.** Revision 01 (subject d4ad7811…) is preserved in `reports/capacity-shift-followup-preparation-20261027-01/review-01-subject-d4ad7811-superseded/`; the changes are listed in section 10 and in that directory's `REVIEW.md`. Source in this directory; preparation evidence in `reports/capacity-shift-followup-preparation-20261027-01/`; seed policy in `reports/capacity-shift-followup-seed-registry-20261027-01/SEED_REGISTRY_POLICY.md`. Every rule below is fixed before the seed draw, the benchmark or any training. The design is the owner-approved revision 2 of `reports/capacity-ladder-result-20261027-01/FOLLOWUP_PROPOSAL.md`, with the owner decisions of 27 October 2026 on saturation handling and the 40-epoch horizon (section 10).

## 1. Question and its link to Jane Street's study

Jane Street ("A study of sequence weighting at scale") reported, among other findings, that (2) more epochs move the model size at which p* peaks to smaller models. The completed capacity ladder (`reports/capacity-ladder-result-20261027-01/`) could not answer this with its frozen rule in G16: P2 (E10 → E30) under R was UNDEFINED, because some R fits at E10 had nonpositive total gain.

Question: **in G16, under full weighting R, does the peak location of p* across the eight depth-4 widths move to smaller widths as adaptation continues from E15 to E40?**

Motivation is **exposed data** (`reports/capacity-ladder-result-20261027-01/FOLLOWUP_SIZING.json`): on the five ladder corpora the per-corpus slope of the location on log2(epoch) over E15–E30 was −1.043 (SD 0.347, negative in 5/5) under R and −0.840 (SD 0.206, 5/5) under S_batch. Those epochs and that direction were seen before this protocol was written. This study uses twelve fresh corpora only; none of the ladder's corpora, seeds or results enter any test.

## 2. Design

- **Task and estimator.** The frozen v0128 generator (`vendor/core.py`, `vendor/engine.py`; byte copies of the confirmation's and the ladder's vendor files). Condition G16 only. p* is the unchanged `core.exponent`: the p in [0, 8] minimizing the mean squared gap between the normalized cumulative signed training-gain curve and the cumulative normalized w^p over ascending weight ranks (0.05 grid, 50-step ternary refinement, candidates {0, midpoint, 8}). Undefined if weights are constant or the total gain is ≤ 1e-10.
- **Architectures.** The ladder's eight widths at fixed depth 4: 32, 48, 64, 96, 128, 192, 256, 384 (4 heads; 57,536 to 7,178,496 parameters; `ladder_plan.parameters`). No bridge pairs.
- **Arms.** R = (w, w, w) and S_batch = (w, w, batch-mean w), coefficients ordered shared/group/instance, the batch mean being the actual loss-device FP32 mean; R uses the original `(sequence_loss*w).mean()` graph. No U, H or G1 trajectories (H is used only by the timing benchmark).
- **Weights.** Log-uniform 0.01–10 per training sequence, one corpus-level mean normalization (`engine.weights`), drawn per corpus from its weight seed and shared by every architecture and arm of that corpus (paired).
- **Recipe.** U pretraining unchanged: 2,048 rows, 4 epochs, batch 32, AdamW 3e-4, WD 0.1, clip 5. Adaptation unchanged except the horizon: 512 train / 256 validation rows, batch 32, **40 epochs (640 updates)** instead of 30, AdamW 1e-4, WD 0.1, clip 1, constant learning rate, no scheduler, fresh optimizer from the architecture's own E0 checkpoint, no early stopping. One order schedule (order seed) and one initialization seed per corpus, shared by all trajectories of the corpus.
- **Why updates 1–480 are the ladder recipe.** `engine.orders(seed, n, epochs)` seeds epoch k's permutation with 999 + seed + k only, so epochs 1–30 of the 40-epoch schedule are exactly the 30-epoch schedule. The learning rate is constant, evaluations run under `fork_rng` and the worker refuses any evaluation that changes an RNG state, and the added validation points (E15, E25, E40) and checks (E31–E40) do not touch training. The worker checks the schedule identity on the real tensors at the start of every stage (`orders[:30]` equal to `engine.orders(seed, 512, 30)`) and fails the stage before any training otherwise. GPU nondeterminism is unchanged from the ladder (deterministic algorithms are off), so this is a recipe identity, not a bitwise replay claim.
- **Readouts.** Training-set per-sequence losses at 49 checks: every 4 updates through epoch 3, then every epoch end through E40. Validation at E1, 3, 5, 10, 15, 20, 25, 30, 40 and at the first crossing of each main group-progress landmark (0.10, 0.50, 0.90). Supplementary landmarks 0.02 and 0.05 use the training arrays. **No landmark states are saved.** p* is computed offline by `shift_analysis.py`, never by the worker.
- **Replication.** Twelve fresh corpus draws c01–c12 from a new outcome-blind registry are the only inference units. Epochs, architectures, arms and checks are not replications.
- **Workload.** 96 pretrained models, 192 trajectories, 147,456 updates (24,576 pretraining, 122,880 adaptation), at most 178,176 evaluation batches (`ladder_plan.counts`).

## 3. Model selection

None. All readouts are at fixed epochs under one fixed recipe. No hyperparameter, epoch or model is chosen by p*, by any fit quantity or by test data (no test split is evaluated). A descriptive validation-selected view is reported as a secondary only: per trajectory, the fixed epoch in {0, 1, 3, 5, 10, 15, 20, 25, 30, 40} with the lowest total validation NLL, ties to the earlier epoch.

## 4. Primary outcome

For corpus j and epoch e ∈ {15, 20, 25, 30, 40}:

- **Point.** The eight total-gain fits p_jr(e) at the rungs. The point is **undefined** if any of the eight fits is undefined.
- **Location.** ℓ_j(e) is the frozen ladder location on corpus j's own curve (`ladder_analysis.peak_location`): the argmax rung (ties go to the smaller width); if interior, the vertex in log2(width) of the parabola through the argmax rung and its two neighbours, clamped to that bracket (the middle rung if the parabola is not concave); if the argmax is an end rung, that rung's log2 width (a boundary location, only a bound).
- **Slope.** b_j is the ordinary least-squares slope of ℓ_j(e) on log2(e) over the corpus's defined points, in log2 width per doubling of epochs. A corpus slope is **eligible** only with at least 4 of the 5 points defined, including at least one of E15/E20 and at least one of E30/E40.
- **Interval and label.** The two-sided 95% Student t interval over the twelve corpus slopes, mean ± 2.200985160 × SD/√12 (df 11): MOVES_SMALLER if the upper bound is below −1e-9, MOVES_LARGER if the lower bound is above 1e-9, otherwise NO_DETECTED_SHIFT. The 1e-9 tolerance only stops round-off from deciding a sign when all values are identical, as in the ladder.
- **UNDEFINED.** If any corpus stage is unavailable or any corpus slope is ineligible, the primary is UNDEFINED. There is no replacement corpus, imputation or complete-case primary.
- **_CENSORED.** Appended if any defined primary point (of any corpus) has a boundary location (argmax at 32/4 or 384/4), because that location is only a bound.

On the exposed ladder data, R was fully defined at E15–E30 in all five corpora and E10 was not; this is why E10 is not a primary epoch. E40 has never been observed.

## 5. Saturation at p = 8 (pre-registered; `shift_analysis.slope_test`)

- **S0. Estimator unchanged.** The primary uses the frozen estimator bounded at [0, 8] and every defined point at its fitted value. Nothing is imputed, dropped or widened in the primary.
- **S1. Flag.** A defined corpus-epoch point is flagged if any of its fits within the argmax ± 1 rung bracket is ≥ 7.999. Because a fit ≥ 7.999 anywhere makes the curve maximum ≥ 7.999, the argmax fit is then itself ≥ 7.999; so a point is flagged exactly when any of its eight fits is ≥ 7.999 (checked in the fixtures).
- **S32. Bound-32 sensitivity, required whenever at least one primary point is flagged.** Every flagged point is refitted at all eight rungs on the same saved per-sequence gains with the search bound raised to 32 (`exponent_upper`: the same 0.05 grid from 0, the same refinement, candidates {0, midpoint, 32}; identical to `core.exponent` at bound 8, checked in the fixtures). Its location is recomputed with the frozen rule; unflagged points keep their primary location; the slopes use the same points as the primary and the same df-11 interval rule. No training is repeated. Refitted fits that reach 32 (p ≥ 31.999) are counted and reported; they are not removed.
- **Unresolved refit.** A refitted point is unresolved if any of its refitted fits within its own argmax ± 1 bracket is ≥ 31.999, that is, the S1 rule at the new bound. Bound-8 fits that tie at 8 and refit to a common 32 give the same location at both bounds (for example, the curve 1, 2, 4, 6, 8, 8, 8, 3 locates at 7.2925 either way), so S32 cannot test such points.
- **SD. Drop-flagged sensitivity.** Flagged points are dropped. A corpus keeps a slope only with at least 3 remaining defined points (no early/late requirement); otherwise it is left out of SD only. SD is computable only if at least 3 corpora keep a slope; its interval is the t interval with df = (corpora kept) − 1 (critical values for df 2–11 are in `shift_analysis.T95`). **SD is required if more than 25% of the 60 nominal primary points (that is, more than 15) are flagged, or if any S32 refit is unresolved** (owner decision, 27 October 2026). It is computed and reported descriptively whenever any point is flagged.
- **Decision, applied in this order.**
  1. UNDEFINED if the primary is UNDEFINED (section 4).
  2. SATURATED if any required sensitivity cannot be computed (owner decision, 27 October 2026). S32 can always be computed when the primary is defined, so in practice this means SD is required but fewer than 3 corpora keep at least 3 unflagged points.
  3. SATURATION_SENSITIVE if any required sensitivity has a label (MOVES_SMALLER, MOVES_LARGER, NO_DETECTED_SHIFT) different from the primary label. No directional claim is made.
  4. Otherwise the primary label; the saturation rate (flagged points out of 60) is reported with it.
  5. _CENSORED is appended (section 4) to every label except UNDEFINED and SATURATED.
- **What this means in practice.** With no flagged point, the primary stands alone. With flagged points that all refit below the new bound and at most 15 flagged, the primary must agree with S32. With an unresolved refit or more than 15 flagged points, the primary must agree with both S32 and SD, and SD must be computable.
- **Reporting.** Whenever any point is flagged, the following are reported: flagged points by epoch, fits at the upper bound by epoch and rung, refits at 32 and unresolved refits, the S32 and SD slopes and intervals with their required flags and reasons, and the corpora dropped from SD.
- **Exposed planning rates.** R had saturation-affected corpora at E15/E20/E25/E30 in 2/1/0/1 of 5 ladder corpora (4 of 20 points, 20%); S_batch had none. S32 will therefore very likely be required. In the one documented beyond-bound fit (c01 G16 R 128/4 E20; `docs/research-account-2026-10-27/NOTE_MAPPING_CHECKS.json`) the objective keeps falling to 32, so unresolved refits, and with them a required SD, are also likely.

## 6. Secondaries (non-gating; all reported)

- The same slope test (with the same saturation rule, the 25% threshold scaled to its nominal points) for **S_batch**, and for both arms over the **E15–E30 window** (4 epochs; a corpus needs at least 3 points including one of E15/E20 and one of E25/E30). The E15–E30 window is the exposed sizing window.
- The paired **R − S_batch slope difference** (primary epochs and the E15–E30 window), df-11 t interval.
- The revision-1 **two-point Δℓ = ℓ(E30) − ℓ(E20)** per arm, df-11 t interval, with _CENSORED; UNDEFINED unless both points are defined in all twelve corpora.
- **Per-epoch descriptive curves** at every fixed epoch and arm: the twelve-corpus panel curve (UNDEFINED if any fit is; no defined-only curve), argmax and location, Rise/Fall/End contrasts on the ladder's fixed window {96/4, 128/4, 192/4} with df-11 t intervals, and a descriptive shape label without the ladder's bootstrap gate (rules in `shift_analysis.epoch_curves`). Undefined fits, fits at the upper and lower bounds per rung, and flagged points are counted at every epoch.
- **Losses and memorization.** Per arm, rung and fixed epoch: train and validation NLL (total and instance), the validation − train gaps, and the R − S_batch validation NLL difference with a df-11 t interval.
- **Fit quality.** J(p*) and J(0) per fit, component p* and the signed centered component gain profiles (`SECONDARIES.csv`, the ladder's table).
- **Clipping.** Gradient-norm mean and maximum and the clip fraction per trajectory and epoch (`CLIPPING.csv`), summarized (mean clip fraction, mean and maximum gradient norm) for E1–E30 and E31–E40.
- **Group-progress crossings** per arm, rung and landmark (crossed, missed, undefined because the E0 group loss is not positive, median update).
- **Validation-selected view** (section 3).
- **Boundary locations** by epoch and end (32/4 or 384/4), because whether a boundary makes the slope conservative or anti-conservative depends on where it falls.
- `POINTS.csv`: every corpus-epoch point of every slope test, with the eight fits, location and flag, and for refitted points the eight refit fits, refit location and the unresolved flag.

## 7. Decisions each outcome would lead to (fixed now)

| Primary label (G16, R) | Meaning here | Next step |
|---|---|---|
| MOVES_SMALLER | The peak location moves to smaller widths as training continues from E15 to E40, on twelve fresh corpora: the direction of Jane Street's finding (2), in this synthetic setting and recipe | Report with the saturation rate and the secondaries. No scaling or large-LM claim. |
| MOVES_SMALLER_CENSORED | The same direction, but at least one corpus-epoch location is at a ladder end and is only a bound | Report as directional with censoring; the slope magnitude is not interpretable as a point estimate. |
| MOVES_LARGER(_CENSORED) | The peak moves the opposite way | Report as contrary to (2) in this setting. |
| NO_DETECTED_SHIFT(_CENSORED) | No shift detected with N = 12 | Report the interval; no claim of absence. |
| SATURATION_SENSITIVE(_CENSORED) | The direction depends on how fits at the p = 8 bound are treated | No directional claim; report every sensitivity. A wider estimator range would need its own protocol. |
| SATURATED | A required drop-flagged sensitivity cannot be computed (fewer than 3 corpora keep 3 unflagged points) | No directional claim; report every count. A wider estimator range or a less saturated design would need its own protocol. |
| UNDEFINED | A corpus is unavailable or lacks an eligible slope | No replacement corpora or seeds; more corpora need a new protocol. |

No secondary changes the primary label.

## 8. Operations and failure policy

One owner command runs, in one WSL process:

1. The outcome-blind benchmark of the ladder (`ladder_worker.benchmark`, unchanged code) on a separate benchmark seed: data generation; per architecture 16 untimed + 32 timed pretraining steps, three state writes with readback (median used), the E0 reload with its tensor-hash check, 16 untimed + 32 timed adaptation steps of the costliest objective (H) with the per-forward guard hook, and one train plus one validation evaluation; then full-guard, inventory and epoch-guard costs. No fits, no landmarks.
2. The frozen cap formula (`ladder_worker.stage_cap`): the projected stage time sums every measured per-call cost times its exact per-stage count (2,048 pretraining and 10,240 adaptation updates, the evaluation batches, one state write per architecture and one reload per trajectory, array and record writes, 42 full guards over at most 50 files plus directories and cache entries, 722 epoch/prewrite guards). The stage cap is `ceil(1.5 × projected + 120 s)`, at most 1,425 s; it stops before any scientific stage if the cap would exceed 1,425 s or 12 × (cap + 300) + 900 > 21,600 s.
3. Stages c01–c12 in order, each under its cap and the overall deadline.

Limits:
- 21,600 s overall worker deadline; the owner wrapper waits 21,900 s and never kills;
- per stage 256 MiB / 128 files, total 3 GiB / 1,000 files (estimate 0.97 GiB including 0.16 GiB of benchmark states and a 48 MiB record bound; 50 files per stage);
- 5 GiB free on D: at admission, 2 GiB reserve during work;
- sampled GPU ≤ 2 GiB, worker peak RSS ≤ 4,032 MiB.

Planning projection from the ladder's own measured benchmark for the same eight rungs (`reports/capacity-shift-followup-preparation-20261027-01/BUDGET.json`): 379 s per stage and a cap of 688 s, so 1.27 h in total; the ladder's actual stages took 0.66 of their projection, which gives 0.85 h expected. The worst-case wall bound at that cap is 3.54 h. With every measured cost doubled the cap is 1,211 s and still feasible. The run's own benchmark replaces these numbers.

Guard cadence and failure policy are the ladder's: a cheap tick (deadline, RSS, GPU) per update and per forward; deadline and disk reserve per epoch and before every write with the exact prewrite quota; a real inventory at trajectory and stage boundaries. Fail closed, with no retry, resume, replacement corpus or seed redraw. A failed stage keeps its directory and makes that corpus UNAVAILABLE, so the primary is UNDEFINED. The wrapper never kills the WSL process; native exit does not prove Linux cleanup.

## 9. Limitations stated in advance

- **Exposed motivation.** The direction and the epoch window come from the completed ladder; this is a fresh-corpus confirmation of a pattern already seen, not an independent discovery.
- **Extended horizon.** E31–E40 go beyond the 30-epoch recipe of every earlier result; E40 has never been observed.
- **Saturation.** Fits at the p = 8 bound are common in G16 R. The primary keeps them at 8; the S32 sensitivity widens the search to 32, where fits can again reach the bound when the objective keeps falling (as in the beyond-bound example of `docs/research-account-2026-10-27/NOTE_MAPPING_CHECKS.json`). Such refits make SD required, and SD then removes the saturated points altogether.
- **One trajectory read at several epochs.** E15–E40 are checkpoints of the same constant-learning-rate trajectory, not separate runs of those lengths. Runs in Jane Street's setting usually tie the learning-rate schedule to the training horizon, so "more epochs" here is not the same intervention.
- **Progress confound.** Larger models learn faster, so fixed epochs mix capacity with training progress; no matched-progress primary is included.
- **Location resolution.** Eight rungs and a three-point parabola; boundary locations are bounds (_CENSORED).
- **Scope.** One synthetic task family, fixed depth 4, one order schedule and one initialization seed per corpus, twelve corpora. No claim about Jane Street's large models, natural text or a scaling law follows.

## 10. Changes from the ladder protocol and from proposal revision 2

From `work/capacity-ladder-source-20261026-01`: G16 only; arms R and S_batch; no bridge, U or H trajectories; 40 adaptation epochs with the in-stage schedule-identity check; validation added at E15, E25 and E40; no landmark states; twelve corpora from a new registry (256 candidates; the ladder registry and its exclusions added to the exclusion set); limits resized (section 8); a new analysis (`shift_analysis.py`) that reuses the sealed `ladder_analysis.py` (byte copy) for loading, gains, fits and locations. `framework_setup.py`, `ORIGINAL_ENVIRONMENT.json`, `ladder_analysis.py` and `vendor/` are byte copies.

From proposal revision 2, by owner decision of 27 October 2026: the 25% gate no longer makes the primary SATURATED; instead the primary keeps every point, the bound-32 sensitivity S32 is required whenever any point is flagged, and the drop-flagged sensitivity SD is required above 25%; any disagreement gives SATURATION_SENSITIVE. The E15–E30 slope was added as a secondary. The SD minimum of 3 corpora (df ≥ 2) is a detail fixed in this protocol.

Revision 02 (27 October 2026, before any draw), after the first independent review (`reports/capacity-shift-followup-preparation-20261027-01/REVIEW.md`):
- by owner decision on review finding 1, an unresolved S32 refit (a refit fit ≥ 31.999 within the refit's argmax ± 1 bracket) also makes SD required;
- by owner decision on review finding 2, SATURATED applies if any required sensitivity cannot be computed (previously only if none could be);
- SD is computed descriptively whenever any point is flagged (finding 3);
- an undefined refit raises an error instead of returning no location (finding 4; unreachable);
- POINTS.csv carries the refit fits, the clipping summary the gradient-norm maximum, and the crossings count UNDEFINED_E0 separately (finding 5);
- boundary locations are reported by epoch and end (finding 6);
- the scope sentence on one trajectory read at several epochs was added (finding 7).
