# Stage 10 — continuous-search agreement on retained model gains

Version v0.11. Local CPU diagnostic, frozen before new measured objective
evaluations. Planned run: `search-v011-20260930-01`. The user authorized the
NEXT_EXPERIMENT.md follow-up; this protocol does not authorize another training
grid, cloud work, publication, or replacement of historical estimates.

## Question and estimand

Do the saved original continuous-search estimates achieve objectives agreeing
with two independently implemented, higher-precision searches on [0,8], for the
complete saved Stage 9 cohorts? Stage 9 established fixed-grid arithmetic
agreement on these inputs, leaving continuous search unresolved. Stage 10
measures search agreement. Neither finite mesh supplies a global-optimality
certificate. No outcome here establishes statistical recovery, identifiability,
generalization, utility, or a capacity-dependent peak.

The historical fit uses the weight-sorted cumulative signed-gain objective

`J(p) = (1/n) sum_k (G_k - Q_k(p))^2`,

where `G_k = sum_{i<=k} g_i / sum_i g_i`, and
`Q_k(p) = sum_{i<=k} w_i^p / sum_i w_i^p`, after stable ascending weight sorting.
The complete interval is [0,8]. Include its endpoints. The historical saved p
is evaluated separately and never inserted into either search's candidate set,
brackets, mesh, initialization, or tie-breaking rule.

## Cohorts fixed by experimental design

All are the random-weight arm, variants M and U, widths 64/128/256, and all
original confirmation corpus/model-seed cells. Do not select by p*, test score,
fit quality, gain sign, objective size, boundary status, or visible peaks.

| Cohort | Original run | Selection retained | Policy references |
|---|---|---|---:|
| S4_fixed30 | baseline-v05-20260929-01 | Original fixed30, g00, epoch30 | 54 |
| S5_R | utility-v06-20260929-01 | Original primary R validation decision | 54 |
| S6_P1_R through S6_P4_R | stability-v07-20260929-01 | Each original primary R panel decision | 216 |

Copy the entire frozen Stage 9 input set: 324 policy references, 207 distinct
native checkpoints, 186 exact numerical weight/gain inputs, nine distinct
weight vectors, n=512. Deduplication is computational only: retain every alias
and every original loss provenance. Stage-specific native counts are 54/54/99;
exact input counts are 54/48/84. There are three confirmation corpora per stage;
model/weight seeds are nested within corpora, and Stage 6 panels reuse
confirmation corpora and may select the same checkpoint. These counts are not
independent experimental replications.

Retain epoch0, negative-total, boundary, failed-fit and undefined cases. The
complete inventory includes seven numerical guard inputs; their counts are
already recorded by Stage 9 and are not new Stage 10 outcomes. No uniform arm,
Stage 4 epoch60 or secondary selection, or Stage 5–6 J policy is newly added.
No model is trained, inferred, retuned, or selected in this diagnostic.

## Inputs and provenance

Saved train losses are float32. Reconstruct gains as
`(initial_loss32 - current_loss32).double()`: subtract in float32 before
promotion. Promote saved float32 weights to float64 unchanged. Keep gains
signed and preserve both constituent losses for every policy alias. Do not
subtract after promotion, clip negative gains, or impute absent metrics.

Freeze snapshots of the Stage 9 source-bound input inventory, arrays, selected
historical files, original model/context tables, and the final Stage 9 audit and
report provenance. Recheck the copied provenance against current original
files and historical final manifests. Check full token/input/target/kind tensor
equality, original batch-order prefixes, weight assignments, initial checkpoints
and metadata, alias array identity, original fit metadata, and float32 gain
operation order. The Stage 9 provenance reconstruction is copied with its
function AST checked against its immutable parent.

The canonical epoch0 source uses its previously verified design weight vector
and identical initial/current losses. Preserve the original reason
`no_adaptation`, separately from numerical `nonpositive_total_gain`. The
historical numerical guard is constant weight range <1e-12 first, then total
gain <=1e-10, including tiny positive totals. Both new implementations also
compute these guards in their high-precision arithmetic using exact binary64
inputs and threshold values. A disagreement is retained as unresolved.

All original p*, K, training and test records, validation decisions, and
utility/peak gates remain immutable. In particular, Stage 4 initial test losses
were not measured: all 54 initial-test and test-gain values remain null, while
selected test metrics remain available. Preserve signed training gains,
memorization, validation/test losses, original fit quality, clipping and
selection context alongside search diagnostics.

## Primary search: 80-digit derivative brackets

Use Python Decimal with precision 80. Convert each promoted binary64 input via
`Decimal.from_float`, preserving its exact value. Use the exact dyadic mesh
`p=j/64`, j=0,...,512. Compute probabilities with shifted exponentials of
`p*log(w)` and form G by summing normalized gain fractions. For each mesh point
save J and the analytic derivative

`J'(p) = -2 mean_k ((G_k-Q_k(p))*Q'_k(p))`,

`Q'_k(p) = sum_{i<=k} q_i(p)*(log(w_i)-sum_j q_j(p)*log(w_j))`.

Retain all exact-zero derivative nodes and consecutive zero runs. Bracket every
adjacent strict derivative sign change in either direction, including maxima.
Refine every bracket by bisection, stopping when width <=1e-12, an exact zero
is found, or 40 iterations are used. Save initial/final bounds, derivative
values, every sampled derivative, iterations, midpoint and convergence status.

Candidates are every mesh point and the final midpoint of every bracket,
including brackets that fail their iteration limit. Evaluate candidate J at
80 digits. The winner is the exact smallest computed Decimal objective, with
the smallest exact Decimal p breaking exact ties. Trace points other than mesh
points and final midpoints are retained but are not additional candidates.

## Independent reference: 110-digit objective brackets

Use a separate implementation, Decimal precision 110, and exact dyadic mesh
`p=j/128`, j=0,...,1024. Compute unshifted exponentials and normalize cumulative
raw numerators by the full denominator. Form G from cumulative raw gains
divided by the total. This differs from the primary accumulation route.

Bracket every interior mesh point with J <= both neighboring values and
strictly < at least one. Save all exactly equal neighboring mesh pairs. Refine
each bracket by golden section with ratio `(sqrt(5)-1)/2`, choosing the left
update when the two sampled objectives are exactly equal. Stop at width
<=1e-12 or 80 iterations. Save initial/final bounds, every sampled p/J,
iterations, midpoint and convergence status. Every mesh point and every final
bracket midpoint is a candidate. Choose exact minimum J, then smallest exact p.

Do not adapt either mesh or precision in response to results. A sign-change
search can miss roots between subdivisions. A mesh minimum bracket need not be
unimodal, and golden section is not a global certificate. Endpoints and exact
mesh zeros are retained to avoid silently dropping boundary/zero cases.

## Frozen numerical comparisons and classifications

Cross-evaluate both winners at the independent 110-digit objective. Evaluate
the original saved p using its exact binary64 value; do not round a new Decimal
p to binary64. Retain signed differences, rather than replacing them by zero.

Check arithmetic agreement between the 80- and 110-digit implementations at
all 513 shared mesh points, both winners, the saved original point when defined,
and the neighborhood diagnostic points below. At each checked p require
`abs(J80-J110) <= 1e-50*max(1,abs(J110))`. Keep every individual discrepancy and
the largest normalized discrepancy. This tests the compared evaluations; it
does not certify every unsampled p or every derivative value.

Let `S=max(1, max(reference mesh J)-min(reference mesh J))`. Freeze:

| Comparison | Agreement rule |
|---|---|
| Primary vs independent objective | `abs(Jprimary110-Jreference110) <= 1e-18*S` |
| Original vs independent objective | `abs(Joriginal110-Jreference110) <= 1e-12*S` |
| Primary vs independent p | `abs(pprimary-preference) <= 1e-6` |
| Original vs independent p | `abs(poriginal-preference) <= 1e-6` |

Evaluate `preference ± .001`, clipped to [0,8], omitting duplicates and the
winner itself. Preserve each signed objective gap to the reference winner.
Call the sampled neighborhood weak only when every available side has
absolute gap <= the original objective tolerance. A side below the reference
winner by more than the search objective tolerance sets `lower_neighbor` and
an unresolved flag. Neighborhood points never become search candidates.

Flag unresolved domain disagreement, arithmetic disagreement, failed bracket
convergence, between-search objective disagreement, lower neighborhood, or
original objective better than the reference by more than the original
tolerance. Keep negative gaps. Parameter disagreement alone, when objectives
agree, is reported separately and is not an automatic solver failure. Weak
neighborhood is a local diagnostic at the prespecified step, not a confidence
interval or proof of non-identifiability. An original objective worse than the
reference beyond tolerance is a measured historical search disagreement;
retain it without retrospectively changing the estimate.

When both methods agree on a guard, save null numeric comparisons, status
`guard`, and unresolved false. Never encode undefined p or absent measurements
as zero. Every planned case appears in analysis; absent completed comparisons
are `not_run`, with all aliases retained. Failure counts and missing counts
always use explicit denominators. Numerical unresolved cases do not disappear
from summaries, and an integrity audit can pass while reporting such cases.

## Freeze, runtime and failure handling

Before measured objectives, finish outcome-independent known-answer fixtures,
analysis fixtures, independent design review, protocol, source and input
hashes. Freeze all 13 files listed by `common_stage10.SOURCES`, config, checks,
review, environment details and selected input snapshots. Parent hashes and
copied-function AST equality are checked. New run directories are create-only;
source/check/report repairs must use separate versions after a freeze.

Preparation has a separate 1,800-second budget, snapshot size cap 512 MiB, and
minimum 2 GiB free space. The experiment has **one shared 3,600-second numerical
runtime limit**, covering source/input verification, provenance checks, cache
construction, both searches and all numerical comparisons. It is not a fresh
hour for each method or phase. Use one process and check both monotonic elapsed
time and elapsed UTC; enforce the greater duration. Cache each weight vector
once per implementation, process every associated input deterministically,
then release the caches. Save elapsed times and peak process memory.

Write completed primary/reference searches, comparisons and progress as they
finish. If the common ceiling is exhausted, retain completed and partial
records, write END status `BUDGET_EXHAUSTED`, record a partial audit, and analyze
the full planned inventory with remaining cases marked `not_run`. Other errors
produce `FAILED` with preserved evidence. Full-inventory numerical reporting
requires verified source/input/storage integrity; if that integrity fails,
record the failed audit and stop numerical reporting rather than trust the
affected inputs. No automatic retry, precision
escalation, outcome-based subset, replacement run, or Stage 11 follows.
Reporting, archival checks and visual review occur outside the numerical
budget and perform no additional measured searches.

## Analysis and deliverables

Report unique numerical inputs separately from native checkpoints and all 324
policy references. Tabulate the 36 cohort/variant/width cells. Save full meshes,
bracket traces, candidate sets, point comparisons, signed objective gaps,
parameter differences, boundary status, neighborhood diagnostics, all guards,
failures, unresolved cases and missingness. Include original model context.
Plots must retain signed values and null availability, use data-based limits,
and receive visual review. Preserve raw files and source hashes in a local
archive, verify SHA256 and ZIP CRC, and update project handoff records.

Interpret search agreement separately from the earlier fixed-grid numerical
audit and from known-truth recovery or model utility. The intended follow-up
is the bounded Stage 4–10 synthesis. Recheck primary literature before any
novelty claim. Only equivalent scripts are executed; do not call the historical
notebook executed. No publication or venue guarantee is implied.
