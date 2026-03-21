# Regatta Results Management - Data Flow Documentation

## Overview
This document describes the complete data flow from regatta search through the 14 header fields to the results section in the Regatta Results Management system.

## Search Process

### 1. Regatta Number Entry
- User enters regatta number in search field
- Search button triggers `searchRegatta()` function

### 2. Database Validation
- **API Endpoint**: `/api/regatta/<regatta_no>/name`
- **Step 1**: Check `regatta_sources` table for regatta existence
  - Query: `SELECT regatta_name FROM app.regatta_sources WHERE regatta_number = %s`
- **Step 2**: Validate results table exists
  - Table: `app.regatta_<regatta_number>_results`
  - Query: `SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'app' AND table_name = %s)`

### 3. Event Data Retrieval
- **Source**: `app.regatta_<regatta_number>_results` table
- **Qualifier**: `info_type = 'Event' AND regatta_no = <searched_regatta_number>`
- **Query**: `SELECT * FROM app.{table_name} WHERE info_type = 'Event' AND regatta_no = %s LIMIT 1`

## 15 Header Fields Data Sources

All fields fetch data directly from the database table with the same qualifier:
**Table**: `app.regatta_<regatta_number>_results`
**Qualifier**: `info_type = 'Event' AND regatta_no = <searched_regatta_number>`

| Field | HTML Element | Database Column | Line | Notes |
|-------|--------------|-----------------|------|-------|
| 1. regatta_no | `event-regatta_no` | `regatta_no` | 536 | Direct mapping |
| 2. regatta_name | `event-regatta_name` | `regatta_name` | 537 | Direct mapping |
| 3. info_typ | `event-info_typ` | `info_type` | 562 | Field ID vs column name |
| 4. regatta_type_provincial | `event-regatta_type_provincial` | `regatta_type_provincial` | 538 | Direct mapping |
| 5. regatta_type_national | `event-regatta_type_national` | `regatta_type_national` | 539 | Direct mapping |
| 6. series | `event-series` | `series` | 540 | Direct mapping |
| 7. series_name | `event-series_name` | `series_name` | 541 | Direct mapping |
| 8. club_abreviation | `event-club_abreviation` | `club_abreviation` | 542 | Direct mapping |
| 9. club_full_name | `event-club_full_name` | `club_full_name` | 543 | Direct mapping |
| 10. province | `event-province` | `province` | 544 | Direct mapping |
| 11. start_date | `event-start_date` | `start_date` | 546-552 | Formatted to "day month year" |
| 12. end_date | `event-end_date` | `end_date` | 553-559 | Formatted to "day month year" |
| 13. fleets_count | `event-fleets_count` | Calculated | 565 | Count of fleet_X = true columns |
| 14. result_status | `event-result_status` | `result_status` | 566 | Direct mapping |
| 15. as_at_time | `event-as_at_time` | `as_at_time` | 567 | Direct mapping |

## Results Section Data Sources

### Main Event Display
- **Line**: "ZVYC Southern Charter Cape Classic 13/14 Sept 2025"
- **Source**: Combination of:
  - `club_abreviation` (e.g., "ZVYC")
  - `regatta_name` (e.g., "Southern Charter Cape Classic")
  - Formatted `start_date` and `end_date` (e.g., "13/14 Sept 2025")

### Club Name
- **Element**: `clubName`
- **Source**: `club_abreviation` column
- **Line**: 581

### Results Status
- **Element**: `resultsStatus`
- **Source**: Template combining:
  - `result_status` (e.g., "Final")
  - Formatted `end_date` (e.g., "14 September 2025")
  - `as_at_time` (e.g., "17:15")
- **Format**: `Results are ${result_status} as of ${formattedEndDate} as at ${as_at_time}`
- **Line**: 584-590

### Fleet Information
- **Element**: `fleetName`
- **Source**: Fleet class data from boat names API
- **Format**: `${fleetClass} Fleet (1)`
- **Fallback**: "420 Fleet (1)" if no fleet class found

### Sailing Parameters
- **Element**: `sailingParams`
- **Source**: Multiple API calls to calculate:
  - `sailed_count`: Count of races with actual scores
  - `discards`: Calculated as `sailed_count // 5`
  - `to_count`: Calculated as `sailed_count - discards`
  - `entries`: Count of `fleet_1 = true AND info_type = 'Entrant'` rows
- **Format**: `Sailed: ${sailed}, Discards: ${discards}, To count: ${toCount}, Entries: ${entries}, Scoring system: Appendix A`

## Data Flow Summary

1. **Search** → Validate regatta exists in `regatta_sources`
2. **Table Check** → Confirm `app.regatta_<number>_results` table exists
3. **Event Data** → Fetch all 15 fields from Event row
4. **Display** → Populate header fields and results section
5. **Validation** → All data comes from database, no hardcoded values

## Fleet Count Calculation Rule

**Field**: `fleets_count`
**Rule**: Count all `fleet_X` columns where `fleet_X = true` in Fleet Info rows
**Process**:
1. Query Fleet Info rows: `info_type = 'Fleet Info' AND regatta_no = <searched_regatta_number>`
2. Check each `fleet_X` column (fleet_1, fleet_2, fleet_3, ..., fleet_15) in all Fleet Info rows
3. Count columns where `fleet_X = true` across all Fleet Info rows
4. Return total count as `fleets_count`

**Example**: Fleet Info rows with fleet_1=true, fleet_2=true, fleet_3=true, fleet_4=true, fleet_5=true → fleets_count = 5

## Fleet Name and Sailing Parameters Rules

### Fleet Name Display Rule
**Format**: `"${actualClass} Fleet (${fleetNumber})"`
**Example**: "420 Fleet (1)", "Dabchick Fleet (2)", "ILCA 4 Fleet (3)"

**Data Sources**:
1. **Fleet Number**: Determined by which `fleet_X = true` in Fleet Info rows
2. **Class Name**: Fetched from Entrant rows where `fleet_X = true`
3. **Table**: `app.regatta_<regatta_number>_results`
4. **Query**: 
   ```sql
   SELECT DISTINCT class 
   FROM app.regatta_<regatta_no>_results 
   WHERE info_type = 'Entrant' AND regatta_no = <regatta_no> AND fleet_X = true
   AND class IS NOT NULL AND class != 'None'
   LIMIT 1
   ```

### Sailing Parameters Line Rule
**Format**: `"Sailed: ${sailed}, Discards: ${discards}, To count: ${toCount}, Entries: ${entries}, Scoring system: Appendix A"`

**Data Sources**:
- **sailed**: Count of race columns with actual scores in database
- **discards**: Calculated as `sailed_count // 5` (1 discard after 5 races)
- **to_count**: Calculated as `sailed_count - discards`
- **entries**: Count of rows where `fleet_X = true AND info_type = 'Entrant'`
- **"Scoring system: Appendix A"**: Hardcoded text

**API Endpoint**: `/api/regatta/<regatta_no>/results`
**Table**: `app.regatta_<regatta_number>_results`

### Fleet Section Structure Template
```html
<div class="fleet-section" id="fleet-${fleetNumber}">
    <h3 class="fleet-name">${actualClass} Fleet (${fleetNumber})</h3>
    <div class="sailing-params" id="fleet-${fleetNumber}-sailing-params">
        Sailed: ${sailed}, Discards: ${discards}, To count: ${toCount}, Entries: ${entries}, Scoring system: Appendix A
    </div>
    <div class="results-table-container" id="fleet-${fleetNumber}-table">
        <!-- Results table will be inserted here -->
    </div>
</div>
```

## Results Table Column Rules

### Rank Column Rule
**Field**: `rank_position`
**Format**: Ordinal format (1st, 2nd, 3rd, 4th, 5th, etc.)
**Data Source**: `rank_position` column from Entrant rows
**Table**: `app.regatta_<regatta_number>_results`
**Query**: 
```sql
SELECT rank_position 
FROM app.regatta_<regatta_no>_results 
WHERE info_type = 'Entrant' AND regatta_no = <regatta_no> AND fleet_1 = true
ORDER BY rank_position ASC
```
**Processing**: Convert numeric ranks to ordinal format (1→1st, 2→2nd, 3→3rd, 4→4th, 5→5th, etc.)
**API Endpoint**: `/api/regatta/<regatta_no>/fleet/1/rank-positions`
**JavaScript Function**: `loadRankData(regattaNo)`

**Implementation Code**:
```javascript
async function loadRankData(regattaNo) {
    try {
        const response = await fetch(`/api/regatta/${regattaNo}/fleet/1/rank-positions`);
        const data = await response.json();
        
        if (data.success && data.ranks) {
            const rankCells = document.querySelectorAll('.results-table tbody tr td:first-child');
            data.ranks.forEach((rank, index) => {
                if (rankCells[index]) {
                    rankCells[index].textContent = rank;
                }
            });
        }
    } catch (error) {
        console.error('Error loading rank data:', error);
    }
}
```

## Key Principles

- **No Hardcoded Data**: All data must come from database queries
- **Single Source**: Each field fetches directly from database, no dependencies on other page elements
- **Consistent Qualifier**: All Event data uses `info_type = 'Event' AND regatta_no = <searched_regatta_number>`
- **Date Formatting**: All dates formatted to "day month year" format
- **Fleet Count**: Calculated dynamically by counting fleet_X = true columns
- **Error Handling**: Fallbacks provided for missing data

## File Locations

- **Frontend**: `Regatta results management.html`
- **Backend API**: `api_server.py`
- **Main API Endpoint**: `/api/regatta/<regatta_no>/name`
