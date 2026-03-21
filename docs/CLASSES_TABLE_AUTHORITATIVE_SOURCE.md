# classes.class_name - Authoritative Source

## Purpose
This document explains that `classes.class_name` is the **AUTHORITATIVE SOURCE** for all class names. All `results.class_canonical` values **MUST** match `classes.class_name` exactly to ensure consistency across the database.

---

## CRITICAL RULE: classes.class_name is AUTHORITATIVE

**Rule**: `classes.class_name` is the **ONLY source of truth** for class names, formatting, spelling, and capitalization.

**Why This Matters**:
1. **Prevents Inconsistencies**: Avoids `29Er` in one table and `29er` in another
2. **Ensures Consistency**: Both `classes` and `results` tables use same format
3. **Enables Validation**: `results.class_canonical` can be validated against `classes.class_name`
4. **Fixes Filtering**: HTML filter/search works correctly when all values match exactly

---

## Data Flow

### Correct Process:

```
classes.class_name = '29Er'  (AUTHORITATIVE - defines format)
    ↓
Extract from PDF: class_original = '29er' (preserves PDF)
    ↓
Validate against classes.class_name: Find '29Er'
    ↓
Use EXACT format from classes.class_name
    ↓
results.class_canonical = '29Er'  (matches classes.class_name EXACTLY)
```

### Wrong Process (BREAKS CONSISTENCY):

```
classes.class_name = '29Er'  (AUTHORITATIVE)
    ↓
Extract from PDF: class_original = '29er'
    ↓
Use PDF format directly: class_canonical = '29er'  ❌ WRONG
    ↓
Result: Inconsistency - '29Er' in classes, '29er' in results
```

---

## Examples of Authoritative Format

### Example 1: 29Er/49Er Classes

**classes.class_name**: `29Er` (AUTHORITATIVE)
- ✅ **CORRECT**: `results.class_canonical = '29Er'` (matches exactly)
- ❌ **WRONG**: `results.class_canonical = '29er'` (doesn't match)
- ❌ **WRONG**: `results.class_canonical = '29-ER'` (doesn't match)

**classes.class_name**: `49Er` (AUTHORITATIVE)
- ✅ **CORRECT**: `results.class_canonical = '49Er'` (matches exactly)
- ❌ **WRONG**: `results.class_canonical = '49er'` (doesn't match)

### Example 2: ILCA Classes

**classes.class_name**: `Ilca 4.7` (AUTHORITATIVE)
- ✅ **CORRECT**: `results.class_canonical = 'Ilca 4.7'` (matches exactly)
- ❌ **WRONG**: `results.class_canonical = 'Ilca 4'` (doesn't match)
- ❌ **WRONG**: `results.class_canonical = 'ILCA 4.7'` (case doesn't match)

**classes.class_name**: `Ilca 7` (AUTHORITATIVE)
- ✅ **CORRECT**: `results.class_canonical = 'Ilca 7'` (matches exactly)
- ❌ **WRONG**: `results.class_canonical = 'ILCA 7'` (case doesn't match)

---

## Validation Process

### Step 1: Check classes.class_name

```sql
-- Find the authoritative format
SELECT class_name 
FROM public.classes 
WHERE class_name ILIKE '%29%';
-- Returns: '29Er' (this is the EXACT format to use)
```

### Step 2: Use EXACT Format

```sql
-- CORRECT: Use exact format from classes.class_name
UPDATE public.results
SET class_canonical = '29Er'  -- From classes.class_name
WHERE class_canonical = '29er';  -- Wrong format
```

### Step 3: Verify Match

```sql
-- Verify all class_canonical match classes.class_name exactly
SELECT DISTINCT
    r.class_canonical,
    CASE 
        WHEN c.class_name IS NULL THEN '❌ Not in classes table'
        WHEN c.class_name != r.class_canonical THEN '❌ Does not match exactly'
        ELSE '✅ Matches classes.class_name exactly'
    END as status
FROM public.results r
LEFT JOIN public.classes c ON r.class_canonical = c.class_name
WHERE r.class_canonical IS NOT NULL;
```

---

## Consistency Rules

### ✅ MUST DO

1. **Always check `classes.class_name` first** - This is the authoritative format
2. **Use EXACT format** - Copy `classes.class_name` exactly (case-sensitive, no variations)
3. **Update `results.class_canonical`** to match `classes.class_name` if different
4. **Validate after updates** - Ensure all `class_canonical` values match `classes.class_name`

### ❌ MUST NOT DO

1. **Don't use PDF format** - PDF may have wrong format (e.g., `29er` instead of `29Er`)
2. **Don't guess format** - Always check `classes.class_name` first
3. **Don't use variations** - Must match `classes.class_name` exactly
4. **Don't update `classes.class_name` without updating `results.class_canonical`** - Both must stay in sync

---

## Fixing Inconsistencies

### When classes.class_name exists but results.class_canonical is different:

```sql
-- Example: Fix 29er → 29Er
UPDATE public.results
SET class_canonical = (SELECT class_name FROM public.classes WHERE class_name ILIKE '%29%' LIMIT 1)
WHERE class_canonical ILIKE '%29%' 
  AND class_canonical != (SELECT class_name FROM public.classes WHERE class_name ILIKE '%29%' LIMIT 1);
```

### When new class is added to classes table:

1. Add class to `classes` table with correct `class_name`
2. Update all existing `results.class_canonical` to match new `class_name`
3. Verify consistency

---

## Validation Script

Run `admin/tools/validate_class_canonical.sql` to check for inconsistencies:

```sql
-- This will show all class_canonical that don't match classes.class_name exactly
SELECT DISTINCT
    r.class_canonical,
    c.class_name as correct_format,
    COUNT(*) as entry_count
FROM public.results r
LEFT JOIN public.classes c ON r.class_canonical = c.class_name
WHERE r.class_canonical IS NOT NULL
  AND (c.class_name IS NULL OR c.class_name != r.class_canonical)
GROUP BY r.class_canonical, c.class_name;
```

---

## Summary

**Key Points**:

1. **`classes.class_name` is AUTHORITATIVE** - Defines format, spelling, capitalization
2. **`results.class_canonical` must match exactly** - No variations allowed
3. **Check `classes.class_name` first** - Always use format from classes table
4. **Validate regularly** - Ensure consistency across both tables
5. **Fix inconsistencies immediately** - Update `results.class_canonical` to match `classes.class_name`

**Why This Matters**:
- Prevents `29Er` vs `29er` inconsistencies
- Ensures HTML filtering works correctly
- Enables proper validation
- Maintains data integrity

**See Also**:
- `docs/CLASS_CANONICAL_VALIDATION_RULES.md` - Full validation process
- `admin/tools/fix_class_canonical_match_classes_table.sql` - Fix inconsistencies
- `admin/tools/validate_class_canonical.sql` - Validate consistency



## Purpose
This document explains that `classes.class_name` is the **AUTHORITATIVE SOURCE** for all class names. All `results.class_canonical` values **MUST** match `classes.class_name` exactly to ensure consistency across the database.

---

## CRITICAL RULE: classes.class_name is AUTHORITATIVE

**Rule**: `classes.class_name` is the **ONLY source of truth** for class names, formatting, spelling, and capitalization.

**Why This Matters**:
1. **Prevents Inconsistencies**: Avoids `29Er` in one table and `29er` in another
2. **Ensures Consistency**: Both `classes` and `results` tables use same format
3. **Enables Validation**: `results.class_canonical` can be validated against `classes.class_name`
4. **Fixes Filtering**: HTML filter/search works correctly when all values match exactly

---

## Data Flow

### Correct Process:

```
classes.class_name = '29Er'  (AUTHORITATIVE - defines format)
    ↓
Extract from PDF: class_original = '29er' (preserves PDF)
    ↓
Validate against classes.class_name: Find '29Er'
    ↓
Use EXACT format from classes.class_name
    ↓
results.class_canonical = '29Er'  (matches classes.class_name EXACTLY)
```

### Wrong Process (BREAKS CONSISTENCY):

```
classes.class_name = '29Er'  (AUTHORITATIVE)
    ↓
Extract from PDF: class_original = '29er'
    ↓
Use PDF format directly: class_canonical = '29er'  ❌ WRONG
    ↓
Result: Inconsistency - '29Er' in classes, '29er' in results
```

---

## Examples of Authoritative Format

### Example 1: 29Er/49Er Classes

**classes.class_name**: `29Er` (AUTHORITATIVE)
- ✅ **CORRECT**: `results.class_canonical = '29Er'` (matches exactly)
- ❌ **WRONG**: `results.class_canonical = '29er'` (doesn't match)
- ❌ **WRONG**: `results.class_canonical = '29-ER'` (doesn't match)

**classes.class_name**: `49Er` (AUTHORITATIVE)
- ✅ **CORRECT**: `results.class_canonical = '49Er'` (matches exactly)
- ❌ **WRONG**: `results.class_canonical = '49er'` (doesn't match)

### Example 2: ILCA Classes

**classes.class_name**: `Ilca 4.7` (AUTHORITATIVE)
- ✅ **CORRECT**: `results.class_canonical = 'Ilca 4.7'` (matches exactly)
- ❌ **WRONG**: `results.class_canonical = 'Ilca 4'` (doesn't match)
- ❌ **WRONG**: `results.class_canonical = 'ILCA 4.7'` (case doesn't match)

**classes.class_name**: `Ilca 7` (AUTHORITATIVE)
- ✅ **CORRECT**: `results.class_canonical = 'Ilca 7'` (matches exactly)
- ❌ **WRONG**: `results.class_canonical = 'ILCA 7'` (case doesn't match)

---

## Validation Process

### Step 1: Check classes.class_name

```sql
-- Find the authoritative format
SELECT class_name 
FROM public.classes 
WHERE class_name ILIKE '%29%';
-- Returns: '29Er' (this is the EXACT format to use)
```

### Step 2: Use EXACT Format

```sql
-- CORRECT: Use exact format from classes.class_name
UPDATE public.results
SET class_canonical = '29Er'  -- From classes.class_name
WHERE class_canonical = '29er';  -- Wrong format
```

### Step 3: Verify Match

```sql
-- Verify all class_canonical match classes.class_name exactly
SELECT DISTINCT
    r.class_canonical,
    CASE 
        WHEN c.class_name IS NULL THEN '❌ Not in classes table'
        WHEN c.class_name != r.class_canonical THEN '❌ Does not match exactly'
        ELSE '✅ Matches classes.class_name exactly'
    END as status
FROM public.results r
LEFT JOIN public.classes c ON r.class_canonical = c.class_name
WHERE r.class_canonical IS NOT NULL;
```

---

## Consistency Rules

### ✅ MUST DO

1. **Always check `classes.class_name` first** - This is the authoritative format
2. **Use EXACT format** - Copy `classes.class_name` exactly (case-sensitive, no variations)
3. **Update `results.class_canonical`** to match `classes.class_name` if different
4. **Validate after updates** - Ensure all `class_canonical` values match `classes.class_name`

### ❌ MUST NOT DO

1. **Don't use PDF format** - PDF may have wrong format (e.g., `29er` instead of `29Er`)
2. **Don't guess format** - Always check `classes.class_name` first
3. **Don't use variations** - Must match `classes.class_name` exactly
4. **Don't update `classes.class_name` without updating `results.class_canonical`** - Both must stay in sync

---

## Fixing Inconsistencies

### When classes.class_name exists but results.class_canonical is different:

```sql
-- Example: Fix 29er → 29Er
UPDATE public.results
SET class_canonical = (SELECT class_name FROM public.classes WHERE class_name ILIKE '%29%' LIMIT 1)
WHERE class_canonical ILIKE '%29%' 
  AND class_canonical != (SELECT class_name FROM public.classes WHERE class_name ILIKE '%29%' LIMIT 1);
```

### When new class is added to classes table:

1. Add class to `classes` table with correct `class_name`
2. Update all existing `results.class_canonical` to match new `class_name`
3. Verify consistency

---

## Validation Script

Run `admin/tools/validate_class_canonical.sql` to check for inconsistencies:

```sql
-- This will show all class_canonical that don't match classes.class_name exactly
SELECT DISTINCT
    r.class_canonical,
    c.class_name as correct_format,
    COUNT(*) as entry_count
FROM public.results r
LEFT JOIN public.classes c ON r.class_canonical = c.class_name
WHERE r.class_canonical IS NOT NULL
  AND (c.class_name IS NULL OR c.class_name != r.class_canonical)
GROUP BY r.class_canonical, c.class_name;
```

---

## Summary

**Key Points**:

1. **`classes.class_name` is AUTHORITATIVE** - Defines format, spelling, capitalization
2. **`results.class_canonical` must match exactly** - No variations allowed
3. **Check `classes.class_name` first** - Always use format from classes table
4. **Validate regularly** - Ensure consistency across both tables
5. **Fix inconsistencies immediately** - Update `results.class_canonical` to match `classes.class_name`

**Why This Matters**:
- Prevents `29Er` vs `29er` inconsistencies
- Ensures HTML filtering works correctly
- Enables proper validation
- Maintains data integrity

**See Also**:
- `docs/CLASS_CANONICAL_VALIDATION_RULES.md` - Full validation process
- `admin/tools/fix_class_canonical_match_classes_table.sql` - Fix inconsistencies
- `admin/tools/validate_class_canonical.sql` - Validate consistency


















