# How Ranks Are Calculated (Admin Search)

**Page:** `http://192.168.0.130:8081/admin/search.html` (served from root `search.html`)  
**Data source:** `GET /api/standings/db?class_name=<class>` — ranks use the **simple 200/100/50 points system** from the `standing_list` table (see `docs/SIMPLE_RANKING_POINTS_200_100_50.md`). If the DB has no data for that class, the page falls back to `GET /api/standings` (head-to-head). “Open Regatta only” still uses `GET /api/standings?open_regatta_only=true`.

---

## 1. Where the rank comes from

- The admin search page calls **`/api/standings/db?class_name=...`** (e.g. Optimist A, Optimist B, Dabchick, 420, etc.) for the **simple 200/100/50 points system**.
- Ranks are read from **`standing_list`** (filled by `calculate_universal_standings.py`). EventPoints = E×(N−P+1)/N with Nationals=200, Provincial/Regional=100, Club=50; best N results summed; sort by total descending.
- If the DB has no data for that class, the page falls back to **`/api/standings`** (head-to-head calculated in `api.py`).
- The API returns `rankings[]` with `main_rank` (1, 2, 3, …) and `total_sailors`. The UI uses `main_rank` as “current rank” and for “#X of Y sailors”.

---

## 2. Who is included (eligible sailors) — fallback / Open Regatta only

- **Helms only** (crew are not ranked separately).
- **Class:** Sailors who have at least one result in that **fleet** (e.g. Optimist A, Optimist B) in the database.
- **Regattas:** All regattas in the last **13 months** (by `end_date` or `start_date`), **excluding regatta 374** for the master list.
- **Raced:** Only results with `raced = TRUE` and a valid `rank` are used.

---

## 3. How the ranking is calculated (head-to-head) — fallback / Open Regatta only

1. **Eligible sailors**  
   All distinct helms with ≥1 raced result in that class (excluding 374 for master list).

2. **Eligible regattas**  
   All regattas for that class in the last 13 months (excluding 374), ordered by importance then size/date.

3. **Regatta weight** (for tie-breaking / weighting)
   - **3** = National / Nationals
   - **2** = Regional / Championship
   - **1** = Club / Provincial  
   Larger regattas (more entries) get an extra weight factor.

4. **Head-to-head (H2H) matrix**  
   For each regatta, for each **block** (fleet):
   - Load all results (sailor_id, rank).
   - For every pair of sailors in that block: lower `rank` = win, higher = loss, same = tie.
   - Store wins/losses/ties, plus weighted wins and “large regatta” / “major” / “vs nationals sailor” counts.

5. **Per-sailor stats**
   - `regatta_count`, `total_rank`, `ranks[]` (all finishes), `wins`, `losses`, `ties`.
   - `win_rate`, `avg_rank`, `improvement` (first vs last rank), `recent_change` (early 3 vs last 3 regattas).

6. **Sort order (who is “above” whom)**  
   Comparison uses this priority:
   - **1. Direct head-to-head**  
     If A and B have raced each other: more H2H wins → higher rank. If tied on wins, **most recent** H2H result wins.
   - **2. No H2H**  
     Use regatta count (more = better), then `avg_rank` (lower = better), then `win_rate` (higher = better).
   - **3. H2H tie-breakers**  
     When H2H wins are equal: large-regatta H2H wins → major (nationals) H2H wins → weighted wins.
   - **4. Final tie-breakers**  
     `avg_rank` → `win_rate` → regatta count.

7. **Stability pass (“dynamic standings”)**  
   Iteratively: if a sailor ranked **below** has more H2H wins over a sailor **above**, swap them. Repeat until no swaps (max 100 iterations).

8. **Double-handed adjustment (Optimist A/B)**  
   Sailors who have crew in their results are moved **down 2 places** in the final order.

9. **Assign rank numbers**  
   After the final order: `main_rank = "1"`, `"2"`, … `"N"` by position.  
   `total_sailors` = number of eligible sailors (same N for “out of Y”).

---

## 4. Special cases

- **`open_regatta_only=true`**  
  When “Open Regatta only” is checked (Optimist A/B), the page calls **`/api/standings?open_regatta_only=true`** — returns only **regatta 374** entries (head-to-head order). Default list (no checkbox) uses **`/api/standings/db`** (simple 200/100/50).

- **Other classes (e.g. Dabchick, 420)**  
  Ranks from **`/api/standings/db`** (simple points system). If no data in `standing_list`, fallback is **`/api/standings`** (head-to-head).

---

## 5. Simple 200/100/50 system (primary for admin search)

- **Spec:** `docs/SIMPLE_RANKING_POINTS_200_100_50.md`  
  Event grades: Nationals 200, Provincial/Regional 100, Club 50. **EventPoints = E×(N−P+1)/N**. Sum best N results; rank by total descending.
- **Used by:** `calculate_universal_standings.py` → writes **`standing_list`**. **`GET /api/standings/db?class_name=...`** reads it.
- **Admin search** uses **`/api/standings/db`** for the main standings list (simple system). Fallback to **`/api/standings`** (head-to-head) when DB has no data for that class.

---

## 6. Summary table

| What you see on admin search | Source |
|-----------------------------|--------|
| “Ranked X of Y sailors” / “#X” (default) | `GET /api/standings/db?class_name=...` → `rankings[].main_rank`, `total_sailors` |
| How `main_rank` is determined | Simple 200/100/50: EventPoints = E×(N−P+1)/N, sum best N, sort descending (see `standing_list`) |
| Fallback when DB empty | `GET /api/standings` (head-to-head in `api.py`) |
| “Open Regatta only” checked | `GET /api/standings?open_regatta_only=true` (head-to-head, 374 entries only) |

**Code:** Primary: `api.py` — `@app.get("/api/standings/db")` (~6925); standings from `standing_list`. Fallback: `@app.get("/api/standings")` (~5259). Population: `calculate_universal_standings.py`.
