# What costs what — priced line items (not guesses)

**FX locked:** **R16 / $1** · **Date:** 2026-09-06  
**Rule:** every total is the **sum of lines**. Housing is **never** inside the WT-43 price.

| Tag | Meaning |
|-----|---------|
| **LIVE** | Price seen on a cart / distributor page |
| **LIST** | Factory published range (ask to confirm) |
| **EST** | Typical Ali class — re-check before pay |

---

## Sourced parts (Puck)

| # | Part | Role | USD | Rand | Evidence |
|---|------|------|----:|-----:|----------|
| 1 | **WT-43-RK-LoRa** | GNSS + LoRa rover brick | **32.19–35.67** | **515–571** | **LIST** Anzewei/OTW factory: [gpsgnssmodule](https://www.gpsgnssmodule.com/sale-53628296-wt-43-rk-lora-rtk-gnss-module-with-lora-data-transmission.html) |
| 1b | same, Ali path | same | **54.17** | **867** | **LIVE** prior Ali 1–499 (do not use if factory quotes) |
| 2a | **Ebyte E73-2G4M08S1F** | nRF54L15 MCU+BLE module | **5.61–6.40** | **90–102** | **LIVE** [JLCPCB $5.61](https://jlcpcb.com/partdetail/57638535-E732G4M08S1F/C54337734) · [ebyteiot ~$6.40](https://ebyteiot.com/products/ebyte-e71-e73-series-soc-wireless-communication-module-low-power-2-4ghz-tl7215d-nrf54l15-chip-multi-protocol-8-10dbm-test-board) |
| 2b | **Ebyte E73-2G4M08S1C** | nRF52840 interim MCU (no CS) | **7.60** | **122** | **LIVE** [ebyteiot](https://ebyteiot.com/products/2-4ghz-ble-mesh-small-smd-e73-2g4m08s1c-nordic-nrf52840-module-small-size-ble-5-0) |
| 2c | **nRF54L15 DK** | Lab MCU only (won’t fit production sled) | **57.97** | **928** | **LIVE** [DigiKey](https://www.digikey.com/en/products/detail/nordic-semiconductor-asa/NRF54L15-DK/25601516) |
| 3 | LiPo cell + charge board | Power | **~3.70–6.10** | **59–98** | **LIVE-ish** Ali 1000 mAh ~$3.69 · 3000 mAh ~$5.09 + TP4056-class ~$1 |
| 4a | **H9–13 waterproof housing (China clone)** | Shell | **5.00–6.50** | **80–104** | **LIST** Made-in-China kitway **$5.85–6.50**; prior Ali class **$5–6** |
| 4b | **Official GoPro ADDIV-001** | Shell (do **not** buy for fleet) | **49.99–54.99** | **800–880** | **LIVE** GoPro / scuba.com / Backscatter |
| 5 | 3D sled + wire + passives | Fit / glue | **~2.50–5.50** | **40–88** | **EST** print + bits |

**Bow Tag (not inside puck):** nRF54L15 Tag **$31.16 → R499** DigiKey — optional OCS experiment only.

---

## Boat Puck — additive totals

### Path A — beta / volume intent (factory WT-43 + Ebyte nRF54 + Ali housing)

| Line | Low R | High R |
|------|------:|-------:|
| WT-43-RK factory | 515 | 571 |
| E73 nRF54L15 | 90 | 102 |
| Battery + charge | 59 | 98 |
| **Electronics subtotal** | **664** | **771** |
| + Ali H9–13 housing | 80 | 104 |
| + sled/passives (EST) | 40 | 88 |
| **Puck total Path A** | **784** | **963** |

Math check: 664+80+40 = **784**; 771+104+88 = **963**.

### Path B — same but interim nRF52840 module ($7.60)

| Line | Low R | High R |
|------|------:|-------:|
| Electronics (WT-43 + E73-52840 + batt) | 515+122+59 = **696** | 571+122+98 = **791** |
| + Ali housing + sled | +120 → **816** | +192 → **983** |

### Path C — if you pay Ali WT-43 ($54.17) instead of factory

| Line | Low R | High R |
|------|------:|-------:|
| Electronics (Ali WT-43 + nRF54 + batt) | 867+90+59 = **1 016** | 867+102+98 = **1 067** |
| + Ali housing + sled | **1 136** | **1 259** |

### Lab only (DK does **not** go in the GoPro)

| | R |
|--|--:|
| WT-43 factory + **DK $57.97** + batt | 515+928+59 → **1 502** to 571+928+98 → **1 597** |
| Housing still separate | +80–104 |

Do **not** quote DK as the “puck MCU cost”.

---

## What sits in the housing

```
Ali H9–13 case (~R80–104)     ← NOT included in WT-43
┌─────────────────────────────────────────┐
│  WT-43-RK (~R515–571 factory)           │  GNSS + LoRa
│  Ebyte nRF54 module (~R90–102)          │  brain + BLE
│  Flat LiPo + charge (~R59–98)            │  power
│  3D sled / wires (~R40–88 EST)          │  fit
└─────────────────────────────────────────┘
No screen. Watch/phone = BLE clients, separate.
```

---

## Committee boat — additive

| # | Part | Role | USD | Rand | Tag |
|---|------|------|----:|-----:|-----|
| 1 | **WT-43-BK-LoRa** | RTK **base** (only one) | **32.19–35.67** | **515–571** | **LIST** same factory family as RK |
| 1b | Ali BK (if used) | same | **~54** | **~867** | prior class |
| 2 | Survey / multi-band patch + pole | Better base antenna | **~15–40** | **240–640** | **EST** Ali survey patch + PVC pole |
| 3 | Dry box + battery (USB bank or 12 V) | Power / weather | **~10–30** | **160–480** | **EST** |
| 4 | USB-serial / Pi Zero-class | Host ↔ UART | **~5–15** | **80–240** | **EST** |
| 5 | Laptop / tablet | Race Control UI | — | **0** | bring existing |

| Build | Sum |
|-------|-----|
| **Minimum electronics** (factory BK only) | **R515–571** |
| **Working committee kit** (BK + antenna/pole + box/batt + bridge) | **515+240+160+80 = R995** low → **571+640+480+240 = R1 931** high |
| **If Ali BK** | add ~**R300** vs factory |

Committee is **not** a GoPro puck. Shell = dry box (**EST**), not ADDIV-001.

---

## Pin / mark pack (no sailor MCU)

| Line | R |
|------|--:|
| WT-43-RK factory | 515–571 |
| Battery + charge | 59–98 |
| Your float / clip box | 0–104 |
| **Pack** | **~R574–773** (+ box if bought) |

---

## Corrected one-liners (use these)

| Question | Answer |
|----------|--------|
| Electronics in one puck? | **~R664–771** (factory WT-43 + Ebyte nRF54 + battery) |
| + China GoPro-class housing? | **add R80–104** → **~R744–875** electronics+case, or **~R784–963** with sled |
| Official GoPro housing? | **~R800–880 alone** — skip for fleet |
| Committee working kit? | **~R1 000–1 900** (factory BK + antenna + box + bridge; laptop R0) |
| Was “650–950 then 750–1100” wrong? | **Yes** — those bands did not add; housing was double-counted / guessed |

---

## Still must confirm before money leaves

1. OTW email: BK + RK **1-pc USD**, SA **433 MHz** LoRa, Hz with RTCM.  
2. Live Ali cart for the exact H9–13 housing SKU (clone **~$5–6.50**, not official **~$55**).  
3. DigiKey/JLCPCB carts on the day you buy (FX and stock move).

Full cart sheet: [`FINAL_BETA_BUY_LIST_RAND.md`](FINAL_BETA_BUY_LIST_RAND.md) (update to match these sums).
