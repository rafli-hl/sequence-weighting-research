# Few-epoch study: DESCRIPTIVE section

**DESCRIPTIVE ONLY: sealed secondaries, not a primary.** You asked for these comparisons after the outcomes had been seen. None is pre-registered and none is a test. They change no label. The labels stay those of `reports/natural-text-fewepoch-result-20261103-01/RESULT.md`: **M CAPACITY_BEYOND_MEMORIZATION, FALL CONTINUES_RISING, RISE RISES,** with NOT_OVERFIT at every width.

**Where this sits.** `RESULT.md` stays exactly as `make_results_report.py` wrote it, because its layout was frozen and bound by hash before any outcome was opened. This file sits beside it.

**Read sections 1 and 2 together.** Section 1 is what was measured. Section 2 is a reason it may not be about width alone. The reason in section 2 is a hypothesis: nothing in this study measures p\* at another rate.

## 1. At every readout, the largest p\* is at 512

All at 3e-4, the one rate of Runs B1 and B2.

| Readout | Panel p\* at 384 | at 512 | at 768 | Per-draw argmax | 512 − 384, mean (lowest, highest draw) | 512 − 768, mean (lowest, highest draw) |
|---|---|---|---|---|---|---|
| E0.25 | 0.0574 | 0.0639 | 0.0565 | 512 ×10 | +0.0065 (+0.0036, +0.0084) | +0.0074 (+0.0061, +0.0102) |
| E0.5 | 0.0591 | 0.0634 | 0.0566 | 512 ×10 | +0.0043 (+0.0026, +0.0077) | +0.0068 (+0.0043, +0.0084) |
| E1 | 0.0602 | 0.0654 | 0.0590 | 512 ×10 | +0.0051 (+0.0025, +0.0070) | +0.0063 (+0.0041, +0.0086) |
| E2 | 0.0764 | 0.0884 | 0.0791 | 512 ×10 | +0.0120 (+0.0096, +0.0139) | +0.0092 (+0.0037, +0.0133) |
| E3 | 0.0979 | 0.1175 | 0.1038 | 512 ×10 | +0.0196 (+0.0161, +0.0226) | +0.0137 (+0.0060, +0.0193) |

- **The argmax is 512 in all 50 draw-readout points,** and on the panel at all five readouts.
- **p\* at 768 is below p\* at 512 in all 50 points.** The smallest difference is +0.0037.
- **The gap does not fall with it.** At E0.25–E2 the panel gap at 768 is above that at 512 (0.1473 against 0.1253 at E0.25, 0.4162 against 0.4159 at E2). At E3 it is just below (0.5640 against 0.5735).
- **What 10/10 means.** All ten draws share the pre-training pool, the tokenizer, the recipe and the rate, so 10/10 shows consistency across corpus draws, not across those.

### The FALL slope, which does not always stay positive

| Readout | FALL statistic, unadjusted 95% interval (df 9) | Draws above 0 | Panel p\* at 768 − at 384 | Draws with 768 above 384 |
|---|---|---|---|---|
| E0.25 | −0.0017 [−0.0030, −0.0004] | 2 | −0.0009 | 5 |
| E0.5 | −0.0031 [−0.0042, −0.0020] | 0 | −0.0025 | 1 |
| E1 | −0.0018 [−0.0028, −0.0009] | 1 | −0.0012 | 2 |
| E2 | +0.0016 [−0.0004, +0.0035] | 7 | +0.0028 | 9 |
| E3 | +0.0040 [+0.0010, +0.0069] | 9 | +0.0059 | 10 |

- **"Stays positive" does not hold as worded.** The statistic is positive at E3, the primary, in 9 of 10 draws (d08: −0.0013). At E2 its interval spans 0. At E0.25, E0.5 and E1 it is negative, with intervals below 0.
- **"Because 768 sits above 384" holds as arithmetic on the panel.** The OLS weights give FALL = 1.0466 × (p\*768 − p\*384) − 0.1122 × (p\*512 − p\*384), checked against every FALL value in `POINTS.csv`. So the sign of the panel slope follows 768 against 384 at all five readouts: 768 is above 384 at E2 and E3, and below it at E0.25–E1. It is an identity about the statistic, not a cause.
- **It can differ in a single draw.** The signs differ in 8 of 50 points. At E3 that is d08, where 768 is above 384 by +0.0008 and the slope is still negative, because of the second term.
- **So FALL mostly compares 768 with 384.** The weight on 512 is about a ninth of that on 768, so FALL says little about the shape in the table above.

**How this stands against the sealed text.** Sealed reading 4 says "no turn-down within this ladder". That sentence reads the slope. In the curve itself, p\* falls from 512 to 768 in every draw at every readout. The frozen words "an interior p\* peak" require FALL TURNS_DOWN with RISE RISES, and FALL is CONTINUES_RISING, so **this study does not report an interior peak as a result.** Neither can this section; that is what a fresh confirmation would be for.

## 2. The learning-rate caveat: 768 may be running at a rate too high for it

**The caveat.** On t00, 768 had lower validation NLL at 1e-4 than at 3e-4, so the drop at 768 may reflect a rate that is too high for 768. The common rate of 3e-4 was selected on the mean over eight widths, by validation NLL only. It is the lowest at 192–512 and not at 768.

**Measured on t00: one draw, one fit per width and rate, no interval.** In bold, the lower validation NLL of the two rates.

| Width | Validation NLL at E3: 1e-4 | 3e-4 | Training NLL at E3: 1e-4 | 3e-4 | Change in training NLL, 1e-4 to 3e-4 | Gap at E3: 1e-4 | 3e-4 |
|---|---|---|---|---|---|---|---|
| 384 | 4.8054 | **4.7314** | 4.4762 | 4.2625 | −0.2136 | 0.3292 | 0.4689 |
| 512 | 4.7344 | **4.7210** | 4.2922 | 4.1534 | −0.1388 | 0.4422 | 0.5676 |
| 768 | **4.6320** | 4.6677 | 4.0938 | 4.0926 | −0.0013 | 0.5382 | 0.5751 |

Validation NLL at 768 on t00, lower at 1e-4 at all five readouts:

| Readout | E0.25 | E0.5 | E1 | E2 | E3 |
|---|---|---|---|---|---|
| 768 at 1e-4 | 5.1552 | 5.0251 | 4.8614 | 4.7044 | 4.6320 |
| 768 at 3e-4 | 5.2223 | 5.0596 | 4.8869 | 4.7406 | 4.6677 |

**What fits the caveat:**
- **Validation.** At 768 the lower rate is better at every readout, by 0.0357 at E3.
- **Training.** Tripling the rate lowered training NLL at E3 by 0.2136 at 384 and 0.1388 at 512, and by only 0.0013 at 768.
- **Clipping and gradient norm, at 3e-4 over the ten draws.** Both rise with width through 512 (clip fraction 0.902 at 64 to 0.961 at 512; mean norm 1.917 to 2.522), then drop at 768 (0.933; 2.088). On t00 in the third epoch, the step from 512 to 768 takes the mean norm from 2.675 to 2.175 at 3e-4, and only from 3.295 to 3.051 at 1e-4; the clip fraction goes from 0.979 to 0.946, and from 0.989 to 0.988.

**What limits it:**
- **p\* at 1e-4 was never recorded.** Run A wrote no per-sequence adaptation arrays, so nothing measures what the lower rate does to p\*, in either direction.
- **The gap points the other way.** On t00 the gap at 768 is smaller at 1e-4 (0.5382 against 0.5751). If p\* tracked the gap, it would fall at the lower rate, not rise.
- **3e-4 is not failing at 768.** Over the ten draws, 768 has the lowest validation NLL of all widths (4.6672, against 4.7036 at 512) and passes NOT_OVERFIT.
- **Another width difference is present.** After the same pre-training, 768 starts from a higher E0 validation NLL than 384 and 512 (5.5516, against 5.5091 and 5.5158). A change of adaptation rate does not touch that.
- **The grid is coarse.** The rates tested are 3e-5, 1e-4, 3e-4, 1e-3 and 3e-3, so the best rate for 768 is not located.

**No mechanism is claimed in either direction.**

## 3. How your claims were checked

| Claim as you worded it | Verdict | Source |
|---|---|---|
| At every readout E0.25-E3, the per-draw argmax width is 512 in 10/10 draws | **HOLDS** | ANALYSIS.json by_readout.*.per_draw_argmax; recomputed from POINTS.csv |
| p* at 768 is below p* at 512 | **HOLDS** | ANALYSIS.json by_readout.*.curve for the panel; POINTS.csv for each of the 50 draw-readout points |
| E3 panel 0.098, 0.118, 0.104 at 384, 512, 768 | **HOLDS** | ANALYSIS.json by_readout.E3.curve |
| The FALL slope over 384-768 stays positive | **DOES NOT HOLD AS WORDED** | ANALYSIS.json by_readout.*.fall |
| It is positive because 768 sits above 384 | **HOLDS AS ARITHMETIC ON THE PANEL** | ANALYSIS.json curves and fall means; the OLS weights, checked against every FALL value in POINTS.csv |
| On t00, 768 had lower validation NLL at 1e-4 than at 3e-4 | **HOLDS** | LR_SELECTION.json and t00/w768/*/record.json. ANALYSIS.json holds no t00 value, so this one could not be verified from it |

99 checks pass (`DESCRIPTIVE_CHECK.json`). The per-draw differences and the sign counts come from `POINTS.csv`, because `ANALYSIS.json` keeps panel curves and argmaxes, not p\* per draw and width. `POINTS.csv` is itself recomputed from the run files in `RESULT_CHECK.json` (PASS, 0 mismatches), and here its panel means and argmaxes are compared with `ANALYSIS.json` again.
