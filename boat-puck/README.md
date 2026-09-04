# Boat Puck

Cheap fleet race-management puck: **RTK rover** + **LoRa (SX1262)** + sailor UI, with an **RTK base on the committee boat**.

Two markets → two boat SKUs (same race network):

1. **Dinghy** — GoPro / small puck + BLE → watch/phone (cost & weight)  
2. **Keelboat** — own IP67 housing + **4.2" RLCD** (cockpit instrument)

See `markets-dinghy-keelboat.md`.

## Docs

| Path | Content |
|------|---------|
| `markets-dinghy-keelboat.md` | Two markets → two SKUs |
| `housing/` | H9–13 cavity = camera; lens pocket → GPS antenna (dinghy) |
| `components-requirements.md` | Race-core BOM + committee base/hub |
| `display-rlcd-4.2-research.md` | Waveshare kit + factory panel suppliers & real $ |
| `system-rlcd-housing.md` | Keelboat components + own housing |

## Architecture (one line)

Committee RTK base → RTCM over LoRa → each boat FIX; boats → positions over LoRa → Race Control; dinghy UI on phone/watch, keelboat UI on 4.2" RLCD.
