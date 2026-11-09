"""
Modul Pelacakan Wajah (Face Tracking Mechanism)
Menggunakan MediaPipe FaceDetector (BlazeFace LiteRT) dan Algoritma Kontrol Proporsional
dengan Deadzone & Smoothing untuk mengarahkan servo 2-axis Pan-Tilt ke wajah pengguna.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import config

@dataclass
class FaceTrackingResult:
    face_detected: bool = False
    bbox: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)
    face_center: Optional[Tuple[int, int]] = None     # (cx, cy)
    offset: Tuple[int, int] = (0, 0)                  # (dx, dy)
    pan_angle: int = config.PAN_CENTER
    tilt_angle: int = config.TILT_CENTER
    confidence: float = 0.0
    in_deadzone: bool = False

class FaceTracker:
    def __init__(self, model_path: str = config.FACE_MODEL_PATH):
        self.model_path = model_path
        
        # Inisialisasi Detektor Wajah MediaPipe Tasks
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.FaceDetectorOptions(
            base_options=base_options,
            min_detection_confidence=config.MIN_FACE_CONFIDENCE
        )
        self.detector = vision.FaceDetector.create_from_options(options)

        # Inisialisasi variabel sudut
        self.pan_angle: float = float(config.PAN_CENTER)
        self.tilt_angle: float = float(config.TILT_CENTER)
        self.smooth_pan: float = float(config.PAN_CENTER)
        self.smooth_tilt: float = float(config.TILT_CENTER)

        # Variabel Smoothing EMA (Exponential Moving Average)
        self.smooth_cx: Optional[float] = None
        self.smooth_cy: Optional[float] = None

        # Status kontrol
        self.is_paused: bool = False
        self.is_enabled: bool = True
        self.invert_pan: bool = config.INVERT_PAN
        self.invert_tilt: bool = config.INVERT_TILT

    def reset_center(self):
        """Mereset posisi servo ke posisi netral tengah (90, 90)."""
        self.pan_angle = float(config.PAN_CENTER)
        self.tilt_angle = float(config.TILT_CENTER)
        self.smooth_pan = float(config.PAN_CENTER)
        self.smooth_tilt = float(config.TILT_CENTER)
        self.smooth_cx = None
        self.smooth_cy = None

    def set_paused(self, paused: bool):
        """Menjeda atau melanjutkan pelacakan servo."""
        self.is_paused = paused

    def process_frame(self, frame_bgr) -> FaceTrackingResult:
        """
        Memproses satu frame video (BGR dari OpenCV), mendeteksi wajah,
        dan menghitung sudut servo Pan & Tilt.
        """
        res = FaceTrackingResult(
            pan_angle=int(round(self.pan_angle)),
            tilt_angle=int(round(self.tilt_angle))
        )

        if not self.is_enabled:
            return res

        h, w, _ = frame_bgr.shape
        frame_center_x = w // 2
        frame_center_y = h // 2

        # Konversi BGR OpenCV ke format MediaPipe RGB Image
        # Note: frame_bgr[:, :, ::-1] menghasilkan view RGB
        rgb_frame = frame_bgr[:, :, ::-1].copy()
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Jalankan deteksi wajah
        detection_result = self.detector.detect(mp_image)

        if not detection_result.detections:
            # Tidak ada wajah terdeteksi, pertahankan sudut saat ini
            return res

        # Cari wajah dengan bounding box terbesar (pengguna utama terdekat)
        largest_detection = None
        max_area = 0

        for d in detection_result.detections:
            bb = d.bounding_box
            area = bb.width * bb.height
            if area > max_area:
                max_area = area
                largest_detection = d

        if largest_detection is None:
            return res

        bb = largest_detection.bounding_box
        confidence = largest_detection.categories[0].score if largest_detection.categories else 0.0

        # Koordinat Bounding Box
        bx = max(0, bb.origin_x)
        by = max(0, bb.origin_y)
        bw = min(w - bx, bb.width)
        bh = min(h - by, bb.height)

        # Hitung pusat wajah mentah
        raw_cx = bx + (bw // 2)
        raw_cy = by + (bh // 2)

        # Terapkan Exponential Moving Average (EMA) untuk meredam jitter
        if self.smooth_cx is None:
            self.smooth_cx = float(raw_cx)
            self.smooth_cy = float(raw_cy)
        else:
            alpha = config.FACE_SMOOTH_FACTOR
            self.smooth_cx = (alpha * self.smooth_cx) + ((1.0 - alpha) * raw_cx)
            self.smooth_cy = (alpha * self.smooth_cy) + ((1.0 - alpha) * raw_cy)

        current_cx = int(round(self.smooth_cx))
        current_cy = int(round(self.smooth_cy))

        # Hitung deviasi / kesalahan (Error Offset) dari pusat layar
        # dx positif = wajah berada di sebelah kanan pusat
        # dy positif = wajah berada di sebelah bawah pusat
        dx = current_cx - frame_center_x
        dy = current_cy - frame_center_y

        # Periksa apakah deviasi berada di dalam zona toleransi (Deadzone)
        in_deadzone_x = abs(dx) <= config.DEADZONE_X
        in_deadzone_y = abs(dy) <= config.DEADZONE_Y
        in_deadzone = in_deadzone_x and in_deadzone_y

        # Logika Pemetaan Posisi Wajah ke Sudut Servo (Kamera Laptop Statis)
        # Menggunakan Absolute Proportional Mapping agar servo TIDAK berputar liar/kencang
        if not self.is_paused:
            # 1. Hitung sudut target Pan (Horizontal) secara proporsional dari pusat layar
            half_w = float(frame_center_x) if frame_center_x > 0 else 320.0
            norm_dx = max(-1.0, min(1.0, float(dx) / half_w))
            
            # Rentang ayunan sudut maksimum dari posisi netral 90 (Limit +- 20 derajat: rentang 70 - 110)
            PAN_RANGE = 20.0
            sign_pan = -1.0 if self.invert_pan else 1.0
            
            target_pan_val = float(config.PAN_CENTER) + (norm_dx * PAN_RANGE * sign_pan)
            
            # Batasi target pan di batas aman
            target_pan_val = max(float(config.PAN_MIN), min(float(config.PAN_MAX), target_pan_val))

            # Terapkan Exponential Moving Average (EMA) agar pergerakan servo meluncur tenang
            alpha_pan = 0.75
            self.smooth_pan = (alpha_pan * self.smooth_pan) + ((1.0 - alpha_pan) * target_pan_val)
            self.pan_angle = self.smooth_pan

            # 2. Hitung sudut target Tilt (Vertikal) jika digunakan
            half_h = float(frame_center_y) if frame_center_y > 0 else 240.0
            norm_dy = max(-1.0, min(1.0, float(dy) / half_h))
            TILT_RANGE = 40.0
            sign_tilt = -1.0 if self.invert_tilt else 1.0
            target_tilt_val = float(config.TILT_CENTER) + (norm_dy * TILT_RANGE * sign_tilt)
            target_tilt_val = max(float(config.TILT_MIN), min(float(config.TILT_MAX), target_tilt_val))

            alpha_tilt = 0.75
            self.smooth_tilt = (alpha_tilt * self.smooth_tilt) + ((1.0 - alpha_tilt) * target_tilt_val)
            self.tilt_angle = self.smooth_tilt

        # Isi hasil data pelacakan
        res.face_detected = True
        res.bbox = (bx, by, bw, bh)
        res.face_center = (current_cx, current_cy)
        res.offset = (dx, dy)
        res.pan_angle = int(round(self.pan_angle))
        res.tilt_angle = int(round(self.tilt_angle))
        res.confidence = float(confidence)
        res.in_deadzone = in_deadzone

        return res

    def close(self):
        """Membersihkan resource model."""
        if hasattr(self, 'detector') and self.detector:
            self.detector.close()
