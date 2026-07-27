# Data Format Specifications - HTML Compatible Standards

## Purpose
This document defines the **exact format** for every column in every table to ensure:
1. **Consistent data entry** across all imports
2. **Zero HTML transformations** - HTML displays data directly as-is
3. **Standardized database values** - fix data in DB, not in code

**CRITICAL RULE**: All data must be entered in this exact format. HTML expects these formats and displays them without modification.

---

## Table: `public.regattas`

### `regatta_id` (TEXT, PK, NOT NULL)
**Format**: `{regatta_number}-{year}-{club_code}-{event-slug}` (SINGLE YEAR ONLY)
**Example**: `359-2025-zvyc-southern-charter-cape-classic`
**CRITICAL RULES**:
- ✅ **SINGLE YEAR ONLY** - `2025` (NOT `2025-2025`)
- Always lowercase
- Use hyphens to separate parts
- Event name converted to slug (lowercase, hyphens)
- No quotes
- **HTML expects**: Used in URLs, dropdowns, string parsing (`.split('-')[0]`)
- ❌ **NEVER double year** - `2025-2025` is FORBIDDEN (breaks HTML parsing)

### `event_name` (TEXT, NOT NULL)
**Format**: Full event name as displayed (NO leading year)
**Example**: `Southern Charter Cape Classic` (NOT `2025 Southern Charter Cape Classic`)
**CRITICAL RULES**:
- ✅ **MUST NOT start with year** - HTML displays as `${year} ${event_name}`
- Title case (first letter of each major word capitalized)
- No abbreviations unless standard (e.g., "ILCA", "ISAF")
- Year in middle/end is OK: `Admirals 2025 Regatta`, `Double Cape Race 2025`
- ❌ **NEVER leading year** - Would create duplicate: "2025 2025 Event Name"
- **HTML expects**: Concatenated with year column: `2025 ${event_name}`

### `year` (INTEGER)
**Format**: 4-digit year
**Example**: `2025`
**Rules**:
- Always 4 digits (not 25, not 2025-2026)
- Year of the regatta start date
- **HTML expects**: Displayed directly

### `host_club_code` (TEXT)
**Format**: 3-4 letter uppercase club abbreviation
**Example**: `ZVYC`, `HYC`, `MAC`
**Rules**:
- Uppercase
- Must exist in `clubs` table
- **HTML expects**: Displayed directly in header

### `result_status` (TEXT)
**Format**: Single letter
**Values**: `P` (Provisional) or `F` (Final)
**Rules**:
- Only `P` or `F`
- Uppercase
- **HTML expects**: Displayed as "Provisional" or "Final" (HTML adds word)

### `as_at_time` (TIMESTAMP WITH TIME ZONE)
**Format**: ISO 8601 timestamp
**Example**: `2025-03-23 16:00:00+02:00`
**Rules**:
- Full timestamp with timezone
- **HTML expects**: Formats as "DD Month YYYY at HH:MM" (HTML formats)

### `start_date` (DATE)
**Format**: ISO date
**Example**: `2025-09-14`
**Rules**:
- ISO format (YYYY-MM-DD)
- **HTML expects**: Direct use in sorting/filtering

### `end_date` (DATE)
**Format**: ISO date
**Example**: `2025-09-16`
**Rules**:
- ISO format (YYYY-MM-DD)
- **HTML expects**: Direct use

### `scoring_system` (TEXT)
**Format**: Standard scoring system name
**Example**: `Appendix A`
**Rules**:
- Title case
- Standard values: "Appendix A", "SCHRS", "PY", "ECHO"
- **HTML expects**: Displayed directly

---

## Table: `public.regatta_blocks`

### `block_id` (TEXT, PK, NOT NULL)
**Format**: `{regatta_id}:{fleet-slug}` (SINGLE YEAR, COLON SEPARATOR, NO QUOTES)
**Example**: `359-2025-zvyc-southern-charter-cape-classic:420`
**CRITICAL RULES**:
- ✅ **SINGLE YEAR ONLY** in regatta_id portion (NOT `2025-2025`)
- ✅ **Colon separator** (`:`) - NOT hyphen
- ✅ **No quotes** - `342-2025-sas-mirror:mirror` (NOT `'342-2025-sas-mirror':mirror`)
- ✅ **Complete format** - Must include full regatta_id (not just number-fleet)
- ✅ **Must match `regattas.regatta_id` format** - Single year only
- Lowercase only, no spaces
- **HTML expects**: Used as JavaScript object key `by[r.block_id]`, data attributes, API URLs
- ❌ **NEVER quotes** - Breaks JavaScript: `by['value']` (invalid syntax)
- ❌ **NEVER double year** - Breaks format
- ❌ **NEVER hyphen separator** - Must use colon `:`

### `regatta_id` (TEXT, FK, NOT NULL)
**Format**: Must match `regattas.regatta_id`
**Rules**:
- Must exist in `regattas` table
- **HTML expects**: Used for joins, no display

### `fleet_label` (TEXT)
**Format**: Fleet designation
**Example**: `A`, `B`, `Open`, `Gold`, `420`
**Rules**:
- As displayed in results sheet
- Title case or uppercase as appropriate
- **HTML expects**: Displayed directly (line 467, 497)

### `class_canonical` (TEXT)
**Format**: Standardized class name
**Example**: `420`, `Optimist`, `ILCA 7`, `Dabchick`
**Rules**:
- Must match `classes.class_name` or standard format
- Title case for multi-word (e.g., "ILCA 7", not "ILCA7" or "ilca 7")
- **HTML expects**: Displayed directly (line 467, 497)

### `class_original` (TEXT, NOT NULL)
**Format**: Original class name from results sheet
**Example**: `420`, `OPTIMIST`, `ILCA 7`, `MIRROR (D/H)`
**Rules**:
- Preserve exactly as in source document
- May include parenthetical notes
- **HTML expects**: Used as fallback, displayed directly

### `races_sailed` (INTEGER)
**Format**: Whole number
**Example**: `8`, `11`, `15`
**Rules**:
- Integer, no decimals
- **HTML expects**: Displayed directly (line 487)

### `discard_count` (INTEGER)
**Format**: Whole number
**Example**: `1`, `2`, `3`
**Rules**:
- Integer, no decimals
- Must be ≤ `races_sailed`
- **HTML expects**: Displayed directly (line 488)

### `to_count` (INTEGER)
**Format**: Whole number
**Example**: `7` (when races_sailed=8, discard_count=1)
**Rules**:
- Integer, no decimals
- Must equal `races_sailed - discard_count`
- **HTML expects**: Displayed directly (line 489)

### `scoring_system` (TEXT)
**Format**: Standard scoring system name
**Example**: `Appendix A`, `ECHO`, `SCHRS`
**Rules**:
- Title case
- Must be populated (default: "Appendix A" if NULL)
- **HTML expects**: Displayed directly (line 491)

---

## Table: `public.results`

### `result_id` (BIGINT, PK, NOT NULL)
**Format**: Auto-incrementing integer
**Rules**:
- Auto-generated by database
- **HTML expects**: Used as data attribute, not displayed

### `regatta_id` (TEXT, FK, NOT NULL)
**Format**: Must match `regattas.regatta_id`
**Rules**:
- Must exist in `regattas` table
- **HTML expects**: Used for joins, no display

### `block_id` (TEXT, FK, NOT NULL)
**Format**: Must match `regatta_blocks.block_id`
**Rules**:
- Must exist in `regatta_blocks` table
- **HTML expects**: Used for grouping, no display

### `rank` (INTEGER)
**Format**: Whole number
**Example**: `1`, `2`, `3`
**Rules**:
- Integer, no decimals
- Sequential (1, 2, 3... no gaps, no duplicates for same position)
- **HTML expects**: Displayed directly, formatted with ordinal (1st, 2nd) (line 466)

### `fleet_label` (TEXT, NOT NULL)
**Format**: Fleet designation (actual fleet name, NOT "Overall")
**Example**: `A`, `B`, `Open`, `Mirror`, `Dabchick`
**CRITICAL RULES**:
- ✅ **MANDATORY FIELD** - Never NULL or empty
- ✅ Actual fleet name - `Dabchick`, `Open`, `29er-49er` (NOT `Overall`)
- ✅ Must match `regatta_blocks.fleet_label` for same block
- ✅ Title case or uppercase as appropriate
- **HTML expects**: Displayed directly in results table (line 467)
- ❌ **NEVER "Overall"** - Use actual fleet/class name
- ❌ **NEVER NULL or empty** - Critical field for grouping

### `class_original` (TEXT, NOT NULL)
**Format**: Original class name from results sheet (exact copy from PDF)
**Example**: `420`, `OPTIMIST`, `ILCA 7`, `MIRROR (D/H)`, `29ER`, `Lazer 7` (may contain errors)
**Data Source**: PDF/Results Sheet - Extracted from fleet header, class column, or fleet name section
**Rules**:
- ✅ Preserve exactly as in source document (exact copy, no modifications)
- ✅ Keep capitalization from PDF: `OPTIMIST`, `MIRROR`, `ILCA 7`
- ✅ Keep parenthetical notes: `MIRROR (D/H)`, `EXTRA (S/H)`
- ✅ Keep formatting exactly - never normalize
- ❌ Never modify/standardize (that's what `class_canonical` is for)
- **Validation**: ❌ NOT validated against `classes` table (may contain errors)
- **HTML Usage**: ❌ **CANNOT be used in HTML** - Not validated, may contain errors
- **Purpose**: Audit trail only - preserves PDF exactly as shown (including errors)
**See**: `docs/CLASS_ORIGINAL_DATA_SOURCE.md` for complete explanation

### `class_canonical` (TEXT, NOT NULL)
**Format**: Standardized class name (validated from `classes` table) - **EXACT match required**
**Example**: `420`, `Optimist`, `Ilca 7`, `Ilca 4.7`, `29Er` (must match `classes.class_name` exactly)
**CRITICAL RULES**:
- ✅ **MANDATORY FIELD** - Never NULL or empty
- ✅ **MUST exist in `classes.class_name` table** - Cannot use invalid classes (unless manually overridden - see `docs/CLASS_CANONICAL_MANUAL_OVERRIDE.md`)
- ✅ **MUST be EXACT match** - Must match `classes.class_name` exactly (case-sensitive, no variations like `Ilca 4` vs `Ilca 4.7`)
- ✅ **MUST be validated** - Check against `classes` table during data entry
- ✅ **MUST be corrected** - If PDF shows wrong class (e.g., "Ilca 4"), correct to valid class ("Ilca 4.7" from `classes` table)
- ✅ Standardized version - Must match `classes.class_name` format exactly
- ✅ Consistent capitalization: `Ilca 7`, `Optimist`, `Dabchick`, `Ilca 4.7`
- ✅ Title case for multi-word classes
- **HTML expects**: Displayed directly in results table (line 468) - **ONLY valid class for HTML**
- **CRITICAL FOR FILTERING**: Invalid `class_canonical` breaks HTML filter/search - results won't be found (e.g., `Ilca 4` vs `Ilca 4.7` won't be grouped)
- ❌ **NEVER NULL or empty** - Critical field that affects sailor profile display
- ❌ **NEVER inconsistent capitalization** - `Ilca 7` (wrong) vs `Ilca 7` (correct, from `classes` table)
- ❌ **NEVER use invalid classes** - Must exist in `classes.class_name` table
- ❌ **NEVER use variations** - `Ilca 4` is NOT valid if `classes.class_name` is `Ilca 4.7`
- ❌ **NEVER use `class_original` in HTML** - PDF may contain errors, not validated
**Validation Script**: `admin/tools/validate_class_canonical.sql` - Run after each data import
**See**: `docs/CLASS_CANONICAL_VALIDATION_RULES.md` for complete validation process

### `sail_number` (TEXT)
**Format**: Sail number as string
**Example**: `3452`, `RSA-3452`, `GBR-5733R`
**Rules**:
- Remove country prefixes (RSA, GBR, etc.) for storage
- Store numeric part plus suffix if any (e.g., "5733R")
- **HTML expects**: Displayed directly (line 469)

### `helm_name` (TEXT)
**Format**: Full name (First Last)
**Example**: `Timothy Weaving`, `Benjamin Blom`
**Rules**:
- Title case (first letter of each word)
- No extra spaces
- Must match `sas_id_personal` names when SA ID matched
- **HTML expects**: Displayed directly (line 470)

### `crew_name` (TEXT)
**Format**: Full name (First Last) or empty
**Example**: `John Smith` or ``
**Rules**:
- Title case
- Empty string if no crew
- **HTML expects**: Displayed directly (line 472)

### `club_raw` (TEXT)
**Format**: Club abbreviation from results sheet
**Example**: `ZVYC`, `HYC`, `VLC/LDYC`
**Rules**:
- Uppercase
- If multiple clubs (e.g., "VLC/LDYC"), use first club only
- **HTML expects**: Displayed as fallback (line 464)

### `club_id` (INTEGER)
**Format**: Foreign key to `clubs.club_id`
**Rules**:
- Must exist in `clubs` table
- Mapped from `club_raw`
- **HTML expects**: Used to get `club_abbrev` via join (line 464)

### `helm_sa_sailing_id` (INTEGER)
**Format**: SA Sailing ID as integer
**Example**: `17427`, `21172`
**Rules**:
- No leading zeros (17427, not 017427)
- Must exist in `sas_id_personal.sa_sailing_id`
- **HTML expects**: Displayed directly (line 471)

### `helm_temp_id` (TEXT)
**Format**: `TMP:{number}`
**Example**: `TMP:4`, `TMP:15`
**Rules**:
- Exact format: `TMP:` followed by number
- Only used when `helm_sa_sailing_id` is NULL
- **HTML expects**: Displayed directly (line 471)

### `crew_sa_sailing_id` (INTEGER)
**Format**: Same as `helm_sa_sailing_id`
**Rules**:
- Same format rules as helm
- **HTML expects**: Displayed directly

### `crew_temp_id` (TEXT)
**Format**: Same as `helm_temp_id`
**Rules**:
- Same format rules as helm
- **HTML expects**: Displayed directly

### `race_scores` (JSONB, NOT NULL)
**Format**: JSONB object with keys R1, R2, R3... and string values

**Standard Formats**:
```json
{
  "R1": "1.0",
  "R2": "2.0",
  "R3": "(3.0)",
  "R4": "10.0 DNS",
  "R5": "(22.0 DNC)"
}
```

**Value Format Rules**:

1. **Normal scores**: `"number.0"`
   - Always one decimal place (`.0`)
   - Example: `"1.0"`, `"2.0"`, `"13.0"`

2. **Discarded scores**: `"(number.0)"`
   - Same as normal but wrapped in parentheses
   - Example: `"(2.0)"`, `"(6.0)"`

3. **ISP codes (not discarded)**: `"number.0 CODE"`
   - **CRITICAL**: Score is MANDATORY - ALL ISP codes must include score
   - Space between number and code
   - Always one decimal place (`.0`)
   - Score = entries + 1 (e.g., 6 entries → DNC = 7.0)
   - Example: `"10.0 DNS"`, `"22.0 DNC"`, `"13.0 RET"`, `"7.0 DSQ"`
   - ❌ **NEVER**: `"DNC"`, `"DSQ"` (without score)

4. **ISP codes (discarded)**: `"(number.0 CODE)"`
   - Wrapped in parentheses
   - **CRITICAL**: Score is MANDATORY - ALL ISP codes must include score
   - Space between number and code
   - Example: `"(10.0 DNS)"`, `"(22.0 DNC)"`, `"(7.0 DSQ)"`
   - ❌ **NEVER**: `"(DNC)"`, `"(DSQ)"` (without score)

5. **Decimal rules**:
   - ✅ Always `.0` (one decimal place)
   - ❌ Never `.00` or `.0.0` or `.00.0`
   - Use regex to fix: `.00` → `.0`, `.0.0` → `.0`

6. **ISP Code Values**:
   - `DNC` - Did Not Compete
   - `DNS` - Did Not Start
   - `DNF` - Did Not Finish
   - `RET` - Retired
   - `DSQ` - Disqualified
   - `OCS` - On Course Side
   - `UFD` - U Flag Disqualification
   - `BFD` - Black Flag Disqualification
   - `DPI` - Discretionary Penalty Imposed

**HTML expects**: Displayed directly, no transformation (line 475-477)
- HTML checks for penalty codes with regex: `/\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b/i`
- HTML checks for discarded with regex: `/^\(.*\)$/`
- HTML applies CSS classes (`code`, `disc`) based on these patterns

### `total_points_raw` (NUMERIC)
**Format**: Decimal number with one decimal place
**Example**: `10.0`, `22.5`, `45.0`
**Rules**:
- Always one decimal place (`.0` if whole number)
- Sum of all race scores (including discards)
- **HTML expects**: Formatted with `.toFixed(1)` - must be numeric format (line 479)

### `nett_points_raw` (NUMERIC)
**Format**: Decimal number with one decimal place
**Example**: `8.0`, `20.5`, `43.0`
**Rules**:
- Always one decimal place (`.0` if whole number)
- Total points minus discarded race scores
- Must be ≤ `total_points_raw`
- **HTML expects**: Formatted with `.toFixed(1)` - must be numeric format (line 480)

### `boat_name` (TEXT)
**Format**: Boat name as string
**Example**: `Chinook`, `Sea Breeze`
**Rules**:
- Title case
- As shown in results sheet
- **HTML expects**: Displayed directly if present

### `bow_no`, `jib_no`, `hull_no` (TEXT)
**Format**: Number as string
**Example**: `123`, `45`
**Rules**:
- String format (may have letters)
- **HTML expects**: Displayed directly if present

---

## Table: `public.clubs`

### `club_id` (INTEGER, PK, NOT NULL)
**Format**: Auto-incrementing integer
**Rules**:
- Auto-generated
- **HTML expects**: Used in joins, not displayed

### `club_abbrev` (TEXT)
**Format**: 3-4 letter uppercase abbreviation
**Example**: `ZVYC`, `HYC`, `MAC`
**Rules**:
- Uppercase
- 3-4 characters
- Unique
- **HTML expects**: Displayed directly (line 464)

### `club_fullname` (TEXT)
**Format**: Full club name
**Example**: `Zandvlei Yacht Club`
**Rules**:
- Title case
- **HTML expects**: Not displayed in main viewer

---

## Table: `public.classes`

### `class_id` (INTEGER, PK, NOT NULL)
**Format**: Auto-incrementing integer
**Rules**:
- Auto-generated
- **HTML expects**: Used in joins, not displayed

### `class_name` (TEXT, NOT NULL)
**Format**: Standardized class name
**Example**: `420`, `Optimist`, `ILCA 7`, `Dabchick`
**Rules**:
- Title case for multi-word (e.g., "ILCA 7")
- Must match `results.class_canonical` format
- Unique
- **HTML expects**: Used for matching/display

---

## Table: `public.sas_id_personal`

### `sa_sailing_id` (TEXT, UNIQUE, NOT NULL)
**Format**: SA Sailing ID without leading zeros
**Example**: `17427`, `21172`, `2798`
**Rules**:
- **NO leading zeros** (17427, not 017427 or 17427)
- Stored as TEXT but must be numeric format
- **HTML expects**: Used for matching, displayed directly

### `first_name` (TEXT)
**Format**: First name, title case
**Example**: `Timothy`, `Benjamin`
**Rules**:
- Title case
- Must match `results.helm_name` / `results.crew_name` when matched
- **HTML expects**: Used for name matching/search

### `last_name` (TEXT)
**Format**: Surname, title case
**Example**: `Weaving`, `Blom`
**Rules**:
- Title case
- Must match `results.helm_name` / `results.crew_name` when matched
- **HTML expects**: Used for name matching/search

---

## Data Entry Rules Summary

### Before Importing Data

1. **Verify club codes**: All `club_raw` values must exist in `clubs` table or map to existing club
2. **Standardize class names**: All `class_canonical` must match `classes.class_name`
3. **Fix numeric formats**: All race scores must use `.0` format (not `.00` or `.0.0`)
4. **Fix ISP codes**: Format as `"number.0 CODE"` with space - **MANDATORY**: ALL ISP codes must include score (never just "DNC" or "DSQ")
5. **Remove leading zeros**: SA IDs stored without leading zeros
6. **Standardize dates**: Use ISO format (YYYY-MM-DD)
7. **Standardize timestamps**: Use ISO 8601 with timezone

### During Import

1. **Checksum validation**: Verify totals match sum of race scores
2. **Discard validation**: Verify nett = total - discarded scores
3. **SA ID matching**: Match names exactly before assigning SA IDs
4. **Format fixes**: Apply all format rules during import

### After Import

1. **Run format fix scripts**: Apply any standardization scripts
2. **Verify HTML display**: Check that HTML displays correctly without transformations
3. **Audit data**: Run validation queries

---

## HTML Compatibility Checklist

Before declaring data ready, verify:
- [ ] All numeric values have `.0` format (not `.00` or `.0.0`)
- [ ] All ISP codes formatted as `"number.0 CODE"` with space - ALL must have score (no bare "DNC" or "DSQ")
- [ ] All discarded scores wrapped in parentheses `"(number.0)"`
- [ ] All SA IDs have no leading zeros
- [ ] All club codes uppercase and exist in `clubs` table
- [ ] All class names match `classes.class_name` format
- [ ] All dates in ISO format
- [ ] All timestamps with timezone
- [ ] HTML displays all values directly without transformation

---

## Quick Reference: Common Format Issues

| Issue | Wrong Format | Correct Format |
|-------|--------------|----------------|
| Decimal places | `5.00`, `10.0.0` | `5.0`, `10.0` |
| ISP code | `10.0DNS`, `22.0.0 DNC`, `DNC`, `DSQ` | `10.0 DNS`, `22.0 DNC`, `7.0 DNC`, `7.0 DSQ` (always with score) |
| SA ID | `017427`, `17427` (as string) | `17427` (no leading zeros) |
| Discarded | `2.0` (should be discarded) | `(2.0)` |
| Club code | `zvyc`, `ZVYC/LDYC` | `ZVYC` (first club only) |
| Class name | `ilca 7`, `ILCA7`, `ILCA 7` | `ILCA 7` (title case, space) |
| Date | `23/03/2025`, `Mar 23 2025` | `2025-03-23` (ISO) |

---

## Enforcement

**CRITICAL**: These formats are not optional. Data must match these specifications exactly. HTML expects these formats and displays them without modification. If data doesn't match, **fix it in the database**, not in HTML/API code.


## Purpose
This document defines the **exact format** for every column in every table to ensure:
1. **Consistent data entry** across all imports
2. **Zero HTML transformations** - HTML displays data directly as-is
3. **Standardized database values** - fix data in DB, not in code

**CRITICAL RULE**: All data must be entered in this exact format. HTML expects these formats and displays them without modification.

---

## Table: `public.regattas`

### `regatta_id` (TEXT, PK, NOT NULL)
**Format**: `{regatta_number}-{year}-{club_code}-{event-slug}` (SINGLE YEAR ONLY)
**Example**: `359-2025-zvyc-southern-charter-cape-classic`
**CRITICAL RULES**:
- ✅ **SINGLE YEAR ONLY** - `2025` (NOT `2025-2025`)
- Always lowercase
- Use hyphens to separate parts
- Event name converted to slug (lowercase, hyphens)
- No quotes
- **HTML expects**: Used in URLs, dropdowns, string parsing (`.split('-')[0]`)
- ❌ **NEVER double year** - `2025-2025` is FORBIDDEN (breaks HTML parsing)

### `event_name` (TEXT, NOT NULL)
**Format**: Full event name as displayed (NO leading year)
**Example**: `Southern Charter Cape Classic` (NOT `2025 Southern Charter Cape Classic`)
**CRITICAL RULES**:
- ✅ **MUST NOT start with year** - HTML displays as `${year} ${event_name}`
- Title case (first letter of each major word capitalized)
- No abbreviations unless standard (e.g., "ILCA", "ISAF")
- Year in middle/end is OK: `Admirals 2025 Regatta`, `Double Cape Race 2025`
- ❌ **NEVER leading year** - Would create duplicate: "2025 2025 Event Name"
- **HTML expects**: Concatenated with year column: `2025 ${event_name}`

### `year` (INTEGER)
**Format**: 4-digit year
**Example**: `2025`
**Rules**:
- Always 4 digits (not 25, not 2025-2026)
- Year of the regatta start date
- **HTML expects**: Displayed directly

### `host_club_code` (TEXT)
**Format**: 3-4 letter uppercase club abbreviation
**Example**: `ZVYC`, `HYC`, `MAC`
**Rules**:
- Uppercase
- Must exist in `clubs` table
- **HTML expects**: Displayed directly in header

### `result_status` (TEXT)
**Format**: Single letter
**Values**: `P` (Provisional) or `F` (Final)
**Rules**:
- Only `P` or `F`
- Uppercase
- **HTML expects**: Displayed as "Provisional" or "Final" (HTML adds word)

### `as_at_time` (TIMESTAMP WITH TIME ZONE)
**Format**: ISO 8601 timestamp
**Example**: `2025-03-23 16:00:00+02:00`
**Rules**:
- Full timestamp with timezone
- **HTML expects**: Formats as "DD Month YYYY at HH:MM" (HTML formats)

### `start_date` (DATE)
**Format**: ISO date
**Example**: `2025-09-14`
**Rules**:
- ISO format (YYYY-MM-DD)
- **HTML expects**: Direct use in sorting/filtering

### `end_date` (DATE)
**Format**: ISO date
**Example**: `2025-09-16`
**Rules**:
- ISO format (YYYY-MM-DD)
- **HTML expects**: Direct use

### `scoring_system` (TEXT)
**Format**: Standard scoring system name
**Example**: `Appendix A`
**Rules**:
- Title case
- Standard values: "Appendix A", "SCHRS", "PY", "ECHO"
- **HTML expects**: Displayed directly

---

## Table: `public.regatta_blocks`

### `block_id` (TEXT, PK, NOT NULL)
**Format**: `{regatta_id}:{fleet-slug}` (SINGLE YEAR, COLON SEPARATOR, NO QUOTES)
**Example**: `359-2025-zvyc-southern-charter-cape-classic:420`
**CRITICAL RULES**:
- ✅ **SINGLE YEAR ONLY** in regatta_id portion (NOT `2025-2025`)
- ✅ **Colon separator** (`:`) - NOT hyphen
- ✅ **No quotes** - `342-2025-sas-mirror:mirror` (NOT `'342-2025-sas-mirror':mirror`)
- ✅ **Complete format** - Must include full regatta_id (not just number-fleet)
- ✅ **Must match `regattas.regatta_id` format** - Single year only
- Lowercase only, no spaces
- **HTML expects**: Used as JavaScript object key `by[r.block_id]`, data attributes, API URLs
- ❌ **NEVER quotes** - Breaks JavaScript: `by['value']` (invalid syntax)
- ❌ **NEVER double year** - Breaks format
- ❌ **NEVER hyphen separator** - Must use colon `:`

### `regatta_id` (TEXT, FK, NOT NULL)
**Format**: Must match `regattas.regatta_id`
**Rules**:
- Must exist in `regattas` table
- **HTML expects**: Used for joins, no display

### `fleet_label` (TEXT)
**Format**: Fleet designation
**Example**: `A`, `B`, `Open`, `Gold`, `420`
**Rules**:
- As displayed in results sheet
- Title case or uppercase as appropriate
- **HTML expects**: Displayed directly (line 467, 497)

### `class_canonical` (TEXT)
**Format**: Standardized class name
**Example**: `420`, `Optimist`, `ILCA 7`, `Dabchick`
**Rules**:
- Must match `classes.class_name` or standard format
- Title case for multi-word (e.g., "ILCA 7", not "ILCA7" or "ilca 7")
- **HTML expects**: Displayed directly (line 467, 497)

### `class_original` (TEXT, NOT NULL)
**Format**: Original class name from results sheet
**Example**: `420`, `OPTIMIST`, `ILCA 7`, `MIRROR (D/H)`
**Rules**:
- Preserve exactly as in source document
- May include parenthetical notes
- **HTML expects**: Used as fallback, displayed directly

### `races_sailed` (INTEGER)
**Format**: Whole number
**Example**: `8`, `11`, `15`
**Rules**:
- Integer, no decimals
- **HTML expects**: Displayed directly (line 487)

### `discard_count` (INTEGER)
**Format**: Whole number
**Example**: `1`, `2`, `3`
**Rules**:
- Integer, no decimals
- Must be ≤ `races_sailed`
- **HTML expects**: Displayed directly (line 488)

### `to_count` (INTEGER)
**Format**: Whole number
**Example**: `7` (when races_sailed=8, discard_count=1)
**Rules**:
- Integer, no decimals
- Must equal `races_sailed - discard_count`
- **HTML expects**: Displayed directly (line 489)

### `scoring_system` (TEXT)
**Format**: Standard scoring system name
**Example**: `Appendix A`, `ECHO`, `SCHRS`
**Rules**:
- Title case
- Must be populated (default: "Appendix A" if NULL)
- **HTML expects**: Displayed directly (line 491)

---

## Table: `public.results`

### `result_id` (BIGINT, PK, NOT NULL)
**Format**: Auto-incrementing integer
**Rules**:
- Auto-generated by database
- **HTML expects**: Used as data attribute, not displayed

### `regatta_id` (TEXT, FK, NOT NULL)
**Format**: Must match `regattas.regatta_id`
**Rules**:
- Must exist in `regattas` table
- **HTML expects**: Used for joins, no display

### `block_id` (TEXT, FK, NOT NULL)
**Format**: Must match `regatta_blocks.block_id`
**Rules**:
- Must exist in `regatta_blocks` table
- **HTML expects**: Used for grouping, no display

### `rank` (INTEGER)
**Format**: Whole number
**Example**: `1`, `2`, `3`
**Rules**:
- Integer, no decimals
- Sequential (1, 2, 3... no gaps, no duplicates for same position)
- **HTML expects**: Displayed directly, formatted with ordinal (1st, 2nd) (line 466)

### `fleet_label` (TEXT, NOT NULL)
**Format**: Fleet designation (actual fleet name, NOT "Overall")
**Example**: `A`, `B`, `Open`, `Mirror`, `Dabchick`
**CRITICAL RULES**:
- ✅ **MANDATORY FIELD** - Never NULL or empty
- ✅ Actual fleet name - `Dabchick`, `Open`, `29er-49er` (NOT `Overall`)
- ✅ Must match `regatta_blocks.fleet_label` for same block
- ✅ Title case or uppercase as appropriate
- **HTML expects**: Displayed directly in results table (line 467)
- ❌ **NEVER "Overall"** - Use actual fleet/class name
- ❌ **NEVER NULL or empty** - Critical field for grouping

### `class_original` (TEXT, NOT NULL)
**Format**: Original class name from results sheet (exact copy from PDF)
**Example**: `420`, `OPTIMIST`, `ILCA 7`, `MIRROR (D/H)`, `29ER`, `Lazer 7` (may contain errors)
**Data Source**: PDF/Results Sheet - Extracted from fleet header, class column, or fleet name section
**Rules**:
- ✅ Preserve exactly as in source document (exact copy, no modifications)
- ✅ Keep capitalization from PDF: `OPTIMIST`, `MIRROR`, `ILCA 7`
- ✅ Keep parenthetical notes: `MIRROR (D/H)`, `EXTRA (S/H)`
- ✅ Keep formatting exactly - never normalize
- ❌ Never modify/standardize (that's what `class_canonical` is for)
- **Validation**: ❌ NOT validated against `classes` table (may contain errors)
- **HTML Usage**: ❌ **CANNOT be used in HTML** - Not validated, may contain errors
- **Purpose**: Audit trail only - preserves PDF exactly as shown (including errors)
**See**: `docs/CLASS_ORIGINAL_DATA_SOURCE.md` for complete explanation

### `class_canonical` (TEXT, NOT NULL)
**Format**: Standardized class name (validated from `classes` table) - **EXACT match required**
**Example**: `420`, `Optimist`, `Ilca 7`, `Ilca 4.7`, `29Er` (must match `classes.class_name` exactly)
**CRITICAL RULES**:
- ✅ **MANDATORY FIELD** - Never NULL or empty
- ✅ **MUST exist in `classes.class_name` table** - Cannot use invalid classes (unless manually overridden - see `docs/CLASS_CANONICAL_MANUAL_OVERRIDE.md`)
- ✅ **MUST be EXACT match** - Must match `classes.class_name` exactly (case-sensitive, no variations like `Ilca 4` vs `Ilca 4.7`)
- ✅ **MUST be validated** - Check against `classes` table during data entry
- ✅ **MUST be corrected** - If PDF shows wrong class (e.g., "Ilca 4"), correct to valid class ("Ilca 4.7" from `classes` table)
- ✅ Standardized version - Must match `classes.class_name` format exactly
- ✅ Consistent capitalization: `Ilca 7`, `Optimist`, `Dabchick`, `Ilca 4.7`
- ✅ Title case for multi-word classes
- **HTML expects**: Displayed directly in results table (line 468) - **ONLY valid class for HTML**
- **CRITICAL FOR FILTERING**: Invalid `class_canonical` breaks HTML filter/search - results won't be found (e.g., `Ilca 4` vs `Ilca 4.7` won't be grouped)
- ❌ **NEVER NULL or empty** - Critical field that affects sailor profile display
- ❌ **NEVER inconsistent capitalization** - `Ilca 7` (wrong) vs `Ilca 7` (correct, from `classes` table)
- ❌ **NEVER use invalid classes** - Must exist in `classes.class_name` table
- ❌ **NEVER use variations** - `Ilca 4` is NOT valid if `classes.class_name` is `Ilca 4.7`
- ❌ **NEVER use `class_original` in HTML** - PDF may contain errors, not validated
**Validation Script**: `admin/tools/validate_class_canonical.sql` - Run after each data import
**See**: `docs/CLASS_CANONICAL_VALIDATION_RULES.md` for complete validation process

### `sail_number` (TEXT)
**Format**: Sail number as string
**Example**: `3452`, `RSA-3452`, `GBR-5733R`
**Rules**:
- Remove country prefixes (RSA, GBR, etc.) for storage
- Store numeric part plus suffix if any (e.g., "5733R")
- **HTML expects**: Displayed directly (line 469)

### `helm_name` (TEXT)
**Format**: Full name (First Last)
**Example**: `Timothy Weaving`, `Benjamin Blom`
**Rules**:
- Title case (first letter of each word)
- No extra spaces
- Must match `sas_id_personal` names when SA ID matched
- **HTML expects**: Displayed directly (line 470)

### `crew_name` (TEXT)
**Format**: Full name (First Last) or empty
**Example**: `John Smith` or ``
**Rules**:
- Title case
- Empty string if no crew
- **HTML expects**: Displayed directly (line 472)

### `club_raw` (TEXT)
**Format**: Club abbreviation from results sheet
**Example**: `ZVYC`, `HYC`, `VLC/LDYC`
**Rules**:
- Uppercase
- If multiple clubs (e.g., "VLC/LDYC"), use first club only
- **HTML expects**: Displayed as fallback (line 464)

### `club_id` (INTEGER)
**Format**: Foreign key to `clubs.club_id`
**Rules**:
- Must exist in `clubs` table
- Mapped from `club_raw`
- **HTML expects**: Used to get `club_abbrev` via join (line 464)

### `helm_sa_sailing_id` (INTEGER)
**Format**: SA Sailing ID as integer
**Example**: `17427`, `21172`
**Rules**:
- No leading zeros (17427, not 017427)
- Must exist in `sas_id_personal.sa_sailing_id`
- **HTML expects**: Displayed directly (line 471)

### `helm_temp_id` (TEXT)
**Format**: `TMP:{number}`
**Example**: `TMP:4`, `TMP:15`
**Rules**:
- Exact format: `TMP:` followed by number
- Only used when `helm_sa_sailing_id` is NULL
- **HTML expects**: Displayed directly (line 471)

### `crew_sa_sailing_id` (INTEGER)
**Format**: Same as `helm_sa_sailing_id`
**Rules**:
- Same format rules as helm
- **HTML expects**: Displayed directly

### `crew_temp_id` (TEXT)
**Format**: Same as `helm_temp_id`
**Rules**:
- Same format rules as helm
- **HTML expects**: Displayed directly

### `race_scores` (JSONB, NOT NULL)
**Format**: JSONB object with keys R1, R2, R3... and string values

**Standard Formats**:
```json
{
  "R1": "1.0",
  "R2": "2.0",
  "R3": "(3.0)",
  "R4": "10.0 DNS",
  "R5": "(22.0 DNC)"
}
```

**Value Format Rules**:

1. **Normal scores**: `"number.0"`
   - Always one decimal place (`.0`)
   - Example: `"1.0"`, `"2.0"`, `"13.0"`

2. **Discarded scores**: `"(number.0)"`
   - Same as normal but wrapped in parentheses
   - Example: `"(2.0)"`, `"(6.0)"`

3. **ISP codes (not discarded)**: `"number.0 CODE"`
   - **CRITICAL**: Score is MANDATORY - ALL ISP codes must include score
   - Space between number and code
   - Always one decimal place (`.0`)
   - Score = entries + 1 (e.g., 6 entries → DNC = 7.0)
   - Example: `"10.0 DNS"`, `"22.0 DNC"`, `"13.0 RET"`, `"7.0 DSQ"`
   - ❌ **NEVER**: `"DNC"`, `"DSQ"` (without score)

4. **ISP codes (discarded)**: `"(number.0 CODE)"`
   - Wrapped in parentheses
   - **CRITICAL**: Score is MANDATORY - ALL ISP codes must include score
   - Space between number and code
   - Example: `"(10.0 DNS)"`, `"(22.0 DNC)"`, `"(7.0 DSQ)"`
   - ❌ **NEVER**: `"(DNC)"`, `"(DSQ)"` (without score)

5. **Decimal rules**:
   - ✅ Always `.0` (one decimal place)
   - ❌ Never `.00` or `.0.0` or `.00.0`
   - Use regex to fix: `.00` → `.0`, `.0.0` → `.0`

6. **ISP Code Values**:
   - `DNC` - Did Not Compete
   - `DNS` - Did Not Start
   - `DNF` - Did Not Finish
   - `RET` - Retired
   - `DSQ` - Disqualified
   - `OCS` - On Course Side
   - `UFD` - U Flag Disqualification
   - `BFD` - Black Flag Disqualification
   - `DPI` - Discretionary Penalty Imposed

**HTML expects**: Displayed directly, no transformation (line 475-477)
- HTML checks for penalty codes with regex: `/\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b/i`
- HTML checks for discarded with regex: `/^\(.*\)$/`
- HTML applies CSS classes (`code`, `disc`) based on these patterns

### `total_points_raw` (NUMERIC)
**Format**: Decimal number with one decimal place
**Example**: `10.0`, `22.5`, `45.0`
**Rules**:
- Always one decimal place (`.0` if whole number)
- Sum of all race scores (including discards)
- **HTML expects**: Formatted with `.toFixed(1)` - must be numeric format (line 479)

### `nett_points_raw` (NUMERIC)
**Format**: Decimal number with one decimal place
**Example**: `8.0`, `20.5`, `43.0`
**Rules**:
- Always one decimal place (`.0` if whole number)
- Total points minus discarded race scores
- Must be ≤ `total_points_raw`
- **HTML expects**: Formatted with `.toFixed(1)` - must be numeric format (line 480)

### `boat_name` (TEXT)
**Format**: Boat name as string
**Example**: `Chinook`, `Sea Breeze`
**Rules**:
- Title case
- As shown in results sheet
- **HTML expects**: Displayed directly if present

### `bow_no`, `jib_no`, `hull_no` (TEXT)
**Format**: Number as string
**Example**: `123`, `45`
**Rules**:
- String format (may have letters)
- **HTML expects**: Displayed directly if present

---

## Table: `public.clubs`

### `club_id` (INTEGER, PK, NOT NULL)
**Format**: Auto-incrementing integer
**Rules**:
- Auto-generated
- **HTML expects**: Used in joins, not displayed

### `club_abbrev` (TEXT)
**Format**: 3-4 letter uppercase abbreviation
**Example**: `ZVYC`, `HYC`, `MAC`
**Rules**:
- Uppercase
- 3-4 characters
- Unique
- **HTML expects**: Displayed directly (line 464)

### `club_fullname` (TEXT)
**Format**: Full club name
**Example**: `Zandvlei Yacht Club`
**Rules**:
- Title case
- **HTML expects**: Not displayed in main viewer

---

## Table: `public.classes`

### `class_id` (INTEGER, PK, NOT NULL)
**Format**: Auto-incrementing integer
**Rules**:
- Auto-generated
- **HTML expects**: Used in joins, not displayed

### `class_name` (TEXT, NOT NULL)
**Format**: Standardized class name
**Example**: `420`, `Optimist`, `ILCA 7`, `Dabchick`
**Rules**:
- Title case for multi-word (e.g., "ILCA 7")
- Must match `results.class_canonical` format
- Unique
- **HTML expects**: Used for matching/display

---

## Table: `public.sas_id_personal`

### `sa_sailing_id` (TEXT, UNIQUE, NOT NULL)
**Format**: SA Sailing ID without leading zeros
**Example**: `17427`, `21172`, `2798`
**Rules**:
- **NO leading zeros** (17427, not 017427 or 17427)
- Stored as TEXT but must be numeric format
- **HTML expects**: Used for matching, displayed directly

### `first_name` (TEXT)
**Format**: First name, title case
**Example**: `Timothy`, `Benjamin`
**Rules**:
- Title case
- Must match `results.helm_name` / `results.crew_name` when matched
- **HTML expects**: Used for name matching/search

### `last_name` (TEXT)
**Format**: Surname, title case
**Example**: `Weaving`, `Blom`
**Rules**:
- Title case
- Must match `results.helm_name` / `results.crew_name` when matched
- **HTML expects**: Used for name matching/search

---

## Data Entry Rules Summary

### Before Importing Data

1. **Verify club codes**: All `club_raw` values must exist in `clubs` table or map to existing club
2. **Standardize class names**: All `class_canonical` must match `classes.class_name`
3. **Fix numeric formats**: All race scores must use `.0` format (not `.00` or `.0.0`)
4. **Fix ISP codes**: Format as `"number.0 CODE"` with space - **MANDATORY**: ALL ISP codes must include score (never just "DNC" or "DSQ")
5. **Remove leading zeros**: SA IDs stored without leading zeros
6. **Standardize dates**: Use ISO format (YYYY-MM-DD)
7. **Standardize timestamps**: Use ISO 8601 with timezone

### During Import

1. **Checksum validation**: Verify totals match sum of race scores
2. **Discard validation**: Verify nett = total - discarded scores
3. **SA ID matching**: Match names exactly before assigning SA IDs
4. **Format fixes**: Apply all format rules during import

### After Import

1. **Run format fix scripts**: Apply any standardization scripts
2. **Verify HTML display**: Check that HTML displays correctly without transformations
3. **Audit data**: Run validation queries

---

## HTML Compatibility Checklist

Before declaring data ready, verify:
- [ ] All numeric values have `.0` format (not `.00` or `.0.0`)
- [ ] All ISP codes formatted as `"number.0 CODE"` with space - ALL must have score (no bare "DNC" or "DSQ")
- [ ] All discarded scores wrapped in parentheses `"(number.0)"`
- [ ] All SA IDs have no leading zeros
- [ ] All club codes uppercase and exist in `clubs` table
- [ ] All class names match `classes.class_name` format
- [ ] All dates in ISO format
- [ ] All timestamps with timezone
- [ ] HTML displays all values directly without transformation

---

## Quick Reference: Common Format Issues

| Issue | Wrong Format | Correct Format |
|-------|--------------|----------------|
| Decimal places | `5.00`, `10.0.0` | `5.0`, `10.0` |
| ISP code | `10.0DNS`, `22.0.0 DNC`, `DNC`, `DSQ` | `10.0 DNS`, `22.0 DNC`, `7.0 DNC`, `7.0 DSQ` (always with score) |
| SA ID | `017427`, `17427` (as string) | `17427` (no leading zeros) |
| Discarded | `2.0` (should be discarded) | `(2.0)` |
| Club code | `zvyc`, `ZVYC/LDYC` | `ZVYC` (first club only) |
| Class name | `ilca 7`, `ILCA7`, `ILCA 7` | `ILCA 7` (title case, space) |
| Date | `23/03/2025`, `Mar 23 2025` | `2025-03-23` (ISO) |

---

## Enforcement

**CRITICAL**: These formats are not optional. Data must match these specifications exactly. HTML expects these formats and displays them without modification. If data doesn't match, **fix it in the database**, not in HTML/API code.

