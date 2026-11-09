"""
Konfigurasi Sistem Face Tracking & Hand Gesture Identification
Arduino Uno + Kamera Laptop
"""

import os
from pathlib import Path

# Direktori Dasar Proyek
BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"

# Path Model MediaPipe LiteRT / Tasks
FACE_MODEL_PATH = str(MODELS_DIR / "blaze_face_short_range.tflite")
GESTURE_MODEL_PATH = str(MODELS_DIR / "gesture_recognizer.task")

# URL Download Resmi jika file model belum ada di komputer
FACE_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite"
GESTURE_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task"

# -------------------------------------------------------------
# PENGATURAN KAMERA
# -------------------------------------------------------------
CAMERA_INDEX = 0          # 0 = Kamera bawaan laptop (Default webcam)
FRAME_WIDTH = 640         # Resolusi horizontal yang optimal & ringan
FRAME_HEIGHT = 480        # Resolusi vertikal
FLIP_HORIZONTAL = True    # True = Mirror mode (sangat intuitif untuk interaksi tangan)

# -------------------------------------------------------------
# PENGATURAN SERIAL ARDUINO
# -------------------------------------------------------------
SERIAL_PORT = None        # None = Auto-detect port COM Arduino otomatis
BAUD_RATE = 115200        # Harus sama dengan Serial.begin di Arduino Uno
SEND_INTERVAL_SEC = 0.033 # ~30 Hz (Mencegah buffer overload pada Arduino)

# -------------------------------------------------------------
# BATASAN SUDUT SERVO (ARDUINO UNO)
# -------------------------------------------------------------
PAN_MIN = 70              # Batas minimal sudut Pan (-20 deg dari tengah)
PAN_MAX = 110             # Batas maksimal sudut Pan (+20 deg dari tengah)
PAN_CENTER = 90           # Sudut netral Pan (Tengah)

TILT_MIN = 35             # Batas minimal sudut Tilt (Bawah)
TILT_MAX = 145            # Batas maksimal sudut Tilt (Atas)
TILT_CENTER = 90          # Sudut netral Tilt

# -------------------------------------------------------------
# PARAMETER KONTROL PELACAKAN (FACE TRACKER)
# -------------------------------------------------------------
# Deadzone: Area toleransi di tengah layar (dalam piksel).
# Jika wajah berada di dalam kotak toleransi ini, servo TIDAK akan bergerak.
# Ini sangat ampuh menghilangkan getaran (jitter) mikro.
DEADZONE_X = 35           # Toleransi horizontal (piksel)
DEADZONE_Y = 30           # Toleransi vertikal (piksel)

# Gain Proportional (Kp)
# Mengatur seberapa cepat servo merespon jarak deviasi wajah dari pusat.
KP_PAN = 0.038
KP_TILT = 0.038

# Arah pergerakan (Inversi)
# Sesuaikan jika servo Anda terpasang terbalik secara fisik
INVERT_PAN = False
INVERT_TILT = True

# Smoothing (Exponential Moving Average) untuk koordinat wajah
FACE_SMOOTH_FACTOR = 0.7  # 0.0 - 1.0 (makin tinggi makin stabil / halus)

# -------------------------------------------------------------
# GESTURE IDENTIFICATION MAPPING
# -------------------------------------------------------------
# Mapping gesture MediaPipe ke kode angka untuk Arduino
GESTURE_CODES = {
    "None": 0,
    "Open_Palm": 1,       # Resume / Aktifkan Tracking
    "Closed_Fist": 2,     # Pause / Kunci Posisi Servo
    "Victory": 3,         # Reset Posisi Servo ke Center (90, 90)
    "Thumb_Up": 4,        # Nodding / Gerakan Mengangguk Servo
    "Pointing_Up": 5,     # Mode Pointer
    "Thumb_Down": 6,      # Standby
    "ILoveYou": 7         # Special Action
}

# Label nama dalam Bahasa Indonesia untuk visual HUD
GESTURE_DISPLAY_NAMES = {
    "None": "Tidak Ada",
    "Open_Palm": "Telapak Terbuka (Tracking Aktif)",
    "Closed_Fist": "Kepalan Tangan (Pause / Lock)",
    "Victory": "Peace / Victory (Reset Tengah)",
    "Thumb_Up": "Jempol Atas (Apresiasi / Nod)",
    "Pointing_Up": "Menunjuk (Fokus)",
    "Thumb_Down": "Jempol Bawah (Standby)",
    "ILoveYou": "I Love You"
}

# Ambang batas kepercayaan deteksi
MIN_FACE_CONFIDENCE = 0.6
MIN_GESTURE_CONFIDENCE = 0.65
GESTURE_DEBOUNCE_FRAMES = 4  # Minimal frame konsisten sebelum gesture diterima
