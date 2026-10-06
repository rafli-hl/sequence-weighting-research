# v0133-r1 completed result and decision

4 October 2026 UTC. Status: COMPLETE. The numerical and pairing audit passed;
the independent Astra result review reported PASS with no blocking discrepancy.
The scientific practical interaction criterion failed. These are separate decisions.
No further experiment, tuning, retry, seed expansion or execution is authorized.

The study remains v0133, source revision r1, successful attempt 20261004-02.
The original v0133 attempt failed during module loading before data generation.
Its source, attestation, failure latch and receipts remain intact. Revision r1
added one `import torch` before StepSnapshot decorators, routed a distinct attempt
and preserved the frozen science. FAILED_ATTEMPT_BINDINGS.json binds all 41
original files; Windows recording checks found them unchanged.

Five fresh G1 corpora and two nested model/weight seeds per corpus supplied ten
shared U-pretrained checkpoints and forty matched Uclip/Iclip/Unoclip/Inoclip
adaptations. Width128/depth3/F10, LR1e-4, WD0.1, batch32 and equal component
coefficients were fixed. Clipped arms used clip1; unclipped arms used no clipping.
Tokens, labels, teacher-forced context, initial checkpoints, batch orders and
random instance-weight assignments were matched. Shared/group weights were one.
Five corpora, rather than ten model seeds, are the replication units.

The primary contrast is D=(Iclip-Uclip)-(Inoclip-Unoclip), using group-token test
NLL. Two seed contrasts are averaged within each corpus, then five corpus means
equally. Positive D means a more adverse instance-weighting effect under clip1.
The frozen practical criterion required mean D>=0.01 nats AND all five corpus
means positive; this was not a significance test.

CORPUS_SUMMARY.json records mean D **+0.0007437080144882202 nats/group answer
token**, corpus SD **0.001968223783821887**, range **-0.0014055408537387848 to
+0.002910800278186798**, and **3/5 positive** corpus means. Both parts of the
criterion failed; verdict: `practical_interaction_not_supported`.

| Corpus seed | D | Iclip-Uclip | Inoclip-Unoclip | Unoclip own-baseline group gain |
|---|---:|---:|---:|---:|
| 91420101 | +0.001745963 | +0.032791965 | +0.031046001 | +2.735308429 |
| 91420102 | +0.001759313 | +0.028126065 | +0.026366752 | +2.731982704 |
| 91420103 | +0.002910800 | +0.029685229 | +0.026774429 | +2.733415212 |
| 91420104 | -0.001291996 | +0.037533477 | +0.038825473 | +2.749577733 |
| 91420105 | -0.001405541 | +0.031588037 | +0.032993577 | +2.738964312 |

All entries use nats/group answer token. Exact values and every nested seed remain
in CORPUS_SUMMARY.json and PAIRS.json, including unfavorable signs. No corpus
was excluded or replaced. The two conditional mean penalties are
**+0.03194495439529419** with clip1 and **+0.03120124638080597** without clipping;
both are positive in all five corpus means. Unoclip adequacy passed in all five
corpora: own-baseline group gains range from +2.731982704 to +2.749577733,
mean +2.737849678. The no-clip control therefore learned the group rule under
the frozen adequacy definition; the interaction verdict is not an inadequacy case.

Removing clip1 did not remove the conditional group-NLL penalty in this design.
This weakens a clipping-only explanation of that penalty. It does not establish
policy equivalence, zero clipping effect, statistical significance, mediation,
capacity competition, or a universal mechanism. D is a continuous signed result,
not evidence of equivalence merely because it is small and mixed. This study is
not a clipping-policy tuning exercise and does not reopen historical v0130.

Secondary allocation in ALLOCATION.json uses fixed extreme quartiles sorted by
(saved weight, sequence index), 128 sequences per extreme. Its signed I-versus-U
training gain is U NLL minus I NLL. Under both clipping policies, high-weight
instance quartile gains are positive and low-weight gains negative in all ten
paired seeds. This is preferential instance allocation, not increased overall
memorization. The unweighted mean instance training NLL from PAIRS.json is:

| Policy | Uniform | Random instance weights |
|---|---:|---:|
| Clip1 | 2.730193233 | 2.791167092 |
| No clip | 2.741701984 | 2.801520944 |

The random-instance arms have worse overall instance training NLL despite their
preferential fit on high-weight items. These secondary means equally average the
ten balanced seed pairs; they do not increase the dataset replication count.
Training allocation alone does not identify what mediates the group penalty.

Actual-step logs are descriptive secondary evidence. Across the balanced ten
pairs, mean parameter-step L2 is 0.028111400/0.028134425 for Uclip/Iclip and
0.025675823/0.027882810 for Unoclip/Inoclip. Mean relative step L2 is
0.000818150/0.000818941 and 0.000747478/0.000811511 respectively. Mean clipping
fractions are 0.464375 for Uclip and 0.90875 for Iclip; no-clip fractions are zero.
Large clipping-rate differences coexist with similar clipped mean step norms.
Norms do not establish equal update directions, moment histories, per-component
contributions or learning efficiency. They do not prove a pathway or mediation.
The audit checks saved-step arithmetic and fixtures; it does not independently
replay intermediate research optimizer updates from retained intermediate states.

AUDIT.json reports PASS_NUMERICAL_AND_PAIRING_AUDIT: 50 checkpoint reevaluations,
10 full input regenerations, 6400 adaptation update rows, ten matched seed rows,
five corpus rows, forty trajectories and 14494 discrepancy checks. Objective/
gradient, step snapshot, clipping, zero-norm guard and nonfinite fixtures passed.
Recorded maxima by tolerance are:

| Tolerance | Maximum discrepancy |
|---:|---:|
| 1e-12 | 0 |
| 1e-9 | 6.006306563222097e-14 |
| 1e-7 | 8.881784197001252e-16 |
| 2e-6 NLL | 4.76837158203125e-7 |
| 0.001 clip-gradient norm | 1.4668231870018644e-5 |

Outer runtime was **713.688033843 seconds** through postwrite, within1798.
Adding the conservatively charged2 seconds for the preserved failed attempt gives
**715.688033843/1800 seconds**. Audit was **57.535809384/600 seconds** through
postwrite. All phase and outer exits were zero. Saved containment receipts confirm
group disappearance, no survivors, wrapper reaping and zero cancellation for
both completed modes. No current r1 failure latch exists. The runtime gate's
combined rounded allocation was148.328125MiB with80MiB archive/terminal reserves
and5.166622GiB free; the small audit outputs and these records remain subject to
the unchanged512MiB/2GiB constraints. The recording-time Windows storage check
projected148.484375MiB including these records and found more than5.16GiB free;
including the80MiB reserves remains below512MiB. No unused budget authorizes
another run.

Provenance and bindings, verified from saved Windows files:

- Source manifest SHA256:
  `baf8a3de3aab342b842f8d2fc0ce4b1899cf77b6e58987745df9d64b27ab5ab3`.
- Independent r1 source attestation SHA256:
  `1458216638d8c118f161bfe9beac7d5ec9fdfdffba8a8808cafa4c933b6b42df`.
- [AUDIT.json](AUDIT.json) SHA256:
  `915ecc81692fd6f7f7aba52f80d55af66e563139e6a64ae1e54b75ba89a16078`.
- [CORPUS_SUMMARY.json](CORPUS_SUMMARY.json) SHA256:
  `92f3fa92003ab391b8d64982e97616f2a7e828cd6e2703df8bd258a35615e2b9`.
- [PAIRS.json](PAIRS.json) SHA256:
  `996e2a14368931a84ab5ef15444adf8151d70d7daec25b279566f2243f01cc26`.
- [ALLOCATION.json](ALLOCATION.json) SHA256:
  `20493022efaa9b153f7431b22c9e01334c4e005f73094da0cd6c01b8814b802b`.
- Outer runtime exit/postwrite SHA256:
  `c21a65365a5ffd71a3b441e5301726bcf544eb8ae12cc200691d4cf45f554f68` /
  `ecb99c768a931b10fcd22110deadd27db42e7e375b6c4aa8648e4b34075fbd2e`.
- Outer audit exit/postwrite SHA256:
  `e6606ceea68ae7eb7e99f8f64610a4a01d517ea3ed45a5c7bbbd587ebdffb39e` /
  `e3231a359369c9933e258f9df158f90f3e483e1ad6ab1093a556139fe335426d`.
- Independent Astra result review provenance: turn
  `01a1071e-967b-7735-8efd-3fa513484b5e`; the parent delegation communicated PASS
  with no blocking discrepancy. This is conversation-level provenance; no local
  result-review attestation file was present when these records were written.

Decision: close v0133-r1 as an audited study with an unsupported practical
interaction criterion and persistent adverse conditional group-NLL effects.
The next question worth formulating is which aspects of update direction,
optimizer preconditioning/state or shared representations carry the remaining
penalty. That is a question, not an identified mechanism or an approved protocol.
Any follow-up requires its own frozen design, independent review and explicit
authorization. No peak criterion, tuning, favorable-outcome search or adaptive
seed growth follows from this record.
