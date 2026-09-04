# HERO9–13 housing — insert envelope & fit checklist

## Design box (provisional)

Internal usable volume is a **tight mold of the camera**. Until a cavity is calipered, design to the official/teardown camera chassis with margin.

| Parameter | Value | Source | Confidence |
|-----------|-------|--------|------------|
| Camera W × H × D | **71.8 × 50.8 × 33.6 mm** | Clifton / Hypoxic H13 (same as H9–12) | high (camera) |
| Alt community H×W | 71.0 × 55.0 × 33.6 mm | GoPro community articles | medium (rounding / fingers) |
| **Max insert (recommended)** | **≤ 70.0 × 49.0 × 32.0 mm** | camera − ~1 mm/side margin | provisional |
| Approx insert volume | ~**110 cm³** | 70×49×32 | provisional |
| Housing outer (ADDIV listing) | ~80 × 80 × 50 mm | Icecat / retailers | medium |
| Clone outer (Telesin GP-WTP-901) | 94 × 85 × 46 mm | Telesin listing | medium |
| Depth rating | 60 m (official WP backdoor) | GoPro | high |

**Working rule:** freeze PCBA + battery stack inside **70 × 49 × 32 mm**. If it fits that box, it should drop into ADDIV and most H9–13 clones.

## Axis convention (Boat Puck in housing)

Looking at the housing as mounted on a typical GoPro buckle (lens forward):

| Axis | Housing | Boat Puck intent |
|------|---------|------------------|
| **X** (W) | left–right, ~72 mm | PCB width |
| **Y** (H) | top–bottom, ~51 mm | PCB + battery height |
| **Z** (D) | front–back, ~34 mm | stack thickness (antennas / modules) |

Front = flat glass / lens tunnel. Rear = hinged backdoor + latch on top.

## Keep-outs (do not place hard parts here)

Until measured, treat these as **soft keep-outs** and verify on a physical shell:

1. **Lens tunnel (front centre)** — cylindrical boss behind glass. Leave clear or replace glass with blank plug if no camera.
2. **Button plungers** — typically top shutter, front/side mode. Either leave pockets or remove plungers for electronics-only use.
3. **Latch / hinge** — top rear latch and bottom hinge steal irregular volume; rear face is not a clean rectangle.
4. **Folding fingers (H9–13)** — camera fingers fold under; for a custom insert you can reclaim that volume (no fingers on a PCB brick).
5. **O-ring land** — do not press PCB/battery against the rear gasket face; leave ≥1 mm compress gap so the door seals.

## Fit checklist (print + bring to bench)

- [ ] Empty housing opens/closes; gasket clean; latch clicks fully
- [ ] Print or machine **70 × 49 × 32** dummy; insert without force
- [ ] With dummy in, backdoor closes and latch engages (no bulge)
- [ ] Measure leftover gap at: front glass, rear door, top latch, bottom hinge
- [ ] Mark plunger positions on dummy with marker through button holes
- [ ] Decide: keep plungers (need soft pads) vs remove (seal holes)
- [ ] GNSS antenna: clear sky path — plastic shell OK; avoid battery under patch ant
- [ ] SX1262 / BLE antenna: plastic OK; keep away from large ground pours & Li-ion pouch
- [ ] Pressure test / dunk test after cable glands / no open USB
- [ ] Mount: standard GoPro buckle / thumb-screw still usable with insert mass

## RF / waterproof notes (cheap path)

| Topic | Note |
|-------|------|
| Shell material | Polycarbonate + glass front — RF-friendly for LoRa/BLE/GNSS |
| Underwater RF | 2.4 GHz and GNSS die in water; surface/boat mount only for radio |
| Glass | Not needed for Boat Puck; optional blank for more internal Z or antenna window |
| Heat | No airflow; budget thermal for GNSS/MCU continuous RTK |
| Mount ecosystem | Huge used market for suckers, rail mounts, 3M, floaty |

## Component stack (first guess into 32 mm Z)

Suggest front→back:

1. Optional thin foam / antenna window at front  
2. GNSS patch or Cowin L1/L5 ceramic (sky-up when boat-mounted — orientation TBD)  
3. K902 (or equiv) + MCU PCB  
4. SX1262 module + BLE  
5. Li-ion pouch / 18650 flat cell (thickness limited)  
6. Foam crush pad at rear door  

Exact BOM fit is a later step; this folder only freezes the **mechanical envelope**.

## Update path after calipers

1. Edit `dimensions.json` → `confidence: "measured"`  
2. Replace provisional keep-out numbers in the SVG  
3. Regenerate SCAD `CAVITY_*` from measured values  
4. Re-print dummy; photo evidence into `boat-puck/housing/photos/` (optional)
