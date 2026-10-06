<a name="stage-6-v07--replikasi-panel-tuning-untuk-kebijakan-tanpa-adaptasi"></a>

# Stage 6 v0.7 — tuning-panel replication of no-adaptation selection

Run `stability-v07-20260929-01`: **576 tuning + 216 confirmation trajectories**, **102 pretrained models**, and **54 initial test evaluations**. Four fresh tuning panels share the same confirmation corpora.

<a name="1-hasil-utama"></a>

## 1. Main result

For **U / R / random**, the largest capacity selected no adaptation in **3/4 panels**. The useful-adaptation criterion for the middle capacity passed in **0/4 panels**. These are descriptive frequencies across four panels; no new threshold assigns a binary “stable” label, and no significance test was performed.

| Panel | Largest epoch 0 | Middle update>0 | 3 corpora Δtest>0 | 3 corpora val≤initial | Middle useful | Globally useful | Scaling | K verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | True | True | False | False | False | False | False | inconclusive_undefined |
| P2 | True | False | False | True | False | False | True | inconclusive_undefined |
| P3 | True | False | False | True | False | False | True | inconclusive_undefined |
| P4 | False | True | False | False | False | False | False | inconclusive_undefined |

Δtest = initial test NLL − selected test NLL. Utility at one capacity requires nonzero updates, positive mean Δtest in every corpus, and mean validation NLL no worse than the initial model in every corpus. Epoch 0 gives exactly zero delta and undefined p*. Scaling is a separate gate: test NLL must decrease strictly with capacity and validation NLL must be ≤initial across all capacities/corpora.

**Replication design:** 4 tuning panels × **the same 3 confirmation corpora**, each with 3 nested model/weight seeds. The 12 panel×corpus cells are not 12 independent corpora, and the 36 pairs per capacity are not 36 independent dataset replications. Identical selected configurations reuse the same confirmation checkpoints. No panel was selected using test results, p*, or peaks.

<a name="2-seluruh-keputusan-validation-dan-frekuensinya"></a>

## 2. All validation decisions and their frequencies

R selects random-weight validation NLL; J selects the joint random/uniform result. Each panel uses two separate tuning corpus/model pairs. Panel variation includes tuning data, model/weight seeds, and pretraining data; it does not isolate the tuning-corpus effect alone. The canonical epoch 0 candidate is compared with six optimizers×six epochs; ties use full precision, earliest epoch, then smallest LR and WD.

| Selector | Condition | Width | Epoch 0 /4 | Setting frequency (grid/epoch: panel) |
| --- | --- | --- | --- | --- |
| R | M | 64 | 0 | g4/e30: 4/4 (P1,P2,P3,P4) |
| R | M | 128 | 0 | g5/e20: 4/4 (P1,P2,P3,P4) |
| R | M | 256 | 0 | g4/e10: 2/4 (P3,P4); g5/e10: 2/4 (P1,P2) |
| R | U | 64 | 0 | g4/e5: 1/4 (P4); g4/e10: 3/4 (P1,P2,P3) |
| R | U | 128 | 2 | gNone/e0: 2/4 (P2,P3); g4/e3: 1/4 (P1); g0/e20: 1/4 (P4) |
| R | U | 256 | 3 | gNone/e0: 3/4 (P1,P2,P3); g0/e10: 1/4 (P4) |
| J | M | 64 | 0 | g4/e30: 4/4 (P1,P2,P3,P4) |
| J | M | 128 | 0 | g4/e20: 3/4 (P1,P3,P4); g5/e20: 1/4 (P2) |
| J | M | 256 | 0 | g4/e10: 3/4 (P1,P3,P4); g5/e10: 1/4 (P2) |
| J | U | 64 | 0 | g4/e10: 1/4 (P4); g4/e20: 3/4 (P1,P2,P3) |
| J | U | 128 | 0 | g4/e5: 1/4 (P4); g2/e10: 1/4 (P2); g4/e10: 2/4 (P1,P3) |
| J | U | 256 | 1 | gNone/e0: 1/4 (P1); g4/e5: 1/4 (P4); g2/e10: 1/4 (P3); g0/e20: 1/4 (P2) |

![All selections](selection-panels.png)

All candidate scores, LR/WD settings, selections, and the confirmation union were frozen in `selection.json`. Identical settings/aliases are retained in `panel-summary.json`. The optimizer union was run in both arms through epoch 30; all six declared checkpoints were evaluated, without confirmation-based reselection.

<a name="3-matriks-gain-silang-dan-dua-marginal-terpisah"></a>

## 3. Crossed gain matrix and two separate margins

Each cell is the mean of three seeds for a panel/corpus pair. “Panel SD” is the SD of four panel margins after averaging over three corpora; “corpus SD” is the SD of three corpus margins after averaging over four panels. They measure different sources of variation, rather than standard errors/CIs or estimates assuming all cells are independent. No pooled SD over 12 cells/36 pairs is used for inference.

| Width | Δtest grand mean | Panel-margin SD (n=4) | Corpus-margin SD (n=3) | Unique checkpoint sources /36 |
| --- | --- | --- | --- | --- |
| 64 | 0.032417 | 0.001974 | 0.005521 | 18 |
| 128 | 0.000460 | 0.000531 | 0.001128 | 27 |
| 256 | -0.000356 | 0.000712 | 0.000243 | 18 |

![Crossed primary gains](crossed-gains.png)

![Panel utility](utility-panels.png)

`crossed-summary.json` retains the matrix, each margin, all 36 paired values, and checkpoint references. `policy-cells.csv` retains losses/accuracies for all components, clipping, gains, p*, and undefined reasons for every policy.

<a name="4-semua-kebijakan-dan-kualitas-fit"></a>

## 4. All policies and fit quality

| Panel | Policy | Arm | Useful global | Scaling | K mean | Undefined K /9 | K positive /9 | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | M_R | random | True | True | 0.001486 | 0 | 5 | mixed/inconclusive |
| P1 | M_R | uniform | True | True | undefined | 9 | 0 | undefined_uniform |
| P1 | U_R | random | False | False | undefined | 9 | 0 | inconclusive_undefined |
| P1 | U_R | uniform | False | True | undefined | 9 | 0 | undefined_uniform |
| P1 | M_J | random | True | True | 0.004848 | 0 | 7 | mixed/inconclusive |
| P1 | M_J | uniform | True | True | undefined | 9 | 0 | undefined_uniform |
| P1 | U_J | random | False | False | undefined | 9 | 0 | inconclusive_undefined |
| P1 | U_J | uniform | False | False | undefined | 9 | 0 | undefined_uniform |
| P2 | M_R | random | True | True | 0.001486 | 0 | 5 | mixed/inconclusive |
| P2 | M_R | uniform | True | True | undefined | 9 | 0 | undefined_uniform |
| P2 | U_R | random | False | True | undefined | 9 | 0 | inconclusive_undefined |
| P2 | U_R | uniform | False | True | undefined | 9 | 0 | undefined_uniform |
| P2 | M_J | random | True | True | 0.001486 | 0 | 5 | mixed/inconclusive |
| P2 | M_J | uniform | True | True | undefined | 9 | 0 | undefined_uniform |
| P2 | U_J | random | False | False | undefined | 1 | 2 | inconclusive_undefined |
| P2 | U_J | uniform | True | True | undefined | 9 | 0 | undefined_uniform |
| P3 | M_R | random | True | True | 0.001486 | 0 | 5 | mixed/inconclusive |
| P3 | M_R | uniform | True | True | undefined | 9 | 0 | undefined_uniform |
| P3 | U_R | random | False | True | undefined | 9 | 0 | inconclusive_undefined |
| P3 | U_R | uniform | False | True | undefined | 9 | 0 | undefined_uniform |
| P3 | M_J | random | True | True | 0.004848 | 0 | 7 | mixed/inconclusive |
| P3 | M_J | uniform | True | True | undefined | 9 | 0 | undefined_uniform |
| P3 | U_J | random | False | False | -0.978110 | 0 | 3 | mixed/inconclusive |
| P3 | U_J | uniform | True | False | undefined | 9 | 0 | undefined_uniform |
| P4 | M_R | random | True | True | 0.001486 | 0 | 5 | mixed/inconclusive |
| P4 | M_R | uniform | True | True | undefined | 9 | 0 | undefined_uniform |
| P4 | U_R | random | False | False | undefined | 1 | 0 | inconclusive_undefined |
| P4 | U_R | uniform | True | True | undefined | 9 | 0 | undefined_uniform |
| P4 | M_J | random | True | True | 0.004848 | 0 | 7 | mixed/inconclusive |
| P4 | M_J | uniform | True | True | undefined | 9 | 0 | undefined_uniform |
| P4 | U_J | random | False | False | -1.270858 | 0 | 1 | disappears |
| P4 | U_J | uniform | True | True | undefined | 9 | 0 | undefined_uniform |

K = middle-capacity p* − max(small-capacity p*, large-capacity p*). Every undefined value propagates into means and contrasts. Uniform-weight p* is always undefined. Three capacities cannot establish movement between two interior peaks.

| Panel | Condition / R random | Width | Epoch | p* mean | Undefined /9 | Upper boundary /9 | Objective mean | Cancellation mean | Negative Δtest /9 | Negative Δvalidation /9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | M | 64 | 30 | 0.041994 | 0 | 0 | 0.000054 | 1.000000 | 0 | 0 |
| P1 | M | 128 | 20 | 0.043480 | 0 | 0 | 0.000054 | 1.000000 | 0 | 0 |
| P1 | M | 256 | 10 | 0.025852 | 0 | 0 | 0.000021 | 1.000000 | 0 | 0 |
| P1 | U | 64 | 10 | 0.354999 | 0 | 0 | 0.000957 | 0.775695 | 0 | 0 |
| P1 | U | 128 | 3 | 1.590241 | 0 | 0 | 0.079808 | 0.303125 | 4 | 4 |
| P1 | U | 256 | 0 | undefined | 9 | 0 | undefined | undefined | 0 | 0 |
| P2 | M | 64 | 30 | 0.041994 | 0 | 0 | 0.000054 | 1.000000 | 0 | 0 |
| P2 | M | 128 | 20 | 0.043480 | 0 | 0 | 0.000054 | 1.000000 | 0 | 0 |
| P2 | M | 256 | 10 | 0.025852 | 0 | 0 | 0.000021 | 1.000000 | 0 | 0 |
| P2 | U | 64 | 10 | 0.354999 | 0 | 0 | 0.000957 | 0.775695 | 0 | 0 |
| P2 | U | 128 | 0 | undefined | 9 | 0 | undefined | undefined | 0 | 0 |
| P2 | U | 256 | 0 | undefined | 9 | 0 | undefined | undefined | 0 | 0 |
| P3 | M | 64 | 30 | 0.041994 | 0 | 0 | 0.000054 | 1.000000 | 0 | 0 |
| P3 | M | 128 | 20 | 0.043480 | 0 | 0 | 0.000054 | 1.000000 | 0 | 0 |
| P3 | M | 256 | 10 | 0.026718 | 0 | 0 | 0.000022 | 1.000000 | 0 | 0 |
| P3 | U | 64 | 10 | 0.354999 | 0 | 0 | 0.000957 | 0.775695 | 0 | 0 |
| P3 | U | 128 | 0 | undefined | 9 | 0 | undefined | undefined | 0 | 0 |
| P3 | U | 256 | 0 | undefined | 9 | 0 | undefined | undefined | 0 | 0 |
| P4 | M | 64 | 30 | 0.041994 | 0 | 0 | 0.000054 | 1.000000 | 0 | 0 |
| P4 | M | 128 | 20 | 0.043480 | 0 | 0 | 0.000054 | 1.000000 | 0 | 0 |
| P4 | M | 256 | 10 | 0.026718 | 0 | 0 | 0.000022 | 1.000000 | 0 | 0 |
| P4 | U | 64 | 5 | 0.187629 | 0 | 0 | 0.000717 | 0.873643 | 0 | 0 |
| P4 | U | 128 | 20 | 1.767128 | 0 | 1 | 0.522528 | 0.346585 | 3 | 4 |
| P4 | U | 256 | 10 | undefined | 1 | 0 | undefined | 0.178036 | 7 | 7 |

P* uses the original signed gains and search range [0,8]. Nonpositive/below-guard gains, no adaptation, and uniform weights remain undefined. Cancellation ratio = |Σgain|/Σ|gain|, undefined when all gains are zero. Boundary values and poor objectives limit interpretation, without filtering or changing the estimator range. Objective figures retain every point; a mean is omitted if even one value is undefined.

![Selected fits](selected-fits.png)

| Panel | Policy | Arm | Width | Train NLL | Validation NLL | Test NLL | Instance train accuracy | Clipping |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | M_R | random | 64 | 2.011199 | 2.083453 | 2.083173 | 0.061903 | 0.999537 |
| P1 | M_R | random | 128 | 1.895633 | 2.052223 | 2.055430 | 0.097439 | 1.000000 |
| P1 | M_R | random | 256 | 1.872513 | 2.021971 | 2.023664 | 0.097005 | 0.999306 |
| P1 | M_R | uniform | 64 | 1.852419 | 1.889731 | 1.889937 | 0.060167 | 1.000000 |
| P1 | M_R | uniform | 128 | 1.657434 | 1.820907 | 1.828682 | 0.108127 | 0.988542 |
| P1 | M_R | uniform | 256 | 1.644342 | 1.797141 | 1.799880 | 0.101780 | 0.979167 |
| P1 | U_R | random | 64 | 1.942249 | 1.970811 | 1.968145 | 0.063802 | 0.837500 |
| P1 | U_R | random | 128 | 1.864235 | 1.875611 | 1.873763 | 0.067708 | 0.553241 |
| P1 | U_R | random | 256 | 1.853060 | 1.853307 | 1.853035 | 0.059570 | undefined |
| P1 | U_R | uniform | 64 | 1.883992 | 1.920835 | 1.919574 | 0.065538 | 0.305556 |
| P1 | U_R | uniform | 128 | 1.843923 | 1.860525 | 1.859850 | 0.063965 | 0.004630 |
| P1 | U_R | uniform | 256 | 1.853060 | 1.853307 | 1.853035 | 0.059570 | undefined |
| P1 | M_J | random | 64 | 2.011199 | 2.083453 | 2.083173 | 0.061903 | 0.999537 |
| P1 | M_J | random | 128 | 1.883436 | 2.053874 | 2.056882 | 0.102756 | 1.000000 |
| P1 | M_J | random | 256 | 1.868023 | 2.023083 | 2.024719 | 0.098470 | 0.999306 |
| P1 | M_J | uniform | 64 | 1.852419 | 1.889731 | 1.889937 | 0.060167 | 1.000000 |
| P1 | M_J | uniform | 128 | 1.639574 | 1.816004 | 1.824511 | 0.110623 | 0.988889 |
| P1 | M_J | uniform | 256 | 1.636828 | 1.795166 | 1.797960 | 0.102322 | 0.979861 |
| P1 | U_J | random | 64 | 1.906937 | 1.977880 | 1.977050 | 0.077908 | 0.917014 |
| P1 | U_J | random | 128 | 1.817535 | 1.924021 | 1.920742 | 0.091797 | 0.829861 |
| P1 | U_J | random | 256 | 1.853060 | 1.853307 | 1.853035 | 0.059570 | undefined |
| P1 | U_J | uniform | 64 | 1.769847 | 1.871438 | 1.874475 | 0.090712 | 0.652083 |
| P1 | U_J | uniform | 128 | 1.660197 | 1.801971 | 1.802937 | 0.097059 | 0.543056 |
| P1 | U_J | uniform | 256 | 1.853060 | 1.853307 | 1.853035 | 0.059570 | undefined |
| P2 | M_R | random | 64 | 2.011199 | 2.083453 | 2.083173 | 0.061903 | 0.999537 |
| P2 | M_R | random | 128 | 1.895633 | 2.052223 | 2.055430 | 0.097439 | 1.000000 |
| P2 | M_R | random | 256 | 1.872513 | 2.021971 | 2.023664 | 0.097005 | 0.999306 |
| P2 | M_R | uniform | 64 | 1.852419 | 1.889731 | 1.889937 | 0.060167 | 1.000000 |
| P2 | M_R | uniform | 128 | 1.657434 | 1.820907 | 1.828682 | 0.108127 | 0.988542 |
| P2 | M_R | uniform | 256 | 1.644342 | 1.797141 | 1.799880 | 0.101780 | 0.979167 |
| P2 | U_R | random | 64 | 1.942249 | 1.970811 | 1.968145 | 0.063802 | 0.837500 |
| P2 | U_R | random | 128 | 1.874796 | 1.874900 | 1.874668 | 0.059570 | undefined |
| P2 | U_R | random | 256 | 1.853060 | 1.853307 | 1.853035 | 0.059570 | undefined |
| P2 | U_R | uniform | 64 | 1.883992 | 1.920835 | 1.919574 | 0.065538 | 0.305556 |
| P2 | U_R | uniform | 128 | 1.874796 | 1.874900 | 1.874668 | 0.059570 | undefined |
| P2 | U_R | uniform | 256 | 1.853060 | 1.853307 | 1.853035 | 0.059570 | undefined |
| P2 | M_J | random | 64 | 2.011199 | 2.083453 | 2.083173 | 0.061903 | 0.999537 |
| P2 | M_J | random | 128 | 1.895633 | 2.052223 | 2.055430 | 0.097439 | 1.000000 |
| P2 | M_J | random | 256 | 1.872513 | 2.021971 | 2.023664 | 0.097005 | 0.999306 |
| P2 | M_J | uniform | 64 | 1.852419 | 1.889731 | 1.889937 | 0.060167 | 1.000000 |
| P2 | M_J | uniform | 128 | 1.657434 | 1.820907 | 1.828682 | 0.108127 | 0.988542 |
| P2 | M_J | uniform | 256 | 1.644342 | 1.797141 | 1.799880 | 0.101780 | 0.979167 |
| P2 | U_J | random | 64 | 1.906937 | 1.977880 | 1.977050 | 0.077908 | 0.917014 |
| P2 | U_J | random | 128 | 1.859120 | 1.879952 | 1.877507 | 0.065484 | 0.602083 |
| P2 | U_J | random | 256 | 1.837861 | 1.864012 | 1.863650 | 0.070909 | 0.770139 |
| P2 | U_J | uniform | 64 | 1.769847 | 1.871438 | 1.874475 | 0.090712 | 0.652083 |
| P2 | U_J | uniform | 128 | 1.821501 | 1.852289 | 1.851388 | 0.067112 | 0.030556 |
| P2 | U_J | uniform | 256 | 1.776507 | 1.827405 | 1.827861 | 0.072049 | 0.140972 |
| P3 | M_R | random | 64 | 2.011199 | 2.083453 | 2.083173 | 0.061903 | 0.999537 |
| P3 | M_R | random | 128 | 1.895633 | 2.052223 | 2.055430 | 0.097439 | 1.000000 |
| P3 | M_R | random | 256 | 1.868023 | 2.023083 | 2.024719 | 0.098470 | 0.999306 |
| P3 | M_R | uniform | 64 | 1.852419 | 1.889731 | 1.889937 | 0.060167 | 1.000000 |
| P3 | M_R | uniform | 128 | 1.657434 | 1.820907 | 1.828682 | 0.108127 | 0.988542 |
| P3 | M_R | uniform | 256 | 1.636828 | 1.795166 | 1.797960 | 0.102322 | 0.979861 |
| P3 | U_R | random | 64 | 1.942249 | 1.970811 | 1.968145 | 0.063802 | 0.837500 |
| P3 | U_R | random | 128 | 1.874796 | 1.874900 | 1.874668 | 0.059570 | undefined |
| P3 | U_R | random | 256 | 1.853060 | 1.853307 | 1.853035 | 0.059570 | undefined |
| P3 | U_R | uniform | 64 | 1.883992 | 1.920835 | 1.919574 | 0.065538 | 0.305556 |
| P3 | U_R | uniform | 128 | 1.874796 | 1.874900 | 1.874668 | 0.059570 | undefined |
| P3 | U_R | uniform | 256 | 1.853060 | 1.853307 | 1.853035 | 0.059570 | undefined |
| P3 | M_J | random | 64 | 2.011199 | 2.083453 | 2.083173 | 0.061903 | 0.999537 |
| P3 | M_J | random | 128 | 1.883436 | 2.053874 | 2.056882 | 0.102756 | 1.000000 |
| P3 | M_J | random | 256 | 1.868023 | 2.023083 | 2.024719 | 0.098470 | 0.999306 |
| P3 | M_J | uniform | 64 | 1.852419 | 1.889731 | 1.889937 | 0.060167 | 1.000000 |
| P3 | M_J | uniform | 128 | 1.639574 | 1.816004 | 1.824511 | 0.110623 | 0.988889 |
| P3 | M_J | uniform | 256 | 1.636828 | 1.795166 | 1.797960 | 0.102322 | 0.979861 |
| P3 | U_J | random | 64 | 1.906937 | 1.977880 | 1.977050 | 0.077908 | 0.917014 |
| P3 | U_J | random | 128 | 1.817535 | 1.924021 | 1.920742 | 0.091797 | 0.829861 |
| P3 | U_J | random | 256 | 1.826847 | 1.875293 | 1.874707 | 0.075358 | 0.811111 |
| P3 | U_J | uniform | 64 | 1.769847 | 1.871438 | 1.874475 | 0.090712 | 0.652083 |
| P3 | U_J | uniform | 128 | 1.660197 | 1.801971 | 1.802937 | 0.097059 | 0.543056 |
| P3 | U_J | uniform | 256 | 1.733825 | 1.809617 | 1.811172 | 0.086426 | 0.279167 |
| P4 | M_R | random | 64 | 2.011199 | 2.083453 | 2.083173 | 0.061903 | 0.999537 |
| P4 | M_R | random | 128 | 1.895633 | 2.052223 | 2.055430 | 0.097439 | 1.000000 |
| P4 | M_R | random | 256 | 1.868023 | 2.023083 | 2.024719 | 0.098470 | 0.999306 |
| P4 | M_R | uniform | 64 | 1.852419 | 1.889731 | 1.889937 | 0.060167 | 1.000000 |
| P4 | M_R | uniform | 128 | 1.657434 | 1.820907 | 1.828682 | 0.108127 | 0.988542 |
| P4 | M_R | uniform | 256 | 1.636828 | 1.795166 | 1.797960 | 0.102322 | 0.979861 |
| P4 | U_R | random | 64 | 1.963446 | 1.974020 | 1.972093 | 0.061035 | 0.718056 |
| P4 | U_R | random | 128 | 1.864933 | 1.875116 | 1.873733 | 0.064562 | 0.524306 |
| P4 | U_R | random | 256 | 1.849602 | 1.854793 | 1.854459 | 0.069770 | 0.720833 |
| P4 | U_R | uniform | 64 | 1.942332 | 1.955209 | 1.953842 | 0.059625 | 0.013889 |
| P4 | U_R | uniform | 128 | 1.845505 | 1.862475 | 1.861632 | 0.061632 | 0.001389 |
| P4 | U_R | uniform | 256 | 1.840776 | 1.848888 | 1.849231 | 0.066840 | 0.011111 |
| P4 | M_J | random | 64 | 2.011199 | 2.083453 | 2.083173 | 0.061903 | 0.999537 |
| P4 | M_J | random | 128 | 1.883436 | 2.053874 | 2.056882 | 0.102756 | 1.000000 |
| P4 | M_J | random | 256 | 1.868023 | 2.023083 | 2.024719 | 0.098470 | 0.999306 |
| P4 | M_J | uniform | 64 | 1.852419 | 1.889731 | 1.889937 | 0.060167 | 1.000000 |
| P4 | M_J | uniform | 128 | 1.639574 | 1.816004 | 1.824511 | 0.110623 | 0.988889 |
| P4 | M_J | uniform | 256 | 1.636828 | 1.795166 | 1.797960 | 0.102322 | 0.979861 |
| P4 | U_J | random | 64 | 1.942249 | 1.970811 | 1.968145 | 0.063802 | 0.837500 |
| P4 | U_J | random | 128 | 1.851012 | 1.880780 | 1.879886 | 0.071723 | 0.669444 |
| P4 | U_J | random | 256 | 1.820536 | 1.878553 | 1.878564 | 0.081434 | 0.879167 |
| P4 | U_J | uniform | 64 | 1.883992 | 1.920835 | 1.919574 | 0.065538 | 0.305556 |
| P4 | U_J | uniform | 128 | 1.796063 | 1.839831 | 1.839794 | 0.080349 | 0.131944 |
| P4 | U_J | uniform | 256 | 1.717560 | 1.804598 | 1.807092 | 0.090820 | 0.359722 |

Epoch 0 clipping is undefined because no updates occur. Component, group+instance, oracle-reference, signed-allocation/Gram, positive/negative-gain-mass diagnostics, and all checkpoints are retained. These diagnostics neither replace the primary estimator nor enter selection.

<a name="5-manipulasi-baseline-dan-audit"></a>

## 5. Baseline intervention and audit

Manipulation check: **9/9** capacities/corpora passed. U must reduce initial group/instance validation NLL relative to M, with shared accuracy≥95%.

| Width | Corpus | U group | M group | U instance | M instance | U shared accuracy | Passed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 64 | 61103 | 2.792166 | 4.424853 | 2.807484 | 4.628993 | 1.000000 | True |
| 64 | 61211 | 2.796420 | 4.499488 | 2.799079 | 4.527988 | 1.000000 | True |
| 64 | 61319 | 2.792117 | 4.415681 | 2.800576 | 4.541801 | 1.000000 | True |
| 128 | 61103 | 2.778645 | 5.847270 | 2.786970 | 6.152012 | 1.000000 | True |
| 128 | 61211 | 2.782178 | 6.001019 | 2.783206 | 6.017591 | 1.000000 | True |
| 128 | 61319 | 2.778833 | 5.896590 | 2.783314 | 6.055578 | 1.000000 | True |
| 256 | 61103 | 2.773079 | 7.771592 | 2.778419 | 8.171053 | 1.000000 | True |
| 256 | 61211 | 2.774681 | 7.937776 | 2.775908 | 8.005195 | 1.000000 | True |
| 256 | 61319 | 2.772776 | 7.826018 | 2.776531 | 8.028852 | 1.000000 | True |

M/U pairs share full tokens/labels, cold state, assignments, and order. U changes the pretraining objective and may change representations/dynamics; U−M does not isolate the effect of a single baseline value. This check is not a complete probability-calibration assessment.

Independent integrity audit: **PASS**; utility/scaling/K were rechecked for every panel. The audit covers frozen source, Stage 0–5 history, complete data regeneration, seed splits, cold/pretrained equality, weights/orders, candidates/ties/schedules across all panels, epoch 0 aliases, and test evaluation after the selection freeze.

Original Gram strict absolute-check failures: **0**; every failure is recorded and must pass prespecified 70-digit verification/float64 accumulation bounds. Undefined cumulative-primary normalizations: **0**, saved as null with reasons. No other tolerance was relaxed; fits/gains/selection are unchanged. See `DIAGNOSTIC_AUDIT.json`.

<a name="6-runtime-dan-keterbatasan-penyimpanan"></a>

## 6. Runtime and storage limitations

Training timers: perf_counter **80.43 minutes**, UTC **83.02 minutes**; UTC−perf_counter difference **155.702609 seconds**, without inferring a cause. The 180-minute budget used the larger timer; CPU analysis is excluded.

| Tahap | Jumlah | Peak allocated MiB | Peak reserved MiB |
| --- | --- | --- | --- |
| Pretraining | 102 | 150.097656 | 184.000000 |
| Initial evaluation | 54 | 60.790527 | 184.000000 |
| Adaptation | 792 | 150.490234 | 184.000000 |

**Model storage:** cold/pretrained models and epoch 30 models were saved in full. Adaptation models at epochs 1/3/5/10/20 were not saved as binaries; model-tensor SHA maps were recorded at runtime, together with all per-sequence losses/metrics at each checkpoint. The audit can check losses/fits/selection from those records, but cannot recompute intermediate-weight hashes from binaries that were not saved. Intermediate models require regeneration through a rerun if needed; hash availability is not equivalent to a fresh binary-checkpoint audit.

Available full models remain local and are excluded from the compact archive; all raw files have recorded SHA hashes, datasets/losses/assignments/orders/source are included, and the archive was checked by CRC and SHA. This stage involved no implicit retry, replacement seed, cloud execution, upload, or publication.

<a name="7-batas-ilmiah-dan-provenance"></a>

## 7. Scientific limitations and provenance

Four panels extend replication of the selection process, but share only three confirmation corpora. The bounded optimizer grid/horizon, synthetic task, and three capacities do not establish a global optimum, general scaling, exact large-LM replication, novelty, or venue readiness. The notebook is not claimed to have executed; experiment scripts were used. Stage 5 interpretation motivated the design rather than providing additional confirmation data.

Protocol SHA256: `9859d5644b8468506f47bd8c28ee594e2eb93f1371989f0fdb2c7e7c3be37164`. Selection SHA256: `678a1430ca845ab99ede2a4c683c40120a8641df4b76487fe0685f6aa3eb3de7`. Complete source/environment/check manifests are available in the raw archive. Literature guidance and claim boundaries follow `LITERATURE_CHECK.md`; this stage makes no new novelty claim.
