# Stage 5 v0.6 — useful adaptation against no adaptation

29 September 2026. Freeze protocol and training source before new training;
freeze analysis source and outcome-independent tests before reading new outcomes.
User authorized continuation of NEXT_EXPERIMENT.md. Local Ubuntu WSL GPU only.
Prior Stage 4 results motivate design, not confirmation. No upload/publication.

## Question and estimands

Can validation-selected gentler adaptation improve on the same pretrained model
without adaptation? Primary condition U, primary selector R (random-arm validation),
primary evaluation random arm. This explicitly changes the selection objective
from Stage 4's joint-arm rule to target the random arm's usefulness directly.
Secondary selector J retains joint-arm validation for continuity. M is a paired
pretraining control; S is omitted to focus the question and bound compute.

Primary per-capacity estimand: delta_test = own initial test NLL minus selected
test NLL. Report all nine paired values, three corpus means, mean/SD/range across
corpora. Useful adaptation at a capacity requires selected epoch>0, strictly
positive mean delta_test in every corpus, and mean selected validation NLL <=
mean own initial validation NLL in every corpus. Global useful adaptation requires
all three capacities. Report each component separately; zero adaptation gives
zero delta, never evidence of useful learning.

Separate historical scaling gate: strictly decreasing corpus-mean test NLL across
the three capacities AND validation<=initial at each capacity, in every corpus.
Epoch 0 may satisfy this gate through the pretrained models; it does not thereby
pass usefulness. Report both arms under both selectors/conditions, without choosing
the preferred scientific story from their outcomes. No formal significance test.

Original signed-gain p* and K=p_mid-max(p_small, p_large) remain descriptive
mechanism outcomes under the selected policy. Peak survives only if all nine K
are defined and positive; disappears only if all defined and all three corpus
means<=0; otherwise mixed or inconclusive_undefined. No-adaptation p* is undefined,
not zero. Any undefined value propagates to its aggregate and contrast; do not
silently average the remaining values. Uniform p* is always undefined. Three
capacities cannot establish an interior-to-interior peak shift.

## Preserved model, data and pretraining

Mixed task: 512 adaptation train /256 validation /512 test, 4/4/4 shared/group/
instance queries, 84 vocabulary tokens, capacities width/layers 64/2,128/3,256/4.
Original generator and corrected disjoint key namespaces are preserved. Full
corpora generated before test-visibility toggles. Full token/target/type equality
is checked, not only keys. Test labels are never evaluated during tuning.

M/U pretraining exactly follows Stage 4: identical mixed tokens/labels/context,
cold state and orders, 2048 train/256 val, four epochs, AdamW LR 3e-4 WD .1 clip 5,
batch 32, fp32, no dropout. M uses mean hard shared-answer CE. U adds separately
normalized coefficient 1 CE to a uniform target over 16 answer tokens 68..83 at
group/instance positions, with full 84-vocabulary logsoftmax. Teacher-forced
nonshared answers remain in both contexts. No strength/duration tuning.
Each condition/capacity/pair shares its exact pretrained model across adaptation
arms/configurations; AdamW resets. U can change representation and learning
dynamics, so neither U−M nor arithmetic baseline diagnostics isolate a scalar cause.

Fresh tuning triples (adaptation data, model/weight, pretraining data):
(48371,701,96101),(50723,702,96102). Two coupled corpus/model pairs.
Confirmation (adaptation data, pretraining data):
(52919,96201),(55049,96202),(57163,96203), crossed with model/weight 801,802,803.
Three corpus replications, not nine independent datasets. All applicable arms,
conditions, capacities and configurations pair full data, random weights and
orders. Random weights use the original log-uniform .01..10 mean-normalized draw;
uniform weights are one. Do not reuse tuning or confirmation outcomes from prior stages.

Manipulation checks, without filtering/retry: at every capacity/corpus U initial
group and instance validation NLL <M, U shared accuracy>=95%. Report failures.
This is not a full probability-calibration assessment.

## Validation selection and confirmation

Adaptation grid: LR{1e-5,3e-5,1e-4} x WD{.1,1}, clip 1, AdamW, batch 32, fp32.
All tuning trajectories run 30 epochs, measured at 0,1,3,5,10,20,30. Each condition/
capacity has ONE canonical epoch 0 candidate with optimizer/grid_index=null,
baseline validation averaged once per tuning pair; duplicate initial losses
across arms/configurations must be exactly equal. Nonzero candidates cover all
six configurations x six measured epochs. R score averages random-arm validation
over two tuning pairs; J averages both arms over both pairs. Epoch 0 is identical
between arms, so duplication would not change its numerical mean, but is omitted.
Tie order: full-precision score, earliest epoch, ascending LR, ascending WD
(null fields only occur at epoch 0). No p*, fit, test or peak selection criterion.

Freeze all candidate scores, chosen R/J settings and deduplicated confirmation
schedule before confirmation pretraining/test. For each condition/capacity confirm
the union of selected nonzero optimizer configurations under R/J, in both arms,
each run through 30 epochs. No fixed-F extra trajectories. Evaluate all declared
nonzero checkpoints for these configurations; these trajectories are descriptive
and were chosen from tuning, not confirmation. No confirm re-selection.

Separately evaluate epoch 0 train/validation/test ONCE for each of 54 distinct
confirmation condition/capacity/corpus/model cells, after selection freeze, even
when epoch 0 is not selected. Reuse these saved identical baseline test records
for all applicable arms/configurations. This permits a direct paired test utility
comparison and is a deliberate change from Stage 4's no-baseline-test protocol.
If both selectors choose epoch 0, no adaptation trajectory is required for that
condition/capacity; its baseline evaluation remains mandatory. No-adaptation
gain is exactly zero by subtraction of the same record; clipping is undefined
because there were zero updates. Aliased policies are not extra replications.

## Counts, resources, failures

144 tuning trajectories; at most 216 confirmation trajectories; at most 360 total
adaptation runs. Exactly 66 pretrained models (12 tuning +54 confirmation). At most
2160 adapted checkpoints; at most 1350 confirmation test evaluations, including
54 initial tests. Unique raw run utility-v06-20260929-01, new Stage 5 sources.

Training-stage budget 10800 seconds, including pretraining, evaluation, saving and
setup inside the experiment; exclude preparation/CPU audit/report. Record both
perf_counter and UTC elapsed; enforce the larger at budget checks. Record any
discrepancy without guessing a cause. Baseline/adaptation/pretraining save runtime
and CUDA allocated/reserved memory. Budget/nonfinite/run failure stops execution,
saves failure details, no implicit retry or unregistered fallback. Do not delete
completed work, widen grid or choose a replacement seed to get a favorable peak.

## Fit/cancellation diagnostics (never selection)

Preserve original estimator, search[0,8], signed per-sequence gain and uniform/
nonpositive-total undefined handling. Preserve original float32 loss subtraction
before float64 estimator conversion; do not clip negative gains. Report total and
mean gain, positive/negative absolute mass, negative fraction, cancellation ratio
abs(sum gain)/sum abs(gain) (undefined if denominator 0), fit objective, p bounds,
training component loss/accuracy, validation/test and clipping.

The inherited numerical guards also declare sum(gain)<=1e-10 undefined (including
tiny positive totals, despite the legacy reason string nonpositive_total_gain),
and constant-weight spread<1e-12 undefined. Allocation uses componenttotal>3e-10.
These guards are disclosed and retained exactly, not retuned to the new outcomes.

For every confirmation checkpoint (including canonical zero), compute component,
group+instance and oracle-reference fits as labeled diagnostics, not replacements
for primary p*. Save signed allocation/cumulative Gram diagnostics when defined.
The Stage 4 versioned roundoff verification is now prespecified: keep original
absolute 1e-12 Gram result and, if it fails, recompute at 70 decimal digits with
identity residual<1e-50 and float64 accumulation bound 8*n*eps/(1-8*n*eps)*scale.
All such strict failures stay recorded. Other component/cumulative tolerances
are unchanged (component identity 2e-6, cumulative absolute 1e-12); any failure is
preserved and requires explicit versioned diagnosis, never silent relaxation.
Near-zero signed gain, upper-bound fits and poor objectives are substantive
interpretability concerns, even when numerical identities verify.

## Audit and deliverables

Independently reconstruct candidate scores/ties/schedule and all primary p*,
scalar metrics, useful/scaling/peak gates. Audit frozen source, historical hashes,
all corpora, full cold/pretrained pairing, assignments/orders, all model hashes,
exact tests after freeze, epoch 0 aliases and resource budget. Outcome-independent
fixtures cover zero winner/ties, undefined propagation, utility versus scaling,
paired statistics and cancellation. No data-seed pseudo-replication or test tuning.

Report all outcomes, failed/undefined values, fit caveats and limited-grid scope.
Save source/config/seeds/hashes/per-sequence losses, selection, runtime/memory,
scientific figures with visual review, audits and CRC/SHA-checked compact archive.
Full models stay local with hashes. Preserve all prior artifacts. Update HANDOFF,
NEXT_EXPERIMENT and RUNBOOK after completion. No notebook execution claim, exact
large-LM replication, novelty assertion or publication/venue guarantee.
