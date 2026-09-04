# 4.2" RLCD — URLs, factory, spec, price

**Verified 2026-09-04.** Boat Atlas locked display.

Driver IC: **ST7305** (Sitronix).

---

## A. Buy today — complete board (prototype)

| Item | URL | Price (USD) | Notes |
|------|-----|-------------|-------|
| **Waveshare ESP32-S3-RLCD-4.2-EN** (no 18650) | https://www.waveshare.com/esp32-s3-rlcd-4.2.htm?sku=33507 | **$24.99** · $24.39×2 · $24.09×3 · **$23.97×4+** | **Buy this for UI proto** |
| **Waveshare ESP32-S3-RLCD-4.2** (18650 holder) | https://www.waveshare.com/esp32-s3-rlcd-4.2.htm?sku=33298 | **$26.99** · $26.39×2 · $26.09×3 · **$25.97×4+** | Same electronics + holder |
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
| **`TT420FSN21A`** (21-pin SPI) | https://toppoplcd.com/productdetails_5835009.html | https://www.alibaba.com/product-detail/4-2-Inch-300-400-SPI_1601596625687.html | **~$7.80** @2+ → **~$6** volume |
| **`TT420FSN10A`** (24-pin SPI) | https://toppoplcd.com/productdetails_5685341.html | https://www.alibaba.com/product-detail/4-2-inch-300-400-Mono_1600890627041.html | **~$8** sample → **~$6** volume |

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

| What | Channel | Real $ |
|------|---------|--------|
| Full S3+RLCD kit | Waveshare **33507** | **24.99** |
| Full kit + 18650 holder | Waveshare **33298** | **26.99** |
| Bare panel sample | Toppop Alibaba | **~7.80–12** |
| Bare panel volume | Toppop / peers | **~5–8** |
| Industrial wide-temp | Good Display | **RFQ** |

---

## D. Order for Boat Atlas

1. **Now:** https://www.waveshare.com/esp32-s3-rlcd-4.2.htm?sku=33507 — **$24.99**  
2. **Parallel:** Toppop **`TT420FSN21A`** — https://toppoplcd.com/productdetails_5835009.html  
3. **Marine temp RFQ:** Good Display **`GDTL042T71`** — https://www.good-display.com/product/455.html  
