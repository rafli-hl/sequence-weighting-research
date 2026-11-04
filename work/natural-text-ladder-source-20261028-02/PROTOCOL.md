# Natural-text capacity ladder: Jane Street's findings (1) and (2) on WikiText-2 with small Transformers

Status: **revision 05, the second and final attempt, frozen for owner approval on 29 October 2026 (section 12).** Revision 04 was approved and run: the corpus, the seed draw, Run A and the learning-rate selection are complete and are reused unchanged. Its Run B (attempt 1) failed operationally in draw d02 and is never analysed. Revision 05 changes operations only; no outcome of any draw has been read.

Revision 04 status, as frozen: **PROPOSED; frozen for owner approval on 28 October 2026 (revision 04); no outcome exists; nothing has been tokenized, drawn or run.** This is the owner-approved design (proposal revision 2 with the owner changes of 28 Oct 2026, section 11), revised after independent review 1 with the owner's decisions on it (revision 02), again with the owner's changes to revision 02 (revision 03), and again after independent review 2 with the owner's decisions on it (revision 04; section 11). Revisions 01, 02 and 03 are preserved in `reports/natural-text-ladder-preparation-20261028-01/review-01-subject-b14f56b3-superseded/`, `revision-02-subject-09f94777-superseded/` and `review-02-subject-f26c977f/`. Paths:
- source: this directory;
- preparation, fixtures and review: `reports/natural-text-ladder-preparation-20261028-01/` (revision 04) and `reports/natural-text-ladder-revision-05-20261028-01/` (revision 05);
- seed policy: `reports/natural-text-ladder-seed-registry-20261028-01/SEED_REGISTRY_POLICY.md`;
- Amendment 01 (outcome-blind, applies unchanged): `reports/natural-text-ladder-amendment-20261028-01/AMENDMENT_01.md`;
- attempt 1 failure record: `reports/natural-text-ladder-run-b-failure-20261028-01/FAILURE_REPORT.md`.

Every rule below was fixed before the tokenizer was trained, the seeds were drawn or any model was trained. Revision 05 (section 12) changes only operations, before any outcome of Run B has been read.

## 1. Questions

Jane Street (blog: https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/; excerpts in `docs/references/jane-street-blog-excerpts.md`) report:
- **(1)** p* rises and then falls with model size;
- **(2)** more epochs move the peak to smaller models.

This project reproduced (2) in direction on synthetic data: frozen MOVES_SMALLER on 12 fresh corpora, `reports/capacity-shift-followup-result-20261028-01/REPORT.md`. The question here is whether (1) and (2) appear when small decoder Transformers are trained on **natural text**, with log-uniform per-sequence weights, from a sequence-weight-invariant baseline.

## 2. Inference unit and regime (stated in advance)

- **Draws are the inference unit.** Sequences from the same article are correlated, so every draw is a disjoint set of whole articles, and all intervals use the ten draws: df 9, t = 2.262157163. Sequences, widths, epochs, readouts and owner runs are not replications.
- **Ten draws are a resource choice, not a power calculation.** No power analysis supports 10; it is what one owner run of 6 h holds at the planning rates (or two runs of five, section 9).
- **Memorization regime.** 1,536 sequences × 32 epochs is a memorization regime. It is unlike Jane Street's "We train for 3 epochs" on large corpora. Large widths are expected to memorize much of each draw, which is where weighting acts on training-set fits; generalization claims are limited accordingly.

## 3. Data (pre-registered; outcome-blind preparation)

- **Text.** WikiText-2 raw, already in the project, pinned and hash-verified on 28 Sep 2026, licence CC-BY-SA-3.0. The exact files are the rows files `work/text-assets/{train,validation,test}-rows.json`, with SHA-256 339320f3…, 62193966… and 224cadbb… (full values in `text_plan.TEXT_ASSETS`, verified before reading).
- **Articles** (owner decision of 28 Oct 2026). A row starts an article iff it matches `^ = [^=].* = \n$` (a level-1 heading) **and the rows directly before and after it are empty**. Rows before the first heading are dropped; every later row stays in its article. This finds **600 train, 60 validation and 60 test articles**. The pattern alone also matches table and formula rows such as " = Position ; GP = ", which would give 629 and 62 fragments in train and test.
- **Tokenizer.**
  - Settings: the `tokenizers` 0.21.4 BPE model, vocabulary **4,096**, minimum frequency 2, special token `<|endoftext|>`, ByteLevel pre-tokenizer (add_prefix_space=False, use_regex=True), ByteLevel decoder, byte alphabet.
  - **Training text:** the `text` field of every row of train-rows.json, in file order, unmodified (36,718 rows, empty rows included).
  - `prepare_corpus.py` trains it **twice and refuses unless both are byte-identical**, then freezes it (its SHA-256 is recorded) **before any draw is cut**.
- **Corpus manifest.** `prepare_corpus.py` writes `CORPUS_MANIFEST.json` and checks it before writing: tokenizer settings and library version equal to the plan, the vocabulary, the sequence length, the text hashes, the SHA-256 of the code that produced it (`prepare_corpus.py`, `text_plan.py`, `text_data.py`), the article counts 600/60/60, and contiguous article offsets. Python, platform and `TOKENIZERS_PARALLELISM` are recorded, not checked. The seed draw, the builder and the worker re-check the manifest against the sealed source; the draw refuses an invalid manifest before it claims anything.
- **Sequences.** Each article is encoded separately with no special tokens and chunked into non-overlapping 129-token windows; the remainder is dropped. Each window gives 128 next-token targets.
- **Draws** (`text_data.partition`).
  - One tuning group t00 and ten analysis draws d01–d10, each a disjoint set of whole training-split articles.
  - Articles are shuffled with `random.Random(partition_seed)` and assigned in order to the current group until it holds at least N sequences; each group uses its first N sequences.
  - **N = 1,536**. Fallback, if eleven groups cannot be filled: the largest multiple of 16 that is at least 512 and fills them, decided from token counts only.
- **Shared pools.**
  - Uniform pre-training: up to 2,048 test-split sequences, stride-selected.
  - Validation: 512 validation-split sequences, stride-selected.
  - Both are shared by all groups and share no articles with any draw.
- **Seeds.** A new outcome-blind registry of 46 values:
  - the partition seed;
  - for each of the 11 groups: initialization, weight, pre-training order and adaptation order seeds;
  - a benchmark seed.

  The draw **requires the corpus manifest** and records its SHA-256, so the seeds cannot exist before the tokenizer and corpus are frozen.

## 4. Models and recipe

- **Models.** Depth-4 decoder Transformers with 4 heads: the confirmation's model code (`text_model.py`) with the vocabulary as a parameter and an untied output layer. **Widths 64, 96, 128, 192, 256 and 384** have 732,544; 1,246,272; 1,858,304; 3,377,280; 5,289,472 and 10,293,504 parameters (`text_plan.parameters`). No width is swapped or added for any reason.
- **Uniform pre-training (fixed; never tuned).**
  - Per group and width: a fresh model from the group's initialization seed.
  - Uniform weights on the pool: **4 epochs, batch 16** (512 updates for a 2,048-sequence pool), AdamW 3e-4, weight decay 0.1, clip 5.
  - The checkpoint is **E0**: the sequence-weight-invariant baseline of every gain. This follows the estimator note's definition of the gain as "reduction of loss … versus a given sequence-weight-invariant baseline" (`docs/references/sequence-weighting-note.pdf`, p. 1). It also matches the synthetic studies' E0.
- **Weighted adaptation (arm R).**
  - From E0, with a fresh AdamW at a constant learning rate, weight decay 0.1, clip 1, **batch 16**, for **32 epochs** (3,072 updates at N = 1,536).
  - Weights are log-uniform 0.01–10 per training sequence, with one mean normalization, from the group's weight seed. This is `vendor/engine.py`'s rule, generalized to N.
  - The objective is `(sequence_loss * w).mean()`, where sequence loss is the mean next-token NLL over 128 targets.
  - There is no uniform reference arm.
- **Readouts.** Per-sequence training and validation NLL at **E0, E1, E2, E4, E6, E8, E12, E16, E24 and E32**, evaluated under `fork_rng` with an RNG-unchanged check.
- **Workload.**
  - Run A: 6 pre-trainings and 18 adaptations (55,296 adaptation updates).
  - Run B: 60 pre-trainings and 60 adaptations (184,320 adaptation updates); under the split, B1 and B2 each do half (30 and 30).

## 5. Model selection: learning rate only, on the tuning group, by validation NLL only

- For each width, every rate in **{3e-5, 1e-4, 3e-4}** is run on t00 in Run A.
- **Rule** (`select_lr.py`): for each rate, take the lowest mean validation NLL over the fixed readout epochs E1–E32. E0 is excluded because it does not depend on the rate.
- The selected rate is the lowest of these values; **ties go to the smaller rate**.
- A rate at a grid edge is **accepted and flagged; the grid is not extended**.
- `select_lr.py` reads only the validation rows; **p\* is never used** and no p* is computed on t00 before Run B is analysed.
- The selected rates are frozen into every Run B activation (B, or B1 and B2). No other selection exists: no early stopping, and no epoch, width or model is chosen by any fit quantity.
- `select_lr.py` also freezes the **Run B plan** from Run A's timing forecast only (section 9). It reads no loss for this.

## 6. Primary outcomes (both pre-registered; `text_analysis.primaries`)

**Gains and fits.**
- Gain: E0 training loss minus readout training loss, per sequence, signed (float32 subtraction as in the ladder analysis).
- Fit: `vendor/core.exponent` on [0, 8]. It is undefined for nonpositive total gain; undefined fits stay undefined.

**Points.** A draw-epoch point at e ∈ {4, 6, 8, 12, 16, 24, 32} is defined only if all six width fits are defined.
- A draw is **eligible** with at least 6 of the 7 points defined, including one of E4/E6 and one of E24/E32.
- If any draw's stage did not complete (failed, infeasible or never run), **both primaries are UNAVAILABLE**.
- Otherwise, if any draw is ineligible, **both primaries are UNDEFINED**.
- No replacement draw exists in either case.

**Primary A: peak shift (finding 2).**
- The location is the frozen ladder location on the draw's six-rung curve: the argmax, with ties to the smaller width. If interior, it is the vertex of the three-point parabola clamped to its bracket; if at an end, it is the boundary rung.
- The draw's slope is the OLS slope of the location on log2(epoch) over its defined primary points.
- Labels from the df-9 t interval of the mean slope, with the ±1e-9 tolerance:
  - **MOVES_SMALLER** if the upper bound is below 0;
  - **MOVES_LARGER** if the lower bound is above 0;
  - otherwise **NO_DETECTED_SHIFT**.
- **_CENSORED** is added if any defined point is at a ladder end.

**Primary B: interior peak (finding 1), location-free.**
- For each defined draw-epoch point:
  - fit the least-squares quadratic p = a + b·u + c·u², with u = log2(width) − mean(log2 widths), to the six fits;
  - **two lines with a data-located break** (owner decisions of 28 Oct 2026, revisions 03 and 04), in the style of Simonsohn (2018, *Advances in Methods and Practices in Psychological Science* 1(4), 538–555). His Robin Hood break adjustment is not used.
    - The break is at the point's own quadratic vertex. Because the widths are discrete, the break is **the rung nearest that vertex** in log2 width, with ties to the smaller width. That rung belongs to **both** lines.
    - **Clamp** (revision 04). If the nearest rung is 64 or 384, the break moves in to 96 or 256, so each line always has at least 2 widths. A point is never discarded because its vertex lies near or beyond a ladder end. Review 2 showed that discarding such points selects on noise and biases the slopes toward a rise and fall.
    - The left slope is the OLS slope of p* on log2(width) over the rungs from 64 up to the break; the right slope is over the rungs from the break to 384.
    - **Per-point rise and fall** (revision 04): min(left slope, −right slope). It is positive only if this point itself rises before its break and falls after it.
    - The two lines are undefined only if the vertex is not finite, which means |c| ≤ 1e-12: zero curvature, including round-off on flat curves. Undefined two lines stay undefined.
    - Points whose quadratic is convex are not excluded: their break is at the quadratic's minimum, and their slopes count against a rise and fall.
- Each draw's b and c are averaged over its defined primary points. Its left slope, right slope and rise and fall are averaged over those of its defined primary points whose two lines are defined. If it has none, these means are undefined.
- The mean quadratic averages the draw coefficients; its vertex is mean(log2 widths) − mean(b) / (2 · mean(c)). The vertex is undefined when |mean(c)| ≤ 1e-12 or the vertex is not finite. It is reported as a width only if it lies in [0, 16] in log2 units, so a near-flat curve cannot crash the analysis.
- Four conditions, each a df-9 t interval over the ten draws:
  - **(i) curvature:** the interval of the mean c lies **below 0**;
  - **(ii) vertex:** the vertex of the mean quadratic lies in **[log2 64, log2 384]** = [6, 8.585];
  - **(iii) rise and fall:** every one of the ten draws has defined two-lines means, the interval of the mean left slope lies **above 0**, and that of the mean right slope lies **below 0**. If any draw's means are undefined, (iii) fails: the rise and fall is not established. Intervals are then not computed, and the counts are reported.
  - **(iv) within points** (owner decision of 28 Oct 2026, revision 04): the interval of the mean per-point rise and fall lies **above 0**. A rise at some epochs can then not pair with a fall at others.
- Labels:
  - **INTERIOR_PEAK** iff (i), (ii), (iii) and (iv) all hold;
  - **RISE_AND_FALL_NOT_WITHIN_POINTS** if (i), (ii) and (iii) hold but (iv) fails. The mean slopes rise before the break and fall after it, but the mean per-point rise and fall is not significantly above 0: a rise and fall is not established within the same draw-epoch points. One cause is a rise at early epochs and a fall at late ones; another is a rise or fall too weak point by point. The label also occurs, rarely, for true stationary peaks and for curves that never rise and fall (`POWER_PRIMARY_B.json`);
  - **CONCAVE_WITHOUT_RISE_AND_FALL** if (i) and (ii) hold but (iii) fails. This covers curves that rise and level off, or stay flat and then fall (review 1 showed that (i) and (ii) alone accept them), and the case where some draw has no point with a finite vertex, so its two-lines means are undefined;
  - **CONCAVE_VERTEX_OUTSIDE_LADDER** if (i) holds but the vertex is outside the ladder or undefined;
  - **CONVEX** if the curvature interval lies above 0;
  - otherwise **NO_DETECTED_CURVATURE**.
- INTERIOR_PEAK is an intersection of tests, each at two-sided 95%, so it needs every one of them; no adjustment is applied.
- **Measured operating characteristics** (designed curves with Gaussian noise, `reports/natural-text-ladder-preparation-20261028-01/POWER_PRIMARY_B.json` and `POWER_PRIMARY_B_REFINE.json`; section 10). These are fixed with this revision and quoted in section 8 when the result is not INTERIOR_PEAK.

**Saturation rule (both primaries; the follow-up's rule, on the same points).**
- **S1.** A point is flagged if any of its fits is ≥ 7.999.
- **S32.** Required whenever a point is flagged: its six fits are refitted on the same gains with search bound 32 (the 0.05 grid and refinement; identical to `core.exponent` at bound 8). The location, the quadratic, the break and the two lines are recomputed.
- **Unresolved.** A refit with a fit ≥ 31.999 within its argmax ± 1 bracket.
- **SD.** Flagged points are dropped. A draw needs at least 3 points left, and SD needs at least 3 draws (df = draws − 1). SD is required if more than 25% of the 70 nominal points are flagged (18 or more) or any refit is unresolved; it is computed descriptively whenever a point is flagged.
- **Decision, in this order:**
  1. UNAVAILABLE, then UNDEFINED;
  2. SATURATED if any required sensitivity cannot be computed;
  3. SATURATION_SENSITIVE if any required sensitivity's label differs from the primary label;
  4. otherwise the primary label.

  A's _CENSORED suffix is added to SATURATION_SENSITIVE and to the primary labels, but not to UNAVAILABLE, UNDEFINED or SATURATED.
- **Lower bound.** Fits at p ≤ 0.001 are not part of the saturation rule; their counts by epoch are reported with the primaries.

**Multiplicity.** A and B answer different findings. Each is reported at two-sided 95%, with no family-wise adjustment, stated in advance.

## 7. Secondaries (non-gating; all reported)

- **Per readout epoch:**
  - the ten-draw panel curve (UNAVAILABLE if a draw is missing, UNDEFINED if any fit is undefined) with its argmax and location;
  - the vertex of the mean quadratic, the df-9 intervals of the mean curvature, of the two slopes and of the rise and fall (when every draw's two lines are defined), each draw's break, and the Primary B label at that epoch;
  - per-draw locations and vertices;
  - undefined, upper-bound, lower-bound and flagged counts.
- The two-point location change E8 → E32 (df 9, _CENSORED).
- Saturation, lower-bound and boundary counts by epoch; two-lines counts by epoch (defined, clamped, no finite vertex, and the break widths).
- Train and validation NLL, and the gap, per width and readout; E0 losses; the pre-training clip fraction.
- Clipping per width (mean fraction, mean and maximum gradient norm).
- The full learning-rate selection table: 6 widths × 3 rates, with the minimum validation NLL and its epoch, and the edge flags.
- Every fit with J(p*), J(0), total gain and the negative-gain fraction (`FITS.csv`).
- `POINTS.csv`: every primary point, with fits, location, quadratic, break width and whether it was clamped, two-lines slopes, the per-point rise and fall, flags and refits.

## 8. What each outcome would mean (fixed now)

**Primary A on its own.**

| Label | Meaning |
|---|---|
| MOVES_SMALLER | Finding (2) is reproduced in direction on natural text for these small models: the peak location moves to smaller widths with more epochs. |
| MOVES_SMALLER_CENSORED | The same direction, but at least one point's peak is at a ladder end, where the location is the end rung. The direction stands; the size of the shift is not estimable. |
| MOVES_LARGER (_CENSORED) | Contrary to (2) in this setting. |
| NO_DETECTED_SHIFT (_CENSORED) | No shift is detected with ten draws. This is not a claim of absence, and it departs from the synthetic result. |
| SATURATION_SENSITIVE (_CENSORED) | The label changes when fits at the p = 8 bound are refitted or dropped. No directional claim. |
| SATURATED | A required drop-flagged check cannot be computed. No claim. |
| UNDEFINED | At least one draw is ineligible (too many undefined fits). No claim; no replacement draw. |
| UNAVAILABLE | At least one draw's stage did not complete. No claim; no replacement draw. |

**Primary B on its own.**

| Label | Meaning |
|---|---|
| INTERIOR_PEAK | Finding (1) is reproduced in shape: p* is concave in log2 width, the vertex lies inside 64–384, and, with the break at each point's own vertex, p* rises significantly before the break and falls significantly after it, within the same points. |
| RISE_AND_FALL_NOT_WITHIN_POINTS | The mean slopes rise before the break and fall after it, but a rise and fall is not established within the same draw-epoch points. The rise and the fall may come from different epochs, or be too weak point by point. Finding (1) is not reproduced; a peak that moves through the ladder or appears only at some epochs is possible, and Primary A and the by-epoch secondaries describe it. The required wording below applies. |
| CONCAVE_WITHOUT_RISE_AND_FALL | The curve bends downward inside the ladder, but a rise and a fall are not both established (for example, rising then levelling, or flat then falling). Finding (1) is not reproduced. |
| CONCAVE_VERTEX_OUTSIDE_LADDER | The curve bends downward, but the vertex of the mean quadratic lies outside 64–384 or is undefined. An interior peak within 64–384 is not established; a wider ladder needs its own protocol. The required wording below applies. |
| CONVEX | The mean quadratic bends upward (a dip). An interior peak is not established. This is not evidence against (1): a lopsided true peak can read CONVEX (section 10). The required wording below applies. |
| NO_DETECTED_CURVATURE | No curvature is detected with ten draws. Not a claim of absence. |
| SATURATION_SENSITIVE, SATURATED, UNDEFINED, UNAVAILABLE | As for Primary A. |

**Required wording whenever Primary B is not INTERIOR_PEAK** (owner decision of 28 Oct 2026, pre-registered). The report must say:
- The test has low power for shallow peaks under epoch-correlated noise. The measured power is quoted from section 10: For the shallow fixture peaks at 96 and 256 (noise sd 0.3), measured power is 89.8% and 92.2% with independent noise, but 38.0% and 35.0% when half of the noise variance persists across epochs within a draw, and 30.2% and 33.8% when 80% does; sharp peaks were detected in 100.0% of replicates in all three.
- The result is therefore **inconclusive for shallow peaks**.
- It is **not evidence that no peak exists**.

Lopsided peaks can also be missed (section 10). This wording applies to every label above other than INTERIOR_PEAK, including CONVEX.

**Joint reading** (only when neither label is SATURATION_SENSITIVE, SATURATED, UNDEFINED or UNAVAILABLE; otherwise the other primary is read on its own).

| Primary A | Primary B | Meaning |
|---|---|---|
| MOVES_SMALLER (_CENSORED) | INTERIOR_PEAK | Findings (1) and (2) are both reproduced in direction on natural text, for small models from a weight-invariant baseline, in a memorization regime. No large-model claim. |
| MOVES_SMALLER (_CENSORED) | any other | The location moves smaller, but no interior peak is established within 64–384. (2)'s direction is consistent; (1) is not reproduced, which is inconclusive for shallow peaks (required wording above). |
| NO_DETECTED_SHIFT (_CENSORED) | INTERIOR_PEAK | (1) is reproduced; (2) is not detected with ten draws. |
| NO_DETECTED_SHIFT (_CENSORED) | any other | Neither finding is reproduced at this scale under this recipe. For (1) this is inconclusive for shallow peaks (required wording above). |
| MOVES_LARGER (_CENSORED) | any | Contrary to (2) in this setting; B is read on its own. |

## 9. Operations, limits and failure policy

**Owner steps, each separately approved** (exact commands in the preparation report). Steps 1–5 are complete (revision 04) and reused; in revision 05, steps 6–9 use the -02 folders of section 12:
1. `prepare_corpus.py` in WSL: tokenizer (trained twice, identical) and corpus, with the manifest.
2. `text_registry.py draw <registry dir> <CORPUS_MANIFEST.json>`: the seeds, bound to the manifest.
3. Build activation A: binds the subject, registry, corpus manifest and partition.
4. **Run A**: benchmark probe, then t00 at three rates per width.
5. `select_lr.py`: the learning rates and the Run B plan.
6. Build activation B (plan B) or B1 (plan B1+B2). It also binds the selection and Run A's COMPLETE terminal, and checks that Run A ran under the same subject, registry, manifest and partition. In revision 05, Run A is checked under the revision 04 subject (90e3f3ef…), under which it ran. Run B (for B1 after a fallback) and Run B1 (for B2) are checked under revision 05's subject.
7. **Run B**, or **Run B1** (d01–d05). If Run B ends in the start-up fallback, build activation B1 (which also binds Run B's fallback terminal) and run B1.
8. Under the split only: build activation B2, which also binds Run B1's COMPLETE terminal; then **Run B2** (d06–d10).
9. `text_analysis.py`, on Run B or on Run B1 and Run B2. It runs only after every Run B run has ended, and it refuses:
   - Run B1 without Run B2, so no p* from draws 1–5 is computed before B2 has ended;
   - any run that is neither COMPLETE nor FAILED, such as a Run B that ended in the start-up fallback;
   - a Run B2 whose TERMINAL.json does not bind this Run B1's terminal, or whose bindings differ from Run B1's.

   If B1 fails, B2 does not start and the primaries are UNAVAILABLE without an analysis.

**Run B plan** (owner rule of 28 Oct 2026; outcome-blind). Run A's `BENCHMARK.json` holds, besides its own cap, the frozen cap formula applied to its benchmark for a ten-draw run (B) and a five-draw run (B1). `select_lr.py` freezes the plan from that forecast only:
- **B** if ten draws are feasible within 6 h;
- otherwise **B1+B2**: two sequential owner runs, B1 = d01–d05 and B2 = d06–d10, each within 6 h, with identical science, seeds, learning rates and analysis. B2 starts only after B1 is COMPLETE;
- otherwise **UNAVAILABLE**: even five draws would exceed 6 h.

**Run B start-up fallback** (owner rule of 28 Oct 2026, revision 03; timing only). Run A can forecast that ten draws fit while Run B's own start-up benchmark puts them over 6 h. If that benchmark, under the same frozen cap formula, finds a five-draw run feasible, Run B stops before any training. It ends with status **FALLBACK_TO_SPLIT**: no stage, its benchmark bound by hash in TERMINAL.json. The draws then go to the same split, B1 = d01–d05 and B2 = d06–d10, with new activations. The builder and the worker re-derive the fallback from Run B's bound benchmark before admitting B1 or B2. The builder also requires Run B's owner exit receipt to confirm an observed exit with status FALLBACK_TO_SPLIT and the same terminal hash. Like `check_fallback`, `select_lr.py` re-derives Run A's forecast from the bound benchmark.

No draw, epoch or width is cut under any plan or fallback. Each of B, B1 and B2 runs its own benchmark and applies the cap formula to its own stage count. If that benchmark finds the run infeasible, the run stops before any stage, except for Run B's fallback above. The primaries are **UNAVAILABLE** only if:
- Run A fails, so there is no selection or plan;
- the plan is UNAVAILABLE;
- Run B's start-up check finds even five draws over 6 h;
- Run B fails before or after its start-up check, other than the fallback;
- B1 or B2 fails or stops (B2 cannot start without a COMPLETE B1);
- a run stops because the GPU stayed busy for the whole 30-minute window before a draw (revision 05, section 12); or
- a run ends without a TERMINAL.json, which the analysis refuses.

There is no retry and no further re-planning. Revision 05 is the final attempt: if its run fails for any reason, the natural-text ladder closes as UNAVAILABLE (section 12).

**Inside each run:**
- **Benchmark.** An outcome-blind benchmark on the pool, through the stage code paths. Every step passes the sampled-GPU guard, so a width over 2 GiB stops the run before any science.
- **Cap formula** (`text_worker.stage_cap`). The projected stage time sums every measured cost times its per-stage count. The cap is ceil(1.25 × projected + 120 s); a run is feasible iff stages × (cap + 60) + 900 ≤ 21,600 s, otherwise it stops before any stage. The 1.25 multiplier replaces the ladder's 1.5: two earlier runs used 0.66 and 0.68 of their projections, and 1.5 would not fit ten draws in 6 h.

**Limits per run** (each of A, B, B1 and B2):
- 21,600 s worker deadline; the wrapper waits 21,900 s and never kills.
- 2 GiB / 1,000 files in total; 256 MiB / 128 files per stage.
- 4 GiB free on D: at admission; 2 GiB reserve.
- **Sampled GPU ≤ 2 GiB (unchanged)**; worker RSS ≤ 4,032 MiB. The GPU should be otherwise idle during each run: review 1 estimated about 0.6 GiB of headroom under the guard at width 384. Attempt 1 showed that this in-WSL guard does not register Windows GPU apps; revision 05 adds the Windows-side check of section 12.

**Failure policy.** Fail closed: no retry, resume, width swap, limit increase, replacement draw, seed redraw or re-planning.

## 10. Limitations

- One encyclopaedia corpus; draws are disjoint article sets, but the pre-training and validation pools are shared.
- **No held-out test loss.** The test split is the uniform pre-training pool, so generalization is reported only as validation NLL.
- No component labels, so no mechanism decomposition.
- Small models (0.73–10.29 M parameters), depth 4, a 4,096-token vocabulary. No large-model or scaling claim follows.
- Fixed epochs mix capacity with progress.
- One constant-learning-rate trajectory per draw is read at several epochs.
- **Per-width learning rates.** Widths can receive different rates. That is part of the recipe, and the selection rule is fixed, but a rate change between neighbouring widths can move p* and so the location in Primary A. The full selection table is reported with the result.
- Fits can saturate near p = 8, or sit at p = 0.
- Clipping is likely frequent.
- **Discrete, clamped break.** The two-lines break is the rung nearest each point's vertex, clamped to 96–256, not the continuous vertex. A peak between rungs is broken at the nearer one.
- **Lopsided peaks can be missed** (review 2, finding 3; accepted). A least-squares quadratic is a poor summary of a lopsided peak. In the fixtures:
  - [1, 4, 2, 2, 2, 2] (peak at 96) reads CONCAVE_WITHOUT_RISE_AND_FALL. Its vertex is at log2 7.27, so the break is at 128, not at the argmax, and the right line is flat.
  - [1, 1, 1, 1, 4, 3] (peak at 256) reads CONVEX. Its quadratic has c = +0.40, so condition (i) fails before the break matters.
- **Measured power and false positives of Primary B** (designed curves, Gaussian noise per fit with total sd 0.3, ten draws × seven epochs; a variance share ρ of the noise persists across epochs within a draw). The owner's 80% power bar applies to the independent-noise fixtures (ρ = 0); the false-positive limit of 5% applies to the null and epoch-mixing curves under ρ = 0.5 and 0.8 as well.

  | Designed curve (noise sd 0.3) | ρ = 0 | ρ = 0.5 | ρ = 0.8 |
  |---|---|---|---|
  | Shallow parabolic peak at 96 (curvature 0.6): power | 89.8% | 38.0% | 30.2% |
  | Shallow parabolic peak at 256 (curvature 0.6): power | 92.2% | 35.0% | 33.8% |
  | Sharp (tent) peaks at 96 and 256, central peak at 7.3: power | 100.0% | 100.0% | 100.0% |
  | Null curves that never rise and fall (8 shapes): highest false INTERIOR_PEAK rate | 2.8% | 3.1% | 3.5% |
  | Epoch-mixing curves (2 shapes): highest false INTERIOR_PEAK rate | 2.5% | 2.2% | 2.6% |

  Power and the ρ = 0 rates use 400 replicates (`POWER_PRIMARY_B.json`). The ρ = 0.5 and 0.8 false-positive rates use 4,000 replicates (`POWER_PRIMARY_B_REFINE.json`); at 400 replicates, one null curve read 6.0% at ρ = 0.8, and its 4,000-replicate estimate is 2.6%.
- **Low power for shallow peaks under correlated noise.** Real p* for one draw is correlated across epochs, so averaging over epochs reduces noise less than in the independent-noise fixtures. For the shallow fixture peaks at 96 and 256 (noise sd 0.3), measured power is 89.8% and 92.2% with independent noise, but 38.0% and 35.0% when half of the noise variance persists across epochs within a draw, and 30.2% and 33.8% when 80% does; sharp peaks were detected in 100.0% of replicates in all three. A result other than INTERIOR_PEAK is therefore inconclusive for shallow peaks and is not evidence that no peak exists (section 8). The noise level and correlation of real natural-text p* are unknown; sd 0.3 is an assumption.
- **Planning arithmetic** (`reports/natural-text-ladder-preparation-20261028-01/BUDGET.json`, revision 02, unchanged in revisions 03 and 04, scaled from the follow-up run's measured benchmark):

  | Run | Projected | Worst case | Feasible up to |
  |---|---|---|---|
  | A | 0.90 h | 1.42 h | — |
  | B | 3.34 h | 4.93 h | 1.26 × the planning costs |
  | B1 or B2 | 1.67 h each | 2.59 h each | 2.68 × the planning costs |

  Storage: A 0.35 GiB, B 1.12 GiB, B1 or B2 0.69 GiB. These are planning numbers; each run's own benchmark sets its cap.

## 11. Owner decisions of 28 Oct 2026

**On proposal revision 2:**
1. **Finding (1).** The central-window primary is replaced by the location-free quadratic-curvature test with the vertex condition; vertex locations by epoch are a secondary; the saturation rule is the same. The "mean vertex" is the vertex of the mean quadratic, so a single draw with near-zero curvature cannot dominate it. This protocol fixes that reading.
2. **Learning rate.** Per width from {3e-5, 1e-4, 3e-4} on the tuning draw, by the lowest validation NLL over the fixed readout epochs; ties to the smaller rate; edges accepted and flagged; no grid extension; never p*.
3. **Draws.** 10, stated as a resource choice.
4. **No uniform reference arm.**
5. **Tokenizer.** Pre-registered: 4,096 vocabulary, the exact training text, frozen before the draws are cut.
6. **Inference unit and regime.** Section 2.

**Kept unchanged from the proposal:** WikiText-2; batch 16; the 2 GiB guard; widths 64–384; the fixed uniform pre-training on the test split; separate owner runs for probe and analysis; no width swaps or limit increases.

**Detail fixed here:** "Readout epoch" in the finding-(1) primary means the seven primary epochs E4–E32, the same points as Primary A; E1 and E2 enter only the secondaries.

**On independent review 1** (findings 1, 3 and 6):
1. **Two lines.** Primary B also requires a significant rise and a significant fall, with a breakpoint fixed without any p* outcome, at least two widths on each side (three here), and both slopes significant. Revision 02 fixed the break at 128/192. Revision 03 replaces it with a data-located break (below; section 6).
2. **Articles.** A heading needs an empty row directly before and after it: 600/60/60 articles (section 3).
3. **Run B split.** The fallback is pre-registered and depends only on Run A's measured timing. If Run B is projected over the 6-hour limit, it is split into two sequential owner runs, B1 (draws 1–5) and B2 (draws 6–10), each within 6 hours, with identical science, seeds and analysis. The analysis runs only after both complete. Only if even a five-draw run would exceed 6 hours, or B2 fails, is the primary recorded UNAVAILABLE. Draws, epochs and widths are never reduced (section 9).

**On revision 02** (revision 03):
1. **Data-located break.** The fixed 64–128 / 192–384 break is replaced by a Simonsohn-style break at each draw-epoch point's quadratic vertex, with at least 2 widths on each side (section 6). The discrete-rung reading, with the break rung in both lines, is fixed here so that true peaks at 96 or 256 can be detected. CONCAVE_WITHOUT_RISE_AND_FALL and NO_DETECTED_CURVATURE are kept.
2. **Run B start-up fallback.** If Run B's own start-up check finds ten draws over 6 h after Run A forecast that they fit, the B1/B2 split applies, decided from timing only, before any training. UNAVAILABLE applies only if a five-draw run would also exceed 6 h, or B2 fails (section 9).

**On independent review 2** (revision 04):
1. **Clamp, not discard** (finding 1). A break nearest 64 or 384 moves in to 96 or 256 (section 6).
2. **Within points** (finding 2). The both-halves rule was measured first and not adopted: under independent noise at sd 0.3 it had 36–40% power for the shallow fixture peaks (`revision-04-draft-both-halves/`). It is replaced by condition (iv), the per-point rise and fall, with the label RISE_AND_FALL_NOT_WITHIN_POINTS.
3. **Lopsided peaks** (finding 3). Missed lopsided peaks are accepted as a stated limitation; the fixtures show it (section 10).
4. **Power bar.** The owner's 80% bar applies to the independent-noise fixtures. Power under epoch-correlated noise is a stated limitation. The 5% false-positive limit applies to the null and epoch-mixing curves under both noise models.
5. **Required wording.** A result other than INTERIOR_PEAK must be reported as inconclusive for shallow peaks, with the measured power, and never as evidence that no peak exists (sections 8 and 10).
6. **UNAVAILABLE list** (finding 8). B1 failure and a Run B failure after its start-up check also make the primaries UNAVAILABLE (section 9), as necessary consequences of the owner's rule. The owner is asked to confirm this with the revision-04 approval request. Section 9 also names Run A failure and a missing TERMINAL.json, for completeness.

The mechanical fixes for findings 4–8 are listed in the revision-04 preparation report.

**Revision-02 fixes for the other review findings:**
- The vertex overflow (2).
- Corpus manifest binding: code hashes, plan equality and offsets; the draw requires the manifest (4).
- Tokenizer trained twice (5).
- Corrected hours (6).
- Per-primary outcome table (7).
- Run A and Run B1 cross-checks in the builder and worker (8).
- Integrity checks in the analysis and selection (9).
- Lower-bound counts (10).
- UNAVAILABLE separated from UNDEFINED.
- The approval record hash is checked (13).

## 12. Revision 05: the second and final attempt (owner ruling of 28 Oct 2026)

**Attempt 1.** Revision 04's Run B (`work/runs/natural-text-ladder-b-20261028-01`, TERMINAL.json ab01d898c6a2888c2a9672346b7990ca99057c51030a62005282257fb90506e4) failed in draw d02 at its per-draw work cap. d01 completed in 671.9 s. A GPU game started at 22:20:36, during d01. In d02, the five widths that finished ran 1.55–1.78× slower than in d01. The timing coincides, but the records cannot prove the cause (`reports/natural-text-ladder-run-b-failure-20261028-01/FAILURE_REPORT.md`).

Its primaries were UNAVAILABLE under section 9. Only operational fields and file times were read, for the failure record. No outcome (per-sequence array, loss or p*) has been read.

**Owner ruling (verbatim):**
> Decision: B, revision 05. I rule that rerunning the same unseen draws after this operational failure is a new attempt, not a retry, under these pre-registered conditions:
> 1. The failed Run B is never analysed. Its folders stay preserved and unopened for outcomes, including d01. Revision 05 reruns all ten draws from scratch, and the analysis reads only the new run.
> 2. This is the final attempt. If revision 05's run fails for any reason, the natural-text ladder closes as UNAVAILABLE with no further attempt.
> 3. The final report discloses attempt 1, its cause as recorded in FAILURE_REPORT.md, and that its outputs were never analysed.
> Operational addition: the GPU check runs on the Windows side in the owner script using nvidia-smi (memory used and utilization), not inside WSL. Before start, refuse if the GPU is busy. Between draws, if busy, wait and recheck for up to 30 minutes, then stop with a clear status. Record every check in the run folder. Thresholds are fixed now from an idle baseline; tell me the values.
> Keep everything else identical: science, seeds, draws, learning rates, Amendment 01, cap formula. Fixture tests, then one scoped review of only the revision 05 changes, then stop for my approval with hashes and commands. I commit to keeping games and other GPU apps closed for the whole run.

**Unchanged from revision 04:**
- the science (sections 1–8 and 10);
- the seeds and draws (registry 8ce7d597…) and the corpus (manifest 72daa1e1…);
- the learning rates (`LR_SELECTION.json` cb059387…, from Run A, terminal 6c6e7fe2…, reused);
- Amendment 01 (adc19ccc…);
- the cap formula and every limit of section 9.

Every source file is a byte copy of revision 04 except `text_worker.py`, `text_analysis.py`, `TEXT_OWNER_RUN.ps1`, `PROTOCOL.md` and `README.md`. Two files are new: `gpu_check.ps1` and `GPU_CHECK.json`. The sealer checks this.

**Folders.** Run B uses `work/natural-text-ladder-activation-b-20261028-02` and `work/runs/natural-text-ladder-b-20261028-02`; B1 and B2, after a start-up fallback, likewise use -02. Run A and its activation are revision 04's.

**Analysis (condition 1).** `text_analysis.load` refuses attempt 1's folder, and any run under the revision 04 subject, before reading any draw.

**Windows-side GPU check** (owner addition; `gpu_check.ps1`, thresholds in `GPU_CHECK.json`). The owner script runs `C:\Windows\System32\nvidia-smi.exe` on Windows, not inside WSL.
- **One check.** It settles for 3 s, then takes 10 readings 1 s apart of memory used, memory total and utilization. The check is **UNVERIFIED**, and never IDLE, if any reading fails. Otherwise:
  - **before start**, with no worker, it is **BUSY** if the mean utilization exceeds **12%** or any reading's memory used exceeds **658 MiB**;
  - **before a draw**, it is **BUSY** if the mean utilization exceeds 12%. Memory is recorded in every reading but not gated, because the worker is alive and may hold GPU memory (owner change of 29 Oct 2026, below).
- **How the thresholds were fixed.** They come from the idle baseline `reports/natural-text-ladder-revision-05-20261028-01/GPU_BASELINE.json` (sha256 0774b915…; 300 readings, 0 failed, 29 Oct 2026 02:20–02:25 local time: memory used 105–146 MiB, mean utilization 0.04%, highest single reading 13%, highest 10-reading mean 1.3%), by a rule written before the baseline was measured (`gpu_baseline.ps1`):
  - utilization: the larger of 10% and (the highest rolling 10-reading mean, rounded up to a whole percent, + 10 points), giving max(10, ceil(1.3) + 10) = 12%;
  - memory before start: the highest reading + 512 MiB, giving 146 + 512 = 658 MiB;
  - acceptance: the baseline counts as idle only if no reading failed, the highest rolling mean is at most 10% and the highest memory is at most 1,024 MiB.

  The baseline was taken after the game had exited. The Riot Client background service and the Vanguard tray (`RiotClientServices`, `RiotClientCrashHandler`, `vgtray`) were still running; the owner had confirmed that no other GPU app was running.
- **Owner change of 29 Oct 2026 (before the baseline was measured; verbatim):**
  > One change to the threshold rule, before measuring: the before-draw gate uses utilization only. Between draws the worker likely still holds GPU memory (PyTorch cache plus CUDA context, which the WSL-side 1.49 GiB may not include), so a memory gate could falsely stop the final attempt. Before draws, record memory in every check but do not gate on it. Keep the memory gate before start, when no worker exists. Add a test for a before-draw check with high memory and idle utilization, which must pass.
- **Before start.** The owner script checks before it claims the activation. If the check is not IDLE, it refuses and claims nothing. It records the check in the activation folder (`gpu-checks/PRESTART-REFUSED-k.json`). The same command can then be run again once the GPU is idle; a refused start is not an attempt.
- **Before every draw:** d01, after the benchmark, and each later draw.
  - The worker writes a request into the run folder and waits; the owner script checks.
  - If the check is BUSY or UNVERIFIED, the script waits 60 s after each check (a cycle of about 72 s) and rechecks, for up to 30 minutes from the start of the first check. It then answers BUSY_TIMEOUT.
  - On BUSY_TIMEOUT the worker stops before the draw with GpuBusyError. Its message says whether the checks were busy, unverifiable (every check had a failed nvidia-smi reading) or both. The status is FAILED, and the owner receipt carries stop_reason GPU_NOT_IDLE_30_MIN.
  - The wait lies outside the draw's work cap; the 6 h overall deadline still applies.
  - Each nvidia-smi reading times out after 15 s. The last check can start just before 30 minutes and take up to 3 + 9 + 10 × 15 = 162 s, so a verdict arrives at most about 1,962 s after the first check. The worker fails closed if no verdict arrives within 2,400 s.
- **Records.** Every check, with all its readings, is recorded in the run folder's `gpu-checks/`: the pre-start check, any refused pre-start checks, and per draw the request and the verdict with every check behind it. The owner script's verdict files stay in the activation folder, and the owner receipt lists them with their hashes.
- **Console.** While the worker runs, the owner script prints nothing. Progress, including every GPU check, goes to `OWNER_PROGRESS.log` in the activation folder; the final status is printed after the worker exits. Review 4 found that a console write can stall in a legacy console window while text is selected in it. Closing the window or pressing Ctrl+C during the run ends the owner script without a receipt.
- **What the gate cannot do:**
  - A GPU app started during a draw, or during the start-up benchmark, is not seen until the next check. In attempt 1 the game started during d01 and would have been seen only before d02. A game that starts mid-draw can still push that draw over its cap.
  - A game during the benchmark inflates the cap; a slowdown beyond about 2.15× could trigger FALLBACK_TO_SPLIT.
  - Before a draw, a check with mean utilization at most 12% passes whatever its memory, for example a paused or minimized game.
  - Any other sustained load on the NVIDIA GPU above 12%, such as hardware-accelerated video in a browser, stops the final attempt after 30 minutes.

  The owner's commitment below therefore remains the main safeguard; the gate only stops a draw from starting on a busy GPU.
- **Owner commitment:** games and other GPU apps stay closed for the whole run.

**Failure (condition 2).** If revision 05's run fails for any reason, the natural-text ladder closes as UNAVAILABLE, with no further attempt. Reasons include a GPU-busy stop, a cap, a guard or a missing TERMINAL.json.

A start-up FALLBACK_TO_SPLIT is not a failure: the split into B1 and B2 follows as in section 9, each with the same GPU checks. If either fails, the ladder closes as UNAVAILABLE.

Whether `text_analysis.py` is run on a FAILED revision 05 run is the owner's decision. It would give descriptive secondaries for the completed draws; the primaries are UNAVAILABLE either way. The decision is recorded in the approval text of this revision.

Amendment 01 applies unchanged to revision 05; the approval text binds it to revision 05's subject.

**Report (condition 3).** The final report discloses attempt 1, its cause as recorded in FAILURE_REPORT.md, and that its outputs were never analysed.
