# Boat Puck

**Own version of Vakaros — better and cheaper.** Fleet race management (cm RTK + LoRa mesh + OCS/line/start), not a Sailmon clone.

See [`NORTH_STAR.md`](NORTH_STAR.md).

**Primary boat product:** [`universal-puck.md`](universal-puck.md)

- **Universal Puck** — biggest common **action-cam** waterproof case, **screen on back cover**, Opti → bigger boats  
- **Bigger boats** — same puck + **tablet / smartwatch / phone** app over BLE  
- **Boat Atlas** — optional later own shell + 4.2" RLCD (`atlas/`)

## Docs

| Path | Content |
|------|---------|
| `NORTH_STAR.md` | Beat Vakaros — doctrine |
| `universal-puck.md` | **One puck** Opti→bigger; back LCD; BLE scale-up |
| `markets-dinghy-keelboat.md` | Markets vs Universal / Atlas |
| `PRICE_RULE.md` | Always show **R** and **($)** |
| `housing/` | H9–13 cavity; back-cover screen fit |
| `atlas/` | Optional future Atlas 2 class |
| `components-requirements.md` | Race-core BOM + committee base/hub |
| `display-rlcd-4.2-research.md` | 4.2" research (Atlas path) |
| `system-rlcd-housing.md` | Keelboat RLCD + own housing notes |

## Architecture (one line)

Committee RTK base → RTCM over LoRa → each boat FIX; boats → positions over LoRa → Race Control; sailor UI = puck **back-cover LCD** + optional BLE watch/phone/tablet.
