# China order register

Updated **2026-09-15**. **Pay Moko + Dragino first** (they issue PI from this list). **Lucas follows.**

## Ship-to (all samples)

深圳市福田区华强北友谊路上步工业区404栋2楼212号  
吴建军 18680660780 kevin

## 1. SEND PI NOW — Moko

Qty: Dev list + Richard **20× LW014**. Band **EU868**. Draft: [`drafts/to-moko-pi.md`](drafts/to-moko-pi.md)

| Status | SKU | Qty | Notes |
|--------|-------|----:|-------|
| **SEND PI** | LW014 wearable / wrist | **20** | Richard 10 Sep. Store ~$52/pc list |
| **SEND PI** | LW013 smart button | **10** | Minimum 10 (was 1 sample) |
| **SEND PI** | LW006 smart badge | **4** | Dev |

**Not on PI:** LW010-CT (Kevin mentioned only).

## 2. SEND PI NOW — Dragino

Farming + one dev module. Band **EU868**, **-LB** LoRaWAN. Draft: [`drafts/to-dragino-pi.md`](drafts/to-dragino-pi.md)

| Status | SKU | Qty | Notes |
|--------|-------|----:|-------|
| **SEND PI** | WSC2-L weather station kit | 1 | Ask for full kit (not bare MPU only) |
| **SEND PI** | SE01-LB soil moisture & EC | 1 | Richard SE01 / SE OX |
| **SEND PI** | SPH01-LB soil pH | 1 | |
| **SEND PI** | S31B-LB outdoor T/H | 1 | Vineyard humidity. **Not** S31-CB (cellular) |
| **SEND PI** | LT-22222-L I/O | 1 | Valve + open/closed feedback |
| **SEND PI** | LA66 module | 1 | Develop |

## 3. FOLLOW — Lucas / OTW (do not PI yet)

| Status | SKU | Qty | Unit | Line | Notes |
|--------|-------|----:|-----:|-----:|-------|
| **FOLLOW** | WT-43-RK-LORA | 3 | $40 | **$120 (R1 920)** | 868 MHz rover |
| **FOLLOW** | WT-43-BK-LORA | 1 | $55 | **$55 (R880)** | Base |
| **HOLD** | Minew nRF54L15 DK | 1? | | | Team list; not Lucas |

Lucas range + 旗鱼 reply **sent**. He will answer the seven questions later.

| # | Ask | Status |
|---|-----|--------|
| 1 | Tested LoRa range over open water | waiting |
| 2 | 868 MHz band | waiting |
| 3 | Transmit power | **22 dB** (read as **22 dBm TX**, 15 Sep 13:04) |
| 4 | Antenna | waiting |
| 5 | Data rate | waiting |
| 6 | Max rovers per base | waiting |
| 7 | RTCM broadcast to all rovers | waiting |

Battery sizing still open: **22 dBm is RF output, not current draw.** Need TX mA and idle mA (and input voltage) to size the puck battery.

22 dBm ≈ **158 mW RF**. Radio-only ballpark ~100–130 mA @ 3.3 V while TX. WT-43 GNSS is extra. **Cannot size the pack from 22 dB alone.**

Follow-up: [`drafts/to-lucas-battery-ma.md`](drafts/to-lucas-battery-ma.md)

## Google Sheet — rows this session

Copy from [`sheet.csv`](sheet.csv).

| Action | Supplier | SKU | Qty | Status |
|--------|----------|-----|----:|--------|
| **ADD** | Moko | LW014 EU868 | 20 | SEND PI |
| **ADD** | Moko | LW013 EU868 | 10 | SEND PI |
| **ADD** | Moko | LW006 EU868 | 4 | SEND PI |
| **ADD** | Dragino | WSC2-L kit EU868 | 1 | SEND PI |
| **ADD** | Dragino | SE01-LB EU868 | 1 | SEND PI |
| **ADD** | Dragino | SPH01-LB EU868 | 1 | SEND PI |
| **ADD** | Dragino | S31B-LB EU868 | 1 | SEND PI (not CB) |
| **ADD** | Dragino | LT-22222-L EU868 | 1 | SEND PI |
| **ADD** | Dragino | LA66 EU868 | 1 | SEND PI |
| **KEEP** | OTW | WT-43-RK-LORA | 3 | FOLLOW — no PI |
| **KEEP** | OTW | WT-43-BK-LORA | 1 | FOLLOW — no PI |
