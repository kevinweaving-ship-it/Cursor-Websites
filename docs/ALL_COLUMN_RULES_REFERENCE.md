# Complete Column Rules Reference - All Tables

**CRITICAL**: This document is the **master reference** for ALL column rules across ALL tables. Every rule must be checked during data entry to ensure compliance and consistency.

**Last Updated**: 2025-01-XX (after comprehensive audit)

---

## Purpose

This document consolidates **ALL** column-by-column rules that have been audited and standardized. Before entering ANY new data, you MUST:

1. **Read this document** for the relevant table/columns
2. **Run validation scripts** before entry (see Pre-Entry Validation below)
3. **Verify compliance** after entry using checksum scripts

**Data corruption prevention**: These rules are **MANDATORY** and must be enforced at data entry time, not fixed later.

---

## Pre-Entry Validation Process

**BEFORE** inserting/updating any data, run:

1. **Format Validation**: `admin/tools/validate_race_scores_pre_entry.sql` (for race_scores)
2. **Foreign Key Validation**: Verify all FK values exist in referenced tables
3. **Format Checks**: Use validation queries from column rules below

**If ANY validation fails**: **DO NOT INSERT DATA**. Fix source data first.

---

## Table: `public.results`

### Complete Column Rules

**Primary Reference**: `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` - Complete column-by-column standards

**Quick Summary of Critical Rules**:

1. **`result_id`**: Auto-increment, NEVER set manually
2. **`regatta_id`**: Single year only (`342-2025-...` NOT `342-2025-2025-...`), lowercase, no quotes
3. **`block_id`**: Format `{regatta_id}:{fleet-slug}`, colon separator, no quotes, single year
4. **`rank`**: Ordinal string format (`"1st"`, `"2nd"`, `"3rd"`), NOT integer
5. **`fleet_label`**: Actual fleet name (NOT "Overall"), must match `classes.class_name` or authorized override
6. **`class_original`**: Exact PDF copy, NOT validated, NOT for HTML
7. **`class_canonical`**: Validated against `classes.class_name`, EXACT match required, **ONLY field for HTML**
8. **`sail_number`**: Alphanumeric, no country prefixes (remove "RSA ", "SA "), no spaces, no quotes
9. **`bow_no`, `jib_no`, `hull_no`**: Alphanumeric, trimmed, no spaces/quotes
10. **`boat_name`**: Preserve as entered, trimmed, NULL not empty string
11. **`club_raw`**: Uppercase, trimmed, no empty string (use NULL), must map to `club_id`
12. **`club_id`**: FK to `clubs.club_id`, never NULL if `club_raw` exists
13. **`helm_sa_sailing_id`**: SA-ID or NULL (use temp ID if no SA-ID)
14. **`helm_temp_id`**: Format `"TMP:4"` (colon and space), not `"T4"` or `"TMP4"`
15. **`crew_sa_sailing_id`**, **`crew_temp_id`**: Same rules as helm
16. **`races_sailed`**: INTEGER, NOT NULL, must match actual race count in `race_scores` JSONB
17. **`discard_count`**: INTEGER, NOT NULL, must match actual discard count (bracketed scores) in `race_scores`
18. **`ranks_sailed`**: INTEGER, total entries in fleet/class for this row
19. **`race_scores`**: JSONB format - see `docs/RACE_SCORES_RULES.md` for complete rules
20. **`total_points_raw`**: Numeric with `.0` format, must match sum of all race scores - see `admin/audit/RESULTS_TOTAL_POINTS_RAW_RULES.md`
21. **`nett_points_raw`**: Numeric with `.0` format, must match `total_points_raw - discard_sum` - see `admin/audit/RESULTS_NETT_POINTS_RAW_RULES.md`

### Race Scores Format (CRITICAL)

**Primary Reference**: `docs/RACE_SCORES_RULES.md` - Complete format specifications

**Pre-Entry Validation**: `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` - **MANDATORY** validation rules

**Quick Rules**:
- Keys: `R1`, `R2`, `R3`, etc. (uppercase R)
- Numeric scores: `"1.0"`, `"5.0"`, `"13.0"` (MUST have `.0`)
- Discarded scores: `"(11.0)"`, `"(6.0)"` (parentheses, MUST have `.0` inside)
- Penalty codes: `"14.0 DNC"`, `"7.0 DNS"` (score + space + code, MUST have score)
- Discarded penalties: `"(14.0 DNC)"`, `"(7.0 DNS)"` (parentheses + score + space + code)

**Validation Script**: `admin/tools/validate_race_scores_pre_entry.sql` - Run BEFORE data entry

---

## Table: `public.regattas`

**Primary Reference**: `docs/DATA_FORMAT_SPECIFICATIONS.md` - Section "Table: public.regattas"

### Critical Rules

1. **`regatta_id`**: Single year only, lowercase, hyphen-separated, no quotes
2. **`event_name`**: Must NOT start with year (HTML displays as `year + event_name`)
3. **`year`**: 4-digit integer
4. **`host_club_id`**, **`host_club_code`**, **`host_club_name`**: ALL THREE required

---

## Table: `public.regatta_blocks`

**Primary Reference**: `docs/DATA_FORMAT_SPECIFICATIONS.md` - Section "Table: public.regatta_blocks"

### Critical Rules

1. **`block_id`**: Format `{regatta_id}:{fleet-slug}`, colon separator, single year in regatta_id
2. **`regatta_id`**: FK to `regattas.regatta_id`, single year only
3. **`fleet_label`**: Must match `results.fleet_label` for same block
4. **`races_sailed`**: Must match actual race count, NOT NULL
5. **`discard_count`**: Must match per-sailor discard count (NOT sum across all sailors), NOT NULL

---

## Table: `public.classes`

**Primary Reference**: `docs/DATA_FORMAT_SPECIFICATIONS.md` - Section "Table: public.classes"

### Critical Rules

1. **`class_name`**: **AUTHORITATIVE SOURCE** - All `results.class_canonical` must match exactly (case-sensitive)
2. **`crew_policy`**: Valid values: `'single'`, `'double'`, `'Crewed'`, or `NULL`
3. **Parent classes** (`Ilca/Laser`, `Optimist`) always `'single'`
4. **`_sailors_in_class`**: Count of unique sailors per class - **MUST BE UPDATED after every results import**

**See**: 
- `docs/CLASSES_TABLE_AUTHORITATIVE_SOURCE.md` - Complete explanation
- `docs/SAILORS_IN_CLASS_RULES.md` - Complete `_sailors_in_class` rules and update process

---

## Table: `public.clubs`

**Primary Reference**: `docs/DATA_FORMAT_SPECIFICATIONS.md` - Section "Table: public.clubs"

### Critical Rules

1. **`club_id`**: PK, used by `results.club_id`
2. **`club_abbrev`**: Uppercase, 3-4 letters, used for display
3. **`club_fullname`**: Full club name
4. **Invalid club**: Use `UNK` club_id

---

## Table: `public.sas_id_personal`

**Primary Reference**: `docs/DATA_FORMAT_SPECIFICATIONS.md` - Section "Table: public.sas_id_personal"

### Critical Rules

1. **`sa_sailing_id`**: PK, TEXT format (may contain letters)
2. **`primary_sailno`**: Sail number, no country prefixes
3. **Mismatch with `results.sail_number`**: Legitimate if sailor uses different sail number for specific regatta

---

## Validation Scripts

### Pre-Entry (Run BEFORE Data Entry)

1. **All Rules**: `admin/tools/validate_new_data_pre_entry.sql` - **COMPREHENSIVE** - Validates all column rules
2. **Race Scores Format**: `admin/tools/validate_race_scores_pre_entry.sql` - Specific race_scores format validation

### Post-Entry (Run AFTER Data Entry)

1. **Discard Brackets Compliance**: `admin/tools/validate_discard_brackets_compliance.sql` - **CRITICAL** - Ensures discard_count matches bracketed scores and worst scores are discarded
2. **Entry Counts**: `admin/tools/checksum_entry_counts.sql` - Entry count validation
3. **Fleet Labels**: `admin/tools/checksum_fleet_label.sql` - Fleet label validation
4. **Class Canonical**: `admin/tools/validate_class_canonical.sql` - Class canonical validation
5. **Total/Nett Points**: `admin/tools/checksum_total_nett_points.sql` - Total/nett points checksum

---

## Checksum Scripts (Run After Data Entry)

1. **Total/Nett Points**: `admin/tools/checksum_total_nett_points.sql`
2. **Entry Counts**: `admin/tools/checksum_entry_counts.sql`
3. **Fleet Labels**: `admin/tools/checksum_fleet_label.sql`
4. **Discard Count**: Validated in total/nett checksum

---

## Data Entry Checklist

**BEFORE entry**:
- [ ] Read column rules from this document
- [ ] Run pre-entry validation scripts
- [ ] Verify all FK values exist
- [ ] Check format compliance (single year, no quotes, etc.)

**DURING entry**:
- [ ] Follow INSERT statement templates
- [ ] Ensure `class_canonical` matches `classes.class_name` exactly
- [ ] Ensure `fleet_label` matches PDF (or authorized override)
- [ ] Ensure penalty codes have scores
- [ ] Ensure discards use parentheses
- [ ] Ensure all scores have `.0` format
- [ ] Ensure `discard_count` matches number of bracketed scores
- [ ] Ensure worst scores are discarded (per block discard rule)

**AFTER entry**:
- [ ] Run `admin/tools/validate_discard_brackets_compliance.sql` - **CRITICAL** - Check discard brackets
- [ ] Run `admin/tools/update_sailors_in_class.sql` - **MANDATORY** - Update sailor counts for all classes
- [ ] Run checksum validation scripts
- [ ] Fix any mismatches
- [ ] Verify HTML display (no broken formatting)

---

## Related Documents

- **`docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md`** - Complete `public.results` standards
- **`docs/DATA_FORMAT_SPECIFICATIONS.md`** - Format specs for all tables
- **`docs/DATA_ENTRY_GUIDELINES.md`** - Quick reference checklist
- **`docs/RACE_SCORES_RULES.md`** - Complete race_scores format rules
- **`docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md`** - Mandatory validation rules
- **`docs/CLASS_CANONICAL_VALIDATION_RULES.md`** - class_canonical validation
- **`docs/FLEET_LABEL_CHECKSUM_RULES.md`** - Fleet label validation

---

**Remember**: Data corruption happens when rules are ignored. Enforce these rules at entry time, not later.


**CRITICAL**: This document is the **master reference** for ALL column rules across ALL tables. Every rule must be checked during data entry to ensure compliance and consistency.

**Last Updated**: 2025-01-XX (after comprehensive audit)

---

## Purpose

This document consolidates **ALL** column-by-column rules that have been audited and standardized. Before entering ANY new data, you MUST:

1. **Read this document** for the relevant table/columns
2. **Run validation scripts** before entry (see Pre-Entry Validation below)
3. **Verify compliance** after entry using checksum scripts

**Data corruption prevention**: These rules are **MANDATORY** and must be enforced at data entry time, not fixed later.

---

## Pre-Entry Validation Process

**BEFORE** inserting/updating any data, run:

1. **Format Validation**: `admin/tools/validate_race_scores_pre_entry.sql` (for race_scores)
2. **Foreign Key Validation**: Verify all FK values exist in referenced tables
3. **Format Checks**: Use validation queries from column rules below

**If ANY validation fails**: **DO NOT INSERT DATA**. Fix source data first.

---

## Table: `public.results`

### Complete Column Rules

**Primary Reference**: `docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md` - Complete column-by-column standards

**Quick Summary of Critical Rules**:

1. **`result_id`**: Auto-increment, NEVER set manually
2. **`regatta_id`**: Single year only (`342-2025-...` NOT `342-2025-2025-...`), lowercase, no quotes
3. **`block_id`**: Format `{regatta_id}:{fleet-slug}`, colon separator, no quotes, single year
4. **`rank`**: Ordinal string format (`"1st"`, `"2nd"`, `"3rd"`), NOT integer
5. **`fleet_label`**: Actual fleet name (NOT "Overall"), must match `classes.class_name` or authorized override
6. **`class_original`**: Exact PDF copy, NOT validated, NOT for HTML
7. **`class_canonical`**: Validated against `classes.class_name`, EXACT match required, **ONLY field for HTML**
8. **`sail_number`**: Alphanumeric, no country prefixes (remove "RSA ", "SA "), no spaces, no quotes
9. **`bow_no`, `jib_no`, `hull_no`**: Alphanumeric, trimmed, no spaces/quotes
10. **`boat_name`**: Preserve as entered, trimmed, NULL not empty string
11. **`club_raw`**: Uppercase, trimmed, no empty string (use NULL), must map to `club_id`
12. **`club_id`**: FK to `clubs.club_id`, never NULL if `club_raw` exists
13. **`helm_sa_sailing_id`**: SA-ID or NULL (use temp ID if no SA-ID)
14. **`helm_temp_id`**: Format `"TMP:4"` (colon and space), not `"T4"` or `"TMP4"`
15. **`crew_sa_sailing_id`**, **`crew_temp_id`**: Same rules as helm
16. **`races_sailed`**: INTEGER, NOT NULL, must match actual race count in `race_scores` JSONB
17. **`discard_count`**: INTEGER, NOT NULL, must match actual discard count (bracketed scores) in `race_scores`
18. **`ranks_sailed`**: INTEGER, total entries in fleet/class for this row
19. **`race_scores`**: JSONB format - see `docs/RACE_SCORES_RULES.md` for complete rules
20. **`total_points_raw`**: Numeric with `.0` format, must match sum of all race scores - see `admin/audit/RESULTS_TOTAL_POINTS_RAW_RULES.md`
21. **`nett_points_raw`**: Numeric with `.0` format, must match `total_points_raw - discard_sum` - see `admin/audit/RESULTS_NETT_POINTS_RAW_RULES.md`

### Race Scores Format (CRITICAL)

**Primary Reference**: `docs/RACE_SCORES_RULES.md` - Complete format specifications

**Pre-Entry Validation**: `docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md` - **MANDATORY** validation rules

**Quick Rules**:
- Keys: `R1`, `R2`, `R3`, etc. (uppercase R)
- Numeric scores: `"1.0"`, `"5.0"`, `"13.0"` (MUST have `.0`)
- Discarded scores: `"(11.0)"`, `"(6.0)"` (parentheses, MUST have `.0` inside)
- Penalty codes: `"14.0 DNC"`, `"7.0 DNS"` (score + space + code, MUST have score)
- Discarded penalties: `"(14.0 DNC)"`, `"(7.0 DNS)"` (parentheses + score + space + code)

**Validation Script**: `admin/tools/validate_race_scores_pre_entry.sql` - Run BEFORE data entry

---

## Table: `public.regattas`

**Primary Reference**: `docs/DATA_FORMAT_SPECIFICATIONS.md` - Section "Table: public.regattas"

### Critical Rules

1. **`regatta_id`**: Single year only, lowercase, hyphen-separated, no quotes
2. **`event_name`**: Must NOT start with year (HTML displays as `year + event_name`)
3. **`year`**: 4-digit integer
4. **`host_club_id`**, **`host_club_code`**, **`host_club_name`**: ALL THREE required

---

## Table: `public.regatta_blocks`

**Primary Reference**: `docs/DATA_FORMAT_SPECIFICATIONS.md` - Section "Table: public.regatta_blocks"

### Critical Rules

1. **`block_id`**: Format `{regatta_id}:{fleet-slug}`, colon separator, single year in regatta_id
2. **`regatta_id`**: FK to `regattas.regatta_id`, single year only
3. **`fleet_label`**: Must match `results.fleet_label` for same block
4. **`races_sailed`**: Must match actual race count, NOT NULL
5. **`discard_count`**: Must match per-sailor discard count (NOT sum across all sailors), NOT NULL

---

## Table: `public.classes`

**Primary Reference**: `docs/DATA_FORMAT_SPECIFICATIONS.md` - Section "Table: public.classes"

### Critical Rules

1. **`class_name`**: **AUTHORITATIVE SOURCE** - All `results.class_canonical` must match exactly (case-sensitive)
2. **`crew_policy`**: Valid values: `'single'`, `'double'`, `'Crewed'`, or `NULL`
3. **Parent classes** (`Ilca/Laser`, `Optimist`) always `'single'`
4. **`_sailors_in_class`**: Count of unique sailors per class - **MUST BE UPDATED after every results import**

**See**: 
- `docs/CLASSES_TABLE_AUTHORITATIVE_SOURCE.md` - Complete explanation
- `docs/SAILORS_IN_CLASS_RULES.md` - Complete `_sailors_in_class` rules and update process

---

## Table: `public.clubs`

**Primary Reference**: `docs/DATA_FORMAT_SPECIFICATIONS.md` - Section "Table: public.clubs"

### Critical Rules

1. **`club_id`**: PK, used by `results.club_id`
2. **`club_abbrev`**: Uppercase, 3-4 letters, used for display
3. **`club_fullname`**: Full club name
4. **Invalid club**: Use `UNK` club_id

---

## Table: `public.sas_id_personal`

**Primary Reference**: `docs/DATA_FORMAT_SPECIFICATIONS.md` - Section "Table: public.sas_id_personal"

### Critical Rules

1. **`sa_sailing_id`**: PK, TEXT format (may contain letters)
2. **`primary_sailno`**: Sail number, no country prefixes
3. **Mismatch with `results.sail_number`**: Legitimate if sailor uses different sail number for specific regatta

---

## Validation Scripts

### Pre-Entry (Run BEFORE Data Entry)

1. **All Rules**: `admin/tools/validate_new_data_pre_entry.sql` - **COMPREHENSIVE** - Validates all column rules
2. **Race Scores Format**: `admin/tools/validate_race_scores_pre_entry.sql` - Specific race_scores format validation

### Post-Entry (Run AFTER Data Entry)

1. **Discard Brackets Compliance**: `admin/tools/validate_discard_brackets_compliance.sql` - **CRITICAL** - Ensures discard_count matches bracketed scores and worst scores are discarded
2. **Entry Counts**: `admin/tools/checksum_entry_counts.sql` - Entry count validation
3. **Fleet Labels**: `admin/tools/checksum_fleet_label.sql` - Fleet label validation
4. **Class Canonical**: `admin/tools/validate_class_canonical.sql` - Class canonical validation
5. **Total/Nett Points**: `admin/tools/checksum_total_nett_points.sql` - Total/nett points checksum

---

## Checksum Scripts (Run After Data Entry)

1. **Total/Nett Points**: `admin/tools/checksum_total_nett_points.sql`
2. **Entry Counts**: `admin/tools/checksum_entry_counts.sql`
3. **Fleet Labels**: `admin/tools/checksum_fleet_label.sql`
4. **Discard Count**: Validated in total/nett checksum

---

## Data Entry Checklist

**BEFORE entry**:
- [ ] Read column rules from this document
- [ ] Run pre-entry validation scripts
- [ ] Verify all FK values exist
- [ ] Check format compliance (single year, no quotes, etc.)

**DURING entry**:
- [ ] Follow INSERT statement templates
- [ ] Ensure `class_canonical` matches `classes.class_name` exactly
- [ ] Ensure `fleet_label` matches PDF (or authorized override)
- [ ] Ensure penalty codes have scores
- [ ] Ensure discards use parentheses
- [ ] Ensure all scores have `.0` format
- [ ] Ensure `discard_count` matches number of bracketed scores
- [ ] Ensure worst scores are discarded (per block discard rule)

**AFTER entry**:
- [ ] Run `admin/tools/validate_discard_brackets_compliance.sql` - **CRITICAL** - Check discard brackets
- [ ] Run `admin/tools/update_sailors_in_class.sql` - **MANDATORY** - Update sailor counts for all classes
- [ ] Run checksum validation scripts
- [ ] Fix any mismatches
- [ ] Verify HTML display (no broken formatting)

---

## Related Documents

- **`docs/RESULTS_TABLE_DATA_ENTRY_STANDARDS.md`** - Complete `public.results` standards
- **`docs/DATA_FORMAT_SPECIFICATIONS.md`** - Format specs for all tables
- **`docs/DATA_ENTRY_GUIDELINES.md`** - Quick reference checklist
- **`docs/RACE_SCORES_RULES.md`** - Complete race_scores format rules
- **`docs/RACE_SCORES_DATA_ENTRY_VALIDATION.md`** - Mandatory validation rules
- **`docs/CLASS_CANONICAL_VALIDATION_RULES.md`** - class_canonical validation
- **`docs/FLEET_LABEL_CHECKSUM_RULES.md`** - Fleet label validation

---

**Remember**: Data corruption happens when rules are ignored. Enforce these rules at entry time, not later.

