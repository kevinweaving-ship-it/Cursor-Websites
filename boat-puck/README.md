# Boat Puck

**Own version of Vakaros — better and cheaper.** Fleet race management (cm RTK + LoRa mesh + OCS/line/start), not a Sailmon clone.

See [`NORTH_STAR.md`](NORTH_STAR.md).

Two markets → two boat SKUs (same race network):

1. **Dinghy** — GoPro / small puck + BLE → watch/phone (cost & weight)  
2. **Keelboat — Boat Atlas** — own IP67 + **4.2" RLCD** (our Atlas 2)

See `markets-dinghy-keelboat.md` and `atlas/`.

## Docs

| Path | Content |
|------|---------|
| `NORTH_STAR.md` | Beat Vakaros — doctrine |
| `markets-dinghy-keelboat.md` | Two markets → two SKUs |
| `atlas/` | **Boat Atlas** — our Atlas 2 (spec, UI, parity) |
| `housing/` | H9–13 cavity = camera; lens pocket → GPS antenna (dinghy) |
| `components-requirements.md` | Race-core BOM + committee base/hub |
| `display-rlcd-4.2-research.md` | Waveshare kit + factory panel suppliers & real $ |
| `system-rlcd-housing.md` | Keelboat components + own housing |

## Architecture (one line)

Committee RTK base → RTCM over LoRa → each boat FIX; boats → positions over LoRa → Race Control; dinghy UI on phone/watch, keelboat UI on 4.2" RLCD.
