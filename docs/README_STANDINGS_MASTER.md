# Master Standings Calculation System - README

**Version:** 1.0  
**Date:** 10 December 2025  
**Status:** Current / Active Version

---

## Overview

This document describes the complete, automated system for calculating and maintaining sailing class standings. The system processes regatta results chronologically, builds head-to-head comparisons, and automatically maintains Master Lists and Standing Lists for all classes.

**⚠️ IMPORTANT:** This is the CURRENT and ACTIVE version. All previous standings READMEs and calculation methods are deprecated unless explicitly stated.

---

## System Architecture

### Components

1. **Master List** - Complete list of all eligible sailors for a class
2. **Standing List** - Ranked list of sailors based on head-to-head results
3. **Head-to-Head Matrix** - Complete comparison data between all sailors
4. **Auto-Update System** - Automatic maintenance when new regatta data arrives
5. **API Endpoints** - RESTful access for HTML pages

### Key Principles

- **Generic System:** Works for ALL classes (Dabchick, Optimist, ILCA, Hobie 16, etc.)
- **Fully Automated:** No manual intervention required
- **WC Weighted:** World Championship results carry more weight
- **Proof Required:** Leapfrog logic requires transitive proof
- **Always Validated:** Standing List count must equal Master List count

### Exceptions to Generic Process

**Note:** The process is the same for all classes, with only TWO exceptions:

1. **Classes with Progression (e.g., Optimist B → A):**
   - Master List must account for sailors from both progression levels
   - See "Classes with Progression" section for details

2. **Age Out Rules:**
   - Sailors exceeding age limits must be excluded/discarded
   - Age limits are class-specific (e.g., Optimist: max 15, so 16+ not eligible)
   - See "Age Limits and Eligibility" section for details

---

## Step-by-Step Process

### Step 1: Identify and Make List of Valid Sailors (Master List)

**Purpose:** Create the complete, unchanging list of all eligible sailors for a class.

**Criteria for Valid Sailors:**
1. Has raced in the class (`raced = TRUE`)
2. Is a helm (not crew-only)
3. Raced within last 13 months
4. Excludes Regatta 374 (incomplete regattas)
5. Meets age eligibility (if applicable)
6. **Exception:** For classes with progression (e.g., Optimist B→A), include sailors from both levels

**SQL Query:**
```sql
SELECT DISTINCT
    COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) as sailor_id,
    r.helm_name as name,
    s.first_name, s.last_name, s.year_of_birth, s.age
FROM results r
JOIN regatta_blocks rb ON rb.block_id = r.block_id
JOIN regattas reg ON reg.regatta_id = r.regatta_id
LEFT JOIN sas_id_personal s ON s.sa_sailing_id::text = r.helm_sa_sailing_id::text
WHERE 
    (LOWER(rb.fleet_label) = LOWER(%s) OR LOWER(rb.class_canonical) = LOWER(%s) 
     OR LOWER(REPLACE(rb.fleet_label, ' Fleet', '')) = LOWER(%s) 
     OR LOWER(REPLACE(rb.class_canonical, ' Fleet', '')) = LOWER(%s))
    AND r.raced = TRUE
    AND reg.regatta_number != 374
    AND (reg.end_date >= %s OR reg.start_date >= %s)
    AND COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) IS NOT NULL
    AND (s.age IS NULL OR s.age <= %s)  -- Age limit if applicable
ORDER BY r.helm_name
```

**Output:** List of all eligible sailors with their data.

---

### Step 2: Identify Valid Regattas and Determine Major Regattas

**Purpose:** Identify all valid regattas in last 12 months and classify which are "major."

**Valid Regatta Criteria:**
1. Has results for the class (`raced = TRUE`)
2. Occurred within last 12 months
3. Excludes Regatta 374
4. Matches class name

**Major Regatta Classification:**
- **Largest Regatta:** Highest number of entries
- **70% Threshold:** Any regatta with entries >= 70% of largest

**SQL Query:**
```sql
SELECT 
    reg.regatta_id, reg.regatta_number, reg.event_name,
    reg.start_date, reg.end_date,
    COUNT(DISTINCT COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id)) as entries
FROM results r
JOIN regatta_blocks rb ON rb.block_id = r.block_id
JOIN regattas reg ON reg.regatta_id = r.regatta_id
WHERE 
    -- Class matching
    (LOWER(rb.fleet_label) = LOWER(%s) OR ...)
    AND r.raced = TRUE
    AND reg.regatta_number != 374
    AND (reg.end_date >= %s OR reg.start_date >= %s)
    AND COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id) IS NOT NULL
GROUP BY reg.regatta_id, reg.regatta_number, reg.event_name, reg.start_date, reg.end_date
ORDER BY reg.start_date ASC
```

**Output:**
- Total valid regattas
- Oldest regatta
- Largest regatta
- Major regattas list (>= 70% of largest)
- WC regattas (if multi-province)

---

### Step 3: Create Master Sailor List and Initialize Standing List

**Purpose:** Establish two separate lists for the calculation process.

**Master Sailor List:**
- Source: Step 1 output
- Status: Immutable reference list
- Purpose: Verify eligibility, ensure completeness

**Standing List:**
- Initial State: Empty `[]`
- Final State: All sailors ranked 1-N
- Purpose: Final ranked standings

**Implementation:**
```python
master_sailor_list = step1_valid_sailors  # From Step 1
class_standing_list = []  # Empty, will be populated
```

---

### Step 4: Identify Sailors from Oldest Regatta (But Don't Add Yet)

**Purpose:** Identify sailors from the oldest valid regatta, but **DO NOT** add them to the Standing List yet. They will be added at the BOTTOM after all other regattas are processed.

**⚠️ CRITICAL CHANGE:** Sailors from the oldest regatta who haven't raced since must start at the BOTTOM of the standings. They can only move up if they have beaten sailors from OTHER regattas (not just their own old regatta).

**Process:**
1. Get oldest regatta (from Step 2)
2. Fetch ALL sailors who raced in that regatta (no ID filtering)
3. Store them in a separate list (`old_regatta_sailors`) with flag `from_old_regatta = True`
4. **DO NOT** add them to Standing List yet
5. Start with empty Standing List

**SQL Query:**
```sql
SELECT 
    r.rank,
    COALESCE(r.helm_sa_sailing_id::text, r.helm_temp_id, 'NO_ID_' || r.result_id::text) as sailor_id,
    r.helm_name as name
FROM results r
JOIN regatta_blocks rb ON rb.block_id = r.block_id
WHERE 
    r.regatta_id = %s  -- Oldest regatta ID
    AND (LOWER(rb.fleet_label) LIKE '%%class_name%%' 
         OR LOWER(rb.class_canonical) LIKE '%%class_name%%')
    AND r.raced = TRUE
    -- NO ID FILTERING - Include everyone
ORDER BY r.rank ASC
```

**Output:** List of sailors from oldest regatta (stored separately, not yet in Standing List).

---

### Step 5: Process Next Regatta and Integrate into Standing List

**Purpose:** Process the next regatta chronologically and integrate sailors based on head-to-head.

**Process:**
1. Get next regatta in chronological order
2. For each sailor in regatta:
   - **If already in Standing List:** Update regatta count
   - **If new sailor:** Determine position based on head-to-head

**Head-to-Head Testing:**
- Find sailors in Standing List who also raced this regatta
- Compare ranks:
  - If new sailor beat standing sailor: Place above
  - If new sailor lost to standing sailor: Place below

**Positioning Rules:**
- **Above sailors they beat:** Insert above best (lowest rank) sailor they beat
- **Below sailors they lost to:** Insert below worst (highest rank) sailor they lost to
- **No head-to-head:** Depends on regatta type (see Step 6)

**No Duplicates:** Sailors already in Standing List are not added again.

---

### Step 6: Process Non-Major Regatta with Special Rules

**Purpose:** Handle non-major regattas with special placement rules.

**Special Rules:**
1. **Sailors who only sailed this regatta:**
   - If no head-to-head: **Append to BOTTOM**
   - Stay below sailors who sailed more regattas

2. **Sailors with head-to-head:**
   - Follow normal positioning (above those they beat, below those they lost to)

3. **Sailors already in Standing List:**
   - Update regatta count
   - May be repositioned if head-to-head suggests it

**Rule:** Non-major regattas carry less weight. Sailors from small regattas don't automatically rank high.

---

### Step 7: Generic Iterative Process for All Remaining Regattas

**Purpose:** Continue processing all remaining regattas in chronological order.

**⚠️ CRITICAL: Step 7 is REPEATED for EACH regatta (EXCEPT oldest regatta)**

**Process continues:**
- Regatta 298 (oldest) - **SKIPPED** (sailors added at end)
- Regatta 331 - Step 7 iteration 1
- Regatta 336 - Step 7 iteration 2
- ... continue for each regatta ...
- Most recent regatta - Step 7 final iteration

**For Each Regatta:**
1. Identify regatta type (Major/Non-Major/WC)
2. Get regatta results
3. Add new sailors (if not in Standing List)
4. Update regatta counts for existing sailors
5. Apply head-to-head positioning
6. Apply leapfrog logic (with proof requirement)
7. Renumber ranks

**After Each Regatta:**
- Standing List grows (new sailors added)
- Existing sailors' regatta counts updated
- Leapfrog logic applied (WC weighted)
- List becomes more accurate

**After ALL Regattas Processed:**
1. Add sailors from oldest regatta who haven't raced since to BOTTOM of Standing List
2. Mark them with `from_old_regatta = True` flag
3. Apply final leapfrog pass (respecting old regatta restrictions - see Leapfrog Logic section)
4. Renumber all ranks

**Key Rule:** Sailors from the oldest regatta who only raced in that one regatta must stay at the bottom. They can only move up if they have beaten sailors from OTHER regattas (proving they can compete with current active sailors).

---

### WC Regatta Weighting and Leapfrog Logic

**WC Regattas with Multi-Province Participation:**
- Regattas with "WC" or "World Championship" in name
- Must have sailors from multiple provinces/clubs
- These regattas carry **MORE WEIGHT** than regular major regattas

**Leapfrog Logic (with Proof Requirement):**

**A sailor can ONLY leapfrog above another if:**
1. **Direct Beat:** Current sailor beat the higher-ranked sailor in at least one regatta
2. **Proof of Strength:** The higher-ranked sailor has beaten at least one sailor below them

**Implementation:**
```
FOR each sailor in Standing List (from bottom to top):
    FOR each sailor above them in Standing List:
        IF current sailor beat the higher-ranked sailor (especially WC):
            # PROOF REQUIRED
            IF higher-ranked sailor has beaten at least one sailor below them:
                Move current sailor ABOVE the higher-ranked sailor
            ELSE:
                Skip (no proof - higher sailor may be weak)
```

**Why Proof is Needed:**
- Prevents weak sailors from incorrectly ranking above strong sailors
- A single head-to-head result isn't enough - need transitive proof
- Only leapfrog if there's proof the higher sailor deserves their position

**WC Weight Priority:**
- WC head-to-head results override regular regatta results
- If a sailor beats someone in a WC, they should rank above them
- Pay close attention to ranks in WC regattas

---

### Step 8: Auto-Update Process

#### 8.1: Auto-Update Master List

**When New Sailor Sails for First Time:**
1. Detect new sailor (not in Master List)
2. Validate eligibility (age, raced, helm, etc.)
3. Add to Master List

**When Sailor Ages Out:**
1. Detect aged-out sailors (`age > max_age`)
2. Remove from Master List (`is_active = FALSE`)
3. Remove from Standing List
4. Renumber Standing List ranks

#### 8.2: Auto-Update Standing List

**When New Regatta Results Added:**
1. Identify new regatta (not yet processed)
2. Process new regatta (add sailors, update counts)
3. Apply head-to-head positioning
4. Apply leapfrog logic (with proof)
5. Mark regatta as processed

**Note:** Open regattas (not yet raced) use Standing List for auto-sort. Once race results are entered, real race scores override standings-based ranks.

#### 8.3: Open Regatta Auto-Sort (Before Races)

**For open regattas with entries but no race results:**

**Auto-Sort Process:**
1. **Check if regatta has race results:**
   - Query: `SELECT COUNT(*) FROM results WHERE regatta_id = %s AND raced = TRUE AND race_scores IS NOT NULL`
   - If count = 0: No races completed yet

2. **If No Races Completed:**
   - Sort entries by Standing List rank
   - Assign `rank` = Standing List rank (placeholder)
   - Display sailors in standings order

3. **If Races Completed:**
   - Sort entries by actual race scores (Nett points, or Total if no discards)
   - Assign `rank` = Race score rank
   - Standing List rank is ignored (real results take precedence)

**Implementation:**
```python
def get_regatta_rankings(regatta_id, class_name):
    # Check if races completed
    has_race_results = check_has_race_results(regatta_id)
    
    if not has_race_results:
        # Use Standing List (placeholder)
        standings = get_standing_list(class_name)
        return sort_by_standings(regatta_entries, standings)
    else:
        # Use actual race results
        return sort_by_race_scores(regatta_results)
```

**Key Rule:** Real race results always override standings. Standing-based rank is only a placeholder until races are completed.

---

### Step 9: Data Storage, Auto-Update, and API Access

#### Database Tables

**Master List Table:**
```sql
CREATE TABLE master_list (
    id SERIAL PRIMARY KEY,
    class_name TEXT NOT NULL,
    sailor_id TEXT NOT NULL,
    name TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    year_of_birth INTEGER,
    age INTEGER,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    removed_date TIMESTAMP,
    removal_reason TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(class_name, sailor_id)
);
```

**Standing List Table:**
```sql
CREATE TABLE standing_list (
    id SERIAL PRIMARY KEY,
    class_name TEXT NOT NULL,
    sailor_id TEXT NOT NULL,
    name TEXT NOT NULL,
    rank INTEGER NOT NULL,
    regattas_sailed INTEGER DEFAULT 1,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(class_name, sailor_id)
);
```

**Processed Regattas Table:**
```sql
CREATE TABLE processed_regattas (
    id SERIAL PRIMARY KEY,
    class_name TEXT NOT NULL,
    regatta_id TEXT NOT NULL,
    regatta_number INTEGER,
    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(class_name, regatta_id)
);
```

#### API Endpoints

**Get Standing List:**
```
GET /api/standings?class_name={class_name}
```

**Get Master List:**
```
GET /api/standings/master?class_name={class_name}
```

**Get Single Sailor Standing:**
```
GET /api/standings/sailor/{sailor_id}?class_name={class_name}
```

**Check Status:**
```
GET /api/standings/status?class_name={class_name}
```

#### Auto-Update Triggers

**Trigger 1: New Regatta Results Imported**
- Automatically detect new regatta
- Update Master List (add new sailors, remove aged-out)
- Update Standing List (process new regatta)
- Mark as processed

**Trigger 2: Age Eligibility Check (Monthly)**
- Check all classes for aged-out sailors
- Remove from both lists
- Renumber Standing List

**Trigger 3: New Sailor Detection**
- When new regatta added, find new sailors
- Add to Master List if eligible
- Add to Standing List with appropriate rank

---

## Critical Validation Rules

### Rule 1: Standing List Count = Master List Count

**After processing the last/most recent regatta:**

```
IF len(Standing List) != len(Master List):
    ERROR: Missing sailors or duplicate entries
    Identify which sailors are:
    - In Master List but NOT in Standing List
    - In Standing List but NOT in Master List
```

**If counts don't match, the process has failed.**

### Rule 2: No Duplicates

- Never add the same sailor twice to Standing List
- If sailor already in list, only update regatta count

### Rule 3: Sequential Ranks

- Ranks must be sequential (1, 2, 3, ... N) with no gaps
- No duplicate ranks for same class

### Rule 4: All Sailors Accounted For

- All sailors in Standing List must be in Master List
- All active sailors in Master List must be in Standing List

---

## Important Notes

### Regatta 374 Exclusion

**⚠️ CRITICAL:** Regatta 374 is **NEVER** used as a filter in any step of the standings calculation process. Do NOT exclude or filter by Regatta 374 in any query.

### Open Regattas (Not Yet Raced) - Auto Sort Function

**For open regattas (e.g., Regatta 374) that have entries but no race results yet:**

**Auto Sort Function:**
1. **Before Races Completed:**
   - Use **Standing List** to sort entries
   - Sailors are displayed in order of their master standings rank
   - This is a **placeholder** until real race results are entered
   - Rank in results table = Standing List rank

2. **After Races Completed:**
   - Switch to using **actual race scores** (Total/Discard/Nett)
   - Real race results **override** standing-based ranks
   - Rank in results table = Race score rank (Total/Nett points)
   - Standing/rank becomes irrelevant once real results exist

**Implementation Logic:**
```python
IF regatta has race results (raced = TRUE, race_scores populated):
    # Use actual race results for ranking
    Sort by: nett_points_raw ASC (or total_points_raw if no discards)
    Rank = Position based on race scores
ELSE:
    # Use Standing List for ranking (placeholder)
    Sort by: Standing List rank ASC
    Rank = Standing List rank (placeholder)
```

**Key Points:**
- **Standing-based rank is temporary** - only used until races are completed
- **Real race results always take precedence** - once races are entered, standings are ignored
- **Auto-sort function** ensures entries are displayed in logical order even before racing
- **Seamless transition** from standings-based to results-based ranking

**Example:**
- Regatta 374 Dabchick: 31 entries, no races yet → Sorted by master standings rank
- Regatta 374 ILCA 4.7: 16 entries, no races yet → Sorted by master standings rank
- Once races are completed, real race scores override standings-based ranks

**Implementation:**
- The `/api/regatta/{regatta_id}` endpoint automatically sorts Regatta 374 entries by master standings from the `standing_list` table
- The `/api/standings?class_name={class}&open_regatta_only=true` endpoint returns Regatta 374 entries ranked by master standings
- Both endpoints query the `standing_list` table to get master standings ranks for each sailor

**Database Update Process (Manual):**
When master standings are recalculated, Regatta 374 entries should be updated to match:

```sql
-- Update Regatta 374 entries to be sorted by master standings
WITH regatta_374_entries AS (
    SELECT 
        r.result_id,
        r.helm_sa_sailing_id,
        sl.rank as standing_rank,
        COALESCE(sl.rank, 9999) as sort_rank
    FROM results r
    JOIN regatta_blocks rb ON r.block_id = rb.block_id
    JOIN regattas reg ON reg.regatta_id = r.regatta_id
    LEFT JOIN standing_list sl ON sl.sailor_id = r.helm_sa_sailing_id::text 
        AND sl.class_name = 'CLASS_NAME'
    WHERE reg.regatta_number = 374
        AND LOWER(rb.class_canonical) LIKE '%class_name%'
),
ranked_entries AS (
    SELECT 
        result_id,
        ROW_NUMBER() OVER (ORDER BY sort_rank ASC, helm_sa_sailing_id::text ASC) as new_rank
    FROM regatta_374_entries
)
UPDATE results r
SET rank = re.new_rank
FROM ranked_entries re
WHERE r.result_id = re.result_id;
```

**Note:** Replace `CLASS_NAME` and `class_name` with the actual class name (e.g., 'Dabchick', 'ILCA 4.7').
- Display: Sailors sorted by Standing List (1st, 2nd, 3rd, ... 31st)
- After R1 completed: Display: Sailors sorted by R1 score (lowest score = 1st)
- After all races: Display: Sailors sorted by Nett points (lowest = 1st)

### Age Limits and Eligibility

**Age Out Rule:**
- Sailors who exceed the maximum age limit are **NOT eligible** to participate
- Must be **excluded/discarded** from Master List and Standing List
- Age is calculated from `year_of_birth` or `age` column

**Current Age Limits:**
- **Optimist:** Max 15 years (16 and older NOT eligible)
- **Dabchick:** Max 19 years (20 and older NOT eligible)
- **Other classes:** Age limits to be added as they are determined

**Age Limit Configuration:**
- Age limits are configurable per class
- Stored in class configuration or age_limits table
- Can be updated as new class limits are determined

**SQL Query for Age Eligibility:**
```sql
-- In Step 1, filter by age limit
AND (s.age IS NULL OR s.age <= %s)  -- max_age for class

-- Age out check (Step 8.1)
WHERE age IS NOT NULL AND age > %s  -- max_age for class
```

**Note:** Age limits will be added for other classes as they are determined. System is designed to accommodate any age limit per class.

### Class Name Normalization

- Handle variations: "Hobie 16" vs "Hobie 16 Fleet"
- Remove "Fleet" suffix for matching
- Case-insensitive matching

### Crew Members

- **Only helms are counted** in standings
- Crew members share the helm's boat/result
- Crew-only entries are excluded

### Classes with Progression (Exception to Generic Process)

**Classes with Progression (e.g., Optimist B → A):**

**Special Case:** Some classes have progression levels where sailors move from one level to another (e.g., Optimist B to Optimist A).

**Master List Must Account for Progression:**
1. **Include sailors from both levels:**
   - Optimist A: Include all sailors who have raced in Optimist A
   - Optimist B: Include all sailors who have raced in Optimist B
   - **OR** combine both if standings are unified

2. **Progression Logic:**
   - If a sailor has raced in both A and B, they should appear in the appropriate level's Master List
   - Master List for "Optimist A" should include:
     - All sailors who raced in Optimist A
     - Sailors who progressed from B to A (if applicable)

3. **Standing List Considerations:**
   - Standing List should reflect the appropriate level
   - If unified standings: Combine results from both A and B
   - If separate standings: Maintain separate lists for A and B

**Implementation:**
- Master List query must check for both class variations:
  ```sql
  WHERE (LOWER(rb.fleet_label) LIKE '%%optimist a%%' 
         OR LOWER(rb.fleet_label) LIKE '%%optimist b%%'
         OR LOWER(rb.class_canonical) LIKE '%%optimist%%')
  ```
- Or maintain separate Master Lists for each progression level
- Age limits apply to the progression level (e.g., Optimist A: max 15, Optimist B: max 15)

**Note:** This is the only exception to the generic process. All other classes follow the standard process without modification.

---

## Automation Requirements

### Fully Automated System

1. **No Manual Intervention:** Process runs automatically when new data arrives
2. **Real-Time Updates:** Master List and Standing List update automatically
3. **Age Monitoring:** Sailors automatically removed when they exceed age limits
4. **API Access:** HTML pages access data via REST API endpoints
5. **Validation:** Automatic validation ensures data integrity after each update

### Scheduled Jobs

**Monthly Age Check:**
- Run age eligibility check for all classes
- Remove aged-out sailors
- Update Standing List accordingly

**Daily Regatta Check:**
- Check for new regattas not yet processed
- Auto-process new regattas for all classes
- Update Standing Lists

---

## HTML Page Integration

### Automatic Data Access

HTML pages can access standings data via API:

```javascript
// Fetch standing list for a class
async function loadStandings(className) {
    const response = await fetch(`/api/standings?class_name=${encodeURIComponent(className)}`);
    const data = await response.json();
    displayStandings(data.rankings);
}

// Auto-refresh on page load
window.addEventListener('load', () => {
    const className = getClassFromURL();
    loadStandings(className);
});
```

**No manual updates required** - HTML pages automatically get current standings.

---

## Summary

This system provides:

1. **Complete Process:** Step-by-step calculation from Master List to final Standing List
2. **WC Weighting:** World Championship results carry more weight
3. **Proof Requirement:** Leapfrog logic requires transitive proof
4. **Auto-Updates:** Automatic maintenance when new data arrives
5. **API Access:** RESTful endpoints for HTML page access
6. **Validation:** Automatic validation ensures data integrity
7. **Generic System:** Works for all classes

**The system is fully automated and requires no manual intervention once implemented.**

---

**Document Version:** 1.0  
**Last Updated:** 10 December 2025  
**Status:** Current / Active Version

---

*This is the master reference document for the standings calculation system. All previous READMEs are deprecated unless explicitly stated.*

