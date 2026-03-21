# Scraping Data Rules (CRITICAL)

## Core Principle: ONLY Insert Real Data

**RULE**: When scraping data from SA Sailing website, **ONLY insert data that actually exists on the website**. Never assume or make up data.

## What Can Be Scraped

### ✅ ALLOWED - Data Available on Website
- **Name**: Full name, first name, last name (from `<b>` tags)
- **Birth Year**: From "Born YYYY" text on page
- **Age**: Calculated from birth year (real calculation, not assumption)
- **SA Sailing ID**: The ID being scraped

### ❌ FORBIDDEN - Must NOT Be Added Without Real Data

**NEVER add these fields unless they exist on the website:**

1. **Role/Position** (helm, crew)
   - **RULE**: A sailor is only a "helm" if `results` table shows them as helm
   - **RULE**: A sailor is only "crew" if `results` table shows them as crew
   - **NEVER assume** a sailor's role from scraped website data
   - Website does NOT show role/position information

2. **Class Information** (`primary_class`)
   - **RULE**: Only populate from `results.class_canonical` after sailor has actual results
   - **NEVER assume** class from website data
   - Website may not show current class or may show outdated info

3. **Club Information** (`club_1`, `club_2`, `primary_club`, etc.)
   - **RULE**: Only populate from `results.club_raw` or `results.club_id` after sailor has actual results
   - **NEVER assume** club from website data
   - Website may not show current club or may show outdated info

## Scraping Process

1. **Scrape ONLY**:
   - SA Sailing ID
   - Name (first, last, full)
   - Birth year (if visible)
   - Age (calculated from birth year)

2. **Insert ONLY scraped data** into `sas_id_personal`

3. **Leave NULL**:
   - `primary_class`
   - `club_1`, `club_2`, etc.
   - `primary_club`
   - Any role/position fields

4. **Update role/class/club later** from `results` table after sailor has actual regatta results

## Example: What NOT To Do

```python
# ❌ WRONG - Assuming class from website
sailor_data['primary_class'] = extract_class_from_website()  # NO!

# ❌ WRONG - Assuming club from website  
sailor_data['club_1'] = extract_club_from_website()  # NO!

# ❌ WRONG - Assuming helm role
sailor_data['is_helm'] = True  # NO!
```

## Example: What TO Do

```python
# ✅ CORRECT - Only scrape real data
sailor_data = {
    'sa_sailing_id': str(sa_id),
    'first_name': first_name,      # From website
    'last_name': last_name,        # From website
    'full_name': full_name,        # From website
    'year_of_birth': birth_year,   # From website (if exists)
    'age': calculated_age          # Calculated from birth_year
}
# primary_class, club_1, etc. remain NULL - will be populated from results later
```

## Why This Rule Exists

1. **Data Integrity**: Website data may be outdated or incomplete
2. **Authoritative Source**: `results` table is the only source of truth for:
   - What class a sailor actually sails
   - What club they actually race for
   - Whether they helm or crew
3. **No Assumptions**: Making up data corrupts the database
4. **Real Results Only**: Only populate role/class/club when sailor has actual results in `results` table

## Verification

After scraping, verify:
- ✅ Only name and birth year/age were inserted
- ✅ `primary_class` is NULL
- ✅ `club_1`, `club_2`, etc. are NULL
- ✅ No role/position data was added

## Related Scripts

- `admin/tools/scrape_new_sailors_27835_27873.py` - Scrapes new sailors (follows these rules)
- `admin/tools/scrape_birth_years_for_missing.py` - Only updates birth year/age (follows these rules)

## Last valid SAS ID — DOCUMENTED_SAS_MAX_ID (snapshot)

- **Source:** [SA Sailing Member Finder](https://www.sailing.org.za/member-finder?parentBodyID=28406&firstname=&surname=)
- **DOCUMENTED_SAS_MAX_ID:** **28406** — snapshot as of Feb 2026. **Not a permanent ceiling;** verify on the site when doing maintenance. For automation use **DETECTED_SAS_MAX_ID** from incremental scraper (see [SAS_SCRAPE_ARCHITECTURE.md](SAS_SCRAPE_ARCHITECTURE.md)).

## Corrected architecture (SAS scrape)

**Full specification:** [SAS_SCRAPE_ARCHITECTURE.md](SAS_SCRAPE_ARCHITECTURE.md)

- **DOCUMENTED_SAS_MAX_ID** vs **DETECTED_SAS_MAX_ID**: manual snapshot vs auto-probed upper bound (batch logs).
- **Registry expansion:** Only to `sas_id_registry`; no auto-merge into sailors table, no identity resolution, no qualification scrape.
- **Incremental scrape:** Start at `MAX(sas_id)+1`, stop after N consecutive NOT_FOUND (e.g. N=20), record detected upper bound, log batch.
- **Never write scraped results directly into race_results;** all pipelines must use staging tables.
- **Batch logging:** Every run must record batch_id, start_id, end_id, detected_upper_bound, valid_count, not_found_count, error_count, started_at, completed_at (`sas_scrape_batches`).

## Core Principle: ONLY Insert Real Data

**RULE**: When scraping data from SA Sailing website, **ONLY insert data that actually exists on the website**. Never assume or make up data.

## What Can Be Scraped

### ✅ ALLOWED - Data Available on Website
- **Name**: Full name, first name, last name (from `<b>` tags)
- **Birth Year**: From "Born YYYY" text on page
- **Age**: Calculated from birth year (real calculation, not assumption)
- **SA Sailing ID**: The ID being scraped

### ❌ FORBIDDEN - Must NOT Be Added Without Real Data

**NEVER add these fields unless they exist on the website:**

1. **Role/Position** (helm, crew)
   - **RULE**: A sailor is only a "helm" if `results` table shows them as helm
   - **RULE**: A sailor is only "crew" if `results` table shows them as crew
   - **NEVER assume** a sailor's role from scraped website data
   - Website does NOT show role/position information

2. **Class Information** (`primary_class`)
   - **RULE**: Only populate from `results.class_canonical` after sailor has actual results
   - **NEVER assume** class from website data
   - Website may not show current class or may show outdated info

3. **Club Information** (`club_1`, `club_2`, `primary_club`, etc.)
   - **RULE**: Only populate from `results.club_raw` or `results.club_id` after sailor has actual results
   - **NEVER assume** club from website data
   - Website may not show current club or may show outdated info

## Scraping Process

1. **Scrape ONLY**:
   - SA Sailing ID
   - Name (first, last, full)
   - Birth year (if visible)
   - Age (calculated from birth year)

2. **Insert ONLY scraped data** into `sas_id_personal`

3. **Leave NULL**:
   - `primary_class`
   - `club_1`, `club_2`, etc.
   - `primary_club`
   - Any role/position fields

4. **Update role/class/club later** from `results` table after sailor has actual regatta results

## Example: What NOT To Do

```python
# ❌ WRONG - Assuming class from website
sailor_data['primary_class'] = extract_class_from_website()  # NO!

# ❌ WRONG - Assuming club from website  
sailor_data['club_1'] = extract_club_from_website()  # NO!

# ❌ WRONG - Assuming helm role
sailor_data['is_helm'] = True  # NO!
```

## Example: What TO Do

```python
# ✅ CORRECT - Only scrape real data
sailor_data = {
    'sa_sailing_id': str(sa_id),
    'first_name': first_name,      # From website
    'last_name': last_name,        # From website
    'full_name': full_name,        # From website
    'year_of_birth': birth_year,   # From website (if exists)
    'age': calculated_age          # Calculated from birth_year
}
# primary_class, club_1, etc. remain NULL - will be populated from results later
```

## Why This Rule Exists

1. **Data Integrity**: Website data may be outdated or incomplete
2. **Authoritative Source**: `results` table is the only source of truth for:
   - What class a sailor actually sails
   - What club they actually race for
   - Whether they helm or crew
3. **No Assumptions**: Making up data corrupts the database
4. **Real Results Only**: Only populate role/class/club when sailor has actual results in `results` table

## Verification

After scraping, verify:
- ✅ Only name and birth year/age were inserted
- ✅ `primary_class` is NULL
- ✅ `club_1`, `club_2`, etc. are NULL
- ✅ No role/position data was added

## Related Scripts

- `admin/tools/scrape_new_sailors_27835_27873.py` - Scrapes new sailors (follows these rules)
- `admin/tools/scrape_birth_years_for_missing.py` - Only updates birth year/age (follows these rules)


















