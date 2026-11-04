# Few-epoch study: result

**Date:** 03 Nov 2026. **Status:** Runs B1 and B2 are COMPLETE and the sealed analysis is COMPLETE. The owner ran it once, under approval OWNER-20261103-FEWEPOCH-ANALYSIS-01 (`reports/natural-text-ladder-owner-decisions-20261103-02/OWNER_DECISIONS.md`). The order and wording of this report were fixed before any outcome was opened; its readings are the sealed ones, quoted. **Measured results are in sections 1 to 3 and 5. Nothing here claims a mechanism.**

**Check:** **PASS: 0 mismatches against the sealed outputs in 4,889 comparisons, and 0 differences from the real-engine check's inputs** (section 7).

| Record | SHA-256 |
|---|---|
| `ANALYSIS.json` | `df0c56146387142983b60773adbbf1d8eddc7d0fb85eae2231f4d6d28ca9ab26` |
| `POINTS.csv` | `9a2baad33a711901098ffa365294a18eff6a6761d01293449d0b17cb576de026` |
| `FITS.csv` | `262fea51f7d6f933a56cf1adcb56f8e83a34127bc20ad86a1c8165b9a8dd05e8` |
| `Run B1 TERMINAL.json` | `7b04d74b62d10847e288c8972a861f179d06e528e2f60ce31a432f04473c8ae2` |
| `Run B2 TERMINAL.json` | `eef9f17516f836042b124b50c17a5a28a5d01cb8659b6e8b296d4c96d80ab95e` |
| `SOURCE_SUBJECT.json` | `62f05466d1f3c0ef09de3d9ed12e8683036c82912978e0d77a91eeb34be3602a` |
| `this layout, make_results_report.py` | `91a61d0a4c074e095071416bc87e2edad07518e561199cfceed306a66e1a4a41` |
| `owner decision` | `b3899baa4016c379e6bc210777845de7dda89c25e95b8af453378a7e6d194283` |

## 1. NOT_OVERFIT per width, the manipulation check

Per width, per draw, Δ = validation NLL at E3 minus at E2. The verdict is per width, from the df-9 interval of the mean Δ over the ten draws: below 0 gives NOT_OVERFIT, above 0 OVERFIT, otherwise PLATEAU. There is no verdict for a single draw.

| Width | Verdict | Mean Δ | 95% interval (df 9) | Draws Δ < 0 | Mean gap at E3 | Lowest mean validation NLL (readout) |
|---|---|---|---|---|---|---|
| 64 | **NOT_OVERFIT** | −0.1351 | [−0.1385, −0.1317] | 10/10 | +0.1669 | 5.2589 (E3) |
| 96 | **NOT_OVERFIT** | −0.1123 | [−0.1170, −0.1075] | 10/10 | +0.2045 | 5.1184 (E3) |
| 128 | **NOT_OVERFIT** | −0.1035 | [−0.1080, −0.0991] | 10/10 | +0.2347 | 5.0319 (E3) |
| 192 | **NOT_OVERFIT** | −0.1075 | [−0.1135, −0.1015] | 10/10 | +0.2907 | 4.9145 (E3) |
| 256 | **NOT_OVERFIT** | −0.1213 | [−0.1284, −0.1141] | 10/10 | +0.3502 | 4.8142 (E3) |
| 384 | **NOT_OVERFIT** | −0.0852 | [−0.0905, −0.0800] | 10/10 | +0.4729 | 4.7240 (E3) |
| 512 | **NOT_OVERFIT** | −0.0593 | [−0.0651, −0.0535] | 10/10 | +0.5735 | 4.7036 (E3) |
| 768 | **NOT_OVERFIT** | −0.0727 | [−0.0821, −0.0634] | 10/10 | +0.5640 | 4.6672 (E3) |

**What each primary needs.** A primary is read as a test of the few-epoch question only if every width it uses is NOT_OVERFIT.

| Primary | Widths it uses | All NOT_OVERFIT | Widths that fail |
|---|---|---|---|
| M | 384, 768 | yes | none |
| FALL | 384, 512, 768 | yes | none |
| RISE | 64, 96, 128, 192, 256, 384 | yes | none |

**Δ per draw,** recomputed from each `record.json`, because `ANALYSIS.json` keeps the interval and not the ten values:

| Width | d01 | d02 | d03 | d04 | d05 | d06 | d07 | d08 | d09 | d10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 64 | −0.1341 | −0.1364 | −0.1260 | −0.1327 | −0.1434 | −0.1384 | −0.1364 | −0.1325 | −0.1324 | −0.1391 |
| 96 | −0.1093 | −0.1209 | −0.1019 | −0.1070 | −0.1244 | −0.1161 | −0.1136 | −0.1094 | −0.1109 | −0.1090 |
| 128 | −0.1030 | −0.1028 | −0.0901 | −0.0992 | −0.1142 | −0.1038 | −0.1049 | −0.1025 | −0.1074 | −0.1073 |
| 192 | −0.0982 | −0.1205 | −0.1002 | −0.1015 | −0.1146 | −0.0984 | −0.1184 | −0.1074 | −0.1041 | −0.1121 |
| 256 | −0.1135 | −0.1315 | −0.1106 | −0.1085 | −0.1293 | −0.1163 | −0.1305 | −0.1225 | −0.1138 | −0.1362 |
| 384 | −0.0776 | −0.0919 | −0.0812 | −0.0745 | −0.0922 | −0.0757 | −0.0852 | −0.0903 | −0.0925 | −0.0913 |
| 512 | −0.0475 | −0.0646 | −0.0596 | −0.0518 | −0.0653 | −0.0595 | −0.0468 | −0.0650 | −0.0619 | −0.0708 |
| 768 | −0.0576 | −0.0739 | −0.0520 | −0.0721 | −0.0873 | −0.0630 | −0.0742 | −0.0905 | −0.0884 | −0.0685 |

## 2. The primaries: M, FALL and RISE under Holm

Two-sided one-sample t tests over the ten draws, Holm step-down at family-wise 5%. **The labels come from Holm; the intervals and the first p-value are unadjusted.** So an interval can exclude 0 while the label is not a rejection.

| Primary | Holm label | Read as a few-epoch test | Mean | Unadjusted 95% interval (df 9) | p, unadjusted | Holm step, threshold | Rejected | Holm-adjusted p | Draws < 0 / > 0 | Draws flagged at p\* ≥ 7.999 |
|---|---|---|---|---|---|---|---|---|---|---|
| **M** | **CAPACITY_BEYOND_MEMORIZATION** | yes | −0.0066 | [−0.0076, −0.0055] | 1.76e−07 | 2, p ≤ 0.0250 | yes | 3.51e−07 | 10/0 | none |
| **FALL** | **CONTINUES_RISING** | yes | +0.0040 | [+0.0010, +0.0069] | 0.0133 | 3, p ≤ 0.0500 | yes | 0.0133 | 1/9 | none |
| **RISE** | **RISES** | yes | +0.0275 | [+0.0269, +0.0280] | 1.91e−15 | 1, p ≤ 0.0167 | yes | 5.74e−15 | 0/10 | none |

| Primary | Statistic per draw | Memorization-only account predicts | Jane Street pattern predicts | Power stated in advance, from effects seen at 3e-5 (section 4c): at the seen effect, at half |
|---|---|---|---|---|
| M | Mean over 101 gap levels of p\*(768) − p\*(384) | NOT_DETECTED | not fixed by the pattern | >0.999, 0.953 |
| FALL | OLS slope of p\* on log2 width over 384, 512, 768 at E3 | CONTINUES_RISING or INCONCLUSIVE | TURNS_DOWN | 0.999, 0.714 |
| RISE | OLS slope of p\* on log2 width over 64–384 at E3 | RISES | RISES | >0.999, >0.999 |

**Per-draw values.** The common range is the gap range that 384 and 768 both span along E0.25–E3, over which M is averaged.

| Draw | M | M common gap range | FALL | RISE |
|---|---|---|---|---|
| d01 | −0.0070 | [+0.1427, +0.4817] | +0.0005 | +0.0274 |
| d02 | −0.0042 | [+0.1484, +0.4612] | +0.0047 | +0.0272 |
| d03 | −0.0046 | [+0.1686, +0.4838] | +0.0126 | +0.0264 |
| d04 | −0.0070 | [+0.1352, +0.4657] | +0.0024 | +0.0287 |
| d05 | −0.0061 | [+0.1311, +0.4564] | +0.0013 | +0.0271 |
| d06 | −0.0062 | [+0.1741, +0.5252] | +0.0072 | +0.0273 |
| d07 | −0.0088 | [+0.1442, +0.4491] | +0.0009 | +0.0277 |
| d08 | −0.0084 | [+0.1566, +0.4759] | −0.0013 | +0.0288 |
| d09 | −0.0067 | [+0.1129, +0.4268] | +0.0060 | +0.0275 |
| d10 | −0.0066 | [+0.1589, +0.5036] | +0.0052 | +0.0266 |

**The saturation rule did not apply:** no draw was flagged, so no refit at bound 32 was needed.

**The sealed readings,** quoted exactly from `ANALYSIS.json`:

1. "The few-epoch question is read only where every width a primary uses was still improving its validation loss from E2 to E3 (NOT_OVERFIT). The models are small (0.73-34.7 M parameters, depth 4) and see far fewer tokens per parameter than compute-optimal training; "closer to Jane Street's setting" means 3 epochs and no detected overfitting, nothing more."
2. "Labels follow Holm's step-down over M, FALL and RISE at family-wise 5% (two-sided t tests, ten draws); every primary's Holm-adjusted p-value is reported."
3. "M: at matched train-validation gap, p* at 768 is below p* at 384 (CAPACITY_BEYOND_MEMORIZATION). This contradicts the memorization-only account, which predicts NOT_DETECTED. It is not by itself evidence of a capacity effect. At matched gap the larger width has had fewer epochs, so a nonzero M is also what p* gives if it depends on training progress rather than on the gap (stated in advance; in the planning fixtures an epoch-only curve read CAPACITY_BEYOND_MEMORIZATION in 96-99% of replicates). The gap includes each width's E0 offset (training articles from WikiText-103, validation from WikiText-2's validation split); mean E0 gap: 384 -0.0341, 768 -0.0350."
4. "FALL: at E3, p* rises with width over 384-768 (CONTINUES_RISING): no turn-down within this ladder. This matches the memorization-only prediction, and also Jane Street's pattern with a peak above 768; the study cannot separate the two."
5. "RISE: at E3, p* rises with width over 64-384 (RISES), as both accounts predict."
6. "Data: WikiText-103 raw training articles, excluding every article equal by title or text to a WikiText-2 article; the tokenizer, the validation set and the pre-training pool are those of the earlier natural-text studies. The common rate was chosen on the tuning draw t00 by validation NLL only."

## 3. Secondaries

Non-gating, with no multiplicity adjustment. Only M, FALL and RISE, under Holm, are primaries.

### 3a. The peak shift across readouts

**MOVES_LARGER:** mean OLS slope of the peak location on log2 readout +0.0237 doublings of width per doubling of readout, 95% interval [+0.0117, +0.0357] (df 9), draws 0 below 0 and 10 above.

**Slope per draw:** d01 +0.0049, d02 +0.0116, d03 +0.0497, d04 +0.0234, d05 +0.0082, d06 +0.0242, d07 +0.0032, d08 +0.0280, d09 +0.0448, d10 +0.0389.

| Readout | E0.25 | E0.5 | E1 | E2 | E3 |
|---|---|---|---|---|---|
| Locations at 768 | 0 | 0 | 0 | 0 | 0 |
| Locations at 64 | 0 | 0 | 0 | 0 | 0 |

**The sealed censoring statement:** "No location is at a ladder end, so the slope is not censored."

### 3b. By readout

| Readout | FALL statistic, unadjusted 95% interval | RISE statistic, unadjusted 95% interval | Panel argmax | Per-draw argmax | Mean location, log2 (width) |
|---|---|---|---|---|---|
| E0.25 | −0.0017 [−0.0030, −0.0004], 8 draws < 0 | +0.0153 [+0.0144, +0.0163], 10 draws > 0 | 512 | 512 ×10 | 9.066 (536) |
| E0.5 | −0.0031 [−0.0042, −0.0020], 10 draws < 0 | +0.0157 [+0.0150, +0.0163], 10 draws > 0 | 512 | 512 ×10 | 9.023 (520) |
| E1 | −0.0018 [−0.0028, −0.0009], 9 draws < 0 | +0.0160 [+0.0155, +0.0164], 10 draws > 0 | 512 | 512 ×10 | 9.059 (533) |
| E2 | +0.0016 [−0.0004, +0.0035], 3 draws < 0 | +0.0209 [+0.0205, +0.0213], 10 draws > 0 | 512 | 512 ×10 | 9.119 (556) |
| E3 | +0.0040 [+0.0010, +0.0069], 1 draws < 0 | +0.0275 [+0.0269, +0.0280], 10 draws > 0 | 512 | 512 ×10 | 9.129 (560) |

**Peak location per draw,** log2 width; "end" marks a location at a ladder end, which is censored:

| Draw | E0.25 | E0.5 | E1 | E2 | E3 |
|---|---|---|---|---|---|
| d01 | 9.102 | 9.043 | 9.039 | 9.094 | 9.102 |
| d02 | 9.089 | 9.092 | 9.086 | 9.120 | 9.130 |
| d03 | 9.050 | 9.056 | 9.119 | 9.201 | 9.205 |
| d04 | 9.050 | 9.010 | 9.047 | 9.099 | 9.115 |
| d05 | 9.093 | 9.050 | 9.048 | 9.099 | 9.110 |
| d06 | 9.091 | 9.032 | 9.079 | 9.141 | 9.150 |
| d07 | 9.113 | 9.033 | 9.060 | 9.088 | 9.104 |
| d08 | 9.014 | 8.978 | 9.030 | 9.084 | 9.090 |
| d09 | 9.020 | 8.985 | 9.017 | 9.148 | 9.145 |
| d10 | 9.037 | 8.953 | 9.060 | 9.119 | 9.135 |

**Panel mean p\*:**

| Width | E0.25 | E0.5 | E1 | E2 | E3 |
|---|---|---|---|---|---|
| 64 | 0.0179 | 0.0188 | 0.0201 | 0.0232 | 0.0261 |
| 96 | 0.0260 | 0.0258 | 0.0271 | 0.0316 | 0.0360 |
| 128 | 0.0313 | 0.0314 | 0.0330 | 0.0391 | 0.0449 |
| 192 | 0.0408 | 0.0406 | 0.0431 | 0.0522 | 0.0607 |
| 256 | 0.0479 | 0.0482 | 0.0514 | 0.0624 | 0.0735 |
| 384 | 0.0574 | 0.0591 | 0.0602 | 0.0764 | 0.0979 |
| 512 | 0.0639 | 0.0634 | 0.0654 | 0.0884 | 0.1175 |
| 768 | 0.0565 | 0.0566 | 0.0590 | 0.0791 | 0.1038 |

**Panel mean gap,** validation NLL minus training NLL:

| Width | E0 (offset) | E0.25 | E0.5 | E1 | E2 | E3 |
|---|---|---|---|---|---|---|
| 64 | −0.0102 | +0.0278 | +0.0484 | +0.0830 | +0.1318 | +0.1669 |
| 96 | −0.0160 | +0.0399 | +0.0686 | +0.1120 | +0.1669 | +0.2045 |
| 128 | −0.0202 | +0.0516 | +0.0842 | +0.1328 | +0.1911 | +0.2347 |
| 192 | −0.0275 | +0.0692 | +0.1096 | +0.1624 | +0.2303 | +0.2907 |
| 256 | −0.0311 | +0.0850 | +0.1290 | +0.1861 | +0.2675 | +0.3502 |
| 384 | −0.0341 | +0.1081 | +0.1612 | +0.2269 | +0.3490 | +0.4729 |
| 512 | −0.0375 | +0.1253 | +0.1864 | +0.2682 | +0.4159 | +0.5735 |
| 768 | −0.0350 | +0.1473 | +0.2051 | +0.2810 | +0.4162 | +0.5640 |

The E0 gap is each width's offset: training text comes from WikiText-103 articles, validation text from WikiText-2's validation split (`PROTOCOL.md` section 6a).

### 3c. Losses and clipping (panel means; NLL in nats per token)

| Width | E0 train | E0 validation | E0.25 train | E0.5 train | E1 train | E2 train | E3 train | E0.25 validation | E0.5 validation | E1 validation | E2 validation | E3 validation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 64 | 6.1155 | 6.1053 | 5.8868 | 5.7433 | 5.5322 | 5.2622 | 5.0919 | 5.9147 | 5.7917 | 5.6152 | 5.3940 | 5.2589 |
| 96 | 5.9230 | 5.9070 | 5.6898 | 5.5362 | 5.3183 | 5.0638 | 4.9139 | 5.7297 | 5.6048 | 5.4304 | 5.2307 | 5.1184 |
| 128 | 5.8044 | 5.7843 | 5.5546 | 5.3977 | 5.1812 | 4.9443 | 4.7972 | 5.6062 | 5.4820 | 5.3140 | 5.1354 | 5.0319 |
| 192 | 5.6588 | 5.6313 | 5.3811 | 5.2223 | 5.0184 | 4.7917 | 4.6238 | 5.4503 | 5.3319 | 5.1808 | 5.0220 | 4.9145 |
| 256 | 5.5875 | 5.5564 | 5.2859 | 5.1265 | 4.9250 | 4.6679 | 4.4640 | 5.3709 | 5.2555 | 5.1110 | 4.9355 | 4.8142 |
| 384 | 5.5432 | 5.5091 | 5.1922 | 5.0239 | 4.7772 | 4.4603 | 4.2511 | 5.3003 | 5.1851 | 5.0041 | 4.8093 | 4.7240 |
| 512 | 5.5533 | 5.5158 | 5.1512 | 4.9438 | 4.6668 | 4.3470 | 4.1301 | 5.2765 | 5.1302 | 4.9351 | 4.7629 | 4.7036 |
| 768 | 5.5867 | 5.5516 | 5.1113 | 4.8976 | 4.6302 | 4.3237 | 4.1031 | 5.2586 | 5.1027 | 4.9112 | 4.7399 | 4.6672 |

| Width | Mean clip fraction | Mean gradient norm | Largest gradient norm |
|---|---|---|---|
| 64 | 0.902 | 1.917 | 8.309 |
| 96 | 0.919 | 2.003 | 9.422 |
| 128 | 0.926 | 2.054 | 9.300 |
| 192 | 0.935 | 2.135 | 11.410 |
| 256 | 0.942 | 2.224 | 13.036 |
| 384 | 0.954 | 2.393 | 12.955 |
| 512 | 0.961 | 2.522 | 10.922 |
| 768 | 0.933 | 2.088 | 8.028 |

### 3d. Fit quality (`FITS.csv`, 400 fits at 3e-4, each with its bound flags)

- **Range of p\*:** 0.017 to 0.120, over 400 defined fits. At the upper bound: 0. At the lower bound: 0.
- **Undefined fits:** 0. They stay undefined.
- **Total gain:** signed; smallest 3598.3.
- **Sequences with negative gain:** in 321 fits; at 5% or more in 0. Largest 4.3% (width 384 at E0.25, d06).
- **Objective at p\* over the objective at p = 0:** 0.042 to 0.088.

## 4. Disclosures

Written before any outcome was opened. The sealed analysis does not print these three, so they are given here by hand, as the owner decided.

### 4a. Identical and repeated text across the groups

**The groups share no article index and no sequence index, but they do share some text.** WikiText-103 holds some articles with identical text under different indices, so some texts, and some exact token sequences, appear in more than one group. `PROTOCOL.md` section 2's "the groups share no article" holds by index only. The owner kept the frozen partition and chose this disclosure (decisions 20261102-01 and 20261102-03). No rule changed because of it.

- **Identical-text sets across groups: 10.** 2 touch t00 and 8 span analysis draws.
- **Sequences in a text shared with another group:** mean 0.74% of a group over the eleven groups, largest 1.89% (d04).
- **Exact token sequences used in more than one group: 670 distinct,** 578 of them across analysis draws and 92 touching t00. Counted per group, they are a mean 0.74% of a group, largest 1.89% (d04).
- **64-token runs recurring in another group,** on all 22,974,909 windows of the used sequences: mean 1.00%, largest 2.21% (d04).
- **Used sequences exactly equal to a validation sequence:** 0.

| Group | Sequences in a shared text | Share of 16,384 | Sequences identical to one in another group | 64-token runs recurring elsewhere | Validation sequences touched (of 512) | Pool sequences touched (of 2,048) |
|---|---|---|---|---|---|---|
| t00 | 92 | 0.56% | 92 | 0.79% | 1 | 1 |
| d01 | 28 | 0.17% | 28 | 0.45% | 3 | 0 |
| d02 | 83 | 0.51% | 84 | 0.76% | 1 | 2 |
| d03 | 219 | 1.34% | 219 | 1.53% | 2 | 0 |
| d04 | 310 | 1.89% | 310 | 2.21% | 1 | 1 |
| d05 | 162 | 0.99% | 162 | 1.29% | 1 | 1 |
| d06 | 34 | 0.21% | 34 | 0.54% | 2 | 3 |
| d07 | 29 | 0.18% | 29 | 0.35% | 2 | 0 |
| d08 | 279 | 1.70% | 279 | 2.00% | 2 | 2 |
| d09 | 74 | 0.45% | 74 | 0.66% | 0 | 0 |
| d10 | 28 | 0.17% | 29 | 0.38% | 1 | 0 |

**Limits of this disclosure.** The draws are treated as independent in every interval and test above. The earlier rough bound, a variance rise of about 1% for the ten-draw mean, is an assumption and not a measurement (`reports/natural-text-fewepoch-runa-package-20261102-02/DISCLOSURE_FIGURES.md`). Earlier reports quote 1.01% and 2.34% from a 1 in 64 sample of windows; the figures above replace them. The B package's report says the groups share "no sequence"; that holds by index only, and this section corrects it.

### 4b. Tied weights

The weights are used exactly as drawn (owner decision 20261102-03). Exact float32 ties occur at this N, so the check in `text_engine.weights` allows at most n / 1,024 tied values, which is 16 here, in place of the earlier refusal of any tie. Tied values means n minus the number of distinct values.

| Draw | Tied values in the run | Real-engine check, real Torch | Limit |
|---|---|---|---|
| d01 | 2 | 2 | 16 |
| d02 | 0 | 0 | 16 |
| d03 | 4 | 4 | 16 |
| d04 | 2 | 2 | 16 |
| d05 | 2 | 2 | 16 |
| d06 | 2 | 2 | 16 |
| d07 | 1 | 1 | 16 |
| d08 | 2 | 2 | 16 |
| d09 | 3 | 3 | 16 |
| d10 | 4 | 4 | 16 |

- **The order of tied entries.** The estimator's stable sort keeps them in ascending sequence index, so p\* repeats bit for bit for the same inputs on the same Python and libm.
- **That order matters to the objective.** In the real-engine check, on synthetic gains, the objective differed when the ties were reversed, in every draw with a tie.
- **Not measured:** how much the order of ties moves p\* on these real gains. The frozen analysis has no such step.

### 4c. The rate change from 3e-5 to 3e-4

**This study ran every width at 3e-4. The earlier studies that motivated it ran at 3e-5:** the one-rate study at every width, the late-turn study at 256–768. Ladder Run B used 3e-4 at 64, 1e-4 at 96 and 3e-5 at 128–384. The rate here was selected on t00, a draw used for nothing else, by validation NLL only, under the frozen rule: no p\*, gain or analysis draw entered.

| Rate on t00 | Eligible | Diverged widths | Mean E3 validation NLL over the eight widths |
|---|---|---|---|
| 3e-5 | yes | none | 5.2671 |
| 1e-4 | yes | none | 5.0489 |
| 3e-4 **(selected)** | yes | none | 4.9088 |
| 1e-3 | yes | none | 4.9575 |
| 3e-3 | yes | none | 5.4391 |

**The common rate is lowest on the mean, not at every width.** E3 validation NLL on t00; the lowest for each width is in bold:

| Width | 3e-5 | 1e-4 | 3e-4 | 1e-3 | 3e-3 |
|---|---|---|---|---|---|
| 64 | 5.8419 | 5.5733 | 5.2587 | **5.1142** | 5.1871 |
| 96 | 5.6259 | 5.3672 | 5.1130 | **5.0444** | 5.1534 |
| 128 | 5.4822 | 5.2403 | 5.0378 | **5.0072** | 5.1312 |
| 192 | 5.2781 | 5.0692 | **4.9171** | 4.9630 | 5.2893 |
| 256 | 5.1628 | 4.9697 | **4.8237** | 4.8946 | 5.4316 |
| 384 | 5.0190 | 4.8054 | **4.7314** | 4.8268 | 5.6396 |
| 512 | 4.9366 | 4.7344 | **4.7210** | 4.8458 | 6.0833 |
| 768 | 4.7903 | **4.6320** | 4.6677 | 4.9643 | 5.5970 |

**What follows from the change:**
- **Within this study,** every width shares the one rate, so M, FALL and RISE do not compare rates. On t00, one draw, the rate with the lowest validation NLL is not the same at every width (the table above). What that does to p\* is not measured here.
- **Against the earlier studies,** the rate changed together with the data per draw (1,536 to 16,384 sequences), the epochs (32 to 3) and the corpus (WikiText-2 to WikiText-103 articles), with 3,072 updates per width held fixed (`PROTOCOL.md` section 3). So no difference from those studies can be assigned to any one of these.
- **The levels of p\* may not carry over.** At 64 and 96, the one-rate study measured, at 3e-5 against Run B's higher rates, a lower mean p\* over E4–E32, a smaller gap at E32 and a lower validation NLL at E32 (`reports/natural-text-onerate-result-20261031-01/RESULT.md`).
- **The power stated in advance is not a measure of power at 3e-4.** It uses effects seen in the earlier studies, at 3e-5 on WikiText-2: M over E1–E4, FALL at E24, RISE at E1 (`PROTOCOL.md` section 9).

### 4d. Also stated in advance

- **Seen design.** The design follows natural-text results already seen: the late turn-down and peak shift at E24–E32, and the one-rate panel means behind M (`PROTOCOL.md`, opening disclosure and section 6c, exploratory).
- **Shared items.** The validation set, the pool and the tokenizer are those of the earlier natural-text studies, and every analysis draw shares them.
- **One analysis.** The sealed analysis was run once, by the owner. This report reads its outputs and does not re-run it.

## 5. Operations (measured, from the status records)

| Measure | Run B1 | Run B2 |
|---|---|---|
| Draw seconds, by the worker's clock | d01 1,905.6, d02 1,900.1, d03 1,956.7, d04 1,990.7, d05 1,999.3 | d06 1,933.6, d07 1,948.8, d08 1,944.9, d09 1,890.5, d10 1,911.8 |
| Worker elapsed | 9,959 s | 9,821 s |
| Owner elapsed, Windows clock | 10,592 s | 10,583 s |
| Windows over the worker's clock | 1.064 | 1.078 |
| Worker peak memory | 2.41 GB | 2.41 GB |
| GPU peak, sampled | 2,388,446,412 bytes | 2,388,446,412 bytes |
| Kept output | 18,637,710 bytes, 153 files | 18,638,316 bytes, 153 files |
| Battery, first to last | 11% to 80% | 80% to 80% |

Each run: exit 0, gates idle at the first check, on AC throughout, every state deleted without error. Run A selected the rate; Runs B1 and B2 used it. Verification: `reports/natural-text-fewepoch-b1-result-20261102-01/RUN_B1_VERIFICATION.json`, `reports/natural-text-fewepoch-b2-result-20261103-01/RUN_B2_VERIFICATION.json`. **The causes of the slow worker clock and of the changes in draw time are not established.**

## 6. Limitations (`PROTOCOL.md` section 11)

- **Scale:** depth 4, at most 34.7 M parameters, one corpus family, few tokens per parameter. No large-model or scaling claim follows.
- **Not Jane Street's setting:** a constant rate with no horizon-tied schedule; small models adapted from a short uniform pre-training.
- **Censoring:** a peak above 768 cannot be placed, and CONTINUES_RISING does not separate the accounts.
- **The M confound:** at matched gap the larger width has had fewer epochs. M can contradict the memorization-only account but cannot show a capacity effect.
- **Fixed readouts mix capacity with training progress.**
- **Data selection:** the corpus excludes WikiText-2's articles, so it is not the full WikiText-103 training split.
- **No held-out test loss:** the test split is the pre-training pool.
- **Sample:** ten draws from one corpus are the only inference unit. Seeds and schedules are not replications.

## 7. How these numbers were checked

`RESULT_CHECK.json` holds this check. **PASS: 0 mismatches against the sealed outputs in 4,889 comparisons, and 0 differences from the real-engine check's inputs**.

- **Recomputed from the run files, in code that imports neither `fewepoch_analysis` nor `text_analysis`:** all 400 fits with the sealed estimator; every row of `POINTS.csv` and `FITS.csv`; the ten values, mean, interval and p-value of each primary, with the t tail integrated directly; Holm and the labels; NOT_OVERFIT; the by-readout curves and statistics; the peak shift; losses, clipping and the E0 gap.
- **Records against arrays:** the largest difference between a record's loss and the mean of its array is 1.02e-06, against a limit of 1e-04.
- **Inputs:** each draw's weight, order and token hashes and its tied values, from its own `INPUTS.json`, against the real-engine check.
- **The readings:** their wording is sealed. Their labels, the NOT_OVERFIT prefix, the power and the E0 gap are compared with the recomputed values.
- **Not recomputed:** the estimator itself, which defines p\*; the refits at bound 32, which were not needed.
