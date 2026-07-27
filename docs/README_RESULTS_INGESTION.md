# Results ingestion – class resolution and ingestion issues

Manual parsed-results ingestion (scripts that insert into `results`, e.g. `add_regatta_385_420_fleet.py`) uses **strict class resolution**. No fuzzy matching, no auto-creation of classes, no guessing.

---

## 🔐 Canonical URL & Date Authority Rules (LOCKED)

**Regatta URL slug and dates must reflect regatta start/end date — NOT parse/import date.**

- **Source of truth:** `regattas.start_date` / `regattas.end_date`
- **Never use:** file upload timestamp, ingest timestamp, parse timestamp, `current_date`
- **Sitemap `<lastmod>` for regatta-result URLs** must equal `regattas.end_date`. If `end_date` is NULL, fallback to `start_date`. Never use `updated_at` for regatta-result lastmod unless it is an upcoming event URL.
- **Results ingestion must NOT modify** `regattas.start_date` or `regattas.end_date` unless explicitly corrected by admin. Parsing a file must not overwrite `start_date` or `end_date`.

### Slug Stability Rule

If results are re-imported, corrected, or re-parsed:

- URL must remain identical.
- Slug must not change.
- Only content changes, not canonical path.

### SEO Integrity Rule

Google canonicalization depends on event date stability. **Any logic that ties URL or sitemap dates to import date is considered a critical bug.**

---

## ⚠️ Developer Warning

**DO NOT tie URL or sitemap dates to file ingestion timestamp.**  
Only `regattas.start_date` / `regattas.end_date` are authoritative for regatta-result URLs and lastmod.

---

## Race class vs family class rule

- **Only classes with `is_race_class = TRUE`** may be inserted into `results`.
- **Family classes** (e.g. Optimist, ILCA) are aggregate-only and **must never** be stored in `results`. Use the concrete race classes (e.g. Optimist A, Optimist B, Optimist C; Ilca 4.7, Ilca 6, Ilca 7).
- If a resolved class has `is_race_class = FALSE`, ingestion **hard-fails** and logs one row to `ingestion_issues` (same as for unknown class).

---

## Class matching rules

- Class labels must **exactly match** `classes.class_name` (after normalisation: TRIM, collapse whitespace, **case-insensitive**).
- Variants such as `ILCA 4`, `Ilca4`, `ILCA4` are **not** matched by fuzzy logic. Handle them via the **`class_aliases`** table (alias → `class_id`).
- **No new classes are ever created** from results ingestion. Add the class (or an alias) in the database first, then re-run the script.

---

## Class resolution rules

1. **Normalise** the raw label: TRIM, collapse multiple spaces, casefold (for comparison).
2. **Resolve** using only:
   - `JOIN classes ON LOWER(TRIM(classes.class_name)) = normalised_label`
   - If no row: lookup `class_aliases` where `LOWER(TRIM(alias)) = normalised_label` → use that `class_id`.
3. **Do not** fuzzy match, auto-create classes, or guess (e.g. "Ilca 4" → "Ilca 4.7").
4. If no match → **block insertion** and write one row to `ingestion_issues` per unknown label; return a clear error summary (counts per unknown class label).

---

## How to add an alias (`class_aliases`)

If the source data uses a variant (e.g. `"ILCA 4"`) and the canonical class in `classes` is `"ILCA 4.7"`:

1. Ensure the table exists (ingestion scripts call `ensure_class_aliases_table(conn)`):
   ```sql
   CREATE TABLE IF NOT EXISTS class_aliases (
       id SERIAL PRIMARY KEY,
       alias TEXT NOT NULL,
       class_id INTEGER NOT NULL REFERENCES classes(class_id),
       created_at TIMESTAMPTZ DEFAULT NOW(),
       UNIQUE(LOWER(TRIM(alias)))
   );
   ```
2. Insert the mapping (use the `class_id` from `classes` for the target class):
   ```sql
   INSERT INTO class_aliases (alias, class_id)
   SELECT 'ILCA 4', class_id FROM classes WHERE LOWER(TRIM(class_name)) = 'ilca 4.7'
   WHERE NOT EXISTS (SELECT 1 FROM class_aliases WHERE LOWER(TRIM(alias)) = 'ilca 4');
   ```
   Or with explicit `class_id`:
   ```sql
   INSERT INTO class_aliases (alias, class_id) VALUES ('ILCA 4', 8);
   ```
3. Re-run the ingestion script; the same raw label will resolve to that `class_id`.

---

## What happens when an unknown class appears

1. **No results rows** are inserted for that class.
2. **One row** is written to **`ingestion_issues`** with:
   - `regatta_id`, `source_file`, `raw_class_label`
   - `sample_row_json` (one sample result row for debugging)
   - `created_at`, `status = 'OPEN'`
3. The script prints an **error summary**, for example:
   - `ERROR: Unknown class label. No block or results inserted.`
   - `Unknown class: 'Topper 5.3' (normalised: must match classes.class_name or class_aliases)`
   - `Blocked rows: 12`
   - `One row written to ingestion_issues. Add class or alias then re-run.`

---

## How to resolve ingestion_issues and re-run

1. **Inspect** open issues:
   ```sql
   SELECT id, regatta_id, source_file, raw_class_label, sample_row_json, created_at, status
   FROM ingestion_issues WHERE status = 'OPEN' ORDER BY created_at DESC;
   ```
2. **Fix** the missing class:
   - **Option A:** Add a row to `classes` with the correct `class_name` (if it’s a new boat class).
   - **Option B:** Add a row to `class_aliases` mapping the raw label (or its normalised form) to an existing `classes.class_id`.
3. **Mark** the issue resolved (optional):
   ```sql
   UPDATE ingestion_issues SET status = 'RESOLVED' WHERE id = <id>;
   ```
4. **Re-run** the ingestion script (e.g. `add_regatta_385_420_fleet.py`). It will resolve the class and insert results (and set `results.class_id` and `results.class_canonical` from `classes`).

---

## Example: unknown class blocked and queued

```
$ python add_regatta_385_420_fleet.py
ERROR: Unknown class label. No block or results inserted.
  Unknown class: 'Topper 5.3' (normalised: must match classes.class_name or class_aliases)
  Blocked rows: 9
  One row written to ingestion_issues. Add class or alias then re-run.
```

After adding `Topper 5.3` to `classes` or adding an alias in `class_aliases`, re-run:

```
$ python add_regatta_385_420_fleet.py
Block 385-2026-hyc-cape-classic:420 created/updated
Inserted 9 results for 420 fleet (class_id=229, class_canonical=420)
```

---

## Sailor resolution guardrail

- **Never create or assign a fake SAS ID.** If a sailor cannot be resolved to a row in `sas_id_personal` or `sailor_helm_aliases`, set `helm_sa_sailing_id` (and `crew_sa_sailing_id`) to **NULL** so the row goes to the review queue.
- Use **`resolve_helm_to_sa_id(cur, helm_name, sail_number)`** from `results_ingestion_common`: it returns a single `sa_sailing_id` (int) only when the match is unambiguous; otherwise `None`. Ingestion must use this (or an equivalent that only returns IDs that exist in `sas_id_personal` / `sailor_helm_aliases`).

---

## Shared module

- **`results_ingestion_common.py`** provides:
  - `resolve_class_id(cur, raw_label)` → `class_id` or `None`
  - `require_class_id(conn, cur, raw_label, regatta_id, source_file, sample_row)` → `(class_id, class_canonical)` or raise; unknown class → log to ingestion_issues and stop.
  - `get_class_name_by_id(cur, class_id)` → `class_name` for writing `results.class_canonical`
  - **`resolve_helm_to_sa_id(cur, helm_name, sail_number)`** → `sa_sailing_id` (int) or `None`; only returns IDs from `sas_id_personal` / `sailor_helm_aliases`. If `None`, leave helm_sa_sailing_id NULL (review queue).
  - `ensure_class_aliases_table(conn)`, `ensure_ingestion_issues_table(conn)`
  - `record_ingestion_issue(cur, regatta_id, source_file, raw_class_label, sample_row_json, status='OPEN')`

Ingestion scripts should: (1) resolve class first; if unknown, record issue and exit. (2) Resolve sailor via `resolve_helm_to_sa_id`; if `None`, set `helm_sa_sailing_id = NULL` (review queue). Never set a SAS ID that is not from the resolver or from a known-valid source.

---

## Host club code (`CODE - Full name` on results)

When **`regattas.host_club_id`** is set but **`regattas.host_club_code`** is still empty, the public site should show the host as **`HYC - Hermanus Yacht Club`** (abbrev from `clubs.club_abbrev`, full name from `clubs.club_fullname`). That abbrev is stored on **`regattas.host_club_code`** when present.

**Automatic (no extra step in most flows):**

- **`header_validation.revalidate_and_persist`** (e.g. admin **Mark ready**, header revalidation) runs **`persist_regatta_host_club_code_from_clubs_cur`** so the code is filled from `clubs` whenever validation persists.
- **`bulk_auto_match_regatta`** and result-edit API paths (`PATCH /api/result/...`, race score edits, etc.) also refresh **`host_club_code`** when **`host_club_id`** is set.

**Manual ingestion scripts** (raw SQL that sets `host_club_id` without going through the API) should call the same helper after commit:

```python
from regatta_host_code import persist_regatta_host_club_code_from_clubs_cur

# after UPDATE regattas SET host_club_id = ... (same connection):
persist_regatta_host_club_code_from_clubs_cur(cur, regatta_id)
conn.commit()
```

Or **`from api import persist_regatta_host_club_code_from_clubs`** (opens its own connection) if importing `api` is acceptable for that script.

**One-off backfill** (existing rows with `host_club_id` but blank `host_club_code`):

```sql
UPDATE regattas r
SET host_club_code = NULLIF(TRIM(c.club_abbrev), '')
FROM clubs c
WHERE c.club_id = r.host_club_id
  AND r.host_club_id IS NOT NULL
  AND NULLIF(TRIM(COALESCE(r.host_club_code, '')), '') IS NULL;
```

(Run only if column `regattas.host_club_code` exists.)
