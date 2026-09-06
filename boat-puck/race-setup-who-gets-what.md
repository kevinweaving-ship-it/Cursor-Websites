# Full race setup — who gets what

**Read this when asking:** committee tablet? pin? mark? finish boat? rescue?  
**FX:** R16/$1 · Prices from [`cost-what-goes-where.md`](cost-what-goes-where.md).

---

## One picture

```
                         COMMITTEE BOAT
         ┌──────────────────────────────────────────────┐
         │  A. RADIO / GNSS KIT (required)              │
         │     WT-43-BK = ONLY RTK base on the bay      │
         │     + pole antenna + battery + dry box       │
         │                                              │
         │  B. RACE CONTROL UI (required)               │
         │     IP68 tablet  OR  laptop                  │
         │     ← this is NOT a “puck”                   │
         │     ← talks to base over USB / BLE / Pi      │
         │                                              │
         │  C. OPTIONAL line-end rover on bow           │
         │     WT-43-RK if pole ≠ geometric line end    │
         └────────────────────┬─────────────────────────┘
                              │ LoRa RTCM (corrections)
         ┌────────────────────┼─────────────────────────┐
         ▼                    ▼                         ▼
   START PIN            MARK PACKS                 BOAT PUCKS
   WT-43-RK float       WT-43-RK each mark         WT-43-RK + nRF54
   (no sailor UI)       (+ LoRa relay)             + battery + GoPro
                                                   BLE → watch/phone
```

**Hard rules**

1. **One base only** (committee BK). Everything else = **rover**.  
2. **Tablet ≠ base.** Tablet is the operator screen. Base is the WT-43-BK brick.  
3. **IP68 tablet** (XM30R class or any rugged Android/iPad) = **nice Race Control host** in spray — still needs the base kit beside it.  
4. Race-critical path = **LoRa**, not 4G. Tablet 4G = scoring upload / spectators only.

---

## Role catalogue

| Role on the water | What it is | Hardware | Mode | ~R (guide) |
|-------------------|------------|----------|------|------------|
| **Committee — corrections** | Source of cm truth for everyone | **WT-43-BK** + pole antenna + batt/box | **BASE** | **515–571** brick + **~480–1 360** antenna/box/bridge |
| **Committee — Race Control UI** | Start sequence, line, OCS list, finish, map | **IP68 tablet** *or* laptop + Race Control app | Host | Tablet **~R2 400–3 200** if buying XM30R; **R0** if club already has rugged tablet/laptop |
| **Committee — line end (optional)** | Clean geometric end of start/finish if pole isn’t on the line | **WT-43-RK** on bow | Rover | **515–571** + pack |
| **Start pin** | Other end of start line | **WT-43-RK** float/clip pack + battery | Rover | **~574–773** |
| **Finish pin** | Other end of finish line **only if finish ≠ start** | Same as start pin | Rover | **~574–773** |
| **Finish boat** | Committee-style boat at a **separate** finish | **WT-43-RK** rover pack (never a 2nd base) + optional tablet for local finish UI | Rover | **~574–773** (+ tablet if wanted) |
| **Each course mark** | Windward / leeward / offset / gate buoy | **WT-43-RK** pack (+ relay firmware) | Rover | **~574–773** each; gate = **×2** |
| **Racing boat** | Sailor product | **Universal Puck** = WT-43-RK + nRF54 + batt + GoPro clone | Rover | **~784–963** |
| **Rescue / safety / jury / coach** | Usually **not** race-critical | Optional: same **pin pack** if you want them on the map; or nothing | Rover or none | **0** or **~574–773** |
| **Shore / tower (alt base)** | Instead of committee boat for base | Same as committee radio kit | BASE | same as committee A |

---

## Your IP68 tablet question — answered straight

| Idea | Correct? |
|------|----------|
| “IP68 tablet **is** the committee puck” | **No** |
| “IP68 tablet **is** Race Control (Vakaros-tablet role)” | **Yes** |
| “Committee still needs a WT-43-BK (or equivalent) for RTCM” | **Yes — always** |
| “XM30R can replace the base because it has RTK” | **No for V1** — XM30R is a handheld survey/Android face; it is not our LoRa RTCM fleet base. Optional as **UI** or **1× survey stick**, not the radio architecture |

So committee boat equipment = **(A) base radio kit + (B) tablet/laptop**. Two boxes, two jobs.

```
Spray-proof tablet (Race Control app)
        │ USB / BLE / Wi-Fi-local / Pi bridge
        ▼
WT-43-BK on pole  ──LoRa RTCM──►  fleet
```

---

## How a typical dinghy start/finish works

### Layout 1 — Finish = start (most club racing)

| End | Device |
|-----|--------|
| Committee boat end | Base pole **or** bow rover + base on pole |
| Pin end | **Start pin pack** |
| Finish | **Same line** — no finish pin, no finish boat |

### Layout 2 — Separate finish line (big events)

| End | Device |
|-----|--------|
| Start committee | **Base stays here** (don’t move mid-regatta) |
| Start pin | Start pin pack |
| Finish boat | **Rover** pack (+ optional tablet for finish calls) |
| Finish pin | Finish pin pack |

### Layout 3 — Finish at a mark

| | |
|--|--|
| Finish target | That **mark pack** already on the buoy |

---

## Example club event BOM (counts)

Assume: committee at start, finish = start, windward + leeward gate, 20 boats.

| Qty | Unit | Role |
|----:|------|------|
| 1 | WT-43-BK + pole + box | Committee base |
| 1 | IP68 tablet or laptop | Race Control |
| 1 | WT-43-RK pin pack | Start pin |
| 1 | WT-43-RK mark pack | Windward |
| 2 | WT-43-RK mark packs | Leeward gate L+R |
| 20 | Boat Pucks | Racing boats |
| 0 | Finish pin / finish boat | Not needed (finish = start) |
| 0–2 | Extra pin packs | Optional rescue boats on map |

**Money order of magnitude (factory WT-43 path):**

| Block | ~R |
|-------|---:|
| Committee A (base kit) | 1 000–1 900 |
| Committee B (tablet) if buy XM30R-class | 2 400–3 200 · else **0** |
| Start pin | 575–775 |
| 3 mark packs | 1 725–2 320 |
| 20 boat pucks @ ~R850 | **~17 000** |
| **Event kit (ex tablet)** | **~20 000–22 000** |
| **+ tablet** | **~22 500–25 000** |

(Beta first: **1 base + 1 pin + 2 pucks** before buying 20.)

---

## Rescue / finish / “etc.” cheat sheet

| Asset | Need puck? | Need pin pack? | Need tablet? |
|-------|------------|----------------|--------------|
| Racing dinghy/keelboat | **Yes** (full Puck) | No | Optional sailor phone/watch |
| Start pin buoy | No | **Yes** | No |
| Finish pin buoy | No | **Yes if separate finish** | No |
| Windward / gate marks | No | **Yes** (mark = same pack) | No |
| Finish boat (separate) | No | **Yes** (rover) | Optional finish UI |
| Rescue RIB | No | Optional map-only pack | Optional |
| Jury / coach | No | Optional | Optional |
| Committee | Base kit | Optional bow rover | **Yes** (tablet/laptop) |

---

## Data flow (unchanged)

```
BASE (committee BK) --LoRa RTCM--> all ROVERS
ROVERS (boats, pins, marks, finish boat) --LoRa positions--> Race Control
Boat Puck --BLE--> watch / phone / optional screen housing
Race Control app runs on tablet/laptop on committee
```

OCS: **committee end + start pin** = line · boat bow = lever from Puck · gun = GNSS time from Race Control.

---

## Related docs

| Doc | What |
|-----|------|
| [`race-kit-roles-wt43-v1.md`](race-kit-roles-wt43-v1.md) | Short role table |
| [`cost-what-goes-where.md`](cost-what-goes-where.md) | Puck vs committee money + housing |
| [`ROBBY_FULL_SYSTEM_BREAKDOWN.md`](ROBBY_FULL_SYSTEM_BREAKDOWN.md) | Engineer full system |
| [`universal-puck.md`](universal-puck.md) | Sailor product tree (puck ≠ tablet) |
