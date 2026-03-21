# `regattas.results_snapshot` format fix (v1)

## DB

- Migration: `database/migrations/182_regattas_results_snapshot.sql` — adds nullable `results_snapshot TEXT`.
- Apply on Postgres before API relies on `load_regatta_header_row` (SELECT includes this column).

## Code

- `header_validation.normalise_results_snapshot(raw_text)` — whitespace → comma, digits+commas only, collapse commas, strip ends.
- `validate_regatta_snapshot_race_list` — optional column; empty/NULL passes; else stored value must match `^\d+(,\d+)*$` or be normalisable to that (until one-time UPDATE, fixable rows still fail validation).
- `log_results_snapshot_parse_issue` → `logs/results_snapshot_parse_issues.log` when normalisation cannot yield a valid pattern (no DB UPDATE).

## One-time script

```bash
python3 scripts/fix_results_snapshot_format.py
```

Prints: `UPDATED:` / `SKIPPED:` / `REMAINING_INVALID:`

## QA note

Batch category **RESULTS_LINE_INVALID** includes **all** `field="results_snapshot"` issues from:

1. **Existing** `validate_results_snapshot(result_status, as_at_time, …)` (status / snapshot time / event dates) — this is the main driver of high counts today.
2. **New** race-list column rules when `results_snapshot` is non-empty.

Fixing only the **text column** does not clear (1); run the script after bad values exist in `results_snapshot`, then re-audit.

## Deploy

Ensure live server has updated `header_validation.py` next to `api.py` (not only `api.py`).
