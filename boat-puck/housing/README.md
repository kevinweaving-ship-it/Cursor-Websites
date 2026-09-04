# Boat Puck — GoPro housing pack (cheap enclosure path)

Reuse commodity GoPro waterproof housings instead of custom IP67 tooling for early Boat Puck prototypes.

## Status

| Item | Status |
|------|--------|
| Published camera / outer dims | Captured |
| Official internal CAD from GoPro | **Does not exist** |
| Provisional insert envelope | This folder |
| Physical caliper / scan of empty cavity | **TODO** (required before PCB freeze) |

## Target housing (most common)

**GoPro Protective Housing ADDIV-001 / ADDIV-001-VT** (and clones e.g. Telesin GP-WTP-901)  
Compatible: **HERO9 / 10 / 11 / 12 / 13** (shared chassis).

Secondary (cheaper / smaller): HERO4 Standard Housing ± BacPac deep backdoor — see `gopro-h4-notes.md`.

## Files

| File | Purpose |
|------|---------|
| `gopro-h9-13-envelope.md` | Fit checklist, volumes, keep-outs, RF notes |
| `gopro-h9-13-keepout.svg` | 2D keep-out sketch (top / front / side) |
| `gopro-h9-13-envelope.scad` | Parametric max insert + optional print dummy |
| `gopro-h4-notes.md` | Smaller H4 path + BacPac depth hack |
| `dimensions.json` | Machine-readable dims for CAD/scripts |

## Next physical step

1. Buy one official ADDIV + one cheap Telesin clone.
2. Caliper empty cavity XYZ, lens boss, button plungers, latch intrusion.
3. Update `dimensions.json` `confidence` from `provisional` → `measured`.
4. Print `envelope_dummy()` from the SCAD and drop-fit test.
