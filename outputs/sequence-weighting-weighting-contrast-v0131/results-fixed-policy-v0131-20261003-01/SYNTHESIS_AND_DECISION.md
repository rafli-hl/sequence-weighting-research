# Decision record: fixed-policy weighting and clipping diagnostics

3 October 2026 UTC. This closes the bounded existing-data v0131 analysis and places it beside the completed G1 clipping diagnostic v0130. It does not authorize another run. Keep all frozen source, raw records, the failed/cancelled attempt evidence and its receipts.

## Evidence and review status

The v0131 source manifest is `outputs/sequence-weighting-weighting-contrast-v0131/MANIFEST.txt` (SHA256 `9f2ff243d91544b4a636084d12727ad2830a695eb2b015999a1421cbb5116697`). The derived result is `outputs/sequence-weighting-weighting-contrast-v0131/results-fixed-policy-v0131-20261003-01/SUMMARY.json` (SHA256 `4f2b751aab694fabc3a06c591dc54d85b858e864c440e98c8293e8e57d54d297`), with all 360 rows in `PAIRS.json`, five-corpus test contributions in `COMPONENT_TABLE.csv`, and the paired visual `PAIRED_FIGURE.png`. `ANALYSIS_COMPLETE.json` (SHA256 `14d29e06df2653827c0eb6713d9a1f96e499f3fa7e9d655cfb44371335bb7169`) binds those outputs. `RECONCILIATION.json` (SHA256 `855af1b3979b42d864bbbfc7611b9e239720774168ba9b6f20a65f077ad40bc2`) records 360 checkpoint contrasts, 60 F10 quartile pairs and 10 primary pairs. Its saved candidate status preceded final review.

The two current Ubuntu receipt sets under `outputs/sequence-weighting-weighting-contrast-v0131/receipts/` each have exit 0, matching stdout/stderr hashes and no failure marker. Terminal durations were **40 seconds for analysis** and **86 seconds for reconciliation**, each below its 300-second ceiling. The independent final **read-only** result review (thread `01a0f36f-6b34-72f7-8592-bcf656ff10bf`, turn `01a10302-27fd-7135-a439-95c71767479f`) concluded **PASS with no result blockers** after checking the 360 checkpoint contrasts, 60 F10 quartile pairs and 10 primary pairs. No training, model evaluation, p* refit or new numerical execution was part of that review.

The first manual v0131 invocation was cancelled by the user, and a second invocation hit the existing-directory guard. The empty directory and seven failed receipts were preserved at `outputs/sequence-weighting-weighting-contrast-v0131/preserved-cancelled-attempts-20261003T1634Z/`; the original cancelled attempt's duration is unknown. Those attempts are not scientific results and are not counted as completed analysis. The later successful analysis and reconciliation used the same reviewed source without altering v0128 or v0130.

## Fixed-F10 result

The primary estimand is **random minus uniform test NLL** at v0128 G1 width 128, fixed epoch 10, clip 1, LR 1e-4 and WD .1. The two model/weight seeds are paired and nested within each of five already seen corpus draws; corpus means are weighted equally. Positive values mean random weighting is worse on test data.

| Corpus seed | Paired-seed mean test NLL difference, nats |
|---:|---:|
| 88547 | +0.031357 |
| 88771 | +0.044778 |
| 88993 | +0.049268 |
| 89203 | +0.047019 |
| 89431 | +0.038879 |
| **Five-corpus mean** | **+0.042260** |

The descriptive SD across the five corpus means is **0.007218 nats**, range **+0.031357 to +0.049268**. All five corpus means and all ten paired values are positive. The test difference decomposes arithmetically into shared **+0.008754**, group **+0.016464**, and instance **+0.017042** nats, each already divided by three; their sum recovers +0.042260. This is a decomposition of loss, not causal attribution.

Using the saved random-arm weights, the bottom and top 128 sequences were fixed by ascending `(weight, sequence_index)` before reading losses. The random-minus-uniform training-gain contrast averages **-0.068130** nats in the low-weight quartile and **+0.015144** in the high-weight quartile; high minus low is **+0.083274**. Component high-minus-low contrasts are shared **+0.003789**, group **+0.016125**, instance **+0.229908** component-NLL nats; their average recovers the total. Crucially, the high-weight shared and group contrasts themselves remain negative (**-0.022739** and **-0.034844**); the positive high-weight total comes from instance (**+0.103014**). This is preferential *allocation* to high-weight sequences, especially their instance content, not more overall memorization or a demonstrated mediation mechanism.

Consistent with that distinction, mean training NLL is **0.976774 random versus 0.934007 uniform**, and instance training accuracy is **7.407% random versus 8.130% uniform**. Random weights have worse overall training fit and worse held-out test NLL in this fixed comparison. The 60-pair, six-checkpoint G1/G16 × three-capacity grid is retained as descriptive context; no checkpoint or p* was selected from it.

## Joint decision and limits

The prior clipping record is `outputs/g1-clipping-diagnostic-v0130/results/DECISION_RECORD.md` (SHA256 `fd951f9a2f9b287f09f8a046c517cd28cf195d930ad0a863f623e23914ad8a9b`). There, removing adaptation clipping failed the frozen width-128 validation criterion (mean clip-1 minus no-clip **-0.006168 nats**, negative in all five corpora); K remained negative in every measured pair despite positive delta K. **Retain v0128 clip 1 as the canonical fixed G1 control.** Do not reinterpret v0130 random/no-clip versus v0128 uniform/clip-1 as a weighting comparison.

Together the saved results support a narrow descriptive statement: under one fixed synthetic setup, unequal weights preferentially improve high-weight instance training sequences while degrading overall train and held-out test losses relative to uniform; disabling clipping does not rescue the prespecified middle-capacity validation outcome. These five corpora were reused, and two seeds nested in one corpus are not independent dataset replications. Three capacities do not establish an interior-peak shift. Neither the train association nor the test decomposition proves causality or a large-LM mechanism. No venue, novelty or publication claim follows without renewed primary-literature review.

**Completed-study decision:** record the adverse held-out tradeoff and the failed no-clip criterion, preserve all signed/undefined fit records and raw arrays, and close this analysis. **Future question only, not an approved experiment:** whether the high-weight instance allocation and held-out penalty persist under fresh paired corpora with a separately frozen validation-based design. No new run, search, cloud use or publication is authorized by this record.
