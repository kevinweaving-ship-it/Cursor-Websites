# Boat Puck

Cheap fleet race-management puck: **RTK rover** + **LoRa (SX1262)** + sailor UI, with an **RTK base on the committee boat**.

Two UI SKUs:

- **Cheap:** GoPro H9–13 shell + BLE → phone/watch  
- **Display:** 4.2" RLCD + **own IP67 housing** (does not fit GoPro)

## Docs

| Path | Content |
|------|---------|
| `housing/` | H9–13 cavity = camera; lens pocket → GPS antenna |
| `components-requirements.md` | Race-core BOM + committee base/hub |
| `display-rlcd-4.2-research.md` | Waveshare kit + factory panel suppliers & real $ |
| `system-rlcd-housing.md` | Full components + own housing when using RLCD |

## Architecture (one line)

Committee RTK base → RTCM over LoRa → each puck FIX; pucks → positions over LoRa → Race Control; sailor UI on phone/watch **or** on-boat 4.2" RLCD.
