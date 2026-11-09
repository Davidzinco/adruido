@echo off
cd /d "%~dp0"
TITLE Sistem Kipas Otomatis & Face Tracking
echo =====================================================================
echo  Memulai Sistem Kipas Otomatis ^& Face Tracking (Arduino Uno + PC)
echo =====================================================================

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment .venv belum ditemukan. Membuat .venv...
    python -m venv .venv
    echo [INFO] Menginstall paket dependensi...
    .\.venv\Scripts\pip install -r requirements.txt
)

echo [INFO] Menjalankan aplikasi pengarah kipas otomatis...
.\.venv\Scripts\python.exe python\main_kipas.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Terjadi kesalahan saat menjalankan program.
)

pause
