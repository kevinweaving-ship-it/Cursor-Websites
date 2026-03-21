## Results Passing Workflow (Per User Spec)

1. **Regatta Intake**
   - Capture the regatta number supplied.
   - Confirm the regatta name against `regatta-admin-V22.html`.
   - Verify both local and URL source documents.  
   - If OCR/extraction fails on those sources, stop and request the results sheet.

2. **Header & Fleet Context**
   - From the results sheet extract the three HTML header lines:  
     i. Regatta name  
     ii. Host (club code)  
     iii. **Results status line** (see format below)
   - Record the fleet label (starting with the first fleet if multiple).
   - Capture the sailed line: `Sailed: U, Discards: V, To count: W, Entries: X, Scoring system: Y`.

   **Results status line — sentence and date/time format (canonical)**  
   - **Display sentence:** `Results are [Provisional|Final] as at DD Month YYYY at HH:MM`  
     Example: `Results are Provisional as at 15 February 2026 at 14:20`
   - **Date/time format:** DD = two-digit day (e.g. `15`), Month = full month name (e.g. `February`), YYYY = four-digit year, HH:MM = 24-hour time (e.g. `14:20`). Do not use "as of"; use **"as at"**.
   - **Where to store:** `regattas.result_status` = status word (e.g. `'Provisional'`, `'Final'`); `regattas.as_at_time` = timestamp in DB (e.g. `'2026-02-15 14:20:00'`). If regattas is not populated, the API may use `results.result_status` and `results.as_at_time` from the first result row. Never use current date/time or event start/end date as the "as at" value.

   **Pass header to regatta_viewer** — Store extracted header so `regatta_viewer.html` can display it:
   - **regattas**: `result_status` = X (e.g. `'Provisional'`, `'Final'`, `'Provisional - Day 1 of 2'`); `as_at_time` = Y at Z as timestamp (e.g. `'2026-02-15 14:20:00'`). Use `UPDATE regattas SET result_status=..., as_at_time=... WHERE regatta_id=...` when adding results.
   - **regatta_blocks**: `races_sailed` = U, `discard_count` = V, `to_count` = W, `scoring_system` = Y (e.g. `'Appendix A'`). Entries count comes from results.
   - The API returns these fields; regatta_viewer shows them in the header bar and fleet strips.

3. **Sailor Identification**
   - List every helm and crew before processing ranks.
   - For each sailor:
     a. Attempt SA ID match.  
     b. If no SA ID, check for existing Temp ID.  
     c. If still unmatched, consult prior results and/or sail number (within class) to locate an ID.  
   - Always use the canonical name from SA ID/Temp. Apply the correct club code (crew inherits helm club if missing).
   - Output two sets: matched sailors and those still requiring Temp/None so the user can advise.

4. **Rank Extraction**
   - Once the sailor list is resolved, process ranks sequentially. For each rank:
     - Use the validated helm/crew IDs from step 3.
     - Extract class, fleet, sail number, boat name, bow/jib numbers, race scores, totals, nett, and penalties/ISP.
     - Apply discard colouring (yellow for normal discards, red for ISP discards) and maintain score formatting.
     - Run checksums and scoring rules before insertion.

5. **Fleet Completion**
   - After rank 1 is passed, continue rank-by-rank (2, 3, …) until the fleet is complete.
   - Repeat the same workflow for additional fleets: confirm fleet data, reuse sailor process, then capture ranks.

**Club reference (recent additions)**
- `Plett` → Plettenberg Bay Yacht Club (`club_id` 132)
- `CAT` → Catamaran Association Team (`club_id` 133)

