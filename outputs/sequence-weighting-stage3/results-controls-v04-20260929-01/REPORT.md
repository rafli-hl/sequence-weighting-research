# Stage 3 v0.4: optimizer, durasi, tujuan seleksi, dan baseline

108 run konfirmasi berpasangan dan 27 checkpoint pretraining selesai tanpa
kegagalan. Tiga corpus baru × tiga seed model/bobot; enam konfigurasi unik
lintas tiga kapasitas, dengan random dan uniform. Tidak ada grid tuning baru.
Audit integritas **PASS**. Semua angka di bawah berasal dari protokol yang
dibekukan sebelum konfirmasi; diagnostik Stage 2 diberi label retrospektif.

## 1. Optimizer dan durasi

Pada data baru, perubahan jadwal C30 → EJ menghasilkan mean perubahan K 0.017682 dengan optimizer F dan -0.079479 dengan J. Interaksi optimizer×durasi adalah -0.097161 (tanda mean corpus: negative). Dengan epoch 30 yang sama, F/J memberi verdict disappears / survives; pada jadwal 30/10/10 verdict-nya disappears / disappears. Ini memisahkan perubahan checkpoint pada trajectory yang sama dari perubahan konfigurasi optimizer dalam eksperimen terkontrol ini.

F adalah LR 1e-4, WD 0,1, clipping 1 pada semua kapasitas. J adalah konfigurasi
pilihan joint validation Stage 2. C30 berarti epoch 30/30/30; EJ berarti 30/10/10.
K = p* menengah − max(p* kecil,p* besar). Optimizer dan jadwal disilangkan pada
corpus, checkpoint awal, bobot, dan batch order identik. Kontras ini tidak
menyamakan intervensi gabungan LR/WD dengan efek regularisasi saja.

| Cell | Alias | Mean K | Between-corpus SD | Positive / 9 | Peak verdict | Random generalization |
| --- | --- | --- | --- | --- | --- | --- |
| F_C30 | - | -0.040267 | 0.006178 | 0 | disappears | False |
| F_EJ | - | -0.022584 | 0.002914 | 0 | disappears | False |
| J_C30 | - | 0.073606 | 0.005694 | 9 | survives | False |
| J_EJ | - | -0.005873 | 0.005860 | 1 | disappears | False |
| J_ER | J_EJ | -0.005873 | 0.005860 | 1 | disappears | False |
| R_EJ | - | -0.009651 | 0.005316 | 0 | disappears | False |
| R_ER | R_EJ | -0.009651 | 0.005316 | 0 | disappears | False |

Alias menandai sel yang memakai trajectory dan checkpoint persis sama. Sel-sel
itu tidak dihitung sebagai replikasi tambahan. F/J identik pada kapasitas kecil.

![Optimizer dan durasi](optimizer-duration.png)

| Effect on K | Mean | Between-corpus SD | Corpus-mean sign |
| --- | --- | --- | --- |
| Q1_optimizer_C30 | 0.113873 | 0.009216 | positive |
| Q1_optimizer_EJ | 0.016712 | 0.003182 | positive |
| Q1_duration_F | 0.017682 | 0.003641 | positive |
| Q1_duration_J | -0.079479 | 0.006050 | negative |
| Q1_interaction | -0.097161 | 0.009691 | negative |
| Q2_configuration_EJ | -0.003779 | 0.000657 | negative |
| Q2_duration_J | 0.000000 | 0.000000 | zero |
| Q2_interaction | 0.000000 | 0.000000 | zero |
| Q2_total | -0.003779 | 0.000657 | negative |

Seluruh 9 kontras dan mean/SD dalam tiap corpus tersedia di policy-summary.json
dan policy-cells.csv. SD pada tabel efek adalah SD tiga mean corpus, bukan
ketidakpastian dari sembilan dataset. Tiga corpus belum mendukung klaim
signifikansi. Efek konsisten berarti ketiga mean corpus bertanda sama; nol,
mixed, dan undefined tetap ditampilkan.

## 2. Tujuan seleksi validasi

Seleksi random-only menghasilkan verdict disappears, 0/9 kontras positif. Perubahan total K terhadap joint selection: -0.003779. EJ=ER persis, sehingga efek perubahan jadwal dan interaksinya pada perbandingan tujuan seleksi adalah nol karena desain terpilih identik. Perbedaan yang tersisa adalah konfigurasi, khususnya WD 0,1 → 1 pada kapasitas menengah dengan LR dan clipping tetap.

| Policy | Width | LR | WD | Clip | Selected epoch |
| --- | --- | --- | --- | --- | --- |
| F | 64 | 0.0001 | 0.1 | 1.0 | fixed trajectories |
| F | 128 | 0.0001 | 0.1 | 1.0 | fixed trajectories |
| F | 256 | 0.0001 | 0.1 | 1.0 | fixed trajectories |
| J | 64 | 0.0001 | 0.1 | 1.0 | 30 |
| J | 128 | 0.0003 | 0.1 | 1.0 | 10 |
| J | 256 | 0.0001 | 1.0 | 1.0 | 10 |
| R | 64 | 0.0001 | 0.1 | 1.0 | 30 |
| R | 128 | 0.0003 | 1.0 | 1.0 | 10 |
| R | 256 | 0.0001 | 1.0 | 1.0 | 10 |

J dan R dihitung dari **dua replikasi tuning Stage 2 yang digunakan ulang**.
J meminimalkan mean validation NLL random+uniform; R memakai random saja.
Tie rule: skor presisi penuh, epoch lebih awal, LR naik, WD naik, clip 1 sebelum
disabled. Hash semua input/keputusan, kandidat dan jadwal tersimpan dalam
selection.json. Tidak ada test, p* atau hasil konfirmasi dalam seleksi.

![Tujuan seleksi](selection-objective.png)

Efek kebijakan ini bersyarat pada dua replikasi tuning tersebut. Hasil tidak
membuktikan bahwa satu tujuan seleksi selalu lebih baik atau bahwa optimum
global ditemukan. Per-capacity paired effects untuk p*, train/validation/test
NLL, memorisasi dan clipping tersedia di per-capacity-effects.csv dan JSON.

## 3. Audit baseline pretraining

Pada J/EJ, referensi oracle/uniform alternatif menghasilkan p* undefined pada 27/27 pasangan kapasitas/corpus/seed. Bandingkan aggregate gain terhadap referensi itu dengan gain terhadap pretrained baseline sebelum menafsirkan besarnya loss reduction sebagai pembelajaran pola spesifik. Ini sensitivitas terhadap referensi, bukan efek kausal mengubah pretraining.

| Source | Width | Total val NLL | Shared NLL | Group NLL | Instance NLL |
| --- | --- | --- | --- | --- | --- |
| stage2_tuning_retrospective | 64 | 3.234835 | 0.235978 | 4.771241 | 4.697286 |
| stage2_tuning_retrospective | 128 | 4.193495 | 0.047410 | 6.335068 | 6.198006 |
| stage2_tuning_retrospective | 256 | 5.450627 | 0.007936 | 8.256560 | 8.087385 |
| fresh_confirmation | 64 | 3.220053 | 0.234622 | 4.715975 | 4.709560 |
| fresh_confirmation | 128 | 4.133592 | 0.048944 | 6.166673 | 6.185159 |
| fresh_confirmation | 256 | 5.398345 | 0.008105 | 8.075870 | 8.111061 |

Komponen NLL pada tabel adalah rata-rata per answer token komponen masing-masing;
total mixed NLL adalah mean ketiganya. Angka Stage 2 memakai enam baseline
tuning yang dideduplikasi, sehingga cocok dengan konteks 3,23/4,19/5,45.
Pretraining shared-only tidak mengoptimalkan group dan instance mixed task.
Referensi uniform atas 16 jawaban memiliki NLL log(16)=2,772589 per komponen.

![Komponen baseline](baseline-components.png)

Berikut alokasi gain pada J/EJ, random, konfirmasi baru. Signed mass share
dapat negatif; gain komponen tidak dipotong. RMS mengukur bentuk kontribusi
kumulatif terhadap penyimpangan dari alokasi uniform. Cross-terms lengkap
disimpan dalam diagnostics.json karena kontribusi tidak independen.

| Width | Component | Initial train NLL | Current NLL | Signed mean gain | Gain mass share | Centered cumulative RMS | Component p* | Undefined / 9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 64 | shared | 0.234499 | 0.527483 | -0.292983 | -0.084876 | 0.005666 | undefined | 9 |
| 64 | group | 4.703795 | 2.742689 | 1.961106 | 0.566571 | 0.012082 | 0.031952 | 0 |
| 64 | instance | 4.687210 | 2.893176 | 1.794034 | 0.518304 | 0.010631 | 0.030719 | 0 |
| 128 | shared | 0.048924 | 0.207852 | -0.158928 | -0.023696 | 0.001739 | undefined | 9 |
| 128 | group | 6.159197 | 2.613015 | 3.546182 | 0.528970 | 0.013184 | 0.037514 | 0 |
| 128 | instance | 6.158640 | 2.842059 | 3.316581 | 0.494726 | 0.009622 | 0.029260 | 0 |
| 256 | shared | 0.008095 | 0.154618 | -0.146523 | -0.013965 | 0.000890 | undefined | 9 |
| 256 | group | 8.063546 | 2.634587 | 5.428958 | 0.517401 | 0.009382 | 0.027165 | 0 |
| 256 | instance | 8.084946 | 2.874981 | 5.209965 | 0.496564 | 0.006570 | 0.019750 | 0 |

| Cell | Width | Original p* | Group+instance p* | Oracle-ref p* | Oracle undefined / 9 | Oracle mean gain |
| --- | --- | --- | --- | --- | --- | --- |
| J_EJ | 64 | 0.042864 | 0.031373 | undefined | 9 | -0.206057 |
| J_EJ | 128 | 0.036992 | 0.033525 | undefined | 9 | -0.039249 |
| J_EJ | 256 | 0.025213 | 0.023531 | undefined | 9 | -0.039670 |
| J_C30 | 64 | 0.042864 | 0.031373 | undefined | 9 | -0.206057 |
| J_C30 | 128 | 0.200998 | 0.198614 | 4.272652 | 0 | 0.171829 |
| J_C30 | 256 | 0.127392 | 0.126392 | 1.856754 | 0 | 0.353572 |
| J_C60 | 64 | 0.144442 | 0.134974 | undefined | 9 | -0.068719 |
| J_C60 | 128 | 0.182661 | 0.182266 | 0.833181 | 0 | 0.700048 |
| J_C60 | 256 | 0.075937 | 0.075765 | 0.299426 | 0 | 1.193213 |

Referensi alternatif [0,log(16),log(16)] adalah oracle shared-rule dan prediksi
uniform untuk group/instance, **bukan checkpoint pretrained lain**. Nilai
undefined berarti estimator tidak teridentifikasi atau aggregate gain tidak
positif; nilai itu tidak dibuang atau diubah menjadi nol. Mean diagnostik hanya
ditampilkan bila semua sembilan nilai terdefinisi. p* primer tetap estimator
asli terhadap baseline pretrained dan memakai gain bertanda.

Identitas gain total = mean tiga gain komponen diperiksa; maksimum selisih
float32 adalah 1.38767064e-06. Alokasi kumulatif
dan matriks cross-term juga direkonstruksi. Diagnostik mencakup seluruh 540
checkpoint adaptasi Stage 3 dan 450 checkpoint Stage 2 retrospektif. Baseline
dan perubahan referensi dapat memengaruhi interpretasi gain/p*, tetapi ini
bukan intervensi pretraining yang mengidentifikasi sebab kausal puncak.

## 4. Generalisasi, memorisasi, dan clipping

| Cell | Arm | Width | Epoch | p* | Train NLL | Validation NLL | Test NLL | Instance train acc | Clipping |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F_C30 | random | 64 | 30 | 0.042864 | 2.054449 | 2.147894 | 2.146821 | 6.77% | 100.0% |
| F_C30 | random | 128 | 30 | 0.092165 | 1.854368 | 2.219055 | 2.225263 | 17.32% | 100.0% |
| F_C30 | random | 256 | 30 | 0.132432 | 1.458673 | 2.740242 | 2.735825 | 42.76% | 100.0% |
| F_C30 | uniform | 64 | 30 | undefined | 1.847775 | 1.904737 | 1.900077 | 6.68% | 100.0% |
| F_C30 | uniform | 128 | 30 | undefined | 1.475345 | 1.884096 | 1.882798 | 14.71% | 99.4% |
| F_C30 | uniform | 256 | 30 | undefined | 0.408759 | 2.075258 | 2.074555 | 68.48% | 99.1% |
| F_EJ | random | 64 | 30 | 0.042864 | 2.054449 | 2.147894 | 2.146821 | 6.77% | 100.0% |
| F_EJ | random | 128 | 10 | 0.020280 | 2.104665 | 2.184561 | 2.184487 | 6.55% | 100.0% |
| F_EJ | random | 256 | 10 | 0.026158 | 1.884945 | 2.052492 | 2.050965 | 10.03% | 100.0% |
| F_EJ | uniform | 64 | 30 | undefined | 1.847775 | 1.904737 | 1.900077 | 6.68% | 100.0% |
| F_EJ | uniform | 128 | 10 | undefined | 1.878945 | 1.937995 | 1.935183 | 6.42% | 100.0% |
| F_EJ | uniform | 256 | 10 | undefined | 1.647194 | 1.818490 | 1.819554 | 10.69% | 97.2% |
| J_C30 | random | 64 | 30 | 0.042864 | 2.054449 | 2.147894 | 2.146821 | 6.77% | 100.0% |
| J_C30 | random | 128 | 30 | 0.200998 | 1.676563 | 2.696547 | 2.685456 | 35.28% | 100.0% |
| J_C30 | random | 256 | 30 | 0.127392 | 1.494821 | 2.646037 | 2.646580 | 40.66% | 100.0% |
| J_C30 | uniform | 64 | 30 | undefined | 1.847775 | 1.904737 | 1.900077 | 6.68% | 100.0% |
| J_C30 | uniform | 128 | 30 | undefined | 0.705349 | 1.990881 | 1.984160 | 44.43% | 98.4% |
| J_C30 | uniform | 256 | 30 | undefined | 0.480548 | 1.991647 | 1.990135 | 62.90% | 99.1% |
| J_EJ | random | 64 | 30 | 0.042864 | 2.054449 | 2.147894 | 2.146821 | 6.77% | 100.0% |
| J_EJ | random | 128 | 10 | 0.036992 | 1.887642 | 2.033437 | 2.033754 | 10.11% | 99.9% |
| J_EJ | random | 256 | 10 | 0.025213 | 1.888062 | 2.049755 | 2.048131 | 9.83% | 100.0% |
| J_EJ | uniform | 64 | 30 | undefined | 1.847775 | 1.904737 | 1.900077 | 6.68% | 100.0% |
| J_EJ | uniform | 128 | 10 | undefined | 1.669073 | 1.827530 | 1.829391 | 10.69% | 95.2% |
| J_EJ | uniform | 256 | 10 | undefined | 1.653898 | 1.820356 | 1.821334 | 10.63% | 97.2% |
| R_ER | random | 64 | 30 | 0.042864 | 2.054449 | 2.147894 | 2.146821 | 6.77% | 100.0% |
| R_ER | random | 128 | 10 | 0.033213 | 1.901952 | 2.034029 | 2.032501 | 9.44% | 99.9% |
| R_ER | random | 256 | 10 | 0.025213 | 1.888062 | 2.049755 | 2.048131 | 9.83% | 100.0% |
| R_ER | uniform | 64 | 30 | undefined | 1.847775 | 1.904737 | 1.900077 | 6.68% | 100.0% |
| R_ER | uniform | 128 | 10 | undefined | 1.690043 | 1.835094 | 1.835852 | 10.32% | 94.4% |
| R_ER | uniform | 256 | 10 | undefined | 1.653898 | 1.820356 | 1.821334 | 10.63% | 97.2% |

Kriteria generalisasi diterapkan per corpus: test NLL harus menurun ketat
dengan kapasitas dan validation NLL tidak lebih buruk dari epoch 0 pada setiap
kapasitas. Hasil masing-masing corpus dan arm ada di policy-summary.json.
Tidak ada evaluasi test epoch 0 atau seleksi ulang dari konfirmasi.
Uniform p* selalu undefined. Semua undefined/boundary fits, termasuk komponen
dan referensi alternatif, disimpan di diagnostics.json dan diagnostics.csv.

![Trajectory epoch bersama](trajectories.png)

## 5. Integritas, runtime, reproduksi

Training-stage wall time 1212.8 detik
(20.2 menit), termasuk pretraining, evaluasi dan
serialisasi di interval tersebut; tidak termasuk persiapan/audit/laporan.
Puncak alokasi adaptasi 150.49 MiB;
reserved 184.00 MiB.
Ini memori PyTorch, bukan seluruh desktop/driver. Batas dua jam dan 144 run
dipenuhi; jumlah aktual 108 didapat melalui deduplikasi sebelum training.

Audit memeriksa 3031 file historis,
108 run, 27 pretrained checkpoints, 540 model checkpoint adaptasi dan tepat
540 evaluasi test setelah freeze. Source/tensor/order/weight/checkpoint hashes,
pairing across-arm dan across-config, split/toggle equality, pemilihan validasi
independen, seluruh scalar metric dan p* asli direkonstruksi. Tidak ada run gagal.

Raw: `work/runs/controls-v04-20260929-01/`. Arsip ringkas menyimpan protokol/source,
input tuning dan keputusan, data, assignment/order, per-sequence losses,
retrospective evidence, audit, laporan dan gambar. Model penuh dikecualikan
dari ZIP tetapi tersedia lokal dengan hash. environment-lock.txt mencatat
runtime aktual. Notebook tidak dijalankan; skrip ekuivalen menjalankan studi.

## 6. Posisi paper dan batas klaim

Kontribusi kandidat adalah kontrol atas kebijakan optimizer/durasi/seleksi dan
audit baseline pada tugas terstruktur. Efek terukur berlaku untuk konfigurasi
dan corpus dalam protokol ini. Tiga kapasitas hanya memberi satu titik interior;
tidak ada bukti perpindahan antara dua lokasi puncak interior. Tiga corpus dan
dua replikasi tuning yang digunakan ulang membatasi generalisasi inferensi.

[Jane Street](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/)
menggunakan tuning held-out dan regularisasi kuat pada LM pretrained; hasil
sintetis ini tidak setara dengan setting itu. Estimator signed-gain mengikuti
[technical note](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/sequence-weighting-note.pdf).
Hubungan pembobotan dengan durasi dan regularisasi sudah terkait
[Byrd & Lipton, ICML 2019](https://proceedings.mlr.press/v97/byrd19a.html) dan
[Xu, Ye & Ruan, 2021](https://arxiv.org/abs/2103.15209). Rincian recheck sumber
primer ada di LITERATURE_CHECK.md. Tidak ada klaim novelty/venue atau publikasi.
