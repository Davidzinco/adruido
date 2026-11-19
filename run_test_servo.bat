@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
TITLE Test Face Tracking Servo

echo =====================================================================
echo  Memulai Pengujian Face Tracking Servo (Arduino Uno + Kamera)
echo =====================================================================

set "VENV_PY=.venv\Scripts\python.exe"

REM --- 1. Cek keberadaan virtual environment ---
if not exist "%VENV_PY%" goto :create_venv

REM --- 2. Cek apakah venv benar-benar bisa dipakai (bukan sisa komputer lain) ---
"%VENV_PY%" -c "import sys" >nul 2>&1
if errorlevel 1 goto :recreate_venv

REM --- 3. Cek apakah dependensi sudah terinstall ---
"%VENV_PY%" -c "import cv2, mediapipe, serial, numpy" >nul 2>&1
if errorlevel 1 goto :install_deps

goto :run


:recreate_venv
echo [INFO] Virtual environment .venv rusak / tidak valid. Membuat ulang...
rmdir /s /q ".venv" >nul 2>&1

:create_venv
if not exist ".venv" echo [INFO] Virtual environment .venv belum ditemukan. Membuat .venv...

set "BASE_PY="
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "BASE_PY=py -3"
)
if not defined BASE_PY (
    where python >nul 2>&1
    if not errorlevel 1 (
        python -c "import sys" >nul 2>&1
        if not errorlevel 1 set "BASE_PY=python"
    )
)

if not defined BASE_PY (
    echo.
    echo [ERROR] Python tidak ditemukan di komputer ini.
    echo         Install Python 3.x dari https://www.python.org/downloads/
    echo         dan centang "Add python.exe to PATH", lalu jalankan ulang file ini.
    goto :end
)

echo [INFO] Membuat .venv menggunakan: !BASE_PY!
!BASE_PY! -m venv .venv
if not exist "%VENV_PY%" (
    echo [ERROR] Gagal membuat virtual environment .venv
    goto :end
)

:install_deps
echo [INFO] Menginstall paket dependensi...
"%VENV_PY%" -m pip install --upgrade pip
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Gagal menginstall dependensi. Periksa koneksi internet lalu coba lagi.
    goto :end
)


:run
echo [INFO] Menjalankan program pelacak wajah servo...
"%VENV_PY%" python\main_servo.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Terjadi kesalahan saat menjalankan program.
)

:end
pause
