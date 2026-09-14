# Robby — complete system rundown

**What this is:** one puck design for **boat / start pin / mark / finish**, plus **one committee** brick.  
**Race radio:** LoRa. **Training / long-range:** SoftSIM LTE. **Sailor UI:** BLE to phone/watch; optional RLCD on puck.

**Cavity (pucks):** GoPro H9–13 · **71.8 × 50.8 × 33.6 mm**  
**Ship China parts to:** Eric Shenzhen — `ERIC_SHENZHEN_SHIP_TO.md`

---

## 1. Who gets what (first water kit)

| Role | Unit | Main GNSS/radio brick |
|------|------|------------------------|
| Start pin | **Puck 1** | WT-43-**RK**-LORA |
| Racing boat | **Puck 2** | WT-43-**RK**-LORA |
| Mark / finish | **Puck 3** | WT-43-**RK**-LORA |
| Committee / Race Control | **Committee box** | WT-43-**BK**-LORA + tablet/laptop UI |

Same puck electronics on pin / boat / mark. SoftSIM lets a puck work **alone** (training) or when LoRa can’t reach (boat traffic **and** mark position).

---

## 2. Every component — what it does / can do

### A. Inside each puck (×3)

| # | Component | What it does | Also can do |
|---|-----------|--------------|-------------|
| 1 | **H9–13 waterproof housing** | Sealed shell; lens port = GNSS sky window; stock buttons on case | Mount with GoPro-style arms |
| 2 | **WT-43-RK-LORA** | Dual-freq RTK GNSS + **LoRa** radio; position math on-module; streams NMEA/RTK to MCU | Rover on pin/boat/mark; receive RTCM over LoRa from committee |
| 3 | **ME54BS62 (nRF54)** | **Race brain** — start/OCS logic, BLE to phone/watch, UART hub to WT-43 + SoftSIM + optional screen | Buttons, LEDs, beeps; future Channel Sounding experiments |
| 4 | **Flat LiPo ~1000 mAh** | Power for whole puck | — |
| 5 | **TP4056** | Charge LiPo from Qi (or USB if wired) | Protect charge path |
| 6 | **Qi RX coil** | Wireless charge through shell | No open charge port on water |
| 7 | **SoftSIM LTE (A7672-class)** | Cellular backhaul **without SIM tray** | Solo training; LoRa-out-of-range uplink for boat **and** mark/pin |
| 8 | **FPC cell antenna** | LTE RF on inner wall | — |

### B. Optional puck UI (later — only if RLCD gate passes)

| # | Component | What it does | Also can do |
|---|-----------|--------------|-------------|
| 9 | **RLCD back-lid screen** (reflective) | Sunlight timer / OCS / status on rear door | Better contrast in bright sun (no fat backlight) |
| 10 | **Speaker + amp** | Race timer beeps (gun, countdown, OCS) | Alerts without looking |
| 11 | **Buttons ×2 (internal)** | Under **stock housing** shutter + mode plungers | Connect / confirm / mute / ack — **no new holes** |
| 12 | **LEDs ×3–4** | FIX / LoRa / SoftSIM / batt (or race state) | Night cue when RLCD has no backlight |

### C. Committee (×1)

| # | Component | What it does | Also can do |
|---|-----------|--------------|-------------|
| 13 | **WT-43-BK-LORA** | RTK **base** + LoRa broadcast of corrections / race messages | Not a puck; stays in dry box |
| 14 | **IP67 dry box** | Holds BK + LiPo + charge | Cable gland later for survey ant |
| 15 | **LiPo + TP4056** | Committee power / USB charge | No Qi required on V1 |
| 16 | **Tablet / laptop** | Race Control UI (set gun, line, scores) | **Not** the RTK base |
| 17 | **Survey GNSS antenna + pole** (later) | Better base sky view | Optional after first test |

### D. Sailor / shore clients (not inside puck)

| Component | What it does |
|-----------|--------------|
| **Phone / Wear OS watch** | BLE client — countdown, OCS, track | 
| **Onomondo / Monogoto SoftSIM profile** | Software SIM for A7672 |
| **Qi charge pad (bench)** | Charge sealed pucks |

---

## 3. How it connects (system)

```
                    ┌─────────────────────────────┐
                    │  COMMITTEE                  │
                    │  Tablet/laptop = Race UI    │
                    │       │ USB/BLE/Wi‑Fi       │
                    │  WT-43-BK ──LoRa──► fleet   │
                    │  (RTK base + race msgs)     │
                    │  SoftSIM optional later     │
                    └──────────────┬──────────────┘
                                   │ LoRa 868
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
   ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
   │ PUCK pin    │          │ PUCK boat   │          │ PUCK mark   │
   │             │          │             │          │             │
   │ WT-43-RK ◄──LoRa──►    │ WT-43-RK    │          │ WT-43-RK    │
   │    │ UART              │    │ UART   │          │    │ UART   │
   │ nRF54 ◄─────────────── │ nRF54       │          │ nRF54       │
   │  │    │                │  │    │     │          │  │    │     │
   │  │    └─ SoftSIM LTE ──┼──┴────┴─────┼──────────┼──┴────┴─────┼──► cloud / phone
   │  │       (training /   │             │          │  when LoRa  │     NTRIP / telem
   │  │        long range)  │             │          │  too weak   │
   │  ├─ BLE ──► watch/phone│             │          │             │
   │  ├─ SPI ──► RLCD (opt) │             │          │             │
   │  ├─ GPIO ► buttons×2   │             │          │             │
   │  ├─ GPIO ► LEDs×3–4    │             │          │             │
   │  └─ PWM ─► speaker     │             │          │             │
   │ LiPo ← TP4056 ← Qi RX  │  (same)     │          │  (same)     │
   └─────────────┘          └─────────────┘          └─────────────┘
```

### Buttons (detail)

```
Outside H9–13 casing button (shutter / mode)
        ↓ mechanical plunger
Inside tactile switch on insert
        ↓
nRF54 GPIO  →  Connect / Confirm / Mute / Start-ack (firmware)
```

No drilled holes; factory waterproof boots stay.

### Power (puck)

```
Qi pad (outside) → Qi RX (inner wall) → TP4056 → LiPo 3.7 V
                         → WT-43 · nRF54 · SoftSIM · UI
```

### Data roles

| Path | Carries |
|------|---------|
| **LoRa** | RTCM corrections, race start/gun/line, puck positions (race-critical when in range) |
| **SoftSIM LTE** | Same kinds of traffic when training alone or LoRa too far; NTRIP/shore |
| **BLE** | Sailor display (phone/watch) |
| **UART** | WT-43 ↔ nRF54 · SoftSIM ↔ nRF54 |
| **SPI** | Optional RLCD ↔ nRF54 |

---

## 4. URLs (factories / buy)

### Ordered / enquired now

| Part | URL |
|------|-----|
| WT-43-RK-LORA | https://www.ontheway-tech.com/product/wt-43-rk-lora/ |
| WT-43-BK-LORA | https://www.ontheway-tech.com/product/wt-43-bk-lora-module/ |
| OTW home | https://www.ontheway-tech.com/ |
| ME54BS62 nRF54 | https://store.minewsemi.com/product/bluetooth-modules-nrf54l15-me54bs62/ |
| MinewSemi | https://en.minewsemi.com/ |
| Committee dry box G3109 | https://www.robotics.org.za/G3109 |
| H9–13 housing (Temu class) | search Temu/Ali “Hero 9-13 waterproof housing” |

### SoftSIM (tomorrow contact — fit locked)

| Part | URL |
|------|-----|
| SIMCom A7672 | https://www.simcom.com/product/A7672X.html |
| Misuxin A7672E-LASE (~$17) | https://misuxinelectronics.com/showpro_2816381_569.html |
| SoftSIM for SIMCom | https://onomondo.com/product/softsim-for-simcom/ |
| Alt Quectel EG915U | https://www.quectel.com/product/lte-cat-1-bis-eg915u-series/ |

### Optional RLCD screen (gate: reflective + thin + lid size)

| Part | URL |
|------|-----|
| Deep-dive + prices | `DEEP_DIVE_RLCD_BACK_LID.md` |
| Toppop (ST7305 family / Atlas 4.2) | https://toppoplcd.com/ · https://toppoplcd.com/productdetails_5835009.html |
| Ask Toppop/OSPTEK **2.13" ST7305 reflective** | https://www.alibaba.com/product-detail/Factory-price-2-13-inch-122x250_1601215517333.html |
| Midas 2.13 MDTR0213A-SPI | search DigiKey / https://www.unikeyic.com/products/lcd-display/mdtr0213a-spi/871293466.html |
| Sharp LS027 2.7" Memory LCD | DigiKey / LCSC search `LS027B7DH01A` |
| Atlas 4.2 kit (proto UI only — **not** in puck) | https://www.waveshare.com/esp32-s3-rlcd-4.2.htm?sku=33507 |

### Charge (local)

| Part | URL |
|------|-----|
| Micro Robotics (Qi / TP4056 class) | https://www.robotics.org.za/ |
| Qi RX ≤48×32 (AF1901-class) | Micro Robotics / Adafruit 1901-class |
| Flat LiPo ~1000 mAh ≤5–6 mm | local / Ali “503450 1000mAh” |

---

## 5. Pack reminder (puck)

```
H9–13
 Front lens → WT-43 GNSS
 Beside WT-43 (~29 mm strip) → SoftSIM
 Under → LiPo + nRF54 + TP4056
 Walls → Qi RX + cell FPC
 Rear lid → optional RLCD
 Case buttons → internal switches ×2
```

Fit proof: **`HOUSING_FIT_ALL.md`**

---

## 6. Status snapshot

| Item | Status |
|------|--------|
| Housing ×3 | ORDERED |
| WT-43 RK×3 + BK×1 | ORDER SENT → Eric |
| nRF54 ×3 modules + **ME54BE62 kit ×1** | ENQUIRY — **must add kit** to Minew PO |
| LiPo / Qi / TP4056 | BUY LOCAL |
| SoftSIM | FIT LOCKED — factory tomorrow |
| RLCD UI | OPTIONAL — after water test + lid caliper |
| Dry box | CURRENT buy step (committee) |

---

## 7. One-line for Robby

**Puck = waterproof GoPro shell + WT-43 (GPS/LoRa) + nRF54 (race brain/BLE) + battery/Qi + SoftSIM for training/long-range; optional sunlight RLCD + beeps; two case buttons drive internal switches; committee = BK base in dry box + tablet Race Control.**
