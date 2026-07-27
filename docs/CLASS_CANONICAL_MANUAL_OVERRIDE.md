# class_canonical Manual Override Process

## Purpose
This document explains when and how to **manually override** `class_canonical` validation when a class doesn't exist in the `classes` table but is still valid for data entry.

---

## General Rule: NO Override Without Authorization

**Default**: `class_canonical` MUST exist in `classes.class_name` table. No exceptions.

**Override**: Only if explicitly authorized (documented below).

---

## When Override is Authorized

### Case 1: New Class Not Yet in `classes` Table

**Scenario**: PDF shows a new class that doesn't exist in `classes` table yet (e.g., new boat class).

**Process**:
1. **First**: Add class to `classes` table with correct `class_name`
2. **Then**: Use that `class_name` for `class_canonical`
3. **Override NOT needed** if class is added first

### Case 2: Special/Temporary Class Name

**Scenario**: Rare case where class name is valid but intentionally different from `classes` table.

**Process**:
1. **Document override** in this file
2. **Get explicit authorization** before using override
3. **Note reason** for override
4. **Review periodically** - may need to add to `classes` table instead

---

## Manual Override Examples

### Example 1: Special Fleet Name (NOT YET AUTHORIZED)

**Status**: ❌ NOT AUTHORIZED - Add to `classes` table instead

**Example**: If PDF shows `Saldanha` as class but not in `classes` table:
- ❌ **Don't override** - Add `Saldanha` to `classes` table first
- ✅ **Then use** `class_canonical = 'Saldanha'` (now valid)

### Example 2: Temporary Override for Legacy Data

**Status**: ⚠️ Requires explicit authorization per case

**Process**:
1. Document the override request
2. Get authorization
3. Apply override
4. Document in this file
5. Plan to add to `classes` table in future

---

## Override Documentation Format

If override is authorized, document here:

```markdown
## Override: [Class Name]

**Date**: YYYY-MM-DD
**Authorized By**: [Name]
**Reason**: [Why override is needed]
**Valid Until**: [Date to add to classes table]
**Example**:
- class_original: [PDF value]
- class_canonical: [Override value]
- Entries affected: [Number]
```

---

## Current Override List

### None Currently Authorized

**Status**: No manual overrides currently active. All `class_canonical` values must exist in `classes.class_name` table.

---

## Override Removal Process

When override is no longer needed:

1. Add class to `classes` table if missing
2. Update all `class_canonical` values to match `classes.class_name`
3. Remove override documentation
4. Run validation check

---

## Validation After Override

After applying any override, run:

```sql
-- Verify override doesn't break validation
SELECT DISTINCT
    r.class_canonical,
    CASE 
        WHEN c.class_name IS NULL THEN '❌ INVALID (even with override)'
        ELSE '✅ VALID'
    END as status
FROM public.results r
LEFT JOIN public.classes c ON r.class_canonical = c.class_name
WHERE r.class_canonical IS NOT NULL;
```

**Expected**: All should show `✅ VALID` (override should still match `classes` table when possible)

---

## Summary

**Default Rule**: `class_canonical` MUST exist in `classes.class_name` table - **NO EXCEPTIONS**

**Override Process**:
1. Add class to `classes` table first (preferred)
2. If override needed, get explicit authorization
3. Document override in this file
4. Review periodically
5. Remove override when class added to `classes` table

**Key Point**: Overrides should be **rare exceptions**, not standard practice. Always prefer adding to `classes` table.



## Purpose
This document explains when and how to **manually override** `class_canonical` validation when a class doesn't exist in the `classes` table but is still valid for data entry.

---

## General Rule: NO Override Without Authorization

**Default**: `class_canonical` MUST exist in `classes.class_name` table. No exceptions.

**Override**: Only if explicitly authorized (documented below).

---

## When Override is Authorized

### Case 1: New Class Not Yet in `classes` Table

**Scenario**: PDF shows a new class that doesn't exist in `classes` table yet (e.g., new boat class).

**Process**:
1. **First**: Add class to `classes` table with correct `class_name`
2. **Then**: Use that `class_name` for `class_canonical`
3. **Override NOT needed** if class is added first

### Case 2: Special/Temporary Class Name

**Scenario**: Rare case where class name is valid but intentionally different from `classes` table.

**Process**:
1. **Document override** in this file
2. **Get explicit authorization** before using override
3. **Note reason** for override
4. **Review periodically** - may need to add to `classes` table instead

---

## Manual Override Examples

### Example 1: Special Fleet Name (NOT YET AUTHORIZED)

**Status**: ❌ NOT AUTHORIZED - Add to `classes` table instead

**Example**: If PDF shows `Saldanha` as class but not in `classes` table:
- ❌ **Don't override** - Add `Saldanha` to `classes` table first
- ✅ **Then use** `class_canonical = 'Saldanha'` (now valid)

### Example 2: Temporary Override for Legacy Data

**Status**: ⚠️ Requires explicit authorization per case

**Process**:
1. Document the override request
2. Get authorization
3. Apply override
4. Document in this file
5. Plan to add to `classes` table in future

---

## Override Documentation Format

If override is authorized, document here:

```markdown
## Override: [Class Name]

**Date**: YYYY-MM-DD
**Authorized By**: [Name]
**Reason**: [Why override is needed]
**Valid Until**: [Date to add to classes table]
**Example**:
- class_original: [PDF value]
- class_canonical: [Override value]
- Entries affected: [Number]
```

---

## Current Override List

### None Currently Authorized

**Status**: No manual overrides currently active. All `class_canonical` values must exist in `classes.class_name` table.

---

## Override Removal Process

When override is no longer needed:

1. Add class to `classes` table if missing
2. Update all `class_canonical` values to match `classes.class_name`
3. Remove override documentation
4. Run validation check

---

## Validation After Override

After applying any override, run:

```sql
-- Verify override doesn't break validation
SELECT DISTINCT
    r.class_canonical,
    CASE 
        WHEN c.class_name IS NULL THEN '❌ INVALID (even with override)'
        ELSE '✅ VALID'
    END as status
FROM public.results r
LEFT JOIN public.classes c ON r.class_canonical = c.class_name
WHERE r.class_canonical IS NOT NULL;
```

**Expected**: All should show `✅ VALID` (override should still match `classes` table when possible)

---

## Summary

**Default Rule**: `class_canonical` MUST exist in `classes.class_name` table - **NO EXCEPTIONS**

**Override Process**:
1. Add class to `classes` table first (preferred)
2. If override needed, get explicit authorization
3. Document override in this file
4. Review periodically
5. Remove override when class added to `classes` table

**Key Point**: Overrides should be **rare exceptions**, not standard practice. Always prefer adding to `classes` table.


















