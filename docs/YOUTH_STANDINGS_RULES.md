# Youth Standings Rules for Non-Optimist Classes

**Version:** 1.0  
**Date:** December 30, 2025  
**Status:** Active for 420, Sonnet, Dabchick, Hobie, ILCA, and other youth classes

---

## Overview

This document defines the standings calculation rules for **youth classes** (non-Optimist) such as 420, Sonnet, Dabchick, Hobie 16, ILCA 4, ILCA 6, etc. These rules apply when age-out limits are not yet defined or needed.

**Key Principle:** For youth regattas (especially major events like Regatta 374 - SA Youth Nationals), **Nationals rank = Standing** when a sailor has sailed in a Nationals regatta for that class.

---

## Core Rules

### Rule 1: Nationals Rank = Standing (Primary Rule)

**When a sailor has sailed in a Nationals regatta for a class:**
- Their **standing** is their **rank from that Nationals regatta**
- The standing is displayed as: `"Rank X / Y Sailors"` where:
  - `X` = Their rank in the Nationals regatta
  - `Y` = Total eligible sailors in the class (from master_list or standing_list)

**Examples:**
- Tim ranked **5th** in 420 Nationals (Regatta 366) → Standing: **5th / 19 Sailors**
- Tim ranked **6th** in Sonnet Nationals (Regatta 302) → Standing: **6th / 30 Sailors**

**API Endpoint:** `/api/member/{sa_id}/nationals-rank?class_name={class_name}`

---

### Rule 2: Identifying Nationals Regattas

A regatta is considered a **Nationals** if:
1. Event name contains: "national", "nationals", "youth nationals", "sa sailing youth nationals"
2. Event name contains: "championship" AND "national" (e.g., "420 National Championship")
3. Regatta type = "NATIONAL"

**Examples of Nationals:**
- ✅ "420 National Championship Results"
- ✅ "Sonnet National Championship 2025"
- ✅ "SA Youth Nationals Dec 2025"
- ✅ "2025 Dabchick WC Championship" (if it's the class Nationals)
- ❌ "Cape Classic Series" (not a Nationals)
- ❌ "Regional Championship" (not a Nationals unless it contains "national")

---

### Rule 3: Head-to-Head Comparison (When No Nationals)

**When a sailor has NOT sailed the most recent Nationals:**
- Use head-to-head comparisons with sailors who DID sail the Nationals
- Compare their rank in their most recent regatta with the Nationals sailors' ranks
- Position them based on who they beat/lost to in head-to-head comparisons

**Example:**
- Tim sailed Regatta 328 (Dabchick WC Championship) and ranked **9th**
- He did NOT sail Regatta 374 (SA Youth Nationals Dec 2025)
- Calculate his standing by comparing his 9th place in 328 with how Nationals sailors (374) performed
- Use head-to-head logic to determine his position among all 59 Dabchick sailors

---

### Rule 4: Age-Out Rules (Currently Ignored)

**For youth classes (420, Sonnet, Dabchick, Hobie, ILCA, etc.):**
- **Age-out limits are NOT currently applied**
- All sailors who have raced in the class are eligible
- No maximum age restriction
- Master list includes all historical sailors (no age filtering)

**Note:** This may change in the future when age limits are defined for specific classes.

---

### Rule 5: Master List Eligibility

**A sailor is eligible for a class master list if:**
1. Has raced in the class (`raced = TRUE`)
2. Is a helm (not crew-only)
3. Has raced within the last 14 months (for active status)
4. Has a valid SA Sailing ID or Temp ID
5. **NO age limit applied** (for youth classes)

**Time Window:**
- **Master List:** All historical sailors (no date limit)
- **Active Status:** Last 14 months (for displaying standings)
- **Standings Calculation:** Uses last 13 months of regattas for head-to-head

---

### Rule 6: Youth Regattas (e.g., Regatta 374)

**Special handling for youth regattas like SA Youth Nationals (Regatta 374):**
- These are **major regattas** with high weight (weight = 3)
- Sailors who sailed these regattas use their rank as their standing
- Sailors who didn't sail are positioned using head-to-head comparisons
- Regatta 374 is included in calculations once races are completed

**Regatta 374 Details:**
- Event: "SA Youth Nationals Dec 2025"
- Multiple classes: Optimist A, Optimist B, 420, Dabchick, Sonnet, ILCA, etc.
- Each class has its own standings based on Nationals results

---

## API Endpoints

### Primary Endpoint: `/api/member/{sa_id}/nationals-rank`

**Purpose:** Get Nationals rank for a sailor in a class (or calculate standing if they didn't sail Nationals)

**Parameters:**
- `sa_id` (path): Sailor's SA Sailing ID
- `class_name` (query): Class name (e.g., "420", "Sonnet", "Dabchick")

**Response:**
```json
{
  "rank": 5,
  "total_sailors": 19,
  "regatta_number": 366,
  "event_name": "420 National Championship Results",
  "sailed_nationals": true
}
```

**Or (if didn't sail Nationals):**
```json
{
  "rank": 9,
  "total_sailors": 59,
  "regatta_number": 328,
  "event_name": "2025 Dabchick WC Championship",
  "nationals_regatta": 374,
  "nationals_event": "SA Youth Nationals Dec 2025",
  "sailed_nationals": false,
  "head_to_head_beaten": 3,
  "head_to_head_lost": 2
}
```

**Logic:**
1. Find most recent Nationals regatta for the class
2. If sailor sailed it → return their rank and total eligible sailors
3. If sailor didn't sail it → find their most recent regatta and do head-to-head comparisons with Nationals sailors

---

### Fallback Endpoint: `/api/standings/db`

**Purpose:** Get pre-calculated standings from database (used as fallback)

**When to use:**
- Only when `/api/member/{sa_id}/nationals-rank` returns no data
- For Optimist classes (which have special progression rules)
- As a fallback for classes without Nationals regattas

---

## Display Rules

### Main Page (search.html)

**For each class in the profile:**
1. **First:** Call `/api/member/{sa_id}/nationals-rank?class_name={class_name}`
2. **If Nationals rank found:** Display `"Standing: Xth / Y Sailors"` (where X = Nationals rank)
3. **If no Nationals rank:** Fallback to `/api/standings/db` then `/api/standings`

**Example Display:**
- 420: "Standing: 5th / 19 Sailors" (from Nationals rank)
- Sonnet: "Standing: 6th / 30 Sailors" (from Nationals rank)
- Dabchick: "Standing: 9th / 59 Sailors" (from head-to-head calculation)

---

### Popup Modal (Sailor Stats)

**Same logic as main page:**
1. **First:** Call `/api/member/{sa_id}/nationals-rank?class_name={class_name}`
2. **If Nationals rank found:** Display `"Standing: Xth / Y Sailors"`
3. **If no Nationals rank:** Fallback to `/api/standings/db` then `/api/standings`

**Critical:** Popup and main page **MUST** show identical standings (same endpoint, same data).

---

## Examples

### Example 1: 420 Class

**Tim's Results:**
- Regatta 366: "420 National Championship Results" - Rank: **5th** out of 12 entries
- Total eligible 420 sailors: **19**

**Standing Display:**
- ✅ **Correct:** "Standing: 5th / 19 Sailors"
- ❌ **Wrong:** "Standing: 15th / 19 Sailors" (from calculated standings)

**Reason:** Nationals rank (5th) IS the standing, not the calculated standing (15th).

---

### Example 2: Sonnet Class

**Tim's Results:**
- Regatta 302: "Sonnet National Championship 2025" - Rank: **6th** out of 20 entries
- Total eligible Sonnet sailors: **30**

**Standing Display:**
- ✅ **Correct:** "Standing: 6th / 30 Sailors"
- ❌ **Wrong:** "Standing: Not ranked / 30 Sailors" (from calculated standings)

**Reason:** Nationals rank (6th) IS the standing.

---

### Example 3: Dabchick Class

**Tim's Results:**
- Regatta 328: "2025 Dabchick WC Championship" - Rank: **9th** out of 17 entries
- Regatta 374: "SA Youth Nationals Dec 2025" - **Did NOT sail**
- Total eligible Dabchick sailors: **59**

**Standing Calculation:**
1. Find most recent Nationals: Regatta 374 (SA Youth Nationals Dec 2025)
2. Tim didn't sail it
3. Find Tim's most recent regatta: Regatta 328 (ranked 9th)
4. Compare Tim's 9th place in 328 with how Nationals sailors (374) performed
5. Use head-to-head logic to position Tim among all 59 sailors

**Standing Display:**
- ✅ **Correct:** "Standing: Xth / 59 Sailors" (where X is calculated from head-to-head)
- ❌ **Wrong:** "Standing: 61th / 59 Sailors" (impossible, from incorrect calculated standings)

---

## Implementation Notes

### For Optimist Classes

**DO NOT apply these rules to Optimist A or Optimist B:**
- Optimist has special progression rules (B → A)
- Optimist has age-out rules (max 15)
- Optimist uses calculated standings from `/api/standings` or `/api/standings/db`
- See `docs/B_STANDINGS_RULES.md` and `docs/README_STANDINGS_RANKING.md` for Optimist-specific rules

### For Other Youth Classes

**Apply these rules to:**
- 420
- Sonnet
- Dabchick
- Hobie 16
- ILCA 4, ILCA 6, ILCA 7
- Any other youth class without defined age limits

---

## Data Consistency Requirements

### Single Source of Truth

**Critical Rule:** There can only be ONE source of truth for standings data.

1. **Nationals rank = Standing** (when sailor sailed Nationals)
2. **Same endpoint everywhere:** `/api/member/{sa_id}/nationals-rank`
3. **Same data displayed:** Main page and popup MUST show identical standings
4. **No conflicting data:** Cannot have different standings in different places

### Validation

**Before displaying standings, verify:**
- Main page and popup use the same endpoint
- Both show the same rank and total sailors
- Nationals rank takes priority over calculated standings
- Total sailors count matches master_list or standing_list

---

## Future Enhancements

- [ ] Define age limits for specific youth classes (if needed)
- [ ] Add standing history tracking
- [ ] Add standing export functionality
- [ ] Add visualization of head-to-head comparisons
- [ ] Add standing change notifications

---

## Related Documentation

- `docs/README_STANDINGS_RANKING.md` - General standings system (includes Optimist rules)
- `docs/README_STANDINGS_MASTER.md` - Master standings calculation system
- `docs/B_STANDINGS_RULES.md` - Optimist B specific rules
- `docs/STANDINGS_CALCULATION_STEPS.md` - Step-by-step calculation process

---

## Technical Implementation

- **API Endpoint:** `/api/member/{sa_id}/nationals-rank` in `api.py`
- **Frontend:** `search.html` - Main page and popup modal
- **Database Tables:** `regattas`, `results`, `regatta_blocks`, `standing_list`, `master_list`
- **Key Functions:**
  - `api_member_nationals_rank()` - Main endpoint logic
  - `showSailorStats()` - Popup modal display
  - Standings fetch in main page profile rendering

---

**Last Updated:** December 30, 2025

