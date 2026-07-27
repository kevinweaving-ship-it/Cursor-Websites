# RACE_SCORES DATA ENTRY VALIDATION - MANDATORY CHECKS

## Purpose
This document defines **MANDATORY validation rules** that MUST be checked **BEFORE** any race_scores data is entered into the database. Data that fails validation **MUST BE REJECTED** and fixed before entry.

---

## VALIDATION RULES (HARD STOPS)

### Rule 1: Penalty Codes MUST Include Scores
**Status**: ❌ **HARD STOP - REJECT DATA**

**Invalid Examples** (DO NOT ACCEPT):
- `"DNC"` - missing score
- `"DNS"` - missing score  
- `"OCS"` - missing score

**Valid Format** (REQUIRED):
- `"14.0 DNC"` - score + space + code
- Score = `entries + 1` for penalty codes
- Example: 13 entries → DNC = `"14.0 DNC"`

**Validation Query**:
```sql
-- Flag any penalty code without numeric score
WHERE value ~ '\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b' 
  AND value !~ '^[0-9]'
```

**Action**: If found → **REJECT DATA** → Fix source → Re-validate

---

### Rule 2: All Numeric Scores MUST Have .0 Format
**Status**: ❌ **HARD STOP - REJECT DATA**

**Invalid Examples** (DO NOT ACCEPT):
- `"5"` - missing .0
- `"13"` - missing .0
- `"1.00"` - wrong decimal places

**Valid Format** (REQUIRED):
- `"5.0"` - single .0 decimal
- `"13.0"` - single .0 decimal

**Validation Query**:
```sql
-- Flag integers or wrong decimals
WHERE value ~ '^[0-9]+$'  -- Integer only
   OR value ~ '^[0-9]+\.[0-9][0-9]+[^0-9]'  -- Too many decimals
```

**Action**: If found → **REJECT DATA** → Fix format → Re-validate

---

### Rule 3: Discards MUST Use Parentheses
**Status**: ❌ **HARD STOP - REJECT DATA**

**Invalid Examples** (DO NOT ACCEPT):
- `"-11.0"` - minus sign (from source sheet)
- `"11.0"` - missing parentheses when discard

**Valid Format** (REQUIRED):
- `"(11.0)"` - parentheses for discards
- `"(14.0 DNC)"` - parentheses for discarded penalties

**Validation Query**:
```sql
-- Flag minus signs (should be parentheses)
WHERE value ~ '^-'
```

**Action**: If found → **REJECT DATA** → Transform source format → Re-validate

---

### Rule 4: Discard Count MUST Match Bracketed Scores
**Status**: ❌ **HARD STOP - REJECT DATA** (Post-Entry Check)

**Rule**: After entering race_scores, `discard_count` MUST equal number of bracketed scores.

**Invalid Examples** (DO NOT ACCEPT):
- `discard_count = 2` but only 1 bracketed score → **ERROR**
- Block rule "Discards: 2" but sailor has 0 discards → **ERROR**
- `discard_count = 1` but 0 bracketed scores → **ERROR**

**Valid Format** (REQUIRED):
- Block rule "Discards: 2" = each sailor must have exactly 2 bracketed scores
- `discard_count = 2` and exactly 2 scores have parentheses → **ACCEPT**

**Validation**: Run `admin/tools/validate_discard_brackets_compliance.sql` after entry

**Action**: If found → **FIX IMMEDIATELY** → Add missing brackets → Re-validate

---

### Rule 5: Worst Scores MUST Be Discarded
**Status**: ❌ **HARD STOP - REJECT DATA** (Post-Entry Check)

**Rule**: If discard_count > 0, the worst score(s) MUST be bracketed.

**Invalid Examples** (DO NOT ACCEPT):
- Worst score is `5.0` (not bracketed) but `4.0` is `(4.0)` → **ERROR**
- Block says "Discards: 2" but worst 2 scores not bracketed → **ERROR**

**Valid Format** (REQUIRED):
- Worst scores have parentheses → **ACCEPT**
- Discard_count = 2, worst 2 scores are `(5.0)` and `(4.0)` → **ACCEPT**

**Validation**: Run `admin/tools/validate_discard_brackets_compliance.sql` after entry

**Action**: If found → **FIX IMMEDIATELY** → Add brackets to worst scores → Re-validate

---

### Rule 6: Penalty Codes MUST Have Space
**Status**: ❌ **HARD STOP - REJECT DATA**

**Invalid Examples** (DO NOT ACCEPT):
- `"10.0DNS"` - missing space
- `"14.0DNC"` - missing space

**Valid Format** (REQUIRED):
- `"10.0 DNS"` - single space between score and code

**Validation Query**:
```sql
-- Flag missing space
WHERE value ~ '[0-9]\.[0-9][A-Z]'
```

**Action**: If found → **REJECT DATA** → Add space → Re-validate

---

### Rule 5: Penalty Codes MUST Be Uppercase
**Status**: ❌ **HARD STOP - REJECT DATA**

**Invalid Examples** (DO NOT ACCEPT):
- `"14.0 dnc"` - lowercase
- `"10.0 Dns"` - mixed case

**Valid Format** (REQUIRED):
- `"14.0 DNC"` - uppercase

**Validation Query**:
```sql
-- Flag lowercase
WHERE value ~* '\b(dnc|dns|dnf|ret|dsq|ufd|bfd|dpi|ocs)\b'
  AND value !~ '\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b'
```

**Action**: If found → **REJECT DATA** → Uppercase code → Re-validate

---

## DATA ENTRY WORKFLOW

### Step 1: Extract Data from Source
- Read from PDF/results sheet
- Extract race scores as they appear

### Step 2: Transform Source Format
- Add `.0` to integers: `"5"` → `"5.0"`
- Transform discards: `"-11"` → `"(11.0)"`, `(11)` → `"(11.0)"`
- Transform penalties: `"DNC"` → `"{entries+1}.0 DNC"`
- Add spaces: `"10.0DNS"` → `"10.0 DNS"`
- Uppercase codes: `"dnc"` → `"DNC"`

### Step 3: Pre-Entry Validation (MANDATORY)
**Run validation script**: `admin/tools/validate_race_scores_pre_entry.sql`

**If ANY errors found**:
- ❌ **DO NOT INSERT DATA**
- Fix source/transformation
- Re-run validation
- **ONLY proceed when 100% valid**

**If ALL valid**:
- ✅ **Proceed with data entry**

### Step 4: Post-Entry Validation (MANDATORY)

**BEFORE** finalizing data entry, run:

1. **Discard Brackets Compliance**: `admin/tools/validate_discard_brackets_compliance.sql`
   - ✅ `discard_count` matches number of bracketed scores
   - ✅ Worst scores are actually discarded (bracketed)
   - ✅ Block discard rule is followed (e.g., "Discards: 2" = each sailor has 2 discards)

2. **Checksum Validation**: `admin/tools/checksum_total_nett_points.sql`
   - Total = Sum of all race scores
   - Nett = Total - Discards
   - Verify against stored values

**If ANY validation fails, DO NOT finalize data. Fix all issues first.**

---

## EXAMPLE: REJECTED DATA

```json
{
  "R1": "1.0",        // ✅ Valid
  "R2": "DNC",        // ❌ REJECT - missing score
  "R3": "5",          // ❌ REJECT - missing .0
  "R4": "-11.0",      // ❌ REJECT - minus sign
  "R5": "10.0DNS"     // ❌ REJECT - missing space
}
```

**Action**: Fix all errors before entry:
```json
{
  "R1": "1.0",        // ✅ Valid
  "R2": "14.0 DNC",   // ✅ Fixed
  "R3": "5.0",        // ✅ Fixed
  "R4": "(11.0)",     // ✅ Fixed
  "R5": "10.0 DNS"    // ✅ Fixed
}
```

---

## ENFORCEMENT

**These rules are NOT suggestions - they are MANDATORY:**

1. **No exceptions** - all data MUST pass validation
2. **Automated checks** - use validation scripts before entry
3. **Manual review** - if automated checks pass, verify penalty code scores match `entries + 1`
4. **Documentation** - log any validation failures for audit

---

**Related Documents**:
- `docs/RACE_SCORES_RULES.md` - Complete format rules
- `admin/tools/validate_race_scores_pre_entry.sql` - Validation script
- `admin/tools/checksum_total_nett_points.sql` - Post-entry checksum


## Purpose
This document defines **MANDATORY validation rules** that MUST be checked **BEFORE** any race_scores data is entered into the database. Data that fails validation **MUST BE REJECTED** and fixed before entry.

---

## VALIDATION RULES (HARD STOPS)

### Rule 1: Penalty Codes MUST Include Scores
**Status**: ❌ **HARD STOP - REJECT DATA**

**Invalid Examples** (DO NOT ACCEPT):
- `"DNC"` - missing score
- `"DNS"` - missing score  
- `"OCS"` - missing score

**Valid Format** (REQUIRED):
- `"14.0 DNC"` - score + space + code
- Score = `entries + 1` for penalty codes
- Example: 13 entries → DNC = `"14.0 DNC"`

**Validation Query**:
```sql
-- Flag any penalty code without numeric score
WHERE value ~ '\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b' 
  AND value !~ '^[0-9]'
```

**Action**: If found → **REJECT DATA** → Fix source → Re-validate

---

### Rule 2: All Numeric Scores MUST Have .0 Format
**Status**: ❌ **HARD STOP - REJECT DATA**

**Invalid Examples** (DO NOT ACCEPT):
- `"5"` - missing .0
- `"13"` - missing .0
- `"1.00"` - wrong decimal places

**Valid Format** (REQUIRED):
- `"5.0"` - single .0 decimal
- `"13.0"` - single .0 decimal

**Validation Query**:
```sql
-- Flag integers or wrong decimals
WHERE value ~ '^[0-9]+$'  -- Integer only
   OR value ~ '^[0-9]+\.[0-9][0-9]+[^0-9]'  -- Too many decimals
```

**Action**: If found → **REJECT DATA** → Fix format → Re-validate

---

### Rule 3: Discards MUST Use Parentheses
**Status**: ❌ **HARD STOP - REJECT DATA**

**Invalid Examples** (DO NOT ACCEPT):
- `"-11.0"` - minus sign (from source sheet)
- `"11.0"` - missing parentheses when discard

**Valid Format** (REQUIRED):
- `"(11.0)"` - parentheses for discards
- `"(14.0 DNC)"` - parentheses for discarded penalties

**Validation Query**:
```sql
-- Flag minus signs (should be parentheses)
WHERE value ~ '^-'
```

**Action**: If found → **REJECT DATA** → Transform source format → Re-validate

---

### Rule 4: Discard Count MUST Match Bracketed Scores
**Status**: ❌ **HARD STOP - REJECT DATA** (Post-Entry Check)

**Rule**: After entering race_scores, `discard_count` MUST equal number of bracketed scores.

**Invalid Examples** (DO NOT ACCEPT):
- `discard_count = 2` but only 1 bracketed score → **ERROR**
- Block rule "Discards: 2" but sailor has 0 discards → **ERROR**
- `discard_count = 1` but 0 bracketed scores → **ERROR**

**Valid Format** (REQUIRED):
- Block rule "Discards: 2" = each sailor must have exactly 2 bracketed scores
- `discard_count = 2` and exactly 2 scores have parentheses → **ACCEPT**

**Validation**: Run `admin/tools/validate_discard_brackets_compliance.sql` after entry

**Action**: If found → **FIX IMMEDIATELY** → Add missing brackets → Re-validate

---

### Rule 5: Worst Scores MUST Be Discarded
**Status**: ❌ **HARD STOP - REJECT DATA** (Post-Entry Check)

**Rule**: If discard_count > 0, the worst score(s) MUST be bracketed.

**Invalid Examples** (DO NOT ACCEPT):
- Worst score is `5.0` (not bracketed) but `4.0` is `(4.0)` → **ERROR**
- Block says "Discards: 2" but worst 2 scores not bracketed → **ERROR**

**Valid Format** (REQUIRED):
- Worst scores have parentheses → **ACCEPT**
- Discard_count = 2, worst 2 scores are `(5.0)` and `(4.0)` → **ACCEPT**

**Validation**: Run `admin/tools/validate_discard_brackets_compliance.sql` after entry

**Action**: If found → **FIX IMMEDIATELY** → Add brackets to worst scores → Re-validate

---

### Rule 6: Penalty Codes MUST Have Space
**Status**: ❌ **HARD STOP - REJECT DATA**

**Invalid Examples** (DO NOT ACCEPT):
- `"10.0DNS"` - missing space
- `"14.0DNC"` - missing space

**Valid Format** (REQUIRED):
- `"10.0 DNS"` - single space between score and code

**Validation Query**:
```sql
-- Flag missing space
WHERE value ~ '[0-9]\.[0-9][A-Z]'
```

**Action**: If found → **REJECT DATA** → Add space → Re-validate

---

### Rule 5: Penalty Codes MUST Be Uppercase
**Status**: ❌ **HARD STOP - REJECT DATA**

**Invalid Examples** (DO NOT ACCEPT):
- `"14.0 dnc"` - lowercase
- `"10.0 Dns"` - mixed case

**Valid Format** (REQUIRED):
- `"14.0 DNC"` - uppercase

**Validation Query**:
```sql
-- Flag lowercase
WHERE value ~* '\b(dnc|dns|dnf|ret|dsq|ufd|bfd|dpi|ocs)\b'
  AND value !~ '\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b'
```

**Action**: If found → **REJECT DATA** → Uppercase code → Re-validate

---

## DATA ENTRY WORKFLOW

### Step 1: Extract Data from Source
- Read from PDF/results sheet
- Extract race scores as they appear

### Step 2: Transform Source Format
- Add `.0` to integers: `"5"` → `"5.0"`
- Transform discards: `"-11"` → `"(11.0)"`, `(11)` → `"(11.0)"`
- Transform penalties: `"DNC"` → `"{entries+1}.0 DNC"`
- Add spaces: `"10.0DNS"` → `"10.0 DNS"`
- Uppercase codes: `"dnc"` → `"DNC"`

### Step 3: Pre-Entry Validation (MANDATORY)
**Run validation script**: `admin/tools/validate_race_scores_pre_entry.sql`

**If ANY errors found**:
- ❌ **DO NOT INSERT DATA**
- Fix source/transformation
- Re-run validation
- **ONLY proceed when 100% valid**

**If ALL valid**:
- ✅ **Proceed with data entry**

### Step 4: Post-Entry Validation (MANDATORY)

**BEFORE** finalizing data entry, run:

1. **Discard Brackets Compliance**: `admin/tools/validate_discard_brackets_compliance.sql`
   - ✅ `discard_count` matches number of bracketed scores
   - ✅ Worst scores are actually discarded (bracketed)
   - ✅ Block discard rule is followed (e.g., "Discards: 2" = each sailor has 2 discards)

2. **Checksum Validation**: `admin/tools/checksum_total_nett_points.sql`
   - Total = Sum of all race scores
   - Nett = Total - Discards
   - Verify against stored values

**If ANY validation fails, DO NOT finalize data. Fix all issues first.**

---

## EXAMPLE: REJECTED DATA

```json
{
  "R1": "1.0",        // ✅ Valid
  "R2": "DNC",        // ❌ REJECT - missing score
  "R3": "5",          // ❌ REJECT - missing .0
  "R4": "-11.0",      // ❌ REJECT - minus sign
  "R5": "10.0DNS"     // ❌ REJECT - missing space
}
```

**Action**: Fix all errors before entry:
```json
{
  "R1": "1.0",        // ✅ Valid
  "R2": "14.0 DNC",   // ✅ Fixed
  "R3": "5.0",        // ✅ Fixed
  "R4": "(11.0)",     // ✅ Fixed
  "R5": "10.0 DNS"    // ✅ Fixed
}
```

---

## ENFORCEMENT

**These rules are NOT suggestions - they are MANDATORY:**

1. **No exceptions** - all data MUST pass validation
2. **Automated checks** - use validation scripts before entry
3. **Manual review** - if automated checks pass, verify penalty code scores match `entries + 1`
4. **Documentation** - log any validation failures for audit

---

**Related Documents**:
- `docs/RACE_SCORES_RULES.md` - Complete format rules
- `admin/tools/validate_race_scores_pre_entry.sql` - Validation script
- `admin/tools/checksum_total_nett_points.sql` - Post-entry checksum

