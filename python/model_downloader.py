"""
Modul Pengunduh Model MediaPipe Otomatis
Mengunduh model yang diperlukan secara otomatis jika belum ada di lokal.
"""

import os
import sys
import urllib.request
from pathlib import Path
from config import (
    MODELS_DIR,
    FACE_MODEL_PATH,
    GESTURE_MODEL_PATH,
    FACE_MODEL_URL,
    GESTURE_MODEL_URL
)

def _download_file(url: str, dest_path: str, description: str):
    path = Path(dest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if path.exists() and path.stat().st_size > 1000:
        return

    print(f"[DOWNLOAD] Mengunduh model {description}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    req = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(req) as response:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 64 * 1024
        
        with open(dest_path, "wb") as f:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    sys.stdout.write(f"\r  Progres: {percent:.1f}% ({downloaded // 1024} KB / {total_size // 1024} KB)")
                    sys.stdout.flush()
    print(f"\n[DOWNLOAD] Selesai: {dest_path}")

def ensure_models_exist():
    """Memastikan kedua model (Face & Gesture) siap digunakan."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    _download_file(FACE_MODEL_URL, FACE_MODEL_PATH, "Face Detector (BlazeFace)")
    _download_file(GESTURE_MODEL_URL, GESTURE_MODEL_PATH, "Hand Gesture Recognizer")
    return True

if __name__ == "__main__":
    ensure_models_exist()
