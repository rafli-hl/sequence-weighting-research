# Owner decisions on tied weights and the real-engine check

**Date:** 2 Nov 2026. **Applies to:** the two decisions asked in `reports/natural-text-fewepoch-runa-package-20261102-01/REPORT.md`, section 9.

## Owner message (verbatim)

> Option 1, add the check.
> 1. Replace the exact-tie refusal with the limit of n / 1,024 tied values. Ties keep a deterministic order: a stable sort by sequence index, so p* is bit-for-bit reproducible. Update the estimator docstring and add a test with real tied weights that confirms identical p* on repeated runs.
> 2. Add the real-engine check before Run A: the real-input check on CPU with real Torch on all eleven seeds, and the GPU smoke test on two small widths with synthetic tokens and test seeds, writing only to scratch, reading no loss. Package both for me to run.
> 3. Fix the two weak tests, record the real overlap figures (mean 0.74%, max 1.89% in d04, 10 identical-text sets across groups) for the disclosure, re-test, narrow re-review of the fix only, pin the builder, and stop for my approval with hashes, commands and the disk check.

## Instructions as recorded

1. **Tied weights: option 1.** The exact-tie refusal in `text_engine.weights` becomes a limit of n / 1,024 tied values. The weights stay exactly as drawn.
2. **Deterministic order.** Ties keep a stable sort by sequence index. The estimator's docstring is updated, and a test with real tied weights confirms identical p\* on repeated runs.
3. **The real-engine check, packaged for the owner to run, before Run A:**
   - the real-input check, on CPU with real Torch, on all eleven seeds;
   - the GPU smoke test, on two small widths, with synthetic tokens and test seeds, writing only to scratch, reading no loss.
4. **The two weak tests are fixed** (`test_runa_package.py` tests 04 and 11; review findings of 2 Nov 2026).
5. **The real overlap figures are recorded for the disclosure:** mean 0.74%, maximum 1.89% in d04, 10 identical-text sets across groups.
6. **Then:** re-test, a narrow re-review of the fix only, pin the builder, and stop for the owner's approval with hashes, commands and the disk check.

## How the terms are used

- **Tied values:** n minus the number of distinct values. This is the count already reported (`WEIGHT_TIES_CHECK.json`): t00 has 2 at N = 16,384. The limit is 16 at N = 16,384.
- **Reading no loss:** the check's own code neither reads nor reports a loss value. The sealed stage code it exercises cannot train without computing losses, so that code computes them on the synthetic tokens and writes them into scratch, as it does in any stage.
