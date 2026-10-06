# Stage 2: capacity-specific validation tuning

Hasil: **puncak p* menghilang** menurut aturan deskriptif yang dibekukan.
Kontras positif: **1/15** pasangan corpus/seed.
Kriteria generalisasi primer **tidak terpenuhi**.
Ini hasil tugas sintetis dengan grid terbatas, bukan replikasi eksak LM besar.

## Desain dan eksekusi

216 run tuning, 90 run konfirmasi, satu benchmark engineering terpisah,
52 checkpoint pretraining. Semua selesai; tidak ada run gagal. Training lokal
RTX 3050 Laptop melalui Ubuntu WSL 2, float32. Kode/protokol dibekukan sebelum
benchmark dan selection.json dibekukan sebelum konfirmasi. Test hanya sekali
per run konfirmasi, pada epoch terpilih. Notebook tidak dieksekusi; skrip yang
menjalankan eksperimen.

Dua replikasi tuning masing-masing memakai satu corpus dan satu seed model;
keduanya tidak disilangkan. Konfirmasi memakai tiga corpus independen dengan
lima seed model/bobot per corpus. Seed model/bobot bukan 15 replikasi dataset.
Semua arm memiliki token/label, checkpoint awal, dan urutan batch berpasangan;
bobot acak identik lintas kapasitas. Data lengkap dihasilkan sebelum toggle tes.

## Pemilihan hanya berdasarkan validasi

| Width/layers | LR | WD | Clip | Epoch | Tuning val NLL | Epoch 0 val NLL |
| --- | --- | --- | --- | --- | --- | --- |
| 64/2 | 0.0001 | 0.1 | 1.0 | 30 | 2.009139 | 3.234835 |
| 128/3 | 0.0003 | 0.1 | 1.0 | 10 | 1.895202 | 4.193495 |
| 256/4 | 0.0001 | 1.0 | 1.0 | 10 | 1.901818 | 5.450627 |

Rata-rata dua arm × dua replikasi tuning menjadi skor seleksi. Tie rule:
skor presisi penuh, epoch lebih awal, LR naik, WD naik, clip 1 sebelum disabled.
Epoch 0 adalah pembanding wajib; kandidat adaptasi adalah epoch 1/3/10/30/60.
Kapasitas dengan pilihan adaptasi lebih buruk dari epoch 0:
[].
Tidak ada p*, test loss atau bentuk kurva dalam kriteria seleksi.

## Hasil pada kebijakan terpilih

| Arm | Parameters | Epoch | p* mean | Train NLL | Val NLL | Test NLL | Instance train accuracy | Clipping |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| random | 113408 | 30 | 0.046519 | 2.05450 | 2.14454 | 2.14875 | 6.44% | 99.9% |
| random | 621696 | 10 | 0.038538 | 1.88132 | 2.02793 | 2.02661 | 9.89% | 99.7% |
| random | 3212800 | 10 | 0.027615 | 1.87971 | 2.04190 | 2.04119 | 9.80% | 99.6% |
| uniform | 113408 | 30 | undefined | 1.85120 | 1.89826 | 1.89661 | 6.17% | 100.0% |
| uniform | 621696 | 10 | undefined | 1.65830 | 1.81381 | 1.81462 | 9.69% | 95.8% |
| uniform | 3212800 | 10 | undefined | 1.63720 | 1.79727 | 1.79884 | 9.71% | 98.8% |

Angka tabel adalah mean 15 run per arm/kapasitas, dengan jumlah seed sama di
setiap corpus. Ini perbandingan kebijakan: durasi bisa berbeda antar kapasitas.
Uniform p* tidak teridentifikasi. CSV menyimpan seluruh komponen, gain, fit,
clipping dan checkpoint agar angka rata-rata tidak menutupi hasil individual.

![Kebijakan terpilih](selected-policy.png)

| Corpus | Model/weight seed | p* small | p* middle | p* large | Middle minus max endpoint |
| --- | --- | --- | --- | --- | --- |
| 57721 | 201 | 0.048086 | 0.036757 | 0.026499 | -0.011328 |
| 57721 | 202 | 0.042568 | 0.033231 | 0.025276 | -0.009337 |
| 57721 | 203 | 0.050965 | 0.044397 | 0.032146 | -0.006568 |
| 57721 | 204 | 0.040614 | 0.031262 | 0.023101 | -0.009352 |
| 57721 | 205 | 0.052189 | 0.046461 | 0.029782 | -0.005728 |
| 14142 | 201 | 0.043092 | 0.040623 | 0.026656 | -0.002469 |
| 14142 | 202 | 0.051336 | 0.034134 | 0.024526 | -0.017202 |
| 14142 | 203 | 0.042216 | 0.030720 | 0.022705 | -0.011496 |
| 14142 | 204 | 0.037892 | 0.040094 | 0.031680 | 0.002203 |
| 14142 | 205 | 0.047403 | 0.039184 | 0.029789 | -0.008219 |
| 17320 | 201 | 0.038989 | 0.032866 | 0.021807 | -0.006123 |
| 17320 | 202 | 0.049790 | 0.045515 | 0.028199 | -0.004275 |
| 17320 | 203 | 0.049909 | 0.040281 | 0.030024 | -0.009628 |
| 17320 | 204 | 0.054278 | 0.041323 | 0.030461 | -0.012955 |
| 17320 | 205 | 0.048454 | 0.041215 | 0.031582 | -0.007239 |

| Corpus | Mean contrast | Within-corpus SD | Positive / 5 |
| --- | --- | --- | --- |
| 14142 | -0.007436696014881021 | 0.007583735229707229 | 1 |
| 17320 | -0.008043978199351418 | 0.0033604921699118156 | 0 |
| 57721 | -0.008462625667742302 | 0.0022822826041384125 | 0 |

Mean kontras antar corpus: -0.007981099960658248; SD antar corpus:
0.0005158470391801077; rentang: [-0.008462625667742302, -0.007436696014881021].
SD dalam corpus di atas mengukur variasi model/bobot pada data yang sama.
Tiga corpus terlalu sedikit untuk klaim signifikansi; tidak ada bootstrap
sequence yang diperlakukan sebagai replikasi dataset.

![Kontras berpasangan](paired-contrasts.png)

## Generalisasi, memorisasi dan kualitas fit

| Corpus | Arm | Test decreases with capacity | Selected val no worse than epoch 0 |
| --- | --- | --- | --- |
| 14142 | random | False | True |
| 14142 | uniform | True | True |
| 17320 | random | False | True |
| 17320 | uniform | True | True |
| 57721 | random | False | True |
| 57721 | uniform | True | True |

Aturan primer mewajibkan test NLL random menurun ketat pada ketiga kapasitas
di setiap corpus serta mean validation NLL terpilih tidak lebih buruk dari
epoch 0 pada setiap kapasitas/corpus. Nilai lengkapnya ada di summary.json.
Baseline test tidak dijadwalkan, sehingga tidak ada klaim perbaikan test
terhadap epoch 0. Kontrol uniform dilaporkan terpisah.

p* random primer undefined: 0/45;
boundary bawah (p<=.001): 0/45;
boundary atas (p>=7.999): 0/45.
Rentang objective fit: 7.517703433987704e-06 sampai 0.00010353193440490573.
Rentang total gain bertanda: 562.0836169719696 sampai 1848.9171843528748.
Rentang fraksi gain negatif: 0.0 sampai 0.001953125.
Jumlah seluruh checkpoint dengan p* undefined menurut alasan:
{"no_adaptation": 307, "constant_weights": 765}. Termasuk epoch 0,
kontrol uniform, tuning, konfirmasi dan benchmark engineering; benchmark tidak
masuk inferensi primer. Tidak ada undefined yang disubstitusi menjadi nol.
Gain negatif dipertahankan. Objective kecil tidak otomatis membuktikan model
mekanisme benar. Pilihan clipping dalam grid bukan intervensi kausal tersendiri.

![Fit pada corpus/seed tetap](gain-fit.png)

## Diagnostik sekunder

![Trajectory dengan epoch yang sama](trajectories.png)

| Epoch | Kontras positif / 15 | Undefined | Mean kontras per corpus |
| --- | --- | --- | --- |
| 1 | 13 | 0 | 14142: 0.0012605589564729624, 17320: 0.004535690078206001, 57721: 0.004257881857760932 |
| 3 | 15 | 0 | 14142: 0.002444034726352248, 17320: 0.0020939775908275144, 57721: 0.005920298707585646 |
| 10 | 15 | 0 | 14142: 0.007373047715695082, 17320: 0.004583245600071917, 57721: 0.006951888433079744 |
| 30 | 15 | 0 | 14142: 0.05940599427265688, 17320: 0.06843275785044688, 57721: 0.06458881829756843 |
| 60 | 10 | 0 | 14142: 0.015776224642135607, 17320: 0.008552526371074742, 57721: 0.013634599809569947 |

Trajektori memakai optimizer terpilih setiap kapasitas, dengan epoch sama.
Model boleh dilatih setelah epoch pengujian hanya untuk diagnostik yang sudah
dijadwalkan; tidak ada pemilihan ulang atau test tambahan. Historical v0.2
adalah pembanding lintas studi, bukan kontrol dengan tensor identik. Belum ada
kontrol baru yang menyamakan semua optimizer v0.2 pada corpus Stage 2.

## Runtime, audit dan reproduksi

Wall time grid sampai konfirmasi selesai: 3314.8 detik (55.2 menit),
termasuk pretraining yang diperlukan, evaluasi dan serialisasi dalam interval
tersebut; tidak termasuk persiapan, benchmark dan audit. Jumlah waktu per-run
(termasuk benchmark, dan pretraining pada pemanggilan pertama): 3153.0 detik.
Puncak alokasi adaptasi: 150.49 MiB;
reserved: 184.00 MiB. Ini memori
PyTorch, bukan seluruh penggunaan desktop/driver.

AUDIT.json memverifikasi 307 run dan 52 checkpoint, pairing penuh, semua hash,
rekonstruksi seleksi, urutan freeze/test, seluruh p* dari gain bertanda dan
ketiadaan test saat tuning. raw-manifest.json mencatat hash seluruh file raw,
termasuk model penuh yang tidak dimasukkan ke arsip ringkas. run-records.zip
menyimpan kode, protokol, lingkungan, corpus, assignment/order, semua loss,
keputusan seleksi, laporan dan gambar. Model penuh tetap di:
`work/runs/generalization-v03-20260928-01/`.

Reproduksi memerlukan environment-lock.txt dan CUDA WSL lokal. Gunakan source
Stage 2 dengan run-id baru: jalankan fase benchmark, lalu fase experiment bila
gate lolos, kemudian analyze_stage2.py. Jangan menimpa direktori ini.

## Posisi paper dan batas kesimpulan

Hasil mendukung pembingkaian paper sebagai batas ketahanan puncak terhadap seleksi validasi dalam tugas sintetis ini. Jangan menjadikannya klaim replikasi kurva Jane Street. Prioritas tindak lanjut adalah kontrol optimizer/durasi pada corpus identik untuk memisahkan kontribusi early stopping dan perubahan regularisasi. Perluasan teks besar dan kompensasi inverse-exponent belum dibenarkan oleh hasil ini.

[Pemeriksaan sumber primer terbaru](../LITERATURE_CHECK.md) membatasi novelty:
hubungan bobot, regularisasi, durasi dan memorisasi sudah terkait literatur.
Jane Street memilih hyperparameter untuk validasi dan melaporkan peningkatan
held-out dengan skala; perbedaan kondisi itu harus tetap eksplisit.

Tiga kapasitas hanya memiliki satu titik interior. Pilihan dalam grid bukan
optimum global. Tidak ada dropout baru atau perubahan proporsi pola. Model dan
bobot menggunakan seed yang terkait. Tiga corpus mendukung deskripsi lintas
data yang lebih baik dari Stage 1, tetapi belum cukup untuk klaim universal.
Satu Pythia size/seed dari Stage 1 tetap tidak membentuk kurva scaling. Tidak
ada publikasi, upload, pengeluaran cloud, klaim venue atau janji publikasi.
