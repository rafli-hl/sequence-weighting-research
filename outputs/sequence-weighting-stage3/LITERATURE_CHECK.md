# Focused primary-source recheck — 29 September 2026

These primary pages were reopened during Stage 3. This is a focused positioning
check, not an exhaustive novelty search.

- [Renda & Mani, Jane Street, 2026](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/):
  the scale curves accompany held-out improvement and validation-tuned strong
  regularization. Stage 3 controls optimizer and duration separately within a
  synthetic setting; it does not equate a bundle of AdamW changes with an
  isolated regularization intervention or exact LM replication.
- [Estimator technical note](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/sequence-weighting-note.pdf):
  the estimator compares normalized signed loss reduction to powered weights
  using a cumulative rank-kernel criterion. Positive aggregate gain is an
  identification condition; individual gains can be negative. Component and
  alternative-reference fits here are diagnostics with their own undefined cases.
- [Byrd & Lipton, ICML 2019](https://proceedings.mlr.press/v97/byrd19a.html):
  empirical work already connects weighting sensitivity to training duration
  and regularization. Observing sensitivity alone is not novel. The contribution
  candidate is the paired decomposition under a frozen selection policy and
  controlled mixed-pattern task.
- [Xu, Ye & Ruan, 2021](https://arxiv.org/abs/2103.15209):
  theoretical work addresses weighting through implicit bias and margin-based
  learning. Applying those theorems to this causal Transformer would require
  checking assumptions separately; Stage 3 does not assert that identification.

Shared-only synthetic pretraining, three capacities, three new corpora, coupled
model/weight seeds and reuse of just two tuning replications limit the result.
A reference-loss diagnostic is not an intervention on pretraining. Report all
frozen cells/interactions, regardless of their signs. No novelty, venue or
publication guarantee is established. Text scaling and inverse-exponent
compensation are not executed.
