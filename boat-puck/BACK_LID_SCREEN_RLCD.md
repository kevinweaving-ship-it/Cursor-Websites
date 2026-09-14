# Back-lid screen — **RLCD / reflective** (sunlight absorbs ambient light)

**Type you meant:** **RLCD = Reflective LCD** (also called full-reflective / MIP reflective).  
**Not** a 1000-nit backlight TFT. Reflective glass uses **sunlight** — more light → **better** readability, low power, thin.

| Type | How it works outdoors | Puck / Atlas |
|------|------------------------|--------------|
| **RLCD (reflective)** | Reflects ambient light — **gets better in sun** | **Preferred** |
| Transflective | Reflect + weak backlight | Colour hybrid (Atlas 2 class) — costlier |
| **1000 nit TFT** | Brute-force backlight | Fallback only if RLCD supply fails |

---

## Already locked elsewhere

| Product | Glass | Fit |
|---------|-------|-----|
| **Boat Atlas** | **4.2" ST7305 RLCD** (Toppop / Waveshare) | **Own housing** — AA 63.6×84.8 **does not** fit H9–13 back |
| **Puck (H9–13 back lid)** | Need **smaller RLCD** | Window ~**62.7 × 41.7** · thin ~1–2 mm |

Atlas URLs: `atlas/display-4.2-rlcd.md` · `atlas/buy-urls.md`

---

## Puck back-lid — reflective picks that fit

| Candidate | Type | Module mm | Fits 62.7×41.7? | Factory / URL |
|-----------|------|-----------|-----------------|---------------|
| **#1 ST7305 2.13" RLCD** | Full reflective mono | **27.1 × 56.2 × 1.1** | **YES** | DigiKey class MDTR0213A-SPI · Hicenda / Toppop ST7305 family |
| **ST7305 2.9" RLCD** | Full reflective mono | **31.1 × 71.0 × 0.8** | **NO** (71 > 63 long) | Same family — skip for lid |
| **Kyocera TN0216 2.2" reflective** | Reflective mono SPI | **51.1 × 31.9 × 1.5** | **YES** | https://www.youritech.com/products/tn0216anvnann-gn00-2-2-inch-reflective-display-320x176-sunlight-readable-3-wire-spi-mip-display.html |
| Chenghao / Orient **1000 nit TFT** | Transmissive backlight | 34.6×47.8 / 42.7×58.5 | Yes / tight | Fallback only — `BACK_LID_SCREEN_1000NIT.md` |
| **4.2" RLCD** | Reflective | 63.6×84.8 AA | **NO** | Atlas only |

---

## Buy #1 (puck) — **2.13" ST7305 RLCD**

| | |
|--|--|
| **What** | Mono **reflective** TFT · **ST7305** · SPI · **no backlight** |
| **Size** | **27.07 × 56.2 × 1.10 mm** · AA ~23.7 × 48.5 |
| **Why** | Same tech family as Atlas 4.2" RLCD · **fits lid** · thin · sun gets better · low power |
| **Supplier class** | Toppop / Hicenda ST7305 reflective · DigiKey **MDTR0213A-SPI** datasheet class |
| **Hicenda 2.9" page (family)** | https://hicenda.com/product/Reflective-TFT-Display.html |
| **Toppop** | https://www.toppoplcd.com/ · ask **2.13" ST7305 reflective** (same house as Atlas 4.2") |
| **Ask** | `2.13" ST7305 full reflective SPI ×3 samples, outline ≤56×28×1.2, ship Eric Shenzhen` |

## Buy #2 (alt) — Kyocera **TN0216** 2.2" reflective

| | |
|--|--|
| **URL** | https://www.youritech.com/products/tn0216anvnann-gn00-2-2-inch-reflective-display-320x176-sunlight-readable-3-wire-spi-mip-display.html |
| **Outline** | 51.1 × 31.85 × 1.54 · SPI · no backlight |
| **Shop** | Youritech Shenzhen · `info@youritech.com` · +86 755 8658 9469 |

---

## Pack on back lid

```
Back lid window ~62.7 × 41.7
┌─────────────────────────────────┐
│  thin RLCD (reflective)         │  ← 2.13" ST7305 preferred
│  SPI → nRF54 · no backlight     │     sun light = better contrast
│  LEDs for night cue             │
│  buttons under stock plungers   │
└─────────────────────────────────┘
```

Night: use **LEDs ×3–4** / beeps — RLCD has no backlight (optional front-light later).

---

## Lock

- **Preferred sunlight tech = RLCD / reflective** (not 1000-nit TFT).  
- **Puck lid:** **2.13" ST7305 RLCD** (or Kyocera TN0216).  
- **Atlas:** keep **4.2" RLCD** (won’t fit puck).  
- 1000-nit Chenghao = **fallback** only.
