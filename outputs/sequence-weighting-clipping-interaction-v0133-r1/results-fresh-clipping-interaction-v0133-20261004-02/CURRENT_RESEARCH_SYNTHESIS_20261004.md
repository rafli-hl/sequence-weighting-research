# Current research synthesis: completed v0133-r1

4 October 2026 UTC. The latest bounded study, v0133-r1, is COMPLETE after numerical
audit and independent Astra result review. Its frozen practical interaction
criterion failed. [RESULT_AND_DECISION_20261004.md](RESULT_AND_DECISION_20261004.md)
records all corpus signs, adequacy, secondary observations, audit discrepancy
maxima, timings, evidence hashes and independent-review provenance. Historical
records and the original failed v0133 attempt remain unchanged.

The completed v0131 reanalysis found an adverse random-versus-uniform held-out
tradeoff and preferential high-weight instance allocation on five already seen
corpora. Its training associations and arithmetic decomposition did not identify
a mechanism. Historical v0130 failed its frozen width128 no-clip validation
criterion; clip1 remained the canonical fixed control. These studies remain closed.

Completed fresh-data v0132 isolated an adverse instance-weighting effect under
the fixed canonical policy: group-token test NLL +0.035304929 nats, corpus SD
0.004915780 and5/5 positive corpus means. I-U was +0.033297779. Its factorial
intervention strengthened the narrow causal statement about loss weighting under
that training algorithm, while leaving the pathway unresolved.

New v0133-r1 crossed instance weighting with clip1 versus no clipping on five
fresh G1 corpora, two nested seeds each, ten shared U-pretrained checkpoints and
forty width128/depth3/F10 adaptations. The primary group-test contrast
D=(Iclip-Uclip)-(Inoclip-Unoclip) was **+0.000743708 nats/group answer token**,
corpus SD **0.001968224**, with only **3/5 positive** corpora. It missed both
the prospective mean>=0.01 and all-five-positive requirements. No corpus was
discarded and no favorable-result search followed.

The conditional penalties remained **+0.031944954** under clip1 and
**+0.031201246** without clipping, each positive in all five corpus means.
Unoclip own-baseline group gains were positive in all five, satisfying the frozen
adequacy gate. A clipping-only explanation is therefore weakened: removing clip1
did not eliminate this penalty under the tested fixed policies. This is not a
zero-effect or equivalence result for clipping, and does not select a new policy.
It does not contradict or reopen v0130's different historical criterion.

Preferential training allocation remains separate from overall memorization.
Both policies favored high-weight instance items relative to U and disfavored
low-weight items in all ten paired seeds, while random-instance arms had worse
overall unweighted instance training NLL. The allocation observation supports
redistribution of fit, but does not prove that extra overall memorization consumed
capacity needed for group learning. Neither allocation nor scalar step norms
establishes mediation or identifies representation competition.

Update traces show much higher clipping frequency in Iclip than Uclip despite
similar mean actual clipped step norms. No-clip step summaries differ as well.
These are descriptive observations: equal or different scalar norms do not reveal
directions, AdamW preconditioning/moment paths or component-specific learning.
The audit verified saved arithmetic and fixtures, not an independent replay of
every intermediate optimization update. Near-ceiling group accuracy and the
teacher-forced synthetic design also restrict claims.

The audited record covers50 checkpoint reevaluations,10 full-input regenerations,
6400 adaptation trace rows and all frozen tolerances. Runtime was713.688034s
plus the2s failed-attempt charge; audit was57.535809s. Both bounded modes ended
successfully with confirmed saved containment. Original failure evidence and
all numerical outputs are preserved. Source manifest is
`baf8a3de3aab342b842f8d2fc0ce4b1899cf77b6e58987745df9d64b27ab5ab3`;
AUDIT.json is
`915ecc81692fd6f7f7aba52f80d55af66e563139e6a64ae1e54b75ba89a16078`.
Independent Astra result-review provenance is turn
`01a1071e-967b-7735-8efd-3fa513484b5e`, PASS with no blocking discrepancy,
as communicated by the parent delegation.

Current decision: retain the persistent conditional group-NLL penalty as a
narrow fixed-policy result, and reduce confidence in a clipping-only account.
The next scientific question is which update-direction/preconditioning or shared
representation changes explain the residual penalty. No new experiment is
authorized. A follow-up must be separately designed and frozen; it cannot be
selected by favorable signs, spare runtime, test scores, p* or an adaptive seed
search. No universal mechanism, scaling curve, large-LM replication or mediation
claim is established.

Previous synthesis:
[completed v0132](../../sequence-weighting-factorial-v0132/results-fresh-factorial-v0132-20261004-01/CURRENT_RESEARCH_SYNTHESIS_20261004.md).
