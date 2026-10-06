# v0136 calibration: result and decision

5 October 2026 UTC. **Bounded runtime and independent numerical audit completed; scientific status: CALIBRATION_FAILED.** The parent-supplied final independent Astra result review accepted the numerical evidence and retained that decision. Close this calibration without inverse-exponent compensation confirmation.

## Frozen design and gate result

G1, width 128/depth 3, fixed F10, canonical AdamW LR 1e-4/WD 0.1/clip 1. Three fresh corpus draws, two nested model/weight seeds per corpus, six shared-U pretrained checkpoints and twelve matched U/R adaptations. U weights all components uniformly; R applies one globally mean-normalized log-uniform [0.5,2] target q to the whole sequence. Tokens, labels, teacher-forced contexts, initial checkpoints, batch orders and component coefficients were paired. There is one synthetic capacity and three independent corpora, not six independent corpus replications.

The independently checked descriptive pcal is **0.02403094734957752**, averaging two seed exponents within each corpus, then three corpus means equally. All six fitted exponents are defined and interior, but none passes profile identification. A defined small residual is not a sufficiently identified or transportable calibration.

| Frozen eligibility requirement | Passed |
|---|---:|
| Mean R training gain >=0.05 | 6/6 seeds |
| Profile identification | **0/6 seeds** |
| p >= log(4)/log(1000), approximately 0.200686664 | **0/6 seeds** |
| Absolute fit RMS <=0.02 | 6/6 seeds |
| Seed p within 25% of pcal | **3/6 seeds** |
| Corpus mean RMS improvement over p0 >0.01 | **0/3 corpora** |
| Positive U and R own-baseline validation gains | 3/3 corpora for each arm |
| R-minus-U validation cost <0.01 | 3/3 corpora |
| Leave-one-corpus-out p within 25% of pcal | 3/3 corpora |

The observed improvement over p0 is 0.002302767,0.002737650 and 0.003074565 by corpus, below the frozen 0.01 requirement. Passing aggregate learning and utility conditions cannot override failed identification, minimum-exponent, seed-stability or improvement gates.

## Component interpretation

The final independent review summarized the saved own-initial and R-F10 component metrics: mean group training NLL reduction **2.728775 nats/group-answer token**, versus instance training reduction **0.043607 nats/instance-answer token**. R instance NLL increased from its own initial baseline by **0.021207 on validation** and **0.021572 on test**, in component-token units. These are component losses without division by three.

Positive total training/validation gains therefore do not establish instance generalization. The component averages alone do not identify dependence of gains on q, prove that group learning causes the fitted exponent, or justify a component-specific compensation rule. The aggregate component values above are final-review-reported summaries of existing records, not a new computation performed while writing this decision.

## Audit, resources and limits

Runtime: 06:23:48–06:29:26 UTC, **338.456018133 seconds** inclusive, below 900. Audit: 06:38:49–06:39:43 UTC, **53.643908799 seconds** inclusive, below 300. Both outer exits were 0; containment confirmed group termination, no survivors, wrapper reaping and zero cancellation. Existing resource receipts remain within the frozen storage/free-space caps.

[AUDIT.json](AUDIT.json) reports PASS_CALIBRATION_NUMERICAL_AUDIT, six complete input regenerations, 24 checkpoint reevaluations and four prescribed first/last real-step checks. Its **discrepancy_count 2779 is a comparison count, not 2779 failures**. Maximum evaluation discrepancies and unused tolerance margins were not retained; no zero-error or quantified tolerance-slack claim follows. The audit shares trusted architecture/autograd, and four checked steps are not full optimizer replay. Bounded solver agreement and the finite-profile rule are not global-optimality, confidence-interval or universal scaling results.

## Closed decision and evidence

Compensation confirmation is **blocked by the frozen protocol**. pcal remains descriptive and must not become a compensation exponent. Do not change thresholds, floor exponents, clip weights, narrow q, select favorable seeds, expand the panel or automatically rerun. No new protocol or implementation is authorized.

- [Independent decision](CALIBRATION_DECISION.json), SHA256 777fd45feaf04e1fe7b7462fe12faf56857667d8d4702302461a062608ebde60.
- [Numerical audit](AUDIT.json), SHA256 8f72f522dc2100729a3fe6f846af1fcdbfa655629de24a1238d01a5ba6888dbf.
- [Independent fits](INDEPENDENT_FITS.json), [frozen protocol](../FROZEN_PROTOCOL.md), original receipts and full component arrays/metrics under work/runs/compensation-calibration-v0136-20261005-01.
- Source manifest remains 6bc67e09f61bbeb78ad38f26778408b2b051671a8e26d4f657e62f6e7b2f7865.

These two closing records involve Windows file reads/writes and preservation hashes only. No experiment, numerical audit, WSL call or numerical rerun accompanied them.
