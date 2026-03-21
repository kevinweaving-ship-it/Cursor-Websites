# class_canonical - Validation Rules

## Purpose
This document explains **how `class_canonical` is validated** against the `classes` table and why it is **CRITICAL** for HTML filtering/searching. Invalid `class_canonical` values break filtering - results won't be found when searching for the same class.

**CRITICAL FILTERING ISSUE**: If `class_canonical` doesn't exactly match `classes.class_name`, HTML filter/search will miss results. Example: `Ilca 4` (invalid) vs `Ilca 4.7` (valid) - they won't be grouped together.

**AUTHORITATIVE SOURCE**: `classes.class_name` is the **ONLY source of truth** for class names. All `results.class_canonical` values **MUST** match `classes.class_name` exactly. This ensures consistency across both tables and prevents issues like `29Er` in one table and `29er` in another.

---

## CRITICAL RULE: HTML MUST Use `class_canonical` ONLY

### ❌ `class_original` CANNOT be used in HTML

**Why:**
1. **Not validated** - `class_original` is NOT checked against `classes` table
2. **May contain errors** - PDF/results sheets often have:
   - Misspellings: `Lazer 7` instead of `ILCA 7`
   - Wrong formats: `29-er` instead of `29Er`
   - Incorrect class names
   - Typos or formatting issues
3. **Preserves PDF errors** - `class_original` keeps PDF exactly as shown (including errors)
4. **May not exist in database** - Could reference classes that don't exist in `classes` table

### ✅ `class_canonical` MUST be used in HTML

**Why:**
1. **Validated** - `class_canonical` MUST exist in `classes.class_name` table
2. **Corrected** - During data entry, if PDF shows wrong class, it gets corrected
3. **Standardized** - Format matches `classes.class_name` **EXACTLY** (case-sensitive, no variations)
4. **Trusted** - Only contains classes that exist in `classes` table
5. **CRITICAL FOR FILTERING** - HTML filter/search uses `class_canonical` to find all results. If invalid (e.g., `Ilca 4` instead of `Ilca 4.7`), those results won't be found when filtering.

**Filtering Example - Why Validation is Critical:**
```
Search for "Ilca 4.7" class:
- ✅ class_canonical = 'Ilca 4.7' → Found (5 results)
- ❌ class_canonical = 'Ilca 4' → NOT Found (5 results LOST!)

Total results: 10, but only 5 found in search!
This is why EXACT match with classes.class_name is CRITICAL.
```

---

## Validation Process

### Step 1: Extract `class_original` from PDF

```
PDF shows: "Lazer 7"
    ↓
class_original = 'Lazer 7' (exact copy, preserves PDF error)
```

### Step 2: Validate against `classes.class_name` table (AUTHORITATIVE SOURCE)

**IMPORTANT**: `classes.class_name` is the **AUTHORITATIVE SOURCE** - all formatting, spelling, and capitalization comes from here.

**Query to check if class exists:**
```sql
SELECT class_name FROM public.classes 
WHERE class_name = 'Lazer 7';
-- Returns: No rows (class doesn't exist)
```

**Query to get exact format from classes table:**
```sql
SELECT class_name FROM public.classes 
WHERE class_name ILIKE '%laser%' OR class_name ILIKE '%ilca%';
-- Returns: 'Ilca 7' (this is the EXACT format to use)
```

### Step 3: Find correct class in `classes` table

**Query to find similar class:**
```sql
SELECT class_name FROM public.classes 
WHERE class_name ILIKE '%lazer%' OR class_name ILIKE '%laser%' OR class_name ILIKE '%ilca%';
-- Returns: 'ILCA 7'
```

### Step 4: Correct to valid class (USE EXACT FORMAT FROM classes.class_name)

```
PDF showed: "Lazer 7" (WRONG - doesn't exist in classes table)
    ↓
Validate against classes.class_name (AUTHORITATIVE SOURCE)
    ↓
Find correct class: 'Ilca 7' (from classes.class_name - use EXACT format)
    ↓
class_canonical = 'Ilca 7' (matches classes.class_name EXACTLY - validated, corrected)
```

**CRITICAL**: Copy the **EXACT** format from `classes.class_name`:
- `classes.class_name = '29Er'` → `results.class_canonical = '29Er'` (NOT `29er`)
- `classes.class_name = '49Er'` → `results.class_canonical = '49Er'` (NOT `49er`)
- `classes.class_name = 'Ilca 4.7'` → `results.class_canonical = 'Ilca 4.7'` (NOT `Ilca 4`)

### Step 5: Store both fields

```sql
INSERT INTO public.results (
    class_original,    -- 'Lazer 7' (preserves PDF error for audit)
    class_canonical    -- 'ILCA 7' (validated, corrected, valid for HTML)
) VALUES (
    'Lazer 7',         -- Exact from PDF (NOT validated)
    'ILCA 7'           -- Validated from classes table (ONLY valid for HTML)
);
```

---

## Data Entry Workflow

### Complete Validation Process

1. **Extract from PDF**:
   ```
   PDF: "Lazer 7"
   → class_original = 'Lazer 7'
   ```

2. **Check `classes` table**:
   ```sql
   SELECT class_name FROM public.classes WHERE class_name = 'Lazer 7';
   -- Result: No rows (invalid class)
   ```

3. **Find correct class**:
   ```sql
   SELECT class_name FROM public.classes 
   WHERE class_name ILIKE '%ilca%' OR class_name ILIKE '%laser%';
   -- Result: 'ILCA 7'
   ```

4. **Store validated class**:
   ```sql
   class_canonical = 'ILCA 7'  -- From classes table (valid)
   ```

5. **Verify both fields**:
   ```sql
   -- Both must be populated
   class_original = 'Lazer 7'    -- Preserves PDF (for audit)
   class_canonical = 'ILCA 7'    -- Validated (for HTML)
   ```

---

## Examples of Validation & Correction

### Example 1: Misspelling
**PDF**: `Lazer 7`  
**class_original**: `Lazer 7` (preserves PDF error)  
**Validation**: ❌ Not in `classes` table  
**Correct Class**: `ILCA 7` (from `classes` table)  
**class_canonical**: `ILCA 7` ✅ (validated, corrected)

### Example 2: Wrong Format
**PDF**: `29-er`  
**class_original**: `29-er` (preserves PDF format)  
**Validation**: ❌ Not in `classes` table  
**Correct Class**: `29Er` (from `classes` table)  
**class_canonical**: `29Er` ✅ (validated, corrected)

### Example 3: Correct PDF
**PDF**: `ILCA 7`  
**class_original**: `ILCA 7` (exact copy)  
**Validation**: ✅ Exists in `classes` table  
**Correct Class**: `ILCA 7` (same as PDF)  
**class_canonical**: `ILCA 7` ✅ (validated, matches PDF)

### Example 4: Parenthetical Notes
**PDF**: `MIRROR (D/H)`  
**class_original**: `MIRROR (D/H)` (preserves parenthetical)  
**Validation**: ❌ Not in `classes` table (parenthetical not valid)  
**Correct Class**: `Mirror` (from `classes` table, parenthetical removed)  
**class_canonical**: `Mirror` ✅ (validated, corrected)

---

## Validation Rules

### ✅ MUST DO

1. **Validate every `class_canonical`** against `classes.class_name` table - **MANDATORY**
2. **Use EXACT match** - `class_canonical` must match `classes.class_name` **EXACTLY** (case-sensitive, no variations)
3. **Correct if PDF is wrong** - Find correct class from `classes` table (e.g., `Ilca 4` → `Ilca 4.7`)
4. **Populate both fields** - `class_original` (PDF) and `class_canonical` (validated)
5. **Manual Override** - Only if authorized (document override and reason)

### ❌ CRITICAL - Must NOT DO

1. **Don't use variations** - `Ilca 4` is NOT valid if `classes.class_name` is `Ilca 4.7`
2. **Don't use close matches** - Must be exact match from `classes.class_name`
3. **Don't skip validation** - Every `class_canonical` MUST exist in `classes` table (or be manually overridden)
4. **Don't use invalid classes** - Breaks HTML filtering/searching

### Examples of Invalid `class_canonical` (Breaking Filtering):

| Invalid (WRONG) | Valid (CORRECT) | Impact |
|----------------|-----------------|--------|
| `Ilca 4` | `Ilca 4.7` | 5 results won't be found when filtering for "Ilca 4.7" |
| `29er` | `29Er` | 10 results won't be found when filtering for "29Er" |
| `49er` | `49Er` | 2 results won't be found when filtering for "49Er" |
| `ILCA 7` | `Ilca 7` | Results won't be found if case doesn't match |

### ❌ MUST NOT DO

1. **Don't use `class_original` in HTML** - Not validated, may contain errors
2. **Don't leave `class_canonical` NULL** - Must be populated with valid class
3. **Don't use classes not in `classes` table** - Must validate first
4. **Don't skip validation** - Every `class_canonical` must exist in `classes` table

---

## Database Schema

```sql
-- classes table (authoritative source)
CREATE TABLE public.classes (
    class_id INTEGER PRIMARY KEY,
    class_name TEXT NOT NULL UNIQUE  -- Valid classes only
);

-- results table
CREATE TABLE public.results (
    class_original TEXT NOT NULL,    -- PDF exact copy (NOT validated)
    class_canonical TEXT NOT NULL     -- Validated from classes.class_name (ONLY valid for HTML)
);
```

---

## HTML Usage

### ✅ CORRECT - Use `class_canonical`

```javascript
// ✅ CORRECT - Use validated class_canonical
const displayClass = result.class_canonical || '';  // Only valid classes

// ❌ WRONG - Don't use class_original (not validated)
const displayClass = result.class_original || '';   // May contain errors
```

### Current HTML Implementation

```javascript
// Line 468 in regatta_viewer.html
<td>${r.class_canonical||''}</td>
```

**Notes:**
- Uses `class_canonical` only ✅ (correct - no fallback to `class_original`)
- If `class_canonical` is NULL or empty → **THIS IS A DATA ENTRY ERROR** and must be fixed
- `class_canonical` must be validated from `classes.class_name` table with EXACT match

---

## Validation Checksum

### After Data Entry

Run this query to verify all `class_canonical` values are valid:

```sql
-- Find invalid class_canonical (not in classes table)
SELECT DISTINCT
    r.class_canonical,
    'INVALID - Not in classes table' as error
FROM public.results r
LEFT JOIN public.classes c ON r.class_canonical = c.class_name
WHERE r.class_canonical IS NOT NULL
  AND c.class_name IS NULL
ORDER BY r.class_canonical;
```

**Expected Result**: No rows (all `class_canonical` values should exist in `classes` table)

---

## Summary

**`class_canonical` Validation Rules:**

1. ✅ **MUST exist in `classes.class_name` table** - Cannot use invalid classes (unless manually overridden - see `docs/CLASS_CANONICAL_MANUAL_OVERRIDE.md`)
2. ✅ **MUST be EXACT match** - Must match `classes.class_name` exactly (case-sensitive, no variations like `Ilca 4` vs `Ilca 4.7`)
3. ✅ **MUST be corrected** - If PDF shows wrong class (e.g., `Ilca 4`), correct to valid class (`Ilca 4.7`)
4. ✅ **ONLY valid class for HTML** - HTML must use `class_canonical`, never `class_original`
5. ✅ **MANDATORY field** - Never NULL or empty
6. ✅ **CRITICAL FOR FILTERING** - Invalid `class_canonical` breaks HTML filter/search (results won't be found)

**Why Validation is Critical:**
- HTML filter/search uses `class_canonical` to find all results of the same class
- If invalid (e.g., `Ilca 4` instead of `Ilca 4.7`), those results **won't be found** when filtering
- Example: 10 ILCA 4.7 sailors, but 5 have `class_canonical = 'Ilca 4'` → only 5 found in search!

**Key Point**: 
- `class_original` = PDF exact copy (may be wrong, NOT validated, for audit only)
- `class_canonical` = Validated from `classes` table with **EXACT match** (ONLY valid class for HTML, critical for filtering)

**See Also**: `docs/CLASS_CANONICAL_MANUAL_OVERRIDE.md` for override process (rare exceptions only)


## Purpose
This document explains **how `class_canonical` is validated** against the `classes` table and why it is **CRITICAL** for HTML filtering/searching. Invalid `class_canonical` values break filtering - results won't be found when searching for the same class.

**CRITICAL FILTERING ISSUE**: If `class_canonical` doesn't exactly match `classes.class_name`, HTML filter/search will miss results. Example: `Ilca 4` (invalid) vs `Ilca 4.7` (valid) - they won't be grouped together.

**AUTHORITATIVE SOURCE**: `classes.class_name` is the **ONLY source of truth** for class names. All `results.class_canonical` values **MUST** match `classes.class_name` exactly. This ensures consistency across both tables and prevents issues like `29Er` in one table and `29er` in another.

---

## CRITICAL RULE: HTML MUST Use `class_canonical` ONLY

### ❌ `class_original` CANNOT be used in HTML

**Why:**
1. **Not validated** - `class_original` is NOT checked against `classes` table
2. **May contain errors** - PDF/results sheets often have:
   - Misspellings: `Lazer 7` instead of `ILCA 7`
   - Wrong formats: `29-er` instead of `29Er`
   - Incorrect class names
   - Typos or formatting issues
3. **Preserves PDF errors** - `class_original` keeps PDF exactly as shown (including errors)
4. **May not exist in database** - Could reference classes that don't exist in `classes` table

### ✅ `class_canonical` MUST be used in HTML

**Why:**
1. **Validated** - `class_canonical` MUST exist in `classes.class_name` table
2. **Corrected** - During data entry, if PDF shows wrong class, it gets corrected
3. **Standardized** - Format matches `classes.class_name` **EXACTLY** (case-sensitive, no variations)
4. **Trusted** - Only contains classes that exist in `classes` table
5. **CRITICAL FOR FILTERING** - HTML filter/search uses `class_canonical` to find all results. If invalid (e.g., `Ilca 4` instead of `Ilca 4.7`), those results won't be found when filtering.

**Filtering Example - Why Validation is Critical:**
```
Search for "Ilca 4.7" class:
- ✅ class_canonical = 'Ilca 4.7' → Found (5 results)
- ❌ class_canonical = 'Ilca 4' → NOT Found (5 results LOST!)

Total results: 10, but only 5 found in search!
This is why EXACT match with classes.class_name is CRITICAL.
```

---

## Validation Process

### Step 1: Extract `class_original` from PDF

```
PDF shows: "Lazer 7"
    ↓
class_original = 'Lazer 7' (exact copy, preserves PDF error)
```

### Step 2: Validate against `classes.class_name` table (AUTHORITATIVE SOURCE)

**IMPORTANT**: `classes.class_name` is the **AUTHORITATIVE SOURCE** - all formatting, spelling, and capitalization comes from here.

**Query to check if class exists:**
```sql
SELECT class_name FROM public.classes 
WHERE class_name = 'Lazer 7';
-- Returns: No rows (class doesn't exist)
```

**Query to get exact format from classes table:**
```sql
SELECT class_name FROM public.classes 
WHERE class_name ILIKE '%laser%' OR class_name ILIKE '%ilca%';
-- Returns: 'Ilca 7' (this is the EXACT format to use)
```

### Step 3: Find correct class in `classes` table

**Query to find similar class:**
```sql
SELECT class_name FROM public.classes 
WHERE class_name ILIKE '%lazer%' OR class_name ILIKE '%laser%' OR class_name ILIKE '%ilca%';
-- Returns: 'ILCA 7'
```

### Step 4: Correct to valid class (USE EXACT FORMAT FROM classes.class_name)

```
PDF showed: "Lazer 7" (WRONG - doesn't exist in classes table)
    ↓
Validate against classes.class_name (AUTHORITATIVE SOURCE)
    ↓
Find correct class: 'Ilca 7' (from classes.class_name - use EXACT format)
    ↓
class_canonical = 'Ilca 7' (matches classes.class_name EXACTLY - validated, corrected)
```

**CRITICAL**: Copy the **EXACT** format from `classes.class_name`:
- `classes.class_name = '29Er'` → `results.class_canonical = '29Er'` (NOT `29er`)
- `classes.class_name = '49Er'` → `results.class_canonical = '49Er'` (NOT `49er`)
- `classes.class_name = 'Ilca 4.7'` → `results.class_canonical = 'Ilca 4.7'` (NOT `Ilca 4`)

### Step 5: Store both fields

```sql
INSERT INTO public.results (
    class_original,    -- 'Lazer 7' (preserves PDF error for audit)
    class_canonical    -- 'ILCA 7' (validated, corrected, valid for HTML)
) VALUES (
    'Lazer 7',         -- Exact from PDF (NOT validated)
    'ILCA 7'           -- Validated from classes table (ONLY valid for HTML)
);
```

---

## Data Entry Workflow

### Complete Validation Process

1. **Extract from PDF**:
   ```
   PDF: "Lazer 7"
   → class_original = 'Lazer 7'
   ```

2. **Check `classes` table**:
   ```sql
   SELECT class_name FROM public.classes WHERE class_name = 'Lazer 7';
   -- Result: No rows (invalid class)
   ```

3. **Find correct class**:
   ```sql
   SELECT class_name FROM public.classes 
   WHERE class_name ILIKE '%ilca%' OR class_name ILIKE '%laser%';
   -- Result: 'ILCA 7'
   ```

4. **Store validated class**:
   ```sql
   class_canonical = 'ILCA 7'  -- From classes table (valid)
   ```

5. **Verify both fields**:
   ```sql
   -- Both must be populated
   class_original = 'Lazer 7'    -- Preserves PDF (for audit)
   class_canonical = 'ILCA 7'    -- Validated (for HTML)
   ```

---

## Examples of Validation & Correction

### Example 1: Misspelling
**PDF**: `Lazer 7`  
**class_original**: `Lazer 7` (preserves PDF error)  
**Validation**: ❌ Not in `classes` table  
**Correct Class**: `ILCA 7` (from `classes` table)  
**class_canonical**: `ILCA 7` ✅ (validated, corrected)

### Example 2: Wrong Format
**PDF**: `29-er`  
**class_original**: `29-er` (preserves PDF format)  
**Validation**: ❌ Not in `classes` table  
**Correct Class**: `29Er` (from `classes` table)  
**class_canonical**: `29Er` ✅ (validated, corrected)

### Example 3: Correct PDF
**PDF**: `ILCA 7`  
**class_original**: `ILCA 7` (exact copy)  
**Validation**: ✅ Exists in `classes` table  
**Correct Class**: `ILCA 7` (same as PDF)  
**class_canonical**: `ILCA 7` ✅ (validated, matches PDF)

### Example 4: Parenthetical Notes
**PDF**: `MIRROR (D/H)`  
**class_original**: `MIRROR (D/H)` (preserves parenthetical)  
**Validation**: ❌ Not in `classes` table (parenthetical not valid)  
**Correct Class**: `Mirror` (from `classes` table, parenthetical removed)  
**class_canonical**: `Mirror` ✅ (validated, corrected)

---

## Validation Rules

### ✅ MUST DO

1. **Validate every `class_canonical`** against `classes.class_name` table - **MANDATORY**
2. **Use EXACT match** - `class_canonical` must match `classes.class_name` **EXACTLY** (case-sensitive, no variations)
3. **Correct if PDF is wrong** - Find correct class from `classes` table (e.g., `Ilca 4` → `Ilca 4.7`)
4. **Populate both fields** - `class_original` (PDF) and `class_canonical` (validated)
5. **Manual Override** - Only if authorized (document override and reason)

### ❌ CRITICAL - Must NOT DO

1. **Don't use variations** - `Ilca 4` is NOT valid if `classes.class_name` is `Ilca 4.7`
2. **Don't use close matches** - Must be exact match from `classes.class_name`
3. **Don't skip validation** - Every `class_canonical` MUST exist in `classes` table (or be manually overridden)
4. **Don't use invalid classes** - Breaks HTML filtering/searching

### Examples of Invalid `class_canonical` (Breaking Filtering):

| Invalid (WRONG) | Valid (CORRECT) | Impact |
|----------------|-----------------|--------|
| `Ilca 4` | `Ilca 4.7` | 5 results won't be found when filtering for "Ilca 4.7" |
| `29er` | `29Er` | 10 results won't be found when filtering for "29Er" |
| `49er` | `49Er` | 2 results won't be found when filtering for "49Er" |
| `ILCA 7` | `Ilca 7` | Results won't be found if case doesn't match |

### ❌ MUST NOT DO

1. **Don't use `class_original` in HTML** - Not validated, may contain errors
2. **Don't leave `class_canonical` NULL** - Must be populated with valid class
3. **Don't use classes not in `classes` table** - Must validate first
4. **Don't skip validation** - Every `class_canonical` must exist in `classes` table

---

## Database Schema

```sql
-- classes table (authoritative source)
CREATE TABLE public.classes (
    class_id INTEGER PRIMARY KEY,
    class_name TEXT NOT NULL UNIQUE  -- Valid classes only
);

-- results table
CREATE TABLE public.results (
    class_original TEXT NOT NULL,    -- PDF exact copy (NOT validated)
    class_canonical TEXT NOT NULL     -- Validated from classes.class_name (ONLY valid for HTML)
);
```

---

## HTML Usage

### ✅ CORRECT - Use `class_canonical`

```javascript
// ✅ CORRECT - Use validated class_canonical
const displayClass = result.class_canonical || '';  // Only valid classes

// ❌ WRONG - Don't use class_original (not validated)
const displayClass = result.class_original || '';   // May contain errors
```

### Current HTML Implementation

```javascript
// Line 468 in regatta_viewer.html
<td>${r.class_canonical||''}</td>
```

**Notes:**
- Uses `class_canonical` only ✅ (correct - no fallback to `class_original`)
- If `class_canonical` is NULL or empty → **THIS IS A DATA ENTRY ERROR** and must be fixed
- `class_canonical` must be validated from `classes.class_name` table with EXACT match

---

## Validation Checksum

### After Data Entry

Run this query to verify all `class_canonical` values are valid:

```sql
-- Find invalid class_canonical (not in classes table)
SELECT DISTINCT
    r.class_canonical,
    'INVALID - Not in classes table' as error
FROM public.results r
LEFT JOIN public.classes c ON r.class_canonical = c.class_name
WHERE r.class_canonical IS NOT NULL
  AND c.class_name IS NULL
ORDER BY r.class_canonical;
```

**Expected Result**: No rows (all `class_canonical` values should exist in `classes` table)

---

## Summary

**`class_canonical` Validation Rules:**

1. ✅ **MUST exist in `classes.class_name` table** - Cannot use invalid classes (unless manually overridden - see `docs/CLASS_CANONICAL_MANUAL_OVERRIDE.md`)
2. ✅ **MUST be EXACT match** - Must match `classes.class_name` exactly (case-sensitive, no variations like `Ilca 4` vs `Ilca 4.7`)
3. ✅ **MUST be corrected** - If PDF shows wrong class (e.g., `Ilca 4`), correct to valid class (`Ilca 4.7`)
4. ✅ **ONLY valid class for HTML** - HTML must use `class_canonical`, never `class_original`
5. ✅ **MANDATORY field** - Never NULL or empty
6. ✅ **CRITICAL FOR FILTERING** - Invalid `class_canonical` breaks HTML filter/search (results won't be found)

**Why Validation is Critical:**
- HTML filter/search uses `class_canonical` to find all results of the same class
- If invalid (e.g., `Ilca 4` instead of `Ilca 4.7`), those results **won't be found** when filtering
- Example: 10 ILCA 4.7 sailors, but 5 have `class_canonical = 'Ilca 4'` → only 5 found in search!

**Key Point**: 
- `class_original` = PDF exact copy (may be wrong, NOT validated, for audit only)
- `class_canonical` = Validated from `classes` table with **EXACT match** (ONLY valid class for HTML, critical for filtering)

**See Also**: `docs/CLASS_CANONICAL_MANUAL_OVERRIDE.md` for override process (rare exceptions only)

