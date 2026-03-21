# Entry Count Checksum Rules

## Purpose
Validate that the number of results (entries) imported matches the expected count from the results sheet/PDF.

## Critical Rule

**CRITICAL**: After importing data for a block/fleet, the entry count MUST be validated:

```
Actual Count = COUNT(*) FROM results WHERE block_id = 'block-id'
Expected Count = Number of entries shown in PDF/results sheet for that fleet
Validation: Actual Count MUST equal Expected Count
```

---

## When to Perform Checksum

### 1. During Data Import
- **After inserting all results for a block**: Immediately verify count matches PDF
- **Before moving to next fleet**: Ensure current fleet is complete

### 2. After Data Import
- **Post-import validation**: Run checksum script to verify all blocks
- **Before closing data entry session**: Final verification

### 3. When Updating Data
- **After adding results**: Verify count increased correctly
- **After deleting results**: Verify count decreased correctly

---

## Checksum Process

### Step 1: Count Expected Entries
From the PDF/results sheet:
1. Identify the fleet/class section
2. Count all ranked entries (1, 2, 3, ... N)
3. Note any DNS/DNC entries (may or may not be ranked)
4. **Expected Count** = Total ranked entries

### Step 2: Count Actual Entries in Database
```sql
-- Count actual entries for a block
SELECT COUNT(*) as actual_entry_count
FROM public.results
WHERE block_id = '342-2025-sas-mirror-national-championship:mirror';
```

### Step 3: Compare and Validate
```sql
-- Expected: 20 entries (from PDF)
-- Actual: COUNT(*) = 20
-- Status: ✅ MATCH
```

---

## Validation Rules

### ✅ Valid Cases

1. **Exact Match**: Actual = Expected
   - **Status**: ✅ **VALID** - All entries imported correctly

2. **Missing DNS/DNC**: Actual < Expected (if DNS/DNC not ranked)
   - **Status**: ✅ **VALID** - DNS/DNC entries may not have ranks
   - **Note**: Check if DNS/DNC entries are in database with `rank IS NULL`

3. **Ties**: Actual > Expected (if multiple sailors tied at same rank)
   - **Status**: ✅ **VALID** - Ties create duplicate ranks
   - **Note**: Verify `nett_points_raw` is same for tied entries

### ❌ Invalid Cases

1. **Missing Entries**: Actual < Expected (and no DNS/DNC explanation)
   - **Status**: ❌ **ERROR** - Some entries not imported
   - **Action**: Check PDF again, verify all rows imported

2. **Extra Entries**: Actual > Expected (and no ties)
   - **Status**: ❌ **ERROR** - Duplicate imports or wrong block
   - **Action**: Check for duplicate `helm_name` + `sail_number` combinations

3. **Zero Entries**: Actual = 0
   - **Status**: ❌ **ERROR** - No data imported
   - **Action**: Verify block_id, check INSERT statements

---

## SQL Validation Queries

### Basic Entry Count Check
```sql
-- Count entries for a specific block
SELECT 
    block_id,
    COUNT(*) as actual_entry_count,
    MIN(rank) as min_rank,
    MAX(rank) as max_rank,
    COUNT(DISTINCT rank) as unique_ranks
FROM public.results
WHERE block_id = '342-2025-sas-mirror-national-championship:mirror'
GROUP BY block_id;
```

### Compare All Blocks
```sql
-- Show entry counts for all blocks
SELECT 
    rb.block_id,
    rb.fleet_label,
    rb.class_canonical,
    rb.races_sailed,
    COUNT(r.result_id) as actual_entry_count,
    CASE 
        WHEN COUNT(r.result_id) = 0 THEN '⚠️ NO ENTRIES'
        ELSE '✅ Has entries'
    END as status
FROM public.regatta_blocks rb
LEFT JOIN public.results r ON r.block_id = rb.block_id
GROUP BY rb.block_id, rb.fleet_label, rb.class_canonical, rb.races_sailed
ORDER BY rb.block_id;
```

### Check for Duplicates
```sql
-- Find potential duplicate entries (same helm + sail number)
SELECT 
    block_id,
    helm_name,
    sail_number,
    COUNT(*) as duplicate_count
FROM public.results
WHERE helm_name IS NOT NULL AND sail_number IS NOT NULL
GROUP BY block_id, helm_name, sail_number
HAVING COUNT(*) > 1;
```

### Check for Missing Ranks
```sql
-- Find blocks with gaps in ranking (may indicate missing entries)
WITH rank_stats AS (
    SELECT 
        block_id,
        COUNT(*) as actual_count,
        MIN(rank) as min_rank,
        MAX(rank) as max_rank
    FROM public.results
    WHERE rank IS NOT NULL
    GROUP BY block_id
)
SELECT 
    block_id,
    actual_count,
    min_rank || ' to ' || max_rank as rank_range,
    max_rank - min_rank + 1 as expected_count,
    (max_rank - min_rank + 1) - actual_count as missing_ranks
FROM rank_stats
WHERE (max_rank - min_rank + 1) != actual_count;
```

---

## Integration with Data Entry Process

### During Import (Manual Process)

1. **Extract Header Info**: Identify fleet/class name
2. **Count PDF Entries**: Count all ranked entries in PDF
3. **Import Data**: INSERT all results into database
4. **Immediate Checksum**: Run `SELECT COUNT(*) WHERE block_id = ...`
5. **Compare**: Actual vs Expected
6. **Fix if needed**: Re-check PDF, verify imports

### Example Workflow

```sql
-- Step 1: PDF shows 15 entries for Optimist A fleet
-- Expected Count: 15

-- Step 2: Import all 15 rows
INSERT INTO public.results (block_id, rank, helm_name, ...) VALUES (...);

-- Step 3: Verify count
SELECT COUNT(*) FROM public.results 
WHERE block_id = '342-2025-regatta-id:optimist-a';
-- Result: 15
-- Status: ✅ MATCH - All entries imported

-- Step 4: If mismatch, investigate
-- If COUNT = 14: Check PDF again, find missing entry
-- If COUNT = 16: Check for duplicate, verify all entries unique
```

---

## Automation Script

Run validation script after import:

```bash
psql "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master" \
  -f admin/tools/checksum_entry_counts.sql
```

This script will:
1. Show entry counts for all blocks
2. Identify potential duplicates
3. Flag blocks with missing ranks
4. Provide manual verification checklist

---

## Common Issues

### Issue 1: Missing Entries
**Symptom**: Actual Count < Expected Count  
**Cause**: Row not imported, skipped due to error, or not in PDF section  
**Fix**: Re-check PDF, verify all rows in INSERT statement

### Issue 2: Extra Entries
**Symptom**: Actual Count > Expected Count  
**Cause**: Duplicate import, wrong block_id, or ties not accounted for  
**Fix**: Check for duplicates, verify block_id, confirm if ties exist

### Issue 3: Zero Entries
**Symptom**: Actual Count = 0  
**Cause**: Wrong block_id, INSERT failed, or no data in section  
**Fix**: Verify block_id exists, check INSERT statements, confirm PDF has entries

---

## Documentation

- **Validation Script**: `admin/tools/checksum_entry_counts.sql`
- **Audit Script**: `audit_regatta.py` (line 80: `entries_count = len(rows)`)
- **Data Entry Standards**: `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md`

---

## Summary

**CRITICAL RULE**: Always verify entry count after import:

1. ✅ Count entries in PDF/results sheet
2. ✅ Count entries in database: `SELECT COUNT(*) WHERE block_id = ...`
3. ✅ Compare: Must match (or explain with DNS/DNC/ties)
4. ✅ Fix mismatches before proceeding

**This checksum is MANDATORY for data integrity.**



## Purpose
Validate that the number of results (entries) imported matches the expected count from the results sheet/PDF.

## Critical Rule

**CRITICAL**: After importing data for a block/fleet, the entry count MUST be validated:

```
Actual Count = COUNT(*) FROM results WHERE block_id = 'block-id'
Expected Count = Number of entries shown in PDF/results sheet for that fleet
Validation: Actual Count MUST equal Expected Count
```

---

## When to Perform Checksum

### 1. During Data Import
- **After inserting all results for a block**: Immediately verify count matches PDF
- **Before moving to next fleet**: Ensure current fleet is complete

### 2. After Data Import
- **Post-import validation**: Run checksum script to verify all blocks
- **Before closing data entry session**: Final verification

### 3. When Updating Data
- **After adding results**: Verify count increased correctly
- **After deleting results**: Verify count decreased correctly

---

## Checksum Process

### Step 1: Count Expected Entries
From the PDF/results sheet:
1. Identify the fleet/class section
2. Count all ranked entries (1, 2, 3, ... N)
3. Note any DNS/DNC entries (may or may not be ranked)
4. **Expected Count** = Total ranked entries

### Step 2: Count Actual Entries in Database
```sql
-- Count actual entries for a block
SELECT COUNT(*) as actual_entry_count
FROM public.results
WHERE block_id = '342-2025-sas-mirror-national-championship:mirror';
```

### Step 3: Compare and Validate
```sql
-- Expected: 20 entries (from PDF)
-- Actual: COUNT(*) = 20
-- Status: ✅ MATCH
```

---

## Validation Rules

### ✅ Valid Cases

1. **Exact Match**: Actual = Expected
   - **Status**: ✅ **VALID** - All entries imported correctly

2. **Missing DNS/DNC**: Actual < Expected (if DNS/DNC not ranked)
   - **Status**: ✅ **VALID** - DNS/DNC entries may not have ranks
   - **Note**: Check if DNS/DNC entries are in database with `rank IS NULL`

3. **Ties**: Actual > Expected (if multiple sailors tied at same rank)
   - **Status**: ✅ **VALID** - Ties create duplicate ranks
   - **Note**: Verify `nett_points_raw` is same for tied entries

### ❌ Invalid Cases

1. **Missing Entries**: Actual < Expected (and no DNS/DNC explanation)
   - **Status**: ❌ **ERROR** - Some entries not imported
   - **Action**: Check PDF again, verify all rows imported

2. **Extra Entries**: Actual > Expected (and no ties)
   - **Status**: ❌ **ERROR** - Duplicate imports or wrong block
   - **Action**: Check for duplicate `helm_name` + `sail_number` combinations

3. **Zero Entries**: Actual = 0
   - **Status**: ❌ **ERROR** - No data imported
   - **Action**: Verify block_id, check INSERT statements

---

## SQL Validation Queries

### Basic Entry Count Check
```sql
-- Count entries for a specific block
SELECT 
    block_id,
    COUNT(*) as actual_entry_count,
    MIN(rank) as min_rank,
    MAX(rank) as max_rank,
    COUNT(DISTINCT rank) as unique_ranks
FROM public.results
WHERE block_id = '342-2025-sas-mirror-national-championship:mirror'
GROUP BY block_id;
```

### Compare All Blocks
```sql
-- Show entry counts for all blocks
SELECT 
    rb.block_id,
    rb.fleet_label,
    rb.class_canonical,
    rb.races_sailed,
    COUNT(r.result_id) as actual_entry_count,
    CASE 
        WHEN COUNT(r.result_id) = 0 THEN '⚠️ NO ENTRIES'
        ELSE '✅ Has entries'
    END as status
FROM public.regatta_blocks rb
LEFT JOIN public.results r ON r.block_id = rb.block_id
GROUP BY rb.block_id, rb.fleet_label, rb.class_canonical, rb.races_sailed
ORDER BY rb.block_id;
```

### Check for Duplicates
```sql
-- Find potential duplicate entries (same helm + sail number)
SELECT 
    block_id,
    helm_name,
    sail_number,
    COUNT(*) as duplicate_count
FROM public.results
WHERE helm_name IS NOT NULL AND sail_number IS NOT NULL
GROUP BY block_id, helm_name, sail_number
HAVING COUNT(*) > 1;
```

### Check for Missing Ranks
```sql
-- Find blocks with gaps in ranking (may indicate missing entries)
WITH rank_stats AS (
    SELECT 
        block_id,
        COUNT(*) as actual_count,
        MIN(rank) as min_rank,
        MAX(rank) as max_rank
    FROM public.results
    WHERE rank IS NOT NULL
    GROUP BY block_id
)
SELECT 
    block_id,
    actual_count,
    min_rank || ' to ' || max_rank as rank_range,
    max_rank - min_rank + 1 as expected_count,
    (max_rank - min_rank + 1) - actual_count as missing_ranks
FROM rank_stats
WHERE (max_rank - min_rank + 1) != actual_count;
```

---

## Integration with Data Entry Process

### During Import (Manual Process)

1. **Extract Header Info**: Identify fleet/class name
2. **Count PDF Entries**: Count all ranked entries in PDF
3. **Import Data**: INSERT all results into database
4. **Immediate Checksum**: Run `SELECT COUNT(*) WHERE block_id = ...`
5. **Compare**: Actual vs Expected
6. **Fix if needed**: Re-check PDF, verify imports

### Example Workflow

```sql
-- Step 1: PDF shows 15 entries for Optimist A fleet
-- Expected Count: 15

-- Step 2: Import all 15 rows
INSERT INTO public.results (block_id, rank, helm_name, ...) VALUES (...);

-- Step 3: Verify count
SELECT COUNT(*) FROM public.results 
WHERE block_id = '342-2025-regatta-id:optimist-a';
-- Result: 15
-- Status: ✅ MATCH - All entries imported

-- Step 4: If mismatch, investigate
-- If COUNT = 14: Check PDF again, find missing entry
-- If COUNT = 16: Check for duplicate, verify all entries unique
```

---

## Automation Script

Run validation script after import:

```bash
psql "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master" \
  -f admin/tools/checksum_entry_counts.sql
```

This script will:
1. Show entry counts for all blocks
2. Identify potential duplicates
3. Flag blocks with missing ranks
4. Provide manual verification checklist

---

## Common Issues

### Issue 1: Missing Entries
**Symptom**: Actual Count < Expected Count  
**Cause**: Row not imported, skipped due to error, or not in PDF section  
**Fix**: Re-check PDF, verify all rows in INSERT statement

### Issue 2: Extra Entries
**Symptom**: Actual Count > Expected Count  
**Cause**: Duplicate import, wrong block_id, or ties not accounted for  
**Fix**: Check for duplicates, verify block_id, confirm if ties exist

### Issue 3: Zero Entries
**Symptom**: Actual Count = 0  
**Cause**: Wrong block_id, INSERT failed, or no data in section  
**Fix**: Verify block_id exists, check INSERT statements, confirm PDF has entries

---

## Documentation

- **Validation Script**: `admin/tools/checksum_entry_counts.sql`
- **Audit Script**: `audit_regatta.py` (line 80: `entries_count = len(rows)`)
- **Data Entry Standards**: `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md`

---

## Summary

**CRITICAL RULE**: Always verify entry count after import:

1. ✅ Count entries in PDF/results sheet
2. ✅ Count entries in database: `SELECT COUNT(*) WHERE block_id = ...`
3. ✅ Compare: Must match (or explain with DNS/DNC/ties)
4. ✅ Fix mismatches before proceeding

**This checksum is MANDATORY for data integrity.**


















