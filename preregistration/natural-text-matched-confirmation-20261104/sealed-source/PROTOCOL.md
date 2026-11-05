# Matched-progress confirmation (N7) on fresh WikiText-103 draws: protocol

**Status:** frozen 4 Nov 2026, before any seed of this study was drawn and before any data of this study exists. A pin-only revision sets the registry and partition pins after the owner-run seed draw (section 12), and `SOURCE_SUBJECT.json` says whether they are set. This is revision 2, of the same day, under the owner decisions below. Revision 1 (subject `7063a650…`) is kept in `reports/natural-text-matched-preparation-20261104-01/revision-01-7063a650/`.

**Owner instruction:** "New study: matched-progress confirmation (N7)" of 4 Nov 2026; recorded in `reports/natural-text-matched-preparation-20261104-01/REPORT.md`. **Owner decisions:** `reports/natural-text-ladder-owner-decisions-20261104-02/OWNER_DECISIONS.md`.

**Disclosure.** This hypothesis comes from a post-hoc reanalysis of N6 (`reports/adversarial-review-20261104-01/RECOMPUTE_MATCHED.json`; `reports/adversarial-review-response-20261104-01/RESPONSE.md`, sections 4 and 5). At 1e-4 after 3 epochs, p\* at 512 exceeded 768 when 768 was read at the training NLL 512 reaches at E3 (+0.0132 [+0.0106, +0.0158], 6/6), although at fixed updates 768 was higher (−0.0050 [−0.0090, −0.0010], N6's RATE_DEPENDENT). That figure was interpolated between E2 and E3. So N6 and its draws cannot confirm it.

## 1. The question

On draws never used, with readouts dense enough to replace most of the interpolation: at 1e-4, is p\* at 512 at E3 above p\* at 768 read at the training NLL that 512 reaches at E3?

## 2. Data

**Corpus:** the WikiText-103 corpus of the few-epoch study (manifest `be911db7…`), read-only. N = 16,384 sequences per draw. The validation set, the pre-training pool and the tokenizer are those of N6.

**Fresh articles** (`matched_data.fresh_pool`; policy `reports/natural-text-matched-seed-registry-20261104-01/SEED_REGISTRY_POLICY.md`). From the eligible articles:
- every article N5 assigned to t00–d10 and every article N6 assigned to c01–c06 is out, each partition re-derived and required to equal its pin;
- text duplicates of assigned articles are out;
- every copy of a text repeated inside the pool is out.

N6's records leave 16,451 of its fresh articles unused, so that is the size expected here; the draw records the real count. N1, N3, N4 and the first attempts of N1 and N3 drew WikiText-2 articles, which the corpus manifest excludes. S is synthetic.

**Partition** (`matched_data.partition`): the fresh indices are sorted, shuffled with the registry's `partition_seed`, and assigned whole to m01, …, m06 until each holds at least 16,384 sequences; each group uses its first 16,384.

**Seeds:** a new registry, `reports/natural-text-matched-seed-registry-20261104-01`, 26 values, drawn once by the owner. It excludes every earlier registry's values and exclusion lists, S's, N1's and N3's (and so their first attempts'), N4's, N5's and N6's, and a census of saved JSON records that never enters a folder whose path holds `work/runs`.

**No tuning draw.** Both rates are already fixed (section 3).

## 3. Design

**Unchanged from N6:** depth 4, 4 heads, context 128, 4,096-token vocabulary; per group, each width pre-trained uniformly for 4 epochs at 3e-4 (clip 5) on the pool, giving E0; weighted adaptation (R, log-uniform weights 0.01–10) at a constant rate, batch 16, weight decay 0.1, clip 1; the weights used exactly as drawn, with at most n / 1,024 tied values; signed gains from each width's own E0; p\* from the sealed estimator on [0, 8]. Undefined fits stay undefined.

**Length and readouts:** 3.5 epochs, 3,584 updates. Readouts at E0 (each width's pre-trained state) and E0.25, E0.5, E1, E2, E2.25, E2.5, E2.75, E3, E3.25, E3.5 (after updates 256, 512, 1,024, 2,048, 2,304, 2,560, 2,816, 3,072, 3,328, 3,584), with training and validation per-sequence losses at each. Batch orders are drawn per epoch, as in N6, and the fourth is used up to E3.5.

**The arms per draw:**

| Width | 1e-4 (primary) | 3e-4 (secondary) |
|---|---|---|
| 768 | yes | yes |
| 512 | yes | yes |

**The decision on the 3e-4 arms: included.** The owner's rule keeps them only if the projected time per run stays within the 6-hour cap with the usual margin. With them, a run of three draws has a forecast of 2.56 h on the Windows clock, a stage cap of 3,483 s, 1.24 times its forecast (N6: 1.25), and a worst case of 3.70 h on the worker's clock, or 4.70 h with every gate at its full wait (section 10). The worker still stops a run before any training if its own start-up benchmark puts it over the formula.

- **Pairing.** A width's arms share one E0, and every arm of a draw shares its tokens, weights and batch order.
- **Per stage, widest first:** pre-training, the width's arms, then its model state hashed and deleted. At most one state exists at a time.
- **The rates are not chosen again.** 3e-4 is the rate the few-epoch study selected on t00, and 1e-4 is 768's lowest validation NLL on t00 among the five rates tried (`LR_SELECTION.json`, `fa760ba0…`, pinned copy in `reports/natural-text-peak-analysis-approval-20261103-01/pinned-records/`). p\* enters neither.
- **Runs:** M1 (m01–m03) and M2 (m04–m06), because six draws in one run do not fit (section 10). M2 is admitted on M1's terminal under the same source subject and inputs: COMPLETE, or FAILED with at least 2 completed draws (section 12).

## 4. The matching rule

Per draw, the target is the value of 512 at E3: its training NLL (the per-draw `train` field as defined in N6), its gap (validation NLL minus training NLL) or its validation NLL.

768's p\* is read along its own readouts E2, E2.25, E2.5, E2.75, E3, E3.25, E3.5, by linear interpolation between the two bracketing readouts. Fixed in advance, where a path is not monotone or a value is tied:
- the reading comes from the **first interval in readout order** whose two values hold the target, and the number of intervals holding it is reported;
- a target equal to a readout's value is held by the first interval that contains it;
- if an interval's two values are equal and equal the target, the reading is at its earlier readout.

**If the target lies outside 768's E2–E3.5 path, that draw is UNAVAILABLE for that statistic.** A draw whose bracketing p\* is undefined, or whose p\* for 512 at E3 is undefined, is also unavailable for it, with its reason reported. Which readouts bracket each draw is reported, in `ANALYSIS.json` and `MATCHED.csv`.

## 5. The primary

**P1 (1e-4):** D4m_train = p\*(512, E3) − p\*(768, matched on training NLL), per draw. A t interval over the available draws, df = draws − 1, 95%.

| Label | Rule |
|---|---|
| **REVERSAL_CONFIRMED** | The interval is entirely above 0 |
| **NOT_REVERSED** | The interval is entirely below 0 |
| **INCONCLUSIVE** | Anything else |
| **UNAVAILABLE** | Fewer than 5 draws available |

## 6. The fixed sequence

P1 → S1 → S3 → S4 → S5 → S2, the owner's order. **Each step is read as a confirmation only while every earlier step is confirmed.** That holds the chance of any false confirmation over the six at about 2.5%, one tail of each 95% interval, and at about 5% if a false result on the other side counts too (simulated in `reports/natural-text-matched-preparation-20261104-01/review-02/REVIEW_FINDINGS.md`: 0.0254 and 0.0505). There is one exception on that side: if S2 is truly 0 and every earlier step is certain, the draws S2 drops push its kept mean down, so CONTRARY at S2 is likelier than that. A later step is still computed and reported, and is not read as a confirmation.

| Step | Statistic | Confirmed if the interval is |
|---|---|---|
| **P1** | D4m_train: 512 − 768 at 1e-4, matched on training NLL | entirely above 0 |
| **S1** | D4m on the gap | entirely above 0 |
| **S3** | Fixed-update D4 at E3: p\*(512, E3) − p\*(768, E3) at 1e-4. Expected negative, which replicates N6's RATE_DEPENDENT | entirely below 0 |
| **S4** | D2m_train: 512 − 768 at 3e-4, matched on training NLL | entirely above 0 |
| **S5** | Fixed-update D2 at E3, at 3e-4 | entirely above 0 |
| **S2** | D4m on validation NLL | entirely above 0 |

Secondary labels: **CONFIRMED** on the expected side, **CONTRARY** on the other side, **INCONCLUSIVE** if the interval spans 0, and **UNAVAILABLE** with fewer than 5 draws.

**Stated in advance: S2 may be unavailable. It comes last, so that stops nothing.** On N6's six draws, 768 reached 512's validation NLL before E2 in two draws (E1.94 in c01, E1.99 in c04). Under the rule above such a draw is unavailable for S2, **so on N6's own draws S2 has 4 of 6.** From the same six positions, the chance that S2 has at least 5 draws is 73% from a normal fitted to them and treated as known, 65% with a noninformative prior on that normal, 38% with a Jeffreys prior on the count of 2 outside, and 35% from the observed fraction. If it does not, S2 is UNAVAILABLE, and no other step is affected.

## 7. Readings (fixed now; `matched_analysis.readings` prints them)

| Outcome | Reading |
|---|---|
| **REVERSAL_CONFIRMED, with S3 reached and CONFIRMED** | At 1e-4, p\* at 512 at E3 is above p\* at 768 read at the training NLL 512 reaches at E3. At fixed updates at E3 on these draws, 768 is above 512, so on these draws the comparison axis reverses the 512–768 ordering at 1e-4 |
| **REVERSAL_CONFIRMED, with S3 reached and INCONCLUSIVE or unreadable** | The same first sentence. At fixed updates at E3 on these draws, 768 is not shown above 512, so on these draws the ordering is not shown to reverse: 512 is above 768 at matched training NLL, and the fixed-update order is not established here |
| **REVERSAL_CONFIRMED, with S3 reached and CONTRARY** | The same first sentence. At fixed updates at E3 on these draws, 512 is above 768 as well, so on these draws the ordering does not reverse: 512 is above 768 on both axes, which is contrary to the fixed-update order N6 found |
| **REVERSAL_CONFIRMED, with the sequence stopped before S3,** because S1 is not confirmed | The same first sentence. The fixed sequence stopped before S3, so the fixed-update contrast at E3 is reported and not read here, and this study does not confirm that the ordering reverses on these draws: 512 is above 768 at matched training NLL, and N6's fixed-update order is not confirmed on them |
| **Any of those adds** | This does not show a capacity mechanism, and nothing about Jane Street's scale follows. Matching on training loss also removes any faster learning of the wider model, so neither axis is privileged |
| **NOT_REVERSED** | At 1e-4, p\* at 512 at E3 is below p\* at 768 read at that training NLL. N6's post-hoc figure, +0.0132, is not reproduced on these draws: matching on training NLL does not put 512 above 768 here |
| **INCONCLUSIVE** | The interval includes 0. This is not a claim of absence. The power stated in advance follows |
| **UNAVAILABLE** | Fewer than 5 draws have a reading. It is not read, and it is not evidence either way |
| **A run did not complete, and P1 has fewer than 5 available draws** | A run did not complete, and P1 has fewer than 5 available draws, so the completed draws are not read and the study closes UNAVAILABLE. This is not evidence either way |
| **S1 or S2 CONFIRMED** | At 1e-4, p\* at 512 at E3 is above p\* at 768 read at the gap, or at the validation NLL, that 512 reaches at E3 |
| **S3 CONFIRMED** | S3 replicates N6's fixed-budget result (RATE_DEPENDENT): after 3,072 updates at 1e-4, 768 is above 512. This is a fixed-budget fact. It does not say that the fall from 512 to 768 depends on the rate |
| **S4 CONFIRMED** | At 3e-4, p\* at 512 at E3 is above p\* at 768 read at the training NLL 512 reaches at E3 |
| **S5 CONFIRMED** | At 3e-4, after 3,072 updates, 512 is above 768, as in N6. This is a fixed-budget fact |
| **A secondary CONTRARY** | The interval lies on the other side of 0 from the one expected. The sequence stops here, unless this is S2, the last step |
| **A secondary INCONCLUSIVE** | The interval includes 0. This is not a claim of absence. The sequence stops here, unless this is S2, the last step |
| **NOT_READ** | The sequence did not reach this step. The side of its interval is reported, and it is not read as a confirmation |

**The label name.** REVERSAL_CONFIRMED needs only P1. Whether the ordering reverses on these draws also needs S3, confirmed in the sequence, which is why the reading has these forms. The owner's sentence, that REVERSAL_CONFIRMED shows the comparison axis reverses the ordering, is what the first form says; the others say why it cannot be said on those draws.

**The printed labels.** A step the sequence does not reach has the label NOT_READ, whatever its interval, so the word CONFIRMED never appears beside a step that is not read. Each statistic's `status` and `decision.sides` keep the side of its interval.

**Every set of readings also says** on how many draws P1 has a reading, which draws have none and why, how many draws lack a reading of each statistic, by reason, and whether a run ended without completing.

**No reading claims a mechanism.** A reading is about 512 and 768, at two rates, on these draws.

## 8. Always reported, not gating; NOT_OVERFIT, missing data and saturation

**For every statistic, even an unavailable one, unless a failed run closes the analysis (below):** sign counts, the exact two-sided sign test, and leave-one-draw-out intervals when at least 4 draws have a value. **For every matched statistic:** the per-draw bracket, weight and read position. **For the whole analysis:** the largest difference between any record's losses and the mean of the array block the fits use; above 0.001 the readings open with a warning, and the owner decides what follows before anything is read. None of these gates a label.

**NOT_OVERFIT (manipulation check).** Per arm, per draw, Δ = validation NLL at E3 minus at E2. The interval of the mean Δ: below 0 gives NOT_OVERFIT, above 0 OVERFIT, otherwise PLATEAU. It does not gate. If an arm a reading uses fails, the label stands and its reading is prefixed. **No remedy is allowed:** no re-run, data increase or replacement draw.

**Missing data:** a statistic with fewer than 5 available draws is UNAVAILABLE. With 5 it is read at df 4. A draw with an undefined fit is unavailable for each statistic that uses that fit, and the count of draws without a reading is always reported, per statistic and by reason: undefined fit, target outside the path, draw missing.

**If either run did not complete,** the completed draws are read only if P1 has at least 5 available draws. The owner's sentence names Run M2; a failed Run M1 that admits Run M2 reaches the same question, so the same rule applies. Otherwise nothing is read: the analysis reports availability and its counts, and no value, interval, side, loss or fit, and the study closes UNAVAILABLE. If every run completed, P1 being unavailable stops the sequence, and the later steps are reported as NOT_READ with the sides of their intervals.

**Saturation (the few-epoch rule):** a draw is flagged if a fit its statistic uses is ≥ 7.999, and those fits are refitted at bound 32. An unresolved refit makes the statistic SATURATED, and a side that differs at bound 32 makes it SATURATION_SENSITIVE. Neither is read. N6 flagged no draw.

## 9. Descriptive (non-gating; no multiplicity adjustment)

By readout, the fixed-update 512 − 768 contrast at each rate, and the panel p\*, gap and losses per arm; the rate effects at each width at E3; losses and clipping per arm, E0 per width, and every fit with its bound flags.

## 10. Power, time, disk and memory (forecasts)

All in `reports/natural-text-matched-preparation-20261104-01/MATCHED_PLANNING.json`, from saved records.

**Power of P1,** from N6's spread (sd 0.0025) and the effect it was seen at (+0.0132). That effect selected this hypothesis, so it is likely flattering.

| Draws available | At +0.0132 | At half of it | At +0.0132, sd at its upper 95% limit | At half of it, sd at its upper limit |
|---|---|---|---|---|
| 6 | >0.999 | 0.999 | 0.998 | 0.703 |
| 5 | >0.999 | 0.990 | 0.985 | 0.576 |

**The power table for this order,** from a rough joint simulation on N6's six draws. Each cell gives the chance at the seen effect, then at half of it, with the same spread. *Alone* is the chance of the expected side, ignoring S2's availability. *Read* is the chance that every earlier step is confirmed. *Confirmed* adds this step's own interval.

| Step | Alone, six draws | Alone, five draws | Read in the sequence | Confirmed in the sequence |
|---|---|---|---|---|
| **P1** | >0.999, 0.999 | >0.999, 0.990 | >0.999, >0.999 | >0.999, 0.999 |
| **S1** | >0.999, 0.984 | >0.999, 0.939 | >0.999, 0.999 | >0.999, 0.983 |
| **S3** | 0.733, 0.259 | 0.606, 0.208 | >0.999, 0.983 | 0.734, 0.253 |
| **S4** | >0.999, >0.999 | >0.999, 0.999 | 0.734, 0.253 | 0.734, 0.253 |
| **S5** | >0.999, >0.999 | >0.999, 0.998 | 0.734, 0.253 | 0.734, 0.253 |
| **S2** | >0.999, 0.951 | >0.999, 0.873 | 0.734, 0.253 | 0.522, 0.148 |

S2's figures use the 73% of section 6. At its other estimates, S2's confirmed figure at the seen effect becomes 0.46, 0.27 and 0.25, and no other step changes. S3 is the step that limits S4, S5 and S2. Six points give a poor covariance, so these are a guide only.

**What the 3e-4 arms cost.** They add 1.17 h to a run's forecast (2.56 h against 1.39 h), and they are what forces two runs: with the 1e-4 arms alone, six draws fit in one run (forecast 2.71 h; worst case 14,604 s). The owner's rule keeps them, because they fit. Their confirmatory steps are read only as far as the sequence reaches them, as above.

**Time** (each run computes its own cap from its own start-up benchmark):

| One run of three draws, with the 3e-4 arms | Worker clock | Windows clock |
|---|---|---|
| Forecast | 2.40 h | 2.56 h |
| Worst case: 900 s benchmark, three stages at the 3,483 s cap, one full gate wait | 3.70 h | 4.00 h |
| Worst case with every gate at its full 30 minutes | 4.70 h | 5.08 h |

The stage cap comes from a projection of 2,690 s, recovered from the saved projections of N6's layouts, because Run A's benchmark is under `work/runs/` and was not read. The forecast comes from N5's measured wall times; that model gives N6's stage as 2,278 s, against 2,170–2,294 s measured, and the projection gives N6's layout as 2,176 s. **Six draws in one run do not fit:** with one gate wait, 23,958 s against 21,600 s. A run whose own benchmark came in about 1.82 times slower would still be admitted; that is the largest cap three stages allow. **The owner script's wait is the nearer limit:** from a benchmark about 1.69 times slower (1.66 times at N6's clock), with every stage at its cap, a run would outlast the script's 21,900 s wait, and its receipt would read EXIT_UNOBSERVED_NO_KILL. No past stage came near its cap.

The Windows figures use the clock measured on Run A, 1.081. N6 measured 1.093 and 1.092; at 1.093 they become 2.62 h, 4.05 h and 5.14 h. No decision changes.

The formula is the few-epoch worker's: cap = ceil(1.25 × projected + 120 s); a run stops before any training unless stages × (cap + 60) + 900 + 1,800 ≤ 21,600 s.

**Disk:** run admission requires 3 GiB free, with a 2 GiB reserve. A run keeps about 10 MB (3.3 MB per draw). Start-up benchmark states are about 620 MB, transient. D: had 3.43 GiB free when this was written, so Run M1 is admitted with about 0.40 GiB over the requirement if nothing else is written.

**GPU memory:** every width must peak at or below 2.25 GiB at start-up, or the run stops before training (not counted). 768 measured 2.2244 GiB in N5's Run A. The 2.5 GiB guard applies throughout.

**Gates** (unchanged): before every stage, the Windows GPU check (mean utilization at most 12%) and an AC power check, rechecked for up to 30 minutes; a refusal on battery; a power log every 5 s.

## 11. Limitations stated in advance

- **A mechanism:** no result here says why p\* orders as it does.
- **The axis:** matching on training loss also removes any faster learning of the wider model. Neither axis is privileged, and this study does not choose between them.
- **Jane Street's scale:** depth 4, 16.9 M and 34.7 M parameters, one corpus family. Nothing about Jane Street's scale follows, and this is not their setting: a constant rate with no horizon-tied schedule, and small models adapted from a short uniform pre-training.
- **Interpolation:** p\* between readouts is still linear, now over a quarter of an epoch.
- **Equal training NLL is not equal gain:** p\* is fit to gains from each width's own E0, and 768 starts higher. On N6's panel, E0 is 5.6037 against 5.5509, so at the target 768 has gained 1.337 against 1.285. Matching on gain would read 768 near E2.14, not E2.36, and raise P1 by about 0.006. So this axis leans against a reversal, and "matched progress" here means matched training NLL, not matched gain.
- **Normality:** the t intervals assume normal draws, untested at five or six draws. The sign test is reported beside them.
- **A draw lost to a failure** in either run is not a random draw. The readings say how many draws P1 was read on, and which run failed.
- **Selection by matching:** a draw whose target lies outside the path is unavailable, and such draws are not a random subset.
- **Other rates:** the rates are the two tested in N6. The best rate for 768 is not located.
- **Shared items:** consistency across the pool, the tokenizer and the recipe is not tested. After the same pre-training, 768 starts from a higher E0 validation NLL than 512.
- **Independence:** draws are treated as independent in every interval.
- **No held-out test loss:** the test split is the pre-training pool.
- **Pre-registration:** the public registration fixes the protocol before any data exists, and is the first in this project to do so. The rest of its verification is still by the owner and the assistant.

## 12. Operations and failure policy

**The steps, in the owner's order (decision 20261104-02, item 4). Each is approved, and run by the owner unless it says otherwise:**
1. **The seed draw:** `run_seed_draw.py` in `reports/natural-text-matched-seed-package-20261104-01`, once. Under `work/runs/` it reads the corpus manifest by its exact path and nothing else, and an audit hook stops it otherwise. It writes the registry, the partition and the post-draw checks and disclosure. If the post-draw step is interrupted the draw stands, and the script's disclosure-only mode runs that step once.
2. **A pin-only revision and a new seal,** by the assistant, with `apply_matched_pins.py`: the pins in `matched_plan.py`, the README's status, and the builder and the real-engine check pinned to the new subject. The sealer refuses anything else. No scientific field changes.
3. **The real-engine check:** real Torch, CUDA and WSL on synthetic inputs, with no study data. On CPU, the seeds of all six groups give their real weights and batch orders, on synthetic tokens. On the GPU, a smoke test of the sealed stage code on two small widths with two rates, on synthetic tokens and test seeds. It opens nothing under `work/runs/`, writes only to scratch, reads no loss, and is not a stage of any run. Its two receipts are then copied into `reports/natural-text-matched-engine-check-result-20261104-01`, where the builder looks.
4. **A scoped review,** in a fresh context, of what has changed.
5. **The public registration** on GitHub, merged, with its commit hash recorded. It holds the sealed source with `SOURCE_SUBJECT.json`, the seed policy, the draw's `REGISTRY.json`, `EXCLUSIONS.json`, `DRAW.json` and `PARTITION.json`, so that anyone can re-derive the registry, and the hashes of the real-engine check's receipts. No activation comes before this. The builder refuses unless the recorded registration is of the subject it is pinned to and names the receipts it finds, so **a subject changed after the registration needs a new check and a new registration.**
6. **Run M1, then Run M2:** each from an activation built by `build_matched_activation.py` and run with `MATCHED_OWNER_RUN.ps1`, and each checked afterwards with `verify_matched_run.py`.
7. **The analysis:** `matched_analysis.py` on M1 and M2, once both have ended with a terminal, with the results report's layout frozen first.

**Counting rule:**
- a run that creates any stage folder is the only attempt of its stages;
- a stop before any stage folder exists (a refusal, STOPPED_AT_STARTUP) is not counted, and the next step is an owner decision;
- a nonfinite update is a failure;
- **one source subject:** M1 and M2 must run under the same sealed source subject.

**A stop before any stage folder exists,** whatever its status (STOPPED_AT_STARTUP, or FAILED at the gate before the run's first draw), is not counted and is not analysed: `matched_analysis.load` refuses such a run. The next step is the owner's decision. A re-run would need a new run folder, and so a new revision, a new real-engine check and a new registration.

**After a failure, once a stage folder exists:**
- **Run M1 FAILED with at least 2 completed draws:** Run M2 is admitted. The rule is mechanical. It counts the completed draws in the terminal's stage records, by name and status, and the builder requires the receipts on disk to agree. Nothing else about the run is weighed, and no outcome field is read. With m01 and m02 complete, the study can then have 5 draws at most, so one more loss makes P1 UNAVAILABLE.
- **Run M1 FAILED with fewer than 2 completed draws:** M2 cannot run, the analysis is not run, and the study closes UNAVAILABLE from the terminal and the owner receipt.
- **Run M2 FAILED:** the analysis runs, and section 8 says what it reads.

**A run that leaves no terminal,** because WSL died or the machine crashed, counts for nothing, whatever receipts are on disk. A draw counts only through a terminal's stage records. Run M2 is not admitted after such a Run M1, the analysis is not run, and the study closes UNAVAILABLE.

**Checks that read `work/runs/`.** The assistant opens nothing under `work/runs/`. So everything that does is owner-run: the draw with its post-draw checks and disclosure, the builder, the runs, the per-run file checks (`verify_matched_run.py`) and the analysis. Until the analysis, their records under `reports/` hold no loss. The per-run checks read operational records only, and an audit hook stops them from opening any file in a draw folder. A failing per-run check stops nothing by itself: it goes to the owner before the next step.

**Token-level overlaps are not measured.** N6's disclosure measured exact token sequences and 64-token runs, which read the corpus's split files. The draw script may read only the manifest. The results report says that these were not measured, unless the owner approves a separate step.

**No retry,** resume, rate or width change, limit increase, replacement draw or seed redraw.

## 13. Every change from N6

| What | N6 | N7 |
|---|---|---|
| Question | INTERIOR_PEAK at 3e-4, control at 1e-4, at fixed updates | D4m_train at 1e-4, in the fixed sequence P1, S1, S3, S4, S5, S2 |
| Widths | 384, 512, 768 | 512, 768 |
| Arms | 768 and 512 at both rates, 384 at 3e-4 | 768 and 512 at both rates |
| Epochs and updates | 3; 3,072 | 3.5; 3,584, with a fourth epoch's batch order drawn |
| Readouts | E0.25, E0.5, E1, E2, E3 | E0.25, E0.5, E1, E2, E2.25, E2.5, E2.75, E3, E3.25, E3.5 |
| Groups and runs | c01–c06; C1, C2 | m01–m06; M1, M2 |
| Fresh articles | Excludes N5 | Excludes N5 and N6 |
| Seed registry | N6's | New, with N6's values and list excluded |
| Census | Walked all of `work/` | Never enters a folder whose path holds `work/runs`, by the owner's rule |
| Registry output | Registry only | Registry and `PARTITION.json` |
| Primary, labels, readings | N6's | Sections 5–7 |
| Secondaries | D3, rate effects, M, by readout | Sections 6, 8 and 9; D1, D3 and M are not computed |
| Missing draws | Any missing draw: UNAVAILABLE | Fewer than 5 available draws: UNAVAILABLE |
| Failure of the first run | Closes the study UNAVAILABLE | Admits the second run with at least 2 completed draws, counted from operational records |
| Failure of the second run | Closes the study UNAVAILABLE | The completed draws are read only if P1 has at least 5 available draws |
| Analysis outputs | `ANALYSIS.json`, `POINTS.csv`, `FITS.csv` | The same, and `MATCHED.csv` |
| Worker code | `peak_worker.py` | `matched_worker.py`, with its own `Context.adapt_readouts`, `inputs`, `stage`, `study_counts` |
| Benchmark widths | 384, 512, 768 | 512, 768 |
| Builder | Real-engine check required | Also needs the public registration's merge commit; the registration must be of this subject and name the check's receipts |
| Real-engine check | The real corpus and real seeds, before the run | Synthetic tokens and real seeds, before the registration |
| Seed draw | The registry tool, run directly | Through `run_seed_draw.py`, with an audit hook on `work/runs/` |
| Post-draw disclosure | Tokens, texts and ties, by the assistant | Articles, texts, titles and ties from the manifest, owner-run within the draw; tokens not measured |
| Per-run file checks | By the assistant, from status fields | Owner-run, from operational records (`verify_matched_run.py`) |
| A stop before any stage folder | Not counted | The same, and the analysis refuses it |
| Rate source | The file under `work/runs/` | Its byte-identical pinned copy under `reports/` |
| An undefined fit in a statistic | The status UNDEFINED | That draw is unavailable, with its reason |
| The control's premise line | Printed | Gone, with the control |
| Clipping and gradient means | Over epochs | Weighted by updates, because the fourth epoch is short |
| NOT_OVERFIT | All six draws | At least 5 draws |
| Records and terminal | | `epochs[].updates`, and the terminal's `readouts` |
| Bindings | The few-epoch registry | Also the peak registry, in the worker, the owner script and the builder |
| Labels | | NOT_READ for a step the sequence does not reach |
| Counts | | Draws without a reading, per statistic and by reason, always reported |
| Reported and not gating | | `records_against_arrays`, and sign tests and leave-one-out intervals on unavailable statistics |
| Files dropped | | `peak_plan.py`, `peak_worker.py`, `peak_analysis.py`, `peak_registry.py`, `PEAK_OWNER_RUN.ps1` |

**Kept byte for byte,** by the subject's check against N6's: the model, data pipeline, tokenizer use, pre-training recipe, batch, clipping, weights distribution, the estimator (`vendor/core.py`), the few-epoch and text workers' sealed code, the GPU gate at 12%, the power gate on AC. Also kept, by the same constants: NOT_OVERFIT's definition, the 2.5 GiB guard, the 6-hour limit per run, no retries, and the owner-run PowerShell pattern (`reports/natural-text-matched-preparation-20261104-01/OWNER_SCRIPT_DIFF.txt`).
