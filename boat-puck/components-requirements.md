# Boat Puck — component requirements (LoRa + RTK)

Envelope: GoPro H9–13 housing **71.8 × 50.8 × 33.6 mm**.  
Front lens pocket: **~Ø32 × 5.5 mm** → **GPS/GNSS antenna**.

## System idea (cheap HALO / RaceSense-class)

```
COMMITTEE BOAT                         EACH RACING BOAT
─────────────────                      ─────────────────
RTK Base GNSS  ──RTCM──┐               Boat Puck (GoPro shell)
                       │                  GNSS rover (RTK FIX)
LoRa radio (SX1262) ◄──┴── broadcast ──►  LoRa (SX1262)
     ▲                                    BLE ──► watch / phone
     │                                    IMU / MCU / battery
     │         boat position / status
Race Control ◄───────────────────────────┘
(tablet / laptop)
```

**Two LoRa flows (same radio family):**

1. **Downlink (critical for cm):** Base → all pucks = **RTCM corrections** (+ time sync, line geometry, race state).  
2. **Uplink:** Each puck → race control = **position / heading / OCS flags / battery**.

Cellular is **not** required for race-critical traffic (same principle as Vakaros RaceSense).

---

## A. Inside each Boat Puck (the GoPro box)

### Must-have

| Block | Role | Notes / fit |
|-------|------|-------------|
| **GNSS antenna** | Receive L1 (+ L5 preferred) | **In front lens pocket**, facing housing glass. ≤ ~Ø30 × 5 mm stack. |
| **GNSS rover module** | RTK rover → cm position | Dual-band L1/L5 if possible (e.g. Unicore/Quectel/u-blox class). Needs RTCM in. Target high rate (10–50 Hz class). |
| **IMU (6- or 9-axis)** | Heel / pitch / heading aid | Sensor fusion with GNSS; helps when satellites briefly drop. |
| **MCU** | Fusion, protocol, radio, BLE | ESP32-C3/S3, nRF52, or STM32 — enough UART/SPI for GNSS + LoRa + BLE. |
| **LoRa radio (SX1262 class)** | RTCM in + telemetry out | Sub‑GHz (region: 868 / 915). Antenna: whip/chip/flex — **not** behind big ground under GPS patch. |
| **BLE** | Sailor display | Phone / watch: DTL, timer, OCS, SOG. No expensive on-puck screen. |
| **Battery** | Runtime | LiPo / Li-ion pouch sized to leftover volume after PCBs. Target multi-hour race day min; stretch goal day+. |
| **PMIC / charge** | Power path | USB‑C charge when housing open or via sealed pogo later. |
| **Status LED** | Fix / LoRa / OCS | Can use housing translucency or small light pipe; optional external LED ring later. |

### Should-have

| Block | Role |
|-------|------|
| **Flash / log** | Record track if radio drops |
| **Hull / mount offset config** | Stored lever-arm from antenna to bow/line reference (HALO-style geometry) |
| **Watchdog / brownout** | Don’t brick mid-start |
| **Unique boat ID** | Fleet addressing on LoRa |

### Explicitly out of the puck (for v1)

| Item | Why |
|------|-----|
| Large LCD | Cost/size — use BLE watch/phone |
| NMEA2000 / wind instruments | Sailmon territory, not race mesh |
| Cellular modem | Optional later for spectator tracking only |

### Rough stack inside the box (front → back)

1. **GPS antenna** (lens pocket)  
2. Thin foam to glass  
3. **GNSS module + MCU PCB**  
4. **SX1262 + BLE** (same PCB or mezzanine)  
5. **IMU** on PCB  
6. **Battery pouch**  
7. Foam crush pad at backdoor  

Everything must live in **71.8 × 50.8 × 33.6 mm**.

---

## B. Committee boat — RTK base + LoRa hub

This is **not** in a GoPro shell. One set serves the whole fleet.

### Must-have

| Block | Role | Notes |
|-------|------|-------|
| **RTK base GNSS** | Survey-grade or “base mode” dual-band receiver | Fixed antenna with clear sky; known/absolute position. |
| **Base GNSS antenna** | L1/L5 survey antenna | Mag-mount / pole on committee boat or shore. Stable mount matters more than pretty box. |
| **RTCM generator** | Base outputs RTCM3 | From base receiver UART/USB. |
| **LoRa hub (SX1262 class)** | Broadcast RTCM to fleet; receive boat telemetry | Higher duty-cycle TX for corrections; good antenna (elevated). May need **gateway MCU** (Pi / ESP32 / laptop dongle). |
| **Race Control app** | Timers, start line ends, OCS list, finishes | Tablet/laptop. Line ends can be: two more pucks, or RC + pin positions. |
| **Power** | Base + radio all day | 12 V boat / powerbank / USB‑PD. |

### Should-have

| Block | Role |
|-------|------|
| **2× line-end references** | Pin + committee positions on LoRa (can be “base-class” pucks or spare rovers) for live moving line |
| **Shore repeater** (optional) | If course is huge / RF shadowed |
| **Logging PC** | Protest / replay |

### Correction path (cm accuracy)

```
Base GNSS (fixed) → RTCM3 stream → LoRa broadcast → each puck GNSS rover → RTK FIX (cm)
```

Without RTCM, pucks fall back to metre-class GNSS (still useful for tracking, **not** for fair OCS).

---

## C. LoRa backbone requirements

| Need | Requirement |
|------|-------------|
| Chip | **SX1262** class (or SX1261/8 same family) |
| Band | Local ISM (EU 868 / US 915 / AU 915 / ZA — confirm) |
| Topology v1 | **Star:** committee hub ↔ boats (simplest) |
| Topology later | Mesh / store-forward if range or occlusions demand it |
| Downlink payload | RTCM fragments + sync + race state (line, gun, flags) |
| Uplink payload | Lat/lon/alt or local ENU, heading, SOG, fix quality, boat ID, battery |
| Rate budget | RTCM often ~0.5–1 Hz effective; positions 1–5 Hz v1 (higher later) |
| Fairness | Scheduled uplink slots so 30–100 boats don’t collide |
| Independence | Race-critical path must work **with phone airplane mode** |

---

## D. Functional requirements (what the components must enable)

| # | Requirement |
|---|-------------|
| R1 | Each puck achieves **RTK FIX** when base is up and sky is OK |
| R2 | Fleet gets corrections **over LoRa**, not cellular |
| R3 | Race control sees live boat positions |
| R4 | Start line geometry known (RC + pin) |
| R5 | OCS / DTL computable at gun (hull offset configured) |
| R6 | Sailor gets timer / DTL / OCS via **BLE** display |
| R7 | One charge lasts at least a race day |
| R8 | Fits **H9–13 GoPro housing** with sealed backdoor |

---

## E. Minimum BOM sketch (names = class, not frozen SKUs)

### Per boat puck

1. Dual-band RTK GNSS module (rover)  
2. GNSS patch / PCB antenna (lens pocket)  
3. SX1262 LoRa module + matching antenna  
4. MCU with BLE (or MCU + BLE module)  
5. IMU  
6. LiPo + charger IC  
7. LED(s), buttons optional  
8. Flex PCB / rigid PCB + 3D insert sled  

### Per committee set

1. Dual-band GNSS **base** receiver  
2. Survey / marine GNSS antenna + mount  
3. SX1262 hub (power amp / better antenna as needed)  
4. Host (Pi / laptop / tablet) running Race Control + RTCM bridge  
5. Power distribution  
6. Optional: 2× reference pucks for line ends  

---

## F. Open choices (next decisions)

1. **GNSS module:** cost vs L1+L5 RTK rate (Unicore / Quectel / u-blox / “K902-class”).  
2. **LoRa air protocol:** raw RTCM framing + TDMA uplink vs LoRaWAN (LoRaWAN is usually wrong for low-latency race mesh — prefer custom star).  
3. **Antenna:** ceramic in lens pocket vs PCB under glass.  
4. **Line ends:** dedicated units vs reused pucks.  
5. **Region frequency** + legal ERP.

---

## Bottom line

**In the GoPro box:** GNSS antenna (front) + RTK rover + IMU + MCU + **SX1262 LoRa** + BLE + battery.  
**On the committee boat:** RTK **base** + LoRa **hub** broadcasting RTCM + Race Control receiving boat reports.

That is the cheap HALO path: **cm from local RTK over LoRa**, display on a watch/phone, shell from a commodity GoPro housing.
