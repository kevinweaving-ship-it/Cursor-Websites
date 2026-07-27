# SA Sailing Regatta Database Tables

## Overview
This document describes the database schema and data flow for the SA Sailing regatta results system.

## Core Tables

### 1. `regattas` - Main Regatta Events
**Purpose**: Stores header information for each regatta event
**Key Fields**:
- `regatta_id` (PK): Unique identifier (e.g., "359-2025-2025-zvyc-southern-charter-cape-classic")
- `event_name`: Full regatta name
- `year`: Year of the regatta
- `host_club_code`: Club abbreviation (e.g., "ZVYC")
- `result_status`: "P" (Provisional) or "F" (Final)
- `as_at_time`: Timestamp of results

### 2. `regatta_blocks` - Fleet Information
**Purpose**: Stores fleet-level data for each regatta
**Key Fields**:
- `block_id` (PK): Unique identifier (e.g., "359-2025-2025-zvyc-southern-charter-cape-classic:420-fleet")
- `regatta_id` (FK): Links to regattas table
- `fleet_label`: Fleet name (e.g., "420", "OPEN", "Optimist A")
- `class_canonical`: Standardized class name (e.g., "420", "Optimist")
- `class_original`: Original class name from results sheet
- `races_sailed`: Number of races completed
- `discard_count`: Number of races to discard
- `handicap_system`: Scoring system (usually "Appendix A")

**Checksum Rules**:
- `to_count = races_sailed - discard_count`
- `entries_count = COUNT(*) FROM results WHERE block_id = block_id`

### 3. `results` - Individual Sailor Results
**Purpose**: Stores individual sailor/boat results for each fleet
**Key Fields**:
- `result_id` (PK): Auto-incrementing ID
- `block_id` (FK): Links to regatta_blocks
- `rank`: Final position in fleet
- `helm_name`: Helmsman's full name
- `crew_name`: Crew member's name (if applicable)
- `sail_number`: Boat's sail number
- `club_raw`: Club abbreviation from results sheet
- `helm_sa_sailing_id`: Official SA Sailing ID (if matched)
- `helm_temp_id`: Temporary ID (if no SAS ID match)
- `race_scores`: JSONB containing R1, R2, R3... scores
- `total_points_raw`: Sum of all race scores (including discards)
- `nett_points_raw`: Total after removing discarded races

**Checksum Rules**:
- `total_points_raw = SUM(race_scores)`
- `nett_points_raw = total_points_raw - discarded_race_scores`

### 4. `sailing_id` - Official SA Sailing Members
**Purpose**: Master list of all SA Sailing members
**Key Fields**:
- `sa_sailing_id` (PK): Official SA Sailing ID
- `first_name`: Member's first name
- `last_name`: Member's surname
- `date_of_birth`: Birth date
- `home_club_code`: Primary club abbreviation
- `status`: Member status

### 5. `temp_people` - Temporary Sailor Records
**Purpose**: Stores sailors not yet matched to official SAS IDs
**Key Fields**:
- `temp_id` (PK): Auto-incrementing temporary ID
- `full_name`: Complete sailor name
- `club_name`: Club information
- `notes`: Source information

### 6. `clubs` - Sailing Clubs
**Purpose**: Master list of sailing clubs
**Key Fields**:
- `club_id` (PK): Auto-incrementing ID
- `club_abbrev`: Club abbreviation (e.g., "ZVYC", "MAC")
- `club_name`: Full club name
- `province_code`: Province abbreviation

## Data Flow Process

### 1. From Results Sheet Screenshot to Database

#### Step 1: Extract Fleet Header Information
From screenshot header line (e.g., "Sailed: 8, Discards: 1, To count: 7, Entries: 6, Scoring system: Appendix A"):
```sql
INSERT INTO regatta_blocks (
    block_id, regatta_id, fleet_label, class_canonical, class_original,
    races_sailed, discard_count, handicap_system
) VALUES (
    'regatta-id:fleet-name', 'regatta-id', 'Fleet Name', 'Class', 'Class',
    8, 1, 'Appendix A'
);
```

#### Step 2: Extract Individual Results
For each sailor row in the results table:
```sql
INSERT INTO results (
    regatta_id, block_id, rank, helm_name, crew_name, sail_number,
    club_raw, race_scores, total_points_raw, nett_points_raw
) VALUES (
    'regatta-id', 'block-id', 1, 'Sailor Name', '', 'Sail No',
    'Club Code', '{"R1":"1.0","R2":"2.0",...}', 10.0, 8.0
);
```

#### Step 3: Automated SAS ID Matching
```sql
SELECT app.process_fleet('block-id');
```
This function:
- Matches helm names to SAS IDs (exact name match)
- Creates temp IDs for unmatched sailors
- Updates club codes in sailing_id table
- Updates club_id in results table

### 2. Checksum Validation

#### Fleet Level Checksums
- **Entries Count**: `COUNT(*) FROM results WHERE block_id = 'block-id'`
- **To Count**: `races_sailed - discard_count`
- **Scoring System**: Must be "Appendix A" for standard racing

#### Sailor Level Checksums
- **Total Points**: Sum of all race scores (including discarded)
- **Nett Points**: Total points minus discarded race scores
- **Race Scores**: Must match individual race results from screenshot

#### Example Validation Query
```sql
SELECT 
    r.rank, r.helm_name, r.total_points_raw, r.nett_points_raw,
    -- Validate race scores sum
    (SELECT SUM(value::numeric) FROM jsonb_each_text(r.race_scores)) as calculated_total,
    -- Validate nett calculation
    (SELECT SUM(value::numeric) FROM jsonb_each_text(r.race_scores) 
     WHERE key NOT LIKE '(R%' AND value NOT LIKE '(%') as calculated_nett
FROM results r 
WHERE r.block_id = 'block-id'
ORDER BY r.rank;
```

## HTML Viewer Integration

### API Endpoints
- `GET /api/regatta/{regatta_id}`: Returns all fleet data for a regatta
- `GET /api/people/search`: Searches for sailors by name
- `POST /api/people/temp`: Creates new temporary sailor
- `PATCH /api/result/{result_id}`: Updates individual result fields

### Data Display Rules
1. **Fleet Headers**: Display from `regatta_blocks` table
2. **Sailor Names**: Two-line format (first name / surname)
3. **Race Scores**: Two-line format (score / penalty code)
4. **SAS ID Matching**: Auto-suggest with exact match priority
5. **Club Codes**: Display from `club_raw` field

### Inline Editing
- Helm/Crew names: Live search with SAS ID suggestions
- Race scores: Direct editing with validation
- Club codes: Auto-complete from clubs table
- All changes saved via PATCH API calls

## Quality Assurance

### Data Integrity Rules
1. All fleets must have matching `regatta_blocks` and `results` entries
2. SAS IDs must exist in `sailing_id` table before assignment
3. Club codes must exist in `clubs` table
4. Race scores must sum correctly to totals
5. Discarded scores must be properly marked in JSONB

### Validation Queries
```sql
-- Check for unmapped clubs
SELECT DISTINCT club_raw FROM results WHERE club_id IS NULL;

-- Check for missing SAS IDs
SELECT COUNT(*) FROM results WHERE helm_sa_sailing_id IS NULL AND helm_temp_id IS NULL;

-- Validate race score calculations
SELECT result_id, total_points_raw, nett_points_raw,
       (SELECT SUM(value::numeric) FROM jsonb_each_text(race_scores)) as calc_total
FROM results WHERE total_points_raw != (SELECT SUM(value::numeric) FROM jsonb_each_text(race_scores));
```

## Automation Functions

### `app.process_fleet(block_id)`
Automatically processes a fleet by:
1. Matching helm names to SAS IDs
2. Creating temp IDs for unmatched sailors
3. Updating club codes in sailing_id table
4. Setting club_id in results table

### `app.create_fleet_with_validation(regatta_id, fleet_data)`
Creates a complete fleet with validation:
1. Validates regatta exists
2. Creates/updates regatta_blocks entry
3. Inserts/updates all results
4. Runs automatic SAS ID matching
5. Updates club mappings

This ensures 99% correct data on first population with minimal manual intervention.
