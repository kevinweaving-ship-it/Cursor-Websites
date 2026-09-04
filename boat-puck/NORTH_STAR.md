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
| Sailor UI | Expensive Atlas on boat | **Universal Puck** back-cover LCD + BLE watch/phone/tablet |
| Shell | Custom only | **Biggest common action-cam case** (production look) |
| Price | Atlas + HALO stack is elite | Fraction of that BOM; same race jobs |
| Software | Closed | Own Race Control; iterate UI fast |

---

## One boat puck, one race network

| | Product | Beats Vakaros by… |
|--|---------|-------------------|
| **Universal Puck** | Action-cam case + back-cover screen; Opti → bigger boats | Cost/weight; one SKU for fleets |
| **Bigger boats** | Same puck + **tablet / smartwatch app** over BLE | Atlas-like UI without a second brick |
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
