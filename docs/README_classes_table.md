# CLASSES Table - GPT Rules & Data Structure

## Purpose
Stores standardized sailing class information with aliases for different naming conventions.

## Table Structure
```sql
CREATE TABLE classes (
    class_id SERIAL PRIMARY KEY,
    class_canonical TEXT NOT NULL UNIQUE,   -- Standardized class name (420, Optimist, etc.)
    class_description TEXT,                 -- Full description
    crew_count INTEGER,                     -- Number of crew (1, 2, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE class_aliases (
    alias_id SERIAL PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES classes(class_id),
    class_alias TEXT NOT NULL,              -- Alternative name/variation
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(class_id, class_alias)
);
```

## Data Rules (from GPT instructions)

### Class Standardization
- **class_canonical**: Use standard names (420, Optimist, 29er, Laser, etc.)
- **class_aliases**: Store variations (Laser Radial, Laser 4.7, etc.)
- **crew_count**: Single-handed (1) or double-handed (2)

### Common Class Mappings
- **420** → Standard double-handed dinghy
- **Optimist** → Single-handed youth dinghy  
- **29er** → High-performance double-handed skiff
- **Laser** → Single-handed dinghy (with aliases for Radial, 4.7)
- **Dabchick** → Single-handed youth dinghy
- **ILCA 4/6/7** → Laser class variations

### Data Integrity Rules
1. **NEVER use placeholders** - only real data or NULL
2. **NEVER hardcode values** - always extract from source
3. **ALWAYS use standard class names** for canonical
4. **ALWAYS create aliases** for variations
5. **ALWAYS set correct crew count**

## ⚠️ CRITICAL RULES - NEVER IGNORE

**BEFORE entering ANY classes data**, you MUST:

1. ✅ **Read `docs/ALL_COLUMN_RULES_REFERENCE.md`** - Master reference for ALL columns
2. ✅ **Read `docs/CLASSES_TABLE_AUTHORITATIVE_SOURCE.md`** - Authoritative source explanation
3. ✅ **Check existing correct examples** in database
4. ✅ **Verify format consistency** (e.g., `29Er` not `29er`, `Ilca 4.7` not `Ilca 4`)

## 🚨 CLASS NAME CAPITALIZATION RULE - FREQUENTLY VIOLATED

**THIS RULE IS CONSTANTLY BROKEN - READ CAREFULLY:**

- **`classes.class_name` is the AUTHORITATIVE SOURCE** - All `results.class_canonical` must match EXACTLY
- **DO NOT USE LOWERCASE** - The classes table uses proper capitalization:
  - ✅ `Optimist A` (NOT ❌ "optimist a")
  - ✅ `Optimist B` (NOT ❌ "optimist b")
  - ✅ `Dabchick` (NOT ❌ "dabchick")
  - ✅ `ILCA 4` (NOT ❌ "ilca 4")
  - ✅ `ILCA 6` (NOT ❌ "ilca 6")
  - ✅ `RS Tera` (NOT ❌ "rs tera")
  - ✅ `Mirror` (NOT ❌ "mirror")
  - ✅ `Topaz` (NOT ❌ "topaz")
  - ✅ `Topper 5.3` (NOT ❌ "topper 5.3")

**BEFORE SETTING `class_canonical`:**
1. Query `classes` table: `SELECT class_name FROM classes WHERE LOWER(class_name) = LOWER('your_class')`
2. Use the EXACT value from `classes.class_name` (case-sensitive)
3. NEVER assume lowercase - always check the classes table first

**Column Rules**:
- **`class_name`**: ⚠️ **AUTHORITATIVE SOURCE** - All `results.class_canonical` must match EXACTLY (case-sensitive, no variations)
  - Format must be consistent: `29Er` (not `29er`), `Ilca 4.7` (not `Ilca 4`)
  - If PDF shows wrong class (e.g., "Lazer 7"), correct to valid class ("ILCA 7")
  - Invalid `class_canonical` breaks HTML filtering - results won't be found in search
- **`crew_policy`**: Valid values: 'single', 'double', 'Crewed', or NULL
  - Must match actual results data - not assigned by default
- **`_sailors_in_class`**: Integer, **MUST be updated after every results import**

**Pre-Entry Validation**:
- [ ] Verify `class_name` format matches existing (case-sensitive)
- [ ] If adding new class, ensure format is consistent (e.g., `Ilca 4.7` not `Ilca 4`)

**Post-Entry Validation** (MANDATORY after results import):
- [ ] Run `admin/tools/update_sailors_in_class.sql` - **MANDATORY** - Update unique sailor counts per class
- [ ] Run `admin/tools/validate_sailors_in_class.sql` - Verify counts match calculated values
- [ ] Run `admin/tools/update_crew_policy_from_results_proper.sql` - Update crew_policy from actual results
- [ ] Run `admin/tools/validate_class_canonical.sql` - Verify all `results.class_canonical` match `classes.class_name`

**Documentation**: 
- `docs/CLASSES_TABLE_AUTHORITATIVE_SOURCE.md` - Complete explanation of authoritative source rule
- `docs/SAILORS_IN_CLASS_RULES.md` - Sailor count rules and update process
- `docs/CREW_POLICY_AUDIT_PROCESS.md` - Crew policy audit process

## Example Data
```sql
INSERT INTO classes (class_canonical, class_description, crew_count) VALUES
('420', 'Double-handed dinghy', 2),
('Optimist', 'Single-handed youth dinghy', 1),
('29er', 'High-performance double-handed skiff', 2),
('Dabchick', 'Single-handed youth dinghy', 1),
('Laser', 'Single-handed dinghy', 1),
('ILCA 4', 'Laser 4.7 - single-handed youth', 1),
('ILCA 6', 'Laser Radial - single-handed', 1),
('ILCA 7', 'Laser Standard - single-handed', 1);

INSERT INTO class_aliases (class_id, class_alias) VALUES
(1, '420'), (1, '420 Fleet'),
(2, 'Optimist'), (2, 'Opti'), (2, 'Optimist A'), (2, 'Optimist B'),
(3, '29er'), (3, '29er Fleet'),
(4, 'Dabchick'), (4, 'Dabchick Fleet'),
(5, 'Laser'), (5, 'Laser Standard'), (5, 'Laser Fleet'),
(6, 'Laser 4.7'), (6, 'ILCA 4'), (6, 'ILCA4'),
(7, 'Laser Radial'), (7, 'ILCA 6'), (7, 'ILCA6'),
(8, 'Laser Standard'), (8, 'ILCA 7'), (8, 'ILCA7');
```

## Related Tables
- `regatta_blocks.class_canonical` - Links to standardized class
- `regatta_blocks.class_original` - Original class name from results
- `results.class_original` - Class as printed in results

## Usage Patterns
- **Results entry**: Use `class_original` from results sheet
- **Standardization**: Map to `class_canonical` via aliases
- **Display**: Use canonical name for consistency
- **Reporting**: Group by canonical class for statistics

```sql
INSERT INTO classes (class_canonical, class_description, crew_count) VALUES
('420', 'Double-handed dinghy', 2),
('Optimist', 'Single-handed youth dinghy', 1),
('29er', 'High-performance double-handed skiff', 2),
('Dabchick', 'Single-handed youth dinghy', 1),
('Laser', 'Single-handed dinghy', 1),
('ILCA 4', 'Laser 4.7 - single-handed youth', 1),
('ILCA 6', 'Laser Radial - single-handed', 1),
('ILCA 7', 'Laser Standard - single-handed', 1);

INSERT INTO class_aliases (class_id, class_alias) VALUES
(1, '420'), (1, '420 Fleet'),
(2, 'Optimist'), (2, 'Opti'), (2, 'Optimist A'), (2, 'Optimist B'),
(3, '29er'), (3, '29er Fleet'),
(4, 'Dabchick'), (4, 'Dabchick Fleet'),
(5, 'Laser'), (5, 'Laser Standard'), (5, 'Laser Fleet'),
(6, 'Laser 4.7'), (6, 'ILCA 4'), (6, 'ILCA4'),
(7, 'Laser Radial'), (7, 'ILCA 6'), (7, 'ILCA6'),
(8, 'Laser Standard'), (8, 'ILCA 7'), (8, 'ILCA7');
```

## Related Tables
- `regatta_blocks.class_canonical` - Links to standardized class
- `regatta_blocks.class_original` - Original class name from results
- `results.class_original` - Class as printed in results

## Usage Patterns
- **Results entry**: Use `class_original` from results sheet
- **Standardization**: Map to `class_canonical` via aliases
- **Display**: Use canonical name for consistency
- **Reporting**: Group by canonical class for statistics
