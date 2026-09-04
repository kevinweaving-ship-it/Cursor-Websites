# Boat Puck — GoPro H9–13 housing (cheap enclosure)

Primary shell: **Protective Housing ADDIV-001** (and clones) for **HERO9–13**.

## Core rule

The waterproof housing is a **tight negative of the camera**.

| | |
|--|--|
| **Positive** | GoPro HERO9–13 camera body CAD / published dims |
| **Negative** | Housing internal cavity |
| **Clearance** | Mold release only — **microns**, not millimetres |

So the **exact camera dimensions are the exact inside dimensions** of the housing (for packing purposes). Do not invent a smaller “guess” cavity.

## Authoritative positive (shared H9–13 chassis)

**71.8 W × 50.8 H × 33.6 D mm**  
GoPro product specs (HERO9–13); weight listings include mounting fingers on the same chassis.

## Files

| File | Purpose |
|------|---------|
| `gopro-h9-13-envelope.md` | Envelope doctrine + fit checklist |
| `dimensions.json` | Machine-readable cavity = camera |
| `gopro-h9-13-keepout.svg` | 2D views at exact camera size |
| `gopro-h9-13-envelope.scad` | Exact positive solid for CAD / print |
| `gopro-h4-notes.md` | Secondary smaller housing (not primary) |

## Next

1. Prefer a real H9–13 **STEP/STL body** as the insert outer (best).  
2. Or print the SCAD `camera_positive()` brick at **71.8 × 50.8 × 33.6** and confirm latch close.  
3. Subtract keep-outs (lens boss, plungers) from that positive for the electronics solid.
