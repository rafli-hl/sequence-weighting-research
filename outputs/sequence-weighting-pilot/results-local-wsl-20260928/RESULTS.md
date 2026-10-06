# GPU pilot results

These are measured exploratory results, not a scaling-law claim.

- Data: training count per run below; 256 validation, 512 test sequences; 12 answer tokens per sequence.
- Random initialization, float32, fixed final-epoch evaluation.
- Seeds: [42]. This report does not compute between-seed confidence intervals.
- Memory figures describe the PyTorch allocator, excluding desktop/driver allocations.

- Timings cover the instrumented training/evaluation section; interpreter imports, model/optimizer setup, package installation, and final checkpoint serialization are excluded.

## mixed / random

- Model parameters: 621,696.
- Training sequences / epochs / seed: 2,048 / 3 / 42.
- Final p*: 0.00254.
- Training answer NLL: 4.4694 -> 1.8857 nats/token.
- Final test answer NLL: 1.8956 nats/token.
- Elapsed training + evaluation: 4.2 seconds.
- Peak allocated / reserved VRAM: 58.8 / 84.0 MiB.
- Clipped-step fractions by epoch: [0.984375, 0.96875, 0.875].
- shared test accuracy: 100.00%.
- group test accuracy: 11.18%.
- instance test accuracy: 5.62%.

## mixed / uniform

- Model parameters: 621,696.
- Training sequences / epochs / seed: 2,048 / 3 / 42.
- Final p*: undefined (constant_weights).
- Training answer NLL: 4.4694 -> 1.7536 nats/token.
- Final test answer NLL: 1.7815 nats/token.
- Elapsed training + evaluation: 5.2 seconds.
- Peak allocated / reserved VRAM: 58.8 / 84.0 MiB.
- Clipped-step fractions by epoch: [1.0, 0.671875, 0.96875].
- shared test accuracy: 100.00%.
- group test accuracy: 21.24%.
- instance test accuracy: 6.69%.

## Interpretation limits

The original Jane Street study uses pretrained model families and an internal text benchmark. This pilot starts from random weights and applies sequence weights to conditional answer losses. The initial gain also includes learning that answer tokens occupy a restricted vocabulary. That shared gain can dilute p*. A low exponent alone therefore does not identify a capacity regime.

Uniform weights have no identifiable exponent. Rule accuracy on held-out examples is a diagnostic, not a replacement for the original training-set metric. One seed cannot establish a non-monotonic capacity curve or its epoch shift.

The next decision should depend on pattern learnability, gradient clipping, and fit quality. Freeze a validation-selected setup before running a multi-seed capacity ladder.

Source: https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/
