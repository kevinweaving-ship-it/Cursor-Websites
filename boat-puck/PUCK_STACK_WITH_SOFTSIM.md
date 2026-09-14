# Puck stack — with SoftSIM fitted

**Cavity:** 71.8 × 50.8 × 33.6 mm (H9–13)

## What’s in each puck (locked)

| # | Part | Size / note | Qty rule |
|---|------|-------------|----------|
| 1 | **H9–13 housing** | Shell | ×3 |
| 2 | **WT-43-RK-LORA** | 43×43×14 · RTK + LoRa 868 · GNSS→lens | ×3 |
| 3 | **ME54BS62** (nRF54) | Race brain / BLE · UART hub | ×3 |
| 4 | **Flat LiPo ~1000 mAh** | Under/beside stack | ×3 (of 4 w/ committee) |
| 5 | **TP4056** | Charge path | ×3 (of 4) |
| 6 | **Qi RX** | ≤48×32×1.5 · side/rear wall | ×3 |
| 7 | **SoftSIM LTE** | **A7672 SoftSIM** (or SIM7672 / EG915U) on ≤28×28 carrier + **FPC cell ant on wall** | **×3** (same puck roles) |

**Not in puck:** WT-43-BK, dry box, survey ant (committee).

---

## Pack (SoftSIM in the leftover strip)

```
H9–13  71.8 × 50.8 × 33.6
┌────────────────────────────────────┐
│ WT-43-RK 43×43×14  (GNSS→lens)     │▓▓ SoftSIM 24×24×2.4
│                                    │▓▓ ≤28×28 carrier
│ LiPo flat                          │▓▓ FPC LTE ant → WALL
│ nRF54 ──UART── SoftSIM             │   (not sky / not GNSS face)
│ Qi RX on side/rear wall            │
└────────────────────────────────────┘
 Leftover beside WT-43 ≈ 28.8 mm  →  A7672 fits (~4.8 mm margin)
```

| SoftSIM pick | Why |
|--------------|-----|
| **1st: SIMCom A7672 SoftSIM** | 24×24×2.4 · Cat 1 · SA LTE · SoftSIM FW |
| Alt: SIM7672 / EG915U | Same strip fit |
| **Out:** EG21/EG25, EVB, ESP32+4G, nRF91-first for SA | Too big or coverage |

**Wiring:** SoftSIM UART → **nRF54**. LoRa still primary on race day when in range. SoftSIM = training alone + LoRa-range backhaul (boat **and** mark/pin).

---

## Buy status

| Part | Status |
|------|--------|
| Housing / WT-43-RK / Minew / LiPo / charge | As `ORDERED_SO_FAR.md` |
| **SoftSIM A7672 carrier ×3** | **FIT LOCKED** — not this sample PO; buy after LoRa water test + custom carrier design (or Lucas LoRa+SoftSIM combo) |

Ask Lucas in parallel: SoftSIM onboard WT-43 vs our A7672 add-on (see `LORA_BOARD_FLAVOURS.md`).

**Optional UI (later):** RLCD back-lid screen (gate) + speaker + buttons under casing + LEDs → `OPTIONAL_PUCK_UI_SCREEN_BEEPS.md` · `DEEP_DIVE_RLCD_BACK_LID.md`

**Full housing fit (all parts):** → **`HOUSING_FIT_ALL.md`** — core + SoftSIM + RLCD options vs 71.8×50.8×33.6.
