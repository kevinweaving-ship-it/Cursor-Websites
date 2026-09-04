# HERO9–13 — cavity = camera positive

## Doctrine

GoPro’s ADDIV protective housing is tooled as a **negative of the HERO9–13 camera**.

```
camera body (positive)  ≈  housing inside (negative)
```

Mold release clearance is **microns** (order ~0.05–0.1 mm), not millimetres.  
For Boat Puck packing: **use the exact camera dimensions as the internal housing dimensions.**

Do **not** shrink the envelope by an arbitrary 1 mm “safety” margin — that wastes volume and is not how the case was made.

## Authoritative positive / cavity

| Axis | mm | Notes |
|------|-----|--------|
| **W** | **71.8** | left–right |
| **H** | **50.8** | top–bottom (product spec; finger form factor) |
| **D** | **33.6** | lens front → rear screen / door |
| Volume | **~122.7 cm³** | bounding box |

**Source:** GoPro HERO9–13 *Design + Dimensions* product specs (shared chassis across 9–13).  
**Ignore** older community rounded figures (71.0 × 55.0 × 33.6) for packing.

## What Boat Puck fills

The insert’s **outer solid** should match the camera positive:

**71.8 × 50.8 × 33.6 mm**

Then **subtract** camera-shaped features you do not need (lens barrel, fingers, buttons) to free volume for PCB / battery / antennas.

| Feature on camera | Effect in housing | For Boat Puck |
|--------------------|-------------------|---------------|
| Lens + cover glass | Front tunnel / glass window | Void or blank plug; reclaim depth if blanked |
| Folding mount fingers | Bottom finger wells | No fingers → can fill wells or leave empty |
| Shutter / mode buttons | Housing plungers | Soft pads or remove plungers |
| Side battery door | Side relief | Can use as cable/antenna route later |
| Rear screen | Flat against backdoor | Foam crush pad + seal clearance |

## Optional print slip only

If 3D-printing a dummy or shell insert, a **print tolerance** of e.g. **−0.15 mm per side** may help it drop in. That is **printer accuracy**, not unknown cavity size.

| | W | H | D |
|--|---|---|---|
| Cavity / camera | 71.8 | 50.8 | 33.6 |
| Print slip example (−0.15/side, −0.3 on D) | 71.5 | 50.5 | 33.3 |

## Fit checklist

- [ ] CAD outer = **71.8 × 50.8 × 33.6** (or camera STEP if available)
- [ ] Print / machine positive; inserts and **latch closes fully**
- [ ] If tight: apply print slip only; do not redesign cavity smaller
- [ ] Mark plunger / lens keep-outs on the positive
- [ ] Boolean-subtract keep-outs; pack GNSS / radio / pack inside remaining solid
- [ ] Confirm O-ring uncompressed: rear face must not force the door open

## Axis

- **+Z** toward backdoor  
- **−Z** toward lens glass  
- **+Y** top (shutter)  
- **−Y** bottom (fingers / mount)
