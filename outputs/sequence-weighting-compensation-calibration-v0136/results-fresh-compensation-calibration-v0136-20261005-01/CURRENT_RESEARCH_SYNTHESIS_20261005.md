# Current research synthesis: completed v0136

5 October 2026 UTC. v0136 is closed following the saved numerical audit and the parent-supplied final independent Astra result review. **Inverse-exponent compensation calibration failed; confirmation is blocked.** See [RESULT_AND_DECISION_20261005.md](RESULT_AND_DECISION_20261005.md) for gates, audit scope, timing and evidence hashes.

## What the completed studies establish

**v0131: historical allocation evidence.** The fixed G1 width 128/F10 random-minus-uniform total test NLL was +0.042260 across five reused corpora. High-weight sequences received preferential instance training-gain allocation, but random weighting had worse overall training fit as well as worse held-out NLL. Allocation is not greater overall memorization or mediation. [Saved synthesis](../../sequence-weighting-weighting-contrast-v0131/results-fixed-policy-v0131-20261003-01/SYNTHESIS_AND_DECISION.md).

**v0132: fresh factorial intervention.** On five fresh corpora, the instance-weight factor increased group-token test NLL by +0.035304929 nats, positive in all five corpus means. The four matched U/R/S/I arms support a narrow causal effect of instance-loss weighting under the specified optimizer policy. The pathway remains unresolved, and near-ceiling group accuracy makes this an NLL penalty rather than a large accuracy collapse. [Result](../../sequence-weighting-factorial-v0132/results-fresh-factorial-v0132-20261004-01/RESULT_AND_DECISION_20261004.md).

**v0133-r1: clipping interaction.** The primary interaction +0.000743708, 3/5 positive, failed its frozen practical criterion. Instance penalties persisted under clip 1 and no clipping (+0.031944954 and +0.031201246; each 5/5 positive). This weakens a clipping-only account; it is not equivalence or proof of zero clipping influence. [Result](../../sequence-weighting-clipping-interaction-v0133-r1/results-fresh-clipping-interaction-v0133-20261004-02/RESULT_AND_DECISION_20261004.md).

**v0134: descriptive gradient panel.** Initial group/extra-instance cosine averaged -0.07425019, with mixed corpus/seed signs. Extra-component dispersion exceeded uniform-component dispersion at all 30 saved states, but total weighted-gradient variance also depends on covariance. These were raw gradients, not actual AdamW directions; endpoint associations could be consequences of training. [Prior synthesis](../../sequence-weighting-gradient-alignment-v0134/results-existing-gradient-panel-v0134-20261004-01/CURRENT_RESEARCH_SYNTHESIS_20261005.md).

**v0135: preconditioning intervention.** Mean attenuation 0.006226374 was below the frozen 0.01 threshold. The uniform utility margin failed in all five corpora although both uniform policies learned. Numerical acceptance did not rescue the scientific gates; the intervention remains closed without retuning. This does not establish zero preconditioning influence or mediation. [Decision](../../sequence-weighting-preconditioning-v0135/results-fresh-preconditioning-v0135-20261005-01/RESULT_AND_DECISION_20261005.md).

**v0136: whole-sequence transport calibration.** On three different fresh corpora, descriptive pcal 0.02403094735 was too small, insufficiently identified and partly seed-unstable. Identification and minimum-exponent gates passed 0/6 seeds; improvement over p0 passed 0/3 corpora. Positive aggregate learning, small absolute RMS and acceptable validation cost did not provide an eligible compensation exponent.

## Why the component evidence matters

The reviewed v0136 R-arm group training reduction was 2.728775 component-token nats, versus 0.043607 for instance training. Instance validation/test losses worsened by 0.021207/0.021572 from their own baselines. Strong aggregate learning therefore mostly accompanies group-rule improvement; it must not be described as successful instance generalization.

This calibration used mild whole-sequence q weights on all loss components. Earlier factorial studies manipulated instance weights separately, with a broader random-weight distribution; the gradient and preconditioning studies also used different controls and optimizer conditions. Their magnitudes are not interchangeable and no cross-study causal chain is established. v0136 neither refutes the v0132 instance-factor effect nor demonstrates its mechanism. Failed calibration is a boundary result for the proposed transport step, not a universal impossibility of weighting or compensation.

## One prospective question

**Is v0136's weak aggregate weight response dominated by nearly weight-insensitive group-rule gains, while instance gains have a distinct dependence on q?**

The saved component means motivate this hypothesis but do not test weight dependence. A separately authorized examination of the existing signed component arrays and allocation profiles could address whether aggregating very different component responses obscures the meaning of the whole-sequence exponent. Such an examination would be exploratory; it could not retroactively validate pcal, relax the failed gates, select favorable seeds or establish causal mediation.

This is one proposed research question only. No new protocol, implementation, experiment or numerical reanalysis is authorized by this record. Preserve all source, receipts, signed gains, undefined/weak fit records and prior studies. Three independent calibration corpora with two nested seeds and one synthetic capacity do not answer a capacity curve, duration-dependent peak shift, large-LM replication or universal mechanism question.
