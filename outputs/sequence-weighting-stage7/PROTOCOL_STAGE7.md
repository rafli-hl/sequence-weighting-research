# Stage 7 v0.8 — estimator recovery under signed perturbations

## Status and purpose

Design written before simulation outcomes, 30 September 2026. Authorized by the
request to execute NEXT_EXPERIMENT.md. A source/config/checks snapshot and UTC
freeze must precede all measured simulations. This is a CPU Monte Carlo study
of the unchanged Stage 6 estimator, plus a retrospective Stage 4–6 synthesis.
There is no training, validation/test selection, GPU grid, model-policy change,
cloud use, upload, or claim of new model generalization. All cells are retained.

## Estimator and targets

Copy Stage 6 core.py byte for byte. Fit normalized signed gains with its original
cumulative objective, grid/ternary minimization, and p in [0,8]. Preserve the
exact constant-weight check and sum(gain)<=1e-10 guard. The saved reason
`nonpositive_total_gain` includes small positive totals below that guard; report
this distinction. Never clip individual gains or filter fits. The existing upper
flag is p>=7.999; a descriptive lower flag p<=.001 is added outside the estimator.

For n sequences, q_i(p)=exp(p log w_i)/mean_j exp(p log w_j). Its mean is one.
For positive signal amplitude the target exponent describes conditional expected
gain, not a guaranteed finite-sample fit. p=0 is a constrained lower-bound target.
p=8 is an upper-bound control; p=10 is deliberate model misspecification and its
error must not be interpreted as ordinary within-range recovery failure.

## Independent units and paired draws

n in {128,512}; 64 independent replicates at each n. There are 128 independent
base draws, each used for 65 prespecified conditions, 8,320 fits in total.
Different n use independent draws. All truths/noise/scales within a draw reuse
the same complete weights and Gaussian vector. Conditions are paired repeated
measurements, not additional independent replications.

For n index j=0,1 and replicate r=0,...,63, weight seed is 730000001+10000*j+r,
noise seed 740000001+10000*j+r. These are fresh separate stdlib random.Random
streams. Draw log-weights uniformly on [log(.01), log(10)], exponentiate and divide
by arithmetic mean. Draw z_i using Random.gauss(0,1). Use float64 throughout.
The cancellation vector is e=(z-mean(z))/RMS(z-mean(z)), using math.fsum for its
mean and squared norm. It has dependent coordinates and zero conditional
expectation by sign symmetry; it is independent of weights. Its sum is zero up
to floating point arithmetic; retain both the estimator's Python sum(gains)
and math.fsum(gains) as total_gain and total_gain_fsum.

## Prespecified families

1. **Recovery (6,144 fits):** p={0,.2,1,4}, sigma={0,.5,2,8},
   a={1,1e-8,1e-14}; g_i=a*(q_i(p)+sigma*z_i). Conditional mean is a*q_i.
   Same relative noise at all scales isolates gain-scale invariance apart from
   the absolute guard and roundoff. IID noise randomizes the denominator.
2. **Cancellation (1,536 fits):** generator p={.2,1},
   c={1,.1,.01,1e-12,0,-.01}; g_i=c*q_i(p)+e_i. For c>0 target p is eligible;
   c=0 is unidentifiable and c<0 is outside the positive-gain estimator domain.
   Keep generator_p for all cells, but truth_p=null when c<=0. Both signal/noise
   ratio and cancellation change with c; this does not isolate a causal effect
   of cancellation alone. Total is approximately n*c; c=1e-12 probes small
   positive totals just above the guard without changing the estimator.
3. **Controls (640 fits):** exact random-weight p=8 and p=10; constant weights
   and constant unit gains (no identifiable exponent); random weights and all
   zero gains; random weights and negative q(1) gains (outside positive domain).
   Five conditions at both n and every replicate. All diagnostics stay recorded.

Configurations are ordered recovery p/sigma/scale, cancellation generator_p/c,
then the five controls. Each draw's NPZ stores full base weights, original and
centered noise, and a 65-by-n gain matrix before fitting. Uniform control uses
all-one weights. No invented model NLLs are subtracted to create small gains:
the direct signed gain arrays are authoritative. Token data, checkpoints,
memorization, clipping, validation/test losses and model selection are not
applicable to this estimator-only study; historical evidence remains in synthesis.

## Frozen summaries and interpretation

Each condition has 64 independent replicates. Cancellation groups include
generator_p even when truth_p is null; do not merge the two null-target cells.
For every cell report defined/undefined counts and reasons, undefined fraction,
upper/lower boundary counts, fit objective mean/max, negative-gain fraction and
cancellation ratio |sum g|/sum |g| (null for all-zero gains). Report actual totals,
including guard-positive cases. Recovery error uses only eligible targets.

Report explicitly conditional-on-defined bias, RMSE, MAE, SD, and quantiles
with their denominators. Also retain unconditional mean estimate/RMSE as null
if any fit is undefined. No imputation, dropped failures, winsorization, threshold
chosen from results, or pooled IID inference across cells. Exact controls repeat
across random draws to test design coverage, not independent model experiments.
64 replicates give worst-case binomial Monte Carlo standard error .0625 for one
cell frequency; conditional error summaries become fragile when few fits exist.
No accuracy-based pass/fail gate or inferential significance test is specified.

Three figures: recovery error/undefined frequencies; paired gain-scale
differences and guard outcomes; cancellation with boundaries/fit objectives.
All defined points must be shown inside axes, with eligible/defined denominators.
Differences are paired within n/replicate/truth/sigma; undefined scale pairs
stay counted. No averaging across incomparable noise/cancellation conditions.

## Runtime, audit and deliverables

Run locally with work/.venv-wsl/bin/python through Ubuntu WSL, one CPU process.
Simulation ceiling is 1,800 seconds using the larger UTC/perf_counter elapsed
timer, checked before each fit. No silent resumption, replacement seeds or
adaptive reduction: preserve partial output and record failure on overrun/error.
Preparation requires >=1 GiB free. Independent audit has its own 1,800-second
ceiling. Analysis/archiving is timed separately. Save peak process RSS; no GPU
memory is applicable. Snapshot environment, full sources, seeds/config, hashes,
all gain arrays and estimates, run chronology and failures. Refuse existing IDs.

Before outcomes, check exact recovery at representative powers, boundary and
guard behavior, scalar invariance above guard, cancellation construction,
deterministic regeneration, paired arrays and undefined-summary propagation.
Freeze analyzer/auditor with the runner. Independently regenerate every draw,
reconstruct every gain array and refit every estimate, verify all source/raw
hashes and schedule. Audit historical manifest coverage: all pre-Stage 7 versioned
output files and raw top-level records/source snapshots. Existing historical
model/sequence arrays are untouched but not all rehashed in this CPU study;
do not describe this limited integrity check as a full repeat of prior audits.

Save outputs/sequence-weighting-stage 7 source and a unique work/runs run,
audited report/tables/figures, lossless raw archive with SHA/CRC, visual review,
and updated handoff/runbook/next recommendation. Preserve all original stages.
Synthesis is retrospective; Monte Carlo recovery cannot prove a mechanism,
model generalization, a large-LM replication, a novelty claim or venue readiness.
No new literature claim is made. Any later novelty claim needs primary-literature
verification. Any diagnostic use on old results must remain exploratory and
cannot retroactively filter/reselect those results.
