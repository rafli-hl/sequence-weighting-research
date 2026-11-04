# Evidence chain: the natural-text studies and the synthetic follow-up

**Date:** 4 Nov 2026. **Status:** a summary of saved, verified results. It contains no new measurement or analysis and is not paper text; the only new figures are tallies of saved tables, in section 6. **This version adds N5 and N6** to the chain of 31 Oct (`reports/natural-text-evidence-chain-20261031-01`, kept unchanged) and updates the sections they affect.

**Check.** `check_evidence_chain.py` (in this folder) checks every number below against the saved record it cites and writes `EVIDENCE_CHAIN_CHECK.json`. The verdict is recorded there.

**Which four studies.** The owner's instruction names the ladder, the one-rate extension and the late-turn confirmation, and counts four natural-text studies. The fourth natural-text run in this chain is the 768 memory probe. It is engineering only and has no scientific primary. The September public-text check (Pythia-70M) is outside the chain; it enters only as a disclosure in N4.

**N5 and N6** were added on 4 Nov, on the owner's instruction. **N5's draws d01–d10 are not the d01–d10 of N1 and N3:** the names repeat, but the articles and the corpus differ.

## 1. The question and the studies

Jane Street's findings, as the project frames them (RESEARCH_GOAL.md):
- **(1)** p\* rises, then falls, with model size (an interior peak);
- **(2)** more epochs move the p\* peak to smaller models.

| ID | Study (date) | Data | Ladder and rate | Pre-registered primaries | Data status |
|---|---|---|---|---|---|
| **S** | Synthetic capacity-shift follow-up (28 Oct) | 12 synthetic corpora (G16, full weighting R) | depth-4 widths 32–384, one constant rate | slope of the peak location on log2 epoch, E15–E40 | fresh; the direction was first seen in the exposed synthetic ladder |
| **N1** | Natural-text capacity ladder, Run A and Run B, revision 05 (28–29 Oct) | WikiText-2, ten article draws d01–d10 | widths 64–384; rates from Run A, selected by validation NLL: 64 at 3e-4, 96 at 1e-4, 128–384 at 3e-5 | A: peak shift over E4–E32; B: interior peak | fresh at the time |
| **N2** | 768 memory probe (30 Oct) | none | 384, 512, 768 | an engineering verdict only | not applicable |
| **N3** | One-rate extension, revision 02 (30–31 Oct) | the same d01–d10 | widths 64–768, all at 3e-5; 128–384 reused from N1's Run B | turn-down, dip, memorization (E4–E32 averages) | seen draws: an extension |
| **N4** | Late-turn confirmation (31 Oct) | four fresh draws f01–f04 | widths 256–768, all at 3e-5 | P1, P3, P2 in a fixed sequence | fresh; predictions from N3's seen secondaries |
| **N5** | Few-epoch width ladder, Runs A, B1 and B2 (2–3 Nov) | WikiText-103 articles outside WikiText-2: tuning draw t00, then ten draws d01–d10 | widths 64–768, all at 3e-4, selected on t00 by validation NLL | M, FALL and RISE under Holm | fresh; the design follows N3's and N4's seen results |
| **N6** | Peak confirmation, Runs C1 and C2 (3–4 Nov) | six fresh WikiText-103 draws c01–c06, excluding the articles of t00 and N5's draws | 384 at 3e-4; 512 and 768 at 3e-4 and 1e-4 | INTERIOR_PEAK at E3 at 3e-4; a control at 1e-4, read only if it passes | fresh; the hypothesis was formed after seeing N5's d01–d10 |

**The natural-text recipe (N1, N3, N4):**
- N = 1,536 sequences per draw;
- depth-4 decoder Transformers with a 4,096-token vocabulary;
- uniform pre-training, then 32 epochs of weighted adaptation (batch 16, constant rate, clip 1, log-uniform weights 0.01–10);
- signed gains from each width's own E0, and p\* on [0, 8]; undefined fits stay undefined.

**The few-epoch recipe (N5, N6):**
- N = 16,384 sequences per draw;
- depth-4 decoder Transformers with a 4,096-token vocabulary, each width pre-trained uniformly for 4 epochs at 3e-4;
- 3 epochs of weighted adaptation (batch 16, constant rate, clip 1, log-uniform weights 0.01–10), 3,072 updates per arm, read at E0.25, E0.5, E1, E2 and E3;
- signed gains from each width's own E0, and p\* on [0, 8]. N5 and N6 each have 0 undefined fits and 0 fits at a bound.

## 2. Pre-registered confirmations (the predicted label, on fresh data)

| Study | Primary | Label | Estimate, 95% interval | Units | Replication unit |
|---|---|---|---|---|---|
| S | per-corpus slope of the peak location on log2 epoch (G16, R) | **MOVES_SMALLER** | −0.796 [−0.982, −0.609], 12/12 negative | log2 width per doubling of epochs | 12 fresh synthetic corpora (df 11) |
| N4 P1 | slope of p\* on log2 width over 384–768 at E32 | **TURNS_DOWN** | −0.1886 [−0.2083, −0.1688], 4/4 negative | p\* per doubling of width | 4 fresh draws (df 3) |
| N4 P3 | S = L(E8) − L(E32) | **SHIFTS_TO_SMALLER_WIDTH** | +0.9090 [+0.8641, +0.9539], 4/4 positive | doublings of width | 4 fresh draws (df 3) |
| N6 D1 | p\*(512) − p\*(384), both at 3e-4, at E3 | **INTERIOR_PEAK**, with D2 | +0.0192 [+0.0179, +0.0204], 6/6 positive | p\* | 6 fresh draws (df 5) |
| N6 D2 | p\*(512) − p\*(768), both at 3e-4, at E3 | **INTERIOR_PEAK**, with D1 | +0.0158 [+0.0131, +0.0185], 6/6 positive | p\* | 6 fresh draws (df 5) |

**S, the saturation rule.**
- 19 of 60 points were flagged, so both sensitivities were required. Both read MOVES_SMALLER: S32 −0.817 [−0.990, −0.644], and SD −0.794 [−0.966, −0.622] on 8 corpora.
- **Seen first:** the direction and the window came from the exposed synthetic ladder. Its E15–E30 slope was −1.043 on 5 exposed corpora; −0.922 fresh.

**N4, the sequence.** P1 → P3 → P2 holds the family-wise error over the three primaries at 5%. The verifier passes (PASS), and TERMINAL.json carries no `terminal_outside_ledger` flag.

**N4, readings quoted from the sealed analysis:**
- **Regime:** "The late-epoch pattern is tested at E24 and E32, long after the best validation loss of 384-768, which was at E4 on the seen draws d01-d10: a heavily overfit regime, unlike Jane Street's 3-epoch setting. A confirmation supports the pattern in this regime only."
- **P3's condition:** every E8 location is censored at 768 (censoring category LOWER_BOUND_IF_CURVES_CONTINUE). The sealed reading states: "S is therefore a conservative lower bound on the shift, provided each censored curve continues beyond its ladder end in the direction it leaves it (at E8, still rising at 768; at E32, still falling with width at 256). A peak above 768 cannot be tested on the 4 GiB card."

**N6, how the primary was read.**
- **Rule:** both lower limits above 0, so there is no multiplicity adjustment.
- **Manipulation check:** NOT_OVERFIT in all five arms. Mean Δ, validation NLL at E3 minus at E2, runs from −0.0814 to −0.0539, and is below 0 in 6/6 draws in every arm.
- **Saturation:** no draw was flagged, so no refit at bound 32 was needed.
- **Seen first:** the hypothesis was formed after seeing N5's d01–d10, so d01–d10 and t00 cannot confirm it. The idea for the control also came after seeing p\*.
- **The reading, quoted:** "At 3e-4 at E3, p* at 512 is above p* at 384 and at 768 on fresh draws (INTERIOR_PEAK). This is an ordering of three rungs; it does not place the peak between rungs."

**N6, the control.** It was read because the primary passed. RATE_DEPENDENT is one of three readings stated in advance, not a predicted label.

| Contrast | Label | Estimate, 95% interval (df 5) | p, unadjusted |
|---|---|---|---|
| D4 = p\*(512) − p\*(768), both at 1e-4, at E3 | **RATE_DEPENDENT** | −0.0050 [−0.0090, −0.0010], 6/6 negative | 0.0232 |

- **The reading, quoted:** "Peak at 3e-4 only (RATE_DEPENDENT): at 1e-4, 768 is above 512, so the fall seen at 3e-4 is rate-dependent, at the two rates tested."
- **The premise repeats.** The control uses 1e-4 because that was 768's lower validation NLL of the two rates on t00. On the six draws, V at 768, 1e-4 minus 3e-4, is −0.0166 [−0.0321, −0.0011].
- **Its power was an assumption.** No p\* existed at 1e-4 on this recipe before N6. The sd of D4, measured here, is 0.0038.
- **Limit:** 384 was not trained at 1e-4, so at that rate only the fall from 512 to 768 is measured.

**N5, a three-way test on fresh draws.** The labels come from Holm over M, FALL and RISE at family-wise 5%. The intervals are unadjusted, with df 9. All eight widths read NOT_OVERFIT.

| Primary | Statistic | Holm label | Estimate, 95% interval | Holm-adjusted p | Draws | Memorization-only predicts | Jane Street pattern predicts |
|---|---|---|---|---|---|---|---|
| M | mean over 101 gap levels of p\*(768) − p\*(384), along E0.25–E3 | **CAPACITY_BEYOND_MEMORIZATION** | −0.0066 [−0.0076, −0.0055] | 3.51e−07 | 10/10 negative | NOT_DETECTED | not fixed by the pattern |
| FALL | slope of p\* on log2 width over 384, 512, 768 at E3 | **CONTINUES_RISING** | +0.0040 [+0.0010, +0.0069] | 0.0133 | 9/10 positive | CONTINUES_RISING or INCONCLUSIVE | TURNS_DOWN |
| RISE | slope of p\* on log2 width over 64–384 at E3 | **RISES** | +0.0275 [+0.0269, +0.0280] | 5.74e−15 | 10/10 positive | RISES | RISES |

**N5, readings quoted from the sealed analysis:**
- **Regime:** "The few-epoch question is read only where every width a primary uses was still improving its validation loss from E2 to E3 (NOT_OVERFIT). The models are small (0.73-34.7 M parameters, depth 4) and see far fewer tokens per parameter than compute-optimal training; "closer to Jane Street's setting" means 3 epochs and no detected overfitting, nothing more."
- **M:** "M: at matched train-validation gap, p* at 768 is below p* at 384 (CAPACITY_BEYOND_MEMORIZATION). This contradicts the memorization-only account, which predicts NOT_DETECTED. It is not by itself evidence of a capacity effect. At matched gap the larger width has had fewer epochs, so a nonzero M is also what p* gives if it depends on training progress rather than on the gap (stated in advance; in the planning fixtures an epoch-only curve read CAPACITY_BEYOND_MEMORIZATION in 96-99% of replicates)."

## 3. Pre-registered predictions met on seen draws (N3: an extension, not a fresh replication)

| Primary (E4–E32 average) | Label | Estimate, 95% interval (df 9) | Draws |
|---|---|---|---|
| Turn-down, slope over 384–768 | CONTINUES_RISING | +0.0220 [+0.0176, +0.0264] | 10/10 positive |
| Dip at one rate, slope over 64–128 | NO_DIP_AT_ONE_RATE | +0.0428 [+0.0400, +0.0455] | 10/10 positive |
| Memorization, Spearman of p\* with the gap over 8 widths | TRACKS_MEMORIZATION | +0.9643 [+0.9619, +0.9667] | 10/10 positive |

- **Joint reading: MEMORIZATION_PREDICTIONS_MET.** The memorization account's three predictions were met; the Jane Street turn-down prediction was not (section 4).
- **What limits it:**
  - **seen draws:** the same ten draws as N1, and 128–384 are N1's Run B trajectories;
  - **the dip:** NO_DIP_AT_ONE_RATE cannot separate the rate from under-training at 64 and 96;
  - **memorization:** the primary does not discriminate between the two accounts on this ladder;
  - **the averages:** they dilute the late epochs. The turn-down average is the sum of +0.0502 and −0.0282, from E4–E16 and E24–E32 respectively.

## 4. Pre-registered nulls and predictions not met

| Study | Primary | Label | Estimate | Reading (quoted from the sealed protocol) |
|---|---|---|---|---|
| N1 | A: peak shift over E4–E32 | **NO_DETECTED_SHIFT_CENSORED** | slope 0 [0, 0]; 70 of 70 locations at the ladder top, 384 | "No shift is detected with ten draws. This is not a claim of absence, and it departs from the synthetic result." |
| N1 | B: interior peak | **CONVEX** | curvature +0.0611 [+0.0588, +0.0634], 10/10 positive; vertex at width 128.6 | "The mean quadratic bends upward (a dip). An interior peak is not established. This is not evidence against (1): a lopsided true peak can read CONVEX (section 10). The required wording below applies." |
| N3 | Jane Street turn-down prediction for the E4–E32 average | **CONTINUES_RISING** (predicted TURNS_DOWN) | +0.0220 [+0.0176, +0.0264] | Not a null: the average is positive in 10/10 draws. |
| N4 | P2: the P1 statistic at E24 | **INCONCLUSIVE** | −0.0238 [−0.0479, +0.0003], 4/4 negative | "P2 not confirmed: no fall or rise over 384-768 is detected at E24 with four draws. This is not a claim of absence. Power stated in advance (four draws, 95%): 0.678 at the seen effect, 0.157 conservative, 0.247 halved." |
| N5 | Jane Street's turn-down prediction for FALL at E3 | **CONTINUES_RISING** (predicted TURNS_DOWN) | +0.0040 [+0.0010, +0.0069], 9/10 positive | "FALL: at E3, p* rises with width over 384-768 (CONTINUES_RISING): no turn-down within this ladder. This matches the memorization-only prediction, and also Jane Street's pattern with a peak above 768; the study cannot separate the two." |

- **N1's joint reading** (NO_DETECTED_SHIFT_CENSORED / CONVEX): "Neither finding is reproduced at this scale under this recipe. For (1) this is inconclusive for shallow peaks (required wording above)."
- **N1's required wording** includes: "The result is therefore inconclusive for shallow peaks." and "It is not evidence that no peak exists."
- **N5's FALL and N6's primary ask different things.** FALL is a slope, and its weight on 512 is about a ninth of that on 768 (N5's descriptive note). D1 and D2 compare 512 directly with each neighbour.

## 5. Pre-registered secondaries and descriptives (non-gating; no multiplicity adjustment)

**S (synthetic):**
- **S_batch** (which removes the instance coefficient's within-batch weight heterogeneity): −0.851 [−0.934, −0.768], 12/12, MOVES_SMALLER.
- **R − S_batch:** NO_DETECTED_DIFFERENCE +0.055 [−0.128, +0.237]. In that design the shift does not require within-batch instance-weight heterogeneity; its cause is not identified.
- **Panel peak** (descriptive; INTERIOR_PEAK shape labels with no gating rule): 192/4 at E20, 128/4 at E25, 96/4 at E30, 96/4 at E40.

**N3 (seen draws; these set N4's predictions):**
- **The late epochs:**
  - E24: TURNS_DOWN −0.0225 [−0.0314, −0.0136], 10/10;
  - E32: TURNS_DOWN −0.1748 [−0.1872, −0.1624], 10/10.
- **Panel argmax, E1 to E32:** E1 512, E2 512, E4 768, E6 768, E8 768, E12 768, E16 768, E24 512, E32 384.
- **Memorization by epoch:** the Spearman of p\* with the gap falls to 0.833 at E32.
- **Lowest validation NLL:** at E4 for 384–768.

**N4 (fresh draws):**

| Primary | Seen, d01–d10 (df 9) | Fresh, f01–f04 (df 3) |
|---|---|---|
| P1 | −0.1748 [−0.1872, −0.1624] | −0.1886 [−0.2083, −0.1688] |
| P3 | +0.9056 [+0.8871, +0.9242] | +0.9090 [+0.8641, +0.9539] |
| P2 | −0.0225 [−0.0314, −0.0136] | −0.0238 [−0.0479, +0.0003] |

- **Panel argmax, E1 to E32:** E1 512, E2 512, E4 512, E6 768, E8 768, E12 768, E16 768, E24 512, E32 384. It differs from N3 only at E4.
- **E32 locations** are interior in 4/4 draws (mean width 409).
- **The E4–E32 average** reads CONTINUES_RISING +0.0210 [+0.0079, +0.0342], as N3's primary did on the seen draws.
- **Lowest validation NLL:** at E4 for 384–768 and at E6 for 256, as on the seen draws.

**N2 (engineering):**
- Verdict FITS_768: the 768 peak sampled was 2.2225 GiB, 28.2 MiB below the 2.25 GiB limit.
- N4's start-up benchmark measured the same 768 peak, 2.2225 GiB.

**N5 (fresh draws):**
- **Peak shift across readouts** (outside the Holm family): MOVES_LARGER +0.0237 [+0.0117, +0.0357] doublings of width per doubling of readout, 10/10 positive. No location is at a ladder end.
- **Panel argmax:** 512 at all five readouts, and 512 in 10/10 draws at each.
- **FALL by readout, unadjusted:** E0.25 −0.0017 [−0.0030, −0.0004]; E0.5 −0.0031 [−0.0042, −0.0020]; E1 −0.0018 [−0.0028, −0.0009]; E2 +0.0016 [−0.0004, +0.0035]; E3 +0.0040 [+0.0010, +0.0069].

**N6 (fresh draws):**
- **D3 = p\*(512 at 3e-4) − p\*(768 at 1e-4), at E3, the pre-registered secondary:** +0.0111 [+0.0072, +0.0150], 6/6 positive. The caveat, stated in advance and quoted: "D3, a pre-registered secondary: p* at 512 at 3e-4 minus p* at 768 at 1e-4, at E3. It is not a test of the rate account, because it compares two rates. Stated in advance: on t00 the gap at 512 at 3e-4 (0.5676) is above the gap at 768 at 1e-4 (0.5382), so if p* simply tracked the gap, D3 would be above 0 with no turn at 768."
- **The gaps behind that caveat:** the mean gap at E3 is 0.5823 at 512 at 3e-4 and 0.5430 at 768 at 1e-4.
- **Rate effects at E3, 1e-4 minus 3e-4:**

| Width | p\* (R) | Validation NLL (V) | Draws below 0 / above 0, R; V |
|---|---|---|---|
| 512 | −0.0161 [−0.0170, −0.0153] | +0.0181 [+0.0120, +0.0241] | 6/0; 0/6 |
| 768 | +0.0047 [+0.0015, +0.0079] | −0.0166 [−0.0321, −0.0011] | 0/6; 5/1 |

- **By readout, unadjusted:**

| Readout | D1 | D2 | D4 |
|---|---|---|---|
| E0.25 | +0.0059 [+0.0047, +0.0070] | +0.0075 [+0.0062, +0.0089] | +0.0038 [+0.0027, +0.0049] |
| E0.5 | +0.0042 [+0.0037, +0.0048] | +0.0068 [+0.0049, +0.0086] | +0.0044 [+0.0031, +0.0056] |
| E1 | +0.0047 [+0.0040, +0.0055] | +0.0072 [+0.0057, +0.0088] | +0.0043 [+0.0028, +0.0058] |
| E2 | +0.0116 [+0.0107, +0.0125] | +0.0104 [+0.0083, +0.0125] | −0.0001 [−0.0027, +0.0026] |
| E3 | +0.0192 [+0.0179, +0.0204] | +0.0158 [+0.0131, +0.0185] | −0.0050 [−0.0090, −0.0010] |

- **Per-draw argmax at 3e-4:** 512 in 6/6 draws at all five readouts.
- **FALL at E3 at 3e-4:** +0.0014 [−0.0013, +0.0041], 4/6 positive.
- **M at 3e-4:** −0.0078 [−0.0102, −0.0053], 6/6 negative. The sealed note, quoted: "At matched gap the larger width has had fewer epochs, so a nonzero M is also what p* gives if it depends on training progress rather than on the gap."
- **Lowest mean validation NLL:** at E3 in all five arms.

## 6. Exploratory observations (after a result was seen; not pre-registered)

**N1's exploratory note** (29 Oct; descriptive, no test). With rates 64 at 3e-4, 96 at 1e-4, 128–384 at 3e-5:
- p\* is lowest at 128 at all nine readout epochs, where the rate changes;
- over 128–384, p\* rises with width at every epoch;
- the gap is also lowest at 128;
- the Spearman of p\* with the gap is 0.964 over the 54 width-epoch means, but 0.43–1.00 within single epochs.

It motivated N3, whose pre-registered dip primary then read NO_DIP_AT_ONE_RATE.

**N5's descriptive note** (3 Nov; asked for by the owner after the outcomes; no test):
- p\* at 768 is below p\* at 512 in all 50 draw-readout points; the smallest difference is +0.0037;
- on t00, 768 has lower validation NLL at 1e-4 than at 3e-4, by 0.0357 at E3. Nothing then measured p\* at 1e-4.

It motivated N6, whose control then read RATE_DEPENDENT.

**Juxtapositions made in this summary** (no test and no inference):
- **N1's null is a censoring outcome.** All 70 of its locations sat at its top rung, 384, so every per-draw slope was 0. With the ladder extended to 768, the panel argmax lies above 384 at E4–E16, in N3 on the same draws and in N4 on fresh draws.
- **The same direction in two settings.** On natural text the peak moves to a smaller width from E8 to E32 (N4, P3); on synthetic data it moves to smaller widths from E15 to E40 (S). The statistics differ: a two-point shift in doublings of width, against a slope per doubling of epochs. The tasks differ, and the natural-text shift lies in an overfit regime. No numerical comparison is made.
- **The turn-down comes after the validation minimum.** The turn-down statistic reads TURNS_DOWN at E24 and E32 in N3, and at E32 in N4: 20 and 28 epochs after the lowest validation NLL (E4 for 384–768). Meanwhile training NLL keeps falling and the gap keeps rising with width. No protocol selected an epoch by validation NLL.
- **N6 repeats N5's ordering at 3e-4.** Panel p\* at E3 at 384, 512 and 768: 0.0979, 0.1175, 0.1038 in N5, and 0.0979, 0.1171, 0.1013 in N6, on separate draws.
- **The peak shifts in opposite directions in two settings.** Over E8–E32 at 3e-5, N4's location moves to a smaller width (P3). Over E0.25–E3 at 3e-4, N5's location moves to a larger one, as a secondary. The rate, the data per draw, the epochs and the corpus all changed together, so the difference cannot be assigned to any one of them. No numerical comparison is made.
- **In N6, p\* and the gap order 512 and 768 the same way at E3, and not at the earlier readouts.** Draws out of 6 where 512 is above 768, tallied from `POINTS.csv`:

| Readout | At 3e-4: p\* | At 3e-4: gap | At 1e-4: p\* | At 1e-4: gap |
|---|---|---|---|---|
| E0.25 | 6 | 0 | 6 | 0 |
| E0.5 | 6 | 0 | 6 | 0 |
| E1 | 6 | 0 | 6 | 0 |
| E2 | 6 | 2 | 3 | 0 |
| E3 | 6 | 6 | 0 | 0 |

  So at E3 the p\* ordering follows the gap in 6/6 draws at both rates. At E0.25–E1 it runs against the gap in 6/6 draws at both rates. No protocol tests this, and it does not say why p\* orders as it does.

## 7. What the chain supports, and what it does not

**Supported, within its scope:**
1. **Synthetic, finding (2) in direction** (S): pre-registered, on 12 fresh corpora; one task family, depth 4, widths 32–384, one constant rate.
2. **Natural text, fresh draws, overfit regime** (N4): at E32, p\* falls with width over 384–768 (P1). The p\* peak location moves to a smaller width from E8 to E32 (P3; a lower bound only if the E8 curves keep rising beyond 768).
   - **Scope:** one corpus, one recipe at 3e-5, models of 5.3–34.7 M parameters, four draws.
   - **Regime:** the confirmation supports the pattern in this regime only.
3. **Natural text, averaged over E4–E32** (N3's primary on seen draws; N4's descriptive on fresh draws): p\* rises with width over 384–768. The late-epoch turn-down does not show in the average.
4. **Natural text, 3 epochs, fresh draws (N6's primary):** at E3 at 3e-4, p\* at 512 is above p\* at 384 and at 768, with all three arms NOT_OVERFIT. This is an ordering of three rungs, and it does not place a peak.
   - **Scope:** WikiText-103 articles, one recipe, six draws, widths 384–768, at most 34.7 M parameters.
5. **At E3 that fall depends on the rate, at the two rates tested (N6's control):** at 1e-4, 768 is above 512 at E3. At E0.25–E1, 512 is above 768 at 1e-4 too (unadjusted secondary).
6. **Natural text, 3 epochs, fresh draws (N5):** at E3 at 3e-4, p\* rises with width over 64–384 (RISE). M contradicts the memorization-only account, and is not by itself evidence of a capacity effect.

**Not supported, or not tested:**
- **Jane Street's setting:** N5 and N6 share its 3 epochs, with no detected overfitting, and nothing more. They use a constant rate with no horizon-tied schedule, and small models adapted from a short uniform pre-training.
- **A turn-down at E24 on fresh draws:** not detected with four draws (P2). This is not a claim of absence.
- **Finding (1) on natural text, beyond three rungs at one rate:** N6's INTERIOR_PEAK orders 384, 512 and 768 at E3 at 3e-4, and at 1e-4 the fall from 512 to 768 does not hold at E3. No pre-registered test establishes a rise and fall over a whole ladder. N1 read CONVEX, which is inconclusive for shallow peaks; N5's FALL read CONTINUES_RISING; N4 did not test it, and its interior E24 and E32 locations are descriptive.
- **Where a few-epoch peak sits:** N6 has no rung between 512 and 768 and nothing above 768.
- **Other rates:** N6's control speaks to 1e-4 only. The best rate for 768 is not located, and the grid is coarse.
- **A mechanism:**
  - N3's memorization primary does not discriminate between the accounts;
  - the synthetic shift appears without within-batch instance heterogeneity (S_batch), and its cause is not identified;
  - in every study, fixed epochs mix capacity with training progress;
  - N6 shows a rate dependence at E3 and does not say why.
- **Scaling:** depth 4, at most 34.7 M parameters, one corpus family. WikiText-2's training split is exhausted at N = 1,536, so no further fresh draws of that kind exist. 16,451 fresh WikiText-103 articles remain unused after N6.
- **The E8 peak above 768:** it cannot be placed on this GPU.

## 8. Disclosures that apply across the chain

- **Failed attempts, never analysed:**
  - N1's Run B attempt 1 FAILED in d02 on its work cap;
  - N3's attempt 1 FAILED in d06 after the charger was unplugged and the lid closed.

  S, N2, N4, N5 and N6 each completed on their first attempt.
- **Seen-data flow:**
  - S's direction came from the exposed synthetic ladder;
  - N3 was designed after N1's exploratory note and extends N1's draws;
  - N4 was designed after N3's result, and tests N3's seen secondaries on fresh draws;
  - N5 was designed after N3's and N4's results;
  - N6 was designed after N5's outcomes, and its hypothesis and the idea for its control came from them.
- **Shared across N1, N3 and N4:**
  - the tokenizer, the pre-training pool and the validation set;
  - the tokenizer was trained on every training row, including N4's fresh articles;
  - ten of N4's articles were used by the September text check. The owner chose option (a): keep them and disclose them.
- **Shared by N5 and N6 with the earlier studies:** the tokenizer, the pre-training pool and the validation set. Their training text comes from WikiText-103 articles outside WikiText-2.
- **What changed from N1, N3 and N4 to N5 and N6:** the rate, the data per draw, the epochs and the corpus, all together. No difference from those studies can be assigned to any one of them.
- **Repeated text in N5 and N6:**
  - **N5:** 10 identical-text sets across groups; sequences in a shared text, mean 0.74%, largest 1.89% (d04); 64-token runs recurring in another group, mean 1.00%, largest 2.21%.
  - **N6:** the fresh rule leaves 0 identical-text sets across its groups. 64-token runs recurring in another fresh group: mean 0.15%, largest 0.19%. Recurring in the sequences t00–d10 used: mean 0.26%, largest 0.35%.
  - Draws are treated as independent in every interval. These figures do not measure how far that is true.
- **Tied weights in N5 and N6:** the weights are used as drawn, with at most n / 1,024 tied values, which is 16 here. How much the order of ties moves p\* on real gains is not measured.
- **N6's public registration came after the runs and before the analysis** ([pull request 3](https://github.com/rafli-hl/sequence-weighting-research/pull/3), about 22.0 minutes after Run C2 ended). It fixes the analysis in public, not the data collection. The losses already existed, and that they were unopened rests on local records and the owner's word. Section 7f of N6's report predates the later edit and comment, so read it with `NOTE_PUBLIC_REGISTRATION_EDITS.md`.
- **Who ran what.** The owner ran every run, seed draw and sealed analysis, each under its own approval. The assistant ran none of them; it ran the frozen results reports of N5 and N6, which read the sealed outputs and recompute them.

## 9. Sources

| ID | Result report | Record the numbers are checked against |
|---|---|---|
| S | `reports/capacity-shift-followup-result-20261028-01/REPORT.md` | `RESULT_SUMMARY.json` (extracted from the frozen ANALYSIS.json) |
| N1 | `reports/natural-text-ladder-analysis-20261029-01/REPORT.md`; `reports/natural-text-ladder-exploratory-20261029-01/EXPLORATORY_NOTE.md` | `sealed-analysis/ANALYSIS.json`; `EXPLORATORY_CHECKS.json` |
| N2 | `reports/natural-text-ladder-probe-result-20261030-01/RESULT.md` | `PROBE_READING.json` |
| N3 | `reports/natural-text-onerate-result-20261031-01/RESULT.md` | `RESULT_CHECK.json` |
| N4 | `reports/natural-text-lateturn-result-20261031-01/RESULT.md` | `RESULT_CHECK.json`; the sealed `ANALYSIS.json` for the readings |
| N5 | `reports/natural-text-fewepoch-result-20261103-01/RESULT.md`; `reports/natural-text-fewepoch-descriptive-20261103-01/DESCRIPTIVE.md` | the sealed `ANALYSIS.json` and `POINTS.csv` in `reports/natural-text-fewepoch-analysis-20261103-01`; `RESULT_CHECK.json` |
| N6 | `reports/natural-text-peak-result-20261103-01/RESULT.md`; `NOTE_PUBLIC_REGISTRATION_EDITS.md` beside it | the sealed `ANALYSIS.json` and `POINTS.csv` in `reports/natural-text-peak-analysis-20261103-01`; `RESULT_CHECK.json` |
