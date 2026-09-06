# Lipton-shaped event kit — 17 keelboats — complete list + Rand

**Event shape:** Lipton Challenge Cup class (packed trails R1–R10): **17 boats**, **start pin–RC line**, **separate finish line**, **4 course marks**.  
**FX:** R16 / $1 · **Date:** 2026-09-06  
**Unit prices:** [`cost-what-goes-where.md`](cost-what-goes-where.md) · factory WT-43 path.

### Assumptions (read these)

| # | Assumption |
|---|------------|
| 1 | **One** committee WT-43-BK; antenna **on** the start-line committee end (no second bow rover) |
| 2 | Trails have **start L/R** + **finish L/R** → kit **start pin** + **finish pin** (finish often near start; one end can be RC when boat is there — still budget a finish-pin pack) |
| 3 | Trails have **marks 1–4** → **4 mark packs** |
| 4 | Each keelboat: **1 Puck** (radio/RTK) + **1 IP68 tablet** (Atlas-like helm UI over **BLE**). Tablet has **no** LoRa/RTK |
| 5 | Committee: **1 IP68 tablet** (or laptop) for Race Control UI |
| 6 | Spares: **2** infra packs + **1** puck + **1** helm tablet |
| 7 | Rescue RIBs: **not** required for race — optional note below |
| 8 | Software / labour: **R0** hardware (you write Race Control + sailor app) |
| 9 | Shipping / DUT / ICASA: **not** in totals |

---

## Unit costs used

| SKU | What’s in it | Low R | High R | Tag |
|-----|--------------|------:|-------:|-----|
| **Boat Puck** | WT-43-RK + Ebyte nRF54 + batt + Ali GoPro clone + sled | **784** | **963** | sum of LIVE/LIST/EST |
| **Infra pack** (pin/mark/finish) | WT-43-RK + batt + float/clip box | **574** | **877** | factory RK + batt + box |
| **Committee radio kit** | WT-43-BK + pole antenna + dry box/batt + USB/Pi bridge | **995** | **1 931** | LIST + EST |
| **IP68 helm / RC tablet** (8" Android class) | BLE client / Race Control host — **not** XM30R | **2 432** | **3 200** | **LIST/EST** Ali Utab-class ~**$152** (R2 432) · budget up to ~**$200** (R3 200) for 1-pc |
| **Premium rugged tablet** (optional) | nicer 8" industrial | **5 120** | **6 080** | Ali ~**$320–380** — use only if you refuse value tablets |

**Do not** buy XM30R ×17 (R2 885–3 211 each) as helm glass — that is a survey/PoC handset, not an Atlas UI clone, and doubles GNSS for no reason.

---

## Complete hardware list (Lipton 17)

### A — Committee boat

| Qty | Item | Role | Low R | High R |
|----:|------|------|------:|-------:|
| 1 | Committee radio kit (BK) | Only RTK **base** + start-line committee end | 995 | 1 931 |
| 1 | IP68 tablet | Race Control UI (start, line, OCS, finish, map) | 2 432 | 3 200 |
| | **Committee subtotal** | | **3 427** | **5 131** |

### B — Line ends / marks (infra)

| Qty | Item | Role | Low R | High R |
|----:|------|------|------:|-------:|
| 1 | Infra pack | **Start pin** | 574 | 877 |
| 1 | Infra pack | **Finish pin** | 574 | 877 |
| 4 | Infra pack | **Course marks 1–4** | 2 296 | 3 508 |
| | **Infra subtotal (6 packs)** | | **3 444** | **5 262** |

### C — Racing fleet (17 keelboats)

| Qty | Item | Role | Low R | High R |
|----:|------|------|------:|-------:|
| 17 | Boat Puck | RTK + LoRa on each boat | 13 328 | 16 371 |
| 17 | IP68 tablet | Helm / nav UI (Atlas-like pages via BLE) | 41 344 | 54 400 |
| | **Fleet subtotal** | | **54 672** | **70 771** |

### D — Spares (recommended)

| Qty | Item | Role | Low R | High R |
|----:|------|------|------:|-------:|
| 2 | Infra pack | Pin/mark failure | 1 148 | 1 754 |
| 1 | Boat Puck | Boat failure | 784 | 963 |
| 1 | IP68 tablet | Helm / RC spare | 2 432 | 3 200 |
| | **Spares subtotal** | | **4 364** | **5 917** |

### E — Optional (not in headline total)

| Qty | Item | Why | ~R |
|----:|------|-----|---:|
| 0–2 | Infra pack on rescue RIB | Map-only | 574–877 each |
| 0–17 | nRF54 Tag at bow | Channel Sounding experiment | 499 each → up to **8 483** |
| 0 | Second committee WT-43 | Not needed if antenna on line | 0 |
| swap | Premium tablets ×18 (17+RC) | Instead of value IP68 | add **~R48 000–52 000** vs value tier |

---

## Grand total — run a Lipton-shaped event

| Block | Low R | High R |
|-------|------:|-------:|
| A Committee | 3 427 | 5 131 |
| B Infra (start+finish+4 marks) | 3 444 | 5 262 |
| C 17× (Puck + tablet) | 54 672 | 70 771 |
| D Spares | 4 364 | 5 917 |
| **EVENT SYSTEM TOTAL** | **65 907** | **87 081** |

**About R66k–R87k** hardware (value IP68 tablets, factory WT-43, with spares).

| Without spares (A+B+C only) | **61 543** | **81 164** |
| Electronics only if boats already own tablets (A+B + 17 pucks + 0 boat tablets + RC tablet) | **~20 200–26 900** | — |

---

## Cost per boat (keelboat package)

| | Low R | High R |
|--|------:|-------:|
| Puck | 784 | 963 |
| Helm tablet | 2 432 | 3 200 |
| **Per-boat sailor kit** | **3 216** | **4 163** |
| Share of infra+committee÷17 | ~400–600 | ~600–900 |
| **Fully loaded per boat** (incl. share of RC/infra/spares) | **~3 900–4 800** | **~5 100–5 900** |

---

## What this replaces (context)

| Vakaros-class | Our Lipton kit |
|---------------|----------------|
| Atlas-class UI on each boat | IP68 tablet BLE → Puck |
| HALO / RaceSense radio on each boat | Puck (WT-43 + nRF54) |
| Pin / mark / RC RaceSense units | Infra packs + one BK |
| RC tablet | Committee IP68 tablet |

---

## Buy order (same event, staged)

1. Prove: **1 BK kit + 1 start pin + 2 (Puck+tablet)**  
2. Add: finish pin + 4 marks  
3. Scale: remaining 15 boat kits  
4. Spares last  

Kill gate unchanged: **moving RTK FIX + LoRa RTCM on water** before step 3.
