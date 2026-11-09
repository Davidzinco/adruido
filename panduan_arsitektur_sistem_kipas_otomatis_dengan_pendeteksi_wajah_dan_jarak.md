# Panduan Arsitektur Sistem Kipas Otomatis & Face Tracking

Dokumen ini merupakan **panduan konseptual (referensi alur kerja)** untuk membangun sistem kipas pintar berbasis mikrokontroler dan pemrosesan citra komputer (*Computer Vision*). 

> **Catatan:** Kode dan konfigurasi pin pada dokumen ini bersifat sebagai ilustrasi alur (*pseudocode/reference*), bukan acuan pustaka absolut. Implementasi akhir dapat disesuaikan dengan kebutuhan komponen yang digunakan.

---

## 1. Ikhtisar Sistem (*System Overview*)

Sistem ini membagi beban kerja menjadi dua unit utama:

1. **Hardware Control Unit (Mikrokontroler):**
   - Membaca data jarak dari sensor ultrasonik (HC-SR04).
   - Mengendalikan status daya kipas (ON/OFF) berdasarkan ada/tidaknya objek.
   - Menerima instruksi posisi dari PC dan menggerakkan Motor Servo penopang kipas.

2. **Vision Processing Unit (PC / Laptop):**
   - Mengambil *feed* video dari webcam.
   - Memproses deteksi wajah menggunakan *Computer Vision* (misalnya OpenCV / MediaPipe).
   - Menghitung offset posisi wajah terhadap titik tengah kamera, lalu mengirimkan perintah kalkulasi sudut ke mikrokontroler via komunikasi Serial.

```text
+---------------------+              +-----------------------+
|  Sensor HC-SR04     |              |  Webcam / Camera      |
+----------+----------+              +-----------+-----------+
           |                                     |
           | (Deteksi Jarak)                     | (Frame Video)
           v                                     v
+----------+----------+     Serial USB      +----+------------------+
|   Mikrokontroler    |<------------------->| Program PC (Python)   |
+----+-------------+--+  (Instruksi Servo)  +-----------------------+
     |             |
     | (Control)   | (PWM Signal)
     v             v
+----+----+   +----+----+
| Kipas   |   | Motor   |
| DC      |   | Servo   |
+---------+   +---------+
```

---

## 2. Diagram & Skema Blok Koneksi

### A. Alur Kontrol Kipas (Pendeteksian Objek)
1. HC-SR04 memancarkan pulsa ultrasonik melalui pin `TRIG` dan menerima pantulannya di pin `ECHO`.
2. Mikrokontroler menghitung jarak objek.
3. Jika `Jarak < Ambang_Batas` (misal $< 50\text{ cm}$), mikrokontroler memberi sinyal HIGH ke saklar elektronik (Relay / MOSFET / Transistor) untuk menyalakan kipas DC.

### B. Alur Tracking Servo (Pendeteksian Wajah)
1. Program di PC membaca frame video dari kamera.
2. Algoritma deteksi menemukan koordinat pusat wajah $X_{\text{wajah}}$.
3. Program mengukur selisih koordinat dengan pusat frame $X_{\text{center}}$:
   $$\text{Error} = X_{\text{wajah}} - X_{\text{center}}$$
4. Jika $\text{Error} > \text{Deadzone}$, sudut servo disesuaikan bertahap (kiri/kanan) dan dikirimkan sebagai perintah string via Serial (UART).
5. Mikrokontroler membaca string tersebut dan memperbarui posisi sudut servo.

---

## 3. Matriks Referensi Pin & Kelistrikan

| Komponen | Pin Modul | Target Pin MCU | Catatan Daya & Keamanan |
| :--- | :--- | :--- | :--- |
| **HC-SR04** | VCC | 5V | Hubungkan ke jalur daya 5V MCU. |
| | GND | GND | Common Ground. |
| | TRIG | Digital Output | Pin pengirim sinyal pulsa. |
| | ECHO | Digital Input | Pin pembaca waktu balik sinyal. |
| **Servo Motor** | VCC | Ext 5V / 5V MCU | **Disarankan daya eksternal** jika servo menarik arus besar. |
| | GND | GND | Wajib di-kopel (*Common Ground*) ke MCU. |
| | Signal | Pin PWM | Mengontrol sudut rotasi servo. |
| **Driver Kipas**| IN / Control| Digital Output | Mengendalikan Switch Relay/MOSFET. |
| | Power (+/-)| Ext Power (12V/5V)| **Jangan mengambil daya kipas langsung dari pin I/O MCU.** |

---

## 4. Ilustrasi Alur Program (Logic Framework)

### A. Logika pada Mikrokontroler (Pseudo-code)

```cpp
// REFERENSI LOGIKA MIKROKONTROLER

void setup() {
    Inisialisasi_Serial(9600);
    Inisialisasi_Pin_HCSR04();
    Inisialisasi_Pin_Kipas();
    Inisialisasi_Servo();
}

void loop() {
    // 1. Logika Sensor Ultrasonik
    float jarak = Hitung_Jarak_HCSR04();
    if (jarak > 0 && jarak < AMBANG_BATAS_JARAK) {
        Nyalakan_Kipas();
    } else {
        Matikan_Kipas();
    }

    // 2. Logika Penerimaan Perintah Servo dari PC
    if (Serial_Tersedia()) {
        int sudut_target = Baca_Angka_Serial();
        if (sudut_target >= 0 && sudut_target <= 180) {
            Set_Sudut_Servo(sudut_target);
        }
    }
}
```

### B. Logika pada PC / Computer Vision (Pseudo-code)

```python
# REFERENSI LOGIKA PROGRAM PC

Inisialisasi_Kamera()
Inisialisasi_Koneksi_Serial(Port='COM_MCU', Baudrate=9600)

sudut_servo = 90  # Posisi awal (Tengah)

while Kamera_Aktif():
    frame = Ambil_Frame_Kamera()
    daftar_wajah = Deteksi_Wajah(frame)
    
    if Ada_Wajah(daftar_wajah):
        wajah_utama = Ambil_Wajah_Terdekat(daftar_wajah)
        posisi_x = Dapatkan_Titik_Tengah_X(wajah_utama)
        tengah_screen = Dapatkan_Lebar_Frame() / 2
        
        selisih = posisi_x - tengah_screen
        
        # Deadzone menjaga servo agar tidak jitter / bergetar berlebihan saat tenang
        if abs(selisih) > AMBANG_DEADZONE:
            if selisih > 0:
                sudut_servo -= LANGKAH_DAPAT_DISESUAIKAN
            else:
                sudut_servo += LANGKAH_DAPAT_DISESUAIKAN
                
            Batasi_Sudut(sudut_servo, Min=0, Max=180)
            Kirim_Data_Serial(sudut_servo)

Tutup_Kamera()
Tutup_Koneksi_Serial()
```

---

## 5. Panduan Pengujian & Integrasi (*Testing Guide*)

1. **Uji Jalur Kelistrikan & Driver Kipas:**
   - Pastikan *ground* antara sumber daya eksternal dan mikrokontroler terhubung (*Common Ground*).
   - Pastikan relay/MOSFET bekerja ketika pin digital diberi sinyal HIGH.
2. **Calibrasi Sensor Jarak:**
   - Lakukan pengetesan rentang ukur HC-SR04 untuk memastikan kipas tidak menyala akibat pembacaan palsu (*false positive*).
3. **Uji Komunikasi Serial:**
   - Gunakan Serial Monitor untuk mengirim nilai angka (misal `45`, `90`, `135`) secara manual guna memastikan servo bergerak akurat sebelum mengintegrasikan skrip deteksi wajah.
4. **Tuning Tracking Wajah:**
   - Atur parameter *Deadzone* dan *Step Size* pada program PC untuk memperoleh pergerakan servo yang halus (*smooth*) tanpa mengalami efek bergetar (*jittering*).