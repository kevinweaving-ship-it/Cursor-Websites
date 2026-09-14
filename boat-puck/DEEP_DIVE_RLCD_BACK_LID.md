# Deep dive — puck screen **only if** RLCD + thin + correct size

**Hard gate:** no screen on the puck unless **all three** pass:

1. **Type = full reflective RLCD / MIP reflective** (sun uses ambient light — better outdoors)  
2. **Thin** ≤ **~2.0 mm** glass/module (prefer ≤1.7 mm)  
3. **Size** fits H9–13 **back-lid** budgets below  

If any fail → **no screen** (LEDs + beeps + under-casing buttons only).  
**1000-nit colour TFT is not the preferred path** (battery + heat); keep only as last fallback.

---

## Lid mechanical lock (HERO13 / H9–13)

| Budget | mm | Use |
|--------|-----|-----|
| Insert rear face | **71.8 × 50.8** | Absolute max module outline |
| **Visible backdoor window** | **~62.7 × 41.7** | What you see through lid glass |
| Depth for display stack | **≤ 2.0 mm** prefer (≤ 4 mm hard max) | Thin — don’t steal WT-43 / LiPo depth |
| Stock GoPro AA reference | 48.0 × 32.0 | Comfortable bezel class |

```
PASS outline if:
  W ≤ 71.8  AND  H ≤ 50.8   (face)
  AND thickness ≤ 2.0 (prefer) / 4.0 (hard)
Ideal: AA / visible glass ≤ 62.7 × 41.7
Slight under-frame overhang OK if outline ≤ face and AA inside window.
```

---

## Size matrix — reflective only

| # | Panel | Type | Outline mm | Thick | AA mm | Face 71.8×50.8? | Window 62.7×41.7? | Verdict |
|---|-------|------|------------|------:|-------|:---------------:|:-----------------:|---------|
| **A** | **Sharp LS027B7DH01(A) 2.7"** | MIP **reflective** (Memory LCD) | **62.8 × 42.82** | **1.65** | 58.8 × 35.28 | **YES** | **Tight** (~0.1 / ~1.1 over glass) — AA inside | **BEST lid fill** if door frame covers rim |
| **B** | **ST7305 2.13" RLCD** | Full reflective mono | **~27.1 × 56.2** | **~1.1** | ~23.7 × 48.5 | **YES** | **YES** (easy) | **BEST safe RLCD** — same IC family as Atlas |
| **C** | **ST7305 1.54" RLCD** | Full reflective mono | **29.5 × 31.7** | **0.80** | 27.7 × 27.7 | **YES** | **YES** | Pass size — small UI only |
| **D** | **Kyocera TN0216 2.2"** | Full reflective mono | **51.1 × 31.85** | **1.54** | 48 × 26 | **YES** | **YES** | Pass — landscape strip |
| **E** | **ST7305 2.9" RLCD** | Full reflective mono | **70.95 × 31.1** | **~0.8** | 66.9 × 29.1 | **YES** (70.95&lt;71.8) | Long **over** window (~8 mm under frame) | **Maybe** — measure real door |
| **F** | **ST7305 4.2" RLCD** | Full reflective mono | outline ~**67.6 × 91** · AA **63.6 × 84.8** | **~0.8** | 63.6 × 84.8 | **NO** (91≫50.8) | **NO** | **Atlas only** — never puck |
| — | Chenghao/Orient 1000-nit TFT | Transmissive backlight | 34.6×47.8 / 42.7×58.5 | 2.0–2.2 | — | Yes / tight | Yes / tight | **Not gate type** — fallback only |

---

## Deep dive — candidates that **pass the gate**

### A — Sharp **LS027B7DH01 / LS027B7DH01A** (max fill)

| | |
|--|--|
| **Why** | Almost **fills the back lid** · reflective MIP · **1.65 mm** thin · SPI · no backlight |
| **Outline** | **62.8 × 42.82 × 1.65 mm** |
| **Active** | **58.8 × 35.28 mm** (fits inside ~62.7×41.7 window) |
| **Res** | 400 × 240 |
| **Power** | µW-class static (Memory-in-Pixel) |
| **Buy** | DigiKey **425-2908-ND** / Mouser **852-LS027B7DH01** · LCSC **C17247735** (A) ~**$16–35** ea |
| **Datasheet class** | Sharp Memory LCD 2.7" |
| **Risk** | Module outline **~1 mm** taller than glass short axis — must sit under door frame; **caliper real Temu door** before lock |
| **Night** | No BL — use LEDs / optional later front-light |

**Ask / buy check:** confirm clone door clear aperture ≥58.8×35.3 and rim can hide 62.8×42.8 module.

---

### B — **ST7305 2.13" RLCD** (safe same-tech as Atlas) ← **default recommend**

| | |
|--|--|
| **Why** | **Same reflective ST7305 family** as Atlas 4.2" · thin · proven SPI · **clear size pass** |
| **Outline** | **~27.07 × 56.2 × 1.10 mm** (MDTR0213A class) |
| **Res** | 122 × 250 |
| **Factory / channel** | Toppop (ask 2.13" ST7305 reflective) https://toppoplcd.com/ · OSPTEK / AliExpress fish-hawk stores · DigiKey MDTR0213A-SPI class |
| **Atlas link** | Same IC as Toppop **TT420FSN21A** 4.2" — https://toppoplcd.com/productdetails_5835009.html |
| **Cost** | Expect **~$5–12** glass sample class |
| **Risk** | Smaller than lid — more bezel (OK for timer digits) |

**Ask Toppop:**
```
Quote 2.13" ST7305 full-reflective SPI glass ×3 (outline ~27×56×1.1).
Same reflective family as TT420FSN21A. Ship Eric Shenzhen.
```

---

### C — **ST7305 1.54"** (tiny)

| Outline | **29.46 × 31.71 × 0.80** | DigiKey MDTR0154A-SPI class |
| Pass? | **Yes** | Only if UI is tiny status/timer |

### D — Kyocera **TN0216ANVNANN-GN00** 2.2"

| Outline | **51.1 × 31.85 × 1.54** |
| URL | https://www.youritech.com/products/tn0216anvnann-gn00-2-2-inch-reflective-display-320x176-sunlight-readable-3-wire-spi-mip-display.html |
| Buy | Youritech ~**$27** w/ demo option · `info@youritech.com` |

### E — **2.9" ST7305** (borderline)

| Outline | **70.95 × 31.1 × ~0.8** | https://www.good-display.com/product/454.html **GDTL029T51** |
| Face | Pass | Window long side under frame ~8 mm total — **measure door** or skip |

---

## Fail (do not put on puck)

| Panel | Why fail |
|-------|----------|
| **4.2" RLCD** (Waveshare / Toppop TT420) | AA 63.6×84.8 — **Atlas only** |
| Waveshare colour SPI TFT | Not reflective gate type; usually &lt;1000 nit anyway |
| ESP32-S3-RLCD-4.2 **kit** | Board too big for cavity |
| Any screen **&gt;2 mm** with thick PCB bezel under lid | Depth fail |

---

## Recommendation lock

| Priority | Choice | Why |
|---------:|--------|-----|
| **1** | **ST7305 2.13" RLCD** | Gate pass (type+thin+size) · same tech as Atlas · safe margins |
| **2** | **Sharp LS027 2.7"** | Best lid fill · caliper Temu door first |
| **3** | Kyocera TN0216 / 1.54" ST7305 | Alts |
| **Skip screen** | — | If neither A nor B samples fit real door → LEDs+beeps only |

**Drive:** SPI → **nRF54**.  
**Buttons:** still under stock casing plungers.  
**Night:** LEDs ×3–4 + speaker beeps (RLCD has no backlight).

---

## Next actions (not today’s SoftSIM PO)

1. RFQ Toppop **2.13" ST7305 reflective ×3**.  
2. Optional: buy **1× Sharp LS027** to dry-fit against Temu H9–13 backdoor with calipers.  
3. No screen PO until fit photo / caliper pass.

Related: `OPTIONAL_PUCK_UI_SCREEN_BEEPS.md` · `atlas/display-4.2-rlcd.md` · `housing/gopro-back-screen-fit.md`
