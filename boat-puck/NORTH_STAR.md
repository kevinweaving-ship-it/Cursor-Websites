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
| Sailor UI | Expensive Atlas on boat | **Dinghy:** BLE watch/phone · **Keelboat (Boat Atlas):** **4.2" reflective LCD** |
| Shell | Custom only | **Dinghy:** GoPro ecosystem · **Keelboat:** own IP67 |
| Price | Atlas + HALO stack is elite | Fraction of that BOM; same race jobs |
| Software | Closed | Own Race Control; iterate UI fast |

---

## Two markets, one race network

| Market | Product | Beats Vakaros by… |
|--------|---------|-------------------|
| **Dinghy** | Small puck (GoPro) + BLE | Cost/weight; clubs can equip a whole fleet |
| **Keelboat** | **Puck guts + 4.2" RLCD** in own housing (**Boat Atlas**) | Atlas-like sunlight UI without Atlas price |

Committee gear is shared: RTK base + LoRa hub + Race Control + line ends.

Detail: [`markets-dinghy-keelboat.md`](markets-dinghy-keelboat.md).

---

## Explicitly not the centre

- Sailmon-style NMEA instrument hub as the product  
- Phone-network-dependent race timing  
- Shipping Waveshare’s voice/AI calendar board as the boat instrument  

Race-critical path stays: **base → LoRa → boats → LoRa → Race Control**.
