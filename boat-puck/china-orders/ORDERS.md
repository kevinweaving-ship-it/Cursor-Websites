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

Lucas range + 旗鱼 reply **sent**. **Seven answers in.** Battery **mA** still open.

| # | Ask | Lucas | Our read |
|---|-----|--------|----------|
| 1 | Open-water LoRa range | 1–3 km no interference; **on-site test** | Start line 100–150 m is fine. Fleet 2–5 km is at/above his claim — extra gateways still the plan |
| 2 | 868 MHz | No problem | OK |
| 3 | TX power | **22 dB** | **22 dBm** = 158 mW RF |
| 4 | Antenna | **FPC surface-mount** | Chip/FPC is weak for the **base** — pole/patch still worth adding |
| 5 | Data rate | **2.4 – 62.5k** | Assume kbps. RTCM can fit; higher rate = shorter range. Confirm units |
| 6 | Max rovers | “Range does not limit rover count” | Avoided airtime. **100+ still unproven** — duty cycle / collisions limit, not range |
| 7 | RTCM broadcast | **Yes**, no 1-to-1. Accuracy vs base–rover **distance** | Broadcast = what we need. Distance = **RTK baseline** (cm + ppm), not LoRa |

**Supply:** **3.3–6.5 V, typically 5 V**.

**Battery (still no mA from him):** 22 dBm = 158 mW RF. LoRa PA ~100–130 mA **on 3.3 V chip rail**. At **5 V** in (regulator to 3.3 V) radio TX is roughly **~80–100 mA** at the 5 V input if PA is ~0.4–0.5 W DC. GNSS/RTK on WT-43 is extra and likely larger. **Ask him to confirm or send actual TX/idle mA at 5 V.**

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
