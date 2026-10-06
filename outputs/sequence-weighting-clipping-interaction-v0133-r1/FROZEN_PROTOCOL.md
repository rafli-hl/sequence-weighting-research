# v0133 frozen source candidate: clipping × instance weighting

4 October 2026 UTC. Implements the accepted planning proposal (SHA256
`0c5cde22d42db88e7218f29c783e96d20dd4478401ec711cfdbf7c799b44e1d1`).
Scientific choices and seeds below are fixed before outcomes. Independent
exact-source review and separate user launch approval are required. This source
phase executes no Python, tests, WSL, generation, pretraining, training or audit.

## Cohort and pairing

G1 only; width128/depth3; 621696 parameters; fp32; batch32; adaptation F10.
Five fresh corpus units, two nested model/weight seeds each, ten fresh shared
U-pretrained checkpoints and forty adaptations. Train/validation/test sizes
512/256/512; four answer tokens per shared/group/instance component.

| Adaptation corpus | Pretraining corpus | Nested model/weight seeds |
|---|---|---|
| 91420101 | 91430101 | 91440101, 91440151 |
| 91420102 | 91430102 | 91440201, 91440251 |
| 91420103 | 91430103 | 91440301, 91440351 |
| 91420104 | 91430104 | 91440401, 91440451 |
| 91420105 | 91430105 | 91440501, 91440551 |

Uclip/Iclip/Unoclip/Inoclip are run in that fixed order for each pair. Component
weight masks are (1,1,1)/(1,1,w)/(1,1,1)/(1,1,w). All components have coefficient
1/3; each component loss averages its four answer tokens. Draw the one random
vector per pair using Python Random(1000+model_seed), raw exp(Uniform(log(.01),
log(10))), cast float32 and normalize once to corpus mean one. Reuse it in both
instance-weighted arms; no batch-weight normalization. Reject nonfinite,
nonpositive or tied random weights without redraw.

Use the same full tokens, labels, teacher-forced context, initial checkpoint,
weights and orders within each four-arm set. Reset AdamW for every arm. LR1e-4,
WD.1 are fixed. Adaptation clip is 1 for Uclip/Iclip and None for no-clip arms.
No-clip uses an infinite norm threshold solely to measure/check gradients; the
effective rescaling coefficient is one. Finiteness checks remain active.

Pretraining is unchanged from v0132: 2048 train/256 validation examples, four
epochs, uniform weights, AdamW LR3e-4/WD.1/clip5; hard shared-rule loss plus soft
uniform sixteen-answer auxiliary loss on group/instance positions. Fresh data
and model identities create ten baselines; no old checkpoint/data is reused.
Namespaces remain disjoint. Order RNG is Torch 999+model_seed+epoch, four
pretraining epochs with N2048 and ten adaptation epochs with N512. Nested model
seeds differ by fifty; their ten-epoch order ranges are disjoint. Fixed pool991
and within-pair Python/Torch seed-integer coincidence are inherited intentional
pairing. TF32 and strict deterministic algorithms remain disabled; no bitwise
GPU reproducibility claim.

Windows source preparation found no base/derived candidate identifiers in 17776
historical text files (1177251314 bytes). FRESHNESS_RECONCILIATION.json compares
selected identities to 630 prior seed records, 134 derived streams, 43 nonliteral
expressions and actual later v0128/v0132 designs: 1208 semantic historical values,
zero collisions. It preserves the difference between textual absence and semantic
reconciliation. Independent review must accept coverage; unrecorded/deleted seeds
remain unknowable. Binary archives were not decoded. Runtime preparation rehashes
all census inputs inside the same runtime cap and rejects missing/drifted inputs.

## Primary, adequacy and decision rules

Y is unweighted group-answer test NLL at F10 (nats/group-answer token; no /3):

    Cclip_cs = Y(Iclip)-Y(Uclip)
    Cnoclip_cs = Y(Inoclip)-Y(Unoclip)
    D_cs = Cclip_cs-Cnoclip_cs

Average two seeds within each corpus, then five corpus means equally. Always
retain all seed/corpus values, continuous D and both conditional effects, their
SD/range and all signs. Dataset N=5; seeds are nested, not ten corpus replications.
Practical criterion: mean D >=.01 AND all five D_c>0. This is not a significance
threshold. Mixed/nonpositive corpora count against consistency; no p-value,
selection, tuning, replacement or expansion.

Evaluate each shared initial checkpoint on train/test once before adaptation.
Adequacy A_cs = initial group test NLL - Unoclip F10 group test NLL; average two
seeds per corpus. Require all five A_c>0 for the proposed mechanistic interpretation
to be eligible. Retain/report each A_cs/A_c and mean/SD/range. Failed adequacy
means inconclusive mechanism; it does not delete finite primary results. A
nonfinite value, broken pairing, missing input or cap stop is a terminal incomplete
experiment: preserve partial evidence and do not substitute a favorable subset.

Positive D may mean less benefit, not necessarily a penalty, under clipping.
Report both conditional signs; do not claim that no clipping eliminates a
penalty just from D. No mediation, capacity competition, greater overall
memorization, universal weighting disadvantage, p* peak or scaling curve claim.

## Minimal instrumentation and independent audit

Immediately around each adaptation optimizer.step(), after gradient clipping,
measure actual parameter-step L2 and its ratio to pre-step parameter L2. This
includes AdamW/WD. One reusable GPU float32 snapshot holds 621696 values =
2486784 bytes (~2.37MiB), sorted named-parameter order; copy before, subtract
model values into that buffer after. Float64 scalar norm reductions, no activation
logging, extra persistent snapshots or optimizer archives. It never writes model
parameters/gradients. Existing pre-gradient norms/clipping fractions remain.
If finite denominator<=1e-12, relative norm is None with guard reason; absolute
norm remains. Nonfinite norm/parameters/gradients stops. Snapshot overhead,
temporary reductions and synchronizations are unmeasured and count toward caps.

Audit uses independent data regeneration and masked log-softmax NLL reductions;
all ten initial plus forty final checkpoints, full input equality, policies,
weights/orders/state hashes, 2560 pretraining and 6400 adaptation trace rows.
It computes D and adequacy independently and checks the equivalent difference
of clip effects. Numerical PASS is separate from criterion/adequacy outcomes.
Signed conditional allocation and train/validation/test component metrics remain
secondary, along with descriptive per-arm step summaries and guarded counts.

Outcome-independent fixtures cover four loss/gradient masks, clip/no-clip
gradient checks, actual snapshot steps including AdamW/WD, zero-denominator guard
and nonfinite rejection. These fixtures run only inside the later bounded audit;
none has run now. Tolerances: NLL/component identities 2e-6; objective/gradient
1e-7; snapshot norms 1e-9; recorded scalar ratios/contrast identities 1e-12;
float32 versus float64 pre-gradient-norm fixture 1e-3. AUDIT.json records maximum
observed absolute discrepancy for each tolerance and comparison counts. Audit
does not replay intermediate research optimization or independently reconstruct
every recorded step from unavailable intermediate checkpoints. Independent
source/result reviewers must assess these actual limits.

## Budgets and provenance

Inclusive runtime1800 seconds: preparation/source/census/hash checks, imports,
pretraining, initial/final evaluations, forty adaptations, instrumentation,
receipts and termination. Separate audit600 seconds, likewise inclusive. Global
manual outer watchdog TERM at1790/590, KILL after5; remaining5 seconds for final
receipts. Inner cumulative admission includes15-second grace and postwrite
charges. Worker inherits outer process group; inner cleanup is direct-child
terminate/wait2/kill/wait1. Preserve failure latch and partial evidence, no retry.

512MiB additional allocated storage includes planning document, this bundle,
raw run/results/reviews/receipts and reserves. Preserve64MiB archive+16MiB terminal
reserves inside the cap; normal writes stop at432MiB. Retain>=2GiB free. No archive
is generated. No CPU/cloud fallback or security-policy change. Retain all ten
pretrained and forty final fp32 checkpoints; no optimizer/intermediate archives.

v0132 measured601.933168 runtime/43.409159 audit seconds, but new no-clip stability,
snapshot/reduction overhead and historical I/O mean v0133 feasibility is unmeasured.
Expected runtime10–20 minutes is uncertain; exact design must fail closed rather
than grow caps or change cohort. Source review and separate user launch approval
are still pending. The original planning document and all completed studies stay
unchanged; SOURCE_MANIFEST.json binds this candidate and inherited dependencies.
