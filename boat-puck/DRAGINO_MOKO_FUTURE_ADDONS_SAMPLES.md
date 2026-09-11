# Dragino + Moko — future add-ons only (not race core)

**Date:** 2026-09-11  
**Catalog source:** Dragino *New product catalog (1).pdf* 2026 (26 pp) — **Dragino only** (no Moko SKUs in that PDF).  
**Moko:** separate vendor (mokosmart.com / mokolora.com) — BLE + LoRaWAN trackers/gateways for future add-ons.

## Hard framing

| Layer | What | Dragino / Moko? |
|-------|------|-----------------|
| **Race core (V1)** | Boat Puck · committee WT-43 base · pin/marks | **No** — stay on OTW WT-43 + Ebyte nRF54 |
| **Future / add-on** | Club IoT, asset tags, weather, BLE presence, LoRaWAN venue net | **Yes — sample now if useful** |

**China order cadence:** ~**every 6 months**. **Next order: next week.**  
Anything you might want in the next half-year → **put on next week’s cart**. Waiting = ~6 months delay.

---

## ORDER NEXT WEEK — Dragino (from catalog)

| Priority | Product | Qty | Why sample (future / add-on) | Direct URL | Skip-if |
|----------|---------|----:|------------------------------|------------|---------|
| **A** | **LPS8v2** indoor multi-ch LoRaWAN gateway | **1** | Stand up a **club/venue LoRaWAN** sandbox (ChirpStack built-in). Needed before any LoRaWAN end-node is useful. | https://www.dragino.com/products/lora-lorawan-gateway/item/228-lps8v2.html | You already own a multi-ch gateway |
| **A** | **TrackerD** LoRaWAN GPS+BLE+WiFi tracker | **2** | Coarse GPS tag for **RIB / tractor / gear bag** — *not* cm race OCS. Tests GPS+motion+alarm UX we may mirror later. | https://www.dragino.com/products/lora-lorawan-end-node/item/192-trackerd.html | Pure firmware curiosity only |
| **A** | **LA66** LoRaWAN module | **2** | Tiny module to **benchmark LoRaWAN vs our proprietary LoRa** on the bench; Arduino/AT path for Robby. | https://www.dragino.com/products/lora-lorawan-end-node/item/178-la66-lorawan-module.html | Never touching LoRaWAN |
| **B** | **BCN02** BLE iBeacon | **5** | Cheap **BLE presence** for clubhouse / boat park / start box experiments (walk-up detect). | https://www.dragino.com/products/lora-lorawan-end-node/item/225-bcn02.html | Watch/phone BLE only forever |
| **B** | **BH01-LB** BLE→LoRaWAN hub | **1** | Bridges BLE tags → LoRaWAN — pattern for “many BLE stickers → one long-range uplink”. | https://www.dragino.com/products/lora-lorawan-end-node/item/265-bh01-lb.html | No BLE beacon plan |
| **B** | **TrackerD-LS** solar asset tracker | **1** | Same as TrackerD but **solar** — useful mental model for unattended mark-boat *asset* tag (still not RTK). | Ask Dragino sales / shop.dragino.com for TrackerD-LS | TrackerD enough |
| **C** | **DLOS8N** outdoor gateway *or* **LG308N** indoor | **0–1** | Only if LPS8v2 indoor is too weak for harbour. Prefer **one** outdoor later; indoor first. | shop.dragino.com (confirm AS923/AU915/EU868 for SA) | LPS8v2 covers lab |
| **C** | **WSC / WSS-09** weather kit | **0–1** | Club **race-day weather** on LoRaWAN (wind/rain) as Race Control add-on — not OCS. | shop.dragino.com weather | Phone weather OK |
| **C** | **LoRaWAN IoT Kit v3** | **0–1** | Training kit if someone new joins RF work. Overlap with A-items. | shop.dragino.com | Already buying gateway+nodes |

**Band note (SA):** order gateways/nodes as **AS923** (or confirm ICASA plan) — do **not** default EU868/US915 without checking.

### Dragino — do **not** burn next-week budget on

Temp/humidity farms (LHT*), soil, CO₂, water leak, door (LDS/LWL), AI meter camera, RS485 converters, relays — fine IoT, **zero leverage** for sailing race product in next 6 months.

---

## ORDER NEXT WEEK — Moko (not in Dragino PDF)

| Priority | Product | Qty | Why sample (future / add-on) | URL | Skip-if |
|----------|---------|----:|------------------------------|-----|---------|
| **A** | **LW001-BG PRO** LoRaWAN GPS tracker | **2** | Compare vs Dragino TrackerD for **asset/RIB** tagging (GNSS+WiFi+BLE). Pick a winner later. | https://www.mokosmart.com/lorawan-tracker/ | Buying TrackerD only is OK |
| **A** | **LW003-B** BLE→LoRaWAN probe/gateway | **1** | Same job as Dragino BH01 — BLE beacons → LoRaWAN. Good A/B. | https://www.mokosmart.com/lorawan-probe-lw003-b/ | BH01 covers it |
| **B** | **MKGW2-LW** indoor LoRaWAN gateway | **0–1** | Only if **not** buying Dragino LPS8v2. One venue gateway is enough. | https://www.mokosmart.com/lorawan-gateways/ | LPS8v2 ordered |
| **B** | **H2 / H4 BLE beacon** (or Moko iBeacon pack) | **5–10** | Stick-on BLE for dinghy park / container / trolley — feeds LW003-B or BH01. | https://www.mokosmart.com/beacon/ | BCN02 pack ordered |
| **C** | Wearable/badge LoRaWAN tracker | **0–1** | Future “crew ashore / junior safety” — not helm race UI. | mokosmart.com trackers | Out of scope 6 mo |

**Pick rule:** don’t buy **two** full gateway stacks. Prefer **Dragino LPS8v2 + mixed end-nodes** (TrackerD + LA66 + BCN02) **or** **Moko LW001 + LW003-B + beacons** if you want one vendor. Best learning: **1 Dragino gateway + 1 Moko tracker + 1 Dragino tracker** for A/B.

---

## Suggested NEXT-WEEK cart (lean)

| # | Item | Qty | Vendor |
|---|------|----:|--------|
| 1 | LPS8v2 gateway (SA band) | 1 | Dragino |
| 2 | TrackerD | 2 | Dragino |
| 3 | LA66 module | 2 | Dragino |
| 4 | BCN02 beacon | 5 | Dragino |
| 5 | LW001-BG PRO | 1–2 | Moko |
| 6 | LW003-B *or* BH01-LB | 1 | Moko *or* Dragino |

≈ enough to demo: venue LoRaWAN + asset GPS + BLE presence — **without** touching puck/committee/marks BOM.

---

## What this is **not**

- Not a substitute for **WT-43** cm RTK  
- Not sailor watch / Race Control UI  
- Not pin/mark infra packs  
- Not “order everything in the 1000+ SKU catalog”

Email Dragino `sales@dragino.com` + Moko sales **this week** with: SA frequency, 1-pc pricing, DHL to SA, lead time before your China consolidation ships.
