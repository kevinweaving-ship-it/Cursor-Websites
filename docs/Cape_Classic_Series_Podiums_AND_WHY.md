# Cape Classic series — podiums and why the series exists

This doc is for **side-project / ops** work: **what** we call the “Cape Classic **series**”, **how** to list **podiums** (1st–3rd) from SailingSA data, and **why** the series is structured the way it is.

---

## 1. What “the series” is (Western Cape)

In common **Cape Classic Series / Grand Slam** wording, three **club-hosted** events form one **seasonal arc** (names and dates vary slightly by year):

| Leg | Host | Typical timing | Role |
|-----|------|----------------|------|
| **ZVYC** | Zeekoe Vlei YC | **Sept** | Spring / early-season **Classic** at Zeekoe Vlei |
| **HYC** | Hermanus YC | **Feb** | **Classic** at Kleinrivier Lagoon |
| **TSC** | Theewater SC | **Late Nov / Dec** | **Classic** inland at Theewater |

**Important:** SailingSA stores **each leg as its own `regatta_id`** (and usually **per-class blocks**). There is **no guarantee** in the database of a single **combined “series total”** row — **overall series champion** (if any) is **organiser / SAS** rules + often **published outside** our `results` table unless someone ingests it.

**Podiums we can always “work out” in-repo:** **per leg, per class** — `rank` **1, 2, 3** from `results` (same as any other regatta).

### Series eligibility — **3 of 3 classics minimum** (mandatory)

For any **overall Cape Classic series** table (combined ranking, series winner, series 1st–3rd) for a given **class / fleet**:

- A helm must have a **`results` row in all three legs** — **ZVYC + TSC + HYC** — for that class’s mapped `block_id`s.
- That is **3 of 3** — **not** 2 of 3, **not** “best two legs”, **not** dropped worst leg, unless you **explicitly** define a **separate** trophy with different rules.
- Sailors with only **one** or **two** legs may appear on **per-leg** podiums but **must not** be ranked in the **overall series** table unless the doc states a different rule.

---

## 2. Why this series matters (not results — **purpose**)

Use these **why** lines in copy, methodology, or TimAdvisor context:

1. **Regional weight** — In standings logic, events whose name matches **“cape classic”** are treated as **regional / championship tier** (see `docs/README_STANDINGS_RANKING.md` — Weight 2 style), so they **move** master standings **more** than a casual club day.
2. **Three venues, one narrative** — Sailors **travel** between **coastal Hermanus**, **Cape Town vlei**, and **Theewater** — it’s a **deliberate** **multi-venue** test (breeze, water type, fleet depth), not one club’s internal series.
3. **Calendar spread** — Legs sit **across the sailing year**, so **form** and **development** show over **months**, not one weekend.
4. **Branding** — Historical SAS listings use **“Cape Classic #1 / #2 / #3”** style; **capeclassicseries.co.za** (when used) ties the **story** together even when the DB is **per-event**.

---

## 3. How to list podiums (technical)

**Definition:** **Podium** = `results.rank` **IN (1, 2, 3)** for a given **`regatta_id`** + **`block_id`** (class fleet).

**Query pattern:**

```sql
SELECT regatta_id, block_id, helm_name, rank, nett_points_raw
FROM results
WHERE regatta_id = '<regatta_id>'
  AND block_id = '<block_id>'
  AND rank IS NOT NULL
  AND rank <= 3
ORDER BY rank;
```

**Quirk (seen on live):** `regatta_id` may be **`380-2026-hyc-cape-classic`** while `block_id` still uses **`385-2026-hyc-cape-classic:optimist-a`**. Always filter by **`regatta_id`** for “which event”, and **`block_id`** for “which fleet”.

---

## 4. “Series podium” vs “leg podium”

| Question | Answer |
|----------|--------|
| Leg podium | **Yes** — from DB as above. |
| Overall series ranking (1st–3rd for the **series**) | **Minimum:** helm has **3 of 3** leg results in that class (`COUNT(DISTINCT leg) = 3`). Otherwise **exclude** from overall series tables. |
| Official **overall** Cape Classic Series winner (all legs combined) | **Only if** the **organiser** publishes a **combined** score and/or we **ingest** it. **Not** auto-derived here unless you add a **series results** table or script. |
| Practical proxy | After **3/3** filter: e.g. **sum of leg ranks** or **sum of netts** — **document the rule** next to the table. |

---

## 5. Example — Optimist A, recent legs (live snapshot)

Legs where **`optimist-a`** (or `optimist-a-fleet`) blocks exist — **podiums only**:

### ZVYC — `359-2025-zvyc-southern-charter-cape-classic` (`…:optimist-a-fleet`)

| Rank | Helm | Nett |
|------|------|------|
| 1 | Timothy Weaving | 9 |
| 2 | Sean van Aswegen | 12 |
| 3 | Bazolele Mseswa | 22 |

### TSC — `371-2025-tsc-cape-classic` (`…:optimist-a`)

| Rank | Helm | Nett |
|------|------|------|
| 1 | Timothy Weaving | 6 |
| 2 | Nathan McCombe | 12 |
| 3 | Bazolele Mseswa | 13 |

### HYC — `380-2026-hyc-cape-classic` (block `385-2026-hyc-cape-classic:optimist-a`)

| Rank | Helm | Nett |
|------|------|------|
| 1 | Ben Madel | 6 |
| 2 | Lele Mseswa | 9 |
| 3 | James Tanner | 9 |

*Names/host spelling come from `results` as stored; same sailor may appear under different display names across events.*

**Narrative (example “why” for chat / report):** Across these legs, **Timothy** topped **ZVYC + TSC**; **Ben** topped **HYC** — different **winners per venue** is **normal** for a **multi-leg** series without a single ingested **combined** row.

---

## 6. Next steps (if you want a **combined** series table)

1. Confirm with **organiser** whether **official** series points exist for the year.
2. If yes: add **ingestion** (CSV or one row per sailor per series) **or** a small **Python** script that reads `results` for the three `regatta_id`s and applies a **declared** rule (e.g. **lowest sum of netts across three legs**).
3. Store **rule + year** in this doc or a sibling **`SERIES_SCORING_RULES.md`**.

---

## 7. Overall series podium (proxy) + **per-race** scores — Optimist A (live)

**Eligibility:** **3 of 3** Cape Classics in this class (see above). Optional extra filters (e.g. **current WC 2026 Optimist A** only) are **documented per table** when applied.

**Blocks:** ZVYC `359-2025-zvyc-southern-charter-cape-classic:optimist-a-fleet`, TSC `371-2025-tsc-cape-classic:optimist-a`, HYC `380-2026-hyc-cape-classic` / `385-2026-hyc-cape-classic:optimist-a`.

### Who meets **3 / 3** legs (same `helm_sa_sailing_id`)

Only **three** helms have a row in **each** of the three blocks (others missed a leg, e.g. no **HYC** result):

| Overall (proxy) | Sailor (as stored) | ZVYC rank / nett | TSC rank / nett | HYC rank / nett | **Sum of ranks** | Sum of netts |
|-----------------|--------------------|------------------|-----------------|-----------------|-------------------|--------------|
| **1** | **Bazolele Mseswa** / **Lele Mseswa** (SA **26437**) | 3 / 22 | 3 / 13 | 2 / 9 | **8** | 44 |
| **2** | **Ben Madel** (**14506**) | 6 / 44 | 5 / 17 | 1 / 6 | **12** | 67 |
| **3** | **Benjamin Fourie** (**25017**) | 5 / 32 | 7 / 30 | 6 / 20 | **18** | 82 |

**Proxy rule used:** lowest **sum of leg ranks** (tie-break: lower sum of netts). *Not* an official organiser rule — **document if you publish**.

**Timothy Weaving** (**21172**) won **ZVYC** and **TSC** but has **no** HYC row — **fails the 3/3 minimum** for **any** overall series podium. Per-race scores below are **informational only** (leg wins, not series-eligible).

---

### Per-race scores (`race_scores` JSON) — proposed **top 3** (all 3 legs)

Parentheses **( )** = discarded for nett **where shown** on the sheet.

#### 1) Bazolele Mseswa / Lele Mseswa (26437) — **best sum of ranks (8)**

| Leg | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 |
|-----|----|----|----|----|----|----|----|-----|
| **ZVYC** | 4 | 4 | 3 | 3 | 4 | (5) | 3 | 1 |
| **TSC** | 1 | 2 | 5 | 5 | — | — | — | — |
| **HYC** | (6) | 1 | 2 | 3 | 3 | — | — | — |

*TSC = 4 races; HYC = 5 races.*

#### 2) Ben Madel (14506)

| Leg | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 |
|-----|----|----|----|----|----|----|----|-----|
| **ZVYC** | (9 DNC) | 9 DNC | 9 DNC | 6 | 3 | 4 | 6 | 7 |
| **TSC** | 4 | 5 | 2 | 6 | — | — | — | — |
| **HYC** | (5) | 3 | 1 | 1 | 1 | — | — | — |

*ZVYC: first three races are **DNC** — explains **6th** there despite **winning HYC**.*

#### 3) Benjamin Fourie (25017)

| Leg | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 |
|-----|----|----|----|----|----|----|----|-----|
| **ZVYC** | (5) | 5 | 5 | 4 | 5 | 3 | 5 | 5 |
| **TSC** | 7 | 7 | 7 | 9 DNC | — | — | — | — |
| **HYC** | 7 | 4 | 3 | (6) | 6 | — | — | — |

---

### Per-race scores — **Timothy Weaving** (21172) — **2 legs only** (both **1st**)

| Leg | R1 | R2 | R3 | R4 | R5 | R6 | R7 | R8 |
|-----|----|----|----|----|----|----|----|-----|
| **ZVYC** | 1 | (2) | 1 | 1 | 2 | 1 | 1 | 2 |
| **TSC** | 2 | 1 | 1 | 2 | — | — | — | — |

*No **HYC** — **does not meet 3 of 3**; **not eligible** for overall series ranking under the mandatory rule.*

---

## 8. Series **top 3** by fleet (3 / 3 classics) — live snapshot

**Rule:** Only helms with a **result in all three** legs (ZVYC + TSC + HYC) for that fleet’s `block_id` mapping. **Ranking:** lowest **sum of leg ranks**, then lowest **sum of netts**.

**Legs:** `359-2025-zvyc-southern-charter-cape-classic`, `371-2025-tsc-cape-classic`, `380-2026-hyc-cape-classic` (HYC blocks use `385-2026-hyc-cape-classic:*`).

### Optimist A (`…optimist-a-fleet` / `…optimist-a` / `…optimist-a`)

| Series rank | Helm (as stored) | ZVYC | TSC | HYC | Σ ranks | Σ nett |
|-------------|------------------|------|-----|-----|---------|--------|
| 1 | Lele Mseswa (26437) *also Bazolele on earlier legs* | 3 | 3 | 2 | 8 | 44 |
| 2 | Ben Madel (14506) | 6 | 5 | 1 | 12 | 67 |
| 3 | Benjamin Fourie (25017) | 5 | 7 | 6 | 18 | 82 |

### ILCA 4.7 (`…ilca-4-fleet` / `…ilca47` / `…ilca4`)

| Series rank | Helm | ZVYC | TSC | HYC | Σ ranks | Σ nett |
|-------------|------|------|-----|-----|---------|--------|
| 1 | Joshua Keytel (13522) | 1 | 1 | 1 | 3 | 18 |
| 2 | Isabella Keytel (10148) | 5 | 3 | 4 | 12 | 83 |
| 3 | Patrick Jackson (3088) | 3 | 4 | 8 | 15 | 102 |

### Optimist B (`…optimist-b-fleet` / `…optimist-b` / `…optimist-b`)

Only **one** helm has **3 / 3** in this snapshot — **no** second/third for series unless more sailors complete all legs.

| Series rank | Helm | ZVYC | TSC | HYC | Σ ranks | Σ nett |
|-------------|------|------|-----|-----|---------|--------|
| 1 | Dwayne McCombe (25013) | 6 | 5 | 6 | 17 | 82 |

### 420 (`…420-fleet` / `…420` / `…420`)

Only **one** helm has **3 / 3**.

| Series rank | Helm | ZVYC | TSC | HYC | Σ ranks | Σ nett |
|-------------|------|------|-----|-----|---------|--------|
| 1 | Hayden Miller (8683) | 1 | 1 | 3 | 5 | 38 |

### Fleets **not** in this table (same class all three legs)

- **Mirror:** **HYC** has **no** `mirror` block (only e.g. **Open**); do **not** merge Mirror ZVYC/TSC with **Open** HYC without a **class filter**.
- **Hobie / Topaz / ILCA 6 / ILCA 7:** Block names **don’t** line up across all three regattas in the DB for a clean **3 / 3** map — add when `regatta_blocks` align.

**SQL tip:** Aggregate with `GROUP BY helm_sa_sailing_id` only (not `helm_name`), or **name changes** (Bazolele vs Lele) **split** rows.

---

## Related

- `docs/EVENT_SERIES_CANDIDATES.md` — recurring **event_name** → future `/events/series/{slug}`.
- `docs/README_STANDINGS_RANKING.md` — **Cape Classic** keyword and **weight**.
- `sas_events_list.csv` — SAS calendar rows for **HYC / TSC / ZVYC** Cape Classic dates.
