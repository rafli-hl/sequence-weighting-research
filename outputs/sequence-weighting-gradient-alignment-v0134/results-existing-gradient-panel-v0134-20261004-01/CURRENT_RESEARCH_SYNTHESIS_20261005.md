# Current research synthesis: completed v0134

5 October 2026 UTC. v0134 is COMPLETE following the saved numerical audit and
independent final Astra review PASS (turn 01a109f2-031d-70b3-8370-d8f26030baeb,
parent-supplied provenance). The fixed panel is closed. Detailed evidence,
sign counts, receipts, limitations and hashes are in
[RESULT_AND_DECISION_20261005.md](RESULT_AND_DECISION_20261005.md).

The closed v0131 historical reanalysis associated random sequence weighting with
worse group learning and preferential high-weight instance allocation; it did not
identify a mechanism. v0130 failed its frozen width 128 no-clip validation criterion.
Those historical studies remain closed and unchanged.

Fresh factorial v0132 found an adverse random-instance weighting effect on group
test NLL under the fixed canonical policy: +0.035304929 nats, corpus SD 0.004915780,
positive in all five corpus means. This supports a narrow causal effect of weighting
under that training algorithm, with the pathway unresolved.

Fresh v0133-r1 tested clipping interaction. Its primary interaction was +0.000743708
nats, SD 0.001968224,3/5 positive, missing the frozen mean>=0.01/all-positive gate.
The instance penalty persisted both with clip 1 (+0.031944954) and without clipping
(+0.031201246), each 5/5 positive. This weakened a clipping-only explanation; it
was not a clipping equivalence result. Preferential fit allocation did not establish
that extra overall memorization consumed group-learning capacity.

v0134 added a descriptive existing-checkpoint gradient panel using that completed
cohort: five corpora, two nested seeds, three states per pair (30 states, 480 batches).
Its initial validation-group versus extra-instance-gradient cosine averaged
-0.0742501917 (corpus SD 0.0981493989): 4/5 negative corpus means but only 6/10
negative seeds. Initial conflict is mixed and provides no consistent mechanism
finding. Unoclip_F10 averaged -0.0290379732, and Inoclip_F10+0.1424547196.
The endpoint shift can reflect training consequences. Corpus cosine and dot sign
counts differ because normalization precedes seed averaging; the result record
preserves both. All observed cosines were defined, and strict null handling was
audited rather than bypassed.

Extra-component batch dispersion exceeded uniform dispersion at all 30 states.
Mean extra/uniform batch RMS ratios were 1.12666321,1.53129478 and 1.42534886
for initial, U-F10 andI-F10. This is a component result. The total weighted-gradient
variance also depends on covariance with the uniform gradient, so increased total
variance is not established. The gradients are not actual AdamW updates; the panel
contains no causal mediation test, optimizer-moment replay or representation test.

The combined diagnostic+audit used 319.216 s of its 600 s envelope. All three exits
were zero, children exited, group disappearance and wrapper reaping were recorded,
and cancellation was zero. The audit passed 5,579 comparisons, independently
recomputing full-population and all batch reductions plus analytic fixtures.
It shares trusted forward code and autograd, retains no gradient vectors and does
not independently replay actual optimization. Source and numerical evidence remain
unchanged; no new numerical execution accompanied these records.

Current decision: retain the narrow, persistent group-NLL penalty; weaken the
clipping-only account; leave directional interference and stochasticity pathways
unresolved. Close the panel without seed/state/layer/example expansion, favorable
result search, tuning or peak/capacity claims.

Next intervention remains proposed, not approved; independent planning recommends evaluating AdamW coordinate-wise preconditioning. Its norm-matched AdamW preconditioning comparison remains a proposal awaiting the user's decision. No variance intervention was selected or approved. Exact controls, primary outcome, resource feasibility and audit would require a separately frozen source-only design and independent review before execution. No new experiment was executed here.

Previous synthesis:
[completed v0133-r1](../../sequence-weighting-clipping-interaction-v0133-r1/results-fresh-clipping-interaction-v0133-20261004-02/CURRENT_RESEARCH_SYNTHESIS_20261004.md).
