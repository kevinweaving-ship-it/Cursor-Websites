# Role Determination Rules (CRITICAL)

## Core Principle: Role Based ONLY on Actual Results Data

**RULE**: A sailor's role (Helm/Crew) must ONLY be determined from actual regatta results data in the `results` table. No assumptions or defaults.

## Role Determination Logic

### Role Priority (in order):
1. **Helm**: If sailor appears in `results.helm_sa_sailing_id` → Role = `'Helm'`
2. **Crew**: If sailor appears in `results.crew_sa_sailing_id`, `crew2_sa_sailing_id`, or `crew3_sa_sailing_id` → Role = `'Crew'`
3. **NULL**: If sailor has NO results → Role = `NULL` (not shown)

### SQL Logic (applied in `/api/search`):

```sql
CASE 
    WHEN EXISTS(SELECT 1 FROM public.results res 
                WHERE res.helm_sa_sailing_id::text = TRIM(LEADING '0' FROM s.sa_sailing_id::text)) 
        THEN 'Helm'
    WHEN EXISTS(SELECT 1 FROM public.results res 
                WHERE res.crew_sa_sailing_id::text = TRIM(LEADING '0' FROM s.sa_sailing_id::text)) 
        THEN 'Crew'
    WHEN EXISTS(SELECT 1 FROM public.results res 
                WHERE res.crew2_sa_sailing_id::text = TRIM(LEADING '0' FROM s.sa_sailing_id::text)) 
        THEN 'Crew'
    WHEN EXISTS(SELECT 1 FROM public.results res 
                WHERE res.crew3_sa_sailing_id::text = TRIM(LEADING '0' FROM s.sa_sailing_id::text)) 
        THEN 'Crew'
    ELSE NULL
END as role
```

## Display Format

- **Helm**: Capitalized as `'Helm'`
- **Crew**: Capitalized as `'Crew'` (applies to crew, crew2, crew3)
- **No Results**: `NULL` (empty/blank in display)

## Rules

1. **No Default**: NEVER default to 'Helm' or 'Crew' if sailor has no results
2. **Actual Data Only**: Role is ONLY determined by existence in `results` table
3. **Helm Priority**: If sailor has sailed as both Helm and Crew, show as 'Helm' (helm takes priority)
4. **Capitalization**: Always use capital H/C ('Helm', 'Crew', not 'helm', 'crew')

## Examples

### Sailor with Helm Results Only
- Has entries in `results.helm_sa_sailing_id`
- **Role**: `'Helm'`

### Sailor with Crew Results Only
- Has entries in `results.crew_sa_sailing_id` (or crew2/crew3)
- **No helm results**
- **Role**: `'Crew'`

### Sailor with Both Helm and Crew Results
- Has entries in both `helm_sa_sailing_id` AND `crew_sa_sailing_id`
- **Role**: `'Helm'` (helm takes priority)

### Sailor with No Results
- No entries in `results` table at all
- **Role**: `NULL` (no role shown)

### Newly Scraped Sailor (No Results Yet)
- Just added to `sas_id_personal` via scraping
- No regatta results yet
- **Role**: `NULL` (will show 'Helm' or 'Crew' once they sail in a regatta)

## Implementation

This logic is implemented in:
- `/api/search` endpoint (member finder search)
- `/api/member/{sas_id}/results` endpoint (member profile)
- `/api/member/{temp_id}/results` endpoint (temp ID profile)

All endpoints use the same CASE statement logic to ensure consistency.



## Core Principle: Role Based ONLY on Actual Results Data

**RULE**: A sailor's role (Helm/Crew) must ONLY be determined from actual regatta results data in the `results` table. No assumptions or defaults.

## Role Determination Logic

### Role Priority (in order):
1. **Helm**: If sailor appears in `results.helm_sa_sailing_id` → Role = `'Helm'`
2. **Crew**: If sailor appears in `results.crew_sa_sailing_id`, `crew2_sa_sailing_id`, or `crew3_sa_sailing_id` → Role = `'Crew'`
3. **NULL**: If sailor has NO results → Role = `NULL` (not shown)

### SQL Logic (applied in `/api/search`):

```sql
CASE 
    WHEN EXISTS(SELECT 1 FROM public.results res 
                WHERE res.helm_sa_sailing_id::text = TRIM(LEADING '0' FROM s.sa_sailing_id::text)) 
        THEN 'Helm'
    WHEN EXISTS(SELECT 1 FROM public.results res 
                WHERE res.crew_sa_sailing_id::text = TRIM(LEADING '0' FROM s.sa_sailing_id::text)) 
        THEN 'Crew'
    WHEN EXISTS(SELECT 1 FROM public.results res 
                WHERE res.crew2_sa_sailing_id::text = TRIM(LEADING '0' FROM s.sa_sailing_id::text)) 
        THEN 'Crew'
    WHEN EXISTS(SELECT 1 FROM public.results res 
                WHERE res.crew3_sa_sailing_id::text = TRIM(LEADING '0' FROM s.sa_sailing_id::text)) 
        THEN 'Crew'
    ELSE NULL
END as role
```

## Display Format

- **Helm**: Capitalized as `'Helm'`
- **Crew**: Capitalized as `'Crew'` (applies to crew, crew2, crew3)
- **No Results**: `NULL` (empty/blank in display)

## Rules

1. **No Default**: NEVER default to 'Helm' or 'Crew' if sailor has no results
2. **Actual Data Only**: Role is ONLY determined by existence in `results` table
3. **Helm Priority**: If sailor has sailed as both Helm and Crew, show as 'Helm' (helm takes priority)
4. **Capitalization**: Always use capital H/C ('Helm', 'Crew', not 'helm', 'crew')

## Examples

### Sailor with Helm Results Only
- Has entries in `results.helm_sa_sailing_id`
- **Role**: `'Helm'`

### Sailor with Crew Results Only
- Has entries in `results.crew_sa_sailing_id` (or crew2/crew3)
- **No helm results**
- **Role**: `'Crew'`

### Sailor with Both Helm and Crew Results
- Has entries in both `helm_sa_sailing_id` AND `crew_sa_sailing_id`
- **Role**: `'Helm'` (helm takes priority)

### Sailor with No Results
- No entries in `results` table at all
- **Role**: `NULL` (no role shown)

### Newly Scraped Sailor (No Results Yet)
- Just added to `sas_id_personal` via scraping
- No regatta results yet
- **Role**: `NULL` (will show 'Helm' or 'Crew' once they sail in a regatta)

## Implementation

This logic is implemented in:
- `/api/search` endpoint (member finder search)
- `/api/member/{sas_id}/results` endpoint (member profile)
- `/api/member/{temp_id}/results` endpoint (temp ID profile)

All endpoints use the same CASE statement logic to ensure consistency.


















