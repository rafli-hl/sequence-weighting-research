<a name="primary-source-recheck--29-september-2026-before-stage5-outcomes"></a>

# Primary-source recheck — 29 September 2026, before Stage 5 outcomes

The following primary sources were opened again during preparation. This is a
focused alignment check, not a systematic novelty search.

- [Jane Street: A study of sequence weighting at scale](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/), Alex Renda and Nitya Mani, 14 September 2026.
  The methodology uses random log-uniform sequence weights .01..10, validation
  loss for hyperparameters, and reports improving held-out performance with
  capacity. These motivate our separate usefulness and scaling checks. The post
  studies pretrained LMs on an internal text benchmark; our synthetic task and
  modest grid cannot establish its exact replication.
- [Estimator technical note](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/sequence-weighting-note.pdf).
  Defines loss reduction against a weight-invariant baseline and assumes positive
  expected gain; individual gains may be negative. Its normalized cumulative
  discrepancy motivates retaining signed gains and reporting near-zero totals.
  Our finite [0,8] search and numerical guards are implementation limitations.
  Epoch 0 has no gain, so it is a legitimate policy choice with undefined p*.
- [Pereyra et al.,2017](https://arxiv.org/abs/1701.06548).
  Studies confidence regularization and its relation to label smoothing. This is
  prior context for uniform-target objectives, not evidence that our U procedure
  is novel or identical to their full method. U's objective/support are specified
  directly in PROTOCOL_STAGE5.md.

Design inference: first determine whether a validation-selected policy actually
improves on its own pretrained model; a finite exponent or apparent peak alone
does not establish useful adaptation. No source here guarantees that smaller
learning rates will help, or that this research is novel or venue-ready.
