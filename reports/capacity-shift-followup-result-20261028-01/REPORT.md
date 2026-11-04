# Capacity-shift follow-up: result

28 October 2026.
- **Run.** One owner run under approval OWNER-20261027-FOLLOWUP-01: COMPLETE, exit 0, no retry.
- **Verification.** Read-only, `VERIFICATION.json` run 02: **23/23 PASS**. Run 01 failed one reconciliation check and is preserved in `run-01-check-error/` (section 8).
- **Analysis.** The sealed `shift_analysis.py`, re-run from the activation copy, reproduces all four analysis files byte for byte.

Every number below is in `RESULT_SUMMARY.json`, extracted by `summarize_followup_result.py` from the frozen `ANALYSIS.json`. Labels:
- **FROZEN**: a pre-registered rule (PROTOCOL.md revision 02, subject d93eee95…).
- **SECONDARY**: a frozen rule that does not gate the decision.
- **DESCRIPTIVE**: reported without a decision rule.

Slopes are in log2 width per doubling of epochs; locations are in log2 width.

## 1. Frozen decision

**MOVES_SMALLER** (G16, full weighting R; not censored).

The capacity at which p* peaks moved to smaller widths as adaptation continued from E15 to E40. This holds on twelve fresh corpora drawn after the protocol was frozen. It is the direction of Jane Street's finding (2), shown here in one synthetic task family. The saturation rule required both sensitivities, and both agree with the primary (section 2).

## 2. Primary and saturation sensitivities (FROZEN)

| Readout | Label | Mean slope | SD | 95% t interval | Corpora | Negative |
|---|---|---:|---:|---|---:|---:|
| **Primary, R** (E15/E20/E25/E30/E40) | **MOVES_SMALLER** | **−0.796** | 0.293 | **[−0.982, −0.609]** (df 11) | 12 | 12/12 |
| S32: flagged points refitted with bound 32 | MOVES_SMALLER | −0.817 | 0.272 | [−0.990, −0.644] (df 11) | 12 | — |
| SD: flagged points dropped | MOVES_SMALLER | −0.794 | 0.206 | [−0.966, −0.622] (df 7) | 8 | — |

**Points.**
- 59 of 60 corpus-epoch points are defined.
- The undefined point is c01 at E15, where the 256/4 fit had nonpositive total gain. c01 keeps an eligible slope from its 4 remaining points.
- No defined point has a boundary location, so the label carries no _CENSORED suffix.

**Why both sensitivities were required.**
- 19 of 60 points were flagged (31.7%, above the 15-point gate).
- 2 of the 19 bound-32 refits were unresolved, each with one fit at 32 (c04 E20 and c10 E15).

**How the sensitivities came out.**
- The refits moved the flagged locations by +0.051 on average (largest |change| 0.450).
- SD dropped c01, c03, c04 and c10; each kept fewer than 3 unflagged points.
- All three readouts are negative with intervals well below 0.

**Arithmetic on the estimate (descriptive).** −0.796 log2 width per doubling of epochs corresponds to the peak width shrinking by a factor of 2^−0.796 ≈ 0.58 for each doubling of epochs. Over E15 → E40 (1.415 doublings), that is about 2^−1.126 ≈ 0.46.

## 3. Frozen secondaries (SECONDARY)

| Readout | Label | Mean | SD | 95% t interval | Negative |
|---|---|---:|---:|---|---:|
| S_batch slope (primary epochs; no flagged points, no sensitivity required) | MOVES_SMALLER | −0.851 | 0.131 | [−0.934, −0.768] | 12/12 |
| **R − S_batch slope difference** (primary epochs) | **NO_DETECTED_DIFFERENCE** | +0.055 | — | [−0.128, +0.237] | — |
| R − S_batch slope difference (E15–E30) | NO_DETECTED_DIFFERENCE | +0.097 | — | [−0.236, +0.430] | — |
| R slope, E15–E30 window (S32 −0.939; SD on 7 corpora −1.085; both MOVES_SMALLER) | MOVES_SMALLER | −0.922 | 0.440 | [−1.201, −0.642] | 12/12 |
| S_batch slope, E15–E30 window | MOVES_SMALLER | −1.018 | 0.250 | [−1.177, −0.860] | 12/12 |
| Two-point Δℓ E20 → E30, R (6 flagged points among the 24 used) | MOVES_SMALLER | −0.498 | 0.321 | [−0.702, −0.294] | 11/12 |
| Two-point Δℓ E20 → E30, S_batch | MOVES_SMALLER | −0.313 | 0.209 | [−0.445, −0.180] | 11/12 |

The shift appears under S_batch too, with a similar slope, and no R − S_batch difference was detected.

## 4. Per-epoch peak widths (DESCRIPTIVE)

Twelve-corpus panel curves. The argmax rung is shown with the parabola-vertex location, written as a width 2^ℓ. A panel is UNDEFINED if any of its 96 fits is undefined. The shape labels use the protocol §6 rule, which has no bootstrap gate.

| Epoch | R label | R argmax (vertex) | R undefined fits | S_batch label | S_batch argmax (vertex) | S_batch undefined fits |
|---|---|---|---:|---|---|---:|
| E1 | UNDEFINED | — | 43 | UNDEFINED | — | 35 |
| E3 | UNDEFINED | — | 1 | UNDEFINED | — | 1 |
| E5 | UNDEFINED | — | 1 | PLATEAU_OR_INCONCLUSIVE | 256 (290) | 0 |
| E10 | UNDEFINED | — | 2 | RISING_TO_LARGEST | 384 (384) | 0 |
| E15 | UNDEFINED | — | 1 | INTERIOR_PEAK | 256 (237) | 0 |
| E20 | INTERIOR_PEAK | 192 (163) | 0 | INTERIOR_PEAK | 128 (144) | 0 |
| E25 | INTERIOR_PEAK | 128 (134) | 0 | INTERIOR_PEAK | 128 (123) | 0 |
| E30 | INTERIOR_PEAK | 96 (110) | 0 | INTERIOR_PEAK | 96 (108) | 0 |
| E40 | INTERIOR_PEAK | 96 (98) | 0 | INTERIOR_PEAK | 96 (92) | 0 |

The R panel at E15 is UNDEFINED because of the single undefined c01 fit. The primary slope does not use panels: it uses each corpus's own curve, and c01 keeps 4 points.

## 5. Saturation counts by epoch (FROZEN counts, primary R)

| | E15 | E20 | E25 | E30 | E40 | Total |
|---|---:|---:|---:|---:|---:|---:|
| Flagged points (of 12 corpora; c01 E15 undefined) | 9 | 5 | 4 | 1 | 0 | 19 / 60 |
| Fits at the upper bound within defined points | 15 | 11 | 5 | 2 | 0 | 33 |

**Where saturation sat (descriptive).**
- Fits at the bound fall at the larger widths. At E15 the panel counts are 3/6/5/4 at 128/192/256/384, including the 3 fits inside the undefined c01 point.
- Saturation is gone by E40.
- S_batch had no flagged point at any primary epoch. Its only fits at the bound were 2 at E1.

**Against the exposed ladder (descriptive).** Over E15–E30 the flagged rate was 19/48 = 39.6% of points, against 20% (4/20) on the five exposed corpora.

## 6. Training, memorization, clipping and progress (DESCRIPTIVE)

**Memorization grows with width and epochs.** Means over 12 corpora, R:

| Rung | Epoch | Train NLL | Validation NLL | Gap | Instance validation NLL |
|---|---|---:|---:|---:|---:|
| 32/4 | E15 | 2.321 | 2.334 | 0.012 | 2.826 |
| 32/4 | E40 | 2.182 | 2.234 | 0.052 | 2.864 |
| 128/4 | E15 | 1.816 | 2.021 | 0.205 | 3.113 |
| 128/4 | E40 | 1.655 | 2.504 | 0.849 | 3.936 |
| 384/4 | E15 | 1.727 | 2.536 | 0.809 | 4.051 |
| 384/4 | E40 | 0.716 | 3.065 | 2.349 | 5.569 |

**R − S_batch validation NLL (df 11).**
- Above 0 at 32/4, 96/4 and 128/4 at E15, E30 and E40, so R is worse there. At 128/4, E40: +0.178 [+0.149, +0.208].
- At 384/4 it reverses: +0.337 at E15, but −0.103 [−0.148, −0.058] at E40.

**Clipping.**
- The clip-1 threshold is active on almost every update: the mean clip fraction is 0.89–1.00 in every summarized cell, and 1.00 over E31–E40 at 32/4 and 128/4.
- Mean gradient norms over E31–E40 are 2.3–10.3.
- Clipping is therefore part of every weighting intervention here.

**Group progress.**
- P = 0.10 was crossed in all 12 corpora at 96/4 and wider, in some corpora at 48/4 and 64/4, and never at 32/4.
- P = 0.50 was crossed in all 12 corpora at 384/4 (median update 464), and at 256/4 in 9/12 (R) and 3/12 (S_batch) corpora.
- P = 0.90 was never crossed.
- Larger models learn faster, so fixed epochs mix capacity with progress.

**Validation-selected view.** The lowest validation NLL fell at E0 for 33/96 R and 22/96 S_batch trajectories, and at E40 for 12 and 16. Selection is not used for any readout; the p* readouts are at fixed epochs by design.

## 7. Jane Street comparison

| Jane Street finding | This study (G16, synthetic, depth-4 widths 32–384) | Status |
|---|---|---|
| (2) More epochs move the p* peak to smaller models | Per-corpus peak-location slope −0.80 log2 width per doubling of epochs, 95% [−0.98, −0.61], 12/12 fresh corpora. The result holds under both saturation sensitivities. Panel peak (descriptive): 192/4 at E20, 128/4 at E25, 96/4 at E30–E40. | **Reproduced in direction**, pre-registered, on fresh corpora, in this synthetic setting. The same direction holds under S_batch, with no detected R − S_batch difference. Not tested at Jane Street's scale, on natural text, or with horizon-tied learning-rate schedules. |
| (1) p* rises then falls with model size (context) | Panel shape labels INTERIOR_PEAK at E20–E40 under R and at E15–E40 under S_batch | Descriptive only: no bootstrap gate and no fresh-corpus gating rule for finding (1) in this protocol. |

## 8. Limits and verification

**What the result does not show.**
- **Mechanism.** The shift appears with S_batch, which removes the instance coefficient's within-batch weight heterogeneity, and no R − S_batch difference was detected. So in this design the shift does not require that heterogeneity. The cause is not identified.
- **Progress confound.** Larger widths progress faster, and fixed epochs do not match progress.
- **One trajectory per corpus.** E15–E40 are checkpoints of one constant-learning-rate trajectory per corpus, not separate runs of those lengths.
- **Exposed motivation.** The direction and the epoch window were seen in the exposed ladder (E15–E30 R slope −1.043 on 5 corpora). The fresh value, −0.922, is smaller in magnitude. This study confirms a pattern seen before; it is not an independent discovery.
- **Scope.** One task family, fixed depth 4, heavy clipping and strong memorization at large widths. No claim about large language models, natural text or a scaling law follows.

**Verification.** `VERIFICATION.json`, run 02: 23/23 PASS. It checked:
- **Bindings.** The subject and every bound file in the activation and the source; the builder hash ad0480cb…; the approval text and id; the six evidence pins; the authorization bindings.
- **Registry.** Re-derived from its draw: 61 of 256 candidates accepted, none rejected before the 61st acceptance, against 4,046 exclusion values.
- **Activation.** The manifest was ARMED_UNUSED at build time, and only the owner claim, receipt and logs were added afterwards.
- **Timing.** Owner receipt COMPLETE, exit 0, terminal 00eb9807…. Worker 4,355.5 s and owner wall time 4,839.9 s, against 21,600 s. Benchmark projection 519.7 s per stage, cap 900 s; stages took 232–468 s.
- **Storage.** 993,523,223 bytes in 638 files, against 3 GiB / 1,000. Each stage has 50 files and about 68.9 MB.
- **Peaks.** Sampled GPU 1.17 GB and worker RSS 1.57 GB, against 2 GiB / 4,032 MiB.
- **Records.** 192 records with 49 checks and 40 epochs, with array bindings; no landmark states; 147,456 updates; 174,744 evaluation batches, equal to the recomputation from the records (147 landmark validations).
- **Read-only.** All trees were unchanged by the verification.

**Run 01 of the verifier (preserved).** It required the run tree to equal the final inventory plus TERMINAL.json exactly. It failed by one file of 2,355 bytes. That file had left `cache/`, the library temporary directory, after the final inventory. The ladder verification saw the same thing, also 2,355 bytes. Run 02 states the vanished file explicitly and confirms that `cache/` is now empty.

**Files here.**
- `verify_followup_result.py` → `VERIFICATION.json`
- `summarize_followup_result.py` → `RESULT_SUMMARY.json`
- `analysis-rerun/` and `analysis-rerun.log`
- `run-01-check-error/`
- `NATURAL_TEXT_LADDER_PROPOSAL.md` (a proposal only; not built)
