# E73 page variants — what NOT to buy

Shop shows some options uncrossed. **Those are not replacements for the puck module.**

| Shop label | Real SKU | Chip | Form | For puck? |
|------------|----------|------|------|-----------|
| **E73-2G4M54LP(15)** (crossed) | **E73-2G4M08S1F** | **nRF54L15** | SMD module ~$4.85 | **YES — need ×3 — OOS** |
| E73-2G4M54LX(15) (crossed) | E73-2G4M08S1FX | nRF54L15 | SMD + IPEX | Same family, also OOS |
| **EWT73-2G4M54LP(15)** (open) | EWT73… | nRF54L15 | **Test kit / breakout board** ~$9.58 | **NO** — won’t fit GoPro housing |
| **E71-2G4M10S1A** (open) | E71… | **Telink TL7215D** | SMD ~$4.60 | **NO** — wrong chip / wrong SDK |
| **EWT71-2G4M10S1A** (open) | EWT71… | Telink | Test kit ~$7.35 | **NO** |

`EWT*` = **eval / test board**, not the production module.  
`E71*` = **Telink**, not Nordic. Do not substitute.

OOS on E73 ≠ discontinued. Ebyte still sells E71/EWT71/EWT73 as parallel line. Module stock is just empty.

## What to do

Email `ebyteiot@cdebyte.com`:

> Need **E73-2G4M08S1F** (shop label E73-2G4M54LP(15)) **×3**.  
> Web shop sold out. Confirm still in production. Quote lead time / backorder / 1-pc USD + ship SA.  
> Do **not** substitute E71 or EWT73 test kit.

## If Ebyte cannot supply soon

Same class (~$5–7 SMD nRF54L15, fits housing) — full lock: **`NRF54_ALT_SUPPLIERS.md`**

- **PRIMARY:** Raytac **AN54LQ-15** via TME (~$6.62 @3, ~170 stock) — https://www.tme.eu/en/details/an54l15q/iot-wifi-bluetooth-modules/raytac/an54lq-15/
- MinewSemi **ME54BS62** $5 — https://store.minewsemi.com/product/bluetooth-modules-nrf54l15-me54bs62/
- Fanstel **BC15C** from $5.64 — https://www.fanstel.com/buy1/

**Never** nRF54L15-DK ($58) for the boat.
