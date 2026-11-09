@echo off
cd /d "%~dp0"
TITLE Test Face Tracking Servo
echo =====================================================================
echo  Memulai Pengujian Face Tracking Servo (Arduino Uno + Kamera)
echo =====================================================================

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment .venv belum ditemukan. Membuat .venv...
    python -m venv .venv
    echo [INFO] Menginstall paket dependensi...
    .\.venv\Scripts\pip install -r requirements.txt
)

echo [INFO] Menjalankan program pelacak wajah servo...
.\.venv\Scripts\python.exe python\main_servo.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Terjadi kesalahan saat menjalankan program.
)

pause
