# Hasil eksekusi PILOT_NOTES.md

28 September 2026 · seluruh training lokal di RTX 3050 Laptop 4 GB melalui Ubuntu WSL 2.

## Status pekerjaan

Semua tahap dalam catatan sudah dijalankan: 10 checkpoint pretraining sintetis,
18 run kalibrasi, 3 run diagnostik durasi/inisialisasi, 30 run konfirmasi, dan
2 run teks publik. Totalnya **53 run adaptasi**, di luar pretraining.

**Hasil utama:** puncak p* pada kapasitas menengah muncul di ketiga seed untuk
data campuran pada epoch 60. Ini mendukung kemungkinan mekanisme dalam tugas
terkontrol ini. Hasil belum membuktikan penjelasan Jane Street pada model bahasa
besar dengan regularisasi optimal.

## 1. Pretraining dan pemilihan konfigurasi

Pretraining memakai 2.048 contoh shared-rule, bobot seragam, empat epoch.
Namespace kunci contoh pretraining, adaptasi, validasi, dan tes terpisah.
Checkpoint pretrained yang sama dipakai oleh arm berpasangan; state AdamW
direset ketika adaptasi dimulai. Seluruh pretraining mencapai akurasi validasi
shared-rule 100%.

Kalibrasi memakai 512 contoh adaptasi dan 256 validasi. Grid tiga learning rate
× tiga clipping × dua pembobotan menghasilkan 18 run. Kriteria pemilihan adalah
rata-rata validation NLL kedua arm pada epoch 30, bukan p* atau test loss.
Pilihan: **learning rate 0,0001, clipping 1, weight decay 0,1**; skor 2,04087.

Clipping tetap sering aktif. Menonaktifkannya tidak otomatis menjadi pilihan
terbaik pada grid ini; satu seed kalibrasi tidak cukup untuk memisahkan semua
interaksi optimizer, clipping, dan kapasitas.

![Kalibrasi](calibration.png)

## 2. Memorisasi sudah dapat diukur

Pada arm pretrained dengan bobot acak, p* pada epoch 30/60/120 adalah
0,0959 / 0,1911 / 0,0672. Akurasi instance training meningkat dari 18,4% menjadi
46,3% dan 83,1%. Kontrol uniform mencapai 64,5% pada epoch 60 dan 99,3% pada 120.
Gate learnability pertama kali lolos pada **60 epoch**.

Validation loss memburuk ketika memorisasi meningkat. Durasi 60 dipilih untuk
mengamati mekanisme; ini bukan early stopping yang optimal untuk generalisasi.
Arm cold-start juga menunjukkan kenaikan lalu penurunan p* terhadap durasi.
Pretraining tidak terbukti sebagai syarat mutlak untuk fenomena tersebut.

![Diagnostik durasi](duration-diagnostics.png)

Kurva alokasi gain aktual dan fit eksponennya disimpan agar p* dapat diperiksa
bersama kualitas fit. Gain negatif tetap dipertahankan.

![Pemeriksaan fit](gain-fit.png)

## 3. Konfirmasi pada data baru

Konfigurasi dibekukan sebelum beralih ke seed data 2718. Tiga kapasitas dan tiga
seed training/bobot (42, 43, 44) dijalankan pada shared, structured, dan mixed.
Ada tiga kontrol uniform tambahan pada kapasitas menengah untuk mixed.
Tes dievaluasi sekali pada epoch akhir tetap, tanpa pemilihan konfigurasi dari tes.

**Mixed, epoch 60; rata-rata ± simpangan baku antar tiga seed:**

| Parameter | p* | Akurasi instance training | Validation NLL |
|---:|---:|---:|---:|
| 113,408 | 0.1355 ± 0.0113 | 15.4% | 2.2431 |
| 621,696 | 0.1906 ± 0.0057 | 42.6% | 2.6976 |
| 3,212,800 | 0.0565 ± 0.0077 | 81.2% | 3.1508 |

Selisih p* model menengah terhadap nilai terbesar dari kedua endpoint positif
pada ketiga seed: **0,0669; 0,0466; 0,0518**. Ini konsistensi deskriptif, bukan
uji signifikansi. Shared-only memberi p* hampir nol. Structured menunjukkan
puncak menengah pada epoch 30, sedangkan pada epoch 60 nilai terbesar berada
di kapasitas terkecil yang diukur.

![Kurva kapasitas](capacity-curves.png)

Tiga kapasitas hanya menyediakan satu lokasi puncak interior. Perubahan argmax
ke endpoint belum membuktikan pergeseran antara dua puncak interior. Klaim
kuat tentang pergeseran puncak dengan epoch masih memerlukan kapasitas tambahan.

## 4. Pemeriksaan pada model pretrained dan teks publik

Pythia-70M (70.426.624 parameter), seluruh parameter dilatih dalam float32,
tanpa LoRA. Data: 512 paragraf train, 128 validasi, 128 tes dari WikiText-2 raw;
masing-masing 129 token dan 128 target. Pemilihan deterministik paragraf panjang,
truncation, dan pembuangan duplikat token lintas split telah dicatat. Ini bukan
protokol benchmark WikiText standar; overlap dengan pretraining tidak diketahui.

Learning rate 0,00003 ditetapkan sebelum hasil dilihat, batch efektif 32,
clipping 1, weight decay 0,1, tiga epoch, seed 42. Tidak ada tuning dari tes.

| Bobot | p* akhir | Train NLL | Validation NLL | Test NLL |
|---|---:|---:|---:|---:|
| random | 0.3482 | 3.6178 | 4.5806 | 4.7951 |
| uniform | tidak terdefinisi | 3.0459 | 4.3737 | 4.5551 |

p* bobot acak naik **0,1905 → 0,2837 → 0,3482**. Baseline validation NLL kedua
arm adalah 4,3911. Hasil mengonfirmasi bahwa pipeline pengukuran berjalan pada
teks dan checkpoint pretrained. Satu ukuran model dan satu seed tidak
mengonfirmasi kurva kapasitas, mekanisme, atau keunggulan metode pembobotan.
Clipping terjadi pada semua update kedua arm.

![Pemeriksaan teks](text-check.png)

## 5. Sumber daya yang benar-benar terukur

- Sintetis: adaptasi dan evaluasi 51 run berjumlah 368,17 detik; puncak alokasi
  PyTorch 150,49 MiB dan reserved 184 MiB.
- Teks: kedua run berjumlah 154,99 detik; puncak alokasi 1.585,79 MiB
  (sekitar 1,55 GiB), reserved 1.652 MiB.
- Angka waktu berasal dari bagian program yang diinstrumentasi; tidak mencakup
  keseluruhan startup, unduhan, instalasi, pretraining, baseline evaluation, dan
  penyimpanan checkpoint. Angka memori tidak mencakup desktop/driver.

## 6. Batas klaim dan keputusan untuk paper

Jane Street melaporkan kenaikan performa held-out dengan kapasitas dan
menggunakan regularisasi yang dituning terhadap validasi. Pada data mixed kita,
validation loss justru meningkat dengan kapasitas. Karena itu hasil sekarang
paling tepat diposisikan sebagai **demonstrasi mekanisme pada tugas terkontrol
dengan memorisasi**, belum reproduksi kondisi regularisasi studi asal.

Batas lain: hanya tiga seed training pada satu corpus konfirmasi; weight decay
tetap; pretraining sintetis shared-only; proporsi pola berubah antarregime;
clipping sangat sering; dan pemeriksaan teks hanya satu model/seed.

Prioritas berikut untuk paper adalah menguji **apakah puncak tersebut bertahan
ketika setiap kapasitas dituning untuk generalisasi terbaik**. Bekukan grid
regularisasi, gunakan data baru, dan tambahkan kapasitas yang memungkinkan dua
puncak interior teramati. Tambahkan beberapa seed data independen. Perluasan
ini belum dijalankan dan tidak boleh diklaim sudah selesai.

Judul kerja yang sesuai bukti saat ini: *Controlled Pattern Complexity and
Non-Monotonic Sequence Weighting*. Klaim novelty dan kelayakan venue masih
memerlukan peninjauan literatur serta eksperimen tambahan.

## Audit dan reproduksi

- `all-checkpoints.csv`: seluruh checkpoint sintetis yang dievaluasi.
- `summary.json`, `text-summary.json`: hasil numerik dan keputusan gate.
- `AUDIT.json`: jumlah run, kesamaan baseline berpasangan, split, dan hash kode.
- `run-records.zip`: konfigurasi, hasil, bobot/loss per contoh, metadata data,
  kode, protokol, versi lingkungan, dan provenance teks; checkpoint model penuh
  tetap disimpan di workspace untuk menghindari arsip besar.
- `../PROTOCOL_STAGE1.md` dan `../TEXT_PROTOCOL.md`: protokol sebelum run.

Tidak ada model atau hasil training yang dipublikasikan ke layanan luar.

## Sumber

- [Studi Jane Street](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/)
- [Definisi estimator](https://blog.janestreet.com/a-study-of-sequence-weighting-at-scale/sequence-weighting-note.pdf)
- [Pythia-70M, EleutherAI](https://huggingface.co/EleutherAI/pythia-70m)
- [WikiText, Salesforce](https://huggingface.co/datasets/Salesforce/wikitext)

Revisi model: `a39f36b100fe8a5377810d56c3f4789b9c53ac42`.
Revisi data: `b08601e04326c79dfdd32d625aee71d232d685c3`.
Model berlisensi Apache-2.0; kartu data mencantumkan CC-BY-SA-3.0 dan GFDL.
