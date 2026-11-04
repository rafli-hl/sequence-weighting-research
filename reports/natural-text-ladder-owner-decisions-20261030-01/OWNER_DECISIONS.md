# Owner decisions on the next natural-text study (one learning rate, ladder above 384)

**Date:** 30 Oct 2026. The decisions were given after the revision 05 result and the EXPLORATORY note had been seen. The study they define is therefore motivated by that seen result and is disclosed as such.

**Applies to:** the draft `reports/natural-text-ladder-next-study-proposal-20261029-01/PROPOSAL_DRAFT.md` (sha256 7308abc41a355c0703e9b214eb41843b66e43efde274a14a4b0815ec68657771), and its planning numbers in `ESTIMATES.json` (3b08571ee89e0d4b3337c96c49d4ed03ce77b1c032e9e5df7d6aeaa7c41e5755). Both are left unchanged.

## Owner message (verbatim)

> Decisions for the next study:
> 1. Draws: R1 (same ten draws, extension, disclosed as such).
> 2. Ladder top: 512 and 768. First prepare the separately approved memory and timing measurement for 768 (about 15 minutes), then stop. If 768 does not fit under a 2.5 GiB guard with margin, fall back to 512 and record why.
> 3. Rate: 3e-5 fixed for every width. Pre-register the under-training limitation at 64 and 96.
> 4. Storage: record new model files by hash, not kept.
> 5. Primaries, each with direction-specific labels and df-9 intervals over the ten draws, epochs E4-E32 as before:
>    - Turn-down: per-draw slope of p* on log2 width over 384, 512, 768 (TURNS_DOWN if the interval is below 0, CONTINUES_RISING if above, otherwise INCONCLUSIVE).
>    - Dip at one rate: slope over 64, 96, 128 at 3e-5 (DIP_PERSISTS if below 0, NO_DIP_AT_ONE_RATE if above, otherwise INCONCLUSIVE).
>    - Add a pre-registered third primary, the memorization hypothesis: at each fixed epoch, the across-width rank correlation between p* and the train-validation gap over all eight widths, averaged over E4-E32 per draw, with a df-9 interval (TRACKS_MEMORIZATION if above 0). Do not pool across epochs.
>    State the prediction of each hypothesis in advance: memorization predicts CONTINUES_RISING and NO_DIP_AT_ONE_RATE; the Jane Street pattern predicts TURNS_DOWN.
> Include fixture-based power and false-positive checks for all three, as before. Then the usual sequence: seal, tests, one scoped review, stop for my approval.

## Decisions as recorded

1. **Draws: R1.** The same ten draws d01–d10 (registry 8ce7d597…), as an extension of the revision 05 Run B, disclosed as such. It is not a fresh replication: Run B's results at 128–384 at 3e-5 have been seen.
2. **Ladder top: 512 and 768, after a separately approved probe.**
   - **First step:** a memory and timing measurement for 768 (about 15 minutes), prepared and then stopped for approval.
   - **Fallback:** if 768 does not fit under a 2.5 GiB guard with margin, the ladder falls back to 512, and the reason is recorded. The margin and the fit rule are fixed in the probe's preparation, before it is run.
3. **Rate: 3e-5 for every width.** The under-training limitation at 64 and 96 is pre-registered. On t00 in Run A, both widths reached their lowest validation NLL at 3e-5 at E32, the last readout (`AMENDMENT_01.md` §2).
4. **Storage:** new model files are recorded by sha256 and size and are not kept.
5. **Primaries.** There are three, each with direction-specific labels and a df-9 interval over the ten draws, on epochs E4–E32:
   - **Turn-down:** the per-draw slope of p* on log2 width over 384, 512 and 768. Labels: TURNS_DOWN if the interval lies below 0, CONTINUES_RISING if it lies above 0, otherwise INCONCLUSIVE.
   - **Dip at one rate:** the per-draw slope over 64, 96 and 128 at 3e-5. Labels: DIP_PERSISTS if below 0, NO_DIP_AT_ONE_RATE if above 0, otherwise INCONCLUSIVE.
   - **Memorization:**
     - At each fixed epoch: the rank correlation, across all eight widths, between p* and the train-validation gap.
     - Per draw: those correlations averaged over E4–E32, never pooled across epochs.
     - The interval is df-9. Label: TRACKS_MEMORIZATION if the interval lies above 0. The labels for the other outcomes are fixed in the protocol.
   - **Predictions, stated in advance:**
     - Memorization predicts CONTINUES_RISING and NO_DIP_AT_ONE_RATE.
     - The Jane Street pattern predicts TURNS_DOWN.
6. **Checks and process.**
   - Fixture-based power and false-positive checks for all three primaries, as before.
   - Then the usual sequence: seal, tests, one scoped review, and stop for the owner's approval.

## Sequence

1. Prepare the 768 memory and timing probe (fixture tests and independent review), then stop for its approval. The owner runs it.
2. Decide the ladder top from the probe under its pre-fixed rule. If 768 does not fit, fall back to 512 and record why.
3. Build the study source with the three primaries and their power and false-positive fixtures. Then seal, test, hold one scoped review, and stop for approval.
