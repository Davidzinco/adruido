"""
=============================================================================
PROGRAM UTAMA: ARDUINO UNO FACE TRACKING & HAND GESTURE IDENTIFICATION
=============================================================================
Aplikasi Computer Vision menggunakan kamera laptop untuk:
1. Melacak posisi wajah pengguna (Face Tracking 2-Axis Pan & Tilt).
2. Mengidentifikasi gesture tangan (Hand Gesture Identification).
3. Mengirimkan sinyal kendali sudut servo dan kode gesture ke Arduino Uno
   melalui koneksi USB Serial secara realtime.
=============================================================================
"""

import argparse
import sys
import time
import cv2

# Import modul lokal
import config
from model_downloader import ensure_models_exist
from serial_comm import ArduinoSerial
from tracker import FaceTracker
from gesture_recognizer import HandGestureIdentifier
from visualizer import HUDVisualizer

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Arduino Uno Face Tracking & Hand Gesture Identification System"
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=config.CAMERA_INDEX,
        help="Indeks kamera laptop/webcam (default: 0)"
    )
    parser.add_argument(
        "--port",
        type=str,
        default=config.SERIAL_PORT,
        help="Nama COM Port Arduino (contoh: COM3, COM4). Default: Auto-detect"
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=config.BAUD_RATE,
        help="Baud rate komunikasi serial (default: 115200)"
    )
    parser.add_argument(
        "--no-serial",
        action="store_true",
        help="Jalankan tanpa koneksi ke Arduino (Mode Simulasi pada Layar)"
    )
    parser.add_argument(
        "--width",
        type=int,
        default=config.FRAME_WIDTH,
        help="Lebar resolusi frame kamera (default: 640)"
    )
    parser.add_argument(
        "--height",
        type=int,
        default=config.FRAME_HEIGHT,
        help="Tinggi resolusi frame kamera (default: 480)"
    )
    return parser.parse_args()

def main():
    args = parse_arguments()

    print("=" * 70)
    print("  ARDUINO UNO FACE TRACKING & HAND GESTURE IDENTIFICATION SYSTEM  ")
    print("=" * 70)

    # 1. Pastikan model AI telah diunduh
    print("[1/5] Memeriksa ketersediaan model AI MediaPipe...")
    try:
        ensure_models_exist()
    except Exception as e:
        print(f"[ERROR] Gagal mengunduh atau memuat model: {e}")
        return

    # 2. Inisialisasi Komunikasi Serial Arduino
    print("[2/5] Menginisialisasi komunikasi Serial...")
    serial_enabled = not args.no_serial
    arduino = ArduinoSerial(port=args.port, baud_rate=args.baud, enabled=serial_enabled)

    # 3. Inisialisasi Detektor Wajah & Gesture
    print("[3/5] Memuat model Face Tracking & Hand Gesture...")
    try:
        tracker = FaceTracker()
        gesture_id = HandGestureIdentifier()
        visualizer = HUDVisualizer()
    except Exception as e:
        print(f"[ERROR] Gagal menginisialisasi modul penglihatan komputer: {e}")
        return

    # 4. Inisialisasi Kamera Laptop
    print(f"[4/5] Membuka kamera laptop (Indeks: {args.camera})...")
    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
    
    # Pengaturan resolusi kamera
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, 30)

    if not cap.isOpened():
        print(f"[ERROR] Tidak dapat mengakses kamera pada indeks {args.camera}!")
        print("Pastikan kamera laptop tidak sedang digunakan oleh aplikasi lain (Zoom, Teams, dsb.)")
        arduino.close()
        return

    # Baca frame uji
    ret, test_frame = cap.read()
    if not ret or test_frame is None:
        print("[ERROR] Berhasil membuka kamera, tetapi tidak dapat membaca frame video.")
        cap.release()
        arduino.close()
        return

    print("[5/5] Sistem siap! Menjalankan antarmuka grafis...")
    print("-" * 70)
    print("PETUNJUK KONTROL TOMBOL:")
    print("  [Q] atau [ESC] : Keluar dari program")
    print("  [R]            : Reset posisi servo ke pusat (90, 90)")
    print("  [P]            : Jeda (Pause) / Lanjutkan pelacakan servo")
    print("  [T]            : Aktifkan / Nonaktifkan pelacakan wajah")
    print("  [G]            : Aktifkan / Nonaktifkan identifikasi gesture")
    print("  [S]            : Sambungkan ulang port Serial Arduino")
    print("-" * 70)

    # Variabel waktu & FPS
    prev_time = time.time()
    fps = 30.0
    is_paused = False

    window_name = "Face Tracking & Hand Gesture - Arduino Uno"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    try:
        while True:
            loop_start = time.time()
            ret, frame = cap.read()
            if not ret or frame is None:
                print("[WARNING] Frame kamera kosong atau terputus.")
                time.sleep(0.01)
                continue

            # Mirror horizontal agar pergerakan tangan dan wajah alami
            if config.FLIP_HORIZONTAL:
                frame = cv2.flip(frame, 1)

            # 1. Jalankan Pelacakan Wajah
            face_result = tracker.process_frame(frame)

            # 2. Jalankan Identifikasi Gesture Tangan
            gesture_result = gesture_id.process_frame(frame)

            # 3. Logika Interaksi Gesture -> Kontrol Pelacakan
            current_gesture = gesture_result.gesture_name
            if current_gesture == "Closed_Fist":
                # Kepalan tangan: Mengunci posisi servo saat ini (Pause)
                tracker.set_paused(True)
                is_paused = True
            elif current_gesture == "Open_Palm":
                # Telapak terbuka: Melanjutkan pelacakan wajah
                tracker.set_paused(False)
                is_paused = False
            elif current_gesture == "Victory":
                # Peace sign: Reset servo ke tengah (90, 90)
                tracker.reset_center()

            # 4. Kirim Data ke Arduino via Serial
            pan_val = face_result.pan_angle
            tilt_val = face_result.tilt_angle
            g_code = gesture_result.gesture_code

            arduino.send_data(pan=pan_val, tilt=tilt_val, gesture=g_code)

            # 5. Cek pesan masuk dari Arduino (jika ada)
            arduino_msg = arduino.read_incoming()
            if arduino_msg:
                print(f"[ARDUINO]: {arduino_msg}")

            # 6. Hitung FPS Rata-rata
            now = time.time()
            dt = now - prev_time
            prev_time = now
            if dt > 0:
                current_fps = 1.0 / dt
                fps = (0.9 * fps) + (0.1 * current_fps)

            # 7. Render HUD Overlay
            display_frame = visualizer.draw_hud(
                frame=frame,
                face_res=face_result,
                gesture_res=gesture_result,
                fps=fps,
                serial_connected=arduino.is_connected,
                port_name=arduino.port_name or "SIMULASI",
                is_paused=is_paused
            )

            cv2.imshow(window_name, display_frame)

            # 8. Tangani Input Keyboard
            key = cv2.waitKey(1) & 0xFF
            if key in [ord('q'), ord('Q'), 27]: # 27 = ESC
                print("[INFO] Perintah keluar diterima. Menghentikan program...")
                break
            elif key in [ord('r'), ord('R')]:
                print("[AKSI] Reset posisi servo ke pusat (90, 90)")
                tracker.reset_center()
            elif key in [ord('p'), ord('P')]:
                is_paused = not is_paused
                tracker.set_paused(is_paused)
                print(f"[AKSI] Status pelacakan: {'DIJEDA' if is_paused else 'AKTIF'}")
            elif key in [ord('t'), ord('T')]:
                tracker.is_enabled = not tracker.is_enabled
                print(f"[AKSI] Deteksi wajah: {'AKTIF' if tracker.is_enabled else 'NONAKTIF'}")
            elif key in [ord('g'), ord('G')]:
                gesture_id.is_enabled = not gesture_id.is_enabled
                print(f"[AKSI] Deteksi gesture: {'AKTIF' if gesture_id.is_enabled else 'NONAKTIF'}")
            elif key in [ord('s'), ord('S')]:
                if not arduino.is_connected:
                    print("[AKSI] Mencoba menghubungkan ulang ke Arduino...")
                    arduino.connect()

    except KeyboardInterrupt:
        print("\n[INFO] Dihentikan oleh pengguna (Ctrl+C).")

    finally:
        # Bersihkan resource
        print("[INFO] Membersihkan resource sistem...")
        cap.release()
        cv2.destroyAllWindows()
        tracker.close()
        gesture_id.close()
        arduino.close()
        print("[INFO] Program selesai.")

if __name__ == "__main__":
    main()
