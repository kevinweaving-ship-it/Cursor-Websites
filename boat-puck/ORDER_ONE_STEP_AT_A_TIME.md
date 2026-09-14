# Order workflow — ONE STEP at a time

## How we build (virtual puck) — locked

1. Pick **next puck component** only.
2. If committee uses the **same** part → order **extra** (usually ×4 not ×3).
3. Find / confirm correct SKU + factory.
4. Later: request PI → pay → ship to **Eric Shenzhen** → he combines.
5. **Next component only after that.**

---

## Eric Shenzhen ship-to (always paste this)

```
深圳市福田区华强北友谊路上步工业区404栋2楼212号
吴建军
18680660780
```

Full card: `ERIC_SHENZHEN_SHIP_TO.md`

---

## Built so far (virtual)

| Layer | Item | Qty | Who | Status |
|-------|------|----:|-----|--------|
| Shell | H9–13 housing | 3 | Temu | ORDERED |
| GNSS/LoRa | WT-43-RK-LORA | 3 | Lucas / OTW | ORDER SENT · 868 · Eric |
| GNSS/LoRa | WT-43-BK-LORA | 1 | Lucas / OTW | ORDER SENT · committee |

---

## NEXT PUCK COMPONENT — BLE MCU

| | |
|---|---|
| **What** | Bluetooth MCU module inside each puck (talks to phone/watch) |
| **Part** | **ME54BS62** |
| **Chip** | Nordic **nRF54L15** · PCB antenna · **6×9×1.8 mm** |
| **Fits housing?** | Yes (tiny; sits with WT-43 + flat LiPo) |
| **Qty** | **3** |
| **Committee?** | **No** — committee uses tablet/Race Control, not this module → **do not order 4** |
| **Factory** | MinewSemi (Shenzhen) |
| **Price** | **$5.00**/pc → **$15** for ×3 |
| **Page** | https://store.minewsemi.com/product/bluetooth-modules-nrf54l15-me54bs62/ |
| **Email** | **minewsemi@minew.com** |
| **Phone** | +86 755 2801 0353 |

### Confirm message (copy/paste) — request quote/stock first; PI when ready

**To:** minewsemi@minew.com  

```
Hi, need sample quote please.

Part: ME54BS62 (nRF54L15, PCB antenna)
Qty: 3pcs
Please confirm: exact model ME54BS62, Nordic nRF54L15, in stock now?

Ship to (when we PI):
深圳市福田区华强北友谊路上步工业区404栋2楼212号
吴建军
18680660780

Mark: Boat Puck / ME54BS62 / Kevin
Please send unit price + shipping to this Shenzhen address + lead time + payment method.
```

### Done when

- [ ] They confirm **ME54BS62** + **nRF54L15** + stock
- [ ] PI → pay → Eric
- [ ] Then: **next puck component only**

If Minew says no → fallback 1 only: Ebyte **E73-2G4M08S1F** (`ebyteiot@cdebyte.com`). Do not spray other factories.
