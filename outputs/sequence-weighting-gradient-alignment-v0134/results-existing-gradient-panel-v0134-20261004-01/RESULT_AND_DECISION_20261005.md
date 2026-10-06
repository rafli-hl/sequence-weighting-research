# v0134 result and decision: fixed gradient panel closed

5 October 2026 UTC. The existing-checkpoint diagnostic and independent numerical
reduction audit completed. Independent final Astra review was PASS, provenance
turn `01a109f2-031d-70b3-8370-d8f26030baeb`, as supplied by the parent delegation.
This review provenance is an external turn reference, not a locally generated
review attestation. The numerical source and original artifacts remain unchanged.

The panel contains 30 states: ten shared U-pretrained initial checkpoints and
ten each of Unoclip_F10 and Inoclip_F10 from the completed v0133-r1 cohort.
Five corpora, each with two nested model/weight seeds, are the replication units.
Saved train512/validation256 examples and the first saved epoch's16 batches32
were reused. There were 480 state-batch rows, no new corpora, no test evaluation,
no optimizer step and no checkpoint/layer/example selection from these results.

Let gV be the gradient of validation group NLL and gD the extra instance-weight
training gradient: mean((w-1)*Linstance/3), equivalent to gI-gU at the same state.
Negative gV dot gD means an infinitesimal ordinary descent step along -gD locally
increases validation group NLL. It does not describe an actual AdamW update.
Each metric is averaged over two seeds within corpus, then over five corpora
equally; the mean cosine is not the cosine of an averaged gradient vector.

| State | Mean cosine | Corpus SD | Negative cosine corpora | Negative seed cosines | Mean dot gV,gD | Negative dot corpora |
|---|---:|---:|---:|---:|---:|---:|
| initial | -0.0742501917 | 0.0981493989 | 4/5 | 6/10 | -0.0091114221 | 4/5 |
| Unoclip_F10 | -0.0290379732 | 0.0714224913 | 4/5 | 6/10 | -0.0064409730 | 3/5 |
| Inoclip_F10 | +0.1424547196 | 0.2030918655 | 2/5 | 3/10 | +0.2365841570 | 1/5 |

Initial adverse alignment is modest and heterogeneous. Four corpus cosine means
are negative, but four of ten seed cosines are positive and corpus91420105 is
positive. These observations count against a consistent initial-conflict account;
there is no significance or practical-threshold claim. Endpoint alignment changes
with the trained state; Inoclip_F10 is favorable on average. Endpoint associations
may be consequences of training and cannot explain the earlier penalty by themselves.

Corpus dot and cosine signs can differ because seed cosines are normalized before
averaging and seed dots retain magnitude. In Unoclip_F10, four negative corpus
cosines coexist with three negative corpus dots; in Inoclip_F10, two negative
cosines coexist with one negative dot. Do not substitute these sign counts.
All30 seed cosines and all15 corpus cosines are defined; saved seed guards are
empty. Zero-norm/undefined fixtures passed. The frozen EPS1e-12 guard, explicit
nulls and strict aggregation rule remain binding: an undefined constituent would
make its aggregate undefined, rather than be dropped or converted to zero.

Extra-component batch population dispersion exceeds uniform-component dispersion
in every one of the30 states. Equal-corpus mean extra/uniform batch RMS ratios are
1.12666321 initially,1.53129478 at Unoclip_F10 and1.42534886 at Inoclip_F10.
Mean extra/uniform population gradient norm ratios are0.79138702,0.88265263
and0.83013418 respectively. These are scalar component comparisons, not the
variance of the total instance-weighted gradient. For centered batch vectors,
Var(gI)=Var(gU)+Var(gD)+2Cov(gU,gD); the covariance is needed to determine the
total. Neither larger component dispersion nor the current alignment proves mediation.

## Completion and audit evidence

The combined diagnostic plus conditional audit finished within the single600s
cap: inclusive outer postwrite319.216155078s (rounded319.216s). Diagnostic exit0,
audit exit0 and outer exit0; both children confirmed exited. Saved containment
confirms no surviving group, wrapper reaped, cancellation exit0, cleanup reason
none. The parent-supplied final independent review accepted the execution gate.

AUDIT.json reports PASS_GRADIENT_REDUCTION_AND_PANEL_AUDIT,30 full-population
states,480 independently recomputed batch rows,15 corpus-state rows and5,579
passing discrepancy comparisons. Saved output hashes were checked before writing
this record. Analytic softmax, ignored context, one-third training scaling,
full validation normalization, centered finite differences, ordinary-descent
signs, uniform-zero-extra, zero-norm undefined, strict-null aggregation and
nonfinite rejection fixtures all passed. The largest recorded tolerance fraction
was0.4999621837 for an ordinary-descent fixture; all classes were within tolerance.
The maximum real full I-minus-U gradient discrepancy was7.8231096e-8;
aggregation maximum absolute discrepancy was2.0847124e-7.

The audit independently recomputed direct-token full-population and batch reductions,
but shares the trusted forward implementation, PyTorch autograd and operational
input guards. It is not a separate model implementation. No gradient vectors were
retained; there was no optimizer-moment replay, intermediate update reconstruction,
strict determinism claim or test evaluation. Numerical precision was FP32 with
FP64 gradient accumulation and scalar reductions. This remains a fixed synthetic
G1,width128,F10,existing-state association and establishes no universal mechanism,
capacity trend, peak criterion or representation mediation.

## Decision

Close this fixed panel. Retain the prior fixed-policy instance-weighting penalty,
while treating initial directional interference as mixed and unresolved. Do not
expand seeds or search layers, checkpoints, batches or examples for favorable signs.
No additional numerical work is authorized by this record.

Next intervention remains proposed, not approved; independent planning recommends evaluating AdamW coordinate-wise preconditioning. The planner recommends a norm-matched AdamW preconditioning comparison, but it awaits the user's decision. No variance intervention was selected or approved.

A separate source-only design and independent review would be required before any
new execution. Exact controls, pairing, optimizer state policy, primary outcome,
resource feasibility and audit remain to be frozen. No new intervention source,
data generation, training or numerical analysis was performed for these records.

## Evidence identities (SHA-256)

| Evidence | SHA-256 |
|---|---|
| SOURCE_MANIFEST.json | 630283aa3b9bca47f4d689482f8bf374291638a781d68fe0b821740ff21d7062 |
| INPUT_BINDINGS.json | 59a846e852d998ae431780eef57a19a4564d4bfc0c6ceb33f7dfeebf890df2f9 |
| reviews/SOURCE_REVIEW.json | ffcfa7fc3ade288d087268ab946f636857e79b5ad687e27a4fccf6d95f11dc09 |
| results-existing-gradient-panel-v0134-20261004-01/AUDIT.json | 94ebc3b1195c7c384477d6d82d35de72c9290d2946a3610c596aa96e30d02d9b |
| results-existing-gradient-panel-v0134-20261004-01/COHORT_SUMMARY.json | 5e1c8b81ffcc28f27ff6d6909dedd14ef3163985fa0c2455e412426c9e4fe3e3 |
| results-existing-gradient-panel-v0134-20261004-01/CORPUS_SUMMARY.json | 21faf0fc99242d23d7870e61ef78396dad9f74a46f576b81ef6fa07164b83f1a |
| results-existing-gradient-panel-v0134-20261004-01/PAIRS.json | 243e137160fcb99f4796565d86a4aee2f725b82e05b2ee9a898f9bef82cc351a |
| results-existing-gradient-panel-v0134-20261004-01/BATCHES.json | 17463c8f304536dc88d52b09155e4a2da77939df3706cac459b810fc58a0f173 |
| results-existing-gradient-panel-v0134-20261004-01/PANEL_REPORT.md | dd5be259667e99853510f9c626f6e0b7701481eb1a3d896b108f9804fadec7c0 |
| receipts/outer-panel.exit.json | aaaa0618d496d8b5c74f49a67c4ea88464f82fcb599310605c742728df22a31f |
| receipts/outer-panel.postwrite.json | d353bef6f876aec5ba593eb8f67f8a7784f6654f988179efbe998775dd47767f |
| receipts/outer-panel.containment.json | 86585137e3b79b8cf9b90bf057694086ddcbc9bba095b0d9241ca5a062caa7ed |
| receipts/diagnose.exit.json | 5940c0fd06bfa415ecd5d3b2ef180f9cc3970587f2b6c5ae29e47fc026c7767a |
| receipts/audit.exit.json | a2d934c0546d70741dffce7c30f577a3865e0b7852e65dd2c1099bf03625df21 |

