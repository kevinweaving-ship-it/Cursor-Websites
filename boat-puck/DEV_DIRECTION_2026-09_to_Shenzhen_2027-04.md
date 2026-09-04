# SailingSA Boat Puck — Development Direction (digest)

**Horizon:** Sep 2026 → Shenzhen **April 2027** (~7 months)  
**Stance:** Do **not** freeze production PCB yet. Arrive in China with **working prototypes, measured data, firmware experience, defined architecture, target BOM** — not “what GPS tracker can you sell us?”  
**FX / money:** quote hardware in **R** (and $).

Source brief digested Sep 2026; cross-checked against Lipton R1–R10 / Vakaros findings in [`accuracy-vs-racesense-pins.md`](accuracy-vs-racesense-pins.md).

---

## One-line direction

**Prove or kill:** multi-band **RTK** + **LoRa RTCM** (no race-day cloud) + **nRF54L15 Bluetooth 6** (+ optional bow Channel Sounding) + **IMU** — using cheap **OTW/Anzewei WT-43** first, **Unicore UM980** as benchmark. **UWB off every-boat BOM.**

Likely Apr 2027 production shape (prediction, not freeze):

`RTK GNSS + nRF54L15 + LoRa + 6-axis IMU + 3000–5000 mAh + waterproof shell`  
(+ tiny bow tag if Channel Sounding earns ≤~5 cm sailing)  
Committee: RTK base + LoRa broadcast + nRF54L15 + optional 4G.

---

## Why this vs earlier stack

| Earlier lean | Now |
|--------------|-----|
| UM980 + DWM3001C UWB on every puck + BMI270 | **OTW WT-43 first**; UM980 = **reference**; **UWB = lab only** (~R700+/boat unjustified); IMU from Nordic Tag first |
| Old BLE then replace | **Develop on Bluetooth 6 / Channel Sounding now** (Nordic + NXP) |
| Cloud/NTRIP critical path | **Local base → LoRa RTCM → rovers** |

---

## Architecture (roles)

```
COMMITTEE: WT-43-BK-LoRa (base) --RTCM/LoRa broadcast--> fleet
PIN / MARKS / FINISH: RTK + LoRa (+ BT6 experiment; UWB only on selected infra for tests)
BOAT PUCK: WT-43-RK-LoRa (or UM980 later) + nRF54L15 + IMU + battery + GoPro-class case
BOW TAG (experiment): nRF54L15 Tag / Channel Sounding ↔ Puck
```

**OCS:** bow vs **live RTK line** (committee end + pin) at GNSS **T=0**, in a **horizontal 2D** frame (antenna height irrelevant for basic OCS).

**OCS error budget (must measure, not believe datasheets):**

1. RTK position  
2. Line-end accuracy  
3. Timing  
4. Puck→bow geometry  
5. Heading / IMU  

Manufacturer “1 cm” ≠ finished OCS 1 cm.

---

## Hardware paths

### A — Primary prototype (cheap)

| Item | Role | Target |
|------|------|--------|
| **WT-43-RK-LoRa** | Boat / pin / mark rover | ~**R600–750**; dual-freq RTK ~1 cm+1 ppm; **1–20 Hz**; UART; integrated LoRa+antenna class |
| **WT-43-BK-LoRa** | Committee base | Matching RTCM over LoRa |

**Kill / prove:** moving FIX; 20 Hz; RTCM over LoRa; latency; range over water; chipset IDs; API; antenna; SA regulatory band/power.

### B — High-end reference

| Item | Role |
|------|------|
| **Unicore UM980** (×2 carriers) | Benchmark; production GNSS **if** OTW fails sailing needs (rate / FIX / antenna) |

Prefer **20 Hz**; **10 Hz** minimum; **50 Hz** useful not required.

### C — App MCU / short-range (future-proof)

| Item | Role |
|------|------|
| **nRF54L15** (+ DK, **Tag**) | Main firmware, BLE watch/phone, **BT6 Channel Sounding**, proprietary 2.4, OTA, IMU study |
| **NXP MCXW72-LOC** (×2) | Independent Channel Sounding benchmark — don’t Nordic-only bet |

### D — LoRa discrete

| Item | Role |
|------|------|
| **A39** UART LoRa (~**R110–130**) | Independent RTCM pipe / range tests vs OTW integrated LoRa |

### E — UWB

| Item | Role |
|------|------|
| **DWM3001C** (few) | Ranging comparison only — **not** on sailor puck BOM |

---

## Buy-now list (from brief)

| Vendor | Qty | Purpose |
|--------|-----|---------|
| Nordic nRF54L15 DK | 2 | MCU / BT6 |
| Nordic nRF54L15 Tag | 4–6 | Bow tag, CS, IMU, multi-node |
| NXP MCXW72-LOC | 2 | CS benchmark |
| OTW WT-43-BK-LoRa | 1 | RTK base |
| OTW WT-43-RK-LoRa | 2 (→4) | Fleet RTK |
| Unicore UM980 boards | 2 | Reference |
| A39 LoRa modules | 4–6 | Discrete LoRa / range |
| DWM3001C | few | UWB reference only |

Enclosure: **GoPro-style waterproof** for development — **no injection tooling yet**.

---

## Test programmes (evidence before China)

**RTK:** static / moving (walk, car, boat); 10 / 20 / 50 Hz; TTF; FIX hold; recovery; correction age vs accuracy; antennas wet/heel/crew/mount.

**LoRa:** 1 → 10 → simulated 50/100 rovers (**broadcast** RTCM — don’t ACK every correction); throughput, latency, loss, FIX; **open water 0.5 / 1 / 2 / 5 km**; SA band compliance.

**BT6 Channel Sounding:** 0.25–100 m; static/moving/heel/sail/crew/carbon/wet; real **95%** sailing error — chase ±20 / ±10 / ±5 cm; ≤5 cm → bow tag interesting; else RTK+geometry authoritative.

**OCS:** live RTK line; signed bow vs line at T=0; vs video / surveyed / deliberate crosses; publish confidence band (definite OCS / clear / grey zone).

---

## Lipton lessons to keep in this direction

(From R1–R10 Vakaros data — not in the original brief as strongly; **do not drop**.)

| Lesson | Implication for us |
|--------|-------------------|
| Start/OCS mostly OK; **upwind to M1** lost points | Marks + boats as **radios/relays**, not GNSS-only |
| RC→M1 ~**1.5–2.3 km**; boats ~**2–2.5 km** | LoRa design margin **≥3 km** at usable air rate |
| “Jumps” = **gaps**, not teleport | **Store all points on puck**; backfill between roundings |
| Spectators care start / rounding / finish live | Live stream those; **upload full track in quiet legs** — congestion not a product issue |
| OCS knife-edge ~**10–40 cm** | cm RTK + measured bow/heading; grey-zone policy |

**Store + ACK (or batch ACK) for race log** remains the way to claim zero missed history; live can lag and catch up.

---

## Before Shenzhen (Apr 2027 checklist)

Know from **our** measurements:

- OTW vs UM980 for sailing  
- Whether 10 vs 20 vs 50 Hz matters on water  
- LoRa RTCM across real course distances  
- BT6 CS useful at 20 / 10 / 5 cm or not  
- Nordic vs NXP (accuracy, power, SDK, cost, RF)  
- IMU need; full-day battery Wh; antenna architecture; housing envelope  

**Take to factories:** working pucks, base, bow tags, LoRa RTCM, BT6 ranging, sailing datasets, schematics, PCB/antenna/battery/housing reqs, firmware, target BOM, **100 / 500 / 1000** pricing asks.

Ask: *manufacture this cheaper/smaller/better* — not *what tracker do you sell*.

---

## Report verdict

| | |
|--|--|
| **Direction quality** | Strong — timeboxed, evidence-first, future radio (BT6), cost-disciplined (OTW first, UWB off BOM) |
| **Aligns with Lipton** | Yes on local RTK+LoRa; **add explicitly** mark/boat **relays** + **on-puck store/backfill** |
| **Biggest bets to kill** | (1) OTW moving FIX @ 20 Hz + LoRa over water (2) BT6 CS for bow ≤5–10 cm sailing |
| **Don’t freeze** | Production PCB / injection mould until those bets are measured |
| **Default production prediction** | RTK + nRF54L15 + LoRa + IMU — **not** UM980+UWB-on-every-boat |

---

## Related docs

- [`race-kit-roles-wt43-v1.md`](race-kit-roles-wt43-v1.md) — committee / pin / marks  
- [`logic-check-wt43-v1.md`](logic-check-wt43-v1.md) — V1 logic  
- [`accuracy-vs-racesense-pins.md`](accuracy-vs-racesense-pins.md) — Lipton pin/OCS bar  
- [`gnss-50hz-lock.md`](gnss-50hz-lock.md) — ≥25 Hz parity / 50 Hz stretch  
- [`NORTH_STAR.md`](NORTH_STAR.md) — beat Vakaros doctrine  
