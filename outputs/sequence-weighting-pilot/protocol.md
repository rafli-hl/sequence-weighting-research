# Protocol v0.1 — 28 September 2026

Historical initial protocol. Subsequent execution is specified in
`PROTOCOL_STAGE1.md` and reported in `results-mechanism-v02/REPORT.md`.
Stage labels below describe the original planning state.

## Question and alignment

Can controlled shared, group-specific, and instance-specific structure explain
the non-monotonic effective sequence-weight exponent and its movement with
training duration reported by Jane Street?

The paper's central outcome is the training-set exponent. Generalization is a
mechanistic diagnostic. We do not assume the original authors claimed that
their exponent predicts downstream accuracy.

## Stage 0: feasibility (authorized and implemented)

Use 2,048 synthetic training sequences, 256 validation sequences, and 512 final
test sequences. One 128-wide, three-layer causal Transformer; batch size 32;
AdamW, learning rate 0.0003, weight decay 0.1, gradient clipping at 1.0; three
epochs. Start with mixed data, seed 42, random sequence weights and a paired
uniform control. Report allocated/reserved VRAM, wall time, learning curves,
exponent, component accuracy, and gradient-clipping frequency.

This stage is exploratory engineering validation. It is not a hypothesis test.
No hardware runtime estimates are asserted before measurement.

## Stage 1: establish a usable task

Check that shared-rule accuracy improves beyond chance and that new-instance
random-answer accuracy remains around 1/16. Inspect group-rule learnability.
Inspect the fitted cumulative curve as well as its scalar exponent. If a task
is at floor or ceiling throughout the capacity ladder, change its complexity
using validation only and record the change as a new protocol version.

Inspect gradient clipping and the common loss reduction caused simply by
learning the answer-token vocabulary. An untrained baseline can dilute the
effective exponent because all examples benefit from this shared improvement.
Compare a shared-rule pretrained initialization before interpreting this as
evidence about adaptation of pretrained language models.

## Stage 2: mechanism study (not started)

After feasibility, freeze a validation-selected learning setup and test a
capacity ladder in the same architecture family. Candidate configurations are
width/layers: 64/2, 128/3, 256/4, 384/6. Actual parameter counts and feasibility
must be measured. Keep vocabulary, query count, data, and weight assignments
constant across capacities.

Data interventions: shared only; shared + group; shared + group + instance.
Each model is evaluated after epochs 1, 2, 3, with a separately declared longer
training arm if needed. Epoch checkpoints from one run are correlated; they
are not independent experimental replicates.

Use at least three independent training/weight seeds and report paired
differences across capacities and interventions. Increase seed count based on
pilot variability, not on whether a preferred result becomes significant.
Keep at least one independent data-generator seed for a robustness check.

### Hypotheses

- H1: Mixed shared/idiosyncratic structure can produce an interior maximum of
  the exponent as capacity increases.
- H2: Increased training duration can move that maximum toward smaller models.
- H3: The movement coincides with changes in which components of the loss are
  reduced; component learning explains more than parameter count alone.

These are conditional hypotheses, not guaranteed outcomes or universal laws.

### Primary measurements

- p-star and goodness-of-fit of its cumulative allocation curve.
- Per-component training loss reduction from a fixed baseline checkpoint.
- Location of the observed maximum on the tested capacity ladder, including
  uncertainty across independent runs.

### Secondary measurements

- Validation/test rule accuracy and NLL; sequence-specific random answers
  serve as a no-transfer control.
- Gradient norm/clipping frequency; total answer tokens and processed tokens;
  weight quantiles and effective sample size.
- Sensitivity to learning rate, weight decay, and initialization, using a
  predefined limited ablation rather than an unrestricted search.

## Stage 3: external validation (not started)

If the mechanism is identifiable in the controlled study, adapt a small open
pretrained LM (initial candidate: Pythia 70M) on public text. If multiple model
sizes do not fit or learn meaningfully, limit the claim to external validation
at that size. LoRA is a separate adaptation-capacity intervention and must not
be silently substituted for full fine-tuning in a capacity comparison.

## What would count as evidence?

- Support: an interior peak and epoch movement reproduced across independent
  runs, with the predicted pattern-component transition.
- Boundary: an effect appears only in specified structure/optimization regimes.
- Counterevidence to the proposed mechanism in our setting: the exponent
  changes without the predicted component-learning transition.
- Inconclusive: the explored ladder never reaches both sides of a peak,
  learning remains at floor/ceiling, or between-run uncertainty is too large.

A missing peak on a small synthetic ladder does not refute the original result
on very large pretrained models. A single-seed peak is not publishable evidence
of a scaling law.

## Sources

- Jane Street article: https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/
- Estimator note: https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/sequence-weighting-note.pdf
- Byrd & Lipton, importance weighting: https://arxiv.org/abs/1812.03372
- Pythia model suite: https://arxiv.org/abs/2304.01373
- TinyStories, small-model experimentation: https://arxiv.org/abs/2305.07759
