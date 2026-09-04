# Boat Atlas — display locked: 4.2" reflective LCD

**Decision (hard):** Boat Atlas uses a **4.2" mono full-reflective LCD (RLCD)** only.  
Not colour IPS, not e-ink, not phone-as-display, not Atlas-style transflective colour.

| Spec | Value |
|------|--------|
| Size | **4.2 inch** |
| Type | **Full reflective** LCD (reads with sunlight; e-ink look, LCD refresh) |
| Resolution | **300 × 400** portrait |
| Driver IC | **ST7305** |
| Interface | **SPI** |
| Backlight | **None** |
| Active area (AA) | **63.6 × 84.8 mm** |
| Prototype kit | Waveshare **ESP32-S3-RLCD-4.2-EN** — SKU **33507** (~$25) |
| Production glass | Toppop **`TT420FSN21A`** (21-pin) or **`TT420FSN10A`** (24-pin) — ~$6–8 vol |

Suppliers & cost detail: [`../display-rlcd-4.2-research.md`](../display-rlcd-4.2-research.md).

---

## Why RLCD (vs Atlas 2’s 4.4" colour)

| | Atlas 2 | Boat Atlas |
|--|---------|------------|
| Glass | Transflective **colour** + red backlight | **Reflective mono** RLCD |
| Sunlight | Good | **Excellent** (paper-like) |
| Power | Higher with backlight | **Lower** — no backlight |
| BOM | Proprietary / expensive | Glass **~$6–8**; kit **~$25** to learn UI |
| Night | Built-in backlight | LED cues; optional front-light **later** |

v1 accepts **no colour** and **weaker night** to win **sun + cost + power** for race day.

---

## Mechanical envelope (housing follows glass)

| Dimension | mm | Notes |
|-----------|-----|--------|
| Active area | **63.6 × 84.8** | Visible pixels |
| Window clear opening | ≥ **64 × 85** | Slightly over AA |
| Gasket land | +2–3 mm each side | IP67 compression |
| Waveshare board (proto) | ~**92.5 × 70 × 13.5** | Custom PCB can shrink; **glass still masters** |

**GoPro H9–13 cavity cannot take this panel.** Own IP67 shell only — [`../system-rlcd-housing.md`](../system-rlcd-housing.md).

---

## UI constraint

All pages are **300×400 mono** — [`ui-pages.md`](ui-pages.md).  
No colour, no backlight dimming for hierarchy — use size, invert, bars, LED.
