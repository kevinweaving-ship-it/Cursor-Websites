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
| **AN54LQ-15** (nRF54; was E73) | **3** | Pucks only — **not** committee → **3 not 4**. E73 OOS → Raytac/TME primary |
| Flat LiPo + TP4056 | **4** | 3 pucks + committee → **4** |
| H9–13 GoPro housing | **3** | One shell per puck (or 3+1 spare later) |
| Survey antenna + pole | **1** | Committee only |
| IP67 dry box | **1** | Committee only |
| USB bank / UART bridge | **1** | Committee only |

## BLE MCU stock (E73 OOS)

ebyteiot **E73-2G4M08S1F sold out**. **Pay Tuesday primary:** Raytac **AN54LQ-15 ×3** on TME.

Full alt list: **`NRF54_ALT_SUPPLIERS.md`**

- **BUY:** https://www.tme.eu/en/details/an54l15q/iot-wifi-bluetooth-modules/raytac/an54lq-15/
- Backup: MinewSemi ME54BS62 · Fanstel BC15C
- Parallel only: Email `ebyteiot@cdebyte.com` — “E73-2G4M08S1F **×3**, lead time / backorder”
