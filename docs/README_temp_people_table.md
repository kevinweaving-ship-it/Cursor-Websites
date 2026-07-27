# TEMP_PEOPLE Table - GPT Rules & Data Structure

## Purpose
Stores temporary sailor records for unidentified sailors until they can be matched to official SA Sailing IDs.

## Table Structure
```sql
CREATE TABLE temp_people (
    temp_id SERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,                -- Name as it appears in results
    first_name TEXT,                        -- Extracted first name
    last_name TEXT,                         -- Extracted last name
    club_raw TEXT,                          -- Club as printed in results
    club_id INTEGER REFERENCES clubs(club_id), -- Mapped club (if identified)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    matched_at TIMESTAMP,                   -- When matched to official SA Sailing ID
    matched_sa_sailing_id TEXT REFERENCES sailing_id(sa_sailing_id) -- Official ID when matched
);
```

## Data Rules (from GPT instructions)

### Temporary Record Creation
1. **NEVER CREATE TEMP IDs WITHOUT USER PERMISSION** - Always validate SAS IDs first and get explicit approval
2. **ALWAYS VALIDATE SAS IDs FIRST** - Search sailing_id table thoroughly before considering Temp ID
3. **Present unmatched sailors** to user for decision before creating any Temp IDs
4. **Check for nicknames/variants** (e.g., "Max" vs "Maximilian", "Ben" vs "Benjamin")
5. **Present ambiguous cases to user** for decision before creating any Temp IDs
6. **Store name exactly** as it appears in results
7. **Attempt club mapping** if possible
8. **Generate unique temp_id** for tracking
9. **ALWAYS use lowest available Temp ID** to fill gaps in sequence (e.g., if 1,2,8,15 exist, use 3,4,5,6,7,9,10,11,12,13,14,16,17,18...)
10. **Delete duplicate Temp IDs** when SAS ID is found for same sailor

### Temp ID Format in Results Table
- **ALWAYS use "TMP:" prefix** when storing in results.helm_temp_id or results.crew_temp_id
- **Correct format**: "TMP:1", "TMP:15", "TMP:28"
- **NEVER use**: "1", "15", "T16" (inconsistent formats)
- **Example**: `UPDATE results SET helm_temp_id = 'TMP:1' WHERE ...`

### Matching Process
1. **Search sailing_id table** using name variations
2. **Use promote_temp_to_official function** when match found
3. **Update associated results** to use official SA Sailing ID
4. **Mark temp record as matched** with timestamp

### Data Integrity Rules
1. **NEVER use placeholders** - only real data or NULL
2. **NEVER invent names** - extract exactly from results
3. **ALWAYS attempt club mapping** when possible
4. **ALWAYS use promote function** for upgrades
5. **PRESERVE original names** exactly as printed

## Example Data
```sql
INSERT INTO temp_people (full_name, first_name, last_name, club_raw, club_id) VALUES
('John Smith', 'John', 'Smith', 'RNYC', 1),
('Jane Doe', 'Jane', 'Doe', 'ZVYC', 2),
('Unknown Sailor', 'Unknown', 'Sailor', 'HMYC', 3);
```

## Related Tables
- `sailing_id` - Official SA Sailing records
- `results.helm_sa_sailing_id` - Links to helm sailor
- `results.crew_sa_sailing_id` - Links to crew sailor
- `clubs` - Club information

## Promotion Function
```sql
CREATE OR REPLACE FUNCTION promote_temp_to_official(
    p_temp_id INTEGER,
    p_sa_sailing_id TEXT
) RETURNS VOID AS $$
BEGIN
    -- Update temp_people record
    UPDATE temp_people 
    SET matched_sa_sailing_id = p_sa_sailing_id,
        matched_at = CURRENT_TIMESTAMP
    WHERE temp_id = p_temp_id;
    
    -- Update associated results
    UPDATE results 
    SET helm_sa_sailing_id = p_sa_sailing_id
    WHERE helm_sa_sailing_id = 'temp_' || p_temp_id::text;
    
    UPDATE results 
    SET crew_sa_sailing_id = p_sa_sailing_id
    WHERE crew_sa_sailing_id = 'temp_' || p_temp_id::text;
END;
$$ LANGUAGE plpgsql;
```
