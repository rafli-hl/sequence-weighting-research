# Response to the adversarial review of 4 November 2026

**Date:** 4 Nov 2026. **Responds to:** `reports/adversarial-review-20261104-01/REVIEW.md` (`f39c463776bdaecb19c11134e352b0c974e2ce32103157827b969d695379da96`). **Reanalysis records:** `RECOMPUTE.json` (`c872be45145069a18c012856c6ca19cd11265b69df62a68771e60e98f4d02250`) and `RECOMPUTE_MATCHED.json` (`03771d691f05fbeb5b775176f3dcff86ac90316430aec681f9a5d8b6984d1c5a`) in the same folder.

**Status.** The decisions are the owner's, recorded by the assistant, except where section 1 marks a proposal. No experiment, training or verify or check script was run. No sealed file was edited, so sealed labels and readings stay as written in their own records. New wording applies to summaries and later writing, and the data are unchanged.

**The dispositions.**
- **CONCEDE:** the point becomes a stated limitation.
- **REWORD:** the old sentence or label is replaced in summaries by the wording given.
- **REANALYSIS:** post-hoc figures from the saved tables are reported beside the sealed labels.
- **PARTIAL REBUT:** part of the point is accepted, and part is answered.

**What "pre-registered" means here.** Pre-specified and hash-sealed locally within one team, as conceded under §3.5. Only N6 is public, and only after its data existed.

## 1. Disposition of every numbered point

| Point in `REVIEW.md` | Disposition | Decided by |
|---|---|---|
| §2 Claim 1, more training moves the peak smaller | REWORD; its synthetic saturation is conceded | Owner |
| §2 Claim 2, p\* falls with width past 384 | REWORD | Owner |
| §2 Claim 3, matched-gap test M | REWORD | Owner |
| §2 Claim 4, INTERIOR_PEAK and RATE_DEPENDENT | PARTIAL REBUT; its figures come from the reanalysis | Owner |
| §2 Claim 5, the rate and p\* shapes | REWORD; its novelty is conceded | Owner |
| §3.1 Scale and regime | CONCEDE | Owner |
| §3.2 p\* is progress-dependent by construction | REANALYSIS | **Proposal:** the decisions do not name this point |
| §3.3 The estimator's scale | CONCEDE | **Proposal:** the decisions do not name this point |
| §3.4 Fixed-effect factors | CONCEDE | Owner |
| §3.5 Pre-registration is internal | CONCEDE | Owner |
| §3.6 Second attempts on the same seeds | CONCEDE | Owner |
| §3.7 Chain-level forking | CONCEDE | Owner |
| §3.8 Clipping | CONCEDE | Owner |
| §3.9 Width at fixed depth | CONCEDE | Owner |
| §3.10 Near-null labels | REWORD | Owner |
| §3.11 Overclaiming | REWORD | Owner, except the N3 label, which is a **proposal** |
| §3.12 Minor | CONCEDE | **Proposal:** the decisions do not name this point |

## 2. The five claims

### Claim 1: REWORD

**Old claim:** "On synthetic data and on WikiText-2 (overfit regime), more training moves the p\* peak to smaller models, as Jane Street found (pre-registered, fresh data)."

**Old status in `RESEARCH_GOAL.md`:** "Reproduced in direction (pre-registered, 12 fresh synthetic corpora, 28 Oct)".

**New wording:** "On a synthetic task of the project's own design, in which 19 of 59 defined points have their largest fit at the estimator's bound, the width of peak p\* moves smaller from E15 to E40 (−0.796 [−0.982, −0.609], 12/12 fresh corpora). On WikiText-2 at 3e-5, the E32 peak lies below the E8 peak in 4/4 fresh draws (+0.9090 [+0.8641, +0.9539]); this is implied by P1, is not a separate confirmation, and is a bound because E8 is censored at the top rung. This is the same sign as Jane Street's finding (2), not a reproduction: the regime, the scale and the estimator's range differ."

- **Dropped:** "as Jane Street found" and "Reproduced in direction".
- **Conceded, the synthetic saturation:** 19 of 59 defined points (60 nominal) have their largest fit at p = 8, and 10 have two or more widths tied there (`RECOMPUTE.json`: `S_saturation`). The S32 and SD sensitivities agree, so the direction stands on this task. Its cause is not identified, and the direction and window were chosen after seeing them on the exposed ladder.
- **P3 is implied by P1.** L(E8) is the top rung in 4/4 draws, so S = 9.585 − L(E32), and S is above 0 once the E32 peak lies below 768 (`RECOMPUTE.json`: `N4_P1_P3_per_draw`). P1 and P3 count as one confirmation.
- **Regime:** E32 is 28 epochs past the validation minimum, which is at E4 for 384–768.
- **An alternative not excluded:** memorization saturation. Panel p\* peaks at E16 at 768, at E24 at 512, and at E32 at 384 and 256 (`RECOMPUTE_MATCHED.json`: `N4_epoch_of_peak_p_by_width.panel`). The negative-gain share at E32 is 13% at 384 and at 512, and 6% at 768 (`RECOMPUTE.json`: `N4_negative_gain_fraction_E32_by_width`).
- **Only in this regime:** at 3 epochs N5's location moves larger, +0.0237 [+0.0117, +0.0357], as a sealed secondary. So "more training moves the peak smaller" does not hold at few epochs.
- **A detail in the review:** it reads P3 "24" epochs past the minimum. 24 is the length of the E8–E32 window. E8 is 4 epochs past the minimum and E32 is 28.

### Claim 2: REWORD

**Old claim:** "On WikiText-2 late in training, p\* falls with width past 384 (pre-registered, 4 fresh draws)."

**New wording:** "At 3e-5, a rate selected only for 128–384, at the grid's lower edge, and never for 512 or 768, p\* over 384–768 falls with width at E32, 28 epochs past the validation minimum (P1, −0.1886 [−0.2083, −0.1688], 4/4 fresh draws)."

- **Limitation:** this is a fixed-epoch ordering of models at different stages. Training NLL at E32 is 4.10, 3.48 and 2.54 at 384, 512 and 768 (`RECOMPUTE.json`: `N4_by_epoch.E32`).
- **Not resolved:** no reanalysis can remove the rate confound, because no other rate exists at 32 epochs for 512 or 768.
- **Not in dispute:** the size of the effect against the draw-to-draw spread.

### Claim 3: REWORD

**Old claim:** "On WikiText-103 in 3 epochs without overfitting, a memorization-only account of p\* is rejected (matched-gap test M)."

**Old label:** CAPACITY_BEYOND_MEMORIZATION.

**New wording:** "The gap alone does not determine p\*: at matched train–validation gap, p\* at 768 is below p\* at 384 (M, −0.0066 [−0.0076, −0.0055], 10/10 fresh draws). An epoch-only curve with no width effect reads the same sealed label, CAPACITY_BEYOND_MEMORIZATION, in 96–99% of fixture replicates, so this does not show capacity beyond memorization."

- **Rule from now on:** the sealed label is always quoted with the 96–99% epoch-only fixture rate (N5 `PROTOCOL.md` §9: 0.960–0.992).
- **Limitation:** the gap accounts for most of the pooled variance of p\* on N6, R² 0.902 (`RECOMPUTE.json`: `N6_pooled_ols_of_p_on_loss_state.gap.r2`). This is post hoc, and M is small: about a tenth of the p\* it is read against.
- **Not done:** the review's free reanalysis, the M that the epoch-only fixture predicts from the measured curves.

### Claim 4: PARTIAL REBUT

**Old claim:** "At rate 3e-4, p\* at width 512 is above 384 and 768 on fresh draws (INTERIOR_PEAK); at 1e-4 the fall from 512 to 768 reverses by epoch 3 (RATE_DEPENDENT)."

**Final wording, the owner's:** "At 3e-4, p\* at 512 exceeds 768 at fixed updates and under all three progress matchings, 6/6. At 1e-4, the 512–768 order depends on the axis: 768 is higher at fixed updates (−0.0050 [−0.0090, −0.0010], fragile under leave-one-out), and 512 is higher at matched training loss (+0.0132, post hoc). The 384→512 rise is mostly training progress (+0.0027 at matched training loss)."

**The sealed label and its reading.** RATE_DEPENDENT stands as a fixed-budget fact. Its causal reading, "the fall depends on the rate", is withdrawn. INTERIOR_PEAK stands as an ordering after 3,072 updates at 3e-4.

**What is accepted (section 4 has the figures):**
- The arms are at different stages at E3. Panel training NLL at 1e-4 is 4.266 at 512 and 4.115 at 768 (`RECOMPUTE_MATCHED.json`: `N6_panel_train_E3`).
- D4 is fragile. Its interval spans 0 when c02 or c05 is left out.
- The 512–768 fall at 3e-4 survives all three matchings.
- The 384→512 rise shrinks under all three matchings. It is +0.0027 on training loss, +0.0009 on the gap, and +0.0077 on validation NLL. So "mostly" is strongest on the gap and weakest on validation NLL, where the interval still excludes 0.

**What is rebutted.** The review treats matched progress as the correct axis and fixed updates as an artifact. Neither axis is privileged:
- **Fixed updates are Jane Street's own axis.** "We train for 3 epochs and evaluate after each epoch" (blog read, item 5). In N6, 3 epochs is 3,072 updates in every arm.
- **Matching on training loss also removes faster learning, which width genuinely causes.** A contrast with that difference matched away answers a different question. It does not correct the fixed-update one.

**Limits of the rebut.**
- Jane Street's page states epochs and not updates, and does not state a batch size, so equal update counts across its rungs are not established.
- It also tunes hyperparameters on a validation set and fits them across scale for its largest models. N6's rates were not tuned per width on these draws, so the fixed-update axis is shared and the recipe is not.

**The link to finding (1) is removed.**
- **Old sentence, `RESEARCH_GOAL.md`:** "Finding (1) on natural text. There is now a pre-registered ordering of three rungs on fresh draws at 3 epochs, at 3e-4. At E3 it does not hold at 1e-4. It does not establish a rise and fall over a whole ladder or place a peak."
- **New sentence:** "No link to Jane Street's finding (1). The peak confirmation orders three rungs of 10–35 M parameters; it does not test a rise and fall with model size, and Jane Street place their peak orders of magnitude higher."

### Claim 5: REWORD

**Old claim:** "Per-width or common learning-rate choices can create or reverse p\* shapes across model sizes, so cross-size comparisons need the rate controlled."

**New wording, the owner's:** "Comparing widths at equal updates or at equal training loss can reverse the p\* ordering; cross-width p\* comparisons should report both, or tune per width."

- **Novelty conceded.** That the best learning rate shifts with width is the premise of muP (Yang et al., "Tensor Programs V", NeurIPS 2021, as cited by the review and not re-read here), and Jane Street tuned per scale. This is a practical caution, not a contribution.
- **What the evidence is.** The reversal is D4 at fixed updates, pre-registered, against D4 at matched training loss, post hoc. The recommendation is a judgement drawn from that reversal, not a measured result.
- **A residual stays open.** At 768 at 3e-4 the loss-state residual is −0.0048 to −0.0075, and the rate effect on p\* at 768 is +0.0047 [+0.0015, +0.0079] with nearly equal training NLL. This is a few thousandths of p\*, and no mechanism is claimed.
- **A correction to the review.** It says the rate changed progress and not the ordering, and quotes the matched rate effect at 512 as +0.0030 [+0.0019, +0.0040], on training loss only. Matched on the gap it is +0.0061 [+0.0053, +0.0070], and on validation NLL it is −0.0064 [−0.0100, −0.0028]. Its sign depends on the matching variable, which supports "neither axis is privileged" (`RECOMPUTE.json`: `N6_matched_progress.*.rate_effect_512_at_matched_interval`).
- **The nearest case to tuning per width, not in the owner's decisions.** D3 sets each width at its lower-NLL rate of the two on t00. 512 stays above 768 at fixed updates (+0.0111 [+0.0072, +0.0150], with its gap caveat) and under all three matchings, 6/6 each. That selection is from one draw and two of the rates.

## 3. The issues not tied to one claim

**§3.1 Scale and regime: CONCEDE.** Limitation: every model is at or below Jane Street's smallest rung (0.73–34.7 M parameters against "tens of millions to hundreds of billions"). Each draw has 196,608 or 2,097,152 unique tokens, with 0.18–0.61 adaptation token-passes per parameter at 768–384 (`RECOMPUTE.json`: `tokens`). "Capacity" here means the ability to memorize a small draw. Jane Street warn that small-scale behaviour "does not cleanly predict behavior at the largest scales". No result here tests their setting.

**§3.2 p\* is progress-dependent by construction: REANALYSIS (proposal).** Cross-width comparisons at 3 epochs are reported on both axes, using the figures in section 4. Limitation that the reanalysis cannot remove: gains are measured against E0, and no natural-text study has a uniform-weight arm, so the weight-driven part of the gain is never isolated.

**§3.3 The estimator's scale: CONCEDE (proposal).** Limitation: 1000^p is 2.00 at p = 0.1, 2.24 at 0.117, 31.6 at 0.5 and 10^24 at 8 (`RECOMPUTE.json`: `implied_gain_ratio_1000_to_the_p`). So the text contrasts are small in implied gain ratio, and the synthetic values near the bound are a different regime of the estimator. Jane Street print no p\* values on the page, so no comparison of magnitude can be made from the repository.

**§3.4 Fixed-effect factors: CONCEDE.** Limitation: every draw shares the pre-training pool, the validation set, the tokenizer and the recipe, so "6/6" and small p-values measure sampling of articles, not robustness to the pipeline. After identical pre-training, 768 starts about 0.06 nats worse than 384 on validation (`RECOMPUTE.json`: `N6_E0`).

**§3.5 Pre-registration is internal: CONCEDE.** Limitation: protocols were sealed locally and verified by the owner and the assistant. The only public registration is N6's, about 22 minutes after Run C2 ended, with the losses on disk. The independent reviews were by a model-based reviewer. "Pre-registered" means pre-specified within one team.

**§3.6 Second attempts on the same seeds: CONCEDE.** Limitation: N1's Run B and N3 are second attempts on the same draws and seeds, under an owner ruling. That the first attempts' outputs were never opened rests on the owner's word and on supporting records, and cannot be checked independently.

**§3.7 Chain-level forking: CONCEDE.** Limitation: each study's primary came from the previous study's secondaries. Multiplicity is handled within each study and is not adjusted across the chain. N3's MEMORIZATION_PREDICTIONS_MET and N5's three labels have no fresh confirmatory replication. N6 re-measures M (−0.0078 [−0.0102, −0.0053]) and FALL only as non-gating secondaries.

**§3.8 Clipping: CONCEDE.** Limitation: clipping at norm 1 is active on 93–99% of updates on text, so the applied weighting is not w, and the distortion on text is not quantified.

**§3.9 Width at fixed depth: CONCEDE.** Limitation: depth 4 throughout, so "model size" rests on one architectural knob, and 384 to 768 is a factor of 3.4 in parameters.

**§3.10 Near-null labels: REWORD.**
- **Old (chain §4):** N5's FALL listed as CONTINUES_RISING, a prediction not met for Jane Street's pattern.
- **New:** "N5's FALL at E3 is a near-null: CONTINUES_RISING, +0.0040 [+0.0010, +0.0069], 9/10, which did not re-reject on N6's six draws (+0.0014 [−0.0013, +0.0041], 4/6)."
- **Context:** N6 has six draws and did not test FALL as a primary. N5's interval excludes 0 under every leave-one-out, with a lowest limit of +0.0004 (`RECOMPUTE.json`: `N5_FALL_E3`).

**§3.11 Overclaiming: REWORD.** Each row replaces the old wording in summaries. Sealed records stay as written.

| Old sentence or label | New wording |
|---|---|
| `RESEARCH_GOAL.md`: "Reproduced in direction (pre-registered, 12 fresh synthetic corpora, 28 Oct)" | "Same sign as Jane Street's finding (2); not a reproduction" |
| N5 label CAPACITY_BEYOND_MEMORIZATION; chain §7 item 6: "M contradicts the memorization-only account" | "The gap alone does not determine p\*", always with the 96–99% epoch-only fixture rate |
| N6 reading: "so the fall seen at 3e-4 is rate-dependent"; chain §7 item 5: "At E3 that fall depends on the rate" | "At a fixed budget of 3,072 updates at 1e-4, 768 is above 512 at E3 (sealed label RATE_DEPENDENT)." The causal reading is withdrawn |
| N3 label MEMORIZATION_PREDICTIONS_MET alone (**proposal**) | "MEMORIZATION_PREDICTIONS_MET, for the E4–E32 averages only; at E24 and E32 the by-epoch secondaries read TURNS_DOWN" |
| Chain §2 table: N4 P1 and N4 P3 as two confirmations | "N4 P1 is the confirmation; P3 is implied by P1, not a separate confirmation" |
| `RESEARCH_GOAL.md`: "Finding (1) on natural text." | "No link to Jane Street's finding (1)", as under Claim 4 |
| N5 reading: "closer to Jane Street's setting" means 3 epochs and no detected overfitting, nothing more | No change. The review calls it accurate, and it governs every summary |

**§3.12 Minor: CONCEDE (proposal).** Limitation: normality of the t intervals at n = 4 and 6 is untested, and every validation-based choice rests on one shared 65,536-token validation set. Ties and repeated text are measured and disclosed in N5's and N6's reports. The exact two-sided sign test at 6/6 gives 0.031 (`RECOMPUTE.json`: `N6_contrasts_at_E3.D4.sign_test_two_sided_p`).

## 4. The reanalysis

**Every figure in this section is POST HOC.** They are a reanalysis of saved tables, made after the sealed outcomes were seen, and none is a sealed result. No interval is adjusted for that.

**Interpolation.** One arm's p\* is read by linear interpolation along its own path, at the point where it matches the other arm's E3 value (`recompute_matched.py`, `read_at`). The readings are interpolated between E2 and E3, with one exception: D4 matched on validation NLL reads between E1 and E2 in c01 (E1.94) and c04 (E1.99). The review's caveat says E2–E3 for all of them. No figure in the final wording depends on those two readings.

Source: `RECOMPUTE_MATCHED.json`, `N6_contrasts_at_fixed_updates_E3` and `N6_contrasts_at_matched_progress.<contrast>.<train|gap|validation>.interval`.

| Contrast at N6 | Fixed updates, E3 (sealed values) | Matched training NLL | Matched gap | Matched validation NLL |
|---|---|---|---|---|
| D1: 512 − 384, at 3e-4 | +0.0192 [+0.0179, +0.0204], 6/6 | +0.0027 [+0.0005, +0.0049], 5/6 | +0.0009 [−0.0006, +0.0024], 5/6 | +0.0077 [+0.0013, +0.0140], 5/6 |
| D2: 512 − 768, at 3e-4 | +0.0158 [+0.0131, +0.0185], 6/6 | +0.0177 [+0.0147, +0.0206], 6/6 | +0.0132 [+0.0109, +0.0156], 6/6 | +0.0261 [+0.0222, +0.0300], 6/6 |
| D4: 512 − 768, at 1e-4 | −0.0050 [−0.0090, −0.0010], 0/6 | +0.0132 [+0.0106, +0.0158], 6/6 | +0.0101 [+0.0076, +0.0126], 6/6 | +0.0187 [+0.0135, +0.0239], 6/6 |
| D3: 512 at 3e-4 − 768 at 1e-4 | +0.0111 [+0.0072, +0.0150], 6/6 | +0.0123 [+0.0092, +0.0153], 6/6 | +0.0041 [+0.0016, +0.0066], 6/6 | +0.0288 [+0.0222, +0.0355], 6/6 |

The draw counts are draws above 0.

**Other post-hoc figures:**

| Figure | Value | Key in `RECOMPUTE.json` |
|---|---|---|
| D4 at fixed updates, leaving out c02 | [−0.0102, +0.0003] | `N6_contrasts_at_E3.D4.leave_one_out.c02` |
| D4 at fixed updates, leaving out c05 | [−0.0090, +0.0004] | `N6_contrasts_at_E3.D4.leave_one_out.c05` |
| D4 after adjusting for the loss state | +0.0039 to +0.0074, each interval above 0 | `N6_pooled_ols_of_p_on_loss_state.*.residual_contrasts_at_E3.D4` |

**Optional future work, not run and not authorized:** denser readouts (E2.25–E3.5) on the 1e-4 arms to replace the interpolation, about 2–3 h. N6 deleted its model states, so this means retraining and not extending Runs C1 and C2. It would be a new study under its own protocol, and it would not change N6's sealed labels.

## 5. The final claims

**Evidence status.** *Pre-registered* is meant as defined at the top of this file. *Post-hoc reanalysis* means section 4. *Descriptive* means no test was fixed for it.

| Claim | Final wording | Evidence status |
|---|---|---|
| **1** | "On a synthetic task of the project's own design, in which 19 of 59 defined points have their largest fit at the estimator's bound, the width of peak p\* moves smaller from E15 to E40 (−0.796 [−0.982, −0.609], 12/12 fresh corpora). On WikiText-2 at 3e-5, the E32 peak lies below the E8 peak in 4/4 fresh draws (+0.9090 [+0.8641, +0.9539]); this is implied by P1, is not a separate confirmation, and is a bound because E8 is censored at the top rung. This is the same sign as Jane Street's finding (2), not a reproduction: the regime, the scale and the estimator's range differ." | **Pre-registered:** S's slope; N4's P3, implied by P1. **Descriptive:** the saturation count and the comparison of sign with Jane Street |
| **2** | "At 3e-5, a rate selected only for 128–384, at the grid's lower edge, and never for 512 or 768, p\* over 384–768 falls with width at E32, 28 epochs past the validation minimum (P1, −0.1886 [−0.2083, −0.1688], 4/4 fresh draws)." | **Pre-registered:** N4's P1 |
| **3** | "The gap alone does not determine p\*: at matched train–validation gap, p\* at 768 is below p\* at 384 (M, −0.0066 [−0.0076, −0.0055], 10/10 fresh draws). An epoch-only curve with no width effect reads the same sealed label, CAPACITY_BEYOND_MEMORIZATION, in 96–99% of fixture replicates, so this does not show capacity beyond memorization." | **Pre-registered:** N5's M under Holm, and the fixture rate, stated in advance |
| **3, related** | "N5's FALL at E3 is a near-null: CONTINUES_RISING, +0.0040 [+0.0010, +0.0069], 9/10, which did not re-reject on N6's six draws (+0.0014 [−0.0013, +0.0041], 4/6)." | **Pre-registered:** N5's FALL. **Descriptive:** its value on N6, a sealed non-gating secondary |
| **4** | "At 3e-4, p\* at 512 exceeds 768 at fixed updates and under all three progress matchings, 6/6. At 1e-4, the 512–768 order depends on the axis: 768 is higher at fixed updates (−0.0050 [−0.0090, −0.0010], fragile under leave-one-out), and 512 is higher at matched training loss (+0.0132, post hoc). The 384→512 rise is mostly training progress (+0.0027 at matched training loss)." | **Pre-registered:** the fixed-update D2 and D4, with labels INTERIOR_PEAK and RATE_DEPENDENT standing as fixed-budget facts. **Post-hoc reanalysis:** all matched figures and the leave-one-out, interpolated as section 4 states |
| **5** | "Comparing widths at equal updates or at equal training loss can reverse the p\* ordering; cross-width p\* comparisons should report both, or tune per width." | **Post-hoc reanalysis:** the reversal. **Descriptive:** the recommendation is a judgement, and its novelty is conceded |

**The review's top three criticisms (`REVIEW.md` §5):**

| Criticism | How it was handled | What stays open |
|---|---|---|
| **1. The reference problem is not being tested.** | Conceded under §3.1. "As Jane Street found" and "Reproduced in direction" are dropped, the link from N6 to finding (1) is removed, and the project is re-scored at 70/100 on the original scale because alignment with Jane Street was overstated. The data are unchanged. | Nothing here tests Jane Street's setting. Only a shared sign and a shared 3 epochs remain |
| **2. Capacity is never separated from training progress and memorization, and the labels say it is.** | Partly conceded and partly rebutted. M is reworded and always quoted with its fixture rate. RATE_DEPENDENT's causal reading is withdrawn. The matched figures are reported beside the sealed labels. Fixed updates are defended as a legitimate axis, since neither axis is privileged. | No uniform-weight arm exists, the matched figures are interpolated, and memorization saturation is not excluded |
| **3. The learning-rate confound cuts the project's own results.** | Conceded. Claim 2 is restricted to 3e-5, unselected for 512 and 768. Claim 4 is stated by axis. Claim 5 is reworded with its novelty conceded. | No other rate exists at 32 epochs for 512 or 768, and the best rate for 768 at 3 epochs is not located |

The review's fourth, on the limits of pre-registration and the second attempts, is conceded under §3.5 and §3.6.
