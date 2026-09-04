# HERO9–13 front lens protrusion → GPS antenna pocket

## Why this matters

The waterproof housing’s front window is molded around the **removable protective lens** that sticks out of the H9–13 body.  
That forward pocket is wasted for Boat Puck optics — we use it for a **GNSS / GPS antenna** looking out through the flat glass.

```
[ housing front glass ]
        ↑ small air gap
[ protective lens tip ]  ← farthest forward on camera
        ↑ protrusion depth  ≈ 5–6 mm
[ camera front face / LCD plane ]
        ↑ body depth
[ rear screen ]
```

Overall published camera depth **33.6 mm already includes** this lens stick-out.

## Best available numbers (H9–12 stock protective lens)

GoPro does **not** publish a separate “lens protrusion” CAD callout. Values below are from community calipers / accessory fit data for the **stock protective lens** shared by HERO9–12 (H13 cover is ~1 mm wider, slightly thinner — Hypoxic).

| Parameter | Value | Confidence | Source |
|-----------|-------|------------|--------|
| **Protrusion past front face** | **~5–6 mm** | medium | Forum calipers: ~6 mm height; silicone-cap stack listed **5 mm** deep |
| **Outer footprint (lens module)** | **~31.5 × 31.5 mm** | medium | H9 silicone-cap / lens-housing listing |
| **Outer diameter (approx)** | **~33 mm** | medium | Community “3.3 cm” outer measure |
| Camera total D (with lens) | **33.6 mm** | high | GoPro product specs |
| Implied body depth without lens tip | **~27.6–28.6 mm** | derived | 33.6 − (5…6) |
| H13 stock cover | **~+1 mm wider, slightly thinner** | medium | Hypoxic H13 teardown |

### Working design target for GPS pocket (until calipers)

Use this as the **first-pass antenna volume** inside the ADDIV housing:

| | |
|--|--|
| **Pocket diameter / square** | **Ø 32 mm** usable (design to ≤ 30 mm antenna so it clears walls) |
| **Pocket depth** | **5.5 mm** nominal (range 5–6 mm) |
| **Usable antenna stack** | **≤ 5.0 mm** thick including foam/adhesive (leave ~0.5 mm to glass) |
| **Sky window** | Housing flat glass — RF-friendly plastic/glass; mount antenna face toward glass |

**Volume ≈** π × (15 mm)² × 5.5 mm ≈ **3.9 cm³** for a Ø30 × 5.5 cylinder — enough for a small ceramic patch (e.g. 15×15×4 or 18×18×4) or a custom PCB antenna, **not** a large 25×25×6 stack without thinning the ground/foam.

## What sticks out (parts)

1. **Bayonet protective lens / cover glass** (removable) — this is the main protrusion the housing tunnels around.  
2. **Underlying fixed optic** — sits deeper; with cover removed the camera is still usable but shallower for accessories.  
3. **Max Lens Mod / HB mods** — much deeper (~20 mm package for Max Lens Mod listing); **do not** size the stock ADDIV pocket from Max Lens Mod. Stock housing is for the **standard protective lens**, not Max Lens Mod.

For Boat Puck we assume **stock protective-lens envelope** only.

## GPS packaging notes

| Topic | Guidance |
|-------|----------|
| Orientation | Antenna radiating face toward housing front glass (sky when boat-mounted upright — confirm mount attitude) |
| Ground plane | Keep copper ground behind/around patch per antenna datasheet; may sit in body volume behind the pocket |
| Metal | No metal plate between antenna and glass |
| Foam | Thin PORON/foam crush pad to glass; do not crush ceramic |
| Cable | Feed into main 71.8×50.8×33.6 body toward K902 / GNSS module |
| H13 housings | If using H13-specific cover geometry, re-caliper — cover is slightly wider |

## Must measure on bench (lock these)

Print this checklist on the physical camera + empty ADDIV:

- [ ] Caliper **protrusion**: front LCD glass plane → protective lens front glass tip  
- [ ] Caliper **lens module OD** (or W×H if square)  
- [ ] Caliper **housing tunnel ID** and **depth** glass-inner → body stop  
- [ ] Measure **air gap** lens tip → housing glass (should be small)  
- [ ] Update `dimensions.json` → `confidence: "measured"`

Until then treat **5.5 mm × Ø32 mm** as the provisional GPS well.
