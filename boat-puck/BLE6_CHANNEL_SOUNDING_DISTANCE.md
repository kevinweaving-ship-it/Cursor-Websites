# BLE 6 accurate distance — Channel Sounding

**Feature name:** Bluetooth **Channel Sounding** (Bluetooth Core **6.0**)  
**On our puck:** nRF54 **ME54BS62** supports it (hardware + Nordic SDK samples).  
**Not the same as:** old RSSI “distance guess” (that was junk outdoors).

---

## What it is

Two BLE devices measure **how far apart they are** by sounding the 2.4 GHz radio channel — not by “how loud” the signal is.

| Old way | BLE 6 Channel Sounding |
|---------|-------------------------|
| RSSI (signal strength) | Phase / timing across many frequencies |
| Easy to fool (body, water, orientation) | Real ranging measurement |
| Often metres of error | Typically **~±0.5 m** class (marketing); better in lab LOS |

**Roles**
- **Initiator** — usually phone (asks “how far?”)
- **Reflector** — usually puck/tag (answers with sounding)

Our **nRF54** can be reflector (and/or initiator between two pucks).

---

## How accurate (honest)

| Situation | What to expect |
|-----------|----------------|
| Marketing / SIG typical | About **±50 cm** |
| Lab, short range, antennas facing, clear LOS | Can look **cm-level** repeatability (demos) |
| Real world, rotation, multipath, pockets | Errors grow — tens of cm to metres |
| Water / metal / crowded RF | Worse — treat as assist, not survey grade |

**Do not** replace **RTK GPS (WT-43)** with BLE distance for race line / OCS.  
RTK = centimetre position on Earth.  
BLE CS = relative distance between two radios.

---

## What it’s useful for on our system

| Use | Fit |
|-----|-----|
| Phone ↔ puck “how far is my puck” | Nice extra |
| Two pucks proximity (boat near pin) | Experiment later |
| Find-my-puck / gear pairing | Good |
| Official start-line OCS | **No** — use WT-43 RTK + LoRa |

Race-critical path stays: **WT-43 RTK + LoRa (+ SoftSIM backup)**.  
BLE CS = **bonus** because we already chose nRF54 for BLE 6.

---

## How it connects in our stack

```
Phone (BLE 6 Channel Sounding capable)
        ↕ BLE CS
nRF54 on puck (reflector)
        │
        └─ still also: UART to WT-43 (real GPS), SoftSIM, buttons, etc.
```

**Needs:** both ends support Channel Sounding (nRF54 yes; phone must be a CS-capable model / OS).

---

## URLs

| | |
|--|--|
| Nordic Channel Sounding | https://www.nordicsemi.com/Products/Wireless/Bluetooth-Low-Energy/Channel-Sounding |
| nRF54 module we use | https://store.minewsemi.com/product/bluetooth-modules-nrf54l15-me54bs62/ |
| SDK samples (initiator/reflector) | nRF Connect SDK → Bluetooth Channel Sounding samples |

---

## WhatsApp short

```
BLE 6 accurate distance = Channel Sounding
Not RSSI guess — real radio ranging between two BLE devices.

Typical accuracy ~±50 cm (lab can look better; water/multipath worse).
nRF54 on puck can do it (phone must support CS too).

Useful for: phone↔puck distance, find gear, experiments.
NOT for race OCS — that stays WT-43 RTK GPS + LoRa.
```
