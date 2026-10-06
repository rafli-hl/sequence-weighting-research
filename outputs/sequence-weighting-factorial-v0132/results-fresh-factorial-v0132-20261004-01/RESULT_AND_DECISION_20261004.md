# v0132 fresh factorial: result and decision

4 October 2026 UTC. **Bounded study complete; runtime, numerical audit and
independent result review passed.** This is the new fresh-data experiment, not
the completed v0130 clipping diagnostic or v0131 historical reanalysis.

## Frozen design and result

G1 only, width 128, fixed F10, AdamW LR 1e-4 / WD .1 / clip 1. Five fresh corpus
seeds (91320101–91320105), two nested model/weight seeds per corpus, ten shared
U-pretrained checkpoints, forty matched adaptations. Tokens, labels,
teacher-forced context, initial checkpoints, batch orders and component loss
coefficients were fixed within each matched set. The arms apply weights to
(shared, group, instance) losses as U=(1,1,1), R=(w, w, w), S=(w, w, 1), I=(1,1, w).

The primary is **0.5 × [(R−S)+(I−U)] in unweighted F10 group-token test NLL**:
compute within each matched seed, average the two nested seeds, then average
the five corpus means equally. Positive means worse held-out group-rule NLL.
Group outcomes are nats per group-answer token, without division by three.
The corpus replication count is five, not ten; no p-value is claimed.

| Fresh corpus | Primary contrast, nats/group-answer token |
|---:|---:|
| 91320101 | +0.035716462 |
| 91320102 | +0.037377211 |
| 91320103 | +0.029746206 |
| 91320104 | +0.042160697 |
| 91320105 | +0.031524067 |
| **Equal-corpus mean** | **+0.035304929** |

Corpus SD: **0.004915780**; **5/5 corpus means positive**. Secondary reviewed
contrasts: R−S **+0.037312078**, I−U **+0.033297779**, interaction
(R−S)−(I−U) **+0.004014299**. Fresh R−U replication: total test NLL
**+0.041261750 nats/answer token**, group test NLL **+0.053229730
nats/group-answer token**. These secondary summaries use the same nested-seed
then equal-corpus weighting. Complete paired values and arm metrics remain in
[PAIRS.json](PAIRS.json); corpus contributions remain in
[CORPUS_SUMMARY.json](CORPUS_SUMMARY.json).

## Interpretation and decision

Changing instance-loss weights worsened held-out group NLL under this fixed
training algorithm, including when shared/group losses remained uniform
(I−U). This is a narrow causal intervention result for the controlled synthetic
setup and the whole specified optimization procedure. It does not identify a
mediating path or establish capacity competition, a universal weighting
disadvantage, greater overall memorization, a p* peak or a scaling curve.

Clipping rates differ materially across arms: the intervention can change
updates through clipping and AdamW as well as the raw component gradients.
Group accuracy is near ceiling, so the NLL differences must not be described
as a large group-accuracy collapse. Supporting preferential allocation is
present: the instance-factor contrast in signed instance training gains is
**+0.111726** in the high-weight quartile and **−0.110032** in the low-weight
quartile. Quartiles contain 128 sequences each, ranked by (saved weight, index).
Overall instance training loss nevertheless worsened. Preferential allocation
does not establish greater overall memorization or explain the test penalty.
The reviewed allocation summaries are supported by [ALLOCATION.json](ALLOCATION.json).

Close this bounded study and preserve all source, raw checkpoints, arrays,
traces, receipts and signed results. A further clipping/update-policy study is
**a proposal only**; this record authorizes no run, tuning, retry or seed expansion.

## Validation and provenance

Saved outer postwrite runtime: **601.933168 seconds / 1800**. Separate outer
postwrite audit: **43.409159 seconds / 600**. All prepare/pretrain/adapt/audit
phase receipts and both outer receipts report exit 0; phase child exits are
confirmed, log hashes match, and no failure marker exists. The audit reports
PASS for fifty checkpoint reevaluations, ten full input regenerations, 6400
adaptation trace rows and four-arm objective/gradient fixtures. NLL/component
tolerance was 2e-6 absolute; fixture tolerance was 1e-7. Maximum observed
discrepancies were **not recorded**; passing the checks is not evidence of zero
error. Intermediate optimization was not independently replayed.

Independent Astra result review: **PASS, no blocker**, turn
`01a105e0-9b4c-73a1-b3eb-848082796f59`, as supplied in the recording instruction
in source thread `01a0f185-4faf-7170-9912-8a162785700d`. This record preserves that
review provenance; the recorder does not impersonate the independent reviewer
or manufacture a separate review attestation. Source acceptance is retained in
`../reviews/SOURCE_REVIEW.json`.

SHA256 evidence bindings (paths relative to the v0132 bundle unless noted):

- `SOURCE_MANIFEST.json`: `9405cf967cc6d9c38453fc1994e94d4dbd525b8872e48f19fd82cfdd971141b3`
- `reviews/SOURCE_REVIEW.json`: `558beb078a39d7cb44e77fbe4bf1506ce55f03fdbc9569d3a1be0637d804b867`
- Result `AUDIT.json`: `eb8450830d571142dec2dc86740648ea26a5fdf5c2bca2bd809474902c943406`
- Result `CORPUS_SUMMARY.json`: `2c7398f4cf5e74957997636f28645055909615f44d851e822135357ef04ec627`
- Result `PAIRS.json`: `1cc3cbc5c30db816feda0e5f9f821a2cc2cbc6cbd429ffca8dd80a361a9119ae`
- `receipts/outer-runtime.exit.json`: `39ceae6b543a880ee7ce69645b14fcf00b6a97b1d5da02e0a142d8db0ae4b8ba`
- `receipts/outer-runtime.postwrite.json`: `47d6a7f58dfd7edb5e3212fa654e38fdff93f8176b4f5084c22764dd7e76a0a4`
- `receipts/outer-audit.exit.json`: `1297d7c6d57cbc60c31804562610e810f6b2d16890ba446fd563352ac0c8445c`
- `receipts/outer-audit.postwrite.json`: `00390fd2f3534d5a887abfa2b45c5df9b9f02f6c855a374b6d322689ccb0f02f`

The source manifest binds all seventeen source payloads; AUDIT.json binds the
four numerical result payloads, including allocation and corpus CSV. Recording
used Windows reads/writes and SHA256 verification only. No numerical execution,
tests, WSL, training, source changes or deletion occurred. This new narrative
postdates the audit and is not itself an audit-bound numerical output.
