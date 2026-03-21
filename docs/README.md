# Regatta Results System

## ⚠️ CRITICAL DATA INTEGRITY WARNING ⚠️

**BEFORE MAKING ANY CHANGES, READ `DATA_INTEGRITY_RULES.md`**

**VIOLATION OF DATA INTEGRITY RULES WILL CAUSE SYSTEM FAILURE AND DATA CORRUPTION.**

## Creating New Regatta Results Tables

### Process for New Regattas (e.g., Reg no 258)

1. **Check Regatta Source Table**
   - Use regatta number to check `regatta_sources` table
   - Remember the name and number from that table
   - Document this step

2. **Validate Header Information - Event Data**
   - Receive header information from results sheet
   - **Pass Cursor**: Copy/paste the result sheet header for Event information
   - Do checksum by comparing name from results sheet with name from `regatta_sources` table
   - If valid (names match), proceed to Step 3

3. **Create Results Table**
   - Create table called `regatta_XXX_results` (replace XXX with regatta number)
   - Use template: `CREATE TABLE app.regatta_XXX_results (LIKE app.regatta_XXX_results_template);`
   - **CRITICAL: Grant permissions immediately after creation**

### Event Data Identification
When receiving data, identify it as **Event information** and recognize which column each piece of information should go into:
- Event name → `regatta_name` column
- Club name → `club_abreviation` column  
- Result status → `result_status` column
- End date → `end_date` column
- As at time → `as_at_time` column

### Permission Rule for New Tables

**When creating a new table, you MUST grant all permissions to PUBLIC:**

```sql
GRANT ALL ON TABLE app.regatta_XXX_results TO PUBLIC;
```

This command works on the first attempt and prevents permission denied errors.

### Template Table

The `regatta_XXX_results_template` table contains all required columns with zero data:
- 119 columns including race scores (race_1_score through race_30_score)
- Race LPS codes (race_1_lps_code through race_30_lps_code)
- Fleet, entrant, and scoring information
- All boolean flags and metadata fields

Use this template to create new regatta results tables by copying its structure.

## Data Validation Requirements for Results Sheet Processing

### CRITICAL: All Data Must Be Validated During Import

When processing results sheets, the following validation rules MUST be enforced automatically:

#### Club Code Validation
- **ALL club codes must be 3-4 letters maximum**
- **ALL club codes must exist in the `clubs` table**
- **Invalid club codes** (NA, NAM, NULL, empty, or >4 letters) must be automatically assigned to 'UNK'
- **Club mapping must happen during import** - not as a post-processing step
- **club_id must be automatically resolved** from club_abbrev during import

#### Class Code Validation  
- **ALL class codes must exist in the `classes` table**
- **Invalid class codes must be flagged** and handled appropriately
- **class_canonical must be populated** from valid class codes

#### Sailor ID Validation
- **SAS IDs must be validated** against the `sailing_id` table
- **Temp IDs must be created** for sailors not in the SAS ID table
- **Name matching must be automated** with fuzzy matching for similar names

#### Required Column Population
**The following columns MUST be populated automatically during import:**

**Club Information:**
- `club_abbrev` - 3-4 letter club code (validated against clubs table)
- `club_id` - Foreign key to clubs table (auto-resolved)
- `club_fullname` - Full club name (auto-populated from clubs table)
- `province` - Province code (auto-populated from clubs table)

**Class Information:**
- `class_1` - Primary class (validated against classes table)
- `class_canonical` - Canonical class name (auto-populated)

**Sailor Information:**
- `helm_sas_id` - SAS ID if sailor exists in sailing_id table
- `crew_sas_id` - SAS ID if sailor exists in sailing_id table
- `helm_temp_id` - Temp ID if sailor not in sailing_id table
- `crew_temp_id` - Temp ID if sailor not in sailing_id table

### Import Process Requirements

**Before any results sheet data is imported:**

1. **Validate all club codes** against the clubs table
2. **Validate all class codes** against the classes table  
3. **Create missing clubs/classes** if they are valid (3-4 letter codes)
4. **Assign UNK club** to any invalid club codes
5. **Auto-match sailors** to SAS IDs or create Temp IDs
6. **Populate all required foreign key relationships**

**NO MANUAL POST-PROCESSING SHOULD BE REQUIRED**

### Error Handling

- **Invalid data must be logged** but not prevent import
- **UNK assignments must be documented** for future correction
- **All validation failures must be reported** in import logs

### Future Regatta Processing

**Every new regatta import must:**
- Follow these validation rules automatically
- Not require manual club/class assignment fixes
- Generate clean, validated data from the start
- Update sailor club affiliations automatically
