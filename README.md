# Project 6 — Working Notes / Quick Start

## ⚠️ CRITICAL: MANDATORY DATA EXTRACTION WORKFLOW

**BEFORE asking user for ANY data, read:**
- `docs/MANDATORY_DATA_EXTRACTION_WORKFLOW.md` - **MUST FOLLOW**
- Run: `admin/tools/PRE_DATA_REQUEST_CHECKLIST.sh` before any data request
- **NEVER ask for data that user already confirmed as provided**

### ⚠️ REPEATED ISSUE: FALSE CLAIMS ABOUT MISSING DATA

**CRITICAL WARNING**: The assistant has repeatedly (50+ times) claimed data is missing when it was actually provided in image descriptions. 

**NEVER claim data is missing when:**
- Image description says "All X entries have complete race scores"
- Image description provides detailed breakdown for all entries
- User provides raw data with all entries listed
- Image description explicitly states "9 rows of data" or similar

**Example of FALSE claim (DO NOT DO THIS):**
> "I've inserted the 3 entries with complete data (ranks 1, 2, 9) and applied the complete workflow. The remaining 6 entries (ranks 3–8) need race scores that aren't in the image description."

**When image description says "All 9 entries have complete race scores R1-R8" and provides detailed data for all 9 entries, ALL 9 entries must be extracted and inserted. DO NOT claim only 3 are available.**

**If you cannot extract data from image description, check:**
1. PDF/URL sources in database
2. HTML files in Project 4
3. Previous chat history
4. Image description more carefully - ALL data is usually there

**DO NOT LIE about missing data. Extract ALL available data immediately.**

This repository contains an isolated copy of the viewer and API used for development and staging.

## Components

- **API (FastAPI)**: `Project 6/api.py` running on port 8081
- **Static viewer**: `Project 6/regatta_viewer.html` (served locally via Python http.server on 8090)
- **Docs**: `Project 6/docs/`
  - Paste your scope/brief into `docs/brief.md`
  - **Data Format Specifications**: `docs/DATA_FORMAT_SPECIFICATIONS.md` - **CRITICAL** - Standard formats for all tables/columns (must read before data entry)
  - **Data Standardization Philosophy**: `docs/DATA_STANDARDIZATION_PHILOSOPHY.md` - Core principle: fix data in DB, HTML displays raw
  - **Fleet/Class Hierarchy**: `docs/FLEET_CLASS_HIERARCHY.md` - Parent/sub-class structure rules
  - **Data Entry Guidelines**: `docs/DATA_ENTRY_GUIDELINES.md` - Quick checklist and common mistakes
  - **Display Rules**: `docs/README_DISPLAY_RULES.md` - **CRITICAL** - Rank ordinals, name display from SA ID table, ISP codes (red), discards (yellow/red brackets)
- **Live deploy / SSH**: **`sailingsa/deploy/SSH_LIVE.md`** - Server, expect scripts, fix scripts, sync. Use this for any live work. Never claim "SSH is blocked." **All fixes (sailor URLs, 385 data, etc.) must be deployed to production** via the readme (deploy code + sync 385); local-only changes do not affect sailingsa.co.za.

### SITEMAP ARCHITECTURE — FROZEN (Mar 2026)

Sitemap is static-file only (Nginx serves `/var/www/sailingsa/static/sitemap.xml`). Rebuild runs only after results ingestion, regatta create/edit, or `result_status` update (event-driven; never on GET or page view). **Any changes to sitemap build, lock, or trigger logic require explicit architectural review.**

## Quick URLs

- API health: `http://192.168.0.130:8081/api/health`
- Regattas list (JSON): `http://192.168.0.130:8081/api/regattas`
- Paste Box (web form → saves to `docs/brief.md`): `http://192.168.0.130:8081/paste`  
  (Requires the API to be started/restarted after code changes.)
- Viewer (served over HTTP 8090): `http://192.168.0.130:8090/regatta_viewer.html`

## Start / Restart API (8081)

**Profile regatta results click (result sheet in modal) only works when the app is served by the API.** Use uvicorn on 8081 below. Do **not** use a static-only server (e.g. `python -m http.server 8081` or Live Server) on 8081 — `/api/regatta/...` would 404 and you’ll see "Failed to load regatta data".

```bash
# Stop any existing uvicorn on 8081 (ignore error if none)
pkill -f "uvicorn api:app --host 0.0.0.0 --port 8081" || true

# Start API (from Project 6/)
export DB_URL="postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master"
cd "/Users/kevinweaving/Desktop/MyProjects_Local/Project 6"
python3 -m uvicorn api:app --host 0.0.0.0 --port 8081
```

Then open **http://192.168.0.130:8081** (or http://localhost:8081). Same origin serves both the app and `/api/`.

Background (optional):
```bash
nohup python3 -m uvicorn api:app --host 0.0.0.0 --port 8081 > uvicorn_8081.log 2>&1 &
```

## Serve Viewer (8090)

```bash
python3 -m http.server 8090 -d "/Users/kevinweaving/Desktop/MyProjects_Local/Project 6"
```

Then open:
```text
http://192.168.0.130:8090/regatta_viewer.html
```

## Paste Your Brief (two options)

- **Web form (Paste Box)** — after API is running on 8081:
  - `http://192.168.0.130:8081/paste`
  - Click Save → content stored in `Project 6/docs/brief.md`

- **Direct file**:
  - Open in TextEdit and paste:
  ```bash
  open -a "TextEdit" "/Users/kevinweaving/Desktop/MyProjects_Local/Project 6/docs/brief.md"
  ```

## Audit / Checksum (Regatta 359 example)

Run checksum audit against all fleets in 359:
```bash
cd "/Users/kevinweaving/Desktop/MyProjects_Local/Project 6"
python3 audit_regatta.py "359-%"
```

## Notes

- The viewer reads scores from `R1..Rn` / `r1..rn` or `race_scores.{R#}`.
- Club display falls back: `club_code` → `club_abbrev` → `club_raw`.
- Ask "run restart" any time; the commands above are copy-paste ready.

## Pending Issues / TODOs

- **Regatta 345/348/350 Issue**: See `admin/tools/TODO_REGTTA_345_348_350_ISSUE.md`
  - Need to verify PDF contents and resolve duplicate/missing Optimist results

---

## Results Data Pass / HTML Header Data (3-Line Rules)

Use these rules every time you pass/import results and when rendering the header in HTML. This is the canonical reference.

1) Event Name (Line 1)
- Source: `regattas.event_name` (or the saved name used for the event/PDF).
- Rule: Accept the official event name as provided for the regatta unless explicitly instructed to adjust it.

2) Host Club (Line 2)
- Source: `regattas.host_club_code` (or join to clubs).
- Rule: Display the club code/abbreviation ONLY (e.g., `PYC`), not the full club name.

3) Results Status Line (Line 3)
- **Sentence (strict):** `Results are [Provisional|Final] as at DD Month YYYY at HH:MM`
- **Date/time format:** DD = two-digit day, Month = full month name, YYYY = year, HH:MM = 24-hour time. Example display: `15 February 2026 at 14:20`.
- **Database:** Store in `regattas.result_status` (e.g. `'Provisional'`, `'Final'`) and `regattas.as_at_time` as timestamp (e.g. `'2026-02-15 14:20:00'`). API may fall back to `results.result_status` / `results.as_at_time` when regattas is null. Never use current date/time or event start/end date as placeholder.
- **Example:** `Results are Provisional as at 15 February 2026 at 14:20`.

Validation Reminder
- Results sheets often contain errors. Always validate and transform against master data before insert/display (classes, fleets, SA IDs, club codes, dates, sail numbers).

---

## ⚠️ DATA ENTRY RULES - MASTER REFERENCE (CRITICAL - NEVER IGNORE)

⚠️ **VIOLATION EXAMPLE**: When adding regattas 361-371, I violated the `event_name` rule by inserting `'361 - 2025 Dart 18 Nationals Results'` (with regatta number and year prefix). This broke the documented rule that `event_name` must NOT include these prefixes. The database has been fixed, but this shows what happens when rules are ignored. See `admin/audit/DATA_ENTRY_VIOLATION_REPORT.md` for details.

**CRITICAL**: **ALL** rules, validations, and checksums listed below MUST be checked before entering ANY new data. Ignoring rules causes data corruption and system failures.

### 📋 PRE-ENTRY CHECKLIST (MANDATORY)

**BEFORE** entering ANY new data (regatta, results, sailor, etc.), you MUST:

1. ✅ **Read `docs/ALL_COLUMN_RULES_REFERENCE.md`** - Master reference for ALL columns in ALL tables
2. ✅ **Read table-specific README** (e.g., `docs/README_regattas_table.md`, `docs/README_results_table.md`)
3. ✅ **Run pre-entry validation**: `admin/tools/validate_new_data_pre_entry.sql`
4. ✅ **Verify foreign keys exist** in referenced tables (clubs, classes, sas_id_personal)
5. ✅ **Check format compliance** - Single year, no quotes, no duplications
6. ✅ **Review existing correct examples** in database before inserting
7. ❌ **NEVER assume format** - Always verify against documentation

### 📊 TABLE-BY-TABLE RULES & VALIDATIONS

#### Table: `public.regattas`
**Full Documentation**: `docs/README_regattas_table.md` | `docs/DATA_FORMAT_SPECIFICATIONS.md` (Section: public.regattas)

**Critical Column Rules**:
- `regatta_id`: Format `{number}-{year}-{club}-{slug}` (SINGLE YEAR only, lowercase, no quotes)
- `event_name`: Clean name only (NO regatta number prefix, NO year prefix)
- `year`: 4-digit integer (2025, not 25)
- `source_url`: Format `https://www.sailing.org.za/file/{hash}`
- `local_file_path`: Relative path to local PDF
- `doc_hash`: Full MD5 hash (32 chars) - unique constraint may prevent duplicates
- `file_type`: Uppercase ('PDF', not 'pdf')

**Pre-Entry Validation**: 
- ✅ Check `event_name` doesn't start with year/regatta number
- ✅ Verify `regatta_id` uses single year format
- ✅ Ensure `host_club_code` exists in `clubs` table

**Post-Entry Checksum**: None (single row per regatta)

---

#### Table: `public.regatta_blocks`
**Full Documentation**: `docs/README_regatta_blocks_table.md` | `docs/DATA_FORMAT_SPECIFICATIONS.md` (Section: public.regatta_blocks)

**Critical Column Rules**:
- `block_id`: Format `{regatta_id}:{fleet-slug}` (COLON separator, single year in regatta_id, no quotes)
- `regatta_id`: Must exist in `regattas` table (FK)
- `fleet_label`: Actual fleet name (NOT "Overall"), must match `classes.class_name` or authorized override
- `class_canonical`: Validated against `classes.class_name` (EXACT match required)
- `races_sailed`: Integer, NOT NULL if block has results
- `discard_count`: Integer, NOT NULL, must be `<= races_sailed`
- `to_count`: Must equal `races_sailed - discard_count`

**Pre-Entry Validation**:
- ✅ Run `admin/tools/validate_class_canonical.sql` - Ensure `class_canonical` exists in `classes.class_name`
- ✅ Run `admin/tools/validate_fleet_label_from_classes.sql` - Verify `fleet_label` matches or authorized override
- ✅ Check `block_id` format (colon separator, single year)

**Post-Entry Checksum**:
- ✅ Run `admin/tools/checksum_entry_counts.sql` - Verify entry counts match PDF
- ✅ Run `admin/tools/checksum_fleet_label.sql` - Verify fleet_label consistency
- ✅ Run `admin/tools/validate_discard_count_checksum.sql` - Verify `discard_count` vs `races_sailed`
- ✅ Run `admin/tools/validate_races_sailed_checksum.sql` - Verify `races_sailed` vs actual races

**Documentation**: `docs/ENTRY_COUNT_CHECKSUM_RULES.md` | `docs/FLEET_LABEL_CHECKSUM_RULES.md`

---

#### Table: `public.results`
**Full Documentation**: `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` | `docs/ALL_COLUMN_RULES_REFERENCE.md` (Section: public.results)

**Critical Column Rules** (Complete list - ALL must be checked):

1. **`result_id`**: Auto-increment, NEVER set manually
2. **`regatta_id`**: Format `{number}-{year}-{club}-{slug}` (SINGLE YEAR only, lowercase, no quotes, FK to `regattas`)
3. **`block_id`**: Format `{regatta_id}:{fleet-slug}` (COLON separator, no quotes, FK to `regatta_blocks`)
4. **`rank`**: Ordinal string (`"1st"`, `"2nd"`, `"3rd"`) - NOT integer
5. **`fleet_label`**: Actual fleet name (NOT "Overall"), must match `classes.class_name` or authorized override, NEVER NULL/empty
6. **`class_original`**: Exact PDF copy (NOT validated, NOT for HTML, may contain errors)
7. **`class_canonical`**: Validated against `classes.class_name` (EXACT match), **ONLY field for HTML**, NEVER NULL/empty
8. **`sail_number`**: Alphanumeric, no country prefixes (remove "RSA ", "SA "), no spaces, no quotes
9. **`bow_no`, `jib_no`, `hull_no`**: Alphanumeric, trimmed, no spaces/quotes
10. **`boat_name`**: Preserve as entered, trimmed, NULL not empty string
11. **`club_raw`**: Preserve as entered, uppercase, no empty string (use NULL)
12. **`club_id`**: FK to `clubs.club_id`, never NULL if `club_raw` exists
13. **`helm_name`, `crew_name`, `crew2_name`, `crew3_name`**: Preserve as entered, trimmed
14. **`helm_sa_sailing_id`, `crew_sa_sailing_id`, etc.**: Must exist in `sas_id_personal` or NULL
15. **`helm_temp_id`, `crew_temp_id`, etc.**: Format `TMP:X` (e.g., `TMP:4`) if no SA ID
16. **`nationality`**: Format `character varying(10)` (e.g., "RSA", "GBR", "USA")
17. **`class_id`**: FK to `classes.class_id` (optional, for reference)
18. **`races_sailed`**: Integer, NOT NULL, must match actual race count in `race_scores`
19. **`discard_count`**: Integer, NOT NULL, must match bracketed scores count in `race_scores`
20. **`ranks_sailed`**: Integer, total entries in fleet/class
21. **`race_scores`**: JSONB format - See `docs/RACE_SCORES_RULES.md` for complete format
   - Keys: "R1", "R2", "R3", etc.
   - Values: `"1.0"` (with .0), `"(2.0)"` (discarded), `"10.0 DNS"` (penalty with score)
   - **CRITICAL**: All penalty codes MUST have scores (`"10.0 DNS"` not `"DNS"`)
   - **CRITICAL**: All scores MUST have `.0` format (`"5.0"` not `"5"`)
   - **CRITICAL**: All discards MUST use parentheses (`"(11.0)"` not `"-11.0"`)
22. **`total_points_raw`**: Numeric with `.0` format, must equal sum of all race scores
23. **`nett_points_raw`**: Numeric with `.0` format, must equal `total_points_raw - discard_sum`

**Pre-Entry Validation** (MANDATORY):
- ✅ Run `admin/tools/validate_new_data_pre_entry.sql` - Comprehensive pre-entry validation
- ✅ Run `admin/tools/validate_race_scores_pre_entry.sql` - Race scores format validation
- ✅ Verify `class_canonical` exists in `classes.class_name` (EXACT match)
- ✅ Verify `fleet_label` matches or authorized override
- ✅ Verify all SA IDs exist in `sas_id_personal` or assign temp IDs
- ✅ Verify `club_id` exists in `clubs` table
- ✅ Check single year format (no `2025-2025`)
- ✅ Check no quotes in text fields
- ✅ Check no regatta number/year prefixes in `event_name`

**Post-Entry Validation** (MANDATORY):
- ✅ Run `admin/tools/checksum_total_nett_points.sql` - Verify total/nett points calculations
- ✅ Run `admin/tools/validate_discard_brackets_compliance.sql` - Verify discard brackets and worst scores discarded
- ✅ Run `admin/tools/checksum_entry_counts.sql` - Verify entry counts per block
- ✅ Run `admin/tools/checksum_fleet_label.sql` - Verify fleet_label consistency
- ✅ Run `admin/tools/validate_class_canonical.sql` - Verify `class_canonical` matches `classes.class_name`
- ✅ Run `admin/tools/validate_club_raw.sql` - Verify club mappings

**Documentation**: 
- `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` - Complete column-by-column rules
- `docs/RACE_SCORES_RULES.md` - Complete race_scores format rules
- `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` - Pre-entry validation checklist
- `docs/ALL_COLUMN_RULES_REFERENCE.md` - Master reference for all columns

---

#### Table: `public.classes`
**Full Documentation**: `docs/README_classes_table.md` | `docs/CLASSES_TABLE_AUTHORITATIVE_SOURCE.md`

**Critical Column Rules**:
- `class_name`: **AUTHORITATIVE SOURCE** - All `results.class_canonical` must match EXACTLY
- `class_id`: Auto-increment primary key
- `crew_policy`: Values: 'single', 'double', 'Crewed', or NULL (must be valid if set)
- `_sailors_in_class`: Integer, must be updated after every results import

**Pre-Entry Validation**:
- ✅ Verify `class_name` is consistent (e.g., `29Er` not `29er`)
- ✅ If adding new class, ensure format matches existing (case-sensitive)

**Post-Entry Validation**:
- ✅ Run `admin/tools/update_sailors_in_class.sql` - **MANDATORY** after every results import
- ✅ Run `admin/tools/validate_sailors_in_class.sql` - Verify counts match calculated values
- ✅ Run `admin/tools/update_crew_policy_from_results_proper.sql` - Update crew_policy from actual results

**Documentation**: `docs/SAILORS_IN_CLASS_RULES.md` | `docs/CREW_POLICY_AUDIT_PROCESS.md`

---

#### Table: `public.clubs`
**Full Documentation**: `docs/README_clubs_table.md`

**Critical Column Rules**:
- `club_id`: Auto-increment primary key
- `club_abbrev`: Uppercase abbreviation (e.g., "ZVYC", "HYC")
- `club_fullname`: Full club name

**Pre-Entry Validation**:
- ✅ Verify club exists before using in `results.club_id`
- ✅ If new club, add to `clubs` table first

**Post-Entry Validation**:
- ✅ Run `admin/tools/validate_club_raw.sql` - Verify all `club_raw` values mapped correctly

---

#### Table: `public.sas_id_personal`
**Full Documentation**: `docs/README_sas_id_personal.md` | `docs/SCRAPING_DATA_RULES.md`

**Critical Column Rules**:
- `id`: Integer, should match `sa_sailing_id::integer` for numeric IDs
- `sa_sailing_id`: Official SA Sailing ID (character varying)
- `first_name`, `last_name`, `full_name`: Name fields (trimmed)
- `year_of_birth`, `age`: Birth year and calculated age
- **Role fields** (`primary_class`, `helm`, `crew`, etc.): **ONLY if actual results data supports** - NOT by default

**Pre-Entry Validation**:
- ✅ Verify `id = sa_sailing_id::integer` for numeric IDs
- ✅ Only add real data from website scraping (no invented fields)

**Post-Entry Validation**:
- ✅ Run `admin/tools/fix_sas_id_personal_id_mismatch.sql` - Verify id matches sa_sailing_id
- ✅ Check for missing year_of_birth/age for named sailors

**Documentation**: `docs/SCRAPING_DATA_RULES.md` | `docs/ROLE_DETERMINATION_RULES.md`

---

### 🔄 COMPLETE DATA ENTRY WORKFLOW

**When importing NEW RESULTS DATA**:

1. **PRE-ENTRY** (BEFORE any INSERT/UPDATE):
   - [ ] Read `docs/ALL_COLUMN_RULES_REFERENCE.md` for relevant table
   - [ ] Read table-specific README (e.g., `docs/README_results_table.md`)
   - [ ] Run `admin/tools/validate_new_data_pre_entry.sql` with sample data
   - [ ] Run `admin/tools/validate_race_scores_pre_entry.sql` if importing race_scores
   - [ ] Verify all foreign keys exist (clubs, classes, sas_id_personal)
   - [ ] Check format compliance (single year, no quotes, no duplications)
   - [ ] Review existing correct examples in database

2. **DATA ENTRY**:
   - [ ] Insert `regattas` row (check `event_name` rule - no number/year prefix)
   - [ ] Insert `regatta_blocks` rows (check `block_id` format, `class_canonical` validation)
   - [ ] Insert `results` rows (check ALL 23 column rules above)
   - [ ] Use UPDATE statements only (NEVER delete and reinsert rows)

3. **POST-ENTRY** (MANDATORY):
   - [ ] Run `admin/tools/checksum_total_nett_points.sql` - Verify calculations
   - [ ] Run `admin/tools/validate_discard_brackets_compliance.sql` - Verify discard rules
   - [ ] Run `admin/tools/checksum_entry_counts.sql` - Verify entry counts
   - [ ] Run `admin/tools/checksum_fleet_label.sql` - Verify fleet_label consistency
   - [ ] Run `admin/tools/validate_class_canonical.sql` - Verify class_canonical matches
   - [ ] Run `admin/tools/update_sailors_in_class.sql` - **MANDATORY** - Update sailor counts
   - [ ] Run `admin/tools/validate_sailors_in_class.sql` - Verify counts correct

4. **VERIFICATION**:
   - [ ] Check HTML displays correctly (no duplicate years/numbers)
   - [ ] Verify filter/search works (class_canonical matches classes.class_name)
   - [ ] Check all foreign keys valid
   - [ ] Verify no NULL values in mandatory fields

---

### 📚 COMPLETE DOCUMENTATION INDEX

**Master References**:
- `docs/ALL_COLUMN_RULES_REFERENCE.md` - **START HERE** - Master reference for ALL columns
- `docs/DATA_FORMAT_SPECIFICATIONS.md` - Complete format specs for all tables
- `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` - Complete results table standards

**Table-Specific Documentation**:
- `docs/README_regattas_table.md` - Regattas table rules
- `docs/README_regatta_blocks_table.md` - Regatta blocks table rules
- `docs/README_results_table.md` - Results table rules (legacy, see RESULTS_TABLE_DATA_ENTRY_STANDARDS.md for current)
- `docs/README_classes_table.md` - Classes table rules
- `docs/README_clubs_table.md` - Clubs table rules
- `docs/README_sas_id_personal.md` - SAS ID personal table rules

**Validation & Checksum Documentation**:
- `docs/ENTRY_COUNT_CHECKSUM_RULES.md` - Entry count validation
- `docs/FLEET_LABEL_CHECKSUM_RULES.md` - Fleet label validation
- `docs/RACE_SCORES_RULES.md` - Race scores format rules
- `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` - Race scores validation checklist

**Special Rules**:
- `docs/CLASS_CANONICAL_VALIDATION_RULES.md` - class_canonical validation (CRITICAL)
- `docs/CLASS_ORIGINAL_DATA_SOURCE.md` - class_original data source
- `docs/CREW_POLICY_AUDIT_PROCESS.md` - Crew policy audit
- `docs/SAILORS_IN_CLASS_RULES.md` - Sailor count rules
- `docs/SCRAPING_DATA_RULES.md` - Data scraping rules
- `docs/ROLE_DETERMINATION_RULES.md` - Role determination rules

**Validation Scripts Location**: `admin/tools/validate_*.sql` and `admin/tools/checksum_*.sql`

### Post-Entry: Update Sailor Counts
**After completing results data entry**, run:
```bash
psql ... -f admin/tools/update_sailors_in_class.sql
```
This updates `classes._sailors_in_class` to reflect unique sailors per class. **MANDATORY** after every regatta import.

See `docs/SAILORS_IN_CLASS_RULES.md` for complete rules.

**MANDATORY READING** before importing any new results data:

### Quick Start Reference
- **`admin/tools/START_HERE_RULES_QUICK_REFERENCE.md`** - **READ FIRST** - Most common violations and quick checklist

### Master Reference (START HERE)
- **`docs/ALL_COLUMN_RULES_REFERENCE.md`** - **CRITICAL** - **COMPLETE RULES FOR ALL COLUMNS IN ALL TABLES**
  - Consolidates ALL column-by-column rules that have been audited and standardized
  - Pre-entry validation process
  - Data entry checklist
  - Validation and checksum scripts
  - **MUST CHECK ALL RULES WHEN NEW RESULTS DATA PASSED**
  - **READ THIS FIRST** - Then refer to detailed documents below for specific tables/columns

### Primary Documents
- **`docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md`** - **CRITICAL** - Complete data entry standards for `public.results` table
  - Column-by-column rules with HTML compatibility requirements
  - Single year format rule (no `2025-2025`)
  - No quotes rule (breaks HTML)
  - No duplications rule (same logical value = identical format)
  - INSERT statement templates
  - Validation queries

- **`docs/DATA_FORMAT_SPECIFICATIONS.md`** - Complete format specs for all tables/columns
- **`docs/DATA_ENTRY_GUIDELINES.md`** - Quick reference checklist
- **`docs/DATA_STANDARDIZATION_PHILOSOPHY.md`** - Core principle: fix data in DB, HTML displays raw

### Key Rules for Results Table
1. **Single Year Only**: `regatta_id` and `block_id` must use single year (`2025`, NOT `2025-2025`)
2. **No Quotes**: No single quotes (`'`) in any text fields (breaks HTML/JavaScript)
3. **Colon Separator**: `block_id` must use colon `:` (NOT hyphen `-`)
4. **Complete Format**: `block_id` must include full `regatta_id` (not just number-fleet)
5. **Mandatory Fields**: `class_canonical` and `fleet_label` must NEVER be NULL/empty
6. **Numeric Format**: All scores, totals, nett must use `.0` format (`15.0`, not `15`)
7. **ISP Codes**: Must include score (`10.0 DNS`, NOT just `DNS`)
8. **Event Name**: Must NOT start with year (HTML displays as `year + event_name`)

**Before every data import**: 
1. Review `docs/ALL_COLUMN_RULES_REFERENCE.md` - **MASTER REFERENCE** for all column rules
2. Run `admin/tools/validate_new_data_pre_entry.sql` - Comprehensive pre-entry validation
3. Review `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` for detailed results table rules
4. Ensure compliance with ALL rules before inserting data

### Entry Count Checksum (MANDATORY)
- **Documentation**: `docs/ENTRY_COUNT_CHECKSUM_RULES.md` - **CRITICAL** - Entry count validation process
- **Validation Script**: `admin/tools/checksum_entry_counts.sql` - Run after each block import
- **Rule**: Actual entry count MUST match PDF count (or explain with DNS/DNC/ties)

### Fleet Label Checksum (MANDATORY)
- **Documentation**: `docs/FLEET_LABEL_CHECKSUM_RULES.md` - **CRITICAL** - Fleet label validation process with manual override
- **Validation Script**: `admin/tools/checksum_fleet_label.sql` - Run after each block import
- **Rule**: `fleet_label` MUST match PDF (or manually override if PDF is wrong - rare cases)
- **Consistency Rule**: All entries in same block must have identical `fleet_label`
- **Never Use**: "Overall" - always use actual fleet name

### class_original vs class_canonical Rules (CRITICAL)
- **Documentation**: 
  - `docs/CLASS_ORIGINAL_DATA_SOURCE.md` - Where class_original comes from (PDF exact copy)
  - `docs/CLASS_CANONICAL_VALIDATION_RULES.md` - **CRITICAL** - Validation and HTML usage rules
  - `docs/CLASS_CANONICAL_MANUAL_OVERRIDE.md` - Manual override process (rare exceptions only)
- **class_original**: PDF/results sheet exact copy - NOT validated, may contain errors - For audit/debugging only
- **class_canonical**: Validated from `classes.class_name` table - **ONLY field HTML should use**
- **Validation Rule**: `class_canonical` MUST exist in `classes.class_name` table with **EXACT match** (case-sensitive, no variations)
- **EXACT Match Required**: Must match `classes.class_name` exactly (e.g., `Ilca 4.7` not `Ilca 4`) - variations break filtering
- **Filtering Impact**: Invalid `class_canonical` (e.g., `Ilca 4` instead of `Ilca 4.7`) breaks HTML filter/search - results won't be found
- **HTML Rule**: HTML must ONLY use `class_canonical` (never `class_original`) - PDF may contain errors, not validated
- **Data Entry Process**: Extract `class_original` from PDF → Validate against `classes.class_name` (EXACT match) → Correct if wrong → Store in `class_canonical`
- **Manual Override**: Only if explicitly authorized - see `docs/CLASS_CANONICAL_MANUAL_OVERRIDE.md`
- **Validation Script**: `admin/tools/validate_class_canonical.sql` - Run after each data import to check for invalid values
- **Authoritative Source**: `classes.class_name` is the ONLY source of truth - all `results.class_canonical` must match exactly
- **Fix Script**: `admin/tools/fix_class_canonical_match_classes_table.sql` - Fixes inconsistencies (e.g., `29er` → `29Er`)
- **See**: `docs/CLASSES_TABLE_AUTHORITATIVE_SOURCE.md` - Complete explanation of authoritative source rule

### Crew Policy Audit (Periodic)
- **Documentation**: `docs/CREW_POLICY_AUDIT_PROCESS.md` - How to update crew_policy from results
- **Update Script**: `admin/tools/update_crew_policy_from_results_proper.sql` - **PROPER AUDIT** using actual crew fields
- **Frequency**: Run periodically as new results are imported
- **3-Tier System**:
  1. **Single**: Only Helm (no `crew_name`) = 1 sailor
  2. **Double**: Helm + 1 Crew (`crew_name` exists, no `crew2_name`/`crew3_name`) = 2 sailors
  3. **Crewed**: Helm + 2+ Crew (`crew_name` + `crew2_name` or `crew3_name`) = 3+ sailors
- **Logic**: If ANY results have `crew2_name`/`crew3_name` → Crewed, else if ANY have `crew_name` → Double, else → Single
- **Current Status**: 27 classes updated (14 single, 12 double, 1+ crewed), 52 remain NULL (no results yet)


Run checksum audit against all fleets in 359:
```bash
cd "/Users/kevinweaving/Desktop/MyProjects_Local/Project 6"
python3 audit_regatta.py "359-%"
```

## Notes

- The viewer reads scores from `R1..Rn` / `r1..rn` or `race_scores.{R#}`.
- Club display falls back: `club_code` → `club_abbrev` → `club_raw`.
- Ask "run restart" any time; the commands above are copy-paste ready.

## Pending Issues / TODOs

- **Regatta 345/348/350 Issue**: See `admin/tools/TODO_REGTTA_345_348_350_ISSUE.md`
  - Need to verify PDF contents and resolve duplicate/missing Optimist results

---

## Results Data Pass / HTML Header Data (3-Line Rules)

Use these rules every time you pass/import results and when rendering the header in HTML. This is the canonical reference.

1) Event Name (Line 1)
- Source: `regattas.event_name` (or the saved name used for the event/PDF).
- Rule: Accept the official event name as provided for the regatta unless explicitly instructed to adjust it.

2) Host Club (Line 2)
- Source: `regattas.host_club_code` (or join to clubs).
- Rule: Display the club code/abbreviation ONLY (e.g., `PYC`), not the full club name.

3) Results Status Line (Line 3)
- **Sentence (strict):** `Results are [Provisional|Final] as at DD Month YYYY at HH:MM`
- **Date/time format:** DD = two-digit day, Month = full month name, YYYY = year, HH:MM = 24-hour time. Example display: `15 February 2026 at 14:20`.
- **Database:** Store in `regattas.result_status` (e.g. `'Provisional'`, `'Final'`) and `regattas.as_at_time` as timestamp (e.g. `'2026-02-15 14:20:00'`). API may fall back to `results.result_status` / `results.as_at_time` when regattas is null. Never use current date/time or event start/end date as placeholder.
- **Example:** `Results are Provisional as at 15 February 2026 at 14:20`.

Validation Reminder
- Results sheets often contain errors. Always validate and transform against master data before insert/display (classes, fleets, SA IDs, club codes, dates, sail numbers).

---

## ⚠️ DATA ENTRY RULES - MASTER REFERENCE (CRITICAL - NEVER IGNORE)

⚠️ **VIOLATION EXAMPLE**: When adding regattas 361-371, I violated the `event_name` rule by inserting `'361 - 2025 Dart 18 Nationals Results'` (with regatta number and year prefix). This broke the documented rule that `event_name` must NOT include these prefixes. The database has been fixed, but this shows what happens when rules are ignored. See `admin/audit/DATA_ENTRY_VIOLATION_REPORT.md` for details.

**CRITICAL**: **ALL** rules, validations, and checksums listed below MUST be checked before entering ANY new data. Ignoring rules causes data corruption and system failures.

### 📋 PRE-ENTRY CHECKLIST (MANDATORY)

**BEFORE** entering ANY new data (regatta, results, sailor, etc.), you MUST:

1. ✅ **Read `docs/ALL_COLUMN_RULES_REFERENCE.md`** - Master reference for ALL columns in ALL tables
2. ✅ **Read table-specific README** (e.g., `docs/README_regattas_table.md`, `docs/README_results_table.md`)
3. ✅ **Run pre-entry validation**: `admin/tools/validate_new_data_pre_entry.sql`
4. ✅ **Verify foreign keys exist** in referenced tables (clubs, classes, sas_id_personal)
5. ✅ **Check format compliance** - Single year, no quotes, no duplications
6. ✅ **Review existing correct examples** in database before inserting
7. ❌ **NEVER assume format** - Always verify against documentation

### 📊 TABLE-BY-TABLE RULES & VALIDATIONS

#### Table: `public.regattas`
**Full Documentation**: `docs/README_regattas_table.md` | `docs/DATA_FORMAT_SPECIFICATIONS.md` (Section: public.regattas)

**Critical Column Rules**:
- `regatta_id`: Format `{number}-{year}-{club}-{slug}` (SINGLE YEAR only, lowercase, no quotes)
- `event_name`: Clean name only (NO regatta number prefix, NO year prefix)
- `year`: 4-digit integer (2025, not 25)
- `source_url`: Format `https://www.sailing.org.za/file/{hash}`
- `local_file_path`: Relative path to local PDF
- `doc_hash`: Full MD5 hash (32 chars) - unique constraint may prevent duplicates
- `file_type`: Uppercase ('PDF', not 'pdf')

**Pre-Entry Validation**: 
- ✅ Check `event_name` doesn't start with year/regatta number
- ✅ Verify `regatta_id` uses single year format
- ✅ Ensure `host_club_code` exists in `clubs` table

**Post-Entry Checksum**: None (single row per regatta)

---

#### Table: `public.regatta_blocks`
**Full Documentation**: `docs/README_regatta_blocks_table.md` | `docs/DATA_FORMAT_SPECIFICATIONS.md` (Section: public.regatta_blocks)

**Critical Column Rules**:
- `block_id`: Format `{regatta_id}:{fleet-slug}` (COLON separator, single year in regatta_id, no quotes)
- `regatta_id`: Must exist in `regattas` table (FK)
- `fleet_label`: Actual fleet name (NOT "Overall"), must match `classes.class_name` or authorized override
- `class_canonical`: Validated against `classes.class_name` (EXACT match required)
- `races_sailed`: Integer, NOT NULL if block has results
- `discard_count`: Integer, NOT NULL, must be `<= races_sailed`
- `to_count`: Must equal `races_sailed - discard_count`

**Pre-Entry Validation**:
- ✅ Run `admin/tools/validate_class_canonical.sql` - Ensure `class_canonical` exists in `classes.class_name`
- ✅ Run `admin/tools/validate_fleet_label_from_classes.sql` - Verify `fleet_label` matches or authorized override
- ✅ Check `block_id` format (colon separator, single year)

**Post-Entry Checksum**:
- ✅ Run `admin/tools/checksum_entry_counts.sql` - Verify entry counts match PDF
- ✅ Run `admin/tools/checksum_fleet_label.sql` - Verify fleet_label consistency
- ✅ Run `admin/tools/validate_discard_count_checksum.sql` - Verify `discard_count` vs `races_sailed`
- ✅ Run `admin/tools/validate_races_sailed_checksum.sql` - Verify `races_sailed` vs actual races

**Documentation**: `docs/ENTRY_COUNT_CHECKSUM_RULES.md` | `docs/FLEET_LABEL_CHECKSUM_RULES.md`

---

#### Table: `public.results`
**Full Documentation**: `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` | `docs/ALL_COLUMN_RULES_REFERENCE.md` (Section: public.results)

**Critical Column Rules** (Complete list - ALL must be checked):

1. **`result_id`**: Auto-increment, NEVER set manually
2. **`regatta_id`**: Format `{number}-{year}-{club}-{slug}` (SINGLE YEAR only, lowercase, no quotes, FK to `regattas`)
3. **`block_id`**: Format `{regatta_id}:{fleet-slug}` (COLON separator, no quotes, FK to `regatta_blocks`)
4. **`rank`**: Ordinal string (`"1st"`, `"2nd"`, `"3rd"`) - NOT integer
5. **`fleet_label`**: Actual fleet name (NOT "Overall"), must match `classes.class_name` or authorized override, NEVER NULL/empty
6. **`class_original`**: Exact PDF copy (NOT validated, NOT for HTML, may contain errors)
7. **`class_canonical`**: Validated against `classes.class_name` (EXACT match), **ONLY field for HTML**, NEVER NULL/empty
8. **`sail_number`**: Alphanumeric, no country prefixes (remove "RSA ", "SA "), no spaces, no quotes
9. **`bow_no`, `jib_no`, `hull_no`**: Alphanumeric, trimmed, no spaces/quotes
10. **`boat_name`**: Preserve as entered, trimmed, NULL not empty string
11. **`club_raw`**: Preserve as entered, uppercase, no empty string (use NULL)
12. **`club_id`**: FK to `clubs.club_id`, never NULL if `club_raw` exists
13. **`helm_name`, `crew_name`, `crew2_name`, `crew3_name`**: Preserve as entered, trimmed
14. **`helm_sa_sailing_id`, `crew_sa_sailing_id`, etc.**: Must exist in `sas_id_personal` or NULL
15. **`helm_temp_id`, `crew_temp_id`, etc.**: Format `TMP:X` (e.g., `TMP:4`) if no SA ID
16. **`nationality`**: Format `character varying(10)` (e.g., "RSA", "GBR", "USA")
17. **`class_id`**: FK to `classes.class_id` (optional, for reference)
18. **`races_sailed`**: Integer, NOT NULL, must match actual race count in `race_scores`
19. **`discard_count`**: Integer, NOT NULL, must match bracketed scores count in `race_scores`
20. **`ranks_sailed`**: Integer, total entries in fleet/class
21. **`race_scores`**: JSONB format - See `docs/RACE_SCORES_RULES.md` for complete format
   - Keys: "R1", "R2", "R3", etc.
   - Values: `"1.0"` (with .0), `"(2.0)"` (discarded), `"10.0 DNS"` (penalty with score)
   - **CRITICAL**: All penalty codes MUST have scores (`"10.0 DNS"` not `"DNS"`)
   - **CRITICAL**: All scores MUST have `.0` format (`"5.0"` not `"5"`)
   - **CRITICAL**: All discards MUST use parentheses (`"(11.0)"` not `"-11.0"`)
22. **`total_points_raw`**: Numeric with `.0` format, must equal sum of all race scores
23. **`nett_points_raw`**: Numeric with `.0` format, must equal `total_points_raw - discard_sum`

**Pre-Entry Validation** (MANDATORY):
- ✅ Run `admin/tools/validate_new_data_pre_entry.sql` - Comprehensive pre-entry validation
- ✅ Run `admin/tools/validate_race_scores_pre_entry.sql` - Race scores format validation
- ✅ Verify `class_canonical` exists in `classes.class_name` (EXACT match)
- ✅ Verify `fleet_label` matches or authorized override
- ✅ Verify all SA IDs exist in `sas_id_personal` or assign temp IDs
- ✅ Verify `club_id` exists in `clubs` table
- ✅ Check single year format (no `2025-2025`)
- ✅ Check no quotes in text fields
- ✅ Check no regatta number/year prefixes in `event_name`

**Post-Entry Validation** (MANDATORY):
- ✅ Run `admin/tools/checksum_total_nett_points.sql` - Verify total/nett points calculations
- ✅ Run `admin/tools/validate_discard_brackets_compliance.sql` - Verify discard brackets and worst scores discarded
- ✅ Run `admin/tools/checksum_entry_counts.sql` - Verify entry counts per block
- ✅ Run `admin/tools/checksum_fleet_label.sql` - Verify fleet_label consistency
- ✅ Run `admin/tools/validate_class_canonical.sql` - Verify `class_canonical` matches `classes.class_name`
- ✅ Run `admin/tools/validate_club_raw.sql` - Verify club mappings

**Documentation**: 
- `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` - Complete column-by-column rules
- `docs/RACE_SCORES_RULES.md` - Complete race_scores format rules
- `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` - Pre-entry validation checklist
- `docs/ALL_COLUMN_RULES_REFERENCE.md` - Master reference for all columns

---

#### Table: `public.classes`
**Full Documentation**: `docs/README_classes_table.md` | `docs/CLASSES_TABLE_AUTHORITATIVE_SOURCE.md`

**Critical Column Rules**:
- `class_name`: **AUTHORITATIVE SOURCE** - All `results.class_canonical` must match EXACTLY
- `class_id`: Auto-increment primary key
- `crew_policy`: Values: 'single', 'double', 'Crewed', or NULL (must be valid if set)
- `_sailors_in_class`: Integer, must be updated after every results import

**Pre-Entry Validation**:
- ✅ Verify `class_name` is consistent (e.g., `29Er` not `29er`)
- ✅ If adding new class, ensure format matches existing (case-sensitive)

**Post-Entry Validation**:
- ✅ Run `admin/tools/update_sailors_in_class.sql` - **MANDATORY** after every results import
- ✅ Run `admin/tools/validate_sailors_in_class.sql` - Verify counts match calculated values
- ✅ Run `admin/tools/update_crew_policy_from_results_proper.sql` - Update crew_policy from actual results

**Documentation**: `docs/SAILORS_IN_CLASS_RULES.md` | `docs/CREW_POLICY_AUDIT_PROCESS.md`

---

#### Table: `public.clubs`
**Full Documentation**: `docs/README_clubs_table.md`

**Critical Column Rules**:
- `club_id`: Auto-increment primary key
- `club_abbrev`: Uppercase abbreviation (e.g., "ZVYC", "HYC")
- `club_fullname`: Full club name

**Pre-Entry Validation**:
- ✅ Verify club exists before using in `results.club_id`
- ✅ If new club, add to `clubs` table first

**Post-Entry Validation**:
- ✅ Run `admin/tools/validate_club_raw.sql` - Verify all `club_raw` values mapped correctly

---

#### Table: `public.sas_id_personal`
**Full Documentation**: `docs/README_sas_id_personal.md` | `docs/SCRAPING_DATA_RULES.md`

**Critical Column Rules**:
- `id`: Integer, should match `sa_sailing_id::integer` for numeric IDs
- `sa_sailing_id`: Official SA Sailing ID (character varying)
- `first_name`, `last_name`, `full_name`: Name fields (trimmed)
- `year_of_birth`, `age`: Birth year and calculated age
- **Role fields** (`primary_class`, `helm`, `crew`, etc.): **ONLY if actual results data supports** - NOT by default

**Pre-Entry Validation**:
- ✅ Verify `id = sa_sailing_id::integer` for numeric IDs
- ✅ Only add real data from website scraping (no invented fields)

**Post-Entry Validation**:
- ✅ Run `admin/tools/fix_sas_id_personal_id_mismatch.sql` - Verify id matches sa_sailing_id
- ✅ Check for missing year_of_birth/age for named sailors

**Documentation**: `docs/SCRAPING_DATA_RULES.md` | `docs/ROLE_DETERMINATION_RULES.md`

---

### 🔄 COMPLETE DATA ENTRY WORKFLOW

**When importing NEW RESULTS DATA**:

1. **PRE-ENTRY** (BEFORE any INSERT/UPDATE):
   - [ ] Read `docs/ALL_COLUMN_RULES_REFERENCE.md` for relevant table
   - [ ] Read table-specific README (e.g., `docs/README_results_table.md`)
   - [ ] Run `admin/tools/validate_new_data_pre_entry.sql` with sample data
   - [ ] Run `admin/tools/validate_race_scores_pre_entry.sql` if importing race_scores
   - [ ] Verify all foreign keys exist (clubs, classes, sas_id_personal)
   - [ ] Check format compliance (single year, no quotes, no duplications)
   - [ ] Review existing correct examples in database

2. **DATA ENTRY**:
   - [ ] Insert `regattas` row (check `event_name` rule - no number/year prefix)
   - [ ] Insert `regatta_blocks` rows (check `block_id` format, `class_canonical` validation)
   - [ ] Insert `results` rows (check ALL 23 column rules above)
   - [ ] Use UPDATE statements only (NEVER delete and reinsert rows)

3. **POST-ENTRY** (MANDATORY):
   - [ ] Run `admin/tools/checksum_total_nett_points.sql` - Verify calculations
   - [ ] Run `admin/tools/validate_discard_brackets_compliance.sql` - Verify discard rules
   - [ ] Run `admin/tools/checksum_entry_counts.sql` - Verify entry counts
   - [ ] Run `admin/tools/checksum_fleet_label.sql` - Verify fleet_label consistency
   - [ ] Run `admin/tools/validate_class_canonical.sql` - Verify class_canonical matches
   - [ ] Run `admin/tools/update_sailors_in_class.sql` - **MANDATORY** - Update sailor counts
   - [ ] Run `admin/tools/validate_sailors_in_class.sql` - Verify counts correct

4. **VERIFICATION**:
   - [ ] Check HTML displays correctly (no duplicate years/numbers)
   - [ ] Verify filter/search works (class_canonical matches classes.class_name)
   - [ ] Check all foreign keys valid
   - [ ] Verify no NULL values in mandatory fields

---

### 📚 COMPLETE DOCUMENTATION INDEX

**Master References**:
- `docs/ALL_COLUMN_RULES_REFERENCE.md` - **START HERE** - Master reference for ALL columns
- `docs/DATA_FORMAT_SPECIFICATIONS.md` - Complete format specs for all tables
- `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` - Complete results table standards

**Table-Specific Documentation**:
- `docs/README_regattas_table.md` - Regattas table rules
- `docs/README_regatta_blocks_table.md` - Regatta blocks table rules
- `docs/README_results_table.md` - Results table rules (legacy, see RESULTS_TABLE_DATA_ENTRY_STANDARDS.md for current)
- `docs/README_classes_table.md` - Classes table rules
- `docs/README_clubs_table.md` - Clubs table rules
- `docs/README_sas_id_personal.md` - SAS ID personal table rules

**Validation & Checksum Documentation**:
- `docs/ENTRY_COUNT_CHECKSUM_RULES.md` - Entry count validation
- `docs/FLEET_LABEL_CHECKSUM_RULES.md` - Fleet label validation
- `docs/RACE_SCORES_RULES.md` - Race scores format rules
- `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` - Race scores validation checklist

**Special Rules**:
- `docs/CLASS_CANONICAL_VALIDATION_RULES.md` - class_canonical validation (CRITICAL)
- `docs/CLASS_ORIGINAL_DATA_SOURCE.md` - class_original data source
- `docs/CREW_POLICY_AUDIT_PROCESS.md` - Crew policy audit
- `docs/SAILORS_IN_CLASS_RULES.md` - Sailor count rules
- `docs/SCRAPING_DATA_RULES.md` - Data scraping rules
- `docs/ROLE_DETERMINATION_RULES.md` - Role determination rules

**Validation Scripts Location**: `admin/tools/validate_*.sql` and `admin/tools/checksum_*.sql`

### Post-Entry: Update Sailor Counts
**After completing results data entry**, run:
```bash
psql ... -f admin/tools/update_sailors_in_class.sql
```
This updates `classes._sailors_in_class` to reflect unique sailors per class. **MANDATORY** after every regatta import.

See `docs/SAILORS_IN_CLASS_RULES.md` for complete rules.

**MANDATORY READING** before importing any new results data:

### Quick Start Reference
- **`admin/tools/START_HERE_RULES_QUICK_REFERENCE.md`** - **READ FIRST** - Most common violations and quick checklist

### Master Reference (START HERE)
- **`docs/ALL_COLUMN_RULES_REFERENCE.md`** - **CRITICAL** - **COMPLETE RULES FOR ALL COLUMNS IN ALL TABLES**
  - Consolidates ALL column-by-column rules that have been audited and standardized
  - Pre-entry validation process
  - Data entry checklist
  - Validation and checksum scripts
  - **MUST CHECK ALL RULES WHEN NEW RESULTS DATA PASSED**
  - **READ THIS FIRST** - Then refer to detailed documents below for specific tables/columns

### Primary Documents
- **`docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md`** - **CRITICAL** - Complete data entry standards for `public.results` table
  - Column-by-column rules with HTML compatibility requirements
  - Single year format rule (no `2025-2025`)
  - No quotes rule (breaks HTML)
  - No duplications rule (same logical value = identical format)
  - INSERT statement templates
  - Validation queries

- **`docs/DATA_FORMAT_SPECIFICATIONS.md`** - Complete format specs for all tables/columns
- **`docs/DATA_ENTRY_GUIDELINES.md`** - Quick reference checklist
- **`docs/DATA_STANDARDIZATION_PHILOSOPHY.md`** - Core principle: fix data in DB, HTML displays raw

### Key Rules for Results Table
1. **Single Year Only**: `regatta_id` and `block_id` must use single year (`2025`, NOT `2025-2025`)
2. **No Quotes**: No single quotes (`'`) in any text fields (breaks HTML/JavaScript)
3. **Colon Separator**: `block_id` must use colon `:` (NOT hyphen `-`)
4. **Complete Format**: `block_id` must include full `regatta_id` (not just number-fleet)
5. **Mandatory Fields**: `class_canonical` and `fleet_label` must NEVER be NULL/empty
6. **Numeric Format**: All scores, totals, nett must use `.0` format (`15.0`, not `15`)
7. **ISP Codes**: Must include score (`10.0 DNS`, NOT just `DNS`)
8. **Event Name**: Must NOT start with year (HTML displays as `year + event_name`)

**Before every data import**: 
1. Review `docs/ALL_COLUMN_RULES_REFERENCE.md` - **MASTER REFERENCE** for all column rules
2. Run `admin/tools/validate_new_data_pre_entry.sql` - Comprehensive pre-entry validation
3. Review `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` for detailed results table rules
4. Ensure compliance with ALL rules before inserting data

### Entry Count Checksum (MANDATORY)
- **Documentation**: `docs/ENTRY_COUNT_CHECKSUM_RULES.md` - **CRITICAL** - Entry count validation process
- **Validation Script**: `admin/tools/checksum_entry_counts.sql` - Run after each block import
- **Rule**: Actual entry count MUST match PDF count (or explain with DNS/DNC/ties)

### Fleet Label Checksum (MANDATORY)
- **Documentation**: `docs/FLEET_LABEL_CHECKSUM_RULES.md` - **CRITICAL** - Fleet label validation process with manual override
- **Validation Script**: `admin/tools/checksum_fleet_label.sql` - Run after each block import
- **Rule**: `fleet_label` MUST match PDF (or manually override if PDF is wrong - rare cases)
- **Consistency Rule**: All entries in same block must have identical `fleet_label`
- **Never Use**: "Overall" - always use actual fleet name

### class_original vs class_canonical Rules (CRITICAL)
- **Documentation**: 
  - `docs/CLASS_ORIGINAL_DATA_SOURCE.md` - Where class_original comes from (PDF exact copy)
  - `docs/CLASS_CANONICAL_VALIDATION_RULES.md` - **CRITICAL** - Validation and HTML usage rules
  - `docs/CLASS_CANONICAL_MANUAL_OVERRIDE.md` - Manual override process (rare exceptions only)
- **class_original**: PDF/results sheet exact copy - NOT validated, may contain errors - For audit/debugging only
- **class_canonical**: Validated from `classes.class_name` table - **ONLY field HTML should use**
- **Validation Rule**: `class_canonical` MUST exist in `classes.class_name` table with **EXACT match** (case-sensitive, no variations)
- **EXACT Match Required**: Must match `classes.class_name` exactly (e.g., `Ilca 4.7` not `Ilca 4`) - variations break filtering
- **Filtering Impact**: Invalid `class_canonical` (e.g., `Ilca 4` instead of `Ilca 4.7`) breaks HTML filter/search - results won't be found
- **HTML Rule**: HTML must ONLY use `class_canonical` (never `class_original`) - PDF may contain errors, not validated
- **Data Entry Process**: Extract `class_original` from PDF → Validate against `classes.class_name` (EXACT match) → Correct if wrong → Store in `class_canonical`
- **Manual Override**: Only if explicitly authorized - see `docs/CLASS_CANONICAL_MANUAL_OVERRIDE.md`
- **Validation Script**: `admin/tools/validate_class_canonical.sql` - Run after each data import to check for invalid values
- **Authoritative Source**: `classes.class_name` is the ONLY source of truth - all `results.class_canonical` must match exactly
- **Fix Script**: `admin/tools/fix_class_canonical_match_classes_table.sql` - Fixes inconsistencies (e.g., `29er` → `29Er`)
- **See**: `docs/CLASSES_TABLE_AUTHORITATIVE_SOURCE.md` - Complete explanation of authoritative source rule

### Crew Policy Audit (Periodic)
- **Documentation**: `docs/CREW_POLICY_AUDIT_PROCESS.md` - How to update crew_policy from results
- **Update Script**: `admin/tools/update_crew_policy_from_results_proper.sql` - **PROPER AUDIT** using actual crew fields
- **Frequency**: Run periodically as new results are imported
- **3-Tier System**:
  1. **Single**: Only Helm (no `crew_name`) = 1 sailor
  2. **Double**: Helm + 1 Crew (`crew_name` exists, no `crew2_name`/`crew3_name`) = 2 sailors
  3. **Crewed**: Helm + 2+ Crew (`crew_name` + `crew2_name` or `crew3_name`) = 3+ sailors
- **Logic**: If ANY results have `crew2_name`/`crew3_name` → Crewed, else if ANY have `crew_name` → Double, else → Single
- **Current Status**: 27 classes updated (14 single, 12 double, 1+ crewed), 52 remain NULL (no results yet)
