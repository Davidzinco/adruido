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
  
  Pinout:
  - Pin 2 : Sinyal Servo (Kabel Kuning / Oranye)
  - 5V    : VCC Servo (Kabel Merah)
  - GND   : GND Servo (Kabel Coklat / Hitam) - Wajib Common Ground ke Arduino
  
  Baudrate: 115200 bps
  =============================================================================
*/

#include <Servo.h>

const int SERVO_PIN = 2; // Pin sinyal servo

// Batas sudut input yang diterima
const int BATAS_MIN_SERVO = 0;
const int BATAS_MAX_SERVO = 180;
const int POSISI_TENGAH   = 90;

Servo myServo;

int targetAngle  = POSISI_TENGAH;
int currentAngle = POSISI_TENGAH;

unsigned long lastTelemetryTime = 0;

// Buffer Serial Non-Blocking
const byte MAX_BUF = 32;
char serialBuffer[MAX_BUF];
byte bufferIdx = 0;
bool packetStarted = false;

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
  Serial.begin(115200);

  // Inisialisasi Servo
  myServo.attach(SERVO_PIN, 544, 2400);
  myServo.write(POSISI_TENGAH);
  currentAngle = POSISI_TENGAH;
  targetAngle  = POSISI_TENGAH;

  delay(200);
  Serial.println(F("[SYSTEM] Servo Face Tracking Siap!"));
  Serial.println(F("[CONFIG] Pin: D2 | Baud: 115200 | Mode: Respon Cepat"));
}

// =============================================================================
// LOOP UTAMA
// =============================================================================
void loop() {
  unsigned long now = millis();

  // 1. Baca data serial secara instan
  bacaSerial();

  // 2. Kirim feedback telemetri periodik ke PC (tiap 250 ms)
  if (now - lastTelemetryTime >= 250) {
    lastTelemetryTime = now;
    Serial.print(F("$SERVO,"));
    Serial.print(currentAngle);
    Serial.print(F(","));
    Serial.println(targetAngle);
  }
}
