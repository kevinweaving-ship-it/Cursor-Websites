# Pages and Display Format

All pages that show class ranking use the same display format for consistency.

## Display format

- **Ranked:** `Ranked X (Score: Z) out of Y sailors` — X = rank (e.g. 1st, 2nd), Z = ranking score when available, Y = total sailors in class (last 12 months, SAS ID).
- **Not ranked:** `Not ranked out of Y sailors` when the sailor is not in the standings list for that class but the class has Y sailors; or `Not ranked` when there is no class total.

Score is shown when `standing_list.ranking_score` is populated (by `recalc_standings_after_upload.py` / `calculate_universal_standings.py`). To get scores for all classes, run a full recalc: `python3 recalc_standings_after_upload.py`.

## Pages that show rank/score

| Page | Where shown |
|------|-------------|
| **search.html** | Sailor profile → class pills; Sailing Statistics header; Sailor Stats modal → per-class rank; member results table |
| **sailingsa/frontend/index.html** | Sailor Stats modal → Standing per class |
| **member-finder.html** | Class summary pills (Ranked X out of Y sailors); sailor stats rows |

## Data source

- **API:** `GET /api/standings/db?class_name=<Class Name>` returns `rankings` (with `main_rank`, `ranking_score`) and `total_sailors` (Y).
- **Y (total sailors):** From `standings_metadata.total_sailors_12m` when present, else live `get_total_sailors_in_class_last_12m()` — same source for all pages.

## Related docs

- `docs/RANKING_RULES_README.md` — ranking rules and recalc
- `docs/STANDINGS_RANK_SCORE_DISPLAY.md` — rank/score display
- `docs/STANDINGS_DISPLAY_AND_CALCULATION_SPEC.md` — calculation spec
