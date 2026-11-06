# An assistant check beside the result: not a sealed result

**Filed:** 6 Nov 2026, at the owner's instruction (`reports/natural-text-ladder-owner-decisions-20261106-01/OWNER_DECISIONS.md`). **Its record:** [`recompute.py`](../natural-text-matched-assistant-recompute-20261106-01/recompute.py) (`b1e822eebf863bc0f65b3a8da0ff114d217b9d04181f3206eb8d24a5e498aa4b`) and [`RECOMPUTE.json`](../natural-text-matched-assistant-recompute-20261106-01/RECOMPUTE.json) (`24a512928a3e8ce5b6cb0185660c8b7a463bc151eb3a35525ccf97320aad5b78`).

**What it is.** A post-hoc recomputation from `POINTS.csv`, run by the assistant from the chat on the owner's laptop. That is a different session from the one that ran the frozen layout and the verifier. It is not part of `RESULT.md` or `RESULT_VERIFICATION.json`, and it changes no label, interval or reading.

**What it cannot reach: p\*, the losses, E0 or clipping.** `POINTS.csv` holds p\* and the losses as the sealed analysis wrote them, and those values need the run files under `work/runs/`. So it checks the arithmetic downstream of `POINTS.csv`, as the verifier does, and it cannot find an error in the sealed analysis's reading of the run files.

## What it recomputes

| Statistic | Mean and 95% interval, df 5 | Draws < 0 / > 0 | Against `ANALYSIS.json` |
|---|---|---|---|
| **P1** | +0.00909 [+0.00400, +0.01417] | 0/6 | Equal |
| **S1** | +0.00808 [+0.00487, +0.01130] | 0/6 | Equal |
| **S3** | −0.00454 [−0.00795, −0.00114] | 6/0 | Equal |
| **S4** | +0.01394 [+0.00893, +0.01896] | 0/6 | Equal |
| **S5** | +0.01382 [+0.01116, +0.01648] | 0/6 | Equal |
| **S2** | No interval: 3 draws, and 5 are needed | Not read | Same three draws, and not read |

**Checked by the session that filed it.** The script opens only the one `POINTS.csv` it is given, prints JSON and writes nothing. Run again on that file, it reproduces the values in `RECOMPUTE.json`. Its means, interval limits and sign counts for those five statistics, and its per-draw contrasts and brackets for P1, S1 and S4, equal `ANALYSIS.json` with a largest difference of 0.

## The bound on the epoch boundary

**With 768 read at the higher p\* of its bracket in every draw, P1 is +0.00702 [+0.00216, +0.01189], 5/6 positive.** The one negative draw is m06, at −0.00057. The session that filed this got the same figure in separate code, to within 7e−13.

**Post hoc, and not a label.** P1 remains REVERSAL_CONFIRMED at +0.00909 [+0.00400, +0.01417], as sealed. The higher end is the reading least favourable to a reversal, but only if p\* stays between the two readouts around it, and nothing inside E2.0–E2.25 can show that yet. The bound also does not say whether comparing different points in the epoch is the right comparison.

**The owner has decided not to pursue this.** It is recorded as a limitation, with readouts inside E2.0–E2.25 as future work, in [the note on claims 4 and 5](../adversarial-review-response-note-20261106-01/CLAIMS_4_AND_5_STATUS.md). Nothing is authorized.
