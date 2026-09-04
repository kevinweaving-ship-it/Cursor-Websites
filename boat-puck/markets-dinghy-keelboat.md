# Boat Puck — markets (updated for Universal Puck)

North star: [`NORTH_STAR.md`](NORTH_STAR.md).  
**Primary boat SKU:** [`universal-puck.md`](universal-puck.md).

Same **race network** (committee RTK base + LoRa + Race Control).  
**One** boat-side puck from Optimist through bigger boats. Scale the UI with BLE clients — not a second housing.

| | **Universal Puck** | **Bigger-boat add-ons** | **Boat Atlas (later)** |
|--|--------------------|-------------------------|-------------------------|
| Who | Opti → youth/Olympic dinghies → small keelboats | Keelboat helm / nav | Buyers who want on-device big glass |
| Offer | Action-cam case + **back-cover screen** + race core | **Tablet / smartwatch / phone app** → same puck | Own IP67 + 4.2" RLCD |
| Housing | **Largest common action-cam waterproof case** (H9–13 class) | — | Custom shell |
| Sailor UI | Back LCD (aft on mast) | Large digits / pages on tablet or watch | On-device RLCD |
| Mount | Mast / rail / clamp (class adapters) | Same puck, different plate | Pedestal / bulkhead |

---

## Shared (do not fork the radio)

- cm RTK from **committee base** over LoRa  
- Sync start, live line, OCS, finish, scoring  
- Same boat ID / bow offset / FIX quality uplink  

**One Race Control. One Universal Puck. Companion apps scale the glass.**

```
                    ┌─ Committee (one set per venue) ─┐
                    │  RTK base · LoRa hub · RC app   │
                    └──────────────┬──────────────────┘
                                   │ LoRa
                                   ▼
                          UNIVERSAL PUCK
                     (action-cam · back LCD)
                                   │ BLE
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
                 Watch          Phone          Tablet
```

---

## What we skip (for Universal v0)

| Skip | Why |
|------|-----|
| 4.2" in the puck | Does not fit action-cam backdoor; use tablet |
| Junction-box / Pelican as product shell | Looks proto, not production |
| Phone dive cases | Too thin for full stack |
| Osmo 360 / Action as compute host | No custom app on camera screen |
| Separate dinghy-only “no screen” SKU | Back-cover LCD is standard on Universal |

---

## Go-to-market order

1. **Universal Puck** in H9–13-class case — Opti fleets + shared mounts.  
2. **BLE watch + phone app**, then **tablet** layout for bigger boats.  
3. **Boat Atlas** only if demand wants built-in 4.2" (`atlas/`).

Firmware and Race Control stay shared.
