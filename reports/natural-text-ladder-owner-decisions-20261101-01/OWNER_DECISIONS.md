# Owner decision: the next study is a few-epoch, data-rich width ladder (draft only)

**Date:** 1 Nov 2026. **Follows:** the late-turn confirmation result and the evidence-chain summary (`reports/natural-text-ladder-owner-decisions-20261031-04/OWNER_DECISIONS.md`).

## Owner message (verbatim)

> Next study, decided: a pre-registered few-epoch, data-rich width ladder that removes heavy overfitting, to test whether the late turn-down and peak shift appear in a regime closer to Jane Street's (3 epochs, no memorization). Draft only; build and download nothing yet.
> Draft a proposal covering:
> 1. Corpus: WikiText-103 raw (same source and licence family as WikiText-2), reusing the existing 4,096-token tokenizer. Report download size, disk needed against 4.3 GiB free, and how the pinned and hash-verified acquisition would work.
> 2. Data per draw: enough that every width up to 768 is still improving validation NLL at its final readout. Pre-register a manipulation check (NOT_OVERFIT) and say how results are read if it fails.
> 3. Training: about 3 epochs; readouts at fractional epochs (for example 0.25, 0.5, 1, 2, 3); widths 64-768; one common learning rate chosen on a tuning draw by validation NLL only, never p*.
> 4. Primaries in a fixed sequence, each at 95%: (a) fall over 384-768 at the final readout; (b) rise over 64-384 at the final readout; (c) peak location moving to smaller width across readouts. Prediction for Jane Street's pattern versus a memorization-only account, stated in advance.
> 5. Draws and power: number of fresh draws, power from the effect sizes seen so far and at half of them, plus false-positive fixtures.
> 6. Time and disk from the probe timings (768 at 0.134 s per update), including whether a B1/B2 split is needed, within the 6-hour limit and the power and GPU gates.
> Then stop for my decisions.

## Decisions as recorded

1. **The next study** is a pre-registered few-epoch, data-rich width ladder on WikiText-103 raw, reusing the frozen 4,096-token tokenizer.
2. **Scope now:** a draft proposal only. Nothing is built, downloaded, drawn or run.
3. **The draft:** `reports/natural-text-fewepoch-proposal-20261101-01/PROPOSAL_DRAFT.md`, with its planning arithmetic.
4. **Next:** the owner's decisions on the draft's open items. No runtime, download or seed draw is authorized.
