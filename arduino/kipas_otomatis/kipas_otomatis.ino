/*
  =============================================================================
  PROYEK: SISTEM KIPAS OTOMATIS & FACE TRACKING (ARDUINO UNO)
  =============================================================================
  Deskripsi:
  Program Arduino Uno untuk mengendalikan kipas otomatis dan pelacakan wajah:
  1. Mengukur jarak objek menggunakan Sensor Ultrasonik HC-SR04.
  2. Menyalakan Kipas DC (lewat Relay/MOSFET) jika jarak objek <= AMBANG_BATAS_JARAK.
  3. Menggerakkan Motor Servo penopang kipas secara horizontal (Pan) mengikuti
     posisi wajah pengguna yang dikirimkan oleh PC/Laptop via USB Serial.
  4. Non-blocking (tanpa delay panjang) sehingga responsif dan anti-jitter.
  
  Format Komunikasi Serial (Baudrate: 115200):
  - Format Paket: <SUDUT> atau <PAN,TILT,GESTURE>
    Contoh:
      <90>        -> Sudut 90 derajat
      <110,90,0>  -> Sudut Pan 110 derajat (kompatibel dengan app Python)
  - Format Teks Manual: 90 (bisa diketik langsung di Serial Monitor)

  Pinout Arduino Uno:
  - Pin 12 : HC-SR04 TRIG (Output Pulsa)
  - Pin 13 : HC-SR04 ECHO (Input Pantulan)
  - Pin 2  : Motor Servo Signal (PWM / Timer1 via Servo.h)
  - Pin 7  : Driver Kipas (Relay / MOSFET / Transistor)
  =============================================================================
*/

#include <Servo.h>

// =============================================================================
// KONFIGURASI PIN & PERANGKAT KERAS
// =============================================================================
const int TRIG_PIN  = 12; // Pin TRIG Sensor Ultrasonik HC-SR04
const int ECHO_PIN  = 13; // Pin ECHO Sensor Ultrasonik HC-SR04
const int SERVO_PIN = 2;  // Pin Sinyal Motor Servo (SG90 / MG90S)
const int FAN_PIN   = 7;  // Pin Kontrol Driver Kipas (Relay / MOSFET)

// Logika Aktif Driver Kipas:
// Set true  jika relay/driver berlogika Active-HIGH (HIGH = Nyala, LOW = Mati)
// Set false jika relay modul berlogika Active-LOW  (LOW = Nyala, HIGH = Mati)
const bool FAN_ACTIVE_HIGH = true;

// =============================================================================
// PARAMETER SISTEM
// =============================================================================
// Ambang batas jarak untuk menyalakan kipas (dalam centimeter)
const float AMBANG_BATAS_JARAK = 50.0; // Kipas ON jika ada objek <= 50 cm

// Jeda waktu mati kipas (Off-delay Hysteresis) dalam milidetik
// Mencegah kipas mati-nyala berkedip mendadak jika pembacaan sensor sesaat drop
const unsigned long FAN_OFF_DELAY_MS = 2500;

// Batasan sudut fisik servo (Sesuai contoh.txt agar rotasi tidak terlalu jauh)
const int BATAS_MIN_SERVO = 75;  // Batas kiri (maksimal 15 derajat ke kiri dari tengah)
const int BATAS_MAX_SERVO = 105; // Batas kanan (maksimal 15 derajat ke kanan dari tengah)
const int POSISI_TENGAH   = 90;

// Kecepatan pergerakan konstan & santai (Kecepatan tetap, tidak makin kencang)
const int INTERVAL_SERVO_STEP_MS = 30; // Interval update posisi servo (ms)
const int MAX_STEP_SIZE          = 1;  // Kecepatan konstan: hanya 1 derajat per interval (~33 deg/s)

// Interval pembacaan sensor dan telemetri
const unsigned long INTERVAL_SENSOR_MS    = 80;  // Baca ultrasonik tiap 80 ms
const unsigned long INTERVAL_TELEMETRY_MS = 300; // Kirim status ke PC tiap 300 ms

// =============================================================================
// VARIABEL STATUS GLOBAL
// =============================================================================
Servo myServo;

int targetAngle  = POSISI_TENGAH;
int currentAngle = POSISI_TENGAH;

float jarakTerakhir = -1.0;
bool statusKipas    = false;
unsigned long waktuTerakhirTerdeteksi = 0;

// Pewaktu non-blocking millis()
unsigned long lastSensorTime    = 0;
unsigned long lastServoTime     = 0;
unsigned long lastTelemetryTime = 0;
unsigned long lastSerialPacket  = 0;

// Buffer penerimaan Serial
const byte MAX_BUF = 32;
char serialBuffer[MAX_BUF];
byte bufferIdx = 0;
bool packetStarted = false;

// =============================================================================
// FUNGSI BANTU KIPAS
// =============================================================================
void aturStatusKipas(bool nyala) {
  statusKipas = nyala;
  if (FAN_ACTIVE_HIGH) {
    digitalWrite(FAN_PIN, nyala ? HIGH : LOW);
  } else {
    digitalWrite(FAN_PIN, nyala ? LOW : HIGH);
  }
}

// =============================================================================
// FUNGSI PENGUKURAN JARAK HC-SR04 (NON-BLOCKING SAFE)
// =============================================================================
float bacaJarakUltrasonik() {
  // Pancarkan pulsa ultrasonik 10us
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Baca pantulan gelombang. Timeout 20000 us (~3.4 meter)
  // Menghindari blocking lama jika tidak ada pantulan
  long durasi = pulseIn(ECHO_PIN, HIGH, 20000);

  if (durasi == 0) {
    return -1.0; // Di luar jangkauan / timeout
  }

  // Hitung jarak dalam cm (kecepatan suara ~0.034 cm/us, bolak-balik / 2)
  float jarakCm = (durasi * 0.034) / 2.0;

  // Filter nilai tak wajar
  if (jarakCm < 2.0 || jarakCm > 400.0) {
    return -1.0;
  }

  return jarakCm;
}

// =============================================================================
// FUNGSI PENGOLAHAN PROTOKOL SERIAL
// =============================================================================
void prosesDataSerial(char* data) {
  // Format bisa berupa:
  // 1. "90" (angka langsung)
  // 2. "90,85,0" (format PAN, TILT, GESTURE)
  int sudutPan = targetAngle;

  char* token = strtok(data, ",");
  if (token != NULL) {
    sudutPan = atoi(token);
  }

  // Validasi dan batasi dalam jangkauan aman servo
  if (sudutPan >= BATAS_MIN_SERVO && sudutPan <= BATAS_MAX_SERVO) {
    targetAngle = sudutPan;
    lastSerialPacket = millis();
  }
}

void bacaSerialInput() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    // Deteksi awal paket berformat <...>
    if (c == '<') {
      packetStarted = true;
      bufferIdx = 0;
      continue;
    }

    // Deteksi akhir paket berformat <...>
    if (c == '>') {
      if (packetStarted) {
        serialBuffer[bufferIdx] = '\0';
        prosesDataSerial(serialBuffer);
        packetStarted = false;
        bufferIdx = 0;
      }
      continue;
    }

    // Deteksi format string biasa berakhiran newline (\n atau \r)
    if (c == '\n' || c == '\r') {
      if (!packetStarted && bufferIdx > 0) {
        serialBuffer[bufferIdx] = '\0';
        prosesDataSerial(serialBuffer);
        bufferIdx = 0;
      }
      continue;
    }

    // Simpan karakter ke buffer jika masih muat
    if (bufferIdx < MAX_BUF - 1) {
      // Hanya simpan angka, tanda minus, dan koma
      if (isDigit(c) || c == ',' || c == '-') {
        serialBuffer[bufferIdx++] = c;
      }
    }
  }
}

// =============================================================================
// SETUP
// =============================================================================
void setup() {
  // Inisialisasi Serial Baudrate cepat & stabil
  Serial.begin(115200);

  // Setup Pin HC-SR04
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

  // Setup Pin Driver Kipas
  pinMode(FAN_PIN, OUTPUT);
  aturStatusKipas(false); // Pastikan kipas mati saat pertama kali menyala

  // Setup Motor Servo
  // Parameter pulsa standar SG90: 544us - 2400us untuk rotasi penuh 0 - 180 derajat
  myServo.attach(SERVO_PIN, 544, 2400);
  myServo.write(POSISI_TENGAH);
  currentAngle = POSISI_TENGAH;
  targetAngle  = POSISI_TENGAH;

  delay(300);
  Serial.println(F("[SYSTEM] Kipas Otomatis & Face Tracking Siap!"));
  Serial.println(F("[CONFIG] Baud: 115200 | Trig: D12 | Echo: D13 | Servo: D2 | Fan: D7"));
}

// =============================================================================
// LOOP UTAMA (NON-BLOCKING)
// =============================================================================
void loop() {
  unsigned long now = millis();

  // 1. Baca Perintah Serial dari PC (Prioritas Tinggi & Cepat)
  bacaSerialInput();

  // 2. Pergerakan Halus Servo (Smoothing Interpolation)
  if (now - lastServoTime >= INTERVAL_SERVO_STEP_MS) {
    lastServoTime = now;

    if (currentAngle != targetAngle) {
      int selisih = targetAngle - currentAngle;
      if (abs(selisih) <= MAX_STEP_SIZE) {
        currentAngle = targetAngle;
      } else if (selisih > 0) {
        currentAngle += MAX_STEP_SIZE;
      } else {
        currentAngle -= MAX_STEP_SIZE;
      }
      myServo.write(currentAngle);
    }
  }

  // 3. Pembacaan Sensor Jarak HC-SR04 secara Periodik
  if (now - lastSensorTime >= INTERVAL_SENSOR_MS) {
    lastSensorTime = now;
    float jarak = bacaJarakUltrasonik();

    if (jarak > 0) {
      jarakTerakhir = jarak;
      // Jika objek berada dalam jangkauan ambang batas
      if (jarak <= AMBANG_BATAS_JARAK) {
        waktuTerakhirTerdeteksi = now;
        if (!statusKipas) {
          aturStatusKipas(true);
        }
      }
    }

    // Logika Pemadaman Kipas dengan Off-delay Hysteresis
    if (statusKipas) {
      if (now - waktuTerakhirTerdeteksi >= FAN_OFF_DELAY_MS) {
        aturStatusKipas(false);
      }
    }
  }

  // 4. Kirim Data Telemetri ke PC (untuk visualisasi atau monitoring)
  if (now - lastTelemetryTime >= INTERVAL_TELEMETRY_MS) {
    lastTelemetryTime = now;

    // Format terstruktur agar mudah dibaca manusia maupun diparse oleh Python
    // Contoh: $DATA,32.4,1,90
    Serial.print(F("$DATA,"));
    if (jarakTerakhir > 0) {
      Serial.print(jarakTerakhir, 1);
    } else {
      Serial.print(F("-1"));
    }
    Serial.print(F(","));
    Serial.print(statusKipas ? 1 : 0);
    Serial.print(F(","));
    Serial.println(currentAngle);
  }
}
