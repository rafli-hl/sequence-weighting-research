# Bounded synthesis: Stages 4–10

Dated 2026-09-30. Stages 4–10 below use their final audited reports. Stage 10 completed with [independent final verification PASS](FINAL_REVIEW-search-v011-20260930-01.json), including saved bracket/classification replay, all report summaries, source/input provenance, visual review and archive CRC/SHA256. This document consolidates existing evidence without changing estimates, selections, gates or experimental protocols.

## Scientific question and current answer

The research asks whether a capacity-dependent peak in the fitted sequence-weighting exponent survives useful adaptation and validation selection, and whether the estimator is numerically trustworthy. The evidence supports a bounded methodological case study: pretraining and adaptation policy affect the descriptive peak; the primary useful-adaptation criterion fails across the four fresh tuning panels; numerical fidelity and recovery answer separate questions. The present results do not establish a general scaling mechanism.

M uses shared-only loss on mixed pretraining tokens; U adds uniform-target cross-entropy on group/instance positions. Their matched comparison changes the pretraining objective and may change representations and adaptation dynamics. R selects random-arm validation NLL; J selects mean validation NLL across random/uniform arms. Neither uses p*, test scores, fit quality or a visible peak. K = p* at middle capacity − max(p* at small, p* at large); undefined values propagate.

## Evidence by question

| Stage / question | Preserved evidence | Main limit | What remains unresolved |
| --- | --- | --- | --- |
| [4: pretraining and gain reference](../sequence-weighting-stage4/results-baseline-v05-20260929-01-r2/REPORT.md) | At fixed optimizer/epoch30, U−M mean K = 4.600252; U’s peak survives and M’s disappears. U’s middle-capacity mean fit objective is 2.600139 versus M’s 0.000177; 2/9 U fits hit p=8. At epoch60 U’s peak disappears. | U−M changes more than a scalar baseline. Reference swapping is an arithmetic diagnostic; some contrasts are undefined. Stage 4 did not measure own-initial test losses. | A causal account of the baseline/representation/dynamics effects, and a peak supported by useful adaptation and satisfactory model fit. |
| [5: useful adaptation versus epoch0](../sequence-weighting-stage5/results-utility-v06-20260929-01-r1/REPORT.md) | Primary U/R/random utility passes at widths 64/128 and fails globally: width256 selects epoch0. Test gains are 0.030936, 0.001879, 0; 9/27 p* values are undefined. | Middle-capacity improvement is small; one tuning panel does not establish selection stability. One of nine middle-capacity pairs worsens on test, despite all three corpus means passing. | Reproducibility of the primary utility result under fresh tuning panels, addressed by Stage 6. |
| [6: fresh-panel selection stability](../sequence-weighting-stage6/results-stability-v07-20260929-01/REPORT.md) | Largest U/R/random model selects epoch0 in 3/4 panels; middle-capacity utility passes in 0/4; global utility fails in all four. All primary K verdicts remain inconclusive_undefined. | Four panels share the same three confirmation corpora and reuse selected checkpoints. Panel variation combines tuning data, pretraining and model/weight seeds. | Broader population stability and a useful-adaptation peak remain unestablished. Numerical audits cannot change this utility result. |
| [7: recovery and guard behavior](../sequence-weighting-stage7/results-estimator-v08-20260930-01-r1/REPORT.md) | 8,320 fits; 5,328 defined and 2,992 undefined. Noiseless in-range error above the guard is at most 8.52574e-12. At scale1e-14, all 2,048 recovery evaluations are guarded. At c=1e-12 all 256 fits are defined, with conditional RMSE 3.84717–5.13481. | There are 128 independent weight/noise blocks; conditions within a block are paired. Changing c changes signal-to-noise ratio and cancellation together. | Numerical ranking errors and finite-sample recovery error require separate diagnosis; neither follows from defined p* alone. |
| [8: grid arithmetic on synthetic cancellation profiles](../sequence-weighting-stage8/results-precision-v09-20260930-01-r2/REPORT.md) | Of 1,536 saved profiles, 1,024 are comparable. Legacy and naive contrasts match the high-precision grid argmin in 987/1,024; factored contrasts match 1,024/1,024. All 37 legacy mismatches occur among the 256 c=1e-12 profiles. | Factoring changes algebra and accumulation. Grid fidelity does not measure generating-exponent recovery or validate continuous optimization. | Whether numerical problems occur on retained trained-model gains, addressed by Stage 9. |
| [9: grid arithmetic on complete saved model cohorts](../sequence-weighting-stage9/results-model-precision-v010-20260930-01-r2/REPORT.md) | All three arithmetic methods match the high-precision grid argmin for all 179 comparable inputs; seven guards remain. There are 186 distinct inputs, 207 native checkpoints and 324 policy references, with no guard disagreement or unresolved reference classification. | These counts include repeated panels/aliases. Agreement is checked on a 161-point grid and saved p; no true exponent is known for these model gains. | Continuous-search agreement, addressed by Stage 10; statistical recovery and held-out usefulness remain separate. |
| [10: independent continuous searches](results-search-v011-20260930-01/REPORT.md) | All 186 inputs completed: 179 compared, seven guards, zero unresolved or missing; all 324 policy references retained (269 compared, 55 guards). The two searches agree in objective and p for 179/179 comparable inputs. Original objectives agree for 179/179; original p agrees for 175/179 at tolerance 1e-6. All 93,435 saved arithmetic checks pass; numerical runtime is 15.41 minutes. | Finite meshes and local refinement provide no global-optimality certificate. Original p does not enter either candidate set. Objective and parameter agreement use different frozen tolerances. | Statistical recovery, causal mechanisms and held-out utility remain unestablished by search agreement; the four original-parameter discrepancies remain reported. |

## Utility and peak verdicts remain unchanged

Stage 4 uses its original generalization criterion. Its “survives” rule requires all nine K values to be defined and positive; it does not require the later Stage 5 useful-adaptation gate. F/T denote fixed/selected optimizer; C30/C60 denote common epochs; ET denotes the selected epoch vector.

| Stage 4 condition | F/C30 | F/C60 | T/C30 | F/ET | T/ET |
| --- | --- | --- | --- | --- | --- |
| S | disappears | survives | survives | disappears | disappears |
| M | disappears | survives | survives | disappears | disappears |
| U | survives | disappears | survives | mixed/inconclusive | inconclusive_undefined |

All Stage 4 random-arm generalization gates fail. Its uniform-arm gate passes only for S/T/ET and M/T/ET. These historical gates are not relabeled as the later utility gate.

Stage 5–6 utility requires nonzero adaptation, positive test improvement in every corpus mean and validation no worse than the initial model in every corpus mean, at every capacity for the global gate. Scaling is a separate criterion. The following tables preserve the original global utility and K verdicts; full capacity/corpus and scaling tables remain in the linked reports.

| Stage 5 policy | Random global utility | Random K verdict | Uniform global utility | Uniform K verdict |
| --- | --- | --- | --- | --- |
| M/R | True | mixed/inconclusive | True | undefined_uniform |
| M/J | True | mixed/inconclusive | True | undefined_uniform |
| U/R | False | inconclusive_undefined | False | undefined_uniform |
| U/J | False | disappears | True | undefined_uniform |

| Stage 6 policy / arm | Global utility P1, P2, P3, P4 | K verdict P1, P2, P3, P4 |
| --- | --- | --- |
| M/R random; M/J random | True, True, True, True | mixed/inconclusive in all four |
| M/R uniform; M/J uniform | True, True, True, True | undefined_uniform in all four |
| U/R random | False, False, False, False | inconclusive_undefined in all four |
| U/R uniform | False, False, False, True | undefined_uniform in all four |
| U/J random | False, False, False, False | inconclusive_undefined, inconclusive_undefined, mixed/inconclusive, disappears |
| U/J uniform | False, True, True, True | undefined_uniform in all four |

## Interpretation and reporting boundaries

- **Numerical fidelity:** Stage 8 identifies grid-ranking failures in extreme synthetic cancellation cases. Stage 9 finds no corresponding grid mismatch in its complete saved model cohorts. Stage 10 finds agreement between both bounded searches and objective agreement with every defined original estimate under the frozen tolerances. These are different input populations and numerical questions.
- **Recovery:** Stage 7 demonstrates accurate noiseless recovery above the guard and poor recovery in specified noisy/cancelling conditions. More precise objective evaluation alone does not establish a true exponent, finite-sample identifiability or accuracy on trained-model gains.
- **Utility:** Stage 5’s small primary middle-capacity benefit does not meet the same utility criterion in any Stage 6 fresh panel. The original failed utility gates and undefined peaks remain evidence even if numerical searches agree.
- **Context:** Keep signed gain mass/cancellation, fit objectives, boundary frequencies, training memorization, validation/test losses and clipping alongside p*. Stage 4’s 54 absent own-initial test measurements and gains remain null in the Stage 9–10 cohorts; all 324 selected test measurements remain available. No zero or proxy is substituted.
- **Scope:** Three capacities cannot show a shift between two interior peaks. Nested model/weight seeds and repeated panels are not independent corpus replications. The synthetic task is not an exact replication of large-LM/private-text training; one Pythia size/seed cannot support a scaling curve.

## Bounded paper preparation

Organize a research note around three claims supported by the existing record: sensitivity of the descriptive exponent to pretraining/adaptation policy; limits of useful adaptation under replicated validation selection; and the distinction between availability, recovery and numerical fidelity. Present every prespecified failure and undefined outcome, with the local source/audit/archive trail and the full historical verdict tables as supplements.

Stage 10's largest absolute between-search objective gap is 7.83201e-26; the largest original-minus-reference objective gap is 3.48804e-15. Four original p values differ by more than 1e-6 (largest absolute difference 3.60684e-6) while satisfying objective agreement. This is parameter disagreement under objective agreement, not a measured weak-neighborhood finding: the prespecified ±.001 weak-neighborhood flag is false for all 179 comparable inputs. No original point beats the independent search beyond tolerance. The objective tolerances are 1e-18·S between searches and 1e-12·S for original points, with S=max(1, reference-mesh objective span); historical p*, K and selection remain unchanged.

The existing record is ready for bounded manuscript organization and a source-by-source claim audit. A subsequent research decision should identify one specific scientific gap that materially changes the paper argument before proposing more computation. This synthesis authorizes no new training or numerical run. Recheck primary literature before making any novelty claim; publication readiness and venue suitability have not been established. Only equivalent scripts were executed, not the historical notebook.
