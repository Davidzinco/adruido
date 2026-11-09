"""
=============================================================================
SISTEM KIPAS OTOMATIS & PELACAKAN WAJAH (PC / PYTHON)
=============================================================================
Aplikasi Computer Vision untuk Kipas Pintar Berbasis Jarak & Wajah:
1. Membaca feed kamera webcam/laptop secara realtime.
2. Melacak posisi wajah pengguna (Horizontal Pan).
3. Mengirimkan instruksi sudut servo ke Arduino Uno via Serial.
4. Menerima data telemetri dari Arduino (Jarak HC-SR04 & Status Nyala Kipas).
5. Menampilkan antarmuka visual (HUD) informatif dengan status lengkap.
=============================================================================
"""

import argparse
import sys
import time
from pathlib import Path
import cv2
import numpy as np

# Pastikan folder modul 'python' masuk ke dalam sys.path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import config
from model_downloader import ensure_models_exist
from serial_comm import ArduinoSerial
from tracker import FaceTracker

class KipasHUDVisualizer:
    """Menggambar antarmuka visual HUD khusus sistem kipas otomatis."""
    def __init__(self):
        self.COLOR_BG = (25, 28, 32)
        self.COLOR_CYAN = (240, 200, 0)
        self.COLOR_GREEN = (50, 220, 100)
        self.COLOR_YELLOW = (0, 220, 255)
        self.COLOR_RED = (60, 60, 245)
        self.COLOR_ORANGE = (0, 140, 255)
        self.COLOR_WHITE = (245, 245, 245)
        self.COLOR_GRAY = (140, 140, 140)

    def draw(self, frame: np.ndarray,
             face_res,
             jarak_cm: float,
             kipas_on: bool,
             arduino_servo_angle: int,
             fps: float,
             serial_connected: bool,
             port_name: str,
             is_paused: bool) -> np.ndarray:
        canvas = frame.copy()
        h, w, _ = canvas.shape
        cx, cy = w // 2, h // 2

        # 1. Deadzone Reticle di Pusat Layar
        self._draw_reticle(canvas, cx, cy)

        # 2. Kotak Pelacakan Wajah
        if face_res.face_detected and face_res.bbox:
            self._draw_face_box(canvas, face_res, cx, cy)

        # 3. Header Atas
        self._draw_header(canvas, fps, serial_connected, port_name, w)

        # 4. Panel Info Kipas & Sensor (Kiri Atas / Bawah)
        self._draw_kipas_panel(canvas, face_res.pan_angle, jarak_cm, kipas_on, arduino_servo_angle, is_paused)

        # 5. Footer Panduan Tombol
        self._draw_footer(canvas, w, h)

        return canvas

    def _draw_reticle(self, img: np.ndarray, cx: int, cy: int):
        dx, dy = config.DEADZONE_X, config.DEADZONE_Y
        cv2.rectangle(img, (cx - dx, cy - dy), (cx + dx, cy + dy), (80, 150, 100), 1, cv2.LINE_AA)
        cv2.line(img, (cx - 12, cy), (cx + 12, cy), self.COLOR_GREEN, 1, cv2.LINE_AA)
        cv2.line(img, (cx, cy - 12), (cx, cy + 12), self.COLOR_GREEN, 1, cv2.LINE_AA)
        cv2.circle(img, (cx, cy), 2, self.COLOR_WHITE, -1)

    def _draw_face_box(self, img: np.ndarray, res, cx: int, cy: int):
        bx, by, bw, bh = res.bbox
        fx, fy = res.face_center
        color = self.COLOR_GREEN if res.in_deadzone else self.COLOR_CYAN

        # Sudut siku-siku (Corner brackets)
        klen = min(20, bw // 4, bh // 4)
        th = 2
        # Kiri Atas
        cv2.line(img, (bx, by), (bx + klen, by), color, th, cv2.LINE_AA)
        cv2.line(img, (bx, by), (bx, by + klen), color, th, cv2.LINE_AA)
        # Kanan Atas
        cv2.line(img, (bx + bw, by), (bx + bw - klen, by), color, th, cv2.LINE_AA)
        cv2.line(img, (bx + bw, by), (bx + bw, by + klen), color, th, cv2.LINE_AA)
        # Kiri Bawah
        cv2.line(img, (bx, by + bh), (bx + klen, by + bh), color, th, cv2.LINE_AA)
        cv2.line(img, (bx, by + bh), (bx, by + bh - klen), color, th, cv2.LINE_AA)
        # Kanan Bawah
        cv2.line(img, (bx + bw, by + bh), (bx + bw - klen, by + bh), color, th, cv2.LINE_AA)
        cv2.line(img, (bx + bw, by + bh), (bx + bw, by + bh - klen), color, th, cv2.LINE_AA)

        # Garis deviasi dari pusat wajah ke garis tengah
        cv2.circle(img, (fx, fy), 4, color, -1)
        cv2.line(img, (fx, fy), (cx, fy), self.COLOR_YELLOW, 1, cv2.LINE_AA)

        label = f"WAJAH: {int(res.confidence * 100)}%"
        cv2.putText(img, label, (bx, max(15, by - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    def _draw_header(self, img: np.ndarray, fps: float, connected: bool, port: str, width: int):
        # Bar Atas
        cv2.rectangle(img, (0, 0), (width, 36), self.COLOR_BG, -1)
        cv2.line(img, (0, 36), (width, 36), (60, 65, 75), 1)

        # Judul
        title = "SISTEM KIPAS OTOMATIS & FACE TRACKING"
        cv2.putText(img, title, (14, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.55, self.COLOR_WHITE, 1, cv2.LINE_AA)

        # Status Serial & FPS
        port_text = f"ARDUINO: {port if connected else 'SIMULASI (DISCONNECTED)'}"
        p_color = self.COLOR_GREEN if connected else self.COLOR_ORANGE
        cv2.circle(img, (width - 240, 18), 5, p_color, -1)
        cv2.putText(img, port_text, (width - 225, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.42, self.COLOR_WHITE, 1, cv2.LINE_AA)

        fps_text = f"FPS: {fps:.0f}"
        cv2.putText(img, fps_text, (width - 60, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.42, self.COLOR_CYAN, 1, cv2.LINE_AA)

    def _draw_kipas_panel(self, img: np.ndarray, target_pan: int, jarak_cm: float, kipas_on: bool, arduino_servo: int, is_paused: bool):
        # Panel Informasi Status
        px, py, pw, ph = 14, 50, 240, 150
        sub = img[py:py+ph, px:px+pw]
        overlay = np.zeros_like(sub)
        overlay[:] = self.COLOR_BG
        cv2.addWeighted(sub, 0.25, overlay, 0.75, 0, sub)
        cv2.rectangle(img, (px, py), (px + pw, py + ph), (70, 80, 95), 1)

        # 1. Status Kipas
        cv2.putText(img, "STATUS KIPAS:", (px + 10, py + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.COLOR_GRAY, 1, cv2.LINE_AA)
        if kipas_on:
            cv2.rectangle(img, (px + 130, py + 10), (px + 225, py + 30), self.COLOR_GREEN, -1)
            cv2.putText(img, "NYALA (ON)", (px + 137, py + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (10, 30, 10), 1, cv2.LINE_AA)
        else:
            cv2.rectangle(img, (px + 130, py + 10), (px + 225, py + 30), (50, 50, 60), -1)
            cv2.putText(img, "MATI (OFF)", (px + 138, py + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.42, self.COLOR_GRAY, 1, cv2.LINE_AA)

        # 2. Sensor Jarak HC-SR04
        cv2.putText(img, "JARAK OBJEK:", (px + 10, py + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.COLOR_GRAY, 1, cv2.LINE_AA)
        if jarak_cm > 0:
            dist_str = f"{jarak_cm:.1f} cm"
            d_color = self.COLOR_GREEN if jarak_cm <= 50.0 else self.COLOR_WHITE
        else:
            dist_str = "-- (Jauh)"
            d_color = self.COLOR_GRAY
        cv2.putText(img, dist_str, (px + 130, py + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, d_color, 1, cv2.LINE_AA)

        # 3. Sudut Servo Pan (Target & Aktual)
        cv2.putText(img, "SUDUT SERVO:", (px + 10, py + 86), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.COLOR_GRAY, 1, cv2.LINE_AA)
        angle_str = f"Target {target_pan} deg"
        cv2.putText(img, angle_str, (px + 130, py + 86), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.COLOR_CYAN, 1, cv2.LINE_AA)

        # 4. Mode Pelacakan
        cv2.putText(img, "MODE TRACKING:", (px + 10, py + 117), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.COLOR_GRAY, 1, cv2.LINE_AA)
        if is_paused:
            cv2.putText(img, "PAUSED", (px + 130, py + 117), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.COLOR_YELLOW, 1, cv2.LINE_AA)
        else:
            cv2.putText(img, "AKTIF", (px + 130, py + 117), cv2.FONT_HERSHEY_SIMPLEX, 0.45, self.COLOR_GREEN, 1, cv2.LINE_AA)

        # Visual Mini Slider Sudut Servo (0 - 180)
        bar_x, bar_y, bar_w, bar_h = px + 10, py + 132, pw - 20, 6
        cv2.rectangle(img, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (50, 55, 65), -1)
        # Indikator tengah (90 deg)
        cv2.line(img, (bar_x + bar_w // 2, bar_y - 2), (bar_x + bar_w // 2, bar_y + bar_h + 2), self.COLOR_WHITE, 1)
        # Posisi saat ini
        pos_x = bar_x + int((target_pan / 180.0) * bar_w)
        cv2.circle(img, (pos_x, bar_y + bar_h // 2), 4, self.COLOR_CYAN, -1)

    def _draw_footer(self, img: np.ndarray, width: int, height: int):
        cv2.rectangle(img, (0, height - 26), (width, height), self.COLOR_BG, -1)
        cv2.line(img, (0, height - 26), (width, height - 26), (60, 65, 75), 1)
        hint = "[Q/ESC] Keluar  |  [R] Reset Tengah  |  [P] Jeda/Lanjut  |  [F] Mirror Kamera"
        cv2.putText(img, hint, (14, height - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.38, self.COLOR_GRAY, 1, cv2.LINE_AA)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Kipas Otomatis & Face Tracking (Arduino Uno)")
    parser.add_argument("--camera", type=int, default=config.CAMERA_INDEX, help="Indeks kamera laptop (default: 0)")
    parser.add_argument("--port", type=str, default=config.SERIAL_PORT, help="Port COM Arduino (contoh: COM3, COM4)")
    parser.add_argument("--baud", type=int, default=config.BAUD_RATE, help="Baud rate Serial (default: 115200)")
    parser.add_argument("--no-serial", action="store_true", help="Jalankan dalam mode simulasi tanpa Arduino")
    return parser.parse_args()


def main():
    args = parse_arguments()

    print("=" * 70)
    print("      SISTEM KIPAS OTOMATIS & FACE TRACKING (ARDUINO UNO + PC)      ")
    print("=" * 70)

    # 1. Pastikan model Face Tracking tersedia
    print("[1/4] Memeriksa ketersediaan model MediaPipe Face Detection...")
    try:
        ensure_models_exist()
    except Exception as e:
        print(f"[ERROR] Gagal memverifikasi model: {e}")
        return

    # 2. Inisialisasi Koneksi Serial ke Arduino
    print(f"[2/4] Menginisialisasi komunikasi Serial ke Arduino (Baud: {args.baud})...")
    serial_enabled = not args.no_serial
    arduino = ArduinoSerial(port=args.port, baud_rate=args.baud, enabled=serial_enabled)

    # 3. Inisialisasi Pelacak Wajah
    print("[3/4] Menginisialisasi modul Face Tracking...")
    try:
        tracker = FaceTracker()
        visualizer = KipasHUDVisualizer()
    except Exception as e:
        print(f"[ERROR] Gagal menginisialisasi modul FaceTracker: {e}")
        return

    # 4. Inisialisasi Kamera Laptop
    print(f"[4/4] Membuka kamera laptop (Indeks: {args.camera})...")
    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)

    if not cap.isOpened():
        print(f"[ERROR] Tidak dapat membuka kamera indeks {args.camera}!")
        arduino.close()
        return

    print("\n[OK] Sistem Kipas Otomatis Berhasil Dimulai!")
    print("Arahkan wajah Anda ke kamera untuk melihat servo mengikuti posisi Anda.")
    print("Tekan [Q] di jendela kamera untuk keluar.")
    print("-" * 70)

    prev_time = time.time()
    fps = 30.0
    flip_camera = config.FLIP_HORIZONTAL
    is_paused = False

    # Variabel status telemetri dari Arduino
    jarak_ultrasonik = -1.0
    kipas_menyala = False
    arduino_servo_angle = 90

    window_name = "Kipas Otomatis & Face Tracking"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    try:
        while True:
            t_start = time.time()
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            if flip_camera:
                frame = cv2.flip(frame, 1)

            # Deteksi & Lacak Wajah
            face_result = tracker.process_frame(frame)

            # Kirim target sudut Pan ke Arduino via Serial
            pan_angle = face_result.pan_angle
            # Kirim format paket: <PAN,90,0> atau <PAN>
            arduino.send_data(pan=pan_angle, tilt=90, gesture=0)

            # Baca telemetri dari Arduino (jika ada)
            incoming = arduino.read_incoming()
            if incoming:
                # Format telemetri dari Arduino: $DATA,jarak,fan_status,currentAngle
                if incoming.startswith("$DATA,"):
                    parts = incoming.split(",")
                    if len(parts) >= 4:
                        try:
                            jarak_ultrasonik = float(parts[1])
                            kipas_menyala = (int(parts[2]) == 1)
                            arduino_servo_angle = int(parts[3])
                        except (ValueError, IndexError):
                            pass
                elif "[SYSTEM]" in incoming or "[CONFIG]" in incoming:
                    print(f"[ARDUINO] {incoming}")

            # Hitung FPS
            t_now = time.time()
            dt = t_now - prev_time
            prev_time = t_now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt)

            # Gambar Antarmuka Visual
            display_frame = visualizer.draw(
                frame=frame,
                face_res=face_result,
                jarak_cm=jarak_ultrasonik,
                kipas_on=kipas_menyala,
                arduino_servo_angle=arduino_servo_angle,
                fps=fps,
                serial_connected=arduino.is_connected,
                port_name=arduino.port_name or "N/A",
                is_paused=is_paused
            )

            cv2.imshow(window_name, display_frame)

            # Tangani Tombol Keyboard
            key = cv2.waitKey(1) & 0xFF
            if key in [ord('q'), ord('Q'), 27]: # Q atau ESC
                print("[INFO] Menghentikan program...")
                break
            elif key in [ord('r'), ord('R')]: # Reset ke tengah
                tracker.reset_center()
                print("[COMMAND] Posisi servo direset ke 90 derajat.")
            elif key in [ord('p'), ord('P')]: # Pause / Resume
                is_paused = not is_paused
                tracker.set_paused(is_paused)
                print(f"[COMMAND] Pelacakan {'DIJEDA' if is_paused else 'DILANJUTKAN'}.")
            elif key in [ord('f'), ord('F')]: # Flip camera
                flip_camera = not flip_camera

    except KeyboardInterrupt:
        print("\n[INFO] Dihentikan oleh pengguna (Ctrl+C).")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        tracker.close()
        arduino.close()
        print("[INFO] Selesai. Semua resource ditutup.")


if __name__ == "__main__":
    main()
