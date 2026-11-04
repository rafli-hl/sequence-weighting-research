# Evidence chain: the natural-text studies and the synthetic follow-up

**Date:** 31 Oct 2026. **Status:** a summary of saved, verified results. It contains no new measurement or analysis and is not paper text.

**Check.** `check_evidence_chain.py` (in this folder) checks every number below against the saved record it cites and writes `EVIDENCE_CHAIN_CHECK.json`. The verdict is recorded there.

**Which four studies.** The owner's instruction names the ladder, the one-rate extension and the late-turn confirmation, and counts four natural-text studies. The fourth natural-text run in this chain is the 768 memory probe. It is engineering only and has no scientific primary. The September public-text check (Pythia-70M) is outside the chain; it enters only as a disclosure in N4.

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

**The natural-text recipe (N1, N3, N4):**
- N = 1,536 sequences per draw;
- depth-4 decoder Transformers with a 4,096-token vocabulary;
- uniform pre-training, then 32 epochs of weighted adaptation (batch 16, constant rate, clip 1, log-uniform weights 0.01–10);
- signed gains from each width's own E0, and p\* on [0, 8]; undefined fits stay undefined.

## 2. Pre-registered confirmations (the predicted label, on fresh data)

| Study | Primary | Label | Estimate, 95% interval | Units | Replication unit |
|---|---|---|---|---|---|
| S | per-corpus slope of the peak location on log2 epoch (G16, R) | **MOVES_SMALLER** | −0.796 [−0.982, −0.609], 12/12 negative | log2 width per doubling of epochs | 12 fresh synthetic corpora (df 11) |
| N4 P1 | slope of p\* on log2 width over 384–768 at E32 | **TURNS_DOWN** | −0.1886 [−0.2083, −0.1688], 4/4 negative | p\* per doubling of width | 4 fresh draws (df 3) |
| N4 P3 | S = L(E8) − L(E32) | **SHIFTS_TO_SMALLER_WIDTH** | +0.9090 [+0.8641, +0.9539], 4/4 positive | doublings of width | 4 fresh draws (df 3) |

**S, the saturation rule.**
- 19 of 60 points were flagged, so both sensitivities were required. Both read MOVES_SMALLER: S32 −0.817 [−0.990, −0.644], and SD −0.794 [−0.966, −0.622] on 8 corpora.
- **Seen first:** the direction and the window came from the exposed synthetic ladder. Its E15–E30 slope was −1.043 on 5 exposed corpora; −0.922 fresh.

**N4, the sequence.** P1 → P3 → P2 holds the family-wise error over the three primaries at 5%. The verifier passes (PASS), and TERMINAL.json carries no `terminal_outside_ledger` flag.

**N4, readings quoted from the sealed analysis:**
- **Regime:** "The late-epoch pattern is tested at E24 and E32, long after the best validation loss of 384-768, which was at E4 on the seen draws d01-d10: a heavily overfit regime, unlike Jane Street's 3-epoch setting. A confirmation supports the pattern in this regime only."
- **P3's condition:** every E8 location is censored at 768 (censoring category LOWER_BOUND_IF_CURVES_CONTINUE). The sealed reading states: "S is therefore a conservative lower bound on the shift, provided each censored curve continues beyond its ladder end in the direction it leaves it (at E8, still rising at 768; at E32, still falling with width at 256). A peak above 768 cannot be tested on the 4 GiB card."

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

- **N1's joint reading** (NO_DETECTED_SHIFT_CENSORED / CONVEX): "Neither finding is reproduced at this scale under this recipe. For (1) this is inconclusive for shallow peaks (required wording above)."
- **N1's required wording** includes: "The result is therefore inconclusive for shallow peaks." and "It is not evidence that no peak exists."

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

## 6. Exploratory observations (after a result was seen; not pre-registered)

**N1's exploratory note** (29 Oct; descriptive, no test). With rates 64 at 3e-4, 96 at 1e-4, 128–384 at 3e-5:
- p\* is lowest at 128 at all nine readout epochs, where the rate changes;
- over 128–384, p\* rises with width at every epoch;
- the gap is also lowest at 128;
- the Spearman of p\* with the gap is 0.964 over the 54 width-epoch means, but 0.43–1.00 within single epochs.

It motivated N3, whose pre-registered dip primary then read NO_DIP_AT_ONE_RATE.

**Juxtapositions made in this summary** (no test and no inference):
- **N1's null is a censoring outcome.** All 70 of its locations sat at its top rung, 384, so every per-draw slope was 0. With the ladder extended to 768, the panel argmax lies above 384 at E4–E16, in N3 on the same draws and in N4 on fresh draws.
- **The same direction in two settings.** On natural text the peak moves to a smaller width from E8 to E32 (N4, P3); on synthetic data it moves to smaller widths from E15 to E40 (S). The statistics differ: a two-point shift in doublings of width, against a slope per doubling of epochs. The tasks differ, and the natural-text shift lies in an overfit regime. No numerical comparison is made.
- **The turn-down comes after the validation minimum.** The turn-down statistic reads TURNS_DOWN at E24 and E32 in N3, and at E32 in N4: 20 and 28 epochs after the lowest validation NLL (E4 for 384–768). Meanwhile training NLL keeps falling and the gap keeps rising with width. No protocol selected an epoch by validation NLL.

## 7. What the chain supports, and what it does not

**Supported, within its scope:**
1. **Synthetic, finding (2) in direction** (S): pre-registered, on 12 fresh corpora; one task family, depth 4, widths 32–384, one constant rate.
2. **Natural text, fresh draws, overfit regime** (N4): at E32, p\* falls with width over 384–768 (P1). The p\* peak location moves to a smaller width from E8 to E32 (P3; a lower bound only if the E8 curves keep rising beyond 768).
   - **Scope:** one corpus, one recipe at 3e-5, models of 5.3–34.7 M parameters, four draws.
   - **Regime:** the confirmation supports the pattern in this regime only.
3. **Natural text, averaged over E4–E32** (N3's primary on seen draws; N4's descriptive on fresh draws): p\* rises with width over 384–768. The late-epoch turn-down does not show in the average.

**Not supported, or not tested:**
- **Jane Street's setting** (few epochs, large corpora, large models): not tested.
- **A turn-down at E24 on fresh draws:** not detected with four draws (P2). This is not a claim of absence.
- **Finding (1) on natural text** as a pre-registered result: N1 read CONVEX, which is inconclusive for shallow peaks. N4 did not test it; its interior E24 and E32 locations are descriptive.
- **A mechanism:**
  - N3's memorization primary does not discriminate between the accounts;
  - the synthetic shift appears without within-batch instance heterogeneity (S_batch), and its cause is not identified;
  - in every study, fixed epochs mix capacity with training progress.
- **Scaling:** depth 4, at most 34.7 M parameters, one corpus. WikiText-2's training split is exhausted at N = 1,536, so no further fresh draws of this kind exist.
- **The E8 peak above 768:** it cannot be placed on this GPU.

## 8. Disclosures that apply across the chain

- **Failed attempts, never analysed:**
  - N1's Run B attempt 1 FAILED in d02 on its work cap;
  - N3's attempt 1 FAILED in d06 after the charger was unplugged and the lid closed.

  S, N2 and N4 each completed on their first attempt.
- **Seen-data flow:**
  - S's direction came from the exposed synthetic ladder;
  - N3 was designed after N1's exploratory note and extends N1's draws;
  - N4 was designed after N3's result, and tests N3's seen secondaries on fresh draws.
- **Shared across N1, N3 and N4:**
  - the tokenizer, the pre-training pool and the validation set;
  - the tokenizer was trained on every training row, including N4's fresh articles;
  - ten of N4's articles were used by the September text check. The owner chose option (a): keep them and disclose them.
- **Who ran what.** The owner ran every run, seed draw and sealed analysis, each under its own approval. The assistant ran none of them.

## 9. Sources

| ID | Result report | Record the numbers are checked against |
|---|---|---|
| S | `reports/capacity-shift-followup-result-20261028-01/REPORT.md` | `RESULT_SUMMARY.json` (extracted from the frozen ANALYSIS.json) |
| N1 | `reports/natural-text-ladder-analysis-20261029-01/REPORT.md`; `reports/natural-text-ladder-exploratory-20261029-01/EXPLORATORY_NOTE.md` | `sealed-analysis/ANALYSIS.json`; `EXPLORATORY_CHECKS.json` |
| N2 | `reports/natural-text-ladder-probe-result-20261030-01/RESULT.md` | `PROBE_READING.json` |
| N3 | `reports/natural-text-onerate-result-20261031-01/RESULT.md` | `RESULT_CHECK.json` |
| N4 | `reports/natural-text-lateturn-result-20261031-01/RESULT.md` | `RESULT_CHECK.json`; the sealed `ANALYSIS.json` for the readings |
