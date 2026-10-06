# Fresh component loss-weighting factorial v0132

Frozen scientific choices, 4 October 2026 UTC. SOURCE PREPARATION ONLY. This is a
new prospective experiment, with no result or readiness claim. Independent review
of the exact manifest is required before any numerical execution. The agent must
not run Python, tests, WSL, corpus generation, pretraining, adaptation or analysis
in this preparation task. Previous denied agent WSL access must not be retried.
The later commands are for a manual Ubuntu session after review.

## Question and intervention

Under the canonical G1 fixed optimizer policy, does random weighting of instance
loss impair held-out group-rule learning? Use G1 only: one group permutation across
the sixteen group identifiers; architecture width 128, three layers, 621,696
parameters; fp32; batch 32. Each sequence contains four shared, four group and four
instance answer tokens. Train/validation/test sizes are 512/256/512. The full
teacher-forced token sequence, including instance answers in later context,
remains the same across all four arms. This changes the direct loss weighting,
not the context or presence of the instance tokens.

For per-sequence component mean NLLs L_shared, L_group, L_instance, minimize
the batch mean of (w_shared L_shared + w_group L_group + w_instance L_instance)/3.
The coefficient 1/3 for every component is fixed in every arm. Do not normalize
weights within a batch, divide by the batch's sum of weights, or renormalize the
combined objective separately per arm. With four tokens per component this is
mathematically the inherited uniform/random sequence objective for U/R. Component
reduction can differ from the historical implementation by float32 rounding;
fresh U and R use this same component implementation throughout.

| Arm | Shared loss weight | Group loss weight | Instance loss weight |
|---|---|---|---|
| U | 1 | 1 | 1 |
| R | w_i | w_i | w_i |
| S | w_i | w_i | 1 |
| I | 1 | 1 | w_i |

Draw one vector per matched corpus/model pair: raw_i = exp(Uniform(log(.01),
log(10))) using Python Random(1000 + model_seed), cast to float32 and divide by
its corpus mean once. Use that exact vector in R, S and I; U is ones. Stop on
nonfinite/nonpositive/tied random weights; never redraw. Shared and group
weighting form one factorial factor, instance weighting forms the other.

## Fresh units and pairing

| Fresh corpus seed | U pretraining corpus seed | Two nested model/weight seeds |
|---|---|---|
| 91320101 | 91330101 | 91340101, 91340151 |
| 91320102 | 91330102 | 91340201, 91340251 |
| 91320103 | 91330103 | 91340301, 91340351 |
| 91320104 | 91330104 | 91340401, 91340451 |
| 91320105 | 91330105 | 91340501, 91340551 |

Windows source preparation conservatively searched all selected base identifiers,
data-key offsets +77, and weight/batch offsets 1000..1009 in 17,602 readable
historical text files. No identifier matches occurred. SEED_CENSUS.json binds
every scanned path and SHA256. This includes failed/diagnostic records, source,
protocols and the previous semantic seed inventory; binary checkpoints and
archives were not decoded. Previously undocumented/deleted/dynamically computed
seeds cannot be ruled out by numeric-text absence alone. Independent source review
must reconcile the previous semantic inventory and subsequent v0128-v0131 corpus
declarations before accepting freshness. That is a review gate, not an asserted
proof from a text search. Runtime preparation verifies the unchanged census
inputs and rejects drift, missing inputs or errors.

Use unchanged copied v0128 core.py/model.py/engine.py for the model, G1 generator,
namespaces, weight distribution, batch orders, U objective and evaluation. Never
import a historical launcher. Each fresh pretraining corpus has 2048 train and
256 validation sequences. Historical U pretraining means uniform sequence
weights, hard shared-rule NLL plus soft uniform sixteen-answer auxiliary NLL
on group/instance positions. Keep four epochs, AdamW LR 3e-4, WD .1, clip 5,
with fresh optimizer state. Do not substitute ordinary hard-label pretraining.

Generate ten checkpoints, one per corpus/model pair. Each checkpoint initializes
all four matched adaptation arms exactly; reset AdamW state for each arm.
Adapt for ten epochs with LR 1e-4, WD .1 and clip 1. Keep data, all labels, context,
checkpoint state, orders and component coefficients identical within each pair.
Order seeds are 999 + model_seed + epoch; pretraining uses the first four order
seeds with N=2048; adaptation uses ten with N=512. The paired nested model seeds
are separated by fifty, so their order-seed ranges do not overlap. Identical
numeric weight/order seeds within one matched seed use different PRNG engines
and are inherited, intentional pairing. Arm execution order is U,R,S,I for each
corpus and seed, fixed in advance. The hardware/runtime policy disables TF32 and
strict deterministic algorithms as in v0128; exact paired inputs do not establish
strict bitwise GPU determinism.

## Frozen endpoint and conclusions

Final unweighted group-token test NLL at F10 is the primary outcome. For matched
seed s in corpus c:

    d_cs = 0.5 * ((NLL_R_group - NLL_S_group) + (NLL_I_group - NLL_U_group))
    d_c = mean of the two d_cs values
    d = mean of the five d_c values, with equal corpus weights

Positive means worse group-rule learning from random instance weighting under
this fixed optimizer policy. Report all ten seed values and five corpus values,
the equally weighted mean, corpus SD/range and count of positive corpus means.
The dataset replication unit is the corpus, N=5; the ten nested seeds are not ten
independent corpus replications. No statistical significance or mediation claim
is planned. An all-positive pattern is direction-consistent at this tested policy;
mixed or nonpositive corpus results count against the hypothesis even if the
grand mean is positive. Preserve zero/negative values and never seek favorable
replacements. Tiny signs near the stated numerical audit tolerance need explicit
precision qualification rather than strong directional interpretation.

Secondary: fresh R-U group and total test NLL replication; the group interaction
(R-S)-(I-U); shared/group-factor effect 0.5*((R-I)+(S-U)); unweighted train,
validation and test total/component NLL and accuracies; clipping fraction,
per-update objectives/norms and training allocation. Arithmetic identity:
instance effect + shared/group-factor effect = R-U on the group endpoint.
Secondary allocation uses signed own-baseline train component gains. Rank the
512 sequences by (saved random weight, index) and use bottom/top 128; report both
the R-U gain contrast and 0.5*((gain_R-gain_S)+(gain_I-gain_U)), including high-low
component contrasts. No p*, peak criterion, capacity sweep, validation selection,
test-driven tuning, early stopping or adaptive seed expansion is allowed.

An incomplete/capped/nonfinite/broken-pairing run is a failed or incomplete
experiment, not a successful subset. Preserve completed and partial evidence;
do not pool a favorable subset as the frozen primary result. Do not retry,
regenerate data, resume a failed directory, expand seeds or silently change limits.
This experiment neither proves mediation nor a universal/large-LM mechanism.

## Caps and feasibility

Later runtime preparation, source/census verification, imports, U pretraining,
initial train evaluation, all forty adaptations, final evaluation, I/O and
termination share 1800 seconds TOTAL. No separate preparation allowance.
The outer manual runtime watchdog sends TERM at 1790 seconds and KILL after five
seconds; the remaining five seconds cover final shell receipts. Inner supervisors
use a cumulative charge and a fifteen-second termination/I/O reserve inside the
same allowance. Separate audit limit: 600 seconds including its imports, input
regeneration, checkpoint evaluation, arithmetic, receipts and termination.
No benchmark or automatic retry is added.

Total additional allocated storage, including this source bundle, run inputs,
checkpoints, arrays, outputs, logs, review documents and reserves: 512 MiB.
Keep 64 MiB unconsumed for a possible future archive and 16 MiB for terminal
receipts; normal worker writes stop at 432 MiB. No archive is made here or by the
commands. Retain >=2 GiB free at runtime; no silent CPU or cloud fallback.
Windows observed D: free space during preparation: 5,852,487,680 bytes; this is
a dated observation, not launch evidence.

Ten retained pretrained and forty final float32 checkpoints need roughly 124
million bytes plus serialization overhead. Corpus/assignment arrays, traces,
loss arrays, census and receipts add tens of MiB; projected nonarchive footprint
is below 200 MiB, not a measured execution footprint. No optimizer states or
intermediate adaptation checkpoints are retained. The runtime storage watcher
uses conservative allocation rounding and free-space checks.

The proposed 15-25 minute estimate remains uncertain. v0130's 911 seconds for
thirty mixed-capacity trajectories is budget context only: it reused checkpoints
and cannot establish the cost of ten new pretrainings, census hashing and forty
new adaptations. If the exact design exceeds a cap, stop and report insufficiency.
Source preparation cannot certify that it fits. CPU/GPU/OS unresponsiveness can
prevent a watchdog/receipt from completing; missing or unconfirmed exit evidence
blocks acceptance and is preserved without retry.
