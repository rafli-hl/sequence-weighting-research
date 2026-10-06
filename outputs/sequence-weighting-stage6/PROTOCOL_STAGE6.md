# Stage 6 v0.7 — selection stability across fresh tuning panels

29 September 2026. User authorized this follow-up. Freeze this protocol and
training source before training; freeze analysis source and synthetic checks
before any new measured outcomes. Local Ubuntu WSL GPU only. Prior results
motivate the design and are not confirmation observations.

## Question and primary outcomes

Does the Stage 5 selection procedure repeatedly choose no adaptation at the
largest capacity, and does the small middle-capacity benefit recur, when the
entire tuning panel is independently redrawn? Primary condition U, selector R,
evaluation random arm. Retain M as the paired pretraining control and J as the
secondary selection objective; report both weighting arms for every policy.

Four independent panels each contain two fresh coupled adaptation-data,
model/weight and pretraining-data pairs. Thus stability concerns the whole
tuning procedure, not an isolated causal effect of the tuning corpus. Four
panels give frequency increments of 25%; they cannot precisely estimate a
population selection probability. No binary threshold declaring stability or
new significance test is introduced.

Primary descriptive outcomes:

1. Selected epoch/configuration counts and proportions over four panels at
   each capacity, particularly largest-capacity epoch 0 frequency for U/R.
2. For each U/R policy, middle-capacity paired test NLL improvement against its
   own initial model, its three corpus means, and the Stage 5 utility components.
3. The 4-panel × 3-confirmation-corpus matrix of mean test improvement at each
   capacity. Report the equally weighted grand mean and separate descriptive
   means/SD/ranges of the four panel marginals and three corpus marginals.

All panels and all failures are included. There is no choice of a winning
panel based on test loss, p*, fit or peak appearance. Confirmation is shared
and paired across panel policies: four policies evaluated on the same three
corpora do not constitute twelve independent corpus replications. Three model/
weight seeds within each corpus are nested pairs, not independent datasets.
Per-panel utility successes on shared confirmation are not independent trials.

## Preserved task, models and optimization

Exactly the Stage 5 generator/model/pretraining/adaptation definitions:
mixed task, 512/256/512 adaptation train/validation/test; 4/4/4 shared/group/
instance queries; 84-token vocabulary; widths/layers 64/2, 128/3, 256/4.
Corrected disjoint key namespaces and full token/label equality checks retained.
Full corpus generation precedes test-visibility toggles; test is never evaluated
during tuning. Random weights are log-uniform .01..10, mean-normalized; uniform
weights equal one. Pair full data, initial states, weight assignments and batch
orders across all relevant conditions/configurations/arms/panel policies.

M/U pretraining: same mixed tokens/labels/context/cold state/orders, 2048 train /
256 validation, four epochs, batch 32, AdamW LR 3e-4, WD .1, clip 5, fp32.
M minimizes shared-answer hard CE. U adds separately normalized coefficient-1
uniform-target CE at group/instance positions over answer tokens 68..83 using
the full 84-vocabulary softmax. Pretraining is not tuned. U can alter learned
representations and dynamics; U−M does not isolate a scalar baseline mechanism.

Adaptation: AdamW, batch 32, fp32, clip 1, LR {1e-5,3e-5,1e-4} × WD {.1,1}.
Every tuning and unique confirmation trajectory runs 30 epochs, with records at
0/1/3/5/10/20/30. AdamW resets for each trajectory. No grid, capacity, horizon,
task or baseline changes are allowed after outcomes.

## Fresh seeds fixed before execution

Each tuning triple is (adaptation data, model/weight, pretraining data):

| Panel | Pair 1 | Pair 2 |
| --- | --- | --- |
| P1 | 60101 / 901 / 97101 | 60209 / 902 / 97102 |
| P2 | 60317 / 903 / 97103 | 60427 / 904 / 97104 |
| P3 | 60539 / 905 / 97105 | 60649 / 906 / 97106 |
| P4 | 60761 / 907 / 97107 | 60869 / 908 / 97108 |

Confirmation adaptation/pretraining data pairs: 61103/97201, 61211/97202,
61319/97203; each crossed with model/weight seeds 1001,1002,1003. These nine
cells are shared across all selected panel policies. Seeds are distinct from
prior stages. Finite task support can overlap across corpus draws; independence
means separate generator draws, not globally disjoint token support.

## Selection and confirmation scheduling

For each panel/condition/capacity, compare one canonical epoch 0 candidate
(optimizer/grid null) with six configurations × six nonzero epochs.
Require exact initial validation equality across all configurations and arms.
R averages random-arm validation NLL over that panel's two tuning pairs.
J averages both arms over the same two pairs. Ties use full-precision score,
earliest epoch, ascending LR, then ascending WD. No test, p*, fit or peak enters
selection. Report every candidate score and its input hashes.

Freeze ALL four panels' R/J choices together before any confirmation test.
For each condition/capacity, train the union of nonzero configurations selected
across panels and objectives, deduplicating identical trajectories. Both arms
run for each configuration. All six confirmation checkpoints are evaluated on
test as declared here, regardless of which epochs were selected. Only each
panel's frozen epoch enters its policy outcome; other checkpoints are descriptive.
Identical selected policies reuse exact observations and are labelled aliases.

Evaluate each of 54 condition/capacity/corpus/model initial cells once on train,
validation and test after selection freeze, including cells where all policies
select epoch 0. Reuse the same exact baseline records across configurations and
arms. If every policy abstains, all 54 initial tests still run.

## Utility, scaling and signed-gain interpretation

For each panel, condition, selector, arm and capacity, delta_test equals own
initial test NLL minus selected test NLL. Per-capacity usefulness requires
nonzero selected epoch, strictly positive corpus-mean delta_test in all three
corpora, and corpus-mean selected validation NLL <= own initial validation NLL
in every corpus. Global usefulness requires all three capacities. Retain the
per-pair values and negative-pair counts, even when corpus means pass.

Scaling is separate: strictly decreasing corpus-mean selected test NLL across
capacity AND validation <= initialization at each capacity in every corpus.
Epoch 0 can pass scaling without constituting useful adaptation.

Keep the original signed sequence-gain p* and range [0,8]. Uniform weights and
primary total gain <=1e-10 have undefined p*. This inherited guard includes tiny
positive totals. Component allocation has its inherited <=3e-10 guard. Report
total/positive/negative mass, cancellation, fit objective, boundary flags,
component/reference diagnostics, memorization, train/validation/test losses and
clipping without filtering or selecting by them. No additional fit cutoff.

K = p*_middle − max(p*_small, p*_large). Per-panel descriptive peak survives only
if all nine K are defined and positive; disappears only if all nine are defined
and all three corpus means <=0; otherwise mixed or inconclusive_undefined.
Epoch 0 gives exactly zero gain/utility and undefined p*, K and clipping, never
p*=0. Undefined propagates through any p*/K aggregate containing it. Do not
silently average only defined cells or remove no-adaptation policies.

Baseline manipulation is descriptive: U initial group/instance validation NLL
< M and shared accuracy >=95% for every capacity/corpus. Failures do not trigger
retries or exclusions. This is not a complete calibration assessment.

## Compute, storage and failure policy

576 tuning runs; 0..648 deduplicated confirmation runs; <=1,224 adaptation
trajectories; exactly 102 pretrained models (48 tuning +54 confirmation), even
under complete abstention. 54 initial tests plus 6 tests per confirmation run,
maximum 3,942 tests. Three-hour training-stage ceiling, enforced using the
larger of perf_counter and UTC elapsed, including pretraining/selection/initial
evaluations; CPU audit/report time is separate. Report both clocks and any
unexplained discrepancy. Stop and preserve failures; no replacement seeds,
silent retry, implicit resume, budget increase or result-dependent omission.

Source/runtime, configs/seeds, full data and metadata, weights/orders,
per-sequence losses at every measured epoch, scalar metrics, selection inputs/
decisions, per-epoch tensor SHA256, timing and CUDA memory are retained locally.
To fit available storage without deleting historical records, retain only the
epoch-30 full adapted model binary per trajectory, plus all cold/pretrained
binaries. Intermediate tensor hashes record training states at creation but
cannot be independently rehashed or re-evaluated from absent binaries. The audit
must distinguish this limit from verification of retained model binaries.
No intermediate binary is written and later deleted. Replay remains possible
from source/environment/data/initial states/orders/seeds, without claiming it
has been performed. Preparation requires >=11 GiB free; check a >=2 GiB reserve
during training. Storage failure stops the run and preserves records.

Unique source: outputs/sequence-weighting-stage 6/.
Unique raw run: work/runs/stability-v07-20260929-01/.
Never overwrite prior source/results/checkpoints/archives. Verify prior hashes.
Compact archive retains all non-model evidence and hashes of retained models.
No cloud, spending, uploads, publication or notebook execution.

## Verification, report and scientific scope

Outcome-independent fixtures cover panel-isolated decisions, deterministic ties,
canonical zero, union deduplication, all-zero schedule, shared-confirmation
aggregation, aliases and undefined propagation. Independent audit reconstructs
selection without calling the selector, checks full tensors/states/assignments,
source and historical hashes, all loss/fit calculations, final model binaries,
intermediate hash structure, exact schedule and test chronology.

Inherit Stage 5's frozen diagnostic serialization clarification and prespecified
70-digit/float64-bound Gram verification, unchanged in formula and tolerances.
Report every original strict failure and special undefined-primary comparison;
verification never changes primary p*, selection or scientific outcomes.

Complete only after independent audits, all panel/corpus results, figures and
visual review, archive SHA/CRC checks and updated handoff. Four tuning panels,
three confirmation corpora, a bounded grid and one synthetic task limit scope.
No exact large-LM replication, interior-to-interior peak shift, causal scalar
baseline explanation, novelty or publication guarantee is established.
