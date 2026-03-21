# Podium Template – GPT / Cursor Instructions

## ✅ FILE YOU ALREADY HAVE (LOCK THIS)

**Filename:** `assets/podium/master-podium.png`

**Rules (do not break):**
- Never modify this file
- Never write text into it manually
- Never regenerate it
- Cursor only overlays text on top

---

## 📐 TEXT OVERLAY ZONES (LOCKED)

Define these ONCE. Cursor must not move them.

| Zone   | x    | y    | w   | h   | Plaque              |
|--------|------|------|-----|-----|---------------------|
| ZONE_1ST | 1240 | 860  | 760 | 220 | blue plaque – centre |
| ZONE_2ND | 360  | 980  | 620 | 190 | silver plaque – left |
| ZONE_3RD | 2140 | 1000 | 600 | 180 | bronze plaque – right |

**Canvas size:** 3000 × 2000 px

---

## 🧾 EXACT TEXT FORMAT (NO VARIATION)

Cursor must render exactly this, line-for-line:

```
SAILOR NAME
Sail 1234 · HYC
Races: 12
Total: 20.0 · Net: 14.0
```

**Rules:**
- Center aligned
- Same font for all three
- No icons
- No emojis
- No wrapping
- If text too long → reduce font size slightly

---

## 🧠 CURSOR – MASTER INSTRUCTION

Use the image `assets/podium/master-podium.png` as a fixed background.

For a given regatta and class:
1. Fetch results ordered by net score
2. Select positions 1, 2, and 3 only

Overlay sailor data as centered text in the predefined plaque zones:
- 1st place → ZONE_1ST
- 2nd place → ZONE_2ND
- 3rd place → ZONE_3RD

**Do not:**
- Alter the background image
- Change layout, colours, or proportions
- Add or remove elements

**Export:** New PNG at full resolution. One image per class.

---

## 🧩 CODE (Python – PIL)

```python
from PIL import Image, ImageDraw, ImageFont

# --- CONFIG ---
MASTER_IMAGE = "assets/podium/master-podium.png"
OUTPUT_IMAGE = "output/podium_optimist_a.png"

FONT_PATH = "assets/fonts/LibreBaskerville-Regular.ttf"
FONT_SIZE = 42
FONT_COLOR = (20, 20, 20)  # dark slate

ZONES = {
    "1st": (1240, 860, 760, 220),
    "2nd": (360,  980, 620, 190),
    "3rd": (2140, 1000, 600, 180),
}
```

---

## 📁 RECOMMENDED FOLDER STRUCTURE

```
assets/
  podium/
    master-podium.png
  fonts/
    LibreBaskerville-Regular.ttf

output/
  podiums/
    sa-youth-nats-2025/
      optimist-a.png
      optimist-b.png
      ilca-4.png
```
