# Logic check — WT-43 as Puck V1 core (Rand only)

FX: **R16 / $1** (internal only — quotes below in **R**).  
Factory: [WT-43-RK-LORA](https://www.ontheway-tech.com/product/wt-43-rk-lora/).

## Verdict

**Mostly sound. Good enough to build V1 around — with three hard caveats.**  
Agree: better **first prototype** bet than ~**R2 000+** UM980 + separate LoRa.

| Claim | Score |
|-------|--------|
| cm RTK class for OCS | **Pass** (datasheet; antenna TBD) |
| 20 Hz + time-stamp math | **Pass** |
| LoRa corrections, no cellular | **Pass on paper** |
| UART/NMEA usable | **Pass** |
| Power ~0.4 W | **Pass** |
| Fits GoPro | **Pass if you use 14 mm height** (not 8.2) |
| Dynamics | **Pass** |
| Cost R600–750 | **Optimistic** — plan **R850–900** Ali / **R500–850** factory quote |
| “Proven at 20 Hz + LoRa FIX moving” | **Not proven** — your own gate is correct |

---

## Point-by-point

### 1. Accuracy — agree, with math tweak
Factory: **H 1 cm + 1 ppm CEP50 · V 2 cm + 1 ppm**.  
At **1 km** baseline: 1 ppm ≈ **1 mm** → ~**1.1 cm** H (not ~2 cm). At **2 km** → ~**1.2 cm**.  
Still **OCS-class** on paper. Real world = antenna + multipath on a wet boat.

### 2. 20 Hz + interpolate — agree
Factory **1–20 Hz**. Time-stamped fix + interpolate to start gun is the right OCS method.  
**20 Hz ≠ Atlas 25 Hz** — close enough for V1; not a reason to reject.

### 3. LoRa RTK path — agree as architecture
Factory story matches: base → LoRa → rover RTK. Urban **1–2 km**, open **~5 km**.  
**Caveat:** correction **latency + packet loss** at 20 Hz while moving is **exactly** what two samples must prove.

### 4. UART/NMEA — agree
Baud to **921600**, NMEA — fine for our MCU.  
Ignore “u-blox binary” marketing noise; chip is **unnamed** L1+L5 / 128-ch class.

### 5. Power — agree
**80 mA @ 5 V ≈ 0.4 W**. + BLE/IMU still day-sailable on ~3000 mAh.

### 6. Size — fix the number
Factory: **43 × 43 × 14 mm** (±0.5), **not 8.2 mm**.  
Still OK in GoPro *if* battery is flat and layout is tight. Integrated **antenna on module** is the bigger risk than mm.

### 7. Dynamics — agree
**515 m/s · ≤4 g** — dinghy is nowhere near.

---

## Cost (R only)

| Item | R |
|------|--:|
| WT-43 Ali (live earlier) | **~867** |
| WT-43 factory quotes (range) | **~512–864** |
| Your “R600–750” | Possible on factory quote; **don’t bank Ali that low** |
| UM980 board alone | **~1 600–2 720** |
| UM980 + separate E22 LoRa | **~1 700–2 850** |

**V1 core:** WT-43 wins on **R and integration**.  
**Long race stack:** UM980 still better if you need ≥25–50 Hz clean multi-freq later.

---

## Stack — agree, with one antenna rule

```
WT-43 RTK+LoRa  → 20 Hz cm + corrections
E73 BLE MCU     → watch/phone + logic
IMU             → heel/pitch + puck→bow
LiPo + charger
GoPro case
```

**Must test / may need:** external or case-top **L1+L5 antenna** if onboard patch is blind in the housing. Do not assume the 43 mm integrated antenna is race-OK.

---

## Decision alignment

| Your call | Ours |
|-----------|------|
| V1 around WT-43 | **Yes** |
| Two samples before ×100 | **Mandatory** |
| Better than ~R2k UM980+DWM for V1 | **Yes** |
| Field gate: FIX @ 20 Hz moving + LoRa | **Correct kill criterion** |

**Buy now (R):** 2× WT-43 (**~R1 700–1 800** Ali) + 2× E73 (**~R244**) + housing/battery/IMU.  
If moving FIX dies → fall back UM980 path.
