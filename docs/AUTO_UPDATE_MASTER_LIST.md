# Auto-Update Master List System

**Version:** 1.0  
**Date:** December 30, 2025  
**Status:** Active

---

## Overview

This system automatically updates the `master_list` table with valid sailors per class whenever new regatta results are added. It includes checksum validation to ensure data integrity.

---

## Components

### 1. Python Script: `auto_update_master_list.py`

**Purpose:** Command-line tool to update master_list with checksum validation

**Usage:**
```bash
# Update all classes
python3 auto_update_master_list.py

# Update specific class
python3 auto_update_master_list.py --class "420"

# Dry run (show changes without applying)
python3 auto_update_master_list.py --dry-run

# Update with age limit
python3 auto_update_master_list.py --class "Optimist A" --age-limit 15
```

**Features:**
- ✅ Detects new sailors automatically
- ✅ Validates eligibility (raced, helm, time period, age)
- ✅ Checksum validation to ensure data integrity
- ✅ Shows what will change before applying
- ✅ Reports validation results

---

### 2. Database Functions: `auto_update_master_list_trigger.sql`

**Purpose:** PostgreSQL functions for automatic updates

**Functions:**
1. **`auto_update_master_list_for_class(class_name)`**
   - Updates master_list for a specific class
   - Returns statistics (counts, changes, validation)

2. **`update_all_master_lists()`**
   - Updates all classes at once
   - For scheduled jobs

3. **`trigger_auto_update_master_list()`** (optional)
   - Database trigger function
   - Automatically runs when new results are inserted

**Usage:**
```sql
-- Update specific class
SELECT * FROM auto_update_master_list_for_class('420');

-- Update all classes
SELECT * FROM update_all_master_lists();
```

---

## Validation & Checksum

### Checksum Calculation

The system calculates a checksum of all sailor IDs to validate that:
1. All valid sailors are in master_list
2. No sailors are missing
3. No duplicate entries

**Formula:**
```
checksum = MD5(sorted(sailor_ids).join('|'))
```

### Validation Rules

1. **Count Match:** `master_list.active_count == valid_sailors.count`
2. **Checksum Match:** `master_list.checksum == valid_sailors.checksum`
3. **All Sailors Present:** Every valid sailor must be in master_list

---

## Criteria for Valid Sailors

Based on `docs/README_STANDINGS_MASTER.md` Step 1:

1. ✅ Has raced in the class (`raced = TRUE`)
2. ✅ Is a helm (not crew-only)
3. ✅ Raced within last 13 months
4. ✅ Excludes Regatta 374 (incomplete regattas)
5. ✅ Meets age eligibility (if applicable)

---

## Automated Workflow

### Option 1: Scheduled Job (Recommended)

**Cron Job (Daily):**
```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/project && python3 auto_update_master_list.py >> /var/log/master_list_update.log 2>&1
```

**Cron Job (After Results Import):**
```bash
# Run after results import script
python3 import_results.py && python3 auto_update_master_list.py
```

### Option 2: Database Trigger (Optional)

**Enable automatic trigger:**
```sql
-- Uncomment in auto_update_master_list_trigger.sql
CREATE TRIGGER trg_auto_update_master_list
    AFTER INSERT OR UPDATE ON results
    FOR EACH ROW
    WHEN (NEW.raced = TRUE)
    EXECUTE FUNCTION trigger_auto_update_master_list();
```

**Note:** Triggers run synchronously and may slow down bulk inserts. Use scheduled jobs for better performance.

### Option 3: API Endpoint (Future)

Add API endpoint to trigger updates:
```python
@app.post("/api/admin/update-master-list")
def api_update_master_list(class_name: Optional[str] = None):
    # Call auto_update_master_list.py or database function
    pass
```

---

## Integration with Results Import

### Recommended Workflow

1. **Import Results:**
   ```bash
   python3 import_regatta_results.py --regatta 375
   ```

2. **Auto-Update Master List:**
   ```bash
   python3 auto_update_master_list.py
   ```

3. **Recalculate Standings:**
   ```bash
   python3 calculate_all_standings.py --class "420"
   ```

### Automated Script

Create `import_and_update.sh`:
```bash
#!/bin/bash
# Import results and auto-update master list

REGATTA_ID=$1
CLASS_NAME=$2

# Import results
python3 import_regatta_results.py --regatta $REGATTA_ID

# Update master list
if [ -z "$CLASS_NAME" ]; then
    python3 auto_update_master_list.py
else
    python3 auto_update_master_list.py --class "$CLASS_NAME"
fi

# Recalculate standings
if [ -z "$CLASS_NAME" ]; then
    python3 calculate_all_standings.py
else
    python3 calculate_all_standings.py --class "$CLASS_NAME"
fi
```

---

## Monitoring & Logging

### Check for Unprocessed Regattas

```sql
SELECT 
    class_name,
    COUNT(*) as unprocessed_count
FROM (
    SELECT DISTINCT
        COALESCE(rb.class_canonical, rb.fleet_label) as class_name,
        reg.regatta_id
    FROM results r
    JOIN regatta_blocks rb ON rb.block_id = r.block_id
    JOIN regattas reg ON reg.regatta_id = r.regatta_id
    WHERE r.raced = TRUE
      AND reg.regatta_number != 374
      AND reg.regatta_id NOT IN (
          SELECT regatta_id FROM processed_regattas
      )
) unprocessed
GROUP BY class_name
ORDER BY unprocessed_count DESC;
```

### Validate Master List

```sql
-- Check counts match
SELECT 
    ml.class_name,
    COUNT(*) as master_list_count,
    COUNT(CASE WHEN ml.is_active = TRUE THEN 1 END) as active_count
FROM master_list ml
GROUP BY ml.class_name
ORDER BY ml.class_name;
```

---

## Troubleshooting

### Issue: New sailors not added

**Check:**
1. Sailor meets eligibility criteria (raced, helm, time period)
2. Age limit not exceeded (if applicable)
3. Regatta not excluded (e.g., Regatta 374)

**Fix:**
```bash
# Run with verbose output
python3 auto_update_master_list.py --class "CLASS_NAME" --dry-run
```

### Issue: Checksum mismatch

**Check:**
1. Database transaction completed
2. No concurrent updates
3. All valid sailors included

**Fix:**
```bash
# Re-run update
python3 auto_update_master_list.py --class "CLASS_NAME"
```

### Issue: Performance slow

**Solutions:**
1. Use scheduled jobs instead of triggers
2. Update specific classes only
3. Run during off-peak hours

---

## Related Documentation

- `docs/README_STANDINGS_MASTER.md` - Master list system overview
- `docs/YOUTH_STANDINGS_RULES.md` - Youth standings rules
- `calculate_all_standings.py` - Standings calculation script

---

**Last Updated:** December 30, 2025

