# Order workflow — ONE STEP at a time

## How we order (locked)

1. **One item only** — know exact part + qty + who.
2. **Contact that factory** — confirm **correct SKU** + **in stock**.
3. **Get PI** with **ship to Shenzhen office (Eric)** — not SA, not multi-supplier cart chaos.
4. Eric **receives + combines** into one box → ships to us.
5. Only when that item is locked (PI / paid / confirmed) → **next item**.

Do **not** open parallel “buy options” as competing actions. Alts are a **fallback queue** only if this factory cannot supply.

---

## CURRENT STEP (do this only)

| | |
|---|---|
| **Item #** | BLE MCU for pucks |
| **Part** | **ME54BS62** (Nordic **nRF54L15**, PCB antenna, 6×9×1.8 mm) |
| **Qty** | **3** (pucks only — committee does **not** need this) |
| **Why this factory** | **MinewSemi = Shenzhen** → short hop to Eric. Ebyte E73 shop is **OOS**. |
| **Factory** | Shenzhen MinewSemi |
| **Product page** | https://store.minewsemi.com/product/bluetooth-modules-nrf54l15-me54bs62/ |
| **Email** | **minewsemi@minew.com** |
| **Phone** | +86 755 2801 0353 |

### Email — copy/paste

**To:** minewsemi@minew.com  
**Subject:** Sample PI — ME54BS62 ×3 — ship to Shenzhen (Eric)

```
Hello MinewSemi,

Please quote and issue PI for sample order:

Part: ME54BS62 (nRF54L15, PCB antenna)
Qty: 3 pcs
Confirm: exact model ME54BS62, Nordic nRF54L15, in stock now?

Ship to: our Shenzhen consolidation office (Eric)
[PASTE ERIC FULL NAME + ADDRESS + PHONE HERE]

Mark packages: Boat Puck / ME54BS62 / Kevin
Please include: unit price, shipping to this Shenzhen address, lead time, payment method.

Thank you
```

### Done when

- [ ] They confirm **ME54BS62** + **nRF54L15** + **stock**
- [ ] PI received (price + ship to Eric Shenzhen)
- [ ] Paid / PO number noted
- [ ] Then ask agent for **NEXT item only**

### If they say no stock / wrong part

**Fallback queue (one at a time — do not contact all):**
1. Ebyte `ebyteiot@cdebyte.com` → **E73-2G4M08S1F ×3** (original lock; shop OOS — ask lead time + ship Eric Shenzhen)
2. Raytac `sales@raytac.com` → **AN54LQ-15 ×3** (chip ant; ask ship Eric Shenzhen)
3. Fanstel `info@fanstel.com` → **BC15C ×3** (last)

See `NRF54_ALT_SUPPLIERS.md` for specs only — **not** a multi-buy list.

---

## Already locked / previous

- OTW: WT-43-RK ×3 + WT-43-BK ×1 (separate PO — Lucaszhang@ontheway-tech.com)

## Not this step

Housing · LiPo · dry box · antenna · lab DK — **later, one each.**
