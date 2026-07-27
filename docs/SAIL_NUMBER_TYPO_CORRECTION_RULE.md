# Sail Number Typo Correction Rule

## Rule: When Sailor Same Class Has Conflicting Sail Numbers

### Problem
A sailor in the same class appears with different sail numbers across regattas, and we suspect a typo.

### Solution Method
Use pattern analysis with other sail numbers in the same range to determine which is correct.

---

## Step-by-Step Process

### 1. Identify the Conflict
- Same sailor (SA ID)
- Same class
- Different sail numbers in different regattas

**Example**: Rudy McNeill (SA ID: 1644, Ilca 7)
- Previous regatta: 124133
- Current regatta: 214133

### 2. Check Sail Number Patterns

Query sail numbers in both ranges:

```sql
-- Check range around first sail number
SELECT DISTINCT sail_number
FROM public.results
WHERE class_canonical = 'Ilca 7'
  AND sail_number ~ '^[0-9]+$'
  AND sail_number::numeric BETWEEN 124000 AND 124200;

-- Check range around second sail number
SELECT DISTINCT sail_number
FROM public.results
WHERE class_canonical = 'Ilca 7'
  AND sail_number ~ '^[0-9]+$'
  AND sail_number::numeric BETWEEN 214000 AND 214200;
```

### 3. Analyze Results

**Pattern Analysis**:
- If one range has multiple nearby sail numbers → That range is likely correct
- If one range is isolated (no nearby numbers) → Likely typo

**Example**:
- 124133 range: Only 1 sail number (isolated)
- 214133 range: 4 sail numbers (214128, 214130, 214131, 214132) → Pattern exists

**Conclusion**: 214133 is correct (fits pattern), 124133 is typo

### 4. Verify Against PDF Source

Check what the PDF actually shows:
- If PDF matches the pattern → Use PDF value
- If PDF doesn't match pattern → PDF might have OCR error, use pattern

### 5. Apply Correction

Update the sail number to match the pattern:

```sql
UPDATE public.results
SET sail_number = '214133'  -- Correct based on pattern
WHERE helm_sa_sailing_id = '1644'
  AND class_canonical = 'Ilca 7'
  AND sail_number = '124133';  -- Incorrect (isolated)
```

### 6. Document the Correction

Record in audit log:
- Original value: 124133
- Corrected value: 214133
- Reason: Pattern analysis - 214xxx range has multiple sails, 124xxx is isolated
- Evidence: 214128, 214130, 214131, 214132 exist in same range

---

## Real Example: Rudy McNeill (SA ID: 1644)

### Conflict
- Previous regatta: Sail 124133
- Regatta 336: Sail 214133 (from PDF OCR)

### Pattern Analysis
```
Sail numbers 124000-124200:
  124133 (only one - isolated)

Sail numbers 214000-214200:
  214128 (Pierre Goosen)
  214130 (Peter Wilson)
  214131 (Leon de Raay)
  214132 (Campbell Alexander)
  214133 (Rudy McNeill - fits pattern)
```

### Conclusion
- **214133 is correct** - fits pattern with other 214xxx sails
- **124133 was typo** - isolated, no nearby numbers

### Correction Applied
```sql
UPDATE public.results
SET sail_number = '214133'
WHERE block_id = '336-2025-ilca-nationals-results:ilca-7'
  AND rank = 1
  AND helm_name = 'Rudy McNeill';
```

---

## Rules Summary

1. ✅ **Check both ranges** - Don't assume previous value is correct
2. ✅ **Look for patterns** - Multiple nearby numbers = likely correct range
3. ✅ **Isolated = typo** - Single number in range = likely OCR error
4. ✅ **Verify with PDF** - But pattern takes precedence if PDF has error
5. ✅ **Document correction** - Record in audit log with reasoning

---

## When NOT to Apply This Rule

- **Different classes**: Sail numbers can legitimately differ across classes
- **Sail number changes**: Sailors can change sail numbers over time
- **No clear pattern**: If both ranges have similar patterns, use most recent value
- **PDF clearly wrong**: If PDF has obvious OCR error (e.g., "214133" but all other evidence points to "124133")

---

## Enforcement

**Before correcting conflicting sail numbers:**
1. Run pattern analysis query
2. Compare ranges
3. Document reasoning
4. Apply correction
5. Update audit log

**This rule is MANDATORY for all sail number conflicts.**



## Rule: When Sailor Same Class Has Conflicting Sail Numbers

### Problem
A sailor in the same class appears with different sail numbers across regattas, and we suspect a typo.

### Solution Method
Use pattern analysis with other sail numbers in the same range to determine which is correct.

---

## Step-by-Step Process

### 1. Identify the Conflict
- Same sailor (SA ID)
- Same class
- Different sail numbers in different regattas

**Example**: Rudy McNeill (SA ID: 1644, Ilca 7)
- Previous regatta: 124133
- Current regatta: 214133

### 2. Check Sail Number Patterns

Query sail numbers in both ranges:

```sql
-- Check range around first sail number
SELECT DISTINCT sail_number
FROM public.results
WHERE class_canonical = 'Ilca 7'
  AND sail_number ~ '^[0-9]+$'
  AND sail_number::numeric BETWEEN 124000 AND 124200;

-- Check range around second sail number
SELECT DISTINCT sail_number
FROM public.results
WHERE class_canonical = 'Ilca 7'
  AND sail_number ~ '^[0-9]+$'
  AND sail_number::numeric BETWEEN 214000 AND 214200;
```

### 3. Analyze Results

**Pattern Analysis**:
- If one range has multiple nearby sail numbers → That range is likely correct
- If one range is isolated (no nearby numbers) → Likely typo

**Example**:
- 124133 range: Only 1 sail number (isolated)
- 214133 range: 4 sail numbers (214128, 214130, 214131, 214132) → Pattern exists

**Conclusion**: 214133 is correct (fits pattern), 124133 is typo

### 4. Verify Against PDF Source

Check what the PDF actually shows:
- If PDF matches the pattern → Use PDF value
- If PDF doesn't match pattern → PDF might have OCR error, use pattern

### 5. Apply Correction

Update the sail number to match the pattern:

```sql
UPDATE public.results
SET sail_number = '214133'  -- Correct based on pattern
WHERE helm_sa_sailing_id = '1644'
  AND class_canonical = 'Ilca 7'
  AND sail_number = '124133';  -- Incorrect (isolated)
```

### 6. Document the Correction

Record in audit log:
- Original value: 124133
- Corrected value: 214133
- Reason: Pattern analysis - 214xxx range has multiple sails, 124xxx is isolated
- Evidence: 214128, 214130, 214131, 214132 exist in same range

---

## Real Example: Rudy McNeill (SA ID: 1644)

### Conflict
- Previous regatta: Sail 124133
- Regatta 336: Sail 214133 (from PDF OCR)

### Pattern Analysis
```
Sail numbers 124000-124200:
  124133 (only one - isolated)

Sail numbers 214000-214200:
  214128 (Pierre Goosen)
  214130 (Peter Wilson)
  214131 (Leon de Raay)
  214132 (Campbell Alexander)
  214133 (Rudy McNeill - fits pattern)
```

### Conclusion
- **214133 is correct** - fits pattern with other 214xxx sails
- **124133 was typo** - isolated, no nearby numbers

### Correction Applied
```sql
UPDATE public.results
SET sail_number = '214133'
WHERE block_id = '336-2025-ilca-nationals-results:ilca-7'
  AND rank = 1
  AND helm_name = 'Rudy McNeill';
```

---

## Rules Summary

1. ✅ **Check both ranges** - Don't assume previous value is correct
2. ✅ **Look for patterns** - Multiple nearby numbers = likely correct range
3. ✅ **Isolated = typo** - Single number in range = likely OCR error
4. ✅ **Verify with PDF** - But pattern takes precedence if PDF has error
5. ✅ **Document correction** - Record in audit log with reasoning

---

## When NOT to Apply This Rule

- **Different classes**: Sail numbers can legitimately differ across classes
- **Sail number changes**: Sailors can change sail numbers over time
- **No clear pattern**: If both ranges have similar patterns, use most recent value
- **PDF clearly wrong**: If PDF has obvious OCR error (e.g., "214133" but all other evidence points to "124133")

---

## Enforcement

**Before correcting conflicting sail numbers:**
1. Run pattern analysis query
2. Compare ranges
3. Document reasoning
4. Apply correction
5. Update audit log

**This rule is MANDATORY for all sail number conflicts.**


















