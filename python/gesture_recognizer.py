"""
Modul Identifikasi Gesture Tangan (Hand Gesture Identification)
Menggunakan MediaPipe GestureRecognizer Tasks API LiteRT dengan Landmark 21 Titik
serta Stabilisasi Debounce untuk klasifikasi gesture yang akurat dan stabil.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import config

@dataclass
class HandGestureResult:
    hand_detected: bool = False
    gesture_name: str = "None"
    gesture_display: str = config.GESTURE_DISPLAY_NAMES.get("None", "Tidak Ada")
    gesture_code: int = 0
    confidence: float = 0.0
    handedness: str = "Unknown"
    landmarks_px: List[Tuple[int, int]] = field(default_factory=list)
    bbox: Optional[Tuple[int, int, int, int]] = None

class HandGestureIdentifier:
    def __init__(self, model_path: str = config.GESTURE_MODEL_PATH):
        self.model_path = model_path
        
        # Konfigurasi MediaPipe GestureRecognizer
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.GestureRecognizerOptions(
            base_options=base_options,
            num_hands=1,  # Fokus pada tangan utama pengendali
            min_hand_detection_confidence=config.MIN_GESTURE_CONFIDENCE,
            min_hand_presence_confidence=config.MIN_GESTURE_CONFIDENCE,
            min_tracking_confidence=config.MIN_GESTURE_CONFIDENCE
        )
        self.recognizer = vision.GestureRecognizer.create_from_options(options)

        # Buffer Debounce untuk mencegah flicker
        self.history = deque(maxlen=config.GESTURE_DEBOUNCE_FRAMES)
        self.stable_gesture_name = "None"
        self.is_enabled = True

    def process_frame(self, frame_bgr) -> HandGestureResult:
        """
        Menganalisis frame BGR untuk mendeteksi tangan dan mengenali gesture.
        """
        res = HandGestureResult()
        if not self.is_enabled:
            return res

        h, w, _ = frame_bgr.shape
        
        # Format ke RGB MediaPipe
        rgb_frame = frame_bgr[:, :, ::-1].copy()
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Inferensi model
        result = self.recognizer.recognize(mp_image)

        if not result.hand_landmarks or len(result.hand_landmarks) == 0:
            self.history.append("None")
            self._update_stable_gesture()
            res.gesture_name = self.stable_gesture_name
            res.gesture_code = config.GESTURE_CODES.get(self.stable_gesture_name, 0)
            res.gesture_display = config.GESTURE_DISPLAY_NAMES.get(self.stable_gesture_name, "Tidak Ada")
            return res

        # Ambil tangan pertama (pengendali)
        raw_landmarks = result.hand_landmarks[0]
        
        # Konversi koordinat normalisasi (0.0 - 1.0) ke piksel
        landmarks_px = []
        xs, ys = [], []
        for lm in raw_landmarks:
            px = int(lm.x * w)
            py = int(lm.y * h)
            landmarks_px.append((px, py))
            xs.append(px)
            ys.append(py)

        # Bounding box tangan
        min_x, max_x = max(0, min(xs) - 15), min(w, max(xs) + 15)
        min_y, max_y = max(0, min(ys) - 15), min(h, max(ys) + 15)
        hand_bbox = (min_x, min_y, max_x - min_x, max_y - min_y)

        # Deteksi nama gesture dari classifier bawaan
        raw_gesture_name = "None"
        confidence = 0.0
        if result.gestures and len(result.gestures[0]) > 0:
            top_category = result.gestures[0][0]
            raw_gesture_name = top_category.category_name
            confidence = top_category.score

        # Handedness (Kanan / Kiri)
        handedness = "Hand"
        if result.handedness and len(result.handedness[0]) > 0:
            handedness = result.handedness[0][0].category_name

        # Masukkan ke buffer filter debounce
        self.history.append(raw_gesture_name)
        self._update_stable_gesture()

        res.hand_detected = True
        res.gesture_name = self.stable_gesture_name
        res.gesture_code = config.GESTURE_CODES.get(self.stable_gesture_name, 0)
        res.gesture_display = config.GESTURE_DISPLAY_NAMES.get(self.stable_gesture_name, "Tidak Ada")
        res.confidence = float(confidence)
        res.handedness = handedness
        res.landmarks_px = landmarks_px
        res.bbox = hand_bbox

        return res

    def _update_stable_gesture(self):
        """Memastikan gesture bertahan beberapa frame sebelum mengganti state."""
        if not self.history:
            self.stable_gesture_name = "None"
            return
            
        most_common = max(set(self.history), key=self.history.count)
        count = self.history.count(most_common)
        
        # Harus memenuhi syarat minimal konsistensi frame
        if count >= (config.GESTURE_DEBOUNCE_FRAMES // 2) + 1:
            self.stable_gesture_name = most_common

    def close(self):
        """Membersihkan resource recognizer."""
        if hasattr(self, 'recognizer') and self.recognizer:
            self.recognizer.close()
