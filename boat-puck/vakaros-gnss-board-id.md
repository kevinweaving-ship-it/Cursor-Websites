# What GNSS board does Vakaros use?

**Status:** Not publicly named. Best fingerprint match below. No teardown / FCC internal photos found that stamp a part number.

## Atlas 2 (instrument GNSS)

### Public fingerprint (locked by Vakaros marketing)

| Spec | Atlas 2 claim |
|------|----------------|
| Bands | **L1 + L5** (not L1+L2) |
| Rate | **25 Hz** GNSS |
| Constellations | GPS, Galileo, GLONASS, BeiDou |
| Standalone accuracy | ~**50 cm** / “centimetres” class (ionosphere dual-band) |
| RaceSense | Real-time **DGNSS** over BLE mesh (not onboard full RTK) |
| Power story | **100+ hours** → GNSS must be low-power |
| Timeline | Atlas 2 designed ~2020–21, launched 2021–22 |

HALO RTK is a **separate** second receiver (cm RTK add-on). Atlas 2 alone is dual-band L1+L5 + DGNSS — not a survey RTK brick.

### Best match: Sony **CXD5610** (often as Telit **SE868SY-D**)

| Fingerprint | Sony CXD5610 / Telit SE868SY-D | Fit? |
|-------------|-------------------------------|------|
| L1 + L5 | Yes | Yes |
| Update rate | **Up to 25 Hz** (explicitly marketed) | Exact |
| Accuracy | Sub-1 m CEP L1+L5 (passive antenna OK) | Matches ~50 cm claim with good antenna / DGNSS |
| Power | **&lt;45 mW** L1+L5 tracking | Matches 100 h battery story |
| Size | Module **11×11 mm** | Fits thin instrument PCB |
| Market window | Telit launch **Feb 2021** | Aligns with Atlas 2 design window |
| Raw meas. | Supported (Telit docs) | Useful for custom fusion / DGNSS |

Sources: Telit SE868SY-D launch (Sony CXD5610, 25 Hz, &lt;45 mW, L1+L5); Vakaros Atlas 2 product page / Panbo.

**Confidence:** High as *class* (Sony CXD5610 family). Medium as *exact module* (could be Telit SE868SY-D, another CXD5610 OEM, or bare LSI on custom RF). **Not confirmed by teardown.**

### Ruled out for Atlas 2 GNSS

| Candidate | Why not |
|-----------|---------|
| Quectel **LC29H** (Airoha AG3335) | Official PVT **≤10 Hz** (DA RTK 1 Hz / EA 10 Hz) — not 25 Hz |
| u-blox **ZED-F9P** class | L1+**L2** RTK-centric; Atlas markets L1+**L5**; onboard RTK not how Atlas 2 ships |
| Unicore **UM980** / survey RTK | Overkill + power for 100 h instrument; Atlas keeps full RTK on **HALO** |
| Broadcom phone hubs (BCM4775x/65) | L1+L5 phone/wearable class possible, but **25 Hz** is the Sony/Telit marketing hook, not Broadcom’s |

Industry chatter (RRS etc.) that “marine gadgets use phone L1+L5 chips” fits this class — antenna + fusion do the sailing work.

## HALO RTK (separate)

- Second high-accuracy receiver paired with Atlas 2/Edge for **~1 cm** RTK.
- Hz / chipset **not published**.
- Would be a true multi-freq RTK part (u-blox F9/X20, Unicore UM98x, Septentrio, etc.) — **unknown which**. Needs FCC photos or teardown.

## How to confirm (if we get hardware)

1. Open unit → photo GNSS module marking (Telit `SE868…`, Sony `CXD…`, Quectel, u-blox, Unicore).
2. FCC ID on label → internal photos in grant (BLE intentional radiator should have a filing; search blocked from this environment).
3. UART NMEA / proprietary `$PTWS…` (Telit) vs u-blox UBX vs Unicore — command dialect fingerprints the stack.

## Implication for Boat Puck

- Atlas 2’s own GNSS is **not** a 50 Hz RTK engine — it is a **25 Hz L1+L5 low-power** receiver + mesh DGNSS (+ IMU fusion ~50 Hz).
- Our Puck **≥50 Hz GNSS** bar (UM980 path) is **above** Atlas 2’s published GNSS rate.
- Competing Atlas *product feel* (battery life, L1+L5, 25 Hz) could reuse a **Sony CXD5610 / Telit SE868SY-D**-class part for a cheap “Atlas-like” instrument — but that is **not** the Puck RTK north star.
