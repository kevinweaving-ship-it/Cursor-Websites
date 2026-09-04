# Boat Puck — full system breakdown (for Robby)

**Audience:** engineer / developer who must understand the whole race system end-to-end.  
**Date:** 2026-09-04 · **FX for guide prices:** **R16 / $1** (always show both — see [`PRICE_RULE.md`](PRICE_RULE.md)).  
**Product goal:** cheaper Vakaros-class fleet race network (cm RTK + LoRa + start/line/OCS), not a Sailmon clone.

**Locked V1 hardware bet:** OTW/Anzewei **WT-43-RK-LoRa** (boat/pin/mark) + **WT-43-BK-LoRa** (committee base). **Unicore UM980** = benchmark / fallback. **UWB off every-boat BOM.**

Related digests:

| Doc | What |
|-----|------|
| [`DEV_DIRECTION_2026-09_to_Shenzhen_2027-04.md`](DEV_DIRECTION_2026-09_to_Shenzhen_2027-04.md) | Sep 2026 → Shenzhen Apr 2027 direction |
| [`race-kit-roles-wt43-v1.md`](race-kit-roles-wt43-v1.md) | Who gets which box |
| [`logic-check-wt43-v1.md`](logic-check-wt43-v1.md) | Why WT-43 is V1 core |
| [`accuracy-vs-racesense-pins.md`](accuracy-vs-racesense-pins.md) | Lipton R1–R10 OCS accuracy bar |
| [`universal-puck.md`](universal-puck.md) | Puck + optional screen/watch/tablet |
| [`housing/README.md`](housing/README.md) | GoPro H9–13 shell packing |
| [`puck-components-buy-list.md`](puck-components-buy-list.md) | Alternate discrete UM980 path parts |
| [`components-requirements.md`](components-requirements.md) | Capability checklist vs Vakaros |

**Live Lipton references (same GPS, different UIs):**

- Vakaros player: https://player.vakaros.com/watch/Lv9A35uOBSBRmGpHgXtH/J22  
- SailingSA replay: https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-dev  
- Sailfish UI: https://sailingsa.co.za/tracking-dev2.html  

---

## 0. One picture of the whole system

```
                         ┌─────────────────────────────────────┐
                         │  COMMITTEE BOAT (Race Control)      │
                         │  • WT-43-BK-LoRa = RTK BASE         │
                         │  • Survey antenna on pole           │
                         │  • Laptop/tablet = Race Control SW  │
                         │  • Optional 4G for spectators only  │
                         └──────────────┬──────────────────────┘
                                        │ LoRa broadcast RTCM
                                        │ (no cellular on race path)
          ┌─────────────────────────────┼─────────────────────────────┐
          ▼                             ▼                             ▼
   ┌──────────────┐            ┌──────────────┐              ┌──────────────┐
   │ START PIN    │            │ MARK packs   │              │ BOAT PUCKS   │
   │ WT-43 rover  │            │ WT-43 rover  │              │ WT-43 rover  │
   │ float/clip   │            │ float/clip   │              │ + nRF54L15   │
   │              │            │ each mark    │              │ + IMU+batt   │
   │              │            │              │              │ + GoPro case │
   └──────┬───────┘            └──────┬───────┘              └──────┬───────┘
          │ positions                 │ positions                   │ pos + OCS
          └───────────────────────────┴──────────── LoRa uplink ────┘
                                        │
                                        ▼
                               Race Control UI
                               (line, OCS, finish, tracks)

   Boat Puck ──BLE──► watch / phone / optional Screen housing
   (optional experiment) Bow Tag nRF54L15 ↔ Puck Channel Sounding
```

**Hard rules**

1. **One RTK base** for the whole venue (committee). Everything else is a **rover**.  
2. **No cellular on the race-critical path** (RTCM, gun, OCS, finish). Optional 4G = media/spectator only.  
3. **Live priority:** start/OCS → finish → mark roundings. Full track may **store + backfill** between events.  
4. Marks and boats are **radios/relays**, not GNSS-only dumb sensors (Lipton dropped points upwind to M1).

---

## 1. What problem we are solving (OCS bar)

From Lipton Challenge Cup J22 R1–R10 (Vakaros GPS):

| Fact | Implication |
|------|-------------|
| Many OCS/clear calls sit in **~0.1–0.5 m** at the gun | Sub-metre DGNSS is **marginal**; need **cm RTK** |
| Example R1: KYC **+0.21 m** OCS vs GLYC **−0.19 m** clear | Decision gap **~0.4 m** |
| RC→M1 ~**1.5–2.3 km**; boats ~**2–2.5 km** from RC | LoRa design margin **≥3 km** usable |
| Worst dropouts **upwind to M1**, not always max range | Need **relays** + **on-device store/backfill** |

Full write-up: [`accuracy-vs-racesense-pins.md`](accuracy-vs-racesense-pins.md).

**OCS math (same class as RaceSense):**

1. Live line = **committee end** + **start pin** (both RTK).  
2. Boat reports antenna position; firmware applies **puck→bow lever arm** using heading/IMU.  
3. At gun epoch **T=0** (GNSS-synced), signed horizontal distance of **bow** to line.  
4. Publish confidence: **definite OCS / clear / grey zone** (do not pretend datasheet 1 cm = finished OCS 1 cm).

Error budget to **measure**: RTK fix · line ends · timing · bow geometry · heading.

---

## 2. Roles — what sits where

### 2.1 Committee boat (Race Control)

| Item | What | Why |
|------|------|-----|
| **WT-43-BK-LoRa** | RTK **base** | Broadcasts RTCM over integrated LoRa to all rovers |
| **Survey / patch antenna on pole** | Better base antenna | On-module patch is weak for *base*; pole clears metal |
| **12 V / large battery box** | All-day power | Base must not die mid-race |
| **Laptop or tablet** | Race Control host | Start sequence, line, OCS list, finish, scoring, maps |
| **USB/UART bridge** (Pi or USB-serial) | Host ↔ base / hub | Pipe status, inject race messages, log |
| **Optional 2nd WT-43 rover on bow** | Clean “committee end” of line | Only if base pole ≠ the geometric line end |
| **Optional 4G modem** | Spectator uplink | **Never** required for OCS |

**V1 simplest layout:** base antenna pole on committee **is** one end of the start line.

**Guide price (committee core electronics):**

| Part | Guide | URL |
|------|------:|-----|
| WT-43-BK-LoRa | **~R512–900 ($32–56)** factory; Ali ~**R867 ($54)** | https://www.ontheway-tech.com/product/wt-43-bk-lora-module/ |
| Survey patch + pole + box | **~R300–800 ($19–50)** | any marine/survey patch + PVC pole |
| Host laptop/tablet | bring existing | — |
| **Committee core total** | **~R850–1 700 ($53–106)** + host | |

Factory contact pattern: `Lucaszhang@ontheway-tech.com` (confirm on reply).

---

### 2.2 Start pin (not committee end)

| Item | What |
|------|------|
| **WT-43-RK-LoRa** | Rover — continuous cm position |
| Sealed **float / clip pack** | Survives dunk + pin clip |
| Battery (1–2 race days) | Same LoRa mesh as boats |
| **No** BLE watch stack required | Not a sailor UI device |

**Job:** other end of start line → Race Control + every boat compute live line / OCS.

**Guide price:** **~R850–900 ($53–56)** per pin pack (module-dominated).

Product page (rover): https://www.ontheway-tech.com/product/wt-43-rk-lora/

---

### 2.3 Marks (windward, leeward, gate, offset, …)

| Item | What |
|------|------|
| **1× WT-43-RK-LoRa rover pack per mark** | Same brick as pin |
| Gate | **2 packs** (L + R) |
| Firmware role | Position report + **LoRa relay** for boats up the course |

**Job:** live mark positions for tracking / bounds / optional hit-mark; **radio relay** so upwind boats don’t go dark (Lipton lesson).

**Not** an RTK base. Never configure a mark as second base.

**Guide price:** **~R850–900 ($53–56) × N marks**.

---

### 2.4 Finish

| Layout | Hardware |
|--------|----------|
| **Finish = start** (common dinghy) | Reuse committee end + start pin — **no extra finish pin** |
| **Separate finish line** | Finish boat **rover** + finish pin **rover** (committee base stays at start) |
| **Finish at a mark** | That mark pack is the target |

**Rule:** finish ends are always **rovers**. Only **one base** venue-wide.

---

### 2.5 Racing boat — the Puck

Primary sailor product: [`universal-puck.md`](universal-puck.md).

| Layer | Part | Role |
|-------|------|------|
| GNSS+LoRa brick | **WT-43-RK-LoRa** | RTK rover; receives RTCM; UART NMEA/positions out |
| App MCU | **nRF54L15** (prod) / Tag+DK (proto) | Fusion, OCS, LoRa protocol helper, BLE to UI, OTA, logging |
| Motion | **6–9 DOF IMU** (from Nordic Tag first, then BMI270-class) | Heel, heading, puck→bow lever |
| Power | **3000–5000 mAh** LiPo + charger | Full race day+ |
| Shell | **GoPro H9–13 waterproof case** | Cheap, mount ecosystem, sky-friendly |
| Antenna | Module patch **or** case-top L1+L5 if needed | **Must prove** inside housing |
| Status | RGB LED | FIX / radio / OCS |
| Optional bow | **nRF54L15 Tag** | Bluetooth 6 Channel Sounding experiment |
| Optional UI | Phone / watch / Screen housing | BLE client only — **no LoRa on UI device** |

**Housing packing:** cavity ≈ camera **71.8 × 50.8 × 33.6 mm**; lens tunnel = GPS well **~Ø32 × 5.5 mm**. See [`housing/README.md`](housing/README.md).

**WT-43 size note:** factory **43 × 43 × ~14 mm** (not 8.2 mm). Fits GoPro only with flat battery + tight sled — [`logic-check-wt43-v1.md`](logic-check-wt43-v1.md).

---

### 2.6 Optional Screen / Atlas display (not V1 race-critical)

| SKU | Role | Guide | URL |
|-----|------|------:|-----|
| Waveshare ESP32-S3-RLCD-4.2 | UI proto | **R400 ($24.99)** | https://www.waveshare.com/esp32-s3-rlcd-4.2.htm?sku=33507 |
| Docs | — | — | https://docs.waveshare.com/ESP32-S3-RLCD-4.2 |

Doctrine: Screen is **BLE client of Puck**, not a second radio brain.

---

## 3. Boat Puck — bill of materials (V1 primary path)

### 3.1 Primary V1 (WT-43 integrated)

| # | Component | Qty/boat | Guide price | Buy / datasheet |
|---|-----------|---------:|------------:|-----------------|
| 1 | **WT-43-RK-LoRa** (rover) | 1 | **R512–900 ($32–56)** | https://www.ontheway-tech.com/product/wt-43-rk-lora/ |
| 2 | **nRF54L15 DK** (bench) / module later | shared | DK ~**R1 600–2 400 ($100–150)** class via DigiKey/Mouser | https://www.nordicsemi.com/Products/Development-hardware/nRF54L15-DK |
| 3 | **nRF54L15 Tag** (bow / IMU / CS) | 0–1 | ~**R480–560 ($30–35)** | https://www.nordicsemi.com/Products/Development-hardware/nRF54L15-Tag |
| 4 | IMU (if not using Tag) | 1 | **R30–80 ($2–5)** BMI270-class | DigiKey / Mouser BMI270 |
| 5 | LiPo 3–5 Ah + charge | 1 | **R80–200 ($5–12)** | any flat LiPo + TP4056-class |
| 6 | GoPro H9–13 waterproof case | 1 | **R80–100 ($5–6)** | AliExpress HERO9–13 protective housing |
| 7 | 3D sled / insert | 1 | **R20–50 ($1–3)** print | design in `housing/` |
| 8 | LED + passives + wiring | 1 | **R20–40 ($1–2.5)** | — |
| | **Electronics+shell guide (WT-43 path)** | | **~R850–1 350 ($53–84)** early; volume lower | |

**Kill / prove gate for this path:** moving **RTK FIX @ up to 20 Hz** with **LoRa RTCM** over water. Fail → UM980 path.

### 3.2 Fallback / benchmark (discrete UM980)

Use if WT-43 fails rate / FIX / antenna / LoRa on water.

| # | Component | Guide | URL |
|---|-----------|------:|-----|
| GNSS | Unicore **UM980** board | **R960–2 080 ($60–130)** Ali · **R2 720 ($170)** trusted | https://en.unicore.com/products/um980/ · https://gnss.store/products/elt0223 |
| MCU+BLE interim | Ebyte **E73** nRF52840 | **R122 ($7.60)** | https://ebyteiot.com/products/2-4ghz-ble-mesh-small-smd-e73-2g4m08s1c-nordic-nrf52840-module-small-size-ble-5-0 |
| LoRa discrete | Ebyte **E22-900M22S** | **R96 ($5.98)** | https://ebyteiot.com/products/sx1262-868mhz-module-electronic-components-22dbm-wireless-transceiver-lora-gfsk-iot-long-range-7km-ebyte-e22-900m22s-spi |
| Alt LoRa UART | **A39**-class | **R110–130 ($7–8)** | e.g. https://openelab.io/products/lora-a39-t900a30d1a (verify SA band) |
| Housing | same GoPro | **R80–100** | Ali |
| **Puck total (UM980 path)** | | **~R1 900–3 500 ($120–220)** | [`puck-components-buy-list.md`](puck-components-buy-list.md) |

### 3.3 Lab-only (do not put on every boat)

| Part | Why | URL |
|------|-----|-----|
| Qorvo/Decawave **DWM3001C** UWB | Ranging reference only (~R700+/boat unjustified) | DigiKey DWM3001C |
| **NXP MCXW72-LOC** ×2 | Independent BT Channel Sounding benchmark | NXP / DigiKey MCXW72 kits |

### 3.4 How the Puck is assembled (proto)

1. Print/mill **sled** that locks WT-43 so the GNSS face looks out the **lens window**.  
2. Place **battery flat** beside/under module (height budget is the tight constraint).  
3. Wire **UART**: WT-43 TX/RX → nRF54L15 UART; share GND; 5 V or regulated rail per datasheet.  
4. Wire **IMU** (SPI/I²C) to nRF; or use Tag’s onboard IMU for early tests.  
5. LoRa antenna: keep clear of battery foil; if module antenna is blind in plastic, add **external L1+L5** through a sealed gland / case-top patch.  
6. Close GoPro door; mount with **sky view** (transom / foredeck / pushpit — class rules permitting).  
7. Calibrate **antenna → bow** offset in config (metres along centreline + lateral).

Production later: custom PCB + own mould — **not yet** (Shenzhen Apr 2027 evidence-first).

---

## 4. How the radio / data plane works

### 4.1 Downlink (critical): RTCM corrections

```
Committee WT-43 BASE  --LoRa broadcast RTCM-->  every rover (boats, pin, marks)
```

- **Broadcast** — do **not** ACK every correction (fleet of 50–100 would melt the air).  
- SA band / power compliance must be checked for 410–525 MHz class modules (WT-43 LoRa band on datasheet).  
- Target usable range **≥3 km** over water at the air rate that still sustains FIX.

### 4.2 Uplink: positions, events, relays

```
Rovers --LoRa--> Race Control (and peer relays)
```

Suggested message classes:

| Message | Who → whom | Priority |
|---------|------------|----------|
| RTCM | Base → all | Continuous |
| Time / gun / start sequence | RC → all | Critical |
| Line ends / course / mark IDs | RC → all | High |
| Position + fix quality + boat ID | Boat → RC (+relay) | High near start/finish; backfill else |
| Pin / mark position | Pin/mark → RC + boats | High |
| OCS / penalty state | Boat ↔ RC | Critical at start |
| Finish cross event | Boat → RC | Critical |
| Track samples | Boat → RC | Store locally; uplink when quiet |
| Relay frames | Mark/boat → boat | As needed for coverage |

**Store + backfill (mandatory from Lipton):**

- Puck logs **all** GNSS samples locally (flash).  
- Live stream can drop; between roundings, **ACK/backfill** missing segments.  
- “Jumps” in Vakaros trails were **missing samples**, not teleportation.

### 4.3 BLE (boat-local only)

```
Puck --BLE--> watch / phone / Screen housing
```

Carries: DTL to line, countdown, OCS flag, speed/heading, battery, config.  
**Does not** carry RTCM for the fleet.

### 4.4 Optional BT6 Channel Sounding (experiment)

```
Bow Tag (nRF54L15 Tag)  <->  Puck (nRF54L15)   // 0.25–100 m ranging
```

Only interesting if sailing **95%** error ≤ ~5–10 cm. Else **RTK + geometry** stays authoritative for bow.

---

## 5. How OCS works (software + geometry)

### 5.1 Inputs at gun

| Input | Source |
|-------|--------|
| Line end A | Committee end (base antenna or bow rover) |
| Line end B | Start pin rover |
| Gun time T=0 | Race Control start sequence, GNSS time sync over LoRa |
| Boat antenna (x,y) | Boat puck RTK at/near T=0 (interpolate if 10–20 Hz) |
| Heading / heel | IMU (+ mag if trusted) |
| Lever arm | Config: antenna → bow (and optional beam offset) |

### 5.2 Algorithm (conceptual)

1. Build infinite line through A–B in **horizontal ENU / local metres**.  
2. Transform antenna → **bow point** using heading + lever.  
3. Signed distance of bow to line (course side = positive).  
4. Classify vs thresholds (example policy — tune from data):  
   - `> +grey` → **OCS**  
   - `< −grey` → **clear**  
   - else → **grey zone** (RC decision / individual recall UI)  
5. Emit event to RC + LED + BLE alert on boat.

### 5.3 Why IMU still matters with cm RTK

- Antenna is rarely at the bow.  
- Heel/leeway change the horizontal lever.  
- Short GNSS blips need coasting.  
- Heading quality drives OCS as much as centimetres of RTK on tight calls.

### 5.4 What must be developed (OCS stack)

| Software piece | Where it runs |
|----------------|---------------|
| GNSS parse + time stamp | Puck MCU |
| Lever-arm + heading fusion | Puck MCU |
| Line geometry + signed distance | Puck **and/or** Race Control (prefer both: local alert + RC authority) |
| Gun scheduler / sync | Race Control → LoRa |
| OCS list UI + protest log | Race Control |
| Confidence / grey-zone policy | Both |
| Replay tools vs video | Shore / SailingSA tooling |

---

## 6. What software must be written (full list)

### 6.1 Embedded — Boat Puck firmware (nRF54L15 + WT-43)

| Module | Responsibility |
|--------|----------------|
| `gnss_uart` | Config WT-43 rate (target 10–20 Hz), parse NMEA/RTCM status, FIX quality |
| `lora_link` | Join mesh/star, receive RTCM, send telemetry, relay, duty cycle |
| `time_sync` | Align to RC GNSS time / gun countdown |
| `imu_fusion` | Heel, pitch, yaw rate, heading estimate |
| `boat_model` | Antenna→bow/stern offsets per class |
| `ocs_engine` | Line distance, gun latch, flags |
| `finish_engine` | Crossing detection vs finish line/mark |
| `mark_events` | Rounding heuristics (optional V1.1) |
| `logger` | Ring buffer / flash; backfill protocol |
| `ble_gatt` | Sailor UI service (DTL, timer, OCS, battery, config) |
| `ota` | Firmware update (BLE or LoRa slow path) |
| `power` | Sleep between races, brownout, charge state |
| `led` | FIX / LOS / OCS / battery codes |
| `cs_ranging` (exp) | Channel Sounding to bow tag |

### 6.2 Embedded — Pin / mark pack firmware

Same GNSS+LoRa brick, **stripped** UI:

- Rover FIX  
- High-rate position broadcast near start (pin)  
- Lower-rate + **relay** role (marks)  
- Battery / health telemetry  
- No BLE sailor stack required (optional BLE for setup phone)

### 6.3 Embedded — Committee base

- WT-43 **base mode**  
- Continuous RTCM LoRa broadcast  
- Health (satellites, age, TX duty) to Race Control host  
- Optional: host injects race messages on same radio via MCU bridge

### 6.4 Race Control application (laptop/tablet)

| Feature | Notes |
|---------|-------|
| Fleet map | Boats, pin, marks, line |
| Start sequence | 5-4-1-gun; sync to GNSS time |
| Live line | From committee end + pin |
| OCS board | Auto list + grey zone + manual override |
| Individual recall / general recall | Flags to boats over LoRa |
| Finish / scoring | Auto cross + manual |
| Course editor | Mark order, gates, finish mode |
| Radio health | RSSI, FIX%, correction age |
| Logging / export | For protests + SailingSA ingest |
| Spectator export (optional) | 4G only |

Tech choice open (Electron / Flutter / web+local server). Must work **offline on water**.

### 6.5 Sailor apps

| Client | Job |
|--------|-----|
| Phone (iOS/Android) | Setup, offsets, live DTL/timer/OCS |
| Watch | Eyes-up countdown / OCS vibe |
| Screen housing firmware | Digits + **loud** start/OCS beep |

### 6.6 Shore / SailingSA integration (later)

- Ingest tracks into existing replay (`lipton-dev-trail-rN.json` class)  
- Compare vs Vakaros for validation  
- Not required for first on-water OCS proof

---

## 7. Minimal kits and guide budgets

### 7.1 Bench prove (buy first)

| Qty | Item | ~R | ~$ |
|----:|------|---:|---:|
| 1 | WT-43-BK-LoRa base | 850–900 | 53–56 |
| 1 | WT-43-RK-LoRa rover | 850–900 | 53–56 |
| 2 | nRF54L15 DK | ~3 200–4 800 | 200–300 |
| 2 | nRF54L15 Tag | ~960–1 120 | 60–70 |
| — | Wires, USB serial, bench PSU | 200 | 12 |
| | **Bench subtotal** | **~R6 000–8 000** | **~$375–500** |

**Pass gate:** static then moving FIX with LoRa RTCM.

### 7.2 Two-boat OCS field kit

| Qty | Item | Role | ~R each |
|----:|------|------|--------:|
| 1 | WT-43 base + pole | Committee | 850–900 + ant |
| 2 | Boat Pucks | Rovers + MCU/IMU/case | 850–1 350 |
| 1 | Pin pack | Start pin | 850–900 |
| 1 | Host tablet | Race Control | existing |
| | **Field electronics** | | **~R4 500–6 500 ($280–400)** |

### 7.3 Club event kit (illustrative)

| Role | Qty | ~R |
|------|----:|---:|
| Base | 1 | 900 |
| Boat Pucks | 20 | 20 × 1 100 ≈ 22 000 |
| Start pin | 1 | 900 |
| Marks (W + gate + L) | 4 | 3 600 |
| Finish (if separate) | 0–2 | 0–1 800 |
| **Rough fleet electronics** | | **~R28 000–30 000 ($1.7k–1.9k)** |

Compare: Vakaros Atlas 2 ~**$1 249 (~R20 000)** **per boat** + HALO ~**$599**. Our boat puck target remains **≪ Atlas**.

---

## 8. Assembly matrix (what plugs to what)

| From | To | Interface | Notes |
|------|-----|-----------|-------|
| WT-43 rover | nRF54L15 | UART TTL | NMEA + status; baud up to 921600 |
| WT-43 LoRa | peer WT-43 / hub | LoRa RF | RTCM / telemetry |
| IMU | nRF54L15 | SPI or I²C | ≥100 Hz preferred |
| Battery | 5 V rail / charger | power | WT-43 typ. 3.6–6 V (5 V) |
| nRF54L15 | LED | GPIO | status |
| nRF54L15 | Phone/watch | BLE | sailor UI |
| nRF54L15 | Bow Tag | BLE CS | experiment |
| Base WT-43 | Race Control host | USB-UART or BLE bridge | config + health |
| Race Control | Base radio | same | gun / course messages |

---

## 9. Development sequence (for Robby)

1. **Bench RTK:** 1 base + 1 rover, walk test, log FIX%, age of corrections.  
2. **Rate:** lock 10 Hz then 20 Hz moving.  
3. **MCU bring-up:** nRF54L15 reads GNSS UART; LED = FIX.  
4. **OCS sandbox:** two fixed line ends + one moving rover; gun button; plot signed distance.  
5. **Housing:** sled in GoPro; re-test antenna (may need external).  
6. **Two boats + pin on water:** deliberate OCS vs clear vs video.  
7. **Add windward mark pack:** measure uplink loss with/without relay.  
8. **Store/backfill:** induce RF blackouts; prove log completeness.  
9. **BT6 CS bow tag:** only after RTK OCS works.  
10. **UM980 A/B:** if WT-43 fails gates.  
11. **Shenzhen Apr 2027:** take working units + datasets + BOM asks 100/500/1000 — not “what tracker do you sell?”

---

## 10. Clickable buy list (quick)

| What | URL | Guide |
|------|-----|------:|
| WT-43-RK-LoRa (rover) | https://www.ontheway-tech.com/product/wt-43-rk-lora/ | R512–900 ($32–56) |
| WT-43-BK-LoRa (base) | https://www.ontheway-tech.com/product/wt-43-bk-lora-module/ | R512–900 ($32–56) |
| Unicore UM980 | https://en.unicore.com/products/um980/ | OEM |
| UM980 trusted board | https://gnss.store/products/elt0223 | R2 720 ($170) |
| nRF54L15 DK | https://www.nordicsemi.com/Products/Development-hardware/nRF54L15-DK | ~$100–150 |
| nRF54L15 Tag | https://www.nordicsemi.com/Products/Development-hardware/nRF54L15-Tag | ~$30–35 |
| Ebyte E73 nRF52840 | https://ebyteiot.com/products/2-4ghz-ble-mesh-small-smd-e73-2g4m08s1c-nordic-nrf52840-module-small-size-ble-5-0 | R122 ($7.60) |
| Ebyte E22 LoRa | https://ebyteiot.com/products/sx1262-868mhz-module-electronic-components-22dbm-wireless-transceiver-lora-gfsk-iot-long-range-7km-ebyte-e22-900m22s-spi | R96 ($5.98) |
| Waveshare 4.2" RLCD | https://www.waveshare.com/esp32-s3-rlcd-4.2.htm?sku=33507 | R400 ($24.99) |
| GoPro H9–13 case | AliExpress “HERO9 HERO10 HERO11 HERO12 HERO13 protective housing” | R80–100 ($5–6) |

**Do not buy as Boat Puck:** locked indoor iBeacon-only nRF54L tags (e.g. KKM “NRF54L Bluetooth 6.0 Beacon”) — wrong firmware class for Channel Sounding / open Nordic SDK. Use **Nordic’s** Tag/DK.

---

## 11. Glossary

| Term | Meaning |
|------|---------|
| **Base** | Stationary RTK reference that emits corrections |
| **Rover** | Moving RTK receiver (boat, pin, mark) |
| **RTCM** | Correction messages for RTK |
| **FIX** | RTK fixed integer solution (cm-class) |
| **OCS** | On course side (over early) at start |
| **DTL** | Distance to line |
| **Puck** | Boat unit in GoPro shell |
| **Pin pack** | Sealed rover on start/finish pin |
| **Mark pack** | Sealed rover on a course mark (+ relay) |
| **Race Control** | Committee software + operator |

---

## 12. One-page “if you remember nothing else”

1. **Committee** = 1× WT-43 **base** + antenna pole + Race Control laptop.  
2. **Pin / marks / finish ends** = WT-43 **rovers** in float packs.  
3. **Every boat** = WT-43 rover + nRF54L15 + IMU + battery in **GoPro** case.  
4. **LoRa** carries RTCM down and positions/events up; **BLE** is sailor UI only.  
5. **OCS** = bow vs live RTK line at GNSS gun time, with grey zone.  
6. **Write:** puck firmware, pin/mark firmware, Race Control app, sailor BLE apps, logger/backfill.  
7. **Prove** moving LoRa-RTK before scaling; **UM980** if WT-43 dies; **no UWB** on every boat.  
8. Prices above are **guide** at R16/$1 — re-quote before PO.

---

*End of Robby breakdown. Keep this file as the single onboarding map; deep dives stay in the linked docs.*
