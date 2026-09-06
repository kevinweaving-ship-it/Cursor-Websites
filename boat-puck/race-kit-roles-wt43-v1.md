# Recommendation — race kit roles (WT-43 V1)

**Rand only.** FX R16/$1 for internal math — quote in **R**.

## Recommendation now

**Build Puck V1 and the race network around OTW/Anzewei WT-43-RK-LORA.**

| Role | Hardware | Mode |
|------|----------|------|
| Every racing boat | **Puck** = WT-43 + small BLE MCU + IMU + battery + GoPro case | **Rover** |
| Whole fleet corrections | **One** WT-43 as **RTK base** (committee or shore) | **Base** → LoRa RTCM |
| Line / marks / finish ends | Same WT-43 in a sealed float/clip pack | **Rover** (report position) |

One chip family everywhere. Prove **2× boat + 1× base** first, then pins/marks.

---

## Who needs what

### 1. Committee boat (Race Control)

**Jobs:** run Race Control UI · broadcast RTCM · often sit near one end of the start/finish.

| Fit | Need |
|-----|------|
| **RTK base (required)** | **1× WT-43 in base mode** + best practical antenna (even a cheap survey patch on a pole beats the onboard chip antenna for the *base*) + 12 V / big battery · LoRa out |
| **Race Control** | **IP68 tablet or laptop** on committee — **UI only**, not a puck / not the RTK base |
| **As start/finish “boat end”?** | **Usually the same one device.** Put the **base antenna on the geometric line end** (bow / staff on the line). **Do not** buy a second WT-43 for committee unless the base antenna *cannot* sit on the line (e.g. pole midships for sky, line is at the bow) — only then add an optional bow **rover**. |

**V1 default:** **one** WT-43-BK on committee. Antenna **on the line end**. That single position is both “base” and “committee end of the line.”

**Only split into two** if physics forces it (antenna needs clear sky midships, but the line is at the bow). That is an exception, not the design.

**Tablet note:** An IP68 tablet (XM30R-class or any rugged tablet) is the **Race Control screen** (Vakaros-tablet role). It does **not** replace **WT-43-BK**. Full layout including finish boat / rescue: [`race-setup-who-gets-what.md`](race-setup-who-gets-what.md).

**Budget (committee core):** **~R515–571** (one WT-43-BK factory) + antenna/pole/battery box + **tablet/laptop** (existing or buy).

---

### 2. Starting pin (not the committee end)

**Job:** other end of the start line → continuous RTK position → boats + Race Control compute the line / OCS.

| Fit | Need |
|-----|------|
| **Start pin** | **1× WT-43 rover** in a sealed float/clip on the pin · battery · same LoRa mesh |

Not a full sailor Puck (no BLE watch stack required). Same radio/GNSS brick.

**Budget:** **~R850–900** per pin pack.

---

### 3. Marks (windward, leeward, gate, etc.)

**Job:** live mark positions for tracking, bounds, optional “hit mark” logic — **not** RTK base.

| Fit | Need |
|-----|------|
| **Each mark** | **1× WT-43 rover** pack (same as pin) |

Gate = **two** packs (left + right).

**Budget:** **~R850–900 × N marks**.

---

### 4. Finish — committee end vs finish pin

| Finish layout | Committee end | Other end |
|---------------|---------------|-----------|
| **Finish = start line** (common dinghy) | Same as start — **reuse** committee base/end + **start pin** | **No extra finish pin** |
| **Separate finish line** | Finish boat **or** committee at finish: **rover** (or move base — don’t) | **1× finish pin rover** |
| **Finish at a mark** | That **mark pack** is the finish target — no finish pin | — |

**Rule:** only **one base** for the whole venue. Finish ends are always **rovers**, never a second base.

If finish ≠ start and committee stays at the start: put a **finish boat rover** + **finish pin rover** (two packs).

---

## Minimal club kit (V1 field test → first event)

| Qty | Unit | Role | ~R each |
|----:|------|------|--------:|
| 1 | WT-43 **base** | Committee corrections (+ optional line end) | 850–900 |
| 2 | WT-43 **rover** Pucks | Two boats (prove OCS) | 850–900 + MCU/IMU/case |
| 1 | WT-43 **rover** | Start pin | 850–900 |
| 0–1 | WT-43 **rover** | Windward mark (optional early) | 850–900 |

**Later event add:** more boat Pucks · mark packs · finish pin only if finish ≠ start.

---

## Data flow (unchanged)

```
Committee BASE (WT-43) --LoRa RTCM--> all ROVERS
Boat / pin / mark ROVERS --LoRa positions--> Race Control
Boat Puck --BLE--> watch / phone / optional screen
```

OCS: committee end + start pin = line · boat bow = IMU lever from Puck · gun epoch = GNSS time.

---

## Buy order now

1. **2× WT-43** — one base, one rover (bench)  
2. **+2× WT-43** — second boat + start pin  
3. MCU/IMU/battery/GoPro for boat Pucks only  

Kill criterion unchanged: **FIX @ 20 Hz moving with LoRa corrections**. Fail → revisit UM980 path.
