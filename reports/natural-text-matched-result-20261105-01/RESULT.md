# Matched-progress confirmation: result

**Written:** 06 Nov 2026. **Status:** Runs M1 and M2 are COMPLETE and the sealed analysis is COMPLETE. The owner ran it, under approval OWNER-20261105-MATCHED-ANALYSIS-01 (`reports/natural-text-ladder-owner-decisions-20261105-03/OWNER_DECISIONS.md`), and reports one run. The order and wording of this report were fixed before any outcome was opened, and its labels, intervals and readings are the sealed analysis's, as produced. **Measured results are in sections 1 to 3, 5, 6 and 8, and section 4 quotes the sealed readings. Nothing here claims a mechanism or a scaling law.**

**Check:** `RESULT_VERIFICATION.json`, written by `verify_results_report.py` after this report. A copy of this report without a passing check beside it has not been checked (section 10).

| Record | SHA-256 |
|---|---|
| `ANALYSIS.json` | `a4af7bad78fdf9f4fe34317f73e6a1932fd0d29367b5da188b79ae73db95ce65` |
| `POINTS.csv` | `234434a34cf64d98e0d45cfe029bb37935207176fd996cafe85756956c7d860f` |
| `FITS.csv` | `b1cd03dec3a6e13ba2d82a6a95a48e99342ace8aaf4a0cdf1b36392fa8c7aa67` |
| `MATCHED.csv` | `86ea11d7210682375717d7eb67a58c74d806ad22dc57ec87ab9db4e836421e3b` |
| `Run M1 TERMINAL.json` | `1392187d518d55ce9463fd7c687d258a791e7e1780d68e4be46b11de1337e65d` |
| `Run M2 TERMINAL.json` | `6ac3614815ce884dffbfb1b093188fb72699a636a24fbd9c7070b6b4fe8c3737` |
| `RUN_M1_VERIFICATION.json` | `77c4277ed5375ca61c28babdc8340eb0ff1cb4483655b164b8682c15b5ba00e8` |
| `RUN_M2_VERIFICATION.json` | `2cab0b791f7cd50d5d600823484e1fcfe773579a2cc9c1df5fbc209038106278` |
| `ANALYSIS_EXIT_RECEIPT.json` | `33c929078caa9e268f85fa2726d199695111b9eb280656c286befd4181b6536d` |
| `RUN_INPUTS_CHECK.json` | `247f6a183386da208f77a8eb32aa13e4fa48c3a8992297f3c2988eae0c3bc562` |
| `SOURCE_SUBJECT.json` | `7ef133ad0120d0852c93ebe65f020718f51cebbf75abd43c29f89cdec8674f56` |
| `matched_analysis.py` | `2108f0b287a0b355d20b3d6faedec6bd93d6ad1074f3f5da629b69e14e6ddf9c` |
| `this layout, make_results_report.py` | `db330602333ad0c2058c60be0c071948d763e698881dd29376f40dd57d7837dd` |
| `the verifier, verify_results_report.py` | `00e013dcfd197401df529c379dd9741be6696143c8bf87b0f472bf23070b97d9` |
| `owner decision` | `6d49712283513601922a01bf7250467efcd48787cc446736f154d49d0c5159ea` |

## 1. NOT_OVERFIT per arm, the manipulation check

Per arm, per draw, Δ = validation NLL at E3 minus at E2. The verdict is per arm, from the interval of the mean Δ over the draws: below 0 gives NOT_OVERFIT, above 0 OVERFIT, otherwise PLATEAU. It gates no label. If an arm a reading uses fails, the label stands and its reading is prefixed. No remedy is allowed: no re-run, data increase or replacement draw.

| Arm | Steps at this rate | Verdict | Mean Δ | 95% interval | df | Draws Δ < 0 | Mean gap at E3 | Lowest mean validation NLL (readout) |
|---|---|---|---|---|---|---|---|---|
| 512 at 3e-4 | S4, S5 | **NOT_OVERFIT** | −0.0560 | [−0.0714, −0.0405] | 5 | 6/6 | +0.5683 | 4.7044 (E3) |
| 512 at 1e-4 | P1, S1, S3, S2 | **NOT_OVERFIT** | −0.0838 | [−0.0934, −0.0742] | 5 | 6/6 | +0.4482 | 4.7185 (E3) |
| 768 at 3e-4 | S4, S5 | **NOT_OVERFIT** | −0.0665 | [−0.0841, −0.0488] | 5 | 6/6 | +0.5586 | 4.6697 (E3) |
| 768 at 1e-4 | P1, S1, S3, S2 | **NOT_OVERFIT** | −0.0749 | [−0.0826, −0.0672] | 5 | 6/6 | +0.5322 | 4.6485 (E3) |

| Rate | Arms | All NOT_OVERFIT | Arms that fail |
|---|---|---|---|
| rate_low | 512 at 1e-4, 768 at 1e-4 | yes | none |
| rate_high | 512 at 3e-4, 768 at 3e-4 | yes | none |

**Δ per draw,** from `POINTS.csv`, because `ANALYSIS.json` keeps the interval and not the values:

| Arm | m01 | m02 | m03 | m04 | m05 | m06 |
|---|---|---|---|---|---|---|
| 512 at 3e-4 | −0.0526 | −0.0834 | −0.0543 | −0.0393 | −0.0565 | −0.0499 |
| 512 at 1e-4 | −0.0838 | −0.0994 | −0.0788 | −0.0723 | −0.0811 | −0.0874 |
| 768 at 3e-4 | −0.0610 | −0.0990 | −0.0668 | −0.0508 | −0.0618 | −0.0592 |
| 768 at 1e-4 | −0.0719 | −0.0891 | −0.0676 | −0.0731 | −0.0744 | −0.0734 |

## 2. The primary, P1

**Label: REVERSAL_CONFIRMED.** At 1e-4, per draw: p\*(512, E3) − p\*(768, read at the training NLL 512 reaches at E3). REVERSAL_CONFIRMED if the 95% interval lies entirely above 0, NOT_REVERSED if entirely below, INCONCLUSIVE otherwise, and UNAVAILABLE with fewer than 5 draws (`PROTOCOL.md` section 5). Saturation can make it SATURATED or SATURATION_SENSITIVE, and neither is read (section 8 there). **The label needs only P1.** Whether the ordering reverses on these draws also needs S3, confirmed in the sequence, which is why the sealed reading in section 4 has several forms.

| Step | Draws with a reading | Status | Mean | 95% interval | df | p, unadjusted | Draws < 0 / > 0 | Exact sign test, p | Draws flagged at p\* ≥ 7.999 |
|---|---|---|---|---|---|---|---|---|---|
| **P1** | 6 of 6 | ABOVE | +0.00909 | [+0.00400, +0.01417] | 5 | 0.0059 | 0/6 | 0.03125 | none |

**Per draw,** with the bracket on 768's readouts. The reading comes from the first interval in readout order whose two values hold the target:

| Draw | Status | Target: 512 at E3 | 768's path, E2 to E3.5: lowest, highest | Bracket | Weight | Read at | Intervals holding the target | p\* of 512 at E3 | p\* of 768 as read | Contrast |
|---|---|---|---|---|---|---|---|---|---|---|
| m01 | READ | 4.2782 | [4.0145, 4.3399] | E2 to E2.25 | 0.9959 | E2.249 | 1 | 0.10179 | 0.09008 | +0.01171 |
| m02 | READ | 4.2873 | [4.0543, 4.3859] | E2.25 to E2.5 | 0.5615 | E2.390 | 1 | 0.10255 | 0.09232 | +0.01023 |
| m03 | READ | 4.2895 | [4.0398, 4.3632] | E2.25 to E2.5 | 0.2071 | E2.302 | 1 | 0.10472 | 0.09655 | +0.00817 |
| m04 | READ | 4.2647 | [3.9873, 4.3158] | E2 to E2.25 | 0.7561 | E2.189 | 1 | 0.10294 | 0.08890 | +0.01404 |
| m05 | READ | 4.2632 | [3.9971, 4.3196] | E2 to E2.25 | 0.9251 | E2.231 | 1 | 0.10370 | 0.09333 | +0.01037 |
| m06 | READ | 4.2393 | [4.0287, 4.3555] | E2.25 to E2.5 | 0.9029 | E2.476 | 1 | 0.10074 | 0.10072 | +0.00002 |

**Power stated in advance,** the chance that P1 reads REVERSAL_CONFIRMED, from N6's spread and the effect it was seen at, +0.0132. That effect selected this hypothesis, so it is likely flattering. It is a plan, not a result:

| Draws available | Spread used, sd | At the effect seen | At half of it | At half of it, with the sd at its upper 95% limit |
|---|---|---|---|---|
| 6 | 0.0025 | >0.999 | 0.999 | 0.703 |
| 5 | 0.0025 | >0.999 | 0.990 | 0.576 |

## 3. The fixed sequence

P1, S1, S3, S4, S5, S2, in this order. A step is read as a confirmation only while every earlier step is confirmed. A step the sequence does not reach has the label NOT_READ, whatever its interval, and the side of its interval stays in the table (`PROTOCOL.md` section 6).

| Step | Per draw | Confirmed if the interval lies | Label | Status of its interval | Read as a confirmation | Confirmed | Arms at this rate all NOT_OVERFIT |
|---|---|---|---|---|---|---|---|
| **P1** | p\*(512, E3) − p\*(768, read at the training NLL 512 reaches at E3), at 1e-4 | above 0 | **REVERSAL_CONFIRMED** | ABOVE | yes | yes | yes |
| **S1** | p\*(512, E3) − p\*(768, read at the gap 512 reaches at E3), at 1e-4 | above 0 | **CONFIRMED** | ABOVE | yes | yes | yes |
| **S3** | p\*(512, E3) − p\*(768, E3), at 1e-4: the fixed-update contrast | below 0 | **CONFIRMED** | BELOW | yes | yes | yes |
| **S4** | p\*(512, E3) − p\*(768, read at the training NLL 512 reaches at E3), at 3e-4 | above 0 | **CONFIRMED** | ABOVE | yes | yes | yes |
| **S5** | p\*(512, E3) − p\*(768, E3), at 3e-4: the fixed-update contrast | above 0 | **CONFIRMED** | ABOVE | yes | yes | yes |
| **S2** | p\*(512, E3) − p\*(768, read at the validation NLL 512 reaches at E3), at 1e-4 | above 0 | **UNAVAILABLE** | UNAVAILABLE | yes | no | not read |

| Confirmed through |
|---|
| S5 |

| Step | Draws with a reading | Status | Mean | 95% interval | df | p, unadjusted | Draws < 0 / > 0 | Exact sign test, p | Draws flagged at p\* ≥ 7.999 |
|---|---|---|---|---|---|---|---|---|---|
| **P1** | 6 of 6 | ABOVE | +0.00909 | [+0.00400, +0.01417] | 5 | 0.0059 | 0/6 | 0.03125 | none |
| **S1** | 6 of 6 | ABOVE | +0.00808 | [+0.00487, +0.01130] | 5 | 0.0013 | 0/6 | 0.03125 | none |
| **S3** | 6 of 6 | BELOW | −0.00454 | [−0.00795, −0.00114] | 5 | 0.0187 | 6/0 | 0.03125 | none |
| **S4** | 6 of 6 | ABOVE | +0.01394 | [+0.00893, +0.01896] | 5 | 8.33e−04 | 0/6 | 0.03125 | none |
| **S5** | 6 of 6 | ABOVE | +0.01382 | [+0.01116, +0.01648] | 5 | 4.20e−05 | 0/6 | 0.03125 | none |
| **S2** | 3 of 6 | UNAVAILABLE | none | none | none | none | 1/2 | 1.00000 | none |

**The contrast per draw.** A draw without a value shows why:

| Draw | P1 | S1 | S3 | S4 | S5 | S2 |
|---|---|---|---|---|---|---|
| m01 | +0.01171 | +0.01034 | −0.00290 | +0.01829 | +0.01685 | TARGET_OUTSIDE_PATH |
| m02 | +0.01023 | +0.01268 | −0.00014 | +0.01707 | +0.01687 | +0.00611 |
| m03 | +0.00817 | +0.00752 | −0.00639 | +0.01555 | +0.01344 | +0.01414 |
| m04 | +0.01404 | +0.00608 | −0.00283 | +0.01292 | +0.01062 | TARGET_OUTSIDE_PATH |
| m05 | +0.01037 | +0.00783 | −0.00566 | +0.01487 | +0.01279 | TARGET_OUTSIDE_PATH |
| m06 | +0.00002 | +0.00405 | −0.00933 | +0.00494 | +0.01236 | −0.00571 |

**p\* at E3 per draw, and the panel mean,** which S3 and S5 use directly:

| Draw | 512 at 3e-4 | 512 at 1e-4 | 768 at 3e-4 | 768 at 1e-4 |
|---|---|---|---|---|
| m01 | 0.11953 | 0.10179 | 0.10267 | 0.10469 |
| m02 | 0.11887 | 0.10255 | 0.10200 | 0.10269 |
| m03 | 0.12149 | 0.10472 | 0.10804 | 0.11111 |
| m04 | 0.11956 | 0.10294 | 0.10894 | 0.10577 |
| m05 | 0.11902 | 0.10370 | 0.10624 | 0.10936 |
| m06 | 0.11625 | 0.10074 | 0.10389 | 0.11007 |
| **Mean** | 0.11912 | 0.10274 | 0.10530 | 0.10728 |

**S1 per draw:** p\*(512, E3) − p\*(768, read at the gap 512 reaches at E3), at 1e-4.

| Draw | Status | Target: 512 at E3 | 768's path, E2 to E3.5: lowest, highest | Bracket | Weight | Read at | Intervals holding the target | p\* of 512 at E3 | p\* of 768 as read | Contrast |
|---|---|---|---|---|---|---|---|---|---|---|
| m01 | READ | 0.4462 | [0.3711, 0.6395] | E2.25 to E2.5 | 0.2130 | E2.303 | 1 | 0.10179 | 0.09144 | +0.01034 |
| m02 | READ | 0.4283 | [0.3630, 0.6247] | E2.25 to E2.5 | 0.1753 | E2.294 | 1 | 0.10255 | 0.08987 | +0.01268 |
| m03 | READ | 0.4519 | [0.3847, 0.6591] | E2.25 to E2.5 | 0.3246 | E2.331 | 1 | 0.10472 | 0.09720 | +0.00752 |
| m04 | READ | 0.4732 | [0.3899, 0.6542] | E2.25 to E2.5 | 0.9010 | E2.475 | 1 | 0.10294 | 0.09686 | +0.00608 |
| m05 | READ | 0.4469 | [0.3832, 0.6552] | E2.25 to E2.5 | 0.1911 | E2.298 | 1 | 0.10370 | 0.09587 | +0.00783 |
| m06 | READ | 0.4426 | [0.3689, 0.6470] | E2.25 to E2.5 | 0.2397 | E2.310 | 1 | 0.10074 | 0.09668 | +0.00405 |

**S4 per draw:** p\*(512, E3) − p\*(768, read at the training NLL 512 reaches at E3), at 3e-4.

| Draw | Status | Target: 512 at E3 | 768's path, E2 to E3.5: lowest, highest | Bracket | Weight | Read at | Intervals holding the target | p\* of 512 at E3 | p\* of 768 as read | Contrast |
|---|---|---|---|---|---|---|---|---|---|---|
| m01 | READ | 4.1454 | [4.0126, 4.3090] | E2.75 to E3 | 0.2042 | E2.801 | 1 | 0.11953 | 0.10123 | +0.01829 |
| m02 | READ | 4.1481 | [4.0388, 4.3601] | E2.75 to E3 | 0.8043 | E2.951 | 1 | 0.11887 | 0.10180 | +0.01707 |
| m03 | READ | 4.1636 | [4.0443, 4.3492] | E2.75 to E3 | 0.3845 | E2.846 | 1 | 0.12149 | 0.10594 | +0.01555 |
| m04 | READ | 4.1309 | [3.9787, 4.2888] | E2.5 to E2.75 | 0.9280 | E2.732 | 1 | 0.11956 | 0.10663 | +0.01292 |
| m05 | READ | 4.1229 | [4.0120, 4.3080] | E2.75 to E3 | 0.3352 | E2.834 | 1 | 0.11902 | 0.10415 | +0.01487 |
| m06 | READ | 4.1057 | [4.0383, 4.3279] | E3 to E3.25 | 0.3314 | E3.083 | 1 | 0.11625 | 0.11131 | +0.00494 |

**S2 per draw:** p\*(512, E3) − p\*(768, read at the validation NLL 512 reaches at E3), at 1e-4.

| Draw | Status | Target: 512 at E3 | 768's path, E2 to E3.5: lowest, highest | Bracket | Weight | Read at | Intervals holding the target | p\* of 512 at E3 | p\* of 768 as read | Contrast |
|---|---|---|---|---|---|---|---|---|---|---|
| m01 | TARGET_OUTSIDE_PATH | 4.7244 | [4.6391, 4.7149] | none | none | none | 0 | 0.10179 | none | none |
| m02 | READ | 4.7156 | [4.6598, 4.7489] | E2.5 to E2.75 | 0.2845 | E2.571 | 1 | 0.10255 | 0.09644 | +0.00611 |
| m03 | READ | 4.7414 | [4.6802, 4.7479] | E2 to E2.25 | 0.6807 | E2.170 | 1 | 0.10472 | 0.09058 | +0.01414 |
| m04 | TARGET_OUTSIDE_PATH | 4.7379 | [4.6326, 4.7057] | none | none | none | 0 | 0.10294 | none | none |
| m05 | TARGET_OUTSIDE_PATH | 4.7100 | [4.6284, 4.7028] | none | none | none | 0 | 0.10370 | none | none |
| m06 | READ | 4.6819 | [4.6510, 4.7244] | E2.75 to E3 | 0.1370 | E2.784 | 3 | 0.10074 | 0.10645 | −0.00571 |

## 4. The sealed readings

Quoted exactly from `ANALYSIS.json`:

1. "The models are small (depth 4, 16.9 M and 34.7 M parameters) and this is one corpus family at one recipe. A reading is about the two widths and two rates on these draws. No reading claims a mechanism or a scaling law, and nothing about Jane Street's scale follows."
2. "P1 has a reading on 6 of 6 draws; without one: none."
3. "Draws without a reading, by statistic (undefined fit, target outside the path, draw missing): P1 0, 0, 0; S1 0, 0, 0; S3 0, 0, 0; S4 0, 0, 0; S5 0, 0, 0; S2 0, 3, 0."
4. "At 1e-4, p* at 512 at E3 is above p* at 768 read at the training NLL 512 reaches at E3 (REVERSAL_CONFIRMED). At fixed updates at E3 on these draws, 768 is above 512, so on these draws the comparison axis reverses the 512-768 ordering at 1e-4. This does not show a capacity mechanism, and nothing about Jane Street's scale follows. Matching on training loss also removes any faster learning of the wider model, so neither axis is privileged."
5. "S1, at 1e-4, matched on the gap: CONFIRMED. At 1e-4, p* at 512 at E3 is above p* at 768 read at the gap 512 reaches at E3."
6. "S3, at 1e-4, the fixed-update contrast at E3: CONFIRMED. S3 replicates N6's fixed-budget result (RATE_DEPENDENT): after 3,072 updates at 1e-4, 768 is above 512. This is a fixed-budget fact. It does not say that the fall from 512 to 768 depends on the rate."
7. "S4, at 3e-4, matched on training NLL: CONFIRMED. At 3e-4, p* at 512 at E3 is above p* at 768 read at the training NLL 512 reaches at E3."
8. "S5, at 3e-4, the fixed-update contrast at E3: CONFIRMED. At 3e-4, after 3,072 updates, 512 is above 768, as in N6. This is a fixed-budget fact."
9. "S2, at 1e-4, matched on validation NLL: UNAVAILABLE. It is not read."
10. "Data: never-assigned WikiText-103 training articles, excluding every article of N5 and N6 and their text duplicates and repeats inside the pool; new seeds; no new tuning. The validation set, the pre-training pool and the tokenizer are those of the earlier natural-text studies. The hypothesis came from a post-hoc reanalysis of N6 (reports/adversarial-review-20261104-01/RECOMPUTE_MATCHED.json), so N6 cannot confirm it. p* between readouts is a linear interpolation over a quarter of an epoch. A draw whose target lies outside 768's E2-E3.5 path is unavailable for that statistic, and such draws are not a random subset. Equal training NLL is not equal gain, because p* is fit to gains from each width's own E0. The t intervals assume normal draws, untested at five or six."

## 5. Always reported, not gating

### 5a. Draws without a reading

| Step | Undefined fit | Target outside the path | Draw missing | Draws |
|---|---|---|---|---|
| P1 | 0 | 0 | 0 | none |
| S1 | 0 | 0 | 0 | none |
| S3 | 0 | 0 | 0 | none |
| S4 | 0 | 0 | 0 | none |
| S5 | 0 | 0 | 0 | none |
| S2 | 0 | 3 | 0 | m01, m04, m05 |

Draws whose target lies outside 768's path are not a random subset of the draws.

### 5b. Leaving out one draw at a time

The interval over the remaining draws, for every statistic with at least 4 draws. The sign tests are in section 3.

| Step | Draw left out | Mean | 95% interval | df | Side |
|---|---|---|---|---|---|
| P1 | m01 | +0.00856 | [+0.00208, +0.01505] | 4 | ABOVE |
| P1 | m02 | +0.00886 | [+0.00218, +0.01554] | 4 | ABOVE |
| P1 | m03 | +0.00927 | [+0.00258, +0.01597] | 4 | ABOVE |
| P1 | m04 | +0.00810 | [+0.00228, +0.01392] | 4 | ABOVE |
| P1 | m05 | +0.00883 | [+0.00216, +0.01550] | 4 | ABOVE |
| P1 | m06 | +0.01090 | [+0.00822, +0.01359] | 4 | ABOVE |
| S1 | m01 | +0.00763 | [+0.00367, +0.01159] | 4 | ABOVE |
| S1 | m02 | +0.00717 | [+0.00429, +0.01005] | 4 | ABOVE |
| S1 | m03 | +0.00820 | [+0.00397, +0.01243] | 4 | ABOVE |
| S1 | m04 | +0.00848 | [+0.00446, +0.01251] | 4 | ABOVE |
| S1 | m05 | +0.00813 | [+0.00389, +0.01238] | 4 | ABOVE |
| S1 | m06 | +0.00889 | [+0.00565, +0.01214] | 4 | ABOVE |
| S3 | m01 | −0.00487 | [−0.00923, −0.00051] | 4 | BELOW |
| S3 | m02 | −0.00542 | [−0.00879, −0.00206] | 4 | BELOW |
| S3 | m03 | −0.00417 | [−0.00850, +0.00015] | 4 | SPANS |
| S3 | m04 | −0.00488 | [−0.00924, −0.00053] | 4 | BELOW |
| S3 | m05 | −0.00432 | [−0.00876, +0.00012] | 4 | SPANS |
| S3 | m06 | −0.00358 | [−0.00669, −0.00047] | 4 | BELOW |
| S4 | m01 | +0.01307 | [+0.00714, +0.01901] | 4 | ABOVE |
| S4 | m02 | +0.01332 | [+0.00703, +0.01960] | 4 | ABOVE |
| S4 | m03 | +0.01362 | [+0.00708, +0.02016] | 4 | ABOVE |
| S4 | m04 | +0.01415 | [+0.00755, +0.02074] | 4 | ABOVE |
| S4 | m05 | +0.01376 | [+0.00715, +0.02036] | 4 | ABOVE |
| S4 | m06 | +0.01574 | [+0.01318, +0.01830] | 4 | ABOVE |
| S5 | m01 | +0.01322 | [+0.01036, +0.01607] | 4 | ABOVE |
| S5 | m02 | +0.01321 | [+0.01037, +0.01605] | 4 | ABOVE |
| S5 | m03 | +0.01390 | [+0.01039, +0.01741] | 4 | ABOVE |
| S5 | m04 | +0.01446 | [+0.01170, +0.01722] | 4 | ABOVE |
| S5 | m05 | +0.01403 | [+0.01058, +0.01748] | 4 | ABOVE |
| S5 | m06 | +0.01411 | [+0.01074, +0.01749] | 4 | ABOVE |
| S2 | none | none | none | none | none |

### 5c. Saturation

A draw is flagged if a fit its statistic uses is at or above 7.999, and those fits are refitted at bound 32. An unresolved refit makes the statistic SATURATED, and a side that differs at bound 32 makes it SATURATION_SENSITIVE. Neither is read.

| Step | Flagged draws | Refit needed | Computable | Unresolved refits | Side at bound 8 | Side at bound 32 | Mean at bound 32 | Interval at bound 32 |
|---|---|---|---|---|---|---|---|---|
| P1 | none | no | none | none | ABOVE | none | none | none |
| S1 | none | no | none | none | ABOVE | none | none | none |
| S3 | none | no | none | none | BELOW | none | none | none |
| S4 | none | no | none | none | ABOVE | none | none | none |
| S5 | none | no | none | none | ABOVE | none | none | none |
| S2 | none | none | none | none | none | none | none | none |

### 5d. Records against arrays

| Measure | Value |
|---|---|
| Largest difference between a record's loss and the mean of the array block the fits use | 8.55e−07 |
| Limit | 0.001 |
| Within the limit | yes |

## 6. Descriptive

Non-gating, with no multiplicity adjustment (`PROTOCOL.md` section 9).

### 6a. By readout, the fixed-update contrast 512 − 768

| Readout | 1e-4, mean | 1e-4, 95% interval | 3e-4, mean | 3e-4, 95% interval |
|---|---|---|---|---|
| E0.25 | +0.00516 | [+0.00391, +0.00641] | +0.00872 | [+0.00630, +0.01114] |
| E0.5 | +0.00551 | [+0.00437, +0.00665] | +0.00772 | [+0.00563, +0.00980] |
| E1 | +0.00522 | [+0.00388, +0.00657] | +0.00705 | [+0.00570, +0.00840] |
| E2 | +0.00095 | [−0.00118, +0.00309] | +0.00958 | [+0.00729, +0.01187] |
| E2.25 | −0.00227 | [−0.00513, +0.00059] | +0.01038 | [+0.00769, +0.01307] |
| E2.5 | −0.00334 | [−0.00638, −0.00030] | +0.01143 | [+0.00859, +0.01427] |
| E2.75 | −0.00371 | [−0.00661, −0.00081] | +0.01317 | [+0.01006, +0.01628] |
| E3 | −0.00454 | [−0.00795, −0.00114] | +0.01382 | [+0.01116, +0.01648] |
| E3.25 | −0.00895 | [−0.01306, −0.00485] | +0.01542 | [+0.01142, +0.01942] |
| E3.5 | −0.00990 | [−0.01450, −0.00529] | +0.01698 | [+0.01271, +0.02125] |

### 6b. Panel means, per arm and readout

**p\*:**

| Arm | E0.25 | E0.5 | E1 | E2 | E2.25 | E2.5 | E2.75 | E3 | E3.25 | E3.5 |
|---|---|---|---|---|---|---|---|---|---|---|
| 512 at 3e-4 | 0.06528 | 0.06502 | 0.06742 | 0.08959 | 0.10658 | 0.11221 | 0.11624 | 0.11912 | 0.14054 | 0.14748 |
| 512 at 1e-4 | 0.04536 | 0.05298 | 0.06024 | 0.07908 | 0.09045 | 0.09541 | 0.09937 | 0.10274 | 0.11739 | 0.12324 |
| 768 at 3e-4 | 0.05656 | 0.05731 | 0.06036 | 0.08001 | 0.09620 | 0.10078 | 0.10307 | 0.10530 | 0.12512 | 0.13050 |
| 768 at 1e-4 | 0.04020 | 0.04748 | 0.05502 | 0.07812 | 0.09272 | 0.09874 | 0.10308 | 0.10728 | 0.12635 | 0.13313 |

**Gap,** validation NLL minus training NLL. The E0 gap is each width's offset, which both of its arms share:

| Arm | E0 | E0.25 | E0.5 | E1 | E2 | E2.25 | E2.5 | E2.75 | E3 | E3.25 | E3.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 512 at 3e-4 | −0.0262 | +0.1305 | +0.1895 | +0.2674 | +0.4114 | +0.4811 | +0.5184 | +0.5478 | +0.5683 | +0.6617 | +0.6961 |
| 512 at 1e-4 | −0.0262 | +0.0798 | +0.1312 | +0.2026 | +0.3237 | +0.3681 | +0.4006 | +0.4250 | +0.4482 | +0.5055 | +0.5383 |
| 768 at 3e-4 | −0.0246 | +0.1507 | +0.2083 | +0.2767 | +0.4123 | +0.4823 | +0.5164 | +0.5369 | +0.5586 | +0.6474 | +0.6777 |
| 768 at 1e-4 | −0.0246 | +0.1004 | +0.1597 | +0.2360 | +0.3768 | +0.4364 | +0.4748 | +0.5037 | +0.5322 | +0.6092 | +0.6466 |

**Training NLL,** in nats per token:

| Arm | E0 | E0.25 | E0.5 | E1 | E2 | E2.25 | E2.5 | E2.75 | E3 | E3.25 | E3.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 512 at 3e-4 | 5.5437 | 5.1536 | 4.9396 | 4.6743 | 4.3490 | 4.2796 | 4.2301 | 4.1863 | 4.1361 | 4.0891 | 4.0498 |
| 512 at 1e-4 | 5.5437 | 5.1587 | 4.9975 | 4.7760 | 4.4786 | 4.4238 | 4.3710 | 4.3219 | 4.2704 | 4.2347 | 4.1922 |
| 768 at 3e-4 | 5.5807 | 5.1133 | 4.8948 | 4.6365 | 4.3238 | 4.2588 | 4.2108 | 4.1633 | 4.1111 | 4.0639 | 4.0208 |
| 768 at 1e-4 | 5.5807 | 5.0966 | 4.9064 | 4.6602 | 4.3466 | 4.2823 | 4.2262 | 4.1712 | 4.1163 | 4.0708 | 4.0203 |

**Validation NLL,** in nats per token:

| Arm | E0 | E0.25 | E0.5 | E1 | E2 | E2.25 | E2.5 | E2.75 | E3 | E3.25 | E3.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 512 at 3e-4 | 5.5175 | 5.2841 | 5.1292 | 4.9417 | 4.7603 | 4.7608 | 4.7484 | 4.7340 | 4.7044 | 4.7508 | 4.7459 |
| 512 at 1e-4 | 5.5175 | 5.2384 | 5.1287 | 4.9786 | 4.8023 | 4.7918 | 4.7716 | 4.7469 | 4.7185 | 4.7402 | 4.7305 |
| 768 at 3e-4 | 5.5561 | 5.2640 | 5.1031 | 4.9133 | 4.7361 | 4.7412 | 4.7272 | 4.7002 | 4.6697 | 4.7113 | 4.6984 |
| 768 at 1e-4 | 5.5561 | 5.1970 | 5.0661 | 4.8962 | 4.7234 | 4.7187 | 4.7009 | 4.6749 | 4.6485 | 4.6800 | 4.6669 |

### 6c. The rate effects at E3: 1e-4 minus 3e-4

| Width | Quantity | Mean | 95% interval | Draws < 0 / > 0 |
|---|---|---|---|---|
| 512 | p\* | −0.01638 | [−0.01731, −0.01545] | 6/0 |
| 512 | Validation NLL | +0.0142 | [+0.0059, +0.0225] | 0/6 |
| 512 | Training NLL | +0.1343 | [+0.1289, +0.1397] | 0/6 |
| 512 | Gap | −0.1201 | [−0.1246, −0.1156] | 6/0 |
| 768 | p\* | +0.00198 | [−0.00128, +0.00524] | 1/5 |
| 768 | Validation NLL | −0.0212 | [−0.0323, −0.0100] | 6/0 |
| 768 | Training NLL | +0.0052 | [−0.0020, +0.0123] | 1/5 |
| 768 | Gap | −0.0263 | [−0.0348, −0.0178] | 6/0 |

**Per draw:**

| Width | Quantity | m01 | m02 | m03 | m04 | m05 | m06 |
|---|---|---|---|---|---|---|---|
| 512 | p\* | −0.01774 | −0.01632 | −0.01677 | −0.01662 | −0.01532 | −0.01551 |
| 512 | Validation NLL | +0.0076 | +0.0174 | +0.0061 | +0.0131 | +0.0280 | +0.0130 |
| 512 | Training NLL | +0.1328 | +0.1392 | +0.1259 | +0.1338 | +0.1402 | +0.1336 |
| 512 | Gap | −0.1252 | −0.1218 | −0.1198 | −0.1208 | −0.1122 | −0.1206 |
| 768 | p\* | +0.00201 | +0.00069 | +0.00306 | −0.00317 | +0.00312 | +0.00618 |
| 768 | Validation NLL | −0.0168 | −0.0096 | −0.0216 | −0.0389 | −0.0270 | −0.0132 |
| 768 | Training NLL | +0.0131 | +0.0144 | +0.0028 | +0.0001 | −0.0006 | +0.0010 |
| 768 | Gap | −0.0300 | −0.0240 | −0.0244 | −0.0390 | −0.0263 | −0.0142 |

### 6d. Clipping

Means are weighted by updates, because the fourth epoch is short.

| Arm | Mean clip fraction | Mean gradient norm | Largest gradient norm |
|---|---|---|---|
| 512 at 3e-4 | 0.965 | 2.574 | 11.652 |
| 512 at 1e-4 | 0.979 | 3.078 | 11.071 |
| 768 at 3e-4 | 0.939 | 2.136 | 5.804 |
| 768 at 1e-4 | 0.973 | 2.837 | 6.970 |

### 6e. Fit quality (`FITS.csv`)

| Measure | Value |
|---|---|
| Fits | 240 |
| Defined fits | 240 |
| Smallest p\* | 0.038 |
| Largest p\* | 0.149 |
| At the upper bound | 0 |
| At the lower bound | 0 |
| Undefined fits | 0 |
| Reasons a fit is undefined | none |
| Smallest total gain, signed | 6027.2 |
| Fits with any sequence of negative gain | 207 |
| Fits with 5% or more of sequences at negative gain | 0 |
| Largest share of sequences at negative gain | 3.9% |
| Where that is | m05, 512 at 3e-4, E0.25 |
| Lowest objective at p\* over the objective at p = 0 | 0.029 |
| Highest objective at p\* over the objective at p = 0 | 0.076 |

## 7. Disclosures

Their wording was fixed before any outcome was opened. The figures depend on the corpus manifest, the partition, the weights and the status records, and on no loss.

### 7a. The fresh rule, and identical text

| Figure | Value |
|---|---|
| Eligible articles | 27,859 |
| Assigned in N5 and N6, and out | 11,099 |
| Text duplicates of assigned articles, and out | 94 |
| Copies of texts repeated inside the pool, and out | 215 |
| Sets of those repeats | 107 |
| Fresh articles | 16,451 |
| Fresh sequences | 681,075 |
| Articles the six groups use | 2,412 |
| Articles left over | 14,039 |
| Identical text: sets across the fresh groups | 0 |
| Identical text: fresh texts equal to an assigned article's | 0 |
| Identical text: repeated inside a group | 0 |
| Titles shared across the fresh groups | 0 |
| Fresh articles sharing a title with an assigned article, with a different text | 0 |

| Group | Articles | Sequences used |
|---|---|---|
| m01 | 407 | 16,384 |
| m02 | 388 | 16,384 |
| m03 | 376 | 16,384 |
| m04 | 425 | 16,384 |
| m05 | 421 | 16,384 |
| m06 | 395 | 16,384 |

**Not measured: exact token sequences and 64-token runs,** which N6's disclosure measured. They would have read the corpus's split files, and the owner-run draw could open only the manifest. So how far token runs recur across m01–m06, N5, N6, the validation set and the pool is not known here. For scale, N6's groups had 64-token runs recurring in another fresh group at a mean of 0.15%. That is N6's figure, not a measurement of these draws.

**Limit.** The draws are treated as independent in every interval and test above. These figures do not measure how far that is true.

### 7b. Tied weights, on real Torch

The weights are used exactly as drawn, with at most n / 1,024 tied values. Tied values means n minus the number of distinct values. **Counted from each draw's own `INPUTS.json`,** by the owner-run `check_run_inputs.py`, because the assistant opens nothing under `work/runs/`.

| Draw | In the run | Real-engine check, real Torch | Stdlib draw, before and after division by numpy's mean | Limit |
|---|---|---|---|---|
| m01 | 3 | 3 | 3 and 3 | 16 |
| m02 | 4 | 4 | 3 and 4 | 16 |
| m03 | 1 | 1 | 0 and 0 | 16 |
| m04 | 1 | 1 | 1 and 1 | 16 |
| m05 | 1 | 1 | 1 and 1 | 16 |
| m06 | 1 | 1 | 1 and 1 | 16 |

**The order of tied entries.** The estimator's stable sort keeps them in ascending sequence index, so p\* repeats for the same inputs on the same Python and libm. How much the order of ties moves p\* on these real gains is not measured: the frozen analysis has no such step.

### 7c. Each draw's inputs against the real-engine check

The sealed analysis does not compare these, so the owner-run `check_run_inputs.py` does, from each draw's `INPUTS.json`: the recorded hashes of the weights, orders and pool orders against the real-Torch check; the list of weights itself, which is what the fits use, rehashed against the same check; seeds against the registry; articles and sequence indices against the partition; validation and pool against N6's native hashes. The six training hashes have no reference, because the real-engine check ran on synthetic tokens, so only their being distinct is checked.

| Draw | N | Weights, recorded hash | Weights, the list the fits use | Orders | Pool orders | Tied values | Seeds | Articles | Sequence indices | Validation | Pool |
|---|---|---|---|---|---|---|---|---|---|---|---|
| m01 | equal | equal | equal | equal | equal | equal | equal | equal | equal | equal | equal |
| m02 | equal | equal | equal | equal | equal | equal | equal | equal | equal | equal | equal |
| m03 | equal | equal | equal | equal | equal | equal | equal | equal | equal | equal | equal |
| m04 | equal | equal | equal | equal | equal | equal | equal | equal | equal | equal | equal |
| m05 | equal | equal | equal | equal | equal | equal | equal | equal | equal | equal | equal |
| m06 | equal | equal | equal | equal | equal | equal | equal | equal | equal | equal | equal |

| Measure | Value |
|---|---|
| Comparisons | 67 |
| Differences | 0 |
| The six training hashes are distinct | yes |

### 7d. The hypothesis and the rates

- **The hypothesis is post hoc.** It came from a reanalysis of N6 (`reports/adversarial-review-20261104-01/RECOMPUTE_MATCHED.json`), so N6 and its draws cannot confirm it, and they are excluded here.
- **The rates were not chosen again.** 3e-4 is the rate the few-epoch study selected on t00, and 1e-4 is 768's lowest validation NLL on t00 among the five rates tried. p\* entered neither.
- **The target is 512's value at E3,** and the axis matters. Matching on training NLL is not matching on gain: see the limitation "Equal training NLL is not equal gain" in section 9.

### 7e. Shared items, and one analysis

- **Shared by design:** the validation set, the pre-training pool and the tokenizer are those of N6, and every draw shares them.
- **One analysis.** The owner reports running it once, and the command's claim file stops a second run through that command. A run by another route would not be seen. This report reads its outputs and does not re-run it.
- **One breach of the rule on `work/runs/`, by the assistant, before the analysis.** One search from the project root, with a filter on four file names, will have walked folders there. It printed counts per file and named nothing there. Draw folders hold none of those names, so no draw file was opened and no outcome was seen. Details: `reports/natural-text-matched-m1-result-20261105-01/RESULT.md`.

### 7f. The public registration, before any data

The protocol, the sealed source, the seed registry with its draw and exclusions, the partition and the real-engine check's hashes were published and merged before any activation, and the builder refused without them. Each run's approval record names the merge commit. **What it does not show:** the layout of this report was frozen later, by the owner's approval of the analysis, and is not in that pull request. **The losses already existed when this layout was frozen.** That they were unopened rests on local records and the owner's word, and the public record cannot show it.

| Item | Value |
|---|---|
| Pull request | https://github.com/rafli-hl/sequence-weighting-research/pull/5 |
| Merged at | 2026-11-05T04:44:28Z |
| Merge commit | `f3a2571029f4a0b4d0dc2ee974338e13996e11d8` |
| Source subject at that commit | `7ef133ad0120d0852c93ebe65f020718f51cebbf75abd43c29f89cdec8674f56` |
| Package files, local and public | 55 and 55 |
| Package files that differ | 0 |
| Run M1's approval record names that commit | yes |
| Run M2's approval record names that commit | yes |

### 7g. Where the analysis ran

On the owner's machine, by the owner, with native Windows Python and the standard library only: no WSL, Torch or GPU. From the command's exit receipt:

| Item | Value |
|---|---|
| Python | `<LOCAL_USER_HOME>\AppData\Local\Programs\Python\Python312\python.exe` |
| Python version | Python 3.12.10 |
| Operating system | Microsoft Windows NT 10.0.26300.0 |
| Started, UTC | 2026-11-05T17:55:38Z |
| Ended, UTC | 2026-11-05T17:58:43Z |
| Seconds, by the command's clock | 184.7 |
| Exit code | 0 |

## 8. Operations (measured, from the status records)

| Measure | Run M1 | Run M2 |
|---|---|---|
| Ended | COMPLETE | COMPLETE |
| Per-run check | 20 of 20 | 21 of 21 |
| Draws, by the worker's clock | m01 2,770.4 s, m02 2,805.0 s, m03 2,769.4 s | m04 2,824.9 s, m05 2,858.9 s, m06 2,870.1 s |
| Worker elapsed | 8,456 s | 8,671 s |
| Owner elapsed, Windows clock | 9,278 s | 9,604 s |
| Windows over the worker's clock | 1.097 | 1.108 |
| Worker peak memory | 2.46 GB | 2.46 GB |
| GPU peak, sampled | 2,386,349,260 bytes | 2,386,349,260 bytes |
| Kept output | 9,835,404 bytes, 51 files | 9,835,974 bytes, 51 files |
| Gate before each draw | m01 IDLE at check 1, m02 IDLE at check 1, m03 IDLE at check 1 | m04 IDLE at check 1, m05 IDLE at check 1, m06 IDLE at check 1 |
| Power readings off AC | 0 | 0 |
| Battery, first to last | 80% to 80% | 80% to 80% |

**The causes of the slow worker clock, of the rise in its ratio between the runs, and of the changes in draw time are not established.**

## 9. Limitations

Quoted from `PROTOCOL.md` section 11, stated in advance:

- **A mechanism:** no result here says why p\* orders as it does.
- **The axis:** matching on training loss also removes any faster learning of the wider model. Neither axis is privileged, and this study does not choose between them.
- **Jane Street's scale:** depth 4, 16.9 M and 34.7 M parameters, one corpus family. Nothing about Jane Street's scale follows, and this is not their setting: a constant rate with no horizon-tied schedule, and small models adapted from a short uniform pre-training.
- **Interpolation:** p\* between readouts is still linear, now over a quarter of an epoch.
- **Equal training NLL is not equal gain:** p\* is fit to gains from each width's own E0, and 768 starts higher. On N6's panel, E0 is 5.6037 against 5.5509, so at the target 768 has gained 1.337 against 1.285. Matching on gain would read 768 near E2.14, not E2.36, and raise P1 by about 0.006. So this axis leans against a reversal, and "matched progress" here means matched training NLL, not matched gain.
- **Normality:** the t intervals assume normal draws, untested at five or six draws. The sign test is reported beside them.
- **A draw lost to a failure** in either run is not a random draw. The readings say how many draws P1 was read on, and which run failed.
- **Selection by matching:** a draw whose target lies outside the path is unavailable, and such draws are not a random subset.
- **Other rates:** the rates are the two tested in N6. The best rate for 768 is not located.
- **Shared items:** consistency across the pool, the tokenizer and the recipe is not tested. After the same pre-training, 768 starts from a higher E0 validation NLL than 512.
- **Independence:** draws are treated as independent in every interval.
- **No held-out test loss:** the test split is the pre-training pool.
- **Pre-registration:** the public registration fixes the protocol before any data exists, and is the first in this project to do so. The rest of its verification is still by the owner and the assistant.

## 10. How these numbers were checked

`verify_results_report.py` is a separate file with code of its own. Its comparisons use no sealed module, it loads this layout only afterwards, to compare bytes, and it writes `RESULT_VERIFICATION.json` beside this report.

- **Recomputed from `POINTS.csv`, in code of its own:** each target, bracket, weight and read position; each contrast; each mean, interval and p-value, with the t tail integrated directly; the sign tests; the leave-one-out intervals; each side, status and label; the sequence; NOT_OVERFIT; the rate effects; the by-readout tables; the panel means and losses at each readout; and the bound counts. Each is compared with `ANALYSIS.json` and `MATCHED.csv`.
- **The readings:** each is compared, word for word, with the verifier's copy of the sealed wording, under the recomputed labels and prefixes.
- **This report against those outputs:** every table cell is compared with a value the verifier formats itself, and every number outside a table must be one of the plan's constants. This report must also equal, byte for byte, what the frozen layout writes from those outputs.
- **The outputs against the run:** their hashes must equal those the owner's command recorded when the analysis ended, in `ANALYSIS_EXIT_RECEIPT.json`.
- **Not recomputed, and reported as produced:** p\* itself and the other fields of `FITS.csv`; the training and validation NLL in `POINTS.csv`, from each `record.json`, on which every target, bracket and matched contrast rests; the E0 losses; clipping; any refit at bound 32, which can move a label; and the record-against-array difference. They need the run files under `work/runs/`, which only the sealed analysis read. So this check cannot find an error inside the sealed analysis's reading of those files: a wrong value that stays consistent with the rest would pass. The suite compared that reading with an independent recomputation on invented losses only.
