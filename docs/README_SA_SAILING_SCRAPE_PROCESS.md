# SA Sailing ID Scraping Process & Data Flow

## Overview
This document describes the complete process for scraping SA Sailing IDs from the official website and inserting them into the `sas_id_personal` table.

## Corrected architecture (SAS ID)

**Full specification:** [SAS_SCRAPE_ARCHITECTURE.md](SAS_SCRAPE_ARCHITECTURE.md)

- **DOCUMENTED_SAS_MAX_ID** — Manual snapshot from member-finder (e.g. **28406** as of Feb 2026). Not a permanent ceiling; verify periodically.
- **DETECTED_SAS_MAX_ID** — Auto-probed by incremental scraper; recorded in `sas_scrape_batches.detected_upper_bound`. Operational upper bound.
- **Registry expansion:** Writes only to `sas_id_registry`. No automatic merge into sailors table, no identity resolution, no qualification scrape.
- **Incremental scrape:** Start at `MAX(sas_id)+1`, probe sequentially, stop after N consecutive NOT_FOUND (e.g. N=20), record detected upper bound, log batch.
- **Staging rule:** Never write scraped results directly into race_results; use staging tables.
- **Batch logging:** Every run records `batch_id`, `start_id`, `end_id`, `detected_upper_bound`, `valid_count`, `not_found_count`, `error_count`, `started_at`, `completed_at` in `sas_scrape_batches`.

---

## Table of Contents
1. [Scraping Source](#scraping-source)
2. [Data Flow Process](#data-flow-process)
3. [Name Parsing Rules](#name-parsing-rules)
4. [Database Schema](#database-schema)
5. [No Record Found Handling](#no-record-found-handling)
6. [Step-by-Step Process](#step-by-step-process)
7. [Automation Considerations](#automation-considerations)

---

## Last valid SAS ID — DOCUMENTED_SAS_MAX_ID (snapshot)

- **Source:** [SA Sailing Member Finder](https://www.sailing.org.za/member-finder?parentBodyID=28406&firstname=&surname=)
- **DOCUMENTED_SAS_MAX_ID:** **28406** — snapshot as of Feb 2026. **Not a permanent ceiling;** verify periodically on the site. For automation, use **DETECTED_SAS_MAX_ID** from incremental scraper batch logs (see [SAS_SCRAPE_ARCHITECTURE.md](SAS_SCRAPE_ARCHITECTURE.md)).

---

## Scraping Source

### URL Format
```
https://www.sailing.org.za/member-finder?parentBodyID={SA_ID}&firstname=&surname=
```

### Parameters
- **parentBodyID**: The SA Sailing ID number (integer, no commas)
- **firstname**: Leave empty (`""`)
- **surname**: Leave empty (`""`)

### Example
- SA ID 27864 → `https://www.sailing.org.za/member-finder?parentBodyID=27864&firstname=&surname=`

### Important Notes
- **NEVER include commas** in SA IDs (e.g., use `27864` not `27,864`)
- **Rate Limiting**: 0.5 second delay between requests (respectful to server)
- **User Agent**: Must include proper User-Agent header

---

## Data Flow Process

```
SA Sailing Website
    ↓
HTTP GET Request (BeautifulSoup)
    ↓
Parse HTML Response
    ↓
Extract Name & Birth Year
    ↓
Parse Name (following rules)
    ↓
Calculate Age
    ↓
Insert/Update sas_id_personal table
```

---

## Name Parsing Rules

### SA Sailing Website Name Formats

#### Format 1: With Comma
```
"Lastname, Firstname Middle"
Example: "Roberts, Michelle"
```

**Parsing Logic:**
- Split on comma
- `last_name` = part before comma (trimmed)
- `first_name` = first word after comma (ONLY first word, not middle names)
- `full_name` = original text (preserve as-is)

#### Format 2: Without Comma
```
"Firstname Middle Lastname"
Example: "Warwick Noel Bursey"
```

**Parsing Logic:**
- Split on spaces
- `last_name` = last word
- `first_name` = first word (ONLY first word)
- `full_name` = original text (preserve as-is)

### Special Cases
- **Double Commas**: Replace `,,` with `,` (fix data entry mistakes)
- **Single Word**: Use as `first_name`, leave `last_name` empty

### Code Example
```python
def parse_name(name_text):
    """Parse name following SA Sailing rules"""
    if name_text == "No Record Found":
        return 'No Record', 'Found', 'No Record Found'
    
    name_text = name_text.replace(',,', ',')  # Fix double commas
    
    if ',' in name_text:
        # Format: "Lastname, Firstname Middle"
        parts = name_text.split(',')
        last_name = parts[0].strip()
        first_name = parts[1].strip().split()[0]  # ONLY first word
        full_name = name_text
    else:
        # Format: "Firstname Middle Lastname"
        name_parts = name_text.split()
        if len(name_parts) >= 2:
            last_name = name_parts[-1]  # Last word
            first_name = name_parts[0]  # ONLY first word
            full_name = name_text
        else:
            first_name = name_text
            last_name = ''
            full_name = name_text
    
    return first_name, last_name, full_name
```

---

## Database Schema

### Target Table: `public.sas_id_personal`

#### Required Columns for Scraping:
```sql
sa_sailing_id  TEXT/VARCHAR      -- SA Sailing ID (e.g., '27864')
id             INTEGER           -- Same as sa_sailing_id (integer)
first_name     VARCHAR           -- First name only (first word)
last_name      VARCHAR           -- Last name (surname)
full_name      VARCHAR           -- Complete name as scraped
year_of_birth  INTEGER           -- Birth year (YYYY)
age            INTEGER           -- Calculated: current_year - year_of_birth
created_at     TIMESTAMP         -- Auto-set to NOW()
updated_at     TIMESTAMP         -- Auto-set to NOW()
```

#### Insert Statement (Valid Member)
```sql
INSERT INTO public.sas_id_personal (
    sa_sailing_id,
    id,
    first_name,
    last_name,
    full_name,
    year_of_birth,
    age,
    created_at,
    updated_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
```

#### Parameters:
1. `sa_sailing_id`: String of SA ID (e.g., `'27864'`)
2. `id`: Integer of SA ID (e.g., `27864`)
3. `first_name`: Parsed first name
4. `last_name`: Parsed last name
5. `full_name`: Full name as scraped
6. `year_of_birth`: Birth year integer or NULL
7. `age`: Calculated age or NULL

---

## No Record Found Handling

### Rule: Sequential Integrity
**CRITICAL**: No gaps allowed in SA Sailing ID sequence. Every ID must be inserted, even if not found.

### When Member Not Found:
If scraping returns "No Record Found" or no member data:

1. **Insert placeholder record:**
   ```sql
   INSERT INTO public.sas_id_personal (
       sa_sailing_id,
       id,
       first_name,
       last_name,
       full_name,
       created_at,
       updated_at
   )
   VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
   ```

2. **Use these values:**
   - `first_name` = `'No Record'`
   - `last_name` = `'Found'`
   - `full_name` = `'No Record Found'`
   - `year_of_birth` = `NULL`
   - `age` = `NULL`

### Verification
```sql
-- Check sequential integrity
SELECT COUNT(*) FROM sas_id_personal 
WHERE sa_sailing_id ~ '^[0-9]+$';

-- Should equal:
SELECT MAX(sa_sailing_id::integer) FROM sas_id_personal;
```

---

## Step-by-Step Process

### Manual Scraping Process

#### 1. Determine Starting ID
```sql
SELECT MAX(sa_sailing_id::integer) FROM public.sas_id_personal
WHERE sa_sailing_id ~ '^[0-9]+$';
```

#### 2. Scrape IDs Sequentially
- Start from `MAX(sa_sailing_id) + 1`
- Scrape each ID with 0.5 second delay
- Stop after 10 consecutive "No Record Found" responses

#### 3. Parse Each Response

**Valid Member Found:**
- Extract name from `<b>` tags
- Extract birth year from "Born YYYY" text
- Parse name using rules
- Calculate age
- Insert into database

**No Record Found:**
- Insert placeholder: `first_name='No Record'`, `last_name='Found'`

#### 4. Verify Data
```sql
-- Check all inserted records
SELECT sa_sailing_id, first_name, last_name, year_of_birth, age
FROM public.sas_id_personal
WHERE sa_sailing_id::integer BETWEEN {start_id} AND {end_id}
ORDER BY sa_sailing_id::integer;
```

### Example Python Script Structure

```python
import requests
from bs4 import BeautifulSoup
import time
import psycopg2
import re
from datetime import datetime

def scrape_sailor(sa_id):
    """Scrape sailor data from SA Sailing website"""
    url = f"https://www.sailing.org.za/member-finder?parentBodyID={sa_id}&firstname=&surname="
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        page_text = response.text
        
        # Check if valid member
        if "No Record Found" in page_text or "no records found" in page_text.lower():
            return None
        
        # Extract name and birth year
        # ... (parse logic)
        
        return {
            'sa_sailing_id': str(sa_id),
            'first_name': first_name,
            'last_name': last_name,
            'full_name': full_name,
            'year_of_birth': birth_year,
            'age': age
        }
    except Exception as e:
        return {'error': str(e)}

# Main scraping loop
for sa_id in range(start_id, end_id + 1):
    result = scrape_sailor(sa_id)
    
    if result is None:
        # Insert "No Record Found"
        insert_no_record(sa_id)
    else:
        # Insert valid member
        insert_member(result)
    
    time.sleep(0.5)  # Rate limiting
```

---

## Automation Considerations

### For Future Website Publication

#### 1. API Endpoint
Create automated endpoint: `/api/scrape-sa-ids`

**Features:**
- Accepts range of IDs to scrape
- Returns JSON with results
- Handles errors gracefully
- Logs all actions

#### 2. Scheduled Scraping
- Daily cron job to check for new IDs
- Start from `MAX(sa_sailing_id) + 1`
- Stop after 10 consecutive "No Record Found"
- Email notification on completion

#### 3. Rate Limiting
- Always maintain 0.5 second delay
- Respect server resources
- Implement exponential backoff on errors

#### 4. Error Handling
- Network errors: Retry with backoff
- Parsing errors: Log and continue
- Database errors: Rollback and retry

#### 5. Data Validation
- Verify sequential integrity after each batch
- Check for duplicate entries
- Validate name parsing results

#### 6. Monitoring
- Track scraping success rate
- Monitor API response times
- Alert on consecutive failures

---

## Current Implementation

### Admin Script
**File**: `admin/tools/scrape_new_sailors_*.py`

**Features:**
- ✅ Follows all rules correctly
- ✅ Inserts "No Record Found" entries
- ✅ Maintains sequential integrity
- ✅ Handles errors gracefully

### API Endpoint
**File**: `api.py` - `/api/run-daily-scrape`

**Status**: ⚠️ Needs fixing
- ❌ Does NOT insert "No Record Found" entries
- ❌ Breaks sequential integrity rule
- ✅ Handles valid members correctly

**Recommendation**: Update API to match admin script behavior

---

## Best Practices

### 1. Always Check for Existing Records
```python
cur.execute("SELECT sa_sailing_id FROM sas_id_personal WHERE sa_sailing_id = %s", (sa_id,))
if cur.fetchone():
    # Update existing record
else:
    # Insert new record
```

### 2. Handle Comma Separators
- Remove commas from input: `sa_id.replace(',', '')`
- Never parse "27,864" directly - convert to "27864" first

### 3. Preserve Original Data
- Always store `full_name` exactly as scraped
- Store `year_of_birth` as integer (not calculated)
- Calculate `age` from `year_of_birth` at insert time

### 4. Transaction Safety
```python
try:
    cur.execute("INSERT INTO ...")
    conn.commit()
except Exception as e:
    conn.rollback()
    print(f"Error: {e}")
```

### 5. Logging
- Log all insertions
- Log all "No Record Found" entries
- Log errors with full context

---

## Verification Checklist

After each scraping session:

- [ ] All IDs in range are present (no gaps)
- [ ] Sequential integrity: `COUNT(*) = MAX(sa_sailing_id)`
- [ ] "No Record Found" entries have correct placeholder values
- [ ] Valid members have correct name parsing
- [ ] Birth years are integers or NULL
- [ ] Ages are calculated correctly
- [ ] No duplicate entries
- [ ] All data in correct columns

---

## Example Verification Queries

```sql
-- Check sequential integrity
SELECT 
    COUNT(*) as total_records,
    MAX(sa_sailing_id::integer) as max_id,
    COUNT(*) = MAX(sa_sailing_id::integer) as integrity_check
FROM public.sas_id_personal
WHERE sa_sailing_id ~ '^[0-9]+$';

-- Check "No Record Found" entries
SELECT COUNT(*) 
FROM public.sas_id_personal
WHERE first_name = 'No Record' AND last_name = 'Found';

-- Check recent scrapes
SELECT sa_sailing_id, first_name, last_name, year_of_birth, age
FROM public.sas_id_personal
WHERE sa_sailing_id::integer BETWEEN 27870 AND 27906
ORDER BY sa_sailing_id::integer;
```

---

## Troubleshooting

### Issue: "No Record Found" not inserted
**Solution**: Ensure scraping logic inserts placeholder when `result is None`

### Issue: Sequential integrity broken
**Solution**: Check for missing IDs and insert "No Record Found" entries

### Issue: Name parsing incorrect
**Solution**: Verify parsing logic handles both comma and non-comma formats

### Issue: Age calculation wrong
**Solution**: Ensure using current year: `datetime.now().year - birth_year`

### Issue: Comma in SA ID causing errors
**Solution**: Remove commas before parsing: `sa_id.replace(',', '')`

---

## Related Files

- `admin/tools/scrape_new_sailors_27835_27873.py` - Working implementation
- `api.py` - API endpoint (needs fixing)
- `docs/README_sailing_id_table.md` - Table structure rules
- `docs/README_sas_id_personal.md` - Complete table documentation

---

## Last Updated
November 5, 2025

## Last Scraped Range
27870-27906 (37 entries: 33 valid, 4 No Record Found)



## Overview
This document describes the complete process for scraping SA Sailing IDs from the official website and inserting them into the `sas_id_personal` table.

---

## Table of Contents
1. [Scraping Source](#scraping-source)
2. [Data Flow Process](#data-flow-process)
3. [Name Parsing Rules](#name-parsing-rules)
4. [Database Schema](#database-schema)
5. [No Record Found Handling](#no-record-found-handling)
6. [Step-by-Step Process](#step-by-step-process)
7. [Automation Considerations](#automation-considerations)

---

## Last valid SAS ID — DOCUMENTED_SAS_MAX_ID (snapshot)

- **Source:** [SA Sailing Member Finder](https://www.sailing.org.za/member-finder?parentBodyID=28406&firstname=&surname=)
- **DOCUMENTED_SAS_MAX_ID:** **28406** — snapshot as of Feb 2026. **Not a permanent ceiling;** verify periodically on the site. For automation, use **DETECTED_SAS_MAX_ID** from incremental scraper batch logs (see [SAS_SCRAPE_ARCHITECTURE.md](SAS_SCRAPE_ARCHITECTURE.md)).

---

## Scraping Source

### URL Format
```
https://www.sailing.org.za/member-finder?parentBodyID={SA_ID}&firstname=&surname=
```

### Parameters
- **parentBodyID**: The SA Sailing ID number (integer, no commas)
- **firstname**: Leave empty (`""`)
- **surname**: Leave empty (`""`)

### Example
- SA ID 27864 → `https://www.sailing.org.za/member-finder?parentBodyID=27864&firstname=&surname=`

### Important Notes
- **NEVER include commas** in SA IDs (e.g., use `27864` not `27,864`)
- **Rate Limiting**: 0.5 second delay between requests (respectful to server)
- **User Agent**: Must include proper User-Agent header

---

## Data Flow Process

```
SA Sailing Website
    ↓
HTTP GET Request (BeautifulSoup)
    ↓
Parse HTML Response
    ↓
Extract Name & Birth Year
    ↓
Parse Name (following rules)
    ↓
Calculate Age
    ↓
Insert/Update sas_id_personal table
```

---

## Name Parsing Rules

### SA Sailing Website Name Formats

#### Format 1: With Comma
```
"Lastname, Firstname Middle"
Example: "Roberts, Michelle"
```

**Parsing Logic:**
- Split on comma
- `last_name` = part before comma (trimmed)
- `first_name` = first word after comma (ONLY first word, not middle names)
- `full_name` = original text (preserve as-is)

#### Format 2: Without Comma
```
"Firstname Middle Lastname"
Example: "Warwick Noel Bursey"
```

**Parsing Logic:**
- Split on spaces
- `last_name` = last word
- `first_name` = first word (ONLY first word)
- `full_name` = original text (preserve as-is)

### Special Cases
- **Double Commas**: Replace `,,` with `,` (fix data entry mistakes)
- **Single Word**: Use as `first_name`, leave `last_name` empty

### Code Example
```python
def parse_name(name_text):
    """Parse name following SA Sailing rules"""
    if name_text == "No Record Found":
        return 'No Record', 'Found', 'No Record Found'
    
    name_text = name_text.replace(',,', ',')  # Fix double commas
    
    if ',' in name_text:
        # Format: "Lastname, Firstname Middle"
        parts = name_text.split(',')
        last_name = parts[0].strip()
        first_name = parts[1].strip().split()[0]  # ONLY first word
        full_name = name_text
    else:
        # Format: "Firstname Middle Lastname"
        name_parts = name_text.split()
        if len(name_parts) >= 2:
            last_name = name_parts[-1]  # Last word
            first_name = name_parts[0]  # ONLY first word
            full_name = name_text
        else:
            first_name = name_text
            last_name = ''
            full_name = name_text
    
    return first_name, last_name, full_name
```

---

## Database Schema

### Target Table: `public.sas_id_personal`

#### Required Columns for Scraping:
```sql
sa_sailing_id  TEXT/VARCHAR      -- SA Sailing ID (e.g., '27864')
id             INTEGER           -- Same as sa_sailing_id (integer)
first_name     VARCHAR           -- First name only (first word)
last_name      VARCHAR           -- Last name (surname)
full_name      VARCHAR           -- Complete name as scraped
year_of_birth  INTEGER           -- Birth year (YYYY)
age            INTEGER           -- Calculated: current_year - year_of_birth
created_at     TIMESTAMP         -- Auto-set to NOW()
updated_at     TIMESTAMP         -- Auto-set to NOW()
```

#### Insert Statement (Valid Member)
```sql
INSERT INTO public.sas_id_personal (
    sa_sailing_id,
    id,
    first_name,
    last_name,
    full_name,
    year_of_birth,
    age,
    created_at,
    updated_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
```

#### Parameters:
1. `sa_sailing_id`: String of SA ID (e.g., `'27864'`)
2. `id`: Integer of SA ID (e.g., `27864`)
3. `first_name`: Parsed first name
4. `last_name`: Parsed last name
5. `full_name`: Full name as scraped
6. `year_of_birth`: Birth year integer or NULL
7. `age`: Calculated age or NULL

---

## No Record Found Handling

### Rule: Sequential Integrity
**CRITICAL**: No gaps allowed in SA Sailing ID sequence. Every ID must be inserted, even if not found.

### When Member Not Found:
If scraping returns "No Record Found" or no member data:

1. **Insert placeholder record:**
   ```sql
   INSERT INTO public.sas_id_personal (
       sa_sailing_id,
       id,
       first_name,
       last_name,
       full_name,
       created_at,
       updated_at
   )
   VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
   ```

2. **Use these values:**
   - `first_name` = `'No Record'`
   - `last_name` = `'Found'`
   - `full_name` = `'No Record Found'`
   - `year_of_birth` = `NULL`
   - `age` = `NULL`

### Verification
```sql
-- Check sequential integrity
SELECT COUNT(*) FROM sas_id_personal 
WHERE sa_sailing_id ~ '^[0-9]+$';

-- Should equal:
SELECT MAX(sa_sailing_id::integer) FROM sas_id_personal;
```

---

## Step-by-Step Process

### Manual Scraping Process

#### 1. Determine Starting ID
```sql
SELECT MAX(sa_sailing_id::integer) FROM public.sas_id_personal
WHERE sa_sailing_id ~ '^[0-9]+$';
```

#### 2. Scrape IDs Sequentially
- Start from `MAX(sa_sailing_id) + 1`
- Scrape each ID with 0.5 second delay
- Stop after 10 consecutive "No Record Found" responses

#### 3. Parse Each Response

**Valid Member Found:**
- Extract name from `<b>` tags
- Extract birth year from "Born YYYY" text
- Parse name using rules
- Calculate age
- Insert into database

**No Record Found:**
- Insert placeholder: `first_name='No Record'`, `last_name='Found'`

#### 4. Verify Data
```sql
-- Check all inserted records
SELECT sa_sailing_id, first_name, last_name, year_of_birth, age
FROM public.sas_id_personal
WHERE sa_sailing_id::integer BETWEEN {start_id} AND {end_id}
ORDER BY sa_sailing_id::integer;
```

### Example Python Script Structure

```python
import requests
from bs4 import BeautifulSoup
import time
import psycopg2
import re
from datetime import datetime

def scrape_sailor(sa_id):
    """Scrape sailor data from SA Sailing website"""
    url = f"https://www.sailing.org.za/member-finder?parentBodyID={sa_id}&firstname=&surname="
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        page_text = response.text
        
        # Check if valid member
        if "No Record Found" in page_text or "no records found" in page_text.lower():
            return None
        
        # Extract name and birth year
        # ... (parse logic)
        
        return {
            'sa_sailing_id': str(sa_id),
            'first_name': first_name,
            'last_name': last_name,
            'full_name': full_name,
            'year_of_birth': birth_year,
            'age': age
        }
    except Exception as e:
        return {'error': str(e)}

# Main scraping loop
for sa_id in range(start_id, end_id + 1):
    result = scrape_sailor(sa_id)
    
    if result is None:
        # Insert "No Record Found"
        insert_no_record(sa_id)
    else:
        # Insert valid member
        insert_member(result)
    
    time.sleep(0.5)  # Rate limiting
```

---

## Automation Considerations

### For Future Website Publication

#### 1. API Endpoint
Create automated endpoint: `/api/scrape-sa-ids`

**Features:**
- Accepts range of IDs to scrape
- Returns JSON with results
- Handles errors gracefully
- Logs all actions

#### 2. Scheduled Scraping
- Daily cron job to check for new IDs
- Start from `MAX(sa_sailing_id) + 1`
- Stop after 10 consecutive "No Record Found"
- Email notification on completion

#### 3. Rate Limiting
- Always maintain 0.5 second delay
- Respect server resources
- Implement exponential backoff on errors

#### 4. Error Handling
- Network errors: Retry with backoff
- Parsing errors: Log and continue
- Database errors: Rollback and retry

#### 5. Data Validation
- Verify sequential integrity after each batch
- Check for duplicate entries
- Validate name parsing results

#### 6. Monitoring
- Track scraping success rate
- Monitor API response times
- Alert on consecutive failures

---

## Current Implementation

### Admin Script
**File**: `admin/tools/scrape_new_sailors_*.py`

**Features:**
- ✅ Follows all rules correctly
- ✅ Inserts "No Record Found" entries
- ✅ Maintains sequential integrity
- ✅ Handles errors gracefully

### API Endpoint
**File**: `api.py` - `/api/run-daily-scrape`

**Status**: ⚠️ Needs fixing
- ❌ Does NOT insert "No Record Found" entries
- ❌ Breaks sequential integrity rule
- ✅ Handles valid members correctly

**Recommendation**: Update API to match admin script behavior

---

## Best Practices

### 1. Always Check for Existing Records
```python
cur.execute("SELECT sa_sailing_id FROM sas_id_personal WHERE sa_sailing_id = %s", (sa_id,))
if cur.fetchone():
    # Update existing record
else:
    # Insert new record
```

### 2. Handle Comma Separators
- Remove commas from input: `sa_id.replace(',', '')`
- Never parse "27,864" directly - convert to "27864" first

### 3. Preserve Original Data
- Always store `full_name` exactly as scraped
- Store `year_of_birth` as integer (not calculated)
- Calculate `age` from `year_of_birth` at insert time

### 4. Transaction Safety
```python
try:
    cur.execute("INSERT INTO ...")
    conn.commit()
except Exception as e:
    conn.rollback()
    print(f"Error: {e}")
```

### 5. Logging
- Log all insertions
- Log all "No Record Found" entries
- Log errors with full context

---

## Verification Checklist

After each scraping session:

- [ ] All IDs in range are present (no gaps)
- [ ] Sequential integrity: `COUNT(*) = MAX(sa_sailing_id)`
- [ ] "No Record Found" entries have correct placeholder values
- [ ] Valid members have correct name parsing
- [ ] Birth years are integers or NULL
- [ ] Ages are calculated correctly
- [ ] No duplicate entries
- [ ] All data in correct columns

---

## Example Verification Queries

```sql
-- Check sequential integrity
SELECT 
    COUNT(*) as total_records,
    MAX(sa_sailing_id::integer) as max_id,
    COUNT(*) = MAX(sa_sailing_id::integer) as integrity_check
FROM public.sas_id_personal
WHERE sa_sailing_id ~ '^[0-9]+$';

-- Check "No Record Found" entries
SELECT COUNT(*) 
FROM public.sas_id_personal
WHERE first_name = 'No Record' AND last_name = 'Found';

-- Check recent scrapes
SELECT sa_sailing_id, first_name, last_name, year_of_birth, age
FROM public.sas_id_personal
WHERE sa_sailing_id::integer BETWEEN 27870 AND 27906
ORDER BY sa_sailing_id::integer;
```

---

## Troubleshooting

### Issue: "No Record Found" not inserted
**Solution**: Ensure scraping logic inserts placeholder when `result is None`

### Issue: Sequential integrity broken
**Solution**: Check for missing IDs and insert "No Record Found" entries

### Issue: Name parsing incorrect
**Solution**: Verify parsing logic handles both comma and non-comma formats

### Issue: Age calculation wrong
**Solution**: Ensure using current year: `datetime.now().year - birth_year`

### Issue: Comma in SA ID causing errors
**Solution**: Remove commas before parsing: `sa_id.replace(',', '')`

---

## Related Files

- `admin/tools/scrape_new_sailors_27835_27873.py` - Working implementation
- `api.py` - API endpoint (needs fixing)
- `docs/README_sailing_id_table.md` - Table structure rules
- `docs/README_sas_id_personal.md` - Complete table documentation

---

## Last Updated
November 5, 2025

## Last Scraped Range
27870-27906 (37 entries: 33 valid, 4 No Record Found)


















