# Universal Puck — Opti → bigger boats

**One boat-side product.** Same puck from Optimist through larger dinghies and small keelboats.  
Bigger boats do **not** get a different brick — they add **tablet / smartwatch / phone** over BLE to the same puck.

North star: [`NORTH_STAR.md`](NORTH_STAR.md).

---

## Product lock

| | |
|--|--|
| **SKU** | **Universal Puck** (one electronics + one shell family) |
| **Shell** | **Biggest common action-cam waterproof case** that still looks like a finished product (not a junction box) |
| **Screen** | **On the back cover** — rear face looking out the backdoor window (helm / aft view when mast-mounted) |
| **Range** | Optimist → 420 / ILCA / 29er / similar → small keelboats |
| **Scale-up UI** | Tablet and/or smartwatch (and phone) **app connected to the puck** over BLE |
| **Not v0** | Custom Atlas-thin shell, 4.2" RLCD, phone dive cases, Osmo 360 as host |

```
                    Committee RTK + LoRa + Race Control
                                    │
                                    ▼
                         ┌─ UNIVERSAL PUCK ─┐
                         │ action-cam case  │
                         │ guts: RTK·LoRa·  │
                         │ IMU·MCU·battery  │
                         │ back-cover LCD   │
                         └────────┬─────────┘
                                  │ BLE
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
         Opti helm            Watch               Tablet / phone
         (reads back LCD)     (digits/alerts)     (big boat UI)
```

---

## Why action-cam case (production look)

| Goal | Choice |
|------|--------|
| Looks bought, not DIY | Stock **GoPro HERO9–13 class** protective housing (+ clones / Ace Pro 60 m same class) |
| Mount ecosystem | Finger / rail / mast straps already exist; clubs know the shape |
| Waterproof | Dive-rated housing, not IP65 wall box |
| Biggest common | H9–13 chassis **71.8 × 50.8 × 33.6 mm** is the large shared action-cam envelope; Ace Pro is not meaningfully bigger |

Reject for this SKU: Pelican / ZP junction boxes (proto-only), phone dive cases (too thin), Osmo 360 (wrong mold, no custom app on camera).

Detail: [`housing/`](housing/), especially [`housing/gopro-back-screen-fit.md`](housing/gopro-back-screen-fit.md).

---

## Back-cover screen

- Display sits on the **rear face of the insert**, through the **backdoor window** (same as a real GoPro LCD).
- Practical size: **~2.0–2.8"** (stock GoPro rear glass ~**62.7 × 41.7 mm**; stock active ~**48 × 32 mm**).
- **4.2" does not fit** this case — deferred; big-boat digits live on **tablet/watch app**.

Mount orientation (Opti and mast boats):

- Mast clamp / hose clamp / Velcro + flat plate  
- **Screen aft** (helm reads the back cover)  
- Below boom / clear of jaw (Opti mast **Ø 45 ± 0.5 mm**)  
- Do not put the fat face into the sail on the stern side of the mast  

---

## Class ladder (same puck)

| Class band | How the sailor uses it |
|------------|-------------------------|
| **Optimist** | Puck on mast (aft screen); optional watch |
| **ILCA / 420 / 29er / youth fleets** | Same mast/rail mount; back LCD + watch |
| **Bigger boats** | Same puck (rail / bulkhead / pedestal adapter); **tablet and/or smartwatch app** for large UI; back LCD still works as local glance |

Firmware, boat ID, RTK/LoRa behaviour: **identical**. Only mount plate and companion app layout change.

---

## Companion app (bigger boats)

BLE from puck →:

| Client | Job |
|--------|-----|
| **Smartwatch** | Speed, start, OCS flash, timer — eyes-up |
| **Phone** | Setup, calibration, replay, club admin |
| **Tablet** | Helm/nav station — Atlas-like pages without putting 4.2" glass in the puck |

Race-critical path stays **LoRa ↔ Race Control**. BLE UI is sailor-facing only (can drop without killing OCS uplink if puck stays on mesh).

---

## vs Boat Atlas (4.2")

| | Universal Puck (now) | Boat Atlas (later, optional) |
|--|----------------------|------------------------------|
| Shell | Action-cam production case | Own IP67 thin shell |
| On-device glass | Back-cover ~2–2.8" | 4.2" RLCD |
| Big UI | Tablet / watch / phone app | On-device + BLE |

Do not block Universal shipping on Atlas glass. Atlas is a **future SKU** if volume pays for a custom shell — not required for Opti→bigger-boat coverage.

---

## v0 buy / build

1. **Housing:** H9–13 (or Ace Pro) **60 m** waterproof case — clear backdoor preferred for screen.  
2. **Insert:** electronics packed to camera outline; GPS in front lens pocket; **LCD on rear**.  
3. **Mount:** hose clamp or Velcro + flat plate; screen aft.  
4. **App:** BLE watch + phone first; tablet layout next for keelboat.

Price quotes: always **R** and **($)** per [`PRICE_RULE.md`](PRICE_RULE.md).
