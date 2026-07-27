# _sailors_in_class Column Rules

**Table**: `public.classes`  
**Column**: `_sailors_in_class` (INTEGER)

---

## Purpose

Tracks the total number of **unique sailors** who have sailed in each class, based on actual results data.

---

## Rules

### 1. Unique Sailor Count
- ✅ **Each sailor counted ONCE per class** - regardless of how many regattas they sailed
- ✅ Counts: **Helms + Crews + Crew2 + Crew3** per class
- ✅ Uses: `helm_sa_sailing_id`, `helm_temp_id`, `crew_sa_sailing_id`, `crew_temp_id`, `crew2_sa_sailing_id`, `crew2_temp_id`, `crew3_sa_sailing_id`, `crew3_temp_id`
- ❌ **NO duplicates** - Same sailor sailing multiple regattas = count 1, not multiple

### 2. Parent Classes vs Sub-Classes

#### Parent Classes (e.g., Optimist, Ilca/Laser)
- ✅ **Parent = SUM of all children**
- Example: `Optimist` = `Optimist A` + `Optimist B` + `Optimist C`
- Example: `Ilca/Laser` = `Ilca 4.7` + `Ilca 6` + `Ilca 7`

#### Sub-Classes (e.g., Optimist A, Ilca 7)
- ✅ **Each sub-class has its own count**
- Counted from actual results using `class_canonical` from `results` table
- **NOT** counted in parent if they're in a sub-class

#### Standalone Classes (e.g., 420, Dabchick, Mirror)
- ✅ **Direct count from results** - no parent/child relationship

### 3. Calculation Logic

**Step 1: Count unique sailors per class** (sub-classes and standalone)
```sql
-- Collect ALL sailors (helm, crew, crew2, crew3) for each class_canonical
-- Count DISTINCT sailor_id per class_canonical
-- Update _sailors_in_class for sub-classes and standalone classes
```

**Step 2: Sum children for parent classes**
```sql
-- For each parent class: SUM all children's _sailors_in_class
-- Update parent._sailors_in_class = SUM(children._sailors_in_class)
```

---

## Data Entry Rule

### **MANDATORY**: Update After Every Results Import

**After completing data entry for a regatta**:

1. ✅ Run `admin/tools/update_sailors_in_class.sql`
2. ✅ Verify parent classes = sum of children
3. ✅ Verify counts are correct (spot-check a few classes)

**This ensures**:
- New sailors are added to counts
- Parent classes reflect total sailors across all sub-classes
- Data stays current

---

## Current Parent-Child Relationships

### Optimist Family
- **Parent**: `Optimist` (class_id = 1)
- **Children**: 
  - `Optimist A` (class_id = 62)
  - `Optimist B` (class_id = 63)
  - `Optimist C` (class_id = 103)
- **Rule**: `Optimist._sailors_in_class` = SUM(`Optimist A` + `B` + `C`)

### Ilca/Laser Family
- **Parent**: `Ilca/Laser` (class_id = 6)
- **Children**:
  - `Ilca 4.7` (class_id = 8)
  - `Ilca 6` (class_id = 45)
  - `Ilca 7` (class_id = 46)
- **Rule**: `Ilca/Laser._sailors_in_class` = SUM(`Ilca 4.7` + `Ilca 6` + `Ilca 7`)

---

## Validation Script

**File**: `admin/tools/validate_sailors_in_class.sql`

**Checks**:
1. ✅ All classes with results have `_sailors_in_class > 0`
2. ✅ Parent classes = sum of children
3. ✅ Counts match actual unique sailors in results table

---

## Examples

### Example 1: Optimist
- Optimist A has 26 unique sailors
- Optimist B has 25 unique sailors  
- Optimist C has 10 unique sailors
- **Optimist (parent) = 26 + 25 + 10 = 61 unique sailors**

### Example 2: Ilca 7 (sub-class)
- Ilca 7 has 14 unique sailors (counted directly from results)
- Ilca/Laser (parent) = Ilca 4.7 + Ilca 6 + Ilca 7 totals

### Example 3: 420 (standalone)
- 420 has 24 unique sailors (counted directly, no parent)

---

## Related Documents

- `docs/ALL_COLUMN_RULES_REFERENCE.md` - Master rules reference
- `admin/tools/update_sailors_in_class.sql` - Update script
- `admin/tools/validate_sailors_in_class.sql` - Validation script

---

**CRITICAL**: This count must be updated **after every regatta results import** to maintain accuracy.



**Table**: `public.classes`  
**Column**: `_sailors_in_class` (INTEGER)

---

## Purpose

Tracks the total number of **unique sailors** who have sailed in each class, based on actual results data.

---

## Rules

### 1. Unique Sailor Count
- ✅ **Each sailor counted ONCE per class** - regardless of how many regattas they sailed
- ✅ Counts: **Helms + Crews + Crew2 + Crew3** per class
- ✅ Uses: `helm_sa_sailing_id`, `helm_temp_id`, `crew_sa_sailing_id`, `crew_temp_id`, `crew2_sa_sailing_id`, `crew2_temp_id`, `crew3_sa_sailing_id`, `crew3_temp_id`
- ❌ **NO duplicates** - Same sailor sailing multiple regattas = count 1, not multiple

### 2. Parent Classes vs Sub-Classes

#### Parent Classes (e.g., Optimist, Ilca/Laser)
- ✅ **Parent = SUM of all children**
- Example: `Optimist` = `Optimist A` + `Optimist B` + `Optimist C`
- Example: `Ilca/Laser` = `Ilca 4.7` + `Ilca 6` + `Ilca 7`

#### Sub-Classes (e.g., Optimist A, Ilca 7)
- ✅ **Each sub-class has its own count**
- Counted from actual results using `class_canonical` from `results` table
- **NOT** counted in parent if they're in a sub-class

#### Standalone Classes (e.g., 420, Dabchick, Mirror)
- ✅ **Direct count from results** - no parent/child relationship

### 3. Calculation Logic

**Step 1: Count unique sailors per class** (sub-classes and standalone)
```sql
-- Collect ALL sailors (helm, crew, crew2, crew3) for each class_canonical
-- Count DISTINCT sailor_id per class_canonical
-- Update _sailors_in_class for sub-classes and standalone classes
```

**Step 2: Sum children for parent classes**
```sql
-- For each parent class: SUM all children's _sailors_in_class
-- Update parent._sailors_in_class = SUM(children._sailors_in_class)
```

---

## Data Entry Rule

### **MANDATORY**: Update After Every Results Import

**After completing data entry for a regatta**:

1. ✅ Run `admin/tools/update_sailors_in_class.sql`
2. ✅ Verify parent classes = sum of children
3. ✅ Verify counts are correct (spot-check a few classes)

**This ensures**:
- New sailors are added to counts
- Parent classes reflect total sailors across all sub-classes
- Data stays current

---

## Current Parent-Child Relationships

### Optimist Family
- **Parent**: `Optimist` (class_id = 1)
- **Children**: 
  - `Optimist A` (class_id = 62)
  - `Optimist B` (class_id = 63)
  - `Optimist C` (class_id = 103)
- **Rule**: `Optimist._sailors_in_class` = SUM(`Optimist A` + `B` + `C`)

### Ilca/Laser Family
- **Parent**: `Ilca/Laser` (class_id = 6)
- **Children**:
  - `Ilca 4.7` (class_id = 8)
  - `Ilca 6` (class_id = 45)
  - `Ilca 7` (class_id = 46)
- **Rule**: `Ilca/Laser._sailors_in_class` = SUM(`Ilca 4.7` + `Ilca 6` + `Ilca 7`)

---

## Validation Script

**File**: `admin/tools/validate_sailors_in_class.sql`

**Checks**:
1. ✅ All classes with results have `_sailors_in_class > 0`
2. ✅ Parent classes = sum of children
3. ✅ Counts match actual unique sailors in results table

---

## Examples

### Example 1: Optimist
- Optimist A has 26 unique sailors
- Optimist B has 25 unique sailors  
- Optimist C has 10 unique sailors
- **Optimist (parent) = 26 + 25 + 10 = 61 unique sailors**

### Example 2: Ilca 7 (sub-class)
- Ilca 7 has 14 unique sailors (counted directly from results)
- Ilca/Laser (parent) = Ilca 4.7 + Ilca 6 + Ilca 7 totals

### Example 3: 420 (standalone)
- 420 has 24 unique sailors (counted directly, no parent)

---

## Related Documents

- `docs/ALL_COLUMN_RULES_REFERENCE.md` - Master rules reference
- `admin/tools/update_sailors_in_class.sql` - Update script
- `admin/tools/validate_sailors_in_class.sql` - Validation script

---

**CRITICAL**: This count must be updated **after every regatta results import** to maintain accuracy.


















