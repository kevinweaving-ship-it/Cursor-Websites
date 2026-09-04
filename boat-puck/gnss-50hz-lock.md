# GNSS rate lock — **Atlas parity ≥25 Hz** (50 Hz stretch)

Boat Puck north star: beat Vakaros on cost/openness/RTK-on-every-boat.  
**Atlas 2 GNSS is ~25 Hz** (+ IMU fusion ~50 Hz). We do **not** need 50 Hz GNSS to match that product.

See [`NORTH_STAR.md`](NORTH_STAR.md) · reassessment [`chat-reassess-gnss-2026-09.md`](chat-reassess-gnss-2026-09.md).

## Hard lock (Puck rover)

```
GNSS MUST support ≥25 Hz position output (RTK preferred, or high-rate PVT).
IMU MUST be ≥100 Hz.
Committee RTK base: ~1 Hz RTCM is enough.
```

**Stretch (nice-to-have):** **50 Hz** GNSS when size/BOM allow — Unicore **UM980** path.

## Reject for Puck rover

| Module / board | Rate | Why |
|----------------|------|-----|
| Quectel **LC29H(DA)** | **1 Hz RTK** | Far below 25 Hz |
| Quectel **LC29H(EA)** | **max 10 Hz RTK** | Below Atlas parity |
| Meter-level drone GPS (M9N etc.) | any | Not cm RTK |
| Finished Android “RTK” walkies / UWB badges | — | Not embeddable guts |

## Buy classes

| Board | Size | Rate | Role | URL |
|-------|------|------|------|-----|
| **Unicore UM980** breakout | chip 17×22; boards ~26×39 | up to **50 Hz** (FW) | **Preferred Puck** + race base | https://gnss.store/products/elt0223 |
| **ZED-F9P** class | varies | typically **≤20–25 Hz** | Atlas-parity candidate if ≥25 Hz confirmed | SparkFun / Ali |
| **OTW WT-43-RK-LORA** | **43×43×14** | **1–20 Hz** + LoRa | **Committee / cheap trial** — not preferred race rover | https://www.ontheway-tech.com/product/wt-43-rk-lora/ |

Always verify seller firmware rate before pay.

## Suggested v0 cart

1. UM980 board — https://gnss.store/products/elt0223 (~**R2 720 / $170**)  
2. Optional: WT-43-RK-LORA — cheap LoRa+RTK base trial (~**R867 / $54**)  
3. E73 nRF — https://ebyteiot.com/products/2-4ghz-ble-mesh-small-smd-e73-2g4m08s1c-nordic-nrf52840-module-small-size-ble-5-0  
4. E22 LoRa — https://www.cdebyte.com/products/E22-900M22S  
5. Housing &lt; R100  

Detail: [`puck-components-buy-list.md`](puck-components-buy-list.md).
