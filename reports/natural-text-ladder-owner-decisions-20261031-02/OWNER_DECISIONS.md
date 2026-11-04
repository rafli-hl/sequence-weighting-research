# Owner decisions on the fresh-draw confirmation draft

**Date:** 31 Oct 2026. The owner made these decisions before any seed of the confirmation exists. No outcome of the confirmation exists.

**Applies to:**
- the draft `reports/natural-text-onerate-confirmation-draft-20261031-01/PROPOSAL_DRAFT.md` (section 11), with its planning record `CONFIRMATION_PLANNING.json`;
- the one-rate result report `reports/natural-text-onerate-result-20261031-01/RESULT.md`.

## Owner message (verbatim)

> Corrections accepted (argmax at E1-E2 is 512; the E24 turn-down rests on 768 alone). Decisions, all as you recommended:
> 1. Draws: N = 1,536 with the existing step-down rule.
> 2. Widths: 256-768.
> 3. P3: parabola-refined peak location. Pre-register that a peak at the top rung (768) is recorded at that rung, so the E8-to-E32 shift is a conservative lower bound, and state it in the readings.
> 4. Multiplicity: fixed sequence E32 turn-down, then peak shift, then E24 turn-down, each at 95%; later tests are read only if earlier ones succeed.
> 5. P2 (E24) stays as the last primary with its power stated in advance.
> 6. Storage: delete each width's state after training.
> 7. Counting rule: as revision 02.
> Also pre-register in the readings that the late-epoch pattern occurs in a heavily overfit regime (best validation loss at E4 for 384-768), unlike Jane Street's 3-epoch setting, so a confirmation supports the pattern in this regime only.
> Proceed: seed draw approval request first, then source, fixture tests, one scoped review, and stop for my approval with hashes and commands.

## Decisions as recorded

1. **Corrections accepted.** The panel argmax is 512 at E1–E2, and the E24 turn-down rests on 768 alone. Both are already stated in RESULT.md, sections 1b and 1c.
2. **Draws (D1):** four fresh groups f01–f04 at N = 1,536, under the partition's existing step-down rule: if four groups cannot be filled, use the largest multiple of 16 (at least 512) that fills them.
3. **Widths (W1):** 256, 384, 512 and 768. Every width is pre-trained and adapted in the one run, and nothing is reused.
4. **P3 statistic:** the parabola-refined peak location in log2 width. A peak at either end of the ladder is recorded at that rung. Because the E8 peak is expected at 768, the E8-to-E32 shift is then a conservative lower bound, and the readings must say so.
5. **Multiplicity (M1):** a fixed sequence P1 (E32 turn-down) → P3 (peak shift) → P2 (E24 turn-down), each at two-sided 95%. A later test is read as confirmed only if every earlier one succeeded.
6. **P2 (E24)** stays the last primary, with its power stated in advance.
7. **Storage:** each width's model state is hashed and deleted after its training.
8. **Counting rule:** as revision 02. A run that creates any draw folder is the study's only attempt.
9. **Required reading text:** the late-epoch pattern occurs in a heavily overfit regime (best validation loss at E4 for 384–768), unlike Jane Street's 3-epoch setting. A confirmation therefore supports the pattern in this regime only.
10. **Order of work:**
    1. the seed-draw approval request;
    2. then the study source, fixture tests and one scoped review;
    3. then a stop for the owner's approval, with hashes and commands.

**Constraint:** the assistant draws no seed and runs nothing.
