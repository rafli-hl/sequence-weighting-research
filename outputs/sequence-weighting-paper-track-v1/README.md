# Sequence weighting: evidence and next scientific test

This local package implements the research milestone requested on 30 September
2026. It consolidates completed Stages 2–10 and prepares the next scientific
decision. It contains no new measured model results.

## Read in this order

1. [Research note](RESEARCH_NOTE.md): bounded argument, methods, measured
   results and limitations.
2. [Claim audit](CLAIMS.md): source files, hashes, counting units and supported
   interpretations.
3. [Literature review](LITERATURE_REVIEW.md) and
   [source registry](LITERATURE_SOURCES.json): focused primary-source checks,
   prior overlap and unresolved novelty.
4. [Alignment and decisions](ALIGNMENT_AND_DECISIONS.md): why this direction
   addresses the remaining Jane Street research question.
5. [Design rationale](DESIGN_RATIONALE.md) and
   [next protocol draft](NEXT_PROTOCOL_DRAFT.md): a bounded, proposed test.
6. `NOTE_REVIEW.json` and `PROTOCOL_REVIEW.json`: independent reviews and
   resolved findings. `REVIEW.json`, `MANIFEST.json` and `COMPLETION.json`
   record package acceptance and provenance after those reviews.

The protocol is **proposed, not implemented, frozen or executed**. A reviewed
document does not replace executable fixtures, a measured resource benchmark,
source/input hashes and a pre-outcome freeze. Historical source/results remain
immutable. The root research goal (unavailable in this distribution; `../../RESEARCH_GOAL.md`) states the milestone
and ongoing scientific constraints.

## Interpretation

The record supports a methodological case study of sensitivity to training
policy and baseline, limited robustness of the primary utility result, and
estimator behavior. It does not establish a major improvement over Jane
Street, an exact large-LM replication or publication novelty. Stage 6's primary
U failures coexist with successful utility gates in M controls. Stage 10's
numerical agreement leaves the useful-learning/mechanism question open.

The next design must accept positive, negative and undefined outcomes. No
experiment is selected or expanded to obtain a desired p* peak. No cloud job,
upload, publication or model training is performed by this package.
