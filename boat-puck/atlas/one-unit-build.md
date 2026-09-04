# Boat Atlas — kit vs bare glass, and one-unit build

## Short formula

```
Boat Puck (dinghy)     =  RTK + IMU + LoRa + battery + LED   (+ BLE phone/watch)
Boat Atlas (keelboat)  =  Boat Puck guts  +  4.2" RLCD  +  soft keys  +  own IP67 shell
```

Same race brain. Atlas is **not** a different system — it is the puck with a sunlight screen and a bigger housing (GoPro is too small for 4.2").

Vakaros naming map: puck ≈ **HALO** · Atlas unit ≈ **Atlas 2** · committee ≈ **RaceSense**.

---

## 1. Kit with ESP32 vs bare 4.2" panel

| | **Waveshare kit** (ESP32 already on board) | **Bare RLCD only** (Toppop glass) |
|--|--------------------------------------------|-----------------------------------|
| What you get | S3 + 4.2" RLCD + USB + battery path + extras | Glass + FPC only (~ST7305 SPI) |
| Buy | [SKU 33507](https://www.waveshare.com/esp32-s3-rlcd-4.2.htm?sku=33507) **R400 ($24.99)** | [`TT420FSN21A`](https://toppoplcd.com/productdetails_5835009.html) **~R125 ($7.80)** |
| Add LoRa / GNSS / IMU | **Hard** — cramped board, wrong form factor, audio junk in the way | **Normal** — you design the PCB around those parts |
| Learn UI / LVGL | **Easy** — plug USB, run samples | Harder — need your own MCU breakout first |
| Ship as product | **No** — calendar/AI board, not marine | **Yes** — after custom PCB + IP67 housing |
| NRE | Low for software | Higher (schematic, PCB, FPC, EMC) |

### How easy is “screen only + our extras”?

**Bare glass:** medium difficulty, **right long-term path**.

- Panel is SPI ST7305 — same driver Waveshare uses.  
- You add: ESP32-S3 module, SX1262, RTK GNSS UART, IMU I²C, PMIC, keys, LED.  
- Hard parts are **not** the LCD — they are **antenna layout**, IP67 window, and GNSS sky view.  
- Expect: 1 custom PCB revision cycle after a breadboard/Waveshare UI proto.

**Waveshare kit + solder extras on:** poor fit.

- Almost no room for RTK module + LoRa + proper antennas.  
- Mics/speaker/RTC calendar circuitry waste space and power.  
- Housing would still be custom; you fight their board outline (~92.5×70 mm) instead of designing for race.

### Recommendation

| Phase | Use |
|-------|-----|
| **Now (UI)** | Waveshare kit **with ESP32** — fastest path to race pages on real glass |
| **Product (Boat Atlas)** | **Bare panel + our PCB** — S3 + LoRa + GNSS + IMU in one layout |
| Do **not** | Try to frankenstein LoRa/GNSS onto the Waveshare calendar board as the final product |

**Short answer:** kit-with-ESP32 is **better to start**; bare screen + own PCB is **better to ship**. Adding extras to screen-only is **straightforward electrically**, hard **mechanically/RF**.

---

## 2. One unit = full Boat Atlas (everything in one box)

This is Architecture **A** — our Atlas 2 as a single instrument (no separate GoPro puck).

```
┌──────────────────── ONE UNIT — Boat Atlas ────────────────────┐
│  IP67 housing + optical window                                │
│                                                               │
│  4.2" ST7305 RLCD (bare glass, SPI)                           │
│  ESP32-S3 N16R8     UI · BLE · hosts LoRa/GNSS/IMU            │
│  SX1262 LoRa + edge antenna                                   │
│  Dual-band RTK GNSS + sky-face patch                          │
│  9-DOF IMU ≥100 Hz + temperature                              │
│  Soft keys (3–4) + RGB status LED                             │
│  Li-ion + PMIC + USB-C charge                                 │
│  Config / log flash                                           │
└───────────────────────────────────────────────────────────────┘
         ▲ RTCM / gun / line              ▼ pos / OCS / track
         └──────── Committee LoRa hub / Race Control ───────────┘
```

### What is *in* the unit (must-have)

| # | Block | Role | Cost class |
|---|-------|------|------------|
| 1 | **4.2" RLCD** FOG | Sailor display | **~R96–128 ($6–8)** vol |
| 2 | **ESP32-S3** (or S31 later) | UI + BLE + glue | **~R48–80 ($3–5)** |
| 3 | **SX1262** + LoRa ant | Fleet radio (RaceSense job) | **~R24–64 ($1.50–4)** |
| 4 | **RTK GNSS** L1+L5 + patch | cm/dm position | **~R320–1280 ($20–80)** ← dominates |
| 5 | **9-DOF IMU** + temp | Heel, heading, fusion | **~R24–96 ($1.50–6)** |
| 6 | Soft keys + RGB LED | Timer / OCS cues | cheap |
| 7 | Battery + PMIC + USB-C | Race-day+ | **~R64–192 ($4–12)** |
| 8 | Custom PCB + assy | Tie it together | **~R128–640 ($8–40)** |
| 9 | **Own IP67 housing** + mount | Not GoPro | **~R80–640 ($5–40)** |

**Ballpark one-unit:** **~R1200–3200 ($75–200)** proto · **~R880–2080 ($55–130)** @100–500.

### What is *not* in the unit (v1)

| Skip | Why |
|------|-----|
| Waveshare mics / speaker / AI | Atlas doesn’t talk; power/space waste |
| Colour IPS / backlight | Fights sun + power story |
| Qi / ambient light / baro | Later / not race-critical |
| NMEA wind/depth hub | Sailmon extras — after race net works |
| Separate dinghy GoPro shell | That’s the other SKU |

### Committee still separate (not inside Boat Atlas)

RTK base · LoRa hub · Race Control tablet/PC · line-end references · shore/RC power.

One boat unit ≠ whole Vakaros system. Atlas-on-boat is this box; RaceSense-on-shore is committee gear.

---

## 3. One unit vs split (quick)

| | **One unit (this doc)** | **Split puck + display** |
|--|-------------------------|---------------------------|
| Sailor experience | Like Atlas — one instrument | Display in cockpit, sensors on rail |
| RF / GNSS | Harder (all antennas in one plastic) | Cleaner sky / LoRa |
| Cost / tooling | One housing | Two housings |
| Dinghy story | Too big / dear for many dinghies | Puck SKU stays cheap |

**For “our Atlas 2” keelboat product: design as one unit.**  
Keep dinghy as sensor puck + phone/watch on the same LoRa network.

---

## 4. Practical next steps

1. Buy Waveshare **33507** — prove Start / DTL / OCS pages on glass.  
2. Sample Toppop **TT420FSN21A** — confirm FPC for custom PCB.  
3. Block diagram → schematic: S3 + ST7305 + SX1262 + GNSS + IMU.  
4. CAD housing from **63.6 × 84.8 mm** AA (glass masters).  
5. First PCB spin; ignore Waveshare outline for production.
