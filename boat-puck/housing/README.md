# Boat Puck — GoPro H9–13 housing (Universal Puck shell)

**Universal kit** uses **two** of the biggest common action-cam waterproof cases (production look) — **Protective Housing ADDIV-001** (and clones) for **HERO9–13**, or Ace Pro 60 m:

| Housing | Role |
|---------|------|
| **Puck** | MCU + battery + RTK/LoRa/IMU — **no screen** |
| **Screen** | MCU + battery + back-cover LCD — BLE to Puck |

Doctrine: [`../universal-puck.md`](../universal-puck.md). Sailor mounts each **anywhere**.

## Core rule

The waterproof housing is a **tight negative of the camera**.

| | |
|--|--|
| **Positive** | GoPro HERO9–13 camera body (published dims / CAD) |
| **Negative** | Housing internal cavity |
| **Clearance** | Mold release only — **microns**, not millimetres |

So the **exact camera dimensions are the exact inside dimensions** of the housing for packing. Do not invent a smaller “guess” cavity.

## Authoritative positive (shared H9–13 chassis)

**71.8 W × 50.8 H × 33.6 D mm**  
GoPro product Design + Dimensions (HERO9–13 shared chassis).

## Front lens → GPS pocket

Stock protective lens sticks out **~5–6 mm** past the front face (~**Ø33 / 31.5×31.5 mm**).  
That housing tunnel is the **GPS antenna well** — see `gopro-h9-13-lens-gps-pocket.md`.

Working target until calipers: **Ø32 × 5.5 mm** deep (antenna stack ≤ **5.0 mm** thick).

## Files

| File | Purpose |
|------|---------|
| `gopro-h9-13-envelope.md` | Doctrine + fit checklist |
| `gopro-h9-13-lens-gps-pocket.md` | Lens protrusion + GPS antenna volume |
| `gopro-back-screen-fit.md` | What size screen fits the **backdoor / rear face** |
| `alternate-waterproof-housings.md` | Common dive/phone housings vs 4.2" + puck depth |
| `dimensions.json` | Machine-readable cavity = camera + lens pocket |
| `gopro-h9-13-keepout.svg` | 2D views at exact camera size |
| `gopro-h9-13-envelope.scad` | Exact positive solid + lens boss |
| `gopro-h4-notes.md` | Secondary smaller housing (not primary) |

## Next

1. Caliper real H9–13 protective lens protrusion + housing tunnel.  
2. Prefer a real H9–13 **STEP/STL body** as the insert outer.  
3. Pack GNSS ceramic/PCB into the front lens pocket facing the glass.
