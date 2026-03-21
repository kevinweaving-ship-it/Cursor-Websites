# REGATTAS Table - GPT Rules & Data Structure

## Purpose
Stores regatta event information with proper date/time formatting and status tracking.

## Table Structure
```sql
CREATE TABLE regattas (
    regatta_id TEXT PRIMARY KEY,           -- Slug format: '359-2025-zvyc-southern-charter-cape-classic'
    regatta_number INTEGER UNIQUE,         -- Sequential number (359, 360, etc.)
    event_name TEXT NOT NULL,              -- Full event name
    year INTEGER,                          -- Event year
    start_date DATE,                       -- Actual start date from results sheet
    end_date DATE,                         -- Actual end date from results sheet
    as_at_time TIMESTAMP WITH TIME ZONE,   -- Results time from sheet (e.g., '2025-09-14 17:15:00+02')
    result_status TEXT,                    -- 'Final', 'Provisional', 'Time'
    host_club_id INTEGER REFERENCES clubs(club_id),
    province_name TEXT,                    -- Province abbreviation (KZN, WC, GP, etc.)
    import_status TEXT DEFAULT 'imported', -- 'imported', 'manual', 'pending'
    file_type TEXT,                        -- 'pdf', 'html', 'screenshot'
    doc_hash TEXT,                         -- File checksum
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Data Rules (from GPT instructions)

### Date/Time Formatting (CRITICAL)
- **start_date/end_date**: Extract actual dates from results sheet
- **as_at_time**: Extract exact time from "Results are Final as of 15 Jan. 25 14:30" format
- **NEVER use placeholder dates** - extract from original sheet
- **Preserve timezone information** when available

### Result Status Codes (CRITICAL - Database Format)
- **Store as FULL WORDS**: 'Provisional', 'Final', 'Time' (NOT 'P', 'F', 'T')
- HTML displays directly from database - no conversion needed
- **Format in HTML**: "Results are Provisional as at 04 October 2025 at 13:50"
  - Day: DD (leading zero: 04, not 4)
  - Month: Full name (October, not Oct)
  - Year: YYYY (2025, not 25)
  - Time: HH:MM (13:50, not 1:50 PM)
  - Use "as at" not "as of"

### Regatta ID Format (CRITICAL)
- Pattern: `{regatta_number}-{year}-{host_club}-{event_slug}`
- Example: `359-2025-zvyc-southern-charter-cape-classic`
- **SINGLE YEAR ONLY**: Use `2025`, NOT `2025-2025` (prevents duplication)
- **Lowercase**: All text lowercase
- **No quotes**: No single quotes in any part
- **NEVER change existing regatta_id** values once created

### Data Integrity Rules
1. **NEVER use placeholders** - only real data or NULL
2. **NEVER hardcode values** - always extract from source
3. **ALWAYS extract actual dates** from results sheet
4. **ALWAYS preserve original timing** information
5. **ALWAYS lookup host club** in clubs table

## ⚠️ CRITICAL RULES - NEVER IGNORE

**BEFORE entering ANY regatta data**, you MUST:

1. ✅ **Read `docs/ALL_COLUMN_RULES_REFERENCE.md`** - Master reference for ALL columns
2. ✅ **Read `docs/DATA_FORMAT_SPECIFICATIONS.md`** - Section: public.regattas
3. ✅ **Check existing correct examples** in database (regattas 356-360)
4. ✅ **Run pre-entry validation** - Check `event_name` doesn't have regatta number/year prefix
5. ✅ **Verify format compliance** - Single year only, no quotes, lowercase

**Column Rules**:
- **`event_name`**: ⚠️ **CRITICAL** - Must NOT include regatta number prefix (e.g., NOT `'361 - ...'`) or year prefix (e.g., NOT `'2025 ...'`)
  - Correct: `'Dart 18 Nationals Results'`
  - Wrong: `'361 - 2025 Dart 18 Nationals Results'`
  - Reason: `regatta_number` column has the number, `year` column has the year - no duplication
- **`regatta_id`**: Format `{number}-{year}-{club}-{slug}` (SINGLE YEAR only, lowercase, no quotes)
- **`source_url`**: Format `https://www.sailing.org.za/file/{hash}` (16-char hash from filename)
- **`doc_hash`**: Full MD5 hash (32 chars) - unique constraint may prevent duplicates for shared PDFs
- **`file_type`**: Uppercase ('PDF', not 'pdf')

**Pre-Entry Validation Checklist** (MANDATORY):
- [ ] `event_name` doesn't start with year or regatta number (e.g., NOT `'361 - ...'` or `'2025 ...'`)
- [ ] `regatta_id` uses single year format (not `2025-2025`)
- [ ] `result_status` is full word ('Final', 'Provisional', NOT 'F', 'P')
- [ ] `host_club_code` exists in `clubs` table
- [ ] `source_url` format: `https://www.sailing.org.za/file/{hash}`
- [ ] `as_at_time` format: `TIMESTAMP WITH TIME ZONE` (e.g., `'2025-10-04 13:50:00+02'`)
- [ ] `doc_hash` populated if PDF available (32-char MD5 hash)
- [ ] Format matches existing regattas (check 345-371 for correct examples)

**Post-Entry Validation**:
- [ ] Verify HTML displays correctly (no duplicate years/numbers in dropdown)
- [ ] Check status line format: "Results are [Status] as at DD Month YYYY at HH:MM"

**Violation Example**: See `admin/audit/DATA_ENTRY_VIOLATION_REPORT.md` - Regattas 361-371 violated `event_name` rule

## Example Data
```sql
INSERT INTO regattas (regatta_id, regatta_number, event_name, year, start_date, end_date, as_at_time, result_status, host_club_id, province_name) VALUES
('359-2025-zvyc-southern-charter-cape-classic', 359, 'ZVYC Southern Charter Cape Classic', 2025, '2025-09-13', '2025-09-14', '2025-09-14 17:15:00+02', 'Final', 1, 'WC');
```

## How to add / update the Results line for a regatta

The **Results line** (e.g. "Results are Provisional as at 19 December 2025 at 14:50") is driven by the **regattas** table only. It is **not** stored in the results table.

1. **Table**: `public.regattas`
2. **Columns**:
   - `result_status` – full word: `'Provisional'` or `'Final'` (not 'P' or 'F')
   - `as_at_time` – when the results were posted: `TIMESTAMP WITH TIME ZONE`, e.g. `'2025-12-19 14:50:00+02:00'`
3. **Example** – add/update results line for regatta 377:
   ```sql
   UPDATE public.regattas
   SET 
       result_status = 'Provisional',
       as_at_time = '2025-12-19 14:50:00+02:00'
   WHERE regatta_number = 377;
   ```
4. **Display**: regatta_viewer.html (and API) read `result_status` and `as_at_time` from the first row of `/api/regatta/{id}` and format as "Results are [Status] as at DD Month YYYY at HH:MM".
5. **If the line doesn’t show**: Ensure the migration has been run (e.g. `database/migrations/121_update_regatta_377_date_info.sql`) so `as_at_time` is set for that regatta.

## Related Tables
- `regatta_blocks` - Fleet/class information per regatta
- `results` - Individual race results
- `clubs` - Host club information

1. ✅ **Read `docs/ALL_COLUMN_RULES_REFERENCE.md`** - Master reference for ALL columns
2. ✅ **Read `docs/DATA_FORMAT_SPECIFICATIONS.md`** - Section: public.regattas
3. ✅ **Check existing correct examples** in database (regattas 356-360)
4. ✅ **Run pre-entry validation** - Check `event_name` doesn't have regatta number/year prefix
5. ✅ **Verify format compliance** - Single year only, no quotes, lowercase

**Column Rules**:
- **`event_name`**: ⚠️ **CRITICAL** - Must NOT include regatta number prefix (e.g., NOT `'361 - ...'`) or year prefix (e.g., NOT `'2025 ...'`)
  - Correct: `'Dart 18 Nationals Results'`
  - Wrong: `'361 - 2025 Dart 18 Nationals Results'`
  - Reason: `regatta_number` column has the number, `year` column has the year - no duplication
- **`regatta_id`**: Format `{number}-{year}-{club}-{slug}` (SINGLE YEAR only, lowercase, no quotes)
- **`source_url`**: Format `https://www.sailing.org.za/file/{hash}` (16-char hash from filename)
- **`doc_hash`**: Full MD5 hash (32 chars) - unique constraint may prevent duplicates for shared PDFs
- **`file_type`**: Uppercase ('PDF', not 'pdf')

**Pre-Entry Validation Checklist** (MANDATORY):
- [ ] `event_name` doesn't start with year or regatta number (e.g., NOT `'361 - ...'` or `'2025 ...'`)
- [ ] `regatta_id` uses single year format (not `2025-2025`)
- [ ] `result_status` is full word ('Final', 'Provisional', NOT 'F', 'P')
- [ ] `host_club_code` exists in `clubs` table
- [ ] `source_url` format: `https://www.sailing.org.za/file/{hash}`
- [ ] `as_at_time` format: `TIMESTAMP WITH TIME ZONE` (e.g., `'2025-10-04 13:50:00+02'`)
- [ ] `doc_hash` populated if PDF available (32-char MD5 hash)
- [ ] Format matches existing regattas (check 345-371 for correct examples)

**Post-Entry Validation**:
- [ ] Verify HTML displays correctly (no duplicate years/numbers in dropdown)
- [ ] Check status line format: "Results are [Status] as at DD Month YYYY at HH:MM"

**Violation Example**: See `admin/audit/DATA_ENTRY_VIOLATION_REPORT.md` - Regattas 361-371 violated `event_name` rule

## Example Data
```sql
INSERT INTO regattas (regatta_id, regatta_number, event_name, year, start_date, end_date, as_at_time, result_status, host_club_id, province_name) VALUES
('359-2025-zvyc-southern-charter-cape-classic', 359, 'ZVYC Southern Charter Cape Classic', 2025, '2025-09-13', '2025-09-14', '2025-09-14 17:15:00+02', 'Final', 1, 'WC');
```

## Related Tables
- `regatta_blocks` - Fleet/class information per regatta
- `results` - Individual race results
- `clubs` - Host club information
