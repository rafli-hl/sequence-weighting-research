# G1 adaptation clipping diagnostic: decision record

3 October 2026 UTC. This records the completed **prospective diagnostic on five previously seen corpora**. It is neither a fresh confirmation nor a new training protocol. Preserve the frozen v0128 and v0130 source and raw results. The canonical comparison remains the existing G1/random F10 **clip-1** control; the no-clip arm is a diagnostic, not a replacement policy.

## Evidence and status

The exact v0130 source manifest is `outputs/g1-clipping-diagnostic-v0130/MANIFEST.txt` (SHA256 `f1337c49f20a8c457805f83918000717ba48e4f38f2cb5cd5e1c0302b62002a0`). The independent *source* review `<LOCAL_USER_HOME>/Documents/Codex/2026-10-01/task/SOURCE_REVIEW_G1_CLIPPING_V0130_20261003-01.md` (SHA256 `2a97ca56ad29b3a8884f0018394ba5407a44a564e01e76314f19fd8659fb86d1`) concluded `PASS_STATIC_SOURCE_REVIEW_FOR_BOUNDED_LAUNCH_CONSIDERATION`. That review did not certify new scientific outcomes.

The frozen input plan is `work/runs/g1-noclip-v0130-20261003-01/plan.json` (SHA256 `a9e7441d228cc13afea841dad59194a1ce144b338da52af5ffe29620bbb73824`). `TRAINING_COMPLETE.json` in that run (SHA256 `919a7c3c46e06a7b5156f60f26836129ac3018dcb0d95a374b243e5df30a1a19`) reports 30 complete trajectories. The original terminal receipts are `outputs/g1-clipping-diagnostic-v0130/receipts/training.*` and `analysis.*`; both saved exit codes are zero, log hashes/sizes match, and neither phase has a failure marker. Training terminal time was 911 s versus a 1200 s ceiling; analysis terminal time was 183 s versus 600 s. All 30 result directories and F10 binaries exist. Read-only verification checked 520 source/input/result bindings with zero mismatches. Raw run plus output and 64 MiB archive/2 MiB terminal-receipt reserves totaled about 239.8 MB against the 512 MiB allowance; measured remaining D: free space was about 5.85 GB, above the 2 GiB reserve. No archive was created here.

The numerical report is `outputs/g1-clipping-diagnostic-v0130/results/AUDIT_AND_ANALYSIS.json` (SHA256 `2a2d0154d4779c262d5921372db6f73c3cd816c20090c0d7eb22f3a7c055bf64`). Its saved, pre-review status is `CANDIDATE_RAW_ARRAY_AUDIT_PASS_PENDING_INDEPENDENT_REVIEW`: 30/30 runs audited at epochs 0, 1, 3, 5, 10, with 160 updates per run and no listed failures. A separate independent **numerical result review completed at 15:46 UTC** (review thread `01a0f36f-6b34-72f7-8592-bcf656ff10bf`, turn `01a1026b-c7be-74c7-accc-5bbb538d8da6`) concluded: “Independent result review passes within the requested read-only scope. The frozen scientific success criterion fails. No blocking discrepancy was found.” The reviewer reconciled the summary against all 30 new and 30 historical F10 histories, recorded bindings, five primary corpus means, all ten paired K calculations, ten source hashes, and saved residual mean squares for 261 defined objectives. This review was read-only, with no new numerical execution. The original candidate status in the immutable JSON is retained as provenance, not as the current review status.

## Frozen primary decision

For width 128, the paired value is clip-1 F10 validation NLL minus no-clip F10 validation NLL. Average the two nested model/weight seeds *inside each corpus*, then average the five corpus values. Practical success required overall mean >= +0.01 nat, every corpus difference positive, and positive mean no-clip own-baseline test gain in every corpus. Neither p* nor K enters this decision.

| Corpus seed | Validation difference, clip minus no-clip | No-clip own-baseline test gain | Delta K, no-clip minus clip |
|---:|---:|---:|---:|
| 88547 | -0.007155 | +0.879424 | +0.021197 |
| 88771 | -0.004328 | +0.867788 | +0.011836 |
| 88993 | -0.006925 | +0.854452 | +0.019525 |
| 89203 | -0.008653 | +0.856004 | +0.016715 |
| 89431 | -0.003778 | +0.871588 | +0.011121 |
| **Five-corpus mean** | **-0.006168** | **+0.865851** | **+0.016079** |

The test-gain guard passes all five corpora. The validation threshold and all-five-positive condition both fail: no clipping has *higher* validation NLL at width 128. The frozen practical criterion is **not met**. Do not choose no clipping from its positive delta K.

## Secondary behavior and interpretation

| Width | Mean p* clip / no-clip | Mean validation difference | Clip-1 clipped-update fraction | Mean no-clip fit objective |
|---:|---:|---:|---:|---:|
| 64 | 0.03260 / 0.02983 | +0.07645 | 1.00000 | 0.0000342 |
| 128 | 0.01774 / 0.01908 | -0.00617 | 0.96875 | 0.0000152 |
| 256 | 0.06441 / 0.04911 | +0.02727 | 0.99375 | 0.0000822 |

At widths 64 and 256, no clipping improves mean validation NLL relative to clip-1, while at 128 it worsens it. This is a capacity-dependent response *within the fixed ten-epoch setup*, not evidence for a generally optimal clipping policy. At width 128 no-clip F10, mean train/validation/test NLL is 0.98068/1.01095/1.01199. Mean group training accuracy is 99.99% and instance training accuracy 7.34%; mean test component losses (shared/group/instance) are 0.06019/0.09847/2.87730. The training group pattern is nearly memorized, while instance learning remains weak.

For each corpus/seed, K is p*(128) minus the larger endpoint p*. All 10 K values are defined and negative in **both** arms; mean K is -0.04666 with clip-1 and -0.03058 without clipping. Positive delta K means a smaller negative curvature, not a surviving middle peak. No p* values were undefined in these 30 pairs. The separate arithmetic audit checks signed gains, guards, component identity, stored residuals, bounded fit objectives and new F10 binary-to-array equality. Its independent reference search provides a one-sided bounded objective check, **not** a global optimum certificate, precise p agreement or proof of statistical fit adequacy. Fit objectives should accompany any p* discussion.

Five corpus draws, not ten nested seeds, are the dataset replication units. These corpora were already seen in v0128, so this result is an exploratory optimization diagnostic. Three capacities cannot establish an interior-to-interior peak shift. Synthetic results do not replicate large-LM behavior. The GPU runtime followed the recorded v0128 seeded setup with deterministic algorithms disabled; exact bitwise backward reproducibility is not claimed.

## Research decision and proposed next step

**Verified within the saved audit and independent read-only result review:** disabling adaptation clipping alone does not satisfy the fixed width-128 validation criterion; retain clip-1 as the canonical G1 F10 control and report the opposite-sign effects at the other two widths. The completed no-clip run should be treated as a boundary-condition result, including its null primary verdict and negative K values.

**Next research recommendation is being finalized separately; no next experiment is approved or launched by this record.** Do not tune on p*, positive K, visible peak or test loss; do not infer a new clipping setting from this diagnostic. Recheck primary literature before any novelty claim.
