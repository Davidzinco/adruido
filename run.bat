@echo off
cd /d "%~dp0"
TITLE Face Tracking & Hand Gesture Arduino Controller
echo =====================================================================
echo  Memulai Arduino Uno Face Tracking & Hand Gesture Identifier
echo =====================================================================

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment .venv belum ditemukan. Membuat .venv...
    python -m venv .venv
    echo [INFO] Menginstall paket dependensi...
    .\.venv\Scripts\pip install -r requirements.txt
)

echo [INFO] Menjalankan aplikasi utama...
.\.venv\Scripts\python.exe python\main.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Terjadi kesalahan saat menjalankan program.
)

pause
