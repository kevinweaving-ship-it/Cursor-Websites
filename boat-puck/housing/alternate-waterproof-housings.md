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
| Phone dive (SeaLife / Divevolk) | AA yes | **No — ~10–12 mm** | Display head only if split |
| **Pelican Micro 1040 clear** | **Yes** | **Yes — ~44 mm** | **Best store-bought one-unit proto** |
| **ZP150.100.60 clear lid** | **Yes** | **Yes — ~50 mm** | Cheap industrial proto |
| Soft Aquapac / OverBoard | Yes (loose) | Yes (floppy) | Splash proto only |
| **Own IP67 shell** | Yes | Yes | **Final product** |

Phone dive cases are too thin. **Next housing to buy: Pelican 1040 clear** (or ZP150×60). Final Atlas = own shell.

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

**12 mm (even Ultra) is not deep enough for all electronics.**

Rough one-unit stack (front → back):

| Layer | Typical depth |
|-------|----------------|
| RLCD glass + window/gasket | ~2–4 mm |
| PCB (ESP32 + LoRa + IMU) | ~8–15 mm |
| RTK GNSS module | ~3–8 mm |
| Battery (LiPo / 18650 flat) | ~8–20 mm |
| Foam / seal clearance | ~1–2 mm |
| **Total** | **~25–45 mm** |

Phone dive cavities (**~10–12 mm**) only fit a **display slab** (glass + S3).  
Full Boat Atlas (puck guts + screen) needs **≥ ~30 mm** internal depth → **own shell** or **split** (GoPro puck + thin display head).

Use SeaLife/Divevolk only if radio/GNSS live **elsewhere**.  
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

### Option C — Deep store-bought boxes (use these instead of phone cases)

#### 1) Pelican Micro **1040** — must buy **CLEAR** version

Solid black/yellow Pelican = **opaque** — you cannot see the RLCD.  
Order the **clear lid / clear body** SKU (e.g. yellow/clear **1040-027-100**).

| | |
|--|--|
| **Internal** | **~165 × 98 × 44 mm** |
| Depth | **44 mm** — enough for full electronics stack |
| Plane | Fits **4.2" AA** + Waveshare ~92.5×70 |
| See-through | **Only the clear SKU** — polycarbonate lid (OK for proto; not optical glass) |
| Rating | IP67 (deck / dunk — not 40 m scuba) |
| Street | ~**R460–700 ($29–44)** |
| URL | https://www.pelican.com/us/en/product/cases/micro/1040 |
| Clear example | https://www.performanceaudio.com/products/pelican-1040-micro-case-clear-yellow |

Also **1050 clear** if you want more depth (~70 mm internal).

**Caveat:** clear Pelican lid is cloudy PC, not a flat optical window — fine to **read big digits in sun for a proto**, not as good as a dedicated RLCD window in a custom shell.

#### 2) IP67 clear-lid junction box — cheap industrial

| Model | Outer | Inner (approx) | Depth |
|-------|-------|----------------|-------|
| **ZP150.100.60** (Kradex / RS PRO) | 150 × 100 × 60 | ~140 × 90 × ~50 | **~50 mm** |
| OEM **158×90×60** | 158 × 90 × 60 | **152 × 84 × 50** | **50 mm** |

| Links | |
|--|--|
| RS / Kradex ZP150 | https://ie.rs-online.com/web/p/general-purpose-enclosures/2384026 |
| Kradex product | https://www.kradex.com.pl/product/enclosures_hermetically_sealed_with_cast_gasket/zp150_100_60sub-ip67_tm_asa?lang=en |

Screw-lid industrial look — good for **proto / volume cheap**, not final Atlas styling.
Fully **transparent lid** = better see-through than opaque Pelican; still not optical glass.

### Option D — Insta360 dive cases? **No**

| Case | Outer (approx) | Why not Atlas |
|------|----------------|---------------|
| **X4 Invisible Dive Case** | ~165 × 88 × 89 mm | Molded for **360 dual lenses** — no big flat rear window for 4.2" RLCD |
| **Ace Pro / Ace Pro 2 Dive Case** | ~108 × 87 × 46 mm | GoPro-class action cam — **too small** for 4.2" AA (84.8 mm) |

Insta360 housings are common watersports gear, but they are **camera-shaped**, not instrument-shaped. Same reject as DJI Action cases.

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

| Housing | Plane | Depth | One-unit Atlas? |
|---------|-------|-------|-----------------|
| Phone dive (~12 mm) | OK | **Fail** | No |
| GoPro 33.6 mm | Fail screen | OK guts | Puck only |
| **Pelican 1040 (44 mm)** | **OK** | **OK** | **Yes (proto)** |
| **ZP150 ×60 mm** | **OK** | **OK** | **Yes (proto)** |
| Own CAD | OK | OK | **Product** |

---

## 6. Practical next step

1. **Do not** buy SeaLife/Divevolk for full Atlas — depth wrong.  
2. **Buy Pelican 1040 clear** (or ZP150.100.60) — prove 4.2" + ESP32 + mock battery fit.  
3. Split path only if you want phone-dive look for display head alone.  
4. Final product: CAD own IP67 shell (look + rail + GNSS sky face).

### Buy links (research)

| Product | Link |
|---------|------|
| **Pelican 1040 Micro** | https://www.pelican.com/us/en/product/cases/micro/1040 |
| **ZP150.100.60** clear lid | https://ie.rs-online.com/web/p/general-purpose-enclosures/2384026 |
| SeaLife SportDiver S | https://www.sealife-cameras.com/product/sportdiver-s-smartphone-housing/ |
| SeaLife size guide | https://www.sealife-cameras.com/sportdiver-selection-guide/ |
| Divevolk SeaTouch 4 Max Plus | https://divecatalog.com/products/divevolk-seatouch-4-max-plus-underwater-smartphone-housing |
| Aquapac Large Whanganui | https://www.nrs.com/aquapac-waterproof-paddle-case-large-668/pp7l |
