# v0135: norm-matched AdamW coordinate preconditioning

Source-only candidate, 5 October 2026 UTC. The user approved protocol/code
preparation, not numerical execution. Independent exact-source acceptance and
separate runtime approval remain required. Prior denied WSL access is binding.
No Python, tests, data generation, model evaluation, backward pass, training or
numerical audit has occurred for v0135. Completed studies and failed evidence
remain immutable; this is a distinct prospective bundle.

## Question and design

Does replacing coordinate-wise AdamW direction with a global norm-matched
first-moment direction attenuate the adverse instance-weighting effect under
this fixed synthetic training policy? This is an optimizer-policy interaction,
not mediation, a universal mechanism, a peak test or a capacity sweep.

G1 only, width128/depth3,621696 parameters, teacher-forced sequences41 tokens,
vocabulary84, four shared/group/instance answer tokens each. Adaptation train512,
validation256,test512; shared-U pretraining train2048/validation256, four epochs,
LR3e-4,WD0.1,clip5 using the trusted pretraining objective and native AdamW.
Pretraining mixed sequences use hard shared labels plus uniform-answer auxiliary
loss for group/instance positions. Its saved policy is common to all arms.

Five fresh independent adaptation/pretraining corpus pairs; two nested
model/weight seeds per corpus. Ten shared pretrained checkpoints initialize
four matched arms each:40 adaptations. F10 only,160 updates per trajectory,
batch32,LR1e-4,WD0.1,betas(0.9,0.999),eps1e-8,no clipping. Each optimizer starts
with zero moments and step0; no pretraining optimizer state is reused.

| Arm | Shared/group loss weights | Instance loss weights | Update direction |
|---|---|---|---|
| U-Adam | uniform | uniform | coordinate-wise AdamW |
| I-Adam | uniform | saved random sequence weights | coordinate-wise AdamW |
| U-isotropic | uniform | uniform | global norm-matched first moment |
| I-isotropic | uniform | same saved random sequence weights | global norm-matched first moment |

Weights are log-uniform draws0.01..10 normalized once over all512 train sequences
to mean1. No minibatch renormalization. The loss is mean over sequences of
(Lshared+Lgroup+w*Linstance)/3; each component is the mean over its four answer
tokens. U substitutes1 for w. The component coefficients, complete tokens/labels,
teacher-forced context, checkpoint parameter state, weight assignments and all
ten epoch orders are held fixed within each four-arm matched pair.

Seeds: adaptation91520101..91520105; pretraining91530101..91530105; nested model/
weight pairs(91540101,91540151),(91540201,91540251),(91540301,91540351),
(91540401,91540451),(91540501,91540551). Corpus is the replication unit.
Within-pair model/weight seeds are nested, not ten independent corpus draws.
The same fixed namespace-pool991 is intentionally inherited. Separate PRNG seed
values do not imply globally disjoint example keys across different corpora;
within-corpus pretraining/adaptation/validation/test key pools are disjoint.

SEED_CENSUS.json binds18,099 readable historical files with no proposed/derived
decimal-token matches. FRESHNESS_RECONCILIATION.json reconciles the semantic ledger,
v0128 and actual v0132/v0133-r1 freezes, including +77,+1000,+999+epoch streams;
v0130 reused older corpora, v0131 added none and v0134 reused v0133-r1 checkpoints.
No collision among1,338 recorded historical semantic values. Unrecorded/deleted
seeds or undocumented dynamic generation cannot be excluded. An independent
reviewer must accept semantic coverage; this scan alone is not semantic proof.
Runtime preparation rehashes all inventoried files before any new generation.
Missing/drifting inputs stop the attempt, without recensus, reseeding or retry.

## Exact update intervention

For each arm's own current state and unclipped gradient g_t:

    m_t = beta1*m_(t-1) + (1-beta1)*g_t
    v_t = beta2*v_(t-1) + (1-beta2)*g_t^2
    mhat_t = m_t/(1-beta1^t)
    vhat_t = v_t/(1-beta2^t)
    a_t = mhat_t/(sqrt(vhat_t)+eps)
    s_t = (global_L2(a_t)/global_L2(mhat_t))*mhat_t
    theta_(t+1) = (1-eta*lambda)*theta_t - eta*d_t

Native direction d=a; isotropic direction d=s. Global norms span all sorted named
parameters, computed with FP64 reduction from FP32 vector values. Moments and
updates are FP32. Bias correction applies at every step. The scale is global,
not per layer or tensor. Native implementation must pass locked PyTorch AdamW
fixtures (foreachFalse,fusedFalse,amsgradFalse,capturableFalse,maximizeFalse)
before any pretraining begins. No tolerance adjustment after fixture failure.

Both directions match a same-state counterfactual adaptive direction in their
own arm. They do not match another arm's actual/historical step. Decoupled decay
is identical, but total parameter step norms can differ because the decay vector
interacts with direction and rounding. The isotropic arm still uses v through
the global adaptive amplitude. This removes coordinate-wise directional scaling,
not all second-moment influence. Trajectories and moments subsequently diverge.

If mhat and a are exactly zero, adaptive direction is exactly zero; decay remains.
If either is nonzero but its norm<=1e-12, fail closed. Missing/sparse/nonfinite
gradients, nonfinite moments/scales/parameters or failed norm match stop the attempt.
Matching bound abs(norm(d)-norm(a))<=1e-8+2e-6*norm(a). No gradient clipping,
fallback denominator, alternate dtype, tuning or optimizer substitution.

## Frozen outcomes and decision rules

Y is fixed F10 group-token test NLL, averaged over all group answer tokens,
with no division by3. Initial group test NLL comes from the same shared checkpoint.
No test value selects epoch, seed, policy, norm rule or hyperparameter.

For each paired nested seed:

    CAdam = Y(I-Adam)-Y(U-Adam)
    Cisotropic = Y(I-isotropic)-Y(U-isotropic)
    D = CAdam-Cisotropic

Average two nested seed D values within each corpus; then average five corpus
means equally. Positive D means a more adverse instance-weighting effect with
coordinate-wise Adam. Primary practical criterion: overall meanD>=0.01 nats AND
all five corpus D means strictly positive. Report all ten seed values, all five
corpus means, signs, corpus SD(divisor4), range and threshold result.

Clean attenuation additionally requires every corpus to pass:

- CAdam>0: native instance penalty replicates.
- InitialNLL-Y(U-Adam)>0 and InitialNLL-Y(U-isotropic)>0.
- abs(mean_seed[Y(U-isotropic)-Y(U-Adam)])<=0.01 nats.
- mean_seed[Y(I-Adam)-Y(I-isotropic)]>0: isotropic improves the I arm directly.

The0.01 uniform margin is prospective utility tolerance, not formal equivalence.
Both uniform controls are necessary: an interaction obtained by harming U cannot
support clean attenuation. Gate failure blocks that interpretation even if D
passes. Negative, mixed, threshold-failing and nonfinite outcomes remain evidence;
nonfinite halts computation, while finite unfavorable outcomes complete/report.
No LR retuning, alternate seed, extra epoch, checkpoint selection or adaptive search.

Secondary: conditional penalties, direct I improvement, signed uniform contrast,
own-baseline uniform gains, all train/validation/test total/component losses and
accuracies, actual update summaries and per-sequence fit allocation. Allocation
uses fixed weight ranks, extreme quartiles128 each, and signed initial-minus-final
component gains; compare I-U separately for each optimizer. No p* estimation.

## Independent numerical audit to execute later

audit.py independently regenerates all ten full dataset containers and verifies
complete token/label equality, all weights/orders/masks, ten initial states,
forty F10 checkpoints and their saved arrays, all6,400 adaptation trace rows and
2,560 pretraining trace rows. Direct log-softmax/token reductions verify losses
independently of worker loss/evaluation functions. Pair/corpus aggregation is
recomputed from independent endpoint reevaluations; no favorable rows dropped.

Pretraining fixtures: locked PyTorch AdamW branch on CPU/CUDA32, WD0/0.1,
varying signed/zero gradients for160 steps with checks at1,2,6,160; analytic CPU64
first/second-moment, bias correction, both directions and decay; exact-zero,
near-zero and nonfinite rejection; objective/gradient1/3 scaling and ignored context.
These fixture source definitions are frozen but have not executed.

Eight snapshots are prescribed: first and last adaptation step of the first
seed of corpus91520101, in each of the four arms. No outcome-dependent selection.
Each retains theta,m,v before, gradient, and theta,m,v after. Independent
audit_optimizer.py imports no candidate optimizer or loss. It recomputes a real
batch gradient from saved pre-step state, reconstructs moments/directions/decay
in CPU64, checks global matching and actual scalar steps, and additionally replays
native-branch snapshots through locked CPU32 PyTorch AdamW using saved moments.
First snapshots bind zero moments and shared checkpoints; last bind F10 parameters.
All instrumentation is tied to exact sorted621696-parameter layouts and hashes.

Frozen elementwise tolerances:

| Check | Absolute tolerance | Relative tolerance |
|---|---:|---:|
| Native fixture parameters/moments | 2e-7 | 2e-6 |
| CPU64 analytic/objective fixtures | 1e-12 | 1e-12 |
| Endpoint NLL/arrays | 2e-6 | 0 |
| Snapshot moments/native parameters | 2e-7 | 2e-6 |
| Snapshot analytic parameters | 4e-8 | 2e-6 |
| Snapshot actual coordinate step | 4e-8+4*FP32epsilon*abs(theta_before) | 2e-4 |
| Independent snapshot gradients/scalar norms | 2e-6 | 2e-4 |
| Same-state global direction matching | 1e-8 | 2e-6 |
| Aggregation identities/relative scalar relations | 1e-12 | 0 |

Coordinate-step tolerance includes the rounding of FP32 parameters and decay;
it is not relaxed after results. Log maximum tolerance fractions and check counts.
Undefined relative steps when parameter norm<=1e-12 retain null plus guard, not0.

Audit shares trusted forward code, autograd and operational guards. It checks
eight prescribed real updates, not every intermediate optimization update or
moment history. Scalar traces alone cannot prove the full intervening path.
No gradient archives outside those eight bounded snapshots. Numerical PASS is
conditional on final outer receipts, containment, source/review bindings and limits,
and requires an independent final result review.

## Runtime, storage and fail-closed policy

Proposed future numerical allowance:1,800s TOTAL for preparation/imports/census
rehash, fixtures, ten pretrainings and forty adaptations, including cleanup/logs/
receipts. Separate600s audit envelope. No previous v0135 attempt exists or charge
is transferred. Runtime estimate15-25min is uncertain; fixture, global-norm,
hashing, snapshot I/O and GPU-memory overhead are unmeasured. If exact design
cannot fit, fail/report; no cap extension, retry, reduced panel or alternative policy.

512MiB ADDITIONAL allocation counts this source/reviews/receipts plus new RUN and
results (results inside source bundle). Normal writes<=432MiB;64MiB archive reserve
and16MiB terminal reserve remain counted if used. No archives are planned.
Retain>=2GiB drive free throughout. Budget is in STORAGE_BUDGET.json, including
all eight seven-vector snapshots (139259904 payload bytes), fifty checkpoints,
inputs, arrays, trace/source/metadata and conservative serialization allowances.
Past completed study storage is retained but is outside this additional cap.
Disk accounting rounds each file up to4KiB and uses larger filesystem allocated
blocks where exposed. No checkpoint or snapshot thinning/deletion to fit caps.

Trusted r1 manual launcher retains its entire containment body after variable
identity substitution. Runtime timeout TERM1790s,KILL+5s,final receipts5s;
audit TERM590s,KILL+5s,final receipts5s. Atomic group registration precedes GO;
cancellation persists; outer owns group cleanup and timing-wrapper reaping even
after supervisor death. Each inner phase retains15s termination/receipt reserve;
cumulative prior phases include postwrite samples plus1s each. Every phase is
one-shot, source/review/input bound, output exclusive and failure-latched.
No direct standalone worker/supervisor execution is permitted.

Manual Ubuntu commands and expected output inventory are in README.md. They are
future instructions only; this preparer must not invoke Ubuntu/WSL or these sources.
