# v0135 completed result and decision — 5 October 2026

Numerical/provenance status: PASS_NUMERICAL_AND_PRECONDITIONING_AUDIT, recorded in AUDIT.json. Source review: PASS_V0135_SOURCE in ../reviews/SOURCE_REVIEW.json. The parent reports the separate completed result review as PASS; that external review is distinguished from the two local attestations.

The frozen scientific criterion failed. Primary mean D =0.00622637402266264 nats/group answer token (corpus SD 0.003972204354273972), below the prespecified 0.01 threshold. All five corpus D values were positive; that sign consistency does not override the practical threshold.

Uniform own-baseline group learning improved under both optimizer policies in all five corpora. Nevertheless, the prespecified uniform utility margin failed in every corpus: signed U-Adam minus U-isotropic own-baseline group-gain differences were -0.020340846851468086, -0.025421389378607273, -0.028415788896381855, -0.02657982800155878, and -0.02660769410431385 nats. Every absolute difference exceeds 0.01. Their mean is -0.02547310944646597. A failed margin is not failure to learn.

Other recorded gates: native instance penalty positive all five; direct I-isotropic improvement over I-Adam positive all five. These secondary positives do not rescue clean attenuation: practical_criterion_met=false, clean_attenuation_interpretation=false, verdict=practical_preconditioning_attenuation_not_supported.

Decision: close the frozen optimizer intervention with its failed scientific gates. Do not retune thresholds, optimizer, seeds or sample size. This does not prove zero preconditioning influence, formal equivalence, historical mediation or a universal mechanism. Preserve all signed corpus/nested-seed outcomes, checkpoints, traces, snapshots, source and failed evidence.

Evidence: CORPUS_SUMMARY.json, CORPUS_CONTRASTS.csv, PAIRS.json, ALLOCATION.json, AUDIT.json; source acceptance ../reviews/SOURCE_REVIEW.json. The numerical audit records 50 checkpoint reevaluations, 10 complete input regenerations, 6400 adaptation update-trace rows and 27410 discrepancy checks. Its prescribed eight update snapshots are not full intermediate optimization replay.

Next step: document-only gated calibration proposal at ../../v0136-planning/PROPOSED_PROTOCOL.md. Direct inverse-exponent compensation is NO-GO now. Calibration and conditional confirmation runtime envelopes remain unapproved. A new proposal is not a reinterpretation of v0135 as successful.
