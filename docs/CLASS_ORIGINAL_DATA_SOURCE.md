# class_original - Data Source Explanation

## Purpose
This document explains **where `class_original` data comes from** during the data import process.

---

## Data Source: PDF/Results Sheet (Exact Text)

**`class_original`** comes directly from the **PDF/results sheet** - it is the **exact text** as shown in the source document, with **NO modifications**.

### Source Location in PDF

The `class_original` is extracted from:

1. **Fleet Header Row** in the results sheet
   - Usually shown at the top of a fleet section
   - Example: "OPTIMIST A", "MIRROR (D/H)", "420", "ILCA 7"

2. **Class Column** in the results table
   - Column header: "Class", "Boat Class", or similar
   - Values per row: Individual class names for each sailor

3. **Fleet Name/Designation**
   - May be part of the fleet header
   - Example: "Optimist A Fleet" → extract "Optimist A"

---

## Extraction Process

### Step 1: Identify Class in PDF

When importing from a PDF/results sheet:

1. **Look for class designation** in:
   - Fleet header (e.g., "OPTIMIST A FLEET")
   - Class column in results table
   - Fleet name section

2. **Extract exactly as shown**:
   - Preserve capitalization: "OPTIMIST" stays "OPTIMIST"
   - Preserve formatting: "MIRROR (D/H)" stays "MIRROR (D/H)"
   - Preserve spaces: "ILCA 7" stays "ILCA 7"
   - Preserve punctuation: "(D/H)", "(S/H)" stay as-is

3. **Store in `class_original`**:
   - No normalization
   - No case changes
   - No abbreviation expansion
   - **EXACT COPY** from PDF

### Step 2: Normalize to class_canonical

After extracting `class_original`, create `class_canonical`:
- Normalize to standard format
- Match `classes.class_name` table
- Use consistent capitalization
- Remove parenthetical notes if needed

---

## Examples

### Example 1: Optimist
**PDF Shows**: `OPTIMIST A`  
**class_original**: `OPTIMIST A` (exact copy, uppercase)  
**class_canonical**: `Optimist A` (normalized, title case)

### Example 2: Mirror
**PDF Shows**: `MIRROR (D/H)`  
**class_original**: `MIRROR (D/H)` (exact copy, with parenthetical)  
**class_canonical**: `Mirror` (normalized, parenthetical removed)

### Example 3: ILCA/Laser
**PDF Shows**: `ILCA 7` or `LASER`  
**class_original**: `ILCA 7` or `LASER` (exact copy)  
**class_canonical**: `ILCA 7` (standardized)

### Example 4: 29Er/49Er
**PDF Shows**: `29ER` or `49er` or `29er`  
**class_original**: `29ER` or `49er` or `29er` (exact copy, preserves PDF format)  
**class_canonical**: `29Er` (normalized to standard: capital E, lowercase r)

### Example 5: Extra
**PDF Shows**: `EXTRA (S/H)`  
**class_original**: `EXTRA (S/H)` (exact copy)  
**class_canonical**: `Xtra` (normalized, parenthetical removed)

---

## Data Flow

```
PDF/Results Sheet
    ↓
OCR or Manual Entry
    ↓
Extract Class Name (EXACT TEXT)
    ↓
class_original = "MIRROR (D/H)"  ← STORED AS-IS
    ↓
Normalize/Standardize
    ↓
class_canonical = "Mirror"  ← STANDARDIZED
```

---

## Rules for class_original

### ✅ DO

1. **Preserve exactly** as shown in PDF
2. **Keep capitalization** from source (uppercase, lowercase, mixed)
3. **Keep parenthetical notes** (e.g., "(D/H)", "(S/H)")
4. **Keep spaces** (e.g., "ILCA 7" not "ILCA7")
5. **Keep special characters** as shown
6. **Extract from PDF** - never invent or guess

### ❌ DON'T

1. **Don't normalize** - that's what `class_canonical` is for
2. **Don't change case** - preserve PDF capitalization
3. **Don't remove parentheticals** - keep "(D/H)", "(S/H)" if shown
4. **Don't expand abbreviations** - "ILCA" stays "ILCA", not "International Laser Class Association"
5. **Don't translate** - keep original language/format
6. **Don't guess** - if PDF doesn't show class, leave as NULL or extract what's there

---

## Use Cases

### When to Use class_original

1. **Preserving Source Document**: See exactly what PDF showed
2. **Debugging**: Compare with PDF to verify extraction accuracy
3. **Audit Trail**: Know original source format
4. **Historical Accuracy**: Maintain exact representation of source

### When to Use class_canonical

1. **Grouping**: Group results by standardized class
2. **Display**: Show consistent class names in UI
3. **Filtering**: Filter by standardized class names
4. **Reporting**: Use standardized format for reports

---

## Database Schema

```sql
class_original TEXT NOT NULL  -- Exact text from PDF
class_canonical TEXT NOT NULL -- Standardized class name (matches classes.class_name)
```

**Both fields are MANDATORY** - `class_original` for source preservation, `class_canonical` for standardization.

---

## Common Patterns in PDFs

### Pattern 1: Uppercase
**PDF**: `OPTIMIST`, `MIRROR`, `420`  
**class_original**: `OPTIMIST`, `MIRROR`, `420`

### Pattern 2: With Parenthetical
**PDF**: `MIRROR (D/H)`, `EXTRA (S/H)`  
**class_original**: `MIRROR (D/H)`, `EXTRA (S/H)`

### Pattern 3: Mixed Case
**PDF**: `Optimist A`, `ILCA 7`, `29ER`  
**class_original**: `Optimist A`, `ILCA 7`, `29ER`

### Pattern 4: Abbreviated
**PDF**: `LASER`, `LASER RADIAL`, `ILCA 4.7`  
**class_original**: `LASER`, `LASER RADIAL`, `ILCA 4.7`

---

## Data Entry Process

### During Import

1. **Open PDF/results sheet**
2. **Find class designation** (fleet header, class column)
3. **Extract exact text** (copy exactly, no changes)
4. **Store in `class_original`**: `INSERT ... class_original = 'MIRROR (D/H)'`
5. **Normalize to `class_canonical`**: `INSERT ... class_canonical = 'Mirror'`
6. **Verify both populated**: Both fields are MANDATORY

---

## Validation

### After Import

Check that `class_original` matches PDF:

```sql
-- Compare class_original with PDF
SELECT 
    block_id,
    class_original,
    class_canonical,
    COUNT(*) as entries
FROM public.results
WHERE block_id = 'your-block-id'
GROUP BY block_id, class_original, class_canonical;

-- Verify: class_original should match PDF exactly
```

---

## HTML Usage Rules

### ❌ CRITICAL: `class_original` CANNOT be used in HTML

**Why `class_original` cannot be used in HTML:**
1. **Not validated** - `class_original` is NOT validated against `classes` table
2. **May contain errors** - PDF/results sheets often have misspellings, wrong formats, or incorrect class names
3. **Not corrected** - `class_original` preserves PDF exactly, including errors
4. **Not in `classes` table** - May reference classes that don't exist in the database

**Examples of PDF errors in `class_original`:**
- `Lazer 7` (wrong) → Should be `ILCA 7` (correct)
- `29-er` (wrong) → Should be `29Er` (correct)
- `Optimist B` (wrong if it should be `Optimist A`)
- `Mirror D/H` (wrong format) → Should be `Mirror` (correct)

### ✅ HTML MUST use `class_canonical` ONLY

**Why `class_canonical` must be used:**
1. **Validated** - `class_canonical` MUST exist in `classes.class_name` table
2. **Corrected** - During data entry, if PDF shows wrong class, it gets corrected to valid class
3. **Standardized** - Format matches `classes.class_name` exactly
4. **Trusted** - Only contains classes that exist in `classes` table

**Data Entry Process:**
```
PDF shows "Lazer 7" (WRONG)
    ↓
class_original = 'Lazer 7' (preserves PDF error)
    ↓
Validate against classes.class_name table
    ↓
Correct to valid class: 'ILCA 7'
    ↓
class_canonical = 'ILCA 7' (validated, corrected, exists in classes table)
    ↓
HTML uses class_canonical = 'ILCA 7' ✅
```

**HTML Fallback (Safety Only):**
- HTML may show `class_canonical||class_original||''` as a safety fallback
- This is ONLY for cases where `class_canonical` is NULL (data entry error)
- If `class_canonical` is NULL, **THIS IS A DATA ENTRY ERROR** and must be fixed
- `class_original` fallback should NEVER be relied upon in production

---

## Summary

**`class_original` = EXACT TEXT FROM PDF/RESULTS SHEET (NOT VALIDATED)**

- Source: PDF/results sheet (fleet header, class column)
- Format: Exact copy - no normalization, no case changes
- Purpose: Preserve original source document representation (audit trail, debugging)
- **Validation**: ❌ NOT validated against `classes` table
- **HTML Usage**: ❌ **CANNOT be used in HTML** - May contain errors
- Must be populated: MANDATORY field (NOT NULL)

**`class_canonical` = VALIDATED CLASS FROM `classes` TABLE (ONLY VALID FOR HTML)**

- **Validation**: ✅ MUST exist in `classes.class_name` table
- **Correction**: ✅ Corrected during data entry if PDF is wrong
- **HTML Usage**: ✅ **ONLY valid class for HTML** - Validated and corrected
- Must be populated: MANDATORY field (NOT NULL)

**Key Point**: 
- `class_original` = What PDF actually showed (may be wrong, NOT validated, for audit/debugging only)
- `class_canonical` = Validated, corrected class from `classes` table (ONLY valid class for HTML)


## Purpose
This document explains **where `class_original` data comes from** during the data import process.

---

## Data Source: PDF/Results Sheet (Exact Text)

**`class_original`** comes directly from the **PDF/results sheet** - it is the **exact text** as shown in the source document, with **NO modifications**.

### Source Location in PDF

The `class_original` is extracted from:

1. **Fleet Header Row** in the results sheet
   - Usually shown at the top of a fleet section
   - Example: "OPTIMIST A", "MIRROR (D/H)", "420", "ILCA 7"

2. **Class Column** in the results table
   - Column header: "Class", "Boat Class", or similar
   - Values per row: Individual class names for each sailor

3. **Fleet Name/Designation**
   - May be part of the fleet header
   - Example: "Optimist A Fleet" → extract "Optimist A"

---

## Extraction Process

### Step 1: Identify Class in PDF

When importing from a PDF/results sheet:

1. **Look for class designation** in:
   - Fleet header (e.g., "OPTIMIST A FLEET")
   - Class column in results table
   - Fleet name section

2. **Extract exactly as shown**:
   - Preserve capitalization: "OPTIMIST" stays "OPTIMIST"
   - Preserve formatting: "MIRROR (D/H)" stays "MIRROR (D/H)"
   - Preserve spaces: "ILCA 7" stays "ILCA 7"
   - Preserve punctuation: "(D/H)", "(S/H)" stay as-is

3. **Store in `class_original`**:
   - No normalization
   - No case changes
   - No abbreviation expansion
   - **EXACT COPY** from PDF

### Step 2: Normalize to class_canonical

After extracting `class_original`, create `class_canonical`:
- Normalize to standard format
- Match `classes.class_name` table
- Use consistent capitalization
- Remove parenthetical notes if needed

---

## Examples

### Example 1: Optimist
**PDF Shows**: `OPTIMIST A`  
**class_original**: `OPTIMIST A` (exact copy, uppercase)  
**class_canonical**: `Optimist A` (normalized, title case)

### Example 2: Mirror
**PDF Shows**: `MIRROR (D/H)`  
**class_original**: `MIRROR (D/H)` (exact copy, with parenthetical)  
**class_canonical**: `Mirror` (normalized, parenthetical removed)

### Example 3: ILCA/Laser
**PDF Shows**: `ILCA 7` or `LASER`  
**class_original**: `ILCA 7` or `LASER` (exact copy)  
**class_canonical**: `ILCA 7` (standardized)

### Example 4: 29Er/49Er
**PDF Shows**: `29ER` or `49er` or `29er`  
**class_original**: `29ER` or `49er` or `29er` (exact copy, preserves PDF format)  
**class_canonical**: `29Er` (normalized to standard: capital E, lowercase r)

### Example 5: Extra
**PDF Shows**: `EXTRA (S/H)`  
**class_original**: `EXTRA (S/H)` (exact copy)  
**class_canonical**: `Xtra` (normalized, parenthetical removed)

---

## Data Flow

```
PDF/Results Sheet
    ↓
OCR or Manual Entry
    ↓
Extract Class Name (EXACT TEXT)
    ↓
class_original = "MIRROR (D/H)"  ← STORED AS-IS
    ↓
Normalize/Standardize
    ↓
class_canonical = "Mirror"  ← STANDARDIZED
```

---

## Rules for class_original

### ✅ DO

1. **Preserve exactly** as shown in PDF
2. **Keep capitalization** from source (uppercase, lowercase, mixed)
3. **Keep parenthetical notes** (e.g., "(D/H)", "(S/H)")
4. **Keep spaces** (e.g., "ILCA 7" not "ILCA7")
5. **Keep special characters** as shown
6. **Extract from PDF** - never invent or guess

### ❌ DON'T

1. **Don't normalize** - that's what `class_canonical` is for
2. **Don't change case** - preserve PDF capitalization
3. **Don't remove parentheticals** - keep "(D/H)", "(S/H)" if shown
4. **Don't expand abbreviations** - "ILCA" stays "ILCA", not "International Laser Class Association"
5. **Don't translate** - keep original language/format
6. **Don't guess** - if PDF doesn't show class, leave as NULL or extract what's there

---

## Use Cases

### When to Use class_original

1. **Preserving Source Document**: See exactly what PDF showed
2. **Debugging**: Compare with PDF to verify extraction accuracy
3. **Audit Trail**: Know original source format
4. **Historical Accuracy**: Maintain exact representation of source

### When to Use class_canonical

1. **Grouping**: Group results by standardized class
2. **Display**: Show consistent class names in UI
3. **Filtering**: Filter by standardized class names
4. **Reporting**: Use standardized format for reports

---

## Database Schema

```sql
class_original TEXT NOT NULL  -- Exact text from PDF
class_canonical TEXT NOT NULL -- Standardized class name (matches classes.class_name)
```

**Both fields are MANDATORY** - `class_original` for source preservation, `class_canonical` for standardization.

---

## Common Patterns in PDFs

### Pattern 1: Uppercase
**PDF**: `OPTIMIST`, `MIRROR`, `420`  
**class_original**: `OPTIMIST`, `MIRROR`, `420`

### Pattern 2: With Parenthetical
**PDF**: `MIRROR (D/H)`, `EXTRA (S/H)`  
**class_original**: `MIRROR (D/H)`, `EXTRA (S/H)`

### Pattern 3: Mixed Case
**PDF**: `Optimist A`, `ILCA 7`, `29ER`  
**class_original**: `Optimist A`, `ILCA 7`, `29ER`

### Pattern 4: Abbreviated
**PDF**: `LASER`, `LASER RADIAL`, `ILCA 4.7`  
**class_original**: `LASER`, `LASER RADIAL`, `ILCA 4.7`

---

## Data Entry Process

### During Import

1. **Open PDF/results sheet**
2. **Find class designation** (fleet header, class column)
3. **Extract exact text** (copy exactly, no changes)
4. **Store in `class_original`**: `INSERT ... class_original = 'MIRROR (D/H)'`
5. **Normalize to `class_canonical`**: `INSERT ... class_canonical = 'Mirror'`
6. **Verify both populated**: Both fields are MANDATORY

---

## Validation

### After Import

Check that `class_original` matches PDF:

```sql
-- Compare class_original with PDF
SELECT 
    block_id,
    class_original,
    class_canonical,
    COUNT(*) as entries
FROM public.results
WHERE block_id = 'your-block-id'
GROUP BY block_id, class_original, class_canonical;

-- Verify: class_original should match PDF exactly
```

---

## HTML Usage Rules

### ❌ CRITICAL: `class_original` CANNOT be used in HTML

**Why `class_original` cannot be used in HTML:**
1. **Not validated** - `class_original` is NOT validated against `classes` table
2. **May contain errors** - PDF/results sheets often have misspellings, wrong formats, or incorrect class names
3. **Not corrected** - `class_original` preserves PDF exactly, including errors
4. **Not in `classes` table** - May reference classes that don't exist in the database

**Examples of PDF errors in `class_original`:**
- `Lazer 7` (wrong) → Should be `ILCA 7` (correct)
- `29-er` (wrong) → Should be `29Er` (correct)
- `Optimist B` (wrong if it should be `Optimist A`)
- `Mirror D/H` (wrong format) → Should be `Mirror` (correct)

### ✅ HTML MUST use `class_canonical` ONLY

**Why `class_canonical` must be used:**
1. **Validated** - `class_canonical` MUST exist in `classes.class_name` table
2. **Corrected** - During data entry, if PDF shows wrong class, it gets corrected to valid class
3. **Standardized** - Format matches `classes.class_name` exactly
4. **Trusted** - Only contains classes that exist in `classes` table

**Data Entry Process:**
```
PDF shows "Lazer 7" (WRONG)
    ↓
class_original = 'Lazer 7' (preserves PDF error)
    ↓
Validate against classes.class_name table
    ↓
Correct to valid class: 'ILCA 7'
    ↓
class_canonical = 'ILCA 7' (validated, corrected, exists in classes table)
    ↓
HTML uses class_canonical = 'ILCA 7' ✅
```

**HTML Fallback (Safety Only):**
- HTML may show `class_canonical||class_original||''` as a safety fallback
- This is ONLY for cases where `class_canonical` is NULL (data entry error)
- If `class_canonical` is NULL, **THIS IS A DATA ENTRY ERROR** and must be fixed
- `class_original` fallback should NEVER be relied upon in production

---

## Summary

**`class_original` = EXACT TEXT FROM PDF/RESULTS SHEET (NOT VALIDATED)**

- Source: PDF/results sheet (fleet header, class column)
- Format: Exact copy - no normalization, no case changes
- Purpose: Preserve original source document representation (audit trail, debugging)
- **Validation**: ❌ NOT validated against `classes` table
- **HTML Usage**: ❌ **CANNOT be used in HTML** - May contain errors
- Must be populated: MANDATORY field (NOT NULL)

**`class_canonical` = VALIDATED CLASS FROM `classes` TABLE (ONLY VALID FOR HTML)**

- **Validation**: ✅ MUST exist in `classes.class_name` table
- **Correction**: ✅ Corrected during data entry if PDF is wrong
- **HTML Usage**: ✅ **ONLY valid class for HTML** - Validated and corrected
- Must be populated: MANDATORY field (NOT NULL)

**Key Point**: 
- `class_original` = What PDF actually showed (may be wrong, NOT validated, for audit/debugging only)
- `class_canonical` = Validated, corrected class from `classes` table (ONLY valid class for HTML)

