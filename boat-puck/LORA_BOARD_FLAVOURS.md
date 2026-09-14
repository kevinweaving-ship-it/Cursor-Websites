# Main LoRa board — flavours (no confusion)

**Locked race path for water test:** **LoRa only** — `WT-43-RK-LORA` ×3 + `WT-43-BK-LORA` ×1 · **868 MHz**.  
**4G/5G SoftSIM** = **future flavour / fallback**, not what this sample PO is.

---

## What the “main board” is

**OTW WT-43 family** = dual-freq RTK GNSS brick (~43×43) with **built-in GNSS antenna class**, UART out.

It comes in a few **radio flavours**. Same form-factor idea; different backhaul.

| Flavour | SKU (public) | Race-critical radio | Cellular | SoftSIM / eSIM | Built-in ants | This sample kit |
|---------|--------------|---------------------|----------|----------------|---------------|-----------------|
| **A — LoRa rover** | **WT-43-RK-LORA** | LoRa | — | — | GNSS (+ LoRa path on module) | **YES ×3** |
| **B — LoRa base** | **WT-43-BK-LORA** | LoRa | — | — | GNSS (+ LoRa) | **YES ×1** |
| **C — 4G rover** | **WT-43-RK-4G** (aka RD-4G) | — | 4G modem | **Not confirmed on datasheet** | GNSS + laminated **4G** ant | **NO** (locked out of this PO) |
| **D — SoftSIM fallback** | Custom / ask Lucas | LoRa **primary** | 4G/5G **fallback** | **Target: SoftSIM only** (no physical SIM slot) | Onboard or add-on ant | **Future — ask before buy** |

---

## SoftSIM / eSIM fallback (what we discussed)

**Goal:** when LoRa is weak / for shore NTRIP / telemetry, fall back to cellular — **software-driven SoftSIM (eSIM)**, **no SIM tray**.

Two build options (pick later with Lucas / modem vendor):

| Option | What it is | Pros | Cons |
|--------|------------|------|------|
| **1 — Onboard (optional use)** | Cell modem + SoftSIM **on the same WT-43-class brick** (or factory option). Software enables/disables. Built-in cell ant. | One brick; fewer wires | Power, heat, RF isolation vs GNSS; may force 4G SKU not LoRa+cell combo |
| **2 — Tiny add-on board** | Separate mini SoftSIM modem board, **no SIM slot**, software UART/SPI to nRF54 (or WT-43 host). Own small ant. | Keep **LoRa WT-43** pure; add cell only where needed (e.g. committee / shore puck) | Extra board + fit in housing |

**Rules we already locked:**

- Race-critical path = **LoRa**, not cell.
- SoftSIM = **software profile**, not a plastic SIM.
- Antennas = **built-in** (no external SMA chase for V1 cell).
- Do **not** order flavour C/D until water test proves LoRa range and we ask Lucas for SoftSIM explicitly.

---

## Ask Lucas (when ready — not blocking water-test PO)

```
We ordered WT-43-RK-LORA ×3 + WT-43-BK-LORA ×1 (868).

For a later flavour we want:
1) LoRa primary (race) + optional 4G/5G SoftSIM fallback (no physical SIM slot)
2) Either: SoftSIM modem onboard (optional software enable), OR a tiny add-on SoftSIM board
3) Built-in antennas (GNSS + cell), software-driven SoftSIM only

Do you have / can you quote:
- WT-43 LoRa + SoftSIM combo?
- SoftSIM add-on board that UART to our MCU?
- Confirm SoftSIM (not nano-SIM tray) and which operators / eUICC
```

---

## Mental model (one line)

**Samples now = Flavour A+B (LoRa).**  
**SoftSIM 4G/5G = Flavour D later** (onboard optional **or** tiny add-on) — **not** mixed into this Eric box.

---

## ESP32-class “more built-in?” (side note — not the sample path)

**Idea:** one board with MCU + radios already glued (ESP32 line = WiFi + BLE + app CPU).

| Path | Built-in | Fit H9–13 | Verdict |
|------|----------|-----------|---------|
| **Our stack** | WT-43 (RTK+LoRa) + **nRF54** (race BLE MCU) | Yes (locked) | **Keep for water test** |
| **ESP32 DevKit / fat S3 boards** | MCU+WiFi+BLE | **Too big** + hungry | **No** |
| **Tiny ESP32-C3/S3 module only** (as MCU instead of nRF54) | WiFi+BLE+MCU | Maybe size OK | Weak: power, no BLE 6 / CS path we locked, WiFi unused on water |
| **TinkerNav-class** (ESP32 + RTK + optional LoRa/cell add-ons) | More integrated kit | Long board + SMA ant — **worse** than WT-43 | Lab curiosity only |
| **More built-in we actually want** | LoRa primary + **SoftSIM 4G** onboard **or** tiny SoftSIM add-on | Same WT-43 footprint / small daughter | **Flavour D** — ask Lucas |

**Rule:** chase **more built-in SoftSIM/cell**, not swap race brain to ESP32.
