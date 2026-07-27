# RACE_SCORES RULES - COMPLETE SPECIFICATION

## Column: `race_scores` (JSONB, NOT NULL)

**Data Type**: JSONB (PostgreSQL JSON Binary format)  
**Storage**: JSON object with race keys as strings  
**Required**: YES (cannot be NULL if row has results)

---

## 1. KEY FORMAT RULES

### Race Keys
- **Format**: `"R1"`, `"R2"`, `"R3"`, ..., `"R30"` (sequential, starting at R1)
- **Naming**: Always uppercase `R` followed by race number (no zero-padding)
- **Sequential**: Must be consecutive (R1, R2, R3... not R1, R3, R5)
- **Max Races**: Typically R1-R30 (depends on regatta)

**✅ CORRECT**:
```json
{"R1": "1.0", "R2": "2.0", "R3": "1.0"}
```

**❌ WRONG**:
```json
{"Race1": "1.0"}           // Wrong key format
{"r1": "1.0"}              // Wrong case
{"R01": "1.0"}             // Wrong padding
{"R1": "1.0", "R3": "2.0"} // Missing R2
```

---

## 2. VALUE FORMAT RULES

### SOURCE FORMATS (What You See in Results Sheet)

Discards can appear in **multiple formats** in the source PDF/results sheet:
- **Parentheses**: `(11)`, `(2)`, `(6)`
- **Minus sign**: `-11`, `-2`, `-6`
- **Crossed out**: `11̶`, `2̶` (visual strikethrough)
- **Other**: Various visual indicators

**CRITICAL**: These are **source formats** - you must transform them to the **standard database format** below.

---

### Rule 2.1: Numeric Format (CRITICAL)
- **Database Format**: Must ALWAYS have `.0` decimal
- **Examples**: `"1.0"`, `"2.0"`, `"13.0"`, `"22.0"`
- **Rule**: Every numeric score MUST end with `.0` in database

**✅ CORRECT**:
```json
{"R1": "1.0", "R2": "2.0", "R3": "13.0"}
```

**❌ WRONG**:
```json
{"R1": "1", "R2": "2", "R3": "13"}        // Missing .0
{"R1": "1.00", "R2": "2.00"}              // Wrong decimal places
{"R1": "1.0.0", "R2": "2.0.0"}           // Double decimal
```

---

### Rule 2.2: Discarded Scores (CRITICAL)

#### Source Formats (Results Sheet)
Discards may appear as:
- `(11)` - parentheses in source
- `-11` - minus sign prefix
- `11̶` - crossed out number (strikethrough)
- Other visual indicators

#### Database Format (What We Store)
- **Format**: Entire value wrapped in parentheses: `"(11.0)"`
- **Rule**: Parentheses indicate this score was discarded
- **No Space Inside**: `"(11.0)"` NOT `"( 11.0 )"`
- **Multiple Discards**: Each in separate parentheses

#### Transformation Rules
When importing from results sheet:
1. **Source `(11)`** → **Database `"(11.0)"`** (add .0, keep parentheses)
2. **Source `-11`** → **Database `"(11.0)"`** (remove minus, add .0, add parentheses)
3. **Source `11̶` (crossed)** → **Database `"(11.0)"`** (remove strikethrough, add .0, add parentheses)
4. **Source `11` (visual discard)** → **Database `"(11.0)"`** (add .0, add parentheses)

**✅ CORRECT (Database Format)**:
```json
{"R1": "1.0", "R2": "(2.0)", "R3": "1.0", "R4": "(11.0)"}
```

**❌ WRONG**:
```json
{"R2": "2.0"}              // Discard missing parentheses
{"R2": "-2.0"}             // Minus sign (should be "(2.0)")
{"R2": "( 2.0 )"}          // Spaces inside parentheses
{"R2": "[2.0]"}            // Wrong brackets
{"R2": "(2)"}              // Missing .0
```

---

### Rule 2.3: Penalty Codes (CRITICAL - DATA ENTRY VALIDATION)
- **Format**: `"{score}.0 {CODE}"` - score + single space + code
- **Score Required**: MUST include numeric score before code
- **Space Required**: Single space between score and code
- **Code Format**: Uppercase letters only (DNC, DNS, OCS, etc.)
- **VALIDATION**: Penalty codes without scores are **INVALID** and **MUST BE REJECTED** during data entry
- **Score Calculation**: For penalty codes, score = `entries + 1` (e.g., 13 entries → DNC = `"14.0 DNC"`)

**✅ CORRECT**:
```json
{"R4": "6.0 DNC", "R5": "10.0 DNS", "R6": "7.0 OCS"}
```

**❌ WRONG** (REJECT DURING DATA ENTRY):
```json
{"R4": "DNC"}               // ❌ Missing score - REJECT
{"R4": "6.0DNC"}            // ❌ Missing space - REJECT
{"R4": "6.0  DNC"}          // ❌ Double space - REJECT
{"R4": "10.0.0 DNS"}         // ❌ Double decimal - REJECT
{"R4": "dnc"}               // ❌ Wrong case - REJECT
```

**See**: `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` for mandatory validation rules

---

### Rule 2.4: Discarded Penalty Codes (CRITICAL)
- **Format**: Penalty code INSIDE parentheses: `"(6.0 DNC)"`
- **Rule**: Both parentheses AND penalty code present
- **Format**: `"({score}.0 {CODE})"`

**✅ CORRECT**:
```json
{"R4": "(6.0 DNC)", "R5": "(10.0 DNS)", "R6": "(7.0 OCS)"}
```

**❌ WRONG**:
```json
{"R4": "(DNC)"}             // Missing score inside brackets
{"R4": "6.0 DNC"}           // Missing parentheses for discard
{"R4": "(6.0DNC)"}          // Missing space inside brackets
```

---

## 3. VALID PENALTY CODES

### World Sailing Standard Codes
- **DNC**: Did Not Compete (score = entries + 1)
- **DNS**: Did Not Start (score = entries + 1)
- **OCS**: On Course Side (score = entries + 1)
- **DSQ**: Disqualified (score = entries + 1)
- **DNF**: Did Not Finish (score = entries + 1)
- **RET**: Retired (score = entries + 1)
- **BFD**: Black Flag Disqualification
- **UFD**: U Flag Disqualification
- **DPI**: Discretionary Penalty Imposed

### Penalty Code Rules
1. **ALWAYS uppercase**: `DNC` not `dnc` or `Dnc`
2. **ALWAYS include score**: `"10.0 DNS"` not `"DNS"`
3. **Score = entries + 1**: For 9 entries, DNC = `"10.0 DNC"`
4. **Preserve exactly**: Never modify penalty codes from source

---

## 4. COMBINATION RULES

### Rule 4.1: Normal Finish
```json
{"R1": "1.0"}
```
- Numeric only
- Ends with `.0`
- No parentheses
- No penalty code

### Rule 4.2: Discarded Normal Finish
```json
{"R2": "(2.0)"}
```
- Numeric with `.0`
- Wrapped in parentheses
- No penalty code

### Rule 4.3: Penalty Code (Not Discarded)
```json
{"R4": "10.0 DNC"}
```
- Numeric score with `.0`
- Single space
- Penalty code
- NO parentheses

### Rule 4.4: Discarded Penalty Code
```json
{"R4": "(10.0 DNC)"}
```
- Numeric score with `.0`
- Single space
- Penalty code
- Wrapped in parentheses

---

## 5. DATA INTEGRITY RULES (CRITICAL)

### Rule 5.1: NEVER Modify Penalty Codes
- **Preserve exactly** as in original results sheet
- **Never change** DNC to DNS or vice versa
- **Never remove** penalty codes
- **Never add** penalty codes not in source

### Rule 5.2: NEVER Remove Parentheses
- **Parentheses = discard indicator**
- **Removing = data corruption**
- **Must preserve** all parentheses exactly

### Rule 5.3: NEVER Convert to Numeric
- **Keep as strings** with codes
- **JSONB stores as text** - preserve format
- **Don't parse/convert** to numbers

### Rule 5.4: ALWAYS Preserve Original Format
- **Copy from source** exactly
- **Transform only format** (add .0, add spaces)
- **Never invent** data

### Rule 5.5: ALWAYS Store Score + Code for Penalties
- **Penalty = score + space + code**
- **Never store code alone**
- **Never store score without code** when penalty present

---

## 6. VALIDATION EXAMPLES

### ✅ VALID Examples

```json
{
  "R1": "1.0",
  "R2": "(2.0)",
  "R3": "1.0",
  "R4": "6.0 DNC",
  "R5": "(10.0 DNS)",
  "R6": "2.0",
  "R7": "1.0",
  "R8": "1.0"
}
```

**Breakdown**:
- R1: Normal finish (1st place)
- R2: Discarded finish (2nd place, discarded)
- R3: Normal finish (1st place)
- R4: Penalty code (6.0 DNC, not discarded)
- R5: Discarded penalty (10.0 DNS, discarded)
- R6-R8: Normal finishes

### ❌ INVALID Examples

```json
// WRONG: Missing .0
{"R1": "1", "R2": "2"}

// WRONG: Discard without parentheses
{"R2": "2.0"}

// WRONG: Penalty without score
{"R4": "DNC"}

// WRONG: Penalty without space
{"R4": "6.0DNC"}

// WRONG: Double decimal
{"R4": "10.0.0 DNS"}

// WRONG: Wrong case
{"R4": "6.0 dnc"}

// WRONG: Wrong key format
{"Race1": "1.0"}

// WRONG: Missing race
{"R1": "1.0", "R3": "2.0"}  // Missing R2
```

---

## 7. CALCULATION RULES

### Total Points Calculation
- **Sum ALL race scores** (including discarded)
- **Extract numeric value** from each race score
- **Penalty codes**: Use numeric score (e.g., `"10.0 DNS"` → `10.0`)
- **Discarded**: Include in total (e.g., `"(2.0)"` → `2.0`)

**Example**:
```json
{"R1": "1.0", "R2": "(2.0)", "R3": "6.0 DNC"}
```
Total = 1.0 + 2.0 + 6.0 = **9.0**

### Nett Points Calculation
- **Total points** MINUS **discarded scores**
- **Identify discards**: Values wrapped in parentheses
- **Extract discard values**: Remove parentheses, extract number

**Example**:
```json
{"R1": "1.0", "R2": "(2.0)", "R3": "6.0 DNC"}
```
Total = 9.0, Discard = 2.0, Nett = **7.0**

### Validation Formula
```
nett_points_raw = total_points_raw - sum_of_discarded_scores
```

---

## 8. COMMON MISTAKES & FIXES

| ❌ WRONG | ✅ CORRECT | Issue |
|---------|-----------|-------|
| `"5"` | `"5.0"` | Missing .0 |
| `"2.0"` (discard) | `"(2.0)"` | Missing parentheses |
| `"-11.0"` | `"(11.0)"` | Minus sign instead of parentheses |
| `"11.0"` (crossed in source) | `"(11.0)"` | Missing parentheses for discard |
| `"DNS"` | `"10.0 DNS"` | Missing score |
| `"10.0DNS"` | `"10.0 DNS"` | Missing space |
| `"10.0.0 DNS"` | `"10.0 DNS"` | Double decimal |
| `"(DNC)"` | `"(10.0 DNC)"` | Missing score in brackets |
| `"6.0  DNC"` | `"6.0 DNC"` | Double space |
| `"dnc"` | `"DNC"` | Wrong case |
| `"(11)"` | `"(11.0)"` | Missing .0 inside parentheses |

---

## 9. SQL QUERIES FOR VALIDATION

### Check for missing .0
```sql
SELECT result_id, helm_name, key, value
FROM public.results,
LATERAL jsonb_each_text(race_scores) AS t(key, value)
WHERE value ~ '^[0-9]+$'  -- Integer only
   OR value ~ '^[0-9]+\.[0-9][0-9]+';  -- Too many decimals
```

### Check for missing parentheses on discards
```sql
-- This requires checking against discard_count
-- See separate validation scripts
```

### Check for penalty code format
```sql
SELECT result_id, helm_name, key, value
FROM public.results,
LATERAL jsonb_each_text(race_scores) AS t(key, value)
WHERE value ~ '[A-Z]'  -- Has penalty code
  AND (
    value !~ '[0-9]\.0 [A-Z]' OR  -- Missing score.0 space code format
    value ~ '[0-9]\.0\.0'          -- Double decimal
  );
```

### Check for missing spaces in penalties
```sql
SELECT result_id, helm_name, key, value
FROM public.results,
LATERAL jsonb_each_text(race_scores) AS t(key, value)
WHERE value ~ '[0-9]\.[0-9][A-Z]';  -- Number directly followed by code
```

---

## 10. HTML DISPLAY RULES

### Styling
- **Normal scores**: Display as-is
- **Discarded scores**: CSS class `disc` (applied if value matches `/^\(.*\)$/`)
- **Penalty codes**: CSS class `code` (applied if value matches `/\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b/i`)

### JavaScript Patterns
```javascript
const PEN = /\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b/i;  // Penalty codes
const DISC = /^\(.*\)$/;  // Discarded scores (parentheses)
```

---

## 11. ENTRY PROCESS RULES

### Pre-Entry Validation (MANDATORY)

**BEFORE** inserting/updating any race_scores, validate:

1. **All penalty codes have scores**:
   - ❌ `"DNC"` → **REJECT** - missing score
   - ✅ `"14.0 DNC"` → **ACCEPT** - has score
   - Check: `WHERE value ~ '[A-Z]' AND value !~ '^[0-9]'` → ERROR

2. **All scores have .0 format**:
   - ❌ `"5"` → **REJECT** - missing .0
   - ✅ `"5.0"` → **ACCEPT**

3. **All discards have parentheses**:
   - ❌ `"2.0"` (when discard) → **REJECT**
   - ✅ `"(2.0)"` → **ACCEPT**

**If ANY validation fails, DO NOT insert data. Fix source data first.**

---

### Step-by-Step Import Process

1. **Read from source** (PDF/results sheet)
   - Identify normal scores: `1`, `2`, `13`, etc.
   - Identify discards: `(11)`, `-11`, `11̶`, etc.
   - Identify penalties: `DNS`, `DNC`, `OCS`, etc.

2. **Transform discard indicators**:
   - **Source `(11)`** → Remove original parentheses → Add `.0` → Add database parentheses → `"(11.0)"`
   - **Source `-11`** → Remove minus sign → Add `.0` → Add parentheses → `"(11.0)"`
   - **Source `11̶` (crossed)** → Remove strikethrough → Add `.0` → Add parentheses → `"(11.0)"`
   - **Source visual discard** → Add `.0` → Add parentheses → `"(11.0)"`

3. **Transform normal scores**:
   - Add `.0` if missing: `"1"` → `"1.0"`
   - Ensure decimal format: `"13"` → `"13.0"`

4. **Transform penalty codes**:
   - Add score if missing: `"DNS"` → `"{entries+1}.0 DNS"`
   - Add space if missing: `"10.0DNS"` → `"10.0 DNS"`
   - Ensure `.0` format: `"10 DNS"` → `"10.0 DNS"`

5. **Transform discarded penalties**:
   - Combine discard + penalty: `"(11 DNS)"` or `"-11 DNS"` → `"(11.0 DNS)"`
   - Ensure proper format: Score + space + code inside parentheses

6. **Validate format** against these rules

7. **Validate** against discard_count (count parentheses matches discard_count)

8. **Store** as JSONB string

---

## 12. SUMMARY CHECKLIST

Before inserting/updating `race_scores`, verify:

### Format Checks
- [ ] All keys are `R1`, `R2`, `R3`... (uppercase R, sequential)
- [ ] All numeric values end with `.0` (not `"1"` or `"1.00"`)
- [ ] Discarded scores have parentheses: `"(2.0)"` (NOT `"-2.0"` or `"2.0"`)
- [ ] Penalty codes have score + space + code: `"10.0 DNS"`
- [ ] Discarded penalties have parentheses: `"(10.0 DNS)"`
- [ ] No double decimals: `"10.0"` not `"10.0.0"`
- [ ] No double spaces: `"10.0 DNS"` not `"10.0  DNS"`
- [ ] All penalty codes are uppercase: `DNC` not `dnc`
- [ ] Sequential races: R1, R2, R3... (no gaps)

### Transformation Checks
- [ ] Source `(11)` → Database `"(11.0)"` (added .0)
- [ ] Source `-11` → Database `"(11.0)"` (removed minus, added parentheses)
- [ ] Source `11̶` (crossed) → Database `"(11.0)"` (removed strikethrough, added parentheses)
- [ ] No minus signs in database: All discards use parentheses only

### Calculation Checks
- [ ] Total matches sum of all race scores
- [ ] Nett matches total minus discarded scores
- [ ] Discard count matches number of parentheses in race_scores

---

**Last Updated**: 2025-01-XX  
**Version**: 1.0  
**Authority**: Database schema and validation rules


## Column: `race_scores` (JSONB, NOT NULL)

**Data Type**: JSONB (PostgreSQL JSON Binary format)  
**Storage**: JSON object with race keys as strings  
**Required**: YES (cannot be NULL if row has results)

---

## 1. KEY FORMAT RULES

### Race Keys
- **Format**: `"R1"`, `"R2"`, `"R3"`, ..., `"R30"` (sequential, starting at R1)
- **Naming**: Always uppercase `R` followed by race number (no zero-padding)
- **Sequential**: Must be consecutive (R1, R2, R3... not R1, R3, R5)
- **Max Races**: Typically R1-R30 (depends on regatta)

**✅ CORRECT**:
```json
{"R1": "1.0", "R2": "2.0", "R3": "1.0"}
```

**❌ WRONG**:
```json
{"Race1": "1.0"}           // Wrong key format
{"r1": "1.0"}              // Wrong case
{"R01": "1.0"}             // Wrong padding
{"R1": "1.0", "R3": "2.0"} // Missing R2
```

---

## 2. VALUE FORMAT RULES

### SOURCE FORMATS (What You See in Results Sheet)

Discards can appear in **multiple formats** in the source PDF/results sheet:
- **Parentheses**: `(11)`, `(2)`, `(6)`
- **Minus sign**: `-11`, `-2`, `-6`
- **Crossed out**: `11̶`, `2̶` (visual strikethrough)
- **Other**: Various visual indicators

**CRITICAL**: These are **source formats** - you must transform them to the **standard database format** below.

---

### Rule 2.1: Numeric Format (CRITICAL)
- **Database Format**: Must ALWAYS have `.0` decimal
- **Examples**: `"1.0"`, `"2.0"`, `"13.0"`, `"22.0"`
- **Rule**: Every numeric score MUST end with `.0` in database

**✅ CORRECT**:
```json
{"R1": "1.0", "R2": "2.0", "R3": "13.0"}
```

**❌ WRONG**:
```json
{"R1": "1", "R2": "2", "R3": "13"}        // Missing .0
{"R1": "1.00", "R2": "2.00"}              // Wrong decimal places
{"R1": "1.0.0", "R2": "2.0.0"}           // Double decimal
```

---

### Rule 2.2: Discarded Scores (CRITICAL)

#### Source Formats (Results Sheet)
Discards may appear as:
- `(11)` - parentheses in source
- `-11` - minus sign prefix
- `11̶` - crossed out number (strikethrough)
- Other visual indicators

#### Database Format (What We Store)
- **Format**: Entire value wrapped in parentheses: `"(11.0)"`
- **Rule**: Parentheses indicate this score was discarded
- **No Space Inside**: `"(11.0)"` NOT `"( 11.0 )"`
- **Multiple Discards**: Each in separate parentheses

#### Transformation Rules
When importing from results sheet:
1. **Source `(11)`** → **Database `"(11.0)"`** (add .0, keep parentheses)
2. **Source `-11`** → **Database `"(11.0)"`** (remove minus, add .0, add parentheses)
3. **Source `11̶` (crossed)** → **Database `"(11.0)"`** (remove strikethrough, add .0, add parentheses)
4. **Source `11` (visual discard)** → **Database `"(11.0)"`** (add .0, add parentheses)

**✅ CORRECT (Database Format)**:
```json
{"R1": "1.0", "R2": "(2.0)", "R3": "1.0", "R4": "(11.0)"}
```

**❌ WRONG**:
```json
{"R2": "2.0"}              // Discard missing parentheses
{"R2": "-2.0"}             // Minus sign (should be "(2.0)")
{"R2": "( 2.0 )"}          // Spaces inside parentheses
{"R2": "[2.0]"}            // Wrong brackets
{"R2": "(2)"}              // Missing .0
```

---

### Rule 2.3: Penalty Codes (CRITICAL - DATA ENTRY VALIDATION)
- **Format**: `"{score}.0 {CODE}"` - score + single space + code
- **Score Required**: MUST include numeric score before code
- **Space Required**: Single space between score and code
- **Code Format**: Uppercase letters only (DNC, DNS, OCS, etc.)
- **VALIDATION**: Penalty codes without scores are **INVALID** and **MUST BE REJECTED** during data entry
- **Score Calculation**: For penalty codes, score = `entries + 1` (e.g., 13 entries → DNC = `"14.0 DNC"`)

**✅ CORRECT**:
```json
{"R4": "6.0 DNC", "R5": "10.0 DNS", "R6": "7.0 OCS"}
```

**❌ WRONG** (REJECT DURING DATA ENTRY):
```json
{"R4": "DNC"}               // ❌ Missing score - REJECT
{"R4": "6.0DNC"}            // ❌ Missing space - REJECT
{"R4": "6.0  DNC"}          // ❌ Double space - REJECT
{"R4": "10.0.0 DNS"}         // ❌ Double decimal - REJECT
{"R4": "dnc"}               // ❌ Wrong case - REJECT
```

**See**: `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` for mandatory validation rules

---

### Rule 2.4: Discarded Penalty Codes (CRITICAL)
- **Format**: Penalty code INSIDE parentheses: `"(6.0 DNC)"`
- **Rule**: Both parentheses AND penalty code present
- **Format**: `"({score}.0 {CODE})"`

**✅ CORRECT**:
```json
{"R4": "(6.0 DNC)", "R5": "(10.0 DNS)", "R6": "(7.0 OCS)"}
```

**❌ WRONG**:
```json
{"R4": "(DNC)"}             // Missing score inside brackets
{"R4": "6.0 DNC"}           // Missing parentheses for discard
{"R4": "(6.0DNC)"}          // Missing space inside brackets
```

---

## 3. VALID PENALTY CODES

### World Sailing Standard Codes
- **DNC**: Did Not Compete (score = entries + 1)
- **DNS**: Did Not Start (score = entries + 1)
- **OCS**: On Course Side (score = entries + 1)
- **DSQ**: Disqualified (score = entries + 1)
- **DNF**: Did Not Finish (score = entries + 1)
- **RET**: Retired (score = entries + 1)
- **BFD**: Black Flag Disqualification
- **UFD**: U Flag Disqualification
- **DPI**: Discretionary Penalty Imposed

### Penalty Code Rules
1. **ALWAYS uppercase**: `DNC` not `dnc` or `Dnc`
2. **ALWAYS include score**: `"10.0 DNS"` not `"DNS"`
3. **Score = entries + 1**: For 9 entries, DNC = `"10.0 DNC"`
4. **Preserve exactly**: Never modify penalty codes from source

---

## 4. COMBINATION RULES

### Rule 4.1: Normal Finish
```json
{"R1": "1.0"}
```
- Numeric only
- Ends with `.0`
- No parentheses
- No penalty code

### Rule 4.2: Discarded Normal Finish
```json
{"R2": "(2.0)"}
```
- Numeric with `.0`
- Wrapped in parentheses
- No penalty code

### Rule 4.3: Penalty Code (Not Discarded)
```json
{"R4": "10.0 DNC"}
```
- Numeric score with `.0`
- Single space
- Penalty code
- NO parentheses

### Rule 4.4: Discarded Penalty Code
```json
{"R4": "(10.0 DNC)"}
```
- Numeric score with `.0`
- Single space
- Penalty code
- Wrapped in parentheses

---

## 5. DATA INTEGRITY RULES (CRITICAL)

### Rule 5.1: NEVER Modify Penalty Codes
- **Preserve exactly** as in original results sheet
- **Never change** DNC to DNS or vice versa
- **Never remove** penalty codes
- **Never add** penalty codes not in source

### Rule 5.2: NEVER Remove Parentheses
- **Parentheses = discard indicator**
- **Removing = data corruption**
- **Must preserve** all parentheses exactly

### Rule 5.3: NEVER Convert to Numeric
- **Keep as strings** with codes
- **JSONB stores as text** - preserve format
- **Don't parse/convert** to numbers

### Rule 5.4: ALWAYS Preserve Original Format
- **Copy from source** exactly
- **Transform only format** (add .0, add spaces)
- **Never invent** data

### Rule 5.5: ALWAYS Store Score + Code for Penalties
- **Penalty = score + space + code**
- **Never store code alone**
- **Never store score without code** when penalty present

---

## 6. VALIDATION EXAMPLES

### ✅ VALID Examples

```json
{
  "R1": "1.0",
  "R2": "(2.0)",
  "R3": "1.0",
  "R4": "6.0 DNC",
  "R5": "(10.0 DNS)",
  "R6": "2.0",
  "R7": "1.0",
  "R8": "1.0"
}
```

**Breakdown**:
- R1: Normal finish (1st place)
- R2: Discarded finish (2nd place, discarded)
- R3: Normal finish (1st place)
- R4: Penalty code (6.0 DNC, not discarded)
- R5: Discarded penalty (10.0 DNS, discarded)
- R6-R8: Normal finishes

### ❌ INVALID Examples

```json
// WRONG: Missing .0
{"R1": "1", "R2": "2"}

// WRONG: Discard without parentheses
{"R2": "2.0"}

// WRONG: Penalty without score
{"R4": "DNC"}

// WRONG: Penalty without space
{"R4": "6.0DNC"}

// WRONG: Double decimal
{"R4": "10.0.0 DNS"}

// WRONG: Wrong case
{"R4": "6.0 dnc"}

// WRONG: Wrong key format
{"Race1": "1.0"}

// WRONG: Missing race
{"R1": "1.0", "R3": "2.0"}  // Missing R2
```

---

## 7. CALCULATION RULES

### Total Points Calculation
- **Sum ALL race scores** (including discarded)
- **Extract numeric value** from each race score
- **Penalty codes**: Use numeric score (e.g., `"10.0 DNS"` → `10.0`)
- **Discarded**: Include in total (e.g., `"(2.0)"` → `2.0`)

**Example**:
```json
{"R1": "1.0", "R2": "(2.0)", "R3": "6.0 DNC"}
```
Total = 1.0 + 2.0 + 6.0 = **9.0**

### Nett Points Calculation
- **Total points** MINUS **discarded scores**
- **Identify discards**: Values wrapped in parentheses
- **Extract discard values**: Remove parentheses, extract number

**Example**:
```json
{"R1": "1.0", "R2": "(2.0)", "R3": "6.0 DNC"}
```
Total = 9.0, Discard = 2.0, Nett = **7.0**

### Validation Formula
```
nett_points_raw = total_points_raw - sum_of_discarded_scores
```

---

## 8. COMMON MISTAKES & FIXES

| ❌ WRONG | ✅ CORRECT | Issue |
|---------|-----------|-------|
| `"5"` | `"5.0"` | Missing .0 |
| `"2.0"` (discard) | `"(2.0)"` | Missing parentheses |
| `"-11.0"` | `"(11.0)"` | Minus sign instead of parentheses |
| `"11.0"` (crossed in source) | `"(11.0)"` | Missing parentheses for discard |
| `"DNS"` | `"10.0 DNS"` | Missing score |
| `"10.0DNS"` | `"10.0 DNS"` | Missing space |
| `"10.0.0 DNS"` | `"10.0 DNS"` | Double decimal |
| `"(DNC)"` | `"(10.0 DNC)"` | Missing score in brackets |
| `"6.0  DNC"` | `"6.0 DNC"` | Double space |
| `"dnc"` | `"DNC"` | Wrong case |
| `"(11)"` | `"(11.0)"` | Missing .0 inside parentheses |

---

## 9. SQL QUERIES FOR VALIDATION

### Check for missing .0
```sql
SELECT result_id, helm_name, key, value
FROM public.results,
LATERAL jsonb_each_text(race_scores) AS t(key, value)
WHERE value ~ '^[0-9]+$'  -- Integer only
   OR value ~ '^[0-9]+\.[0-9][0-9]+';  -- Too many decimals
```

### Check for missing parentheses on discards
```sql
-- This requires checking against discard_count
-- See separate validation scripts
```

### Check for penalty code format
```sql
SELECT result_id, helm_name, key, value
FROM public.results,
LATERAL jsonb_each_text(race_scores) AS t(key, value)
WHERE value ~ '[A-Z]'  -- Has penalty code
  AND (
    value !~ '[0-9]\.0 [A-Z]' OR  -- Missing score.0 space code format
    value ~ '[0-9]\.0\.0'          -- Double decimal
  );
```

### Check for missing spaces in penalties
```sql
SELECT result_id, helm_name, key, value
FROM public.results,
LATERAL jsonb_each_text(race_scores) AS t(key, value)
WHERE value ~ '[0-9]\.[0-9][A-Z]';  -- Number directly followed by code
```

---

## 10. HTML DISPLAY RULES

### Styling
- **Normal scores**: Display as-is
- **Discarded scores**: CSS class `disc` (applied if value matches `/^\(.*\)$/`)
- **Penalty codes**: CSS class `code` (applied if value matches `/\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b/i`)

### JavaScript Patterns
```javascript
const PEN = /\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b/i;  // Penalty codes
const DISC = /^\(.*\)$/;  // Discarded scores (parentheses)
```

---

## 11. ENTRY PROCESS RULES

### Pre-Entry Validation (MANDATORY)

**BEFORE** inserting/updating any race_scores, validate:

1. **All penalty codes have scores**:
   - ❌ `"DNC"` → **REJECT** - missing score
   - ✅ `"14.0 DNC"` → **ACCEPT** - has score
   - Check: `WHERE value ~ '[A-Z]' AND value !~ '^[0-9]'` → ERROR

2. **All scores have .0 format**:
   - ❌ `"5"` → **REJECT** - missing .0
   - ✅ `"5.0"` → **ACCEPT**

3. **All discards have parentheses**:
   - ❌ `"2.0"` (when discard) → **REJECT**
   - ✅ `"(2.0)"` → **ACCEPT**

**If ANY validation fails, DO NOT insert data. Fix source data first.**

---

### Step-by-Step Import Process

1. **Read from source** (PDF/results sheet)
   - Identify normal scores: `1`, `2`, `13`, etc.
   - Identify discards: `(11)`, `-11`, `11̶`, etc.
   - Identify penalties: `DNS`, `DNC`, `OCS`, etc.

2. **Transform discard indicators**:
   - **Source `(11)`** → Remove original parentheses → Add `.0` → Add database parentheses → `"(11.0)"`
   - **Source `-11`** → Remove minus sign → Add `.0` → Add parentheses → `"(11.0)"`
   - **Source `11̶` (crossed)** → Remove strikethrough → Add `.0` → Add parentheses → `"(11.0)"`
   - **Source visual discard** → Add `.0` → Add parentheses → `"(11.0)"`

3. **Transform normal scores**:
   - Add `.0` if missing: `"1"` → `"1.0"`
   - Ensure decimal format: `"13"` → `"13.0"`

4. **Transform penalty codes**:
   - Add score if missing: `"DNS"` → `"{entries+1}.0 DNS"`
   - Add space if missing: `"10.0DNS"` → `"10.0 DNS"`
   - Ensure `.0` format: `"10 DNS"` → `"10.0 DNS"`

5. **Transform discarded penalties**:
   - Combine discard + penalty: `"(11 DNS)"` or `"-11 DNS"` → `"(11.0 DNS)"`
   - Ensure proper format: Score + space + code inside parentheses

6. **Validate format** against these rules

7. **Validate** against discard_count (count parentheses matches discard_count)

8. **Store** as JSONB string

---

## 12. SUMMARY CHECKLIST

Before inserting/updating `race_scores`, verify:

### Format Checks
- [ ] All keys are `R1`, `R2`, `R3`... (uppercase R, sequential)
- [ ] All numeric values end with `.0` (not `"1"` or `"1.00"`)
- [ ] Discarded scores have parentheses: `"(2.0)"` (NOT `"-2.0"` or `"2.0"`)
- [ ] Penalty codes have score + space + code: `"10.0 DNS"`
- [ ] Discarded penalties have parentheses: `"(10.0 DNS)"`
- [ ] No double decimals: `"10.0"` not `"10.0.0"`
- [ ] No double spaces: `"10.0 DNS"` not `"10.0  DNS"`
- [ ] All penalty codes are uppercase: `DNC` not `dnc`
- [ ] Sequential races: R1, R2, R3... (no gaps)

### Transformation Checks
- [ ] Source `(11)` → Database `"(11.0)"` (added .0)
- [ ] Source `-11` → Database `"(11.0)"` (removed minus, added parentheses)
- [ ] Source `11̶` (crossed) → Database `"(11.0)"` (removed strikethrough, added parentheses)
- [ ] No minus signs in database: All discards use parentheses only

### Calculation Checks
- [ ] Total matches sum of all race scores
- [ ] Nett matches total minus discarded scores
- [ ] Discard count matches number of parentheses in race_scores

---

**Last Updated**: 2025-01-XX  
**Version**: 1.0  
**Authority**: Database schema and validation rules

