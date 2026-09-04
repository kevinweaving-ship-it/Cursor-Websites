# Chat reassessment — GNSS buys (2026-09-04)

## What changed

Earlier scoring used a **hard ≥50 Hz GNSS** lock.  
**Vakaros Atlas 2 ships ~25 Hz GNSS** (+ IMU fusion ~50 Hz feel).  
**50 Hz was a stretch goal we invented** — not required to match Atlas race jobs.

**Revised bar (this reassessment):**

```
Puck GNSS:  ≥25 Hz position out (RTK or high-rate PVT)   ← Atlas parity
Puck IMU:   ≥100 Hz                                       ← unchanged
Stretch:    50 Hz GNSS if BOM/size allows (UM980 path)
Committee base: ~1 Hz RTCM — rate irrelevant
```

---

## Rescored — everything from this chat

### Buy / look (Atlas-parity)

| Item | Rate / class | Role | Action |
|------|----------------|------|--------|
| **UM980** board ([gnss.store](https://gnss.store/products/elt0223) / Ali / HighGain) | up to **50 Hz** | **Best Puck rover** + race base | **Buy** — still preferred (headroom + multi-freq) |
| **HighGain** UM980 SKU only | claim 10/20 → FW **50** | Same | Ask sample + board mm (71×46 may not fit GoPro) |
| **OTW WT-43-RK-LORA** ([factory](https://www.ontheway-tech.com/product/wt-43-rk-lora/)) | **1–20 Hz** dual-freq + **LoRa** | **Cheap committee / LoRa-RTK trial** | **Look** — ~R867; not long-term race rover if we want ≥25 Hz clean |
| **ZED-F9P** class boards | typically **≤20–25 Hz** | Possible **Atlas-parity rover** if ≥25 Hz confirmed | Look only if UM980 size/cost hurts |
| E73 nRF + E22 LoRa + GoPro H9–13 case | — | MCU / radio / shell | Buy as before |

### Ask GNSS guts only (not UWB story)

| Item | GNSS read | Ask? |
|------|-----------|------|
| **WES WE-T350** card | Optional **L1+L5 RTK** (~LC29H bands), Hz **unpublished**, RTK **1 cm+1 ppm** | **Yes — chip P/N + max RTK Hz + bare module?** Expect ≤10 Hz → committee toy only |
| HighGain / Ali UM980 kits | Real boards | Confirm **UM980** not UM960; rate; samples |

### Skip (still)

| Item | Why |
|------|-----|
| **XM30R** Android 4G PoC handheld | Finished radio; unknown chip/Hz |
| **SIYI M9N** “RTK” puck | Meter-level drone GPS, not cm RTK |
| **LC29H** / LD-29 / JS-ATP38-M | ≤10 Hz or not RTK |
| **GeoPod Mini** stick | Finished capsule, **20 Hz**, too big |
| **WEST-HN** catalog (T311 etc.) | UWB/RFID IoT — no UM980; T350 not even in store |
| Gutting walkies / badges | Wrong layer — buy modules |

---

## Product stack (unchanged)

1. **Universal Puck** (GoPro) — MCU + batt + **RTK GNSS** + LoRa + IMU — no screen  
2. Screen options via BLE  
3. Later optional Boat Atlas shell + 4.2" RLCD  

FX: **R16 / $1**.

---

## Practical next buy order

1. **UM980** breakout (1 pc) — race rover path  
2. **WT-43-RK-LORA** (1–2 pcs) — cheap base + LoRa experiment  
3. E73 + E22 + housing  
4. Message WE-T350 seller **GNSS-only** questions (chip / Hz / bare) — optional lead  

**Do not** block the project on 50 Hz. Match Atlas at **≥25 Hz**; treat **50 Hz** as upgrade when UM980 fits and FW confirms.
