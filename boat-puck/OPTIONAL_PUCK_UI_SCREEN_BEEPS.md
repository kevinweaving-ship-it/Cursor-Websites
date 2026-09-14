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

**Not:** 4.2" RLCD (too long). **Not** ESP32-on-glass. SPI panel only; **nRF54** drives it.

Detail: `housing/gopro-back-screen-fit.md`

---

## Option lock (rest)

| Piece | Spec | Why |
|-------|------|-----|
| **Flat screen** | As wide/long as **back lid window**; **thin** (~2–4 mm) | Countdown / OCS / status on lid side |
| **Speaker** | Small magnetic / piezo + amp | **Race timer beeps** |
| **Buttons ×2** | On/near back lid or side | Connect / confirm |
| **LEDs ×3 or ×4** | Near screen bezel or side | FIX / LoRa / SoftSIM / batt (or race state) |

---

## Pack

```
H9–13  (front = lens / GNSS)
┌──────────────────────────────────────┐
│ WT-43 + SoftSIM + LiPo + nRF54       │
│                                      │
│════════ back lid opening ════════════│
│  thin flat screen ≈ up to 63×42      │  ← as wide/long as lid window
│  (~2–4 mm thick only)                │
│  buttons ×2 + LEDs ×3–4 in bezel     │
│  speaker at edge of rear cavity      │
└──────────────────────────────────────┘
```

---

## Connect

| UI part | To |
|---------|-----|
| Screen SPI | nRF54 |
| Buttons ×2 | nRF54 GPIO |
| LEDs ×3–4 | nRF54 GPIO |
| Speaker + amp | nRF54 PWM (beeps V1) |

---

## Buy later

- SoftSIM factory → tomorrow (`TOMORROW_SOFTSIM_FACTORY.md`)
- This UI → after no-screen water test
