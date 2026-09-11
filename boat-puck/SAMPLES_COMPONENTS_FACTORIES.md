# Samples — all components + factories

**Date:** 2026-09-11 · **FX:** R16 / $1  
**Locked V1 path:** factory **WT-43** + Ebyte **nRF54** + Ali GoPro clone.  
**Prices:** [`cost-what-goes-where.md`](cost-what-goes-where.md) · **cart intent:** [`FINAL_BETA_BUY_LIST_RAND.md`](FINAL_BETA_BUY_LIST_RAND.md)

---

## Factories / sellers (who to contact)

| # | Factory / seller | Role | Contact / store | Notes |
|---|------------------|------|-----------------|-------|
| 1 | **Anzewei / OTW** (安泽微 / On The Way) | **Core** — WT-43-RK + WT-43-BK | https://www.ontheway-tech.com/ · https://www.gpsgnssmodule.com/ · `Lucaszhang@ontheway-tech.com` | Buy **factory-direct** ($32–36), not Ali (~$54) |
| 2 | **Ebyte** (Chengdu 亿佰特) | **Core** — nRF54 MCU+BLE · optional DIY LoRa | https://www.cdebyte.com/ · https://ebyteiot.com/ · `ebyteiot@cdebyte.com` | E73 nRF54L15 + E22-400 (SA 433) |
| 3 | **Ali / Made-in-China** (any reliable seller) | Housing, battery, dry box, antenna bits | AliExpress / Made-in-China | Not a critical OEM relationship |
| 4 | **Nordic** via DigiKey/Mouser | Lab DK + optional bow Tag | DigiKey nRF54L15 DK / Tag | Lab / Channel Sounding only — **not** in puck BOM |
| 5 | **Unicore** (和芯星通) | Optional DIY GNSS fallback | https://en.unicore.com/ · `info@unicorecomm.com` · +86-10-69939828 | UM980/UM960 boards — Path B if WT-43 fails water test |
| 6 | **Quectel** (移远) | Optional DIY GNSS parallel | https://www.quectel.com/ · disti / SparkFun LG290P | Only if learning ≤2 units |
| 7 | **gnss.store** (EU) | Trusted UM980 breakout if Ali flaky | https://gnss.store/products/elt0223 | Not China factory; backup 1-pc |
| 8 | **BYOD / retail** | Sailor UI + Race Control UI | Apple / Wear OS / phone / own laptop | **No factory sample** — install our app |

**RFQ later (not beta samples):** Huayuen 华云 · Haidao 海导 · Tianhe 天禾 — Ø~12 cm LoRa+RTK terminals (too big for dinghy puck).

---

## A) BUY NOW — sample cart (minimum working race path)

| # | Component | Qty | Factory | ~USD | ~Rand | Goes on |
|---|-----------|----:|---------|-----:|------:|---------|
| 1 | **WT-43-BK-LoRa** | **1** | Anzewei/OTW factory | 32–36 | 515–571 | Committee boat (RTK **base**) |
| 2 | **WT-43-RK-LoRa** | **2–3** | Anzewei/OTW factory | 32–36 | 515–571 | 1× pin + 1× boat puck (+1 mark/spare) |
| 3 | **E73-2G4M08S1F** (nRF54L15) | **2** | Ebyte | 5.6–6.4 | 90–102 | Inside **boat puck** only (BLE brain) |
| 4 | **H9–13 GoPro clone housing** | **1** / puck | Ali / Made-in-China | 5–6.5 | 80–104 | Boat puck shell |
| 5 | **LiPo + charge board** | **1** / unit | Ali | 3.7–6.1 | 59–98 | Puck + pin + committee box |
| 6 | Committee antenna + pole | **1** | Ali survey patch class | 15–40 | 240–640 | Committee — antenna **on line end** |
| 7 | Dry box + USB bank / 12 V | **1** | Ali | 10–30 | 160–480 | Committee weather/power |
| 8 | USB-serial / Pi Zero-class | **1** | Ali / Pi | 5–15 | 80–240 | Committee UART ↔ Race Control |
| 9 | 3D sled + wire + passives | **1** / puck | Print in-house | 2.5–5.5 | 40–88 | Fit WT-43 + MCU in shell |

### Optional lab (same round if budget)

| # | Component | Qty | Factory | ~USD | ~Rand | Why |
|---|-----------|----:|---------|-----:|------:|-----|
| 10 | **nRF54L15 DK** | 0–1 | Nordic / DigiKey | 58 | 928 | Firmware lab — **not** in housing |
| 11 | **nRF54L15 Tag** | 0–1 | Nordic / DigiKey | 31 | 499 | Bow Channel Sounding experiment |

### Do **not** sample as fleet hardware

| Skip | Why |
|------|-----|
| Official GoPro ADDIV-001 | R800–880 shell alone |
| Ali WT-43 if factory quotes | ~$54 vs factory $32–36 |
| Second committee WT-43 | One base, antenna on line |
| UWB bricks | Off every-boat BOM |
| XM30R as helm glass | Survey handset, not sailor UI |
| Locked Ali “smartwatches” (Kospet etc.) | Cannot install our app |

**Core sample spend (no DigiKey):** roughly **R2.6k–4k** for 1 base + 2–3 RK + 2× nRF54 + 1 housing + batteries + committee bits.

---

## B) What each sample builds

| Build | Parts from A | Factory touchpoints |
|-------|--------------|---------------------|
| **1× Committee kit** | BK + antenna/pole + dry box + bridge | OTW + Ali |
| **1× Boat Puck** | RK + E73 nRF54 + LiPo + H9–13 + sled | OTW + Ebyte + Ali |
| **1× Pin / mark pack** | RK + LiPo + float/clip box (**no** nRF54) | OTW + Ali |
| **Sailor UI** | BYOD phone / Apple Watch / Wear OS | None — install app |
| **Race Control UI** | BYOD laptop / IP68 tablet | None (or Ali tablet later) |

---

## C) OPTIONAL ≤2 learn samples (parallel — do not mix into puck unit cost)

| # | Component | Factory / seller | ~USD | Purpose |
|---|-----------|------------------|-----:|---------|
| L1 | **Quectel LG290P** board ×1–2 + **E22-400M22S** ×2 | Quectel disti + **Ebyte** | 50–120 + ~6 | Best DIY GNSS+SA LoRa if WT-43 rate/FIX disappoints |
| L2 | **Unicore UM980** board ×1 | Unicore / Ali / gnss.store | 60–170 | ≥25 Hz (50 Hz stretch) discrete path |
| L3 | **E22-400** (433 MHz) ×2 | Ebyte | ~6 | SA band DIY LoRa (prefer over E22-900 for SA) |
| L4 | OTW **WT-4545-RK** ×1 | Anzewei/OTW | RFQ | GNSS-only sibling + own LoRa |
| L5 | **UM981+ESP32+LoRa** mower PCB ×1 | Ali | 80–200 | Teardown “all-in-one” claim |
| L6 | **UM982** / Holybro heading ×1 | Unicore / Holybro | RFQ | Dual-antenna heading learn |
| L7 | SkyTraq **PX1125R** ×2 | Disti / Ali | cheap | Cheapest dual-band pair |
| L8 | Dalang **LD-29** / Beitian **BT-M002C** ×1 | Ali | 19–57 | Cheap GNSS bench only (no LoRa) |

Pick **≤2** of L1–L8 until water data on WT-43 exists.

---

## D) Emails before pay (paste)

**1 — Anzewei / OTW**

> Quote 1-pc and 10-pc USD for: **WT-43-BK-LoRa**, **WT-43-RK-LoRa** (also list WT-4545-RK if available).  
> Confirm: LoRa centre options for **South Africa 433 MHz**, max Hz while RTK FIX + LoRa RTCM active, NMEA sample, chipset, antenna type, base+rover pairing.

**2 — Ebyte**

> Order **E73-2G4M08S1F** ×2. Quote **E22-400M22S** ×2 (433 MHz SA). Bulk at 50 pcs each?

**3 — Unicore / Ali UM980 (only if Path B)**

> Need **UM980** (not UM960/982 unless separate). Confirm max position rate Hz (≥25; prefer 50 FW). Board mm. Price 1 / 10 / 100 USD.

---

## E) Factory map (one glance)

```
Anzewei/OTW ──► WT-43-BK (×1 committee) + WT-43-RK (puck/pin/marks)
Ebyte ────────► E73 nRF54L15 (puck BLE) · E22-400 (optional DIY LoRa)
Ali ──────────► H9–13 shell · LiPo · dry box · antenna/pole
Nordic/DigiKey ► DK + Tag (lab only)
Unicore/Quectel ► optional learn GNSS only
Sailor/RC UI ─► BYOD (install Boat Puck) — not a China sample
```
