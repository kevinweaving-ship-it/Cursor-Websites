# Regatta Results Management System - README

## Overview
The Regatta Results Management System is a web-based application that displays sailing regatta results dynamically from a PostgreSQL database. It supports multiple fleets, classes, and implements a sophisticated discard system for fair competition scoring.

## Database Structure: `app.regatta_359_results`

### Key Data Types
- **info_type**: Determines row purpose
  - `'Entrant'` = Competitor data rows
  - `'TEMP_SPACE'` = Temporary/spacing rows (not displayed)

### Core Competitor Fields
- **regatta_no**: Regatta identifier (e.g., 359)
- **rank_position**: Final ranking (1st, 2nd, 3rd, etc.)
- **fleet**: Fleet designation (Dabchick, ILCA 4, Mirror, etc.)
- **class**: Boat class (Dabchick, LASER 4.7/ILCA 4, MIRROR (D/H), etc.)
- **sail_no**: Sail number
- **club**: Sailing club abbreviation (SBYC, HYC, ZVYC, IZV)
- **helm_name**: Skipper's name
- **helm_sas_id**: Skipper's SAS ID (unique identifier)
- **crew_name**: Crew member's name (for double-handed boats)
- **crew_sas_id**: Crew's SAS ID

### Race Scoring System
- **race_1_score** through **race_30_score**: Individual race scores
- **race_1_lps_code** through **race_30_lps_code**: Penalty codes (DNC, DNS, OCS, etc.)
- **total**: Sum of all race scores (before discards)
- **nett**: Final score after discards are applied

### Discard System
The system implements a progressive discard system:

#### Discard Rules
- **After 5 races**: 1 discard allowed
- **After 10 races**: 2 discards allowed
- **After 15 races**: 3 discards allowed
- And so on...

#### Discard Columns
- **discard_1_r_no**: Race number with worst score (1st discard)
- **discard_2_r_no**: Race number with 2nd worst score (2nd discard)
- **discard_3_r_no** through **discard_6_r_no**: Additional discards

#### Discard Logic
1. System identifies worst race score for each competitor
2. Stores the race number in `discard_1_r_no`
3. For multiple discards, ranks races from worst to least worst
4. Discarded races are visually highlighted in red on the web interface

#### Discard Display Rule
**ALL discarded scores must be displayed in brackets** regardless of penalty codes:
- **With penalty code**: `(6) DNC`, `(6) OCS`
- **Without penalty code**: `(2)` (not just `2`)
- **Rule**: Brackets indicate discard status, not penalty codes

## Database Scoring Rules and Validation

### Race Score Rules
**CRITICAL RULE**: No two sailors can have the same position/score in the same race unless one has a penalty code.

**Validation Requirements**:
- **Same Race, Different Sailors**: Cannot both have score = 1, 2, 3, etc. unless one has penalty code (DNC, OCS, DNG)
- **Penalty Codes**: Allow multiple sailors to have same score (e.g., multiple DNC = 6)
- **Unique Positions**: Each finishing position must be unique per race

**Example Valid Race**:
- Sailor A: 1 (first place)
- Sailor B: 2 (second place) 
- Sailor C: 6 DNC (did not compete)
- Sailor D: 6 DNC (did not compete)

**Example Invalid Race**:
- Sailor A: 1 (first place)
- Sailor B: 1 (first place) ← VIOLATION: Two sailors cannot both be 1st

### Total and Nett Calculation Rules

**Total Column Rule**:
- **Formula**: Total = Sum of ALL race scores (race_1_score + race_2_score + ... + race_8_score)
- **Validation**: Total must equal sum of individual race scores
- **Database**: `total` column must be calculated from race scores, not manually entered

**Nett Column Rule**:
- **Formula**: Nett = Total - Discarded Race Scores
- **Discard System**: 1 discard after 5 races, 2 discards after 10 races, etc.
- **Validation**: Nett must equal Total minus worst race score(s)
- **Database**: `nett` column must be calculated from Total and discard logic

**Checksum Validation**:
- **Total**: Must equal sum of all race_X_score columns
- **Nett**: Must equal Total minus discarded race scores
- **Discard**: `discard_1_r_no` must point to race with worst score
- **No Manual Entry**: Total and Nett must be calculated, not manually entered into database

### Data Integrity Rules

**Database Table Validation**:
1. **Race Scores**: All race_X_score columns must have valid numeric values
2. **Total Calculation**: `total` = sum(race_1_score to race_8_score)
3. **Nett Calculation**: `nett` = total - discarded_scores
4. **Discard Assignment**: `discard_1_r_no` must identify race with worst score
5. **Position Uniqueness**: No duplicate positions in same race without penalty codes

## Example Data Analysis

### Sample Competitors (First 7 Rows):

1. **Sean Kavanagh (1st - Dabchick)**
   - Scores: 1,1,1,1,1,1,1,1 (perfect scores)
   - Total: 8.0, Nett: 7.0 (1 discard applied)
   - No worst race to discard (all scores equal)

2. **Thomas Henshilwood (4th - Dabchick)**
   - Scores: 2,2,2,6,6,6,6,6
   - Total: 36.0, Nett: 30.0 (6.0 discarded)
   - Worst scores are 6.0 (multiple races)

3. **Joshua Keytel (1st - ILCA 4)**
   - Scores: 2,1,1,1,1,1,1,1
   - Total: 9.0, Nett: 7.0 (2.0 discarded)
   - Worst score is 2.0 in Race 1

4. **Jens Dugas (2nd - ILCA 4)**
   - Scores: 6,2,2,2,2,2,2,6
   - Total: 24.0, Nett: 18.0 (6.0 discarded)
   - Worst scores are 6.0 in Races 1 & 8

5. **Athenkosi Mahlumba (2nd - Mirror)**
   - Scores: 3,2,2,2,2,2,2,2
   - Total: 17.0, Nett: 14.0 (3.0 discarded)
   - Worst score is 3.0 in Race 1

## Fleet Organization
- **Fleet 1**: Primary fleet (filtered by `fleet_1 = true`)
- **Multiple Classes**: Each fleet can contain different boat classes
- **Single/Double Handed**: Support for both sailing configurations

## Web Interface Features
- Dynamic regatta name and club display
- Fleet-specific results tables
- Sequential column loading with delays
- Visual discard highlighting (red background)
- Race penalty codes displayed under scores
- Responsive design with modern UI

## API Endpoints
- `/api/regatta/{id}/name` - Regatta information
- `/api/regatta/{id}/results` - Complete results data
- `/api/regatta/{id}/fleet/{fleet_no}/class` - Fleet class data
- `/api/regatta/{id}/fleet/{fleet_no}/boat-names` - Boat names

## Technical Stack
- **Backend**: Python Flask API server
- **Database**: PostgreSQL with connection pooling
- **Frontend**: HTML/CSS/JavaScript
- **Deployment**: Local development server on port 8081

## Scoring Philosophy
The system ensures fair competition by:
1. Allowing competitors to discard their worst performances
2. Providing visual feedback on which races don't count
3. Supporting penalty codes for rule violations
4. Calculating both gross (total) and net (final) scores
5. Maintaining historical race data for analysis

This creates a robust, transparent scoring system that rewards consistent performance while allowing for the occasional poor race result to be excluded from final standings.

