# Stage 10 — continuous-search agreement on retained model gains

Run `search-v011-20260930-01` ended with status **COMPLETE**; infrastructure/provenance audit: **PASS**. The complete design retains 186 distinct weight/gain inputs, 207 saved native checkpoints and 324 policy references. Original estimates, model selections and utility conclusions remain unchanged.

## Coverage and measured agreement

| Counting unit | Planned | Compared | Guard | Unresolved | Not run |
| --- | --- | --- | --- | --- | --- |
| Distinct inputs | 186 | 179 | 7 | 0 | 0 |
| Policy references (reused inputs) | 324 | 269 | 55 | 0 | 0 |

| Diagnostic (distinct inputs) | True | False | Available | Unavailable |
| --- | --- | --- | --- | --- |
| precision_converged | 179 | 0 | 179 | 7 |
| search_objective_agreement | 179 | 0 | 179 | 7 |
| parameter_agreement | 179 | 0 | 179 | 7 |
| original_objective_agreement | 179 | 0 | 179 | 7 |
| original_parameter_agreement | 175 | 4 | 179 | 7 |
| original_better_than_search | 0 | 179 | 179 | 7 |
| weak_neighborhood | 0 | 179 | 179 | 7 |
| unresolved | 0 | 186 | 186 | 0 |

All denominators include the full design. Conditional rates use only available comparisons and are explicitly labeled; an unavailable comparison is not an agreement or disagreement. Guards retain their mathematical reasons, epoch 0 retains historical `no_adaptation`, and interruption leaves explicit `not_run` records. Numerical disagreement and incomplete convergence remain reported.

## Frozen search methods and limits

The primary Decimal80 search scans 513 points j/64 on [0,8], retains every mesh point (including endpoints and exact-zero derivative nodes), and bisects every strict derivative sign-change bracket to width 1e-12 with at most 40 iterations. Its candidates comprise all mesh points and final bracket midpoints. The independent Decimal110 search uses a different algorithm: 1,025 points j/128 and golden-section objective refinement of every declared mesh-local-minimum neighborhood to width 1e-12 with at most 80 iterations. Its candidates comprise all mesh points and final bracket midpoints. Candidate, mesh, bracket, derivative, refinement and failure records are retained in the raw run. The frozen protocol and config define plateau handling, deterministic ties and all convergence rules.

Both candidate points and the saved original point are compared using Decimal110 arithmetic. The search-agreement objective tolerance is 1e-18 times the frozen profile scale; original-point objective tolerance is 1e-12 times that scale; parameter tolerance is 1e-6. Per-input scale/tolerances and signed gaps remain in the tables. Different parameter values may be objective-equivalent in weakly separated profiles. Precision convergence and objective/parameter classifications remain separate.

Neither search provides a global-optimality certificate. Finite meshes and local refinements can miss stationary structure; agreement means agreement between these bounded searches. A saved original point lower than the reference beyond tolerance is unresolved reference-search evidence. The original point never participates in candidate selection. The shared numerical search/audit ceiling is one hour, checked with monotonic and UTC elapsed time, including verification and cache preparation. No adaptive retry, grid expansion or outcome-based subset is permitted.

| Quantity | Available /186 | Conditional mean | Minimum | Maximum | Negative / zero / positive |
| --- | --- | --- | --- | --- | --- |
| search_signed_gap | 179/186 | 1.10309e-26 | -2.97717e-26 | 7.83201e-26 | 71/3/105 |
| original_signed_gap | 179/186 | 5.21657e-17 | 0e-109 | 3.48804e-15 | 0/3/176 |
| search_parameter_delta | 179/186 | -4.96929e-15 | -5.83987e-13 | 6.30010e-13 | —/—/— |
| original_parameter_delta | 179/186 | 1.41087e-8 | -0.00000134717 | 0.00000360684 | —/—/— |
| reference_mesh_span | 179/186 | 0.347221 | 0.0880290 | 2.67031 | —/—/— |

![Signed objective gaps](objective-gaps.png)

![Parameter differences](parameter-differences.png)

Signed gaps and Decimal strings are preserved without clipping. Summary arithmetic uses 110 decimal digits. Nulls prevent an unconditional mean; conditional statistics retain availability counts. Boundary counts distinguish exact endpoints and proximity within 1e-6, while historical boundary flags remain unchanged in model-context records. Neighborhood points and their signed objective gaps remain fully recorded; weak neighborhoods describe numerical separation, not statistical confidence intervals.

## Policy cells and preserved model context

Each of the 36 cells contains three corpus seeds × three model/weight seeds. Model seeds within one corpus and reused Stage 6 panel selections are paired observations, not additional independent datasets. These tables are descriptive and do not re-evaluate Stage 6 usefulness or any p* peak.

| Cohort | Variant | Width | Distinct /9 | Compared | Guard | Unresolved | Not run | Original objective match / available |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S4_fixed30 | M | 64 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S4_fixed30 | M | 128 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S4_fixed30 | M | 256 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S4_fixed30 | U | 64 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S4_fixed30 | U | 128 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S4_fixed30 | U | 256 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S5_R | M | 64 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S5_R | M | 128 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S5_R | M | 256 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S5_R | U | 64 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S5_R | U | 128 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S5_R | U | 256 | 3 | 0 | 9 | 0 | 0 | 0/0 |
| S6_P1_R | M | 64 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P1_R | M | 128 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P1_R | M | 256 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P1_R | U | 64 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P1_R | U | 128 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P1_R | U | 256 | 3 | 0 | 9 | 0 | 0 | 0/0 |
| S6_P2_R | M | 64 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P2_R | M | 128 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P2_R | M | 256 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P2_R | U | 64 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P2_R | U | 128 | 3 | 0 | 9 | 0 | 0 | 0/0 |
| S6_P2_R | U | 256 | 3 | 0 | 9 | 0 | 0 | 0/0 |
| S6_P3_R | M | 64 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P3_R | M | 128 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P3_R | M | 256 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P3_R | U | 64 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P3_R | U | 128 | 3 | 0 | 9 | 0 | 0 | 0/0 |
| S6_P3_R | U | 256 | 3 | 0 | 9 | 0 | 0 | 0/0 |
| S6_P4_R | M | 64 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P4_R | M | 128 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P4_R | M | 256 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P4_R | U | 64 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P4_R | U | 128 | 9 | 9 | 0 | 0 | 0 | 9/9 |
| S6_P4_R | U | 256 | 9 | 8 | 1 | 0 | 0 | 8/8 |

![Complete cohort coverage](cohort-coverage.png)

Historical contexts are copied exactly from the audited Stage 9 report and joined by full policy-reference identity. They supply saved training memorization, validation/test losses, clipping, signed gain/cancellation and original fit context; no Stage 9 grid statistic is reused as a Stage 10 conclusion. All 324 selected test losses remain available. Stage 4 intentionally did not measure own-initial epoch 0 test metrics, so those 54 test gains remain null; 270/324 test gains are available. No imputation or premixed-baseline proxy is used.

| Cohort | Variant | Width | Train NLL gain | Validation NLL gain | Selected test NLL | Test NLL gain | Test gain available /9 | Train instance accuracy | Clipping (available) | Original p (available) | Original fit J (available) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S4_fixed30 | M | 64 | 1.08381 | 0.994147 | 2.10465 | undefined | 0/9 | 0.0625000 | 0.999306 (9/9) | 0.0412125 (9/9) | 0.0000535194 (9/9) |
| S4_fixed30 | M | 128 | 2.19427 | 1.79316 | 2.21098 | undefined | 0/9 | 0.173774 | 0.999074 (9/9) | 0.0933802 (9/9) | 0.000176653 (9/9) |
| S4_fixed30 | M | 256 | 3.94012 | 2.62024 | 2.71336 | undefined | 0/9 | 0.444716 | 0.999074 (9/9) | 0.131924 (9/9) | 0.0000482127 (9/9) |
| S4_fixed30 | U | 64 | 0.112695 | -0.00405264 | 2.01089 | undefined | 0/9 | 0.100966 | 0.958333 (9/9) | 0.940211 (9/9) | 0.00193784 (9/9) |
| S4_fixed30 | U | 128 | 0.102486 | -0.459968 | 2.33886 | undefined | 0/9 | 0.242839 | 0.927546 (9/9) | 6.19382 (9/9) | 2.60014 (9/9) |
| S4_fixed30 | U | 256 | 0.410354 | -0.902548 | 2.76991 | undefined | 0/9 | 0.439996 | 0.973843 (9/9) | 1.63211 (9/9) | 0.223840 (9/9) |
| S5_R | M | 64 | 1.08535 | 1.00431 | 2.10954 | 0.999752 | 9/9 | 0.0651584 | 0.999769 (9/9) | 0.0436659 (9/9) | 0.0000677958 (9/9) |
| S5_R | M | 128 | 2.13410 | 1.97857 | 2.05329 | 1.96543 | 9/9 | 0.0973850 | 0.999653 (9/9) | 0.0424616 (9/9) | 0.0000609106 (9/9) |
| S5_R | M | 256 | 3.44765 | 3.29948 | 2.01185 | 3.28136 | 9/9 | 0.0929362 | 1 (9/9) | 0.0260168 (9/9) | 0.0000250650 (9/9) |
| S5_R | U | 64 | 0.0574386 | 0.0307414 | 1.96470 | 0.0309361 | 9/9 | 0.0710178 | 0.779861 (9/9) | 0.365058 (9/9) | 0.00116632 (9/9) |
| S5_R | U | 128 | 0.0100565 | 0.00153155 | 1.87373 | 0.00187900 | 9/9 | 0.0732422 | 0.562500 (9/9) | 1.13488 (9/9) | 0.0363124 (9/9) |
| S5_R | U | 256 | 0 | 0 | 1.85376 | 0 | 9/9 | 0.0626628 | undefined (0/9) | undefined (0/9) | undefined (0/9) |
| S6_P1_R | M | 64 | 1.07116 | 1.00562 | 2.08317 | 0.995642 | 9/9 | 0.0619032 | 0.999537 (9/9) | 0.0419939 (9/9) | 0.0000535693 (9/9) |
| S6_P1_R | M | 128 | 2.10861 | 1.96083 | 2.05543 | 1.94183 | 9/9 | 0.0974392 | 1 (9/9) | 0.0434796 (9/9) | 0.0000539939 (9/9) |
| S6_P1_R | M | 256 | 3.42516 | 3.28514 | 2.02366 | 3.26669 | 9/9 | 0.0970052 | 0.999306 (9/9) | 0.0258516 (9/9) | 0.0000206273 (9/9) |
| S6_P1_R | U | 64 | 0.0594726 | 0.0316441 | 1.96815 | 0.0334038 | 9/9 | 0.0638021 | 0.837500 (9/9) | 0.354999 (9/9) | 0.000956896 (9/9) |
| S6_P1_R | U | 128 | 0.0105606 | -0.000710924 | 1.87376 | 0.000904467 | 9/9 | 0.0677083 | 0.553241 (9/9) | 1.59024 (9/9) | 0.0798078 (9/9) |
| S6_P1_R | U | 256 | 0 | 0 | 1.85303 | 0 | 9/9 | 0.0595703 | undefined (0/9) | undefined (0/9) | undefined (0/9) |
| S6_P2_R | M | 64 | 1.07116 | 1.00562 | 2.08317 | 0.995642 | 9/9 | 0.0619032 | 0.999537 (9/9) | 0.0419939 (9/9) | 0.0000535693 (9/9) |
| S6_P2_R | M | 128 | 2.10861 | 1.96083 | 2.05543 | 1.94183 | 9/9 | 0.0974392 | 1 (9/9) | 0.0434796 (9/9) | 0.0000539939 (9/9) |
| S6_P2_R | M | 256 | 3.42516 | 3.28514 | 2.02366 | 3.26669 | 9/9 | 0.0970052 | 0.999306 (9/9) | 0.0258516 (9/9) | 0.0000206273 (9/9) |
| S6_P2_R | U | 64 | 0.0594726 | 0.0316441 | 1.96815 | 0.0334038 | 9/9 | 0.0638021 | 0.837500 (9/9) | 0.354999 (9/9) | 0.000956896 (9/9) |
| S6_P2_R | U | 128 | 0 | 0 | 1.87467 | 0 | 9/9 | 0.0595703 | undefined (0/9) | undefined (0/9) | undefined (0/9) |
| S6_P2_R | U | 256 | 0 | 0 | 1.85303 | 0 | 9/9 | 0.0595703 | undefined (0/9) | undefined (0/9) | undefined (0/9) |
| S6_P3_R | M | 64 | 1.07116 | 1.00562 | 2.08317 | 0.995642 | 9/9 | 0.0619032 | 0.999537 (9/9) | 0.0419939 (9/9) | 0.0000535693 (9/9) |
| S6_P3_R | M | 128 | 2.10861 | 1.96083 | 2.05543 | 1.94183 | 9/9 | 0.0974392 | 1 (9/9) | 0.0434796 (9/9) | 0.0000539939 (9/9) |
| S6_P3_R | M | 256 | 3.42965 | 3.28403 | 2.02472 | 3.26563 | 9/9 | 0.0984701 | 0.999306 (9/9) | 0.0267181 (9/9) | 0.0000217435 (9/9) |
| S6_P3_R | U | 64 | 0.0594726 | 0.0316441 | 1.96815 | 0.0334038 | 9/9 | 0.0638021 | 0.837500 (9/9) | 0.354999 (9/9) | 0.000956896 (9/9) |
| S6_P3_R | U | 128 | 0 | 0 | 1.87467 | 0 | 9/9 | 0.0595703 | undefined (0/9) | undefined (0/9) | undefined (0/9) |
| S6_P3_R | U | 256 | 0 | 0 | 1.85303 | 0 | 9/9 | 0.0595703 | undefined (0/9) | undefined (0/9) | undefined (0/9) |
| S6_P4_R | M | 64 | 1.07116 | 1.00562 | 2.08317 | 0.995642 | 9/9 | 0.0619032 | 0.999537 (9/9) | 0.0419939 (9/9) | 0.0000535693 (9/9) |
| S6_P4_R | M | 128 | 2.10861 | 1.96083 | 2.05543 | 1.94183 | 9/9 | 0.0974392 | 1 (9/9) | 0.0434796 (9/9) | 0.0000539939 (9/9) |
| S6_P4_R | M | 256 | 3.42965 | 3.28403 | 2.02472 | 3.26563 | 9/9 | 0.0984701 | 0.999306 (9/9) | 0.0267181 (9/9) | 0.0000217435 (9/9) |
| S6_P4_R | U | 64 | 0.0382748 | 0.0284356 | 1.97209 | 0.0294563 | 9/9 | 0.0610352 | 0.718056 (9/9) | 0.187629 (9/9) | 0.000717461 (9/9) |
| S6_P4_R | U | 128 | 0.00986330 | -0.000216365 | 1.87373 | 0.000934680 | 9/9 | 0.0645616 | 0.524306 (9/9) | 1.76713 (9/9) | 0.522528 (9/9) |
| S6_P4_R | U | 256 | 0.00345826 | -0.00148597 | 1.85446 | -0.00142372 | 9/9 | 0.0697700 | 0.720833 (9/9) | 2.23287 (8/9) | 0.205926 (8/9) |

## Interpretation and provenance

This is a bounded numerical search diagnostic on saved signed gains, not fresh known-truth recovery or model generalization. No model training, inference, retuning, p* replacement, K recomputation or utility-gate revision occurs. Stage 6 primary utility failures remain unchanged. Three capacities cannot establish a shift between two interior peaks; one Pythia size/seed cannot establish a scaling curve. No novelty or publication claim is made. The next research focus is a bounded Stage 4–10 synthesis, with numerical validity, recovery and held-out usefulness kept distinct. No further experiment is launched automatically.

Results SHA256: `5651f006223535011df71ec51eca8b00d26c508516396fd67a34aaa9a3549c0a`. All frozen sources, copied input provenance, raw searches/comparisons, guards, incomplete records, complete histories, fixture checks and report artifacts are archived. CRC and SHA256 are checked; final visual review is recorded separately.

Execution record:

```json
{
  "status": "COMPLETE",
  "utc": "2026-09-30T12:40:49.592679+00:00",
  "run_id": "search-v011-20260930-01",
  "elapsed_seconds": 924.4766743280001,
  "utc_elapsed_seconds": 924.476693,
  "shared_budget_seconds": 3600,
  "completed_cases": 186,
  "planned_cases": 186,
  "completed_source_ids": [
    "input-36088f45eb255c870658420e",
    "input-38a9a1b71135ff7d4d790194",
    "input-489de68e01db2cfc90536a96",
    "input-50b9ce54641702298e5e7e16",
    "input-5dfb7e402c5578a10f200a74",
    "input-5f3f6be50abf6a345b34655e",
    "input-74f86a35637b41e8e1237a4f",
    "input-83c4312855292fcc54e72eb0",
    "input-8a3f390192fb0fc58f542bd0",
    "input-8bb59bf9d3dcdf76350223bf",
    "input-a6cddc1782592f39003adf55",
    "input-b1cd52686382ea92e27ff683",
    "input-c3262f621f6b496220824607",
    "input-efd7000eb46a7106a5a78a2b",
    "input-f14a90f65ee64f20afeb0b60",
    "input-f28d9dc30c7ccb84d180cca0",
    "input-04601a8e30dd301182f1160e",
    "input-19258395a6f05405d0489e25",
    "input-19d4e63f587418121b896649",
    "input-2c6d5da6dd99b7e9b0432056",
    "input-46cd0e53ce569bdb838ed5b6",
    "input-545efc608846c184e2b00466",
    "input-6941a43a9bd65cfc137484dc",
    "input-7263b312fab80ba19d1f7d3b",
    "input-90fd70f93884789c32908ebd",
    "input-9980fc532bb68398ddc92112",
    "input-ac7be52ee262acea2f942fe3",
    "input-baaabafc9600025a29df8799",
    "input-bbda96af40bcfda796878007",
    "input-d4d977c0ba617c95d5b3d10f",
    "input-d7f39f7672b1e61e2a95e5f0",
    "input-e883611382b5a2fcc6ad5118",
    "input-f67cd14192f271d7104b3abf",
    "input-fae6d842460405022dd22943",
    "input-470850d473a6e5d5ddbf4292",
    "input-47ebde091410854b29ff095e",
    "input-4f11be71b05cd51025c139de",
    "input-52205a55deed90c8dbbacf1d",
    "input-5e16bcc9e4d784542f316d84",
    "input-658d17c467c135aa6dfc7ea9",
    "input-6771c158d30aa71143acebe6",
    "input-6917aa26e842c22d7f392158",
    "input-74ff7e542b4601e2c3870a38",
    "input-8746c79cd7a338e5b870bf46",
    "input-8b25f429c24657a8858d581a",
    "input-916fb941b5bae09f027534c9",
    "input-9d33ea9ae58ada5b77f34b4c",
    "input-a1e9c5128123faca62ae6d70",
    "input-cb438a1f4acd5aa50690f993",
    "input-ea9146d467a6a652f849e8a0",
    "input-14ed141a7d79f7d7c2f60ee4",
    "input-2a9ea405b2234556d2ee1ba5",
    "input-3ff9b4849b492a9c7f732d52",
    "input-4553383b3ce8b6179962af49",
    "input-6047bf1c2b43107d97372264",
    "input-6d740fd862b2be26823f3db8",
    "input-73ff311504a67e95b12ff0eb",
    "input-7d2d1716441e4fb8621ab2ec",
    "input-7e5589d20666cfa0dae9f74e",
    "input-940fc89942b01d79f3c378f0",
    "input-a31d6cb75e819c202497f968",
    "input-a38b431f4cc1d1c45d3b84ce",
    "input-aab596e139a2d50242267a5e",
    "input-ae4bc30bd840cb658784e1d9",
    "input-aeff085dc336cd2cefbf32f7",
    "input-b2161869004bd21649f89fb0",
    "input-bcf4391299a0478d8f9890fa",
    "input-d677cc8ceadfa35201b05116",
    "input-047f7151252de169108d656d",
    "input-04ab18ebccbc81ab471f3c7c",
    "input-126ebf6814b5cff6d09cff8d",
    "input-19f7cf0a9794b04a36bbd879",
    "input-1fc50087416c9e55762882c8",
    "input-24fbb858c4ee67a48748d8b1",
    "input-287506ed827f2fa63b4044fb",
    "input-30dec1bbb0b1196e1d0ff8cd",
    "input-31e5223902db6451c55f7086",
    "input-32de9c5bd18b4708c078b41e",
    "input-3b329902ba99c80586d13890",
    "input-45cf7916f9b9854a5cd4a070",
    "input-56cc8512eaab1a1d3f7b6fa1",
    "input-695a6cdb28508fbd240d81dc",
    "input-78d8d3ad223c0906a60c4c73",
    "input-851c3e71bde860e7caa76e1a",
    "input-a4bcd6a145f64dfadbaaa307",
    "input-aae792ec040159e1473d0355",
    "input-b1a51de7a8212ab7023b0036",
    "input-b1bc774c9eb9761b97429a1b",
    "input-b945fabddcb8849117628a3a",
    "input-c2f5a8302706b7297f198bb1",
    "input-c950fdb4f71dd382819f7316",
    "input-d64c7ffb6b4079a41309e808",
    "input-d92a3ab118b3b7ee5d6870c8",
    "input-de3b4cc5b8136f0c94d15bea",
    "input-ebffbb9e573f4c7ea53fd8cb",
    "input-ef736de052d3e65838074492",
    "input-305829727f2ea2393f1fd8d5",
    "input-3b2e26ab0466dc675e2d702b",
    "input-4aa34ea140af55734c8a7e15",
    "input-4f04bc1136c4e69792cfded1",
    "input-5844e82b3913a014f4ea3e15",
    "input-5a2ff1a186437283cb9c047d",
    "input-5a3c8e228ad218b24328df7d",
    "input-62356291e02695040e17a8a5",
    "input-659944728ea07a8e8c28fd25",
    "input-6d8d8ded0e7ae75491cce924",
    "input-76769c4fea9124807a6032fd",
    "input-90d0cb9cdf93f912c58151c2",
    "input-a0b83c6fa5e77ccde3314a1e",
    "input-c2125a99a1e641c352fab4f8",
    "input-d415f986dc45483bdfbb5b62",
    "input-df9ad7f5e54835fb35f6f8f8",
    "input-e3a3a9132fcc5f089e48ec2f",
    "input-fa278f0336d85f32d88a5d8c",
    "input-0f46c27fd363aa3c56324ae3",
    "input-137b6d823d2f3f578b1b24ba",
    "input-4409bb2b98387c473985e993",
    "input-4d5057220cb2b90225c50ef6",
    "input-4f2b8084cc30c5fca5600b97",
    "input-5f929bb3ff3f199a5cb50cdb",
    "input-63ac0f299ab798bf98560135",
    "input-7058fe8eebcfb2ceb159d91a",
    "input-79cedcb3ce0febba96cbb2a6",
    "input-853a8b7ed0cbb8e208318e7b",
    "input-88e75405b57e689115e92165",
    "input-968711c6b5875f6bdaae7ca6",
    "input-9fe965cc36d8e225cdccf409",
    "input-a201e7ec47b1ca7abea60e8c",
    "input-a8392be6a2e7715adeb673fe",
    "input-aac90796c1d11f0b48f5675b",
    "input-b146e8c6b6dbb77a0627dce5",
    "input-b38cea0c426d7b4f47fe3c6d",
    "input-ba9e749b56684ab06c0277e3",
    "input-ca70f9bfd445765494a765c9",
    "input-ce2304f3e3a6cccb698eb7df",
    "input-dd97d378eab48482bc88f9f0",
    "input-de4a49e4ad2dd0028cee027c",
    "input-e34e45870b21046262f0f66e",
    "input-e89787ef512e808bd3d60471",
    "input-edab14b5f52e5ed3ddd28c21",
    "input-f15bc352a6544d069e8ccbab",
    "input-f5b70b2cbca54df30965dc67",
    "input-064e5bd5e93092440c176eef",
    "input-114faa3631b16485ca0f349d",
    "input-14d57fdc519378798cd204ab",
    "input-45707183ab551c7ff4280926",
    "input-45934448c48ff1366bb457ef",
    "input-54900f348264809a5ac90d84",
    "input-617cbd27d8399549e2d3b2f0",
    "input-61bcfcca3db7432c10b6098d",
    "input-61ea24c381ebb7ed98a5a3b4",
    "input-621ae325178ce4ab72f751eb",
    "input-66d9e4cc2ac19d71c8622b80",
    "input-6aeb0859570c24e37cec1224",
    "input-70dec00eee460127940d9336",
    "input-71153c44c92909ec1fd6578f",
    "input-a1f4a1f776789529bd96fb71",
    "input-a7709af0776bd0811b71822d",
    "input-a813854e67976a1b436b141f",
    "input-aedacb1e49d0d40231131ec3",
    "input-b80e4873c3af326aaf27e221",
    "input-c933aef5fe46289805a94fa8",
    "input-c93d304cc6e9e2de47e3949a",
    "input-d0e36fecb4057e44d6d9579e",
    "input-d9f389c774a3c51aee21e034",
    "input-dc45d0322e13af45b4d5d559",
    "input-dedcf198c7c25ddc9844e975",
    "input-e8aa7aba43ba690ae3034152",
    "input-f11b63e34fd3c4477272e599",
    "input-fe1f82787b5484b9fb7b9d9e",
    "input-2dbd9674b5e971131207bd46",
    "input-42b45a06e6d05a6b3a001968",
    "input-5561ab151841fcbfeeacaacf",
    "input-706c22d40573f76c72dbe9c9",
    "input-7c38639e783db9895b510bc5",
    "input-8046946788e19a44257a4636",
    "input-84ebcea102fe771a8c36a6e2",
    "input-9b2bda9d6c8c0fea3fc8d73a",
    "input-a3dd046fc1594cc65a2a4aba",
    "input-a47c5a73c99b7191238bd3dd",
    "input-be1656ee44f9e9aa9d8fd27b",
    "input-cbce202eb2cb715fc4be48f7",
    "input-df444a85ee9a66a72f233616",
    "input-e5b020ed45d012ed2636c87f",
    "input-e8deaec2c15dbaaa54af82d0",
    "input-f5446073f76439c70d9f6fc9"
  ],
  "remaining_source_ids": [],
  "active_weightgroup": "c89e77c654eaf6bb5186b57235d9f7044dbc61288842163a04ff3029e9759317",
  "active_source_id": "input-f5446073f76439c70d9f6fc9",
  "error": null,
  "results_sha256": "5651f006223535011df71ec51eca8b00d26c508516396fd67a34aaa9a3549c0a",
  "peak_rss_mib": 654.3046875,
  "automatic_retry": false
}
```
