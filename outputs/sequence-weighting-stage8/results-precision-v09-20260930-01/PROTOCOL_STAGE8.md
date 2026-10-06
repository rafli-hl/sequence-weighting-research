# Stage 8 v0.9 — fixed-input objective precision diagnostic

## Authorization, scope and freeze

The user authorized NEXT_EXPERIMENT.md on 30 September 2026. Before any new
objective profiles, freeze this protocol, all nine source files, design review,
fixture evidence and copied input hashes in a unique run. This is a diagnostic
on retained Stage 7 data. It creates no fresh statistical replication, model
training, hyperparameter selection or replacement p* estimates. All prior raw
results, continuous fitted p*, peak verdicts and archives remain unchanged.

## Fixed cases and independent units

Select by design indices alone from estimator-v08-20260930-01: every cancellation
case, n={128,512}, generator p={.2,1}, c={1,.1,.01,1e-12,0,-.01}, all 64 draws.
There are 1,536 cases in 24 cells from 128 base weight/noise draws; conditions
within each block are paired. Positive-c cells provide 1,024 candidate profiles;
the 512 c<=0 cases are retained guard controls. Eligibility is evaluated, not
assumed from old p* or fit quality. No draw is selected from observed estimates.
Copy all 128 original NPZ blocks and selected metadata with original seeds,
weights/gain hashes, source IDs and array indices. Do not regenerate gains.
Saved binary64 arrays are the fixed inputs, including their original rounding.

## Grid, domain and mathematical objective

Use the original 161 binary64 grid values p=float(i/20), i=0,...,160, with anchor
p0=0. Promote each actual binary64 grid value exactly, not rational i/20.
The existing continuous p* is evaluated as one extra reference point when
available; it never enters the grid ranking. Its contrast gap versus the grid
minimum may be negative and is not a continuous-optimum certificate.

Order sequences by increasing saved weight. Let G_k be cumulative normalized
signed gain and Q_k(p) cumulative normalized w^p. The objective is
J(p)=mean_k[(G_k-Q_k(p))^2], including the last prefix. Its anchored contrast is
D(p)=J(p)-J(0)=mean[(Q(0)-Q(p))*(2G-Q(p)-Q(0))]. Individual gains remain signed.
The legacy guard and constant-weight threshold are unchanged; the decimal route
compares against exact binary64 representations of 1e-10 and 1e-12. Record both
domain decisions and any mismatch; unavailable routes remain null. No filters.

## Prespecified arithmetic routes

1. **Legacy64 J and naive D64:** preserve core.py's operation order: Python sum
   in original gain order, binary64 log/exp/max shift and normalization, sorted
   sequential c += normalized_gain - normalized_model_mass, then loss += c*c.
   Cache model probabilities only after their original binary64 divisions.
   Evaluate naive D64 by subtracting the two legacy objectives.
2. **Factored D64 diagnostic:** use the same legacy gain total and binary64 model
   probabilities, but separate sequential G/Q prefixes, and math.fsum of the
   factored contrast products above. This changes algebra and accumulation;
   any improvement cannot be attributed solely to removal of a common offset.
3. **Decimal80 reference profile:** Decimal.from_float promotes all saved weights,
   gains and grid inputs exactly. Recompute total, log, shifted exp, normalization
   and prefixes within precision 80; save full decimal strings for J and factored
   D. Verify D versus J-J0 before conversion. This comparison changes precision
   throughout the objective pipeline, not only the final sum of squares.
4. **Independent Decimal110 audit:** independently rebuild all model probabilities,
   normalization and prefixes from the same binary64 inputs, without importing
   precision_math.py or promoting an 80-digit cache. Compute J and D=J-J0 at 110.
   Preserve every 110-digit profile and all convergence checks in raw audit files.

Caching is per weight block and precision. Every measured cache construction is
included in that phase's runtime. Original gain sum, math.fsum and decimal sum
are all recorded to expose normalization differences. No high-precision result
is treated as the unknown unrounded data-generating input.

## Numerical verification and frozen summary rules

At every eligible grid and original-p point require
abs(J80-J110)<=1e-50*max(1, abs(J110)). For contrasts use
abs(D80-D110)<=1e-50*max(1, max_grid(abs(D110))). The 80-digit factored/direct
identity uses the corresponding contrast-scale 1e-50 bound. Failures are saved
and stop acceptance; never relax the tolerance or drop difficult profiles.
The higher precision is a checked numerical reference, not exact arithmetic.

Reference near-tie band per profile is tau=2e-50*max(1, max_grid(abs(D80))).
Save first-index strict minima for every route, exact floating ties and reference
minimizer sets within tau. For all 12,880 grid pairs per profile, distinguish
reference near-ties, strict ordering reversals and float ties on reference-strict
pairs. Report denominators explicitly. Decimal arithmetic is retained through
comparison/error calculations; only final plotting may convert metrics to float.

Report per-case and per-cell: eligibility/domain differences; grid-minimum index
agreement; reference contrast regret at each route's chosen grid point; exact
and tolerance-aware ties; objective/contrast maximum errors; errors normalized
by max(1, max_abs_reference_D); full reference contrast span and top-two gap;
legacy-total versus decimal-total difference; original-p contrast gap against
grid minimum. Tolerance-aware regret is larger than tau, not a new fit-quality
filter. Near-zero gaps do not prove statistical identification. Retain all
24 cells and all undefined values. Conditional summaries state denominators;
unconditional metrics remain null if required values are undefined. Frequencies
across paired cells are descriptive counts, not extra independent Bernoulli trials.

The grid comparison does not validate the continuous ternary search, isolate
all numerical causes, establish population recovery, or justify retrospective
replacement of Stage 4–7 estimates. Low signal/noise remains a separate issue.

## Checks, runtime and deliverables

Before outcomes, test exact binary64 promotion, faithful legacy evaluation at
the stored estimator candidate on independent fictitious arrays, factored
contrast identity against exact rational fixtures, independent 110-digit
convergence, guard/null preservation, and synthetic ranking/tie/summary cases.
Fixture seeds/arrays are separate from retained measured cases. Bind fixture
and scoped design-review records to all current source hashes before freezing.

Use local Ubuntu WSL work/.venv-wsl/bin/python, one CPU process. Each experiment
and independent audit has its own 3,600-second ceiling, measured with both UTC
and perf_counter and enforced with the larger elapsed time, from before cache
construction to final checks. No implicit resume/retry, replacement cases,
reduced grid or adaptive precision; preserve partial output on failure. Record
per-case timing, phase timing, peak RSS, environment lock and >=1 GiB free-space
preparation check. Model losses, memorization, clipping, token pairing and GPU
memory are inapplicable to this fixed-input estimator diagnostic.

Frozen source: core.py, precision_math.py, stage8.py, check_stage8.py,
audit_stage8.py, analyze_stage8.py, analysis_checks.py, this protocol and README.
Raw records include copied inputs, profiles at both precisions, source/input
manifests, config, checks, audit and resource records. Historical integrity
coverage is all prior versioned output files plus raw top-level/source snapshots;
old full model/sequence arrays are preserved but not all rehashed. Three figures,
complete tables/report, archive SHA/CRC, visual inspection and updated handoff
are required for acceptance. Use versioned presentation repairs if needed.
No cloud work, upload, publication, new novelty claim or venue guarantee.
