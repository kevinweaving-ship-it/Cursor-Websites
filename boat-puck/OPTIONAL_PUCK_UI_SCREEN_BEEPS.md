# Optional puck UI — flat screen + beeps + buttons + LEDs

**Status:** **OPTION** — not on current sample PO. Base puck stays no-screen.  
**Role:** race timer / OCS cues on the puck itself (when phone/watch not used).

---

## Screen lock — **back lid / opening side**

Sits on the **rear face** looking out the **H9–13 backdoor** (lid side).  
**Wide / long as the back lid allows — thin only** (depth into cavity).

| Budget | mm | Rule |
|--------|-----|------|
| Full rear insert face | **71.8 × 50.8** | Absolute max outline |
| **Visible backdoor window** | **~62.7 × 41.7** | **Practical max AA / panel** through lid glass |
| **Thickness** | **~2–4 mm** stack (panel + FPC) | **Thin** — don’t eat WT-43 / LiPo depth toward front |
| Comfortable AA | ≤ **~55 × 37** (~2.5") | Leaves bezel |
| Stock GoPro-class | **48 × 32** (~2.27") | Proven in this door |

**Must be ≥1000 nit** (sunlight). Pick + factory URLs: **`BACK_LID_SCREEN_1000NIT.md`**  
→ **#1 Chenghao CH200QV18B** 2.0" · 1000 nit · 34.6×47.8×2.0 · SPI  

**Not:** 4.2" RLCD · hobby Waveshare (&lt;1000 nit) · ESP32-on-glass. **nRF54** drives SPI.

Detail fit geometry: `housing/gopro-back-screen-fit.md`

---

## Option lock (rest)

| Piece | Spec | Why |
|-------|------|-----|
| **Flat screen** | As wide/long as **back lid window**; **thin** (~2–4 mm) | Countdown / OCS / status on lid side |
| **Speaker** | Small magnetic / piezo + amp | **Race timer beeps** |
| **Buttons ×2** | **Under existing H9–13 casing buttons** | Outside press → inside switch (no new holes) |
| **LEDs ×3 or ×4** | Near screen bezel or side (visible through door/window) | FIX / LoRa / SoftSIM / batt (or race state) |

### Buttons lock (reuse housing)

H9–13 already has **external casing buttons** (typically **top shutter** + **side mode** — see `housing/dimensions.json` `button_faces`).

```
Outside casing button (factory plastic)
        ↓ press
Inside tactile / dome switch on insert PCB
        ↓
nRF54 GPIO
```

| Rule | Detail |
|------|--------|
| **Count** | **×2** — align under the **two usable** stock housing plungers |
| **No new holes** | Don’t drill the waterproof shell |
| **Mount** | Switch + plunger pad on insert, height-matched so lid/body buttons click the switch |
| **Seal** | Keep factory button boots / O-rings intact |
| **Roles (example)** | Connect / confirm · or mute beeps / start-ack |

---

## Pack

```
H9–13  (front = lens / GNSS)
┌──────────────────────────────────────┐
│ WT-43 + SoftSIM + LiPo + nRF54       │
│                                      │
│════════ back lid opening ════════════│
│  thin flat screen ≈ up to 63×42      │  ← as wide/long as lid window
│  (~2–4 mm thick only) · ≥1000 nit    │
│  LEDs ×3–4 in bezel / visible edge   │
│  speaker at edge of rear cavity      │
│  buttons ×2 = under stock casing     │  ← outside housing btn → inside switch
│       (top shutter + side mode)      │
└──────────────────────────────────────┘
```

---

## Connect

| UI part | To |
|---------|-----|
| Screen SPI | nRF54 |
| **Buttons ×2** (under stock plungers) | nRF54 GPIO |
| LEDs ×3–4 | nRF54 GPIO |
| Speaker + amp | nRF54 PWM (beeps V1) |

---

## Buy later

- SoftSIM factory → tomorrow (`TOMORROW_SOFTSIM_FACTORY.md`)
- This UI → after no-screen water test
