# Results HTML "Results are" status line — read-back rule

**Applies to:** All results reports/sheets (regatta results HTML, class results, podium, full regatta, standalone viewer).

## Canonical rule (do not change)

- **Display sentence (strict):**  
  `Results are [Provisional|Final] as at DD Month YYYY at HH:MM`

- **Date/time format:**  
  DD = two-digit day (e.g. `15`).  
  Month = full month name (e.g. `February`).  
  YYYY = four-digit year.  
  HH:MM = 24-hour time (e.g. `14:20`).  
  Use **"as at"** (not "as of").

- **Example:**  
  `Results are Provisional as at 15 February 2026 at 14:20`

- **Source (database):**  
  - `regattas.result_status` (e.g. `'Provisional'`, `'Final'`).  
  - `regattas.as_at_time` as timestamp (e.g. `'2026-02-15 14:20:00'`).  
  - API may fall back to `results.result_status` / `results.as_at_time` when regattas is null.

- **Do not:**  
  Use current date/time, or event start/end date, as placeholder for "as at".

## How it’s applied (from results/regattas → header of each results page)

- **Source:** `regattas.result_status` and `regattas.as_at_time` (API may fall back to `results.result_status` / `results.as_at_time` when regattas is null).
- **Use:** The header of each results page (class results, full regatta, podium, standalone) shows one status line built from that: **Results are [result_status] as at [formatted as_at_time]** in the format above.

## Where it’s defined

- **`docs/RESULTS_PASSING_WORKFLOW.md`** — Results status line (sentence and date/time format).
- **`README.md`** — "Results Data Pass / HTML Header Data" (Line 3, Results Status Line).
- **`docs/README_regattas_table.md`** — as_at_time and format in HTML.

When editing any results HTML or the API that serves this line, follow this rule and do not introduce different wording or formats.
