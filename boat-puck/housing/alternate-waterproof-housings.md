# Alternate waterproof housings (bigger than GoPro)

Goal: find a **common watersports / dive-style housing** that can hold:

| Need | Target |
|------|--------|
| **4.2" RLCD** AA | **63.6 × 84.8 mm** (+ bezel/window) |
| Waveshare / custom PCB width | ~**70–93 mm** |
| Puck guts | RTK GNSS + LoRa + IMU + battery + ESP32 |
| Comfortable stack depth | ideally **≥25–35 mm** (phone cases are ~10–12 mm — too thin) |

GoPro H9–13 cavity (**71.8 × 50.8 × 33.6**) has depth but **not** screen area.  
Phone dive cases have screen area but **not** depth.

---

## Verdict (short)

| Housing class | Screen 4.2"? | Puck guts + ESP32? | Use for Boat Atlas? |
|---------------|--------------|--------------------|---------------------|
| GoPro ADDIV | No | Yes (tight) | Dinghy puck only |
| **Phone dive housings** (SeaLife / Divevolk) | **AA yes (landscape)** | **No — only ~10–12 mm thick** | UI mock in dry box only |
| Action-cam clones (DJI / Insta360) | No (still small) | Maybe | Not Atlas |
| Soft Aquapac / OverBoard | Yes (loose) | Yes (floppy) | Splash proto, not product |
| **Own IP67 shell** | Yes | Yes | **Real Boat Atlas** |

**There is no common “GoPro but bigger” hard dive housing that is both phone-wide and instrument-deep.**  
Atlas stays **custom housing** (or a thick dry box adapted for deck use).

---

## 1. Phone underwater housings (most common “bigger than GoPro”)

Very common for diving / snorkeling / surfing. Clear rear window, latch + O-ring, ¼-20 mounts.

### A. SeaLife SportDiver S — very common

| | |
|--|--|
| Internal | **165 × 80 × 9.7 mm** |
| External | ~213 × 126 × 55 mm |
| Depth rating | ~30 m |
| URL | https://www.sealife-cameras.com/product/sportdiver-s-smartphone-housing/ |

| Fit | |
|--|--|
| 4.2" AA 63.6×84.8 | **Yes** if panel lies flat (84.8 along length, 63.6 along width) |
| ESP32 / Waveshare ~70 mm wide | **Width OK** |
| RTK + battery + LoRa stack | **No** — **9.7 mm** cavity depth |

### B. SeaLife SportDiver Ultra — larger phones

| | |
|--|--|
| Internal | **183 × 80 × 12 mm** |
| External | ~231 × 124 × 61 mm |
| Depth rating | ~40 m |
| URL | https://www.sealife-cameras.com/sportdiver-selection-guide/ |

Same story: **plane fits 4.2"**; **12 mm depth kills the puck stack**.

### C. Divevolk SeaTouch 4 Max Plus — most common touch-through dive phone case

| | |
|--|--|
| Max phone | **180 × 82.5 × 11.2 mm** (lens bump ≤~15 mm) |
| Outer housing | ~226 × 120 × 44 mm |
| Depth | 60 m shell / touch ~30–40 m |
| URL | https://divecatalog.com/products/divevolk-seatouch-4-max-plus-underwater-smartphone-housing |

Again: **screen plane OK**, **thickness ~11 mm — not OK** for GNSS module + cell + LoRa.

### Phone-housing conclusion

Use these only if you build a **flat “display slab”** (S3 + RLCD only) and put radio/GNSS **elsewhere** (split architecture).  
**Not** for one-unit Atlas = puck + 4.2".

---

## 2. Action-camera housings (GoPro-class)

| Example | Approx size | Atlas? |
|---------|-------------|--------|
| DJI Osmo Action 60 m case | outer ~87 × 43 × 79 mm; camera ~70×44×33 | Still GoPro-scale — **no 4.2"** |
| Insta360 X4 dive case | outer ~155×80×85; molded to 360 cam | Wrong shape / no big flat window for RLCD |

Same market as GoPro: **common, cheap mounts, too small for Atlas glass**.

---

## 3. Soft waterproof cases (watersports, very common)

| Example | Size idea | Notes |
|---------|-----------|--------|
| Aquapac Large Whanganui (668) | height ~295 mm, circ ~440 mm | IPX8 ~10 m; touch through TPU; **floppy** |
| OverBoard / similar phone–tablet dry bags | various | Cheap splash/sail proto |

**Pros:** room for 4.2" + thick PCB stack.  
**Cons:** not a hard instrument, poor GNSS sky / mount repeatability, looks nothing like Atlas.

OK for **wet-bench / dinghy rail bag prototype**, not the product shell.

---

## 4. What would actually work

### Option A — Own hard shell (recommended for Boat Atlas)

Design IP67 around:

- Window ≥ **~70 × 90 mm** clear (AA 63.6×84.8 + gasket)  
- Internal depth **≥30–40 mm** for GNSS + battery + LoRa  
- Footprint ~**100 × 120 × 40 mm** class (order-of-magnitude)

Same path as [`../atlas/one-unit-build.md`](../atlas/one-unit-build.md).

### Option B — Split (reuse common housings)

```
GoPro / small hard case     →  RTK + LoRa + IMU + battery   (dinghy puck)
Phone dive housing OR own thin head →  4.2" RLCD + ESP32 only
```

Phone housing depth is suddenly enough if **only** glass + S3 (~13 mm Waveshare board).

### Option C — Deck dry box (not scuba)

Pelican Micro / Hammond / Bud IP67 boxes with a machined window — common in marine electronics, **not** “GoPro aisle at Decathlon”, but real for keelboat deck instruments.

---

## 5. Size check vs our parts

| Part | Footprint | Depth need |
|------|-----------|------------|
| 4.2" RLCD AA | 63.6 × 84.8 | glass ~1–2 mm + FPC |
| Waveshare S3+RLCD board | ~92.5 × 70 | ~13.5 |
| Custom: S3 + SX1262 + IMU | ~60–90 × 50–70 | ~8–15 PCB |
| RTK module (typical) | ~20–40 × 15–30 | ~3–8 |
| 18650 / LiPo pack | varies | **often 10–20** |
| **One-unit stack** | ~90 × 100 | **~25–40** |

Phone dive max thickness **~10–12 mm** → fails one-unit.  
GoPro depth **33.6 mm** → OK for guts, fails screen.

---

## 6. Practical next step

1. **Do not** buy SeaLife/Divevolk expecting full Atlas inside — depth is wrong.  
2. If you want a **store-bought** path for glass + MCU only: Divevolk / SportDiver Ultra as a **display head** + GoPro puck (split).  
3. For **true one-unit Atlas**: CAD own housing (or quote a Chinese dive-case OEM for a **thick** phone-style shell — custom MOQ).

### Buy links (research)

| Product | Link |
|---------|------|
| SeaLife SportDiver S | https://www.sealife-cameras.com/product/sportdiver-s-smartphone-housing/ |
| SeaLife size guide | https://www.sealife-cameras.com/sportdiver-selection-guide/ |
| Divevolk SeaTouch 4 Max Plus | https://divecatalog.com/products/divevolk-seatouch-4-max-plus-underwater-smartphone-housing |
| Aquapac Large Whanganui | https://www.nrs.com/aquapac-waterproof-paddle-case-large-668/pp7l |
