# Optional puck UI — flat screen + beeps + buttons + LEDs

**Status:** **OPTION** — not on current sample PO. Base puck stays no-screen.  
**Role:** race timer / OCS cues on the puck itself (when phone/watch not used).

---

## Option lock

| Piece | Spec | Why |
|-------|------|-----|
| **Flat screen** | Small **SPI TFT/OLED** on **rear face** looking out H9–13 backdoor window | Countdown / OCS / status — see `housing/gopro-back-screen-fit.md` |
| **Speaker** | Small **magnetic / piezo + amp** | **Race timer beeps** (gun, countdown, OCS) |
| **Buttons ×2** | Waterproof / membrane through back or side | Connect / confirm / mute or start-ack |
| **LEDs ×3 or ×4** | Status RGB or discrete | e.g. FIX / LoRa / SoftSIM / battery (or race state) |

**MCU:** driven by **nRF54** already in puck (no ESP32 in housing).

---

## Pack idea (optional layer)

```
H9–13
┌ front lens = GNSS sky window ──────────┐
│ WT-43 + SoftSIM strip + LiPo + nRF54   │
│                                        │
│ rear face → flat screen (through door) │
│         + 2 buttons nearby             │
│         + 3–4 LEDs                     │
│ speaker toward back/side cavity        │
└────────────────────────────────────────┘
```

Screen size: keep to **backdoor window** targets in `housing/gopro-back-screen-fit.md` (small SPI panel — not 4.2" RLCD).

---

## Connect

| UI part | To |
|---------|-----|
| Screen SPI | nRF54 |
| Buttons ×2 | nRF54 GPIO |
| LEDs ×3–4 | nRF54 GPIO (or I²C expander if pins tight) |
| Speaker + amp | nRF54 PWM / I²S (beeps only is enough for V1) |

Same SoftSIM / LoRa / WT-43 stack underneath — UI is an **add-on face**, not a different radio brick.

---

## Buy later (not tomorrow SoftSIM ask)

- SoftSIM factory contact tomorrow → `TOMORROW_SOFTSIM_FACTORY.md`
- Screen/speaker/buttons/LEDs → separate step after water-test no-screen pucks
