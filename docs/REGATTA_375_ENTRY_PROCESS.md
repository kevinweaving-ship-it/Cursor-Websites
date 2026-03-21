# Regatta 375 Entry Process - Initial Entry and Update Routine

## Overview

This document details the process for adding and updating entrants for **Regatta 375 - SA Youth Nationals 2025** (Host: HYC, 14-19 December 2025). This process serves as a template for handling initial entry lists and subsequent updates for major regattas.

---

## Regatta Information

- **Regatta ID:** `375-2025-hyc-sa-youth-nationals`
- **Event Name:** SA Youth Nationals 2025
- **Host Club:** HYC (Hermanus Yacht Club)
- **Dates:** 14-19 December 2025
- **Status:** Final (when results are complete)

---

## Initial Entry Process

### Step 1: Data Preparation

1. **Receive Entry List**
   - Entry list is typically provided as tab-separated data
   - Columns include: Name, Class, Sail Number, Club, DOB, Email, etc.

2. **Parse and Validate Data**
   - Parse tab-separated entries
   - **CRITICAL: Normalize class names to match classes table EXACTLY:**
     - Query `classes` table to get proper class names
     - `Optimist A Fleet` / `Optimist A` → `Optimist A` (from classes table)
     - `Optimist B Fleet` / `Optimist B` → `Optimist B` (from classes table)
     - `ILCA 4` → `ILCA 4` (from classes table)
     - `ILCA 6` → `ILCA 6` (from classes table)
     - `Dabchick` → `Dabchick` (from classes table)
     - `RS Tera` → `RS Tera` (from classes table)
     - `Mirror` → `Mirror` (from classes table)
     - `Topper 5.3` → `Topper 5.3` (from classes table)
     - `Topaz` → `Topaz` (from classes table)
   - **NEVER use lowercase - always match classes.class_name exactly**
   - Extract and clean SA IDs (remove RSA/ZIM prefixes, question marks, etc.)
   - Parse dates (format: YYYY/MM/DD)

3. **Verify Class Totals**
   - Count sailors per class
   - Compare with organizer's expected totals
   - Report any discrepancies

### Step 2: SA ID Verification and Update

1. **Check SA IDs**
   - For each sailor, attempt to find SA ID in:
     - Known ID mappings (hardcoded for common cases)
     - Sail number column (if SA ID format)
     - Database lookup by name
   
2. **Update SA ID Records**
   - Update `sas_id_personal` table with:
     - Date of Birth (DOB) if provided
     - Sail numbers (if not already set)
     - Boat names (if provided)
   
3. **Report Issues**
   - List any sailors missing SA IDs
   - Flag any SA ID format issues
   - Note any data quality concerns

### Step 3: Create Regatta and Blocks

1. **Create/Verify Regatta Record**
   ```sql
   INSERT INTO regattas (regatta_id, event_name, start_date, end_date, result_status)
   VALUES ('375-2025-hyc-sa-youth-nationals', 'SA Youth Nationals 2025', '2025-12-15', '2025-12-20', 'Final')
   ON CONFLICT (regatta_id) DO NOTHING;
   ```

2. **Create Regatta Blocks for Each Class**
   - For each class with entries, create a `regatta_blocks` record
   - Default values (adjust as needed):
     - `races_sailed`: 12 (assumed, update when actual race count known)
     - `discard_count`: 2
     - `to_count`: 10
     - `entries_raced`: 0 (will be updated when results are entered)
     - `scoring_system`: 'Low Point'
   - `fleet_label` = Class name (e.g., "Optimist A Fleet", "Optimist B Fleet")

### Step 4: Add Entries to Results Table

For each entry in the list:

1. **Check for Existing Entry**
   - Query `results` table for existing entry by:
     - `regatta_id`
     - `helm_name`
     - `class_canonical`

2. **Insert New Entry**
   ```sql
   INSERT INTO results (
       regatta_id, block_id, class_canonical, class_original,
       helm_name, helm_sa_sailing_id, sail_number, club_raw,
       raced, result_status
   )
   VALUES (...)
   ```
   - `raced`: Set to `TRUE` (assumes all entries will race)
   - `result_status`: Set to `'Final'` (or appropriate status)
   - No race scores initially (will be added when results are available)

3. **Handle Double-Handed Classes**
   - For Mirror (and other double-handed classes):
     - Extract skipper and crew information
     - Set both `helm_sa_sailing_id` and `crew_sa_sailing_id` if available
     - Note: Crews may be entered separately in some cases

### Step 5: Verification

1. **Count Entries by Class**
   - Verify counts match expected totals
   - Report any discrepancies

2. **Check Data Quality**
   - Verify all SA IDs are valid
   - Check for duplicate entries
   - Validate class names are correct

---

## Update Routine

### When Updated Entry List is Provided

When an updated entry list is received (with additional sailors, corrected SA IDs, etc.):

### Step 1: Parse Updated List

1. **Load Updated Data**
   - Parse the new tab-separated list
   - Normalize class names (same as initial process)

2. **Compare with Existing Entries**
   - Query existing entries from `results` table for this regatta
   - Identify:
     - **New entries** (not in database)
     - **Existing entries** (already in database)
     - **Removed entries** (in database but not in new list - handle carefully)

### Step 2: Update SA IDs

For each sailor in the updated list:

1. **Check SA ID**
   - If SA ID is provided/updated in new list:
     - Update `sas_id_personal` table with new DOB, sail number, boat name
     - Update existing `results` entries for this sailor in this regatta:
       ```sql
       UPDATE results
       SET helm_sa_sailing_id = %s
       WHERE regatta_id = %s
         AND helm_name = %s
       ```

2. **Update Sail Numbers**
   - If sail number is provided/updated:
     ```sql
     UPDATE results
     SET sail_number = %s
     WHERE regatta_id = %s
       AND helm_sa_sailing_id = %s
     ```

### Step 3: Add New Entries

1. **Identify New Sailors**
   - Compare new list with existing entries
   - For each new sailor:
     - Follow Step 4 from Initial Entry Process
     - Add entry to `results` table

2. **Handle Class Changes**
   - If a sailor's class has changed:
     - Update `class_canonical` and `class_original` in `results`
     - Update `block_id` to point to correct class block
     - Note: This may require moving the entry to a different block

### Step 4: Update Fleet/Class Lists

1. **Regenerate Class Counts**
   - Query `results` table for current entry counts per class
   - Update `regatta_blocks.entries_raced` (or create new field for entry count)

2. **Update Master Lists (if applicable)**
   - For Optimist A and B fleets:
     - Re-run eligibility checks
     - Update master standings lists
     - Recalculate rankings if needed

3. **Update HTML Display**
   - Refresh regatta viewer pages
   - Update class tables with new entries
   - Ensure correct sorting and display

### Step 5: Verification

1. **Compare Totals**
   - Verify class totals match organizer's updated list
   - Report any discrepancies

2. **Data Quality Check**
   - Verify all new entries have SA IDs (or temp IDs)
   - Check for duplicates
   - Validate class assignments

---

## Final Scores and Major Standing Update

### When Regatta 375 Has Final Scores

When Regatta 375 results are finalized and scores are entered:

### Step 1: Verify Final Status

1. **Check Result Status**
   - Ensure `regattas.result_status = 'Final'`
   - Verify all race scores are entered
   - Confirm all calculations are complete

2. **Validate Scores**
   - Verify `nett_points_raw` and `total_points_raw` are calculated
   - Check `to_count` matches actual races counted
   - Validate discard logic

### Step 2: Update Main/Major Standing

**Regatta 375 becomes the new Main/Major Regatta for the season/year.**

1. **Identify as Main Regatta**
   - Regatta 375 is the most official ranking for the year
   - It qualifies as "Main Regatta" if:
     - It has 70%+ of the entries of the largest regatta in the last 12 months
     - It is the most recent major regatta
     - Results are final

2. **Recalculate Master Scores**
   - For all sailors who sailed in Regatta 375:
     - Master Score = `nett_points_raw / to_count` (from Regatta 375)
     - This replaces previous master scores from older regattas

3. **Update Rankings**
   - Recalculate all class rankings based on Regatta 375 results
   - For Optimist B fleet:
     - Regatta 375 becomes the new "master" regatta
     - All other regattas are compared against Regatta 375
     - Head-to-head results from Regatta 375 take precedence over older regattas

4. **Update Master Lists**
   - Rebuild master standings lists for all classes
   - Optimist A: Update master list based on Regatta 375
   - Optimist B: Rebuild master list with Regatta 375 as the control regatta
   - Other classes: Update rankings as appropriate

### Step 3: Documentation

1. **Update Process Documentation**
   - Document that Regatta 375 is now the Main Regatta
   - Note the date when final scores were entered
   - Record any changes to master lists

2. **Archive Previous Rankings**
   - Previous main regatta (e.g., Regatta 339) is now historical
   - Keep records for reference but mark as superseded

---

## Script Reference

The process is implemented in:
- **`add_regatta_375_entries.py`**: Initial entry and update script

### Key Functions

- `parse_date(date_str)`: Parse date string (YYYY/MM/DD format)
- `clean_sa_id(sa_id_str)`: Clean SA ID string (remove prefixes, question marks)
- `normalize_class(class_name)`: Normalize class names to canonical format

### Database Tables Used

- `regattas`: Regatta metadata
- `regatta_blocks`: Class/fleet blocks for each regatta
- `results`: Individual sailor entries and results
- `sas_id_personal`: SA ID personal information (DOB, etc.)

---

## Important Notes

1. **Entry vs. Results**
   - Initial process adds **entries only** (no race scores)
   - Race scores are added separately when results are available
   - `raced = TRUE` assumes all entries will race (update if sailor does not race)

2. **SA ID Priority**
   - Use SA ID from `sas_id_personal` table when available
   - If no SA ID, use `helm_temp_id` (temporary ID)
   - Update SA IDs when they become available

3. **Class Normalization - CRITICAL RULE**
   - **MUST MATCH CLASSES TABLE EXACTLY** - Use proper capitalization from `classes.class_name`
   - **DO NOT USE LOWERCASE** - The classes table has proper capitalization:
     - `Optimist A` (NOT "optimist a")
     - `Optimist B` (NOT "optimist b")
     - `Dabchick` (NOT "dabchick")
     - `ILCA 4` (NOT "ilca 4")
     - `ILCA 6` (NOT "ilca 6")
     - `RS Tera` (NOT "rs tera")
     - `Mirror` (NOT "mirror")
     - `Topaz` (NOT "topaz")
     - `Topper 5.3` (NOT "topper 5.3")
   - **ALWAYS CHECK CLASSES TABLE FIRST** before setting `class_canonical`
   - `fleet_label` in `regatta_blocks` uses display name (e.g., "Optimist A Fleet")
   - **This rule is frequently violated - always verify against classes table**

4. **Double-Handed Classes**
   - Mirror entries include both skipper and crew
   - Both should have SA IDs if available
   - Crew may be entered separately in some cases

5. **Update Frequency**
   - Run update routine whenever new entry list is provided
   - Always verify totals match organizer's list
   - Report any discrepancies immediately

6. **Final Scores**
   - Only mark regatta as "Final" when all results are complete
   - Once final, Regatta 375 becomes the authoritative ranking source
   - All future rankings reference Regatta 375 as the main regatta

---

## Example Workflow

### Initial Entry (Day 1)
1. Receive entry list from organizers
2. Parse and validate data
3. Check SA IDs, update where needed
4. Create regatta and blocks
5. Add all entries to `results` table
6. Verify totals match organizer's list
7. Report any issues

### Update (Day 3 - Additional Entries)
1. Receive updated entry list (5 new sailors added)
2. Parse updated list
3. Compare with existing entries
4. Update SA IDs for existing sailors (if changed)
5. Add 5 new entries to `results` table
6. Update class counts
7. Refresh HTML display
8. Verify totals

### Final Scores (After Regatta)
1. Enter all race scores
2. Calculate final positions
3. Mark regatta as "Final"
4. Recalculate master scores using Regatta 375
5. Update all master lists
6. Regatta 375 is now the Main Regatta for the season

---

## Troubleshooting

### Issue: SA ID Not Found
- **Solution**: Check `sas_id_personal` table by name
- If still not found, use `temp_people` table to create temporary ID
- Update SA ID later when available

### Issue: Class Total Mismatch
- **Solution**: 
  - Verify class name normalization
  - Check for entries in wrong class
  - Verify organizer's count includes/excludes certain categories

### Issue: Duplicate Entries
- **Solution**: 
  - Check `results` table for existing entries before inserting
  - Use unique constraint on `(regatta_id, helm_name, class_canonical)`

### Issue: Missing Sail Numbers
- **Solution**: 
  - Some sailors may not have sail numbers yet
  - Leave as NULL, update when available
  - Not critical for initial entry

---

## Related Documentation

- `B_FLEET_MASTER_STANDINGS_PROCESS.md`: Optimist B fleet ranking methodology
- `README_results_table.md`: Results table structure and rules
- `README_regatta_blocks_table.md`: Regatta blocks structure
- `SA_ID_PRIORITY_RULES.md`: SA ID matching and priority rules

---

**Last Updated:** 2025-01-XX  
**Regatta:** 375 - SA Youth Nationals 2025  
**Status:** Active (Entry Process)

