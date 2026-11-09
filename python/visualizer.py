"""
Modul Visualizer & HUD (Heads-Up Display)
Menampilkan overlay visual interaktif pada frame kamera:
- Reticle pelacakan wajah & garis deviasi error
- Landmark kerangka tangan & badge identifikasi gesture
- Meteran sudut servo Pan & Tilt, FPS, dan status koneksi Arduino
"""

import cv2
import numpy as np
from typing import List, Tuple
import config
from tracker import FaceTrackingResult
from gesture_recognizer import HandGestureResult

# Definisi Koneksi Landmark Tangan MediaPipe (21 Titik)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Jempol
    (0, 5), (5, 6), (6, 7), (7, 8),        # Telunjuk
    (5, 9), (9, 10), (10, 11), (11, 12),   # Jari Tengah
    (9, 13), (13, 14), (14, 15), (15, 16), # Jari Manis
    (13, 17), (17, 18), (18, 19), (19, 20),# Kelingking
    (0, 17)                                # Dasar Telapak
]

class HUDVisualizer:
    def __init__(self):
        # Palet Warna BGR
        self.COLOR_BG = (20, 24, 28)
        self.COLOR_CYAN = (240, 200, 0)
        self.COLOR_GREEN = (50, 220, 100)
        self.COLOR_YELLOW = (0, 220, 255)
        self.COLOR_RED = (60, 60, 245)
        self.COLOR_ORANGE = (0, 140, 255)
        self.COLOR_WHITE = (245, 245, 245)
        self.COLOR_GRAY = (140, 140, 140)
        self.COLOR_MAGENTA = (220, 50, 220)

    def draw_hud(self, frame: np.ndarray,
                 face_res: FaceTrackingResult,
                 gesture_res: HandGestureResult,
                 fps: float,
                 serial_connected: bool,
                 port_name: str,
                 is_paused: bool) -> np.ndarray:
        """Menggambar seluruh antarmuka visual HUD ke atas frame video."""
        canvas = frame.copy()
        h, w, _ = canvas.shape
        center_x, center_y = w // 2, h // 2

        # 1. Gambar Area Deadzone & Pusat Layar
        self._draw_center_reticle(canvas, center_x, center_y)

        # 2. Gambar Pelacakan Wajah
        if face_res.face_detected and face_res.bbox:
            self._draw_face_tracker(canvas, face_res, center_x, center_y)

        # 3. Gambar Kerangka & Gesture Tangan
        if gesture_res.hand_detected and gesture_res.landmarks_px:
            self._draw_hand_landmarks(canvas, gesture_res)

        # 4. Gambar Panel Header Atas (Status Proyek, FPS, Serial Port)
        self._draw_header(canvas, fps, serial_connected, port_name, w)

        # 5. Gambar Panel Status Samping (Gauge Servo Pan/Tilt & Mode)
        self._draw_status_panel(canvas, face_res, gesture_res, is_paused)

        # 6. Gambar Footer Pintasan Keyboard
        self._draw_footer(canvas, w, h)

        return canvas

    def _draw_center_reticle(self, img: np.ndarray, cx: int, cy: int):
        """Menggambar reticle tengah dan kotak toleransi Deadzone."""
        dx, dy = config.DEADZONE_X, config.DEADZONE_Y
        
        # Kotak Deadzone transparan tipis
        sub_img = img[max(0, cy - dy):min(img.shape[0], cy + dy),
                      max(0, cx - dx):min(img.shape[1], cx + dx)]
        overlay = np.zeros_like(sub_img)
        overlay[:] = (0, 120, 100) # Hijau kebiruan lembut
        cv2.addWeighted(sub_img, 0.85, overlay, 0.15, 0, sub_img)

        # Garis batas deadzone
        cv2.rectangle(img, (cx - dx, cy - dy), (cx + dx, cy + dy), (100, 160, 120), 1, cv2.LINE_AA)

        # Garis silang titik tengah
        cv2.line(img, (cx - 15, cy), (cx + 15, cy), self.COLOR_GREEN, 1, cv2.LINE_AA)
        cv2.line(img, (cx, cy - 15), (cx, cy + 15), self.COLOR_GREEN, 1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), 3, self.COLOR_WHITE, -1)

    def _draw_face_tracker(self, img: np.ndarray, face_res: FaceTrackingResult, cx: int, cy: int):
        """Menggambar penanda visual pada wajah yang terkunci."""
        bx, by, bw, bh = face_res.bbox
        fx, fy = face_res.face_center
        color = self.COLOR_GREEN if face_res.in_deadzone else self.COLOR_CYAN

        # Sudut siku-siku futuristik (Corner brackets)
        line_len = min(25, bw // 4, bh // 4)
        thickness = 2
        # Kiri Atas
        cv2.line(img, (bx, by), (bx + line_len, by), color, thickness)
        cv2.line(img, (bx, by), (bx, by + line_len), color, thickness)
        # Kanan Atas
        cv2.line(img, (bx + bw, by), (bx + bw - line_len, by), color, thickness)
        cv2.line(img, (bx + bw, by), (bx + bw, by + line_len), color, thickness)
        # Kiri Bawah
        cv2.line(img, (bx, by + bh), (bx + line_len, by + bh), color, thickness)
        cv2.line(img, (bx, by + bh), (bx, by + bh - line_len), color, thickness)
        # Kanan Bawah
        cv2.line(img, (bx + bw, by + bh), (bx + bw - line_len, by + bh), color, thickness)
        cv2.line(img, (bx + bw, by + bh), (bx + bw, by + bh - line_len), color, thickness)

        # Titik pusat wajah
        cv2.circle(img, (fx, fy), 5, self.COLOR_YELLOW, -1, cv2.LINE_AA)
        cv2.circle(img, (fx, fy), 9, color, 1, cv2.LINE_AA)

        # Garis vektor kesalahan offset dari pusat layar ke wajah
        if not face_res.in_deadzone:
            cv2.line(img, (cx, cy), (fx, fy), (0, 200, 255), 1, cv2.LINE_AA)

        # Teks label wajah
        status_txt = "TERKUNCI" if face_res.in_deadzone else f"DX:{face_res.offset[0]} DY:{face_res.offset[1]}"
        label = f"TARGET WAJAH ({int(face_res.confidence * 100)}%) | {status_txt}"
        cv2.putText(img, label, (bx, max(18, by - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)

    def _draw_hand_landmarks(self, img: np.ndarray, gesture_res: HandGestureResult):
        """Menggambar koneksi tulang dan persendian jari tangan serta kartu gesture."""
        pts = gesture_res.landmarks_px

        # Gambar garis antar sendi
        for start_idx, end_idx in HAND_CONNECTIONS:
            pt1 = pts[start_idx]
            pt2 = pts[end_idx]
            cv2.line(img, pt1, pt2, (80, 180, 255), 2, cv2.LINE_AA)

        # Gambar titik-titik persendian
        for i, pt in enumerate(pts):
            # Ujung jari diberi warna aksen khusus
            is_tip = i in [4, 8, 12, 16, 20]
            color = self.COLOR_YELLOW if is_tip else self.COLOR_CYAN
            radius = 4 if is_tip else 3
            cv2.circle(img, pt, radius, color, -1, cv2.LINE_AA)
            cv2.circle(img, pt, radius + 1, self.COLOR_BG, 1, cv2.LINE_AA)

        # Badge Gesture di atas tangan
        if gesture_res.bbox:
            gx, gy, gw, gh = gesture_res.bbox
            badge_y = max(25, gy - 12)
            gesture_label = f"[{gesture_res.handedness.upper()}] {gesture_res.gesture_display}"
            
            # Background badge
            (t_w, t_h), _ = cv2.getTextSize(gesture_label, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
            cv2.rectangle(img, (gx, badge_y - t_h - 4), (gx + t_w + 10, badge_y + 4), (30, 30, 30), -1)
            cv2.rectangle(img, (gx, badge_y - t_h - 4), (gx + t_w + 10, badge_y + 4), self.COLOR_MAGENTA, 1)
            cv2.putText(img, gesture_label, (gx + 5, badge_y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.48, self.COLOR_WHITE, 1, cv2.LINE_AA)

    def _draw_header(self, img: np.ndarray, fps: float, serial_connected: bool, port_name: str, w: int):
        """Menggambar bar informasi di bagian atas."""
        # Bar gelap semi-transparan
        header_h = 36
        sub = img[0:header_h, 0:w]
        black_bg = np.zeros_like(sub)
        cv2.addWeighted(sub, 0.25, black_bg, 0.75, 0, sub)
        cv2.line(img, (0, header_h), (w, header_h), (60, 60, 60), 1)

        # Judul Sistem
        cv2.putText(img, "ARDUINO VISION TRACKER", (14, 23),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, self.COLOR_WHITE, 1, cv2.LINE_AA)

        # Status Koneksi Arduino
        if serial_connected:
            serial_text = f"SERIAL: {port_name} [TERHUBUNG]"
            serial_color = self.COLOR_GREEN
        else:
            serial_text = "SERIAL: MODE SIMULASI"
            serial_color = self.COLOR_ORANGE

        cv2.putText(img, serial_text, (280, 23),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, serial_color, 1, cv2.LINE_AA)

        # FPS Meter
        fps_color = self.COLOR_GREEN if fps >= 24 else (self.COLOR_YELLOW if fps >= 15 else self.COLOR_RED)
        fps_text = f"FPS: {fps:.1f}"
        cv2.putText(img, fps_text, (w - 95, 23),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, fps_color, 1, cv2.LINE_AA)

    def _draw_status_panel(self, img: np.ndarray,
                           face_res: FaceTrackingResult,
                           gesture_res: HandGestureResult,
                           is_paused: bool):
        """Menggambar widget informasi sudut Pan & Tilt serta status gesture di sisi kiri."""
        panel_x = 12
        panel_y = 48
        panel_w = 205
        panel_h = 135

        # Kotak panel semi transparan
        sub = img[panel_y:panel_y + panel_h, panel_x:panel_x + panel_w]
        bg = np.zeros_like(sub)
        cv2.addWeighted(sub, 0.3, bg, 0.7, 0, sub)
        cv2.rectangle(img, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (70, 70, 70), 1)

        # 1. Status Tracking
        if is_paused:
            status_str = "STATUS: DIJEDA (PAUSED)"
            status_col = self.COLOR_YELLOW
        elif face_res.face_detected:
            status_str = "STATUS: MELACAK WAJAH"
            status_col = self.COLOR_GREEN
        else:
            status_str = "STATUS: MENCARI WAJAH..."
            status_col = self.COLOR_CYAN

        cv2.putText(img, status_str, (panel_x + 8, panel_y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, status_col, 1, cv2.LINE_AA)

        # 2. Gauge Servo Pan
        self._draw_servo_gauge(img, panel_x + 8, panel_y + 35, "PAN",
                               face_res.pan_angle, config.PAN_MIN, config.PAN_MAX)

        # 3. Gauge Servo Tilt
        self._draw_servo_gauge(img, panel_x + 8, panel_y + 70, "TILT",
                               face_res.tilt_angle, config.TILT_MIN, config.TILT_MAX)

        # 4. Gesture Aktif
        g_name = gesture_res.gesture_name
        g_disp = config.GESTURE_DISPLAY_NAMES.get(g_name, g_name)
        if len(g_disp) > 22:
            g_disp = g_disp[:20] + ".."
        g_label = f"GESTURE: {g_disp}"
        cv2.putText(img, g_label, (panel_x + 8, panel_y + 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, self.COLOR_MAGENTA, 1, cv2.LINE_AA)

    def _draw_servo_gauge(self, img: np.ndarray, x: int, y: int, label: str,
                          val: int, min_val: int, max_val: int):
        """Menggambar progress bar horizontal sudut servo."""
        cv2.putText(img, f"{label}: {val:3d}*", (x, y + 11),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, self.COLOR_WHITE, 1, cv2.LINE_AA)
        
        bar_x = x + 75
        bar_y = y + 2
        bar_w = 110
        bar_h = 10

        # Background bar
        cv2.rectangle(img, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 50, 50), -1)

        # Rasio pengisian
        ratio = max(0.0, min(1.0, (val - min_val) / float(max_val - min_val)))
        fill_w = int(bar_w * ratio)

        # Warna bar gradasi berdasarkan posisi
        cv2.rectangle(img, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), self.COLOR_CYAN, -1)
        # Garis tengah indikator 90 derajat
        mid_x = bar_x + (bar_w // 2)
        cv2.line(img, (mid_x, bar_y - 2), (mid_x, bar_y + bar_h + 2), self.COLOR_YELLOW, 1)

    def _draw_footer(self, img: np.ndarray, w: int, h: int):
        """Menggambar petunjuk tombol pintasan di bagian bawah."""
        footer_h = 24
        sub = img[h - footer_h:h, 0:w]
        black_bg = np.zeros_like(sub)
        cv2.addWeighted(sub, 0.25, black_bg, 0.75, 0, sub)
        cv2.line(img, (0, h - footer_h), (w, h - footer_h), (60, 60, 60), 1)

        shortcuts = "[Q] Keluar  |  [R] Reset Center  |  [P] Jeda/Lanjut  |  [T] Wajah  |  [G] Gesture"
        cv2.putText(img, shortcuts, (14, h - 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, self.COLOR_GRAY, 1, cv2.LINE_AA)
