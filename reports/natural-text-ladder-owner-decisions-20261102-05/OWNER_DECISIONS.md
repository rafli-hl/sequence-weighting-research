# Owner report of Run A, and the instruction for the B1/B2 package

**Date:** 2 Nov 2026.

## Owner message (verbatim)

> Run A COMPLETE: selected rate 3e-4 (all five rates eligible, none diverged, no grid extension), terminal 3062a888…; output below. Verify from the records, without opening anything beyond Run A's selection and status fields.
> Then build the B1/B2 package as frozen: rate 3e-4 for all widths, draws d01-d05 in B1 and d06-d10 in B2, the power and GPU gates, the counting rule, and the sealed analysis with M, FALL and RISE under Holm and the NOT_OVERFIT check per draw. Recompute the time and disk budget from Run A's measured timings. Fixture tests, one scoped review of what changed, and stop for my approval with hashes, commands and the disk check.

The output did not come through with that message. The owner then sent it: "this is the ouput:" followed by the console output in `reports/natural-text-fewepoch-runa-result-20261102-01/OWNER_CONSOLE_OUTPUT.txt`.

## Instructions as recorded

1. **Verify Run A from the records,** opening nothing beyond its selection and status fields.
2. **Build the B1/B2 package as frozen:**
   - rate 3e-4 for all widths;
   - draws d01–d05 in B1 and d06–d10 in B2;
   - the power and GPU gates, and the counting rule;
   - the sealed analysis: M, FALL and RISE under Holm, and the NOT_OVERFIT check.
3. **Recompute the time and disk budget** from Run A's measured timings.
4. **Fixture tests, one scoped review of what changed,** and a stop for the owner's approval, with hashes, commands and the disk check.

## How the terms are used

- **Selection and status fields:** `LR_SELECTION.json`; the status fields of `TERMINAL.json` and `OWNER_EXIT_RECEIPT.json`; and, inside the sealed re-derivation only, each record's status, width, rate and E2 and E3 validation NLL, which are the fields the selection itself uses. No training NLL, other readout, gradient or clipping field, per-sequence array or `INPUTS.json` is opened.
- **Run A's measured timings:** the timing, memory and size fields of `BENCHMARK.json`, `t00-RECEIPT.json` and the terminal, none of which holds a loss; file sizes and file times, which need no file to be opened.
- **"The NOT_OVERFIT check per draw":** the frozen check. Per width, Δ = validation NLL at E3 minus E2 is computed per draw, and the verdict comes from the df-9 interval of those ten values (`PROTOCOL.md` section 4). There is no separate verdict for a single draw. The package keeps this as frozen.
