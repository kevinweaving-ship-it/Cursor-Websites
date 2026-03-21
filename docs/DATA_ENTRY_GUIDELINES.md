# Data Entry Guidelines - Quick Reference

## Before You Start

**READ FIRST**: `docs/DATA_FORMAT_SPECIFICATIONS.md` - Complete format requirements for every column.

## Quick Checklist for Data Import

### 1. Pre-Import Validation

- [ ] Club codes exist in `clubs` table (uppercase, 3-4 letters)
- [ ] Class names match `classes.class_name` format
- [ ] SA IDs normalized (no leading zeros)
- [ ] Dates in ISO format (YYYY-MM-DD)
- [ ] Timestamps with timezone

### 2. Race Scores Format

**CRITICAL - Must be exact**:
- Normal: `"1.0"`, `"2.0"`, `"13.0"`
- Discarded: `"(2.0)"`, `"(6.0)"`
- ISP code: `"10.0 DNS"`, `"22.0 DNC"` (space between number and code)
- Discarded ISP: `"(10.0 DNS)"`, `"(22.0 DNC)"`

**NEVER**:
- ❌ `5.00` (use `5.0`)
- ❌ `10.0.0 DNS` (use `10.0 DNS`)
- ❌ `10.0DNS` (use `10.0 DNS` with space)
- ❌ `(10.0 DNS` (use `(10.0 DNS)` with closing paren)

### 3. Numeric Fields

- All decimal values: **Always `.0` format**
- `total_points_raw`: `10.0` (not `10` or `10.00`)
- `nett_points_raw`: `8.0` (not `8` or `8.00`)

### 4. SA ID Format

- **No leading zeros**: `17427` (not `017427`)
- **Stored as integer** in `results` table
- **Stored as text** in `sas_id_personal` (without leading zeros)

### 5. Temp ID Format

- **Exact format**: `TMP:4` (not `T4` or `tmp:4`)
- Colon and space after `TMP`

### 6. Club Codes

- **Uppercase**: `ZVYC` (not `zvyc` or `Zvyc`)
- **Single club**: If PDF shows "VLC/LDYC", use `VLC` only
- **Must exist** in `clubs` table

### 7. Class Names

- **Title case**: `ILCA 7` (not `ilca 7` or `ILCA7`)
- **Match classes table**: Must exist in `classes.class_name`
- **Spaces preserved**: `ILCA 7` has space (not `ILCA7`)

## Common Mistakes to Avoid

1. **Double decimals**: `10.0.0` → `10.0`
2. **Wrong decimal places**: `5.00` → `5.0`
3. **Missing space in ISP codes**: `10.0DNS` → `10.0 DNS`
4. **Wrong brackets**: Discarded scores MUST have brackets `(2.0)`
5. **Leading zeros in SA IDs**: `017427` → `17427`
6. **Lowercase club codes**: `zvyc` → `ZVYC`
7. **Multiple clubs**: `VLC/LDYC` → `VLC` (first only)

## Entry Count Checksum (MANDATORY)

**CRITICAL**: After importing data for each block/fleet, verify entry count matches PDF:

```sql
-- Count actual entries for a block
SELECT COUNT(*) as actual_entry_count
FROM public.results
WHERE block_id = 'your-block-id-here';

-- Compare with PDF count
-- Expected: 15 entries (from PDF)
-- Actual: Must match
```

**See**: `docs/ENTRY_COUNT_CHECKSUM_RULES.md` for complete checksum process.

### Fleet Label Checksum (MANDATORY)

**CRITICAL**: After importing data for each block/fleet, verify `fleet_label` matches PDF:

```sql
-- Check fleet_label consistency within block
SELECT DISTINCT fleet_label, COUNT(*)
FROM public.results
WHERE block_id = 'your-block-id-here'
GROUP BY fleet_label;

-- Expected: Only one fleet_label value, matches PDF
-- If multiple values or NULL: ❌ ERROR
```

**Rules**:
- ✅ All entries in same block must have identical `fleet_label`
- ✅ Must match PDF/results sheet (or manual override if PDF wrong)
- ❌ Never use "Overall" - use actual fleet name
- ❌ Never NULL or empty - mandatory field

**See**: `docs/FLEET_LABEL_CHECKSUM_RULES.md` for complete checksum process and manual override.

## Validation Queries

After import, run these to check:

```sql
-- Check for double decimals
SELECT COUNT(*) FROM results WHERE race_scores::text LIKE '%.0.0%';
-- Should return 0

-- Check for .00 patterns
SELECT COUNT(*) FROM results WHERE race_scores::text ~ '[0-9]\.00[^0-9]';
-- Should return 0

-- Check for missing spaces in ISP codes
SELECT COUNT(*) FROM results 
WHERE race_scores::text ~ '[0-9]\.[0-9][A-Z]';
-- Should return 0 (ISP codes should have space: "10.0 DNS")

-- Check for leading zeros in SA IDs (if stored as text)
SELECT COUNT(*) FROM sas_id_personal 
WHERE sa_sailing_id ~ '^0[0-9]';
-- Should return 0

-- Check club code format
SELECT DISTINCT club_raw FROM results 
WHERE club_raw != UPPER(club_raw);
-- Should return empty (all uppercase)
```

## Validation Scripts

Run these after import:

1. **Entry count checksum**: `admin/tools/checksum_entry_counts.sql` - **MANDATORY**
2. **Total/Nett checksum**: `audit_regatta.py` - Validates score calculations

## Format Fix Scripts

If you find issues, run:

1. **ISP code format**: `admin/tools/fix_isp_code_format.sql`
2. **Numeric format**: `admin/tools/fix_numeric_format_consistency.sql`
3. **SA ID format**: `admin/tools/fix_sa_id_duplicates_final.sql`

## HTML Display

**Remember**: HTML displays data **directly** from database without transformations. If it looks wrong in HTML, **fix the database**, not the HTML code.

## Questions?

Refer to `docs/DATA_FORMAT_SPECIFICATIONS.md` for complete details on every column.


## Before You Start

**READ FIRST**: `docs/DATA_FORMAT_SPECIFICATIONS.md` - Complete format requirements for every column.

## Quick Checklist for Data Import

### 1. Pre-Import Validation

- [ ] Club codes exist in `clubs` table (uppercase, 3-4 letters)
- [ ] Class names match `classes.class_name` format
- [ ] SA IDs normalized (no leading zeros)
- [ ] Dates in ISO format (YYYY-MM-DD)
- [ ] Timestamps with timezone

### 2. Race Scores Format

**CRITICAL - Must be exact**:
- Normal: `"1.0"`, `"2.0"`, `"13.0"`
- Discarded: `"(2.0)"`, `"(6.0)"`
- ISP code: `"10.0 DNS"`, `"22.0 DNC"` (space between number and code)
- Discarded ISP: `"(10.0 DNS)"`, `"(22.0 DNC)"`

**NEVER**:
- ❌ `5.00` (use `5.0`)
- ❌ `10.0.0 DNS` (use `10.0 DNS`)
- ❌ `10.0DNS` (use `10.0 DNS` with space)
- ❌ `(10.0 DNS` (use `(10.0 DNS)` with closing paren)

### 3. Numeric Fields

- All decimal values: **Always `.0` format**
- `total_points_raw`: `10.0` (not `10` or `10.00`)
- `nett_points_raw`: `8.0` (not `8` or `8.00`)

### 4. SA ID Format

- **No leading zeros**: `17427` (not `017427`)
- **Stored as integer** in `results` table
- **Stored as text** in `sas_id_personal` (without leading zeros)

### 5. Temp ID Format

- **Exact format**: `TMP:4` (not `T4` or `tmp:4`)
- Colon and space after `TMP`

### 6. Club Codes

- **Uppercase**: `ZVYC` (not `zvyc` or `Zvyc`)
- **Single club**: If PDF shows "VLC/LDYC", use `VLC` only
- **Must exist** in `clubs` table

### 7. Class Names

- **Title case**: `ILCA 7` (not `ilca 7` or `ILCA7`)
- **Match classes table**: Must exist in `classes.class_name`
- **Spaces preserved**: `ILCA 7` has space (not `ILCA7`)

## Common Mistakes to Avoid

1. **Double decimals**: `10.0.0` → `10.0`
2. **Wrong decimal places**: `5.00` → `5.0`
3. **Missing space in ISP codes**: `10.0DNS` → `10.0 DNS`
4. **Wrong brackets**: Discarded scores MUST have brackets `(2.0)`
5. **Leading zeros in SA IDs**: `017427` → `17427`
6. **Lowercase club codes**: `zvyc` → `ZVYC`
7. **Multiple clubs**: `VLC/LDYC` → `VLC` (first only)

## Entry Count Checksum (MANDATORY)

**CRITICAL**: After importing data for each block/fleet, verify entry count matches PDF:

```sql
-- Count actual entries for a block
SELECT COUNT(*) as actual_entry_count
FROM public.results
WHERE block_id = 'your-block-id-here';

-- Compare with PDF count
-- Expected: 15 entries (from PDF)
-- Actual: Must match
```

**See**: `docs/ENTRY_COUNT_CHECKSUM_RULES.md` for complete checksum process.

### Fleet Label Checksum (MANDATORY)

**CRITICAL**: After importing data for each block/fleet, verify `fleet_label` matches PDF:

```sql
-- Check fleet_label consistency within block
SELECT DISTINCT fleet_label, COUNT(*)
FROM public.results
WHERE block_id = 'your-block-id-here'
GROUP BY fleet_label;

-- Expected: Only one fleet_label value, matches PDF
-- If multiple values or NULL: ❌ ERROR
```

**Rules**:
- ✅ All entries in same block must have identical `fleet_label`
- ✅ Must match PDF/results sheet (or manual override if PDF wrong)
- ❌ Never use "Overall" - use actual fleet name
- ❌ Never NULL or empty - mandatory field

**See**: `docs/FLEET_LABEL_CHECKSUM_RULES.md` for complete checksum process and manual override.

## Validation Queries

After import, run these to check:

```sql
-- Check for double decimals
SELECT COUNT(*) FROM results WHERE race_scores::text LIKE '%.0.0%';
-- Should return 0

-- Check for .00 patterns
SELECT COUNT(*) FROM results WHERE race_scores::text ~ '[0-9]\.00[^0-9]';
-- Should return 0

-- Check for missing spaces in ISP codes
SELECT COUNT(*) FROM results 
WHERE race_scores::text ~ '[0-9]\.[0-9][A-Z]';
-- Should return 0 (ISP codes should have space: "10.0 DNS")

-- Check for leading zeros in SA IDs (if stored as text)
SELECT COUNT(*) FROM sas_id_personal 
WHERE sa_sailing_id ~ '^0[0-9]';
-- Should return 0

-- Check club code format
SELECT DISTINCT club_raw FROM results 
WHERE club_raw != UPPER(club_raw);
-- Should return empty (all uppercase)
```

## Validation Scripts

Run these after import:

1. **Entry count checksum**: `admin/tools/checksum_entry_counts.sql` - **MANDATORY**
2. **Total/Nett checksum**: `audit_regatta.py` - Validates score calculations

## Format Fix Scripts

If you find issues, run:

1. **ISP code format**: `admin/tools/fix_isp_code_format.sql`
2. **Numeric format**: `admin/tools/fix_numeric_format_consistency.sql`
3. **SA ID format**: `admin/tools/fix_sa_id_duplicates_final.sql`

## HTML Display

**Remember**: HTML displays data **directly** from database without transformations. If it looks wrong in HTML, **fix the database**, not the HTML code.

## Questions?

Refer to `docs/DATA_FORMAT_SPECIFICATIONS.md` for complete details on every column.

