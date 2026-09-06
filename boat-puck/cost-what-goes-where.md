# What costs what — Puck vs Committee (plain English)

**FX:** R16 / $1 · Guide 1-pc prices · Re-check before pay.

---

## The one idea

| Box | Job in one line |
|-----|-----------------|
| **Committee** | “Here is the centimetre-truth” — broadcasts corrections so everyone else can FIX |
| **Boat Puck** | “Here I am” — centimetre position on the boat, talks to Race Control, talks BLE to watch/phone |
| **Pin / mark packs** | Same GNSS+LoRa brick as the puck guts, **without** sailor MCU/BLE — just “here is this mark/pin” |

There is **only one base** (committee). Everything else is a **rover**.

---

## What each component *does*

| Part | What it is | What it does |
|------|------------|--------------|
| **WT-43-BK-LoRa** | GNSS + antenna + LoRa brick in **base** firmware | Sits on committee; computes corrections (**RTCM**) and **broadcasts them over LoRa** |
| **WT-43-RK-LoRa** | Same hardware family in **rover** firmware | Receives RTCM over LoRa → gets **cm FIX** → outputs position (NMEA/UART) |
| **LoRa (on the WT-43)** | Long-range radio built into the brick | Carries corrections (and later boat/mark positions). **Not** Wi‑Fi / not cell |
| **nRF54L15 (MCU)** | Small computer + Bluetooth 6 | Boat ID, race logic, OCS math, store/backfill, **BLE** to watch/phone/screen. Optional later: Channel Sounding to a bow tag |
| **IMU** | Motion sensor (on Tag / later on PCB) | Heading / heel / bow lever-arm for OCS |
| **Battery** | USB pack or LiPo | Powers the guts |
| **Housing** | Waterproof shell | Keeps water out. **Not** sold as part of the WT-43 — you buy or bring it |
| **Laptop/tablet** | Race Control host | Start sequence, line, OCS list, maps — **software**, not inside the puck |
| **Survey antenna + pole** (committee) | Better GPS antenna up high | Makes the **base** more accurate/stable than the tiny brick antenna alone |
| **Bow Tag** (optional experiment) | Tiny nRF54 Tag at the bow | Measures puck→bow distance for sharper OCS — **not** required for first water test |

---

## A) Boat Puck — what goes *inside* the housing

**Product shell (target):** GoPro H9–13 style waterproof case (~**R80–150** Ali clone).  
**Beta:** your own waterproof box is fine — housing is **extra**, not inside the WT-43 price.

```
┌──────── GoPro / your box (housing) ────────┐
│                                            │
│   ┌─ WT-43-RK-LoRa ─────────────────────┐  │
│   │  • GPS/RTK chip                      │  │
│   │  • onboard GNSS antenna (sky face)   │  │
│   │  • LoRa radio + antenna              │  │
│   └────────────── UART to MCU ───────────┘  │
│                                            │
│   ┌─ nRF54L15 (module or DK for proto) ─┐  │
│   │  • brain + BLE to watch/phone        │  │
│   └──────────────────────────────────────┘  │
│                                            │
│   Battery (power bank / LiPo)              │
│   (Later production: IMU on same PCB)      │
│                                            │
│   NO screen inside the Universal Puck      │
└────────────────────────────────────────────┘
```

| Piece inside puck | Included in WT-43 buy? | ~R |
|-------------------|------------------------|---:|
| WT-43-RK-LoRa (GNSS+LoRa brick) | **Yes — this is the buy** | **512–576** factory (Ali ~850–900) |
| nRF54 MCU | Separate | **80–240** Ebyte / **480–560** Nordic DK |
| Battery | Separate | **50–150** |
| GoPro-class housing | Separate | **80–150** (or **R0** if you use your box) |
| Screen / watch | **Not in puck** | optional BLE client |

### Puck cost (one racing boat)

| Build | What’s in it | ~R |
|-------|--------------|---:|
| **Electronics only** | WT-43-RK + cheap Ebyte nRF54 + battery | **~650–950** |
| **With GoPro housing** | above + case | **~750–1 100** |
| **Proto with Nordic DK** (bigger, for lab) | WT-43-RK + DK + battery + box | **~1 100–1 300** |

**Sailor UI is extra:** watch you already own, or later a second “screen housing” (~R400–800 parts) that only does BLE — it does **not** hold the RTK/LoRa.

---

## B) Committee boat — what it comprises (not one “puck”)

Committee is a **small kit**, not one GoPro brick.

```
COMMITTEE BOAT
│
├─ WT-43-BK-LoRa ─────────── RTK BASE (the only base on the bay)
├─ Survey / patch antenna on a pole ── better sky view for the base
├─ Battery box (12 V or USB bank) ── all-day power
├─ Laptop or tablet ──────── Race Control software (you already have a computer)
├─ Cable / USB-serial or Pi ── talk to the base, log, inject race messages
│
└─ OPTIONAL
     ├─ 2nd WT-43-RK on bow if pole ≠ geometric line end
     └─ 4G modem for spectators only (never for OCS)
```

| Piece | In a “housing”? | ~R |
|-------|-----------------|---:|
| WT-43-BK-LoRa | In a dry box / soft case — **not** a GoPro puck | **512–576** |
| Antenna + pole + mounts | On deck / rail | **300–800** |
| Battery / box | Deck box | **200–500** (or use club 12 V) |
| Laptop/tablet | Helm / nav table | **R0** if you bring one |
| USB-serial / Pi | In same dry box as base | **50–200** |
| **Committee electronics subtotal** | | **~R850–1 700** + host computer |
| **With antenna/pole/battery if buying all** | | **~R1 100–2 500** |

**Housing included?** No finished “committee product shell” yet — beta = **your dry box** + pole. The expensive clever bit is still just the **WT-43-BK** (~R500–600).

---

## C) Pin / mark (same guts, simpler)

Same **WT-43-RK** as the boat, in a **float/clip pack** (your box).  
**Usually no nRF54** on V1 pin/mark — only GNSS+LoRa position uplink.

| Pack | ~R |
|------|---:|
| WT-43-RK + battery + your float box | **~600–800** |

---

## D) Smallest kit that makes a race line

| Role | Hardware | ~R |
|------|----------|---:|
| Committee base | WT-43-BK + pole antenna + box | **850–1 700** |
| Start pin | WT-43-RK pack | **600–800** |
| First boat puck | WT-43-RK + nRF54 + battery (+ housing) | **650–1 100** |
| **Kit total (prove OCS path)** | | **~R2 100–3 600** |

Add marks later: **+R600–800 each**.

---

## Quick answers to “et cetera”

| Question | Answer |
|----------|--------|
| Is housing in the WT-43 price? | **No** |
| Is battery in the WT-43 price? | **No** |
| Is the MCU in the WT-43 price? | **No** — WT-43 is GNSS+LoRa only |
| Does the puck have a screen? | **No** — Universal Puck is blind; UI is BLE watch/phone/optional 2nd housing |
| Does committee use a GoPro puck? | **No** — base + pole + laptop |
| Can one WT-43 do both base and rover? | Buy **BK** for base, **RK** for rovers (same family, different role) |
| Do I need a bow Tag for beta? | **No** — nice later for OCS sharpness |

---

## One sentence each

- **Puck ≈ R750–1 100** in a GoPro case: **WT-43 rover + MCU + battery + housing**.  
- **Committee ≈ R850–1 700** electronics (+ antenna/pole if needed): **WT-43 base + dry box + computer you already own**.  
- **Housing is always a separate line** — beta can be your waterproof boxes at R0 hardware cost.
