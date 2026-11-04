# Proposal, revision 2 (not built): a natural-text capacity ladder

Status, 28 October 2026: **proposal only.** Nothing has been built, downloaded, tokenized or run. This revision applies the owner decisions of 28 Oct 2026; revision 1 is kept as `NATURAL_TEXT_LADDER_PROPOSAL_r1.md`.

Every time and memory figure is planning arithmetic from `natural_text_budget_r2.py` → `NATURAL_TEXT_BUDGET_r2.json`. It is anchored on costs measured in the follow-up run's own benchmark, and none of it is a measurement of this design.

## 1. Question

When small Transformers are trained on natural text with log-uniform per-sequence weights, from a weight-invariant starting point:
- **Finding (1):** does p* rise and then fall with width (an interior peak)?
- **Finding (2):** does the peak move to smaller widths as training continues?

All earlier evidence is synthetic, including the pre-registered MOVES_SMALLER follow-up. This design tests whether the pattern survives on real text. It cannot test large-scale behaviour.

## 2. Owner decisions applied (28 Oct 2026)

- **Corpus.** WikiText-2 raw, already on disk.
  - Location: `work/text-assets/`, Hugging Face revision b08601e0…, pinned and hash-verified on 28 Sep 2026, licence CC-BY-SA-3.0.
  - No download is needed.
- **Memory.** Batch 16 at every width. The 2 GiB sampled-device guard stays unchanged, with no higher limit.
- **Gains.**
  - Each sequence's gain is its loss reduction from a checkpoint E0 taken after a short **uniform-weight** pre-training. The pre-training length is a fixed, pre-registered number (section 3) and is never tuned on outcomes.
  - This matches the synthetic studies' E0. It also matches the estimator note's definition of the gain as the "reduction of loss … versus a given sequence-weight-invariant baseline" (`docs/references/sequence-weighting-note.pdf`, p. 1).
  - The blog itself says only "the loss reduction on that sequence achieved from training".
- **Primaries.** Two are pre-registered with the follow-up's saturation rule: the peak-shift slope for finding (2), and a frozen interior-peak test for finding (1).

## 3. Design (to be frozen in a versioned protocol before any outcome)

**Data.** All preparation steps are outcome-blind: they look at token counts only, never at losses or fits.
- **Tokenizer.** A 4,096-token BPE trained once on the training split with the locked `tokenizers` 0.21.4 in WSL, then frozen.
- **Sequences.** 128 tokens, chunked within articles.
- **Draws.** 10 analysis draws plus 1 tuning draw, each a disjoint set of whole training-split articles with N = 1,536 training sequences (196,608 tokens).
  - The article partition comes from one outcome-blind seeded registry draw.
  - With 2,051,910 training words, an estimated 12–14 such groups fit; 11 are needed.
  - Pre-registered fallback: if the tokenized split holds fewer than 11 groups of 1,536, N becomes the largest multiple of 16 that gives 11 groups. This is decided from token counts only, before any training.
- **Pre-training pool.** 2,048 sequences (262,144 tokens) from the **test split**, whose articles are disjoint from every draw. The split is estimated at 277k–326k tokens. The pool is shared by all draws.
- **Validation.** 512 sequences (65,536 tokens) from the validation split, shared by all draws.

**Models.** Depth-4 decoder Transformers with 4 heads, in a new versioned `model.py` that takes the vocabulary size; the current file fixes `VOCAB = 84`. **Six widths: 64, 96, 128, 192, 256 and 384** (0.73 M to 10.29 M parameters).

**Pre-training (fixed).**
- Per draw and width: a fresh model from the draw's initialization seed.
- Uniform weights; **2,048 sequences × 4 epochs = 512 updates at batch 16**.
- AdamW 3e-4, WD 0.1, clip 5: the synthetic studies' pre-training recipe, not tuned.
- E0 is that checkpoint.

**Weighted adaptation.**
- From E0. Weights are log-uniform 0.01–10 per training sequence, mean-normalized, from the draw's weight seed. Arm R only.
- AdamW with a constant learning rate, WD 0.1, clip 1, batch 16.
- **32 epochs = 3,072 updates.**
- Per-sequence training and validation losses at E0, E1, E2, E4, E6, E8, E12, E16, E24 and E32.

**Learning rate (Run A, tuning draw only).**
- A grid of 3 values, recommended {3e-5, 1e-4, 3e-4}.
- Chosen per width by the lowest validation NLL at E32, with ties going to the smaller rate.
- No p* is computed on the tuning draw before Run B is analysed.

**Seeds.** A new outcome-blind registry holds one partition seed and, per draw, the initialization, weight, pre-training order and adaptation order seeds. It excludes every seed used so far.

## 4. Pre-registered primaries

Both primaries use the 10 analysis draws as the only replication unit: a df-9 t interval, two-sided 95%, critical value 2.262157163, with the follow-up's ±1e-9 sign tolerance. Each answers a different finding; both are reported at 95% with no family-wise adjustment, stated in advance.

**Primary A: peak shift (finding 2).**
- Per draw, the location is the frozen ladder location on the draw's own six-rung curve: the parabola vertex around the argmax rung, or the boundary rung. Ties go to the smaller width.
- The draw's slope is the OLS slope of the location on log2(epoch) over **E4, E6, E8, E12, E16, E24 and E32**. These are equally spaced in log2, at half-doubling steps.
- A draw slope needs at least 6 of the 7 points defined, including one of E4/E6 and one of E24/E32.
- Labels: MOVES_SMALLER, MOVES_LARGER or NO_DETECTED_SHIFT, with _CENSORED if any point is at a ladder end.

**Primary B: interior peak (finding 1).**
- Per draw and primary epoch:
  - Rise = mean p* over the central rungs {128, 192} − p*(64);
  - Fall = mean central p* − p*(384);
  - End = p*(384) − p*(64).
- Each draw's Rise, Fall and End are averaged over its defined primary epochs, with at least 6 of 7 required.
- Labels, in this order:
  - **INTERIOR_PEAK** if the intervals of both Rise and Fall lie above 0;
  - **MONOTONE_RISING** if End lies above 0;
  - **MONOTONE_FALLING** if End lies below 0;
  - otherwise **NO_DETECTED_SHAPE**.
- The fixed central window makes the test conservative for a peak at 96 or 256.

**Saturation rule (both primaries; as in the follow-up).**
- **S1.** A point is flagged if any of its fits is ≥ 7.999.
- **S32.** Required whenever a point is flagged: the point is refitted with bound 32 and the location, Rise, Fall and End are recomputed.
- **Unresolved refit.** A refit fit ≥ 31.999 within the refit's argmax ± 1 bracket.
- **SD.** Flagged points are dropped. A draw needs at least 3 points left, and SD needs at least 3 draws. SD is required if more than 25% of the 70 nominal points (18 or more) are flagged, or if any refit is unresolved.
- **Decision order.**
  1. UNDEFINED if a draw is unavailable or ineligible;
  2. SATURATED if any required sensitivity cannot be computed;
  3. SATURATION_SENSITIVE if any required sensitivity's label differs from the primary label;
  4. otherwise the primary label.

**Secondaries (non-gating).**
- Per-epoch panel shape labels and peak widths.
- A two-point change E8 → E32.
- Train and validation NLL with the memorization gap.
- Clipping.
- J(p*) and J(0).
- The pre-training E0 losses.

## 5. Budget, memory and storage (`NATURAL_TEXT_BUDGET_r2.json`)

**Anchors** (measured in the follow-up benchmark, FP32, TF32 off):
- about 1.19 TFLOP/s effective at 384/4;
- a per-update floor of 15.5 ms;
- 0.90 GB of device memory in use with the smallest model loaded.

Batch 16 × 128 tokens = 2,048 tokens per update; the floor is assumed unchanged. Scenarios use the measured rate, with ×2 and ×½ bounds.

| Width (depth 4) | Parameters | Memory estimate (batch 16) | With the measured 0.90 GB in use | Margin to the 2 GiB guard | Minutes per draw, planning (range) |
|---:|---:|---:|---:|---:|---:|
| 64 | 732,416 | 0.27 GB | 1.17 GB | 0.98 GB | 1.3 (1.1–1.6) |
| 96 | 1,246,080 | 0.31 GB | 1.21 GB | 0.93 GB | 1.6 (1.2–2.2) |
| 128 | 1,858,048 | 0.36 GB | 1.26 GB | 0.89 GB | 1.9 (1.4–2.9) |
| 192 | 3,376,896 | 0.45 GB | 1.35 GB | 0.79 GB | 2.8 (1.9–4.7) |
| 256 | 5,288,960 | 0.55 GB | 1.46 GB | 0.69 GB | 4.0 (2.5–7.1) |
| 384 | 10,292,736 | 0.78 GB | 1.68 GB | 0.47 GB | 7.1 (4.0–13.4) |
| *512 (excluded)* | *16,869,376* | *1.02 GB* | *1.93 GB* | *0.22 GB* | *11.4 (6.2–21.8)* |

**Two owner runs**, each inside the existing 6-hour envelope:

| Run | Content | Planning | Range (2× faster to 2× slower) |
|---|---|---:|---:|
| **A** | Outcome-blind benchmark probe, then learning-rate tuning on the tuning draw (validation NLL only) | 0.85 h | 0.55–1.46 h |
| **B** | 10 analysis draws × 6 widths, with the frozen learning rates | 3.12 h | 2.03–5.32 h |
| Total | | 3.98 h | 2.58–6.78 h |

- **Storage.** About 0.86 GiB: E0 states for every draw and width, plus per-sequence loss arrays. D: had 6.19 GiB free on 28 Oct.
- **Why 512/4 is excluded.** Its estimated guard margin is only 0.22 GB, and adding it would bring the total to about 6.4 h.
- **Memory check.** The memory figures are estimates. Run A's outcome-blind benchmark measures the real peak per width before any weighted training. If a width would exceed the guard, the run stops there under the existing fail-closed rule: no width is swapped and the guard is not raised.
- **Against revision 1** (batch 32, about 2.2 h for six widths). The increase comes from the pre-training, the nine readouts, the tuning draw and twice as many updates at the per-update floor.

## 6. What each outcome would mean (fixed now)

| Primary A (shift) | Primary B (shape) | Meaning |
|---|---|---|
| MOVES_SMALLER | INTERIOR_PEAK | Both findings (1) and (2) are reproduced in direction on natural text, for small models from a weight-invariant baseline. The synthetic pattern carries over to real text at this scale; no large-model claim follows. |
| MOVES_SMALLER(_CENSORED) | MONOTONE_* or NO_DETECTED_SHAPE | The location moves smaller, but no interior peak is established within 64–384 at depth 4. With _CENSORED, at least one location is only a bound. Finding (2)'s direction is consistent; finding (1) is not reproduced. A wider ladder would need its own protocol. |
| NO_DETECTED_SHIFT | INTERIOR_PEAK | An interior peak without a detected shift: finding (1) reproduced, finding (2) not detected with 10 draws. This is not a claim of absence, and it departs from the synthetic result. |
| MOVES_LARGER | any | The shift goes the opposite way to finding (2) in this setting. It is reported as contrary, with the epoch range and the regime stated. |
| NO_DETECTED_SHIFT | MONOTONE_* or NO_DETECTED_SHAPE | Neither finding is reproduced on natural text at this scale under this recipe. The synthetic results do not transfer here. |
| SATURATION_SENSITIVE or SATURATED (either primary) | — | The answer depends on fits at the p = 8 bound, or the drop-flagged check cannot be computed. No directional claim is made. A wider-bound estimator protocol would be the next question. |
| UNDEFINED (either primary) | — | Draws were unavailable or ineligible, for example from nonpositive total gain. No claim; the undefined fits are reported and diagnosed. There are no replacement draws. |

Every outcome is reported together with the memorization gap, clipping and the E0 losses. Large widths will memorize much of 196,608 tokens over 32 epochs, which is the regime where weighting matters, but it limits generalization claims.

## 7. Steps before any run (each needs owner approval)

1. Approve this design, including the open choices below.
2. Outcome-blind preparation and freeze:
   - tokenizer training and token counts;
   - the registry draw (article partition and seeds) and the final N;
   - the versioned source: model with a vocabulary parameter, data pipeline, worker, and an analysis adapted from `shift_analysis`;
   - the frozen protocol;
   - native fixtures.
3. Independent review.
4. **Run A**: benchmark probe and learning-rate tuning. Freeze the selected rates.
5. **Run B**: ten analysis draws, no retry, then the frozen offline analysis and a read-only verification.

## 8. Open choices for the owner (recommended defaults in brackets)

- **Learning-rate selection:** [per width] or one shared rate for all widths.
- **Learning-rate grid:** [{3e-5, 1e-4, 3e-4}].
- **Number of analysis draws:** [10]. 12 would also fit the corpus estimate but leave no spare groups.
- **Uniform reference arm (U):** [excluded]. Including it doubles Run B.

## 9. Limits

- **One corpus.** One encyclopaedia corpus. Draws are disjoint article sets, but the pre-training and validation pools are shared.
- **No mechanism.** There are no component labels, so no mechanism decomposition.
- **Scale.** Small models (0.73–10.29 M parameters), depth 4, a 4,096-token vocabulary. No large-model or scaling claim follows.
- **Shared with the follow-up:**
  - fixed epochs mix capacity with progress;
  - one constant-learning-rate trajectory per draw is read at several epochs;
  - fits can saturate near p = 8;
  - clipping is likely to be frequent.
