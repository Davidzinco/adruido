# PROMPT GENERATE IMAGE — SKEMA PROYEK FACE TRACKING + KIPAS RELAY

## Alur sistem (ringkas, untuk konteks)

1. **Webcam laptop** menangkap video.
2. **`run_test_servo.bat`** menjalankan **`python/main_servo.py`**.
3. **MediaPipe Face Detection** mencari wajah, menghitung offset wajah dari tengah layar.
4. Python menghitung PWM servo dan mengirim paket serial **`<PAN,TILT,GESTURE,FAN>`**
   (contoh: `<105,90,0,1>`) lewat **USB Serial 115200 bps**.
5. **Arduino Uno** (`servo_tracking.ino`):
   - **D2** → sinyal servo (putar kiri/kanan, maks ±20°).
   - **D3** → IN modul relay (Active-LOW).
   - Relay **ON** saat perintah kipas = 1 (wajah) atau 2 (manual ON).
   - Relay **OFF** saat perintah = 3 (manual OFF), atau otomatis 0,5 detik
     setelah perintah 1 berhenti datang.
   - Tombol **[K]** di Python menggilir mode: AUTO → ON → OFF → AUTO.
6. **Relay COM–NO** memutus/menyambung jalur **adaptor → kipas DC**.
7. Arduino mengirim balik telemetri **`$SERVO,current,target,statusKipas`**.

---

## PROMPT UTAMA (rekomendasi, teks Inggris untuk hasil terbaik)

Tempel **satu blok ini saja** ke ChatGPT / generator gambar — negative prompt sudah digabung di bagian akhir.

```
Create a clean flat-vector technical infographic diagram of a face-tracking fan
system, 16:9 landscape, white background, thin dark outlines, muted palette
(Arduino teal #00979D, relay blue #1565C0, servo orange #F57C00,
fan gray #607D8B, signal arrows amber #FFB300), sans-serif labels.

Layout left to right with clear numbered flow:

LEFT — a laptop with webcam, on its screen a simple HUD window showing a green
face bounding box, text "AUTO: TRACKING WAJAH", "PWM: 105" and "KIPAS: AUTO: ON".
Below the laptop a small file tag: "run_test_servo.bat" and
"main_servo.py + MediaPipe Face Detection". Include a tiny keyboard-key badge
"[K] Kipas" to indicate manual fan override (AUTO / ON / OFF).

CENTER-LEFT — a USB cable arrow from laptop to Arduino, labeled
"USB Serial 115200 bps", with a small packet badge above it reading
"<PAN,TILT,GESTURE,FAN>" and example "<105,90,0,1>".

CENTER — an Arduino Uno board viewed from above, simplified but recognizable,
with only two highlighted pin headers: "D2" (servo signal) and "D3" (relay IN).
A small callout near the board: "servo_tracking.ino".

TOP-RIGHT — an SG90/MG90S servo motor with a horn, mounted on a small fan
bracket, with a curved double arrow showing limited rotation "±20°".
Arrow from Arduino D2 to the servo, labeled "Signal PWM".

BOTTOM-RIGHT — a 1-channel relay module with screw terminals, labeled
"Relay Active-LOW", arrow from Arduino D3 to relay "IN". The relay contact
COM–NO is drawn in series on the positive wire between a small DC power
adapter labelled "Adaptor 5V/12V" and a desk fan labelled "Kipas DC".
Add a small note: "Wajah terdeteksi -> Relay ON | Wajah hilang 0,5 s -> OFF".

POWER — a dedicated 5V and GND rail drawn along the bottom connecting
Arduino 5V and GND, servo VCC/GND, relay VCC/GND, and the adapter GND,
with a clear ground symbol and label "COMMON GROUND (GND disatukan)".
Mark the servo power with a dotted line and note "disarankan adaptor terpisah".

STYLE — engineering block diagram aesthetic, flat icons, no gradients,
no photorealism, generous whitespace, logical wiring routes with rounded
right-angle connectors, small numbered circles 1-6 along the flow.
Keep every text label short and spelled exactly as written in quotes.

AVOID: photorealistic rendering, cluttered breadboard, tangled spaghetti wires,
3D render, glossy reflections, dark background, watermark, logo, extra
components, misspelled or gibberish text, random characters, duplicated
Arduino boards, cropped diagram, gradients, drop shadows.
```

---

## PROMPT ALTERNATIF — TANPA TEKS (untuk dilabeli manual di Canva/Figma/PowerPoint)

Model gambar sering salah menulis teks. Versi ini fokus ke bentuk/wiring,
lalu label ditambahkan sendiri agar 100% akurat.

```
Minimal flat-vector wiring diagram, 16:9, white background, no text at all.
Left: laptop with webcam. Center: Arduino Uno board seen from above.
Top right: servo motor with horn and limited-rotation arrow.
Bottom right: 1-channel relay module connected to a desk fan and a small
power adapter in series through COM-NO contacts.
Bottom: a 5V/GND power rail with a ground symbol joining all modules.
Thin consistent lines, rounded 90-degree wire routes, small connector dots,
muted teal / blue / orange / gray palette, clean engineering aesthetic,
generous whitespace, no realism, no clutter.
```

---

## Saran teknis

- Rasio: **16:9** (1536×864 / 1920×1080) agar muat semua blok.
- Teks kecil (nama pin, nama file) sering rusak → generate versi tanpa teks
  lalu tambahkan label sendiri, atau periksa dan perbaiki hasilnya.
- Jika ingin dua gambar terpisah: (1) **diagram alur data** Python ↔ Arduino,
  (2) **diagram wiring** Arduino ↔ servo/relay/kipas. Hasilnya biasanya lebih rapi
  daripada satu gambar padat.
