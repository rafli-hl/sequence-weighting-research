# v0134 frozen existing-checkpoint gradient panel

Source preparation only, 4 October2026UTC. This is a diagnostic for choosing a
future causal experiment, not a mechanism test, training run or mediation claim.
No evaluation, gradient, Python, tests or WSL execution is authorized now.
Independent exact-source acceptance and separate manual launch approval are gates.

Use exactly the completed v0133-r1 cohort: five corpus seeds91420101..91420105,
two nested model/weight seeds per corpus, and three states at each matched seed:
the shared U-pretrained initial state, Unoclip F10 and Inoclip F10. Thirty saved
parameter states, fully enumerated in INPUT_BINDINGS.json, form one fixed panel.
There is no layer/checkpoint/example search, capacity sweep, new corpus, weight
resampling, test-based selection, tuning, optimizer step or checkpoint mutation.
The old corpus .pt container carries test tensors; deserialization is necessary,
but the code immediately keeps only train/validation and never evaluates or uses
test tensors for a gradient, result, selection or interpretation.

At every SAME parameter state, let L_ij be the mean of that sequence's four answer
token NLLs for component j. Predictions use the existing40-position teacher-forced
input tokens[:, :-1], targets tokens[:,1:], all parameters in the fixed128-wide,
3-layer model, float32 forward/backward and eval mode (this architecture has no
dropout). Flatten gradients in sorted named-parameter order,621696 parameters.
Accumulate vectors, dots, norms and variance reductions in float64.

The validation reference is G_val=mean over all256 validation sequences of L_i,group,
equivalently the mean over exactly1024 validation group answer tokens. It has NO
one-third objective coefficient. gV=grad(G_val). Training's uniform reference is
J_U=mean over all512 training sequences of (L_shared+L_group+L_instance)/3.
gU=grad(J_U). The extra weighting objective is
J_delta=mean_i[(w_i-1)*L_i,instance/3], using the saved unmodified float32 w.
gD=grad(J_delta)=grad(J_I)-grad(J_U) at the same state. Shared/group weights stay
one. No per-batch recentering or renormalization is permitted. These are loss
gradients; weight decay, clipping, AdamW moments and preconditioning are excluded.

Use the FIRST saved adaptation epoch order, exactly512 indices, partitioned into
16 consecutive saved batches of32. Every example appears once. Each batch gD_b
uses its own mean over32 and the SAME1/3 coefficient. gU_b has the same32-row mean.
The population gradients are exactly the means of the16 batch gradients. Validation
is evaluated in its stored index order in eight32-row chunks, each scaled1/8.
No batch, population or state changes based on results are allowed.

For each state report gV norm, gU norm, gD norm, gV dot gD, cosine(gV,gD),
ordinary-descent local slope=-gV dot gD, delta_norm/uniform_norm, and
gV dot gD/(validation_norm*uniform_norm). Negative dot/cosine means the small
ordinary descent perturbation theta-eta*gD locally INCREASES validation group
loss: derivative at eta=0 is -gV dot gD. This is NOT an actual AdamW update.
Historical optimizer moments are absent. No finite model parameter perturbation,
real optimizer step or large gradient archive is added by this diagnostic.

Preserve all16 batch records with their saved ID hashes, extra and uniform norms,
alignment/slope, relative magnitudes and objective values. Report population
variance V_D=mean_b||gD_b-gD||^2, V_U=mean_b||gU_b-gU||^2, RMS dispersion,
sqrt(V_D)/||gU||, sqrt(V_D)/sqrt(V_U), and ||gD||/sqrt(V_D). Population divisor16,
not15, is fixed. Diagnostic variance uses mean norm-square minus full mean
norm-square; audit uses explicit deviations from its independently computed full
gradient. Only negative cancellation roundoff within1e-12 of the larger squared
term may be floored to zero; preserve the raw variance and correction flag.
V_D describes the extra component, not total weighted-gradient variance: covariance
between uniform and extra gradients can change that total. Relative dispersion
may motivate investigating variance, but does not establish greater AdamW noise.

Norm<=1e-12 is a prospective numerical undefined guard, not an outcome criterion.
Guard all ratios/cosines and preserve null plus reasons and defined counts. Do not
delete or replace zero/near-zero states or batches. A seed-pair/corpus/overall mean
is null if ANY constituent is undefined; any defined-only descriptive mean must
be labeled and must not substitute for that strict aggregate. Zero dot is retained.
Negative/positive/zero batch signs are descriptive with undefined counts, never
an inferential sample size or success gate.

For every metric and each of the three states, first average two nested seeds per
corpus, then weight all five corpus means equally. Report all30 seed-state rows,
15 corpus-state rows, three panel-state rows, five-corpus SD/range and signs.
F10-minus-initial scalar changes may be described for each SAME matched seed,
then aggregated in the same hierarchy. They do not add independent replications.
Batches, parameters, states and model seeds are repeated measurements; n_corpus=5.

Interpretation is continuous/descriptive, without a practical/significance
threshold, p-value or automated follow-up decision. Consistently adverse initial
alignment, considered with its continuous magnitude, would motivate proposing an
interference intervention. Little directional conflict with larger extra-gradient
dispersion relative to uniform-batch dispersion would motivate proposing a
variance intervention. F10-only association may be consequence of earlier learning.
Mixed, weak, undefined or favorable initial patterns close this fixed panel rather
than prompting a search; an optimizer-direction/preconditioning intervention may
then be a better question. All outcomes survive in the report. These are prospective
interpretation rules, not permission to launch the next experiment or a proof of
mediation, capacity competition, overall memorization or a universal mechanism.

Independent audit is within the SAME600-second envelope. It does not call diagnostic
loss/gradient/summary routines. At all30 states it computes full256-row validation
group and full512-row training uniform/weighted/delta gradients from direct
log-softmax token masks, independently of diagnostic cross-entropy component means
and chunk accumulation. It verifies gD=grad(J_I)-grad(J_U), full versus16-batch
reductions, all480 frozen batch scalar records, explicit centered variances,
aggregation/null handling and parameter immutability. Both implementations share
trusted vendor forward code and PyTorch autograd; this is not an independently
implemented transformer or derivative engine.

Deterministic float64 CPU fixtures compare objective gradients against analytic
softmax-minus-target coefficients with ignored context tokens, component1/3 and
validation group normalization. Centered finite differences check a fixed logits
direction. Quadratic fixtures verify adverse/favorable/zero ordinary-descent signs,
and explicit zero/undefined guards. Fixtures are small algebra inputs, not new
research corpora. All coefficients and signs are fixed before evaluation.

Frozen audit tolerances: all real-state scalar comparisons and vector identity
checks use abs2e-6 + rel2e-4*max absolute reference magnitude; cosine/projection
comparisons use abs2e-4 plus that relative term. Null/guard flags, identities,
batch counts and discrete metadata must match exactly. CPU analytic and linear
scaling fixtures use abs1e-12; central logits finite difference abs1e-8; quadratic
finite-difference sign derivative abs1e-6. Record raw maximum absolute discrepancy
and maximum fraction of allowed tolerance for every check class. Nonfinite,
missing/mismatched inputs, changed parameters, broken pairing or cap failure is
terminal; no automatic retry, extension, subset, replacement or regeneration.

Combined hard600 seconds includes input/source verification, imports, both phases,
all forward/backward work, scalar files, logs, termination and receipts. Outer
timeout TERM at590, KILL after5, final5 seconds for bounded cleanup/receipts.
Each phase reserves15 seconds inside its remaining allowance; source preparation
does not consume numerical budget because it performs no numerical research work.
Estimate2-6min diagnostic plus1-3min audit is UNMEASURED, not a feasibility result.
Audit includes large full-population forwards and all batch checks; OOM/timeouts
fail closed. Do not downsize or use CPU/cloud fallback after failure.

Additional v0134 allocated storage hard16MiB: source, manifests, review, run,
outputs, logs and receipts;12MiB work allowance leaves4MiB terminal reserve.
Only scalar/provenance JSON/Markdown is retained; no model copies, gradients,
activations, optimizer states or intermediate archives. Expected scientific
scalars are under3MiB and bounded phase logs under1MiB combined;16MiB is conservative.
Also count preserved v0133-r1 bundle/run, failed v0133 bundle and planning document
within512MiB, retaining its80MiB archive/terminal reserves and at least2GiB free.
No old study or evidence is written, moved or deleted. Manual commands are future
commands; prior denied WSL access must not be retried by this agent.
