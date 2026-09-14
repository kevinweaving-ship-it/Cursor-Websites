# Charging lock + Qi fit in H9–13 housing

## Charge split (locked)

| Unit | Charge method | Parts |
|------|---------------|--------|
| **Puck ×3** | **Qi wireless** through sealed shell | Qi **RX** ×3 + TP4056 ×3 |
| **Committee ×1** | **USB** | TP4056 ×1 only |

Also: flat LiPo ×4 · one Qi **pad/TX** on the bench (any phone pad).

---

## Qi must fit **side / wall of internal casing**

**Cavity (locked):** **71.8 × 50.8 × 33.6 mm** (HERO13 / H9–13)

### Allowed RX shape

| Spec | Max / target | Why |
|------|----------------|-----|
| Coil / panel | **≤ 48 × 32 mm** footprint | Side wall face is only **50.8 × 33.6** |
| Thickness | **≤ ~1.5 mm** (coil + flex) | Stick to inner plastic; don’t eat stack depth |
| Mount | **Flat on inner wall** (prefer **rear door** or **long side**) | Couple through plastic to pad outside |
| Gap through wall | Keep coil **flush** to plastic; Qi works ~2–8 mm | No thick foam between coil and shell |

### Fit check — Adafruit-class RX (preferred)

**Adafruit #1901 / Micro Robotics AF1901-class**

| Dim | mm | Side wall **50.8 × 33.6** | Rear door **71.8 × 50.8** |
|-----|---:|:--------------------------:|:-------------------------:|
| Panel 48 × 32 × 0.5 | | **YES** (tight: ~2.8 / 1.6 mm margin) | **YES** (easy) |
| Coil ~40–42 × 29 | | **YES** | **YES** |

**Do not use** round ~**43 mm OD** RX kits on the **side wall** (43 > 33.6 depth) — those only go on the **rear door**.

```
H9–13 cavity 71.8 × 50.8 × 33.6
┌─────────────────────────────┐
│  WT-43 43×43×14             │
│  LiPo + BLE                 │
│  ║ Qi RX flat on SIDE/BACK ║  ← ≤48×32×1.5, against shell
└─────────────────────────────┘
         ↑ pad outside
```

---

## Local buy — **physical stores first**

| Prefer | Stores | Part | URL | Notes |
|--------|--------|------|-----|--------|
| **1 Micro Robotics** | Centurion + Stellenbosch | **AF1901** Qi RX (Adafruit) ×3 | https://www.robotics.org.za/AF1901 | Best known DIY; **confirm stock in store** (often thin) |
| **1 Micro Robotics** | same | **PK4056** TP4056 USB-C ×4 | https://www.robotics.org.za/PK4056 | In stock (checked) · ~R18.40 |
| **2 Communica** | Centurion (Samrand) | USB-C LiPo charger if PK4056 miss | https://www.communica.co.za/products/hkd-lith-charger-usb-c-5v-1a | Was sold out online — ask counter |
| Skip for this | Bob Shop marketplace, random Takealot imports | — | — | Not first choice |

**Walk-in ask Micro Robotics:** “Adafruit Qi wireless **receiver** AF1901 / thin ≤48×32 mm coil — need **3**.”  
If OOS: same size class only; measure before pay. No 43 mm round on side wall.

---

## Buy list (local)

| Item | Qty |
|------|----:|
| Qi RX (AF1901-class ≤48×32) | **3** |
| TP4056 USB-C + protect (PK4056) | **4** |
| Flat LiPo ~1000 mAh | **4** |
| Qi charge pad (TX) | **1+** |
