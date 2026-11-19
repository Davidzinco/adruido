/*
  =============================================================================
  PROYEK: PENGUJIAN FACE TRACKING SERVO (ARDUINO UNO)
  =============================================================================
  Deskripsi:
  Program Arduino Uno untuk mengendalikan Motor Servo (baik tipe 180 derajat
  maupun tipe 360 derajat Continuous Rotation) dengan respon cepat tanpa delay.
  
  Menerima perintah serial:
  - Nilai 90 : BERHENTI / DIAM (Stop pada servo 360 / Posisi tengah pada 180)
  - Nilai > 90 : Berputar ke kanan (kecepatan pelan konstan dari Python)
  - Nilai < 90 : Berputar ke kiri (kecepatan pelan konstan dari Python)

  Kontrol Kipas (Relay di D3):
  - Token ke-4 paket serial = perintah kipas:
      0 = AUTO, wajah tidak terdeteksi  -> OFF setelah 0,5 detik (FAN_OFF_DELAY_MS)
      1 = AUTO, wajah terdeteksi        -> ON
      2 = MANUAL ON  (paksa nyala, dari tombol [K])
      3 = MANUAL OFF (paksa mati, dari tombol [K])
  - Contoh paket: <105,90,0,1>  -> servo 105, kipas ON (wajah ada)
                  <90,90,0,2>   -> servo 90, kipas ON (manual)
                  <90,90,0,3>   -> servo 90, kipas OFF (manual)

  Pinout:
  - Pin 2 : Sinyal Servo (Kabel Kuning / Oranye)
  - Pin 3 : IN Modul Relay Kipas
  - 5V    : VCC Servo & VCC Modul Relay
  - GND   : GND Servo, GND Modul Relay (Wajib Common Ground ke Arduino)

  Baudrate: 115200 bps
  =============================================================================
*/

#include <Servo.h>

const int SERVO_PIN = 2; // Pin sinyal servo
const int FAN_PIN   = 3; // Pin kontrol relay kipas (IN relay)

// Logika relay:
// true  = Active-HIGH (HIGH = kipas NYALA, LOW = MATI)
// false = Active-LOW  (LOW  = kipas NYALA, HIGH = MATI)
// Modul relay 1 channel murah (opto-coupler) umumnya Active-LOW.
// Gejala jika salah set: kipas nyala-mati terbalik saat program jalan.
const bool FAN_ACTIVE_HIGH = false;

// Jeda mati kipas setelah wajah hilang (histeresis, mencegah kedip)
const unsigned long FAN_OFF_DELAY_MS = 500;

// Batas sudut input yang diterima
const int BATAS_MIN_SERVO = 0;
const int BATAS_MAX_SERVO = 180;
const int POSISI_TENGAH   = 90;

Servo myServo;

int targetAngle  = POSISI_TENGAH;
int currentAngle = POSISI_TENGAH;

bool statusKipas = false;
unsigned long waktuTerakhirWajah = 0;

unsigned long lastTelemetryTime = 0;

// Buffer Serial Non-Blocking
const byte MAX_BUF = 32;
char serialBuffer[MAX_BUF];
byte bufferIdx = 0;
bool packetStarted = false;

// =============================================================================
// FUNGSI BANTU KIPAS (RELAY)
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
// PARSER SERIAL NON-BLOCKING
// =============================================================================
void prosesPerintahSudut(char* data) {
  char* token = strtok(data, ",");
  if (token != NULL) {
    int sudut = atoi(token);
    if (sudut >= BATAS_MIN_SERVO && sudut <= BATAS_MAX_SERVO) {
      targetAngle = sudut;
      // Respon instan: tulis langsung ke servo tanpa delay perantara
      if (currentAngle != targetAngle) {
        currentAngle = targetAngle;
        myServo.write(currentAngle);
      }
    }
  }

  // Token lanjutan: ke-2 = TILT, ke-3 = GESTURE, ke-4 = PERINTAH KIPAS
  for (byte idx = 2; idx <= 4; idx++) {
    token = strtok(NULL, ",");
    if (token == NULL) return;

    if (idx == 4) {
      int perintahKipas = atoi(token);

      if (perintahKipas == 1 || perintahKipas == 2) {
        // Wajah terdeteksi / manual ON -> nyalakan & segarkan timer
        waktuTerakhirWajah = millis();
        if (!statusKipas) {
          aturStatusKipas(true);
        }
      } else if (perintahKipas == 3) {
        // Manual OFF -> matikan seketika
        aturStatusKipas(false);
      }
      // perintahKipas == 0: biarkan, kipas mati otomatis lewat timer di loop()
    }
  }
}

void bacaSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '<') {
      packetStarted = true;
      bufferIdx = 0;
      continue;
    }

    if (c == '>') {
      if (packetStarted) {
        serialBuffer[bufferIdx] = '\0';
        prosesPerintahSudut(serialBuffer);
        packetStarted = false;
        bufferIdx = 0;
      }
      continue;
    }

    if (c == '\n' || c == '\r') {
      if (!packetStarted && bufferIdx > 0) {
        serialBuffer[bufferIdx] = '\0';
        prosesPerintahSudut(serialBuffer);
        bufferIdx = 0;
      }
      continue;
    }

    if (bufferIdx < MAX_BUF - 1) {
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
  // Set level "MATI" SEBELUM pin dijadikan OUTPUT.
  // Ini mencegah relay berkedip (klik-klik) saat Arduino baru boot/reset.
  digitalWrite(FAN_PIN, FAN_ACTIVE_HIGH ? LOW : HIGH);
  pinMode(FAN_PIN, OUTPUT);
  aturStatusKipas(false);

  Serial.begin(115200);

  // Inisialisasi Servo
  myServo.attach(SERVO_PIN, 544, 2400);
  myServo.write(POSISI_TENGAH);
  currentAngle = POSISI_TENGAH;
  targetAngle  = POSISI_TENGAH;

  delay(200);
  Serial.println(F("[SYSTEM] Servo Face Tracking + Kipas Siap!"));
  Serial.print(F("[CONFIG] Servo: D2 | Relay Kipas: D3"));
  Serial.print(F(" | Relay: "));
  Serial.print(FAN_ACTIVE_HIGH ? F("ACTIVE-HIGH") : F("ACTIVE-LOW"));
  Serial.println(F(" | Baud: 115200"));
}

// =============================================================================
// LOOP UTAMA
// =============================================================================
void loop() {
  unsigned long now = millis();

  // 1. Baca data serial secara instan
  bacaSerial();

  // 2. Matikan kipas jika wajah sudah tidak terdeteksi melewati jeda
  if (statusKipas && (now - waktuTerakhirWajah >= FAN_OFF_DELAY_MS)) {
    aturStatusKipas(false);
  }

  // 3. Kirim feedback telemetri periodik ke PC (tiap 250 ms)
  if (now - lastTelemetryTime >= 250) {
    lastTelemetryTime = now;
    Serial.print(F("$SERVO,"));
    Serial.print(currentAngle);
    Serial.print(F(","));
    Serial.print(targetAngle);
    Serial.print(F(","));
    Serial.println(statusKipas ? 1 : 0);
  }
}
