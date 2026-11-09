"""
Modul Komunikasi Serial Arduino Uno
Menghubungkan Python ke Arduino Uno melalui USB Serial.
Mendukung Auto-Detection COM port dan Mode Simulasi jika board belum terpasang.
"""

import time
import serial
import serial.tools.list_ports
from typing import Optional, Tuple
import config

class ArduinoSerial:
    def __init__(self, port: Optional[str] = None, baud_rate: int = config.BAUD_RATE, enabled: bool = True):
        self.port_name = port
        self.baud_rate = baud_rate
        self.enabled = enabled
        self.serial_conn: Optional[serial.Serial] = None
        self.is_connected = False
        self.last_send_time = 0.0
        self.last_sent_packet = ""

        if self.enabled:
            self.connect()

    def find_arduino_port(self) -> Optional[str]:
        """Mencari COM port Arduino secara otomatis."""
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            return None

        # Kata kunci umum untuk mikrokontroler Arduino Uno / Clone
        arduino_keywords = ["arduino", "ch340", "ch341", "ftdi", "usb serial", "cp210", "prolific"]

        # Prioritas 1: Pencarian berdasarkan deskripsi / HWID
        for p in ports:
            desc = (p.description or "").lower()
            mfg = (p.manufacturer or "").lower()
            hwid = (p.hwid or "").lower()
            
            for kw in arduino_keywords:
                if kw in desc or kw in mfg or kw in hwid:
                    print(f"[SERIAL] Ditemukan perangkat cocok: {p.device} ({p.description})")
                    return p.device

        # Prioritas 2: Jika hanya ada 1 COM port selain COM1
        valid_ports = [p.device for p in ports if p.device != "COM1"]
        if len(valid_ports) == 1:
            print(f"[SERIAL] Menggunakan port aktif tunggal: {valid_ports[0]}")
            return valid_ports[0]

        return None

    def connect(self) -> bool:
        """Membuka koneksi serial ke Arduino Uno."""
        if not self.enabled:
            print("[SERIAL] Mode Serial Dinonaktifkan (Simulasi).")
            self.is_connected = False
            return False

        target_port = self.port_name or self.find_arduino_port()
        
        if not target_port:
            print("[SERIAL] PERINGATAN: Arduino Uno tidak terdeteksi di port COM!")
            print("[SERIAL] Menjalankan dalam MODE SIMULASI (Kamera & UI tetap berjalan).")
            self.is_connected = False
            return False

        try:
            print(f"[SERIAL] Menghubungkan ke {target_port} pada {self.baud_rate} baud...")
            self.serial_conn = serial.Serial(
                port=target_port,
                baudrate=self.baud_rate,
                timeout=0.1,
                write_timeout=0.1
            )
            # Berikan waktu 2 detik bagi Arduino Uno untuk auto-reset setelah DTR dibuka
            time.sleep(2.0)
            self.port_name = target_port
            self.is_connected = True
            print(f"[SERIAL] BERHASIL terhubung ke Arduino Uno ({target_port})!")
            
            # Bersihkan buffer
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()
            return True

        except (serial.SerialException, OSError) as e:
            print(f"[SERIAL] Gagal membuka port {target_port}: {e}")
            print("[SERIAL] Beralih ke MODE SIMULASI.")
            self.serial_conn = None
            self.is_connected = False
            return False

    def send_data(self, pan: int, tilt: int, gesture: int = 0) -> bool:
        """
        Mengirimkan paket koordinat dan kode gesture ke Arduino.
        Format Paket: <PAN,TILT,GESTURE>\n
        """
        now = time.time()
        # Batasi frekuensi kirim untuk mencegah buffer overflow
        if now - self.last_send_time < config.SEND_INTERVAL_SEC:
            return False

        # Pastikan nilai integer dalam batas 0-180 (jangan clamp ke PAN_MIN/MAX
        # karena untuk servo 360, kita perlu mengirim nilai PWM mentah seperti 85/90/95)
        pan = max(0, min(180, int(pan)))
        tilt = max(0, min(180, int(tilt)))
        gesture = int(gesture)

        packet = f"<{pan},{tilt},{gesture}>\n"
        self.last_sent_packet = packet.strip()
        self.last_send_time = now

        if self.is_connected and self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(packet.encode('ascii'))
                return True
            except (serial.SerialTimeoutException, serial.SerialException) as e:
                print(f"[SERIAL] Error pengiriman data: {e}")
                self.is_connected = False
                return False
        return False

    def read_incoming(self) -> Optional[str]:
        """Membaca pesan respon dari Arduino jika ada."""
        if self.is_connected and self.serial_conn and self.serial_conn.is_open:
            try:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        return line
            except Exception:
                pass
        return None

    def close(self):
        """Menutup port serial dengan aman."""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
                print("[SERIAL] Koneksi serial ditutup.")
            except Exception:
                pass
        self.is_connected = False
