# Puck parts — factory / maker URLs only (no LCSC)

Do **not** use lcsc.com. Buy from **Ebyte factory** / Alibaba / Waveshare / GNSS specialists.

FX: **R16 / $1**.

**Hard lock:** GNSS must do **≥50 Hz**. See [`gnss-50hz-lock.md`](gnss-50hz-lock.md).

---

## MCU + BLE — E73-2G4M08S1C (nRF52840 · 13×18 mm)

| | URL |
|--|-----|
| **Ebyte shop (buy)** | https://ebyteiot.com/products/2-4ghz-ble-mesh-small-smd-e73-2g4m08s1c-nordic-nrf52840-module-small-size-ble-5-0 |
| **Factory product page** | https://www.cdebyte.com/products/E73-2G4M08S1C |
| **Price** | **~$5–7.60** → **R80–122** |
| **Note** | Out of stock → **E73-2G4M08S1CX** on same page |

---

## LoRa — E22-900M22S (SX1262 · 14×20 mm)

| | URL |
|--|-----|
| **Factory product page** | https://www.cdebyte.com/products/E22-900M22S |
| **Price** | **~$5–7** → **R80–112** |

---

## GNSS RTK — **must be 50 Hz** (reject LC29H / LG290P)

| Module | Max rate | Verdict |
|--------|----------|---------|
| LC29H(**DA**) | **1 Hz** RTK | **NO** |
| LC29H(**EA**) | **10 Hz** RTK | **NO** |
| LG290P | **20 Hz** | **NO** |
| **UM980** | **50 Hz** | **YES — buy this class** |

| Board | Size | Price | URL |
|-------|------|-------|-----|
| **UM980 breakout** (gnss.store) | **26×39 mm** | **~R2 720 ($170)** | https://gnss.store/products/elt0223 |
| SparkFun UM980 Triband | larger | **R7 360 ($459.95)** — skip (expensive + export issues) | https://www.sparkfun.com/products/23286 |
| Ali “UM980 RTK board 50Hz” | check photo | **~R2 400+ ($150+)** | AliExpress — **verify 50 Hz in listing/firmware** |

UM980 chip itself is **17×22 mm**. Confirm seller firmware supports **50 Hz** (some need upgrade).

---

## Housing

AliExpress: Hero 9–13 waterproof housing 60m — **&lt; R100 (~$5–6)**.

---

## Quick buy order (50 Hz path)

1. https://gnss.store/products/elt0223 — **UM980 50 Hz**  
2. https://ebyteiot.com/products/2-4ghz-ble-mesh-small-smd-e73-2g4m08s1c-nordic-nrf52840-module-small-size-ble-5-0 — nRF  
3. https://www.cdebyte.com/products/E22-900M22S — LoRa  
4. Ali housing &lt; R100  

Ebyte: **ebyteiot@cdebyte.com**
