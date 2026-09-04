# Boat Atlas — our Atlas 2

Working name: **Boat Atlas**  
Role: keelboat / cockpit **sailor instrument** in the Boat Puck stack (Vakaros **Atlas 2** job).

**Display (locked):** **4.2" reflective LCD (RLCD)** — 300×400 mono ST7305 — see [`display-4.2-rlcd.md`](display-4.2-rlcd.md).

North star: [`../NORTH_STAR.md`](../NORTH_STAR.md)  
Markets: keelboat SKU in [`../markets-dinghy-keelboat.md`](../markets-dinghy-keelboat.md)  
Glass research: [`../display-rlcd-4.2-research.md`](../display-rlcd-4.2-research.md)  
Housing/BOM: [`../system-rlcd-housing.md`](../system-rlcd-housing.md)

**Not this product:** dinghy GoPro puck (HALO-like sensor-only). Same LoRa/RTK network; different shell + UI.

---

## 1. What Atlas 2 is (what we must match)

From Vakaros public specs ([atlas2](https://www.vakaros.com/products/atlas2)):

| Area | Atlas 2 | Boat Atlas (target) |
|------|---------|---------------------|
| Display | 4.4" transflective colour LCD 320×240, backlight, Gorilla Glass | **LOCKED: 4.2" mono reflective LCD** 300×400 ST7305 — no backlight |
| GNSS | 25 Hz L1+L5; ~25 cm with RaceSense DGNSS | **L1+L5 RTK/DGNSS** via our LoRa; target **≥25 Hz**, stretch **50 Hz** |
| Motion | Mag + gyro + accel; 50 Hz fusion; 0.1° heading claim | **9-DOF ≥100 Hz** fusion |
| Race UI | DTL, TTL, burn, countdown, shift, stripchart, VMG | **Same race pages** (mono, big digits) |
| RaceSense | Mesh OCS / sync / line | **LoRa** fleet: FIX quality, OCS flag, gun sync, line ends |
| LED | RGB LED array (timer/DTL/heel/…) | **RGB LED** strip or ring lite |
| Battery | 4600 mAh, 100+ h, Qi | **Race-day+** first; Qi later |
| Size / weight | ~3.5×4.5", ~175 g | Own IP67; target **&lt;250 g** without mount |
| Night | Red backlight | RLCD weak at night → **LED + optional dim front-light later**; v1 = day race primary |
| Extras | Ambient light, temp; wireless wind/depth later | **Temp yes**; light skip v1; NMEA/wireless sensors **later** |

**Where we are better on paper:** cm-class when RTK is up (HALO job on the same box), higher IMU rate, open LoRa, far lower BOM, dinghy fleet can use the same network without buying this glass.

**Where Atlas stays ahead until we catch up:** colour UI polish, night backlight, optical coatings, Qi, class-legal locked modes, wireless wind/depth ecosystem.

---

## 2. Hardware block (v1)

```
┌──────────────────────── Boat Atlas ────────────────────────┐
│  Window + gasket                                           │
│  4.2" ST7305 RLCD ──── SPI ──── ESP32-S3 (N16R8)           │
│  Soft keys (3–4) ──── GPIO ────│         │                 │
│  RGB LED ─────────── GPIO/PWM ─┤         ├─ BLE (app/cfg)  │
│  Temp ─────────────── I²C ─────┤         ├─ SX1262 LoRa    │
│  9-DOF IMU ────────── I²C/SPI ─┤         │                 │
│  RTK GNSS module ──── UART ────┘         │                 │
│  GNSS patch ant (sky face)               LoRa ant (edge)   │
│  Li-ion + PMIC + USB-C charge                              │
└────────────────────────────────────────────────────────────┘
         ▲ RTCM / gun / line          ▼ pos / OCS / track
         └────────── Committee LoRa hub / Race Control ──────┘
```

Strip from Waveshare kit: mics, speaker, AI voice, TF “calendar” fluff.

Detail BOM: [`../system-rlcd-housing.md`](../system-rlcd-housing.md).

---

## 3. Soft keys (v1)

| Key | Primary | Long-press |
|-----|---------|------------|
| **A** | Next page | Page list |
| **B** | Start / sync timer | Reset timer |
| **C** | Mark / ping line end (RC mode) | Brightness/LED mode |
| **D** (optional) | Back / lock | Power |

Exact map can move; keep **one-handed** with gloves in mind (44 mm targets on housing, not tiny bezel dots).

---

## 4. Build order (this product only)

| Step | Deliverable | Status |
|------|-------------|--------|
| **1** | Spec + parity + UI page list (this folder) | **Now** |
| 2 | Housing outer envelope CAD from panel AA | Next |
| 3 | Buy Waveshare **33507** — LVGL race pages on 4.2" RLCD | Next |
| 4 | Schematic: S3 + RLCD + SX1262 + GNSS + IMU | After UI feels right |
| 5 | Custom PCB + soft-tool housing | After schematic |

Dinghy puck and committee hub stay parallel tracks — do not block Atlas glass on GoPro keepouts.

---

## 5. Docs in this folder

| File | Content |
|------|---------|
| `README.md` | This product brief |
| `display-4.2-rlcd.md` | **Locked** 4.2" RLCD decision + mechanical envelope |
| `buy-urls.md` | **Factory / store URLs, specs, prices** |
| `ui-pages.md` | Screen list / layout rules for 300×400 mono |
| `parity-checklist.md` | Atlas 2 feature → must / later / skip |
