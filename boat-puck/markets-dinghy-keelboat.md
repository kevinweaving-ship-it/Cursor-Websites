# Boat Puck — markets (updated for Universal Puck)

North star: [`NORTH_STAR.md`](NORTH_STAR.md).  
**Primary boat SKU:** [`universal-puck.md`](universal-puck.md) — **two** GoPro housings (Puck + optional Screen), mount anywhere.

Same **race network** (committee RTK base + LoRa + Race Control).  
Scale UI with BLE clients (Screen housing, watch, phone, tablet) — not a second radio.

| | **Puck** | **Screen** | **Bigger-boat apps** | **Boat Atlas (later)** |
|--|----------|------------|----------------------|-------------------------|
| Who | Every boat on the mesh | Helm who wants local digits | Keelboat helm / nav | Buyers who want big on-device glass |
| Offer | MCU + battery + RTK + LoRa + IMU | MCU + battery + back LCD | Tablet / watch / phone → Puck | Own IP67 + 4.2" RLCD |
| Housing | Action-cam case, **no screen** | Second action-cam case | — | Custom shell |
| Mount | Sky / mesh friendly | Anywhere eyes are | — | Pedestal / bulkhead |

---

## Shared (do not fork the radio)

- cm RTK from **committee base** over LoRa  
- Sync start, live line, OCS, finish, scoring  
- Same boat ID / bow offset / FIX quality uplink  

**One Race Control. One Puck radio. Screen / apps are optional glass.**

```
                    ┌─ Committee (one set per venue) ─┐
                    │  RTK base · LoRa hub · RC app   │
                    └──────────────┬──────────────────┘
                                   │ LoRa
                                   ▼
                         PUCK (GoPro · no screen)
                                   │ BLE
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
        SCREEN housing         Watch / phone         Tablet
        (GoPro · LCD)          (optional)            (bigger boats)
```

---

## What we skip (for Universal v0)

| Skip | Why |
|------|-----|
| One brick with guts + glass | Depth fight; mount compromise — use two housings |
| 4.2" in either case | Does not fit; use tablet or later Atlas |
| Junction-box / Pelican as product shell | Looks proto, not production |
| Phone dive cases | Too thin for full stack |
| Osmo 360 / Action as compute host | No custom app on camera screen |

---

## Go-to-market order

1. **Puck** in H9–13-class case (no screen) — Opti fleets + shared mounts.  
2. **Screen** housing (second case) — optional; BLE to Puck.  
3. **BLE watch + phone app**, then **tablet** for bigger boats.  
4. **Boat Atlas** only if demand wants built-in 4.2" (`atlas/`).

Firmware and Race Control stay shared.
