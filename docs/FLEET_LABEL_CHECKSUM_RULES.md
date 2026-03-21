# Fleet Label Checksum Rules

## Purpose
Validate that `fleet_label` matches the expected fleet name from the results sheet/PDF, with manual override process for rare cases.

## Critical Rule

**CRITICAL**: After importing data for a block/fleet, the `fleet_label` MUST be validated:

```
Expected: Fleet name from PDF/results sheet (e.g., "Optimist A", "Open", "Mirror")
Actual: results.fleet_label column
Validation: Actual MUST match Expected (or manually override if PDF is wrong)
```

---

## When to Perform Checksum

### 1. During Data Import
- **After inserting all results for a block**: Immediately verify `fleet_label` matches PDF
- **Before moving to next fleet**: Ensure current fleet label is correct

### 2. After Data Import
- **Post-import validation**: Run checksum script to verify all blocks
- **Before closing data entry session**: Final verification

### 3. When Updating Data
- **After changing fleet_label**: Re-run checksum to verify consistency
- **After manual override**: Confirm override was applied correctly

---

## Checksum Process

### Step 1: Identify Expected Fleet Label
From the PDF/results sheet:
1. Look at the fleet header/name in the results section
2. Note the exact fleet designation (e.g., "Optimist A", "Open Fleet", "Mirror")
3. **Expected Fleet Label** = Fleet name as shown in PDF

### Step 2: Check Actual Fleet Label in Database
```sql
-- Check fleet_label for a block
SELECT DISTINCT fleet_label, COUNT(*) as entry_count
FROM public.results
WHERE block_id = '342-2025-sas-mirror-national-championship:mirror'
GROUP BY fleet_label;
```

### Step 3: Compare and Validate
```sql
-- Expected: "Mirror" (from PDF)
-- Actual: fleet_label = "Mirror"
-- Status: ✅ MATCH
```

---

## Validation Rules

### ✅ Valid Cases

1. **Exact Match**: Actual = Expected
   - **Status**: ✅ **VALID** - Fleet label matches PDF

2. **Case Difference Only**: Actual differs only in case
   - **Status**: ✅ **VALID** - Normalize to standard case
   - **Action**: Update to standard format (Title Case: "Optimist A", not "OPTIMIST A")

3. **Consistent Within Block**: All entries in same block have same `fleet_label`
   - **Status**: ✅ **VALID** - Internal consistency maintained

### ⚠️ Requires Manual Override

1. **PDF is Wrong**: PDF shows incorrect fleet name
   - **Status**: ⚠️ **MANUAL OVERRIDE REQUIRED**
   - **Action**: Use correct fleet name (from regatta organizers, class list, etc.)
   - **Process**: See Manual Override section below

2. **Mixed Fleet**: PDF shows multiple classes in one fleet
   - **Status**: ⚠️ **MANUAL OVERRIDE REQUIRED**
   - **Action**: Use appropriate fleet name (e.g., "Open", "Mixed", or actual fleet designation)
   - **Example**: PDF shows "420" and "505" racing together → Use "Open" or "Mixed"

3. **PDF Missing Fleet Name**: PDF doesn't show explicit fleet designation
   - **Status**: ⚠️ **MANUAL OVERRIDE REQUIRED**
   - **Action**: Use class name or appropriate fleet designation
   - **Example**: PDF only shows class "420" → Use "420" as fleet_label

### ❌ Invalid Cases

1. **NULL or Empty**: `fleet_label` IS NULL or empty string
   - **Status**: ❌ **ERROR** - Mandatory field
   - **Action**: Populate with correct fleet name

2. **"Overall"**: `fleet_label = "Overall"`
   - **Status**: ❌ **ERROR** - Meaningless, must use actual fleet name
   - **Action**: Replace with actual fleet name (e.g., "Open", "Mirror", "Optimist A")

3. **Inconsistent Within Block**: Same block has different `fleet_label` values
   - **Status**: ❌ **ERROR** - All entries in block must have same `fleet_label`
   - **Action**: Standardize to single `fleet_label` for all entries in block

4. **Mismatch with PDF**: Actual doesn't match PDF and PDF is correct
   - **Status**: ❌ **ERROR** - Data entry error
   - **Action**: Update `fleet_label` to match PDF

---

## SQL Validation Queries

### Basic Fleet Label Check
```sql
-- Check fleet_label for a specific block
SELECT 
    block_id,
    fleet_label,
    COUNT(*) as entry_count,
    COUNT(DISTINCT fleet_label) as unique_labels
FROM public.results
WHERE block_id = '342-2025-sas-mirror-national-championship:mirror'
GROUP BY block_id, fleet_label;
```

### Check for Inconsistencies
```sql
-- Find blocks with multiple fleet_labels
SELECT 
    block_id,
    COUNT(DISTINCT fleet_label) as unique_labels,
    STRING_AGG(DISTINCT fleet_label, ', ') as all_fleet_labels,
    COUNT(*) as total_entries
FROM public.results
WHERE block_id IS NOT NULL
GROUP BY block_id
HAVING COUNT(DISTINCT fleet_label) > 1;
```

### Check for NULL or "Overall"
```sql
-- Find NULL or "Overall" fleet_labels
SELECT 
    block_id,
    fleet_label,
    COUNT(*) as entry_count
FROM public.results
WHERE fleet_label IS NULL 
   OR fleet_label = ''
   OR UPPER(fleet_label) = 'OVERALL'
GROUP BY block_id, fleet_label;
```

### Compare with regatta_blocks
```sql
-- Compare results.fleet_label vs regatta_blocks.fleet_label
SELECT 
    rb.block_id,
    rb.fleet_label as block_fleet_label,
    r.fleet_label as result_fleet_label,
    COUNT(*) as entry_count,
    CASE 
        WHEN rb.fleet_label IS NULL AND r.fleet_label IS NULL THEN '⚠️ Both NULL'
        WHEN rb.fleet_label IS NOT NULL AND r.fleet_label IS NULL THEN '❌ Block has value, Result NULL'
        WHEN UPPER(COALESCE(rb.fleet_label, '')) = UPPER(COALESCE(r.fleet_label, '')) THEN '✅ Match'
        ELSE '⚠️ Mismatch'
    END as status
FROM public.regatta_blocks rb
LEFT JOIN public.results r ON r.block_id = rb.block_id
WHERE rb.fleet_label IS DISTINCT FROM r.fleet_label
GROUP BY rb.block_id, rb.fleet_label, r.fleet_label;
```

---

## Manual Override Process

### When to Override

**Rare cases** where PDF is incorrect or ambiguous:
1. PDF shows wrong fleet name (typo in source document)
2. PDF shows "Overall" but actual fleet is known
3. PDF doesn't show fleet name (only class)
4. Mixed fleet racing together (need appropriate designation)

### Override Steps

#### Step 1: Verify Correct Fleet Name
- Check regatta organizers' documentation
- Check class list or fleet assignments
- Check other sources (website, notices, etc.)
- **Confirm**: What is the correct fleet name?

#### Step 2: Update results.fleet_label
```sql
-- Update all entries in block to correct fleet_label
UPDATE public.results
SET fleet_label = 'CORRECT_FLEET_NAME'
WHERE block_id = 'BLOCK-ID-HERE';

-- Verify update
SELECT DISTINCT fleet_label, COUNT(*)
FROM public.results
WHERE block_id = 'BLOCK-ID-HERE'
GROUP BY fleet_label;
```

#### Step 3: Update regatta_blocks.fleet_label
```sql
-- Update block-level fleet_label to match
UPDATE public.regatta_blocks
SET fleet_label = 'CORRECT_FLEET_NAME'
WHERE block_id = 'BLOCK-ID-HERE';

-- Verify update
SELECT block_id, fleet_label
FROM public.regatta_blocks
WHERE block_id = 'BLOCK-ID-HERE';
```

#### Step 4: Re-run Checksum
```sql
-- Verify fix worked
SELECT 
    block_id,
    fleet_label,
    COUNT(*) as entry_count,
    COUNT(DISTINCT fleet_label) as unique_labels
FROM public.results
WHERE block_id = 'BLOCK-ID-HERE'
GROUP BY block_id, fleet_label;
-- Expected: unique_labels = 1 (all same)
```

### Override Documentation

**When overriding**, document:
- **Block ID**: Which block was overridden
- **PDF Value**: What PDF showed
- **Override Value**: What was used instead
- **Reason**: Why override was necessary
- **Date**: When override was applied

---

## Integration with Data Entry Process

### During Import (Manual Process)

1. **Extract Fleet Name**: Identify fleet designation from PDF header
2. **Set fleet_label**: Use fleet name from PDF (e.g., "Optimist A", "Open")
3. **Import Data**: INSERT all results with consistent `fleet_label`
4. **Immediate Checksum**: Verify all entries have same `fleet_label`
5. **Compare with PDF**: Confirm matches PDF exactly
6. **Override if needed**: Apply manual override if PDF is wrong

### Example Workflow

```sql
-- Step 1: PDF shows "Optimist A" fleet
-- Expected: fleet_label = "Optimist A"

-- Step 2: Import all rows with fleet_label
INSERT INTO public.results (
    block_id,
    fleet_label,  -- Set from PDF: "Optimist A"
    rank,
    helm_name,
    ...
) VALUES (...);

-- Step 3: Verify consistency
SELECT DISTINCT fleet_label, COUNT(*)
FROM public.results
WHERE block_id = '342-2025-regatta-id:optimist-a'
GROUP BY fleet_label;
-- Expected: Only "Optimist A", all entries

-- Step 4: If PDF showed "Overall" but actual is "Optimist A"
-- Apply manual override
UPDATE public.results
SET fleet_label = 'Optimist A'
WHERE block_id = '342-2025-regatta-id:optimist-a'
  AND fleet_label = 'Overall';
```

---

## Automation Script

Run validation script after import:

```bash
psql "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master" \
  -f admin/tools/checksum_fleet_label.sql
```

This script will:
1. Check for NULL or empty `fleet_label`
2. Check for "Overall" usage
3. Identify inconsistencies within blocks
4. Compare with `regatta_blocks.fleet_label`
5. Provide manual override instructions

---

## Common Issues

### Issue 1: NULL fleet_label
**Symptom**: `fleet_label IS NULL`  
**Cause**: Not populated during import  
**Fix**: Set to correct fleet name from PDF or manual override

### Issue 2: "Overall" as fleet_label
**Symptom**: `fleet_label = "Overall"`  
**Cause**: PDF shows "Overall" (meaningless)  
**Fix**: Replace with actual fleet name (manual override)

### Issue 3: Inconsistent Within Block
**Symptom**: Same block has different `fleet_label` values  
**Cause**: Data entry error, mixed values during import  
**Fix**: Standardize all entries in block to same `fleet_label`

### Issue 4: Mismatch with PDF
**Symptom**: `fleet_label` doesn't match PDF  
**Cause**: PDF typo or data entry error  
**Fix**: If PDF wrong → manual override, if data wrong → fix to match PDF

---

## Standard Fleet Label Values

### Common Fleet Designations

- **Class-Based**: "Optimist A", "Optimist B", "ILCA 6", "ILCA 7", "420", "505"
- **Level-Based**: "Gold", "Silver", "Bronze", "Open", "Championship"
- **Mixed Fleets**: "Open", "Mixed", "Combined"
- **Age-Based**: "Youth", "Senior", "Masters"

### Format Rules

- **Title Case**: "Optimist A" (not "OPTIMIST A" or "optimist a")
- **Consistent**: All entries in same block must have identical `fleet_label`
- **Meaningful**: Never use "Overall" - use actual fleet designation

---

## Fleet Label Validation Against Classes Table

**CRITICAL RULE**: `fleet_label` should match a valid `class_name` from the `classes` table, unless manually overridden and authorized.

### Validation Against Classes

Run validation script:
```bash
psql "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master" \
  -f admin/tools/validate_fleet_label_from_classes.sql
```

This validates:
1. ✅ **Valid Classes**: `fleet_label` matches `class_name` in `classes` table
2. ⚠️ **Manual Overrides**: Authorized overrides (e.g., "Er" for Er Fleet)
3. ⚠️ **Generic Fleets**: "Open", "Mixed", "Combined" (may be valid but review)
4. ❌ **Invalid**: `fleet_label` doesn't match any class (requires fix or authorization)

### Authorized Manual Overrides

Current authorized overrides:
- **"Er"**: Er Fleet (for 29Er and 49Er classes combined)

To add new override:
1. Update validation script: Add to `WHERE r.fleet_label IN ('Er', 'NEW_OVERRIDE')`
2. Document reason for override
3. Ensure override is consistent across all related blocks

## Documentation

- **Validation Script**: `admin/tools/checksum_fleet_label.sql`
- **Classes Validation**: `admin/tools/validate_fleet_label_from_classes.sql`
- **Data Entry Standards**: `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md`
- **Fleet Label Rules**: `docs/DATA_FORMAT_SPECIFICATIONS.md` (fleet_label section)

---

## Summary

**CRITICAL RULE**: Always verify `fleet_label` after import:

1. ✅ Extract fleet name from PDF/results sheet
2. ✅ Set `fleet_label` consistently for all entries in block
3. ✅ Verify: All entries in block have same `fleet_label`
4. ✅ Compare: Must match PDF (or apply manual override if PDF wrong)
5. ✅ Fix inconsistencies before proceeding

**Manual override is for rare cases only** when PDF is incorrect or ambiguous.


## Purpose
Validate that `fleet_label` matches the expected fleet name from the results sheet/PDF, with manual override process for rare cases.

## Critical Rule

**CRITICAL**: After importing data for a block/fleet, the `fleet_label` MUST be validated:

```
Expected: Fleet name from PDF/results sheet (e.g., "Optimist A", "Open", "Mirror")
Actual: results.fleet_label column
Validation: Actual MUST match Expected (or manually override if PDF is wrong)
```

---

## When to Perform Checksum

### 1. During Data Import
- **After inserting all results for a block**: Immediately verify `fleet_label` matches PDF
- **Before moving to next fleet**: Ensure current fleet label is correct

### 2. After Data Import
- **Post-import validation**: Run checksum script to verify all blocks
- **Before closing data entry session**: Final verification

### 3. When Updating Data
- **After changing fleet_label**: Re-run checksum to verify consistency
- **After manual override**: Confirm override was applied correctly

---

## Checksum Process

### Step 1: Identify Expected Fleet Label
From the PDF/results sheet:
1. Look at the fleet header/name in the results section
2. Note the exact fleet designation (e.g., "Optimist A", "Open Fleet", "Mirror")
3. **Expected Fleet Label** = Fleet name as shown in PDF

### Step 2: Check Actual Fleet Label in Database
```sql
-- Check fleet_label for a block
SELECT DISTINCT fleet_label, COUNT(*) as entry_count
FROM public.results
WHERE block_id = '342-2025-sas-mirror-national-championship:mirror'
GROUP BY fleet_label;
```

### Step 3: Compare and Validate
```sql
-- Expected: "Mirror" (from PDF)
-- Actual: fleet_label = "Mirror"
-- Status: ✅ MATCH
```

---

## Validation Rules

### ✅ Valid Cases

1. **Exact Match**: Actual = Expected
   - **Status**: ✅ **VALID** - Fleet label matches PDF

2. **Case Difference Only**: Actual differs only in case
   - **Status**: ✅ **VALID** - Normalize to standard case
   - **Action**: Update to standard format (Title Case: "Optimist A", not "OPTIMIST A")

3. **Consistent Within Block**: All entries in same block have same `fleet_label`
   - **Status**: ✅ **VALID** - Internal consistency maintained

### ⚠️ Requires Manual Override

1. **PDF is Wrong**: PDF shows incorrect fleet name
   - **Status**: ⚠️ **MANUAL OVERRIDE REQUIRED**
   - **Action**: Use correct fleet name (from regatta organizers, class list, etc.)
   - **Process**: See Manual Override section below

2. **Mixed Fleet**: PDF shows multiple classes in one fleet
   - **Status**: ⚠️ **MANUAL OVERRIDE REQUIRED**
   - **Action**: Use appropriate fleet name (e.g., "Open", "Mixed", or actual fleet designation)
   - **Example**: PDF shows "420" and "505" racing together → Use "Open" or "Mixed"

3. **PDF Missing Fleet Name**: PDF doesn't show explicit fleet designation
   - **Status**: ⚠️ **MANUAL OVERRIDE REQUIRED**
   - **Action**: Use class name or appropriate fleet designation
   - **Example**: PDF only shows class "420" → Use "420" as fleet_label

### ❌ Invalid Cases

1. **NULL or Empty**: `fleet_label` IS NULL or empty string
   - **Status**: ❌ **ERROR** - Mandatory field
   - **Action**: Populate with correct fleet name

2. **"Overall"**: `fleet_label = "Overall"`
   - **Status**: ❌ **ERROR** - Meaningless, must use actual fleet name
   - **Action**: Replace with actual fleet name (e.g., "Open", "Mirror", "Optimist A")

3. **Inconsistent Within Block**: Same block has different `fleet_label` values
   - **Status**: ❌ **ERROR** - All entries in block must have same `fleet_label`
   - **Action**: Standardize to single `fleet_label` for all entries in block

4. **Mismatch with PDF**: Actual doesn't match PDF and PDF is correct
   - **Status**: ❌ **ERROR** - Data entry error
   - **Action**: Update `fleet_label` to match PDF

---

## SQL Validation Queries

### Basic Fleet Label Check
```sql
-- Check fleet_label for a specific block
SELECT 
    block_id,
    fleet_label,
    COUNT(*) as entry_count,
    COUNT(DISTINCT fleet_label) as unique_labels
FROM public.results
WHERE block_id = '342-2025-sas-mirror-national-championship:mirror'
GROUP BY block_id, fleet_label;
```

### Check for Inconsistencies
```sql
-- Find blocks with multiple fleet_labels
SELECT 
    block_id,
    COUNT(DISTINCT fleet_label) as unique_labels,
    STRING_AGG(DISTINCT fleet_label, ', ') as all_fleet_labels,
    COUNT(*) as total_entries
FROM public.results
WHERE block_id IS NOT NULL
GROUP BY block_id
HAVING COUNT(DISTINCT fleet_label) > 1;
```

### Check for NULL or "Overall"
```sql
-- Find NULL or "Overall" fleet_labels
SELECT 
    block_id,
    fleet_label,
    COUNT(*) as entry_count
FROM public.results
WHERE fleet_label IS NULL 
   OR fleet_label = ''
   OR UPPER(fleet_label) = 'OVERALL'
GROUP BY block_id, fleet_label;
```

### Compare with regatta_blocks
```sql
-- Compare results.fleet_label vs regatta_blocks.fleet_label
SELECT 
    rb.block_id,
    rb.fleet_label as block_fleet_label,
    r.fleet_label as result_fleet_label,
    COUNT(*) as entry_count,
    CASE 
        WHEN rb.fleet_label IS NULL AND r.fleet_label IS NULL THEN '⚠️ Both NULL'
        WHEN rb.fleet_label IS NOT NULL AND r.fleet_label IS NULL THEN '❌ Block has value, Result NULL'
        WHEN UPPER(COALESCE(rb.fleet_label, '')) = UPPER(COALESCE(r.fleet_label, '')) THEN '✅ Match'
        ELSE '⚠️ Mismatch'
    END as status
FROM public.regatta_blocks rb
LEFT JOIN public.results r ON r.block_id = rb.block_id
WHERE rb.fleet_label IS DISTINCT FROM r.fleet_label
GROUP BY rb.block_id, rb.fleet_label, r.fleet_label;
```

---

## Manual Override Process

### When to Override

**Rare cases** where PDF is incorrect or ambiguous:
1. PDF shows wrong fleet name (typo in source document)
2. PDF shows "Overall" but actual fleet is known
3. PDF doesn't show fleet name (only class)
4. Mixed fleet racing together (need appropriate designation)

### Override Steps

#### Step 1: Verify Correct Fleet Name
- Check regatta organizers' documentation
- Check class list or fleet assignments
- Check other sources (website, notices, etc.)
- **Confirm**: What is the correct fleet name?

#### Step 2: Update results.fleet_label
```sql
-- Update all entries in block to correct fleet_label
UPDATE public.results
SET fleet_label = 'CORRECT_FLEET_NAME'
WHERE block_id = 'BLOCK-ID-HERE';

-- Verify update
SELECT DISTINCT fleet_label, COUNT(*)
FROM public.results
WHERE block_id = 'BLOCK-ID-HERE'
GROUP BY fleet_label;
```

#### Step 3: Update regatta_blocks.fleet_label
```sql
-- Update block-level fleet_label to match
UPDATE public.regatta_blocks
SET fleet_label = 'CORRECT_FLEET_NAME'
WHERE block_id = 'BLOCK-ID-HERE';

-- Verify update
SELECT block_id, fleet_label
FROM public.regatta_blocks
WHERE block_id = 'BLOCK-ID-HERE';
```

#### Step 4: Re-run Checksum
```sql
-- Verify fix worked
SELECT 
    block_id,
    fleet_label,
    COUNT(*) as entry_count,
    COUNT(DISTINCT fleet_label) as unique_labels
FROM public.results
WHERE block_id = 'BLOCK-ID-HERE'
GROUP BY block_id, fleet_label;
-- Expected: unique_labels = 1 (all same)
```

### Override Documentation

**When overriding**, document:
- **Block ID**: Which block was overridden
- **PDF Value**: What PDF showed
- **Override Value**: What was used instead
- **Reason**: Why override was necessary
- **Date**: When override was applied

---

## Integration with Data Entry Process

### During Import (Manual Process)

1. **Extract Fleet Name**: Identify fleet designation from PDF header
2. **Set fleet_label**: Use fleet name from PDF (e.g., "Optimist A", "Open")
3. **Import Data**: INSERT all results with consistent `fleet_label`
4. **Immediate Checksum**: Verify all entries have same `fleet_label`
5. **Compare with PDF**: Confirm matches PDF exactly
6. **Override if needed**: Apply manual override if PDF is wrong

### Example Workflow

```sql
-- Step 1: PDF shows "Optimist A" fleet
-- Expected: fleet_label = "Optimist A"

-- Step 2: Import all rows with fleet_label
INSERT INTO public.results (
    block_id,
    fleet_label,  -- Set from PDF: "Optimist A"
    rank,
    helm_name,
    ...
) VALUES (...);

-- Step 3: Verify consistency
SELECT DISTINCT fleet_label, COUNT(*)
FROM public.results
WHERE block_id = '342-2025-regatta-id:optimist-a'
GROUP BY fleet_label;
-- Expected: Only "Optimist A", all entries

-- Step 4: If PDF showed "Overall" but actual is "Optimist A"
-- Apply manual override
UPDATE public.results
SET fleet_label = 'Optimist A'
WHERE block_id = '342-2025-regatta-id:optimist-a'
  AND fleet_label = 'Overall';
```

---

## Automation Script

Run validation script after import:

```bash
psql "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master" \
  -f admin/tools/checksum_fleet_label.sql
```

This script will:
1. Check for NULL or empty `fleet_label`
2. Check for "Overall" usage
3. Identify inconsistencies within blocks
4. Compare with `regatta_blocks.fleet_label`
5. Provide manual override instructions

---

## Common Issues

### Issue 1: NULL fleet_label
**Symptom**: `fleet_label IS NULL`  
**Cause**: Not populated during import  
**Fix**: Set to correct fleet name from PDF or manual override

### Issue 2: "Overall" as fleet_label
**Symptom**: `fleet_label = "Overall"`  
**Cause**: PDF shows "Overall" (meaningless)  
**Fix**: Replace with actual fleet name (manual override)

### Issue 3: Inconsistent Within Block
**Symptom**: Same block has different `fleet_label` values  
**Cause**: Data entry error, mixed values during import  
**Fix**: Standardize all entries in block to same `fleet_label`

### Issue 4: Mismatch with PDF
**Symptom**: `fleet_label` doesn't match PDF  
**Cause**: PDF typo or data entry error  
**Fix**: If PDF wrong → manual override, if data wrong → fix to match PDF

---

## Standard Fleet Label Values

### Common Fleet Designations

- **Class-Based**: "Optimist A", "Optimist B", "ILCA 6", "ILCA 7", "420", "505"
- **Level-Based**: "Gold", "Silver", "Bronze", "Open", "Championship"
- **Mixed Fleets**: "Open", "Mixed", "Combined"
- **Age-Based**: "Youth", "Senior", "Masters"

### Format Rules

- **Title Case**: "Optimist A" (not "OPTIMIST A" or "optimist a")
- **Consistent**: All entries in same block must have identical `fleet_label`
- **Meaningful**: Never use "Overall" - use actual fleet designation

---

## Fleet Label Validation Against Classes Table

**CRITICAL RULE**: `fleet_label` should match a valid `class_name` from the `classes` table, unless manually overridden and authorized.

### Validation Against Classes

Run validation script:
```bash
psql "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master" \
  -f admin/tools/validate_fleet_label_from_classes.sql
```

This validates:
1. ✅ **Valid Classes**: `fleet_label` matches `class_name` in `classes` table
2. ⚠️ **Manual Overrides**: Authorized overrides (e.g., "Er" for Er Fleet)
3. ⚠️ **Generic Fleets**: "Open", "Mixed", "Combined" (may be valid but review)
4. ❌ **Invalid**: `fleet_label` doesn't match any class (requires fix or authorization)

### Authorized Manual Overrides

Current authorized overrides:
- **"Er"**: Er Fleet (for 29Er and 49Er classes combined)

To add new override:
1. Update validation script: Add to `WHERE r.fleet_label IN ('Er', 'NEW_OVERRIDE')`
2. Document reason for override
3. Ensure override is consistent across all related blocks

## Documentation

- **Validation Script**: `admin/tools/checksum_fleet_label.sql`
- **Classes Validation**: `admin/tools/validate_fleet_label_from_classes.sql`
- **Data Entry Standards**: `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md`
- **Fleet Label Rules**: `docs/DATA_FORMAT_SPECIFICATIONS.md` (fleet_label section)

---

## Summary

**CRITICAL RULE**: Always verify `fleet_label` after import:

1. ✅ Extract fleet name from PDF/results sheet
2. ✅ Set `fleet_label` consistently for all entries in block
3. ✅ Verify: All entries in block have same `fleet_label`
4. ✅ Compare: Must match PDF (or apply manual override if PDF wrong)
5. ✅ Fix inconsistencies before proceeding

**Manual override is for rare cases only** when PDF is incorrect or ambiguous.

