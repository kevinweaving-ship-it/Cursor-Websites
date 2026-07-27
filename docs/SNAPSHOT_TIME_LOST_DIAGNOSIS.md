# Diagnosis: Where Snapshot Time Is Lost (Results Import Pipeline)

**Symptom:** The results sheet clearly states e.g. "Results are provisional as of 14:20 on February 15, 2026", but `regattas.as_at_time` and `results.as_at_time` are NULL, so the header shows "(snapshot time not recorded)" or a wrong fallback.

**Conclusion:** The snapshot timestamp is **never parsed by code** and **never written to the DB** in the current import pipeline. It exists only on the source document; no step in the pipeline extracts it or persists it.

---

## 1. Search Results (Project-Wide)

### "provisional as of" / "as of"
- **No code** in the repo parses or matches the phrase "provisional as of" or "as of" for results.
- Docs only: `docs/RESULTS_PASSING_WORKFLOW.md`, `docs/README_regattas_table.md` describe the **canonical format** ("as at" not "as of") and where to store it.

### "as at" / snapshot / as_at
- **api.py**: Reads/writes `as_at_time` from DB (COALESCE in regatta API, `_ensure_snapshot_integrity`, `_get_regatta_full_page_data` fallback). **No parsing of document text.**
- **sailingsa/deploy/export_regatta_385_data.py**: Exports `as_at_time` in `REGATTAS_COLS`; does not parse any sheet.
- **No script** parses a results sheet (HTML/PDF) to extract an "as at" date/time string.

### BeautifulSoup usage
- **api.py** uses BeautifulSoup in:
  - `_fetch_sailing_magazine_news()` — sailing.co.za news, not results.
  - `run_daily_scrape` — SA Sailing member-finder pages (sailing_id), not regatta results.
- **No BeautifulSoup (or other) parsing of regatta results HTML/PDF** anywhere in the project.

### Results header parsing
- **No code** implements "results header parsing" or "three HTML header lines" (event name, host, status line) from a results sheet.
- **docs/RESULTS_PASSING_WORKFLOW.md** describes this as a **human workflow**: "From the results sheet extract the three HTML header lines" and "Use UPDATE regattas SET result_status=..., as_at_time=... when adding results." The doc assumes a human (or future tool) does the extraction; no such tool exists in the repo.

---

## 2. Which File Parses the Regatta Results HTML/PDF?

**None.** There is no file that parses regatta results HTML or PDF.

- **add_regatta_385_*.py**, **amend_regatta_385_*.py**: Use **hardcoded** `RAW_DATA` / `ENTRIES` (rank, sail, club, helm, crew, race scores). Comments say "From results sheet" meaning the human source; data is transcribed manually into the script. No file read, no URL fetch, no HTML/PDF parsing.
- **add_regatta_375_entries.py**: Inserts regatta + results from an embedded TSV string (entries data). No results-sheet header parsing; regatta INSERT has no `as_at_time`.
- **add_regattas_377_384_no_results.py**: Inserts regattas (no results); has `result_status` but no `as_at_time`.
- **export_regatta_385_data.py**: Exports existing DB rows to SQL; does not read or parse any document.
- **scrape_sas_events_historical.py**: Scrapes event list / NOR PDF links; not results sheet content.

So: **the header line containing the snapshot time is never read by any program** in this project.

---

## 3. Is the Parsed Snapshot Time Ever Written to the DB?

### results.as_at_time
- **Not written on import.** All `INSERT INTO results` in add_regatta_385_*.py, amend_*.py, add_regatta_375_entries.py omit `as_at_time` (column not in INSERT list). So every new result row is created with `results.as_at_time = NULL`.
- **Written only by** `_ensure_snapshot_integrity()` in api.py when results are updated via PATCH (result or race) or bulk_auto_match — and then it sets `NOW()`, not a value from a sheet.

### regattas.as_at_time
- **Not written on import.**  
  - `add_regatta_375_entries.py`: INSERT regattas has `(regatta_id, event_name, start_date, end_date, result_status)` — **no as_at_time**.  
  - `add_regattas_377_384_no_results.py`: INSERT regattas has `result_status` but **no as_at_time**.  
  - add_regatta_385_* and amend_* do not INSERT/UPDATE regattas at all; they assume the regatta already exists and only touch regatta_blocks and results.
- **Written only by** `_ensure_snapshot_integrity()` in api.py (sets `NOW()` when NULL and regatta has results).

So: **the snapshot time from the results sheet is never written to `results.as_at_time` or `regattas.as_at_time`.** It is never extracted, so it cannot be written.

---

## 4. Where the Snapshot Time Is Lost (Root Cause)

- **Source of truth:** The results sheet (HTML or PDF) contains a line like "Results are provisional as of 14:20 on February 15, 2026". That timestamp exists only there.
- **Intended flow (per docs):** RESULTS_PASSING_WORKFLOW.md says: extract the results status line from the sheet; store `regattas.result_status` and `regattas.as_at_time`; when adding results, use `UPDATE regattas SET result_status=..., as_at_time=...`.
- **Actual flow:** Scripts are written with hardcoded or pasted entry/score data. They do not:
  1. Read the results sheet (HTML/PDF),
  2. Parse the status line,
  3. Accept or pass `as_at_time` (or result_status from the sheet) into the DB.

So the snapshot time is **lost** because:
1. **It is never extracted** — no parser exists for the results sheet header.
2. **Import scripts do not write it** — they never set `regattas.as_at_time` or `results.as_at_time` from any input.

---

## 5. Where to Insert the Fix (Import Pipeline)

To persist the snapshot time from the sheet:

- **If a parser is added** (new or existing script that reads results HTML/PDF):
  - In that same script, after parsing the status line (e.g. "Results are Provisional as at 15 February 2026 at 14:20"):
    - Parse the date/time into a single timestamp (e.g. `2026-02-15 14:20:00`).
    - Before or after inserting/updating result rows, run:
      - `UPDATE regattas SET result_status = %s, as_at_time = %s WHERE regatta_id = %s`
      - and/or set `as_at_time` on each inserted result row (if the schema and workflow use per-row snapshot).
  - **Exact location:** In the **same function** that parses the results sheet header and performs the regatta/results INSERT/UPDATE, add the `UPDATE regattas SET result_status=..., as_at_time=...` (and optionally set `results.as_at_time` for inserted rows) immediately after the header is parsed and before or after the bulk insert/update.

- **If import remains manual** (human transcribes from sheet into scripts):
  - Add an explicit step in the import scripts: accept or hardcode `result_status` and `as_at_time` (from the sheet) and run:
    - `UPDATE regattas SET result_status = %s, as_at_time = %s WHERE regatta_id = %s`
    after creating/updating the regatta and before or after inserting results.
  - **Exact location:** In each script that creates or updates a regatta and then inserts results (e.g. first run of add_regatta_385_* for a new regatta, or a small shared "apply header" step), immediately after the regatta exists and before or after result INSERTs, execute that UPDATE with the snapshot time from the sheet.

**No such parser or UPDATE step exists today;** adding one of the two approaches above is where the snapshot time must be inserted into the pipeline so it is written to the DB.

---

## 6. Summary Table

| Question | Answer |
|---------|--------|
| Which file parses the regatta results HTML/PDF? | **None.** No file parses results sheet HTML/PDF. |
| Where is the header line with snapshot time read? | **Nowhere.** It is never read by code. |
| Parsed datetime: extracted but not stored? | N/A — not extracted. |
| Parsed datetime: in temp variable but discarded? | N/A — no parsing. |
| Parsed datetime: never extracted at all? | **Yes.** |
| Is that value ever written to `results.as_at_time`? | **No.** |
| Is that value ever written to `regattas.as_at_time`? | **No.** |
| Where should it be inserted? | In the import pipeline: either (a) in a new/added parser, right after parsing the status line and before/after DB insert/update, or (b) in existing scripts, as an explicit `UPDATE regattas SET result_status=..., as_at_time=...` (and optionally set `results.as_at_time`) using the value from the sheet. |

---

*Diagnosis only; no code was modified.*
