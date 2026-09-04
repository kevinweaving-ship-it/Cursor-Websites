# Puck — corrected component buy list

FX: **R16 / $1**. Checked **2026-09-04**.

### Corrections (you were right)

| Was wrong | Fix |
|-----------|-----|
| ESP32 / ESP32-C3 DevKit / big modules | **Won’t fit.** Use **nRF52840 SMD module 13×18 mm** |
| Housing ~R400 ($25) | **AliExpress H9–13 case ~R80–96 ($5–6)** — under **R100** |
| Waveshare **LC29H Pi HAT** (65×30 mm board) | **Proto only / won’t pack.** Prefer **bare LC29H module** on custom PCB |

Cavity budget: **71.8 × 50.8 × 33.6 mm**.

---

## Puck parts (fit + price + URL)

| # | Part | Size | URL | R | ($) |
|---|------|------|-----|---|-----|
| 1 | **MCU+BLE** Ebyte **E73-2G4M08S1C** (nRF52840) | **13 × 18 mm** | https://www.lcsc.com/product-detail/Bluetooth-Modules_Chengdu-Ebyte-Elec-Tech-E73-2G4M08S1C_C356849.html | **R121** | **$7.59** |
| 2 | **LoRa** Ebyte **E22-900M22S** (SX1262) | **14 × 20 mm** | https://www.lcsc.com/product-detail/Wireless-Modules_Chengdu-Ebyte-Elec-Tech-E22-900M22S_C411293.html | **R106** | **$6.60** |
| 3 | **GNSS RTK** Quectel **LC29H(DA)** bare module | ~**12 × 16 mm** class | Alibaba / Quectel disti — search “LC29H DA module” (not Pi HAT) | **~R400–640** | **~$25–40** |
| 4 | **GNSS antenna** dual-band patch / active (lens pocket) | ≤ **Ø30 × 5** | kit with module or Taoglas/Ali patch | **~R80–160** | **~$5–10** |
| 5 | **IMU** BMI270 (chip) or tiny breakout | chip **3×2.5** / breakout trim | https://www.lcsc.com/search?q=BMI270 (chip) · Adafruit breakout only if cut down | **~R30–120** | **~$2–7.50** |
| 6 | **LiPo** flat 3.7 V ~1500–2000 mAh | ≈ **50×34×8** | AliExpress “503450 lipo” / “602040 lipo” | **~R50–100** | **~$3–6** |
| 7 | **Charge / protect** TP4056 + DW01 class (bare boards tiny) | ~**25×17** max | AliExpress TP4056 Type-C mini | **~R10–25** | **~$0.60–1.50** |
| 8 | **Housing** H9–13 60 m waterproof | outer ~80×80×50 | AliExpress “Hero 9 10 11 12 13 waterproof housing 60m” | **~R80–96** | **~$5–6** |
| 9 | **PCB + passives + LED** | custom sled | JLCPCB | **~R50–120** | **~$3–7.50** |

### Puck total (realistic proto)

| | R | ($) |
|--|---|-----|
| **Sum mid** | **~R950–1 300** | **~$59–81** |
| **Housing alone** | **&lt; R100** | **~$5–6** |

---

## Explicitly do **not** buy for the Puck insert

| Part | Why |
|------|-----|
| Any **ESP32 DevKit** / WROOM stick | Too long / thick for cavity |
| Waveshare **LC29H GPS HAT** | Pi HAT outline — won’t pack as final |
| SparkFun **ZED-F9P** breakout | Huge board + **R4 160 ($260)** |
| Official GoPro ADDIV housing | Overkill price vs Ali **&lt;R100** |

---

## Size stack (why this fits)

```
Front (−Z): antenna in lens pocket Ø25–30 × ≤5 mm
Mid:        LC29H + E22 + E73 on one PCB (all ≤20 mm edge)
Rear (+Z):  flat LiPo ~8 mm
Shell:      Ali H9–13 case < R100
```

No ESP32. No Pi HAT.

---

## One-line shopping (corrected)

1. MCU: https://www.lcsc.com/product-detail/Bluetooth-Modules_Chengdu-Ebyte-Elec-Tech-E73-2G4M08S1C_C356849.html — **R121 ($7.59)** · 13×18  
2. LoRa: https://www.lcsc.com/product-detail/Wireless-Modules_Chengdu-Ebyte-Elec-Tech-E22-900M22S_C411293.html — **R106 ($6.60)** · 14×20  
3. GNSS: bare **LC29H(DA)** module (Alibaba) — **~$25–40** · not the HAT  
4. Housing: AliExpress H9–13 60 m — **&lt; R100 ($5–6)**  
5. LiPo + TP4056: AliExpress — **~R60–120 total**

Full cost rollup: [`bom-puck-screen-cost.md`](bom-puck-screen-cost.md).
