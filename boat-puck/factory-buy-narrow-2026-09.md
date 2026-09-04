# Narrowed factory buy list — best prices (2026-09-04)

FX: **R16 / $1**. Rate bar: **≥25 Hz** hard · **50 Hz** stretch ([`gnss-50hz-lock.md`](gnss-50hz-lock.md)).

Stop shopping random Ali “RTK” finished goods. **Four factories only.**

---

## 1. GNSS — Unicore **UM980** (Puck + race base)

| Source | What | 1-pc price | Notes |
|--------|------|------------|-------|
| **Factory** [Unicore](https://en.unicore.com/products/um980/) | Bare **17×22 mm** LGA module | **OEM quote** | `info@unicorecomm.com` · sales +86-10-69939828 — for volume |
| **China board (best $)** Ali UM980/UM982 boards | Breakout ~**26×38 mm** | **~$60–130 → R960–2 080** | Confirm **UM980** + rate ≥25 Hz (ask 50 Hz FW). Example class: [Ali UM980 module listing](https://www.alibaba.com/product-detail/GPS-RTK-Module-UM980-UM982-GNSS_1601460022388.html) ($18–124 band — **verify SKU**) |
| **Trusted EU board** [gnss.store ELT0223](https://gnss.store/products/elt0223) | USB-C breakout **~26×39 mm** | **$169.99 → R2 720** | Live cart; known good |
| Skip | ArduSimple Budget (€223) · SparkFun (~$460) · HighGain MOQ 50 @ 71×46 mm | too dear / too big | |

**Order now (1 pc):** Ali UM980 board **~$100** *or* gnss.store if Ali seller won’t confirm chip/rate.  
**Volume later:** Unicore bare module quote.

---

## 2. Committee trial — **Shenzhen Anzewei / OTW** WT-43-RK-LORA

| Source | Price | URL |
|--------|-------|-----|
| **Factory** [ontheway-tech.com](https://www.ontheway-tech.com/product/wt-43-rk-lora/) | Ask quote | Anzewei (安泽微) |
| Factory listings | **~$32–54 → R512–864** | [ecer $51–61](https://www.ecer.com/corp/details-uuudx2p-p1k8bxj-otw-wt-43-rk-lora-gnss-module-gps-glonass-galileo-bds.html) · some pages **$32–41** |
| Ali (earlier live) | **R867 ($54.17)** | OK if factory quote slower |

**1–20 Hz** dual-freq + LoRa · **43×43×14 mm**. **Base trial only** — not preferred race rover.

Contact pattern: Lucaszhang@ontheway-tech.com (listed on Anzewei reseller pages — confirm on reply).

---

## 3. MCU + BLE — **Ebyte (Chengdu)** factory only

| Part | Factory cart | 1-pc |
|------|--------------|------|
| **E73-2G4M08S1C** (nRF52840) | https://ebyteiot.com/products/2-4ghz-ble-mesh-small-smd-e73-2g4m08s1c-nordic-nrf52840-module-small-size-ble-5-0 | **$7.60 → R122** (live) |
| Alt OOS | **E73-2G4M08S1CX** same page | similar |

Sales: **ebyteiot@cdebyte.com** · factory site https://www.cdebyte.com/

---

## 4. LoRa — **Ebyte** factory only

| Part | Factory cart | 1-pc |
|------|--------------|------|
| **E22-900M22S** (SX1262) | https://ebyteiot.com/products/sx1262-868mhz-module-electronic-components-22dbm-wireless-transceiver-lora-gfsk-iot-long-range-7km-ebyte-e22-900m22s-spi | **$5.98 → R96** (live) |

Bulk 50/200/500: ask Ebyte for factory tier.

---

## 5. Housing

Ali Hero 9–13 case — **&lt; R100 (~$5–6)**. Any seller; not critical.

---

## Narrowed v0 cart (pay these)

| # | Buy | Factory | $ | R |
|---|-----|---------|--:|--:|
| 1 | **UM980** board | Ali China *or* gnss.store | **100–170** | **1 600–2 720** |
| 2 | **E73** | Ebyte | **7.60** | **122** |
| 3 | **E22** | Ebyte | **5.98** | **96** |
| 4 | Housing | Ali | **~6** | **~96** |
| | **Puck electronics subtotal** | | **~$120–190** | **~R1 900–3 030** |
| 5 | **WT-43** (optional base) | Anzewei/OTW | **32–54** | **512–864** |

**One-boat first proto (Puck only, Ali UM980):** aim **~$140 / R2 240** parts.  
**With WT-43 base trial:** add **~$40–54**.

---

## Do not buy from this round

WES cards · XM30R · SIYI M9N · LC29H · GeoPod · SparkFun UM980 · ArduSimple (€223+) · HighGain MOQ-50 giant boards.

---

## Three emails to send

**Unicore / Ali UM980 seller**

> Need **UM980** (not UM960/982 unless quoted separate). Confirm max **position rate Hz** (need ≥25; prefer 50 FW). Board mm. Price 1 / 10 / 100 USD.

**Anzewei (WT-43)**

> Quote **WT-43-RK-LORA** 1 pc and 10 pc USD. Chip inside? RTCM base+rover? Max Hz?

**Ebyte**

> Order E73-2G4M08S1C ×2 + E22-900M22S ×2. Bulk price at 50 pcs each?
