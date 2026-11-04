# Owner decisions after the 768 probe: ladder top and start-up memory fallback

**Date:** 30 Oct 2026. These decisions were given after the probe's result was seen (`reports/natural-text-ladder-probe-result-20261030-01/RESULT.md`). The probe read no draw, gain, loss or p*, so no study outcome had been seen.

**Applies to:** the next natural-text study defined by `reports/natural-text-ladder-owner-decisions-20261030-01/OWNER_DECISIONS.md` (sha256 2861c25f…), which is left unchanged.

## Owner message (verbatim)

> Probe COMPLETE: FITS_768 (PEAK_WITHIN_LIMIT), terminal 9e486faacb7274fa947601cf61a9b2de874a2612ba07d20a67c7a395a9f17f53. Output below. Record the verdict; the ladder top is 512 and 768 with the 2.5 GiB guard.
> For the study:
> 1. 768 peaked at 2.22 GiB, 0.03 GiB under the fit limit. Add a pre-registered start-up memory fallback: if the study's own start-up benchmark finds 768 above 2.25 GiB, the study switches to the 512 top before any training, decided from memory only, with the reason recorded. Also give the time budget from the probe's measured timings, including whether the B1/B2 split is needed.
> 2. Then build the study source with the three primaries as decided (turn-down 384-768, dip at one rate 64-128, memorization tracking across widths at fixed epochs), their power and false-positive fixtures, seal, tests, one scoped review, and stop for my approval.

No output followed the words "Output below". The quoted terminal hash equals the sha256 of `work/runs/natural-text-ladder-probe-20261030-01/TERMINAL.json`, which `PROBE_READING.json` verified.

## Decisions as recorded

1. **Probe verdict: FITS_768 (PEAK_WITHIN_LIMIT).** It is recorded in `reports/natural-text-ladder-probe-result-20261030-01/`. The study's ladder top is 512 and 768, under a 2.5 GiB sampled-GPU guard.
2. **Start-up memory fallback, pre-registered in the study:**
   - **Trigger:** the study's own start-up benchmark finds 768's peak sampled device memory above 2.25 GiB (2,415,919,104 bytes, the probe's fit limit).
   - **Action:** the study switches to the 512 top before any training, and the reason is recorded.
   - **Basis:** memory only. No draw, loss, gain or p* is read.
3. **Time budget:** from the probe's measured timings, including whether the B1/B2 split is needed.
4. **Study source:**
   - **Contents:** the three primaries as decided in decisions 20261030-01 (turn-down over 384–768, dip at one rate over 64–128, memorization tracking across widths at fixed epochs), with their power and false-positive fixtures.
   - **Process:** seal, tests, one scoped review, then stop for the owner's approval.
