# China beta sourcing — deep dive (products you may have missed)

**Date:** 2026-09-06 · **FX guide:** R16 / $1  
**Lens:** beta in **your own box** (IP/form secondary). Care about: cheap · OTS · RTK FIX · corrections without race-day cell · UART/NMEA we can own · roles (committee / pin / mark / finish / boat / big-boat UI).

**Companion buys:** [`puck-components-buy-list.md`](puck-components-buy-list.md) · [`factory-buy-narrow-2026-09.md`](factory-buy-narrow-2026-09.md) · [`alibaba-gnss-eval-2026-09.md`](alibaba-gnss-eval-2026-09.md) · [`DEV_DIRECTION_2026-09_to_Shenzhen_2027-04.md`](DEV_DIRECTION_2026-09_to_Shenzhen_2027-04.md)

---

## 0. What you already surfaced (baseline)

| Item | ~R | Note |
|------|---:|------|
| OTW **WT-43-RK / BK-LoRa** | 850–900 | Still the best integrated RTK+LoRa brick |
| Minewsemi **GE3PGS51** handheld | 2 445 | L1+L5 terminal |
| **XM30R** Android RTK | 3 211 | Survey / helm handset |
| Huaxing **RTK+LoRa+UWB+4G** SOS | 3 342 | Only finished box with LoRa+RTK together |
| KKM **nRF54L** iBeacon | 163 | BLE toy, not Channel Sounding kit |
| Unicore **UM980/982** boards | 960–2 720 | Fallback GNSS |
| Ebyte **E22** LoRa / **E73** nRF52 | ~100 / ~120 | Discrete radio/MCU |

**Verdict unchanged at the top:** no secret finished puck beats WT-43 on price+integration. The rest of this doc is **parallel experiments and OEMs you under-weighted**.

---

## 1. Critical band note (SA) — often wrong in Ali kits

| Band | SA beta? | Why |
|------|----------|-----|
| **433 MHz** (410–434 class) | **Yes — prefer** | Region-1 ISM / SRD; ICASA licence-exempt with power/duty limits |
| **863–870 MHz** (EU LoRa) | **Possible** (SRD) | Aligns with ETSI-style SRD; still needs ICASA type-approval discipline |
| **902–928 MHz** (US) | **No** | Not SA LoRa default |

**OTW WT-43 LoRa is 410–525 MHz** (factory pages) → can sit on **433** — *better* for SA than DFRobot EU 868 / US 915 kits.

**DIY LoRa for SA:** prefer **Ebyte E22-400M22S** (SX1268, **410–493 MHz**, ~**$4–7 / R64–112**) over E22-900 for local water tests. Keep E22-900 only if you deliberately run EU 868.

---

## 2. Same factory family — full OTW / Anzewei catalogue (missed siblings)

Factory store (EN): https://www.ontheway-tech.com/product-category/rtk-development-board/  
(Also branded Anze / 安泽微.)

| SKU | What | Why it matters | Buy? |
|-----|------|----------------|------|
| **WT-43-RK-LoRa** | Dual-freq RTK + LoRa + antenna class, ~43×43, **1–20 Hz** | Primary rover | **Yes — core** |
| **WT-43-BK-LoRa** | Matching **base** | Committee RTCM | **Yes — core** |
| **WT-43-RK-4G** | Same idea + **cellular** | Backup NTRIP / shore only — not race-critical | Optional 1× |
| **WT-4545-RK** | Dual-freq RTK **no LoRa**, compass, **1–10 Hz**, ~47×36 mm | Pair with E22-400 for SA DIY; smaller BOM experiment | **Strong missable** |
| **WT-43-62-RK** | RTK board sibling | Ask catalogue price/Hz | RFQ |
| **WT-27-HP** | Multi-system high-precision module | Possible smaller GNSS-only brick | RFQ |
| **WTB-2526-62-RD** | Dev / DR board | Lab only | Skip fleet |
| **WT-62-RD** | Inertial / dead-reckon flavoured GNSS | Interesting if IMU fusion on-module | Lab |
| **ZED-F9P-01B-00** | They list **u-blox F9P** | Useful if you want Western chip + China seller; dearer | Optional ref |

**Email once (paste):** Lucaszhang@ontheway-tech.com (confirm on reply)

> Quote 1-pc and 10-pc USD for: WT-43-RK-LoRa, WT-43-BK-LoRa, WT-4545-RK, WT-43-RK-4G, WT-27-HP, WT-43-62-RK.  
> Confirm: LoRa **centre freq options for South Africa 433 MHz**, max Hz while RTK FIX + LoRa RTCM active, NMEA sample, chipset inside, antenna type, base+rover pairing.

---

## 3. Quectel stack (you had LC29H — missed the better sibling)

| Product | Link / class | ~price | Role | Verdict |
|---------|--------------|-------:|------|---------|
| **LC29H** (DA/EA/BA…) | Ali boards; Waveshare HAT | Module few $–$65; boards **~$50–80 (R800–1 280)** | Cheap L1+L5 RTK DIY | **Learn only** — DA **1 Hz**; EA ≤**10 Hz**; not OCS gun |
| **DFRobot LC29H + LoRa kit** | dfrobot.com 2970/2971 | Kit **~$150–250 (R2.4–4k)** | Pre-paired base+rover | Band often **868/915** — **wrong for SA** unless you swap radios; 1 Hz |
| **LG290P** (quad-band L1/L2/L5/E6) | https://www.quectel.com/product/gnss-lg290p/ · SparkFun ~$120 · disti **~$50–76** | Module **~$50–120 (R800–1 920)** | **Best Quectel you likely missed** — RTK to **20 Hz**, anti-jam NIC, RTK HOLD | **Strong DIY parallel** if WT-43 rate/FIX disappoints; still need own LoRa |

**Why LG290P matters:** sits between LC29H toys and UM980 money; 20 Hz matches WT-43 class; China OEM with Western disti docs.

---

## 4. Unicore family — beyond UM980/982

| SKU | What | ~price | Missable angle |
|-----|------|-------:|----------------|
| **UM980** | All-constellation multi-freq RTK, **50 Hz** class | Board **~$60–170 (R960–2 720)** | Locked fallback / race-rate benchmark |
| **UM982** | Dual-antenna **heading** + RTK | **~$80–175** | Committee bow / keelboat Gilbert |
| **UM981 / UM981S** | RTK + **INS** on module; high rate claims | RFQ / mower boards | Survives brief GNSS outage under boom/spar |
| **UM981 + ESP32 + LoRa** AGV/mower PCB | https://www.alibaba.com/product-detail/high-precision-RTK-customized-product-unicore_1601333781946.html | Often **~$80–200** | Closest Ali “dev puck”: GNSS+MCU+LoRa one board — ask UART NMEA, does LoRa carry RTCM?, Hz, **433 vs 868** |
| **UM960 / lower** | Cheaper Unicore | lower | Only if seller confirms RTK + rate |

---

## 5. Other Chinese GNSS OEMs (usually missed vs Unicore/Quectel)

### ComNav / SinoGNSS (司南) — *only major brand with own boards*

| Product | Size / claim | ~price | Verdict |
|---------|--------------|-------:|---------|
| **K803** | **30×30 mm**, triple-freq + IMU | EVK ~**$500+ (R8k)** | Too dear for beta fleet; note existence for Apr 2027 OEM talk |
| **K700** | Entry OEM, ≤**20 Hz** RTK | RFQ | Skip vs UM980/WT-43 |

https://www.comnavtech.com/product/oem/k803.html

### Bynav (北云)

| Product | Note | ~price | Verdict |
|---------|------|-------:|---------|
| **C1** dual-ant RTK+heading | 71×46 mm class, own ASIC | List/disti ~**$140–250 (R2.2–4k)** | Committee / big-boat heading ref — not dinghy puck |
| **C2 / M20** series | Automotive-grade Alice SoC | RFQ | Overkill |

https://www.bynav.com/en/products/gnss-boards/c1.html

### Allystar (深圳盟升)

| Product | Note | ~price | Verdict |
|---------|------|-------:|---------|
| **TAU1302** (HD9310) | Dual-band RTK module **12×16 mm** | Module/EVK often **tens–low hundreds $** | Cheap China SoC path; less community than Unicore — **lab curiosity** |
| TAU12xx consumer | Not RTK-grade | cheap | Skip |

https://www.allystar.com/

### SkyTraq / NavSpark (Taiwan, Ali-adjacent)

| Product | Note | ~price | Verdict |
|---------|------|-------:|---------|
| **PX1125R** breakout (NS-HP-GN5) | L1+L5 RTK, tiny | Breakout **~$32**; EVB **~$60** | Cheapest “known good” dual-band RTK DIY after LC29H |
| **PX1172RH** | L1/L2 position + **heading** | Module **~$112** | Heading on a budget |

https://navspark.mybigcommerce.com/

### CHCNAV / Hi-Target / FOIF finished sticks

Almost always **UM980 (or Trimble) inside** + UHF + IMU + Android. **$2k–7k**. Buy **zero** for fleet. Optional **1× teardown** only if you want survey UX — XM30R/Minewsemi already cover that cheaper.

---

## 6. Ready “drone RTK” kits (China retail — easy UART)

| Product | Link | ~price | Why missed | Verdict |
|---------|------|-------:|------------|---------|
| **Holybro H-RTK Unicore UM982** | https://holybro.com/products/h-rtk-unicore-um982 | **~$250 (R4 000)** | Dual helical antennas, USB, docs, can base or heading | **Best “plug USB and see heading” kit** — not cheapest |
| Holybro F9P Base/Rover | holybro.com H-RTK | **~$190–260** | Western chip, good docs | Ref only; dearer than China UM980 board |
| SIYI / Cubepilot Here-class | Ali drone RTK | varies | Often sealed telemetry stacks | Skip unless you strip to UART |

---

## 7. Radio / MCU missables

| Product | Link | ~price | Why |
|---------|------|-------:|-----|
| **Ebyte E22-400M22S** | https://ebyteiot.com / LCSC | **~$4–7 (R64–112)** | **SA 433 LoRa** for DIY UM980/LC29H/LG290P |
| **Ebyte E22-900M22S** | already on buy list | **~$6 (R96)** | EU 868 — secondary for SA |
| **Ebyte E73-2G4M08S1F** (nRF54L15) | https://www.cdebyte.com/products/E73-2G4M08S1F | few–tens $ | China **nRF54L15** module for puck MCU |
| **Ebyte E73-2G4M08S1F / E73 nRF54L15 family** | cdebyte / ebyteiot | ~**$5–15** | Volume proto cheaper than Nordic DK×N |
| **Ebyte E73-2G4M08S1C** (nRF52840) | already listed | **$7.60 (R122)** | Fine if CS not needed yet |
| Nordic **nRF54L15 DK + Tag** | DigiKey/Mouser | Tag ~**$30–35 (R480–560)** | Still best for **bow Channel Sounding** |
| Chinese **UHF 410–470 MHz** “Trimtalk” 1–2 W survey radios | Ali “RTK radio” | **~$50–150 (R800–2 400)** | Longer range than LoRa for **committee↔marks** if LoRa dies at 2–3 km |
| True Trimble TDL450 clones | Ali | **thousands $** | Skip — buy generic UHF modem class instead |

---

## 8. Antennas (easy to under-buy)

| Class | ~R | Note |
|------|---:|------|
| Helical L1+L5 / multi-band (Holybro / Ali) | 150–400 | Boat/rover — height + view of sky beats fancy chip |
| Survey choke / geodetic | 800–3 000 | Committee base only |
| Jumpstar **JS-ATP38-M** style “RTK” patches | 128–400 | Often **metre-class** modules mis-titled — read datasheet |

---

## 9. Finished survey / weird boxes (fleet = no)

| Product | ~R | Keep? |
|---------|---:|-------|
| XM30R Android RTK | 3 211 | **1×** UI / survey |
| Minewsemi GE3PGS51 | 2 445 | **1×** survey |
| Huaxing RTK+LoRa+UWB+4G | 3 342 | **1× teardown** if LoRa=RTCM |
| Archinno GeoPod Mini | RFQ | No — 20 Hz capsule |
| AlphaGEO / Matrix Ultra | thousands $ | No |
| KKM nRF54 iBeacon | 163 | Curiosity only |

---

## 10. Role matrix (beta) — updated with missables

| Role | Primary buy | Strong alt you may have missed | Avoid as fleet |
|------|-------------|-------------------------------|----------------|
| **Committee corrections** | WT-43-BK | UM980/LG290P **base** + **E22-400**; or **1×** Huaxing LoRa+RTK teardown | XM30R as only base |
| **Committee / big-boat UI** | Tablet + BLE | XM30R rugged Android; Holybro UM982 heading | Multiplying handhelds |
| **Start pin** | WT-43-RK | WT-4545-RK + E22-400; LC29H/LG290P rover + LoRa | BLE beacons |
| **Marks / finish** | WT-43-RK | Same; DFRobot kit **only if** band fixed | UWB bricks |
| **Boat puck** | WT-43-RK + nRF54L15 | UM980 or **LG290P** + E22-400 + Ebyte nRF54 | Handhelds |
| **Bow experiment** | Nordic Tag | Ebyte nRF54 module | KKM iBeacon-only |
| **Survey stick** | Minewsemi / XM30R **1×** | — | CHCNAV full kits |

---

## 11. Accuracy vs Vakaros (keep straight)

| System | Typical claim |
|--------|----------------|
| Atlas 2 / RaceSense DGNSS | **~25 cm** (RTDGNSS ~15 cm) |
| Atlas + HALO RTK | **~1 cm** |
| WT-43 / UM980 datasheet RTK | **~1 cm + 1 ppm** |
| LG290P RTK | **~0.8 cm + 1 ppm** class @ ≤20 Hz |
| LC29H RTK | **~cm** (kits often 1 Hz) |
| XM30R marketing | **&lt;10 cm** |
| Lipton OCS knife-edge | **0.1–0.5 m** → need true RTK, not phone GPS |

---

## 12. Recommended China beta cart (missed items included)

**Minimum (still best):**
1. WT-43-BK ×1  
2. WT-43-RK ×2–3  
3. nRF54L15 DK or Ebyte nRF54 module ×2  
4. Your waterproof boxes + 5 V packs  

**~R2.6–4k core.**

**Add if budget for learning (pick ≤2):**
- **Quectel LG290P** board ×1–2 + **E22-400** ×2 — best missed DIY dual/quad-band parallel  
- **WT-4545-RK** ×1 + E22-400 — OTW GNSS-only + SA LoRa  
- **UM981+ESP32+LoRa** mower board ×1 — closest single-PCB “puck-ish” Ali experiment  
- **UM982** or **Holybro UM982** ×1 — heading  
- **Huaxing RTK+LoRa** ×1 — teardown only  
- **SkyTraq PX1125R** breakout ×2 — cheapest known dual-band pair  
- **XM30R or Minewsemi** ×1 — survey / UI toy  

**Do not open a second fleet architecture** until WT-43 path is measured on water (FIX %, Hz, LoRa RTCM latency, range).

---

## 13. Scorecard — “secret better than WT-43?”

| Candidate | Cheaper? | Integrated LoRa? | SA band? | OCS-useful rate? | Beat WT-43 as finished puck? |
|-----------|----------|------------------|----------|------------------|------------------------------|
| WT-43-RK/BK | baseline | **Yes** | **410–525 → 433 OK** | ≤20 Hz | **Reference** |
| WT-4545 + E22-400 | maybe | DIY | Yes | ≤10 Hz | No — more work |
| LC29H + LoRa | yes | kit/DIY | often **no** | 1–10 Hz | No |
| LG290P + E22-400 | similar/less | DIY | Yes if E22-400 | ≤20 Hz | No — more work |
| UM980 + E22 | dearer GNSS | DIY | Yes | **25–50 Hz** | Rate win only if you need it |
| UM981 mower board | maybe | **claim Yes** | **ask** | ask | **Only if** LoRa=RTCM + UART proven |
| Huaxing finished | no | claim Yes | ask | ask | Teardown only |
| Holybro UM982 | no | no | n/a | ≤20 Hz | Heading kit |
| ComNav K803 | no | no | n/a | high | Too expensive |
| Bynav C1 | no | no | n/a | ≤10 Hz | Heading OEM |

---

## 14. Second + third hunt (adversarial) — 2026-09-06

Two independent agent passes forced to find **cheaper or better than WT-43**, not re-list known items.

### What still does **not** exist in this tier
- Non-OTW **RTK + LoRa** brick **under ~$40–50**
- **≥25 Hz RTK + LoRa under ~$80**
- Honest under-$35 “WT-43 clone” from another factory with live cart price

### NEW names from those hunts (not in your earlier paste set)

| Product | ~USD | vs WT-43 | Action |
|---------|-----:|----------|--------|
| **OTW factory WT-43** ([gpsgnssmodule](https://www.gpsgnssmodule.com/sale-53628296-wt-43-rk-lora-rtk-gnss-module-with-lora-data-transmission.html)) | **$32–36** | Same product, **cheaper than Ali ~$54** | **Buy factory-direct** |
| **Dalang AK721-JM / LD-29** | **$19–38** | Cheaper GNSS; **no LoRa**; ≤10 Hz | Bench 1× only |
| **Beitian BT-M002C** | **$50–57** | Similar $; compass; **no LoRa**; **1 Hz** | Optional rover GNSS |
| **Quectel LC29H(DA) bare** (JLCPCB etc.) | **$20–27** | Cheapest dual-band RTK die; **1 Hz**; no radio | Custom PCB only |
| **LOCOSYS RTK-1010** | **$43–100** | Clean L1+L5 SMD; ≤10 Hz; no LoRa | Distro DIY |
| **Unicore UM960** board/module | **$35–70** | Multi-freq **20 Hz**; better FIX class; no LoRa | DIY + E22-400 |
| **Telit SE868K5-RTK** bare | **~$30** | Cheap RTK chip; ≤10 Hz; no radio | Custom PCB |
| **华云时空 Huayuen HY-SA100-9R** | **Quote** | **Full-freq + integrated LoRa** + real antenna Ø~120 mm | **RFQ — best “better integrated” lead** |
| **海导 Haidao T62** | Quote | Full-freq + heading + LoRa/LTE; Ø~122 mm | RFQ if size OK |
| **天禾 Tianhe THAM06** | Quote | Tri-band RTK + LoRa antenna terminal Ø~120 | RFQ |
| **Tianhe TH1100** | **~$20** | Cheap raw/PVT; RTK needs external SDK | Skip beta |
| **OTW ZED-F9P + LoRa** | **~$120** | Better chip + LoRa | Skip — 2×+ WT-43 |
| **WitMotion WTRTK-M10 + LoRa** | **~$129** | Better engine + LoRa | Skip — 3× |

### Closest ways to undercut WT-43
1. **Same brick cheaper:** factory WT-43 **$32–36** (not Ali R867).  
2. **DIY undercut:** LD-29 / Beitian / UM960 / LC29H + **E22-400** — only cheaper if you own antenna + RF work.  
3. **Better-but-bigger:** Huayuen / Haidao / Tianhe Ø12 cm LoRa terminals — RFQ; not dinghy-puck shaped.

---

## 15. One-line conclusion

No second factory sells a **cheaper integrated RTK+LoRa puck** than WT-43. Real levers: **buy WT-43 factory-direct ($32–36)**, **DIY GNSS+E22-400 undercut**, or **RFQ Huayuen/Haidao/Tianhe** for a better antenna/FIX terminal that is not puck-sized.
