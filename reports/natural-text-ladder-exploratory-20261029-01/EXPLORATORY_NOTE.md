# EXPLORATORY note: natural-text ladder, Run B (revision 05)

> **EXPLORATORY.** This note was written on 29 Oct 2026, **after the result was seen. It is not pre-registered.** It describes ten-draw panel means and computes no interval or test. It changes no pre-registered label or reading. The pre-registered result is in `reports/natural-text-ladder-analysis-20261029-01/REPORT.md`: Primary A NO_DETECTED_SHIFT_CENSORED, Primary B CONVEX.

**Inputs:**
- `reports/natural-text-ladder-analysis-20261029-01/sealed-analysis/ANALYSIS.json`, sha256 4414abfdfb163b393d1c09a4051505985475c63478829267e35c1014533c62a8;
- Run A's `LR_SELECTION.json`, sha256 cb059387dc26f6743199f446940487d55d868700130faa68b9256eb333b2c217.

**Recomputed by** `exploratory_checks.py`, giving `EXPLORATORY_CHECKS.json`. The owner proposed the three statements; the assistant checked each one against these files.

## 1. The CONVEX dip at 128 coincides with the learning-rate change (verified)

- **Rates** (Run A selection, by validation NLL only): 64 at 3e-4, 96 at 1e-4, and 128, 192, 256 and 384 at 3e-5. So 128 is the first width at the lowest rate.
- **The dip.** At every one of the nine readout epochs (E1–E32), the ten-draw panel mean p* is lowest at width 128.
- **The labels.** The by-epoch shape label is CONVEX at all nine epochs. All 10 draws have positive mean curvature.
- **Primary B's vertex.** The vertex of the mean quadratic is log2 7.007 (width 128.6).

## 2. Over 128–384, where the rate is constant, panel-mean p* rises with width at every epoch (verified)

At each of the nine readout epochs, the panel mean p* rises strictly from 128 to 192 to 256 to 384. For example:
- E1: 0.0788, 0.0845, 0.0936, 0.1041;
- E32: 0.1895, 0.2698, 0.3797, 0.5204.

Every one of the 70 primary points has its argmax at 384, the ladder end. That is why Primary A's location is censored at the boundary in every point.

## 3. p* tracks the train-validation gap (verified, with a caveat)

- **The gap** is the mean validation NLL minus the mean train NLL, per width and readout (the sealed `losses` section).
- **Both minima at 128.** Like p*, the gap is lowest at width 128 at all nine epochs. Over 128–384 it also rises with width at all nine epochs.
- **Spearman over the 54 width-epoch panel means** (6 widths × 9 readouts): **0.964** (Pearson 0.965).
- **Caveat: the pooled value is mostly a shared trend over epochs.** Both p* and the gap grow with epochs at every width; the across-epoch Spearman within each width is 1.0 for all six widths. The rank agreement across widths within one epoch is weaker and varies:

  | Epoch | Spearman over the 6 widths |
  |---|---|
  | E1 | 0.60 |
  | E2 | 0.60 |
  | E4 | 0.43 |
  | E6 | 0.60 |
  | E8 | 0.89 |
  | E12 | 0.89 |
  | E16 | 0.94 |
  | E24 | 1.00 |
  | E32 | 1.00 |

  So "about 0.96" holds for the pooled 54 means, but it should not be read as the strength of the width-wise association at a fixed epoch.

## 4. What this does and does not show

- **Descriptive only.** These are panel means of ten draws, chosen for description after the result was seen.
- **Not shown:**
  - that the learning-rate change causes the dip. In this design, width and rate change together at 64, 96 and 128.
  - that memorization causes p*.
  - anything about larger models.
- **A hypothesis consistent with the descriptives (not tested):** the higher rates at 64 and 96 raise both memorization (the gap) and p*. On this hypothesis, at a single rate p* might rise monotonically from 64 to 384, and the CONVEX label would reflect the rate change rather than width. Testing it needs a new pre-registered study at one rate for all widths. A draft is in `reports/natural-text-ladder-next-study-proposal-20261029-01/PROPOSAL_DRAFT.md`.
- **Amendment 01's conditional sensitivity** (all widths at 3e-5 on the same ten draws) was pre-registered to run only if Primary B was INTERIOR_PEAK. It was not triggered. Any similar run now would be a new study motivated by this post-hoc observation, and would be labelled as such.
