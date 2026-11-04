# Natural-text one-rate ladder extension: protocol

**Status: revision 02, the final attempt** (owner ruling 20261030-03, section 11), prepared on 30 Oct 2026 for owner approval. Revision 01 was prepared and reviewed in `reports/natural-text-onerate-preparation-20261030-01/` (review 1 in `review-01-subject-6682b2dc/`); its run, attempt 1, failed operationally in d06 and is never analysed. Revision 02 changes operations only. No outcome of either attempt has been opened.

**Owner decisions:**
- `reports/natural-text-ladder-owner-decisions-20261030-01/OWNER_DECISIONS.md` (the study);
- `reports/natural-text-ladder-owner-decisions-20261030-02/OWNER_DECISIONS.md` (the ladder top and the start-up memory fallback);
- `reports/natural-text-ladder-owner-decisions-20261030-03/OWNER_DECISIONS.md` (revision 02, the final attempt; section 11).

**Disclosure.** This study was designed after revision 05's result was seen.
- **That result:** Primary A NO_DETECTED_SHIFT_CENSORED and Primary B CONVEX (`reports/natural-text-ladder-analysis-20261029-01/REPORT.md`).
- **The EXPLORATORY note** (`reports/natural-text-ladder-exploratory-20261029-01/EXPLORATORY_NOTE.md`) recorded three descriptive facts:
  - the dip at 128 coincides with the change of rate;
  - p* rises with width over 128–384 at every epoch;
  - p* tracks the train-validation gap.

The study tests those post-hoc observations, pre-registered here. It is an extension of seen draws, not a fresh replication (section 2).

## 1. Questions and the predictions stated in advance

**Q1, turn-down.** At one learning rate for every width, does p* fall above 384? This is Jane Street's finding (1), "p* rises and then falls with model size", at the top of a wider ladder.

**Q2, the dip at one rate.** At that single rate, is p* still lower at 128 than at 64 and 96? In Run B, 64 and 96 had other rates.

**Q3, memorization tracking.** Across widths at a fixed epoch, does p* rank with the train-validation gap?

**Predictions** (fixed before any run). Owner decision 20261030-01 states that memorization predicts CONTINUES_RISING and NO_DIP_AT_ONE_RATE, and that the Jane Street pattern predicts TURNS_DOWN. TRACKS_MEMORIZATION as the memorization account's third prediction is a **protocol addition**, put to the owner with the approval request:

| Hypothesis | Turn-down | Dip | Memorization |
|---|---|---|---|
| Memorization (p* follows how much each model memorizes its draw) | CONTINUES_RISING | NO_DIP_AT_ONE_RATE | TRACKS_MEMORIZATION |
| Jane Street pattern (rise, then fall with size) | TURNS_DOWN | — | — |

## 2. Design: R1, the same ten draws extended

**Data, seeds and pools.** Everything is revision 05's, unchanged:
- **Draws:** d01–d10, disjoint sets of whole WikiText-2 training articles (partition 5f9f2646…, registry 8ce7d597…, corpus manifest 72daa1e1…);
- **Pools:** the shared pre-training pool (2,048 test-split sequences) and validation set (512 validation-split sequences);
- **Seeds:** every per-draw seed and the benchmark seed. No seed is drawn.

**Widths:** 64, 96, 128, 192, 256, 384, 512 and 768, at **3e-5** for every width (owner decision 20261030-01, item 3).

| Widths | Source |
|---|---|
| 128, 192, 256, 384 | **Run B's own trajectories**, which already used 3e-5 (`LR_SELECTION.json` cb059387…). They are read from Run B (terminal 277e38c7…). Every Run B file that this run or its analysis reads (220 files, 85.5 MB, and each width's rate) is checked against the inventory taken before Run B's analysis (`INVENTORY_BEFORE.json` 36a4c2f9…): by the builder before the activation is armed, by the worker before its run folder exists, and again by the analysis. |
| 64, 96 | **New adaptations at 3e-5 from Run B's own E0 states**, with Run B's weights and batch orders. Before training, the run checks that the draw's inputs equal Run B's: the seeds, the sequence indices, the tensor hashes of the training, validation and pool sequences, of the weights and of both orders, and the weights themselves. The sealed reload checks every tensor hash of the E0 state. Only the rate differs from Run B. |
| 512, 768 | **New widths.** Pre-trained and adapted exactly as Run B's widths were: the same code, recipe, readouts and per-draw seeds. Parameters: 16,870,400 and 34,742,784. |

**Exposure.** Run B's results at 128–384 have been seen. So:
- the turn-down compares unseen rungs (512, 768) with a seen one (384);
- the dip compares unseen rungs (64, 96) with a seen one (128);
- the memorization statistic uses four seen and four unseen widths.

**Unchanged from revision 05** (sections 3–4 of its PROTOCOL):
- the model code;
- the recipe: uniform pre-training of 4 epochs at 3e-4 on the pool; weighted adaptation of 32 epochs, batch 16, constant rate, weight decay 0.1, clip 1, log-uniform weights 0.01–10;
- the readouts E0–E32, the gains and the estimator;
- the inference unit: the ten draws, df 9.

## 3. GPU memory and the start-up memory fallback

**Guard.** The sampled-GPU guard is **2.5 GiB** for the whole run (owner decision 20261030-01, item 2).

**Probe.** The probe measured the benchmark's steps: 768 peaked at 2.2225 GiB, 28.2 MiB below the 2.25 GiB limit; 512 at 1.6346 GiB. Its verdict was FITS_768 (`reports/natural-text-ladder-probe-result-20261030-01/RESULT.md`).

**Start-up memory fallback** (owner decision 20261030-02).
- **How the benchmark runs.** The run's start-up benchmark is revision 05's `text_worker.benchmark`, unchanged. It runs one width at a time (64, 96, 512, then 768), resets each width's peaks before it starts, and has a 900 s budget. Its result sets the ladder top from each width's **peak sampled device memory only**. The limit is 2.25 GiB (2,415,919,104 bytes), the probe's limit.
- **Top 768** (PEAK_768_WITHIN_LIMIT): 64, 96 and 512 are within the limit, and 768 completes within it.
- **Top 512, before any training:** 64, 96 and 512 are within the limit, and 768 does one of these. The reason is recorded:
  - completes above the limit (PEAK_768_OVER_LIMIT);
  - stops on the 2.5 GiB guard (STOPPED_GUARD_AT_768);
  - stops on CUDA out of memory with its sampled peak already above the limit (STOPPED_OOM_AT_768).
- **STOPPED_AT_STARTUP:** anything else. The run stops before any training, and the next step is an owner decision. This covers:
  - a failure or a peak above the limit at 64, 96 or 512;
  - out of memory at 768 within the limit;
  - the RSS limit, a timeout, or another error at 768.

  These are the probe's conservative cases.
- **What falling back changes:** the ladder becomes 64–512, and the turn-down becomes the two-point change 384 → 512 (section 5).

## 4. Time budget and the B1/B2 split

**Formula.** The cap is revision 05's formula (`text_worker.stage_cap`), applied to this run's exact per-stage counts (`onerate_worker.study_cap`). Every measured per-call cost is multiplied by its count:
- pre-training and E0 only for 512 and 768;
- the E0 copy for 64 and 96;
- one adaptation per trained width;
- the guards and the inventory.

Cap = ceil(1.25 × projected + 120 s). Ten draws are feasible iff 10 × (cap + 60) + 900 ≤ 21,600 s.

**From the measured costs** (Run B at 64 and 96, the probe at 512 and 768; `reports/natural-text-onerate-preparation-20261030-01/BUDGET.json`):

| Ladder top | Projected stage | Projected run | Stage cap | Worst case | Feasible up to |
|---|---|---|---|---|---|
| 768 | 973.3 s | 2.70 h | 1,337 s | 4.13 h | 1.57 × the measured costs |
| 512 | 440.2 s | 1.22 h | 671 s | 2.28 h | 3.63 × |

**The split is not needed.** Ten draws fit one 6 h run with either top, so this source has no B1/B2 split. If the run's own start-up benchmark puts ten draws over 6 h, the run stops before any training (STOPPED_AT_STARTUP, TEN_DRAWS_OVER_6_H) for an owner decision.

**Calibration.** Revision 05's measured mean stage was 0.934 of its projection.

## 5. Primaries (owner decision 20261030-01, item 5)

**Fits.**
- **Gain:** E0 training loss minus the readout training loss, per sequence, signed (float32 subtraction, as in revision 05). The E0 is Run B's for 64–384 and this run's for 512 and 768.
- **p\*:** `vendor/core.exponent` on [0, 8], through `text_analysis.fit`, a byte copy.
- Undefined fits stay undefined.

**Points:** the draw-epoch pairs at E4, E6, E8, E12, E16, E24 and E32. Each primary has its own per-point statistic:

| Primary | Statistic per point | Defined iff |
|---|---|---|
| **Turn-down** | OLS slope of p* on log2 width over 384, 512 and 768 (under the 512 top: over 384 and 512, the two-point change) | those fits are defined |
| **Dip at one rate** | OLS slope of p* on log2 width over 64, 96 and 128 | those fits are defined |
| **Memorization** | Spearman rank correlation (average ranks for ties) across all ladder widths (8, or 7 under the 512 top) between p* and the gap. The gap is the validation NLL minus the training NLL at that epoch, the means in the readout records. | every ladder fit is defined, and neither p* nor the gap is constant across widths |

The memorization statistic is computed **at each fixed epoch** and never pooled across epochs.

**Per draw:** the mean of the statistic over the draw's defined points.

**Eligibility and missing draws** (revision 05's rules):
- A draw is eligible with at least 6 of the 7 points defined, including one of E4/E6 and one of E24/E32.
- A primary is **UNAVAILABLE** if any draw's stage did not complete (failed, never run, or a run STOPPED_AT_STARTUP).
- It is **UNDEFINED** if any draw is ineligible.
- There is no replacement draw.

**Labels.** From the df-9 t interval (t = 2.262157163) of the mean of the ten draw means, with a ±1e-9 tolerance:

| Primary | Interval below 0 | Interval above 0 | Otherwise |
|---|---|---|---|
| Turn-down | TURNS_DOWN | CONTINUES_RISING | INCONCLUSIVE |
| Dip at one rate | DIP_PERSISTS | NO_DIP_AT_ONE_RATE | INCONCLUSIVE |
| Memorization | OPPOSES_MEMORIZATION | TRACKS_MEMORIZATION | NO_DETECTED_TRACKING |

**Saturation rule** (revision 05's, on the fits each primary uses):
- **S1:** a point is flagged if every fit it uses is defined and any of them is ≥ 7.999, whether or not its statistic is defined. A memorization point whose fits are all at the bound is constant across widths and has no Spearman correlation; it is flagged, not dropped (review 1, finding 2).
- **S32:** whenever a point is flagged, its fits are refitted at search bound 32, and the statistic is recomputed, also at a flagged point whose statistic was undefined. It is always required then. If a refitted statistic is still undefined, S32 cannot be computed and the label is SATURATED.
- **SD:** flagged points are dropped; a draw needs at least 3 points, and SD needs at least 3 draws. It is required if more than 25% of the 70 points are flagged, or if any used refit is ≥ 31.999 (unresolved).
- **Decision, in order:** UNAVAILABLE, UNDEFINED, SATURATED (a required sensitivity cannot be computed), SATURATION_SENSITIVE (a required sensitivity's label differs), otherwise the label.
- **Expected not to bind:** Run B's fits ranged from 0.095 to 0.56.

**Multiplicity.** Three primaries, each at two-sided 95%, with no family-wise adjustment, stated in advance.

## 6. Secondaries (non-gating; all reported)

- **Per readout epoch E1–E32:** the ten-draw panel p* curve over the ladder, with its argmax and the mean gaps, and each primary's statistic and interval at that epoch alone.
- **The rate pairs at 64 and 96**, per draw, each with a df-9 interval:
  - the mean over E4–E32 of p*(3e-5) minus p* at Run B's rate (3e-4 at 64, 1e-4 at 96);
  - the same difference for the gap at E32;
  - the same difference for the validation NLL at E32.
- **Losses:** training and validation NLL and the gap per width and epoch; the E0 losses; clipping per width.
- **Fits:** every fit with its bound flags (`FITS.csv`), including Run B's own 64 and 96 at their rates; every point (`POINTS.csv`).
- **Records:** the start-up benchmark per width, the ladder decision, and the hashes and sizes of the deleted states.

## 7. What each outcome would mean (fixed now)

**Turn-down.**
- **TURNS_DOWN:** at one rate on these draws, p* falls from 384 to 768. The turn-down of Jane Street's finding (1) appears at this scale, against the memorization prediction for this range. Run B's rise over 128–384 is seen data, so a rise-and-fall shape is not a new pre-registered test.
- **CONTINUES_RISING:** p* still rises up to 768, so there is no turn-down within this ladder. This is what memorization predicts.
- **INCONCLUSIVE:** neither is detected with ten draws. This is not a claim that p* is flat. The power of section 9 is quoted.
- **Under the 512 top,** the reading is limited to 384 → 512, and a turn-down beyond 512 is not tested.

**Dip at one rate.**
- **DIP_PERSISTS:** p* still falls from 64 to 128 at one rate. The Run B dip is not explained by the change of rate alone.
- **NO_DIP_AT_ONE_RATE:** p* rises from 64 to 128 at one rate. The Run B dip coincides with the change of rate. This reading cannot separate the rate itself from under-training at 64 and 96 (section 8).
- **INCONCLUSIVE:** as for the turn-down.

**Memorization.**
- **TRACKS_MEMORIZATION:** at fixed epochs, p* ranks with the train-validation gap across widths. This is an association across widths in one recipe, not a mechanism. On this ladder it also follows from any p* that mostly rises with width (section 8).
- **OPPOSES_MEMORIZATION:** p* ranks against the gap.
- **NO_DETECTED_TRACKING:** no rank association is detected with ten draws.

**Joint reading.** It applies only when no label is UNAVAILABLE, UNDEFINED, SATURATED or SATURATION_SENSITIVE; otherwise each label is read on its own. The table, and MEMORIZATION_PREDICTIONS_MET requiring TRACKS_MEMORIZATION as well, are **protocol additions** to owner decision 20261030-01, put to the owner with the approval request.

| Labels | Reading |
|---|---|
| CONTINUES_RISING, NO_DIP_AT_ONE_RATE, TRACKS_MEMORIZATION | **MEMORIZATION_PREDICTIONS_MET.** Every prediction of the memorization account holds at this scale under this recipe. It is not established as the mechanism: section 8 lists what the same labels would also follow from. |
| TURNS_DOWN, with any dip and memorization label | **JANE_STREET_TURN_DOWN.** The turn-down appears, against the memorization prediction for 384–768. The dip and memorization labels are read on their own. |
| anything else | **NEITHER_PATTERN_COMPLETE.** Each label is read on its own. |

**Required wording** whenever a label is INCONCLUSIVE or NO_DETECTED_TRACKING: it is not detected with ten draws, it is not a claim of absence, and the measured power of section 9 under the noise models is quoted.

## 8. Pre-registered limitations

- **Under-training at 64 and 96** (owner decision 20261030-01, item 3). In Run A, on t00 at 3e-5, both widths reached their lowest validation NLL at E32, the last readout: 5.938 and 5.783. At their selected rates, the lowest values were 5.894 and 5.780 (`AMENDMENT_01.md` §2). At 3e-5 they may memorize less, so their p* may be lower. That gives NO_DIP_AT_ONE_RATE whether the Run B dip was a rate effect or not. The rate pairs (section 6) describe the change at 64 and 96.
- **The memorization primary cannot separate the two hypotheses on this ladder.** At 3e-5 in Run B, the gap rises steeply with width at every epoch (at E16: 0.32, 0.48, 0.65 and 1.05 over 128–384, with draw-to-draw spread of about 5–7%). Its rank across widths is therefore nearly the rank of width itself. The fixtures (section 9) show the consequence: TRACKS_MEMORIZATION for the memorization pattern, but also in 100% of replicates for the Jane Street turn-down pattern at Run B's noise scale, because six of the eight rungs still rise. A turn-down is therefore read from the turn-down primary, not from this one.
- **An extension of seen draws.** R1 cannot test whether the Run B pattern replicates on new articles. Only four fresh WikiText-2 draws remain at N = 1,536.
- **Two runs in one ladder.** 128–384 come from Run B and 64, 96, 512 and 768 from this run, on the same machine and code. GPU arithmetic is not bitwise reproducible across runs, so the rungs are paired in inputs, not in floating-point histories.
- **Scale and regime.** The models are small (0.73–34.7 M parameters, depth 4, a 4,096-token vocabulary). 1,536 sequences × 32 epochs is a memorization regime, unlike Jane Street's few epochs on large corpora. No large-model or scaling claim follows.
- **No held-out test loss.** The test split is the pre-training pool, so generalization is the validation NLL.
- **Fixed epochs** mix capacity with training progress, and one constant-rate trajectory per draw is read at several epochs.
- **The 2.5 GiB guard is seen from inside WSL only.** A Windows GPU app started during a draw is not seen until the next per-draw check (revision 05, section 12), and 768 has little memory margin (section 3).

## 9. Power and false positives of the three primaries (measured; `POWER.json`)

**How the fixtures work.** `reports/natural-text-onerate-preparation-20261030-01/power.py` (3db584d4…) writes `POWER.json` (407f731a…), rerun after review 1 with the memorization designs added at the 512 top. Its power cells equal the reviewed run's; its false-positive cells moved by Monte Carlo noise because the random stream shifted (the reviewed record is kept as `review-01-subject-6682b2dc/POWER-reviewed.json`).
- **Code path:** the designed p* curves go through this analysis's own code (`onerate_analysis.primary`), with ten draws × seven epochs.
- **Replicates:** power uses 400 per cell, and false positives 4,000.
- **Noise:** Gaussian noise of total sd s per fit, of which a share ρ persists across epochs within a draw and width.
- **Gap:** it rises with width and epoch, with 5% relative noise.
- **Slopes:** the designed slopes are in units of p* per doubling of width.

**Noise settings:**

| Setting | Noise |
|---|---|
| **RUNB** | s = 0.015, ρ = 0.85. This is the scale of Run B's p*: its residual sd per width was 0.009–0.018, and the share persisting across epochs 0.65–0.97. It comes from Run B's reported `POINTS.csv`, an already-seen result, used for fixture design only and disclosed here. |
| **WIDE** | s = 0.05, ρ = 0.5 |
| **R05** | s = 0.3, with ρ = 0, 0.5 and 0.8 (revision 05's grid) |

**Context** (seen Run B data): the mean slope over 128–384 was +0.104 per doubling, and over 64–128 at the mixed rates −0.072.

**Power** (share of replicates with the designed label, for designed slopes of 0.01, 0.02, 0.05, 0.1 and 0.2):

| Primary and design | RUNB | WIDE | R05, ρ = 0 | R05, ρ = 0.5 | R05, ρ = 0.8 |
|---|---|---|---|---|---|
| Turn-down, top 768: fall −s beyond 384 → TURNS_DOWN | 32.8, **80.0**, 100, 100, 100% | 9.5, 22.3, 76.0, **100**, 100% | 2.5, 6.2, 13.0, 47.7, **93.8**% | 2.0, 4.8, 5.8, 14.7, 38.0% | 2.8, 3.3, 6.0, 11.7, 29.0% |
| Turn-down, top 512 (two points) → TURNS_DOWN | 7.7, 19.3, **82.3**, 100, 100% | 3.7, 6.2, 21.7, 58.5, **99.0**% | 2.8, 4.0, 4.3, 9.0, 30.7% | 2.8, 1.8, 3.7, 6.5, 11.5% | 3.3, 4.5, 3.7, 5.0, 8.7% |
| Dip: fall −s over 64–128 → DIP_PERSISTS | 30.2, **85.0**, 100, 100, 100% | 7.0, 21.7, 77.5, **100**, 100% | 4.5, 6.2, 12.2, 43.0, **94.8**% | 2.8, 4.3, 5.0, 16.8, 42.5% | 4.0, 3.0, 4.3, 11.7, 25.3% |
| Memorization: p* rises s over the ladder → TRACKS_MEMORIZATION | **100**, 100, 100, 100, 100% | 67.7, **99.8**, 100, 100, 100% | 12.8, 31.0, **96.3**, 100, 100% | 6.8, 12.5, 48.2, **97.3**, 100% | 5.2, 11.3, 37.8, **90.2**, 100% |
| Memorization, top 512 (seven widths) → TRACKS_MEMORIZATION | **100**, 100, 100, 100, 100% | 45.8, **98.5**, 100, 100, 100% | 6.0, 22.5, **83.5**, 100, 100% | 4.5, 10.0, 38.3, **90.5**, 100% | 3.8, 6.8, 26.3, 72.3, **100**% |

The bold entry is the smallest designed slope with at least 80% power.
- **The opposite designs** (a rise beyond 384 → CONTINUES_RISING; a rise over 64–128 → NO_DIP_AT_ONE_RATE) have the same power within Monte Carlo error (`POWER.json`).
- **At Run B's noise scale,** the turn-down and the dip reach 80% power at slopes of 0.02 per doubling. For TURNS_DOWN at the 768 top this is exactly 80.0% (320 of 400; Monte Carlo standard error about 2 points), so 0.02 is a borderline value. Under the 512 top, the turn-down needs 0.05.
- **The memorization primary** reaches 80% at the smallest designed slope, 0.01, at RUNB at both tops (`memo|rising|top512` in `POWER.json`).
- **At revision 05's sd of 0.3,** they need about 0.2 with independent noise, and they have low power under epoch-correlated noise. The noise of p* at 512 and 768 is unknown: in Run B its sd grew with width, from 0.009 at 128 to 0.018 at 384.

**False positives** (designs with no effect in the tested direction):
- **Null designs:**
  - flat beyond 384 (turn-down), and flat over 64–128 (dip);
  - epoch mixing: a rise at E4–E8 and a fall at E16–E32 of the same size, for each of the two;
  - flat p*, and a peak symmetric in rank (memorization).
- **Rates:** the largest rate of any single directional label is **3.12%**, against a nominal 2.5%. The two directional labels together range from 4.2% to 6.0%, against a nominal 5%. The Monte Carlo standard error of a 5% rate at 4,000 replicates is about 0.34 points.
- **Coverage:** every noise setting. The turn-down and memorization designs and nulls run at both tops (768 and the 512 fallback). The dip runs at the 768 top only: its statistic uses 64–128 alone and does not depend on the top.

**The memorization confound** (section 8). With the gap rising with width:
- the Jane Street turn-down design (a rise to 384 and a fall of 0.1 or 0.3 per doubling beyond) reads **TRACKS_MEMORIZATION in 99.75–100%** of replicates at the RUNB and WIDE settings (100% at RUNB);
- so does the dip design.

The memorization primary therefore does not discriminate between the two hypotheses on this ladder. The turn-down primary does.

## 10. Operations, limits and failure policy

**Owner steps,** each run by the owner after approval:
1. Build the activation (revision 02: `reports/natural-text-onerate-revision-02-20261030-01/build_onerate_activation.py`).
   - **Copies:** the sealed source; the registry files from `reports/natural-text-ladder-seed-registry-20261028-01`, checked against Run B's bindings; the partition, re-derived and checked to equal Run B's (5f9f2646…).
   - **Writes:** the approval record, and an enabled one-use authorization that also binds Run B's terminal and inventory.
2. Run `ONERATE_OWNER_RUN.ps1` from the activation: one owner run, about 2.7 h, at most 6 h.
3. After the run ends, run `onerate_analysis.py` from the activation on the run folder, into a new folder.

**Before the claim,** the owner script checks:
- the activation, with a real approval id and fixture false;
- every source file;
- the bound records;
- the corpus manifest, every corpus file and the tokenizer;
- Run B's terminal and inventory (the file-by-file Run B check is the builder's and the worker's);
- at least 3 GiB free on D:;
- revision 05's Windows pre-start check;
- AC power (revision 02, section 11): on battery it refuses.

A refusal claims nothing. The worker then runs the real framework only from the activation's own copy of `onerate_worker.py` (review 1, finding 1), and checks every Run B file it or the analysis reads before its run folder exists.

**Before every draw,** revision 05's Windows nvidia-smi check runs together with an AC power check (revision 02): not ready → recheck for up to 30 minutes → stop. While the worker runs, the power source and the power plan are logged every 5 s outside the before-draw checks (whose readings are in the gate records), and nothing is written to the console.

**Limits:**

| Limit | Value |
|---|---|
| Worker deadline | 21,600 s (the owner script waits 21,900 s and never kills) |
| Benchmark | 900 s |
| Output | 2 GiB and 1,000 files in total; 256 MiB and 128 files per draw |
| Free space on D: | at least 3 GiB at admission; 2 GiB reserve |
| Sampled GPU | ≤ 2.5 GiB |
| Worker RSS | ≤ 4,032 MiB |

**Storage** (owner decision 20261030-01, item 4).
- **Deleted after hashing:** every model state, each recorded by sha256 and size and then deleted:
  - the benchmark's 12 states (643 MB), after the benchmark;
  - each draw's four E0 states (214 MB), after its adaptations;
  - on any failure the worker observes (an exception inside it), the failed draw's states and any benchmark state left, recorded in TERMINAL.json (`states_on_failure`; review 1, finding 3). If the `STATES_DELETED.json` write itself is what fails, the states are already deleted, and their hashes remain in the draw's `PRETRAINED.json`.
- **Not deleted by the worker:** a worker killed from outside (a WSL shutdown, the Linux OOM killer, a host reboot) leaves the active draw's states (up to 214 MB) and no TERMINAL.json. The owner's report lists them, and they are deleted only on the owner's instruction.

  Deleted benchmark states are released from the output ledger, so the receipts count only files that exist (finding 4).
- **Kept:** the per-sequence arrays, the records, the E0 loss arrays of 512 and 768, and the receipts.

**Failure policy.** Fail closed: no retry, resume, width swap, limit increase, replacement draw, seed redraw or re-planning.
- **After the start-up benchmark:** any failure ends the run FAILED, and the primaries are UNAVAILABLE. This includes a GPU guard stop at 768 during a draw, a work cap, a GPU-busy stop and, in revision 02, a power stop.
- **A run without TERMINAL.json** cannot be analysed: `onerate_analysis.py` refuses it, and the primaries are UNAVAILABLE by this protocol, recorded by the owner's report rather than by an analysis.
- **STOPPED_AT_STARTUP:** nothing has been trained, and the next step is an owner decision.
- **Analysis of a FAILED run** is the owner's decision. It would give descriptive secondaries for the completed draws only.

## 11. Revision 02: the final attempt (owner ruling 20261030-03)

**Attempt 1.** Revision 01's run (`work/runs/natural-text-onerate-20261030-01`, TERMINAL.json 0b994ed9…, subject 4ca9833c…) **FAILED in d06** on its per-draw work cap. The outcome-blind failure report (`reports/natural-text-onerate-failure-20261030-01/FAILURE_REPORT.md`) records the cause:
- the charger was unplugged at 15:04:47 local time, 4 min 42 s into d06;
- the ASUS power scheme then switched from Turbo to Silent;
- from 15:08:51 the closed lid put the laptop into Modern Standby;
- d06's 768 adaptation took 2.06 × the d01–d05 mean, and the cap was reached during its 512 adaptation.

The primaries of attempt 1 are UNAVAILABLE (§10). Its outputs, including d01–d05, have never been opened for outcomes (p*, gains, losses); only the operational records listed in FAILURE_REPORT.md were read.

**Owner ruling (verbatim):**
> Decision: option 1. I rule that a fresh run of all ten draws after this power failure is a new attempt, not a retry, under these pre-registered conditions:
> 1. Attempt 1's folders are preserved and never analysed for outcomes, including d01-d05. The new analysis reads only the new run.
> 2. This is the final attempt for this study. If it fails for any reason after a draw folder exists, the study closes as UNAVAILABLE with no further attempt. A stop before any draw folder exists is not counted, as with Run B.
> 3. The final report discloses attempt 1, its cause as recorded in FAILURE_REPORT.md, and that its outputs were never analysed.
> Changes for revision 02: the power gate as you proposed (refuse to start on battery; check AC before every draw, waiting and rechecking up to 30 minutes, then stop), plus a power-source and power-plan log every few seconds during the run. Science, seeds, primaries, analysis and time cap unchanged. Fixture tests, one scoped review of only these changes, then stop for my approval with hashes and commands.
> I commit to keeping the charger plugged in, the lid open and the laptop in Turbo or Performance mode for the whole run.

**What revision 02 changes (operations only):**
- **Folders:** the activation is `work/natural-text-onerate-activation-20261030-02` and the run `work/runs/natural-text-onerate-20261030-02`. Attempt 1's folders are left as they are.
- **Power gate before start** (`power_gate.ps1`, `ONERATE_OWNER_RUN.ps1`). After its GPU check, the owner script reads the Windows power-line status. On battery, or if the status cannot be read, it refuses, writes `PRESTART-REFUSED-k.json` with the power reading, and claims nothing; the same command can be run again once the charger is in. `PRESTART.json` records the power reading.
- **Power gate before every draw.**
  - Each check is revision 05's GPU check followed by a power reading. It is IDLE only if the GPU check is IDLE and the power is AC. Off AC it reads ON_BATTERY or POWER_UNVERIFIED (the power status unreadable); on AC it reads the GPU check's own BUSY or UNVERIFIED.
  - As in revision 05, a check that is not IDLE is rechecked every 60 s for up to 30 minutes from the first check, then the verdict is BUSY_TIMEOUT. Every check, with its power reading, is recorded in the run folder.
  - On BUSY_TIMEOUT the worker stops before the draw. If the last check, at the end of the window, was off AC power, the error is PowerGateError, whose message counts the checks on battery and those with the power status unreadable, and the owner receipt's stop_reason is POWER_NOT_AC_30_MIN. Otherwise it is GpuBusyError, as before; when earlier checks were off AC, its message carries the same counts, and the receipt's gate summary counts the off-AC checks.
- **Power log.** While the worker runs, the owner script reads the power source, the battery percent and the active power scheme every 5 s outside the before-draw checks, and appends each reading to `POWER_LOG.jsonl` in the activation folder. During a before-draw check, including a wait of up to 30 minutes, the readings are those of the checks themselves, about every 60 s, in the gate records. Failed log writes, and readings whose power scheme could not be read, are counted in the receipt; such a reading is not taken as a change of scheme.
  - Every change of source or scheme also goes to `OWNER_PROGRESS.log`.
  - The receipt carries a summary: the readings, the readings off AC, the lowest battery percent, the schemes seen and the changes, with the log's sha256.
  - The log is a record; it does not stop the run.
- **The counting test** (owner decisions 20261029-02 and -03, as for Run B). `TERMINAL.json` and the owner receipt record which draw folders (d01–d10) exist, and whether the run therefore counts as the final attempt.
  - **Any draw folder:** a failure closes the study as UNAVAILABLE. Whether the failed run is analysed descriptively stays the owner's decision (section 10).
  - **No draw folder** (a pre-start refusal, an admission refusal, STOPPED_AT_STARTUP, or a GPU or power stop before d01): the stop is not counted. A new attempt then needs new versioned source, the scoped review and a new approval, with the science unchanged.
  - **TERMINAL.json missing or unreadable:** the draw-folder test alone decides. The owner receipt still records the draw folders, and marks a TERMINAL.json that cannot be hashed or parsed, or that is empty or not an object, as unreadable.
  - **Known limitation (second confirmation of the revision 02 review, C1; accepted, not changed):** if another program holds TERMINAL.json open with write access at the moment the owner script reads it, the receipt marks it unreadable and, if it cannot be parsed, reports FAILED, even when the file says COMPLETE. The worker writes TERMINAL.json once, atomically, and nothing in the design holds it open afterwards. The TERMINAL.json itself, the draw folders (which decide the count) and the analysis, which reads TERMINAL.json directly, are not affected. In that case the receipt is not the authority, and the owner decides from the preserved files.
- **The analysis refuses attempt 1** (condition 1): `onerate_analysis.load` refuses attempt 1's run folder, its TERMINAL.json and its subject before it reads anything else.

**Unchanged:**
- the science (sections 1–9): the draws, seeds, widths, rate, recipe, primaries, labels, reading table, predictions and power;
- the start-up memory fallback, the cap formula (ceil(1.25 × projected + 120 s), from the run's own benchmark), and every limit of section 10;
- the analysis's computations.

The new and changed files are `power_gate.ps1`, `ONERATE_OWNER_RUN.ps1`, `onerate_worker.py`, `onerate_plan.py`, `onerate_analysis.py`, this protocol and the README. Every other file is a byte copy of revision 05 (the sealer checks it).

**What the power gate cannot do.** It checks the power before each draw and logs it during the run. It cannot stop or pause a draw. An unplug during a draw, as in attempt 1, is recorded in the log and the receipt, but it can still slow the draw past its cap. The owner's commitment (charger plugged in, lid open, Turbo or Performance mode) remains the main safeguard.

**Report.** The final report discloses attempt 1, its cause as recorded in FAILURE_REPORT.md, and that its outputs were never analysed.
