# Universal Puck — Opti → bigger boats (split housings)

**Two GoPro-class housings. Sailor mounts each wherever they want.**

| Unit | Inside | Screen |
|------|--------|--------|
| **Puck** | Small processor + battery + RTK GNSS + LoRa + IMU | **None** |
| **Screen** | Small processor + battery + SPI LCD (back cover) | **Yes** (~2.0–2.8") |

Same race network as before. Bigger boats can still add **tablet / smartwatch / phone** over BLE to the **Puck**.

North star: [`NORTH_STAR.md`](NORTH_STAR.md).

---

## Product lock

| | |
|--|--|
| **SKU set** | **Puck** + optional **Screen** (both same shell family) |
| **Shell** | Biggest common **action-cam** waterproof case (H9–13 / Ace class) — production look |
| **Puck guts** | Small MCU + battery + GNSS/RTK + LoRa + IMU — **no display** |
| **Screen guts** | Small MCU + battery + SPI LCD on back cover — **no LoRa/RTK required** |
| **Link** | **BLE** Screen ↔ Puck (same as watch/tablet) |
| **Mount** | Each housing mounts **anywhere** (mast, rail, transom, bulkhead, tiller) |
| **Not v0** | One brick with both guts+glass; custom Atlas shell; ESP32-on-LCD kits |

```
                    Committee RTK + LoRa + Race Control
                                    │
                                    ▼
                         ┌─ PUCK (GoPro case) ─┐
                         │ MCU · battery       │
                         │ RTK · LoRa · IMU    │
                         │ no screen           │
                         └──────────┬──────────┘
                                    │ BLE
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
     ┌─ SCREEN (GoPro) ─┐      Watch / phone         Tablet
     │ MCU · battery    │      (optional)            (bigger boats)
     │ back-cover LCD   │
     └──────────────────┘
        mount anywhere
```

---

## Why two housings

| Problem | Split fix |
|---------|-----------|
| Screen + full radio stack fight for depth in one case | Puck uses full **33.6 mm** for antennas/battery; Screen uses rear for glass |
| Opti wants sensors high / clear sky; helm wants digits aft | Mount **Puck** for GNSS sky; mount **Screen** where eyes are |
| Some sailors only need mesh + phone | Buy **Puck only**; add Screen later |
| Production look | Both look like normal action cams / accessories |

---

## Puck housing (no screen)

- Shell: H9–13 class case (opaque or clear — screen not needed).
- Front lens pocket → **GPS/RTK antenna** ([`housing/gopro-h9-13-lens-gps-pocket.md`](housing/gopro-h9-13-lens-gps-pocket.md)).
- Inside: **small MCU + battery** + LoRa + IMU (+ RTK GNSS).
- No rear LCD — max room for cells and RF.
- Mount for **sky view** and mesh (mast top-ish, rail, transom) — class rules permitting.

---

## Screen housing (display only)

- Same shell family; **clear backdoor**.
- **SPI LCD only** (no ESP32 all-in-one) — see [`housing/gopro-back-screen-fit.md`](housing/gopro-back-screen-fit.md).
  - v0: Waveshare **2.0" SPI** board **58 × 35 mm**, AA **30.6 × 40.8 mm**
- Inside: **small MCU + battery** + BLE; talks to Puck; draws start / speed / OCS / line.
- Mount **anywhere** helm can see (mast aft below boom, bulkhead, tiller, hiking).

---

## Class ladder

| Band | Typical mount |
|------|----------------|
| **Optimist** | Puck for sky; Screen aft on mast or boom area (jaw clearance); or Puck-only + watch |
| **ILCA / 420 / 29er** | Puck rail/mast; Screen at compass height / tiller |
| **Bigger boats** | Puck on rail/pushpit; Screen at helm **or** tablet/watch only |

Firmware identity lives on the **Puck** (boat ID, FIX, OCS). Screen is a dumb-ish BLE client.

---

## Companion apps (still)

| Client | Talks to |
|--------|----------|
| Screen housing | Puck (BLE) |
| Smartwatch / phone / tablet | Puck (BLE) |

Race-critical: **Puck ↔ LoRa ↔ Race Control**. Screen/app can drop; puck stays on mesh.

---

## vs one-unit / Boat Atlas

| | Split Universal (now) | One-unit (rejected for v0) | Boat Atlas (later) |
|--|----------------------|----------------------------|--------------------|
| Housings | **Two** GoPro-class | One brick | Own thin shell |
| Glass | Second case | Back of same case | 4.2" RLCD |
| Mount freedom | **Anywhere each** | Compromise one place | Fixed instrument |

---

## v0 buy / build

1. **Two** H9–13 (or Ace) **60 m** cases — one can be standard door; Screen needs **clear backdoor**.  
2. **Puck insert:** MCU + battery + GNSS in lens pocket + LoRa + IMU.  
3. **Screen insert:** MCU + battery + SPI 2.0" on rear face.  
4. Pair over BLE; mount independently.  
5. Phone/watch/tablet apps optional on top.

Price quotes: **R** and **($)** per [`PRICE_RULE.md`](PRICE_RULE.md).
