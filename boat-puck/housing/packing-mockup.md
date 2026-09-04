# Puck + Screen packing mockup (H9–13 housing)

Cavity = camera positive: **71.8 × 50.8 × 33.6 mm**.

## Files

| File | What |
|------|------|
| `gopro-h9-13-packing-mockup.scad` | 3D insert models (OpenSCAD) |
| `render_packing_mockup.py` | 2D fit drawings (PNG) |
| `packing-mockup-puck-screen.png` | Side + rear views |
| `packing-mockup-fit-table.png` | Fit checklist |

```bash
python3 boat-puck/housing/render_packing_mockup.py
```

## 1. Puck insert (no screen)

| Part | Size mm | Placement |
|------|---------|-----------|
| GPS ceramic | Ø25 × 4 | Front lens pocket (Ø30 × 5.5) |
| GNSS module | 28 × 28 × 3 | Just behind lens |
| LoRa + IMU + MCU modules | ~18×16×3 class | Mid cavity |
| Carrier PCB | ≤65 × 45 × 1.6 | Under battery |
| LiPo | **60 × 40 × 8** | Main volume toward backdoor |

**Fit:** YES — no LCD, full depth for RF + cell.

## 2a. Screen insert

| Part | Size mm | Placement |
|------|---------|-----------|
| Waveshare 2.0" SPI board | **58 × 35 × 2.5** | Against backdoor |
| Active area | 40.8 × 30.6 | Inside board / window |
| Backdoor window | 62.7 × 41.7 | Board margin ~2.4 L/R · ~3.4 T/B |
| MCU (module) | ~18 × 16 × 3 | Forward of LCD |
| LiPo | 45 × 30 × 6 | Forward of LCD |

**Fit:** YES — SPI-only module. ESP32-LCD kits = NO.

## Verdict

Both inserts fit the **same** H9–13 GoPro housing. Sailor mounts Puck for sky and Screen for eyes; BLE between them.
