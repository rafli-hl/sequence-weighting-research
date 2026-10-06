# Stage 4 v0.5 — controlled pretraining and gain-reference intervention

29 September 2026. Freeze this protocol and executable source before new training.
Stage 3 motivated the design; its outcomes are not confirmation for this study.
Local Ubuntu WSL CUDA only. No cloud, upload or publication.

## Conditions and causal scope

Three pretrained initializations S, M, U, each four epochs, 2048 train/256 val,
AdamW LR .0003, WD .1, clip 5, batch 32, fp32, no dropout. S reproduces the
shared-only pretraining recipe. M and U use exactly the same mixed (4/4/4)
pretraining tokens, targets, type masks and orders. All three start from the
same cold model for a given capacity/model seed; pretrained states intentionally
differ across interventions. Every adaptation arm/config within a condition
uses its identical frozen pretrained checkpoint and reset AdamW.

M objective: mean hard-label CE at shared answer positions only. U objective:
the same shared CE plus mean soft-target CE at all group/instance positions,
with target uniform over the 16 answer tokens (IDs 68..83). The soft term has
fixed coefficient 1; its normalization is separate so the shared term is not
rescaled. Log-softmax includes all 84 vocabulary entries. Group/instance hard
targets are not used in the loss term, but their preceding answers remain in
the teacher-forced context in both M and U. This is an auxiliary pretraining
objective intervention, not post-hoc temperature scaling or label smoothing
of a hard group/instance target. No coefficient/pretraining-duration search.

Primary controlled intervention is U−M: same pretraining data/context/cold
checkpoint/order, changed auxiliary objective. S−M is a contextual reference
that also changes query composition and supervised shared-token count; do not
attribute it solely to calibration. U may change representations and learning
dynamics; it does not identify a pure scalar-baseline effect.

Manipulation check, reported without filtering: for every capacity/corpus,
U's mean initial adaptation-validation group/instance NLL is lower than M's,
and U shared accuracy >=95%. Report both tests and all failures separately;
do not expand training to rescue the check. NLL is not a full calibration study.

## Data, grid and budget

Unchanged mixed adaptation corpus 512/256/512, capacities 64/2,128/3,256/4;
original generator and signed-gain p* [0,8]. Always generate complete corpora
before toggling test visibility. Preserve disjoint pretraining/adaptation/
validation/test namespaces; verify full token, target and type equality.

Fresh tuning triples (adaptation data seed, model/weight seed, pretraining data
seed): (37409,501,95101), (39623,502,95102). These are two corpus/model pairs,
not separately crossed factors. Confirmation: corpus/pretraining pairs
(41843,95201), (43997,95202), (46219,95203), each crossed with seeds 601,602,603.
Three confirmation corpora, nine paired cells; model seeds are not independent
dataset replications. All conditions/capacities/arms share adaptation data,
weight assignments and batch orders for a given pair. No reused tuning outcomes.

Adaptation grid: LR {1e-4,3e-4} × WD {.1,1}, clip 1. This restricted grid is
informed by earlier studies and is not a global optimum. Train 60 epochs with
records at 0,1,3,10,30,60. Tuning is 3 conditions × 3 capacities × 4 configs ×
2 pairs × 2 arms =144 runs, with NO test evaluation. For each condition and
capacity, choose config/epoch by mean validation NLL over both arms and the two
tuning pairs. Full-precision ties: earliest epoch, ascending LR, ascending WD.
Candidates are epochs 1/3/10/30/60; epoch 0 is an improvement check, not a
candidate. No p*, test, visible peak or memorization enters selection.

F is fixed LR 1e-4, WD .1, clip 1. T is the fresh validation-selected configuration
for each condition/capacity; ET its selected epoch vector. Freeze all candidates,
decisions and confirmation schedule before any confirmation training/test.
Confirm both F and T configurations, deduplicating exact config equality;
<=324 confirmation trajectories plus 144 tuning =<=468 adaptation runs,
99 pretrained models. All confirmation test evaluations are preregistered at
1/3/10/30/60 (none at 0), regardless of selection. Continuing beyond ET is
diagnostic. Save all five model checkpoints and losses; never select from test.

Maximum total training-stage wall time 3 hours, including pretraining, setup,
evaluation and serialization. Check between runs/epochs. Stop on numerical
failure/budget exhaustion; retain failure records and report incomplete work.
No silent retry, seed replacement, search expansion or outcome-driven stopping.

## Frozen comparisons

For random weights, K=p_middle−max(p_small, p_large). Primary pretraining
comparison: K_U(F, C30)−K_M(F, C30), with all capacity p* and signed gains.
Matched F, C60 and F at 1/3/10 are secondary trajectories. S comparisons are
contextual secondary results. Native p* always anchors to that trajectory's
own pretrained model. Uniform weights/nonpositive aggregate gain are undefined.

For each S/M/U, report F, C30; T, C30; F, ET; T, ET. Decompose optimizer effect at
C30, duration under F and T, and interaction (T_ET−T_C30)−(F_ET−F_C30).
Compare U−M under their own T, ET only as a total selected-policy effect; it
mixes pretrained states and adaptation settings. Never present it as matched
adaptation. Report per-capacity p*, train/validation/test NLL, instance train
accuracy, fit objective, negative-gain fraction and clipping for all cells.

Baseline manipulation: report initial adaptation train/validation component
losses/accuracies, pretraining histories, and U−M paired initial NLL changes.
At every confirmation checkpoint compute original signed component gains,
group+instance p*, oracle reference [0, log16, log16] p*, cumulative signed mass,
centered RMS and Gram cross terms as in frozen v0.4 diagnostics. Preserve all
undefined and boundary fits. Total gain is mean component gains up to float32
roundoff (<2e-6); cumulative identities tolerance 1e-12. No loss clipping.

Preregistered reference-only sensitivity at F, C30 and F, C60: cross initial loss
reference A in {M, U} with trained trajectory B in {M, U}, same capacity/pair,
fitting gain L_initial(A)−L_final(B). Original diagonal remains primary.
For each K and per-capacity p* report reference change at M trajectory, trajectory
change at M reference, and interaction; undefined values propagate through
contrasts. Report signed gain and fit even if undefined. Off-diagonal quantities
are arithmetic diagnostics, not training effects or replacement primary metrics.

## Interpretation and audit

Peak survives descriptively only if all nine K are defined and positive.
Disappears if all defined and all three corpus means <=0; else mixed/undefined.
Report nine values, within-corpus SD, and mean/SD/range across three corpus means.
Effect sign consistent only if all three corpus means have same strict sign.
No significance tests or sequence-bootstrap substitutes for dataset replication.

Generalization for each cell/arm requires strictly decreasing corpus-mean test
NLL across capacities and validation <=initial at every capacity, in every
corpus. Report each criterion, including failures, independently of peak status.
Report uniform outcomes but never a uniform p*. No exact large-LM replication
or interior-to-interior peak-shift claim; only three capacity rungs are present.

Audit all scheduled runs/tests, validation-only selection independently, source
snapshots, historical hashes, datasets/full targets/types, cold checkpoint
identity across S/M/U, pretrained identity within each condition, orders/weights,
initial loss identity across arms/configs, saved model hashes, reconstructed
metrics/p*/diagnostics, manipulation check and compute ceiling. Verify the soft
loss mathematically and its gradient on fixed test logits before experiments.
Archive compact data/loss/config/source/audit/report records; retain model
binaries locally with hashes. Preserve all prior stages. Update handoff and
next-experiment status after report, visual review and archive CRC checks.
