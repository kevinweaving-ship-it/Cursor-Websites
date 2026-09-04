# Boat Puck

**Own version of Vakaros — better and cheaper.** Fleet race management (cm RTK + LoRa mesh + OCS/line/start), not a Sailmon clone.

See [`NORTH_STAR.md`](NORTH_STAR.md).

**Primary boat product:** [`universal-puck.md`](universal-puck.md)

```
1. Universal Puck (GoPro)     required — no screen
2. Screen options (BLE → Puck), any mix:
   a. Screen in GoPro
   b. Waterproof tablet
   c. Smartwatch
```

- **Boat Atlas** — optional later own shell + 4.2" RLCD (`atlas/`)


## Docs

| Path | Content |
|------|---------|
| `NORTH_STAR.md` | Beat Vakaros — doctrine |
| `universal-puck.md` | Product tree: Puck + screen options 2a/2b/2c |
| `vakaros-gnss-board-id.md` | Atlas 2 GNSS fingerprint → Sony CXD5610 / Telit SE868SY-D class |
| `gnss-50hz-lock.md` | Puck GNSS ≥50 Hz (UM980); reject LC29H/LG290P |
| `puck-components-buy-list.md` | **Puck parts + prices + buy URLs** |
| `bom-puck-screen-cost.md` | Cost summary Puck vs Screen (loud speaker on 2a) |
| `markets-dinghy-keelboat.md` | Markets vs Universal / Atlas |
| `PRICE_RULE.md` | Always show **R** and **($)** |
| `housing/` | H9–13 cavity; back-cover screen fit |
| `atlas/` | Optional future Atlas 2 class |
| `components-requirements.md` | Race-core BOM + committee base/hub |
| `display-rlcd-4.2-research.md` | 4.2" research (Atlas path) |
| `system-rlcd-housing.md` | Keelboat RLCD + own housing notes |

## Architecture (one line)

Committee RTK base → RTCM over LoRa → each boat FIX; boats → positions over LoRa → Race Control; sailor UI = **2a Screen** and/or **2b tablet** and/or **2c watch** → **Puck**.
