# BOM cost — Universal Puck + Screen (with loud speaker)

FX: **R16.00 / $1** ([`PRICE_RULE.md`](PRICE_RULE.md)).  
Prices = **small-qty buy** (1–10 pcs, modules). Volume OEM ≈ **0.55–0.7×** electronics.

**Screen must have a loud speaker** for start countdown / OCS beep (hear over wind).

---

## Design reminder

| SKU | Role |
|-----|------|
| **1. Puck** | GoPro case · RTK + LoRa + IMU · **no screen** |
| **2a. Screen** | GoPro case · LCD + **loud speaker** · BLE → Puck |
| **2b / 2c** | Waterproof tablet / smartwatch (buyer’s device — not our BOM) |

---

## 1. Universal Puck — electronics BOM

| # | Part | Typical buy | R | ($) |
|---|------|-------------|---|-----|
| 1 | RTK GNSS module (ZED-F9P class, bare / small board) | LCSC / SparkFun class | **R1 840–3 040** | **($115–190)** |
| 2 | Dual-band GNSS antenna (fits lens pocket) | patch / helical mini | **R240–640** | **($15–40)** |
| 3 | SX1262 LoRa module + antenna | Ebyte / Ra-02 class | **R80–160** | **($5–10)** |
| 4 | IMU 9-DOF | BMI270 / ICM-20948 | **R50–130** | **($3–8)** |
| 5 | Small MCU w/ BLE (module, not big DevKit) | ESP32-C3 / nRF52 | **R50–100** | **($3–6)** |
| 6 | LiPo ~1500–2000 mAh flat | 60×40×8 class | **R100–190** | **($6–12)** |
| 7 | Charger / protection / regulators | TP4056 class + LDO | **R30–65** | **($2–4)** |
| 8 | Flash / LED / passives / flex | — | **R50–100** | **($3–6)** |
| 9 | Custom PCB (proto) | JLCPCB small run | **R80–240** | **($5–15)** |
| 10 | GoPro H9–13 waterproof housing | clone 60 m | **R240–640** | **($15–40)** |
| 11 | 3D sled / foam / seals | print | **R50–100** | **($3–6)** |

| Puck total | R | ($) |
|------------|---|-----|
| **Electronics only** (1–9) | **~R2 520–4 665** | **(~$157–291)** |
| **+ housing** (1–11) | **~R2 810–5 405** | **(~$176–338)** |
| **Driven by** | RTK module (~65–75% of BOM) | |

**Cheaper GNSS path (proto / non-cm):** LC29H / single-band rover ~**R480–960 ($30–60)** → whole Puck drops to roughly **R1 450–2 900 ($90–180)** incl. housing — not HALO-class.

---

## 2a. Screen — electronics BOM (+ loud speaker)

| # | Part | Typical buy | R | ($) |
|---|------|-------------|---|-----|
| 1 | 2.0" SPI IPS LCD (ST7789, **no ESP32**) | Waveshare / clone | **R130–210** | **($8–13)** |
| 2 | Small MCU w/ BLE | ESP32-C3 / nRF52 module | **R50–100** | **($3–6)** |
| 3 | **Loud audio** (see below) | piezo **or** speaker+amp | **R50–160** | **($3–10)** |
| 4 | LiPo ~800–1200 mAh | 45×30×6 class | **R65–130** | **($4–8)** |
| 5 | Charger / power | — | **R30–65** | **($2–4)** |
| 6 | PCB + passives | — | **R50–130** | **($3–8)** |
| 7 | GoPro H9–13 housing (clear backdoor) | clone 60 m | **R240–640** | **($15–40)** |
| 8 | Sled / foam / acoustic path | print + vent/foam | **R50–100** | **($3–6)** |

| Screen total | R | ($) |
|--------------|---|-----|
| **Electronics only** (1–6) | **~R375–795** | **(~$23–50)** |
| **+ housing** (1–8) | **~R665–1 535** | **(~$42–96)** |

### Loud speaker (required on Screen)

Must cut through wind on Opti / dinghy — weak phone-style piezo alone is often **not** enough.

| Option | Level | Fit in H9–13 | Cost | Notes |
|--------|-------|--------------|------|-------|
| **A. Loud piezo** (Ø12–17 mm, ≥85–95 dB @10 cm) | OK alert | Easy | **R16–50 ($1–3)** | Cheap; sharp beep; still thin |
| **B. 20–28 mm mylar speaker + Class-D amp** (PAM8302 / MAX98357) | **Loud** countdown | Tight but doable | **R50–160 ($3–10)** | Prefer for gun/countdown |
| **C. External puck siren** | Very loud | Outside case | extra | Not v0 |

**v0 lock:** Option **B** (speaker + amp) as default; piezo as fallback if depth fights LCD.

Acoustic path: small grille / thinned backdoor foam toward helm — keep O-ring seal (sound through plastic + sealed membrane if dunk-rated).

---

## Kit totals (Puck + Screen)

| Kit | R | ($) |
|-----|---|-----|
| **Puck only** (F9P-class) | **~R2 810–5 405** | **(~$176–338)** |
| **Screen only** (w/ loud speaker) | **~R665–1 535** | **(~$42–96)** |
| **Puck + Screen** | **~R3 475–6 940** | **(~$218–434)** |
| Volume target (guess, F9P still dominates) | **~R2 400–4 000** kit | **(~$150–250)** |

Compare: Vakaros Atlas / HALO retail is typically **thousands of USD** per boat — our hardware BOM is still a fraction even at proto pricing.

---

## Cost drivers / cuts

1. **GNSS** — biggest line; shop bare ZED-F9P vs full SparkFun board.  
2. **Two housings** — ~**R480–1 280 ($30–80)** of kit; needed for mount freedom.  
3. **Screen** is cheap vs Puck — speaker does **not** move the needle.  
4. Do **not** put F9P in the Screen — keeps Screen under ~**R1 600 ($100)**.

---

## v0 buy order (cost-aware)

1. Housing ×2 + 2" SPI LCD + MCU modules + **speaker+amp** → prove Screen UI + beep.  
2. LoRa + cheap GNSS first → radio/mesh.  
3. Drop in F9P when RTK path is ready.

Regen prices before order; FX in [`PRICE_RULE.md`](PRICE_RULE.md).
