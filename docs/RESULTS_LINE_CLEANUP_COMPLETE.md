# RESULTS_LINE_CLEANUP_COMPLETE

**Scope:** RESULT_REGATTAS only (`regatta_id` in `public.results`).  
**Status:** Complete as a **controlled** cleanup — not “zero issues at any cost.”

## Locked baseline (reference)

| Metric | Value (example run) |
|--------|---------------------|
| TOTAL_RESULTS_REGATTAS | 117 |
| INVALID | 40 |
| RESULTS_LINE_INVALID | 21 |
| STATUS_UNRECOGNIZED | 12 |

Remaining `RESULTS_LINE_INVALID` / `STATUS_UNRECOGNIZED` are **expected** where status text cannot be safely canonicalised without human judgement.

## Rules (critical — do not loosen)

1. **Do not map `"Unknown"`** via `result_status_map` or any batch fix.
2. **Do not auto-fix** or fuzzy-map any other value — only **explicit** `INSERT`s into `public.result_status_map` for approved `(raw_status, canonical_status)` pairs.
3. **Approved mappings (exact strings only):**
   - **Map:** `Final` → `Final`, `Provisional` → `Provisional` (identity only if you choose to store them in the map for consistency; validator already accepts canonical `Final` / `Provisional` via `normalise_result_status`.)
   - **Do not map:** `Unknown`, blank, junk, or any value not explicitly approved.

## Scripts (workflow)

1. List distinct statuses (RESULT_REGATTAS, non-NULL):

   ```bash
   python3 scripts/list_distinct_result_statuses_results_only.py
   ```

2. Curate `public.result_status_map` manually (SQL or admin) — **no** `Unknown`.

3. Apply exact updates (RESULT_REGATTAS only):

   ```bash
   python3 scripts/apply_result_status_map.py
   ```

4. QA:

   ```bash
   python3 scripts/qa_results_line_metrics.py
   ```

## Expected “steady” state

After policy is applied, it is **normal** to still see roughly:

- **RESULTS_LINE_INVALID** ≈ count of regattas with unresolvable line issues (including intentional `Unknown` / manual-review cases).
- **STATUS_UNRECOGNIZED** ≈ regatta rows whose `result_status` is non-empty and **not** normalised by `normalise_result_status` (e.g. `Unknown`).

**Do not** “fix” these with system logic. They require **per-regatta manual review** (editorial / data owner), not automation.

## Completion checklist

- [x] All **valid** statuses normalised via `normalise_result_status` + optional **exact** `result_status_map` rows (no guessing).
- [x] **Unknown** statuses intentionally left unmapped.
- [x] No automatic guessing applied.
- [x] System suitable to build **stats / rankings** on rows with valid snapshot metadata; invalid rows stay flagged until manually fixed.

## Next (controlled)

**HOST / `host_club_id` linking** on the **results_only** regatta set — small dataset, high leverage. Keep the same discipline: no fuzzy club matching; explicit maps or manual resolution only.

---

*Document marks **RESULTS_LINE_CLEANUP_COMPLETE** — production-safe, tight scope; do not broaden auto-fix rules without an explicit product decision.*
