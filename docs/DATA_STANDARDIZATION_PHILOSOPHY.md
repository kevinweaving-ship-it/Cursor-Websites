# Data Standardization Philosophy

## Core Principle

**Fix data in the database, not in HTML/API code. HTML displays raw values directly.**

## Why This Approach?

1. **Consistency**: All data in database matches format requirements
2. **Reliability**: No risk of transformation bugs in HTML/API
3. **Performance**: No processing needed at display time
4. **Maintainability**: Single source of truth (database)
5. **Debugging**: Issues visible in database, not hidden in code

## Standard Format Requirements

All data must be entered/stored in the **exact format** HTML expects. See `docs/DATA_FORMAT_SPECIFICATIONS.md` for complete details.

### Key Standards

1. **ISP Codes**: ALWAYS `"number.0 CODE"` (e.g., `"7.0 DNC"`, never just `"DNC"`)
2. **Decimals**: ALWAYS `.0` format (e.g., `"5.0"`, never `"5.00"` or `"5.0.0"`)
3. **Discarded scores**: ALWAYS wrapped in parentheses `"(2.0)"`
4. **SA IDs**: NO leading zeros (e.g., `17427`, not `017427`)
5. **Dates**: ISO format `YYYY-MM-DD`
6. **Timestamps**: ISO 8601 with timezone

## HTML Display Rules

HTML (`regatta_viewer.html`, `member-finder.html`) displays values **directly** from database:

```javascript
// Line 475-477 in regatta_viewer.html
const v = (r.race_scores && r.race_scores[k]) || '';
return `<td>${v}</td>`;
```

**NO transformations** except:
- Numeric formatting for display (`.toFixed(1)`) - but database already has correct format
- CSS classes based on patterns (for styling, not data changes)

## Checksum Rules

### Database Level Checksums

All validation/checksums done at **database level**:

1. **Total Points**: Calculated from `race_scores` JSONB sum
2. **Nett Points**: Calculated as total - discarded scores
3. **Discard Validation**: Verify discard_count matches bracketed scores
4. **Format Validation**: Verify all formats match specifications

### Scripts for Validation

Run these scripts after import to verify data:

1. **ISP Code Format**: `admin/tools/fix_isp_code_format.sql`
2. **ISP Codes with Scores**: `admin/tools/fix_isp_codes_with_scores.sql`
3. **Discard Brackets**: `admin/tools/fix_discard_brackets.sql`
4. **Numeric Format**: `admin/tools/fix_numeric_format_consistency.sql`

### HTML Level

HTML **does not perform checksums**. HTML only:
- Displays values from database
- Applies CSS classes based on patterns
- Formats numbers for display (if needed)

## Data Entry Process

### Step 1: Import Raw Data
- Extract from source (PDF, screenshot)
- Insert into database with minimal transformation

### Step 2: Standardize Format
- Run format fix scripts
- Ensure all formats match specifications

### Step 3: Validate
- Run checksum scripts
- Verify totals/nett calculations
- Verify discard brackets

### Step 4: Display
- HTML displays directly - no modifications needed
- All values should appear correctly

## Example: ISP Code Standardization

### Wrong (Inconsistent)
```
"R1": "DNC"           ← Missing score
"R2": "7.0 DNC"       ← Has score
"R3": "(DSQ)"         ← Missing score, has brackets
"R4": "(7.0 DSQ)"     ← Correct
```

### Correct (Standardized)
```
"R1": "7.0 DNC"       ← Always has score
"R2": "7.0 DNC"       ← Always has score
"R3": "(7.0 DSQ)"     ← Always has score, brackets if discarded
"R4": "(7.0 DSQ)"     ← Always has score, brackets if discarded
```

## Benefits of This Approach

1. **Predictable**: Always know what format data is in
2. **Debuggable**: Issues visible in database queries
3. **Consistent**: Same format everywhere
4. **Maintainable**: Fix once in database, works everywhere
5. **Reliable**: No risk of HTML transformation bugs

## Rules to Follow

1. ✅ **Fix data in database** when format is wrong
2. ✅ **HTML displays raw values** directly
3. ✅ **Run format fix scripts** after import
4. ✅ **Validate with checksums** at database level
5. ❌ **Never transform data** in HTML/API code
6. ❌ **Never assume HTML will fix** format issues

## Reference Documents

- `docs/DATA_FORMAT_SPECIFICATIONS.md` - Complete format requirements
- `docs/DATA_ENTRY_GUIDELINES.md` - Quick reference checklist
- `docs/FLEET_CLASS_HIERARCHY.md` - Fleet/class structure rules
- `admin/tools/fix_*.sql` - Format standardization scripts



## Core Principle

**Fix data in the database, not in HTML/API code. HTML displays raw values directly.**

## Why This Approach?

1. **Consistency**: All data in database matches format requirements
2. **Reliability**: No risk of transformation bugs in HTML/API
3. **Performance**: No processing needed at display time
4. **Maintainability**: Single source of truth (database)
5. **Debugging**: Issues visible in database, not hidden in code

## Standard Format Requirements

All data must be entered/stored in the **exact format** HTML expects. See `docs/DATA_FORMAT_SPECIFICATIONS.md` for complete details.

### Key Standards

1. **ISP Codes**: ALWAYS `"number.0 CODE"` (e.g., `"7.0 DNC"`, never just `"DNC"`)
2. **Decimals**: ALWAYS `.0` format (e.g., `"5.0"`, never `"5.00"` or `"5.0.0"`)
3. **Discarded scores**: ALWAYS wrapped in parentheses `"(2.0)"`
4. **SA IDs**: NO leading zeros (e.g., `17427`, not `017427`)
5. **Dates**: ISO format `YYYY-MM-DD`
6. **Timestamps**: ISO 8601 with timezone

## HTML Display Rules

HTML (`regatta_viewer.html`, `member-finder.html`) displays values **directly** from database:

```javascript
// Line 475-477 in regatta_viewer.html
const v = (r.race_scores && r.race_scores[k]) || '';
return `<td>${v}</td>`;
```

**NO transformations** except:
- Numeric formatting for display (`.toFixed(1)`) - but database already has correct format
- CSS classes based on patterns (for styling, not data changes)

## Checksum Rules

### Database Level Checksums

All validation/checksums done at **database level**:

1. **Total Points**: Calculated from `race_scores` JSONB sum
2. **Nett Points**: Calculated as total - discarded scores
3. **Discard Validation**: Verify discard_count matches bracketed scores
4. **Format Validation**: Verify all formats match specifications

### Scripts for Validation

Run these scripts after import to verify data:

1. **ISP Code Format**: `admin/tools/fix_isp_code_format.sql`
2. **ISP Codes with Scores**: `admin/tools/fix_isp_codes_with_scores.sql`
3. **Discard Brackets**: `admin/tools/fix_discard_brackets.sql`
4. **Numeric Format**: `admin/tools/fix_numeric_format_consistency.sql`

### HTML Level

HTML **does not perform checksums**. HTML only:
- Displays values from database
- Applies CSS classes based on patterns
- Formats numbers for display (if needed)

## Data Entry Process

### Step 1: Import Raw Data
- Extract from source (PDF, screenshot)
- Insert into database with minimal transformation

### Step 2: Standardize Format
- Run format fix scripts
- Ensure all formats match specifications

### Step 3: Validate
- Run checksum scripts
- Verify totals/nett calculations
- Verify discard brackets

### Step 4: Display
- HTML displays directly - no modifications needed
- All values should appear correctly

## Example: ISP Code Standardization

### Wrong (Inconsistent)
```
"R1": "DNC"           ← Missing score
"R2": "7.0 DNC"       ← Has score
"R3": "(DSQ)"         ← Missing score, has brackets
"R4": "(7.0 DSQ)"     ← Correct
```

### Correct (Standardized)
```
"R1": "7.0 DNC"       ← Always has score
"R2": "7.0 DNC"       ← Always has score
"R3": "(7.0 DSQ)"     ← Always has score, brackets if discarded
"R4": "(7.0 DSQ)"     ← Always has score, brackets if discarded
```

## Benefits of This Approach

1. **Predictable**: Always know what format data is in
2. **Debuggable**: Issues visible in database queries
3. **Consistent**: Same format everywhere
4. **Maintainable**: Fix once in database, works everywhere
5. **Reliable**: No risk of HTML transformation bugs

## Rules to Follow

1. ✅ **Fix data in database** when format is wrong
2. ✅ **HTML displays raw values** directly
3. ✅ **Run format fix scripts** after import
4. ✅ **Validate with checksums** at database level
5. ❌ **Never transform data** in HTML/API code
6. ❌ **Never assume HTML will fix** format issues

## Reference Documents

- `docs/DATA_FORMAT_SPECIFICATIONS.md` - Complete format requirements
- `docs/DATA_ENTRY_GUIDELINES.md` - Quick reference checklist
- `docs/FLEET_CLASS_HIERARCHY.md` - Fleet/class structure rules
- `admin/tools/fix_*.sql` - Format standardization scripts


















