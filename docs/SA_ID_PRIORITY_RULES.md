# SA ID Priority Rules for Data Entry

## CRITICAL: Prioritize SA IDs for Sailors Who Actually Raced

### Rule 1: Raced Sailors = HIGH PRIORITY
**Always prioritize getting SA IDs for sailors who actually raced.**

A sailor "raced" if they have **at least one race score that is NOT a penalty code** (DNC, DNS, DNF, RET, etc.).

**Why:**
- Their results count toward rankings
- They appear in official results
- They may be eligible for prizes/qualifications
- Their performance data is meaningful

### Rule 2: No-Race Entrants = LOW PRIORITY
**Sailors who entered but did NOT race can be left with temp IDs if needed.**

A sailor "did not race" if they have **ONLY penalty codes** (DNC, DNS, DNF) or no race scores at all.

**Why:**
- They didn't compete, so their data is less critical
- No impact on rankings or results
- Can be added to database later if needed
- Reduces time spent on non-competitive entries

### Rule 3: Mixed Participation
**If some races have scores and others are penalties:**
- Count as "raced" if ANY race has a non-penalty score
- Still prioritize SA ID matching
- Example: R1=5.0, R2=16.0 DNC → Still raced (has R1)

### Implementation

#### Database Tracking
- `regatta_blocks.entries_raced`: Number of boats that actually raced (calculated automatically)
- `results.ranks_sailed`: Total entries in fleet/class
- Difference: `ranks_sailed - entries_raced` = boats that entered but never raced

#### Data Entry Workflow
1. **First Pass**: Get SA IDs for all sailors who actually raced
2. **Second Pass** (if time): Get SA IDs for no-race entrants
3. **Skip** (if time-constrained): Leave no-race entrants with temp IDs

#### HTML Display
- Shows: `Entries: X (Raced: Y)` when different
- Example: `Entries: 15 (Raced: 4)` for Regatta 370 Multihull Fleet

#### Examples

**Regatta 370 Multihull Fleet:**
- Total Entries: 15
- Actually Raced: 4 (Bradley Stemmett, Kevin Webb, Kobus Holtzhausen, Greg Harrowsmith)
- Did Not Race: 11 (all have 16.0 DNC/DNF/DNS)
- **Action**: Prioritize SA IDs for the 4 who raced. Can skip or defer the 11 who didn't.

**Regatta 371 DF95:**
- All 12 Gold Fleet + 12 Silver Fleet = 24 entries
- All 24 actually raced (have race scores)
- **Action**: Get SA IDs for all 24 (all are high priority)

### SQL Query to Identify Raced vs Not-Raced

```sql
-- Raced: Have at least one non-penalty score
SELECT COUNT(*) as raced_count
FROM public.results r
WHERE r.block_id = '370-2025-vyc-tour-de-vlei-results:multihull'
  AND EXISTS (
      SELECT 1
      FROM jsonb_each_text(r.race_scores) AS t(race_key, score_value)
      WHERE score_value IS NOT NULL
        AND score_value !~ '^[0-9]+\.0 (DNC|DNS|DNF|RET|DSQ|OCS|UFD|BFD|DPI)'
        AND score_value ~ '^[0-9]+\.0'
  );

-- Not Raced: Only penalty codes or empty
SELECT COUNT(*) as not_raced_count
FROM public.results r
WHERE r.block_id = '370-2025-vyc-tour-de-vlei-results:multihull'
  AND NOT EXISTS (
      SELECT 1
      FROM jsonb_each_text(r.race_scores) AS t(race_key, score_value)
      WHERE score_value IS NOT NULL
        AND score_value !~ '^[0-9]+\.0 (DNC|DNS|DNF|RET|DSQ|OCS|UFD|BFD|DPI)'
        AND score_value ~ '^[0-9]+\.0'
  );
```



## CRITICAL: Prioritize SA IDs for Sailors Who Actually Raced

### Rule 1: Raced Sailors = HIGH PRIORITY
**Always prioritize getting SA IDs for sailors who actually raced.**

A sailor "raced" if they have **at least one race score that is NOT a penalty code** (DNC, DNS, DNF, RET, etc.).

**Why:**
- Their results count toward rankings
- They appear in official results
- They may be eligible for prizes/qualifications
- Their performance data is meaningful

### Rule 2: No-Race Entrants = LOW PRIORITY
**Sailors who entered but did NOT race can be left with temp IDs if needed.**

A sailor "did not race" if they have **ONLY penalty codes** (DNC, DNS, DNF) or no race scores at all.

**Why:**
- They didn't compete, so their data is less critical
- No impact on rankings or results
- Can be added to database later if needed
- Reduces time spent on non-competitive entries

### Rule 3: Mixed Participation
**If some races have scores and others are penalties:**
- Count as "raced" if ANY race has a non-penalty score
- Still prioritize SA ID matching
- Example: R1=5.0, R2=16.0 DNC → Still raced (has R1)

### Implementation

#### Database Tracking
- `regatta_blocks.entries_raced`: Number of boats that actually raced (calculated automatically)
- `results.ranks_sailed`: Total entries in fleet/class
- Difference: `ranks_sailed - entries_raced` = boats that entered but never raced

#### Data Entry Workflow
1. **First Pass**: Get SA IDs for all sailors who actually raced
2. **Second Pass** (if time): Get SA IDs for no-race entrants
3. **Skip** (if time-constrained): Leave no-race entrants with temp IDs

#### HTML Display
- Shows: `Entries: X (Raced: Y)` when different
- Example: `Entries: 15 (Raced: 4)` for Regatta 370 Multihull Fleet

#### Examples

**Regatta 370 Multihull Fleet:**
- Total Entries: 15
- Actually Raced: 4 (Bradley Stemmett, Kevin Webb, Kobus Holtzhausen, Greg Harrowsmith)
- Did Not Race: 11 (all have 16.0 DNC/DNF/DNS)
- **Action**: Prioritize SA IDs for the 4 who raced. Can skip or defer the 11 who didn't.

**Regatta 371 DF95:**
- All 12 Gold Fleet + 12 Silver Fleet = 24 entries
- All 24 actually raced (have race scores)
- **Action**: Get SA IDs for all 24 (all are high priority)

### SQL Query to Identify Raced vs Not-Raced

```sql
-- Raced: Have at least one non-penalty score
SELECT COUNT(*) as raced_count
FROM public.results r
WHERE r.block_id = '370-2025-vyc-tour-de-vlei-results:multihull'
  AND EXISTS (
      SELECT 1
      FROM jsonb_each_text(r.race_scores) AS t(race_key, score_value)
      WHERE score_value IS NOT NULL
        AND score_value !~ '^[0-9]+\.0 (DNC|DNS|DNF|RET|DSQ|OCS|UFD|BFD|DPI)'
        AND score_value ~ '^[0-9]+\.0'
  );

-- Not Raced: Only penalty codes or empty
SELECT COUNT(*) as not_raced_count
FROM public.results r
WHERE r.block_id = '370-2025-vyc-tour-de-vlei-results:multihull'
  AND NOT EXISTS (
      SELECT 1
      FROM jsonb_each_text(r.race_scores) AS t(race_key, score_value)
      WHERE score_value IS NOT NULL
        AND score_value !~ '^[0-9]+\.0 (DNC|DNS|DNF|RET|DSQ|OCS|UFD|BFD|DPI)'
        AND score_value ~ '^[0-9]+\.0'
  );
```


















