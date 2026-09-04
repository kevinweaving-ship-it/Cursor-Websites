# Boat Puck

Cheap fleet race-management puck: **GoPro H9–13 housing** + **RTK rover** + **LoRa (SX1262)** + BLE display, with an **RTK base on the committee boat**.

## Docs

| Path | Content |
|------|---------|
| `housing/` | H9–13 cavity = camera; lens pocket → GPS antenna |
| `components-requirements.md` | What goes in the box + committee base/hub |

## Architecture (one line)

Committee RTK base → RTCM over LoRa → each puck FIX; pucks → positions over LoRa → Race Control; sailor UI on phone/watch via BLE.
