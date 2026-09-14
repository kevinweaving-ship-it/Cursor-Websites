# Initial hardware kit — counting rule (locked)

**Units:** **3× Pucks** + **1× Committee**

## Qty rule (no exceptions)

| Who needs the part? | Order qty |
|---------------------|----------:|
| Pucks only | **3** |
| Pucks **and** committee | **4** |
| Committee only | **1** |

Do **not** under-count to “boat only ×1”. If it goes in a puck, count **all 3 pucks**.

## Roles

| # | Role | Radio | Notes |
|---|------|-------|-------|
| C | Committee | **WT-43-BK ×1** | Dry box + line antenna + Race Control UI |
| P1 | Start pin (OCS) | **WT-43-RK** | Puck 1 |
| P2 | Boat (start / OCS) | **WT-43-RK** | Puck 2 |
| P3 | Mark / finish (dual) | **WT-43-RK** | Puck 3 |

## OTW

| Line | Qty | Why |
|------|----:|-----|
| WT-43-RK-LORA | **3** | One per puck |
| WT-43-BK-LORA | **1** | Committee only |
| **OTW $** | **3×40 + 55 = 175** | Live FX ≈ **R2 856** |

## Shared / puck electronics

| Part | Qty | Rule |
|------|----:|------|
| **ME54BS62** (nRF54; CURRENT) | **3** | Pucks only. Contact MinewSemi → PI to Eric Shenzhen. See `ORDER_ONE_STEP_AT_A_TIME.md` |
| Flat LiPo + TP4056 | **4** | 3 pucks + committee → **4** — **not this step** |
| SoftSIM LTE (A7672-class) | **3** | **Pucks only** — fit locked in leftover strip · buy later · `PUCK_STACK_WITH_SOFTSIM.md` |
| H9–13 GoPro housing | **3** | One shell per puck — **not this step** |
| Survey antenna + pole | **1** | Committee only — **not this step** |
| IP67 dry box | **1** | Committee only — **not this step** |
| USB bank / UART bridge | **1** | Committee only — **not this step** |

## BLE MCU — current step only

**One factory:** MinewSemi · **ME54BS62 ×3** · email `minewsemi@minew.com` · PI ship **Eric Shenzhen**.

Copy email + checklist: **`ORDER_ONE_STEP_AT_A_TIME.md`**  
Fallback queue only if Minew fails: **`NRF54_ALT_SUPPLIERS.md`**
