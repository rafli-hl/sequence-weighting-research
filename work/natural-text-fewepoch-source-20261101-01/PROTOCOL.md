# Few-epoch, data-rich width ladder: protocol

**Status:** frozen 1 Nov 2026 for owner approval. Revised after scoped review 1 (subjects 83cc9251… and fff70952…, `reports/natural-text-fewepoch-preparation-20261101-01/review-01-subjects-83cc9251-fff70952/`). Revised 2 Nov 2026 for tied weights (section 3). The corpus and the seeds exist (owner-run, 1–2 Nov 2026); no run of this study exists.

**Owner decisions:**
- `reports/natural-text-ladder-owner-decisions-20261101-01/OWNER_DECISIONS.md`: the study, a draft only;
- `reports/natural-text-ladder-owner-decisions-20261101-02/OWNER_DECISIONS.md`: D1–D7 accepted; the matched-gap primary; Holm across three primaries; the peak shift as a secondary;
- `reports/natural-text-ladder-owner-decisions-20261102-03/OWNER_DECISIONS.md`: tied weights, the real-engine check, the disclosure figures.

**Draft and planning:**
- `reports/natural-text-fewepoch-proposal-20261101-01/` (revision 01: `PROPOSAL_DRAFT.md`, `FEWEPOCH_PLANNING.json`);
- `reports/natural-text-fewepoch-preparation-20261101-01/FEWEPOCH_PLANNING_r2.json` (revision 02: the new primary and Holm).

**Disclosure.** The design follows the natural-text results already seen:
- the turn-down and the peak shift confirmed late (E24–E32) in a heavily overfit regime on WikiText-2;
- the one-rate study's panel means, which motivate the matched-gap primary (section 6c, exploratory).

## 1. The question and the predictions stated in advance

**The question.** Do the late turn-down and the peak shift appear without heavy overfitting, after about 3 epochs on enough data that every width is still improving, a regime closer to Jane Street's? And does p\* depend on width beyond what the train–validation gap (memorization) explains?

| Primary | Jane Street's pattern | Memorization-only account |
|---|---|---|
| **M**, matched-gap contrast (768 − 384) | not fixed by the pattern | **NOT_DETECTED** |
| **FALL** over 384–768 at E3 | TURNS_DOWN | CONTINUES_RISING or INCONCLUSIVE |
| **RISE** over 64–384 at E3 | RISES | RISES |

**The memorization-only account:** p\* is one function of the train–validation gap, the same at every width. Then p\* at matched gap does not depend on width (M = 0). Because the gap has risen with width at every readout seen so far, p\* also rises with width (no FALL).

**What separates the accounts:**
- **M and FALL.** RISE is predicted by both.
- **Only a rejection reads against an account.** A rejected M (either sign) or a TURNS_DOWN contradicts the memorization-only account. Its own predictions are non-rejections or rejections in the rising direction, so the study can contradict that account but cannot confirm it.
- **CONTINUES_RISING is ambiguous.** It also follows from Jane Street's pattern with a peak above 768; the ladder cannot place a peak above 768.
- **M's sign is not fixed by Jane Street's pattern.** In the planning fixtures, revision 01's pattern curve gave M ≈ +0.005 (section 9).

## 2. Data

**Corpus.** WikiText-103 raw (`Salesforce/wikitext`, `wikitext-103-raw-v1`) at the project's pinned revision b08601e0…, acquired by the sealed acquisition source (`work/natural-text-wt103-acquisition-source-20261101-01`).
- **Steps A1–A3:**
  - A1 downloads the two training files (314,076,578 bytes), each checked against its pinned size and SHA-256;
  - A2 extracts the rows after reproducing the WikiText-2 rows files with the same extraction;
  - A3 encodes with the frozen tokenizer, after reproducing the natural-text corpus byte for byte.
- **The binding:** the corpus manifest records the acquisition subject (`fewepoch_plan.ACQUISITION_SUBJECT`). Its hash becomes the plan pin `CORPUS_MANIFEST_SHA256` in a pin-only revision after A3.
- **Validation and pre-training pool:** those of N1, N3 and N4, unchanged. WikiText-103's validation and test files equal WikiText-2's, so the 512 validation and 2,048 pool sequences are identical.
- **Exclusions:** every WikiText-103 training article equal by title row or full text to any WikiText-2 article (train, validation, test). All 600 WikiText-2 training articles must be found by text, or A3 stops.

**Partition** (`fewepoch_data.partition`, sealed with the seed policy):
- the eligible articles are sorted, then shuffled with the drawn `partition_seed`;
- they are assigned whole to t00, d01, …, d10, each group until it holds at least 32,768 sequences;
- a run uses each group's first N sequences.
- **Disjointness**, checked at the builder and at every worker admission: the groups share no article, use no excluded article, and every sequence lies in its group's articles.
- **Seeds:** a new registry (`fewepoch_registry.py`; policy 16eb8ba5…, frozen now) draws 46 roles once, under an owner approval, after A3.

## 3. Design

**Widths:** 64, 96, 128, 192, 256, 384, 512, 768 (depth 4, 4 heads, context 128, 4,096-token vocabulary; 0.73–34.7 M parameters).

**Recipe** (revision 05's, except as stated):
- per group, each width is pre-trained uniformly for 4 epochs at 3e-4 (clip 5) on the pool, giving E0;
- weighted adaptation (R, log-uniform weights 0.01–10) for **3 epochs** at **one constant common rate**, batch 16, weight decay 0.1, clip 1;
- **tied weights** (owner decision 20261102-03): the weights are used exactly as drawn. Exact float32 ties are expected at N = 16,384 (ten of the eleven real draws have 1 to 3 before the division), so the check in `text_engine.weights` allows at most n / 1,024 tied values (n minus the distinct values: 16 at N = 16,384) instead of none. The estimator's stable sort keeps tied entries in ascending sequence index (their position in the draw's weight list), so p\* is bit-for-bit reproducible for the same inputs on the same Python and libm;
- readouts at **E0.25, E0.5, E1, E2, E3** (after updates 256, 512, 1,024, 2,048, 3,072 at N = 16,384);
- signed gains from each width's own E0, and p\* from the sealed estimator on [0, 8]. Undefined fits stay undefined.
- **Per stage, widest first:** pre-training, the adaptations, then the width's model state hashed and deleted. At most one state exists at a time.

**Data per draw (D1): N = 16,384.**
- **Updates:** 3,072 per width, as in the 32-epoch studies at N = 1,536. The design holds updates per width fixed, while repeats per sequence fall from 32 to 3 and unique data grow 10.7×.
- **Tokens per parameter:** 8.59 at 64, 0.18 at 768.

**Run A (tuning, t00; D4, D5):**
- **Training:** every width at 3e-5, 1e-4, 3e-4 and 1e-3, and at the extension 3e-3, from one E0 per width.
- **Records:** validation NLL at every readout and training NLL at E3; no per-sequence adaptation arrays and no p\*. Each width's E0 per-sequence losses are written, as at every stage.
- **Divergence** (review 1, finding 6): a nonfinite update or evaluation in one adaptation records that width and rate as DIVERGED, and Run A continues. A rate with any diverged width is ineligible.
- **Selection** (`select_rate`, read from the written records, by validation NLL only):
  - a rate is **eligible** if no width diverged and every width's E3 validation NLL is below its E2 value;
  - among the eligible grid rates, the lowest mean E3 validation NLL over the eight widths is selected, ties to the smaller rate;
  - if that is 1e-3, the extension replaces it only if eligible and strictly lower (once);
  - no eligible grid rate gives NO_ELIGIBLE_RATE.
- **The 2N fallback:** Run A2N (t00 at 2N = 32,768) may then be approved, after a time re-check. A B layout at 2N is not part of this revision.

**Runs B1 (d01–d05) and B2 (d06–d10):**
- one adaptation per width at the selected rate;
- training and validation per-sequence losses at every readout;
- **chaining:** B1 is bound to Run A's terminal and selection, and B2 also to B1's COMPLETE terminal.

## 4. NOT_OVERFIT (pre-registered manipulation check)

**The check:**
- **Per width:** per draw, Δ = validation NLL at E3 minus at E2.
- **The df-9 interval of the mean Δ:** below 0 gives **NOT_OVERFIT**, above 0 **OVERFIT**, otherwise **PLATEAU**.

**How it gates the primaries.** A primary is read as a test of the few-epoch question only if every width it uses is NOT_OVERFIT: 384 and 768 for M, 384–768 for FALL, 64–384 for RISE.
- **If not:** its label and Holm result are still reported, prefixed: "<name> (<label>) is not read as a few-epoch test: width(s) … were not still improving from E2 to E3 (NOT_OVERFIT failed)."
- **No remedy is allowed.** There is no re-run, data increase or replacement draw.

**Reported alongside:** the gap per width at E3, and the readout of the lowest validation NLL.

## 5. Primaries and Holm

| Primary | Statistic per draw | Rejected below 0 | Rejected above 0 | Not rejected |
|---|---|---|---|---|
| **M** | matched-gap contrast (section 6) | CAPACITY_BEYOND_MEMORIZATION | CAPACITY_ABOVE_MEMORIZATION | NOT_DETECTED |
| **FALL** | OLS slope of p\* on log2 width over 384, 512, 768 at E3 | TURNS_DOWN | CONTINUES_RISING | INCONCLUSIVE |
| **RISE** | OLS slope over 64, 96, 128, 192, 256, 384 at E3 | FALLS | RISES | INCONCLUSIVE |

**Holm** (owner decisions 20261101-02, item 2): two-sided one-sample t tests over the ten draws (df 9).
- **The step-down:** the p-values are ordered (ties in the order M, FALL, RISE), and a primary is rejected while p ≤ 0.05 / (3 − i).
- **The labels:** a rejected primary takes the direction of its mean.
- **Reporting:** every p-value, Holm-adjusted p-value and unadjusted 95% interval is reported.

**Missing data, degeneracy and saturation:**
- **Missing data:** a missing draw makes a primary UNAVAILABLE, an undefined statistic UNDEFINED. Both enter Holm with p = 1, and there is no replacement draw.
- **Degenerate values:** if the draw values are equal to within 1e-9, p is 0 for a nonzero mean and 1 otherwise, and the primary is flagged degenerate.
- **Saturation** (the S32 part of revision 05's rule; the drop-flagged SD sensitivity is not used, since each primary is one point per draw; review 1, findings 1 and 11):
  - a draw is flagged if any fit its statistic uses is ≥ 7.999, and its fits are refitted at bound 32;
  - a primary with an unresolved refit, or an undefined refitted statistic, is **SATURATED** and enters both Holm runs with p = 1. Its bound-8 p-value is reported as `bound8_p`, and its `primary_label` is left empty (confirmation of review 1, N4);
  - **the main Holm** uses every other readable primary's bound-8 p-value;
  - **the re-run:** if any primary is flagged, Holm is re-run with the flagged primaries' bound-32 p-values. **Every** primary whose label differs between the two runs, flagged or not, is **SATURATION_SENSITIVE**;
  - SATURATED and SATURATION_SENSITIVE primaries are reported but not read.

## 6. The matched-gap primary M

### 6a. Definition
- **Gap:** at a readout, the validation NLL minus the training NLL (the worker's record).
- **Common range per draw:** for 384 and for 768, the gaps at E0.25–E3 span [min, max]. The common range is [max of the minima, min of the maxima].
- **Levels:** 101 equally spaced levels G of the common range, the first and last set exactly to its ends.
- **Undefined** (review 1, findings 2 and 3): M is UNDEFINED for a draw if any of its ten fits (384 or 768 at E0.25–E3) is undefined, if the common range is empty or a single point, or if a level is not crossed.
- **Reading p\* at a level:** for each width, p\* at G is read at the first crossing of G along the readout path (linear interpolation within that segment).
- **M** is the mean over the levels of p\*(768, G) − p\*(384, G).

**The E0 offset** (review 1, finding 15). The gap includes each width's E0 offset: the training articles come from WikiText-103 and the validation sequences from WikiText-2's validation split. The mean E0 gap of 384 and of 768 is reported beside M, and in its reading.

### 6b. The confound, stated in advance
**At matched gap the larger width has had fewer epochs.** Larger widths memorize faster, so 768 reaches a given gap at an earlier readout. A nonzero M therefore also follows if p\* depends on training progress rather than on the gap.
- **In the fixtures:** an epoch-only curve, with p\* depending on the readout only and equal across widths, read CAPACITY_BEYOND_MEMORIZATION in 96–99% of replicates (section 9).
- **What M can show:** a rejection contradicts the memorization-only account. It does not by itself show a capacity effect.

### 6c. EXPLORATORY motivation (seen panel means of the one-rate study, d01–d10; not pre-registered)

Verified from `reports/natural-text-onerate-analysis-20261030-02/ANALYSIS.json`: per width, the panel p\* is interpolated along E1–E32 at panel gap G.

| Width | 128 | 192 | 256 | 384 | 512 | 768 |
|---|---|---|---|---|---|---|
| p\* at gap 0.25 | 0.1367 | 0.1403 | 0.1433 | 0.1446 | 0.1471 | 0.1284 |
| 768 minus it | −0.0083 | −0.0120 | −0.0150 | −0.0163 | −0.0187 | |
| p\* at gap 0.5 | 0.1783 | 0.1866 | 0.1918 | 0.1966 | 0.1991 | 0.1770 |
| 768 minus it | −0.0013 | −0.0095 | −0.0148 | −0.0196 | −0.0221 | |

**The owner's statement holds for 384 and 512, and only in part beyond them:**
- **384 and 512:** 768 lies 0.016–0.022 below them at both gaps.
- **Smaller widths:** it lies only 0.008–0.015 below 128–256 at gap 0.25, and 0.001–0.015 below them at gap 0.5.
- **128–512 are not nearly equal:** they span 0.010 at gap 0.25 and 0.021 at gap 0.5, rising with width.
- **The regime differs.** These are seen, overfit-regime panel means. 768 reaches these gaps at E1–E4, the other widths far later.

**Seen per-draw M** (one-rate draws, ladder 384 and 768):

| Readout window | Mean M | sd | Draws negative |
|---|---|---|---|
| E1–E4 | −0.0162 | 0.0059 | 10/10 |
| E1–E32 | −0.0418 | 0.0087 | 10/10 |

## 7. Secondaries (non-gating; no multiplicity adjustment)

**The peak shift:**
- **The statistic:** per draw, the OLS slope of the peak location L on log2 readout over E0.25–E3, with L by the sealed rule on the 8-rung ladder.
- **The labels:** MOVES_SMALLER, MOVES_LARGER or NO_DETECTED_SHIFT, from the df-9 interval.
- **Its censoring statement:**
  - locations at 768 before the mean log2 readout (E0.25, E0.5), or at 64 after it, make the slope conservative for MOVES_SMALLER, provided those curves continue beyond the ladder end;
  - any location at 768 at E1–E3 or at 64 at E0.25–E0.5 can overstate it.
- **Why it is a secondary:** the seen early-epoch peak moved to larger widths (+0.135 per doubling over E1–E4, seen).

**By readout:**
- the panel p\* curve and gap;
- the panel and per-draw argmax;
- the FALL and RISE statistics with unadjusted intervals;
- the per-draw locations.

**Also reported:**
- **losses:** E0 and readout training and validation NLL, the lowest-validation readout, and clipping per width;
- **matched gap:** each draw's common gap range;
- **fits:** every fit, with its bound flags.

## 8. Readings (fixed now; `fewepoch_analysis.readings` prints them)

**Always:**
- **The regime:** "The few-epoch question is read only where every width a primary uses was still improving its validation loss from E2 to E3 (NOT_OVERFIT). The models are small (0.73-34.7 M parameters, depth 4) and see far fewer tokens per parameter than compute-optimal training; "closer to Jane Street's setting" means 3 epochs and no detected overfitting, nothing more."
- **Holm:** the labels follow Holm's step-down over M, FALL and RISE at family-wise 5%.
- **Disclosure:** the data source; the tokenizer, validation set and pool shared with the earlier studies; the rate chosen on t00 by validation NLL only.

**M:**
- **BEYOND:** "… This contradicts the memorization-only account, which predicts NOT_DETECTED. It is not by itself evidence of a capacity effect." The confound (6b) follows.
- **ABOVE:** the contradiction, "It is not by itself evidence of a capacity effect", then the confound.
- **NOT_DETECTED:** "… as the memorization-only account predicts. This is not a claim of absence." Then the power stated in advance, marked as computed from effects seen in the overfit regime of the earlier studies.
- **Every readable M reading** (not UNAVAILABLE, UNDEFINED, SATURATED or SATURATION_SENSITIVE) ends with the mean E0 gap of 384 and 768; the E0 gap is reported in ANALYSIS.json in every case.

**FALL:**
- **TURNS_DOWN:** the fall seen late in the overfit regime also appears in this few-epoch regime, at this scale.
- **CONTINUES_RISING:** "no turn-down within this ladder. This matches the memorization-only prediction, and also Jane Street's pattern with a peak above 768; the study cannot separate the two."
- **INCONCLUSIVE:** not detected with ten draws, not a claim of absence, with the power stated in advance.

**RISE:**
- **RISES:** as both accounts predict.
- **FALLS:** contrary to both.
- **INCONCLUSIVE:** as for FALL.

**FALL TURNS_DOWN with RISE RISES**, both read as few-epoch tests (NOT_OVERFIT holds for their widths): "an interior p\* peak at E3 within 64-768."

**The NOT_OVERFIT prefix** applies wherever a primary's widths fail the check (section 4).

**No reading claims a mechanism.**

## 9. Power and fixtures (stated in advance)

**Holm over the three primaries, ten draws** (`FEWEPOCH_PLANNING_r2.json`: independent normal draw values at the seen means and sds):

| | M | FALL | RISE | All three in the predicted direction |
|---|---|---|---|---|
| At the seen effects | >0.999 | 0.999 | >0.999 | 0.999 |
| At half of them | 0.953 | 0.714 | >0.999 | 0.696 |

- **The family-wise rate under the complete null:** 0.049.
- **The seen effects:** M −0.0162 (sd 0.0059, E1–E4 window); FALL −0.0225 (sd 0.0124, the E24 fall); RISE +0.0159 (sd 0.0018, E1).
- **The seen falls come from the overfit regime.** No fall has been seen at few epochs.

**Curve fixtures (ten draws), on assumed gap trajectories:**
- **Model:** gap(w, e) = −0.10 + 0.10 log2(w / 32) × e / 3, noise sd 0.002.
- **p\* noise:** sd 0.0088, half or 80% persistent.
- **Labels:** the full rules, the three statistics and Holm.

| Curve | M BEYOND | M ABOVE | FALL TURNS_DOWN | RISE RISES |
|---|---|---|---|---|
| Memorization-only, linear | 0.023–0.029 | 0.021–0.024 | 0.000 | 1.000 |
| Memorization-only, concave | 0.027–0.030 | 0.024–0.026 | 0.000 | 1.000 |
| Flat | 0.009–0.010 | 0.008–0.009 | 0.008–0.009 | 0.010 |
| Epoch-only (the confound) | 0.960–0.992 | 0.000 | 0.011–0.012 | 0.011–0.012 |
| 768 offset at the seen M | 0.972–0.993 | 0.000 | 0.000 | 1.000 |
| 768 offset at half the seen M | 0.512–0.610 | 0.000 | 0.000 | 1.000 |
| Revision 01's Jane Street pattern (seen) | 0.001 | 0.217–0.275 | 0.997–0.999 | 1.000 |

**Reading the fixtures:**
- **False positives under memorization-only curves:** M rejects in either direction in 2.1–3.0% of replicates per side, against a nominal 2.5% (4,000 replicates, standard error about 0.25 points).
- **The assumed gaps are not measured in this regime.**

## 10. Time, disk, memory and gates

**Time** (revision 05's cap formula on this design's counts, with probe costs for 384–768):

| Run | Stages | Projected | Stage cap | Worst case |
|---|---|---|---|---|
| A | t00 | 1.82 h | 8,310 s | 2.58 h |
| B1, B2 | 5 draws each | 2.76 h each | 2,604 s | 3.95 h each |
| A2N (only if needed) | t00 | 3.53 h | 16,024 s | 4.72 h |

**Feasibility:** stages × (cap + 60) + 900 + 1,800 ≤ 21,600 s. The 1,800 s reserves one full 30-minute gate wait.

**Disk:**
- 4.27 GiB free now;
- after acquisition about 3.1–3.7 GiB. A kept acquisition failure stays on D: (up to about 0.3 GB) and can bring free space below the 3 GiB admission check; every run would then refuse (not counted) until an owner decision (confirmation of review 1, N3);
- run admission requires 3 GiB, with a 2 GiB reserve;
- start-up benchmark states are about 0.89 GB, transient;
- kept outputs about 5.3 MB per draw.

**Host memory of the acquisition** (confirmation of review 1, N2): A3's text handling peaked at 1.84 GB natively on 536 MB of the WikiText-2 training rows repeated to 1.8 M rows, about 1.9 GB at the real 546 MB, before the tokenizer (not measured). WSL's default limit here is about 8.4 GB.

**GPU memory:**
- every width must peak at or below 2.25 GiB at start-up, or the run stops before training (not counted);
- 768 measured 2.2225 GiB twice;
- the 2.5 GiB guard applies throughout.

**Gates** (unchanged): before every stage, the Windows GPU check and an AC power check, rechecked for up to 30 minutes; a refusal on battery; a power log every 5 s.

## 11. Limitations stated in advance

- **Scale:** depth 4, at most 34.7 M parameters, one corpus family, few tokens per parameter. No large-model or scaling claim follows.
- **Not Jane Street's setting:**
  - a constant rate (D7), with no horizon-tied schedule;
  - small models adapted from a short uniform pre-training.
- **Censoring:** a peak above 768 cannot be placed, and CONTINUES_RISING does not separate the accounts.
- **The M confound** (6b). M can contradict the memorization-only account but cannot show a capacity effect.
- **Fixed readouts mix capacity with training progress.**
- **Shared items:** the validation set and pool are those of N1–N4, and the tokenizer is WikiText-2's.
- **The gap's E0 offset:** training and validation text come from different splits, so each width's gap starts from its own E0 offset; it is reported beside M (6a).
- **Data selection:** WikiText-103's articles exclude WikiText-2's, so the corpus is not the full WikiText-103 training split.
- **No held-out test loss:** the test split is the pre-training pool.

## 12. Operations and failure policy

**Owner steps, each approved separately and run by the owner:**
1. **A1–A3:** the acquisition, one approval, three commands (acquisition source README).
2. **A pin-only revision:** `CORPUS_MANIFEST_SHA256` is set in `fewepoch_plan.py`, checked by a diff limited to the pin lines.
3. **The seed draw:** `fewepoch_registry.py draw`, under its own approval.
4. **A second pin-only revision:** the registry and partition pins. **A third revision:** tied weights (section 3). Then the builder's pin to the final subject, with a check.
5. **The real-engine check, before Run A** (owner decision 20261102-03): the real inputs of all eleven groups on CPU with real Torch, and a GPU smoke test of the sealed stage code on two small widths with synthetic tokens and test seeds. It writes only to scratch, reads no loss, and is not a stage of any run.
6. **Run A, then B1, then B2:** each from an activation built by `build_fewepoch_activation.py` and run with `FEWEPOCH_OWNER_RUN.ps1`.
7. **The analysis:** `fewepoch_analysis.py` on B1 and B2, after both are COMPLETE.

**Counting rule:**
- a run that creates any stage folder is the only attempt of its stages;
- a failure of Run A, A2N, B1 or B2 after that closes the study UNAVAILABLE. A DIVERGED adaptation in Run A or A2N is not a failure: the run continues and that rate is ineligible. A nonfinite update in B1 or B2 is a failure;
- a COMPLETE Run A2N that selects a rate needs a later revision (a B layout at 2N) and an owner decision before any B run. A COMPLETE Run A2N with NO_ELIGIBLE_RATE ends the tuning without a rate: the study cannot proceed in this design, and the next step is an owner decision;
- **one source subject:** Run A, A2N, B1 and B2 must run under the same sealed source subject (each terminal's subject is checked at admission). Every pin must therefore be set before Run A: any source revision after Run A, even a pin-only one, makes the later runs inadmissible, and Run A cannot be repeated (confirmation of review 1, N6);
- a stop before any stage folder exists (a refusal, STOPPED_AT_STARTUP) is not counted, and the next step is an owner decision.

**No retry,** resume, rate or width change, limit increase, replacement draw or seed redraw.

**TERMINAL.json:**
- it is written through the output ledger, or as a last resort directly, with `terminal_outside_ledger`;
- the owner receipt now copies that flag (the late-turn limitation, addressed).
