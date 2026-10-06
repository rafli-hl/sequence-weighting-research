# Alignment and research decisions

30 September 2026. This is a prospective decision record based on completed
studies. New-experiment outcomes have not been generated or inspected.

## What remains central

Jane Street asks how training-sequence weights relate to sequence loss
reduction, how that relationship varies with model scale and training duration,
and why extrapolation across scales can fail. Its shared-versus-specific-pattern
hypothesis motivates a controlled intervention. Its empirical setting uses
validation-oriented tuning and useful held-out performance across a broad
model ladder. See the primary-source review in this package for precise scope.

Our nearest unresolved question is whether the task permits learning held-out
structure beyond correction of a poor starting predictive distribution, and
how sharing a learnable rule changes learning and weight sensitivity.

## What the existing studies permit

- Stages 2–4 show dependence of the descriptive peak on configuration,
  training duration and pretraining. They do not establish a universal peak.
- Stage 6's U/R/random primary utility result fails at the middle capacity in
  all four panels. Its M controls pass global utility; the corresponding random
  K verdicts remain mixed/inconclusive. These facts must be reported together.
- M pretraining can leave large nonshared loss; reducing that loss can partly
  reflect repair of a poor baseline. U addresses that problem through a
  uniform-target pretraining objective, while also potentially changing
  representations and dynamics. The comparison does not isolate a scalar
  calibration effect.
- Stage 7 separates estimator availability from recovery. Stages 8–10 separate
  numerical fidelity from both recovery and usefulness. The model-cohort audits
  do not supply evidence that numerical error explains the earlier peaks.

These statements derive from the linked reports and machine-readable sources
in [CLAIMS.md](CLAIMS.md), rather than reselecting favorable conditions.

## Why the proposed next test is rule sharing

The retained generator draws 16 group-specific permutations once per corpus
and reuses them across training, validation and test. Held-out splits contain
the same 16 groups with different sequence keys. Group answers therefore have
learnable structure. Instance answers are independent uniform draws, so a
new key supplies no expected signal for predicting its random answer.

The proposed intervention ties all group IDs to one of the already generated
permutations, versus the original 16 independently drawn permutations. It keeps
the mixed task's 4/4/4 query composition, sequence length, query/key skeleton,
random instance answers and training apparatus. The U pretrained checkpoint
is shared across the two conditions. The exact construction, seeds and
analysis are specified in [NEXT_PROTOCOL_DRAFT.md](NEXT_PROTOCOL_DRAFT.md).

This intervention changes rule complexity and the number of observations
supporting each rule together. Its causal target is **tying group rules**;
it does not isolate sample support alone. Expected answer marginals remain
uniform, but empirical answer histograms need not be identical. Changed group
answers also change later teacher-forced context. Full input/target equality is
required for paired weighting/configuration arms within a condition; across
conditions the common skeleton and intended answer/context differences must
be verified explicitly. Each condition needs its own initial-loss evaluation.

The pilot asks whether that controlled change improves held-out group learning
and yields useful adaptation from U. Fixed-epoch component comparisons address
the intervention. Validation-selected policies address practical utility.
Different selected durations must not be treated as a fixed-duration causal
comparison. All p*, fit and peak outcomes are retained diagnostics; none is a
selection criterion or a condition for keeping a corpus.

## Alternatives considered

| Route | Scientific value | Decision for this milestone |
| --- | --- | --- |
| More generic numerical audits | Could address a specific new failure | Defer: no unresolved model-cohort discrepancy justifies another generic audit. |
| More optimizer/tuning panels on the unchanged task | Estimates selection variation | Defer: Stage 6 already exposes the primary utility problem; another panel alone does not test rule learning. |
| Immediate broad text/model ladder | Closer to Jane Street's empirical setting | Defer: costly under the local resource limit and weak at isolating a mechanism. |
| Inverse-exponent weight compensation | Could test a practical weighting intervention | Defer: already proposed by Jane Street and vulnerable when p* is undefined or near zero; usefulness needs a separate test. |
| Paired group-rule tying | Directly changes how widely a learnable rule is shared | Prepare a bounded pilot with prospective utility and component-learning criteria. |

## What outcomes would change the argument

If the new held-out-learning criteria pass, the result establishes feasibility
for this changed synthetic task and a specific intervention effect. It does
not establish a peak, a peak shift, a better weighting algorithm or the same
mechanism in large language models. A wider capacity ladder would require a
separately justified and frozen study.

If the criteria fail, retain all records and report which component failed.
Do not choose a new task/grid/seed set after inspecting p* to manufacture a
peak. Utility, group learning, shared-task forgetting, instance memorization
and numerical availability each have a different interpretation.

This package completes a research-planning and writing milestone. Any later
training requires implementation readiness and a pre-outcome freeze under the
local execution constraints; no positive-result requirement is imposed.
