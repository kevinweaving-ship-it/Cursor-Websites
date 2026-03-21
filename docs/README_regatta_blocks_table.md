# REGATTA_BLOCKS Table - GPT Rules & Data Structure

## Purpose
Stores fleet/class block information for each regatta with scoring parameters.

## Table Structure
```sql
CREATE TABLE regatta_blocks (
    block_id TEXT PRIMARY KEY,              -- Format: 'regatta_id:class-fleet-slug'
    regatta_id TEXT NOT NULL REFERENCES regattas(regatta_id),
    class_original TEXT,                    -- Class as printed (420, Optimist, etc.)
    class_canonical TEXT,                   -- Standardized class name
    fleet_label TEXT,                       -- Fleet designation (A, B, Gold, Open, etc.)
    races_sailed INTEGER,                   -- Number of races completed
    discard_count INTEGER,                  -- Number of discards allowed
    to_count INTEGER,                       -- Number of races that count (races_sailed - discard_count)
    handicap_system TEXT,                   -- Scoring system (SCHRS, PY, ECHO, Appendix A)
    block_label_raw TEXT,                   -- Original header text from results
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Data Rules (from GPT instructions)

### Block ID Format
- Pattern: `{regatta_id}:{normalized-class-fleet}`
- Example: `359-2025-zvyc-southern-charter-cape-classic:420`
- **NEVER change existing block_id** values

### Fleet Information
- **fleet_label**: Extract from header (A, B, Gold, Open, etc.)
- **class_original**: Extract from header (420, Optimist, 29er, etc.)
- **class_canonical**: Standardized version for consistency

### Scoring Parameters (from GPT rules)
- **races_sailed**: Extract from header (e.g., "8")
- **discard_count**: Extract from header (e.g., "1") 
- **to_count**: Calculate as `races_sailed - discard_count`
- **handicap_system**: Extract from header (usually "Appendix A")

### Data Integrity Rules
1. **NEVER use placeholders** - only real data or NULL
2. **NEVER hardcode values** - always extract from source
3. **ALWAYS extract from header lines** in results sheet
4. **ALWAYS calculate to_count** correctly
5. **ALWAYS preserve original block_label_raw** text

## ⚠️ CRITICAL RULES - NEVER IGNORE

**BEFORE entering ANY regatta_blocks data**, you MUST:

1. ✅ **Read `docs/ALL_COLUMN_RULES_REFERENCE.md`** - Master reference for ALL columns
2. ✅ **Read `docs/DATA_FORMAT_SPECIFICATIONS.md`** - Section: public.regatta_blocks
3. ✅ **Run pre-entry validation scripts** (see below)
4. ✅ **Check existing correct examples** in database

**Column Rules**:
- **`block_id`**: Format `{regatta_id}:{fleet-slug}` (COLON separator `:`, NOT hyphen, single year in regatta_id, no quotes)
- **`fleet_label`**: Actual fleet name (NOT "Overall"), must match `classes.class_name` or authorized override (see `docs/FLEET_LABEL_CHECKSUM_RULES.md`)
- **`class_canonical`**: ⚠️ **CRITICAL** - Must EXACTLY match `classes.class_name` (case-sensitive, no variations)
- **`races_sailed`**: Integer, NOT NULL if block has results
- **`discard_count`**: Integer, NOT NULL, must be `<= races_sailed`
- **`to_count`**: Must equal `races_sailed - discard_count`

**Pre-Entry Validation** (MANDATORY):
- [ ] Run `admin/tools/validate_class_canonical.sql` - Ensure `class_canonical` exists in `classes.class_name`
- [ ] Run `admin/tools/validate_fleet_label_from_classes.sql` - Verify `fleet_label` matches or authorized override
- [ ] Check `block_id` format (colon separator, single year, no quotes)

**Post-Entry Checksum** (MANDATORY):
- [ ] Run `admin/tools/checksum_entry_counts.sql` - Verify entry counts match PDF
- [ ] Run `admin/tools/checksum_fleet_label.sql` - Verify fleet_label consistency
- [ ] Run `admin/tools/validate_discard_count_checksum.sql` - Verify `discard_count` vs `races_sailed`
- [ ] Run `admin/tools/validate_races_sailed_checksum.sql` - Verify `races_sailed` vs actual races
- [ ] Verify `to_count = races_sailed - discard_count` for all blocks
- [ ] Check `fleet_label` is NOT "Overall" (use actual fleet name)
- [ ] Verify `class_canonical` exists in `classes.class_name` (EXACT match)

**Documentation**: 
- `docs/ENTRY_COUNT_CHECKSUM_RULES.md` - Entry count validation
- `docs/FLEET_LABEL_CHECKSUM_RULES.md` - Fleet label validation with manual override

## Example Data
```sql
INSERT INTO regatta_blocks (block_id, regatta_id, class_original, fleet_label, races_sailed, discard_count, to_count, handicap_system, block_label_raw) VALUES
('359-2025-zvyc-southern-charter-cape-classic:420', '359-2025-zvyc-southern-charter-cape-classic', '420', '', 8, 1, 7, 'Appendix A', '420 - Sailed: 8, Discards: 1, To count: 7, Entries: 5, Scoring system: Appendix A'),
('359-2025-zvyc-southern-charter-cape-classic:dabchick', '359-2025-zvyc-southern-charter-cape-classic', 'Dabchick', '', 8, 1, 7, 'Appendix A', 'Dabchick - Sailed: 8, Discards: 1, To count: 7, Entries: 3, Scoring system: Appendix A');
```

## Related Tables
- `regattas` - Parent regatta event
- `results` - Individual race results for this block
- `classes` - Class information reference

## Fleet Types
- **Single Fleet**: No fleet_label (e.g., 420, Optimist)
- **Multiple Fleets**: A, B, Gold, Silver, Open, etc.
- **Mixed Classes**: Open fleets with multiple boat types

**Pre-Entry Validation** (MANDATORY):
- [ ] Run `admin/tools/validate_class_canonical.sql` - Ensure `class_canonical` exists in `classes.class_name`
- [ ] Run `admin/tools/validate_fleet_label_from_classes.sql` - Verify `fleet_label` matches or authorized override
- [ ] Check `block_id` format (colon separator, single year, no quotes)

**Post-Entry Checksum** (MANDATORY):
- [ ] Run `admin/tools/checksum_entry_counts.sql` - Verify entry counts match PDF
- [ ] Run `admin/tools/checksum_fleet_label.sql` - Verify fleet_label consistency
- [ ] Run `admin/tools/validate_discard_count_checksum.sql` - Verify `discard_count` vs `races_sailed`
- [ ] Run `admin/tools/validate_races_sailed_checksum.sql` - Verify `races_sailed` vs actual races
- [ ] Verify `to_count = races_sailed - discard_count` for all blocks
- [ ] Check `fleet_label` is NOT "Overall" (use actual fleet name)
- [ ] Verify `class_canonical` exists in `classes.class_name` (EXACT match)

**Documentation**: 
- `docs/ENTRY_COUNT_CHECKSUM_RULES.md` - Entry count validation
- `docs/FLEET_LABEL_CHECKSUM_RULES.md` - Fleet label validation with manual override

## Example Data
```sql
INSERT INTO regatta_blocks (block_id, regatta_id, class_original, fleet_label, races_sailed, discard_count, to_count, handicap_system, block_label_raw) VALUES
('359-2025-zvyc-southern-charter-cape-classic:420', '359-2025-zvyc-southern-charter-cape-classic', '420', '', 8, 1, 7, 'Appendix A', '420 - Sailed: 8, Discards: 1, To count: 7, Entries: 5, Scoring system: Appendix A'),
('359-2025-zvyc-southern-charter-cape-classic:dabchick', '359-2025-zvyc-southern-charter-cape-classic', 'Dabchick', '', 8, 1, 7, 'Appendix A', 'Dabchick - Sailed: 8, Discards: 1, To count: 7, Entries: 3, Scoring system: Appendix A');
```

## Related Tables
- `regattas` - Parent regatta event
- `results` - Individual race results for this block
- `classes` - Class information reference

## Fleet Types
- **Single Fleet**: No fleet_label (e.g., 420, Optimist)
- **Multiple Fleets**: A, B, Gold, Silver, Open, etc.
- **Mixed Classes**: Open fleets with multiple boat types
