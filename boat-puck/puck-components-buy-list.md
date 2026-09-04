# Puck — component buy list (with URLs)

FX: **R16 / $1** ([`PRICE_RULE.md`](PRICE_RULE.md)). Prices checked **2026-09-04** — re-check before order.

**Why the earlier total felt high:** SparkFun **ZED-F9P** alone is **R4 160 ($259.95)**. That is optional premium, not the only path.

**Recommended v0 GNSS:** Waveshare **LC29H(DA)** RTK rover **R880 ($54.99)** — still cm-class with corrections.

---

## Recommended Puck BOM (LC29H path)

| # | Component | Qty | Buy URL | Price | R | ($) |
|---|-----------|-----|---------|-------|---|-----|
| 1 | **GNSS RTK rover** LC29H(DA) HAT (+ antenna in kit) | 1 | https://www.waveshare.com/lc29h-gps-hat.htm?sku=25279 | $54.99 | **R880** | **$54.99** |
| 2 | **LoRa SX1262** module E22-900M22S | 1 | https://www.lcsc.com/product-detail/Wireless-Modules_Chengdu-Ebyte-Elec-Tech-E22-900M22S_C411293.html | $6.60 | **R106** | **$6.60** |
| 3 | **LoRa antenna** 868/915 MHz (IPEX/SMA) | 1 | https://ebyteiot.com/products/sx1262-868mhz-module-electronic-components-22dbm-wireless-transceiver-lora-gfsk-iot-long-range-7km-ebyte-e22-900m22s-spi (kit option) or any 915 stub | ~$2–4 | **R32–64** | **$2–4** |
| 4 | **MCU + BLE** ESP32-C3-MINI-1 | 1 | https://www.digikey.com/en/products/detail/espressif-systems/ESP32-C3-MINI-1-H4/14548892 | $3.28 | **R52** | **$3.28** |
| 5 | **IMU** BMI270 breakout (or ICM-20948) | 1 | https://www.adafruit.com/product/5764 (BMI270) | ~$7.50 | **R120** | **~$7.50** |
| 6 | **LiPo 3.7V 2000 mAh** (≈60×36×7 mm) | 1 | https://www.adafruit.com/product/2011 | $12.50 | **R200** | **$12.50** |
| 7 | **USB-C LiPo charger** | 1 | https://www.adafruit.com/product/4410 | $6.95 | **R111** | **$6.95** |
| 8 | **Housing** H9–13 waterproof (clone OK for proto) | 1 | Search “HERO11 waterproof housing 60m” AliExpress / Amazon; official: https://gopro.com/en/us/shop/mounts-accessories/protective-housing/ADDIV-001.html | clone ~$18–35 · official ~$50–70 | **R288–560** / **R800–1 120** | **$18–35** / **$50–70** |
| 9 | **Proto PCB / wires / LED / foam** | 1 | JLCPCB / local | ~$5–15 | **R80–240** | **$5–15** |

### Recommended total (clone housing)

| | R | ($) |
|--|---|-----|
| **Parts sum (mid)** | **~R1 870** | **~$117** |
| **Range** | **~R1 670–2 340** | **~$104–146** |

*(Uses clone housing ~$25 / R400. Official GoPro door adds ~+$30.)*

---

## Optional: premium GNSS (only if you insist on u-blox F9P)

| Component | URL | Price | R | ($) |
|-----------|-----|-------|---|-----|
| SparkFun GPS-RTK-SMA **ZED-F9P** | https://www.sparkfun.com/products/16481 | $259.95 | **R4 160** | **$259.95** |
| ArduSimple **simpleRTK2B Budget** (F9P) | https://www.ardusimple.com/product/simplertk2b/ | €172 ≈ $186 | **~R2 980** | **~$186** |

Replace line #1 with one of these → Puck jumps to **~$250–380** electronics. **Do not use SparkFun pricing as the default kit cost.**

---

## What each part does

| Part | Job on Puck |
|------|-------------|
| LC29H(DA) | cm RTK position (needs LoRa RTCM from committee) |
| E22 SX1262 | Race mesh / corrections / OCS uplink |
| ESP32-C3 | Fusion + LoRa + BLE to Screen/watch/tablet |
| BMI270 | Heel / motion / fusion |
| LiPo + charger | Race-day power |
| Housing | Waterproof production look |

**Not on Puck:** LCD, speaker (those are **Screen 2a**).

---

## Size check (H9–13 cavity 71.8 × 50.8 × 33.6)

| Part | Rough size | Fit notes |
|------|------------|-----------|
| LC29H HAT | 65 × 30.5 mm board | May need **module-only** / cut PCB for final; HAT is proto-ok if trimmed or stacked carefully |
| E22-900M22S | 20 × 14 mm | Easy |
| ESP32-C3-MINI-1 | ~16 × 13 mm | Easy |
| LiPo 2000 mAh | 60 × 36 × 7 | Fits face; depth OK |
| Antenna | lens pocket | Use kit active antenna or smaller patch in lens tunnel |

For a **production sled**, prefer bare LC29H module + custom PCB (cheaper and smaller than Pi HAT). HAT is fine to **buy and prove** RTK tomorrow.

---

## One-click shopping list (recommended)

1. https://www.waveshare.com/lc29h-gps-hat.htm?sku=25279 — **R880 ($54.99)**  
2. https://www.lcsc.com/product-detail/Wireless-Modules_Chengdu-Ebyte-Elec-Tech-E22-900M22S_C411293.html — **R106 ($6.60)**  
3. https://www.digikey.com/en/products/detail/espressif-systems/ESP32-C3-MINI-1-H4/14548892 — **R52 ($3.28)**  
4. https://www.adafruit.com/product/5764 — **~R120 ($7.50)**  
5. https://www.adafruit.com/product/2011 — **R200 ($12.50)**  
6. https://www.adafruit.com/product/4410 — **R111 ($6.95)**  
7. H9–13 60 m housing clone — **~R400 ($25)**  

**Electronics + clone housing ≈ R1 870 ($117)** — not R5 000.

See also: [`bom-puck-screen-cost.md`](bom-puck-screen-cost.md) (will track this recommended path).
