/*
  =============================================================================
  PROYEK: ARDUINO UNO FACE TRACKING & HAND GESTURE IDENTIFICATION
  =============================================================================
  Deskripsi:
  Program Arduino Uno untuk mengendalikan mekanisme 2-Axis Pan & Tilt (Servo)
  berdasarkan koordinat pelacakan wajah dan menerima perintah identifikasi
  gesture tangan dari kamera laptop via Serial USB.
  
  Format Protokol Serial:
    <PAN,TILT,GESTURE>
    Contoh:
      <90,85,0>   -> Pan 90 deg, Tilt 85 deg, Tanpa Gesture
      <120,70,1>  -> Pan 120 deg, Tilt 70 deg, Gesture: Open Palm
      <90,90,3>   -> Pan 90 deg, Tilt 90 deg, Gesture: Peace (Reset Center)
      <90,90,4>   -> Gesture: Thumbs Up (Nodding / Mengangguk)
      
  Pinout Arduino Uno:
    - Pin 9  : Servo Pan (Horizontal / Kiri - Kanan)
    - Pin 10 : Servo Tilt (Vertikal / Atas - Bawah)
    - Pin 13 : LED Indikator Status bawaan (Built-in LED)
    - Pin 8  : LED Indikator Gesture Tambahan (Opsional)
    
  Catatan Catu Daya (PENTING):
    Disarankan memberi daya servo (VCC & GND) dari sumber eksternal 5V (1-2A),
    bukan langsung dari pin 5V Arduino untuk mencegah brown-out / restart saat
    kedua servo bergerak bersamaan. Pastikan GND catu daya eksternal terhubung
    ke GND Arduino (Common Ground).
  =============================================================================
*/

#include <Servo.h>

// Definisi Pin
const int PIN_SERVO_PAN  = 9;
const int PIN_SERVO_TILT = 10;
const int PIN_LED_STATUS = 13;
const int PIN_LED_GESTURE = 8; // Opsional LED eksternal

// Objek Servo
Servo servoPan;
Servo servoTilt;

// Batasan Sudut Servo (Mencegah benturan mekanik & kabel tertarik)
const int PAN_MIN = 10;
const int PAN_MAX = 170;
const int PAN_CENTER = 90;

const int TILT_MIN = 35;
const int TILT_MAX = 145;
const int TILT_CENTER = 90;

// Variabel Posisi Sudut
int currentPan = PAN_CENTER;
int targetPan  = PAN_CENTER;
int currentTilt = TILT_CENTER;
int targetTilt  = TILT_CENTER;

// Kecepatan Pergerakan Halus (Smoothing / Interpolasi)
const int STEP_DELAY_MS = 15;     // Interval pembaruan servo (ms)
const int MAX_STEP_SIZE = 2;       // Perubahan sudut maksimum per interval (derajat)
unsigned long lastServoUpdate = 0;

// Serial Buffer & Parsing
const byte MAX_BUFFER = 32;
char serialBuffer[MAX_BUFFER];
byte bufferIndex = 0;
bool isReceiving = false;

// Status & Failsafe
unsigned long lastPacketTime = 0;
const unsigned long TIMEOUT_FAILSAFE = 4000; // 4 detik tanpa serial -> status idle
int lastGesture = 0;

// Gesture Codes:
// 0: NONE / UNKNOWN
// 1: OPEN_PALM   (Tracking Aktif)
// 2: FIST        (Pause / Kunci Posisi)
// 3: PEACE       (Reset ke Posisi Tengah)
// 4: THUMBS_UP   (Apresiasi: Servo mengangguk / Nod)
// 5: POINTING    (Mode Pointer / Fokus)
// 6: OK          (Konfirmasi)

void setup() {
  // Inisialisasi Serial Komunikasi cepat
  Serial.begin(115200);
  while (!Serial && millis() < 3000) {
    // Tunggu koneksi serial USB terbuka
  }

  // Setup Pin LED
  pinMode(PIN_LED_STATUS, OUTPUT);
  pinMode(PIN_LED_GESTURE, OUTPUT);
  digitalWrite(PIN_LED_STATUS, HIGH);
  digitalWrite(PIN_LED_GESTURE, LOW);

  // Setup Servo
  servoPan.attach(PIN_SERVO_PAN);
  servoTilt.attach(PIN_SERVO_TILT);

  // Set Posisi Awal (Tengah)
  servoPan.write(PAN_CENTER);
  servoTilt.write(TILT_CENTER);
  currentPan = PAN_CENTER;
  targetPan = PAN_CENTER;
  currentTilt = TILT_CENTER;
  targetTilt = TILT_CENTER;

  // Sambutan Start-up (Blink LED 2x)
  blinkLed(PIN_LED_STATUS, 2, 100);

  Serial.println(F("ARDUINO_READY: Face & Hand Gesture Tracker Online"));
  lastPacketTime = millis();
}

void loop() {
  unsigned long now = millis();

  // 1. Baca data Serial yang masuk (Non-blocking)
  readSerialData();

  // 2. Perbarui pergerakan servo secara halus (Smooth Interpolation)
  if (now - lastServoUpdate >= STEP_DELAY_MS) {
    lastServoUpdate = now;
    smoothMoveServos();
  }

  // 3. Failsafe jika koneksi serial terputus lama
  if (now - lastPacketTime > TIMEOUT_FAILSAFE) {
    digitalWrite(PIN_LED_STATUS, LOW); // LED mati menunjukkan timeout
  } else {
    digitalWrite(PIN_LED_STATUS, HIGH); // LED menyala saat koneksi aktif
  }
}

/**
 * Membaca karakter dari serial buffer dengan pembatas '<' dan '>'
 */
void readSerialData() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '<') {
      // Penanda awal frame paket data
      bufferIndex = 0;
      isReceiving = true;
    } 
    else if (c == '>') {
      // Penanda akhir frame paket data
      if (isReceiving) {
        serialBuffer[bufferIndex] = '\0'; // Null-terminate string
        isReceiving = false;
        parsePacket(serialBuffer);
      }
    } 
    else if (isReceiving) {
      if (bufferIndex < MAX_BUFFER - 1) {
        serialBuffer[bufferIndex++] = c;
      } else {
        // Overflow buffer safety
        bufferIndex = 0;
        isReceiving = false;
      }
    }
    // Perintah satu karakter instan (opsional)
    else if (c == 'R' || c == 'r') {
      targetPan = PAN_CENTER;
      targetTilt = TILT_CENTER;
      Serial.println(F("ACK:RESET_CENTER"));
    }
  }
}

/**
 * Membedah isi paket serial "<pan,tilt,gesture>"
 */
void parsePacket(char* data) {
  // Format diharapkan: pan,tilt,gesture
  char* token = strtok(data, ",");
  if (token == NULL) return;
  int pan = atoi(token);

  token = strtok(NULL, ",");
  if (token == NULL) return;
  int tilt = atoi(token);

  token = strtok(NULL, ",");
  if (token == NULL) return;
  int gesture = atoi(token);

  // Validasi dan simpan target sudut servo
  pan = constrain(pan, PAN_MIN, PAN_MAX);
  tilt = constrain(tilt, TILT_MIN, TILT_MAX);

  targetPan = pan;
  targetTilt = tilt;
  lastPacketTime = millis();

  // Tangani event gesture jika berubah
  if (gesture != lastGesture) {
    handleGesture(gesture);
    lastGesture = gesture;
  }
}

/**
 * Menjalankan aksi berdasarkan kode gesture tangan yang terdeteksi
 */
void handleGesture(int gesture) {
  switch (gesture) {
    case 1: // OPEN_PALM: Pelacakan Normal
      digitalWrite(PIN_LED_GESTURE, HIGH);
      break;

    case 2: // FIST: Kunci posisi (Pause)
      digitalWrite(PIN_LED_GESTURE, LOW);
      // Biarkan target di posisi saat ini
      targetPan = currentPan;
      targetTilt = currentTilt;
      break;

    case 3: // PEACE / VICTORY: Reset Center
      targetPan = PAN_CENTER;
      targetTilt = TILT_CENTER;
      blinkLed(PIN_LED_GESTURE, 3, 70);
      break;

    case 4: // THUMBS_UP: Gerakan mengangguk (Nod Action)
      nodAnimation();
      break;

    case 5: // POINTING: Indikasi laser / target
      blinkLed(PIN_LED_GESTURE, 4, 50);
      break;

    case 6: // OK
      blinkLed(PIN_LED_GESTURE, 2, 150);
      break;

    default: // 0: NONE
      digitalWrite(PIN_LED_GESTURE, LOW);
      break;
  }
}

/**
 * Menggerakkan servo secara bertahap menuju target (mengurangi jitter & hentakan)
 */
void smoothMoveServos() {
  bool updated = false;

  // Smoothing Pan
  if (currentPan < targetPan) {
    currentPan = min(currentPan + MAX_STEP_SIZE, targetPan);
    updated = true;
  } else if (currentPan > targetPan) {
    currentPan = max(currentPan - MAX_STEP_SIZE, targetPan);
    updated = true;
  }

  // Smoothing Tilt
  if (currentTilt < targetTilt) {
    currentTilt = min(currentTilt + MAX_STEP_SIZE, targetTilt);
    updated = true;
  } else if (currentTilt > targetTilt) {
    currentTilt = max(currentTilt - MAX_STEP_SIZE, targetTilt);
    updated = true;
  }

  if (updated) {
    servoPan.write(currentPan);
    servoTilt.write(currentTilt);
  }
}

/**
 * Animasi mengangguk (Nod) saat menerima Thumbs Up
 */
void nodAnimation() {
  int originalTilt = currentTilt;
  int downAngle = constrain(originalTilt + 20, TILT_MIN, TILT_MAX);
  int upAngle   = constrain(originalTilt - 15, TILT_MIN, TILT_MAX);

  servoTilt.write(downAngle);
  delay(140);
  servoTilt.write(upAngle);
  delay(140);
  servoTilt.write(originalTilt);
  currentTilt = originalTilt;
  targetTilt = originalTilt;
}

/**
 * Utility untuk mengedipkan LED
 */
void blinkLed(int pin, int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(pin, HIGH);
    delay(delayMs);
    digitalWrite(pin, LOW);
    delay(delayMs);
  }
}
