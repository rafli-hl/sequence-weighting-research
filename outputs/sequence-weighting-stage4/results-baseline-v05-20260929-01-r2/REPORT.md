# Stage 4 v0.5: intervensi pretraining dan referensi gain

**Revisi presentasi r2:** memperjelas timer proses dan interval timestamp UTC, menempatkan peringatan kualitas fit di dekat hasil utama, dan menjelaskan titik undefined pada grafik. Data, estimasi, audit, dan gambar ilmiah identik dengan laporan analisis-r1 yang tetap disimpan.

**Catatan analisis:** audit utama lulus pada analisis awal, tetapi satu pemeriksaan Gram float64 melewati toleransi absolut 1e-12. Hasil ini memakai perbaikan verifikasi numerik yang didokumentasikan dalam NUMERICAL_REPAIR.md; kegagalan awal tetap disimpan. Tidak ada training ulang atau perubahan estimator/seleksi.

144 run tuning baru dan 270 run konfirmasi selesai; 99 model pretrained.
Tiga corpus konfirmasi × tiga seed model/bobot, tiga kapasitas, dua arm.
Audit integritas **PASS**; tidak ada kegagalan run. Formula perbandingan,
data seeds, grid dan evaluasi test dibekukan sebelum training. Seleksi hanya
memakai validation NLL dari dua pasangan corpus/model tuning yang terpisah.

## 1. Jawaban utama: pretraining pada adaptasi yang sama

Pada optimizer F dan epoch 30, perubahan mean K untuk U−M adalah
**4.600252**, dengan tanda mean corpus
**positive**. Verdict M adalah
**disappears**, dan U adalah
**survives**.
K = p* menengah − max(p* kecil,p* besar). Nilai undefined tidak dibuang.

S memakai pretraining shared-only sebelumnya. M dan U memakai token mixed yang
persis sama; M mengoptimalkan shared CE, sedangkan U menambahkan CE target
uniform pada 16 jawaban di posisi group/instance, koefisien tetap 1. Cold
checkpoint dan urutan batch sama. F memakai LR1e-4, WD.1, clipping1.
U−M pada F/C30 menguji intervensi objective pretraining pada adaptasi tetap.
Intervensi dapat mengubah representasi maupun baseline loss; ia tidak
mengidentifikasi efek murni satu angka baseline. S−M juga mengubah konteks dan
jumlah shared-token supervision sehingga merupakan perbandingan kontekstual.

Pada U/F/C30, **2/9** fit kapasitas menengah menyentuh batas pencarian p*=8. Mean objective fit-nya 2.600139, dibanding 0.000177 pada M. Karena fit U jauh lebih buruk dan beberapa nilai dibatasi pencarian, puncak deskriptif ini tidak boleh dianggap bukti mekanisme pangkat yang cocok dengan baik. Pada U/T/ET, 1/27 p* kapasitas/pasangan undefined dan 5/27 menyentuh batas atas. Tidak ada nilai yang dihapus atau rentang pencarian yang diperluas.

![Matched adaptation](matched.png)

| Cell | Mean K | SD corpus means | Positive / 9 | Undefined / 9 | Peak | Gen random | Gen uniform |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S_F_C30 | -0.041060 | 0.003466 | 0 | 0 | disappears | False | False |
| S_F_C60 | 0.050503 | 0.007935 | 9 | 0 | survives | False | False |
| S_T_C30 | 0.066644 | 0.000210 | 9 | 0 | survives | False | False |
| S_F_ET | -0.017580 | 0.002940 | 0 | 0 | disappears | False | False |
| S_T_ET | -0.025444 | 0.002409 | 0 | 0 | disappears | False | True |
| M_F_C30 | -0.038544 | 0.002886 | 0 | 0 | disappears | False | False |
| M_F_C60 | 0.039704 | 0.005262 | 9 | 0 | survives | False | False |
| M_T_C30 | 0.071342 | 0.008147 | 9 | 0 | survives | False | False |
| M_F_ET | -0.021320 | 0.003040 | 0 | 0 | disappears | False | False |
| M_T_ET | -0.024380 | 0.001642 | 0 | 0 | disappears | False | True |
| U_F_C30 | 4.561708 | 1.501001 | 9 | 0 | survives | False | False |
| U_F_C60 | -0.533549 | 0.216302 | 2 | 0 | disappears | False | False |
| U_T_C30 | 3.862426 | 1.238621 | 9 | 0 | survives | False | False |
| U_F_ET | 2.034824 | 0.853716 | 7 | 0 | mixed/inconclusive | False | False |
| U_T_ET | undefined | undefined | 3 | 1 | inconclusive_undefined | False | False |

F/T adalah optimizer tetap/terpilih per kondisi. C30/C60 memakai epoch sama
antar kapasitas; ET memakai vektor epoch yang dipilih untuk kondisi itu.
Alias sel identik tercatat dalam policy-summary.json, bukan replikasi tambahan.
Survives berarti 9/9 kontras terdefinisi dan positif; disappears berarti semua
terdefinisi dan ketiga mean corpus <=0; selain itu mixed atau undefined.
SD mengacu pada tiga mean corpus. Ini hasil deskriptif, tanpa klaim signifikansi.

## 2. Apakah intervensi memperbaiki baseline yang dituju?

Manipulation check keseluruhan: **True**. U menurunkan
kedua component NLL group/instance dibanding M pada **9/9** sel
kapasitas/corpus; shared accuracy U >=95% pada **9/9** sel.
Kedua syarat dilaporkan terpisah dan kegagalan tidak memicu seleksi atau retry.

| Condition | Width | Initial val NLL | Shared NLL | Group NLL | Instance NLL | Shared accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| S | 64 | 3.182204 | 0.232534 | 4.624573 | 4.689504 | 100.00% |
| S | 128 | 4.108480 | 0.047723 | 6.105278 | 6.172439 | 100.00% |
| S | 256 | 5.333983 | 0.008079 | 7.944114 | 8.049758 | 100.00% |
| M | 64 | 3.098612 | 0.251842 | 4.494442 | 4.549553 | 100.00% |
| M | 128 | 4.014371 | 0.049274 | 5.962710 | 6.031128 | 100.00% |
| M | 256 | 5.313718 | 0.007875 | 7.916956 | 8.016324 | 100.00% |
| U | 64 | 2.006810 | 0.415802 | 2.799329 | 2.805299 | 100.00% |
| U | 128 | 1.875265 | 0.060029 | 2.781759 | 2.784008 | 100.00% |
| U | 256 | 1.853632 | 0.009380 | 2.775111 | 2.776404 | 100.00% |

Komponen memiliki empat jawaban masing-masing, sehingga mixed NLL adalah mean
ketiganya. Uniform-answer NLL ideal pada group/instance adalah log(16)=2.772589.
NLL yang lebih rendah bukan bukti lengkap kalibrasi probabilitas. S/M/U tetap
memakai empat epoch pretraining; tidak ada tuning strength atau durasi pretraining.

![Baseline](baseline.png)

## 3. Tuning baru, optimizer dan durasi

| Condition | Width | LR | WD | Clip | Epoch | Tuning validation NLL |
| --- | --- | --- | --- | --- | --- | --- |
| S | 64 | 0.0001 | 0.1 | 1.0 | 30 | 1.992689 |
| S | 128 | 0.0003 | 0.1 | 1.0 | 10 | 1.893534 |
| S | 256 | 0.0003 | 1.0 | 1.0 | 10 | 1.901114 |
| M | 64 | 0.0001 | 0.1 | 1.0 | 30 | 1.982483 |
| M | 128 | 0.0003 | 0.1 | 1.0 | 10 | 1.896345 |
| M | 256 | 0.0003 | 1.0 | 1.0 | 10 | 1.908137 |
| U | 64 | 0.0003 | 0.1 | 1.0 | 10 | 1.896070 |
| U | 128 | 0.0001 | 0.1 | 1.0 | 10 | 1.838469 |
| U | 256 | 0.0003 | 0.1 | 1.0 | 3 | 1.850748 |

Grid terbatas pada LR {1e-4,3e-4}, WD {.1,1}, clip1 dan epoch {1,3,10,30,60}.
Skor adalah mean validation NLL kedua arm dan dua tuning pairs. Tie rule: skor
presisi penuh, epoch awal, LR naik, WD naik. Epoch0 hanya menjadi pemeriksaan
improvement. Hasil terbaik dalam grid ini tidak berarti optimum global.
Perbandingan U−M pada T/ET adalah efek total kebijakan yang turut mengubah
optimizer/durasi, sehingga berbeda dari perbandingan adaptasi tetap di atas.

| Effect on K | Mean | SD corpus means | Corpus-mean sign |
| --- | --- | --- | --- |
| primary_U_minus_M_F_C30 | 4.600252 | 1.498199 | positive |
| secondary_U_minus_M_F_C60 | -0.573252 | 0.211076 | negative |
| context_M_minus_S_F_C30 | 0.002516 | 0.002771 | mixed |
| selected_policy_U_minus_M | undefined | undefined | undefined |
| S_optimizer_C30 | 0.107704 | 0.003256 | positive |
| S_duration_F | 0.023480 | 0.003001 | positive |
| S_duration_T | -0.092089 | 0.002216 | negative |
| S_interaction | -0.115569 | 0.004052 | negative |
| M_optimizer_C30 | 0.109886 | 0.005270 | positive |
| M_duration_F | 0.017224 | 0.004576 | positive |
| M_duration_T | -0.095723 | 0.009731 | negative |
| M_interaction | -0.112947 | 0.006482 | negative |
| U_optimizer_C30 | -0.699283 | 0.262452 | negative |
| U_duration_F | -2.526884 | 2.118819 | negative |
| U_duration_T | undefined | undefined | undefined |
| U_interaction | undefined | undefined | undefined |

Dalam tiap kondisi, interaction=(T_ET−T_C30)−(F_ET−F_C30). Seluruh sembilan
nilai dan tiga mean corpus ada di policy-summary.json. Efek per kapasitas untuk
p*, loss, memorisasi, fit, clipping dan signed gains ada di per-capacity-effects.csv.

![Selected policies](selected.png)

Titik mean p* U pada kapasitas terbesar tidak ditampilkan: satu dari sembilan nilai undefined membuat mean yang dipropagasikan juga undefined; nilainya tidak diimputasi atau dihapus dari agregasi.

## 4. Referensi loss saja: sensitivitas aritmetis

Pada trajectory F yang sama, hitung ulang gain dari baseline awal M atau U.
Diagonal memakai baseline model itu sendiri dan persis cocok dengan p* utama.
Off-diagonal hanya mengganti referensi per-sequence loss, bukan menjalankan
model baru. Propagasi undefined dapat membuat dekomposisi K tidak teridentifikasi.

| Reference cell | Mean K | Undefined K / 9 | p* 64 | p* 128 | p* 256 |
| --- | --- | --- | --- | --- | --- |
| e30_referenceM_trajectoryM | -0.038544 | 0 | 0.041212 | 0.093380 | 0.131924 |
| e30_referenceM_trajectoryU | -0.000385 | 0 | 0.054201 | 0.134421 | 0.134806 |
| e30_referenceU_trajectoryM | undefined | 9 | undefined | 8.000000 | 1.493759 |
| e30_referenceU_trajectoryU | 4.561708 | 0 | 0.940211 | 6.193818 | 1.632110 |
| e60_referenceM_trajectoryM | 0.039704 | 0 | 0.163985 | 0.203689 | 0.054557 |
| e60_referenceM_trajectoryU | 0.059032 | 0 | 0.138943 | 0.197975 | 0.074805 |
| e60_referenceU_trajectoryM | -4.191565 | 0 | 6.063049 | 1.871484 | 0.190285 |
| e60_referenceU_trajectoryU | -0.533549 | 0 | 2.068494 | 1.534945 | 0.283015 |

| Reference diagnostic effect on K | Mean | Undefined / 9 |
| --- | --- | --- |
| e30_reference | undefined | 9 |
| e30_trajectory | 0.038159 | 0 |
| e30_interaction | undefined | 9 |
| e30_total | 4.600252 | 0 |
| e60_reference | -4.231268 | 0 |
| e60_trajectory | 0.019328 | 0 |
| e60_interaction | 3.638688 | 0 |
| e60_total | -0.573252 | 0 |

Efek reference menahan trajectory M; efek trajectory menahan reference M.
Interaksi adalah selisih kedua efek bersilang. Rincian p* dan signed mean gain
per kapasitas/pasangan tersedia di reference-sensitivity.csv dan
reference-capacity-effects.csv. Jangan menjumlahkan hanya komponen yang terdefinisi
untuk membuat kesimpulan total ketika komponen lain undefined.

![Reference sensitivity](reference.png)

Seluruh checkpoint konfirmasi juga menyimpan p* komponen, group+instance-only,
referensi oracle [0,log16,log16], signed mass, centered cumulative RMS dan Gram
cross-terms. Estimator primer tetap memakai seluruh gain bertanda terhadap
baseline pretrained asli. Maksimum galat identitas gain komponen:
1.50012784e-06, di bawah toleransi frozen 2e-6.
Undefined dan boundary fits per kondisi/arm/metric tersimpan di diagnostics.csv
dan diagnostics.json; uniform p* selalu undefined, termasuk diagnostik.

## 5. Generalisasi, memorisasi, dan fit

| Cell | Arm | Width | Epoch | p* | Fit objective | Train | Validation | Test | Instance acc | Clipping |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S_F_C30 | random | 64 | 30 | 0.037633 | 0.000049 | 2.029611 | 2.098864 | 2.099726 | 6.24% | 99.9% |
| S_F_C30 | random | 128 | 30 | 0.091671 | 0.000175 | 1.852486 | 2.231229 | 2.228942 | 17.36% | 99.9% |
| S_F_C30 | random | 256 | 30 | 0.132732 | 0.000055 | 1.414097 | 2.713858 | 2.729006 | 44.46% | 99.9% |
| S_F_C30 | uniform | 64 | 30 | undefined | undefined | 1.864771 | 1.899738 | 1.899610 | 5.98% | 100.0% |
| S_F_C30 | uniform | 128 | 30 | undefined | undefined | 1.464831 | 1.875404 | 1.869152 | 14.28% | 99.8% |
| S_F_C30 | uniform | 256 | 30 | undefined | undefined | 0.405957 | 2.011507 | 2.008177 | 68.03% | 99.3% |
| S_T_ET | random | 64 | 30 | 0.037633 | 0.000049 | 2.029611 | 2.098864 | 2.099726 | 6.24% | 99.9% |
| S_T_ET | random | 128 | 10 | 0.034900 | 0.000041 | 1.869373 | 2.009467 | 2.002905 | 9.64% | 99.7% |
| S_T_ET | random | 256 | 10 | 0.060344 | 0.000080 | 1.830574 | 2.217212 | 2.206835 | 16.78% | 99.7% |
| S_T_ET | uniform | 64 | 30 | undefined | undefined | 1.864771 | 1.899738 | 1.899610 | 5.98% | 100.0% |
| S_T_ET | uniform | 128 | 10 | undefined | undefined | 1.668786 | 1.820266 | 1.813977 | 9.70% | 96.5% |
| S_T_ET | uniform | 256 | 10 | undefined | undefined | 1.276689 | 1.644643 | 1.633762 | 12.97% | 97.2% |
| M_F_C30 | random | 64 | 30 | 0.041212 | 0.000054 | 2.035193 | 2.104465 | 2.104647 | 6.25% | 99.9% |
| M_F_C30 | random | 128 | 30 | 0.093380 | 0.000177 | 1.845299 | 2.221211 | 2.210982 | 17.38% | 99.9% |
| M_F_C30 | random | 256 | 30 | 0.131924 | 0.000048 | 1.408972 | 2.693477 | 2.713359 | 44.47% | 99.9% |
| M_F_C30 | uniform | 64 | 30 | undefined | undefined | 1.863920 | 1.901780 | 1.901230 | 5.99% | 100.0% |
| M_F_C30 | uniform | 128 | 30 | undefined | undefined | 1.462668 | 1.872875 | 1.865668 | 13.87% | 99.4% |
| M_F_C30 | uniform | 256 | 30 | undefined | undefined | 0.391361 | 2.036069 | 2.032204 | 69.42% | 99.4% |
| M_T_ET | random | 64 | 30 | 0.041212 | 0.000054 | 2.035193 | 2.104465 | 2.104647 | 6.25% | 99.9% |
| M_T_ET | random | 128 | 10 | 0.035998 | 0.000043 | 1.866695 | 2.003241 | 1.995848 | 9.73% | 99.8% |
| M_T_ET | random | 256 | 10 | 0.060378 | 0.000079 | 1.823531 | 2.212765 | 2.201349 | 16.81% | 99.7% |
| M_T_ET | uniform | 64 | 30 | undefined | undefined | 1.863920 | 1.901780 | 1.901230 | 5.99% | 100.0% |
| M_T_ET | uniform | 128 | 10 | undefined | undefined | 1.665838 | 1.815626 | 1.808197 | 9.67% | 94.6% |
| M_T_ET | uniform | 256 | 10 | undefined | undefined | 1.281091 | 1.657611 | 1.647451 | 14.27% | 96.0% |
| U_F_C30 | random | 64 | 30 | 0.940211 | 0.001938 | 1.896494 | 2.010863 | 2.010890 | 10.10% | 95.8% |
| U_F_C30 | random | 128 | 30 | 6.193818 | 2.600139 | 1.773489 | 2.335233 | 2.338855 | 24.28% | 92.8% |
| U_F_C30 | random | 256 | 30 | 1.632110 | 0.223840 | 1.443863 | 2.756179 | 2.769913 | 44.00% | 97.4% |
| U_F_C30 | uniform | 64 | 30 | undefined | undefined | 1.719533 | 1.879005 | 1.875303 | 10.09% | 73.2% |
| U_F_C30 | uniform | 128 | 30 | undefined | undefined | 1.187442 | 2.034122 | 2.030189 | 24.64% | 80.8% |
| U_F_C30 | uniform | 256 | 30 | undefined | undefined | 0.216177 | 2.395785 | 2.395172 | 86.27% | 87.9% |
| U_T_ET | random | 64 | 10 | 0.460426 | 0.000765 | 1.898929 | 1.961649 | 1.961026 | 7.92% | 94.9% |
| U_T_ET | random | 128 | 10 | 4.575795 | 0.568448 | 1.840168 | 1.937493 | 1.929643 | 8.77% | 78.3% |
| U_T_ET | random | 256 | 3 | undefined | undefined | 1.847607 | 1.874986 | 1.873920 | 7.80% | 88.0% |
| U_T_ET | uniform | 64 | 10 | undefined | undefined | 1.772316 | 1.867980 | 1.863250 | 8.68% | 68.0% |
| U_T_ET | uniform | 128 | 10 | undefined | undefined | 1.678010 | 1.822166 | 1.813333 | 9.72% | 42.3% |
| U_T_ET | uniform | 256 | 3 | undefined | undefined | 1.770996 | 1.822884 | 1.819284 | 8.11% | 50.5% |

Kriteria generalisasi mensyaratkan test NLL turun ketat dengan kapasitas dan
validation <=epoch0 pada setiap kapasitas, dalam **setiap** corpus. Tabel sel
di atas melaporkan random dan uniform secara terpisah; hasil per corpus ada
di policy-summary.json. Tidak ada evaluasi test saat tuning atau pada epoch0.
Fit objective, negative-gain fraction dan boundary flags bukan kriteria seleksi.
Memorisasi dan clipping harus dibaca bersama p*, bukan bukti mekanisme kausal
clipping. Data akhir lengkap ada di all-checkpoints.csv.

## 6. Integritas, sumber daya dan reproduksi

Audit memeriksa 4826 file historis tanpa
perubahan, 2070 checkpoint adaptasi dan tepat
1350 evaluasi test yang dibekukan sebelumnya.
Cold-model tensors sama lintas kondisi; pretrained model/loss awal sama lintas
arm/config dalam tiap kondisi. Full tokens/targets/type masks, bobot, batch
orders, source hashes, seleksi dan scalar metrics/p* direkonstruksi.

Timer `perf_counter` mencatat 84.1 menit untuk pretraining,
setup, evaluasi dan penyimpanan; tidak mencakup persiapan, audit dan laporan.

Interval dari timestamp UTC awal hingga COMPLETE adalah **92.0 menit** (5518.475 detik), sedangkan timer mencatat 5048.784 detik. Selisihnya 469.690 detik; penyebab perbedaan kedua catatan waktu tidak ditetapkan dari bukti yang tersedia. Keduanya di bawah batas tiga jam. Nilai timer asli tetap disimpan tanpa perubahan; perbedaan ini tidak mengubah seleksi, hasil model, atau kontras statistik.

Puncak alokasi adaptasi 150.49 MiB;
reserved 184.00 MiB.
Memori ini pengukuran PyTorch, bukan seluruh driver/desktop. Batas tiga jam
dan 468 run dipenuhi. Semua output lokal; tidak ada upload/publikasi.

Raw: `work/runs/baseline-v05-20260929-01/`. Arsip ringkas memuat protokol, kode, data,
per-sequence loss, assignments, keputusan tuning, audit, laporan dan gambar.
Model binaries tetap lokal dengan hash di raw-manifest.json. Lingkungan ada
di environment-lock.txt. Notebook tidak dijalankan; skrip menghasilkan hasil.

## 7. Posisi ilmiah dan batas klaim

Hasil menguji intervensi objective pretraining dan ketergantungan gain pada
referensinya dalam tugas sintetis. Tiga kapasitas tidak cukup untuk perpindahan
antara dua puncak interior. Tiga corpus konfirmasi dan dua tuning pairs memberi
bukti terbatas. Manipulasi dapat mengubah representasi, kemampuan shared, dan
dinamika adaptasi sekaligus. Reference swapping membantu diagnosis aritmetis;
tidak membuktikan mediasi kausal baseline loss.

[Jane Street](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/)
memotivasi metrik dan pertanyaan scaling, tetapi eksperimen ini bukan replikasi
LM besar/private text mereka. Uniform-target regularization berkaitan dengan
[Pereyra et al.](https://arxiv.org/abs/1701.06548); pengukuran kalibrasi formal
berbeda dari NLL, seperti dibahas [Guo et al.](https://proceedings.mlr.press/v70/guo17a.html).
LITERATURE_CHECK.md mencatat sumber primer yang diperiksa kembali. Tidak ada
klaim novelty, kelayakan venue atau jaminan publikasi.
