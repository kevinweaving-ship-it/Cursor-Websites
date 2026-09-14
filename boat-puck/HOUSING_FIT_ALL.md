# Housing fit check — **everything** vs H9–13

**Cavity (locked):** **71.8 × 50.8 × 33.6 mm**  
**Rule:** part must clear **plan** and **depth**. Wall-mounted parts (Qi, cell FPC, LEDs) don’t stack in the middle.

---

## Verdict

| Block | Fit? | Note |
|-------|:----:|------|
| **Core race stack** (housing + WT-43 + nRF54 + LiPo + TP4056 + Qi) | **YES** | Locked |
| **SoftSIM A7672** (+ tiny carrier + wall FPC) | **YES** | In ~28.8 mm leftover strip beside WT-43 |
| **RLCD #1 — 2.13" ST7305** | **YES** | Best safe optional screen |
| **RLCD #2 — Sharp LS027 2.7"** | **YES*** | *Caliper Temu door — outline ~1 mm over glass short axis |
| **RLCD 1.54" / Kyocera 2.2"** | **YES** | Small / strip |
| **RLCD 2.9" ST7305** | **MAYBE** | Long side under frame — measure |
| **RLCD 4.2"** | **NO** | Atlas only |
| **1000-nit colour TFT** | Size yes | **Wrong type** for screen gate |
| **Speaker + buttons×2 + LEDs×3–4** | **YES** | Buttons under stock plungers; LEDs/speaker at rim |

**All must-have parts fit.** Optional screen fits **only** if RLCD gate pick (prefer 2.13").

---

## Plan view (71.8 × 50.8)

```
         ← 71.8 →
┌──────────────────────────────┬──────────┐
│                              │ SoftSIM  │ ↑
│   WT-43-RK  43 × 43 × 14     │ 24×24    │ 50.8
│   (GNSS toward front lens)   │ +carrier │ ↓
│                              │ ≤28×28   │
├──────────────────────────────┴──────────┤
│  leftover strip beside WT-43 ≈ 28.8 mm  │
└─────────────────────────────────────────┘
```

| Part | Footprint mm | Clears? |
|------|--------------|---------|
| WT-43-RK-LORA | **43 × 43** | **YES** — margin +28.8 W · +7.8 H |
| SoftSIM A7672 + carrier | **≤28 × 28** (module 24×24) | **YES** — in 28.8 strip (~0.8–4.8 mm) |
| ME54BS62 nRF54 | **6 × 9** | **YES** — on sled under/beside |
| LiPo 1000 mAh class (e.g. 503450) | **~50 × 34 × 5** | **YES** — under WT-43 / sled (50&lt;71.8, 34&lt;50.8) |
| TP4056 board | ~**25 × 17 × 1.5** typ | **YES** — under/beside LiPo |
| Qi RX | ≤**48 × 32 × 1.5** | **YES** — **wall** (side or rear door), not mid-stack |
| Cell FPC ant | flex strip | **YES** — **side wall** (not GNSS face, not under Qi coil) |
| RLCD 2.13" | **~27 × 56 × 1.1** | **YES** — rear face |
| Sharp LS027 2.7" | **62.8 × 42.8 × 1.65** | **YES** on face 71.8×50.8; glass window tight |
| Stock buttons ×2 | housing plungers | **YES** — internal tactiles under shutter + mode |

---

## Depth stack (33.6 mm front → back)

SoftSIM sits **beside** WT-43 (not on top) → doesn’t add to WT-43 height.

| Layer (front → back) | mm (typ) | Running sum |
|----------------------|--------:|------------:|
| Front lens / GNSS keep-out | (in WT-43) | — |
| **WT-43** | **14.0** | 14.0 |
| Sled / foam / tape | 1.5–2.5 | ~16 |
| **LiPo flat** | **5.0** (≤6) | ~21 |
| Carrier: nRF54 1.8 + TP4056 ~1.5 + traces | ~2.5–3.5 | ~24.5 |
| Air / wires / speaker capsule | ~2–4 | ~27 |
| **RLCD** (if fitted) | **1.1–1.65** | **~28.5–29** |
| **Margin vs 33.6** | | **~4.5–5 mm** |

| Check | Result |
|-------|--------|
| Core **without** screen | **~27 mm** used → **YES** (~6 mm free) |
| Core **+ 2.13" RLCD** | **~28.5** → **YES** |
| Core **+ Sharp 2.7"** | **~29** → **YES** if door clears outline |
| LiPo thicker than **6–7 mm** | **Risk** — buy **≤5–6 mm** pouch only |
| SoftSIM EVB / fat PCB | **NO** — carrier must stay thin |

---

## Wall / keep-out map (no clashes)

| Zone | Use | Don’t |
|------|-----|-------|
| **Front lens port** | WT-43 GNSS sky | Metal, LiPo, SoftSIM, Qi |
| **Leftover strip (~29 mm)** | SoftSIM carrier | LiPo brick that blocks UART |
| **Rear face / backdoor** | RLCD (optional) | Thick Qi coil in front of glass |
| **Side / rear wall plastic** | Qi RX **or** split: Qi rear door, cell FPC side | Stack coil over cell ant |
| **Top shutter + side mode** | Internal buttons ×2 | New holes |

---

## Option-by-option screen fit (gate)

| Screen | Plan | Depth | Gate type | Housing fit |
|--------|------|-------|-----------|-------------|
| ST7305 **2.13"** | YES | YES | RLCD | **FIT** — recommend |
| Sharp **LS027 2.7"** | YES* | YES | RLCD | **FIT*** after door caliper |
| ST7305 **1.54"** | YES | YES | RLCD | **FIT** (small) |
| Kyocera **2.2"** | YES | YES | RLCD | **FIT** |
| ST7305 **2.9"** | maybe | YES | RLCD | Measure |
| ST7305 **4.2"** | **NO** | — | RLCD | **NO** |
| Chenghao 1000-nit 2.0" | YES | YES | TFT — wrong type | Size OK, skip as primary |

---

## Wiring still fits (no extra bulk boxes)

| Link | Path |
|------|------|
| WT-43 UART | → nRF54 |
| SoftSIM UART | → nRF54 |
| RLCD SPI | → nRF54 |
| Buttons / LEDs / beep | → nRF54 GPIO/PWM |
| Qi → TP4056 → LiPo | charge rail |

---

## Lock

1. **Everything on the must-buy puck list fits** the H9–13 cavity with the packing above.  
2. **SoftSIM fits** in the side strip.  
3. **Screen only if RLCD** and size-pass — **2.13" ST7305** default; Sharp 2.7" after caliper.  
4. Buy LiPo **≤5–6 mm thick**; SoftSIM on **custom thin carrier** (no EVB).  
5. Dry-fit with real Temu shell before SoftSIM/screen PO.

See also: `PUCK_STACK_WITH_SOFTSIM.md` · `DEEP_DIVE_RLCD_BACK_LID.md` · `WT43_H9-13_FIT_CONFIRM.md`
