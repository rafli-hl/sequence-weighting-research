# Primary-source recheck — 28 September 2026

Sources were reopened from their publishers/arXiv during Stage 2. This is a
focused positioning check, not an exhaustive novelty search.

- [Renda & Mani, Jane Street, 14 September 2026](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/):
  sequence weights are log-uniform from .01 to 10; evaluation follows three
  training epochs. Hyperparameters target validation loss with strong
  regularization, and held-out performance improves with scale. The proposed
  common-pattern/specific-pattern explanation motivates the synthetic task.
  Stage 2 asks whether its peak persists after capacity-specific validation
  selection; this remains a boundary-condition study, not an exact replication.
- [Jane Street estimator note](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/sequence-weighting-note.pdf):
  the finite-sample criterion is a rank-kernel quadratic form on normalized
  signed gains and powered weights. Positive aggregate gain is assumed;
  individual gains may be negative. Our implementation retains signed gains,
  tests direct kernel equivalence, and reports its finite search bound [0,8].
- [Byrd & Lipton, 2019, arXiv:1812.03372v3](https://arxiv.org/abs/1812.03372v3):
  weighting effects can diminish during training, while L2 regularization and
  batch normalization restore some sensitivity in their experiments. Therefore
  an observation that weighting sensitivity changes with training duration or
  regularization is already related to prior work. AdamW weight decay in our
  Transformer is not automatically equivalent to their L2 intervention.
- [Li et al., 2026, arXiv:2608.14071](https://arxiv.org/abs/2608.14071):
  studies repetition of domain data with token budgets scaling with model size.
  The abstract reports mildly increasing optimal repetition at fixed
  tokens-per-parameter. Repetition, domain mixing, fixed compute ratios and
  per-sequence loss weighting are different experimental quantities; we should
  not frame Stage 2 as refuting this result.
- [Zhang et al., ICLR 2017, arXiv:1611.03530v2](https://arxiv.org/abs/1611.03530v2):
  neural networks can fit random labels. Observing synthetic instance-label
  memorization is therefore not a standalone novelty claim.
- [Xu, Ye & Ruan, 2021, arXiv:2103.15209](https://arxiv.org/abs/2103.15209):
  develops formal accounts of importance weighting through gradient-descent
  implicit bias and margin-based learning theory. This further limits claims
  that weight sensitivity and training dynamics are unexplored. Applying a
  particular theorem to this causal Transformer would require checking its
  assumptions; Stage 2 does not make that theoretical identification.

The focused search also checked the [ICML 2019 proceedings record for Byrd &
Lipton](https://proceedings.mlr.press/v97/byrd19a.html). Search terms covered
sequence-weight effective exponents, validation/regularization/scaling, and
importance weighting with early stopping. Only primary sources support the
statements above; absence from these searches is not evidence of novelty.

Potential contribution must come from the controlled separation of pattern
types, explicit validation selection, paired operating-point versus fixed-epoch
comparisons, and replication across corpora. Whether the measured evidence
supports even this limited framing is decided in REPORT.md. No venue fit,
priority claim, or publication guarantee has been established. Inverse-exponent
weight compensation remains untested here and is already suggested by Jane
Street; it should not be presented as an original proposal.
