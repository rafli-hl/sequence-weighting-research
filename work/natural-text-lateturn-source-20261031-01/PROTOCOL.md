# Late-turn confirmation: protocol

**Status:** frozen 31 Oct 2026 for owner approval, before any run of this study exists. The seeds exist: they were drawn once by the owner under OWNER-20261031-LATETURN-SEEDS-01. No outcome of this study exists.

**Owner decisions:**
- `reports/natural-text-ladder-owner-decisions-20261031-01/OWNER_DECISIONS.md` (the one-rate result and the request for this draft);
- `reports/natural-text-ladder-owner-decisions-20261031-02/OWNER_DECISIONS.md` (the design, items 1–9);
- `reports/natural-text-ladder-owner-decisions-20261031-03/OWNER_DECISIONS.md` (the seed-draw approval; option (a) or (b) on the text-check articles not yet chosen, section 2).

**Review.** Revision after the scoped review 1 (subject d3d7d63a…, `reports/natural-text-lateturn-preparation-20261031-01/review-01-subject-d3d7d63a/`).

**Disclosure.** This study was designed after the one-rate study's result was seen (`reports/natural-text-onerate-result-20261031-01/RESULT.md`).
- **Seen there:** its sealed by-epoch secondaries showed the turn-down over 384–768 as TURNS_DOWN at E24 (−0.0225 per doubling) and at E32 (−0.1748), in 10/10 draws each. The panel argmax was 768 at E4–E16, 512 at E24 and 384 at E32.
- **What this study is:** those are seen secondaries on d01–d10. This study confirms them on four fresh draws, with the protocol frozen before any of its outcomes. The draft and its planning record are in `reports/natural-text-onerate-confirmation-draft-20261031-01/`.

## 1. Questions and the predictions stated in advance

- **P1, turn-down at E32.** On fresh draws, does p\* fall with width over 384–768 at E32?
- **P3, peak shift.** Does the location of the p\* peak move to a smaller width from E8 to E32?
- **P2, turn-down at E24.** The P1 question at E24.

**Predictions** (from the seen secondaries): P1 TURNS_DOWN, P3 SHIFTS_TO_SMALLER_WIDTH, P2 TURNS_DOWN.

## 2. Data: the four fresh draws

**Registry.** `reports/natural-text-lateturn-seed-registry-20261031-01`:
- `REGISTRY.json` b9b6a882…, `EXCLUSIONS.json` f6cd90b6…, `DRAW.json` f0e7298a…;
- policy 1050451f…, frozen before the draw;
- registry source subject 49398ed5…;
- 18 roles: the partition value, the init, weight, pre-training order and adaptation order seeds of f01–f04, and the benchmark seed.

Every role is more than 2,048 away from every value used before in the project.

**Partition.** `lateturn_data.fresh_partition` was sealed with the registry tool before any seed existed. Pin f25cfb6d… (encoded).
- **Used articles:** the seen partition (t00, d01–d10; 443 training articles) is re-derived from the natural-text ladder registry (8ce7d597…). It equals `PARTITION.json` 5f9f2646….
- **Fresh articles:** the 157 unused training articles are shuffled with the new partition value and assigned whole to f01–f04 until each group holds N sequences.
- **Result:** N = 1,536 with no step-down. The groups hold 46, 40, 36 and 34 articles, each giving its first 1,536 sequences; one article is left over.

**Disjointness.**
- **In code** (`lateturn_worker.disjoint`, at the builder and at the worker's admission):
  - the four groups share no article with each other or with t00 and d01–d10;
  - each group holds exactly N distinct sequences, every one inside its own group's articles (mapped through the manifest's article offsets).
- **At the builder** (`FRESH_CHECK.json`): by title row and full-text SHA-256, no fresh article equals any seen training article or any validation or test article. The validation selection and the pre-training pool lie in those two splits. The worker's admission requires every overlap count in it to be zero.
- **Measured on the drawn partition:** zero overlap on every side.

**Disclosed prior use of fresh articles:**
- **The September public-text check** (`work/runs/text-check-v02`) fine-tuned Pythia-70M on paragraphs of 36 training articles. Ten of them are in f01–f04: 0, 7, 10, 26 and 29 in f01; 15 and 27 in f02; 21 in f03; 1 and 6 in f04.
- **The owner's choice is open.** The owner has **not yet chosen** between keeping the frozen rule (option a) and excluding these 10 articles (option b; decision 20261031-03, item 3). This source proceeds under option (a), and the choice is asked for with the approval request.
- **Checks:** the builder refuses unless the selection file has its pinned hash (418b04e9…) and gives exactly these 10 articles.
- **No exposure to the new models:** the confirmation's models are trained from scratch with the study's own tokenizer and never see that check's model or outputs.
- **The study's BPE tokenizer** was trained on every training row, including the fresh articles, before any draw, as for the seen draws.

**Unchanged:**
- the corpus manifest (72daa1e1…) and the tokenizer;
- the pre-training pool (2,048 test-split sequences);
- the validation set (512 validation-split sequences).

## 3. Design

**Widths.** 256, 384, 512 and 768 (owner decisions 20261031-02, item 2), all at **3e-5**. Every width is pre-trained and adapted in this run; nothing is reused from Run B or the one-rate run.
- 384–768 carry P1 and P2.
- 256 makes the expected E32 peak at 384 interior.

**Recipe.** The natural-text recipe is unchanged:
- uniform pre-training: 4 epochs at 3e-4 on the pool;
- weighted adaptation: 32 epochs, batch 16, constant rate, weight decay 0.1, clip 1, log-uniform weights 0.01–10;
- readouts E0–E32;
- signed gains from each width's own E0;
- p\* from `vendor/core.exponent` on [0, 8]. Undefined fits stay undefined.

**Per draw** (`lateturn_worker.stage`):
1. **Inputs:** the draw's sequences, weights and orders from its own seeds.
2. **Each width, widest first** (768, 512, 384, 256): pre-training, then one adaptation, then the width's model state hashed by sha256 and size and deleted before the next width (item 6). At most one state exists at a time.

**Code.** The model, engine, guards, output ledger, benchmark and gates are revision 05's sealed code (byte copies), as in the one-rate study.

## 4. GPU memory and the start-up check (no fallback)

**The rule.** The run's start-up benchmark (revision 05's `text_worker.benchmark`, unchanged) runs one width at a time (256, 384, 512, then 768), each with its own peaks, within 900 s. Every width must complete with its peak sampled device memory within **2.25 GiB**, inclusive. Otherwise the run stops before any training (STOPPED_AT_STARTUP), with the reason recorded.

**Why there is no fallback.** Every primary needs 768.

**The 2.5 GiB guard** applies to the whole run.

**Measured before.** In the one-rate run, 768 peaked at 2.224 GiB (26.2 MiB under the limit), after 64, 96 and 512.

## 5. Time budget

**Formula.** The cap is revision 05's formula on this run's exact per-stage counts (`lateturn_worker.study_cap`):
- every width pre-trained, with its E0 state and arrays;
- every width adapted once;
- the guards.

Cap = ceil(1.25 × projected + 120 s). Four draws are feasible iff 4 × (cap + 60) + 900 ≤ 21,600 s. If the run's own benchmark puts four draws over 6 h, the run stops before any training (STOPPED_AT_STARTUP, FOUR_DRAWS_OVER_6_H).

**Planning** (`CONFIRMATION_PLANNING.json`, calibrated to the one-rate run's measured stages; not measured here):

| Measure | Value |
|---|---|
| Per draw | about 1,090 s |
| Four draws | 1.21 h |
| Stage cap | 1,483 s |
| Worst case | 1.96 h |

## 6. Primaries (owner decisions 20261031-02, items 3–5)

**Points.** Each primary uses **one point per draw**, with no averaging over epochs:

| Primary | Statistic per draw | Interval below 0 | Interval above 0 | Otherwise |
|---|---|---|---|---|
| **P1** | OLS slope of p\* on log2 width over 384, 512, 768 at E32 | TURNS_DOWN | CONTINUES_RISING | INCONCLUSIVE |
| **P3** | S = L(E8) − L(E32), in doublings | SHIFTS_TO_LARGER_WIDTH | SHIFTS_TO_SMALLER_WIDTH | NO_DETECTED_SHIFT |
| **P2** | The P1 statistic at E24 | TURNS_DOWN | CONTINUES_RISING | INCONCLUSIVE |

**The peak location L(e)** is revision 05's sealed `text_analysis.peak_location` on the study ladder, in log2 width:
- the argmax over 256–768, with ties to the smaller width;
- an interior argmax is refined by the vertex of the parabola through it and its two neighbours, clamped to that bracket (the middle rung if not concave);
- **a peak at either end of the ladder is recorded at that rung** (item 3). On the seen draws, the E8 peak was at 768, the top rung, in 10/10.

**When S is a lower bound** (review 1, finding 1). A top-rung argmax shows only that p\*(768) exceeds p\*(512). So:
- **The condition:** S is a **conservative lower bound** on the shift only if every censored curve continues beyond its ladder end in the direction it leaves it (at E8, still rising at 768; at E32, still falling with width at 256).
- **What does not give a bound:** an E8 peak at 256, or an E32 peak at 768, is censored in the direction that can overstate the shift. S is then not a lower bound for those draws, and so the four-draw S and its interval are not a lower bound either.
- **In the reading:** it states the four counts (E8 and E32, top and bottom rung) and which of these cases holds (section 8).

**Degenerate intervals** (review 1, finding 4). If the four draw values are equal to within 1e-9 (sd ≤ 1e-9, the interval tolerance), the interval is that single value and the label follows its sign. This can happen for P3 when every draw's peaks sit at the same rungs. The primary is flagged `degenerate`, and the reading says so.

**Inference.**
- **Unit:** the four draws are the only unit.
- **Labels:** from the two-sided 95% t interval of the four draw values (df 3, t = 3.182446305, tolerance ±1e-9).
- **Missing data:**
  - a primary is UNAVAILABLE if any draw's stage did not complete;
  - it is UNDEFINED if any draw's statistic is undefined (a fit it uses is undefined);
  - there is no replacement draw.

**Saturation** (revision 05's rule, for single-point primaries):
- **Flagging:** a draw is flagged if any fit its statistic uses is ≥ 7.999.
- **S32:** a flagged draw's fits are refitted at bound 32, and the statistic is recomputed. This is always required then.
- **Outcome:**
  - an unresolved refit (≥ 31.999), or an undefined refitted statistic, makes the primary SATURATED;
  - a changed S32 label makes it SATURATION_SENSITIVE.
- **SD** does not apply to single points.
- **Expected not to bind:** the seen fits ranged from 0.052 to 0.560.

## 7. Multiplicity: the fixed sequence (item 4)

**Order.** The primaries are read in the fixed order **P1 → P3 → P2**, each at two-sided 95%.

**What counts as confirmed.** A primary is read as a confirmation only if it gives its predicted label and every earlier primary was confirmed. This keeps the family-wise error at 5%.

**Reporting.** Every label is reported. One that comes after an unconfirmed primary is reported but not read as a confirmation.

**Why this order.** It runs from the strongest seen effect to the weakest, so the weak E24 primary cannot gate the shift.

## 8. Readings (fixed now; `lateturn_analysis.readings` prints them)

**Always (item 9):**

> The late-epoch pattern is tested at E24 and E32, long after the best validation loss of 384-768, which was at E4 on the seen draws d01-d10: a heavily overfit regime, unlike Jane Street's 3-epoch setting. A confirmation supports the pattern in this regime only.

**P1:**
- **TURNS_DOWN:** P1 confirmed: at E32, p\* falls with width over 384–768 on the four fresh draws.
- **CONTINUES_RISING:** P1 not confirmed: at E32, p\* rises with width over 384–768 on the fresh draws, contrary to the seen secondary.
- **INCONCLUSIVE:** P1 not confirmed: no fall or rise is detected at E32 with four draws. This is not a claim of absence. The power stated in advance (section 10) is quoted.

**P3:**
- **SHIFTS_TO_SMALLER_WIDTH:** P3 confirmed: the peak location moves to a smaller width from E8 to E32.
- **SHIFTS_TO_LARGER_WIDTH:** P3 not confirmed: the peak moves to a larger width.
- **NO_DETECTED_SHIFT:** not detected with four draws; not a claim of absence; the power is quoted.
- **In every case, the censoring sentence with the measured counts** (`lateturn_analysis.censoring_text`). It opens: "A peak at a ladder end is recorded at that rung. At E8 the peak was at the top rung (768) in a and at the bottom rung (256) in b of 4 draws; at E32, at the top rung in c and at the bottom rung in d." It then gives one of three endings:
  - **No ladder-end peak:** S is not censored.
  - **Only an E8 top-rung or E32 bottom-rung peak:** S is a conservative lower bound on the shift, provided each censored curve continues beyond its ladder end in the direction it leaves it (at E8, still rising at 768; at E32, still falling with width at 256). A peak above 768 cannot be tested on the 4 GiB card.
  - **An E8 peak at 256 or an E32 peak at 768:** S is not a lower bound for those draws, and the four-draw S and its interval are therefore not a lower bound on the shift.

**P2:** as for P1, at E24.

**Labels that are not read:**
- **UNAVAILABLE, UNDEFINED, SATURATED or SATURATION_SENSITIVE:** the primary is not read, and no later primary is read as a confirmation.
- **After an unconfirmed primary:** the label is reported but not read as a confirmation. For INCONCLUSIVE or NO_DETECTED_SHIFT, the text still says that the effect is not detected with four draws, that this is not a claim of absence, and quotes the power stated in advance (review 1, finding 3).

**A degenerate interval** (section 6) adds: "All four draw values are equal to within 1e-9 (sd <= 1e-9), so the interval is that single value and the label follows its sign."

**Always:** the disclosure of the September text check (section 2).

**Mechanism.** No reading claims a mechanism. A confirmation would be an association across widths, in one recipe, on one corpus, at this scale.

## 9. Secondaries (non-gating; all reported)

- **Per readout epoch E1–E32:**
  - the panel p\* curve and gap;
  - the panel and per-draw argmax;
  - the turn statistic with its df-3 interval;
  - the location L per draw and its mean.
- **For comparison only:** the one-rate study's epoch-averaged turn-down (the mean over E4–E32 of the 384–768 slope) on the fresh draws.
- **Losses, per width and epoch:**
  - training and validation NLL, and the gap;
  - the E0 losses;
  - the epoch of the lowest validation NLL (which checks the overfit-regime statement on fresh data);
  - clipping.
- **Fits:** every fit with its bound flags (`FITS.csv`); every point (`POINTS.csv`).
- **Records:** the start-up benchmark per width; the hashes and sizes of every deleted state.

## 10. Power stated in advance (`CONFIRMATION_PLANNING.json`)

**Seen per-draw values** (d01–d10):

| Primary | Mean | sd |
|---|---|---|
| P1 | −0.1748 | 0.0173 |
| P3 | +0.9056 doublings | 0.0259 |
| P2 | −0.0225 | 0.0124 |

**Probability of the predicted label with four draws at 95%:**

| Primary | At the seen effect | Conservative | Halved |
|---|---|---|---|
| P1 | >0.9999 | >0.9999 | >0.9999 |
| P3 | >0.9999 | >0.9999 | >0.9999 |
| **P2** | **0.678** | **0.157** | **0.247** |

- **Conservative:** the mean at the seen 95% bound nearest 0, and the sd at its upper one-sided 95% chi-square bound.
- **Halved:** the seen mean divided by 2.
- **All three confirmed in sequence:** 0.679 at the seen effect, 0.157 conservative, 0.249 halved.
- **P2 is underpowered** (item 5). An INCONCLUSIVE P2 is weak evidence either way. The effects were chosen after being seen and may be optimistic.
- **P3's Gaussian power** does not cover one structural risk: a fresh draw whose E8 peak is below 768, or whose E32 peak is at 512.

## 11. Pre-registered limitations

- **Sample:** four draws (df 3), from one corpus.
- **Regime:** a heavily overfit regime. Fixed epochs mix capacity with training progress.
- **Censoring:** the E8 location is expected to be censored at 768. S is a lower bound only under the condition of section 6, and a peak above 768 cannot be placed.
- **Shared data:** the pool, the validation set and the tokenizer are the seen draws'. Ten fresh articles were used by the September text check.
- **Scale:** small models (5.3–34.7 M parameters, depth 4, a 4,096-token vocabulary), 1,536 sequences × 32 epochs. No large-model or scaling claim follows.
- **No held-out test loss:** the test split is the pre-training pool.
- **The 2.5 GiB guard is seen from inside WSL only.** A Windows GPU app started during a draw is not seen until the next per-draw check.
- **Power during a draw:** the gate checks power only before each draw. An unplug during a draw can still exceed its cap.
- **Corpus exhausted:** the study uses up the WikiText-2 training split at this N.

## 12. Operations, limits and failure policy

**Owner steps,** each run by the owner after approval:
1. **Build the activation:** `reports/natural-text-lateturn-preparation-20261031-01/build_lateturn_activation.py`. It copies the sealed source, the registry files and the seen registry. It re-derives the partition and checks disjointness, then writes `FRESH_CHECK.json`, the approval record and an enabled one-use authorization.
2. **The run:** `LATETURN_OWNER_RUN.ps1` from the activation; one owner run, about 1.5 h, at most 6 h.
3. **The analysis:** after the run ends, `lateturn_analysis.py` from the activation on the run folder, into a new folder. It refuses a run with a FIXTURE approval or in any folder other than the plan's run folder (review 1, finding 7).

**Before the claim,** the owner script checks:
- the activation (a real approval id, fixture false);
- every source file;
- the bound registry, seen registry, partition, fresh check and approval records;
- the corpus manifest, every corpus file and the tokenizer;
- at least 3 GiB free on D:;
- revision 05's Windows pre-start GPU check;
- AC power: on battery it refuses.

A refusal claims nothing.

**At admission,** the worker runs the real framework only from the activation's own copy. Before its run folder exists, it re-derives:
- the registry;
- the seen and fresh partitions;
- the disjointness.

**Before every draw:** the Windows GPU check and an AC power check. If not ready, it rechecks for up to 30 minutes, then stops. The power source and plan are logged every 5 s.

**Limits:**

| Limit | Value |
|---|---|
| Worker deadline | 21,600 s (the owner script waits 21,900 s and never kills) |
| Benchmark | 900 s |
| Output | 2 GiB and 1,000 files in total; 256 MiB and 128 files per draw |
| Free space on D: | at least 3 GiB at admission; 2 GiB reserve |
| Sampled GPU | ≤ 2.5 GiB |
| Worker RSS | ≤ 4,032 MiB |

**Storage:**
- **Deleted after hashing:** the benchmark's 12 states (about 0.81 GB) after the benchmark, and each width's state after its adaptation. At most 139 MB of states exist during a draw.
- **On failure:** on any failure the worker observes, the active draw's state and any benchmark state left are hashed, deleted and recorded in TERMINAL.json.
- **A state that cannot be deleted:** the error is recorded (`STATES_DELETED.json` and the receipt) and is not raised. The state then counts against the 256 MiB per-draw quota, so a later width may stop the run (fail closed).
- **Kept:** the arrays, records, E0 losses and receipts, about 0.1 MB per trajectory.

**TERMINAL.json** is written through the output ledger. If that write fails (a quota or an inventory error), it is written directly as a last resort, flagged `terminal_outside_ledger` (review 1, finding 8). Only if both writes fail is it missing; the owner receipt then still records the draw folders.

**Documented limitation** (confirmation of review 1, new finding 3; for the owner to accept). The `terminal_outside_ledger` flag, and the missing inventory that goes with it, are recorded in TERMINAL.json only, not in the owner receipt or ANALYSIS.json. A run whose last ledger write failed can therefore read COMPLETE in both. The result report reads TERMINAL.json and states the flag.

**Failure policy (item 7, as revision 02).** Fail closed: no retry, resume, width swap, limit increase, replacement draw, seed redraw or re-planning.
- **A run that creates any draw folder** is the study's only attempt. A failure after that closes the study UNAVAILABLE.
- **A stop before any draw folder exists** (a refusal, or STOPPED_AT_STARTUP) is not counted. The next step is then an owner decision.
- **A FAILED run** is analysed only on the owner's decision. It would give descriptive secondaries for the completed draws only.
