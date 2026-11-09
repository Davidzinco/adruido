# Panduan Teknis: Face Tracking & Hand Gesture ke Arduino Uno

Dokumen ini menjelaskan secara rinci:
1. **Bagaimana gesture tangan dideteksi dan dikirimkan ke Arduino**.
2. **Bagaimana mekanisme servo mengikuti pergerakan wajah pengguna**.
3. **Bagian kode mana saja yang perlu disesuaikan/diubah** sesuai kebutuhan fisik alat Anda.

---

## 1. Mekanisme Deteksi Gesture Tangan & Pengiriman ke Arduino

### A. Alur Kerja Deteksi Gesture (Di Sisi Laptop / Python)
1. **Kamera Laptop Mengambil Frame Video:**
   - Frame ditangkap oleh OpenCV (`cv2.VideoCapture`).
   - Frame dibalik secara horizontal (*Mirror Mode*) melalui `cv2.flip(frame, 1)` agar gerakan tangan Anda terasa alami (seperti bercermin).
2. **MediaPipe Gesture Recognizer Membaca Tangan:**
   - Model AI mendeteksi keberadaan tangan dan mengekstrak **21 titik sendi (*landmarks*)** pada tangan (ujung jari, buku jari, dan pergelangan tangan).
   - Berdasarkan orientasi dan posisi relatif antar sendi tersebut, AI mengklasifikasikan bentuk tangan menjadi nama gesture:
     - `Open_Palm` (Telapak terbuka)
     - `Closed_Fist` (Kepalan tinju)
     - `Victory` (Dua jari membentuk huruf V / Peace)
     - `Thumb_Up` (Jempol ke atas)
     - `Pointing_Up` (Jari telunjuk menunjuk)
3. **Filter Debounce (Mencegah Kedipan / Glitch):**
   - Agar sistem tidak salah deteksi hanya karena 1 frame buram, Python menyimpan riwayat gesture dalam buffer (antrian beberapa frame terakhir).
   - Gesture baru dianggap sah jika terbaca stabil secara berturut-turut.
4. **Konversi Nama Gesture Menjadi Kode Angka:**
   - Nama string gesture diubah menjadi angka integer agar hemat memori dan cepat diproses oleh mikrokontroler:
     - `0` = Tidak ada gesture / Netral
     - `1` = Open Palm (Lanjutkan Tracking)
     - `2` = Closed Fist (Kunci / Pause Tracking)
     - `3` = Victory / Peace (Reset ke Posisi Tengah)
     - `4` = Thumb Up (Animasi Mengangguk / Nod)
     - `5` = Pointing Up (Fokus / Indikator LED)

---

### B. Pengiriman Paket Melalui USB Serial
Data dikirim melalui kabel USB dengan protokol berbasis karakter pembatas (*delimiter*):

```text
Format Paket:  <PAN,TILT,GESTURE>
Contoh:        <90,85,1>
```
* `<` menandakan awal paket.
* `90` adalah target sudut servo Pan (Kiri-Kanan).
* `85` adalah target sudut servo Tilt (Atas-Bawah).
* `1` adalah kode gesture (`Open_Palm`).
* `>` menandakan akhir paket.

Frekuensi pengiriman dibatasi pada interval ~30 Hz (tiap 33 milidetik) agar buffer Serial Arduino Uno tidak mengalami *overflow* (penumpukan data).

---

### C. Pembacaan dan Eksekusi di Arduino Uno
1. Arduino membaca byte per byte secara *non-blocking* menggunakan `Serial.read()` sampai menemukan karakter awal `<` dan akhir `>`.
2. Fungsi `parsePacket()` memecah string berdasarkan tanda koma `,`:
   - Nilai sudut Pan dan Tilt disimpan ke variabel `targetPan` dan `targetTilt`.
   - Nilai gesture disimpan ke variabel `gesture`.
3. Jika kode gesture berubah, fungsi `handleGesture(int gesture)` dipanggil:
   ```cpp
   switch (gesture) {
     case 1: // Open Palm -> Hidupkan LED indikator, izinkan tracking
       digitalWrite(PIN_LED_GESTURE, HIGH);
       break;
     case 2: // Closed Fist -> Kunci sudut di posisi saat ini
       targetPan = currentPan;
       targetTilt = currentTilt;
       break;
     case 3: // Victory -> Kembalikan ke posisi 90, 90
       targetPan = 90;
       targetTilt = 90;
       break;
     case 4: // Thumb Up -> Jalankan fungsi nodAnimation()
       nodAnimation(); // Menggerakkan tilt naik-turun seperti mengangguk
       break;
   }
   ```

---

## 2. Cara Servo Mengikuti Arah Wajah (Face Tracking)

Prinsip dasar pelacakan wajah adalah **Loop Kendali Tertutup Berbasis Visi (Closed-Loop Vision Feedback)**:

```text
[Kamera Laptop]
       │ (Membaca wajah)
       ▼
[Hitung Titik Pusat Wajah (cx, cy)]
       │
       ▼
[Bandingkan dengan Pusat Layar (Center X, Center Y)]
       │
       ▼
[Hitung Error Deviasi: dx = cx - W/2, dy = cy - H/2]
       │
       ▼
[Apakah di luar Deadzone?]
  ├── TIDAK  --> Diam (Jangan gerakkan servo, hilangkan jitter)
  └── YA     --> Koreksi Sudut Servo:
                   Sudut_Baru = Sudut_Lama + (Error * Kp)
       │
       ▼
[Kirim ke Arduino via Serial] --> [Servo Bergerak Mengarahkan Kamera/Braket]
```

### Langkah Matematis di Dalam File `tracker.py`:

1. **Menentukan Pusat Layar:**
   Jika resolusi kamera $640 \times 480$:
   * Pusat Horizontal: $X_{pusat} = 640 / 2 = 320$
   * Pusat Vertikal: $Y_{pusat} = 480 / 2 = 240$

2. **Mendeteksi Pusat Wajah Pengguna:**
   MediaPipe mendeteksi kotak wajah (*Bounding Box*):
   * $cx = origin\_x + (width / 2)$
   * $cy = origin\_y + (height / 2)$

3. **Smoothing (Exponential Moving Average):**
   Untuk meredam gerakan kepala yang sedikit gemetar:
   $$\text{Smooth } cx = (\alpha \times \text{Smooth } cx) + ((1 - \alpha) \times cx)$$

4. **Menghitung Jarak Deviasi (Error):**
   * $dx = cx - X_{pusat}$
   * $dy = cy - Y_{pusat}$
   * Jika wajah bergeser ke kanan layar, $dx > 0$.
   * Jika wajah bergeser ke kiri layar, $dx < 0$.
   * Jika wajah bergeser ke bawah layar, $dy > 0$.
   * Jika wajah bergeser ke atas layar, $dy < 0$.

5. **Area Deadzone (Zona Toleransi):**
   Jika $|dx| \le \text{DEADZONE\_X}$ (misal 35 piksel) dan $|dy| \le \text{DEADZONE\_Y}$ (misal 30 piksel), maka sistem mengabaikan koreksi. Wajah dianggap sudah berada di tengah sehingga motor servo tidak terus bergetar mencari titik presisi.

6. **Koreksi Proporsional Sudut:**
   Jika berada di luar deadzone, sudut servo ditambah/dikurangi sebanding dengan jarak deviasinya:
   $$\Delta \text{Pan} = dx \times K_p$$
   $$\Delta \text{Tilt} = dy \times K_p$$
   $$\text{Sudut Pan} = \text{Sudut Pan} + \Delta \text{Pan}$$
   $$\text{Sudut Tilt} = \text{Sudut Tilt} + \Delta \text{Tilt}$$

7. **Smoothing di Arduino:**
   Alih-alih langsung melompat drastis (yang membuat servo tersentak), Arduino menggunakan fungsi `smoothMoveServos()` yang menambah/mengurangi sudut 1-2 derajat setiap 15 milidetik hingga mencapai target.

---

## 3. Bagian Kode yang Harus / Perlu Diubah Nanti

Berikut adalah daftar bagian kode yang sering perlu Anda sesuaikan dengan kondisi fisik mekanik dan perangkat keras Anda:

### A. Di File `python/config.py`

#### 1. Membalik Arah Gerakan Servo (Jika Terbalik)
Tergantung cara Anda memasang braket servo (apakah kepala servo menghadap ke depan atau ke belakang), arah pergerakannya bisa terbalik.
```python
# Buka python/config.py (Baris 58-59)
INVERT_PAN = False   # Ubah ke True jika wajah ke KIRI tetapi servo malah belok ke KANAN
INVERT_TILT = True   # Ubah ke False jika wajah ke ATAS tetapi servo malah mengarah ke BAWAH
```

#### 2. Mengatur Kecepatan Respons & Kehalusan Pelacakan
```python
# Buka python/config.py (Baris 52-55)
KP_PAN = 0.038       # Naikkan (misal 0.050) jika gerakan servo terlalu lambat
KP_TILT = 0.038      # Turunkan (misal 0.025) jika gerakan servo terlalu agresif / overshooting

FACE_SMOOTH_FACTOR = 0.7  # Rentang 0.1 - 0.9. Semakin tinggi, semakin stabil / tidak bergetar
```

#### 3. Mengatur Area Diam (Deadzone)
```python
# Buka python/config.py (Baris 48-49)
DEADZONE_X = 35      # Jika servo sering bergetar saat Anda diam, naikkan nilai ini (misal 45)
DEADZONE_Y = 30      # Jika ingin servo lebih sensitif terhadap gerakan kecil, turunkan nilainya
```

#### 4. Menentukan Port COM Secara Manual (Jika Auto-Detect Tidak Berfungsi)
```python
# Buka python/config.py (Baris 29)
SERIAL_PORT = None   # Ganti misalnya menjadi "COM3" atau "COM4" sesuai port Arduino di Device Manager
```

---

### B. Di File `arduino/face_hand_tracker/face_hand_tracker.ino`

#### 1. Mengubah Pin Servo (Jika Anda Menggunakan Pin Berbeda)
```cpp
// Baris 33-36 di face_hand_tracker.ino
const int PIN_SERVO_PAN   = 9;   // Ganti dengan nomor pin PWM yang Anda pakai
const int PIN_SERVO_TILT  = 10;  // Ganti dengan nomor pin PWM yang Anda pakai
const int PIN_LED_GESTURE = 8;   // Pin untuk LED respon gesture
```

#### 2. Menyesuaikan Batas Sudut Fisik Braket Servo
Mencegah braket servo membentur kabel atau struktur rangka:
```cpp
// Baris 42-49 di face_hand_tracker.ino
const int PAN_MIN = 10;    // Batas putaran paling kiri (derajat)
const int PAN_MAX = 170;   // Batas putaran paling kanan (derajat)

const int TILT_MIN = 35;   // Batas putaran paling bawah (agar tidak menabrak dasar)
const int TILT_MAX = 145;  // Batas putaran paling atas
```

#### 3. Menambahkan atau Mengubah Aksi Saat Gesture Tertentu Terdeteksi
Jika Anda ingin menyalakan buzzer, relay, atau servo tambahan saat gesture tertentu terbaca, ubah fungsi `handleGesture()`:
```cpp
// Baris 200 di face_hand_tracker.ino
void handleGesture(int gesture) {
  switch (gesture) {
    case 1: // Open Palm
      // Tulis aksi Anda di sini (misal: relay ON)
      break;
      
    case 4: // Thumbs Up
      nodAnimation(); // Contoh aksi servo mengangguk
      break;

    // Anda bisa menambahkan aksi kustom untuk gesture lain
  }
}
```

---

## 4. Ringkasan Singkat

1. **Gesture**: Kamera $\rightarrow$ MediaPipe mengenali 21 sendi $\rightarrow$ diubah ke kode angka (0-5) $\rightarrow$ dikirim dalam paket `<PAN,TILT,GESTURE>` via Serial $\rightarrow$ Arduino menjalankan switch-case di `handleGesture()`.
2. **Face Tracking**: Kamera $\rightarrow$ deteksi pusat wajah $(cx, cy)$ $\rightarrow$ hitung selisih dari tengah layar $(dx, dy)$ $\rightarrow$ jika di luar deadzone, koreksi sudut Pan & Tilt $\rightarrow$ kirim ke Arduino $\rightarrow$ Arduino menggerakkan servo secara halus (*smoothing interpolation*).
3. **Penyetelan Utama**: Cukup buka `python/config.py` untuk membalik arah servo (`INVERT_PAN`/`INVERT_TILT`) atau mengatur kelincahan pergerakan (`KP_PAN`/`KP_TILT`).
