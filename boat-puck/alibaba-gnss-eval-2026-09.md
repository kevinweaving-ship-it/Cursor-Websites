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

---

## Paste add-on (2026-09-04 b)

| Listing | Chip | Size | Price | Verdict |
|---------|------|------|-------|---------|
| [LD-29 Dual Band RTK](https://www.alibaba.com/product-detail/LD-29-Dual-Band-RTK-Module_1601753812357.html) | **AK721-JM** / Dalang L1+L5 (not Unicore) | **⌀36 × 11.7 mm** | Retail twin **~$19** → **~R304**; Ali ask live | **NO for Puck** — **1–10 Hz** only. Possible cheap base trial. |
| [LC29H GPS HAT (Pi)](https://www.alibaba.com/product-detail/LC29H-GPS-HAT-for-Raspberry-Pi_1601810249713.html) | **Quectel LC29H** (Waveshare-class HAT) | Pi HAT footprint (~**65×56 mm** typ.) | Waveshare DA **R880 ($54.99)** | **NO for Puck** — DA **1 Hz** RTK. Lab/Pi only. |

---

## UM980 — factory + buy URLs (price)

| Role | URL | Price |
|------|-----|-------|
| **Factory (Unicore)** — datasheet/OEM, no public cart | https://www.unicore.com/products/detail/27 | Quote via Unicore |
| EN docs / manuals | https://en.unicore.com (UM980 product + PDFs) | — |
| **Ali buy (module)** — typical | https://www.alibaba.com/product-detail/UM980-RTK-Positioning-GNSS-Rtk-Gps_1601399905021.html | **~$99–130** → **R1 584–2 080** (sample ~$130 / R2 080) |
| **Ali buy (board / EVK base)** | https://www.alibaba.com/product-detail/Unicorecomm-UM980-GNSS-RTK-Board-Base_1601135459180.html | **~£128** (~**$165 / R2 640**) @ 1–49; lower in volume |
| Known EU breakout (not factory) | https://gnss.store/products/elt0223 | **~R2 720 ($170)** |

Chip size: **17×22×2.6 mm**. Common China PCB breakouts: **~26×38 mm**. Always confirm **50 Hz** before pay.

---

## Paste add-on — JS-ATP38-M

| Listing | Chip / product | Size | Price | Verdict |
|---------|----------------|------|-------|---------|
| [JS-ATP38-M Advanced RTK Anti…](https://www.alibaba.com/product-detail/JS-ATP38-M-Advanced-RTK-Anti_1601675645621.html) | **Jumpstar JS-ATP38-M** L1+L5 antenna module | **~38×38×11.5 mm** (factory: 38×11.5 mm class) | Ali live unknown; class typically **~R128–400 ($8–25)** | **NO** |

**Factory:** https://www.jumpstargnss.com/standard-precision--antenna-modules/js-atp38-m.html  

- Category: **standard precision** (not RTK cm board)  
- Accuracy: **1.0 m** horiz (L1+L5) / 2.5 m (L1)  
- Rate: **max 10 Hz** (default 1 Hz)  
- “RTK / Anti” in Ali title = marketing; not UM980-class RTK  

Skip for Puck and for committee RTK base.

---

## Paste add-on — Archinno GeoPod Mini (short link)

Short URL https://www.alibaba.com/x/1lBAubT?ck=pdp →  
https://www.alibaba.com/product-detail/Archinno-GeoPod-Mini-RTK-GNSS-Rover_1601827597937.html  

| | |
|--|--|
| Product | **Archinno / A&I GeoPOD Mini** handheld RTK rover |
| Factory | https://archi-inno.com/geopod/ · [datasheet PDF](https://archi-inno.com/wp-content/uploads/2025/03/GeoPOD-Datasheet.pdf) |
| Chip class | **1408 ch** full multi-freq (UM980-class engine) |
| Rate | **20 Hz max** |
| Size / mass | **⌀47 × 140 mm**, **200 g** capsule |
| I/O | BLE 5.3 + Type-C; phone app (not embed module) |
| Acc. | RTK H ±(8+1ppm) mm; tilt IMU to 90° |
| Price | Ali live **ask seller** (captcha); quote-only on maker site |

**Verdict:** **NO for Puck** — finished survey stick, not a board; **20 Hz** fails [`gnss-50hz-lock.md`](gnss-50hz-lock.md); too big for GoPro. Possible **field trial / committee handheld** only — prefer bare **UM980 board** for race stack.

---

## Paste add-on — XM30R RTK handheld (short link)

Short URL https://www.alibaba.com/x/1lBAuFh?ck=pdp →  
https://www.alibaba.com/product-detail/subject_1601934271030.html  
(productId **1601934271030**)

| | |
|--|--|
| Product | **XM30R** RTK GNSS handheld / **4G LTE PoC intercom** + rugged camera |
| Seller | Shanghai Xilin Import And Export Co., Ltd. |
| Price (live share) | **R2 885–3 211** (~**$180–201**) · MOQ 1 |
| Form | Android **14** brick · **3.0"** IPS · UIS7863 · 4+64 · IP68 · 5000 mAh hot-swap |
| GNSS claim | “cm RTK” / &lt;10 cm · multi-constellation — **chip + Hz not stated** |
| Other | 4G PoC walkie, dual cameras, IR, SOS — bodycam/survey terminal |

**Verdict:** **NO — skip.** Same class as LTE “RTK intercom” walkies: finished Android radio, not embeddable guts. Paying ~R3 200 for a shell you would gut is waste. Do **not** ask for guts (custom mainboard + SoC); if they sell a bare GNSS module, that would be a different SKU — still need **UM980 + 50 Hz** proof. Prefer [`gnss.store` UM980](https://gnss.store/products/elt0223) / Ali UM980 boards.

---

## Paste add-on — SIYI / “RTK” ArduPilot puck (short link)

Short URL https://www.alibaba.com/x/1lBAuiT?ck=pdp →  
https://www.alibaba.com/product-detail/subject_10000041644207.html  
(productId **10000041644207**)

| | |
|--|--|
| Listing title | “Portable RTK GPS Receiver…” (~**R1 076 / ~$67**) |
| On-device / graphic | **SIYI** · **M9N** · ArduPilot / PX4 drone GPS puck |
| Seller | Shenzhen Dianju IoT Innovation Technology Co. |
| Real class | **u-blox M9N** family — meter-level GNSS for drones, **not** cm RTK |
| Rate | M9N class typically **≤25 Hz** (often lower concurrent) — **fails 50 Hz lock** |
| Form | Finished Ø~60–80 mm puck + optional handheld in hero shot |

**Verdict:** **NO — skip.** Title says RTK; product is **M9N drone GPS**. Wrong accuracy class and wrong rate. Do not buy or ask for guts (you already know the chip). Stay on **UM980**.

---

## Paste add-on — HighGain UM980 / UM982 / F9P kit boards

Short URL https://www.alibaba.com/x/1lBAuXL?ck=pdp → product **1601932849835** (captcha; ID from redirect).  
Screenshots: High Gain multi-band RTK modules.

| | |
|--|--|
| Seller | Shanghai HighGain Information Technology |
| Price | **R1 141–1 939** (~**$71–121**) |
| MOQ | **50 pcs** — pain for first proto |
| SKUs shown | **UM980** · **UM982** · **u-blox ZED-F9P** |
| Spec text | 1408 ch · RTK 0.8 cm+1 ppm · rates **10/20 Hz**, firmware **up to 50 Hz** |
| Board size | **71 × 46 × 12 mm** · MMCX · multi UART 3.3 V |

**Verdict:** **YES — look / ask** — but only the **UM980** SKU.

| SKU | Puck? | Notes |
|-----|-------|-------|
| **UM980** | **Maybe** | Right chip class; **confirm 50 Hz FW as shipped**; size **71×46** is **big** vs gnss.store ~26×39 — may **not fit** GoPro cavity |
| UM982 | Later / no | Dual-antenna heading; not required for Puck |
| ZED-F9P | **NO** | Typically **≤20 Hz** RTK — fails 50 Hz lock |

**Ask (paste):**

> Need **UM980 only** (not UM982 / not F9P). Confirm: (1) firmware **50 Hz** position out as shipped or free upgrade, (2) exact board mm (is 71×46 the only size? any smaller breakout?), (3) NMEA + RTCM base/rover, (4) **sample 1–2 pcs** price despite MOQ 50, (5) 10-pc and 50-pc USD.

Prefer **1-pc** path if they refuse samples: [gnss.store ELT0223](https://gnss.store/products/elt0223) (~R2 720) until HighGain quotes samples + smaller board.

---

## Paste add-on — WES WE-T350 “card fusion” UWB / RTK tag

Screenshots (Meshtastic search → WES badge). Model **WE-T350**.

| | |
|--|--|
| Form | Finished ID-card tag **105 × 62.2 × 9.8 mm** · lanyard loop · magnetic charge |
| Stack | **UWB** (802.15.4z) + BLE 5.1 + optional **CAT1 / LoRa** (470–510 MHz) + RFID + e-ink + voice |
| GNSS (optional) | L1+L5 class (GPS L1/L5, Galileo E1/E5a, BDS B1I/B2a…) · claim RTK **1 cm+1 ppm** — **chip not named** |
| Rate | Spec table **refresh 0.1–20 Hz** — **fails 50 Hz lock** |
| Use | Indoor UWB 0D/1D presence / tunnel tags — personnel asset tracking |

**Verdict:** **NO — skip.** Wrong product class (UWB badge + optional dual-band GNSS). Max **20 Hz**, not UM980 guts, not GoPro-fit. Do **not** ask for guts.

**Factory check (海南世电 / WEST-HN / WES):** public store https://store.west-hn.com — **WE-T350 not listed**. Sibling UWB tags (WE-T241-C, WE-T311, WE-UG230, WE-T206-H) all publish **刷新率 0.1~20 Hz**. No factory datasheet found with ≥50 Hz GNSS. Asking OEM for “higher Hz” is unlikely to help the Puck path.

