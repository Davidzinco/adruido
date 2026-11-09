# Arduino Uno Face Tracking & Hand Gesture Identification System

Sistem pelacakan wajah (*Face Tracking Pan-Tilt Mechanism*) dan pengenalan gesture tangan (*Hand Gesture Identification*) secara *real-time* menggunakan kamera laptop sebagai sumber video dan mikrokontroler **Arduino Uno** sebagai pengendali aktuator mekanik 2-axis.

---

## 🌟 Fitur Utama

1. **Dual-Axis Face Tracking (Pan & Tilt)**:
   - Menggunakan model deep-learning **Google MediaPipe BlazeFace (LiteRT)** untuk mendeteksi wajah dengan kecepatan tinggi (>30 FPS) dan akurasi tinggi.
   - Algoritma kontrol proporsional dilengkapi fitur **Deadzone** dan **Smoothing EMA (Exponential Moving Average)** untuk meredam jitter dan mencegah getaran mikro pada servo.

2. **Hand Gesture Identification**:
   - Mengenali gesture tangan secara *real-time* berbasis **MediaPipe Gesture Recognizer** (21 Titik Landmark Tangan).
   - Dilengkapi filter **Debouncing** untuk mencegah flicker atau kesalahan deteksi sesaat.
   - Mengintegrasikan gesture tangan untuk mengontrol mode pelacakan secara langsung tanpa menyentuh keyboard/mouse.

3. **Interactive HUD (Heads-Up Display)**:
   - Tampilan visual overlay bergaya *cyberpunk HUD* langsung pada jendela kamera.
   - Target reticle pada wajah dengan garis vektor deviasi kesalahan.
   - Kerangka 21 landmark jari tangan dengan badge nama gesture dan persentase keyakinan.
   - Meteran sudut sudut servo Pan & Tilt, indikator status koneksi Serial, dan counter FPS.

4. **Komunikasi Serial Non-Blocking yang Handal**:
   - Mendeteksi port COM Arduino Uno secara otomatis (*Auto-Detect*).
   - Mode Simulasi: Jika Arduino belum dipasang, program tetap dapat dijalankan penuh di laptop untuk menguji kamera dan deteksi AI.
   - Mekanisme Failsafe Timeout pada Arduino untuk mencegah servo hilang kendali jika kabel USB terlepas.
   - Pergerakan servo diperhalus pada sisi Arduino (*Linear Interpolation*) untuk mencegah hentakan mekanik.

---

## 🤖 Daftar Gesture & Aksinya

| No | Gesture Tangan | Tampilan HUD | Respon Sistem / Aksi Arduino |
| :-: | :--- | :--- | :--- |
| **1** | **Open Palm** (Telapak Terbuka) | `[OPEN_PALM] Tracking Aktif` | Melanjutkan (*Resume*) pelacakan wajah |
| **2** | **Closed Fist** (Kepalan Tangan) | `[CLOSED_FIST] Pause / Lock` | Mengunci posisi servo saat ini (*Hold/Pause*) |
| **3** | **Victory / Peace** (Dua Jari V) | `[VICTORY] Reset Tengah` | Mengembalikan posisi servo ke titik tengah netral (90°, 90°) |
| **4** | **Thumbs Up** (Jempol Atas) | `[THUMB_UP] Apresiasi / Nod` | Menjalankan animasi servo mengangguk (*Nod Motion*) |
| **5** | **Pointing Up** (Telunjuk Menunjuk) | `[POINTING_UP] Fokus / Pointer` | Mode fokus target & kedip LED cepat |
| **6** | **Thumbs Down** (Jempol Bawah) | `[THUMB_DOWN] Standby` | Mode standby |

---

## 🛠️ Kebutuhan Hardware

1. **Board Arduino Uno** (R3 / SMD / Kompatibel) + Kabel USB Tipe B.
2. **2x Motor Servo** (TowerPro SG90 micro-servo atau MG90S metal gear).
3. **Mekanisme Pan-Tilt Bracket 2-Axis** (Braket servo 3D printed atau akrilik).
4. **Sumber Daya Eksternal 5V (1A - 2A)** (Adaptor 5V / Powerbank / Modul Breadboard Power Supply).
5. **Kabel Jumper** (Male-to-Male & Male-to-Female) + Breadboard.
6. **Laptop dengan Webcam bawaan** (atau USB Webcam eksternal).

---

## 🔌 Skema Rangkaian (Wiring Diagram)

Silakan lihat dokumentasi lengkap di file [`CIRCUIT_DIAGRAM.md`](file:///c:/Users/David/Documents/adruido/CIRCUIT_DIAGRAM.md).

Ringkasan koneksi pin:
- **Servo 1 (Pan / Horisontal)**:
  - Kabel Kuning / Sinyal -> **Pin D9 (PWM) Arduino**
  - Kabel Merah (VCC) -> **+5V Eksternal**
  - Kabel Coklat / Hitam (GND) -> **GND Eksternal & GND Arduino** (*Common Ground*)
- **Servo 2 (Tilt / Vertikal)**:
  - Kabel Kuning / Sinyal -> **Pin D10 (PWM) Arduino**
  - Kabel Merah (VCC) -> **+5V Eksternal**
  - Kabel Coklat / Hitam (GND) -> **GND Eksternal & GND Arduino** (*Common Ground*)
- **LED Indikator Gesture (Opsional)**:
  - Anoda (+) melalui resistor 220Ω -> **Pin D8 Arduino**
  - Katoda (-) -> **GND Arduino**

> [!WARNING]
> **PENTING: Jangan menyambungkan VCC servo langsung ke pin 5V Arduino Uno!**
> Arus puncak servo yang besar dapat menyebabkan Arduino Uno restart terus menerus (*brown-out reset*). Selalu gunakan catu daya 5V eksternal dengan *GND bersama (Common Ground)*.

---

## 📁 Struktur Direktori

```text
adruido/
├── arduino/
│   └── face_hand_tracker/
│       └── face_hand_tracker.ino     # Kode Sketch C++ Arduino Uno
├── models/
│   ├── blaze_face_short_range.tflite # Model AI Deteksi Wajah MediaPipe
│   └── gesture_recognizer.task       # Model AI Pengenal Gesture MediaPipe
├── python/
│   ├── config.py                     # Parameter konfigurasi, batas sudut & gain
│   ├── model_downloader.py          # Auto-downloader model jika belum tersedia
│   ├── tracker.py                    # Algoritma Face Tracking & Deadzone PID
│   ├── gesture_recognizer.py         # Ekstraksi Landmark & Gesture Classifier
│   ├── serial_comm.py                # Driver USB Serial & Auto-detection
│   ├── visualizer.py                 # Antarmuka Grafis HUD & Video Overlay
│   ├── main.py                       # Skrip eksekusi utama aplikasi
│   └── requirements.txt              # Daftar paket library Python
├── CIRCUIT_DIAGRAM.md                # Dokumentasi detail skema dan pinout
├── README.md                         # Dokumentasi panduan lengkap
└── run.bat                           # Launcher 1-klik untuk Windows
```

---

## 🚀 Panduan Menjalankan Proyek

### Langkah 1: Upload Program ke Arduino Uno

1. Buka aplikasi **Arduino IDE** di komputer.
2. Buka file sketsa:
   `c:\Users\David\Documents\adruido\arduino\face_hand_tracker\face_hand_tracker.ino`
3. Pilih board: **Tools > Board > Arduino AVR Boards > Arduino Uno**.
4. Pilih port: **Tools > Port > COMx** (sesuai nomor port Arduino Anda).
5. Klik tombol **Upload** (tanda panah ke kanan).
6. Setelah upload selesai (*Done uploading*), tutup jendela *Serial Monitor* di Arduino IDE agar port COM tidak sibuk saat diakses oleh Python.

### Langkah 2: Menjalankan Program Python di Laptop

#### Cara Cepat (Windows):
Cukup **klik ganda (double-click)** pada file:
`run.bat`

#### Cara Manual melalui Terminal:
1. Buka Terminal / PowerShell di folder proyek ini:
   ```powershell
   cd c:\Users\David\Documents\adruido
   ```
2. Pastikan virtual environment aktif:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
3. Jalankan aplikasi:
   ```powershell
   python python\main.py
   ```

---

## ⚙️ Opsi Perintah Tambahan (Command-Line Flags)

Anda dapat menyesuaikan parameter eksekusi menggunakan argumen:

- Menjalankan dalam **Mode Simulasi** (tanpa Arduino terhubung):
  ```powershell
  python python\main.py --no-serial
  ```

- Menentukan port COM Arduino secara spesifik:
  ```powershell
  python python\main.py --port COM4
  ```

- Menggunakan kamera webcam eksternal (indeks 1):
  ```powershell
  python python\main.py --camera 1
  ```

---

## ⌨️ Pintasan Keyboard Saat Aplikasi Berjalan

- `Q` atau `ESC`: Keluar dari program secara aman.
- `R`: Reset posisi sudut servo ke pusat netral (90°, 90°).
- `P`: Jeda (*Pause*) / Lanjutkan pelacakan servo.
- `T`: Mengaktifkan / menonaktifkan pelacakan wajah (*Toggle Face Tracking*).
- `G`: Mengaktifkan / menonaktifkan identifikasi gesture (*Toggle Gesture*).
- `S`: Menyambungkan ulang port Serial jika sempat terlepas.

---

## 🔧 Panduan Kalibrasi & Penyetelan (Tuning)

Semua pengaturan utama tersimpan rapi di file [`python/config.py`](file:///c:/Users/David/Documents/adruido/python/config.py):

1. **Arah Pergerakan Servo Terbalik**:
   - Jika servo Pan bergerak menjauh saat wajah ke kanan, ubah:
     ```python
     INVERT_PAN = True
     ```
   - Jika servo Tilt bergerak ke atas saat wajah menunduk ke bawah, ubah:
     ```python
     INVERT_TILT = False
     ```

2. **Menyesuaikan Kecepatan Respon**:
   - Ubah `KP_PAN` dan `KP_TILT` (nilai default: `0.038`).
   - Nilai lebih besar membuat respon lebih agresif; nilai lebih kecil membuat respon lebih lembut.

3. **Menghilangkan Getaran Servo (Jitter)**:
   - Perbesar area Deadzone di `DEADZONE_X = 40` dan `DEADZONE_Y = 35`.
   - Naikkan nilai smoothing `FACE_SMOOTH_FACTOR = 0.8`.

4. **Batasan Sudut Fisik**:
   - Jika braket fisik servo membentur kabel atau rangka pada sudut tertentu, batasi di `config.py` dan di `face_hand_tracker.ino` (misal: `PAN_MIN = 30`, `PAN_MAX = 150`).
