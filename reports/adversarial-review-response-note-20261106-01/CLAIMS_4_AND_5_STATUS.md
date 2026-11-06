# Claims 4 and 5 of `RESPONSE.md`: their status after N7

**Date:** 6 Nov 2026. **The owner's instruction:** "RESPONSE.md's claim 4/5 status by a NEW note file (do not edit RESPONSE.md): the matched-progress reversal is now a pre-registered, confirmed result." (`reports/natural-text-ladder-owner-decisions-20261105-03/OWNER_DECISIONS.md`). **Updated the same day** after the owner's next message (`reports/natural-text-ladder-owner-decisions-20261106-01/OWNER_DECISIONS.md`): the assistant check, and the epoch boundary as a limitation.

**What this note changes:** the evidence status of claims 4 and 5 in `RESPONSE.md` section 5, and nothing else. `RESPONSE.md` (`d265bbffca504e7fad7cfba4864c2c338511bca0af7cfdaff5c631aa88600523`) is not edited and claims 1 to 3 are untouched. The wording of claims 4 and 5 stays the owner's, so the "+0.0132, post hoc" in claim 4 remains N6's figure.

**Where the figures come from:** N7's are from [`RESULT.md`](../natural-text-matched-result-20261105-01/RESULT.md) (`ac482f31a60d8d295a4f1e5807b5c882eea0d533f78979a44c22d64023bec3c8`), whose check, `RESULT_VERIFICATION.json` (`16c2aff8073b719bed2ee113834e3b33c05c469a4a87176e088af99906d44688`), reads PASS. That hash is of the local file, and a public copy that redacts a home-path prefix is mapped to it in `PUBLICATION_TRANSFORMATIONS.json`. N6's are from `RESPONSE.md` section 4 and from `reports/natural-text-peak-result-20261103-01/RESULT.md`.

## The status

**The matched-progress reversal at 1e-4 is now a pre-registered, confirmed result, on N7's six fresh draws.** P1 is REVERSAL_CONFIRMED and S3 is CONFIRMED in the fixed sequence. That gives the first form of the sealed reading, quoted from `ANALYSIS.json`:

> "At 1e-4, p* at 512 at E3 is above p* at 768 read at the training NLL 512 reaches at E3 (REVERSAL_CONFIRMED). At fixed updates at E3 on these draws, 768 is above 512, so on these draws the comparison axis reverses the 512-768 ordering at 1e-4. This does not show a capacity mechanism, and nothing about Jane Street's scale follows. Matching on training loss also removes any faster learning of the wider model, so neither axis is privileged."

| Step | 512 − 768 | N7: label | N7: mean and 95% interval, df 5 | N7: draws < 0 / > 0 | N6: same contrast, and its status there |
|---|---|---|---|---|---|
| **P1** | 1e-4, matched on training NLL | **REVERSAL_CONFIRMED** | +0.00909 [+0.00400, +0.01417] | 0/6 | +0.0132 [+0.0106, +0.0158], post hoc |
| **S1** | 1e-4, matched on the gap | **CONFIRMED** | +0.00808 [+0.00487, +0.01130] | 0/6 | +0.0101 [+0.0076, +0.0126], post hoc |
| **S3** | 1e-4, fixed updates | **CONFIRMED** | −0.00454 [−0.00795, −0.00114] | 6/0 | −0.0050 [−0.0090, −0.0010], pre-registered |
| **S4** | 3e-4, matched on training NLL | **CONFIRMED** | +0.01394 [+0.00893, +0.01896] | 0/6 | +0.0177 [+0.0147, +0.0206], post hoc |
| **S5** | 3e-4, fixed updates | **CONFIRMED** | +0.01382 [+0.01116, +0.01648] | 0/6 | +0.0158 [+0.0131, +0.0185], pre-registered |
| **S2** | 1e-4, matched on validation NLL | **UNAVAILABLE** | Not read: 3 of 6 draws have a reading, and 5 are needed | Not read | +0.0187 [+0.0135, +0.0239], post hoc |

**Beside N6, descriptively:** each of N6's five means lies inside N7's interval for the same contrast, and each N7 mean is closer to 0.

## Claim 4, part by part

| Part of the claim | Status in `RESPONSE.md` section 5 | Status after N7 |
|---|---|---|
| At 1e-4, 512 is higher at matched training loss | Post-hoc reanalysis | **Pre-registered and confirmed on fresh draws:** P1 |
| At 1e-4, 768 is higher at fixed updates | Pre-registered, as a fixed-budget fact; fragile under leave-one-out | **Replicated on fresh draws:** S3. **Still fragile:** its interval spans 0 with m03 left out, [−0.00850, +0.00015], or with m05 left out, [−0.00876, +0.00012]. The causal reading of RATE_DEPENDENT stays withdrawn |
| At 3e-4, 512 exceeds 768 at fixed updates | Pre-registered, as a fixed-budget fact | **Replicated on fresh draws:** S5. N7 has no width 384, so the label INTERIOR_PEAK itself is not tested again |
| At 3e-4, 512 exceeds 768 at matched training loss | Post-hoc reanalysis | **Pre-registered and confirmed on fresh draws:** S4 |
| At 3e-4, 512 exceeds 768 matched on the gap and on validation NLL | Post-hoc reanalysis | **Unchanged.** N7 has no such step, so "all three progress matchings" still rests on N6's post-hoc figures for these two |
| The 384→512 rise is mostly training progress | Post-hoc reanalysis | **Unchanged.** N7 has no width 384 |

**The other axes at 1e-4, in `RESPONSE.md` section 4 and not in the claim's wording.** Matched on the gap, S1 is now pre-registered and confirmed. **Matched on validation NLL, the reversal is not confirmed:** S2 is UNAVAILABLE, with m01, m04 and m05 outside 768's path. It is not read and is not evidence either way, and N6's figure stays post hoc. The protocol stated in advance that S2 might be unavailable, and it stops nothing because it comes last.

## Claim 5, part by part

| Part of the claim | Status in `RESPONSE.md` | Status after N7 |
|---|---|---|
| "Comparing widths at equal updates or at equal training loss can reverse the p\* ordering" | Post-hoc reanalysis | **Pre-registered and confirmed,** for 512 and 768 at 1e-4, on these draws: P1 and S3. **At 3e-4 the ordering does not reverse:** 512 is above 768 on both axes (S4 and S5) |
| "cross-width p\* comparisons should report both, or tune per width" | A judgement, with its novelty conceded | **Unchanged.** N7 tests no recommendation and does not tune per width, and the novelty stays conceded |
| The residual at 768: the rate effect on p\*, +0.0047 [+0.0015, +0.0079], 1e-4 minus 3e-4 | Open | **Still open.** N7's figure is +0.00198 [−0.00128, +0.00524], which spans 0. It is descriptive and non-gating, so it is no test of N6's figure |
| The nearest case to tuning per width, D3 | Not in the owner's decisions | **Unchanged.** D3 is not a step of N7 |

## What "pre-registered" means for N7

`RESPONSE.md` defines the word for its own claims as "Pre-specified and hash-sealed locally within one team", and says that only N6 is public, and only after its data existed. **N7 is stronger on that point:** the protocol, the sealed source, the seed registry, the partition and the real-engine check's hashes were published and merged in [PR #5](https://github.com/rafli-hl/sequence-weighting-research/pull/5) (2026-11-05T04:44:28Z) before any activation, and the builder refused without them.

**Its limits, from `RESULT.md` section 7f:** the results report's layout was frozen later and is not in that pull request. The losses already existed when it was frozen. That they were unopened rests on local records and the owner's word, and the public record cannot show it.

## What "confirmed" does not cover

- **The scope.** Two widths (depth 4, 16.9 M and 34.7 M parameters), two rates, E3, six draws of 16,384 sequences, one corpus family. No mechanism is shown, and nothing about Jane Street's scale follows.
- **A choice of axis.** Neither axis is privileged. "Matched" means matched training NLL, not matched gain, and the protocol's limitations explain why those differ.
- **The margins.** The sign counts rest in part on draws near 0: P1 at m06 is +0.00002 and S3 at m02 is −0.00014. P1's interval stays above 0 with any one draw left out, and S3's does not.
- **What the check reaches.** PASS covers the report against the outputs, and the outputs against themselves. p\*, the per-draw losses, E0, clipping and the record-against-array difference are not recomputed, because they need the run files that only the sealed analysis read. An error in that reading that stays consistent with the rest would pass.
- **The assistant check.** The recomputation the owner reported is filed beside the report: [`ASSISTANT_CHECK.md`](../natural-text-matched-result-20261105-01/ASSISTANT_CHECK.md). It was made by the assistant in the chat on the owner's laptop, not by the session that wrote this note. It is not a sealed result. It matches the sealed P1, S1, S3, S4 and S5, and because it reads `POINTS.csv` only, it cannot reach p\*, the losses, E0 or clipping either.
- **Independence.** Every interval treats the draws as independent. They share the validation set, the pool and the tokenizer, and token-level overlaps across them were not measured.

## The epoch boundary: a limitation and future work, not pursued

**The owner decided on 6 Nov 2026 not to pursue this.** It is recorded here as a limitation, with readouts inside E2.0–E2.25 as future work, and nothing is authorized. **It is post hoc, from table 6b of `RESULT.md`. No statistic of the protocol tests it, it moves no label, and no cause is claimed.**

In all four arms, panel p\* rises most in the first quarter after an epoch boundary: +0.01138 to +0.02142 across E2 to E2.25 and E3 to E3.25, against +0.00223 to +0.00693 for each of the other four quarter steps. N6 had no readout between E2 and E3, so it could not show this.

It matters here because P1 compares 512 at E3, the end of an epoch, with 768 at E2.189 to E2.476, partway through the next. Three of the six readings (m01, m04 and m05) interpolate across the step from E2 to E2.25. So matching on training NLL also changes the point within the epoch, and the protocol's limit on interpolation is most exposed there.

**The bound, from the [assistant check](../natural-text-matched-result-20261105-01/ASSISTANT_CHECK.md):** with 768 read at the higher p\* of its bracket in every draw, the reading least favourable to a reversal, P1 is +0.00702 [+0.00216, +0.01189], 5/6 positive (m06 is −0.00057). The interval stays above 0. The bound holds only if p\* stays between the two readouts around it, which nothing inside E2.0–E2.25 can show yet, and it does not say whether comparing different points in the epoch is the right comparison.
