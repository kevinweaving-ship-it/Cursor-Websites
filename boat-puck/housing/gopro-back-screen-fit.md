# GoPro H9–13 — back / backdoor screen pocket

Question: *If we put a smaller screen in the GoPro box back cover, what size fits?*

## Important: the “back” is not a deep box

```
[ front glass + lens/GPS pocket ~5.5 mm ]
[        main body cavity                ]  ← electronics live here
[ rear LCD face flat against backdoor    ]
[ waterproof BACKDOOR = thin window + O-ring ]  ← not a thick compartment
```

The removable **backdoor** is mostly glass/plastic window + seal.  
A display does **not** go *inside the door* — it sits on the **rear face of the insert**, looking out through the door window (same as a real GoPro screen).

---

## Full inside (whole puck)

| | mm |
|--|-----|
| **W × H × D** | **71.8 × 50.8 × 33.6** |
| Equals | HERO9–13 camera body (housing cavity) |

---

## Rear face — what a screen can use

From GoPro’s own HERO11 rear geometry (same chassis family as 9–13):

| Feature | Size (mm) | Notes |
|---------|-----------|--------|
| **Full rear face of insert** | **71.8 × 50.8** | Absolute max outline |
| **Rear glass / window area** (GoPro) | **62.7 × 41.7** | Practical visible through backdoor |
| **Active LCD** (GoPro stock) | **48.0 × 32.0** (~2.27") | What they actually drive |
| Depth for display stack | typically **~2–4 mm** | Then rest of 33.6 mm = PCB/battery/radio toward front |

### Space around the screen (lid margins)

Assume centred AA in the **rear window** (not the full 71.8×50.8 face — the door frame eats the edge).

| Ring | Size (mm) | Border each side (W / H) |
|------|-----------|---------------------------|
| Insert rear face | 71.8 × 50.8 | — |
| Visible backdoor window | 62.7 × 41.7 | **~4.6 / ~4.6** from face edge to glass |
| Stock GoPro active (~2.27", 48×32) | 48.0 × 32.0 | **~7.4 / ~4.9** glass → AA |
| Face edge → stock AA (total) | — | **~11.9 / ~9.4** |

So on a **~2.0–2.3"** (48×32 class) you get roughly **7–8 mm** left/right and **~5 mm** top/bottom of clear window around the active area, plus another **~4.5 mm** of plastic lid frame outside the glass.

| Target AA (approx) | Diagonal | Glass → AA each side (W / H) | Verdict |
|--------------------|----------|------------------------------|---------|
| 48 × 32 | ~2.27" | **7.4 / 4.9** | Comfortable (stock) |
| ~43 × 29 | ~2.0" | **~10 / ~6** | Plenty of bezel |
| ~55 × 37 | ~2.5" | **~3.9 / ~2.4** | Tight but usable |
| ~60 × 40 | ~2.8" | **~1.4 / ~0.9** | Almost flush — no room for seal/print error |
| > 62.7 × 41.7 | — | negative | Clipped by lid window |

**Rule:** keep AA ≤ **~55×37 (~2.5")** if you want a few mm of dark bezel; treat **2.8"** as max theoretical, not a comfortable buy.

---

## Small screen + board (no ESP32)

ESP32-on-glass kits are too big. Use a **SPI TFT/OLED module** (driver IC on the LCD FPC/PCB only). MCU lives on the **main puck board**.

Lid window budget: **62.7 × 41.7 mm**. Board must sit ≤ that (or ≤ **71.8 × 50.8** face if you accept clipping under the frame — avoid).

| Module (examples) | AA mm | Board mm | Fit window? |
|-------------------|-------|----------|-------------|
| Waveshare **1.54"** SPI ST7789 | 27.7 × 27.7 | **50.0 × 35.0** | **Yes** — easy |
| Waveshare **2.0"** SPI ST7789 | 30.6 × 40.8 | **58.0 × 35.0** | **Yes** — best size match |
| Waveshare **1.69"** SPI | 28.0 × 32.6 | **31.5 × 39.0** | **Yes** — small |
| Bare 1.54" panel+FPC (no big PCB) | 27.7 × 27.7 | outline ~**32 × 35** | **Yes** — thinnest |
| Waveshare **2.4"** SPI | 36.7 × 49.0 | **70.5 × 43.3** | **No** — board > window |
| Any **ESP32 + LCD** all-in-one | — | typically ≥70–80+ | **No** |

**v0 buy:** Waveshare **2inch LCD Module** (SPI only, not ESP32) — board **58 × 35 mm**, AA **30.6 × 40.8 mm**.  
**Better later:** FPC-only glass; ST7789 on main PCB so nothing thick under the lid.

### Practical Boat Puck “back screen” targets

| Option | Fit in stock ADDIV backdoor? | Comment |
|--------|------------------------------|---------|
| **~2.0–2.3"** (≈48×32 class) | **Yes — easy** | ~5–8 mm glass margin; matches GoPro rear LCD |
| **~2.4–2.5"** if AA ≤ ~55×37 | **Yes — tight** | ~2–4 mm glass margin |
| **~2.8"** if AA ≤ ~60×40 | **Maybe** | &lt;1.5 mm margin — caliper real door first |
| **4.2" RLCD** AA **63.6×84.8** | **No** | Longer side **84.8 > 71.8**; needs own housing (Boat Atlas) |

---

## Depth split if screen is on the back

Example packing (front → back), total **D = 33.6 mm**:

| Layer | Depth | Use |
|-------|-------|-----|
| Front GPS pocket | ~5.5 mm | Antenna to front glass |
| Main electronics | ~24–26 mm | GNSS, LoRa, MCU, battery |
| Rear display + foam | ~2–4 mm | Small LCD against backdoor |

O-ring must still close — rear stack must not force the door open.

---

## Product meaning

| Product | Shell | Screen |
|---------|-------|--------|
| **Puck** | GoPro H9–13 / Ace class | **None** (full cavity for radio/battery) |
| **Screen** | Second GoPro H9–13 / Ace class | **Back-cover LCD ~2.0–2.8"** |
| **Bigger boats** | Same Puck | Screen housing and/or **tablet / watch / phone** app |
| **Boat Atlas** (later) | Own IP67 | **4.2" RLCD** (does not fit GoPro back) |

See [`../universal-puck.md`](../universal-puck.md).  
Two housings; Screen is optional. **4.2" own shell** = Atlas later.
