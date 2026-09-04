# Boat Puck — RLCD display path: full system + own housing

When we adopt the **4.2" ST7305 RLCD** (see [`display-rlcd-4.2-research.md`](display-rlcd-4.2-research.md)), the product stops being “HALO in a GoPro shell” and becomes **HALO sensors + Atlas-like sunlight UI in one (or two) custom housings**.

Markets ([`markets-dinghy-keelboat.md`](markets-dinghy-keelboat.md)):

- **Dinghy** = cheap puck + BLE (this RLCD path is optional / usually skip)  
- **Keelboat** = this **display SKU**

---

## 1. Two architectures (pick one for v1 tooling)

### A. One box (simplest BOM / densest)

```
OWN HOUSING — IP67 marine
┌──────────────────────────────────────────────┐
│  Window + 4.2" ST7305 RLCD (AA 63.6×84.8)    │
│  ESP32-S3/S31 — UI + BLE + LoRa host         │
│  SX1262 + LoRa antenna                       │
│  Dual-band RTK GNSS + sky antenna            │
│  9-DOF IMU + temp                            │
│  Battery + PMIC + USB-C charge               │
│  Status LED / soft keys                      │
└──────────────────────────────────────────────┘
```

- Pros: one mount, one battery, sailor sees FIX/OCS on-device.  
- Cons: RF + GNSS + display in same plastic — antenna layout is hard; larger than GoPro.

### B. Split (best RTK hygiene — recommended if budget allows two shells)

```
PUCK (GoPro H9–13 or small own shell)     DISPLAY HEAD (own shell)
┌─────────────────────────────┐           ┌─────────────────────────┐
│ RTK GNSS + ant              │  BLE/UART │ 4.2" RLCD + ESP32-S3    │
│ 9-DOF + temp                │──────────▶│ Soft keys / LED         │
│ SX1262 LoRa                 │           │ Optional local battery  │
│ Battery                     │           └─────────────────────────┘
└─────────────────────────────┘
```

- Pros: antenna on deck/rail clean; display can sit in cockpit like Atlas.  
- Cons: two housings, two batteries (or tethered power).

**Default recommendation:** prototype UI on Waveshare board alone; **product v1 = Architecture A** if we must ship one SKU; move to **B** when RF/GNSS testing shows interference.

---

## 2. Components to add (display SKU vs GoPro-only)

### Already required (race core — unchanged)

| # | Component | Notes |
|---|-----------|--------|
| 1 | Dual-band **RTK GNSS** rover | Dominates BOM (~$20–80) |
| 2 | GNSS antenna (clear sky) | Not under metal / behind thick plastic |
| 3 | **9-DOF IMU** ≥100 Hz + **temp** | Same as HALO/Atlas parity |
| 4 | **SX1262** + LoRa antenna | RaceSense substitute |
| 5 | Battery + charger | Full race day+ |
| 6 | Status LED | FIX / OCS / radio |
| 7 | Config/log flash | Boat ID, bow offset |

### New for RLCD path

| # | Component | Source / cost class |
|---|-----------|---------------------|
| 8 | **4.2" ST7305 RLCD** FOG | Toppop `TT420FSN21A` / `TT420FSN10A` — **~$6–8** vol |
| 9 | **ESP32-S3-WROOM N16R8** (or S31 later) | **~$3–5** |
| 10 | Optical window + gasket | Housing shop — marine acrylic/PC |
| 11 | Soft keys or capacitive buttons | 2–4 keys: Mode / Start / Brightness-n/a / Mark |
| 12 | Custom PCB (drop Waveshare audio) | Strip mics/speaker/AI |
| 13 | **Own IP67 housing + mount** | See §3 — **not** GoPro |

### Still skip on display PCB

Voice mics, speaker, TF calendar fluff, Qi (until later), colour IPS, ambient light (no backlight), barometer (not required for RaceSense parity).

### Committee (unchanged)

RTK base · LoRa hub · Race Control host · line-end refs · all-day power.

---

## 3. Own housing — design envelope

GoPro cavity (**71.8 × 50.8 × 33.6 mm**) is **too small** for 4.2" AA (**63.6 × 84.8 mm**). New shell must be designed around the glass.

### Minimum internal targets (Architecture A)

| Region | Target | Why |
|--------|--------|-----|
| Display window opening | ≥ **64 × 85 mm** clear + gasket land | Panel AA |
| PCB plane | ~**95 × 75 mm** usable | Waveshare board is 92.5×70; custom can be tighter |
| Thickness stack | ~**25–40 mm** typical | Glass + PCB + battery + ant keepouts |
| GNSS antenna pocket | Clear sky; ≥ **Ø30 × 5 mm** class if patch | Same lesson as GoPro lens pocket |
| LoRa antenna | Edge / external stub | Keep away from GNSS |
| Mount | Rail clamp / suction / mast / tiller — decide with sailors | Atlas-like placement |

### Mechanical doctrine

1. **Glass is the master** — CAD from panel outline + FPC bend, not from GoPro.
2. **IP67** seal at window (compression gasket) and any USB door.
3. **No metal over GNSS** patch; plastic window or dedicated sky face.
4. **Service:** battery replaceable or USB-C only for v1.
5. Prototype housings: SLA/SLS → soft-tool PU → injection when volumes clear.

### Cost guess (housing only)

| Process | Unit @ low qty | Notes |
|---------|----------------|--------|
| 3D print + gasket DIY | $5–15 | Proto only |
| Soft tooling / urethane | $15–40 | Small fleet |
| Injection ABS/PC + overmold | $5–15 @ volume | Real product |

---

## 4. Unit cost stack (display SKU, indicative)

| | Proto | 100–500 |
|--|-------|---------|
| Electronics (panel+S3+LoRa+IMU+PCB) | ~$35–70 | ~$25–45 |
| RTK GNSS | ~$25–80 | ~$20–60 |
| Battery + housing | ~$15–50 | ~$10–25 |
| **Total rough** | **~$75–200** | **~$55–130** |

Still far under Atlas+HALO retail; GNSS quality sets the floor.

---

## 5. Build sequence

| Step | Action |
|------|--------|
| 1 | Buy **Waveshare 33507** — LVGL race UI (timer, DTL, SOG, OCS, FIX) |
| 2 | Sample **Toppop TT420FSN21A** — confirm SPI + glass + sunlight |
| 3 | Freeze Architecture **A or B** after antenna mockup |
| 4 | Schematic: S3 + ST7305 + SX1262 + GNSS UART + IMU I²C |
| 5 | CAD own housing from panel + battery + ant keepouts |
| 6 | Keep GoPro puck path as **sensor-only / cheap** SKU if split |

---

## 6. Relation to GoPro housing work

| Path | Housing | Display |
|------|---------|---------|
| **Cheap / HALO-like** | GoPro H9–13 (`housing/`) | BLE phone/watch only |
| **Display / Atlas-like** | **Own shell** (this doc) | 4.2" RLCD |

Do not force RLCD into the GoPro keepout — that envelope stays for the sensor puck.
