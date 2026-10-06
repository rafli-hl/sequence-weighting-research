# Protocol v0.2: execute the pilot notes

Written before the new runs. Stage 0 remains unchanged and exploratory.

## Design

- Existing local WSL CUDA runtime; original causal Transformer and p* estimator.
- Four disjoint example-key namespaces: pretraining, adaptation training,
  validation, and test. All have the same key-token vocabulary. No test metrics
  are computed during calibration. Group rules are constant across adaptation
  splits. New confirmation data seed is fixed in advance at 2718.
- Shared-rule pretraining: 2,048 examples, four epochs, uniform weights,
  learning rate 0.0003, clipping 5, weight decay 0.1. Separate pretraining seed.
  Freeze the resulting checkpoint for all paired adaptation arms of a given
  model/seed. Reset AdamW state at adaptation. Pretraining is synthetic and
  shared-only; it is not equivalent to language-model pretraining.
- Calibration: 512 adaptation examples (reduced from Stage 0's 2,048 to examine
  memorization under limited data), 256 validation examples, data seed 1729,
  training/weight seed 42, width 128 and three layers.
- Grid: learning rates {0.0001, 0.0003, 0.001}, clipping {1, 5, disabled}, both
  random and uniform sequence-weight arms, 30 epochs each (18 runs).
- Select the configuration minimizing the mean final unweighted validation NLL
  across the two arms. Fixed tie order: grid enumeration order. Do not select
  based on p*, test performance, or appearance of a peak. Weight decay stays 0.1.
- Extend the selected configuration to 120 epochs, restarting from the same
  pretrained checkpoint. Inspect epochs 1, 3, 10, 30, 60, 120. A paired cold-start
  random-weight arm is an initialization diagnostic.
- Learnability gate: at one of epochs {30, 60, 120}, uniform-arm training
  accuracy is at least 95% shared, 40% group, and 25% instance. Pick the earliest
  passing duration. Also require pretrained shared-rule validation accuracy
  at least 95%. This is an engineering gate, not a statistical test or evidence
  for the hypothesis. If no duration passes, stop before confirmation and report
  the task's limitation; do not keep altering it until a peak appears.

## Conditional confirmation

After freezing the selected learning rate, clip threshold, and duration:

- Fresh data seed 2718, model/weight seeds {42, 43, 44}.
- Capacities width/layers {64/2, 128/3, 256/4}; three controlled data regimes
  shared, structured (shared+group), mixed (shared+group+instance).
- Random-weight runs for the full 3 x 3 x 3 grid; three additional uniform
  mixed-data controls at 128/3. Fixed checkpoints up to the chosen duration.
- Separate pretrained checkpoints by capacity/seed; within each such pair the
  checkpoint is reused across regimes and weighting arms. Same example keys,
  query inputs, weight assignments, and batch orders are paired.
- Test is evaluated only at the frozen final epoch, once per run, with no
  subsequent selection from those results. Pretraining/adaptation splits and
  source hashes are saved. Report all runs, including undefined p* and negative
  gains; retain signed gains in the original estimator.
- Report all three seeds and paired middle-minus-endpoint differences. Three
  seeds are too few for strong uncertainty claims. An interior peak requires
  the middle capacity to exceed both endpoints in each seed at a checkpoint;
  this descriptive criterion is not a significance test. Report whether peaks
  move across the observed checkpoints; a boundary maximum is not an interior
  peak. No extrapolation beyond the measured capacity range.

## External text validation gate

Proceed to a small pretrained public-text experiment only if confirmation
shows a reproducible interior peak accompanied by the shared/group/instance
learning transition. Otherwise report it as deferred by the mechanism gate,
with the evidence needed to revise the research design. Text validation at one
size cannot by itself validate a scaling curve.

## Alignment and limits

Primary outcome: training-sequence gain exponent relative to the frozen
pretrained baseline. Also report the same end model's gain relative to its
random initialization as a baseline-definition diagnostic. These are different
estimands and must not be conflated with the cold-start training arm.

The original study uses pretrained LMs, text and validation-tuned heavy
regularization. Our long-duration memorization arm deliberately probes
learnability and can overfit. The validation-selected configuration and
validation curves must be shown; memorization alone is not confirmation of
Jane Street's explanation in its original regularization regime.

Source: https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/
