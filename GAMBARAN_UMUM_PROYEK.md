# Gambaran Umum Proyek — Smart Directional Fan
### Kipas Otomatis Berbasis Pelacakan Wajah & Sensor Jarak (Arduino Uno)

> Dokumen ini dibuat sebagai **bahan pertimbangan internal Kelompok 3**, bukan laporan final.
> Isinya: latar belakang, tujuan, cara kerja, serta catatan hal-hal yang perlu diputuskan sebelum proyek dilanjutkan.

---

## 0. Verifikasi Ulang File Presentasi

File yang saat ini ada di folder proyek:

| Item | Keterangan |
| :--- | :--- |
| Nama file | `Jelajah Dunia Digital Presentasi (1).pdf` |
| Ukuran | 14.367.191 byte (± 14,4 MB) |
| Terakhir diubah | 13 November 2026, 17.23 |
| Jumlah halaman | 4 halaman |

Isi yang terbaca:

1. **Halaman 1** — Judul: *Proyek Arduino — Smart Directional Fan*, Kelompok 3.
2. **Halaman 2** — Anggota: Adhinda Arnelita (02), Annisa Cahya (09), David Zinco (15), Miracle Timothy (27).
3. **Halaman 3** — Latar belakang: pengguna enggan beranjak untuk mengatur arah kipas manual yang kurang tepat sasaran → dirancang prototipe *Smart Directional Fan* berbasis Arduino dengan motor servo.
4. **Halaman 4** — Tujuan proyek (4 poin): melatih penerapan mikrokontroler & sensor, menerapkan solusi otomatisasi, menampilkan suhu ruangan & jarak objek real-time pada LCD, dan mengoptimalkan penggunaan energi agar hembusan lebih tepat sasaran. *(Isi slide ini masih menyebut LCD & suhu; lihat keputusan revisi di Bab 6.)*

Catatan: slide **belum memuat cara kerja/workflow**. Bagian 4 dokumen ini mengisinya.

---

## 1. Ringkasan Proyek

Kipas angin pintar yang **mengarahkan sendiri hembusan angin ke posisi pengguna** dan **menyalakan/mematikan dirinya secara otomatis** berdasarkan keberadaan orang di depannya.

Sistem dibagi dua bagian:

- **Otak persepsi (laptop/Python):** kamera mendeteksi wajah, menghitung arah wajah, lalu mengirim perintah sudut ke Arduino.
- **Otak kendali (Arduino Uno):** menggerakkan servo pengarah kipas, membaca sensor jarak ultrasonik, dan mengendalikan relay kipas.

| Aspek | Keterangan |
| :--- | :--- |
| Jenis | Prototipe / proyek mata pelajaran mikrokontroler |
| Pengendali | Arduino Uno |
| Aktuator | 1× motor servo (arah horizontal) + kipas DC via relay/MOSFET |
| Sensor | HC-SR04 (jarak) + kamera/webcam (deteksi wajah) |
| Pemrosesan AI | Python + OpenCV + MediaPipe BlazeFace (di laptop) |
| Komunikasi | USB Serial, 115200 baud |
| Target pengguna | 1 orang, penggunaan indoor, jarak ≤ 50 cm |

---

## 2. Latar Belakang

### 2.1 Masalah yang mendasari

Kipas angin konvensional bekerja dengan arah yang **tetap** dan harus diatur **secara manual** melalui tombol atau *knob* pada badan kipas. Dalam praktik sehari-hari, kondisi ini menimbulkan beberapa masalah:

1. **Arah hembusan cepat tidak relevan lagi.** Ketika pengguna berpindah posisi — bergeser di kursi, berpindah sisi meja, atau berbaring — kipas tetap menyembur ke arah lama. Pengguna harus berulang kali beranjak dan memutar badan kipas.
2. **Hembusan sering tidak tepat sasaran.** Sudut putaran kipas manual biasanya terbatas dan tidak presisi, sehingga angin banyak terbuang ke dinding atau ruang kosong. Energi listrik terpakai, tetapi kenyamanan yang didapat tidak sebanding.
3. **Kipas sering dibiarkan menyala.** Karena tidak ada mekanisme otomatis, kipas tetap berputar meski ruangan sudah kosong. Ini pemborosan energi yang kecil per kejadian, tetapi terjadi terus-menerus.
4. **Ada kelompok pengguna yang sulit menjangkau kipas.** Lansia, pengguna kursi roda, atau orang yang sedang bekerja dengan kedua tangan penuh (mengetik, memasak, memegang bayi) mengalami kesulitan nyata untuk mengatur arah kipas setiap kali posisinya berubah.

### 2.2 Peluang teknologi

Beberapa perkembangan membuat solusi ini layak dibuat sebagai prototipe murah:

- **Arduino Uno** sudah menjadi platform standar pembelajaran mikrokontroler: harga terjangkau, dokumentasi luas, dan cukup untuk mengendalikan servo serta membaca sensor secara *real-time*.
- **Sensor ultrasonik HC-SR04** sangat murah dan memadai untuk mendeteksi keberadaan objek pada jarak dekat (2–400 cm) — cocok sebagai saklar kehadiran.
- **Computer vision sudah ringan.** Model deteksi wajah seperti MediaPipe BlazeFace mampu berjalan **> 30 FPS di laptop biasa tanpa GPU**, sehingga laptop yang sudah dimiliki siswa bisa langsung dipakai sebagai unit pemrosesan, tanpa perangkat tambahan.
- **Motor servo** memberi gerak sudut yang presisi dan mudah dikendalikan dengan satu pin PWM.

### 2.3 Gagasan solusi

Dengan menggabungkan ketiga kemampuan tersebut, lahirlah gagasan **Smart Directional Fan**:

> Kipas yang **"melihat"** posisi pengguna lewat kamera, **"merasakan"** kehadiran pengguna lewat sensor jarak, lalu **"mengarahkan diri"** lewat servo — tanpa pengguna perlu menyentuh apa pun.

Pembagian peran dibuat sederhana dan jelas:

- **Kamera menentukan _ke mana_ angin diarahkan** (posisi wajah → sudut servo).
- **Sensor jarak menentukan _kapan_ kipas menyala** (ada orang ≤ 50 cm → relay ON).
- **Arduino mengeksekusi** kedua keputusan itu secara halus dan *non-blocking*.

### 2.4 Mengapa proyek ini layak dipertimbangkan

- **Relevan dengan masalah nyata** dan mudah dijelaskan kepada orang awam.
- **Menggabungkan dua bidang kompetensi** sekaligus: *embedded system* (Arduino, sensor, aktuator, daya) dan *computer vision* (deteksi wajah, kontrol proporsional) — nilai edukatifnya tinggi.
- **Biaya komponen relatif rendah** dan sebagian besar sudah tersedia di lab/sekolah.
- **Prototipe sudah berjalan** (kode Arduino dan Python tersedia di repositori), bukan sekadar konsep di atas kertas.

---

## 3. Tujuan Proyek

### 3.1 Tujuan umum

Membuat prototipe kipas angin yang mampu **mengarahkan hembusan secara otomatis mengikuti posisi pengguna** dan **mengatur dirinya sendiri (nyala/mati)** berdasarkan keberadaan orang, sebagai penerapan konsep mikrokontroler, sensor, dan *computer vision* untuk menyelesaikan masalah praktis sehari-hari.

### 3.2 Tujuan khusus

| No | Tujuan | Indikator keberhasilan |
| :-: | :--- | :--- |
| 1 | **Pelacakan arah otomatis** — servo mengarahkan kipas mengikuti pergeseran posisi wajah pengguna secara horizontal | Wajah digeser ±40 cm dari tengah, kipas mengikuti dalam < 2 detik dan wajah kembali berada di area tengah layar |
| 2 | **Otomatisasi nyala/mati** — kipas menyala saat pengguna berada dalam jangkauan dan mati saat pengguna pergi | Kipas ON pada jarak ≤ 50 cm; OFF otomatis setelah ±2,5 detik tanpa objek (tanpa kedip mati-nyala) |
| 3 | **Monitoring kondisi secara real-time** — jarak objek, status kipas, dan sudut servo ditampilkan pada **layar laptop** (HUD) | Data pada HUD berubah sesuai kondisi fisik tanpa lag yang terlihat; tidak memerlukan LCD tambahan |
| 4 | **Gerakan halus tanpa getaran** — servo tidak bergetar saat wajah diam | Tidak ada osilasi/jitter saat pengguna diam di dalam area toleransi (*deadzone*) |
| 5 | **Penerapan konsep dasar mikrokontroler & sensor** (tujuan edukatif) | Seluruh rangkaian berjalan dari satu alur program yang dapat dijelaskan siswa satu per satu |
| 6 | **Efisiensi energi** — hembusan lebih tepat sasaran dan kipas tidak menyala saat ruangan kosong | Konsumsi daya saat tidak ada pengguna turun mendekati nol (kipas OFF) |

> **Catatan media tampilan:** informasi kondisi ditampilkan pada **layar laptop** melalui antarmuka HUD, bukan pada LCD tambahan. Dengan demikian proyek tidak memerlukan sensor suhu maupun modul LCD, dan slide presentasi perlu disesuaikan pada bagian ini.

### 3.3 Manfaat yang diharapkan

- **Praktis:** pengguna tidak perlu beranjak atau mengulurkan tangan untuk mengatur arah kipas.
- **Hemat energi:** kipas hanya menyala saat ada orang di depannya.
- **Inklusif:** membantu pengguna dengan keterbatasan mobilitas.
- **Edukatif:** menjadi media belajar integrasi perangkat keras, sensor, aktuator, komunikasi serial, dan AI ringan.

---

## 4. Cara Kerja / Workflow Sistem

### 4.1 Arsitektur sistem

Sistem memisahkan **persepsi** (berat, di laptop) dari **kendali** (ringan, di Arduino). Pemisahan ini penting karena Arduino Uno tidak sanggup menjalankan model AI, sedangkan laptop tidak bisa memberi sinyal PWM sekuat dan sepresisi mikrokontroler.

```text
                    +---------------------------+
                    |        WEBCAM             |
                    +------------+--------------+
                                 | frame video 640x480
                                 v
+-------------------------------------------------------------+
|  LAPTOP / PYTHON  (Vision & Decision Unit)                  |
|  1. Deteksi wajah (MediaPipe BlazeFace)                     |
|  2. Hitung deviasi wajah dari titik tengah                  |
|  3. Filter deadzone + smoothing -> tentukan sudut servo     |
|  4. Tampilkan HUD (kotak wajah, jarak, status kipas, FPS)   |
+----------------+-------------------------^------------------+
                 | USB Serial 115200       |  telemetri
                 | "<PAN,90,0>"            |  "$DATA,jarak,kipas,sudut"
                 v                         |
+-------------------------------------------------------------+
|  ARDUINO UNO  (Hardware Control Unit)                       |
|  - Terima target sudut -> gerakkan servo secara bertahap    |
|  - Baca HC-SR04 tiap 80 ms -> tentukan ON/OFF kipas         |
|  - Kirim telemetri tiap 300 ms                              |
+------+------------------+------------------+----------------+
       | PWM D2           | Digital D7       | Trig D12 / Echo D13
       v                  v                  v
 +-----------+     +--------------+     +-----------+
 | SERVO     |     | RELAY /      |     | HC-SR04   |
 | (arah     |     | MOSFET       |     | (deteksi  |
 |  kipas)   |     |              |     |  jarak)   |
 +-----+-----+     +------+-------+     +-----------+
       |                  |
       v                  v
  [Kepala kipas]     [Kipas DC 5V/12V]
```

### 4.2 Pembagian tugas komponen

| Komponen | Peran | Detail teknis |
| :--- | :--- | :--- |
| Webcam laptop | Mata sistem | Resolusi 640×480, mode *mirror* agar gerak terasa natural |
| Python (OpenCV + MediaPipe) | Persepsi & keputusan | Deteksi wajah, hitung sudut, kirim perintah, tampilkan HUD |
| Arduino Uno | Eksekutor *real-time* | Servo, sensor jarak, relay, protokol serial |
| Servo (SG90/MG90S) | Pengarah angin | Sinyal di **D2**, catu daya **5V eksternal** + *common ground* |
| HC-SR04 | Deteksi kehadiran | **TRIG D12**, **ECHO D13**, jangkauan 2–400 cm |
| Relay/MOSFET | Saklar kipas | Sinyal **D7**, memutus/menyambung jalur daya kipas |
| Kipas DC | Aktuator akhir | 5V/12V, **tidak** diambil dari pin Arduino |

### 4.3 Alur kerja saat sistem berjalan

**A. Tahap persiapan (sekali di awal)**

1. Rangkaian dirakit sesuai skema; servo dan kipas memakai adaptor eksternal dengan GND disatukan ke Arduino.
2. Program `arduino/kipas_otomatis/kipas_otomatis.ino` di-*upload* ke Arduino Uno.
3. Port Serial Monitor di Arduino IDE ditutup agar port COM tidak bentrok.
4. Program Python dijalankan (`run_test_servo.bat` atau `python python/main_kipas.py`).

**B. Tahap inisialisasi**

5. Arduino menyalakan Serial 115200, menetapkan pin, memosisikan servo di **90° (tengah)**, dan memastikan kipas **OFF**.
6. Python mendeteksi port COM Arduino secara otomatis, membuka kamera, dan memuat model deteksi wajah.

**C. Siklus utama (berjalan ±30 kali per detik)**

7. Kamera mengambil satu *frame*, lalu di-*mirror* secara horizontal.
8. Model mendeteksi wajah dan menghasilkan kotak wajah beserta titik tengahnya.
9. Python menghitung **error** = posisi horizontal wajah − titik tengah layar.
10. Error disaring dengan **smoothing EMA** (faktor 0,7) agar tidak kaget/bergetar.
11. Jika error masih di dalam **deadzone** (±35 px), sudut servo **tidak diubah** — ini yang mencegah jitter.
12. Jika di luar deadzone, sudut target dihitung dengan **gain proporsional (Kp = 0,038)** lalu dibatasi pada rentang aman.
13. Sudut target dikirim ke Arduino dalam paket `<PAN,90,0>`.
14. Arduino menerima paket, memvalidasi, dan menyimpan sudut target.
15. Servo tidak melompat langsung, tetapi bergerak **1° setiap 30 ms** (±33°/detik) menuju target — gerakan terlihat halus dan tidak menyentak.

**D. Siklus sensor & aktuator (paralel, *non-blocking*)**

16. Setiap **80 ms**, Arduino memancarkan pulsa ultrasonik dan membaca pantulannya (timeout 20 ms; nilai di luar 2–400 cm diabaikan).
17. Jika jarak ≤ **50 cm**, kipas dinyalakan dan timer kehadiran di-*reset*.
18. Jika tidak ada objek selama **2,5 detik**, kipas dimatikan — jeda ini (*off-delay hysteresis*) mencegah kipas berkedip mati-nyala saat pembacaan sensor sesaat terganggu.

**E. Umpan balik ke pengguna**

19. Setiap **300 ms**, Arduino mengirim telemetri `$DATA,jarak,status_kipas,sudut`.
20. Python membacanya dan memperbarui HUD: kotak wajah, garis deviasi, reticle tengah, jarak aktual, status kipas, sudut servo, FPS, dan status koneksi.
21. Pengguna dapat menekan **R** (reset ke tengah), **P** (jeda/lanjut), **F** (balik kamera), **Q/ESC** (keluar).

### 4.4 Logika keputusan dalam bentuk ringkas

```text
                  ┌──────────────────────────────┐
   frame kamera → │ Ada wajah?                   │
                  └───────┬──────────────┬───────┘
                    ya    │              │ tidak
                          v              v
              ┌───────────────────┐   ┌──────────────────────┐
              │ |error| > deadzone│   │ Pertahankan sudut    │
              └───┬───────────┬───┘   │ terakhir (tidak      │
               ya │           │ tidak │ mengubah apa pun)    │
                  v           v       └──────────────────────┘
        ┌─────────────────┐  ┌────────────────────┐
        │ Sudut baru =    │  │ Sudut tetap        │
        │ sudut ± Kp·err  │  │ (anti-jitter)      │
        └────────┬────────┘  └─────────┬──────────┘
                 └────────┬────────────┘
                          v
                  Kirim <PAN> ke Arduino ──► servo bergerak bertahap

  ┌──────────────────────────────────────────────────────────┐
  │ Jarak ≤ 50 cm ?  ── ya ──►  KIPAS ON, reset timer 2,5 s  │
  │                    tidak ─►  timer habis? ─ ya ─► KIPAS OFF│
  └──────────────────────────────────────────────────────────┘
```

### 4.5 Kontrol & mode pengguna

| Input | Fungsi |
| :--- | :--- |
| **R** | Kembalikan servo ke posisi tengah (90°) |
| **P** | Jeda / lanjutkan pelacakan |
| **F** | Balik (*mirror*) tampilan kamera |
| **Q / ESC** | Keluar dengan aman (kamera & port Serial ditutup) |
| **Mode simulasi** (`--no-serial`) | Menjalankan kamera + AI tanpa Arduino, untuk uji logika di laptop |

### 4.6 Workflow pengembangan (tahapan pengerjaan)

| Tahap | Aktivitas | Keluaran |
| :-: | :--- | :--- |
| 1 | **Studi masalah & perumusan kebutuhan** | Daftar masalah, target pengguna, batasan alat |
| 2 | **Perancangan sistem** | Arsitektur, skema wiring, protokol serial, parameter kontrol |
| 3 | **Uji komponen satuan** | Servo bisa sweep, HC-SR04 akurat vs penggaris, relay mengikuti sinyal |
| 4 | **Pengembangan firmware** | `kipas_otomatis.ino` (non-blocking, parser serial, telemetri) |
| 5 | **Pengembangan program Python** | Deteksi wajah, tracker, HUD, koneksi serial |
| 6 | **Integrasi bertahap** | (a) servo manual → (b) tracking wajah → (c) sensor jarak → (d) kipas |
| 7 | **Kalibrasi & tuning** | Deadzone, Kp, batas sudut, ambang jarak, kecepatan servo |
| 8 | **Pengujian skenario** | Data jarak, pergeseran, kondisi cahaya, kegagalan koneksi |
| 9 | **Dokumentasi & presentasi** | Laporan, slide, demo alat |

### 4.7 Skenario pengujian yang disarankan

| Uji | Cara | Yang diamati |
| :--- | :--- | :--- |
| Jarak | Berdiri di 20 / 40 / 50 / 70 / 100 cm | Kipas ON/OFF sesuai ambang 50 cm |
| Arah | Geser ke kiri–kanan ±20–50 cm | Servo mengikuti, wajah kembali ke tengah |
| Diam | Berdiri diam 30 detik | Tidak ada jitter/osilasi servo |
| Cahaya | Ruangan terang, redup, lampu dari belakang | Deteksi wajah tetap stabil atau batasannya jelas |
| Banyak orang | Dua orang di depan sensor | Perilaku sistem dapat dijelaskan (siapa yang diikuti) |
| Kegagalan | Cabut kabel USB saat berjalan | Sistem berhenti aman, tidak bergerak liar |

---

## 5. Kriteria Keberhasilan (Definisi "Selesai")

Proyek dapat dinyatakan berhasil jika seluruh poin berikut terpenuhi:

- [ ] Kipas menyala ≤ 50 cm dan mati ±2,5 detik setelah pengguna menjauh.
- [ ] Kipas mengikuti pergeseran wajah ke kiri/kanan secara halus.
- [ ] Tidak ada getaran servo saat pengguna diam.
- [ ] Data jarak, status kipas, dan sudut servo tampil **di layar laptop** dan sesuai kondisi fisik.
- [ ] Sistem dapat dijalankan ulang dari kondisi mati total tanpa error.
- [ ] Seluruh anggota mampu menjelaskan alur kerja alat dari sensor sampai aktuator.

---

## 6. Catatan Penting untuk Dipertimbangkan Kembali

Bagian ini **tidak** diminta secara eksplisit, tetapi penting agar keputusan kelompok tidak salah arah.

### 6.1 Selisih antara isi slide dan implementasi saat ini

| Klaim di slide | Kondisi implementasi | Implikasi |
| :--- | :--- | :--- |
| "Menampilkan **suhu ruangan** dan jarak objek pada **LCD**" | **Tidak ada sensor suhu** (DHT) dan **tidak ada LCD**. Sesuai keputusan kelompok, informasi jarak, status kipas, dan sudut servo ditampilkan pada **HUD layar laptop**. | Slide perlu **direvisi** agar sesuai dengan alat. Menambah DHT + LCD tidak lagi menjadi kebutuhan. |
| "Mengarahkan tiupan angin secara otomatis" | Servo hanya menggerakkan **sumbu horizontal (pan)**, dengan batas sempit **75°–105°** (±15°). Sumbu vertikal (tilt) tidak dipakai pada mode kipas. | Jangkauan arah masih terbatas. Perlu uji apakah cukup untuk pergerakan pengguna di meja. |
| (Tidak ada di slide) | Repositori juga memuat **pengenalan gesture tangan** (Open Palm, Fist, Victory, dll.) | Fitur ini di luar cakupan presentasi. Harus diputuskan: dimasukkan atau tidak. |

### 6.2 Keterbatasan teknis yang perlu diketahui

1. **Bukan alat mandiri.** Sistem butuh laptop + webcam + kabel USB. Jika kabel lepas, servo berhenti di posisi terakhir dan kipas tetap mengikuti sensor (belum ada *failsafe* serial di sketch kipas).
2. **Sudut servo lebih sempit daripada sudut pandang kamera.** Kamera bisa "melihat" lebih lebar daripada kemampuan servo memutar kipas, sehingga ada kondisi wajah masih terdeteksi tetapi kipas sudah mentok.
3. **Kipas menyala hanya berdasarkan jarak, bukan suhu.** Kipas bisa menyala di ruangan dingin. Menambahkan sensor suhu akan membuat logika lebih masuk akal (misal: ON jika ada orang **dan** suhu > ambang).
4. **Sensor ultrasonik memiliki keterbatasan.** Sudut pancar sempit, bisa salah baca pada permukaan tertentu, dan jika ada dua orang sistem mengikuti objek terdekat.
5. **Ketergantungan pencahayaan.** Deteksi wajah menurun saat ruangan gelap atau wajah tertutup masker.
6. **Beban mekanik servo.** SG90 kecil mudah *stall* jika menahan kepala kipas yang berat/bergetar; MG90S atau servo torsi lebih besar lebih aman, ditambah bantalan (*bearing*) pada poros.
7. **Getaran kipas** dapat mengganggu kestabilan gambar kamera dan mempercepat keausan servo.
8. **Privasi.** Kamera aktif terus-menerus; perlu penjelasan bahwa pemrosesan dilakukan lokal dan tidak ada rekaman yang disimpan.

### 6.3 Keputusan yang perlu diambil kelompok

| No | Pertanyaan keputusan | Opsi | Rekomendasi |
| :-: | :--- | :--- | :--- |
| 1 | Apakah **LCD + sensor suhu** wajib ada? | (a) Tambah DHT11/DHT22 + LCD I2C; (b) tetap HUD laptop dan revisi slide | **(b) — sudah diputuskan kelompok:** tampilan cukup di HUD laptop |
| 2 | Apakah **suhu** ikut menentukan kipas menyala? | (a) Hanya jarak (sekarang); (b) jarak **dan** suhu | (b) lebih logis dan memanfaatkan sensor suhu |
| 3 | Apakah **gesture tangan** masuk cakupan? | (a) Ya, sebagai fitur tambahan; (b) tidak, fokus pada kipas | (b) untuk menjaga fokus dan stabilitas demo |
| 4 | Apakah servo perlu **tilt** (naik-turun)? | (a) Pan saja; (b) pan + tilt | (a) kecuali mekanik dan daya memadai |
| 5 | Perluas **batas sudut servo**? | (a) Tetap ±15°; (b) perluas setelah uji mekanik | (b), dengan pengaman kabel/rangka |
| 6 | Perlu **mode mandiri** tanpa laptop? | (a) Tidak (tetap pakai laptop); (b) ya, pindah ke Raspberry Pi/ESP32-CAM | (a) sesuai skala prototipe |

---

## 7. Alternatif Cakupan (Jika Ingin Disederhanakan)

- **Versi minimum (paling aman):** sensor jarak + relay + kipas (otomatis nyala/mati) **tanpa** face tracking. Paling mudah didemokan, tetapi tidak lagi "directional".
- **Versi sesuai slide:** tambahkan DHT + LCD pada versi minimum, tanpa AI. Cepat, murah, tetapi kehilangan aspek *computer vision*.
- **Versi saat ini (direkomendasikan):** face tracking + sensor jarak + relay, dengan HUD laptop sebagai pengganti LCD. Paling sesuai semangat "Smart Directional Fan".
- **Versi lengkap:** versi saat ini + DHT + LCD + gesture. Paling menarik, tetapi risiko waktu dan kompleksitas paling tinggi.

---

## 8. Kesimpulan Singkat

Proyek ini menjawab masalah nyata yang sederhana — **kipas yang tidak mengikuti penggunanya dan sering menyala tanpa perlu** — dengan solusi yang memanfaatkan teknologi yang sudah tersedia dan terjangkau. Nilai utamanya bukan pada kecanggihan alat, melainkan pada **integrasi yang berhasil antara sensor, aktuator, mikrokontroler, dan pemrosesan citra** dalam satu alur kerja yang dapat dijelaskan dan diuji.

Dua keputusan masih terbuka sebelum proyek dilanjutkan: **(1)** apakah gesture tangan diikutkan, dan **(2)** seberapa luas jangkauan arah yang ingin dicapai. Sementara itu, media tampilan **sudah diputuskan tetap di layar laptop**, sehingga slide bagian "suhu ruangan & LCD" perlu direvisi.
