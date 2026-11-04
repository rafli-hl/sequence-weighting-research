# Peak confirmation: result

**Date:** 04 Nov 2026. **Status:** Runs C1 and C2 are COMPLETE and the sealed analysis is COMPLETE. The owner ran it once, under approval OWNER-20261103-PEAK-ANALYSIS-01 (`reports/natural-text-ladder-owner-decisions-20261103-08/OWNER_DECISIONS.md`). The order and wording of this report were fixed before any outcome was opened; its readings are the sealed ones, quoted. **Measured results are in sections 1 to 4, 6 and 8. Nothing here claims a mechanism.**

**Check:** **PASS: 0 mismatches against the sealed outputs in 2,705 comparisons, and 0 differences from the real-engine check's inputs** (section 10).

| Record | SHA-256 |
|---|---|
| `ANALYSIS.json` | `69283574ac1bbd4f1bf482fb0c6af2f7cca6d5b17e52e6ef858b0667cb9a6972` |
| `POINTS.csv` | `1fc485744144c86cf5c6c6b297ecdf5fdfcd8e278f43ddfc3c578784ef86f296` |
| `FITS.csv` | `34eba346bf07bd3458e88e9feb036012b313a139133e14de2d70a9da0961a89b` |
| `Run C1 TERMINAL.json` | `77988d64f5b0e97a75789270202a40f99b9ee0baf4714b847d31777c6149d360` |
| `Run C2 TERMINAL.json` | `d7dee4370e03bdafab3fcddec9d47484804da32eecc3358f85b64a86fd7cd205` |
| `SOURCE_SUBJECT.json` | `0d9e8f9adee4544bd24550f43a09c309e935ec6816a90769e04625e764711e28` |
| `this layout, make_results_report.py` | `af2fecbdc662f4b97662e7cc1d22db6632e9ec90b72db604bd4a3315cf456f3e` |
| `owner decision` | `84935b17265d29e00c74ba75ee7bf747563a695aac9e26493ffc70409f672fba` |

**`ANALYSIS.json` was written at 2026-11-04T03:57:12Z.** The folder's name carries the date of the approval package, not this time.

## 1. NOT_OVERFIT per arm, the manipulation check

Per arm, per draw, Δ = validation NLL at E3 minus at E2. The verdict is per arm, from the df-5 interval of the mean Δ over the six draws: below 0 gives NOT_OVERFIT, above 0 OVERFIT, otherwise PLATEAU. There is no verdict for a single draw. If an arm fails, the label stands and its reading is prefixed. No remedy is allowed.

| Arm | Reading it gates | Verdict | Mean Δ | 95% interval (df 5) | Draws Δ < 0 | Mean gap at E3 | Lowest mean validation NLL (readout) |
|---|---|---|---|---|---|---|---|
| 384 at 3e-4 | primary | **NOT_OVERFIT** | −0.0814 | [−0.0891, −0.0737] | 6/6 | +0.4807 | 4.7275 (E3) |
| 512 at 3e-4 | primary | **NOT_OVERFIT** | −0.0539 | [−0.0617, −0.0460] | 6/6 | +0.5823 | 4.7068 (E3) |
| 512 at 1e-4 | control | **NOT_OVERFIT** | −0.0813 | [−0.0877, −0.0750] | 6/6 | +0.4585 | 4.7248 (E3) |
| 768 at 3e-4 | primary | **NOT_OVERFIT** | −0.0727 | [−0.0862, −0.0593] | 6/6 | +0.5680 | 4.6750 (E3) |
| 768 at 1e-4 | control | **NOT_OVERFIT** | −0.0780 | [−0.0840, −0.0720] | 6/6 | +0.5430 | 4.6584 (E3) |

| Reading | Arms it uses | All NOT_OVERFIT | Arms that fail |
|---|---|---|---|
| primary | 384 at 3e-4, 512 at 3e-4, 768 at 3e-4 | yes | none |
| control | 512 at 1e-4, 768 at 1e-4 | yes | none |

The control's reading also carries the prefix of a failing primary arm, since the control is read only if the primary is.

**Δ per draw,** recomputed from each `record.json`, because `ANALYSIS.json` keeps the interval and not the six values:

| Arm | c01 | c02 | c03 | c04 | c05 | c06 |
|---|---|---|---|---|---|---|
| 384 at 3e-4 | −0.0716 | −0.0801 | −0.0894 | −0.0780 | −0.0785 | −0.0908 |
| 512 at 3e-4 | −0.0425 | −0.0563 | −0.0505 | −0.0555 | −0.0532 | −0.0652 |
| 512 at 1e-4 | −0.0710 | −0.0895 | −0.0820 | −0.0807 | −0.0806 | −0.0843 |
| 768 at 3e-4 | −0.0536 | −0.0786 | −0.0841 | −0.0598 | −0.0770 | −0.0832 |
| 768 at 1e-4 | −0.0719 | −0.0746 | −0.0854 | −0.0745 | −0.0767 | −0.0848 |

## 2. The primary: is p\* at 512 above both 384 and 768, at 3e-4 at E3?

**Label: INTERIOR_PEAK.** INTERIOR_PEAK requires the lower limits of the 95% intervals of D1 and D2 both above 0; anything else is NOT_CONFIRMED, with both intervals reported. Both must pass, so there is no multiplicity adjustment. The p-values are reported and the rule does not use them.

**Read as a few-epoch test:** yes.

| Contrast | Per draw at E3 | Status | Mean | 95% interval (df 5) | p, unadjusted | Draws < 0 / > 0 | Draws flagged at p\* ≥ 7.999 |
|---|---|---|---|---|---|---|---|
| **D1** | p\*(512) − p\*(384), both at 3e-4 | **ABOVE** | +0.0192 | [+0.0179, +0.0204] | 1.98e−07 | 0/6 | none |
| **D2** | p\*(512) − p\*(768), both at 3e-4 | **ABOVE** | +0.0158 | [+0.0131, +0.0185] | 2.47e−05 | 0/6 | none |

**Power stated in advance** (six draws, from effects seen in d01–d10, which selected this hypothesis, so those effects are likely flattering): >0.999 at the seen effects and 0.941 at half of them; with the sd at its upper 95% limit, 0.989 and 0.588.

**The contrasts per draw:**

| Draw | D1 | D2 | D4 | D3 |
|---|---|---|---|---|
| c01 | +0.0180 | +0.0125 | −0.0037 | +0.0121 |
| c02 | +0.0177 | +0.0177 | −0.0055 | +0.0112 |
| c03 | +0.0197 | +0.0185 | −0.0003 | +0.0163 |
| c04 | +0.0190 | +0.0126 | −0.0102 | +0.0055 |
| c05 | +0.0201 | +0.0168 | −0.0085 | +0.0085 |
| c06 | +0.0207 | +0.0167 | −0.0019 | +0.0130 |

**p\* at E3 per draw, and the mean:**

| Draw | 384 at 3e-4 | 512 at 3e-4 | 512 at 1e-4 | 768 at 3e-4 | 768 at 1e-4 |
|---|---|---|---|---|---|
| c01 | 0.0986 | 0.1166 | 0.1008 | 0.1041 | 0.1045 |
| c02 | 0.0944 | 0.1121 | 0.0955 | 0.0944 | 0.1009 |
| c03 | 0.0999 | 0.1196 | 0.1029 | 0.1010 | 0.1033 |
| c04 | 0.0966 | 0.1156 | 0.0999 | 0.1030 | 0.1100 |
| c05 | 0.0987 | 0.1188 | 0.1017 | 0.1020 | 0.1103 |
| c06 | 0.0991 | 0.1198 | 0.1050 | 0.1031 | 0.1069 |
| **Mean** | 0.0979 | 0.1171 | 0.1010 | 0.1013 | 0.1060 |

## 3. The control: 512 against 768, both at 1e-4

**Label: RATE_DEPENDENT.** The primary is INTERIOR_PEAK, so the control is read: a lower limit above 0 gives PEAK_AT_BOTH_RATES, an upper limit below 0 gives RATE_DEPENDENT, and otherwise FALL_NOT_DETECTED_AT_1E-4. "Rate-dependent" is reserved for 768 above 512 at 1e-4.

**Read as a few-epoch test:** yes.

| Contrast | Per draw at E3 | Status | Mean | 95% interval (df 5) | p, unadjusted | Draws < 0 / > 0 | Draws flagged at p\* ≥ 7.999 |
|---|---|---|---|---|---|---|---|
| **D4** | p\*(512) − p\*(768), both at 1e-4 | **BELOW** | −0.0050 | [−0.0090, −0.0010] | 0.0232 | 6/0 | none |

**The premise of the control.** It uses 1e-4 because that was 768's lower validation NLL of the two rates on t00, where V at 768, 1e-4 minus 3e-4, was −0.0357. On these six draws V at 768 is −0.0166, 95% interval [−0.0321, −0.0011] (df 5): **below 0, so the premise repeats.** The sealed premise line is not printed: it is printed only if the interval is not below 0 and the control is read.

**The control's power was an assumption.** On this recipe, no p\* existed at 1e-4 before this study, because Run A wrote no arrays. At six draws, the smallest mean detected is 1.43 sds at 80% power and 1.67 at 90% (`PROTOCOL.md` section 10). The sd of D4 was unknown; measured here, it is 0.0038.

## 4. The pre-registered secondary: D3, with its gap caveat

D3 gates nothing, and no multiplicity adjustment applies to it.

| Contrast | Per draw at E3 | Status | Mean | 95% interval (df 5) | p, unadjusted | Draws < 0 / > 0 | Draws flagged at p\* ≥ 7.999 |
|---|---|---|---|---|---|---|---|
| **D3** | p\*(512 at 3e-4) − p\*(768 at 1e-4) | **ABOVE** | +0.0111 | [+0.0072, +0.0150] | 7.59e−04 | 0/6 | none |

**The caveat, stated in advance and quoted:** "D3, a pre-registered secondary: p* at 512 at 3e-4 minus p* at 768 at 1e-4, at E3. It is not a test of the rate account, because it compares two rates. Stated in advance: on t00 the gap at 512 at 3e-4 (0.5676) is above the gap at 768 at 1e-4 (0.5382), so if p* simply tracked the gap, D3 would be above 0 with no turn at 768."

**The gaps at E3 on these draws,** validation NLL minus training NLL, with t00 as stated in advance. In D3, the caveat concerns 512 at 3e-4 against 768 at 1e-4. In D4, at one rate, t00's gap ran the other way.

| Draw | 512 at 3e-4 | 768 at 1e-4 | 512 at 1e-4 | 768 at 3e-4 |
|---|---|---|---|---|
| c01 | 0.5934 | 0.5376 | 0.4643 | 0.5828 |
| c02 | 0.5842 | 0.5531 | 0.4529 | 0.5767 |
| c03 | 0.5871 | 0.5366 | 0.4542 | 0.5699 |
| c04 | 0.5429 | 0.5194 | 0.4329 | 0.5384 |
| c05 | 0.6040 | 0.5724 | 0.4782 | 0.5787 |
| c06 | 0.5818 | 0.5390 | 0.4685 | 0.5617 |
| **Mean** | 0.5823 | 0.5430 | 0.4585 | 0.5680 |
| t00, stated in advance | 0.5676 | 0.5382 | 0.4422 | 0.5751 |

**The saturation rule did not apply:** no draw was flagged, so no refit at bound 32 was needed.

## 5. The sealed readings

Quoted exactly from `ANALYSIS.json`:

1. "The few-epoch question is read only where the arms a reading uses were still improving their validation loss from E2 to E3 (NOT_OVERFIT). The models are small (depth 4, at most 34.7 M parameters) and this is one corpus family at one recipe. No reading claims a mechanism or a scaling law."
2. "At 3e-4 at E3, p* at 512 is above p* at 384 and at 768 on fresh draws (INTERIOR_PEAK). This is an ordering of three rungs; it does not place the peak between rungs."
3. "Peak at 3e-4 only (RATE_DEPENDENT): at 1e-4, 768 is above 512, so the fall seen at 3e-4 is rate-dependent, at the two rates tested."
4. "D3, a pre-registered secondary: p* at 512 at 3e-4 minus p* at 768 at 1e-4, at E3. It is not a test of the rate account, because it compares two rates. Stated in advance: on t00 the gap at 512 at 3e-4 (0.5676) is above the gap at 768 at 1e-4 (0.5382), so if p* simply tracked the gap, D3 would be above 0 with no turn at 768."
5. "Data: never-assigned WikiText-103 training articles, with text duplicates of assigned articles and repeats inside the pool removed; new seeds; no new tuning. The validation set, the pre-training pool and the tokenizer are those of the earlier natural-text studies. The hypothesis was formed after seeing d01-d10, and the idea for the control also came after seeing p*; the rate 1e-4 comes from validation NLL on t00 only."

## 6. Other secondaries

Non-gating, with no multiplicity adjustment. Only the primary and the control carry labels.

### 6a. The rate effects at E3: 1e-4 minus 3e-4

The rate account predicts R above 0 at 768 (`PROTOCOL.md` section 9).

| Width | Quantity | Mean | 95% interval (df 5) | Draws < 0 / > 0 |
|---|---|---|---|---|
| 512 | p\* (R) | −0.0161 | [−0.0170, −0.0153] | 6/0 |
| 512 | Validation NLL (V) | +0.0181 | [+0.0120, +0.0241] | 0/6 |
| 512 | Training NLL | +0.1418 | [+0.1369, +0.1468] | 0/6 |
| 512 | Gap | −0.1238 | [−0.1339, −0.1136] | 6/0 |
| 768 | p\* (R) | +0.0047 | [+0.0015, +0.0079] | 0/6 |
| 768 | Validation NLL (V) | −0.0166 | [−0.0321, −0.0011] | 5/1 |
| 768 | Training NLL | +0.0084 | [−0.0083, +0.0252] | 2/4 |
| 768 | Gap | −0.0250 | [−0.0389, −0.0112] | 6/0 |

**Per draw:**

| Width | Quantity | c01 | c02 | c03 | c04 | c05 | c06 |
|---|---|---|---|---|---|---|---|
| 512 | p\* (R) | −0.0158 | −0.0166 | −0.0166 | −0.0157 | −0.0170 | −0.0149 |
| 512 | Validation NLL (V) | +0.0152 | +0.0154 | +0.0137 | +0.0282 | +0.0140 | +0.0219 |
| 512 | Training NLL | +0.1443 | +0.1467 | +0.1466 | +0.1383 | +0.1399 | +0.1352 |
| 512 | Gap | −0.1291 | −0.1314 | −0.1329 | −0.1101 | −0.1259 | −0.1134 |
| 768 | p\* (R) | +0.0004 | +0.0065 | +0.0022 | +0.0071 | +0.0083 | +0.0037 |
| 768 | Validation NLL (V) | −0.0356 | +0.0005 | −0.0149 | −0.0315 | −0.0162 | −0.0019 |
| 768 | Training NLL | +0.0096 | +0.0241 | +0.0184 | −0.0125 | −0.0100 | +0.0208 |
| 768 | Gap | −0.0452 | −0.0236 | −0.0334 | −0.0190 | −0.0063 | −0.0227 |

### 6b. By readout

The contrasts, with unadjusted intervals:

| Readout | D1, 95% interval (df 5) | D2, 95% interval (df 5) | D4, 95% interval (df 5) | D3, 95% interval (df 5) |
|---|---|---|---|---|
| E0.25 | +0.0059 [+0.0047, +0.0070] | +0.0075 [+0.0062, +0.0089] | +0.0038 [+0.0027, +0.0049] | +0.0222 [+0.0206, +0.0237] |
| E0.5 | +0.0042 [+0.0037, +0.0048] | +0.0068 [+0.0049, +0.0086] | +0.0044 [+0.0031, +0.0056] | +0.0155 [+0.0141, +0.0170] |
| E1 | +0.0047 [+0.0040, +0.0055] | +0.0072 [+0.0057, +0.0088] | +0.0043 [+0.0028, +0.0058] | +0.0111 [+0.0099, +0.0123] |
| E2 | +0.0116 [+0.0107, +0.0125] | +0.0104 [+0.0083, +0.0125] | −0.0001 [−0.0027, +0.0026] | +0.0106 [+0.0078, +0.0133] |
| E3 | +0.0192 [+0.0179, +0.0204] | +0.0158 [+0.0131, +0.0185] | −0.0050 [−0.0090, −0.0010] | +0.0111 [+0.0072, +0.0150] |

At 3e-4: the per-draw argmax of the three rungs, and the FALL statistic, the OLS slope of p\* on log2 width over 384, 512, 768:

| Readout | Per-draw argmax | FALL statistic | 95% interval (df 5) | Draws < 0 / > 0 |
|---|---|---|---|---|
| E0.25 | 512 ×6 | −0.0024 | [−0.0038, −0.0010] | 6/0 |
| E0.5 | 512 ×6 | −0.0031 | [−0.0050, −0.0013] | 6/0 |
| E1 | 512 ×6 | −0.0031 | [−0.0051, −0.0012] | 6/0 |
| E2 | 512 ×6 | −0.0000 | [−0.0025, +0.0024] | 2/4 |
| E3 | 512 ×6 | +0.0014 | [−0.0013, +0.0041] | 2/4 |

**Panel mean p\*:**

| Arm | E0.25 | E0.5 | E1 | E2 | E3 |
|---|---|---|---|---|---|
| 384 at 3e-4 | 0.0566 | 0.0588 | 0.0609 | 0.0766 | 0.0979 |
| 512 at 3e-4 | 0.0625 | 0.0630 | 0.0656 | 0.0883 | 0.1171 |
| 512 at 1e-4 | 0.0442 | 0.0519 | 0.0588 | 0.0776 | 0.1010 |
| 768 at 3e-4 | 0.0550 | 0.0563 | 0.0584 | 0.0778 | 0.1013 |
| 768 at 1e-4 | 0.0403 | 0.0475 | 0.0546 | 0.0777 | 0.1060 |

**Panel mean gap,** validation NLL minus training NLL. The E0 gap is each width's offset: training text comes from WikiText-103 articles, validation text from WikiText-2's validation split.

| Arm | E0 (offset) | E0.25 | E0.5 | E1 | E2 | E3 |
|---|---|---|---|---|---|---|
| 384 at 3e-4 | −0.0324 | +0.1176 | +0.1663 | +0.2319 | +0.3543 | +0.4807 |
| 512 at 3e-4 | −0.0341 | +0.1367 | +0.1934 | +0.2750 | +0.4219 | +0.5823 |
| 512 at 1e-4 | −0.0341 | +0.0789 | +0.1318 | +0.2049 | +0.3306 | +0.4585 |
| 768 at 3e-4 | −0.0350 | +0.1559 | +0.2108 | +0.2867 | +0.4226 | +0.5680 |
| 768 at 1e-4 | −0.0350 | +0.0982 | +0.1591 | +0.2417 | +0.3851 | +0.5430 |

### 6c. M on these draws, at 3e-4

**M, the mean over 101 gap levels of p\*(768) − p\*(384):** −0.0078, 95% interval [−0.0102, −0.0053] (df 5), draws 6 below 0 and 0 above. The sealed note: "At matched gap the larger width has had fewer epochs, so a nonzero M is also what p* gives if it depends on training progress rather than on the gap."

| Draw | M | Common gap range | Reason it has no value |
|---|---|---|---|
| c01 | −0.0063 | [+0.1618, +0.4879] | none |
| c02 | −0.0098 | [+0.1459, +0.4891] | none |
| c03 | −0.0115 | [+0.1479, +0.4742] | none |
| c04 | −0.0056 | [+0.1475, +0.4511] | none |
| c05 | −0.0069 | [+0.1741, +0.4979] | none |
| c06 | −0.0064 | [+0.1581, +0.4838] | none |

### 6d. Losses and clipping (panel means; NLL in nats per token)

| Width | E0 train | E0 validation |
|---|---|---|
| 384 | 5.5407 | 5.5084 |
| 512 | 5.5509 | 5.5167 |
| 768 | 5.6037 | 5.5687 |

| Arm | E0.25 train | E0.5 train | E1 train | E2 train | E3 train | E0.25 validation | E0.5 validation | E1 validation | E2 validation | E3 validation |
|---|---|---|---|---|---|---|---|---|---|---|
| 384 at 3e-4 | 5.1853 | 5.0211 | 4.7774 | 4.4546 | 4.2468 | 5.3029 | 5.1874 | 5.0093 | 4.8089 | 4.7275 |
| 512 at 3e-4 | 5.1438 | 4.9400 | 4.6640 | 4.3387 | 4.1245 | 5.2804 | 5.1334 | 4.9390 | 4.7606 | 4.7068 |
| 512 at 1e-4 | 5.1617 | 5.0036 | 4.7747 | 4.4756 | 4.2664 | 5.2406 | 5.1354 | 4.9796 | 4.8062 | 4.7248 |
| 768 at 3e-4 | 5.1204 | 4.9124 | 4.6420 | 4.3250 | 4.1069 | 5.2763 | 5.1232 | 4.9288 | 4.7477 | 4.6750 |
| 768 at 1e-4 | 5.1162 | 4.9276 | 4.6710 | 4.3513 | 4.1153 | 5.2144 | 5.0867 | 4.9127 | 4.7364 | 4.6584 |

| Arm | Mean clip fraction | Mean gradient norm | Largest gradient norm |
|---|---|---|---|
| 384 at 3e-4 | 0.952 | 2.388 | 8.809 |
| 512 at 3e-4 | 0.960 | 2.517 | 7.088 |
| 512 at 1e-4 | 0.975 | 2.968 | 7.355 |
| 768 at 3e-4 | 0.931 | 2.086 | 5.802 |
| 768 at 1e-4 | 0.969 | 2.740 | 7.455 |

### 6e. Fit quality (`FITS.csv`, 150 fits, each with its bound flags)

- **Range of p\*:** 0.038 to 0.120, over 150 defined fits. At the upper bound: 0. At the lower bound: 0.
- **Undefined fits:** 0. They stay undefined.
- **Total gain:** signed; smallest 5652.2.
- **Sequences with negative gain:** in 133 fits; at 5% or more in 0. Largest 3.8% (384 at 3e-4 at E0.25, c06).
- **Objective at p\* over the objective at p = 0:** 0.042 to 0.076.

## 7. Disclosures

Written before any outcome was opened. The figures here depend on the corpus, the partition, the weights and the status records, and on no loss.

### 7a. The fresh rule, and identical and repeated text

**The rule.** Of 27,859 eligible articles: the 8,692 assigned to t00–d10 are out, including those behind their unused second halves; 94 text duplicates of assigned articles are out; every copy of a text repeated inside the pool is out (215 articles in 107 sets). That leaves 18,858 fresh articles with 779,618 sequences. The six groups use 2,407 of them, and 16,451 are left over.

- **Identical full text:** 0 sets across the fresh groups, 0 fresh texts equal to an assigned article's, 0 repeated inside a group. The rule removes these, so zero is what it should give.
- **What the rule does not remove:** short sequences and runs inside different articles. On all 12,529,953 windows of the used sequences, 64-token runs recurring in another fresh group: mean 0.15%, largest 0.19%. Recurring in the sequences t00–d10 used: mean 0.26%, largest 0.35%.

| Group | Articles | Sequences equal to one used by t00–d10 | Equal to any sequence of an assigned article | Identical to one in another fresh group | Repeats inside the group | Equal to a validation sequence | Equal to a pool sequence | 64-token runs recurring in t00–d10 | 64-token runs recurring in another fresh group | Validation sequences touched (of 512) | Pool sequences touched (of 2,048) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c01 | 390 | 0 | 1 | 1 | 0 | 0 | 0 | 0.24% | 0.13% | 3 | 1 |
| c02 | 402 | 0 | 0 | 0 | 0 | 0 | 0 | 0.21% | 0.16% | 3 | 0 |
| c03 | 413 | 0 | 0 | 0 | 0 | 0 | 0 | 0.28% | 0.19% | 5 | 1 |
| c04 | 380 | 0 | 1 | 1 | 0 | 0 | 0 | 0.21% | 0.15% | 1 | 1 |
| c05 | 401 | 0 | 0 | 0 | 0 | 0 | 0 | 0.26% | 0.14% | 1 | 0 |
| c06 | 421 | 0 | 1 | 0 | 0 | 0 | 0 | 0.35% | 0.15% | 1 | 0 |

**Limit.** The draws are treated as independent in every interval and test above. These figures do not measure how far that is true.

### 7b. Tied weights

The weights are used exactly as drawn. The check in the sealed engine allows at most n / 1,024 tied values, which is 16 here. Tied values means n minus the number of distinct values.

| Draw | Tied values in the run | Real-engine check, real Torch | Limit |
|---|---|---|---|
| c01 | 3 | 3 | 16 |
| c02 | 4 | 4 | 16 |
| c03 | 3 | 3 | 16 |
| c04 | 5 | 5 | 16 |
| c05 | 3 | 3 | 16 |
| c06 | 2 | 2 | 16 |

- **The order of tied entries.** The estimator's stable sort keeps them in ascending sequence index, so p\* repeats bit for bit for the same inputs on the same Python and libm.
- **That order matters to the objective.** In the real-engine check, on synthetic gains, the objective differed when the ties were reversed, in 6 of the 6 draws with a tie.
- **Not measured:** how much the order of ties moves p\* on these real gains. The frozen analysis has no such step.

### 7c. Each draw's inputs against the real-engine check

The sealed analysis does not compare input hashes, so this report does, from each draw's own `INPUTS.json`: weights, orders and pool orders against the real-Torch check; train, validation, pool and sequence indices against the native hashes that check reproduced.

| Draw | weights | orders | pool_orders | train | validation | pool | sequence_indices | tied_values |
|---|---|---|---|---|---|---|---|---|
| c01 | equal | equal | equal | equal | equal | equal | equal | equal |
| c02 | equal | equal | equal | equal | equal | equal | equal | equal |
| c03 | equal | equal | equal | equal | equal | equal | equal | equal |
| c04 | equal | equal | equal | equal | equal | equal | equal | equal |
| c05 | equal | equal | equal | equal | equal | equal | equal | equal |
| c06 | equal | equal | equal | equal | equal | equal | equal | equal |

**0 differences** in 48 comparisons, tied values included.

### 7d. The hypothesis, the rates and the premise

- **The hypothesis was formed after seeing d01–d10.** At every readout there, on a ladder at 3e-4, the per-draw argmax was 512 in 10/10 draws. So d01–d10 and t00 cannot confirm it. The idea for the control also came after seeing p\*.
- **The rates were not chosen again.** 3e-4 is the rate the few-epoch study selected on t00; 1e-4 is 768's lowest validation NLL on t00 among the five rates tried. Both come from validation NLL only, and p\* entered neither.
- **384 was not trained at 1e-4,** so at that rate only the fall from 512 to 768 is measured.

**E3 validation NLL on t00, one draw** (`LR_SELECTION.json`); the lowest for each width is in bold:

| Width | 3e-5 | 1e-4 | 3e-4 | 1e-3 | 3e-3 |
|---|---|---|---|---|---|
| 384 | 5.0190 | 4.8054 | **4.7314** | 4.8268 | 5.6396 |
| 512 | 4.9366 | 4.7344 | **4.7210** | 4.8458 | 6.0833 |
| 768 | 4.7903 | **4.6320** | 4.6677 | 4.9643 | 5.5970 |

### 7e. Shared items, and one analysis

- **Shared by design:** the validation set, the pre-training pool and the tokenizer are those of the earlier natural-text studies, and every draw shares them.
- **One analysis.** The sealed analysis was run once, by the owner. This report reads its outputs and does not re-run it.

### 7f. The public registration: after the runs, before the analysis

**The protocol, the sealed source and the seed registry's `REGISTRY.json` and policy were published at https://github.com/rafli-hl/sequence-weighting-research/pull/3,** created 2026-11-03T16:11:57Z, merged 2026-11-03T16:14:41Z, head commit `315a1f17e2a3d44c8e17a9386cdc851ac3c39122`. All 31 sealed files there are byte-equal to the local ones (`reports/natural-text-peak-analysis-approval-20261103-01/PUBLIC_PREREGISTRATION_CHECK.json`).

- **The timing.** It came about 22.0 minutes after Run C2 ended and before the analysis ran. So it fixes the analysis in public. It does not fix the data collection, whose protocol and seeds were in local records only until then.
- **The losses already existed.** All six draws' losses were on disk when it was published. That they were unopened rests on local records and the owner's word, and the public record cannot show it.
- **What is not public.** `DRAW.json` and `EXCLUSIONS.json` of the seed registry, so an outside reader cannot re-derive the registry; and the run outputs, so an outside reader has nothing to check the terminal hashes against.
- **This layout is not in it.** It was written after that pull request and frozen before the analysis: the owner's approval names its hash, the one in the table at the top of this report, and the report refuses to run under any other.
- **The wording there is looser than the protocol's.** Its description says the control tests "whether the drop at 768 is a learning-rate artifact". The protocol's reading is narrower and is the one that holds: the two rates tested, and nothing about other rates.

## 8. Operations (measured, from the status records)

| Measure | Run C1 | Run C2 |
|---|---|---|
| Draw seconds, by the worker's clock | c01 2,293.9, c02 2,278.9, c03 2,268.6 | c04 2,193.7, c05 2,191.0, c06 2,170.0 |
| Worker elapsed | 6,958 s | 6,810 s |
| Owner elapsed, Windows clock | 7,608 s | 7,438 s |
| Windows over the worker's clock | 1.093 | 1.092 |
| Worker peak memory | 2.43 GB | 2.43 GB |
| GPU peak, sampled | 2,386,349,260 bytes | 2,386,349,260 bytes |
| Kept output | 7,009,811 bytes, 60 files | 7,019,925 bytes, 60 files |
| Battery, first to last | 80% to 80% | 32% to 80% |

Each run: exit 0, on AC throughout, every state deleted without error. Run A of the few-epoch study selected 3e-4, and its records give 1e-4 as 768's lowest validation NLL on t00; Runs C1 and C2 used both. **Before c05 the gate needed 3 checks:** mean GPU utilization 20%, 14.5%, 6%, against a limit of 12%, with verdicts BUSY, BUSY, IDLE. Every other gate was idle at the first check. **What used the GPU is not established.** It waited about 2.5 minutes, outside the stage. Whether it touched c05's results is not measured.

Verification: `reports/natural-text-peak-c1-result-20261103-01/RUN_C1_VERIFICATION.json`, `reports/natural-text-peak-c2-result-20261103-01/RUN_C2_VERIFICATION.json`. **The causes of the slow worker clock and of the changes in draw time are not established.**

## 9. Limitations

From `PROTOCOL.md` section 11, with two additions here: the sentence on INTERIOR_PEAK, which is from section 7, and the line on the sample.

- **A mechanism:** no result here says why p\* orders as it does.
- **Other rates:** the control speaks to 1e-4 only. The best rate for 768 is not located, and the grid is coarse.
- **The rise at 1e-4:** 384 is not trained at 1e-4, so at that rate only the fall from 512 to 768 is measured.
- **The peak's place:** there is no rung between 512 and 768, and nothing above 768. INTERIOR_PEAK is an ordering of three rungs at this scale.
- **Shared items:** consistency across the pool, the tokenizer and the recipe is not tested.
- **E0:** in d01–d10, 768 started from a higher E0 validation NLL than 384 and 512 after the same pre-training. Neither rate arm changes that.
- **Scale:** depth 4, at most 34.7 M parameters, one corpus family. No scaling claim, and this is not Jane Street's setting: a constant rate with no horizon-tied schedule, and small models adapted from a short uniform pre-training.
- **Independence:** draws are treated as independent in every interval. The disclosure figures do not measure how far that is true.
- **No held-out test loss:** the test split is the pre-training pool.
- **Sample:** six draws from one corpus are the only inference unit. Seeds and schedules are not replications.

## 10. How these numbers were checked

`RESULT_CHECK.json` holds this check. **PASS: 0 mismatches against the sealed outputs in 2,705 comparisons, and 0 differences from the real-engine check's inputs**.

- **Recomputed from the run files, in code that imports neither `peak_analysis` nor `fewepoch_analysis` nor `text_analysis`:** all 150 fits with the sealed estimator; every row of `POINTS.csv` and `FITS.csv`; the six values, mean, interval and p-value of each contrast, with the t tail integrated directly; the status of each contrast, and the labels; NOT_OVERFIT; the rate effects; the by-readout tables; M; losses, clipping and E0.
- **Records against arrays:** the largest difference between a record's loss and the mean of its array is 7.24e-07, against a limit of 1e-05.
- **Inputs:** each draw's hashes and its tied values, from its own `INPUTS.json`, against the real-engine check (section 7c).
- **The readings:** each is compared, word for word, with this layout's copy of the sealed wording, under the labels, NOT_OVERFIT prefixes and premise line that follow from the recomputed values.
- **The saved records behind the disclosures:** each has its pinned hash, and each that carries a verdict passes.
- **The refits at bound 32:** not needed.
- **Not recomputed:** the estimator itself, which defines p\*.
