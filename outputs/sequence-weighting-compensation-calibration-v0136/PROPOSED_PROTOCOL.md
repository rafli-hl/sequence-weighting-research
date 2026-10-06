# v0136 proposed inverse-exponent compensation: calibration before confirmation

Planning only; 5 October 2026. No implementation, execution, data generation, model computation or runtime authorization is provided by this document. This is a proposed design freeze for independent review, not a launchable experiment. User approval covers preparation of this proposal. Independent planning review (turn 01a10a4c-7f39-76d0-aa77-989bbe1dc8a7) recommended NO-GO for direct compensation now and GO for a gated calibration proposal.

## Question and reason for the gate

Can an exponent measured under a bounded target-weight distribution predict useful allocation under inverse-exponent weighting on different fresh corpora? This is a transport hypothesis about a fitted response, not a mechanism, mediation or scaling claim. Jane Street's inverse-exponent compensation suggestion remains untested by the completed local studies.

The planner's historical warning used p approximately 0.017745: a 4:1 target ratio would imply an input ratio on the order of 1e34. This historical value is not a transferable calibration estimate. Do not insert it into compensation, apply an exponent floor, narrow the target interval, clip weights or tune the optimizer to rescue feasibility.

Target q is sampled log-uniformly on [0.5,2] and divided once by its arithmetic mean across all adaptation-training sequences. This preserves the target ratio bound 4 and gives global mean 1. The same saved q vector and target ranks apply to U, R and C within a matched seed. No batch normalization of weights.

## Canonical policy and pairing

G1 only; width 128/depth 3, 621696 parameters; sequence length 41, vocabulary 84, four shared, four group and four instance answer tokens. Adaptation train 512/validation 256/test 512. F10, batch 32, 160 updates. Native canonical AdamW: LR 1e-4, WD 0.1, betas(0.9,0.999), epsilon 1e-8, gradient clip global norm 1, fresh zero optimizer moments at adaptation start. No capacity sweep, tuning, peak criterion or adaptive seed expansion.

Use the trusted shared-U pretraining policy: train 2048/validation 256, four epochs, LR 3e-4, WD 0.1, clip 5. Preserve its shared-label plus group/instance uniform-answer auxiliary objective. Each nested seed's single pretrained checkpoint initializes every adaptation arm in that matched comparison.

All adaptation arms weight the entire per-sequence loss, with fixed objective mean_i[w_i*(Lshared_i+Lgroup_i+Linstance_i)/3]. Each component is the mean over its four answer tokens. U uses w=1, R uses w=q, and conditional C uses w=q^(1/pcal) followed by one global mean-one normalization. Full tokens, labels, teacher-forced contexts, checkpoints, epoch batch orders and component coefficients are identical across arms within a matched seed. There is no component-specific randomization.

## Fresh seed partition, reserved before any generation

Calibration has three corpus slots CAL-C01/C02/C03, each with nested model/weight slots N01/N02: six pretrained checkpoints and twelve U/R adaptations. Confirmation, if later admitted, has five different corpus slots CONF-C01 through CONF-C05, each with N01/N02: ten pretrained checkpoints and thirty U/R/C adaptations.

Each corpus slot requires separate pretraining and adaptation corpus seeds; each nested slot requires model, q-draw and batch-order streams. Pretraining/adaptation/validation/test example-key namespaces must be disjoint within a corpus. Calibration and confirmation seed streams must be disjoint from one another and every recorded historical tuning, confirmation and diagnostic stream, including v0135. Different model seeds within one corpus are nested repeats, not independent corpus replications.

These are frozen partition identities, not generated integer seeds or a freshness attestation. Exact integer assignments and all derived stream rules must be recorded in a future seed manifest and checked independently against the updated historical semantic census before implementation is approved. No seed is drawn, corpus generated or historical census rebuilt in this planning task. Undocumented/deleted history cannot be excluded by a ledger; document coverage. Any collision, missing input or provenance ambiguity blocks launch rather than causing automatic reseeding.

## Calibration estimand and mandatory eligibility

For each R seed, retain signed unweighted whole-sequence training gains g_i = own_initial_loss_i - F10_loss_i. Do not subtract U's initial loss, weight the evaluated gains, discard negative gains, or replace undefined p by zero. Fit p on the frozen interval [0,8] using the signed normalized-gain cumulative-discrepancy estimator against q^p. Uniform p is undefined.

Let r_i be the midrank percentile (rank_i-0.5)/N of q_i, with ties assigned their average rank. K_ij=min(r_i, r_j). For any candidate p define d_i(p)=g_i/sum(g)-q_i^p/sum(q^p), and RMSfit(p)=sqrt(d(p)' K d(p)). Sorting, normalization and kernel definition are frozen across estimator, audit and target comparison. Do not optimize on test performance.

For each corpus average its two R exponents; pcal is the equal mean of the three corpus means. Leave-one-corpus-out values are equal means of the remaining two corpus means, not individual seeds treated as new datasets.

Calibration passes only if ALL conditions hold:
- Each of the six R seed mean gains is at least 0.05 nats/answer token; p is defined, finite and independently verified, strictly interior to [0,8] with distance greater than 1e-6 from either boundary.
- Each R exponent is at least log(4)/log(1000), approximately 0.2007. This gates the prospective compensation ratio at 1000; it is not permission to clip an excessive ratio.
- Every one of the six R exponents and each leave-one-corpus-out estimate is within 25% of pcal, measured as absolute difference divided by positive pcal.
- Each seed's RMSfit at its verified p is at most 0.02. In each corpus, the mean across its two seeds of RMSfit(0)-RMSfit(p) is strictly greater than 0.01.
- Both U and R have strictly positive own-baseline total validation gain in every corpus (average the two nested seeds first). R minus U final total validation NLL is strictly less than 0.01 nats/answer token in each corpus.

The U control's gains, components and failed learnability cases must also be retained. The numeric thresholds are proposed practical eligibility tolerances, not confidence intervals, equivalence tests or significance thresholds. Test results are retained for descriptive reporting but are not calibration admission criteria. All exponents, fit profiles and every failed condition remain visible.

Any failed or undefined condition means STOP_NO_CONFIRMATION. No extra calibration seeds, narrower q, exponent floor, relaxed tolerances, retuning, replacement corpus or automatic retry. A calibration PASS permits only a report and request for separate confirmation approval. It does not itself authorize generation or training of confirmation corpora.

## Conditional fresh confirmation and primary outcome

Only after calibration passes independent audit and separate user approval, freeze the exact positive pcal and its supporting hashes before generating the five fresh confirmation corpora. Compute the conditional C weights from the saved q using that same pcal in every seed. Record realized min/max ratio and effective sample size. A ratio above 1000, nonfinite weights or any violated resource bound stops; do not clip or renormalize per batch.

For each arm and matched seed, use signed own-initial training gains and the SAME external q target:
d_i = g_i/sum(g)-q_i/sum(q); E = sqrt(d' K d).
The kernel uses q ranks, including for C. Do not rank by achieved gains or refit an exponent/target to define success. Nonpositive total gain makes E undefined; preserve it and block scientific success. Do not coerce to zero, take absolute gains or report a defined-only success cohort.

Compute seed-level E_R-E_C and average two seeds within each corpus, then five corpus means equally. This is the primary allocation improvement, not a component test-loss contrast. Report all five signed corpus contrasts and all ten nested contrasts.

Confirmation succeeds only when every requirement holds:
- Mean(E_R-E_C) is at least 0.01 and all five corpus contrasts are strictly positive.
- C beats U allocation error in all five corpus means: E_U-E_C strictly positive.
- Equal-corpus mean E_C is at most 0.02.
- In every corpus, C minus R and C minus U final unweighted total test NLL are each strictly less than 0.01 nats/answer token.
- All arms learn: every arm/seed has mean own-initial training gain at least 0.05; every arm has strictly positive own-baseline total validation and test gain in every corpus. All required E values are defined.

Average seed-level E values, not gains pooled across seeds, before corpus aggregation. Negative/mixed contrasts and failed utility count against the proposal; no favorable-outcome search. Secondary fitted exponents are diagnostic only and cannot redefine E, pcal, success or sample size.

## Evidence and scientifically independent audit specification

Future implementation must preserve source/config/seed manifests; complete input and batch-order hashes; shared initial and F10 checkpoints; unweighted per-sequence initial/final total and component losses; signed gains; q and actual R/C weights; full fit profiles and boundary/guard reasons; training allocation curves; component train/validation/test losses; weight extrema, ESS=(sum w)^2/sum(w^2); pre/post-clip gradient norms and clipping counts; timings, exit codes, cancellation/termination and storage/free-space receipts.

The independent reviewer must not merely invoke the candidate summary or optimizer helper. Require separately implemented:
1. Input/seed-history reconciliation and full-token/label/context/checkpoint/batch-order pairing, plus direct objective scaling verification.
2. Checkpoint reevaluation using direct unweighted log-softmax reductions; own-initial signed-gain reconstruction; component/total arithmetic checks.
3. Direct construction of K and cumulative-allocation calculations using the frozen target ranks. Check unique/tied target ranks, uniform q, signed individual gains, nonpositive totals, exact-zero error and nonfinite rejection with prospective fixtures only after separate implementation/test authorization.
4. Independent exponent objective/search with checked high-precision arithmetic and full fit profiles. Compare objective and parameter within prospectively approved tolerances; retain ambiguous/boundary cases as blockers, never widen tolerances after failure.
5. Recompute pcal, every leave-one-corpus-out estimate, six seed eligibility records and three validation/fit gate rows; later recompute all ten confirmation contrasts and five corpus gates without reading candidate verdicts.
6. Verify global normalization, conditional inverse weights, realized ratio/ESS, component coefficients, clip 1 policy and resource/exit receipt chains. Confirm no test-based calibration selection, reused confirmation data, dropped failures or retries.

Independent audit must label source acceptance, numerical/provenance PASS and scientific eligibility/success separately. Each gate record contains identity, source hashes, observed quantity, threshold, comparator, defined/undefined reason and PASS/FAIL; a global status is an AND over all mandatory records. Missing/undefined records cannot pass. Proposed outcome statuses: PLANNING_ONLY; CALIBRATION_FAILED; CALIBRATION_PASSED_PENDING_CONFIRMATION_APPROVAL; CONFIRMATION_FAILED; CONFIRMATION_PASSED; TECHNICAL_STOP. Technical stopping preserves partial evidence and does not imply a scientific null.

Independent numerical comparison tolerances, exact integer seed ledger, source/storage estimates and supervised phase commands must be reviewed and frozen during a separately authorized implementation phase; none exists here. These omissions block runtime readiness, not preparation of this document.

## Proposed resource envelopes; unapproved

Calibration: 900 seconds total runtime preparation/pretraining/adaptation/receipts/termination grace, followed by a separately bounded 300-second independent audit. Conditional confirmation: 1800 seconds inclusive runtime and 600-second independent audit. No execution is authorized by these proposed limits.

Across both future phases retain at most 512 MiB additional storage including planning/source/reviews/checkpoints/data/logs/receipts/reserves; normal writes stop at 432 MiB, leaving 80 MiB reserved. Maintain at least 2 GiB free at all times. Calibration evidence remains retained during confirmation: do not delete it to make room. Estimate the combined retained footprint before requesting runtime approval; feasibility is presently unmeasured. If the fixed design cannot fit, report the conflict rather than shrink samples, thin evidence or expand caps.

Fail closed on missing/drifting inputs, broken pairing, nonfinite values, undefined primary records, failed audit or resource/cleanup caps. No automatic retry, failed-directory resume or regeneration. Separate runtime approval must name the reviewed manifest and exact phase envelope. No WSL denial is retried or bypassed by this planning task.

## Background and current decision

Completed v0135 numerical audit passed, but mean attenuation 0.00622637402266264 was below the frozen 0.01 threshold and the uniform utility margin failed in all five corpora. Preserve the negative decision; do not retune that optimizer intervention. Its results do not establish the calibration exponent or transport validity for whole-sequence q weighting.

Planning review provenance: parent-supplied independent planner turn 01a10a4c-7f39-76d0-aa77-989bbe1dc8a7; this document does not claim independent approval of its final bytes. Final proposal review remains a parent task. Original reference is recorded in outputs/sequence-weighting-paper-track-v1/LITERATURE_SOURCES.json (S01/S02).
