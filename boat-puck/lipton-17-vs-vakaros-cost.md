# Lipton 17 — Boat Puck vs Vakaros Atlas / HALO / RaceSense

**FX:** R16 / $1 · **Date:** 2026-09-06  
**Same event shape:** 17 keelboats · start pin–RC · finish pin · 4 marks · committee tablet.

**Ours:** [`lipton-17-event-kit-cost.md`](lipton-17-event-kit-cost.md) → **R66k–R87k** (with spares).

**Vakaros prices (LIVE retail carts / store):**

| SKU | USD | Rand | Source |
|-----|----:|-----:|--------|
| **Atlas 2** | **1 249** | **19 984** | [vakaros.com/products/atlas-2](https://www.vakaros.com/products/atlas-2) · dealers same |
| **Atlas HALO RTK** | **599** | **9 584** | [vakaros.com/products/atlas-halo-rtk](https://www.vakaros.com/products/atlas-halo-rtk) |
| **Atlas Edge** (cheaper instrument) | **749** | **11 984** | Vakaros store |
| **RaceSense Annual Pass** / device | **149** | **2 384** | [annual pass](https://www.vakaros.com/products/racesense-annual-pass) |
| **RaceSense Month Pass** / device | **50** | **800** | [month pass](https://www.vakaros.com/products/month-pass) |
| RC tablet | — | **~1 280–2 400** | **EST** mid iPad / Android (Vakaros app; not sold as a kit price) |

**How RaceSense is wired (from their manual):** RC needs at least a **Control Atlas** + **Pin Atlas** (Control can double as boat-end). Better: dedicated Control + Boat-end + Pin. Course marks = more Atlas “mark” units. Sailors each need an Atlas (owned or loaned). Passes are per competing Atlas.

**Unknown / quote-only:** full **RaceSense RTK event** package (shore base vs Skylark, event fees). HALO page says *request a quote* for RTK event pricing — retail HALO+Atlas below is a **floor**, not a negotiated event deal.

---

## Apples-to-apples hardware counts

| Role | Boat Puck kit | Vakaros RaceSense |
|------|---------------|-------------------|
| Committee UI | 1× IP68 tablet | 1× tablet (app) |
| Committee radio / control | 1× WT-43-BK kit | 1× **Control Atlas 2** |
| Start pin | 1× infra pack | 1× **Pin Atlas 2** |
| Finish pin | 1× infra pack | 1× **Finish / mark Atlas 2** |
| Marks 1–4 | 4× infra pack | 4× **Mark Atlas 2** |
| Each of 17 boats | Puck + helm tablet | **Atlas 2** (UI+radio+GNSS in one) |
| cm RTK (optional tier) | Built into WT-43 path | **+ HALO** per boat (and event base/corrections) |
| Software licence | Build yourself (R0 HW) | RaceSense pass / device |

**Not double-counting committee “boat end”:** Control Atlas = our one BK on the line (same idea).

---

## A — Vakaros **standard RaceSense** (~25 cm DGNSS)

*Closest to what Lipton-style events often run today (Atlas fleet, not necessarily HALO).*

| Qty | Item | USD | Rand |
|----:|------|----:|-----:|
| 17 | Atlas 2 (boats) | 21 233 | 339 728 |
| 1 | Control Atlas 2 | 1 249 | 19 984 |
| 1 | Start pin Atlas 2 | 1 249 | 19 984 |
| 1 | Finish pin Atlas 2 | 1 249 | 19 984 |
| 4 | Mark Atlas 2 | 4 996 | 79 936 |
| 17 | RaceSense **month** pass | 850 | 13 600 |
| 1 | RC tablet (EST) | 80–150 | 1 280–2 400 |
| | **Subtotal A** | **~30 906–30 976** | **~R494 500–R495 600** |

Optional: dedicated Boat-end Atlas (manual “better range”) **+$1 249 / +R19 984**.

With **annual** passes instead of month: +**$1 683** / +**R26 928** (17×$99 net vs month).

---

## B — Vakaros **RaceSense RTK** (Atlas 2 + HALO on every boat)

*Fair compare to our cm RTK Boat Puck path.*

| Qty | Item | USD | Rand |
|----:|------|----:|-----:|
| Everything in A (month passes) | | ~30 906 | ~494 500 |
| 17 | **HALO RTK** | 10 183 | 162 928 |
| | **Subtotal B (retail floor)** | **~41 089** | **~R657 400** |

Still **missing** RTK base-station / Skylark event quote (Vakaros: *request a quote*). Real event B ≥ this.

If you also put HALO on Control+Pin+Finish+4 marks (7): **+$4 193 / +R67 088** → **~R724 500**.

---

## C — Our Lipton kit (reminder)

| | Low R | High R |
|--|------:|-------:|
| Full system + spares | **65 907** | **87 081** |
| Without spares | 61 543 | 81 164 |

---

## Head-to-head

| Kit | ~Rand | vs ours (mid ~R76k) |
|-----|------:|---------------------|
| **Boat Puck Lipton kit** | **66 000–87 000** | 1× |
| **Vakaros A — RaceSense + Atlas 2** | **~495 000** | **~6–7×** |
| **Vakaros B — + HALO on 17 boats** | **~657 000+** | **~8–10×** |
| **Vakaros B + HALO on infra too** | **~725 000+** | **~9–11×** |

### Per racing boat (sailor package only)

| | Rand | Notes |
|--|-----:|-------|
| Ours: Puck + IP68 tablet | **3 216–4 163** | Split radio + glass |
| Vakaros: Atlas 2 only | **19 984** | Glass+radio+GNSS in one |
| Vakaros: Atlas 2 + HALO | **29 568** | cm RTK tier |
| Vakaros: + month pass | **+800** | |

---

## What you’re not buying on Vakaros (and vice versa)

| | Vakaros | Ours |
|--|---------|------|
| Finished product + support | Yes | No (you build firmware/app) |
| Proven RaceSense software | Yes | You write it |
| Per-boat polished mast display | Atlas screen | Helm tablet (different UX) |
| Pass / licence fees | Yes | No Vakaros pass |
| Hardware for same Lipton shape | **~R0.5–0.7M+** | **~R0.07–0.09M** |

---

## One-line verdict

For a **17-boat Lipton-shaped** venue, **owning** a full Vakaros Atlas RaceSense fleet is about **R495k** at list (standard accuracy), or **~R657k+** with HALO on every boat — roughly **6–10×** our **R66–87k** hardware kit. That gap is the commercial product + software; it is not “same parts, different sticker.”
