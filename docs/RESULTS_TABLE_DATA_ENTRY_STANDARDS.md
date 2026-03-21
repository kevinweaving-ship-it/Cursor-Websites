# Results Table - Complete Data Entry Standards

## Purpose
This document defines **ALL** data entry rules and format standards for the `public.results` table to ensure:
1. **HTML Compatibility** - Data format doesn't break HTML pages
2. **Consistency** - All data follows identical format patterns
3. **Data Integrity** - Foreign keys, constraints, and relationships maintained
4. **No Duplications** - Same logical value has identical format
5. **Single Year Format** - No double years anywhere

**CRITICAL**: These rules MUST be followed for ALL new data entry. Existing data has been standardized to these rules.

---

## Mandatory Checks Before Data Entry

### Pre-Entry Validation Checklist

- [ ] **HTML Compatibility**: Verify column format won't break HTML display
- [ ] **Single Year**: Check for double year patterns (`2025-2025` forbidden)
- [ ] **No Quotes**: Ensure no single quotes (`'`) in text fields
- [ ] **No Duplications**: Verify same logical value has identical format
- [ ] **Format Consistency**: All rows use same pattern
- [ ] **Foreign Keys**: Verify FK values exist in referenced tables
- [ ] **Race Scores Validation**: **MANDATORY** - Run `admin/tools/validate_race_scores_pre_entry.sql` before entry
  - All penalty codes must have scores (`"14.0 DNC"` not `"DNC"`)
  - All scores must have `.0` format (`"5.0"` not `"5"`)
  - All discards must use parentheses (`"(11.0)"` not `"-11.0"`)
  - See `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` for complete rules
- [ ] **Discard Brackets Compliance**: **MANDATORY** - Run `admin/tools/validate_discard_brackets_compliance.sql` after entry
  - `discard_count` must match number of bracketed scores
  - Worst scores must be discarded (per block discard rule)
  - Block rule "Discards: 2" = each sailor must have exactly 2 bracketed scores
  - See `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` section 10 for complete rules

---

## Column-by-Column Data Entry Rules

### `result_id` (BIGINT, PK, AUTO-INCREMENT)

**DO NOT SET MANUALLY** - Database auto-generates this value.

**Rules**:
- ✅ Always let database generate via `SERIAL`/sequence
- ❌ NEVER specify in INSERT statements
- ❌ NEVER manually set value
- ❌ NEVER use explicit numbers

**Example INSERT**:
```sql
-- ✅ CORRECT - Let database generate
INSERT INTO public.results (regatta_id, block_id, rank, ...) VALUES (...);

-- ❌ WRONG - Don't specify result_id
INSERT INTO public.results (result_id, regatta_id, ...) VALUES (123, ...);
```

---

### `regatta_id` (TEXT, NOT NULL, FK)

**Format**: `{regatta_number}-{year}-{club_code}-{event-slug}`

**CRITICAL RULES**:
1. ✅ **SINGLE YEAR ONLY** - `342-2025-sas-mirror-national-championship` (NOT `342-2025-2025-...`)
2. ✅ **Lowercase only** - `zvyc`, `sas`, `hyc`
3. ✅ **No quotes** - `342-2025-sas-mirror` (NOT `'342-2025-sas-mirror'`)
4. ✅ **No spaces** - Use hyphens
5. ✅ **Must exist in `regattas` table** (FK constraint)
6. ❌ **NEVER double year** - `2025-2025` is FORBIDDEN
7. ❌ **NEVER quotes** - Quotes break HTML URLs
8. ❌ **NEVER uppercase** - Breaks URL consistency

**HTML Usage**:
- Used in dropdown: `value="${r.regatta_id}"`
- Used in API calls: `fetch(\`${API}/api/regatta/${id}\`)`
- Used in string parsing: `.split('-')[0]` to extract regatta number

**Examples**:
```sql
-- ✅ CORRECT
'342-2025-sas-mirror-national-championship'

-- ❌ WRONG - Double year
'342-2025-2025-sas-mirror-national-championship'

-- ❌ WRONG - Has quotes
''342-2025-sas-mirror-national-championship''

-- ❌ WRONG - Uppercase
'342-2025-SAS-Mirror-National-Championship'
```

---

### `block_id` (TEXT, NOT NULL, FK)

**Format**: `{regatta_id}:{fleet-slug}`

**CRITICAL RULES**:
1. ✅ **SINGLE YEAR ONLY** in regatta_id portion
2. ✅ **Colon separator** (`:`) between regatta_id and fleet-slug
3. ✅ **No quotes** - `342-2025-sas-mirror:mirror` (NOT `'342-2025-sas-mirror':mirror`)
4. ✅ **Lowercase only**
5. ✅ **No spaces**
6. ✅ **Must exist in `regatta_blocks` table** (FK constraint)
7. ✅ **Complete format** - Must include full regatta_id (not just number-fleet)
8. ❌ **NEVER quotes** - Breaks JavaScript object keys: `by[r.block_id]` (invalid syntax)
9. ❌ **NEVER double year** - `2025-2025` is FORBIDDEN
10. ❌ **NEVER hyphen separator** - Must use colon `:`
11. ❌ **NEVER missing regatta_id parts** - Must have year, club, event-slug

**HTML Usage**:
- Used as JavaScript object key: `by[r.block_id]` (line 432 in regatta_viewer.html)
- Used in data attributes: `data-block-id="${h.block_id}"`
- Used in API calls: `/api/block/${td.dataset.blockId}`

**Examples**:
```sql
-- ✅ CORRECT - Full regatta_id + colon + fleet-slug
'342-2025-sas-mirror-national-championship:mirror'
'349-2025-j22-nationals-results:j22'
'357-2025-dabchick-gauteng-results:dabchick'

-- ❌ WRONG - Missing full regatta_id
'349-j22'  -- Missing: year, club, event-slug

-- ❌ WRONG - Has quotes (breaks JavaScript)
''342-2025-sas-mirror-national-championship':mirror'

-- ❌ WRONG - Double year
'339-2025-2025-wcapedinghychamps-results:optimist-a'

-- ❌ WRONG - Hyphen separator (should be colon)
'357-dabchick'
'343-2025-vasco-offshore'
```

**How to Build block_id**:
1. Get full `regatta_id` from `regattas` table: `SELECT regatta_id FROM regattas WHERE regatta_number = 349`
2. Get fleet-slug (lowercase, hyphens): `j22`, `optimist-a`, `multihull-fleet`
3. Combine with colon: `{regatta_id}:{fleet-slug}`

---

### `rank` (INTEGER)

**Format**: Whole number, positive integer

**Rules**:
- ✅ Positive integer (1, 2, 3, ...)
- ✅ Sequential within fleet/block (no gaps unless ISP-coded entries not ranked)
- ✅ Duplicates allowed if same `nett_points_raw` (legitimate ties)
- ⚠️ NULL allowed for DNS/DNC/DSQ entries that don't have final rank
- ❌ Never zero or negative
- ❌ Never decimals (INTEGER type enforces this)

**HTML Usage**: Displayed directly, formatted with ordinal (1st, 2nd, 3rd) - no transformation needed

**Examples**:
```sql
-- ✅ CORRECT
1, 2, 3, 15, 20  -- Normal ranks
4, 4, 4, 4, 4, 4  -- Legitimate ties (6 sailors tied for 4th, same nett_points_raw)

-- ✅ ACCEPTABLE
NULL  -- DNS/DNC entry without final rank

-- ❌ WRONG
0, -1, 1.5  -- Invalid values (INTEGER type prevents decimals)
```

**Audit Results**:
- ✅ 411/411 results have ranks (100% populated)
- ✅ All ranks valid (1-21 range)
- ✅ 1 block with legitimate ties (6 sailors tied for rank 4, same nett_points_raw)
- ⚠️ 1 block with gaps (may be intentional - DNS/DNC entries not ranked)

---

### `fleet_label` (TEXT, NOT NULL)

**Format**: Fleet designation as displayed (actual fleet name, NOT "Overall")

**CRITICAL RULES**:
- ✅ **MANDATORY FIELD** - Never NULL or empty
- ✅ Actual fleet name - `Optimist A`, `Open`, `Mirror`, `420` (NOT "Overall")
- ✅ Must match `regatta_blocks.fleet_label` for same block
- ✅ Consistent within block - All entries in same block must have identical `fleet_label`
- ✅ Title case or uppercase as appropriate: "Optimist A", "Open", "Mirror"
- ❌ **NEVER "Overall"** - Use actual fleet/class name
- ❌ **NEVER NULL or empty** - Critical field for grouping

**Checksum Validation**: 
- Run `admin/tools/checksum_fleet_label.sql` after import
- Verify all entries in block have same `fleet_label`
- Compare with PDF/results sheet
- **Manual Override**: For rare cases where PDF is wrong - see `docs/FLEET_LABEL_CHECKSUM_RULES.md`

**HTML Usage**: Displayed directly in results table (line 467)

**Examples**:
```sql
-- ✅ CORRECT
'Optimist A', 'Open', 'Mirror', '420', 'ILCA 6'

-- ❌ WRONG - Meaningless
'Overall'

-- ❌ WRONG - Missing
NULL, ''
```

**HTML Usage**: Displayed directly in results table

---

### `class_original` (TEXT, NOT NULL)

**Format**: Original class name from results sheet (exact copy from PDF)

**Data Source**: 
- **PDF/Results Sheet** - Extracted from:
  - Fleet header row (e.g., "OPTIMIST A FLEET")
  - Class column in results table
  - Fleet name section
- **Extraction Method**: Exact text copy - NO modifications

**CRITICAL RULES**:
- ✅ **Preserve exactly** as shown in PDF (exact copy)
- ✅ **Keep capitalization** from source: `OPTIMIST`, `MIRROR`, `ILCA 7`
- ✅ **Keep parenthetical notes**: `MIRROR (D/H)`, `EXTRA (S/H)`
- ✅ **Keep spaces**: `ILCA 7` (not `ILCA7`)
- ✅ **Keep formatting exactly** - never normalize
- ❌ **NEVER modify/standardize** - that's what `class_canonical` is for
- ❌ **NEVER guess** - if PDF doesn't show class, extract what's there

**Examples**:
```sql
-- PDF shows "MIRROR (D/H)" → class_original = 'MIRROR (D/H)'
-- PDF shows "OPTIMIST A" → class_original = 'OPTIMIST A'
-- PDF shows "ILCA 7" → class_original = 'ILCA 7'
-- PDF shows "29ER" → class_original = '29ER' (preserves PDF format)
```

**See**: `docs/CLASS_ORIGINAL_DATA_SOURCE.md` for complete explanation of data source.

**Examples**:
```sql
-- ✅ CORRECT - Preserve original
'OPTIMIST', '420', 'MIRROR (D/H)', 'ILCA 7', 'Dabchick'

-- ❌ WRONG - Don't standardize here
'Optimist' -- If original was 'OPTIMIST', keep it uppercase
```

---

### `class_canonical` (TEXT, NOT NULL)

**Format**: Standardized class name (validated from `classes` table)

**CRITICAL**: This is a MANDATORY field - NEVER leave empty.

**Data Source**: 
- **Validated from `classes.class_name` table** - MUST exist in `classes` table
- **Corrected during data entry** - If PDF shows wrong class, correct to valid class
- **HTML Display**: ✅ **ONLY valid class for HTML** - HTML must use this field

**CRITICAL RULES**:
- ✅ **MUST match `classes.class_name`** - Must exist in `classes` table
- ✅ **MUST be corrected** - If PDF shows wrong class (e.g., "Lazer 7"), correct to valid class ("ILCA 7")
- ✅ **MUST be validated** - Cannot use classes not in `classes` table
- ✅ Title case: `ILCA 7`, `Optimist`, `Dabchick`
- ✅ Consistent capitalization
- ✅ Spaces preserved: `ILCA 7` (not `ILCA7`)
- ✅ **MUST NOT be NULL or empty**
- ❌ Never mixed case: `Ilca 7` (use `ILCA 7`)
- ❌ Never lowercase: `ilca 7` (use `ILCA 7`)
- ❌ Never NULL or empty - **CRITICAL FIELD**
- ❌ Never use invalid classes - Must exist in `classes` table

**Validation Process**:
1. Extract `class_original` from PDF (exact copy)
2. **Validate against `classes.class_name` table** - Check if exists
3. **Use EXACT match** - Must match `classes.class_name` exactly (e.g., `Ilca 4.7` not `Ilca 4`)
4. If PDF is wrong → correct to valid class from `classes` table (e.g., PDF shows `ILCA 4` → use `Ilca 4.7`)
5. Store corrected class in `class_canonical`
6. HTML uses `class_canonical` (validated, corrected, exists in `classes` table)
7. **CRITICAL**: Invalid `class_canonical` breaks HTML filtering - results won't be found in search

**Why EXACT Match is Critical:**
- HTML filter/search uses `class_canonical` to group results
- If `Ilca 4` (invalid) vs `Ilca 4.7` (valid), they won't be grouped together
- Example: 10 ILCA 4.7 sailors, 5 have `Ilca 4` → only 5 found when filtering for "Ilca 4.7"

**HTML Usage**: 
- ✅ **ONLY field HTML should use** for class display
- ❌ **HTML must NOT use `class_original`** - PDF may contain errors, not validated
- Used in results table, grouping, filtering, sailor profiles

**Standard Values**:
- `ILCA 4`, `ILCA 6`, `ILCA 7` (not `Ilca 4` or `ilca 7`)
- `Optimist` (not `optimist` or `OPTIMIST`)
- `Dabchick`, `Mirror`, `420`, `505`, `29er`, `49er`

**Examples**:
```sql
-- ✅ CORRECT
'ILCA 7', 'Optimist', 'Dabchick', 'Mirror', '420'

-- ❌ WRONG - Inconsistent capitalization
'Ilca 7', 'ilca 7', 'ILCA7'

-- ❌ WRONG - Empty/NULL
NULL, ''
```

---

### `sail_number` (TEXT)

**Format**: Sail number as displayed

**Rules**:
- ✅ Preserve exactly as shown
- ✅ Remove country prefix: `RSA-3452` → `3452`
- ✅ Remove other prefixes: `GBR-5733R` → `5733R` (store prefix in `nationality` if available)
- ✅ Keep suffix: `5733R`, `123A`
- ❌ Never include country prefix: Don't store `RSA-3452`

**Examples**:
```sql
-- ✅ CORRECT
'3452', '5733R', '123A', '456'

-- ❌ WRONG - With prefix
'RSA-3452', 'GBR-5733R'
```

---

### `helm_name` (TEXT)

**Format**: Full name as in database

**Rules**:
- ✅ Use name from `sas_id_personal` table (authoritative source)
- ✅ Correct spelling errors from PDF using database
- ✅ Full name: `Timothy Weaving`, `Benjamin Blom`
- ❌ Never use PDF name if database has different spelling
- ❌ Never use nicknames (unless stored in database)

**Name Matching Process**:
1. Search `sas_id_personal` first (by SA ID, sail number history, and fuzzy name)
2. Use database name (corrects PDF spelling errors)
3. Only use PDF name if no match found

**Canonical Name Rule (MANDATORY)**:
- When an SA ID is found for a sailor (helm or crew), set `helm_name`/`crew_name` to the exact `full_name` from `sas_id_personal` — never a nickname and never the PDF text.
- Nicknames from `sas_id_personal.nickname` may be used for matching only, not stored in `results`.
- If the PDF shows a nickname or misspelling (e.g., “Jacqui”), store the canonical name from SA IDs (e.g., “Jacqueline”).
- This normalization happens immediately after staging and ID resolution and BEFORE commit to `results`.

---

### `helm_sa_sailing_id` (INTEGER)

**Format**: Numeric SA Sailing ID (no leading zeros)

**Rules**:
- ✅ Positive integer: `17427`, `25018`, `3709`
- ✅ No leading zeros: `17427` (NOT `017427`)
- ✅ Stored as INTEGER (not TEXT)
- ✅ Must exist in `sas_id_personal` if not NULL
- ❌ Never leading zeros: `017427` → `17427`
- ❌ Never store as text with zeros
- ❌ Never NULL if `helm_temp_id` is also NULL (must have one or the other)

**Normalization**: Always remove leading zeros before insert:
```sql
-- ✅ CORRECT - Remove leading zeros
CAST(TRIM(LEADING '0' FROM '017427') AS INTEGER)  -- Result: 17427
```

---

### `helm_temp_id` (TEXT)

**Format**: `TMP:X` where X is a number

**CRITICAL RULES**:
1. ✅ **Exact format**: `TMP:4`, `TMP:15`, `TMP:42`
2. ✅ **Uppercase `TMP`**
3. ✅ **Colon after `TMP`** (no space)
4. ✅ **No leading zeros in number**: `TMP:4` (NOT `TMP:04`)
5. ❌ **NEVER abbreviate**: `T4`, `tmp:4`, `TMP 4` are all WRONG
6. ❌ **NEVER lowercase**: `tmp:4` is WRONG
7. ❌ **NEVER space**: `TMP 4` is WRONG

**When to Use**:
- Only when sailor NOT found in `sas_id_personal` table
- Only after checking previous results and sail numbers
- Only with explicit approval (don't auto-create)

**Examples**:
```sql
-- ✅ CORRECT
'TMP:4', 'TMP:15', 'TMP:42'

-- ❌ WRONG - All variations
'T4', 'tmp:4', 'TMP 4', 'TMP:04', 'tmp:4'
```

---

### `crew_name`, `crew_sa_sailing_id`, `crew_temp_id`

**Same rules as helm fields** (see above).

---

## Post‑Staging Normalization (Names, IDs, Clubs) – REQUIRED

After rows are staged and before committing to `public.results`:

1. Resolve IDs (priority order):
   - a) Same regatta previous seasons (same fleet/class)  
   - b) All historical results (any class)  
   - c) `sas_id_personal` (including nickname assists)  
   - d) Only if still unknown: request TMP:X (never auto‑create)
2. Normalize names:
   - If SA ID found → overwrite `helm_name`/`crew_name` with `sas_id_personal.full_name` (canonical).
3. Set clubs:
   - `club_raw`/`club_id` = helm’s club from SA ID (`primary_club` then `club_1`);  
   - If helm club missing, use crew’s club; if both missing keep existing or map to `UNK`.
4. Validate classes:
   - Ensure `class_canonical` is a valid exact value from `classes.class_name` (e.g., `Hobie 16`, not `16`).

These steps are non‑negotiable and must run for every import.

### `club_raw` (TEXT)

**Format**: Club name as printed in results sheet

**Rules**:
- ✅ Preserve exactly as shown: `VLC/LDYC`, `SBYC`, `HYC`
- ✅ May contain multiple clubs: `VLC/LDYC` (preserve for reference)
- ✅ May contain province: `VLC (WC)`
- ❌ Never normalize here (that's what `club_id` is for)

---

### `club_id` (INTEGER, FK)

**Format**: Foreign key to `clubs.club_id`

**Rules**:
- ✅ Must exist in `clubs` table
- ✅ Resolve from `club_raw` during import
- ✅ If multiple clubs (e.g., `VLC/LDYC`), use FIRST club only
- ✅ Invalid clubs → map to `UNK` club
- ❌ Never NULL if sailor has a club
- ❌ Never use invalid club codes

**Club Code Validation**:
- Must be 3-4 letters, uppercase
- Must exist in `clubs` table
- Invalid → use `UNK` club_id

---

### `race_scores` (JSONB)

**Format**: JSON object with race keys `R1`, `R2`, `R3`, etc.

**PRE-ENTRY VALIDATION**: **MANDATORY** - Run validation script before data entry
- Script: `admin/tools/validate_race_scores_pre_entry.sql`
- Rules: `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md`
- **If validation fails, DO NOT enter data - fix source first**

**CRITICAL RULES**:

1. **Numeric Format**:
   - ✅ Always `.0` format: `"1.0"`, `"2.0"`, `"13.0"`
   - ❌ Never `"1"` or `"13"` - must have `.0`

2. **Discarded Scores**:
   - ✅ Must have brackets: `"(2.0)"`, `"(6.0)"`
   - ✅ No space inside brackets: `"(2.0)"` (NOT `"( 2.0 )"`)
   - ❌ Never unbracketed discards

3. **ISP Codes (Penalties)**:
   - ✅ Format: `"{score}.0 {CODE}"` - space between number and code
   - ✅ Examples: `"10.0 DNS"`, `"22.0 DNC"`, `"7.0 OCS"`
   - ✅ Discarded ISP: `"(10.0 DNS)"`, `"(22.0 DNC)"`
   - ✅ Score is MANDATORY - always include numeric score before code
   - ❌ Never `"DNS"` alone - must be `"{entries+1}.0 DNS"`
   - ❌ Never `"10.0DNS"` - must have space: `"10.0 DNS"`
   - ❌ Never `"10.0.0 DNS"` - remove double decimals: `"10.0 DNS"`

4. **Multiple Decimals**:
   - ❌ Never `"10.0.0"` or `"15.00.0"`
   - ✅ Fix to single decimal: `"10.0"`, `"15.0"`

**Example JSONB**:
```json
{
  "R1": "1.0",
  "R2": "(2.0)",
  "R3": "1.0",
  "R4": "10.0 DNC",
  "R5": "(10.0 DNS)",
  "R6": "2.0",
  "R7": "1.0",
  "R8": "1.0"
}
```

**Common Mistakes**:
- ❌ `"5"` → ✅ `"5.0"`
- ❌ `"2.0"` (unbracketed discard) → ✅ `"(2.0)"`
- ❌ `"DNS"` (no score) → ✅ `"10.0 DNS"`
- ❌ `"10.0DNS"` (no space) → ✅ `"10.0 DNS"`
- ❌ `"10.0.0 DNS"` (double decimal) → ✅ `"10.0 DNS"`

---

### `total_points_raw` (NUMERIC)

**Format**: Numeric with one decimal place

**Rules**:
- ✅ Always `.0` format: `15.0`, `23.0`, `45.0`
- ✅ Sum of ALL race scores (including discarded)
- ✅ Calculate from `race_scores` JSONB
- ❌ Never `15` or `23` - must be `15.0`, `23.0`
- ❌ Never `.00` format - use `.0`

**Calculation**:
- Sum all numeric values from `race_scores`
- Include discarded scores in total
- ISP codes: Use numeric score (e.g., `10.0 DNS` → `10.0`)

**Examples**:
```sql
-- ✅ CORRECT
15.0, 23.0, 45.0

-- ❌ WRONG
15, 23, 45 (missing .0)
15.00, 23.00 (wrong decimal places)
```

---

### `nett_points_raw` (NUMERIC)

**Format**: Numeric with one decimal place

**Rules**:
- ✅ Always `.0` format: `13.0`, `21.0`, `43.0`
- ✅ `total_points_raw - sum_of_discarded_scores`
- ✅ Must be < `total_points_raw` (unless no discards)
- ❌ Never `13` or `21` - must be `13.0`, `21.0`
- ❌ Never greater than `total_points_raw` (unless no discards)

**Validation**:
- `nett_points_raw = total_points_raw - sum_of_discards`
- If `discard_count = 0`, then `nett_points_raw = total_points_raw`

**Examples**:
```sql
-- ✅ CORRECT
13.0 (when total=15.0, discarded=2.0)
21.0 (when total=23.0, discarded=2.0)

-- ❌ WRONG
13, 21 (missing .0)
```

---

## HTML Compatibility Requirements

### Mandatory Checks for Every Column

Before entering data, verify:

1. **URL Safety**: If used in URLs → No quotes, spaces, special chars
2. **JavaScript Object Keys**: If used as JS keys → No quotes
3. **Data Attributes**: If used in HTML attributes → No quotes
4. **String Parsing**: If HTML uses `.split()` → Consistent format
5. **Display Format**: If HTML displays directly → Match expected format

### Known HTML Usage

**`regatta_id`**:
- Used in: Dropdown values, API URLs, string parsing
- Requirements: No quotes, URL-safe, single year, lowercase

**`block_id`**:
- Used in: JavaScript object keys, data attributes, API URLs
- Requirements: No quotes, colon separator, URL-safe

**`event_name` (in regattas table)**:
- Used in: Dropdown display `${year} ${event_name}`
- Requirements: Must NOT start with year (would create duplicate)

---

## Single Year Format Rule (MANDATORY)

**CRITICAL**: Any column containing year data must use **SINGLE YEAR ONLY**.

**Forbidden**:
- ❌ Double year: `2025-2025`
- ❌ Year range: `2025-2026`
- ❌ Year slash: `2025/2026`

**Required**:
- ✅ Single year: `2025`

**Applies to**: `regatta_id`, `block_id`, and any column with year patterns.

**Example**:
```sql
-- ✅ CORRECT - Single year
'342-2025-sas-mirror-national-championship'

-- ❌ WRONG - Double year
'342-2025-2025-sas-mirror-national-championship'
```

---

## No Duplications Rule (MANDATORY)

**CRITICAL**: Same logical value must have **IDENTICAL FORMAT** - no variations.

**Forbidden**:
- ❌ Format duplications: `'342-2025-...'` vs `342-2025-...` (same regatta, different quote format)
- ❌ Leading zero duplications: `'02798'` vs `'2798'` (same ID, different format)
- ❌ Case duplications: `342-2025-WCAP` vs `342-2025-wcap` (same regatta, different case)
- ❌ Separator duplications: `342-2025-...:mirror` vs `342-2025-...-mirror` (same block, different separator)

**Allowed**:
- ✅ Foreign key duplicates: Same `regatta_id` in `regattas` and `results` (FK relationship)
- ✅ Legitimate duplicates: Same sailor in multiple regattas (different `result_id`)

---

## Data Entry Process

### Step 1: Validate Before Insert

```sql
-- Validate regatta_id exists
SELECT regatta_id FROM public.regattas WHERE regatta_id = '342-2025-sas-mirror-national-championship';

-- Validate block_id exists
SELECT block_id FROM public.regatta_blocks WHERE block_id = '342-2025-sas-mirror-national-championship:mirror';

-- Validate club_id exists
SELECT club_id FROM public.clubs WHERE club_abbrev = 'SAS';

-- Validate class exists
SELECT class_name FROM public.classes WHERE class_name = 'Mirror';
```

### Step 2: Prepare Data

```sql
-- Remove leading zeros from SA ID
CAST(TRIM(LEADING '0' FROM '017427') AS INTEGER)  -- Result: 17427

-- Ensure class_canonical is populated (MANDATORY)
COALESCE(class_canonical, 'Mirror')  -- Never NULL

-- Ensure block_id uses colon separator
CONCAT(regatta_id, ':', fleet_slug)

-- Ensure race_scores has .0 format
'{"R1": "1.0", "R2": "(2.0)", "R3": "10.0 DNC"}'
```

### Step 3: INSERT Statement Template

```sql
INSERT INTO public.results (
    regatta_id,                    -- Single year format, lowercase, no quotes
    block_id,                      -- Full regatta_id: fleet-slug, colon separator, no quotes
    rank,                          -- Positive integer
    fleet_label,                   -- Actual fleet name (not "Overall")
    class_original,                -- Exact from PDF
    class_canonical,               -- Standardized, MANDATORY (never NULL)
    sail_number,                   -- Without country prefix
    helm_name,                     -- From database (authoritative)
    helm_sa_sailing_id,           -- Integer, no leading zeros
    helm_temp_id,                  -- TMP:X format if needed
    club_raw,                      -- As shown in PDF
    club_id,                       -- FK to clubs table
    race_scores,                   -- JSONB with .0 format, proper brackets, ISP codes
    total_points_raw,              -- Numeric with .0 (15.0, not 15)
    nett_points_raw                -- Numeric with .0 (13.0, not 13)
) VALUES (
    '342-2025-sas-mirror-national-championship',  -- Single year
    '342-2025-sas-mirror-national-championship:mirror',  -- Colon separator, no quotes
    1,
    'Mirror',                      -- Not "Overall"
    'MIRROR (D/H)',                -- Original from PDF
    'Mirror',                      -- Standardized, MANDATORY
    '3452',                        -- No RSA- prefix
    'Benjamin Blom',               -- From database
    17427,                         -- No leading zero
    NULL,                          -- Only if helm_sa_sailing_id is NULL
    'VLC',                         -- As in PDF
    42,                            -- Valid club_id
    '{"R1": "1.0", "R2": "(2.0)", "R3": "10.0 DNC"}'::jsonb,
    13.0,                          -- With .0
    11.0                           -- With .0
);
```

---

## Validation Queries (Run After Import)

```sql
-- Check for quotes in block_id
SELECT COUNT(*) FROM public.results WHERE block_id ~ '''';
-- Should return: 0

-- Check for double years
SELECT COUNT(*) FROM public.results WHERE block_id ~ '[0-9]+-[0-9]{4}-[0-9]{4}-';
-- Should return: 0

-- Check for missing class_canonical
SELECT COUNT(*) FROM public.results WHERE class_canonical IS NULL OR class_canonical = '';
-- Should return: 0

-- Check for missing fleet_label (if block has fleet)
SELECT COUNT(*) FROM public.results r
JOIN public.regatta_blocks rb ON rb.block_id = r.block_id
WHERE rb.fleet_label IS NOT NULL AND r.fleet_label IS NULL;
-- Should return: 0

-- Check for wrong separator in block_id
SELECT COUNT(*) FROM public.results WHERE block_id !~ ':';
-- Should return: 0 (all use colon)

-- Check numeric formats (should all have .0)
SELECT COUNT(*) FROM public.results 
WHERE total_points_raw::text !~ '\.0$' 
   OR nett_points_raw::text !~ '\.0$';
-- Should return: 0 (all have .0)
```

---

## Common Mistakes to Avoid

1. ❌ **Double year in regatta_id**: `342-2025-2025-...` → ✅ `342-2025-...`
2. ❌ **Quotes in block_id**: `'342-2025-...':mirror` → ✅ `342-2025-...:mirror`
3. ❌ **Missing class_canonical**: NULL → ✅ Must populate
4. ❌ **Missing full regatta_id in block_id**: `349-j22` → ✅ `349-2025-j22-nationals-results:j22`
5. ❌ **Hyphen separator**: `357-dabchick` → ✅ `357-2025-dabchick-gauteng-results:dabchick`
6. ❌ **Numeric without .0**: `15`, `23` → ✅ `15.0`, `23.0`
7. ❌ **ISP code without score**: `DNS` → ✅ `10.0 DNS`
8. ❌ **ISP code without space**: `10.0DNS` → ✅ `10.0 DNS`
9. ❌ **Double decimals**: `10.0.0 DNS` → ✅ `10.0 DNS`
10. ❌ **Event name starting with year**: `2025 Triple Crown` → ✅ `Triple Crown` (HTML adds year)

---

## Related Documents

- `docs/DATA_FORMAT_SPECIFICATIONS.md` - Complete format specs for all tables
- `docs/DATA_ENTRY_GUIDELINES.md` - Quick reference checklist
- `admin/audit/RESULTS_BLOCK_ID_RULES.md` - Detailed block_id rules
- `admin/audit/RESULTS_REGRATTA_ID_RULES.md` - Detailed regatta_id rules
- `admin/audit/HTML_DATA_FORMAT_VALIDATION.md` - HTML compatibility checklist

---

## Update History

- **2025-01-XX**: Created comprehensive standards based on audit findings
- Includes: Single year rule, no quotes rule, HTML compatibility, mandatory class_canonical


## Purpose
This document defines **ALL** data entry rules and format standards for the `public.results` table to ensure:
1. **HTML Compatibility** - Data format doesn't break HTML pages
2. **Consistency** - All data follows identical format patterns
3. **Data Integrity** - Foreign keys, constraints, and relationships maintained
4. **No Duplications** - Same logical value has identical format
5. **Single Year Format** - No double years anywhere

**CRITICAL**: These rules MUST be followed for ALL new data entry. Existing data has been standardized to these rules.

---

## Mandatory Checks Before Data Entry

### Pre-Entry Validation Checklist

- [ ] **HTML Compatibility**: Verify column format won't break HTML display
- [ ] **Single Year**: Check for double year patterns (`2025-2025` forbidden)
- [ ] **No Quotes**: Ensure no single quotes (`'`) in text fields
- [ ] **No Duplications**: Verify same logical value has identical format
- [ ] **Format Consistency**: All rows use same pattern
- [ ] **Foreign Keys**: Verify FK values exist in referenced tables
- [ ] **Race Scores Validation**: **MANDATORY** - Run `admin/tools/validate_race_scores_pre_entry.sql` before entry
  - All penalty codes must have scores (`"14.0 DNC"` not `"DNC"`)
  - All scores must have `.0` format (`"5.0"` not `"5"`)
  - All discards must use parentheses (`"(11.0)"` not `"-11.0"`)
  - See `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` for complete rules
- [ ] **Discard Brackets Compliance**: **MANDATORY** - Run `admin/tools/validate_discard_brackets_compliance.sql` after entry
  - `discard_count` must match number of bracketed scores
  - Worst scores must be discarded (per block discard rule)
  - Block rule "Discards: 2" = each sailor must have exactly 2 bracketed scores
  - See `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` section 10 for complete rules

---

## Column-by-Column Data Entry Rules

### `result_id` (BIGINT, PK, AUTO-INCREMENT)

**DO NOT SET MANUALLY** - Database auto-generates this value.

**Rules**:
- ✅ Always let database generate via `SERIAL`/sequence
- ❌ NEVER specify in INSERT statements
- ❌ NEVER manually set value
- ❌ NEVER use explicit numbers

**Example INSERT**:
```sql
-- ✅ CORRECT - Let database generate
INSERT INTO public.results (regatta_id, block_id, rank, ...) VALUES (...);

-- ❌ WRONG - Don't specify result_id
INSERT INTO public.results (result_id, regatta_id, ...) VALUES (123, ...);
```

---

### `regatta_id` (TEXT, NOT NULL, FK)

**Format**: `{regatta_number}-{year}-{club_code}-{event-slug}`

**CRITICAL RULES**:
1. ✅ **SINGLE YEAR ONLY** - `342-2025-sas-mirror-national-championship` (NOT `342-2025-2025-...`)
2. ✅ **Lowercase only** - `zvyc`, `sas`, `hyc`
3. ✅ **No quotes** - `342-2025-sas-mirror` (NOT `'342-2025-sas-mirror'`)
4. ✅ **No spaces** - Use hyphens
5. ✅ **Must exist in `regattas` table** (FK constraint)
6. ❌ **NEVER double year** - `2025-2025` is FORBIDDEN
7. ❌ **NEVER quotes** - Quotes break HTML URLs
8. ❌ **NEVER uppercase** - Breaks URL consistency

**HTML Usage**:
- Used in dropdown: `value="${r.regatta_id}"`
- Used in API calls: `fetch(\`${API}/api/regatta/${id}\`)`
- Used in string parsing: `.split('-')[0]` to extract regatta number

**Examples**:
```sql
-- ✅ CORRECT
'342-2025-sas-mirror-national-championship'

-- ❌ WRONG - Double year
'342-2025-2025-sas-mirror-national-championship'

-- ❌ WRONG - Has quotes
''342-2025-sas-mirror-national-championship''

-- ❌ WRONG - Uppercase
'342-2025-SAS-Mirror-National-Championship'
```

---

### `block_id` (TEXT, NOT NULL, FK)

**Format**: `{regatta_id}:{fleet-slug}`

**CRITICAL RULES**:
1. ✅ **SINGLE YEAR ONLY** in regatta_id portion
2. ✅ **Colon separator** (`:`) between regatta_id and fleet-slug
3. ✅ **No quotes** - `342-2025-sas-mirror:mirror` (NOT `'342-2025-sas-mirror':mirror`)
4. ✅ **Lowercase only**
5. ✅ **No spaces**
6. ✅ **Must exist in `regatta_blocks` table** (FK constraint)
7. ✅ **Complete format** - Must include full regatta_id (not just number-fleet)
8. ❌ **NEVER quotes** - Breaks JavaScript object keys: `by[r.block_id]` (invalid syntax)
9. ❌ **NEVER double year** - `2025-2025` is FORBIDDEN
10. ❌ **NEVER hyphen separator** - Must use colon `:`
11. ❌ **NEVER missing regatta_id parts** - Must have year, club, event-slug

**HTML Usage**:
- Used as JavaScript object key: `by[r.block_id]` (line 432 in regatta_viewer.html)
- Used in data attributes: `data-block-id="${h.block_id}"`
- Used in API calls: `/api/block/${td.dataset.blockId}`

**Examples**:
```sql
-- ✅ CORRECT - Full regatta_id + colon + fleet-slug
'342-2025-sas-mirror-national-championship:mirror'
'349-2025-j22-nationals-results:j22'
'357-2025-dabchick-gauteng-results:dabchick'

-- ❌ WRONG - Missing full regatta_id
'349-j22'  -- Missing: year, club, event-slug

-- ❌ WRONG - Has quotes (breaks JavaScript)
''342-2025-sas-mirror-national-championship':mirror'

-- ❌ WRONG - Double year
'339-2025-2025-wcapedinghychamps-results:optimist-a'

-- ❌ WRONG - Hyphen separator (should be colon)
'357-dabchick'
'343-2025-vasco-offshore'
```

**How to Build block_id**:
1. Get full `regatta_id` from `regattas` table: `SELECT regatta_id FROM regattas WHERE regatta_number = 349`
2. Get fleet-slug (lowercase, hyphens): `j22`, `optimist-a`, `multihull-fleet`
3. Combine with colon: `{regatta_id}:{fleet-slug}`

---

### `rank` (INTEGER)

**Format**: Whole number, positive integer

**Rules**:
- ✅ Positive integer (1, 2, 3, ...)
- ✅ Sequential within fleet/block (no gaps unless ISP-coded entries not ranked)
- ✅ Duplicates allowed if same `nett_points_raw` (legitimate ties)
- ⚠️ NULL allowed for DNS/DNC/DSQ entries that don't have final rank
- ❌ Never zero or negative
- ❌ Never decimals (INTEGER type enforces this)

**HTML Usage**: Displayed directly, formatted with ordinal (1st, 2nd, 3rd) - no transformation needed

**Examples**:
```sql
-- ✅ CORRECT
1, 2, 3, 15, 20  -- Normal ranks
4, 4, 4, 4, 4, 4  -- Legitimate ties (6 sailors tied for 4th, same nett_points_raw)

-- ✅ ACCEPTABLE
NULL  -- DNS/DNC entry without final rank

-- ❌ WRONG
0, -1, 1.5  -- Invalid values (INTEGER type prevents decimals)
```

**Audit Results**:
- ✅ 411/411 results have ranks (100% populated)
- ✅ All ranks valid (1-21 range)
- ✅ 1 block with legitimate ties (6 sailors tied for rank 4, same nett_points_raw)
- ⚠️ 1 block with gaps (may be intentional - DNS/DNC entries not ranked)

---

### `fleet_label` (TEXT, NOT NULL)

**Format**: Fleet designation as displayed (actual fleet name, NOT "Overall")

**CRITICAL RULES**:
- ✅ **MANDATORY FIELD** - Never NULL or empty
- ✅ Actual fleet name - `Optimist A`, `Open`, `Mirror`, `420` (NOT "Overall")
- ✅ Must match `regatta_blocks.fleet_label` for same block
- ✅ Consistent within block - All entries in same block must have identical `fleet_label`
- ✅ Title case or uppercase as appropriate: "Optimist A", "Open", "Mirror"
- ❌ **NEVER "Overall"** - Use actual fleet/class name
- ❌ **NEVER NULL or empty** - Critical field for grouping

**Checksum Validation**: 
- Run `admin/tools/checksum_fleet_label.sql` after import
- Verify all entries in block have same `fleet_label`
- Compare with PDF/results sheet
- **Manual Override**: For rare cases where PDF is wrong - see `docs/FLEET_LABEL_CHECKSUM_RULES.md`

**HTML Usage**: Displayed directly in results table (line 467)

**Examples**:
```sql
-- ✅ CORRECT
'Optimist A', 'Open', 'Mirror', '420', 'ILCA 6'

-- ❌ WRONG - Meaningless
'Overall'

-- ❌ WRONG - Missing
NULL, ''
```

**HTML Usage**: Displayed directly in results table

---

### `class_original` (TEXT, NOT NULL)

**Format**: Original class name from results sheet (exact copy from PDF)

**Data Source**: 
- **PDF/Results Sheet** - Extracted from:
  - Fleet header row (e.g., "OPTIMIST A FLEET")
  - Class column in results table
  - Fleet name section
- **Extraction Method**: Exact text copy - NO modifications

**CRITICAL RULES**:
- ✅ **Preserve exactly** as shown in PDF (exact copy)
- ✅ **Keep capitalization** from source: `OPTIMIST`, `MIRROR`, `ILCA 7`
- ✅ **Keep parenthetical notes**: `MIRROR (D/H)`, `EXTRA (S/H)`
- ✅ **Keep spaces**: `ILCA 7` (not `ILCA7`)
- ✅ **Keep formatting exactly** - never normalize
- ❌ **NEVER modify/standardize** - that's what `class_canonical` is for
- ❌ **NEVER guess** - if PDF doesn't show class, extract what's there

**Examples**:
```sql
-- PDF shows "MIRROR (D/H)" → class_original = 'MIRROR (D/H)'
-- PDF shows "OPTIMIST A" → class_original = 'OPTIMIST A'
-- PDF shows "ILCA 7" → class_original = 'ILCA 7'
-- PDF shows "29ER" → class_original = '29ER' (preserves PDF format)
```

**See**: `docs/CLASS_ORIGINAL_DATA_SOURCE.md` for complete explanation of data source.

**Examples**:
```sql
-- ✅ CORRECT - Preserve original
'OPTIMIST', '420', 'MIRROR (D/H)', 'ILCA 7', 'Dabchick'

-- ❌ WRONG - Don't standardize here
'Optimist' -- If original was 'OPTIMIST', keep it uppercase
```

---

### `class_canonical` (TEXT, NOT NULL)

**Format**: Standardized class name (validated from `classes` table)

**CRITICAL**: This is a MANDATORY field - NEVER leave empty.

**Data Source**: 
- **Validated from `classes.class_name` table** - MUST exist in `classes` table
- **Corrected during data entry** - If PDF shows wrong class, correct to valid class
- **HTML Display**: ✅ **ONLY valid class for HTML** - HTML must use this field

**CRITICAL RULES**:
- ✅ **MUST match `classes.class_name`** - Must exist in `classes` table
- ✅ **MUST be corrected** - If PDF shows wrong class (e.g., "Lazer 7"), correct to valid class ("ILCA 7")
- ✅ **MUST be validated** - Cannot use classes not in `classes` table
- ✅ Title case: `ILCA 7`, `Optimist`, `Dabchick`
- ✅ Consistent capitalization
- ✅ Spaces preserved: `ILCA 7` (not `ILCA7`)
- ✅ **MUST NOT be NULL or empty**
- ❌ Never mixed case: `Ilca 7` (use `ILCA 7`)
- ❌ Never lowercase: `ilca 7` (use `ILCA 7`)
- ❌ Never NULL or empty - **CRITICAL FIELD**
- ❌ Never use invalid classes - Must exist in `classes` table

**Validation Process**:
1. Extract `class_original` from PDF (exact copy)
2. **Validate against `classes.class_name` table** - Check if exists
3. **Use EXACT match** - Must match `classes.class_name` exactly (e.g., `Ilca 4.7` not `Ilca 4`)
4. If PDF is wrong → correct to valid class from `classes` table (e.g., PDF shows `ILCA 4` → use `Ilca 4.7`)
5. Store corrected class in `class_canonical`
6. HTML uses `class_canonical` (validated, corrected, exists in `classes` table)
7. **CRITICAL**: Invalid `class_canonical` breaks HTML filtering - results won't be found in search

**Why EXACT Match is Critical:**
- HTML filter/search uses `class_canonical` to group results
- If `Ilca 4` (invalid) vs `Ilca 4.7` (valid), they won't be grouped together
- Example: 10 ILCA 4.7 sailors, 5 have `Ilca 4` → only 5 found when filtering for "Ilca 4.7"

**HTML Usage**: 
- ✅ **ONLY field HTML should use** for class display
- ❌ **HTML must NOT use `class_original`** - PDF may contain errors, not validated
- Used in results table, grouping, filtering, sailor profiles

**Standard Values**:
- `ILCA 4`, `ILCA 6`, `ILCA 7` (not `Ilca 4` or `ilca 7`)
- `Optimist` (not `optimist` or `OPTIMIST`)
- `Dabchick`, `Mirror`, `420`, `505`, `29er`, `49er`

**Examples**:
```sql
-- ✅ CORRECT
'ILCA 7', 'Optimist', 'Dabchick', 'Mirror', '420'

-- ❌ WRONG - Inconsistent capitalization
'Ilca 7', 'ilca 7', 'ILCA7'

-- ❌ WRONG - Empty/NULL
NULL, ''
```

---

### `sail_number` (TEXT)

**Format**: Sail number as displayed

**Rules**:
- ✅ Preserve exactly as shown
- ✅ Remove country prefix: `RSA-3452` → `3452`
- ✅ Remove other prefixes: `GBR-5733R` → `5733R` (store prefix in `nationality` if available)
- ✅ Keep suffix: `5733R`, `123A`
- ❌ Never include country prefix: Don't store `RSA-3452`

**Examples**:
```sql
-- ✅ CORRECT
'3452', '5733R', '123A', '456'

-- ❌ WRONG - With prefix
'RSA-3452', 'GBR-5733R'
```

---

### `helm_name` (TEXT)

**Format**: Full name as in database

**Rules**:
- ✅ Use name from `sas_id_personal` table (authoritative source)
- ✅ Correct spelling errors from PDF using database
- ✅ Full name: `Timothy Weaving`, `Benjamin Blom`
- ❌ Never use PDF name if database has different spelling
- ❌ Never use nicknames (unless stored in database)

**Name Matching Process**:
1. Search `sas_id_personal` first
2. Use database name (corrects PDF spelling errors)
3. Only use PDF name if no match found

---

### `helm_sa_sailing_id` (INTEGER)

**Format**: Numeric SA Sailing ID (no leading zeros)

**Rules**:
- ✅ Positive integer: `17427`, `25018`, `3709`
- ✅ No leading zeros: `17427` (NOT `017427`)
- ✅ Stored as INTEGER (not TEXT)
- ✅ Must exist in `sas_id_personal` if not NULL
- ❌ Never leading zeros: `017427` → `17427`
- ❌ Never store as text with zeros
- ❌ Never NULL if `helm_temp_id` is also NULL (must have one or the other)

**Normalization**: Always remove leading zeros before insert:
```sql
-- ✅ CORRECT - Remove leading zeros
CAST(TRIM(LEADING '0' FROM '017427') AS INTEGER)  -- Result: 17427
```

---

### `helm_temp_id` (TEXT)

**Format**: `TMP:X` where X is a number

**CRITICAL RULES**:
1. ✅ **Exact format**: `TMP:4`, `TMP:15`, `TMP:42`
2. ✅ **Uppercase `TMP`**
3. ✅ **Colon after `TMP`** (no space)
4. ✅ **No leading zeros in number**: `TMP:4` (NOT `TMP:04`)
5. ❌ **NEVER abbreviate**: `T4`, `tmp:4`, `TMP 4` are all WRONG
6. ❌ **NEVER lowercase**: `tmp:4` is WRONG
7. ❌ **NEVER space**: `TMP 4` is WRONG

**When to Use**:
- Only when sailor NOT found in `sas_id_personal` table
- Only after checking previous results and sail numbers
- Only with explicit approval (don't auto-create)

**Examples**:
```sql
-- ✅ CORRECT
'TMP:4', 'TMP:15', 'TMP:42'

-- ❌ WRONG - All variations
'T4', 'tmp:4', 'TMP 4', 'TMP:04', 'tmp:4'
```

---

### `crew_name`, `crew_sa_sailing_id`, `crew_temp_id`

**Same rules as helm fields** (see above).

---

### `club_raw` (TEXT)

**Format**: Club name as printed in results sheet

**Rules**:
- ✅ Preserve exactly as shown: `VLC/LDYC`, `SBYC`, `HYC`
- ✅ May contain multiple clubs: `VLC/LDYC` (preserve for reference)
- ✅ May contain province: `VLC (WC)`
- ❌ Never normalize here (that's what `club_id` is for)

---

### `club_id` (INTEGER, FK)

**Format**: Foreign key to `clubs.club_id`

**Rules**:
- ✅ Must exist in `clubs` table
- ✅ Resolve from `club_raw` during import
- ✅ If multiple clubs (e.g., `VLC/LDYC`), use FIRST club only
- ✅ Invalid clubs → map to `UNK` club
- ❌ Never NULL if sailor has a club
- ❌ Never use invalid club codes

**Club Code Validation**:
- Must be 3-4 letters, uppercase
- Must exist in `clubs` table
- Invalid → use `UNK` club_id

---

### `race_scores` (JSONB)

**Format**: JSON object with race keys `R1`, `R2`, `R3`, etc.

**PRE-ENTRY VALIDATION**: **MANDATORY** - Run validation script before data entry
- Script: `admin/tools/validate_race_scores_pre_entry.sql`
- Rules: `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md`
- **If validation fails, DO NOT enter data - fix source first**

**CRITICAL RULES**:

1. **Numeric Format**:
   - ✅ Always `.0` format: `"1.0"`, `"2.0"`, `"13.0"`
   - ❌ Never `"1"` or `"13"` - must have `.0`

2. **Discarded Scores**:
   - ✅ Must have brackets: `"(2.0)"`, `"(6.0)"`
   - ✅ No space inside brackets: `"(2.0)"` (NOT `"( 2.0 )"`)
   - ❌ Never unbracketed discards

3. **ISP Codes (Penalties)**:
   - ✅ Format: `"{score}.0 {CODE}"` - space between number and code
   - ✅ Examples: `"10.0 DNS"`, `"22.0 DNC"`, `"7.0 OCS"`
   - ✅ Discarded ISP: `"(10.0 DNS)"`, `"(22.0 DNC)"`
   - ✅ Score is MANDATORY - always include numeric score before code
   - ❌ Never `"DNS"` alone - must be `"{entries+1}.0 DNS"`
   - ❌ Never `"10.0DNS"` - must have space: `"10.0 DNS"`
   - ❌ Never `"10.0.0 DNS"` - remove double decimals: `"10.0 DNS"`

4. **Multiple Decimals**:
   - ❌ Never `"10.0.0"` or `"15.00.0"`
   - ✅ Fix to single decimal: `"10.0"`, `"15.0"`

**Example JSONB**:
```json
{
  "R1": "1.0",
  "R2": "(2.0)",
  "R3": "1.0",
  "R4": "10.0 DNC",
  "R5": "(10.0 DNS)",
  "R6": "2.0",
  "R7": "1.0",
  "R8": "1.0"
}
```

**Common Mistakes**:
- ❌ `"5"` → ✅ `"5.0"`
- ❌ `"2.0"` (unbracketed discard) → ✅ `"(2.0)"`
- ❌ `"DNS"` (no score) → ✅ `"10.0 DNS"`
- ❌ `"10.0DNS"` (no space) → ✅ `"10.0 DNS"`
- ❌ `"10.0.0 DNS"` (double decimal) → ✅ `"10.0 DNS"`

---

### `total_points_raw` (NUMERIC)

**Format**: Numeric with one decimal place

**Rules**:
- ✅ Always `.0` format: `15.0`, `23.0`, `45.0`
- ✅ Sum of ALL race scores (including discarded)
- ✅ Calculate from `race_scores` JSONB
- ❌ Never `15` or `23` - must be `15.0`, `23.0`
- ❌ Never `.00` format - use `.0`

**Calculation**:
- Sum all numeric values from `race_scores`
- Include discarded scores in total
- ISP codes: Use numeric score (e.g., `10.0 DNS` → `10.0`)

**Examples**:
```sql
-- ✅ CORRECT
15.0, 23.0, 45.0

-- ❌ WRONG
15, 23, 45 (missing .0)
15.00, 23.00 (wrong decimal places)
```

---

### `nett_points_raw` (NUMERIC)

**Format**: Numeric with one decimal place

**Rules**:
- ✅ Always `.0` format: `13.0`, `21.0`, `43.0`
- ✅ `total_points_raw - sum_of_discarded_scores`
- ✅ Must be < `total_points_raw` (unless no discards)
- ❌ Never `13` or `21` - must be `13.0`, `21.0`
- ❌ Never greater than `total_points_raw` (unless no discards)

**Validation**:
- `nett_points_raw = total_points_raw - sum_of_discards`
- If `discard_count = 0`, then `nett_points_raw = total_points_raw`

**Examples**:
```sql
-- ✅ CORRECT
13.0 (when total=15.0, discarded=2.0)
21.0 (when total=23.0, discarded=2.0)

-- ❌ WRONG
13, 21 (missing .0)
```

---

## HTML Compatibility Requirements

### Mandatory Checks for Every Column

Before entering data, verify:

1. **URL Safety**: If used in URLs → No quotes, spaces, special chars
2. **JavaScript Object Keys**: If used as JS keys → No quotes
3. **Data Attributes**: If used in HTML attributes → No quotes
4. **String Parsing**: If HTML uses `.split()` → Consistent format
5. **Display Format**: If HTML displays directly → Match expected format

### Known HTML Usage

**`regatta_id`**:
- Used in: Dropdown values, API URLs, string parsing
- Requirements: No quotes, URL-safe, single year, lowercase

**`block_id`**:
- Used in: JavaScript object keys, data attributes, API URLs
- Requirements: No quotes, colon separator, URL-safe

**`event_name` (in regattas table)**:
- Used in: Dropdown display `${year} ${event_name}`
- Requirements: Must NOT start with year (would create duplicate)

---

## Single Year Format Rule (MANDATORY)

**CRITICAL**: Any column containing year data must use **SINGLE YEAR ONLY**.

**Forbidden**:
- ❌ Double year: `2025-2025`
- ❌ Year range: `2025-2026`
- ❌ Year slash: `2025/2026`

**Required**:
- ✅ Single year: `2025`

**Applies to**: `regatta_id`, `block_id`, and any column with year patterns.

**Example**:
```sql
-- ✅ CORRECT - Single year
'342-2025-sas-mirror-national-championship'

-- ❌ WRONG - Double year
'342-2025-2025-sas-mirror-national-championship'
```

---

## No Duplications Rule (MANDATORY)

**CRITICAL**: Same logical value must have **IDENTICAL FORMAT** - no variations.

**Forbidden**:
- ❌ Format duplications: `'342-2025-...'` vs `342-2025-...` (same regatta, different quote format)
- ❌ Leading zero duplications: `'02798'` vs `'2798'` (same ID, different format)
- ❌ Case duplications: `342-2025-WCAP` vs `342-2025-wcap` (same regatta, different case)
- ❌ Separator duplications: `342-2025-...:mirror` vs `342-2025-...-mirror` (same block, different separator)

**Allowed**:
- ✅ Foreign key duplicates: Same `regatta_id` in `regattas` and `results` (FK relationship)
- ✅ Legitimate duplicates: Same sailor in multiple regattas (different `result_id`)

---

## Data Entry Process

### Step 1: Validate Before Insert

```sql
-- Validate regatta_id exists
SELECT regatta_id FROM public.regattas WHERE regatta_id = '342-2025-sas-mirror-national-championship';

-- Validate block_id exists
SELECT block_id FROM public.regatta_blocks WHERE block_id = '342-2025-sas-mirror-national-championship:mirror';

-- Validate club_id exists
SELECT club_id FROM public.clubs WHERE club_abbrev = 'SAS';

-- Validate class exists
SELECT class_name FROM public.classes WHERE class_name = 'Mirror';
```

### Step 2: Prepare Data

```sql
-- Remove leading zeros from SA ID
CAST(TRIM(LEADING '0' FROM '017427') AS INTEGER)  -- Result: 17427

-- Ensure class_canonical is populated (MANDATORY)
COALESCE(class_canonical, 'Mirror')  -- Never NULL

-- Ensure block_id uses colon separator
CONCAT(regatta_id, ':', fleet_slug)

-- Ensure race_scores has .0 format
'{"R1": "1.0", "R2": "(2.0)", "R3": "10.0 DNC"}'
```

### Step 3: INSERT Statement Template

```sql
INSERT INTO public.results (
    regatta_id,                    -- Single year format, lowercase, no quotes
    block_id,                      -- Full regatta_id: fleet-slug, colon separator, no quotes
    rank,                          -- Positive integer
    fleet_label,                   -- Actual fleet name (not "Overall")
    class_original,                -- Exact from PDF
    class_canonical,               -- Standardized, MANDATORY (never NULL)
    sail_number,                   -- Without country prefix
    helm_name,                     -- From database (authoritative)
    helm_sa_sailing_id,           -- Integer, no leading zeros
    helm_temp_id,                  -- TMP:X format if needed
    club_raw,                      -- As shown in PDF
    club_id,                       -- FK to clubs table
    race_scores,                   -- JSONB with .0 format, proper brackets, ISP codes
    total_points_raw,              -- Numeric with .0 (15.0, not 15)
    nett_points_raw                -- Numeric with .0 (13.0, not 13)
) VALUES (
    '342-2025-sas-mirror-national-championship',  -- Single year
    '342-2025-sas-mirror-national-championship:mirror',  -- Colon separator, no quotes
    1,
    'Mirror',                      -- Not "Overall"
    'MIRROR (D/H)',                -- Original from PDF
    'Mirror',                      -- Standardized, MANDATORY
    '3452',                        -- No RSA- prefix
    'Benjamin Blom',               -- From database
    17427,                         -- No leading zero
    NULL,                          -- Only if helm_sa_sailing_id is NULL
    'VLC',                         -- As in PDF
    42,                            -- Valid club_id
    '{"R1": "1.0", "R2": "(2.0)", "R3": "10.0 DNC"}'::jsonb,
    13.0,                          -- With .0
    11.0                           -- With .0
);
```

---

## Validation Queries (Run After Import)

```sql
-- Check for quotes in block_id
SELECT COUNT(*) FROM public.results WHERE block_id ~ '''';
-- Should return: 0

-- Check for double years
SELECT COUNT(*) FROM public.results WHERE block_id ~ '[0-9]+-[0-9]{4}-[0-9]{4}-';
-- Should return: 0

-- Check for missing class_canonical
SELECT COUNT(*) FROM public.results WHERE class_canonical IS NULL OR class_canonical = '';
-- Should return: 0

-- Check for missing fleet_label (if block has fleet)
SELECT COUNT(*) FROM public.results r
JOIN public.regatta_blocks rb ON rb.block_id = r.block_id
WHERE rb.fleet_label IS NOT NULL AND r.fleet_label IS NULL;
-- Should return: 0

-- Check for wrong separator in block_id
SELECT COUNT(*) FROM public.results WHERE block_id !~ ':';
-- Should return: 0 (all use colon)

-- Check numeric formats (should all have .0)
SELECT COUNT(*) FROM public.results 
WHERE total_points_raw::text !~ '\.0$' 
   OR nett_points_raw::text !~ '\.0$';
-- Should return: 0 (all have .0)
```

---

## Common Mistakes to Avoid

1. ❌ **Double year in regatta_id**: `342-2025-2025-...` → ✅ `342-2025-...`
2. ❌ **Quotes in block_id**: `'342-2025-...':mirror` → ✅ `342-2025-...:mirror`
3. ❌ **Missing class_canonical**: NULL → ✅ Must populate
4. ❌ **Missing full regatta_id in block_id**: `349-j22` → ✅ `349-2025-j22-nationals-results:j22`
5. ❌ **Hyphen separator**: `357-dabchick` → ✅ `357-2025-dabchick-gauteng-results:dabchick`
6. ❌ **Numeric without .0**: `15`, `23` → ✅ `15.0`, `23.0`
7. ❌ **ISP code without score**: `DNS` → ✅ `10.0 DNS`
8. ❌ **ISP code without space**: `10.0DNS` → ✅ `10.0 DNS`
9. ❌ **Double decimals**: `10.0.0 DNS` → ✅ `10.0 DNS`
10. ❌ **Event name starting with year**: `2025 Triple Crown` → ✅ `Triple Crown` (HTML adds year)

---

## Related Documents

- `docs/DATA_FORMAT_SPECIFICATIONS.md` - Complete format specs for all tables
- `docs/DATA_ENTRY_GUIDELINES.md` - Quick reference checklist
- `admin/audit/RESULTS_BLOCK_ID_RULES.md` - Detailed block_id rules
- `admin/audit/RESULTS_REGRATTA_ID_RULES.md` - Detailed regatta_id rules
- `admin/audit/HTML_DATA_FORMAT_VALIDATION.md` - HTML compatibility checklist

---

## Update History

- **2025-01-XX**: Created comprehensive standards based on audit findings
- Includes: Single year rule, no quotes rule, HTML compatibility, mandatory class_canonical












