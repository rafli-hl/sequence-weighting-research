# Owner decisions on the few-epoch draft: D1–D7 accepted, two design changes, and the build sequence

**Date:** 1 Nov 2026. **Applies to:** `reports/natural-text-fewepoch-proposal-20261101-01/PROPOSAL_DRAFT.md` (decision 20261101-01).

## Owner message (verbatim)

> Decisions D1-D7: accepted as you recommended. Two design changes before building:
> 1. Add a primary that discriminates the memorization-only account: per draw, p* at 768 minus p* at 384 at matched train-validation gap (interpolated across the readouts E0.25-E3 within each width), averaged over matched gap levels both widths reach; label CAPACITY_BEYOND_MEMORIZATION if the 95% interval is below 0, CAPACITY_ABOVE_MEMORIZATION if above, otherwise NOT_DETECTED. Memorization-only predicts NOT_DETECTED. State the confound in advance: at matched gap the larger width has had fewer epochs. Motivation (exploratory, seen panel means from the one-rate run): at gap 0.25 and 0.5, 768 is about 0.016-0.02 below 128-512, which are nearly equal. Verify this from ANALYSIS.json and include it as context, labelled exploratory.
> 2. Replace the fixed sequence with Holm across three primaries at family-wise 95%: the matched-gap test, the fall over 384-768 at E3, and the rise over 64-384 at E3. Drop the peak-shift primary to a secondary, since the seen early-epoch peak moved to larger widths.
> Give power and false-positive fixtures for the new primary, including a memorization-only curve. Then the usual sequence: acquisition package first, then source, tests, one scoped review, stop for my approval.

## Decisions as recorded

1. **D1–D7 accepted as recommended:**
   - D1: N = 16,384 sequences per draw;
   - D2: n = 10 fresh draws, in B1 and B2 runs of 5 + 5;
   - D3: NOT_OVERFIT as drafted (E3 against E2, per-primary width sets);
   - D4: rate grid 3e-5, 1e-4, 3e-4, 1e-3, with eligible rates only and the lowest mean E3 validation NLL;
   - D5: no eligible rate → Run A repeated once at 2N after a time re-check, otherwise stop; a top-edge selection → the grid extended once to 3e-3;
   - D6: acquisition in three steps (A1–A3), with gzip rows and the full token array;
   - D7: a constant rate.
2. **A new primary, the matched-gap contrast:** p\* at 768 minus p\* at 384 at matched train–validation gap, with labels CAPACITY_BEYOND_MEMORIZATION, CAPACITY_ABOVE_MEMORIZATION and NOT_DETECTED. Its confound is stated in advance. Its motivation is verified from the one-rate ANALYSIS.json and reported as exploratory.
3. **Holm across three primaries at family-wise 95%:** the matched-gap contrast, the fall over 384–768 at E3, and the rise over 64–384 at E3. The peak shift becomes a secondary.
4. **Power and false-positive fixtures** for the new primary, including a memorization-only curve.
5. **Sequence:**
   1. the acquisition package;
   2. the study source;
   3. fixture tests;
   4. one scoped review;
   5. a stop for the owner's approval.

   Nothing is downloaded, drawn or run before that approval.
