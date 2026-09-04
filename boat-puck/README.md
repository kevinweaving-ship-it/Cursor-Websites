# Boat Puck

**Own version of Vakaros — better and cheaper.** Fleet race management (cm RTK + LoRa mesh + OCS/line/start), not a Sailmon clone.

See [`NORTH_STAR.md`](NORTH_STAR.md).

**Primary boat product:** [`universal-puck.md`](universal-puck.md)

- **Puck** — GoPro-class case: small MCU + battery + RTK/LoRa/IMU; **no screen**; mount for sky  
- **Screen** — second GoPro-class case: small MCU + battery + back-cover LCD; mount anywhere; BLE to Puck  
- **Bigger boats** — same Puck + tablet / smartwatch / phone app  
- **Boat Atlas** — optional later own shell + 4.2" RLCD (`atlas/`)

## Docs

| Path | Content |
|------|---------|
| `NORTH_STAR.md` | Beat Vakaros — doctrine |
| `universal-puck.md` | **Two GoPro housings** — Puck + Screen; mount anywhere |
| `markets-dinghy-keelboat.md` | Markets vs Universal / Atlas |
| `PRICE_RULE.md` | Always show **R** and **($)** |
| `housing/` | H9–13 cavity; back-cover screen fit |
| `atlas/` | Optional future Atlas 2 class |
| `components-requirements.md` | Race-core BOM + committee base/hub |
| `display-rlcd-4.2-research.md` | 4.2" research (Atlas path) |
| `system-rlcd-housing.md` | Keelboat RLCD + own housing notes |

## Architecture (one line)

Committee RTK base → RTCM over LoRa → each boat FIX; boats → positions over LoRa → Race Control; sailor UI = optional **Screen** housing and/or BLE watch/phone/tablet → **Puck**.
