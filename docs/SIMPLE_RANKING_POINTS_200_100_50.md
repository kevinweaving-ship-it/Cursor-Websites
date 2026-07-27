# Simple Ranking (Points) – 200 / 100 / 50

This is the **simple version** used for standings: event grade by type, then points by position.

---

## Event grades (E)

| Event type        | Grade (E) | 1st place gets |
|-------------------|-----------|-----------------|
| **Nationals**     | 200       | 200 points (2nd less, etc.) |
| **Provincial / Regional** | 100 | 100 points (2nd less, etc.) |
| **Club / other**  | 50        | 50 points (2nd less, etc.) |

- **Nationals:** event name contains "national", "nationals", "youth nationals", "wc ", "world champ" → E = 200.
- **Provincial/Regional:** "regional", "provincial", "championship" → E = 100.
- **Club/other:** everything else → E = 50.

---

## Points per position (same for all event types)

**EventPoints = E × (N − P + 1) / N**

- **E** = event grade (200, 100, or 50).
- **N** = number of boats in that class at that event (fleet size).
- **P** = finishing position (1st, 2nd, 3rd, …).

So:
- 1st → E × (N − 1 + 1) / N = **E** (full grade).
- 2nd → E × (N − 2 + 1) / N = E × (N − 1) / N.
- Last (P = N) → E × 1 / N.

Examples (N = 10):
- Nationals (E=200): 1st = 200, 2nd = 180, 3rd = 160, … 10th = 20.
- Provincial (E=100): 1st = 100, 2nd = 90, … 10th = 10.
- Club (E=50): 1st = 50, 2nd = 45, … 10th = 5.

---

## Ranking score and rank

- Each sailor gets **EventPoints** for each eligible regatta (last 12 months, min fleet size, etc.).
- **Best N results** count (N = result cap per class, typically 3–6).
- **RankingScore** = sum of those best EventPoints.
- **Rank** = order by RankingScore **descending** (higher score = better rank). Tie-breaks: then single best event, then next best, then most recent, then name.

---

## Where it’s implemented

- **Spec:** `docs/STANDINGS_DISPLAY_AND_CALCULATION_SPEC.md`
- **Calculation:** `calculate_universal_standings.py` (constants `GRADE_NATIONALS = 200`, `GRADE_PROVINCIAL = 100`, `GRADE_CLUB = 50`; `get_event_grade()`; EventPoints = E×(N−P+1)/N; writes to `standing_list`).
- **API (DB standings):** `GET /api/standings/db?class_name=...` returns pre-calculated ranks from `standing_list` (this simple points system).
- **Admin search** uses `GET /api/standings/db` for ranks (this simple 200/100/50 system). If the DB has no data for a class, the page falls back to `GET /api/standings` (head-to-head). “Open Regatta only” (e.g. regatta 374) still uses `GET /api/standings?open_regatta_only=true`. Keep standings up to date by running `calculate_universal_standings.py` after new results.
