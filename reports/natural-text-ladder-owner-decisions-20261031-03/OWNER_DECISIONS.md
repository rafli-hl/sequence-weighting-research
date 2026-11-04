# Owner approval of the late-turn seed draw, and the instruction to build the study source

**Date:** 31 Oct 2026. **Applies to:** the seed-draw package `reports/natural-text-lateturn-registry-preparation-20261031-01/REPORT.md`, with registry source subject 49398ed5123b7ca241d76810088f75085c50320ce61afce2becc4360f133ae69 and frozen policy 1050451f48c9a0bcb9b6a7e2f8203b98b424e8d3bad9a4f61d7eadc07f7b0dab.

## Owner message (verbatim)

> I ran the seed draw before your disjointness check finished; registry b9b6a8821613a1f2de610404145aaff56279a7967c130d0c215cdcf5beb0b9ff, output above. The disjointness is verified independently: re-deriving with lateturn_data.py gives f01-f04 at N = 1,536 (no step-down; 46, 40, 36 and 34 articles), zero overlap with the 443 used training articles and zero overlap among the groups. Record my approval text for OWNER-20261031-LATETURN-SEEDS-01 as suggested, confirm these figures from your own check, and continue: build the study source, fixture tests, one scoped review, then stop for my approval.

**Note.** The draw output mentioned ("output above") was not included in the message. The registry is read from disk.

## Approval text for OWNER-20261031-LATETURN-SEEDS-01 (the suggested text, recorded at the owner's instruction)

> I approve OWNER-20261031-LATETURN-SEEDS-01: run lateturn_registry.py draw once, natively, from registry source subject 49398ed5123b7ca241d76810088f75085c50320ce61afce2becc4360f133ae69, into reports/natural-text-lateturn-seed-registry-20261031-01 under the frozen policy 1050451f48c9a0bcb9b6a7e2f8203b98b424e8d3bad9a4f61d7eadc07f7b0dab, for the 18 roles of the late-turn confirmation. No redraw and no replacement. If the registry stops or the command refuses, nothing is retried and the next step is my decision.

## Decisions as recorded

1. **The draw.** The owner ran it once, at 11:37:29–11:38:13 (+07:00), under OWNER-20261031-LATETURN-SEEDS-01. The assistant ran no draw. The registry folder holds `REGISTRY.json` b9b6a8821613a1f2de610404145aaff56279a7967c130d0c215cdcf5beb0b9ff, and `validate()` passes.
2. **Timing.** The draw ran before the assistant's article-disjointness check (section 7 of the package report) had been reported. The check used test values only, so the order did not affect it.
3. **The September text check.** The owner did not choose between keeping the frozen partition rule (option a) and excluding the 10 training articles the check used (option b). The assistant proceeds under the frozen rule (option a), which the seeds were drawn under. The protocol discloses the overlap. Option b remains open to the owner until the source is approved.
4. **Next:**
   1. the study source;
   2. native fixture tests;
   3. one scoped review;
   4. a stop for the owner's approval with hashes and commands.
