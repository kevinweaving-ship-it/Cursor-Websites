# Boat Puck — components to beat Vakaros + Sailmon

Compare the two systems we benchmarked, then list **only what we must build** so Boat Puck is the best race-management system at a fraction of the cost.

| | **Vakaros** (Atlas 2 + HALO + RaceSense) | **Sailmon MAX** | **Boat Puck (ours)** |
|--|------------------------------------------|-----------------|----------------------|
| What it is | Fleet **race network** + instruments | Sailor **performance instrument** | Fleet **race network** (HALO-class), cheap shell |
| Positioning | Atlas ~25 cm DGNSS; HALO **~1 cm RTK** | ~metre GNSS (no fleet RTK) | **cm RTK** on every boat |
| Sensors | 25 Hz GNSS / 50 Hz fusion (Atlas) | 25 Hz GNSS + 9-DOF | Target **≥50 Hz GNSS + ≥100 Hz IMU** (beat on paper) |
| Radio | Proprietary **2.4 GHz RaceSense mesh** (no cellular for critical) | Wi‑Fi / BT / NMEA to phone-cloud | **LoRa SX1262** fleet net (no cellular for critical) |
| Display | Expensive Atlas screen on boat | Expensive 4.4" display | **BLE → watch / phone** (cost kill) |
| RC tools | Tablet: sync start, live line, OCS, finish, scoring | None (not race control) | Same class: start / line / OCS / finish |
| Shell | Custom HALO / Atlas | Custom MAX | **GoPro H9–13 housing** |

**Sailmon is not the architecture to copy** for race management.  
**Vakaros is.** We win by matching RaceSense/HALO capability, beating sensor rate and cost, and skipping the screen.

---

## 1. What Vakaros has that we must match (or beat)

| Capability | Vakaros implementation | Boat Puck must have |
|------------|------------------------|---------------------|
| cm boat position | HALO RTK + hull model | RTK rover + antenna + **mount offset / bow model** |
| Corrections without cellular | RaceSense mesh carries RTK/DGNSS | **LoRa downlink RTCM** from committee base |
| Live start line | Atlas units at line ends | **Line-end references** (2× pucks or RC+pin) on LoRa |
| Sync race clock | RaceSense time | **LoRa time sync** from RC |
| Auto OCS | Geometry + cm pos at gun | Same math on puck and/or RC |
| Individual recall / status | Mesh + LED ring / Atlas UI | LoRa flag + **LED** + BLE alert |
| Finish / scoring | RaceSense finish | Crossing detection + RC scoring |
| Fleet scale | 100+ boats demonstrated | LoRa **TDMA / slotted uplink** for large fleets |
| Sailor feedback | Atlas / LED | **BLE app/watch** (DTL, timer, OCS) |
| Endurance | 100+ h claimed | Battery for **full race day+** (stretch: multi-day) |
| Independent of phone network | Explicit | **Hard requirement** |

## 2. What Sailmon has that we optionally steal (not core)

| Capability | Needed for “best race system”? | Our approach |
|------------|--------------------------------|--------------|
| Fancy transflective display | No (cost) | Phone/watch |
| NMEA wind / BSP / depth | Nice later | Out of v1 puck |
| Cloud session analytics | Nice later | Log locally; sync after racing |
| VMG / line bias UI | Yes as **software** on BLE display | App features, not extra hardware |

---

## 3. Components we need — Boat Puck (every boat)

Envelope: **71.8 × 50.8 × 33.6 mm** GoPro H9–13 shell.  
Lens pocket **~Ø32 × 5.5 mm** = GNSS antenna.

### Tier A — must ship (parity with HALO + RaceSense)

| # | Component | Why (vs competitors) |
|---|-----------|----------------------|
| 1 | **Dual-band GNSS antenna** (L1+L5) in lens pocket | HALO-class sky view; cm RTK needs good antenna |
| 2 | **RTK GNSS rover module** (L1+L5, high update) | Match HALO cm; **beat** Atlas 25 Hz → target **50 Hz** class |
| 3 | **IMU ≥100 Hz** (6- or 9-axis) | Beat Atlas 50 Hz fusion; heel/pitch/heading + outage coasting |
| 4 | **Sensor-fusion MCU** | Turn GNSS+IMU into boat state + OCS geometry |
| 5 | **SX1262 LoRa transceiver + antenna** | Our RaceSense: RTCM in, telemetry out, no cellular |
| 6 | **BLE** (MCU built-in or module) | Replace Atlas screen with watch/phone |
| 7 | **Status RGB LED** (or light pipe) | HALO LED ring lite: FIX / OCS / radio |
| 8 | **Battery + charger IC** | Race-day runtime; Qi later if budget allows |
| 9 | **Non-volatile config + log flash** | Boat ID, bow offset, track if RF drops |
| 10 | **3D insert sled** in GoPro housing | Repeatable antenna/hull reference (HALO mount discipline) |

### Tier B — to be *best* (advantage over Vakaros)

| # | Component / feature | Why “best” |
|---|---------------------|------------|
| 11 | **Higher-rate GNSS+IMU than Atlas** | 50 Hz / 100 Hz marketing + better start call resolution |
| 12 | **Sub‑GHz LoRa range** | Often longer reach than 2.4 GHz BLE-mesh on open water |
| 13 | **No mandatory display hardware** | Huge cost/weight win vs Atlas+HALO stack |
| 14 | **Commodity waterproof shell** | GoPro ecosystem mounts, cheap spares |
| 15 | **Open sailor UI** (phone/watch) | Faster iteration than locked Atlas UI |
| 16 | **On-puck OCS compute** (optional) | Low latency alert even if uplink busy |

### Tier C — later (Sailmon-like extras, not required to beat RaceSense)

| Component | When |
|-----------|------|
| NMEA in, wind/BSP | After race network is solid |
| Qi charging | Convenience |
| Cellular “spectator uplink” on RC only | Media — never race-critical |
| LED halo ring | HALO cosmetics |

---

## 4. Components we need — Committee / shore (one set for the fleet)

This is what makes us a **race system** like Vakaros — Sailmon has **none** of this.

| # | Component | Why |
|---|-----------|-----|
| 1 | **RTK GNSS base receiver** (L1+L5) | Source of cm corrections (HALO base / Skylark role) |
| 2 | **Base GNSS antenna** (survey/marine) | Clear sky, stable mount on RC boat or shore |
| 3 | **LoRa hub (SX1262) + good antenna** | Broadcast RTCM; receive all boats (RaceSense radio role) |
| 4 | **Host computer** (Pi / laptop / tablet) | Bridge RTCM → LoRa; run Race Control |
| 5 | **Race Control software** | Sync start, live line, OCS list, finish, scoring |
| 6 | **Start-line ends** (2× references) | Live moving line like Atlas-at-pin/RC — use 2 pucks or dedicated refs |
| 7 | **All-day power** | 12 V / PD — race day reliability |

**Optional but “best”:** second LoRa sector antenna / repeater for big courses; encrypted fleet key (RaceSense security parity).

---

## 5. Data the system must carry (drives radio + MCU)

| Message | Direction | Competitor equivalent |
|---------|-----------|------------------------|
| RTCM corrections | Base → boats | RaceSense RTK feed |
| Time sync / gun | RC → boats | RaceSense sync start |
| Line ends / course | RC → boats | Live ping / marks |
| Position + fix quality | Boat → RC | Live tracking |
| OCS / penalty state | Both | OCS list + LED |
| Finish event | Boat → RC | Auto finish |
| Sailor UI metrics | Puck → BLE | Atlas DTL / timer |

---

## 6. Architecture we’re building (best of both worlds)

```
                    ┌─ Sailmon-like sailor UX (cheap) ─┐
                    │  BLE → watch / phone             │
                    └──────────────▲───────────────────┘
                                   │
┌──────── Vakaros-like race core ──┴──────────────────────────┐
│  RTK base → LoRa → every puck (cm)                           │
│  Pucks → LoRa → Race Control (OCS / finish / track)        │
│  Hull offset + line geometry                                 │
│  Sensors aimed faster than Atlas                             │
│  Shell = GoPro (cost)                                        │
└──────────────────────────────────────────────────────────────┘
```

**Not building:** Sailmon’s expensive display + NMEA instrument hub as the product centre.  
**Are building:** Vakaros race network, cheaper and (on paper) hotter sensors.

---

## 7. Shortest component checklist

**Every boat:** GPS ant + RTK rover + IMU + MCU + SX1262 + BLE + LED + battery + sled in GoPro case.  

**Committee:** RTK base + ant + SX1262 hub + Race Control host + line-end refs + power.

That set is the minimum to **equal RaceSense/HALO** and **beat Sailmon** at race management — and the lever to be **best on cost, rate, and display flexibility**.
