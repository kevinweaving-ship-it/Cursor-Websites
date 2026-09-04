# Alibaba GNSS listings — price / size / fit (2026-09-04)

User paste set. FX: **R16 / $1**. Alibaba bot-blocked most pages; **#3** parsed live; others from titles + public datasheets + typical China-board quotes. **Re-check live price before order.**

| # | Listing | Chip / product | Size | Price (est.) | Puck (≥50 Hz) | Committee base | Notes |
|---|---------|----------------|------|--------------|---------------|----------------|-------|
| 1 | [Fast Location GNSS](https://www.alibaba.com/product-detail/GNSS-Module-for-Fast-Location-GPS_1601181494368.html) | Consumer GPS class (title) | Often **~18×18 mm** module | Typical **~R80–130 ($5–8)** | **NO** | **NO** | Not dual-freq RTK. Skip. |
| 2 | [Quectel LC29H …](https://www.alibaba.com/product-detail/Quectel-LC29H-LC29HEA-LC29HAA-DA-BA_1601698659297.html) | **LC29H** AA/DA/BA/EA | Module **12.2×16 mm**; breakouts larger | Boards often **~R320–880 ($20–55)** | **NO** | Maybe cheap trial | DA = **1 Hz** RTK; EA ≤ **10 Hz**. Violates [`gnss-50hz-lock.md`](gnss-50hz-lock.md). |
| 3 | [High-precision RTK Board](https://www.alibaba.com/product-detail/The-High-precision-Rtk-Board-Is_1601283218477.html) | **OTW WT-43-RK-Lora** (chip “XX”) | **43×43×14 mm** | **R867 ($54.17)** (1–499) — **live** | **NO** (max **20 Hz**) | **Interesting** | Dual-freq RTK **+ LoRa on board**. L1+L5 class, 128 ch, 1–20 Hz. Good **cheap base experiment**, not race Puck. |
| 4 | [Quectel LC29H …](https://www.alibaba.com/product-detail/Quectel-LC29H-LC29HEA-LC29HAA-DA-BA_1601826296770.html) | **LC29H** (same family as #2) | Same as #2 | Same ballpark as #2 | **NO** | Maybe cheap trial | Duplicate chip family. Reject for Puck. |
| 5 | [UM982 / UM980 Base+Rover](https://www.alibaba.com/product-detail/UM982-UM980-Main-Base-Station-Rover_1601700100272.html) | **UM980 / UM982** | Chip **UM980 17×22 mm** / **UM982 16×21 mm**; common boards **~26×38 mm** | Bare/board China **~R960–2 880 ($60–180)**; EU breakout ~**R2 880 ($180)** | **YES — UM980** | **YES — prefer UM980** | **Best of this paste.** Confirm seller SKU is **UM980** and firmware **50 Hz**. UM982 = dual-antenna heading (≤20 Hz heading) — useful later, not required for Puck. |
| 6 | [For RTK GPS Base and Rover](https://www.alibaba.com/product-detail/For-Rtk-Gps-Base-and-Rover_1601051913317.html) | Unknown (title only) | Unknown | Unknown | **Unknown** | Unknown | Captcha; **do not buy** until chip + update rate confirmed in chat. |

---

## Verdict for Boat Puck

1. **Buy for Puck rover:** listing **#5** style — **UM980** board only. Verify **50 Hz** in message to seller before payment.
2. **Reject for Puck:** **#1, #2, #4** (and any LC29H). **#3** max 20 Hz — fail lock.
3. **#6:** hold until chip named.

## Committee boat = RTK **base**

Base does **not** need 50 Hz. Industry normal is **1 Hz** RTCM. Size less critical than on the Puck.

| Role | Recommended | Why |
|------|-------------|-----|
| **Race-grade base** | **UM980** (same as #5) | Same constellation/RTCM family as Puck; Unicore guidance often **UM980 base**, UM982 more rover/heading. |
| **Cheap integrated trial** | **#3 WT-43-RK-Lora** | **R867 ($54)**; GNSS+LoRa in one; 1–5 km LoRa claim. Fine for shore/committee experiments, not the long-term race stack. |
| **Avoid as primary base** | LC29H alone | Works for corrections in a pinch; weaker multi-freq / rate vs UM980. |

**Committee BOM (minimal):** UM980 board + survey antenna (or good patch) + LoRa radio (E22 class already on buy list) + 12 V / battery box on committee boat. Mount antenna high and clear of metal.

## Price snapshot (order of magnitude)

| Item | R | $ |
|------|---|---|
| #3 WT-43 (live) | **867** | **54.17** |
| LC29H board (#2/#4 typ.) | ~320–880 | ~20–55 |
| UM980/982 China board (#5 typ.) | ~960–2 880 | ~60–180 |
| gnss.store UM980 breakout (known) | ~2 720 | ~170 |

## Next buy message (paste to #5 seller)

> Need **UM980** (not UM960). Confirm: (1) all-constellation multi-freq RTK, (2) NMEA/RTCM out, (3) **position update rate 50 Hz** supported in firmware as shipped or with free upgrade, (4) board dimensions mm, (5) price 1 pc and 10 pcs USD, (6) can same board run as **base** (RTCM out) and **rover**.
