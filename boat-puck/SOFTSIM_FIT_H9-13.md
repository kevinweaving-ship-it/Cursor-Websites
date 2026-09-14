# SoftSIM 4G/5G options that can fit H9–13

**Cavity (locked):** **71.8 × 50.8 × 33.6 mm**  
**Already inside:** WT-43 **43×43×14** + flat LiPo + nRF54 module + Qi RX on wall  
**Leftover strip (plan view):** ~**28.8 × 50.8** beside the WT-43 (along long axis). Side gap beside square is only ~7.8 mm — **too narrow** for cell modules.  
**Stack height left:** ~**19 mm** above/beside WT-43 for battery + BLE + SoftSIM carrier.

**Rule:** SoftSIM = **software UICC on the modem** (no SIM tray).  
**Why SoftSIM on the puck (cost / use):** most of the time the sailor is **training alone** — **no committee, no LoRa race net**. Full LoRa kit (base + marks + Race Control) is race-day. SoftSIM lets the puck work **standalone** (corrections / telemetry / phone backhaul) without that kit. Race day still prefers **LoRa**; cell is also race fallback when LoRa is weak.  
**True 5G NR modules** are generally too big / hot for this cavity — treat **“4/5G” as LTE Cat 1 SoftSIM** for puck fit.

---

## Fit verdict (module only — not EVB)

| Option | Size (mm) | SoftSIM | Radio | Fits leftover ~28.8 strip? | SA practical? | Verdict |
|--------|-----------|---------|-------|----------------------------|---------------|---------|
| **SIMCom A7672** (SoftSIM FW) | **24 × 24 × 2.4** | Yes (Onomondo / Monogoto FW) | LTE **Cat 1** | **YES** (~4.8 mm margin) | Yes — rides normal LTE | **Best add-on pick** |
| **SIMCom SIM7672** | **24 × 24 × 2.4** | Yes (Onomondo) | Cat **1 bis** | **YES** | Yes | Strong alt |
| **Quectel EG915U** (QuecOpen SoftSIM) | **23.6 × 19.9 × 2.4** | Yes (SDK) | Cat 1 | **YES** (easiest) | Yes | Strong alt |
| **Quectel EG912U** (QuecOpen SoftSIM) | **29 × 25 × 2.4** | Yes (SDK) | Cat 1 bis | **Tight / no** in 28.8 strip | Yes | Only if sled stacks **on** WT-43 face (risky RF) |
| **Quectel EG21-G / EG25-GL** | **29 × 32 × 2.4** | Yes (vendor SoftSIM FW) | Cat 1 / Cat 4 | **NO** beside WT-43 | Yes | **Too big** unless custom sled under lens port (don’t) |
| **Nordic nRF9151** SiP | **11 × 12 × 1** | Yes (Onomondo SoftSIM) | **LTE-M / NB-IoT** only | **YES** (tiny) | **Weak** — SA LTE-M not commercial; NB-IoT mainly Vodacom | Size win, coverage risk — **not first pick** |
| **OTW WT-43-RK-4G** | **43 × 43 × ~8–14** | **Not confirmed** | 4G + laminated ant | Replaces LoRa brick | Maybe | **Wrong flavour** for race (no LoRa primary) — ask Lucas only if SoftSIM+LoRa combo exists |
| **Any SoftSIM EVB / USB dongle / ESP32+4G kit** | 50–100+ mm | Varies | Varies | **NO** | — | **Out** (same reason as ESP32) |

---

## How it would pack (add-on path)

```
H9–13  71.8 × 50.8 × 33.6
┌──────────────────────────────────┐
│ WT-43 43×43×14 (GNSS→lens port)  │▓▓ SoftSIM 24×24×2.4
│                                  │▓▓ + FPC cell ant on WALL
│ LiPo flat + nRF54                │▓▓ UART → nRF54
│ Qi RX on side/rear wall          │
└──────────────────────────────────┘
```

- **Carrier:** custom tiny PCB (module + matching + U.FL/FPC pad) — **no SIM slot**, **no USB jack**.  
- **Antenna:** FPC LTE antenna stuck to **inner wall** (not sky window / not on GNSS face).  
- **Host:** UART AT to **nRF54** (preferred) — SoftSIM profile flashed in production.  
- **Power:** share LiPo via regulated rail; cell TX peaks are harsh — need solid 3.7–4.2 V path.

---

## Onboard path (ask Lucas — Flavour D)

Prefer if factory can do it:

1. **WT-43 LoRa + SoftSIM 4G** on one brick (optional software enable), or  
2. Their **tiny SoftSIM daughter** already matched to WT-43 UART.

Until Lucas confirms SoftSIM (not nano-SIM tray), do **not** order WT-43-RK-4G for the puck.

---

## Recommendation (housing-fit)

| Rank | What | Why |
|-----:|------|-----|
| **1** | **A7672 SoftSIM** (or **SIM7672**) on custom ≤28×28 carrier + wall FPC ant | Proven SoftSIM FW, Cat 1 on SA LTE, fits strip |
| **2** | **EG915U** SoftSIM via QuecOpen | Smallest Quectel SoftSIM-capable Cat 1 |
| **3** | Lucas **LoRa+SoftSIM** combo if quoted | Cleanest BOM if real |
| **Skip** | EG21/EG25 bricks, nRF91-only for SA race, any EVB, ESP32+4G | Size and/or coverage |

**Where to put SoftSIM first:** **committee / shore** (dry box has room) before every puck. Puck SoftSIM only after LoRa water test + packing prototype.

**Do not buy SoftSIM hardware in this sample PO** — research lock only. Next order step stays Minew reply / dry box / local charge parts.
