# Natural-text one-rate ladder extension: result (revision 02, the final attempt)

**Date:** 31 Oct 2026. **Status:** the run is COMPLETE and the sealed analysis is COMPLETE. This report records the result as planned. Measured results are kept apart from interpretation, and interpretation goes no further than the protocol's own wording (`PROTOCOL.md` sections 7 and 8).

**Records:**

| Record | Path | SHA-256 |
|---|---|---|
| Sealed analysis | `reports/natural-text-onerate-analysis-20261030-02/ANALYSIS.json` | 7b30dcdc… |
| Points | same folder, `POINTS.csv` | 0d5bb913… |
| Fits | same folder, `FITS.csv` | 5b5b8923… |
| Run terminal | `work/runs/natural-text-onerate-20261030-02/TERMINAL.json` | cc5e9c5e… |
| Owner receipt | `work/natural-text-onerate-activation-20261030-02/OWNER_EXIT_RECEIPT.json` | 76b0b371… |
| Approval | OWNER-20261030-ONERATE-02; subject 52ad8783…; builder 99606db0… | 4b7e1f16… (`APPROVAL_RECORD.json`) |

**Check.** Every number below was recomputed by `verify_result.py` (in this folder), which writes `RESULT_CHECK.json`. Its verdict is **PASS: 0 mismatches against ANALYSIS.json**.
- **Points:** each point's three statistics were recomputed from the p\* and gap columns of `POINTS.csv`.
- **Intervals:** the primaries and all 27 by-epoch intervals were recomputed with a t quantile computed independently (2.2621571628).
- **Bindings:** the terminal, receipt, power-log and source hashes were checked.

Attempt 1 was not read.

**Owner decisions:** `reports/natural-text-ladder-owner-decisions-20261031-01/OWNER_DECISIONS.md` (the approval, and the instructions for this report).

## 1. The result at a glance

The two blocks below have equal standing in this report. They answer different questions. **Neither may be quoted without the other.**

### 1a. Pre-registered primaries (epoch-averaged over E4–E32)

| Primary | Label | Mean per draw | 95% interval (df 9) | Draws in that direction |
|---|---|---|---|---|
| Turn-down (OLS slope of p\* on log2 width over 384, 512, 768) | **CONTINUES_RISING** | +0.0220 per doubling | [+0.0176, +0.0264] | 10/10 |
| Dip at one rate (slope over 64, 96, 128) | **NO_DIP_AT_ONE_RATE** | +0.0428 per doubling | [+0.0400, +0.0455] | 10/10 |
| Memorization (Spearman of p\* with the gap across the 8 widths) | **TRACKS_MEMORIZATION** | +0.9643 | [+0.9619, +0.9667] | 10/10 |

- **Joint reading (pre-registered): MEMORIZATION_PREDICTIONS_MET.** The memorization predictions for the turn-down, the dip and memorization were all met, and the Jane Street turn-down prediction was not.
- **Fits:** all 70 nominal points were defined for each primary. No point was flagged by the saturation rule, so S32 and SD were not required. No fit was at a bound and none was undefined.

### 1b. Sealed by-epoch secondaries (pre-registered as secondaries, not as primaries; non-gating)

| Epoch | Turn-down slope, 384–768 (95% interval) | Label at that epoch | Draws < 0 | Panel argmax width | Per-draw argmax |
|---|---|---|---|---|---|
| E1 | +0.0015 (−0.0028, +0.0058) | INCONCLUSIVE | 4 | 512 | 512 ×9, 768 ×1 |
| E2 | +0.0072 (+0.0026, +0.0118) | CONTINUES_RISING | 2 | 512 | 512 ×8, 768 ×2 |
| E4 | +0.0231 (+0.0175, +0.0287) | CONTINUES_RISING | 0 | 768 | 768 ×5, 512 ×5 |
| E6 | +0.0446 (+0.0376, +0.0516) | CONTINUES_RISING | 0 | 768 | 768 ×8, 512 ×2 |
| E8 | +0.0716 (+0.0637, +0.0795) | CONTINUES_RISING | 0 | 768 | 768 ×10 |
| E12 | +0.1115 (+0.1038, +0.1193) | CONTINUES_RISING | 0 | 768 | 768 ×10 |
| E16 | +0.1007 (+0.0952, +0.1061) | CONTINUES_RISING | 0 | 768 | 768 ×10 |
| **E24** | **−0.0225 (−0.0314, −0.0136)** | **TURNS_DOWN** | **10** | **512** | 512 ×10 |
| **E32** | **−0.1748 (−0.1872, −0.1624)** | **TURNS_DOWN** | **10** | **384** | 384 ×10 |

The panel argmax is the argmax of the ten-draw mean p\* curve. Ties would go to the smaller width; none occurred, in the panel or in any of the 90 draw-epoch curves. E1 and E2 are not primary epochs.

**The late-epoch pattern:**
- **E24 and E32:** the turn-down statistic is TURNS_DOWN, at −0.0225 and −0.1748 per doubling, and negative in 10/10 draws at each.
- **The argmax width:**
  - E1–E2: 512;
  - E4–E16: 768, the ladder top. Per draw it is 768 in 10/10 draws at E8–E16, but at E4 the draws split 5/5 between 768 and 512, and at E6 8/2;
  - E24: 512 in 10/10 draws;
  - E32: 384 in 10/10 draws.
- **The curves at the late epochs** (panel means):

  | Width | 64 | 96 | 128 | 192 | 256 | 384 | 512 | 768 |
  |---|---|---|---|---|---|---|---|---|
  | p\* at E24 | 0.1138 | 0.1450 | 0.1689 | 0.2233 | 0.2973 | 0.4587 | **0.4973** | 0.4413 |
  | gap at E24 | 0.226 | 0.339 | 0.448 | 0.667 | 0.920 | 1.553 | 2.160 | 2.871 |
  | p\* at E32 | 0.1227 | 0.1589 | 0.1895 | 0.2698 | 0.3797 | **0.5204** | 0.4906 | 0.3501 |
  | gap at E32 | 0.289 | 0.428 | 0.562 | 0.847 | 1.204 | 2.035 | 2.805 | 3.896 |

  **At E32 the gap keeps rising with width at every step, while p\* falls above 384** (0.5204 → 0.4906 → 0.3501). At E24, p\* still rises from 384 to 512 and falls only at 768, so the negative E24 slope over 384–768 is carried by 768. The gap is validation minus training NLL.
- **Memorization by epoch:** TRACKS_MEMORIZATION at every epoch, but weaker late:
  - 1.0000 at E8–E16;
  - 0.9333 at E24;
  - 0.8333 at E32, in every draw. At E32, p\* ranks 512 and 768 below 384, while the gap ranks them above.

### 1c. How to read 1a and 1b together

- **The averages dilute the late epochs.** The epoch-averaged primaries dilute this late-epoch pattern. The turn-down primary is the equal-weight mean of seven epochs:
  - E4–E16 contribute +0.0502 (E4 +0.0033, E6 +0.0064, E8 +0.0102, E12 +0.0159, E16 +0.0144);
  - E24 and E32 contribute −0.0282 (−0.0032 and −0.0250);
  - the sum is the primary's +0.0220.

  So the primary reads CONTINUES_RISING although the slope is negative in all ten draws at E24 and at E32. Likewise, the memorization primary's 0.964 averages over E32's 0.833.
- **The joint label is accurate only for the averages.** MEMORIZATION_PREDICTIONS_MET is accurate for the epoch-averaged primaries. It must not be summarised alone. At E24 and E32 the by-epoch turn-down secondary reads TURNS_DOWN, which is the label the protocol's prediction table gives to the Jane Street pattern, not the memorization account's CONTINUES_RISING.
- **The joint reading stands as pre-registered.** These are pre-registered secondaries, so the joint reading itself is unchanged. They are 27 by-epoch intervals (9 epochs × 3 statistics) without a multiplicity adjustment. The E24 and E32 turn-down intervals do not touch 0, with every draw on the same side, but the late-epoch pattern is a seen secondary result, not a confirmed one. It motivates the draft confirmation in `reports/natural-text-onerate-confirmation-draft-20261031-01/`.

## 2. What each label means (PROTOCOL.md section 7, quoted)

- **CONTINUES_RISING:** "p\* still rises up to 768, so there is no turn-down within this ladder. This is what memorization predicts." This holds for the E4–E32 average only (section 1c).
- **NO_DIP_AT_ONE_RATE:** "p\* rises from 64 to 128 at one rate. The Run B dip coincides with the change of rate. This reading cannot separate the rate itself from under-training at 64 and 96 (section 8)."
- **TRACKS_MEMORIZATION:** "at fixed epochs, p\* ranks with the train-validation gap across widths. This is an association across widths in one recipe, not a mechanism. On this ladder it also follows from any p\* that mostly rises with width (section 8)." In the power fixtures, the Jane Street turn-down design read TRACKS_MEMORIZATION in 99.75–100% of replicates (section 9). This primary does not discriminate between the two hypotheses; the turn-down primary does.
- **MEMORIZATION_PREDICTIONS_MET:** "Every prediction of the memorization account holds at this scale under this recipe. It is not established as the mechanism: section 8 lists what the same labels would also follow from."

## 3. Other secondaries and descriptives

**Dip by epoch:** NO_DIP_AT_ONE_RATE at every epoch, E1–E32. The slope over 64–128 grows from +0.0173 at E1 to +0.0665 at E32, positive in 10/10 draws at each epoch.

**Rate pairs at 64 and 96** (3e-5 minus Run B's selected rate, per draw; df-9 intervals; 10/10 draws negative for every row):

| Width (Run B rate) | p\*, mean over E4–E32 | Gap at E32 | Validation NLL at E32 |
|---|---|---|---|
| 64 (3e-4) | −0.1159 (−0.1192, −0.1126) | −1.529 (−1.565, −1.492) | −0.631 (−0.664, −0.597) |
| 96 (1e-4) | −0.0570 (−0.0590, −0.0550) | −0.677 (−0.694, −0.660) | −0.211 (−0.225, −0.197) |

At 3e-5, the two smallest widths have lower p\*, a smaller gap and a lower validation NLL at E32 than at Run B's higher rates.

**Losses and clipping** (panel means; NLL in nats per token):

| Width | E0 validation | Lowest validation NLL (epoch) | E32 training | E32 validation | E32 gap | Mean clip fraction | Clipping source |
|---|---|---|---|---|---|---|---|
| 64 | 6.108 | 5.954 (E32, the last readout) | 5.665 | 5.954 | 0.289 | 0.849 | this run |
| 96 | 5.907 | 5.799 (E32, the last readout) | 5.371 | 5.799 | 0.428 | 0.903 | this run |
| 128 | 5.784 | 5.691 (E16) | 5.150 | 5.711 | 0.562 | 0.929 | Run B |
| 192 | 5.635 | 5.543 (E8) | 4.825 | 5.672 | 0.847 | 0.959 | Run B |
| 256 | 5.557 | 5.456 (E6) | 4.567 | 5.771 | 1.204 | 0.975 | Run B |
| 384 | 5.510 | 5.379 (E4) | 4.040 | 6.075 | 2.035 | 0.989 | Run B |
| 512 | 5.523 | 5.366 (E4) | 3.469 | 6.274 | 2.805 | 0.993 | this run |
| 768 | 5.553 | 5.355 (E4) | 2.558 | 6.454 | 3.896 | 0.987 | this run |

**Descriptive context for the late-epoch pattern:**
- **When it occurs.** For 384, 512 and 768 the lowest validation NLL is at E4. The turn-down at E24 and E32 therefore appears 20–28 epochs later, while training NLL keeps falling and validation NLL rises (768: training 2.558 and validation 6.454 at E32).
- **At E4,** the readout at these widths' validation minimum, the turn-down statistic is +0.0231 (+0.0175, +0.0287), positive in 10/10 draws.
- **Status of this context.** No epoch was selected by validation NLL in this protocol; this is description, not a selection rule.
- **Clipping:** most updates are clipped at norm 1 at every width (mean clip fraction 0.85–0.99).

**Fit quality** (`FITS.csv`, the 720 fits at 3e-5):
- p\* ranges from 0.052 to 0.560. No fit is at a bound, and none is undefined.
- Every total gain is positive (smallest 58.0).
- 545 fits include some sequences with negative gains (signed gains are kept). Shares of 5% or more occur only at 256–768 at E24/E32. The largest is 15.0% (384 at E32).

## 4. Operations (measured)

- **Status:**
  - the run was COMPLETE, with all ten draw folders d01–d10;
  - the ladder top was 768 (PEAK_768_WITHIN_LIMIT; 768's start-up peak was within the 2.25 GiB limit);
  - the run is counted as the final attempt.
- **Time:**
  - the activation was built at 00:02:33 on 31 Oct and the last draw ended at 02:43;
  - the worker took 9,041 s (2.51 h) and the owner script 9,655 s (2.68 h);
  - stages took 871.9–890.6 s (mean 882.8 s), against the run's own projection of 912.6 s and a stage cap of 1,261 s.
- **Memory:**
  - the peak sampled GPU memory was 2,388,446,412 B (2.224 GiB), under the 2.5 GiB guard;
  - the worker's peak RSS was 1.93 GiB.
- **Power:**
  - AC throughout, in the Turbo scheme only, with the battery at 80% throughout;
  - 1,885 samples at 5 s, with 0 off AC, 0 scheme-read failures and 0 log-write failures (`POWER_LOG.jsonl` 81b51667…);
  - the GPU and power gate was IDLE at the first check before each of the ten draws.
- **Storage:**
  - 40 per-draw E0 states were hashed and deleted, with 0 deletion errors;
  - the kept run folder holds 163 files (4.08 MB);
  - 128–384 were read from revision 05's Run B through its pinned inventory (220 files, 85.5 MB, verified).

## 5. Disclosures

- **Attempt 1.** Revision 01's run, attempt 1 (`work/runs/natural-text-onerate-20261030-01`), FAILED in d06 on its per-draw work cap after the charger was unplugged and the lid was closed (`reports/natural-text-onerate-failure-20261030-01/FAILURE_REPORT.md`). Under owner ruling 20261030-03 it was never analysed for outcomes, and this report reads nothing from it. Revision 02 changed operations only (a power gate and a power log).
- **Seen data:**
  - the study was designed after revision 05's result and its exploratory note were seen;
  - it extends the seen draws d01–d10 and is not a fresh replication;
  - 128–384 are Run B's already-seen trajectories, so the turn-down compares two unseen rungs with a seen one.
- **Protocol additions:** TRACKS_MEMORIZATION as the third memorization prediction, and the joint-reading table, were protocol additions put to the owner with the approval request.

## 6. Limitations (PROTOCOL.md section 8, and what this result adds)

- **Under-training at 64 and 96:**
  - at 3e-5 both widths still reach their lowest validation NLL at E32, the last readout;
  - NO_DIP_AT_ONE_RATE therefore cannot separate a rate effect from under-training.
- **The memorization primary cannot separate the hypotheses on this ladder.** The gap rises steeply with width at every epoch.
- **Fixed epochs mix capacity with training progress.** One constant-rate trajectory per draw is read at nine epochs. The late-epoch turn-down appears long after each wide model's validation minimum (section 3).
- **Two runs in one ladder:** 128–384 come from Run B. The rungs are paired in inputs, not in floating-point histories.
- **Scale and regime:**
  - small models (0.73–34.7 M parameters, depth 4, a 4,096-token vocabulary);
  - 1,536 sequences × 32 epochs, a memorization regime unlike Jane Street's few epochs on large corpora;
  - no large-model or scaling claim follows.
- **No held-out test loss:** the test split is the pre-training pool.
- **Statistical support of the late-epoch pattern:** it rests on secondaries without a multiplicity adjustment, on ten seen draws of one corpus.
