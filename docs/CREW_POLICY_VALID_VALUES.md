# crew_policy - Valid Values ONLY

## CRITICAL RULE: ONLY 3 VALID VALUES

**`crew_policy` column in `classes` table can ONLY have these exact values:**

1. `'single'` - Helm only (1 sailor)
2. `'double'` - Helm + 1 crew (2 sailors)  
3. `'Crewed'` - Helm + 2+ crew (3+ sailors)
4. `NULL` - No results yet

**THAT'S IT. NOTHING ELSE.**

---

## ❌ INVALID VALUES (NEVER USE)

- ❌ `'Single-handed'` → ✅ Use `'single'`
- ❌ `'Double-handed'` → ✅ Use `'double'`
- ❌ `'Crewed'` (wrong case) → ✅ Use `'Crewed'` (capital C)
- ❌ `'single-handed'` → ✅ Use `'single'`
- ❌ `'Unknown'` → ✅ Use `NULL`
- ❌ Any other variation → ✅ Use exact values: `'single'`, `'double'`, `'Crewed'`, or `NULL`

---

## Validation

**Check for invalid values:**
```sql
SELECT class_id, class_name, crew_policy
FROM public.classes
WHERE crew_policy IS NOT NULL
  AND crew_policy NOT IN ('single', 'double', 'Crewed');
```

**Expected result**: No rows (all values must be valid)

---

## Data Corruption Prevention

**NEVER allow these:**
- Variations like "Single-handed", "Double-handed"
- Wrong case like "SINGLE", "crewed"
- Other values like "Unknown", "mixed"

**ALWAYS use exact values:**
- `'single'` (lowercase)
- `'double'` (lowercase)
- `'Crewed'` (capital C, lowercase rest)
- `NULL` (for no results yet)

---

## Fix Script

The script `admin/tools/update_crew_policy_from_results_proper.sql` automatically fixes invalid values:
- Converts `'Single-handed'` → `'single'`
- Converts any variation → correct exact value
- Sets invalid values to `NULL` if they can't be mapped

---

## Summary

**ONLY 4 POSSIBLE VALUES:**
1. `'single'` - Exact lowercase
2. `'double'` - Exact lowercase  
3. `'Crewed'` - Capital C, lowercase rest
4. `NULL` - No results yet

**ANY OTHER VALUE IS DATA CORRUPTION**



## CRITICAL RULE: ONLY 3 VALID VALUES

**`crew_policy` column in `classes` table can ONLY have these exact values:**

1. `'single'` - Helm only (1 sailor)
2. `'double'` - Helm + 1 crew (2 sailors)  
3. `'Crewed'` - Helm + 2+ crew (3+ sailors)
4. `NULL` - No results yet

**THAT'S IT. NOTHING ELSE.**

---

## ❌ INVALID VALUES (NEVER USE)

- ❌ `'Single-handed'` → ✅ Use `'single'`
- ❌ `'Double-handed'` → ✅ Use `'double'`
- ❌ `'Crewed'` (wrong case) → ✅ Use `'Crewed'` (capital C)
- ❌ `'single-handed'` → ✅ Use `'single'`
- ❌ `'Unknown'` → ✅ Use `NULL`
- ❌ Any other variation → ✅ Use exact values: `'single'`, `'double'`, `'Crewed'`, or `NULL`

---

## Validation

**Check for invalid values:**
```sql
SELECT class_id, class_name, crew_policy
FROM public.classes
WHERE crew_policy IS NOT NULL
  AND crew_policy NOT IN ('single', 'double', 'Crewed');
```

**Expected result**: No rows (all values must be valid)

---

## Data Corruption Prevention

**NEVER allow these:**
- Variations like "Single-handed", "Double-handed"
- Wrong case like "SINGLE", "crewed"
- Other values like "Unknown", "mixed"

**ALWAYS use exact values:**
- `'single'` (lowercase)
- `'double'` (lowercase)
- `'Crewed'` (capital C, lowercase rest)
- `NULL` (for no results yet)

---

## Fix Script

The script `admin/tools/update_crew_policy_from_results_proper.sql` automatically fixes invalid values:
- Converts `'Single-handed'` → `'single'`
- Converts any variation → correct exact value
- Sets invalid values to `NULL` if they can't be mapped

---

## Summary

**ONLY 4 POSSIBLE VALUES:**
1. `'single'` - Exact lowercase
2. `'double'` - Exact lowercase  
3. `'Crewed'` - Capital C, lowercase rest
4. `NULL` - No results yet

**ANY OTHER VALUE IS DATA CORRUPTION**


















