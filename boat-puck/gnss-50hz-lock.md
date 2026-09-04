# GNSS rate lock — **must be 50 Hz**

Boat Puck north star: **≥50 Hz GNSS** (+ ≥100 Hz IMU).  
See [`NORTH_STAR.md`](NORTH_STAR.md).

## Do **not** buy these for the Puck (too slow)

| Module / board | RTK / nav rate | Why reject |
|----------------|----------------|------------|
| Quectel **LC29H(DA)** / Waveshare LC29H(DA) | **1 Hz RTK** | Far below 50 Hz |
| Quectel **LC29H(EA)** | **max 10 Hz RTK** | Still &lt; 50 Hz |
| Quectel **LG290P** / Waveshare LG290P | **max 20 Hz** | Still &lt; 50 Hz |
| u-blox **ZED-F9P** class | typically **≤20–25 Hz** | Not 50 Hz RTK |

Cheaper LC29H boards are fine for bench learning — **not** for race Puck.

---

## Buy this class — **50 Hz capable**

| Board | Size | Rate | Price (approx) | URL |
|-------|------|------|----------------|-----|
| **Unicore UM980** on breakout | chip **17×22 mm**; boards ~**26×39 mm** | **50 Hz** RTK (firmware) | **~R2 400–2 720 ($150–170)** | https://gnss.store/products/elt0223 |
| SparkFun **UM980 Triband RTK Breakout** | larger breakout | **50 Hz** | check live | https://www.sparkfun.com/sparkfun-triband-gnss-rtk-breakout-um980.html |
| AliExpress / China **UM980 RTK board** | varies — measure | claim **20–50 Hz** — **verify seller/firmware** | **~R2 400+ ($150+)** | search “UM980 RTK board 50Hz” |

Factory chip docs: Unicore UM980 — data update rate **up to 50 Hz** (some firmware needs upgrade for 50 Hz).

---

## Puck GNSS rule (locked)

```
GNSS module MUST support ≥50 Hz position output (RTK or fused).
IMU MUST be ≥100 Hz.
If a “cheap” RTK board is only 1–20 Hz → reject.
```

**Cost reality:** true 50 Hz RTK is the expensive line item. LC29H ~$20–55 cannot replace it for this product.

---

## Suggested v0 cart (50 Hz path)

1. UM980 board — https://gnss.store/products/elt0223 (~**R2 720 / $170**)  
2. E73 nRF — https://ebyteiot.com/products/2-4ghz-ble-mesh-small-smd-e73-2g4m08s1c-nordic-nrf52840-module-small-size-ble-5-0  
3. E22 LoRa — https://www.cdebyte.com/products/E22-900M22S  
4. Housing &lt; R100  

Detail buy list: [`puck-components-buy-list.md`](puck-components-buy-list.md).
