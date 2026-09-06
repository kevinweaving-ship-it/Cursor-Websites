# Lipton event — inferred Vakaros **rental** bill

**FX:** R16 / $1 · **Date:** 2026-09-06  
**Event shape:** same as packed trails — **17 boats**, start pin, finish pin, **4 marks**, committee.

### Your rental assumptions (inputs)

| Role | Rule you gave | Rate used |
|------|---------------|----------:|
| Racing boat (Atlas package for the event) | **R1 800** / boat for the 4–5 day event | **1 800** |
| Committee boat package | **~2×** boat | **3 600** |
| Pin / mark / finish “unit” | **~¼** boat | **450** |

Treat **R1 800** as the **event hire** (whole series days), not per day.

---

## Do marks / pins have HALOs?

**Most likely: no — Atlas units only, RaceSense DGNSS (~15–25 cm), not HALO RTK.**

| Evidence | Read |
|----------|------|
| HALO is sold as **per-boat** RTK sensor + LED ring; needs hull measure / class install | Marks/pins don’t need sailor UI or hull model the same way |
| RaceSense manual: pin / boat-end / control / marks = **Atlas** “RC devices” / “mark devices” | Same Atlas brick, different role in the app |
| Lipton OCS bar we measured fits **RaceSense DGNSS**, not “must be 1 cm HALO” | See [`accuracy-vs-racesense-pins.md`](accuracy-vs-racesense-pins.md) |
| HALO / RaceSense RTK event pricing is **quote-only** and marketed as a **higher tier** (worlds-class) | Lipton 2026 more plausibly standard RaceSense |

**So for rental maths:** boat hire ≈ Atlas 2 (+ RaceSense pass baked into event rate).  
Pin / mark / finish / control hire ≈ **Atlas as infra**, not Atlas+HALO.  
If they *did* run HALO, boat rate would usually be higher than a plain Atlas hire — we don’t have that invoice.

---

## Unit count (Lipton shape)

| Qty | What (Vakaros role) | Rate R | Line R |
|----:|---------------------|-------:|-------:|
| 17 | Boat Atlas (sailor) | 1 800 | **30 600** |
| 1 | Committee package (Control Atlas + RC tablet + ops) @ 2× | 3 600 | **3 600** |
| 1 | Start pin Atlas | 450 | **450** |
| 1 | Finish pin Atlas | 450 | **450** |
| 4 | Course mark Atlases | 450 | **1 800** |
| | **Event rental total** | | **36 900** |

### Optional add (only if they used “recommended” dedicated boat-end Atlas)

RaceSense manual prefers dedicated **Control + Boat-end + Pin** (3 units) instead of Control doubling as boat-end.

| Extra | Rate R | Line R |
|-------|-------:|-------:|
| +1 Boat-end Atlas @ ¼ | 450 | **450** |
| **Total with boat-end** | | **37 350** |

### Spares (unknown — often 1–2 loan Atlases)

| Guess | Line R |
|-------|-------:|
| +2 spare boat Atlases @ 1 800 | +3 600 → **40 500** |
| or spares @ infra rate 450 | +900 → **37 800** |

---

## Implied “what they pay for everything else”

If boat = **R1 800** = 100%:

| Bucket | Line R | Share of R36 900 |
|--------|-------:|-----------------:|
| 17 boats | 30 600 | **83%** |
| Committee @ 2× | 3 600 | **10%** |
| Start + finish + 4 marks (6 × 450) | 2 700 | **7%** |

So under your ratios, **almost all the rental bill is the 17 boat Atlases**. Infra is cheap in rental terms even though each pin/mark is a full Atlas at retail.

### Sanity check vs retail

| | Retail Atlas 2 | Your rental R1 800 |
|--|---------------:|-------------------:|
| List | **R19 984** ($1 249) | — |
| Event hire as % of list | — | **~9%** of retail for 4–5 days |

That’s a plausible **event hire** fraction (roughly **1/11 of buy price** for under a week).  
Infra @ R450 ≈ **2.3% of retail** per unit — aggressive if true, or the “¼ boat” rate is a bundled/discounted mark rate, not a true separate Atlas hire. Either way, **boats dominate**.

---

## Headline answer

| Question | Answer |
|----------|--------|
| HALO on marks/pins? | **Unlikely** — expect **Atlas** roles; HALO mainly on **boats** if used at all |
| Rental bill (your rates, Lipton counts) | **~R36 900** |
| With dedicated boat-end Atlas | **~R37 350** |
| With 2 spare boat hires | **~R40 500** |

**Best single number to use:** **~R37 000** for the event rental under your R1 800 / 2× committee / ¼ infra assumptions.

Compare: our **buy** kit for the same shape is **R66–87k** (own forever) vs their **~R37k rent** for one Lipton — different economics (one week vs capital).
