# Boat Puck — two markets

North star: [`NORTH_STAR.md`](NORTH_STAR.md) — **better Vakaros**, not Sailmon.

Same **race network** (committee RTK base + LoRa + Race Control).  
Two **boat-side products** because dinghies and keelboats buy for different jobs.

| | **1. Dinghy** | **2. Keelboat** |
|--|---------------|-----------------|
| Who | Fleet / club / youth / Olympic-pathway dinghies | Yacht clubs, keelboat fleets, match / inshore |
| Pain | Cost, weight, spray, no place for a big instrument | Want a **cockpit instrument** + fleet race tools |
| Competitor shadow | HALO (sensors) + phone; Atlas is often “too much / too dear” | **Atlas 2** / Sailmon MAX on the boat |
| Our offer | **Sensor puck** — cheap, tiny, tough | **Boat Atlas** — sunlight UI + same race core |
| Housing | **GoPro H9–13** (or small own shell) | **Own IP67** shell with **4.2" RLCD** |
| Sailor UI | **BLE → watch / phone** | **On-device RLCD** (+ BLE still useful) |
| Mount | Transom / mast / hiking strap / rail clamp | Pedestal / bulkhead / tiller / rail |
| BOM priority | Antenna + RTK + LoRa + IMU; **no glass** | Same core **+** ST7305 + window + keys |
| Price posture | Undercut HALO-class stack hard | Undercut Atlas+HALO; still far under Sailmon+race kit |

---

## Shared (do not fork the radio)

Both markets need identical fleet behaviour:

- cm RTK from **committee base** over LoRa (no cellular for critical)
- Sync start, live line, OCS, finish, scoring
- Same boat ID / bow offset / FIX quality uplink

**One Race Control. Two boat SKUs.** That is how we stay Vakaros-like without forcing dinghy sailors to buy a keelboat instrument.

---

## Product mapping

```
                    ┌─ Committee (one set per venue) ─┐
                    │  RTK base · LoRa hub · RC app   │
                    └──────────────┬──────────────────┘
                                   │ LoRa
              ┌────────────────────┼────────────────────┐
              ▼                                         ▼
     DINGHY SKU                                  KEELBOAT = Boat Atlas
     GoPro / small puck                          Own housing + 4.2" RLCD
     BLE watch/phone                             Digits on glass (+ BLE)
     Max cost/weight kill                        Our Atlas 2
```

Docs:

- Dinghy mechanical → `housing/`
- Boat Atlas (Atlas 2 class) → `atlas/`
- Keelboat display + housing → `display-rlcd-4.2-research.md`, `system-rlcd-housing.md`
- Shared electronics checklist → `components-requirements.md`

---

## What each market does *not* need

| Skip for dinghy | Skip for keelboat (v1) |
|-----------------|-------------------------|
| 4.2" display, thick own shell | Fancy NMEA wind/BSP hub (Sailmon extras) |
| Voice / AI mics | Mandatory phone for race-critical UI |
| Colour IPS / backlight | GoPro look-and-feel |

---

## Go-to-market order (suggested)

1. **Dinghy first** — prove RTK+LoRa+OCS in GoPro envelope; club fleets feel cost win.  
2. **Boat Atlas (keelboat)** — same radio firmware; RLCD + own housing (`atlas/`).

Firmware and Race Control stay shared; only housing + display BOM diverge.
