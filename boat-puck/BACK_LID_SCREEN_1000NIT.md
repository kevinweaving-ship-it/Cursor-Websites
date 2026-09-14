# Back-lid screen — ≥1000 nit (sunlight)

**Mount:** rear / **backdoor lid** side · as wide/long as lid allows · **thin only**  
**Window budget:** visible **~62.7 × 41.7 mm** · face max **71.8 × 50.8** · thickness **~2–4 mm**  
**Must:** **≥1000 cd/m² (nits)** · SPI (or SPI+MCU) · driven by **nRF54**

---

## Fit vs lid

| Candidate | Nits | Module mm | AA mm | Fits window 62.7×41.7? | Fill lid? | Verdict |
|-----------|-----:|-----------|-------|------------------------|-----------|---------|
| **Chenghao CH200QV18B 2.0"** | **1000** | **34.6 × 47.8 × 2.0** | 30.6 × 40.8 | **YES** | Partial (~75% long) | **Best safe pick** |
| **Orient AFY240320B0-2.4INTH 2.4"** | **1000** | **42.72 × 58.5 × 2.15** | ~36.7 × 49.0 | **Tight** — 42.72 **>** 41.7 short axis (~1 mm) | Almost full long | Only if under frame / custom door glass |
| Sunshine SDT024 / HOTHMI 2.4" | **1000–1500** | ~42.7 × 59–60 × 2.2–3.2 | 36.7 × 49.0 | Same tight short axis | Almost full | Same as Orient |
| Chenghao / Orient **2.8"** | **1000** | **50 × 69.2 × ~2.2** | 43.2 × 57.6 | **NO** (69 > 63) | Too big | **Out** |
| Waveshare 2.0" hobby SPI | ~300–500 typ | 58 × 35 | 30.6 × 40.8 | Board OK, nits **fail** | — | **Out** (&lt;1000 nit) |

---

## Buy #1 (recommended) — Chenghao 2.0" **1000 nit**

| | |
|--|--|
| **PN** | **CH200QV18B** |
| **Size** | 2.0" IPS · 240×320 · ST7789 class |
| **Brightness** | **1000 cd/m²** |
| **Module** | **34.6 × 47.8 × 2.0 mm** — thin · fits lid window with margin |
| **Interface** | SPI / MCU / RGB (use **SPI** to nRF54) |
| **Factory** | Shenzhen Chenghao Optoelectronic |
| **URL** | https://www.chenghaolcd.com/sale-41201693-sunlight-readable-ips-lcd-display-with-spi-mcu-rgb-multi-interface.html |
| **PDF** | https://www.chenghaolcd.com/doc/41201655/st7789-2-inch-ips-lcd-display-1000-cd-m2-brightness.pdf |
| **Contact** | add@chenghaolcm.com · +86 755 27806536 |
| **Cost** | Factory quote (MOQ often 100; samples usually negotiable) — class **~$8–15** sample |

**Ask:**
```
Quote CH200QV18B (1000 nit) ×3 samples.
Confirm SPI mode + backlight current at 1000 nit.
Ship Eric Shenzhen.
```

Touch variant **CH200QV18A-CT** is thicker (~3.3 mm) — skip for V1 (use external buttons ×2).

---

## Buy #2 (max fill lid) — Orient 2.4" **1000 nit**

| | |
|--|--|
| **PN** | **AFY240320B0-2.4INTH** |
| **Brightness** | **1000 cd/m²** |
| **Module** | **42.72 × 58.5 × 2.15 mm** |
| **Interface** | RGB / MCU / SPI |
| **URL** | https://www.orientdisplay.com/products/2-4-sunlight-readable-ips-240x320-1000-nits-mcu-rgb-spi-interface/ |
| **Fit note** | Short side **42.72 > 41.7** window — needs confirm against clone door glass or sit under frame |

---

## Pack on lid

```
Back lid window ~62.7 × 41.7
┌─────────────────────────────────┐
│     thin 1000-nit panel         │  CH200: 34.6×47.8×2.0  (safe)
│     (SPI → nRF54)               │  or Orient 2.4" if door allows
│  LEDs ×3–4 + buttons ×2 bezel   │
└─────────────────────────────────┘
Speaker at rear cavity edge
```

**Power note:** 1000 nit backlight draws hard (often tens–100+ mA) — size LiPo / duty-cycle brightness for race beeps UI, not always-on max.

---

## Lock

- **≥1000 nit** required for sunlight.  
- **#1 buy enquiry:** Chenghao **CH200QV18B**.  
- Not on today’s SoftSIM/dry-box PO — park with optional UI (`OPTIONAL_PUCK_UI_SCREEN_BEEPS.md`).
