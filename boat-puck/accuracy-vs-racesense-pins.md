# Accuracy vs Lipton pin starts — Vakaros + China Sail (Sailfish)

**Dataset:** 2026 Lipton Challenge Cup J22, races **R1–R10**  
**Vakaros (source GPS / RaceSense-class):** https://player.vakaros.com/watch/Lv9A35uOBSBRmGpHgXtH/J22  
**SailingSA replay (same packed teleapi):** https://sailingsa.co.za/regatta/2026-08-29-lipton-challenge-cup-dev  
**China Sail UI (Sailfish / saill.cn open_trac on same GPS):** https://sailingsa.co.za/tracking-dev2.html  
**Packed JSON:** `/js/lipton-dev-trail-rN.json` · `/js/lipton-dev-replay-rN.json` · `/js/lipton-dev-races.json`

“The Cross” here = **start-line crossing** (teleapi GPS across pin–RC). China Sail = **Sailfish** shell on the same tracks.

---

## What those ten races actually give us

Each race packs:

| Asset | In data | Boat Puck V1 role |
|-------|---------|-------------------|
| **Pin** | `start_line.left` | **WT-43 rover** on pin |
| **RC / boat end** | `start_line.right` | Committee **base** (or 2nd rover on staff) |
| **17 boat tracks** | 1 Hz lat/lon | **Puck** per boat |
| **Gun** | `gun_ts_ms` | GNSS time sync over LoRa |
| **OCS list** | Vakaros Firestore `ocsParticipants` | Same OCS logic we must match |
| **Start order** | GPS **crossing** of pin–RC line | Cross = bow vs live line |
| **Marks** | mark trails (when received) | Mark packs (rovers) |
| **Finish** | `finish_line` (often near start on W/L) | Reuse start ends or finish pin |

Sailfish/dev2 does **not** change the physics — it only reshapes the same Lipton GPS into open_trac-style bootstrap/UI. Integration target is that **geometry**, not a second GNSS truth.

---

## Measured start lines (packed pin–RC)

| Race | Course | Line length | OCS boats (official) |
|------|--------|-------------|----------------------|
| R1 | W/L | **~360 m** | 4 (FBYC, KYC, SBYC, WBYC) |
| R2 | Quadrangle | ~150 m | 0 |
| R3 | Quadrangle | ~154 m | 1 (PYC) |
| R4 | Quadrangle | ~152 m | 1 (SBYC) |
| R5 | Quadrangle | ~173 m | 0 |
| R6 | W/L (pin as leeward) | ~149 m | 0 |
| R7 | W/L | ~156 m | 6 |
| R8 | W/L | ~171 m | 0 |
| R9 | W/L | ~156 m | 3 |
| R10 | W/L | ~131 m | 7 |

Packed trails store **fixed** pin/RC for the race (not a full rode time-series). Live RaceSense / our kit still **must** stream ends continuously — Lipton RC/pin will swing metres on rode; static ping understates that.

---

## How close the OCS calls are (this is the accuracy bar)

At gun, signed distance to the pin–RC line (boat GPS point vs packed ends), oriented so **+ = over / course side**:

| Race | Tightest OCS | Nearest clear | Decision gap |
|------|--------------|---------------|--------------|
| **R1** | KYC **+0.21 m** | GLYC **−0.19 m** | **~0.4 m** |
| **R7** | WYAC **+0.11 m** | SBYC **−0.98 m** | **~0.1–1 m** band |
| **R9** | RCYC **+1.88 m** | FBYC **+0.43 m**\* | ~1.5 m |
| **R10** | several 0.4–1.5 m | clears within **~1 m** | sub‑metre |

\*R3/R4 look orientation-messy in a single-frame gun sample (fleet already streaming); treat R1/R7/R9/R10 as the clean “push the line” set.

**Takeaway from Lipton:** many real OCS/clear calls sit in a **~0.1–0.5 m** band at the gun. That is tighter than **RaceSense DGNSS (~15–25 cm)** on a bad day, and exactly why **cm RTK** matters if we want fewer disputed calls than Vakaros standard.

---

## Accuracy stack — Vakaros vs planned WT-43

| Layer | Vakaros @ Lipton (typical) | Boat Puck (WT-43 V1) |
|-------|----------------------------|----------------------|
| Boat / pin / RC GNSS | Atlas-class L1+L5; RaceSense **~15–25 cm** DGNSS (HALO RTK **~1 cm** if used) | **1 cm + 1 ppm** RTK if FIX held |
| Corrections | Mesh / Skylark-style | **1× WT-43 base → LoRa RTCM** |
| Line ends | Live Atlas pin + boat | Live **pin rover + RC base/rover** |
| Crossing / OCS | GPS + bow model vs line | Same math + **IMU puck→bow** |
| Rate in our pack | Replay **1 Hz** (source higher) | WT-43 **≤20 Hz** (enough for J22; foilers want more later) |

**On paper vs this dataset:** if WT-43 holds FIX, we are aiming at **HALO-class endpoints**, i.e. **better than the DGNSS tier that already called these Lipton OCSs**. The Lipton gaps say we *need* that — **25 cm is not comfortable** when KYC is +21 cm over.

**Error budget that still bites (same as Vakaros):**

1. **Bow vs antenna** (J22 mast/deck mount ≠ hull at line) — calibrate per class  
2. **Heading** for lever arm  
3. **Live pin/RC swing** (packed JSON freezes ends)  
4. **LoRa latency / FIX drops**  
5. Gun epoch sync  

GNSS cm is the easy half once FIX is solid.

---

## How planned kit maps onto this Lipton layout

```
Committee WT-43 BASE  --LoRa RTCM-->  pin rover + 17 boat Pucks + mark rovers
Pin rover + RC end    --positions-->  Race Control + every Puck  => live start_line
Boat Puck             --pos+heading-->  bow point vs line at gun  => OCS / clear / cross order
```

| Lipton / Vakaros node | Our pack |
|-----------------------|----------|
| RaceSense pin unit | WT-43 **pin rover** |
| RaceSense boat/RC unit | WT-43 **base** (and/or staff rover) |
| Atlas on each J22 | **Puck** (WT-43 + BLE MCU + IMU + GoPro case) |
| Marks | WT-43 mark packs |
| Race Control tablet | Same job — ingest LoRa, show OCS, gun, board |
| Sailfish board / overlays | Optional UI skin on **our** tracks (dev2 already prototypes this) |

**Prove path (same event shape):** 1 base + 1 pin + 2 boats on a start → replay OCS vs video/eye → then scale to 17.

---

## Verdict

| Question | Answer from Lipton R1–R10 |
|----------|---------------------------|
| Integrate like Vakaros pin starts? | **Yes** — same pin / RC / boats / gun / cross |
| China Sail / Sailfish? | **Same GPS**, different UI — no second accuracy story |
| Accurate enough? | **Must be cm-class.** Sub‑metre OCS margins in R1/R7/R10 mean DGNSS-only is marginal; **WT-43 RTK is the right target** |
| What to prove on water? | Moving **FIX @ 20 Hz + LoRa**, live pin/RC, **bow offset** — not “is datasheet 1 cm nicer than 25 cm” |

Kill gate unchanged: **FIX under way with LoRa corrections** before buying ×100.
