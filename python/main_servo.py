"""
=============================================================================
PROGRAM FACE TRACKING SERVO 360 + KONTROL MANUAL TOMBOL PANAH
=============================================================================
Perbaikan total:
- Logika arah KANAN dan KIRI dijamin simetris dan bekerja dua-duanya.
- Kontrol manual via Arrow Keys (Kiri/Kanan) atau tombol A/D.
- SPASI untuk beralih antara MODE AUTO (Tracking Wajah) dan MODE MANUAL.
- Cetak debug di konsol agar bisa melihat nilai PWM yang dikirim.
=============================================================================
"""

import argparse
import sys
import time
from pathlib import Path
import cv2
import numpy as np

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import config
from model_downloader import ensure_models_exist
from serial_comm import ArduinoSerial
from tracker import FaceTracker


# ==========================================
# KONSTANTA KONTROL SERVO 360
# ==========================================
# Ubah nilai-nilai ini jika perlu kalibrasi

STOP_PWM_DEFAULT = 90     # Nilai PWM yang membuat motor servo DIAM (biasanya 90)
SPEED_OFFSET_DEFAULT = 15 # Selisih PWM dari STOP untuk berputar (75 = kiri, 105 = kanan)

# Batas rotasi: Maksimal 20 derajat ke kiri (CCW) dan 20 derajat ke kanan (CW) dari posisi tengah
MAX_ROTATION_LIMIT = 20.0  # Limit 20 derajat
CENTER_ANGLE = 90.0
LIMIT_LEFT = CENTER_ANGLE - MAX_ROTATION_LIMIT   # 90 - 20 = 70.0 derajat (Batas Kiri / CCW)
LIMIT_RIGHT = CENTER_ANGLE + MAX_ROTATION_LIMIT  # 90 + 20 = 110.0 derajat (Batas Kanan / CW)

ROTATION_SPEED_DEG_PER_SEC = 80.0  # Estimasi kecepatan putar servo (deg/s)
DEADBAND_ANGLE = 3.0               # Toleransi sudut untuk stop (mencegah bolak-balik jitter)


def draw_hud(frame, face_res, virtual_angle, target_angle, pwm_cmd, motion_text, motion_color,
             fps, connected, port, mode, stop_pwm, speed_ofs, is_inv,
             fan_mode="AUTO", fan_on=False):
    """Menggambar antarmuka visual HUD di atas frame kamera."""
    canvas = frame.copy()
    h, w, _ = canvas.shape
    cx, cy = w // 2, h // 2

    C_BG = (25, 28, 32)
    C_CYAN = (240, 200, 0)
    C_GREEN = (50, 220, 100)
    C_YELLOW = (0, 220, 255)
    C_WHITE = (245, 245, 245)
    C_GRAY = (140, 140, 140)
    C_ORANGE = (0, 140, 255)
    C_RED = (60, 60, 245)

    # 1. Deadzone box
    ddx, ddy = config.DEADZONE_X, config.DEADZONE_Y
    cv2.rectangle(canvas, (cx - ddx, cy - ddy), (cx + ddx, cy + ddy), (80, 150, 100), 1, cv2.LINE_AA)
    cv2.line(canvas, (cx - 15, cy), (cx + 15, cy), C_GREEN, 1, cv2.LINE_AA)
    cv2.line(canvas, (cx, cy - 15), (cx, cy + 15), C_GREEN, 1, cv2.LINE_AA)

    # 2. Face bounding box
    if face_res.face_detected and face_res.bbox:
        bx, by, bw, bh = face_res.bbox
        fx, fy = face_res.face_center
        bc = C_GREEN if face_res.in_deadzone else C_CYAN
        kl = min(20, bw // 4, bh // 4)
        for (x0, y0, x1, y1) in [
            (bx, by, bx + kl, by), (bx, by, bx, by + kl),
            (bx + bw, by, bx + bw - kl, by), (bx + bw, by, bx + bw, by + kl),
            (bx, by + bh, bx + kl, by + bh), (bx, by + bh, bx, by + bh - kl),
            (bx + bw, by + bh, bx + bw - kl, by + bh), (bx + bw, by + bh, bx + bw, by + bh - kl),
        ]:
            cv2.line(canvas, (x0, y0), (x1, y1), bc, 2, cv2.LINE_AA)
        cv2.circle(canvas, (fx, fy), 4, bc, -1)
        cv2.line(canvas, (fx, fy), (cx, fy), C_YELLOW, 1, cv2.LINE_AA)
        cv2.putText(canvas, f"WAJAH ({int(face_res.confidence * 100)}%)", (bx, max(18, by - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, bc, 1, cv2.LINE_AA)

    # 3. Header
    cv2.rectangle(canvas, (0, 0), (w, 36), C_BG, -1)
    cv2.line(canvas, (0, 36), (w, 36), (60, 65, 75), 1)
    mode_label = "[AUTO: TRACKING WAJAH]" if mode == "AUTO" else "[MANUAL: TOMBOL PANAH]"
    mode_c = C_GREEN if mode == "AUTO" else C_YELLOW
    cv2.putText(canvas, mode_label, (14, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.52, mode_c, 1, cv2.LINE_AA)
    p_c = C_GREEN if connected else C_ORANGE
    cv2.circle(canvas, (w - 240, 18), 5, p_c, -1)
    cv2.putText(canvas, f"{'PORT: ' + port if connected else 'SIMULASI'}", (w - 225, 23),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, C_WHITE, 1, cv2.LINE_AA)
    cv2.putText(canvas, f"FPS: {fps:.0f}", (w - 60, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.42, C_CYAN, 1, cv2.LINE_AA)

    # 4. Panel info
    px, py0, pw, ph = 14, 50, 275, 184
    sub = canvas[py0:py0 + ph, px:px + pw]
    ov = np.zeros_like(sub); ov[:] = C_BG
    cv2.addWeighted(sub, 0.18, ov, 0.82, 0, sub)
    cv2.rectangle(canvas, (px, py0), (px + pw, py0 + ph), (70, 80, 95), 1)

    cv2.putText(canvas, "STATUS:", (px + 10, py0 + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.42, C_GRAY, 1, cv2.LINE_AA)
    cv2.putText(canvas, motion_text, (px + 75, py0 + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.40, motion_color, 1, cv2.LINE_AA)

    cv2.putText(canvas, "POSISI VIRTUAL:", (px + 10, py0 + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.42, C_GRAY, 1, cv2.LINE_AA)
    cv2.putText(canvas, f"{virtual_angle:.1f} deg", (px + 140, py0 + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.48, C_CYAN, 1, cv2.LINE_AA)

    cv2.putText(canvas, "SUDUT TARGET:", (px + 10, py0 + 74), cv2.FONT_HERSHEY_SIMPLEX, 0.42, C_GRAY, 1, cv2.LINE_AA)
    cv2.putText(canvas, f"{target_angle:.1f} deg", (px + 140, py0 + 74), cv2.FONT_HERSHEY_SIMPLEX, 0.45, C_WHITE, 1, cv2.LINE_AA)

    cv2.putText(canvas, "PWM KE ARDUINO:", (px + 10, py0 + 98), cv2.FONT_HERSHEY_SIMPLEX, 0.42, C_GRAY, 1, cv2.LINE_AA)
    pd = "STOP" if pwm_cmd == stop_pwm else ("KANAN" if pwm_cmd > stop_pwm else "KIRI")
    cv2.putText(canvas, f"{pwm_cmd} ({pd})", (px + 140, py0 + 98), cv2.FONT_HERSHEY_SIMPLEX, 0.48, C_YELLOW, 1, cv2.LINE_AA)

    # Slider bar (Rentang 60 deg s/d 120 deg, Limit +- 30 deg)
    bx_b, by_b, bw_b, bh_b = px + 10, py0 + 116, pw - 20, 9
    cv2.rectangle(canvas, (bx_b, by_b), (bx_b + bw_b, by_b + bh_b), (50, 55, 65), -1)
    # Penanda Limit Kiri (60 deg, -30 deg) & Limit Kanan (120 deg, +30 deg)
    cv2.line(canvas, (bx_b, by_b - 3), (bx_b, by_b + bh_b + 3), C_RED, 2)
    cv2.line(canvas, (bx_b + bw_b, by_b - 3), (bx_b + bw_b, by_b + bh_b + 3), C_RED, 2)
    # Penanda Tengah (90 deg)
    cv2.line(canvas, (bx_b + bw_b // 2, by_b - 2), (bx_b + bw_b // 2, by_b + bh_b + 2), C_WHITE, 1)
    nv = max(0.0, min(1.0, (virtual_angle - LIMIT_LEFT) / (LIMIT_RIGHT - LIMIT_LEFT)))
    ix = bx_b + int(nv * bw_b)
    cv2.circle(canvas, (ix, by_b + bh_b // 2), 5, C_GREEN if pwm_cmd == stop_pwm else C_CYAN, -1)

    inv_t = "INVERTED" if is_inv else "NORMAL"

    # Status kipas: AUTO (ikut deteksi wajah) atau MANUAL ON/OFF
    if fan_mode == "ON":
        fan_label, fan_c = "MANUAL: ON", C_GREEN
    elif fan_mode == "OFF":
        fan_label, fan_c = "MANUAL: OFF", C_RED
    else:
        fan_label = "AUTO: ON" if fan_on else "AUTO: OFF"
        fan_c = C_GREEN if fan_on else C_GRAY

    cv2.putText(canvas, "KIPAS:", (px + 10, py0 + 142), cv2.FONT_HERSHEY_SIMPLEX, 0.42, C_GRAY, 1, cv2.LINE_AA)
    cv2.putText(canvas, fan_label, (px + 140, py0 + 142), cv2.FONT_HERSHEY_SIMPLEX, 0.45, fan_c, 1, cv2.LINE_AA)

    cv2.putText(canvas, f"Limit:+-20deg | PWM:{stop_pwm} | Spd:{speed_ofs} | {inv_t}",
                (px + 10, py0 + 168), cv2.FONT_HERSHEY_SIMPLEX, 0.32, C_GRAY, 1, cv2.LINE_AA)

    # 5. Footer
    cv2.rectangle(canvas, (0, h - 28), (w, h), C_BG, -1)
    cv2.line(canvas, (0, h - 28), (w, h - 28), (60, 65, 75), 1)
    cv2.putText(canvas, "[A/D] Putar | [SPASI] Auto/Manual | [K] Kipas | [I] Invert | [R] Reset | [Q] Keluar",
                (12, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.36, C_WHITE, 1, cv2.LINE_AA)

    return canvas


def main():
    parser = argparse.ArgumentParser(description="Servo Face Tracking + Manual Arrow Keys")
    parser.add_argument("--camera", type=int, default=config.CAMERA_INDEX)
    parser.add_argument("--port", type=str, default=config.SERIAL_PORT)
    parser.add_argument("--baud", type=int, default=config.BAUD_RATE)
    parser.add_argument("--no-serial", action="store_true")
    args = parser.parse_args()

    print("=" * 75)
    print("   FACE TRACKING SERVO 360 + KONTROL MANUAL TOMBOL PANAH (A / D)    ")
    print("=" * 75)

    ensure_models_exist()

    arduino = ArduinoSerial(port=args.port, baud_rate=args.baud, enabled=not args.no_serial)
    tracker = FaceTracker()

    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)

    if not cap.isOpened():
        print("[ERROR] Kamera tidak dapat dibuka!")
        arduino.close()
        return

    print()
    print("KONTROL KEYBOARD:")
    print("  [A] atau [Arrow Left]  : Putar servo ke KIRI (Manual)")
    print("  [D] atau [Arrow Right] : Putar servo ke KANAN (Manual)")
    print("  [SPASI]                : Beralih MODE AUTO / MANUAL")
    print("  [K]                    : Kipas AUTO -> ON -> OFF (manual)")
    print("  [I]                    : Balik arah putaran (Invert)")
    print("  [R]                    : Reset posisi ke tengah (90 deg)")
    print("  [ [ / ] ]              : Kalibrasi Stop PWM (+/- 1)")
    print("  [ + / - ]              : Ubah kecepatan putar")
    print("  [Q] / [ESC]            : Keluar")
    print()

    # --- STATE ---
    stop_pwm = STOP_PWM_DEFAULT
    speed_offset = SPEED_OFFSET_DEFAULT
    virtual_angle = CENTER_ANGLE
    target_angle = CENTER_ANGLE
    is_inverted = False
    control_mode = "MANUAL"  # Mulai dari MANUAL agar bisa tes arah dulu
    fan_mode = "AUTO"        # AUTO = ikut deteksi wajah, ON / OFF = manual

    prev_time = time.time()
    fps = 30.0
    flip_cam = config.FLIP_HORIZONTAL
    last_debug_time = 0.0

    window_name = "Servo Controller"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    # Perintah putar:
    # Untuk servo 360 continuous:
    #   PWM = stop_pwm         -> DIAM
    #   PWM = stop_pwm + ofs   -> Putar CW  (fisik: mungkin kanan atau kiri tergantung orientasi)
    #   PWM = stop_pwm - ofs   -> Putar CCW (fisik: kebalikan dari di atas)
    #
    # is_inverted membalik KESELURUHAN arah:
    #   False: "kanan" = PWM naik,  "kiri" = PWM turun
    #   True : "kanan" = PWM turun, "kiri" = PWM naik

    def pwm_for_direction(direction: str) -> int:
        """Menghitung nilai PWM berdasarkan arah yang diinginkan.
        direction: 'left', 'right', atau 'stop'
        """
        if direction == "stop":
            return stop_pwm
        elif direction == "right":
            return (stop_pwm - speed_offset) if is_inverted else (stop_pwm + speed_offset)
        else:  # left
            return (stop_pwm + speed_offset) if is_inverted else (stop_pwm - speed_offset)

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            if flip_cam:
                frame = cv2.flip(frame, 1)

            t_now = time.time()
            dt = max(0.001, min(0.08, t_now - prev_time))
            prev_time = t_now
            fps = 0.9 * fps + 0.1 * (1.0 / dt)

            # Baca tombol keyboard (waitKeyEx untuk menangkap Arrow Keys di Windows)
            key = cv2.waitKeyEx(1)

            # Deteksi arah tombol manual
            pressing_left = False
            pressing_right = False

            if key != -1:
                # Keluar (paksa kipas OFF langsung)
                if key in [ord('q'), ord('Q'), 27]:
                    arduino.send_data(pan=stop_pwm, tilt=90, gesture=0, fan=3)
                    break

                # Siklus mode kipas: AUTO -> ON -> OFF -> AUTO
                elif key in [ord('k'), ord('K')]:
                    fan_mode = {"AUTO": "ON", "ON": "OFF", "OFF": "AUTO"}[fan_mode]
                    print(f"[KIPAS] Mode -> {fan_mode}")

                # Toggle mode servo
                elif key == 32:  # SPASI
                    control_mode = "MANUAL" if control_mode == "AUTO" else "AUTO"
                    print(f"[MODE] -> {control_mode}")

                # Reset
                elif key in [ord('r'), ord('R')]:
                    virtual_angle = CENTER_ANGLE
                    target_angle = CENTER_ANGLE
                    arduino.send_data(pan=stop_pwm, tilt=90, gesture=0)
                    print("[RESET] Posisi virtual -> 90 deg")

                # Invert
                elif key in [ord('i'), ord('I')]:
                    is_inverted = not is_inverted
                    print(f"[INVERT] Arah -> {'TERBALIK' if is_inverted else 'NORMAL'}")

                # Kalibrasi Stop PWM
                elif key == ord('['):
                    stop_pwm -= 1
                    print(f"[STOP PWM] -> {stop_pwm}")
                elif key == ord(']'):
                    stop_pwm += 1
                    print(f"[STOP PWM] -> {stop_pwm}")

                # Kalibrasi kecepatan
                elif key in [ord('+'), ord('=')]:
                    speed_offset = min(20, speed_offset + 1)
                    print(f"[SPEED] -> {speed_offset}")
                elif key in [ord('-'), ord('_')]:
                    speed_offset = max(1, speed_offset - 1)
                    print(f"[SPEED] -> {speed_offset}")

                # Tombol arah KIRI: A, atau Arrow Left (2424832 di Windows waitKeyEx)
                elif key in [ord('a'), ord('A'), 2424832]:
                    pressing_left = True
                    if control_mode == "AUTO":
                        control_mode = "MANUAL"
                        print("[MODE] -> MANUAL (tombol panah ditekan)")

                # Tombol arah KANAN: D, atau Arrow Right (2555904 di Windows waitKeyEx)
                elif key in [ord('d'), ord('D'), 2555904]:
                    pressing_right = True
                    if control_mode == "AUTO":
                        control_mode = "MANUAL"
                        print("[MODE] -> MANUAL (tombol panah ditekan)")

                # Flip kamera
                elif key in [ord('f'), ord('F')]:
                    flip_cam = not flip_cam

            # Deteksi wajah (selalu jalan agar HUD tetap menampilkan kotak wajah)
            face_res = tracker.process_frame(frame)

            h_frame, w_frame, _ = frame.shape
            half_w = float(w_frame // 2)

            # =============================================
            # LOGIKA KONTROL UTAMA
            # =============================================
            motion_text = "DIAM (STOP)"
            motion_color = (50, 220, 100)  # Hijau
            pwm_cmd = stop_pwm

            if control_mode == "MANUAL":
                # ----- KONTROL MANUAL: Tombol A/D atau Arrow Left/Right -----
                if pressing_left:
                    if virtual_angle > LIMIT_LEFT:
                        pwm_cmd = pwm_for_direction("left")
                        virtual_angle -= ROTATION_SPEED_DEG_PER_SEC * dt
                        virtual_angle = max(LIMIT_LEFT, virtual_angle)
                        motion_text = "MANUAL: PUTAR KIRI"
                        motion_color = (240, 200, 0)  # Cyan
                    else:
                        pwm_cmd = stop_pwm
                        motion_text = "MENTOK BATAS KIRI!"
                        motion_color = (60, 60, 245)  # Merah

                elif pressing_right:
                    if virtual_angle < LIMIT_RIGHT:
                        pwm_cmd = pwm_for_direction("right")
                        virtual_angle += ROTATION_SPEED_DEG_PER_SEC * dt
                        virtual_angle = min(LIMIT_RIGHT, virtual_angle)
                        motion_text = "MANUAL: PUTAR KANAN"
                        motion_color = (240, 200, 0)  # Cyan
                    else:
                        pwm_cmd = stop_pwm
                        motion_text = "MENTOK BATAS KANAN!"
                        motion_color = (60, 60, 245)  # Merah

                else:
                    pwm_cmd = stop_pwm
                    motion_text = "MANUAL: SIAP (DIAM)"
                    motion_color = (50, 220, 100)

                target_angle = virtual_angle

            else:
                # ----- KONTROL AUTO: FACE TRACKING -----
                if face_res.face_detected:
                    dx = face_res.offset[0]
                    norm_dx = max(-1.0, min(1.0, float(dx) / half_w))
                    # Rentang rotasi dibatasi tepat 30 derajat (bukan 65 derajat)
                    target_angle = CENTER_ANGLE + (norm_dx * MAX_ROTATION_LIMIT)
                    target_angle = max(LIMIT_LEFT, min(LIMIT_RIGHT, target_angle))

                error = target_angle - virtual_angle

                if abs(error) <= DEADBAND_ANGLE:
                    # Target tercapai -> STOP
                    pwm_cmd = stop_pwm
                    motion_text = "LOCK: MENGHADAP WAJAH"
                    motion_color = (50, 220, 100)

                elif error > 0:
                    # Perlu putar ke KANAN
                    if virtual_angle >= LIMIT_RIGHT:
                        pwm_cmd = stop_pwm
                        motion_text = "MENTOK BATAS KANAN!"
                        motion_color = (60, 60, 245)
                    else:
                        pwm_cmd = pwm_for_direction("right")
                        virtual_angle += ROTATION_SPEED_DEG_PER_SEC * dt
                        virtual_angle = min(LIMIT_RIGHT, virtual_angle)
                        motion_text = "AUTO: PUTAR KANAN"
                        motion_color = (0, 220, 255)

                else:
                    # Perlu putar ke KIRI
                    if virtual_angle <= LIMIT_LEFT:
                        pwm_cmd = stop_pwm
                        motion_text = "MENTOK BATAS KIRI!"
                        motion_color = (60, 60, 245)
                    else:
                        pwm_cmd = pwm_for_direction("left")
                        virtual_angle -= ROTATION_SPEED_DEG_PER_SEC * dt
                        virtual_angle = max(LIMIT_LEFT, virtual_angle)
                        motion_text = "AUTO: PUTAR KIRI"
                        motion_color = (0, 220, 255)

            # Tentukan perintah kipas:
            #   0 = auto, wajah tidak ada  -> OFF setelah jeda
            #   1 = auto, wajah terdeteksi -> ON
            #   2 = manual ON  (paksa nyala)
            #   3 = manual OFF (paksa mati)
            if fan_mode == "ON":
                fan_cmd = 2
                fan_on = True
            elif fan_mode == "OFF":
                fan_cmd = 3
                fan_on = False
            else:
                fan_on = bool(face_res.face_detected)
                fan_cmd = 1 if fan_on else 0

            # Kirim PWM ke Arduino + perintah relay kipas (D3)
            arduino.send_data(pan=pwm_cmd, tilt=90, gesture=0, fan=fan_cmd)
            arduino.read_incoming()

            # Debug log setiap 0.5 detik (supaya bisa periksa di terminal)
            if t_now - last_debug_time > 0.5 and pwm_cmd != stop_pwm:
                last_debug_time = t_now
                print(f"  >> PWM={pwm_cmd} | Virtual={virtual_angle:.1f} | Target={target_angle:.1f} | {motion_text}")

            # Gambar HUD
            out = draw_hud(frame, face_res, virtual_angle, target_angle, pwm_cmd,
                           motion_text, motion_color, fps, arduino.is_connected,
                           arduino.port_name or "N/A", control_mode, stop_pwm, speed_offset, is_inverted,
                           fan_mode, fan_on)
            cv2.imshow(window_name, out)

    except KeyboardInterrupt:
        pass
    finally:
        arduino.send_data(pan=stop_pwm, tilt=90, gesture=0, fan=3)
        time.sleep(0.05)
        cap.release()
        cv2.destroyAllWindows()
        tracker.close()
        arduino.close()
        print("\n[INFO] Selesai. Servo dihentikan, port dan kamera ditutup.")


if __name__ == "__main__":
    main()
