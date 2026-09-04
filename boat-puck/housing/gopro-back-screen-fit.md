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

### Practical Boat Puck “back screen” targets

| Option | Fit in stock ADDIV backdoor? | Comment |
|--------|------------------------------|---------|
| **~2.0–2.3"** (≈48×32 class) | **Yes — easy** | Matches GoPro’s own rear LCD |
| **~2.4–2.8"** if AA ≤ ~60×40 | **Maybe** | Needs bezel check; stay under rear glass **62.7×41.7** |
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
| **Universal Puck** (primary) | GoPro H9–13 / Ace class | **Back-cover LCD ~2.0–2.8"** (required) |
| **Bigger boats** | Same puck | Same back LCD + **tablet / watch / phone** app |
| **Boat Atlas** (later) | Own IP67 | **4.2" RLCD** (does not fit GoPro back) |

See [`../universal-puck.md`](../universal-puck.md).  
**Puck + back screen** = Universal. **4.2" own shell** = optional Atlas later.
