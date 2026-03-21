# Fleet/Class Hierarchy Rules

## Principle

**Fleet = Parent Class | Class = Sub-Class**

The `fleet_label` represents the **parent class** (fleet grouping), while `class_canonical` represents the **actual sub-class** (boat type).

## Hierarchy Structure

### Example: 49er Fleet
- **Fleet Label**: `"49er"` (parent - the fleet name)
- **Class Canonical**: `"29ER"` or `"49er"` (sub-class - actual boat type)

### Example: Optimist Fleet
- **Fleet Label**: `"Optimist"` (parent - the fleet name)
- **Class Canonical**: `"Optimist A"`, `"Optimist B"`, `"Optimist C"` (sub-classes - actual divisions)

### Example: ILCA/Laser Fleet
- **Fleet Label**: `"ILCA"` or `"ILCA/Laser"` (parent - the fleet name)
- **Class Canonical**: `"ILCA 4.7"`, `"ILCA 6"`, `"ILCA 7"` (sub-classes - actual boat types)

## Database Structure

### `classes` Table
The `classes` table has a `parent_id` field that establishes the hierarchy:

```sql
-- Parent classes (parent_id IS NULL)
Ilca/Laser (class_id=6)
Optimist (class_id=1)
29er (class_id=3) - Note: Should have parent if part of "49er" fleet
49er (class_id=101) - Note: Should have parent if part of "49er" fleet

-- Child classes (parent_id points to parent)
Ilca 4.7 (parent_id=6)
Ilca 6 (parent_id=6)
Ilca 7 (parent_id=6)
Optimist A (parent_id=1)
Optimist B (parent_id=1)
Optimist C (parent_id=1)
```

### `regatta_blocks` Table
- **`fleet_label`**: Should be set to **parent class name** (e.g., "49er", "Optimist", "ILCA")
- **`class_canonical`**: Should be set to **sub-class name** (e.g., "29ER", "Optimist A", "ILCA 6")

### `results` Table
- **`fleet_label`**: Should match `regatta_blocks.fleet_label` (parent class)
- **`class_canonical`**: Should be the **actual boat class** (sub-class)

## Rules for Data Entry

### When Creating Regatta Blocks

1. **Single Class Fleet** (e.g., "420 Fleet"):
   - `fleet_label`: `"420"` (or leave NULL if no parent)
   - `class_canonical`: `"420"`

2. **Multi-Class Fleet** (e.g., "49er Fleet" with 29ER and 49er):
   - `fleet_label`: `"49er"` (parent class - the fleet name)
   - `class_canonical`: `NULL` or leave empty (mixed fleet)

3. **Sub-Class Fleets** (e.g., "Optimist A", "Optimist B"):
   - `fleet_label`: `"Optimist"` (parent class)
   - `class_canonical`: `"Optimist A"` or `"Optimist B"` (sub-class)

### When Creating Results

1. **For each result row**:
   - `fleet_label`: Copy from `regatta_blocks.fleet_label` (parent class)
   - `class_canonical`: Set to **actual boat class** from results sheet
     - If results show "29ER", use `"29ER"`
     - If results show "49er", use `"49er"`
     - If results show "Optimist A", use `"Optimist A"`

## HTML Display

HTML expects:
- **Fleet column**: Shows `fleet_label` (parent class) - e.g., "49er", "Optimist"
- **Class column**: Shows `class_canonical` (sub-class) - e.g., "29ER", "Optimist A"

From `regatta_viewer.html`:
- Line 467: `${h.fleet_label||h.class_canonical||h.class_original||''}` - Fleet column
- Line 468: `${r.class_name||r.class_canonical||r.class_original||''}` - Class column

## Examples

### Example 1: 49er Fleet (Mixed Classes)
**Block Data**:
- `block_id`: `"339-2025-2025-wcapedinghychamps-results:29er-49er"`
- `fleet_label`: `"49er"` (parent - the fleet)
- `class_canonical`: `NULL` (mixed fleet)

**Results Data**:
- Row 1: `fleet_label`="49er", `class_canonical`="49er"
- Row 2: `fleet_label`="49er", `class_canonical`="29ER"
- Row 3: `fleet_label`="49er", `class_canonical`="29ER"

**HTML Display**:
- Fleet column: "49er" (same for all)
- Class column: "49er" or "29ER" (varies by row)

### Example 2: Optimist Fleet (Sub-Classes)
**Block Data**:
- `block_id`: `"339-2025-2025-wcapedinghychamps-results:optimist-a"`
- `fleet_label`: `"Optimist"` (parent)
- `class_canonical`: `"Optimist A"` (sub-class)

**Results Data**:
- All rows: `fleet_label`="Optimist", `class_canonical`="Optimist A"

**HTML Display**:
- Fleet column: "Optimist" (same for all)
- Class column: "Optimist A" (same for all)

## Fix Script

Run `admin/tools/fix_fleet_class_hierarchy.sql` to:
1. Set `fleet_label` to parent class name based on `classes.parent_id`
2. Update `results.fleet_label` to match `regatta_blocks.fleet_label`
3. Handle mixed fleets (like 49er fleet with 29ER and 49er)

## Validation

```sql
-- Check for blocks with NULL fleet_label that should have parent
SELECT rb.block_id, rb.class_canonical, c.class_name as parent
FROM public.regatta_blocks rb
JOIN public.classes c ON c.class_name = rb.class_canonical
JOIN public.classes parent ON parent.class_id = c.parent_id
WHERE rb.fleet_label IS NULL
  AND c.parent_id IS NOT NULL;

-- Check for results with mismatched fleet_label
SELECT res.result_id, res.fleet_label, rb.fleet_label as block_fleet
FROM public.results res
JOIN public.regatta_blocks rb ON rb.block_id = res.block_id
WHERE res.fleet_label != rb.fleet_label
  AND rb.fleet_label IS NOT NULL;
```



## Principle

**Fleet = Parent Class | Class = Sub-Class**

The `fleet_label` represents the **parent class** (fleet grouping), while `class_canonical` represents the **actual sub-class** (boat type).

## Hierarchy Structure

### Example: 49er Fleet
- **Fleet Label**: `"49er"` (parent - the fleet name)
- **Class Canonical**: `"29ER"` or `"49er"` (sub-class - actual boat type)

### Example: Optimist Fleet
- **Fleet Label**: `"Optimist"` (parent - the fleet name)
- **Class Canonical**: `"Optimist A"`, `"Optimist B"`, `"Optimist C"` (sub-classes - actual divisions)

### Example: ILCA/Laser Fleet
- **Fleet Label**: `"ILCA"` or `"ILCA/Laser"` (parent - the fleet name)
- **Class Canonical**: `"ILCA 4.7"`, `"ILCA 6"`, `"ILCA 7"` (sub-classes - actual boat types)

## Database Structure

### `classes` Table
The `classes` table has a `parent_id` field that establishes the hierarchy:

```sql
-- Parent classes (parent_id IS NULL)
Ilca/Laser (class_id=6)
Optimist (class_id=1)
29er (class_id=3) - Note: Should have parent if part of "49er" fleet
49er (class_id=101) - Note: Should have parent if part of "49er" fleet

-- Child classes (parent_id points to parent)
Ilca 4.7 (parent_id=6)
Ilca 6 (parent_id=6)
Ilca 7 (parent_id=6)
Optimist A (parent_id=1)
Optimist B (parent_id=1)
Optimist C (parent_id=1)
```

### `regatta_blocks` Table
- **`fleet_label`**: Should be set to **parent class name** (e.g., "49er", "Optimist", "ILCA")
- **`class_canonical`**: Should be set to **sub-class name** (e.g., "29ER", "Optimist A", "ILCA 6")

### `results` Table
- **`fleet_label`**: Should match `regatta_blocks.fleet_label` (parent class)
- **`class_canonical`**: Should be the **actual boat class** (sub-class)

## Rules for Data Entry

### When Creating Regatta Blocks

1. **Single Class Fleet** (e.g., "420 Fleet"):
   - `fleet_label`: `"420"` (or leave NULL if no parent)
   - `class_canonical`: `"420"`

2. **Multi-Class Fleet** (e.g., "49er Fleet" with 29ER and 49er):
   - `fleet_label`: `"49er"` (parent class - the fleet name)
   - `class_canonical`: `NULL` or leave empty (mixed fleet)

3. **Sub-Class Fleets** (e.g., "Optimist A", "Optimist B"):
   - `fleet_label`: `"Optimist"` (parent class)
   - `class_canonical`: `"Optimist A"` or `"Optimist B"` (sub-class)

### When Creating Results

1. **For each result row**:
   - `fleet_label`: Copy from `regatta_blocks.fleet_label` (parent class)
   - `class_canonical`: Set to **actual boat class** from results sheet
     - If results show "29ER", use `"29ER"`
     - If results show "49er", use `"49er"`
     - If results show "Optimist A", use `"Optimist A"`

## HTML Display

HTML expects:
- **Fleet column**: Shows `fleet_label` (parent class) - e.g., "49er", "Optimist"
- **Class column**: Shows `class_canonical` (sub-class) - e.g., "29ER", "Optimist A"

From `regatta_viewer.html`:
- Line 467: `${h.fleet_label||h.class_canonical||h.class_original||''}` - Fleet column
- Line 468: `${r.class_name||r.class_canonical||r.class_original||''}` - Class column

## Examples

### Example 1: 49er Fleet (Mixed Classes)
**Block Data**:
- `block_id`: `"339-2025-2025-wcapedinghychamps-results:29er-49er"`
- `fleet_label`: `"49er"` (parent - the fleet)
- `class_canonical`: `NULL` (mixed fleet)

**Results Data**:
- Row 1: `fleet_label`="49er", `class_canonical`="49er"
- Row 2: `fleet_label`="49er", `class_canonical`="29ER"
- Row 3: `fleet_label`="49er", `class_canonical`="29ER"

**HTML Display**:
- Fleet column: "49er" (same for all)
- Class column: "49er" or "29ER" (varies by row)

### Example 2: Optimist Fleet (Sub-Classes)
**Block Data**:
- `block_id`: `"339-2025-2025-wcapedinghychamps-results:optimist-a"`
- `fleet_label`: `"Optimist"` (parent)
- `class_canonical`: `"Optimist A"` (sub-class)

**Results Data**:
- All rows: `fleet_label`="Optimist", `class_canonical`="Optimist A"

**HTML Display**:
- Fleet column: "Optimist" (same for all)
- Class column: "Optimist A" (same for all)

## Fix Script

Run `admin/tools/fix_fleet_class_hierarchy.sql` to:
1. Set `fleet_label` to parent class name based on `classes.parent_id`
2. Update `results.fleet_label` to match `regatta_blocks.fleet_label`
3. Handle mixed fleets (like 49er fleet with 29ER and 49er)

## Validation

```sql
-- Check for blocks with NULL fleet_label that should have parent
SELECT rb.block_id, rb.class_canonical, c.class_name as parent
FROM public.regatta_blocks rb
JOIN public.classes c ON c.class_name = rb.class_canonical
JOIN public.classes parent ON parent.class_id = c.parent_id
WHERE rb.fleet_label IS NULL
  AND c.parent_id IS NOT NULL;

-- Check for results with mismatched fleet_label
SELECT res.result_id, res.fleet_label, rb.fleet_label as block_fleet
FROM public.results res
JOIN public.regatta_blocks rb ON rb.block_id = res.block_id
WHERE res.fleet_label != rb.fleet_label
  AND rb.fleet_label IS NOT NULL;
```


















