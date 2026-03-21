# SAILING_ID Table - GPT Rules & Data Structure

## Purpose
Stores official SA Sailing IDs and sailor information for proper identification.

## Corrected architecture (SAS scrape)

**Full specification:** [SAS_SCRAPE_ARCHITECTURE.md](SAS_SCRAPE_ARCHITECTURE.md)

- **DOCUMENTED_SAS_MAX_ID** — Manual snapshot (e.g. 28406 as of Feb 2026); not a permanent ceiling. **DETECTED_SAS_MAX_ID** — from incremental scraper batch logs (`sas_scrape_batches.detected_upper_bound`).
- **Registry expansion:** Writes only to `sas_id_registry`; no auto-merge into sailors table, no identity resolution, no qualification scrape.
- **Incremental scrape:** Start at `MAX(sas_id)+1`, stop after N consecutive NOT_FOUND (e.g. N=20), record detected upper bound, log in `sas_scrape_batches`.
- **Never write scraped results directly into race_results;** use staging tables. **Batch logging:** Every run records batch_id, start_id, end_id, detected_upper_bound, valid_count, not_found_count, error_count, started_at, completed_at.

## Table Structure
```sql
CREATE TABLE sailing_id (
    sa_sailing_id TEXT PRIMARY KEY,         -- Official SA Sailing ID (e.g., '12345')
    full_name TEXT NOT NULL,                -- Full name as registered
    first_name TEXT,                        -- First name
    last_name TEXT,                         -- Last name
    date_of_birth DATE,                     -- Date of birth
    province TEXT,                          -- Province abbreviation (KZN, WC, GP, etc.)
    club_id INTEGER REFERENCES clubs(club_id), -- Primary club affiliation
    status TEXT DEFAULT 'active',           -- active, inactive, suspended
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Data Rules (from GPT instructions)

### SA Sailing ID Scraping Rules (CRITICAL)
1. **SEQUENTIAL INTEGRITY**: Row count MUST ALWAYS equal MAX(sa_sailing_id)
   - No gaps allowed in sa_sailing_id sequence
   - If ID not found on SA Sailing website, insert as `first_name='No Record'`, `last_name='Found'`
   - Database checksum: `SELECT COUNT(*) FROM sailing_id` MUST equal `SELECT MAX(sa_sailing_id) FROM sailing_id`
2. **SOURCE DATA TRUST**: Store EXACTLY what SA Sailing website returns
   - Valid member: Parse name from `<b>Lastname, Firstname</b>` format
   - No record found: Store as `first_name='No Record'`, `last_name='Found'`
   - NEVER store NULL for scraped IDs
3. **SCRAPING PROCESS** (see also [SAS_SCRAPE_ARCHITECTURE.md](SAS_SCRAPE_ARCHITECTURE.md) — Incremental Scrape Strategy):
   - Start from `MAX(sa_sailing_id) + 1` (or `MAX(sas_id)` from `sas_id_registry` for registry-only pipeline)
   - Stop after N consecutive "No Record Found" (suggest N=20; record `detected_upper_bound` in `sas_scrape_batches`)
   - **DOCUMENTED_SAS_MAX_ID** (snapshot): [member finder](https://www.sailing.org.za/member-finder?parentBodyID=28406&firstname=&surname=) **28406** as of Feb 2026 — not a permanent ceiling; verify periodically. For automation use **DETECTED_SAS_MAX_ID** from batch logs.
   - Delay 0.5 seconds between requests (respectful to SA Sailing server)
   - URL format: `https://www.sailing.org.za/member-finder?parentBodyID={ID}&firstname=&surname=`
   - **Never write scraped results directly into race_results;** use staging tables. Log every run in `sas_scrape_batches`.

### SA Sailing ID Lookup Rules (CRITICAL)
1. **ALWAYS search database first** before adding any sailor
2. **Use exact database names** - if OCR differs, update to match database
3. **Search format**: `WHERE full_name ILIKE '%FirstName%' AND full_name ILIKE '%LastName%'`
4. **If not found**: Set `helm_sa_sailing_id = NULL` or `crew_sa_sailing_id = NULL` in results
5. **NEVER invent SA Sailing IDs**
6. **FILTER "No Record Found"**: Ignore entries where `first_name='No Record'` in search results

### Name Matching Rules
- **Primary search**: Use `full_name` field
- **Partial matching**: Use `ILIKE '%FirstName%' AND ILIKE '%LastName%'`
- **Exact matches preferred** over fuzzy matching
- **Update OCR data** to match database names if found

### Province Abbreviations (CRITICAL)
- **ONLY use these codes**: KZN, WC, GP, EC, FS, NC, MP, LP, NW
- **NEVER invent provinces** - use NULL if unknown

### Data Integrity Rules
1. **NEVER use placeholders** - only real data or NULL
2. **NEVER hardcode values** - always extract from source
3. **ALWAYS verify in database** before creating new records
4. **ALWAYS preserve official SA Sailing IDs** exactly
5. **ALWAYS use exact database names**

## Example Data
```sql
INSERT INTO sailing_id (sa_sailing_id, full_name, first_name, last_name, province, club_id) VALUES
('12345', 'Hayden Miller', 'Hayden', 'Miller', 'KZN', 2),
('67890', 'Megan Miller', 'Megan', 'Miller', 'KZN', 2),
('11111', 'Timothy Weaving', 'Timothy', 'Weaving', 'KZN', 1);
```

## Related Tables
- `results.helm_sa_sailing_id` - Links to helm sailor
- `results.crew_sa_sailing_id` - Links to crew sailor  
- `temp_people` - Temporary records for unidentified sailors
- `clubs` - Club affiliations

## Temporary People Handling
- **temp_people table**: Stores unidentified sailors temporarily
- **promote_temp_to_official function**: Links temp IDs to official SAS IDs
- **Auto-upgrade process**: Updates associated results when sailor is identified

## Name Parsing Rules (CRITICAL)
### SA Sailing Website Name Formats:
1. **With Comma**: `"Lastname, Firstname Middle"` (e.g., "Malan, Maximilian Philip")
   - Parse: `last_name = "Malan"`, `first_name = "Maximilian Philip"`
2. **Without Comma**: `"Firstname Middle Lastname"` (e.g., "Sean Hamilton McDiarmid")
   - Parse: Split on **last space**
   - `last_name = "McDiarmid"` (last word)
   - `first_name = "Sean Hamilton"` (all words except last)
   - `display_name = "Sean Hamilton McDiarmid"` (preserve full name)

### Database Columns:
- `first_name`: Given name(s) + middle name(s)
- `last_name`: Surname only
- `display_name`: Full name as shown on SA Sailing website
- **NEVER lose middle names** - store in `first_name` or `display_name`

### Scraper Logic:
```python
# Fix double commas (data entry mistakes on SA Sailing website)
name_text = name_text.replace(',,', ',')  # Treat double comma as single

if ',' in name_text:
    # Format: "Lastname, Firstname Middle"
    parts = name_text.split(',')
    last_name = parts[0].strip()
    first_name = parts[1].strip()
else:
    # Format: "Firstname Middle Lastname" 
    name_parts = name_text.split()
    if len(name_parts) >= 2:
        last_name = name_parts[-1]  # Last word
        first_name = ' '.join(name_parts[:-1])  # All except last
    else:
        first_name = name_text
        last_name = ''
display_name = name_text  # Preserve original full name
```
