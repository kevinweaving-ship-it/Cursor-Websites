# Universal Puck — product tree

## Design (locked)

```
1. UNIVERSAL PUCK          ← required (GoPro-class housing)
   MCU + battery + RTK + LoRa + IMU
   no screen · mount anywhere (sky-friendly)

2. SCREEN OPTIONS          ← pick any mix (all BLE → Puck)
   a. Screen housing       GoPro case + back LCD + **loud speaker**
   b. Waterproof tablet    companion app
   c. Smartwatch           companion app
```

Phone app still useful for setup/admin; not required for race UI if a/b/c cover it.

North star: [`NORTH_STAR.md`](NORTH_STAR.md).

---

## 1. Universal Puck (required)

| | |
|--|--|
| Shell | Biggest common **action-cam** waterproof case (H9–13 / Ace class) |
| Guts | Small MCU + battery + GNSS/RTK + LoRa + IMU |
| Screen | **None** |
| Mount | Anywhere — prefer clear sky for GNSS |
| Role | Only radio on the boat; boat ID / FIX / OCS live here |

Detail: [`housing/`](housing/), GPS pocket [`housing/gopro-h9-13-lens-gps-pocket.md`](housing/gopro-h9-13-lens-gps-pocket.md).

---

## 2. Screen options (optional, BLE → Puck)

| | Option | Form | Job |
|--|--------|------|-----|
| **a** | **Screen housing** | Second GoPro-class case; SPI LCD on back cover (~2.0–2.8") + **loud speaker** | Digits + **countdown / OCS beep** |
| **b** | **Waterproof tablet** | Rugged/waterproof tablet + app | Bigger-boat helm / nav UI (Atlas-like pages) |
| **c** | **Smartwatch** | Watch + app | Eyes-up speed / start / OCS |

All three are **clients of the Puck**. None carry LoRa/RTK.  
**2a must be loud** — mylar speaker + Class-D amp (not a weak phone beep). See [`bom-puck-screen-cost.md`](bom-puck-screen-cost.md).

Screen housing fit: [`housing/gopro-back-screen-fit.md`](housing/gopro-back-screen-fit.md) — SPI module only (no ESP32 all-in-one).

```
                    Committee RTK + LoRa + Race Control
                                    │
                                    ▼
                    1. UNIVERSAL PUCK (GoPro · no screen)
                                    │ BLE
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
         2a. Screen            2b. Waterproof         2c. Smartwatch
             (GoPro LCD)           tablet
```

---

## Class ladder

| Band | Typical kit |
|------|-------------|
| **Optimist** | Puck + **2a** and/or **2c** |
| **ILCA / 420 / 29er** | Puck + **2a** or **2c** |
| **Bigger boats** | Puck + **2b** and/or **2c** (and optional **2a**) |

---

## Not v0

- One brick with guts + glass together  
- Custom Atlas 4.2" shell (later optional SKU)  
- Phone dive cases / junction boxes as product shell  
- Using Osmo/Action camera as the computer  

---

## Cost snapshot (recommended buy path)

| SKU | R | ($) |
|-----|---|-----|
| **1. Puck** (LC29H RTK, not SparkFun F9P) | **~R1 870** | **~$117** |
| **2a. Screen** (LCD + loud speaker) | **~R870–1 060** | **~$55–66** |
| **Puck + Screen** | **~R2 740–2 930** | **~$171–183** |

Line items + URLs: [`puck-components-buy-list.md`](puck-components-buy-list.md) · [`bom-puck-screen-cost.md`](bom-puck-screen-cost.md).  
(SparkFun ZED-F9P alone is **R4 160 ($260)** — optional premium only.)

## v0 buy

1. One H9–13 (or Ace) **60 m** case → **Puck**  
2. Optional second case clear backdoor → **2a Screen** + Waveshare **2.0" SPI** (58×35 mm) + **speaker+amp**  
3. Pair **2b / 2c** apps to Puck over BLE
