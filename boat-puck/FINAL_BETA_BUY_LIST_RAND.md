# Final beta buy list — what for what (Rand)

**FX:** R16 / $1 · **Date:** 2026-09-06  
**Rule:** one architecture — **WT-43 + nRF54**. Optional lines are learn-only (≤2).

Prices are **guide 1-pc**; re-check before pay. Prefer **OTW factory** WT-43 (~**R512–576**) over Ali (~**R850–900**).

---

## BUY NOW — core beta

| # | Role | What | Qty | ~R each | ~R line |
|---|------|------|----:|--------:|--------:|
| 1 | **Committee — RTK corrections** | **WT-43-BK-LoRa** (base) · factory | 1 | 512–576 | **512–576** |
| 2 | **Boat puck / pin / mark / finish** | **WT-43-RK-LoRa** (rover) · factory | 2–3 | 512–576 | **1 024–1 728** |
| 3 | **Puck MCU + BLE / later CS** | **nRF54L15 DK** *or* Ebyte **E73-2G4M08S1F** | 2 | 480–560 (DK) / 80–240 (Ebyte) | **160–1 120** |
| 4 | **Bow Channel Sounding test** | Nordic **nRF54L15 Tag** | 1 | 480–560 | **480–560** |
| 5 | **Housing + power** | Your waterproof boxes + 5 V packs | — | — | **yours** |

**Core total (2 rovers + 1 base + 2 MCU + 1 Tag):** about **R2 200–4 000**  
**Core total (3 rovers):** about **R2 700–4 600**

### Who gets which WT-43

| Unit | Role |
|------|------|
| **BK ×1** | Committee base → LoRa RTCM to everyone |
| **RK #1** | Start **pin** (other end of line) |
| **RK #2** | First **boat puck** |
| **RK #3** (if buy) | Windward mark *or* 2nd boat |

Marks / finish / more boats = more **RK** later (same brick). **Only one BK** for the venue.

---

## OPTIONAL — pick ≤2 learn units

| Role | What | Qty | ~R | When |
|------|------|----:|---:|------|
| DIY parallel GNSS | **UM960** or **UM980** board + **E22-400** LoRa ×2 | 1+2 | 560–2 720 + 130–220 | If WT-43 FIX/Hz fails |
| Cheap DIY GNSS | **Dalang LD-29 / Beitian BT-M002C** + E22-400 | 1+1 | 300–900 + 65–110 | Bench only |
| Better Quectel DIY | **LG290P** board + E22-400 | 1+1 | 800–1 920 + 65–110 | 20 Hz DIY path |
| Heading (committee / keelboat) | **UM982** board *or* Holybro H-RTK UM982 | 1 | 1 280–2 800 / **~4 000** | Big-boat / Gilbert |
| Survey / Android UI | **XM30R** *or* Minewsemi GE3PGS51 | 1 | **3 211** / **2 445** | Ashore survey only |
| Teardown weird box | Huaxing RTK+LoRa+UWB | 1 | **3 342** | Only if LoRa=RTCM |
| Better antenna terminal | **Huayuen HY-SA100-9R** / Haidao T62 | 1 | **RFQ** | Committee/marks if Ø12 cm OK |
| Long-range radio backup | Chinese UHF 410–470 1–2 W | 1–2 | 800–2 400 | If LoRa dies at 2–3 km |

---

## DO NOT BUY (fleet)

| Item | ~R | Why |
|------|---:|-----|
| KKM nRF54 iBeacon | 163 | Not Channel Sounding |
| DFRobot LC29H LoRa kit (868/915) | 2 400–4 000 | Wrong band for SA |
| CHCNAV / Hi-Target full sticks | 30 000+ | Survey toys |
| OTW ZED-F9P+LoRa / WitMotion M10+LoRa | 1 900–2 100 | 2–3× WT-43 for same job |
| UWB on every boat | 700+ | Lab only |
| Second RTK **base** | — | One BK only |

---

## Minimal money path (prove FIX on water)

| Buy | ~R |
|-----|---:|
| WT-43-BK ×1 | 512–576 |
| WT-43-RK ×2 | 1 024–1 152 |
| Ebyte nRF54 ×2 (cheap MCU path) | 160–480 |
| **Subtotal** | **~R1 700–2 200** + your boxes |

---

## One email before pay

**OTW factory:** WT-43-BK + RK, 1-pc and 10-pc USD, **433 MHz LoRa for South Africa**, max Hz with LoRa RTCM, NMEA while FIX.
