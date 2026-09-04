# Boat Puck — north star

**We are building our own RaceSense / HALO / Atlas stack — better and cheaper than Vakaros.**  
We are **not** building a cheap Sailmon MAX.

Sailmon = sailor performance instrument + cloud.  
**Vakaros = fleet race management** (cm RTK, mesh, live line, OCS, sync start, finish).  
Boat Puck copies the **second** job and beats it on cost, rate, openness, and market fit (dinghy + keelboat).

---

## Better than Vakaros — how

| Dimension | Vakaros | Boat Puck (target) |
|-----------|---------|---------------------|
| Positioning | Atlas ~25 cm; HALO ~1 cm RTK | **cm RTK on every boat** |
| Corrections | RaceSense mesh (no cellular critical) | **LoRa RTCM** from committee (no cellular critical) |
| Sensors | 25 Hz GNSS / 50 Hz fusion (Atlas) | **≥50 Hz GNSS + ≥100 Hz IMU** |
| Radio | Proprietary 2.4 GHz | **SX1262 LoRa** — long range, open stack |
| Sailor UI | Expensive Atlas on boat | **Puck** (no glass) + optional **Screen** housing + BLE watch/phone/tablet |
| Shell | Custom only | **Two** common action-cam cases (production look); mount anywhere |
| Price | Atlas + HALO stack is elite | Fraction of that BOM; same race jobs |
| Software | Closed | Own Race Control; iterate UI fast |

---

## One race network — split boat kit

| | Product | Beats Vakaros by… |
|--|---------|-------------------|
| **Puck** | GoPro case: small MCU + battery + RTK + LoRa + IMU; **no screen** | Cost/weight; sky-friendly mount |
| **Screen** | Second GoPro case: small MCU + battery + back-cover LCD | Digits where eyes are; optional buy |
| **Bigger boats** | Same Puck + tablet/watch app (and/or Screen) | Atlas-like UI without a second radio brick |
| **Boat Atlas** (later) | Optional own shell + 4.2" RLCD | Only if volume pays for custom glass |

Committee gear is shared: RTK base + LoRa hub + Race Control + line ends.

Primary boat doc: [`universal-puck.md`](universal-puck.md).  
Markets note: [`markets-dinghy-keelboat.md`](markets-dinghy-keelboat.md).

---

## Explicitly not the centre

- Sailmon-style NMEA instrument hub as the product  
- Phone-network-dependent race timing  
- Shipping Waveshare’s voice/AI calendar board as the boat instrument  

Race-critical path stays: **base → LoRa → boats → LoRa → Race Control**.
