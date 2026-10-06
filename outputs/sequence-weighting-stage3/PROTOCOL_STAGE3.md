# Stage 3 v0.4 — optimizer, duration, selection objective and baseline

Written 29 September 2026 before new confirmation outcomes. Design is informed
by completed Stage 2; that history is explicitly exploratory for this follow-up.
Source/protocol and the deterministic reused-tuning decision are copied and
hashed before any v0.4 training. Local WSL RTX 3050 only; no publishing/upload.

## Fixed scope and budget

Mixed task, sizes 512/256/512, original 41-token architecture at 64/2,128/3,256/4,
same complete-corpus v0.3 generator and original signed-gain estimator [0,8].
Four-epoch shared-only pretraining (2048/256, LR .0003, WD .1, clip 5), reset
AdamW for adaptation; batch 32, float32. No dropout or generator change.

Fresh confirmation corpus/pretraining-data pairs: (22360,94101), (24494,94102),
(26457,94103). Each crosses model/weight seeds 301,302,303, paired across all
capacities/configurations/arms. Thus 3 dataset replications, with 3 optimization
replications each, not 9 independent datasets. These seeds are disjoint from
Stage 1 and Stage 2. Both random and uniform arms at every unique configuration.

Each unique trajectory runs 60 epochs; record 0,1,3,10,30,60. Save models and
test per-sequence/component losses at each of 1,3,10,30,60, preregistered now to
support all policy crossovers. Test is never used to select anything. Baseline
test is not evaluated. Continuing after selected epochs is diagnostic only.

At most 144 adaptation trajectories and 27 pretraining checkpoints; maximum
2 hours cumulative training-stage wall time, checked between runs/epochs.
Observed Stage 2 costs support this ceiling; no additional benchmark/grid is
needed. Stop and report incomplete results if the ceiling or a numerical failure
is reached. Preserve all failures; no silent retry, replacement seed or grid
expansion. No arbitrary reduction based on p* or test shape.

## Frozen policies and reuse of tuning

F: fixed v0.2 optimizer LR .0001, WD .1, clip 1 at every capacity, implemented
on the corrected v0.3 corpus. Historical raw v0.2 is not a paired control.

J: minimize mean validation NLL over random+uniform and the two Stage 2 tuning
replications. R: minimize validation NLL over random only and those same two
replications. Both search the existing 18-setting × {1,3,10,30,60} table.
Read only tuning validation values for selection (no confirmation/test values,
p*, train memorization or shape). Reconstruct J rather than trusting its label;
it must match the saved Stage 2 choice. Tie order: full-precision score,
earliest epoch, ascending LR, ascending WD, clip 1 before disabled.

This is reuse of two joint tuning replications (corpus/model seeds 31415/101,
16180/102), not fresh tuning evidence. Freeze the extracted inputs, input-file
hashes, all scores, decisions, objective labels and deduplicated run schedule.
Deduplicate by (capacity, LR, WD, clip), independent of epoch or policy label.
F and J are already identical at the smallest capacity, hence <=144 runs.
Let EJ be J's selected epoch vector (expected 30/10/10); ER is R's vector.

## Question 1: optimizer × duration, primary paired contrasts

Define K(G, D)=p_middle(G, D_middle)-max(p_small(G, D_small), p_large(G, D_large))
for one corpus/model seed, random arm. Uniform p* is always undefined.
The primary 2× 2 comparison is G in {F, J}, D in {C30=(30,30,30), EJ}.
Report all four cells and, without selecting one after seeing results:

- optimizer effect at C30: K(J, C30)-K(F, C30);
- optimizer effect at EJ: K(J, EJ)-K(F, EJ);
- duration-policy effect under F: K(F, EJ)-K(F, C30);
- duration-policy effect under J: K(J, EJ)-K(J, C30);
- interaction: [K(J, EJ)-K(J, C30)]-[K(F, EJ)-K(F, C30)].

Also report per-capacity paired differences in p*, train/validation/test NLL,
instance accuracy and clipping. Common epochs 1,3,10,30,60 are fixed secondary
trajectories, including the historically relevant common epoch 60. LR and WD
are bundled optimizer interventions, not a clean effect of regularization alone.
The max endpoint in K can switch; report all three capacity values as well.

## Question 2: selection objective separated from epoch policy

Cross configuration policy G in {J, R} with duration D in {EJ, ER}. Report all
four cells even when some coincide, marking exact deduplication. Decompose:

- configuration effect at EJ: K(R, EJ)-K(J, EJ);
- duration effect at J: K(J, ER)-K(J, EJ);
- interaction: [K(R, ER)-K(R, EJ)]-[K(J, ER)-K(J, EJ)];
- total policy difference: K(R, ER)-K(J, EJ).

Apply the same differences to each capacity's test/validation NLL and p*;
report the random and uniform NLL outcomes separately. This identifies the
effect of applying these two selected policies conditional on the reused tuning
sample, not a universal causal effect of a selection objective or a new optimum.
The matched-epoch F/J/R trajectories are a further cross-check. No policy is
selected again from the new validation or test outcomes.

## Question 3: preregistered diagnostic decomposition of baseline gains

Primary p* always uses original total signed gains. Preserve negative individual
gains and undefined uniform/nonpositive-total cases. The component/alternative
metrics below are diagnostics only and cannot replace the primary exponent.

For each recorded checkpoint and component c in {shared, group, instance}, save
baseline/current NLL, mean/total gain, negative-gain fraction, component p*,
fit objective and boundary flags. The task has four answers per component:
total per-sequence gain equals (g_shared+g_group+g_instance)/3, up to float32
roundoff. Check this identity. Component aggregate gains can be negative.

For random arms and positive total gain, let q be cumulative normalized total
gains by ascending weight, q0=r/N, q_c^contrib be cumulative g_c divided by
the sum of all component gains, and a_c=sum(g_c)/sum_c sum(g_c). Check
q=sum_c q_c^contrib and q-q0=sum_c(q_c^contrib-a_c*q0). Report each signed a_c,
RMS norm of its centered cumulative contribution and pairwise cross-terms;
do not treat contributions as independent or discard negative ones.

Additional fixed sensitivity checks: (a) component p* with its own signed gain,
(b) a group+instance-only gain exponent, (c) a sequence-weight-invariant,
capacity-independent reference-loss vector [0, log(16), log(16)] by component.
For (c), gain per sequence is the mean reference minus the trained mixed loss;
this is an oracle shared-rule + uniform-answers diagnostic, not another trained
checkpoint. It may have nonpositive aggregate gain and undefined p*: report it
as such, without clipping gains or rescuing it. These quantities answer different
questions; sensitivity does not establish that pretraining causally explains K.

Run the same diagnostics retrospectively on the 90 Stage 2 confirmation records
and six deduplicated Stage 2 tuning baselines to explain the previously observed
3.23/4.19/5.45 mixed validation baselines. Label retrospective versus fresh
confirmation explicitly. Do not use these diagnostics in any model selection.

## Interpretation, uncertainty and integrity

For every policy cell, report all 9 paired K values and 3 corpus means, with
within-corpus model/weight SD and between-corpus mean/SD/range. Strict descriptive
peak survival: all 9 K defined and positive. Descriptive disappearance: all
defined and each corpus mean <=0. Otherwise mixed/inconclusive. Effect signs
are called consistent only if all 3 corpus means have the same strict sign;
zero and undefined remain explicit. No significance or sequence-bootstrap claims.

For every policy cell/arm, generalization succeeds only if, in each corpus,
mean selected test NLL strictly decreases with capacity and mean selected
validation NLL at every capacity is <= its epoch-0 value. Uniform has no p*.
Report all missing, failed, undefined and boundary fits, memorization and clipping.

Audit actual full token/target/type tensors, disjoint keys, test-toggle
invariance, actual batch orders/weights, initial checkpoint and loss equality
across arms AND optimizer configurations; policy deduplication; source hashes;
independent validation-only selection reconstruction; all scheduled tests after
freeze; metric/fit/decomposition reconstruction. Preserve v0.1/v0.2/v0.3 and
verify historical hashes. New raw data goes under a unique v0.4 run directory.
Save source, config, seeds, dataset/weight hashes, losses, models, runtime and
memory. Archive compact records, keep full model checkpoints locally with hashes.

Report optimizer, duration, objective and baseline answers separately. Three
capacities cannot resolve an interior-to-interior peak shift. Shared-only
pretraining and synthetic data are not exact LM replication. Recheck relevant
primary literature; no novelty/venue guarantee. Notebook remains unexecuted.
