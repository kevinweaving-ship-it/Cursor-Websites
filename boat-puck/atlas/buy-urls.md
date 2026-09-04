# 4.2" RLCD — URLs, factory, spec, price

**Verified 2026-09-04.** Boat Atlas locked display.

**Price rule (Boat Puck):** always show **Rand (R)** and **USD ($)**.  
FX used here: **R16.00 / $1** (mid-market ~15.99–16.06 on 2026-09-04). Re-check before ordering.

Driver IC: **ST7305** (Sitronix).

---

## A. Buy today — complete board (prototype)

| Item | URL | Price | Notes |
|------|-----|-------|-------|
| **Waveshare ESP32-S3-RLCD-4.2-EN** (no 18650) | https://www.waveshare.com/esp32-s3-rlcd-4.2.htm?sku=33507 | **R400 ($24.99)** · R390 ($24.39)×2 · R385 ($24.09)×3 · **R384 ($23.97)×4+** | **Buy this for UI proto** |
| **Waveshare ESP32-S3-RLCD-4.2** (18650 holder) | https://www.waveshare.com/esp32-s3-rlcd-4.2.htm?sku=33298 | **R432 ($26.99)** · R422 ($26.39)×2 · R417 ($26.09)×3 · **R416 ($25.97)×4+** | Same electronics + holder |
| Product docs | https://docs.waveshare.com/ESP32-S3-RLCD-4.2 | — | Pinout, Arduino, ESP-IDF |
| GitHub samples | https://github.com/waveshareteam/ESP32-S3-RLCD-4.2 | — | Demo code |
| ST7305 datasheet (PDF) | https://files.waveshare.com/wiki/common/ST_7305_V0_2.pdf | — | Controller |

### Board display specs (Waveshare)

| | |
|--|--|
| Panel | 4.2" **RLCD** (full reflective) |
| Resolution | **300 × 400** |
| Colors | Black / white |
| Interface | **SPI** |
| Driver | **ST7305** |
| Backlight | **None** |

---

## B. Factory glass — production (own PCB)

### 1. Shenzhen Toppop (primary)

| Part | Factory page | Alibaba | Listed price |
|------|--------------|---------|--------------|
| **`TT420FSN21A`** (21-pin SPI) | https://toppoplcd.com/productdetails_5835009.html | https://www.alibaba.com/product-detail/4-2-Inch-300-400-SPI_1601596625687.html | **~R125 ($7.80)** @2+ → **~R96 ($6)** volume |
| **`TT420FSN10A`** (24-pin SPI) | https://toppoplcd.com/productdetails_5685341.html | https://www.alibaba.com/product-detail/4-2-inch-300-400-Mono_1600890627041.html | **~R128 ($8)** sample → **~R96 ($6)** volume |

| Spec (Toppop both) | |
|--|--|
| Size | 4.2" |
| Resolution | 300 × 400 |
| Driver | ST7305 |
| Interface | 4-SPI |
| Active area | **63.6 × 84.8 mm** |
| Touch / front LED | None (custom optional) |

Company: **Shenzhen Toppop Electronic Co., Ltd** — https://toppoplcd.com/

### 2. Good Display (wide-temp alt)

| Part | URL | Price | Notes |
|------|-----|-------|-------|
| **`GDTL042T71`** | https://www.good-display.com/product/455.html | RFQ (high MOQ common) | −20…+70 °C; outline **67.6 × 91.0 × 0.8 mm**; 24-pin FPC |
| ST7305 datasheet (GD) | https://www.good-display.com/companyfile/1514.html | — | Same IC |
| CN page | https://www.good-display.cn/product/450.html | — | Same part |

| Spec (`GDTL042T71`) | |
|--|--|
| Active size | 63.6 × 84.8 mm |
| Outline | 67.6 × 91.0 × 0.8 mm |
| Interface | 4-wire SPI |
| Weight | ~10 g |

---

## C. Price cheat-sheet

| What | Channel | Price |
|------|---------|-------|
| Full S3+RLCD kit | Waveshare **33507** | **R400 ($24.99)** |
| Full kit + 18650 holder | Waveshare **33298** | **R432 ($26.99)** |
| Bare panel sample | Toppop Alibaba | **~R125–192 ($7.80–12)** |
| Bare panel volume | Toppop / peers | **~R80–128 ($5–8)** |
| Industrial wide-temp | Good Display | **RFQ** |

---

## D. Order for Boat Atlas

1. **Now:** https://www.waveshare.com/esp32-s3-rlcd-4.2.htm?sku=33507 — **R400 ($24.99)**  
2. **Parallel:** Toppop **`TT420FSN21A`** — https://toppoplcd.com/productdetails_5835009.html — **~R125 ($7.80)** sample  
3. **Marine temp RFQ:** Good Display **`GDTL042T71`** — https://www.good-display.com/product/455.html  
