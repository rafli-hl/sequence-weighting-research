# Proposed next experiment: tie group rules under a common U baseline

30 September 2026. **PROPOSED — NOT FROZEN — NOT EXECUTED.**
This is a reviewable next protocol after the Stage 2–10 synthesis. No new
training or model-result computation is authorized by this file alone. A later
execution must create new versioned source and a unique run directory, pass the
implementation gates below, and record the final pre-outcome freeze. Historical
sources and records remain immutable.

## 1. Question and scope

Does tying a group-specific rule across all groups increase useful held-out
learning and change sequence-weight sensitivity under the same pretrained model,
data skeleton, optimizer and training duration?

The primary comparison is G1 minus G16 at a fixed optimizer and epoch 10.
G16 preserves the original task; G1 shares a single sampled group permutation
across all 16 group IDs. U pretraining is unchanged and paired exactly. This
tests the combined consequences of rule reuse and reduced function complexity.
It does not isolate sample support alone, establish a general scaling law,
prove a power-law mechanism, or test a new beneficial weighting algorithm.

The [design rationale](DESIGN_RATIONALE.md) separates source facts from causal
hypotheses. The unchanged M policies' successful historical utility gates remain
part of the research note; M is omitted from new training to bound this targeted
U experiment, not because its outcomes are inconvenient.

## 2. Data and the intended intervention

Use the original mixed sizes: 512 adaptation train, 256 validation, 512 test;
12 answer queries per 41-token sequence; four shared, four group, four instance;
84-token vocabulary. There are 6,144 supervised answer tokens per train epoch,
3,072 validation answer tokens and 6,144 test answer tokens. Inputs have length
40 for next-token prediction; only the 12 answer positions enter the loss.

Generate G16 with the unchanged generator and corrected disjoint key namespaces.
Generate the complete train/validation/test corpus before toggling visibility.
Save the 16 originally sampled permutations. Copy the full corpus to G1, and
replace only group-answer tokens by `68 + permutations[0][query_value]`.
G16 uses `68 + permutations[group_id][query_value]`. Do not regenerate type
order, queries, keys, random instance answers or group IDs in a second RNG pass.
The same G1 mapping applies to all three splits. Group 0 provides an exact
unchanged subset, but is not an outcome-selection or primary-analysis subset.

Across G1/G16, require exact equality of keys, group IDs, type masks, query
tokens, shared/instance answer tokens and all other skeleton tokens. Every
differing tensor entry must be a permitted group-answer token with the specified
value. Targets and later teacher-forced inputs consequently differ at these
positions. Within each condition, all capacities, arms and configurations must
have full token/label/type equality, including held-out splits.

Save counts for every `(group,query)` and every `(effective_rule,query)` in every
split, missing train-support cells, answer histograms and weighted training mass
per rule/query. Do not resample to eliminate missing support. Counts have
expectations 8 per association in G16 and 128 in G1; realized counts and weight
mass are measured data properties and may vary. The expectations 8/128 apply
to the 512-example train and test splits; the 256-example validation split has
expectations 4/64. Tuning and confirmation use
fresh corpus draws, with their own permutation sets and disjoint example keys
within each corpus. Finite vocabulary/rule support can overlap across draws.

## 3. Fresh proposed seeds and replication unit

| Role | Adaptation data seed | Model/weight seed | Pretraining data seed |
| --- | ---: | ---: | ---: |
| Tuning pair A | 88111 | 1401 | 98101 |
| Tuning pair B | 88321 | 1402 | 98102 |
| Confirmation corpus A | 88547 | 1501, 1502 | 98201 |
| Confirmation corpus B | 88771 | 1501, 1502 | 98202 |
| Confirmation corpus C | 88993 | 1501, 1502 | 98203 |
| Confirmation corpus D | 89203 | 1501, 1502 | 98204 |
| Confirmation corpus E | 89431 | 1501, 1502 | 98205 |

The existing protocol search found none of these proposed identifiers. Before
freeze, an independent inventory must check every historical config/seed role;
if a collision is found, replace and document it before generating new model
outcomes. No post-outcome replacement is permitted.

The five independent confirmation corpus draws are the replication unit. The
two model/weight seeds are nested, paired observations within each corpus, not
ten independent datasets. Reusing these seed numbers across corpora pairs their
initialization/weight randomness; corpus variation is estimated conditional on
this fixed seed set. The two tuning rows are coupled corpus/model/pretraining
pairs, not a fully crossed design. No historical confirmation result enters a
new estimate. No sequence bootstrap is used as a replacement for corpus
replication. Report all ten paired values and five equally weighted corpus
means, with descriptive mean, SD and range across corpus means. No significance
or population selection-probability claim is preregistered.

## 4. Models, pretraining and optimizer controls

Retain the saved causal Transformer definition: width/layers 64/2, 128/3, 256/4,
four attention heads, learned token/position embeddings, fp32, no dropout.
Record exact parameter counts from the implemented model, expecting the
unchanged 113,408 / 621,696 / 3,212,800 counts. This remains three capacities and
one interior rung; do not claim an interior-to-interior peak shift.

For each capacity/model/pretraining-data tuple, produce one U checkpoint:
2,048 mixed pretraining examples and 256 validation examples, four epochs,
AdamW LR 3e-4, WD .1, clip 5, batch 32. Objective is separately normalized shared
hard CE plus coefficient-1 uniform-target CE on group/instance positions over
answer IDs 68..83 under the full 84-vocabulary log-softmax. Save cold and
pretrained states, all pretraining histories and orders. Pretraining uses the
original mixed generator and is **identical across G1/G16**; do not tie its
permutations by treatment. No pretraining strength or duration tuning.

Each adaptation starts from that exact U checkpoint and reset AdamW. Random
weights use the inherited log-uniform .01..10 draw and one corpus-level mean
normalization; uniform weights are one. For a model/weight seed, pair weights
and the entire 30-epoch batch permutation array across conditions, capacities
and configurations. Batch 32 gives 16 updates/epoch. Use CUDA with TF32 disabled
as in prior runs. Record package/environment lock, GPU, deterministic settings,
wall clocks and peak CUDA allocated/reserved memory.

## 5. Two prespecified analysis branches

### A. Matched intervention — primary mechanism comparison

F = AdamW LR 1e-4, WD .1, clip 1, batch 32, fp32. Confirm F for every
condition/capacity/corpus/model/weighting arm regardless of tuning results.
Primary checkpoint is epoch 10, fixed now; epochs 1,3,5,20,30 are descriptive
trajectories. F continues to epoch 30 and is never shortened because of a
validation, utility or p* result. It is not claimed to optimize generalization.

At width 128/random, the primary mechanistic estimand is

`[initial_group_test_NLL − F10_group_test_NLL]_G1 −
 [initial_group_test_NLL − F10_group_test_NLL]_G16`.

Compute each difference within a paired corpus/model cell, then average the two
seeds in each corpus. Record initial and final values separately: paired model
parameters do not imply equal initial losses on different target/context data.
Report the same contrast at other capacities, all component and total losses,
and uniform arms as secondary descriptions. Do not select the most favorable
capacity, checkpoint or component after inspecting the contrasts.

### B. Validation-selected usefulness — primary practical comparison

For each condition and capacity, R selects random-arm validation NLL averaged
over the two tuning pairs. Grid LR `{1e-5,3e-5,1e-4}`, WD .1, clip 1, batch 32,
30 epochs, candidate checkpoints `{1,3,5,10,20,30}` plus one canonical epoch 0.
This restricted LR grid preserves the earlier values and fixes weight decay to
bound computation; it is not a global optimum or full regularization study.

There are 19 candidates per condition/capacity. Epoch 0 has null optimizer/LR
and one baseline score per tuning pair. It must be exactly identical across
weighting/configuration arms within that condition, but need not equal the other
condition's baseline score. Ties: full-precision score, earliest epoch, then
ascending LR. No p*, test score, fit, clipping, memorization or visible peak
enters selection. Uniform runs are paired controls evaluated at the same
selected R policy, not separately optimized policies.

Freeze all six selected settings and the confirmation schedule together before
confirmation training or any confirmation test evaluation. For each condition
and capacity, confirm the union of F and the selected nonzero configuration in
both arms, deduplicating an identical optimizer. If R selects epoch 0, F still
runs for branch A. Run each unique trajectory to 30 epochs. Evaluate all six
declared nonzero checkpoints on confirmation test, plus each condition's own
canonical epoch-0 train/validation/test once per capacity/corpus/model tuple.
The frozen R epoch alone defines selected-policy results; there is no
confirmation re-selection. Alternative trajectory checkpoints stay descriptive.

Different selected settings across conditions estimate a total policy contrast.
Their p* difference does not isolate rule tying at matched training. Branch A
provides the matched contrast, independently of those selections.
Both branches change training and held-out task rules together. They compare
within-task gain against each condition's own baseline, not accuracy or loss
of two models on one identical held-out target set.

## 6. Utility, predictions and bounded go/stop decisions

For a selected policy, delta_test is own epoch-0 total test NLL minus selected
total test NLL. Per-capacity utility passes only if the selected epoch is
nonzero, all five corpus means of delta_test are strictly positive, and all five
corpus means of selected validation NLL are no worse than own initial values.
Report individual negative-pair counts and each component of the gate. Epoch 0
gives exactly zero utility and undefined p* and clipping; it is not positive
evidence. Global utility requires all three capacities.

Predeclared decisions after the complete bounded experiment:

1. **Positive relative response to rule tying:** all five corpus means of
   the primary matched F10 group-gain contrast are positive. Otherwise record
   mixed, contrary, or unavailable evidence with all values; no selective mean.
   A positive contrast alone can mean less forgetting in G1, so it does not
   establish positive absolute group learning.
2. **Readiness for further mechanism work:** G1/R/random passes middle-capacity
   utility, criterion 1 holds, and all five corpus means of G1's own absolute
   F10 group-test gain at width 128/random are strictly positive. Record these
   three checks separately. If any fails, stop expansion of this task and
   document the negative result; do not widen LR/epochs or change the task
   automatically. Passing is a planning criterion, not statistical significance.
   Width 128 is fixed because Stage 6's primary middle-capacity utility failed
   in all four panels, not because a new result made it look favorable.
3. **Readiness for a later capacity-focused test:** G1/R/random additionally
   passes global utility. Report, separately, whether selected test NLL strictly
   decreases across capacities in each corpus and validation is no worse than
   initial at each capacity. Do not equate this with improved generalization
   caused by weighting. Any later capacity/text expansion requires its own
   specific design and freeze; passing does not launch it.

These criteria never filter observations from this experiment. G16 outcomes,
failed capacities, guards, adverse effects and every trained trajectory remain
reported. No direction, existence or magnitude of p* or K is a go criterion.

## 7. Weight-sensitivity diagnostics and safeguards

Retain the original signed-gain estimator and [0,8] interval for continuity.
For total sequence gains, subtract float32 losses before float64 conversion.
For component gains, retain the historical diagnostic operation order:
promote each saved float32 component loss to float64, then subtract. Check the
mean of the three component gains against the total gain under the inherited
2e-6 maximum absolute identity tolerance; they need not be bit-identical.
Do not clip or discard negative gains. Constant spread below 1e-12 and aggregate gain <=1e-10
remain undefined, including tiny positive totals covered by the historical
guard. Uniform p* is always undefined. No-adaptation reason remains explicit.

Save full and component train losses at all declared checkpoints, total positive
and negative gain mass, cancellation ratio, fit objective, lower/upper-bound
flags and per-sequence cumulative fit residuals. Record clipping alongside
train memorization and validation/test component losses/accuracies. Compute
group-component p* as a labeled secondary diagnostic with the <=1e-10 estimator
guard applied to that component, without substituting it for the full p*.
The historical <=3e-10 threshold applies only to allocation normalized by the
sum over all three components, not to an individual component fit. This pilot
does not add allocation/Gram outcomes; any later addition needs an explicit
prefreeze analysis revision with its historical guards and null rules.

Secondary directional prediction at F10: group-component p*(G16) > p*(G1).
Report all ten paired contrasts and the five corpus means only when fully
defined; otherwise retain the undefined aggregate and visible defined points.
Full-estimator K = p_middle − max(p_small,p_large), its complete trajectories
and selected-policy values are descriptive. Any undefined element propagates
through K and its aggregate. No new peak-survival success label or fit cutoff
determines the next research decision.

Source/audit fixtures must reconstruct estimator and loss identities from saved
arrays. Stage 10 agreement on historical cohorts is not a certificate for new
arrays. If a new finite-precision identity or ranking disagreement is detected,
retain the original result and issue a separate versioned numerical diagnosis;
do not silently replace p* or launch another numerical study.

## 8. Counts, execution ceiling and storage

Tuning: 2 conditions × 3 capacities × 2 pairs × 3 LRs × 2 arms = **72**
trajectories. Confirmation: at most 2 unique configurations per condition/
capacity × 2 conditions × 3 capacities × 5 corpora × 2 seeds × 2 arms = **240**.
Total <=312 adaptation trajectories, each 30 epochs. Exactly **36** pretrained
models: 6 tuning and 30 confirmation, shared across conditions. Confirmation
baseline evaluations: 60 condition/capacity/corpus/model records, aliased across
arms/configurations. At most 1,500 confirmation test evaluations including
60 baselines. All counts remain in a literal schedule manifest.

Proposed training-stage ceiling: **5,400 seconds (90 minutes)**, including all
pretraining, adaptation, evaluation, selection and serialization; enforce the
larger of UTC and perf_counter elapsed between epochs and runs. This is a
ceiling, not a measured forecast. Preparation/resource fixtures <=300 seconds;
audit/report <=1,800 seconds each unless a documented integrity failure requires
separate diagnosis. No cloud, paid computation, upload or publishing.

Before execution, require at least **6 GiB free**, a conservative storage
estimate <=4 GiB for the new raw run plus compact archive, and a **2 GiB** free
reserve throughout. Confirm this against actual free space; do not delete prior
records. Keep cold/pretrained binaries, every trajectory's epoch-30 binary,
every F trajectory's epoch-10 binary (including the 24 tuning F trajectories),
and each confirmation selected R checkpoint when it is distinct and nonzero.
Other tuning intermediate binaries are not required; their saved losses support
selection reconstruction but not binary re-evaluation. Deduplicate exact shared
checkpoints using explicit aliases. Save all
per-sequence loss arrays, assignments, orders, source and tensor hashes even
when another intermediate model binary is not retained. Document that such
hashes cannot substitute for re-evaluating a missing binary. Archive excludes
model binaries but includes their hashes; originals stay local.

A deterministic resource fixture using unrelated synthetic fixture seeds must
measure worst-capacity step/evaluation/serialization time and peak memory, and
derive schedule/storage estimates before the final research freeze. It may not
inspect research validation/test/p* outcomes or tune hyperparameters. If the
literal bound does not fit local GPU/disk/time, stop preparation and write a
new draft before any measured research outcomes; do not silently shrink cohorts
or run a partial favorable subset. No benchmark has yet established readiness.

Nonfinite values, budget exhaustion, OOM, source drift, pairing or audit failure
stop execution and preserve completed work plus planned missing rows. No silent
retry, replacement seed, automatic resume, outcome-driven schedule reduction,
or resource-budget increase. Report partial denominators explicitly.

## 9. Required implementation and freeze gates

Before any research training:

- Create new versioned source; copy or derive historical components with parent
  SHA256 records. Keep every old stage immutable. No notebook execution claim.
- Test G1/G16 label formulas on hand-built fixtures, invariant skeleton tokens,
  exact intended differences, unchanged group-0 rows, phase/split key separation,
  complete-generation/test-visibility equality and all within-condition full
  token/label/weight/order pairing.
- Check finite, positive, unique random-arm weights after the saved dtype and
  normalization operations, including fixtures with deliberate ties. A tied
  assignment stops preparation for a documented pre-outcome design revision;
  do not automatically resample. Uniform weights intentionally remain constant.
- Mathematically check U loss and gradient on fixed logits; verify common cold
  and pretrained tensor identity across treatment/weight/configuration arms.
- Independently check canonical-zero selection, ties, condition separation,
  deduplicated F/R schedules, null propagation, signed gains, corpus aggregation,
  utility versus scaling, all-negative effects and incomplete-run reporting.
- Complete the historical-seed/source inventory, resource fixtures and literal
  maximum-count/storage check. Freeze the implementation, protocol, analysis,
  fixtures, environment, seeds and source manifest before research training.
- After tuning, freeze candidate scores, selected policies and the full
  confirmation schedule before confirmation training/test. No test visibility
  during tuning. Keep chronology in append-only event records.

An independent reviewer must approve the source-bound design and fixture
evidence before execution. Any pre-outcome design change gets a new explicit
draft/review; once outcomes exist, repairs are versioned and preserve the
original source and failure record.

## 10. Completion evidence

Save protocol/config/seed/source/environment hashes, generated data and
permutation metadata, full tensors and input hashes, cold/pretrained identity,
all weights/orders/per-sequence losses, selected candidate evidence, model
hashes, runtime/memory, failures and missing schedule entries. Independently
reconstruct selection, metric and contrast calculations, p* guards, aliases and
resource ceilings from retained records. Re-evaluate retained selected/F10
model binaries on saved data to check their saved metrics.

The report must distinguish fixed-epoch intervention, selected-policy utility,
weight-sensitivity diagnostics and historical context. Produce scientific
figures with all values/undefined cases visible, inspect every figure, verify
archive SHA256/CRC, and update handoff/runbook/next-experiment status only after
checks pass or an honest partial/failure outcome is documented. No positive
peak, global optimum, causal mediation, exact large-LM replication, novelty,
publication readiness or venue guarantee is presumed.
