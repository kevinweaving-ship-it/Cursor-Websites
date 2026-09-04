# Compact board with expensive part onboard

Goal: buy **one small board that already has the RTK GNSS** (the expensive bit), then add cheap nRF + LoRa beside it.

Cavity face: **71.8 × 50.8 mm**.

---

## Best fit: Waveshare LG290P GNSS RTK Module

| | |
|--|--|
| **URL** | https://www.waveshare.com/lg290p-gnss-rtk-module.htm |
| **Size** | **33 × 33 mm** (castellated — solder or header) |
| **Onboard** | Quectel **LG290P** quad-band RTK (L1+L2+L5+E6) — the expensive chip |
| **Also on board** | USB-C UART, LDO, antenna connector, status LEDs |
| **In the box** | Active GNSS antenna + cables |
| **Price** | **R1 424 ($88.99)** · with RTC batt **R1 440 ($89.99)** |
| **Fit in H9–13** | Yes — leaves ~39 × 50 mm for nRF52840 + LoRa + LiPo |

**This is the right “buy the expensive part pre-mounted” board.**  
You still add: E73 nRF (**R121**) + E22 LoRa (**R106**) + housing **&lt;R100** + LiPo.

| Proto stack | R | ($) |
|-------------|---|-----|
| LG290P board + antenna | **R1 424** | **$88.99** |
| E73 + E22 | **R227** | **$14.19** |
| Housing + LiPo + charge | **~R150–220** | **~$9–14** |
| **Puck ballpark** | **~R1 800–1 900** | **~$112–118** |

Wiki: https://www.waveshare.com/wiki/LG290P_GNSS_RTK_Module

---

## Cheaper (RTK onboard) — LC29H core board

| | |
|--|--|
| **What** | Small PCB with Quectel **LC29H(DA)** already soldered |
| **URL examples** | Alibaba “LC29HDA core board” — e.g. https://www.alibaba.com/product-detail/Quectel-LC29H-Module-Centimeter-Level-High_1601266516993.html |
| **Price** | **~R300–560 ($19–35)** module/board |
| **Size** | Chip is **12.2 × 16 mm**; core boards usually ~**25–40 mm** (check listing photo) |
| **Tradeoff** | Cheaper than LG290P; dual-band L1+L5 only; quality/docs vary |

Bare module (no PCB): TOP-electronics LC29H-DA **€20.34** ≈ **R370 ($23)** — https://www.top-electronics.com/en/dual-band-multi-constel-gnss-module-4  
Needs your own carrier PCB.

---

## Skip for packing

| Board | Why |
|-------|-----|
| Waveshare **LC29H Pi HAT** 65×30.5 | Works as bench UART proto; awkward sled (USB/header bulk) |
| SparkFun / ArduSimple **F9P** | Expensive + big |
| Any **ESP32+GPS** stick | MCU won’t fit doctrine; usually huge |

---

## Recommendation

**Buy:** https://www.waveshare.com/lg290p-gnss-rtk-module.htm — **33×33 mm**, RTK already on board, **R1 424 ($88.99)**.

Then mate **E73** + **E22** on a thin sled under/ beside it inside the **&lt;R100** housing.
