# nRF54 = the puck processor (race brain)

**Yes:** **ME54BS62 (nRF54L15)** is the **main processor / race brain** in the puck.  
**WT-43 also has a CPU** — but that one only does **GPS/RTK + LoRa radio**. It does **not** run race logic.

---

## Two processors (don’t mix them up)

| Chip | Role | Runs |
|------|------|------|
| **WT-43** | GPS brick | RTK math, NMEA out, LoRa modem |
| **nRF54 (ME54BS62)** | **Puck computer** | Start/OCS logic, BLE, buttons, LEDs, beeps, SoftSIM AT commands, optional screen |

Flow:

```
Committee sets start (tablet)
    → LoRa → WT-43 (radio in)
    → UART → nRF54
    → nRF54 decides OCS / countdown / beeps
    → BLE → phone/watch
    → optional RLCD / speaker / LEDs
```

---

## What the nRF54 is

- Nordic **nRF54L15** inside Minew **ME54BS62** module (~**6 × 9 × 1.8 mm**)
- **Arm Cortex-M33** CPU (~128 MHz)
- Built-in **Bluetooth LE 6** (+ 2.4 GHz)
- Flash + RAM on-chip (enough for race firmware)
- Lots of **GPIO / UART / SPI / PWM** for buttons, SoftSIM, screen, speaker

**URL:** https://store.minewsemi.com/product/bluetooth-modules-nrf54l15-me54bs62/  
**Nordic chip:** https://www.nordicsemi.com/Products/nRF54L15

---

## What we program it to do

Firmware **we write** on nRF54:

1. Talk UART to **WT-43** (read position / fix quality)
2. Talk UART AT to **SoftSIM** modem (when using LTE)
3. **BLE** advertise / connect to phone or watch app
4. Race logic: countdown, gun, **OCS**, line vs mark roles
5. Read **buttons ×2** (under housing plungers)
6. Drive **LEDs** / **speaker beeps**
7. Optional **SPI RLCD** UI

We do **not** reprogram WT-43 for V1 race rules (use it as a GNSS+LoRa brick).

---

## How you program it

| Step | What |
|------|------|
| 1 | Install **nRF Connect SDK** (Zephyr RTOS) — Nordic’s official toolchain |
| 2 | Write C/C++ (or Rust later) app in SDK |
| 3 | Flash over **SWD** (debug wires): nRF54L15 DK, J-Link, or Minew eval if used |
| 4 | Debug with **nRF Connect for VS Code** / Segger Ozone |
| 5 | OTA later optional (DFU over BLE) once bootloader set |

**Dev tools URLs**
- nRF Connect SDK: https://www.nordicsemi.com/Products/Development-software/nRF-Connect-SDK  
- nRF54L15 DK (lab only — too big for puck): https://www.nordicsemi.com/Products/Development-hardware/nRF54L15-DK  
- Zephyr docs: https://docs.zephyrproject.org/

**Practical path**
1. Prototype firmware on **nRF54L15 DK** on the bench  
2. Same binary / port to **ME54BS62** module on the puck PCB (SWD pads)  
3. Phone app talks BLE to that firmware  

---

## WhatsApp short

```
nRF54 = THE processor / race brain in the puck
WT-43 = GPS+LoRa brick (has its own CPU but only for RTK/radio)

We program nRF54 with Nordic nRF Connect SDK (Zephyr):
• read GPS from WT-43 over UART
• drive SoftSIM over UART
• BLE to phone/watch
• buttons / LEDs / beeps / optional screen
• start + OCS race logic

Flash via SWD (dev kit first, then module on puck).
Module: ME54BS62
https://store.minewsemi.com/product/bluetooth-modules-nrf54l15-me54bs62/
SDK: https://www.nordicsemi.com/Products/Development-software/nRF-Connect-SDK
```
