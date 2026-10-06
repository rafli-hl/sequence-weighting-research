# Primary-source check — 29 September 2026

Sources reopened before Stage 4 training:

- [Jane Street, A study of sequence weighting at scale](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/),
  Renda and Mani, 14 September 2026. Defines the question as dependence of
  per-sequence loss reduction on assigned weight; uses validation tuning and
  reports improving held-out performance with scale. Our synthetic pretraining
  intervention examines a boundary condition of interpreting this gain metric.
  It does not replicate their private text benchmark or large-model scaling.
- [Pereyra et al., Regularizing Neural Networks by Penalizing Confident Output Distributions](https://arxiv.org/abs/1701.06548),
  2017. Output confidence regularization and uniform-target/label-smoothing
  ideas have prior literature. Stage 4's auxiliary uniform-answer objective is
  a control, not a claim to invent output regularization; it differs from
  supervising a known hard target with a smoothed mixture.
- [Guo et al., On Calibration of Modern Neural Networks](https://proceedings.mlr.press/v70/guo17a.html),
  ICML 2017. Confidence calibration is a distinct evaluation question. Reduced
  initial NLL here must not be renamed proven calibration; we do not estimate
  full reliability diagrams/ECE or apply their post-hoc temperature procedure.

Frozen estimand retains the original signed-gain p*. Reference swapping and
component gains are explicitly diagnostics. These sources motivate careful
scope; this check does not establish novelty, exhaustive prior-art coverage,
venue suitability, or a publication guarantee.
