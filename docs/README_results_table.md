# RESULTS Table - GPT Rules & Data Structure

## Purpose
Stores individual race results with proper scoring, discards, and sailor information.

## Table Structure
```sql
CREATE TABLE results (
    result_id SERIAL PRIMARY KEY,
    regatta_id TEXT NOT NULL REFERENCES regattas(regatta_id),
    block_id TEXT NOT NULL REFERENCES regatta_blocks(block_id),
    rank INTEGER,                              -- Final position (1, 2, 3, etc.)
    fleet_label TEXT,                          -- Fleet designation (A, B, Gold, etc.)
    class_original TEXT,                       -- Class as printed (420, Optimist, etc.)
    class_canonical TEXT,                      -- Standardized class name
    sail_number TEXT,                          -- Sail number
    bow_no TEXT,                              -- Bow number (if applicable)
    jib_no TEXT,                              -- Jib number (if applicable)  
    hull_no TEXT,                             -- Hull number (if applicable)
    boat_name TEXT,                           -- Boat name
    club_raw TEXT,                            -- Club as printed in results
    club_id INTEGER REFERENCES clubs(club_id), -- Mapped club
    helm_name TEXT,                           -- Helm name
    helm_sa_sailing_id TEXT,                  -- Official SA Sailing ID
    crew_name TEXT,                           -- Crew name
    crew_sa_sailing_id TEXT,                  -- Official SA Sailing ID
    races_sailed INTEGER,                     -- Number of races completed
    discard_count INTEGER,                    -- Number of discards allowed
    race_scores JSONB,                        -- Race scores as JSONB (see race_scores_storage.md)
    total_points_raw NUMERIC,                 -- Sum of all race scores
    nett_points_raw NUMERIC,                  -- Total minus discards
    validation_flag TEXT,                     -- Validation status
    source_row_text TEXT,                     -- Original row text
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Data Rules (from GPT instructions)

### Row Order (CRITICAL - NEVER CHANGE)
1. **Row 1**: Event row (class info) - NOT stored in results table
2. **Row 2**: 1st place entrant  
3. **Row 3**: 2nd place entrant
4. **Row 4**: 3rd place entrant
5. **Row 5**: 4th place entrant
6. **Row 6**: 5th place entrant
7. **Row 7**: 6th place entrant
8. **Row 8**: 7th place entrant

**NEVER DELETE AND REINSERT ROWS - ONLY USE UPDATE STATEMENTS**

### SA Sailing ID Rules (CRITICAL)
1. **ALWAYS search database first** before adding any sailor
2. **Use exact database names** - if OCR differs, update to match database
3. **Search format**: `WHERE full_name ILIKE '%FirstName%' AND full_name ILIKE '%LastName%'`
4. **If not found**: Set `helm_sa_sailing_id = NULL` or `crew_sa_sailing_id = NULL`
5. **NEVER invent SA Sailing IDs**
6. **⚠️ HARD RULE - Name from SA ID Table**: When a result has an SA ID (`helm_sa_sailing_id` or `crew_sa_sailing_id`), **MUST use the exact name from `sas_id_personal` table**, NOT the name from the results sheet if they don't match exactly
   - Example: If results sheet says "JP Myburgh" but SA ID 4176 has "Jean-Pierre Myburgh" in database, use "Jean-Pierre Myburgh"
   - Example: If results sheet says "Stephen Proudfoot" but SA ID 11898 has "Stephan Proudfoot" in database, use "Stephan Proudfoot"
   - The SA ID table is the authoritative source for names when an SA ID is present

### Club Information Rules
1. **Lookup club abbreviation in database** to get correct `club_id`
2. **Preserve original club text** in `club_raw` field
3. **Map to standardized club** in `club_id` field
4. **Use province abbreviations only**: KZN, WC, GP, EC, FS, NC, MP, LP, NW

### Scoring Rules (from GPT checksum rules)
- **total_points_raw**: Sum of ALL race scores (including discarded)
- **nett_points_raw**: Total minus discarded scores
- **Validation**: `nett + total_discard = total`
- **DNC/DNS/OCS codes**: Treat as `entries + 1` points

### Data Integrity Rules
1. **NEVER use placeholders** - only real data or NULL
2. **NEVER hardcode values** - always extract from source
3. **ALWAYS verify SA Sailing IDs** in database
4. **ALWAYS calculate checksums** for total/nett validation
5. **ALWAYS identify discarded races** from parentheses
6. **ALWAYS lookup club information** in database
7. **NEVER modify penalty codes** in race_scores

## ⚠️ CRITICAL RULES - NEVER IGNORE

**BEFORE entering ANY results data**, you MUST:

1. ✅ **Read `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md`** - Complete column-by-column standards
2. ✅ **Read `docs/ALL_COLUMN_RULES_REFERENCE.md`** - Master reference for ALL columns
3. ✅ **Read `docs/RACE_SCORES_RULES.md`** - Complete race_scores format rules
4. ✅ **Run ALL pre-entry validation scripts** (see below)
5. ✅ **Check existing correct examples** in database

**Critical Column Rules** (See `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` for complete list):

**23 Mandatory Column Rules**:
1. `result_id`: Auto-increment, NEVER set manually
2. `regatta_id`: Single year format, lowercase, no quotes, FK to `regattas`
3. `block_id`: Colon separator, single year, no quotes, FK to `regatta_blocks`
4. `rank`: Integer (1, 2, 3, etc.)
5. `rank_ordinal`: **CRITICAL** - Must be spelled correctly: `"1st"`, `"2nd"`, `"3rd"`, `"4th"`, `"5th"`, etc.
   - **NEVER use**: `"2st"`, `"3st"`, `"4st"` (these are WRONG)
   - **Correct ordinals**: 
     - 1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th, 9th, 10th
     - 11th, 12th, 13th (special cases - always "th")
     - 21st, 22nd, 23rd, 24th, etc.
   - Use database function `integer_to_ordinal(rank)` or proper logic:
     - If rank % 100 in [11, 12, 13]: use "th"
     - Else if rank % 10 == 1: use "st"
     - Else if rank % 10 == 2: use "nd"
     - Else if rank % 10 == 3: use "rd"
     - Else: use "th"
5. `fleet_label`: Actual fleet name (NOT "Overall"), NEVER NULL/empty
6. `class_original`: Exact PDF copy (NOT for HTML)
7. `class_canonical`: ⚠️ **CRITICAL** - EXACT match to `classes.class_name`, ONLY field for HTML, NEVER NULL/empty
8. `sail_number`: Alphanumeric, no country prefixes, no spaces/quotes
9-23. See `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` for complete rules

**Pre-Entry Validation** (MANDATORY):
- [ ] Run `admin/tools/validate_new_data_pre_entry.sql` - Comprehensive pre-entry validation
- [ ] Run `admin/tools/validate_race_scores_pre_entry.sql` - Race scores format validation
- [ ] Verify `class_canonical` exists in `classes.class_name` (EXACT match)
- [ ] Verify `fleet_label` matches or authorized override
- [ ] Verify all SA IDs exist in `sas_id_personal` or assign temp IDs
- [ ] Verify `club_id` exists in `clubs` table
- [ ] Check single year format (no `2025-2025`)
- [ ] Check no quotes in text fields
- [ ] Verify race_scores format: `.0` decimals, parentheses for discards, scores with penalty codes

**Post-Entry Validation** (MANDATORY):
- [ ] Run `admin/tools/checksum_total_nett_points.sql` - Verify total/nett points calculations
- [ ] Run `admin/tools/validate_discard_brackets_compliance.sql` - Verify discard brackets and worst scores discarded
- [ ] Run `admin/tools/checksum_entry_counts.sql` - Verify entry counts per block
- [ ] Run `admin/tools/checksum_fleet_label.sql` - Verify fleet_label consistency
- [ ] Run `admin/tools/validate_class_canonical.sql` - Verify `class_canonical` matches `classes.class_name`
- [ ] Run `admin/tools/validate_club_raw.sql` - Verify club mappings
- [ ] Verify `rank_ordinal` is correctly spelled (`"1st"`, `"2nd"`, `"3rd"`, `"4th"`, NOT `"2st"`, `"3st"`, etc.)
- [ ] Verify `fleet_label` and `class_canonical` are NEVER NULL/empty
- [ ] Verify all discards have parentheses: `"(11.0)"` not `"-11.0"` or unbracketed
- [ ] Verify all penalty codes have scores: `"10.0 DNS"` not `"DNS"`
- [ ] Verify all scores use `.0` format: `"5.0"` not `"5"`
- [ ] Check Appendix A discard rule: Highest discard first, tie-break by earliest race

**Complete Documentation**: 
- `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` - **READ THIS FIRST** - Complete column-by-column rules
- `docs/RACE_SCORES_RULES.md` - Complete race_scores format rules
- `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` - Pre-entry validation checklist
- `docs/ALL_COLUMN_RULES_REFERENCE.md` - Master reference for all columns

## Related Tables
- `regattas` - Regatta event information
- `regatta_blocks` - Fleet/class blocks
- `clubs` - Club information
- `sailing_id` - Official SA Sailing IDs
- `temp_people` - Temporary sailor records

## Example Data
```sql
INSERT INTO results (regatta_id, block_id, rank, class_original, sail_number, club_raw, helm_name, crew_name, race_scores, total_points_raw, nett_points_raw) VALUES
('359-2025-zvyc-southern-charter-cape-classic', '359-2025-zvyc-southern-charter-cape-classic:420', 1, '420', '1365', 'HMYC', 'Hayden Miller', 'Megan Miller', '{"R1":"1.0","R2":"(2.0)","R3":"1.0","R4":"2.0","R5":"2.0","R6":"1.0","R7":"1.0","R8":"1.0"}', 11.0, 9.0);
```


**Critical Column Rules** (See `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` for complete list):

**23 Mandatory Column Rules**:
1. `result_id`: Auto-increment, NEVER set manually
2. `regatta_id`: Single year format, lowercase, no quotes, FK to `regattas`
3. `block_id`: Colon separator, single year, no quotes, FK to `regatta_blocks`
4. `rank`: Integer (1, 2, 3, etc.)
5. `rank_ordinal`: **CRITICAL** - Must be spelled correctly: `"1st"`, `"2nd"`, `"3rd"`, `"4th"`, `"5th"`, etc.
   - **NEVER use**: `"2st"`, `"3st"`, `"4st"` (these are WRONG)
   - **Correct ordinals**: 
     - 1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th, 9th, 10th
     - 11th, 12th, 13th (special cases - always "th")
     - 21st, 22nd, 23rd, 24th, etc.
   - Use database function `integer_to_ordinal(rank)` or proper logic:
     - If rank % 100 in [11, 12, 13]: use "th"
     - Else if rank % 10 == 1: use "st"
     - Else if rank % 10 == 2: use "nd"
     - Else if rank % 10 == 3: use "rd"
     - Else: use "th"
5. `fleet_label`: Actual fleet name (NOT "Overall"), NEVER NULL/empty
6. `class_original`: Exact PDF copy (NOT for HTML)
7. `class_canonical`: ⚠️ **CRITICAL** - EXACT match to `classes.class_name`, ONLY field for HTML, NEVER NULL/empty
8. `sail_number`: Alphanumeric, no country prefixes, no spaces/quotes
9-23. See `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` for complete rules

**Pre-Entry Validation** (MANDATORY):
- [ ] Run `admin/tools/validate_new_data_pre_entry.sql` - Comprehensive pre-entry validation
- [ ] Run `admin/tools/validate_race_scores_pre_entry.sql` - Race scores format validation
- [ ] Verify `class_canonical` exists in `classes.class_name` (EXACT match)
- [ ] Verify `fleet_label` matches or authorized override
- [ ] Verify all SA IDs exist in `sas_id_personal` or assign temp IDs
- [ ] Verify `club_id` exists in `clubs` table
- [ ] Check single year format (no `2025-2025`)
- [ ] Check no quotes in text fields
- [ ] Verify race_scores format: `.0` decimals, parentheses for discards, scores with penalty codes

**Post-Entry Validation** (MANDATORY):
- [ ] Run `admin/tools/checksum_total_nett_points.sql` - Verify total/nett points calculations
- [ ] Run `admin/tools/validate_discard_brackets_compliance.sql` - Verify discard brackets and worst scores discarded
- [ ] Run `admin/tools/checksum_entry_counts.sql` - Verify entry counts per block
- [ ] Run `admin/tools/checksum_fleet_label.sql` - Verify fleet_label consistency
- [ ] Run `admin/tools/validate_class_canonical.sql` - Verify `class_canonical` matches `classes.class_name`
- [ ] Run `admin/tools/validate_club_raw.sql` - Verify club mappings
- [ ] Verify `rank_ordinal` is correctly spelled (`"1st"`, `"2nd"`, `"3rd"`, `"4th"`, NOT `"2st"`, `"3st"`, etc.)
- [ ] Verify `fleet_label` and `class_canonical` are NEVER NULL/empty
- [ ] Verify all discards have parentheses: `"(11.0)"` not `"-11.0"` or unbracketed
- [ ] Verify all penalty codes have scores: `"10.0 DNS"` not `"DNS"`
- [ ] Verify all scores use `.0` format: `"5.0"` not `"5"`
- [ ] Check Appendix A discard rule: Highest discard first, tie-break by earliest race

**Complete Documentation**: 
- `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` - **READ THIS FIRST** - Complete column-by-column rules
- `docs/RACE_SCORES_RULES.md` - Complete race_scores format rules
- `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` - Pre-entry validation checklist
- `docs/ALL_COLUMN_RULES_REFERENCE.md` - Master reference for all columns

## Related Tables
- `regattas` - Regatta event information
- `regatta_blocks` - Fleet/class blocks
- `clubs` - Club information
- `sailing_id` - Official SA Sailing IDs
- `temp_people` - Temporary sailor records

## Example Data
```sql
INSERT INTO results (regatta_id, block_id, rank, class_original, sail_number, club_raw, helm_name, crew_name, race_scores, total_points_raw, nett_points_raw) VALUES
('359-2025-zvyc-southern-charter-cape-classic', '359-2025-zvyc-southern-charter-cape-classic:420', 1, '420', '1365', 'HMYC', 'Hayden Miller', 'Megan Miller', '{"R1":"1.0","R2":"(2.0)","R3":"1.0","R4":"2.0","R5":"2.0","R6":"1.0","R7":"1.0","R8":"1.0"}', 11.0, 9.0);
```
