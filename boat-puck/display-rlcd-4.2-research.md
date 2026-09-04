# 4.2" RLCD + ESP32 — suppliers, cost, Boat Puck fit

Research target: *“4.2" RLCD Full Reflective Display Board for ESP32-S3, 300×400 E-ink Like…”*

**Verified prices as of 2026-09-04** (Waveshare store + Alibaba/Toppop listings).

## 1. What that product actually is

| Field | Value |
|-------|--------|
| **Maker / brand** | **Waveshare** (Shenzhen) — this is a branded kit, not a no-name factory white-label |
| **Part** | `ESP32-S3-RLCD-4.2` / `ESP32-S3-RLCD-4.2-EN` |
| **SKU** | **33298** (18650 holder) / **33507** (EN, no battery) |
| **MCU** | ESP32-S3-WROOM-1 **N16R8** (dual-core 240 MHz, 16 MB Flash, 8 MB PSRAM) |
| **Display** | 4.2" **RLCD**, **300×400**, mono B/W, **ST7305**, SPI, **no backlight** |
| **Also on board** | Dual mics + codec, speaker, SHTC3 temp/RH, RTC, TF slot, USB-C, (33298) 18650 holder |
| **Size (board)** | ~**92.5 × 70 × 13.5 mm** (panel AA **63.6 × 84.8 mm**) |
| **Docs** | [waveshare.com](https://www.waveshare.com/esp32-s3-rlcd-4.2.htm), [GitHub](https://github.com/waveshareteam/ESP32-S3-RLCD-4.2) |

Dev kit / AIoT calendar board. **Prototype UI only** — not a marine instrument.

---

## 2. Real prices (retail → factory)

### A. Waveshare complete board (the named product)

| Channel | SKU | Price (USD) | Notes |
|---------|-----|-------------|--------|
| **Waveshare direct** | **33507** EN (no batt) | **$24.99** → $24.39 / $24.09 / **$23.97 @4+** | Best buy-one price |
| **Waveshare direct** | **33298** + 18650 holder | **$26.99** → $26.39 / $26.09 / **$25.97 @4+** | Same electronics + holder |
| OpenELAB | 33298 | **~$35** | Reseller markup |
| Amazon / AliExpress | — | **~$31–$38** | Markup |
| Kamami (EU) | 33507 | ~€27 ex-VAT | Regional |

**Real cost today: $24–27 Waveshare factory store; ~$32–38 street.**

OEM negotiation on this *board* usually only shaves a few dollars — you are still paying for S3 + audio + battery circuitry you may not want.

### B. Bare 4.2" ST7305 RLCD panel (factory — for own PCB)

Same glass tech Waveshare uses. Chinese LCD OEMs sell FOG modules:

| Supplier | Part | Listed price | MOQ / notes |
|----------|------|--------------|-------------|
| **Shenzhen Toppop** | **`TT420FSN21A`** (21-pin SPI) | **$7.80** @2+ → **~$6** at high volume | [toppoplcd.com](https://toppoplcd.com/productdetails_5835009.html); Alibaba listing |
| **Shenzhen Toppop** | **`TT420FSN10A`** (24-pin SPI) | **~$8** sample → **~$6** volume | Same AA 63.6×84.8 mm |
| **Dongguan Shineworld** | 4.2" 300×400 mono reflective | From **~$6.67** | Alternate OEM, higher MOQ often |
| **Good Display** | `GDTL042T71` class | Quote | Industrial / higher MOQ |

**Production panel target: ~$5–$8.** Samples **~$8–$12** incl. shipping uncertainty.

RFQ contacts: Toppop sales via Alibaba / toppoplicd; Shineworld; Good Display for industrial temp range (−20…+70 °C class).

### C. Production Boat Display unit (guess — not a quote)

| Line | Proto (1–10) | 100–500 pcs |
|------|--------------|-------------|
| RLCD panel | $8–12 | $5–8 |
| ESP32-S3 module | $3–5 | $2.50–4 |
| SX1262 LoRa | $2–4 | $1.50–3 |
| GNSS RTK module | $25–80 | $20–60 |
| IMU 9-DOF + temp | $2–6 | $1.5–4 |
| PCB + assy + passives | $15–40 | $8–20 |
| Battery + PMIC | $5–12 | $4–8 |
| Own IP67 housing | $10–40 | $5–15 |
| **Ballpark unit** | **$70–200** | **$50–120** |

GNSS module dominates. Display + S3 is the cheap part.

---

## 3. Better processor options

| Option | Specs vs S3 | Wireless | RLCD kit today? | Cost class | Boat Puck verdict |
|--------|-------------|----------|-----------------|------------|-------------------|
| **ESP32-S3** (current kit) | Dual Xtensa 240 MHz, Wi‑Fi 4 + BLE 5 | On-chip | **Yes** — Waveshare 4.2" | Module ~$3–5 | **v1 default** |
| **ESP32-S31** | Dual RISC-V **320 MHz** + SIMD; Wi‑Fi **6**, BLE **5.4**, Thread/Zigbee path | On-chip | **No** RLCD kit yet | Chip/module ramp 2025–26 | **Best upgrade** when modules are stocked — same single-chip architecture |
| **ESP32-P4** (+ C5/C6) | Dual RISC-V **400 MHz**, strong HMI/MIPI | **No RF on P4** — needs companion | No RLCD; IPS/MIPI kits only | P4-NANO kits ~**$22–36** + radio chip | Overkill for mono digits; dual-chip board |
| **STM32H7 / i.MX RT** + radio | More MCU horsepower | Separate | Custom only | Higher NRE | Skip unless leaving Espressif |

**Recommendation**

1. **Prototype:** buy Waveshare **33507** (~$25) — S3 is enough for LVGL race UI (timer, DTL, SOG, OCS, FIX).
2. **Production PCB:** stay **ESP32-S3 N16R8** (or drop-in **S31** when modules are easy).
3. **Do not** pick P4 for v1 — no Wi‑Fi/BLE on-die, no P4+RLCD kit, colour IPS path fights the sunlight/power story.
4. **Strip** Waveshare mics/speaker/AI voice on custom PCB — Atlas doesn’t talk; saves power and housing depth.

---

## 4. Using this screen for *our* system

| Need | Atlas / Sailmon | 4.2" RLCD |
|------|-----------------|-----------|
| Sunlight readable | Transflective colour | **Yes** — reflective mono |
| Colour | Yes | **No** — B/W |
| Refresh | Fast | Faster than e-ink; fine for digits |
| Power | Higher (backlight) | **Lower** (no backlight) |
| Resolution | ~320×240 colour | 300×400 mono — OK for big digits |

**GoPro H9–13 shell will NOT fit** this panel (~93×70 mm board / 63.6×84.8 AA). **Own housing is mandatory** if RLCD ships on the boat.

Full BOM + housing architecture → [`system-rlcd-housing.md`](system-rlcd-housing.md).

---

## 5. Practical buy / RFQ list

| Priority | What | Where | ~USD |
|----------|------|-------|------|
| 1 | Waveshare **ESP32-S3-RLCD-4.2-EN** (33507) | waveshare.com | **25** |
| 2 | Bare **TT420FSN21A** sample ×2 | Toppop Alibaba | **8–12** ea |
| 3 | Optional Shineworld quote | Accio / Alibaba | **~7** |
| 4 | Later: S31 module samples | Espressif / LCSC when stocked | TBD |

---

## 6. Bottom line

| Question | Answer |
|----------|--------|
| Factory of the named kit? | **Waveshare** (Shenzhen) |
| Real board cost? | **$24–27** direct; **$32–38** reseller |
| Real panel factory cost? | **~$6–8** volume (Toppop / Shineworld); **~$8–12** samples |
| Better CPU? | **ESP32-S31** next; **P4** only if dual-chip + non-RLCD UI |
| For Boat Puck? | **Yes as sunlight UI** — custom PCB + **own IP67 housing** + RTK + LoRa + IMU; don’t ship the voice-AI calendar board as-is |

**Clickable URL / factory / price sheet:** [`atlas/buy-urls.md`](atlas/buy-urls.md).

