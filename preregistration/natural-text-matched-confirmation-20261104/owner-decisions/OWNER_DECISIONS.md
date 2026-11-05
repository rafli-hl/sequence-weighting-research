# Owner decisions for the matched-progress confirmation (N7)

**Date:** 4 Nov 2026. **Applies to:** `reports/natural-text-matched-preparation-20261104-01/REPORT.md`, source subject `7063a650…`.

## Owner message (verbatim)

> Owner decisions for N7, 4 Nov 2026. Record them in a new reports/natural-text-ladder-owner-decisions-20261104-02/OWNER_DECISIONS.md, then build the next revision. Do not train, and do not open, read or search anything under work/runs/ yourself.
>
> 1. Seed draw approved, as an owner-run step. The owner-run draw script may read the corpus manifest by its exact path under work/runs/ and nothing else there; it must print no outcome data. Build the pin-apply tool and the post-draw disclosure, and give me the PowerShell command for the draw.
> 2. Fixed sequence changed to: P1, S1, S3, S4, S5, S2 (S2 last). Update the protocol, the analysis and the readings, and restate the power table for this order.
> 3. A FAILED Run M1 admits Run M2 if at least 2 of its draws completed. The rule must be mechanical: it counts completed draws from operational records only, with no outcome field inspected. The 5-draw minimum for P1 is unchanged.
> 4. The real-engine check (real Torch, CUDA and WSL on synthetic inputs, no study data) runs BEFORE the public registration. Order: seed draw → pin-only revision and new seal → real-engine check → scoped review → public registration (merged on GitHub, commit hash recorded) → activation → Run M1 → Run M2.
> 5. Confirmed: the four reading forms; NOT_READ for unread steps; reading the completed draws if Run M2 fails, only if P1 has at least 5 available draws; a draw with an undefined fit counts as unavailable, and the count is always reported.
> 6. Build the per-run file checks that are still missing.
> 7. Update NEXT_EXPERIMENT.md, HANDOFF.md and INDEX.md: the experiments are reopened for one study, N7, under these decisions; nothing is authorized beyond the steps above.
>
> Then run one scoped fresh-context review covering only what changed (items 2, 3, 6 and the fixes to findings M1 and M4, which were never re-reviewed). Report the findings and fixes, the SHA-256 of every changed file, and the seed-draw command. STOP before the draw itself. Do not commit.

## As recorded

1. **The seed draw is approved as an owner-run step.** Under `work/runs/`, the draw script may read only the corpus manifest, by its exact path. It prints no outcome data.
2. **The fixed sequence is P1, S1, S3, S4, S5, S2.** The power table is restated for this order.
3. **A FAILED Run M1 admits Run M2 if at least 2 of its draws completed,** counted from operational records only. P1 still needs at least 5 draws.
4. **The order:** seed draw, pin-only revision and new seal, real-engine check on synthetic inputs, scoped review, public registration merged with its commit hash recorded, activation, Run M1, Run M2.
5. **Confirmed:**
   - the four reading forms;
   - NOT_READ for steps not read;
   - the completed draws are read if Run M2 fails, only if P1 has at least 5 available draws;
   - a draw with an undefined fit is unavailable, and the count is always reported.
6. **The per-run file checks** are to be built.
7. **`NEXT_EXPERIMENT.md`, `HANDOFF.md` and `INDEX.md`** are to say that the experiments are reopened for one study, N7, and that nothing is authorized beyond these steps.

**Authorized by this message:** building this revision, one scoped review, and the seed draw by the owner. **Not authorized:** the draw by the assistant, any training, any commit, and any step after the draw until its own approval.
