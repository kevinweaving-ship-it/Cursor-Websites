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
| **Race Control** | Laptop/tablet on committee — not a Puck |
| **As start/finish “boat end”?** | **Yes, if** the committee boat *is* that end of the line → use **base antenna position** as that end **or** add a **2nd WT-43 rover** on the bow for a clean line coordinate while base stays on a pole |

**V1 simplest:** base pole on committee = **one end of the start line**. No second unit until you need bow vs pole separation.

**Budget (committee core):** **~R850–900** (WT-43) + antenna/pole/battery box.

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
