# Sailor Standings & Ranking System

## Overview

The standings and ranking system calculates sailor rankings within a class (e.g., Optimist A, ILCA 6) based on head-to-head comparisons from regatta results. This system replaced the previous standing calculation method and provides a more accurate, transparent ranking based on actual race performance.

**Last Updated:** December 8, 2025

## Key Principles

1. **Master List**: All eligible sailors who have raced in the class (excluding regattas that haven't been raced yet, e.g., Regatta 374)
2. **Head-to-Head Comparisons**: Rankings are based on direct comparisons between sailors in the same regattas
3. **Regatta Weighting**: Different regatta types carry different weights (Major > Regional > Club)
4. **13-Month Window**: Head-to-head comparisons use regattas from the last 13 months
5. **No Date Limit for Master List**: The master list includes all historical sailors, but comparisons use recent results

## Master List Eligibility

### Optimist Classes
- **Optimist A**: Maximum age 15 (as of current year)
- **Optimist B**: Maximum age 15 (as of current year)
- Sailors who have aged out are excluded from the master list

### Other Classes
- Age limits are configurable per class (currently TBD for Dabchick, ILCA 4, ILCA 6, ILCA 7)
- All sailors who have raced in the class are included (no age limit by default)

### Exclusion Rules
- **Regatta 374** (and similar future regattas): Excluded from master list and comparisons until races have been completed
- Sailors must have `raced = TRUE` in at least one regatta result
- Sailors must have a valid SA Sailing ID or Temp ID

## Ranking Calculation Process

### Step 1: Build Master List
1. Query all sailors who have raced in the class (excluding unraced regattas)
2. Apply age limits if defined for the class
3. Store basic sailor information (name, SA ID, age, etc.)

### Step 2: Collect Regatta Data
1. Query all regattas from the **last 13 months** where these sailors competed
2. Exclude unraced regattas (e.g., Regatta 374)
3. For each regatta, determine its **weight** (see Regatta Weighting below)

### Step 3: Build Head-to-Head Matrix
For each regatta where two or more sailors competed:
1. Compare each sailor's rank against every other sailor in the same fleet
2. Track wins, losses, and ties
3. Apply regatta weight to each comparison:
   - **Major regatta win**: +3 weighted points
   - **Regional regatta win**: +2 weighted points
   - **Club regatta win**: +1 weighted point
4. Track most recent head-to-head result (preferring higher-weight regattas)

### Step 4: Calculate Sailor Statistics
For each sailor, calculate:
- **Total wins/losses/ties**: Count of head-to-head comparisons
- **Weighted wins**: Sum of weighted points from wins
- **Major wins**: Count of wins in major regattas
- **Regional wins**: Count of wins in regional regattas
- **Club wins**: Count of wins in club regattas
- **Regatta count**: Number of regattas sailed
- **Average rank**: Mean rank across all regattas
- **First rank**: Rank in first regatta
- **Last rank**: Rank in most recent regatta
- **Improvement**: First rank - Last rank (positive = improved)
- **Recent trend**: Average of first 3 regattas vs last 3 regattas (if >= 3 regattas)
- **Win rate**: Wins / (Wins + Losses)
- **Head-to-head comparison count**: Number of unique sailors compared against

### Step 5: Sort and Rank
Sailors are sorted using a multi-priority comparison function:

#### Priority 1: Head-to-Head Comparison Count
- Sailors with **zero comparisons** go to the bottom
- If both have zero comparisons, sort by regatta count
- If comparison counts differ by **>= 5**, prioritize higher comparison count

#### Priority 2: Regatta Count
- Sailors with **zero regattas** go to the bottom
- If regatta counts differ by **>= 2**, prioritize higher regatta count

#### Priority 3: Head-to-Head Results (if regatta counts are similar, difference <= 1)
1. **Major regatta head-to-head** (most important)
   - Compare wins in major regattas (weight = 3)
2. **Weighted wins** (major regattas count more)
   - Compare total weighted wins
3. **Regional regatta head-to-head**
   - Compare wins in regional regattas (weight = 2)
4. **Total head-to-head wins** (unweighted)
   - If difference >= 2, clear winner
   - If difference <= 1, use tiebreakers

#### Priority 4: Tiebreakers (for close matches, difference <= 1)
1. **Most recent result**
   - Prefer result from higher-weight regatta
   - If same weight, prefer better rank in most recent regatta
2. **Improvement trend** (if both have >= 2 regattas)
   - Compare improvement: (first rank - last rank)
   - Positive = improved, negative = declined
3. **Recent trend** (if both have >= 3 regattas)
   - Compare: (average of first 3) - (average of last 3)
   - Positive = improving, negative = declining
4. **Average rank**
   - Lower average rank = better
5. **Win rate**
   - Higher win rate = better

#### Final Tiebreakers
- Regatta count (if still tied)
- Average rank (ultimate tiebreaker)

### Step 6: Assign Final Ranks
After sorting, assign sequential ranks 1, 2, 3, ... N (where N = total eligible sailors)

## Regatta Weighting

Regattas are classified into three categories with different weights:

### Weight 3: Major/National Regattas
- Event name contains: "national", "nationals", "youth nationals", "sa sailing youth nationals"
- Regatta type = "NATIONAL"
- Examples: SA Youth Nationals, SA Sailing Youth Nationals

### Weight 2: Regional/Championship Regattas
- Event name contains: "regional", "championship", "championships", "cape classic", "classic"
- Regatta type = "REGIONAL"
- Examples: Cape Classic Series, Regional Championships

### Weight 1: Club/Provincial Regattas
- All other regattas
- Examples: Club regattas, provincial events

## API Endpoint

### `/api/standings`

**Parameters:**
- `class_name` (required): Class name, e.g., "Optimist A", "ILCA 6"
- `open_regatta_only` (optional, string): If "true", returns only sailors in Regatta 374 (for testing). Default: returns master list

**Response:**
```json
{
  "rankings": [
    {
      "sailor_id": "21172",
      "name": "Timothy Weaving",
      "first_name": "Timothy",
      "last_name": "Weaving",
      "main_rank": "4",
      "regatta_count": 8,
      "avg_rank": 3.5,
      "win_rate": 0.75,
      "h2h_comparisons": 45,
      ...
    }
  ],
  "total_sailors": 65,
  "aged_out": [],
  "unlikely": []
}
```

## Display in HTML

The `search.html` page displays standings in the "Sailing Statistics Main Class" section:

- **Header**: "Sailing Statistics Main Class = Xth of Y sailors"
- **Current Ranking**: "Current Ranking Overall [Class] Fleet = Xth of Y"
- **Sailing History**: Lists regattas in last 13 months with:
  - Sailors ranked above (RED BOLD)
  - Current sailor's rank and name (BLUE BOLD)
  - Sailors ranked below (GREEN BOLD)

## Important Notes

1. **Regatta 374 Exclusion**: Regatta 374 (SA Youth Nationals Dec 2025) is excluded from all calculations until races are completed. It should not appear in sailing history or be used for comparisons.

2. **Master List vs Comparisons**:
   - **Master List**: Includes all historical sailors (no date limit)
   - **Comparisons**: Uses only last 13 months of regattas

3. **Zero Comparisons**: Sailors with zero head-to-head comparisons (e.g., JYC club sailors who only race locally) are ranked at the bottom, sorted by regatta count.

4. **Age Limits**: Currently only Optimist A/B have age limits (max 15). Other classes will have age limits determined later.

5. **Regatta Weighting**: The system automatically classifies regattas based on event name and regatta type. Ensure regatta names and types are correctly set in the database.

## Future Enhancements

- [ ] Determine age limits for Dabchick, ILCA 4, ILCA 6, ILCA 7
- [ ] Add configurable regatta weighting rules
- [ ] Add standing history tracking (rank changes over time)
- [ ] Add standing export functionality
- [ ] Add standing comparison visualization

## Technical Implementation

- **Language**: Python (FastAPI)
- **Database**: PostgreSQL
- **Key Functions**:
  - `api_standings()`: Main API endpoint
  - `get_regatta_weight()`: Classifies regatta weight
  - `compare_sailors()`: Comparison function for sorting
- **Location**: `/api.py` (lines ~1881-2374)

## Related Documentation

- `README_regatta_results_system.md`: Regatta results storage
- `README_results_table.md`: Results table structure
- `README_regattas_table.md`: Regattas table structure

