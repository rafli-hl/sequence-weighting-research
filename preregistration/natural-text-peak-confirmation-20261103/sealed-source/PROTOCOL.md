# Peak confirmation on fresh WikiText-103 draws: protocol

**Status:** frozen 3 Nov 2026 for owner approval. The corpus and the seeds exist (owner-run); no run of this study exists.

**Owner decisions:**
- `reports/natural-text-ladder-owner-decisions-20261103-03/OWNER_DECISIONS.md`: build the confirmation; the layout, the primary, the control, the secondary, six draws, three readings;
- `reports/natural-text-ladder-owner-decisions-20261103-04/OWNER_DECISIONS.md`: the wording of the readings; the C1/C2 split.

**Draft and planning:** `reports/natural-text-peak-confirmation-draft-20261103-01/` (`PROPOSAL_DRAFT.md`, `CONFIRMATION_PLANNING.json`); `reports/natural-text-peak-seed-package-20261103-01/` (`SPLIT_BUDGET.json`, `FRESH_POOL_CHECK.json`).

**Disclosure.** This hypothesis was formed after seeing d01–d10 of the few-epoch study (`reports/natural-text-fewepoch-descriptive-20261103-01/DESCRIPTIVE.md`): at every readout the per-draw argmax was 512 in 10/10 draws, on a ladder at 3e-4. So d01–d10 cannot confirm it, and neither can t00. The idea for the control also came after seeing p\*. The rate it uses comes from t00's validation NLL only.

## 1. The question

At E3 at 3e-4, on draws never used, is p\* at 512 above p\* at both 384 and 768? And does the fall from 512 to 768 survive at 1e-4, 768's lower-NLL rate on t00?

## 2. Data

**Corpus:** the WikiText-103 corpus of the few-epoch study (manifest `be911db7…`), read-only.

**Fresh articles** (`peak_data.fresh_pool`; policy `reports/natural-text-peak-seed-registry-20261103-01/SEED_REGISTRY_POLICY.md`). Of the 27,859 eligible articles:
- the 8,692 assigned to t00–d10 are out, including those behind their unused second halves;
- 94 text duplicates of assigned articles are out;
- every copy of a text repeated inside the pool is out (215 articles in 107 sets);
- that leaves 18,858 fresh articles with 779,618 sequences.

**Partition** (`peak_data.partition`): the fresh indices are sorted, shuffled with the registry's `partition_seed`, and assigned whole to c01, …, c06 until each holds at least 16,384 sequences; each group uses its first 16,384.

**Seeds:** registry `0e8b0528…` (owner-run, OWNER-20261103-PEAK-SEEDS-01), 26 values. Partition `3ba24bff…`. 2,407 articles used; 16,451 left over.

**Measured overlap, disclosed with the results:** `reports/natural-text-peak-seed-registry-20261103-01/DISCLOSURE_FIGURES.md`.

**Shared by design:** the validation set, the pre-training pool and the tokenizer are those of the earlier natural-text studies, and every draw shares them.

**No tuning draw.** Both rates are already fixed (section 3).

## 3. Design

**Unchanged from the few-epoch study:** depth 4, 4 heads, context 128, 4,096-token vocabulary; per group, each width pre-trained uniformly for 4 epochs at 3e-4 (clip 5) on the pool, giving E0; weighted adaptation (R, log-uniform weights 0.01–10) for 3 epochs at a constant rate, batch 16, weight decay 0.1, clip 1; the weights used exactly as drawn, with at most n / 1,024 tied values; readouts at E0.25, E0.5, E1, E2, E3 (after updates 256, 512, 1,024, 2,048, 3,072); signed gains from each width's own E0; p\* from the sealed estimator on [0, 8]. Undefined fits stay undefined.

**The arms per draw:**

| Width | 3e-4 | 1e-4 |
|---|---|---|
| 768 | yes | yes |
| 512 | yes | yes |
| 384 | yes | |

- **Pairing.** A width's arms share one E0, and every arm of a draw shares its tokens, weights and batch order.
- **Per stage, widest first:** pre-training, the width's arms, then its model state hashed and deleted. At most one state exists at a time.
- **The rates are not chosen again.** 3e-4 is the rate the few-epoch study selected on t00 (`LR_SELECTION.json`, `fa760ba0…`). 1e-4 is 768's lowest validation NLL on t00 among the five rates tried. p\* enters neither.
- **Runs:** C1 (c01–c03) and C2 (c04–c06). C2 is admitted only on C1's COMPLETE terminal under the same source subject and inputs.

## 4. The primary

Per draw at E3, at 3e-4: **D1** = p\*(512) − p\*(384), **D2** = p\*(512) − p\*(768). From the 95% interval of each mean (df 5):

| Label | Rule |
|---|---|
| **INTERIOR_PEAK** | Both lower limits above 0 |
| **NOT_CONFIRMED** | Anything else, with both intervals reported |

Both contrasts must pass, so there is no multiplicity adjustment. Simulated with D2 truly 0, the false-positive rate is about 0.025 (`CONFIRMATION_PLANNING.json`).

## 5. The control

**D4** = p\*(512) − p\*(768), both at 1e-4, per draw at E3. **It is read only if the primary is INTERIOR_PEAK,** which keeps the family-wise rate at 5%.

| Primary | D4 interval | Label |
|---|---|---|
| INTERIOR_PEAK | Lower limit above 0 | **PEAK_AT_BOTH_RATES** |
| INTERIOR_PEAK | Upper limit below 0 | **RATE_DEPENDENT** |
| INTERIOR_PEAK | Spans 0 | **FALL_NOT_DETECTED_AT_1E-4** |
| Anything else | Any | **NOT_READ**, reported |

## 6. The pre-registered secondary, with its caveat

**D3** = p\*(512 at 3e-4) − p\*(768 at 1e-4), per draw at E3. It compares each width at its own lower-NLL rate of the two on t00, so it compares two rates, and it is not a test of the rate account.

**The gap caveat, stated in advance.** On t00 the gap at 512 at 3e-4 (0.5676) is above the gap at 768 at 1e-4 (0.5382), so if p\* simply tracked the gap, D3 would be above 0 with no turn at 768. In D4, at the same rate, the t00 gap runs the other way (0.4422 at 512, 0.5382 at 768). These are one draw, and each run reports its own gaps.

## 7. Readings (fixed now; `peak_analysis.readings` prints them)

| Outcome | Reading |
|---|---|
| **Peak at both rates** | At 3e-4, p\* at 512 is above 384 and 768 on fresh draws, and 512 also stays above 768 at 1e-4. The fall from 512 to 768 is not explained by 768's rate, at the two rates tested. 384 was not trained at 1e-4, so the rise to 512 is measured at 3e-4 only |
| **Peak at 3e-4 only** | At 1e-4, 768 is above 512, so the fall seen at 3e-4 is rate-dependent, at the two rates tested |
| **Primary passes, D4 spans 0** | Fall from 512 to 768 at 1e-4 not detected; not a claim of absence; not read as rate-dependent |
| **No peak confirmed** | The lower limits of 512 − 384 and 512 − 768 are not both above 0. This is not a claim of absence. The peak is not confirmed, and the earlier pattern stays descriptive. The power stated in advance follows |

**"Rate-dependent" is reserved for 768 above 512 at 1e-4.** INTERIOR_PEAK means an ordering of three rungs at this scale. It does not place the peak between rungs. **No reading claims a mechanism.**

## 8. NOT_OVERFIT, missing data and saturation

**NOT_OVERFIT (pre-registered manipulation check).** Per arm, per draw, Δ = validation NLL at E3 minus at E2. The df 5 interval of the mean Δ: below 0 gives NOT_OVERFIT, above 0 OVERFIT, otherwise PLATEAU. The primary's arms are the three at 3e-4, and the control's are 512 and 768 at 1e-4. If an arm fails, the label stands and its reading is prefixed. The control's reading also carries the prefix of a failing primary arm, since the control is read only if the primary is. **No remedy is allowed:** no re-run, data increase or replacement draw.

**Missing data:** a missing draw makes a contrast UNAVAILABLE, and an undefined statistic makes it UNDEFINED.

**Saturation (the few-epoch rule):** a draw is flagged if a fit its contrast uses is ≥ 7.999, and its fits are refitted at bound 32. An unresolved refit makes the contrast SATURATED, and a side that differs at bound 32 makes it SATURATION_SENSITIVE.

**A primary or control with such a contrast takes that status and is not read,** in the order UNAVAILABLE, UNDEFINED, SATURATED, SATURATION_SENSITIVE.

## 9. Other secondaries (non-gating; no multiplicity adjustment)

- **The rate effects at 512 and at 768,** 1e-4 minus 3e-4 at E3: p\* (R), validation NLL (V), training NLL and the gap. On t00, V at 768 was −0.0357. If the interval of V at 768 is not below 0 on these draws, the premise of the control is not repeated, and a read control's sealed reading says so. The rate account predicts R above 0 at 768.
- **By readout:** D1, D2, D3 and D4 with unadjusted intervals; the panel p\*, gap and losses per arm; the per-draw argmax of the three rungs at 3e-4; the FALL statistic at 3e-4.
- **M on these draws,** at 3e-4, with the few-epoch definition and its confound.
- **Losses and clipping per arm,** E0 per width, and every fit with its bound flags.

## 10. Power, time, disk and memory (forecasts)

**Power** (`CONFIRMATION_PLANNING.json`, six draws): P(INTERIOR_PEAK) is >0.999 at the effects seen in d01–d10 and 0.941 at half of them; with the sd at its upper 95% limit, 0.989 and 0.588. Those draws selected this hypothesis, so the seen effects are likely flattering.

**The control's power is an assumption, not an estimate.** No p\* exists at 1e-4 at any width, because Run A wrote no arrays. At six draws, the smallest mean detected is 1.43 sds at 80% power and 1.67 at 90%; the sd of D4 is unknown.

**Time** (`SPLIT_BUDGET.json`; each run computes its own cap from its own start-up benchmark):

| One run of three draws | Worker clock | Windows clock (×1.08) |
|---|---|---|
| Forecast | 1.96 h | 2.10 h |
| Worst case: 900 s benchmark, three stages at the 2,841 s cap, one full gate wait | 3.17 h | 3.42 h |
| Worst case with every gate at its full 30 minutes | 4.17 h | 4.51 h |

The formula is that of the few-epoch worker on this layout: cap = ceil(1.25 × projected + 120 s); a run stops before any training unless stages × (cap + 60) + 900 + 1,800 ≤ 21,600 s. No real run has had two rates at a width with arrays at every readout.

**What the formula does not enforce.** The margin above holds at the forecast. A run whose own benchmark came in about 2.09 times slower would still be admitted, though its worst case would pass the owner script's 21,900 s wait: the receipt would then read EXIT_UNOBSERVED_NO_KILL while the worker might still finish. That also needs every stage to reach its cap, which no past stage came near.

**Disk:** run admission requires 3 GiB free, with a 2 GiB reserve; a run keeps about 7.1 MB; start-up benchmark states are about 743 MB for these widths, transient (the budget carries 893 MB, the eight-width figure).

**GPU memory:** every width must peak at or below 2.25 GiB at start-up, or the run stops before training (not counted). 768 measured 2.2244 GiB in Run A. The 2.5 GiB guard applies throughout.

**Gates** (unchanged): before every stage, the Windows GPU check and an AC power check, rechecked for up to 30 minutes; a refusal on battery; a power log every 5 s.

## 11. Limitations stated in advance

- **A mechanism:** no result here says why p\* orders as it does.
- **Other rates:** the control speaks to 1e-4 only. The best rate for 768 is not located, and the grid is coarse.
- **The rise at 1e-4:** 384 is not trained at 1e-4, so at that rate only the fall from 512 to 768 is measured.
- **The peak's place:** there is no rung between 512 and 768, and nothing above 768.
- **Shared items:** consistency across the pool, the tokenizer and the recipe is not tested.
- **E0:** in d01–d10, 768 started from a higher E0 validation NLL than 384 and 512 after the same pre-training. Neither rate arm changes that.
- **Scale:** depth 4, at most 34.7 M parameters, one corpus family. No scaling claim, and this is not Jane Street's setting: a constant rate with no horizon-tied schedule, and small models adapted from a short uniform pre-training.
- **Independence:** draws are treated as independent in every interval. The disclosure figures do not measure how far that is true.
- **No held-out test loss:** the test split is the pre-training pool.

## 12. Operations and failure policy

**Owner steps, each approved and run by the owner:**
1. **The real-engine check:** the real inputs of all six groups on CPU with real Torch, and a GPU smoke test of the sealed stage code on two small widths with two rates, on synthetic tokens and test seeds. It writes only to scratch, reads no loss, and is not a stage of any run.
2. **Run C1, then Run C2:** each from an activation built by `build_peak_activation.py` and run with `PEAK_OWNER_RUN.ps1`.
3. **The analysis:** `peak_analysis.py` on C1 and C2, once both have ended with a terminal, with the results report's layout frozen first. If C1 does not complete, so that C2 cannot exist, or a run leaves no terminal, the analysis is not run: the study closes UNAVAILABLE from the terminal and the owner receipt, and every folder is kept. If C2 fails with a terminal, the analysis runs and prints UNAVAILABLE, with the completed draws reported.

**Counting rule:**
- a run that creates any stage folder is the only attempt of its stages;
- a failure of C1 or C2 after that closes the study UNAVAILABLE. A nonfinite update is a failure;
- a stop before any stage folder exists (a refusal, STOPPED_AT_STARTUP) is not counted, and the next step is an owner decision;
- **one source subject:** C1 and C2 must run under the same sealed source subject.

**No retry,** resume, rate or width change, limit increase, replacement draw or seed redraw.
