# Stage 9 — numerical precision on retained model gains

Version v0.10; local CPU diagnostic, frozen before new objective profiles.
Authorization: user requested the follow-up in NEXT_EXPERIMENT.md. No training,
model inference, cloud execution, publication, or original-result replacement.

## Question and scope

Does the objective ranking failure observed on the Stage 8 extreme synthetic
cancellation inputs also occur on the saved Stage 4–6 model gains? This diagnostic
checks numerical fidelity of objective evaluation on a fixed grid. It does not
validate continuous optimization, parameter recovery, identifiability, usefulness,
or a scaling/peak claim. Original p*, K, selections and gate verdicts are retained.

## Complete design cohorts (selection fixed before new comparisons)

All cohorts use the random-weight arm, variants M and U, and widths 64/128/256.
Each variant/width/corpus/model-seed cell is included, without conditioning on
test scores, p*, objective size, boundary status, signed gain, or visible peaks.

| Cohort | Original run | Confirmation corpus / pretrain seeds | Model/weight seeds | Rule | References |
|---|---|---|---|---|---:|
| S4_fixed30 | baseline-v05-20260929-01 | 41843/95201, 43997/95202, 46219/95203 | 601,602,603 | original F,C30; g00, epoch30, LR1e-4, WD.1, clip1 | 54 |
| S5_R | utility-v06-20260929-01 | 52919/96201, 55049/96202, 57163/96203 | 801,802,803 | existing primary R validation decision for each variant/width | 54 |
| S6_P1_R through S6_P4_R | stability-v07-20260929-01 | 61103/97201, 61211/97202, 61319/97203 | 1001,1002,1003 | each of the four existing primary R panel decisions | 216 |

The pre-comparison inventory contains 324 policy references, 207 distinct native
checkpoints and 186 distinct exact numerical (weight,gain) inputs, each n=512.
There are nine distinct promoted weight vectors. Stage-specific native counts
are 54/54/99; distinct input counts are 54/48/84. Numerical deduplication retains
every alias and loss provenance. Distinct zero-gain initializations can share an
input, and panels can share a native checkpoint. These counts do not represent
324 independent experiments. Dataset replication is three corpora per stage;
model/weight seeds are nested and Stage 6 panels share confirmation corpora.

The Stage 4 epoch60/secondary selections, Stage 5–6 J policies, uniform arms and
arithmetic-reference swaps are outside the prespecified cohort. Epoch0,
negative-total, boundary, failed-fit and undefined records inside the cohorts
remain included. No new validation tuning or model selection occurs.

## Inputs, operation order and pairing

The measured scalar train losses are saved float32 tensors. Compute
`g = (initial_loss - current_loss).double()` with subtraction in float32, exactly
as in historical fitting. Promote saved weights to float64 without modification.
Do not subtract promoted losses or average component gains. The copied loss
vectors and original files retain both constituent losses for every alias.
Each saved loss and weight vector has length512, finite values and positive weights.

For canonical epoch0, current loss equals initial loss exactly. Its random weight
vector comes from the lexicographically first saved M/random assignment for the
same stage/width/corpus/model-seed, verified against the original pure weights
function. This only supplies a design weight vector; no model is evaluated.
Keep original policy reason `no_adaptation` separate from the numerical guard
`nonpositive_total_gain`. The historical guard includes **total <= 1e-10** (zero,
negative, and tiny positive totals); constant weights use range < 1e-12 first.

Bind all selected original raw files to the historical final report manifests,
and bind source, selection, result, dataset, initialization and assignment hashes.
Snapshot selected input/provenance files and compare full source vs copied
dataset tensors: train/validation/test token arrays, shifted input/target labels
and kind labels, not just IDs or hashes. Across relevant references within each
stage/corpus/model-seed verify exact weights and shared batch-order prefixes.
Initial losses agree only within the same variant/capacity/corpus/model-seed.
M and U intentionally have different initial models. Reused native references
must preserve identical loss/weight/gain arrays. No inference regenerates arrays;
some Stage 6 intermediate model binaries were not retained under its protocol.

Deduplicate by SHA256 of concatenated little-endian float64 weight and gain bytes,
with exact input identity and original stored p/objective agreement checked.
All policy aliases and native IDs are retained. Store dtype/shape/byte hashes for
the original float32 losses/weights and promoted gains. SHA-collision ambiguity
or contradictory stored-point metadata stops preparation; no silent collapse.

## Frozen arithmetic and comparisons

Use Stage 8's byte-identical `precision_math.py`, and unchanged Stage 4–8 `core.py`
only for fixtures/provenance. Never run its optimizer on the measured cohorts.
The grid is the 161 binary64 values `i/20`, i=0..160, over [0,8], with fixed anchor
p=0. Decimal receives the exact binary64 values via Decimal.from_float, including
grid points, weights and gains. Stored historical p is evaluated once as an
off-grid reference point, never added as a grid candidate or used for selection.

Compare legacy J64, naive anchored D64 = J64(p)-J64(0), factored D64 using the
unchanged Stage 8 factorization/`math.fsum`, and Decimal80 J and D. The factored
route changes algebra and accumulation together; attribution is not isolated.
Independent Decimal110 source reconstructs model profiles and contrasts from the
same exact inputs. Independently reproduce all three float64 routes. Preserve
full Decimal80 and Decimal110 values, including guarded results and every failure.

Legacy normalization uses Python sequential sum, whereas saved fit metadata uses
Torch float64 sum/mean. Report both routes without requiring universal identity.
For every defined historical p, J64 at that exact p must equal its original saved
objective exactly. Verify mathematical guard vs historical policy reason mapping.

80/110 convergence tolerance is 1e-50 times max(1,abs(J110)) for absolute J;
for D use 1e-50 times max(1,max(abs(D110))). The anchor identity is checked at80
and110 digits. Reference ranking resolution is tau = 2e-50 times that contrast
scale. Validate all grid and stored points; compare exact and tau-level minima,
strict pair order and tau-level pair classifications. Any unresolved
80/110 classification is reported; do not adapt precision, tolerance or grid.

## Summaries fixed before profiles

Keep unique-input and policy-reference analyses separate. Report guard counts,
domain mismatches, unresolved reference classifications, exact and tau-minset
agreement, raw ties, strict reversals, reference regret, J/D absolute errors and
errors relative to contrast scale/span. Report full grid contrast span, top-two
gap, normalization differences and signed stored-point gap vs grid minimum.
A negative stored-point gap is allowed and is not proof of continuous optimality.

Join every reference to its original train/validation/test losses, own-initial
loss changes, group/instance memorization losses, clipping/training gradient
summaries, original p/objective/bounds, signed total and absolute gain mass,
negative-gain fraction and cancellation ratio total/sum(abs(g)). Zero absolute
mass gives an undefined ratio. Retain full diagnostics and histories in JSON.
Summarize by each of six cohorts, variant and capacity (36 cells, nine references
each), preserving all nulls and their denominators. No significance tests or
independence claims for shared inputs/panels. Figures show availability/agreement,
numerical error/separation, and descriptive measured loss/cancellation context.
Do not re-evaluate, rescue or replace prior utility/scaling/peak gates.

## Freeze, resource limits and failure policy

Before any measured comparisons, freeze all15 source files, configuration,
source-bound rational/signed/guard/float32 fixtures, aggregation fixtures and an
independent design review. Snapshot exact input/provenance files and inventory,
then write FREEZE. Separate START follows it. Primary80 and independent110 each
have a 3,600-second CPU wall budget, checked with monotonic and UTC elapsed time,
including source/input checks and all cache construction. Preparation budget is
1,800seconds; input-source snapshot cap1GiB and minimum free disk2GiB. Fixed
counts/grid/precision only; no post-outcome sampling, adaptive stopping or retries.
No GPU is used. Capture environment, sources, runtime and peak RSS. Preserve all
partial profiles and failure records. An exceeded budget or failed mandatory
check stops that phase with no implicit resume or overwritten output.

The historical integrity manifest covers prior stage outputs and prior raw
top-level/source/analysis-source files; selected raw arrays have their additional
origin-file manifest. It does not claim a fresh hash pass of all model binaries.
Analyze only complete source/input/audit-verified records. Use a unique result
directory, render and inspect all figures, and archive source/raw/report files
with SHA256 and ZIP CRC verification. Any presentation-only revision preserves
the original artifacts and all measured raw bytes.

## Interpretation boundaries

These are synthetic-task model arrays, not an exact large-LM replication. Grid
agreement cannot validate continuous search or statistical recovery. Numerical
fidelity does not make a weak fit useful or a nonpositive-gain fit defined.
Stage 6 primary usefulness/peak limitations remain unchanged. Three capacities
cannot establish movement between two interior peaks. No new novelty or venue
claim is made; such claims require a fresh primary-literature review.
