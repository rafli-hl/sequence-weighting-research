# Late-turn confirmation: result

**Date:** 31 Oct 2026. **Status:** the run is COMPLETE and the sealed analysis is COMPLETE. This was the study's first and only attempt. This report records the result as planned. Measured results are kept apart from interpretation, and interpretation goes no further than the protocol's own wording (`PROTOCOL.md` sections 6–8, sealed in `work/natural-text-lateturn-activation-20261031-01/`).

**Records:**

| Record | Path | SHA-256 |
|---|---|---|
| Sealed analysis | `reports/natural-text-lateturn-analysis-20261031-01/ANALYSIS.json` | a20ab6c9… |
| Points | same folder, `POINTS.csv` | 263e22fd… |
| Fits | same folder, `FITS.csv` | 704d0168… |
| Run terminal | `work/runs/natural-text-lateturn-20261031-01/TERMINAL.json` | d61250a2… |
| Owner receipt | `work/natural-text-lateturn-activation-20261031-01/OWNER_EXIT_RECEIPT.json` | 48e38a09… |
| Approval | OWNER-20261031-LATETURN-01; subject 9286f324…; builder 3d2efd0e… | c07acd01… (`APPROVAL_RECORD.json`) |
| Owner decisions | `reports/natural-text-ladder-owner-decisions-20261031-04/OWNER_DECISIONS.md` | the approval and the instructions for this report |

**Check.** `verify_result.py` (in this folder) recomputes every number below and writes `RESULT_CHECK.json`. Its verdict is **PASS: 0 mismatches against ANALYSIS.json**.
- **Points:** each point's turn statistic and peak location were recomputed from the p\* columns of `POINTS.csv`, with formulas written in the verifier, not imported from the sealed code.
- **Intervals:** the three primaries and all nine by-epoch intervals were recomputed with a t quantile computed independently (df 3: 3.1824463053).
- **Bindings:** the terminal, receipt, approval, builder, source, fresh-check and power-log hashes were checked.
- **Readings:** the P3 reading was checked to carry the recomputed censoring counts and the matching ending.

## 1. The terminal_outside_ledger flag (the accepted limitation)

**Absent.** `TERMINAL.json` has no `terminal_outside_ledger` key, so it was written through the output ledger, not by the last-resort path. Three further records agree:
- its ledger inventory is present (75 files, 1,711,187 bytes);
- `WORKER_STDERR.log` is empty (0 bytes), so no terminal-publication failure was written;
- the owner receipt and `ANALYSIS.json` both bind this TERMINAL.json (d61250a2…).

The limitation the owner accepted therefore did not bind in this run.

## 2. Pre-registered primaries (fixed sequence P1 → P3 → P2, each at two-sided 95%)

| Primary | Statistic per draw | Label | Mean | 95% interval (df 3) | Draws in that direction | Predicted | Confirmed |
|---|---|---|---|---|---|---|---|
| **P1** | OLS slope of p\* on log2 width over 384, 512, 768 at E32 | **TURNS_DOWN** | −0.1886 per doubling | [−0.2083, −0.1688] | 4/4 negative | TURNS_DOWN | **yes** |
| **P3** | S = L(E8) − L(E32), in doublings | **SHIFTS_TO_SMALLER_WIDTH** | +0.9090 | [+0.8641, +0.9539] | 4/4 positive | SHIFTS_TO_SMALLER_WIDTH | **yes** |
| **P2** | The P1 statistic at E24 | **INCONCLUSIVE** | −0.0238 per doubling | [−0.0479, +0.0003] | 4/4 negative | TURNS_DOWN | **no** |

- **The sequence.** P1 and P3 gave their predicted labels in order, so P2 was read as a confirmation candidate; it gave INCONCLUSIVE and is not confirmed.
- **Fits:** all 144 fits are defined and none is at a bound. No draw was flagged by the saturation rule (the largest p\* any primary uses is 0.555, against the 7.999 flag), so S32 was not required. No interval is degenerate.

**Per-draw values:**

| Draw | P1 (E32 slope) | P2 (E24 slope) | L(E8): rung, kind | L(E32): rung, kind, log2 (width) | P3 (S) |
|---|---|---|---|---|---|
| f01 | −0.1800 | −0.0056 | 768, boundary | 384, interior, 8.7107 (419.0) | +0.8743 |
| f02 | −0.1807 | −0.0211 | 768, boundary | 384, interior, 8.6458 (400.5) | +0.9392 |
| f03 | −0.2066 | −0.0424 | 768, boundary | 384, interior, 8.6622 (405.1) | +0.9228 |
| f04 | −0.1870 | −0.0261 | 768, boundary | 384, interior, 8.6853 (411.7) | +0.8997 |

L(E8) is log2 768 = 9.5850 in every draw.

### 2a. The sealed readings (ANALYSIS.json `readings`, quoted exactly)

1. **Overfit regime:** "The late-epoch pattern is tested at E24 and E32, long after the best validation loss of 384-768, which was at E4 on the seen draws d01-d10: a heavily overfit regime, unlike Jane Street's 3-epoch setting. A confirmation supports the pattern in this regime only."
2. **P1:** "P1 confirmed: at E32, p* falls with width over 384-768 on the four fresh draws."
3. **P3, with the conditional lower bound:** "P3 confirmed: the peak location moves to a smaller width from E8 to E32. A peak at a ladder end is recorded at that rung. At E8 the peak was at the top rung (768) in 4 and at the bottom rung (256) in 0 of 4 draws; at E32, at the top rung in 0 and at the bottom rung in 0. S is therefore a conservative lower bound on the shift, provided each censored curve continues beyond its ladder end in the direction it leaves it (at E8, still rising at 768; at E32, still falling with width at 256). A peak above 768 cannot be tested on the 4 GiB card."
4. **P2:** "P2 not confirmed: no fall or rise over 384-768 is detected at E24 with four draws. This is not a claim of absence. Power stated in advance (four draws, 95%): 0.678 at the seen effect, 0.157 conservative, 0.247 halved."
5. **Text-check disclosure:** "10 training articles in f01-f04 were used in September by the public-text check (Pythia-70M fine-tuning, work/runs/text-check-v02). The confirmation's models are trained from scratch with the study's own tokenizer and never see that check's model or outputs."

### 2b. What the P3 condition means here

- **E8 is censored in all four draws.** Every E8 location is the top rung, 768. That shows only that p\*(768) exceeds p\*(512) at E8.
- **The bound holds only if the E8 curves keep rising beyond 768.** Then the true E8 peak lies above 768 and the true shift exceeds S. This cannot be checked: no width above 768 fits on the card.
- **No E32 location is censored.** All four are interior, at the 384 rung.
- **No case that would void the bound occurred.** There is no E8 peak at 256 and no E32 peak at 768 (censoring category `LOWER_BOUND_IF_CURVES_CONTINUE`).

### 2c. What P2 does and does not show

- **The interval contains 0.** It is [−0.0479, +0.0003], so the label is INCONCLUSIVE.
- **All four draw values are negative.** The protocol's rule gives no further reading from the signs.
- **Low power was stated in advance.** Under PROTOCOL.md section 10, an INCONCLUSIVE P2 "is weak evidence either way".

## 3. The fresh draws beside the seen draws (descriptive)

The seen values on d01–d10 motivated the predictions. They are not part of the confirmation.

| Primary | Seen d01–d10: mean, 95% interval (df 9), signs | Fresh f01–f04: mean, 95% interval (df 3), signs |
|---|---|---|
| P1 | −0.1748 [−0.1872, −0.1624], 10/10 negative | −0.1886 [−0.2083, −0.1688], 4/4 negative |
| P3 | +0.9056 [+0.8871, +0.9242], 10/10 positive | +0.9090 [+0.8641, +0.9539], 4/4 positive |
| P2 | −0.0225 [−0.0314, −0.0136], 10/10 negative | −0.0238 [−0.0479, +0.0003], 4/4 negative |

- **Sources of the seen values:** the planning record (`CONFIRMATION_PLANNING.json`). The verifier also recomputes them from the one-rate study's `POINTS.csv`, with P3 on the confirmation's ladder (256–768).
- **Why the fresh P2 interval is wider:**
  - the fresh interval uses 4 draws with t = 3.182, where the seen one used 10 draws with t = 2.262;
  - the fresh sd is 0.0151, against 0.0124 seen.

## 4. Secondaries (pre-registered as secondaries; non-gating)

### 4a. By epoch

| Epoch | Turn slope, 384–768 (95% interval, df 3) | Label | Draws < 0 | Panel argmax | Per-draw argmax | Mean L, log2 (width) | Seen panel argmax, 256–768 |
|---|---|---|---|---|---|---|---|
| E1 | −0.0016 (−0.0096, +0.0063) | INCONCLUSIVE | 1 | 512 | 512 ×4 | 9.085 (543) | 512 |
| E2 | +0.0043 (−0.0049, +0.0135) | INCONCLUSIVE | 1 | 512 | 512 ×4 | 9.161 (572) | 512 |
| E4 | +0.0210 (+0.0095, +0.0326) | CONTINUES_RISING | 0 | 512 | 768 ×2, 512 ×2 | 9.400 (675) | 768 |
| E6 | +0.0438 (+0.0285, +0.0592) | CONTINUES_RISING | 0 | 768 | 768 ×3, 512 ×1 | 9.495 (722) | 768 |
| E8 | +0.0723 (+0.0534, +0.0911) | CONTINUES_RISING | 0 | 768 | 768 ×4 | 9.585 (768) | 768 |
| E12 | +0.1176 (+0.0956, +0.1395) | CONTINUES_RISING | 0 | 768 | 768 ×4 | 9.585 (768) | 768 |
| E16 | +0.1049 (+0.0855, +0.1243) | CONTINUES_RISING | 0 | 768 | 768 ×3, 512 ×1 | 9.511 (730) | 768 |
| **E24** | **−0.0238 (−0.0479, +0.0003)** | **INCONCLUSIVE** | **4** | **512** | 512 ×4 | 9.047 (529) | 512 |
| **E32** | **−0.1886 (−0.2083, −0.1688)** | **TURNS_DOWN** | **4** | **384** | 384 ×4 | 8.676 (409) | 384 |

**Notes on the table:**
- **Mean L:** the mean of the four per-draw locations in log2 width; the width shown is 2 to that power.
- **Ties:** none occurred.
- **The seen argmax:** recomputed on 256–768 from the one-rate study's ten draws.
- **The one difference from the seen draws is at E4.** The fresh panel argmax is 512 (p\* 0.1825 against 0.1802 at 768), with the draws split 2/2; the seen panel argmax was 768, with the draws split 5/5.
- **E24 and E32 locations are interior in 4/4 draws.** At E32, p\* at 256 (0.3764) is below p\* at 384 (0.5310). No interior-peak test was pre-registered in this study.

### 4b. The curves at E8, E24 and E32 (four-draw panel means)

| Width | 256 | 384 | 512 | 768 |
|---|---|---|---|---|
| p\* at E8 | 0.1631 | 0.2114 | 0.2651 | **0.2862** |
| gap at E8 | 0.339 | 0.534 | 0.756 | 0.973 |
| p\* at E24 | 0.2945 | 0.4623 | **0.5105** | 0.4447 |
| gap at E24 | 0.873 | 1.497 | 2.162 | 2.864 |
| p\* at E32 | 0.3764 | **0.5310** | 0.4969 | 0.3472 |
| gap at E32 | 1.151 | 1.988 | 2.814 | 3.911 |

- **The gap** (validation minus training NLL) rises with width at every step at every readout epoch.
- **At E32,** p\* falls above 384 while the gap keeps rising.
- **At E24,** p\* still rises from 384 to 512 (+0.0482) and falls from 512 to 768 (−0.0658).

### 4c. The one-rate study's averaged statistic, for comparison only

The mean over E4–E32 of the 384–768 slope reads **CONTINUES_RISING**: +0.0210 [+0.0079, +0.0342], 4/4 positive. On the seen draws it was +0.0220 [+0.0176, +0.0264], 10/10. The sealed note: "Descriptive: the seen study's epoch-averaged turn-down on the fresh draws; not a primary."

### 4d. Losses and the overfit-regime check

Panel means; NLL in nats per token.

| Width | Parameters | E0 validation | Lowest validation NLL (epoch) | Seen lowest at epoch | E32 training | E32 validation | E32 gap | Mean clip fraction |
|---|---|---|---|---|---|---|---|---|
| 256 | 5.29 M | 5.562 | 5.458 (E6) | E6 | 4.616 | 5.767 | 1.151 | 0.971 |
| 384 | 10.29 M | 5.509 | 5.378 (E4) | E4 | 4.097 | 6.084 | 1.988 | 0.988 |
| 512 | 16.87 M | 5.521 | 5.359 (E4) | E4 | 3.480 | 6.294 | 2.814 | 0.993 |
| 768 | 34.74 M | 5.530 | 5.327 (E4) | E4 | 2.543 | 6.454 | 3.911 | 0.984 |

- **The regime statement holds on the fresh draws.** For 384–768, the lowest validation NLL is at E4, as on the seen draws. P2 and P1 are read 20 and 28 epochs later.
- **No epoch was selected by validation NLL** in this protocol. This is a check of the stated regime, not a selection rule.
- **Clipping:** most updates are clipped at norm 1 at every width.

### 4e. Fit quality (`FITS.csv`, 144 fits at 3e-5)

- p\* ranges from 0.078 to 0.555. No fit is at a bound, and none is undefined.
- Every total gain is positive (smallest 246.6).
- 128 fits include some sequences with negative gains (signed gains are kept). Shares of 5% or more occur in 22 fits, all at 384–768 at E24 or E32. The largest is 13.3% (384 at E32, f02).

## 5. Operations (measured)

- **Status:**
  - COMPLETE, with all four draw folders f01–f04;
  - start-up GO (ALL_WIDTHS_WITHIN_LIMIT);
  - counted as the study's only attempt, with no retry.
- **Time:**
  - the activation was built at 14:24:05 (+07:00);
  - the power log runs from 14:24:24 to 15:45:55;
  - the worker took 4,543 s (1.26 h) and the owner script 4,911 s (1.36 h);
  - stages took 1,086.0–1,114.9 s (mean 1,095.0 s), against the run's own projection of 1,113.6 s and a stage cap of 1,512 s.
- **Memory:**
  - the start-up peaks sampled were 1.346, 1.482, 1.635 and 2.2225 GiB for 256, 384, 512 and 768. 768 was 28.2 MiB below the 2.25 GiB start-up limit;
  - the run's peak sampled GPU memory was 2.2225 GiB, under the 2.5 GiB guard;
  - the worker's peak RSS was 1.95 GiB.
- **Power:**
  - AC throughout, in the Turbo scheme only, with the battery at 80% throughout;
  - 957 samples at 5 s, with 0 off AC, 0 scheme-read failures and 0 log-write failures (`POWER_LOG.jsonl` a44c48ba…);
  - the Windows GPU and power gate was IDLE at the pre-start check and at the first check before each of the four draws.
- **Storage:**
  - 12 benchmark states (806,539,824 bytes) and 16 per-width states (268,846,608 bytes per draw) were hashed and deleted, with 0 deletion errors;
  - the run folder's inventory at the terminal was 75 files (1,711,187 bytes).
- **Counts:** 32 models, 16 pre-trained states, 57,344 updates.

## 6. Disclosures

- **Seen design.** The study was designed after the one-rate study's result was seen. Its predictions come from that study's sealed by-epoch secondaries on d01–d10 (`reports/natural-text-onerate-result-20261031-01/RESULT.md`).
- **The September text check.** The owner chose option (a): the frozen partition is kept and the 10 articles are disclosed (reading 5 above; owner decisions 20261031-04).
- **Shared with the seen draws:**
  - the pre-training pool, the validation set and the tokenizer;
  - the tokenizer was trained on every training row, including the fresh articles, before any draw.
- **One analysis.** The sealed analysis was run once, by the owner. The verifier reads its outputs and does not re-run it.

## 7. Limitations (PROTOCOL.md section 11, and what this result adds)

- **Sample:** four draws (df 3), from one corpus. WikiText-2's training split is exhausted at this N, so no further fresh draw of this kind exists.
- **Regime:**
  - a heavily overfit regime; the fresh validation minima at E4 for 384–768 confirm it on new data;
  - the confirmations support the pattern in this regime only;
  - fixed epochs mix capacity with training progress.
- **Censoring:** S is a lower bound only if the E8 curves keep rising beyond 768, which cannot be tested here.
- **P2 is underpowered.** Its INCONCLUSIVE label is weak evidence either way.
- **Multiplicity:** the fixed sequence controls the family-wise error over the three primaries at 5%. The by-epoch secondaries have no multiplicity adjustment.
- **Scale:**
  - small models (5.3–34.7 M parameters, depth 4, a 4,096-token vocabulary);
  - 1,536 sequences × 32 epochs;
  - no large-model or scaling claim follows.
- **No held-out test loss:** the test split is the pre-training pool.
- **No mechanism.** Each confirmation is an association across widths, in one recipe, on one corpus, at this scale.
