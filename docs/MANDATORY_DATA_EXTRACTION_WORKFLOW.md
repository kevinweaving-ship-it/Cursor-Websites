# MANDATORY Data Extraction Workflow - NEVER SKIP

## CRITICAL RULE: NEVER ASK FOR DATA TWICE

This workflow MUST be followed every time data entry is requested. Skipping any step is a violation.

---

## STEP 1: CHECK FOR EXISTING DATA (MANDATORY)

**BEFORE asking user for ANY data:**

1. ✅ **Check image descriptions in conversation history**
   - Search for `<image>` tags with descriptions
   - Extract ALL data from descriptions immediately
   - Document what was found

2. ✅ **Check local PDF files**
   - Query database: `SELECT local_file_path FROM regattas WHERE regatta_id = '{id}'`
   - Use OCR if PDF exists locally
   - Extract data from PDF before asking user

3. ✅ **Check OCR tools availability**
   - Verify: `pip3 list | grep -i "tesseract\|pdf2image\|pillow"`
   - If available, USE THEM immediately
   - Don't ask user - just extract

4. ✅ **Check user confirmations**
   - If user said "I have it" or "confirm you have it" → DO NOT ASK AGAIN
   - Track in memory: "User confirmed data provided for {fleet/regatta}"
   - Reference confirmation before asking

---

## STEP 2: EXTRACT DATA IMMEDIATELY (MANDATORY)

**When user provides data (image, PDF, or confirms):**

1. ✅ **Extract immediately** - Do NOT wait
2. ✅ **Use OCR if needed** - Don't ask permission, just do it
3. ✅ **Create SQL file** - Start entering data right away
4. ✅ **Report what was extracted** - Show progress, not problems

**CRITICAL RULE**: If PDF exists locally, use OCR IMMEDIATELY. The PDF contains ALL data, even if description only shows examples.

**Example**:
- Description says "Rank 1, 7, 22" → PDF has ALL 22 entries
- Extract ALL 22 from PDF using OCR, don't ask user
- Don't say "I only have 3 examples" when PDF has all data

---

## STEP 3: VALIDATION BEFORE ASKING (MANDATORY)

**BEFORE asking user for data, answer these questions:**

1. ❓ **Did user already provide this?** → If YES, DO NOT ASK
2. ❓ **Is data in an image description?** → If YES, EXTRACT IT
3. ❓ **Does local PDF exist?** → If YES, USE OCR
4. ❓ **Did user confirm data provided?** → If YES, NEVER ASK AGAIN
5. ❓ **Have I already asked for this?** → If YES, CHECK HISTORY FIRST

**If ANY answer is YES → DO NOT ASK USER**

---

## STEP 4: ERROR HANDLING (MANDATORY)

**If extraction fails:**

1. ✅ **State what was attempted**: "Tried OCR on PDF, extracted X entries but missing Y"
2. ✅ **State what's missing**: "Need race scores for ranks 3-5"
3. ✅ **DO NOT re-ask for entire dataset**: Only ask for missing pieces
4. ✅ **Show progress**: "Entered 7 of 10 entries, need 3 more"

**NEVER say**: "I need the ILCA 6 Fleet results"  
**ALWAYS say**: "Entered 7 entries from OCR, need race scores for ranks 8-10"

---

## STEP 5: MEMORY SYSTEM (MANDATORY)

**When user confirms data provided:**

1. ✅ **Create memory immediately**: "User confirmed ILCA 6 Fleet data provided for Regatta 367"
2. ✅ **Reference before asking**: Check memory before any data request
3. ✅ **Update if provided**: If user provides again, update memory

---

## STEP 6: FUZZY MATCHING BEFORE NULL SA ID (MANDATORY)

**Before inserting ANY result with NULL SA ID, MUST run fuzzy matching:**

1. ✅ **Check previous results by sail number** (exact match)
2. ✅ **Check previous results by name** (fuzzy match - similarity > 0.75)
3. ✅ **Check SA ID table by name** (fuzzy match - similarity > 0.75)
4. ✅ **If SA ID found, check previous results for that SA ID**
5. ✅ **Only insert NULL if ALL checks fail**

**Rule**: NEVER insert NULL SA ID without checking previous results first.

**Enforcement**:
```bash
python3 admin/tools/FUZZY_MATCH_SAILOR.py --name "Rudi McNeill" --sail "214133" --class "Ilca 7"
```

**Example Failure**: 
- Rudi McNeill → Should have found "Rudy McNeill" (SA ID: 1644, similarity: 80%)
- See: `admin/audit/FUZZY_MATCHING_FAILURE_RUDI_MCNEILL.md`

---

## STEP 7: SAIL NUMBER TYPO CORRECTION (MANDATORY)

**When sailor in same class has conflicting sail numbers:**

1. ✅ **Check sail number patterns** in both ranges
2. ✅ **Identify which range has multiple nearby numbers** (likely correct)
3. ✅ **Identify which range is isolated** (likely typo)
4. ✅ **Use pattern analysis** to determine correct value
5. ✅ **Verify against PDF** but pattern takes precedence
6. ✅ **Apply correction** and document in audit log

**Rule**: Pattern with multiple nearby numbers = correct. Isolated number = typo.

**Enforcement**:
- See: `docs/SAIL_NUMBER_TYPO_CORRECTION_RULE.md`
- Example: Rudy McNeill - 124133 (isolated) vs 214133 (fits pattern with 214128, 214130, 214131, 214132)

---

## STEP 8: CHECK PREVIOUS RESULTS BEFORE SQL INSERT (MANDATORY)

**BEFORE creating ANY SQL INSERT statement, MUST check previous results for EVERY sailor:**

1. ✅ **Run mandatory check for each sailor**:
   ```python
   from admin.tools.MANDATORY_SAILOR_CHECK import check_sailor_before_insert
   sa_id, db_name = check_sailor_before_insert("Name", sail_number)
   ```

2. ✅ **Use the returned SA ID and name** in SQL INSERT (not PDF name)

3. ✅ **If check returns None, THEN** insert NULL (only after all checks fail)

**CRITICAL RULE**: SQL file must be created WITH correct SA IDs and names from the start. NEVER create SQL with NULL SA IDs, then fix later.

**Enforcement**:
- Must call `check_sailor_before_insert()` for each helm/crew BEFORE writing SQL
- SQL INSERT statements must use the returned `db_name` and `sa_id`
- If SQL file is created with NULL SA IDs, it's a violation

**Example Failure**:
- Created SQL with "Murray Hofmeyer" and NULL SA ID
- Should have checked → Found "Murray Hofmeyr" (SA ID: 16016) in previous results
- SQL should have been created with correct name and SA ID from the start

---

## ENFORCEMENT

**Before ANY data request, run:**
```bash
python3 admin/tools/PRE_DATA_REQUEST_VALIDATION.py <regatta_id> <fleet_name>
```

**Violations of this workflow result in:**
- Immediate halt to data entry
- Audit log entry
- User notification of failure

**This workflow is NON-NEGOTIABLE.**

**Root Cause Document**: See `admin/audit/ROOT_CAUSE_ANALYSIS_DATA_EXTRACTION_FAILURES.md` for complete analysis of why this happened 50+ times.

---

## EXAMPLES

### ❌ WRONG
```
Agent: "I need the ILCA 6 Fleet results for Regatta 367"
```

### ✅ CORRECT
```
Agent: "Checking local PDF and image descriptions for ILCA 6 Fleet...
Found PDF at results/2025/2025-gp-regional-results/1f80b2aaa5675d7d.pdf
Running OCR extraction now...
Extracted 10 entries. Entering data now."
```

### ❌ WRONG (After user confirms)
```
Agent: "Can you provide the ILCA 6 Fleet results?"
User: "I already told you I have them!"
```

### ✅ CORRECT (After user confirms)
```
Agent: "You confirmed ILCA 6 Fleet data is available. 
Extracting from image description now. Will enter all 10 entries."
```


## CRITICAL RULE: NEVER ASK FOR DATA TWICE

This workflow MUST be followed every time data entry is requested. Skipping any step is a violation.

---

## STEP 1: CHECK FOR EXISTING DATA (MANDATORY)

**BEFORE asking user for ANY data:**

1. ✅ **Check image descriptions in conversation history**
   - Search for `<image>` tags with descriptions
   - Extract ALL data from descriptions immediately
   - Document what was found

2. ✅ **Check local PDF files**
   - Query database: `SELECT local_file_path FROM regattas WHERE regatta_id = '{id}'`
   - Use OCR if PDF exists locally
   - Extract data from PDF before asking user

3. ✅ **Check OCR tools availability**
   - Verify: `pip3 list | grep -i "tesseract\|pdf2image\|pillow"`
   - If available, USE THEM immediately
   - Don't ask user - just extract

4. ✅ **Check user confirmations**
   - If user said "I have it" or "confirm you have it" → DO NOT ASK AGAIN
   - Track in memory: "User confirmed data provided for {fleet/regatta}"
   - Reference confirmation before asking

---

## STEP 2: EXTRACT DATA IMMEDIATELY (MANDATORY)

**When user provides data (image, PDF, or confirms):**

1. ✅ **Extract immediately** - Do NOT wait
2. ✅ **Use OCR if needed** - Don't ask permission, just do it
3. ✅ **Create SQL file** - Start entering data right away
4. ✅ **Report what was extracted** - Show progress, not problems

**CRITICAL RULE**: If PDF exists locally, use OCR IMMEDIATELY. The PDF contains ALL data, even if description only shows examples.

**Example**:
- Description says "Rank 1, 7, 22" → PDF has ALL 22 entries
- Extract ALL 22 from PDF using OCR, don't ask user
- Don't say "I only have 3 examples" when PDF has all data

---

## STEP 3: VALIDATION BEFORE ASKING (MANDATORY)

**BEFORE asking user for data, answer these questions:**

1. ❓ **Did user already provide this?** → If YES, DO NOT ASK
2. ❓ **Is data in an image description?** → If YES, EXTRACT IT
3. ❓ **Does local PDF exist?** → If YES, USE OCR
4. ❓ **Did user confirm data provided?** → If YES, NEVER ASK AGAIN
5. ❓ **Have I already asked for this?** → If YES, CHECK HISTORY FIRST

**If ANY answer is YES → DO NOT ASK USER**

---

## STEP 4: ERROR HANDLING (MANDATORY)

**If extraction fails:**

1. ✅ **State what was attempted**: "Tried OCR on PDF, extracted X entries but missing Y"
2. ✅ **State what's missing**: "Need race scores for ranks 3-5"
3. ✅ **DO NOT re-ask for entire dataset**: Only ask for missing pieces
4. ✅ **Show progress**: "Entered 7 of 10 entries, need 3 more"

**NEVER say**: "I need the ILCA 6 Fleet results"  
**ALWAYS say**: "Entered 7 entries from OCR, need race scores for ranks 8-10"

---

## STEP 5: MEMORY SYSTEM (MANDATORY)

**When user confirms data provided:**

1. ✅ **Create memory immediately**: "User confirmed ILCA 6 Fleet data provided for Regatta 367"
2. ✅ **Reference before asking**: Check memory before any data request
3. ✅ **Update if provided**: If user provides again, update memory

---

## STEP 6: FUZZY MATCHING BEFORE NULL SA ID (MANDATORY)

**Before inserting ANY result with NULL SA ID, MUST run fuzzy matching:**

1. ✅ **Check previous results by sail number** (exact match)
2. ✅ **Check previous results by name** (fuzzy match - similarity > 0.75)
3. ✅ **Check SA ID table by name** (fuzzy match - similarity > 0.75)
4. ✅ **If SA ID found, check previous results for that SA ID**
5. ✅ **Only insert NULL if ALL checks fail**

**Rule**: NEVER insert NULL SA ID without checking previous results first.

**Enforcement**:
```bash
python3 admin/tools/FUZZY_MATCH_SAILOR.py --name "Rudi McNeill" --sail "214133" --class "Ilca 7"
```

**Example Failure**: 
- Rudi McNeill → Should have found "Rudy McNeill" (SA ID: 1644, similarity: 80%)
- See: `admin/audit/FUZZY_MATCHING_FAILURE_RUDI_MCNEILL.md`

---

## STEP 7: SAIL NUMBER TYPO CORRECTION (MANDATORY)

**When sailor in same class has conflicting sail numbers:**

1. ✅ **Check sail number patterns** in both ranges
2. ✅ **Identify which range has multiple nearby numbers** (likely correct)
3. ✅ **Identify which range is isolated** (likely typo)
4. ✅ **Use pattern analysis** to determine correct value
5. ✅ **Verify against PDF** but pattern takes precedence
6. ✅ **Apply correction** and document in audit log

**Rule**: Pattern with multiple nearby numbers = correct. Isolated number = typo.

**Enforcement**:
- See: `docs/SAIL_NUMBER_TYPO_CORRECTION_RULE.md`
- Example: Rudy McNeill - 124133 (isolated) vs 214133 (fits pattern with 214128, 214130, 214131, 214132)

---

## STEP 8: CHECK PREVIOUS RESULTS BEFORE SQL INSERT (MANDATORY)

**BEFORE creating ANY SQL INSERT statement, MUST check previous results for EVERY sailor:**

1. ✅ **Run mandatory check for each sailor**:
   ```python
   from admin.tools.MANDATORY_SAILOR_CHECK import check_sailor_before_insert
   sa_id, db_name = check_sailor_before_insert("Name", sail_number)
   ```

2. ✅ **Use the returned SA ID and name** in SQL INSERT (not PDF name)

3. ✅ **If check returns None, THEN** insert NULL (only after all checks fail)

**CRITICAL RULE**: SQL file must be created WITH correct SA IDs and names from the start. NEVER create SQL with NULL SA IDs, then fix later.

**Enforcement**:
- Must call `check_sailor_before_insert()` for each helm/crew BEFORE writing SQL
- SQL INSERT statements must use the returned `db_name` and `sa_id`
- If SQL file is created with NULL SA IDs, it's a violation

**Example Failure**:
- Created SQL with "Murray Hofmeyer" and NULL SA ID
- Should have checked → Found "Murray Hofmeyr" (SA ID: 16016) in previous results
- SQL should have been created with correct name and SA ID from the start

---

## ENFORCEMENT

**Before ANY data request, run:**
```bash
python3 admin/tools/PRE_DATA_REQUEST_VALIDATION.py <regatta_id> <fleet_name>
```

**Violations of this workflow result in:**
- Immediate halt to data entry
- Audit log entry
- User notification of failure

**This workflow is NON-NEGOTIABLE.**

**Root Cause Document**: See `admin/audit/ROOT_CAUSE_ANALYSIS_DATA_EXTRACTION_FAILURES.md` for complete analysis of why this happened 50+ times.

---

## EXAMPLES

### ❌ WRONG
```
Agent: "I need the ILCA 6 Fleet results for Regatta 367"
```

### ✅ CORRECT
```
Agent: "Checking local PDF and image descriptions for ILCA 6 Fleet...
Found PDF at results/2025/2025-gp-regional-results/1f80b2aaa5675d7d.pdf
Running OCR extraction now...
Extracted 10 entries. Entering data now."
```

### ❌ WRONG (After user confirms)
```
Agent: "Can you provide the ILCA 6 Fleet results?"
User: "I already told you I have them!"
```

### ✅ CORRECT (After user confirms)
```
Agent: "You confirmed ILCA 6 Fleet data is available. 
Extracting from image description now. Will enter all 10 entries."
```

