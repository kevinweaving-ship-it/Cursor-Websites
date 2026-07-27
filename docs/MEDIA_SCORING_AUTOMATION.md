# Media Scoring Automation for New Podium Results

## Overview

After completing comprehensive passes 1-3 to audit the entire SAS ID table for media scores, we now have the same (or more) information than sailing.org.za has searchable/reachable on the web.

**Key Principle:** The only way sailors without media scores can get one is through **NEW results** where they podium (rank 1-3).

## Logic

1. **Completed Audits:**
   - ✅ First Pass: Initial baseline scoring
   - ✅ Second Pass: All 898 sailors with focused query `"{NAME}" South African Sailing`
   - ✅ Third Pass: Podium finishers at National/Provincial/Regional events

2. **Going Forward:**
   - Only **NEW podium results** can create new media scores
   - If a sailor podiums in a sailing.org.za result, there should be at least a `sailing.org.za` URL where they placed 1st-3rd
   - All new podium results must be processed through passes 1-3

## Automation Script

### `process_new_podium_media_scores.py`

This script automatically identifies and processes sailors who have podiumed in new regatta results.

**Features:**
- Detects new podium results (rank 1-3)
- Only processes sailors who don't have media scores (`media_score = 0`)
- Processes through media scoring passes 1-3
- Can be triggered manually or scheduled

**Usage:**

```bash
# Process all new podium results from last 30 days (default)
python3 process_new_podium_media_scores.py

# Process podium results for a specific regatta
python3 process_new_podium_media_scores.py --regatta-id REGATTA_ID

# Process podium results since a specific date
python3 process_new_podium_media_scores.py --since-date 2025-01-01

# Dry run (see what would be processed)
python3 process_new_podium_media_scores.py --dry-run
```

## Integration Points

### Option 1: Manual Trigger After Regatta Upload

After uploading new regatta results:

```bash
# Process new podium results
python3 process_new_podium_media_scores.py --regatta-id NEW_REGATTA_ID
```

### Option 2: Scheduled Job (Cron)

Run daily/weekly to catch any new podium results:

```bash
# Add to crontab (runs daily at 2 AM)
0 2 * * * cd /path/to/project && python3 process_new_podium_media_scores.py >> logs/media_scoring.log 2>&1
```

### Option 3: Database Trigger (PostgreSQL)

Create a trigger that runs the script when new results are inserted:

```sql
-- Example trigger (would need to call Python script via pg_notify or similar)
CREATE OR REPLACE FUNCTION notify_new_podium_result()
RETURNS TRIGGER AS $$
BEGIN
    -- When new result with rank <= 3 is inserted
    IF NEW.rank <= 3 THEN
        -- Notify or queue for processing
        PERFORM pg_notify('new_podium_result', NEW.regatta_id::text);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_new_podium_result
AFTER INSERT ON results
FOR EACH ROW
WHEN (NEW.rank <= 3 AND NEW.raced = TRUE)
EXECUTE FUNCTION notify_new_podium_result();
```

### Option 4: API Hook

If regatta results are uploaded via API, add a hook after successful upload:

```python
# In your API endpoint after regatta upload
from process_new_podium_media_scores import get_new_podium_sailors, process_new_podium_sailor

# After inserting results
podium_sailors = get_new_podium_sailors(conn, regatta_id=new_regatta_id)
for sa_id, name, regatta_id, rank, event_name in podium_sailors:
    process_new_podium_sailor(conn, sa_id, name, regatta_id, rank, event_name)
```

## Expected Behavior

When a sailor podiums in a new regatta:

1. **Detection:** Script identifies sailor with `rank <= 3` and `media_score = 0`
2. **Processing:** Runs through media scoring passes 1-3
3. **Expected Result:** Should find at least one `sailing.org.za` URL with their result
4. **Score Update:** Media score updated from 0 to at least 1

## Monitoring

Check processing status:

```sql
-- Sailors who recently got media scores from new podiums
SELECT 
    sms.sa_id,
    sms.sailor_name,
    sms.media_score,
    sms.processed_at,
    COUNT(DISTINCT r.regatta_id) as podium_regattas
FROM sailor_media_score sms
JOIN results r ON (
    COALESCE(r.helm_sa_sailing_id::text, r.crew_sa_sailing_id::text) = sms.sa_id
    AND r.rank <= 3
    AND r.raced = TRUE
)
WHERE sms.media_score > 0
  AND sms.processed_at >= NOW() - INTERVAL '30 days'
GROUP BY sms.sa_id, sms.sailor_name, sms.media_score, sms.processed_at
ORDER BY sms.processed_at DESC;
```

## Notes

- The script uses the same filtering and scoring logic as `third_pass_podium_sailors.py`
- Trusted sailing domains (sailing.org.za, sailwave.com, etc.) are automatically accepted
- URL validation ensures only valid, accessible URLs are counted
- Scores are capped at 10 (1 URL = 1 point, max 10 points)
