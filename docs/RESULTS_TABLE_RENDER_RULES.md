# Results Table Render Rules

**Purpose**: Ensure all results sheets render consistently across the app. Apply these rules to every results table (index.html popup, regatta/results.html, regatta/class/class-results.html, regatta/class/podium/podium.html).

## Fleet vs Class (CRITICAL)

- **Fleet** = broad category (Open, Windsurfer, 49er, Optimist)
- **Class** = boat sailed within that fleet (Sonnet, Bic, 29ER, Optimist A)
- There is no "Open Class" – use "Open Fleet" for the fleet name
- Single-class fleets: Fleet and Class may be the same (e.g. 420 Fleet, 420 Class)

## Column Rules

### Standard Column Order
`Rank | Fleet | Class | Sail No | [Boat Name] | [Jib No] | [Bow No] | [Hull No] | Club | Helm | [Crew] | [R1..Rn] | Total | Nett`

### Fleet Column
- **Source**: When `class_canonical` appears in more result rows than `fleet_label`, use `class_canonical` for Fleet (broader term). Otherwise `blockData.fleet_label || blockData.class_canonical || ''`
- **Purpose**: Parent/fleet name (Open, Windsurfer LT, etc.)
- **Example**: Windsurfer LT National – Fleet = "Windsurfer LT" (broader), Class = "BIC" or "Windsurfer LT" (boat sailed). BIC cannot be Fleet; it is a class within the Windsurfer fleet.

### Class Column
- **Source**: `r.result_class_canonical || r.result_class_original || r.class_name || r.class_canonical || r.class_original || ''`
- **Purpose**: Boat sailed in that row (Sonnet, Bic, etc.)
- **API**: Regatta API must return `result_class_canonical` and `result_class_original` per row (from `results` table)

### Lite View (compact)
- Single-class blocks: `Rank | Class | Sail No | Club | Helm | [Crew] | Nett` (no Fleet column)
- Multi-class blocks: Same as standard but Class shows boat per row

## Block Matching (for class-results, podium, popup)

Match blocks by:
1. `blockData.fleet_label`
2. `blockData.class_canonical`
3. `blockData.class_original`
4. `r.result_class_canonical` (any row in block)
5. `r.result_class_original` (any row in block)
6. Use `normalizeClass()`: trim, replace `_`, strip ` Fleet` suffix, lowerCase
7. Flexible match: exact, starts-with, contains

### Multi-Class Fleets (e.g. Open Fleet)
- Block has `fleet_label = "Open"`
- Rows have different `result_class_canonical` (Sonnet, Laser, etc.)
- When filtering by class (e.g. Sonnet): find block by row match, then filter rows where `result_class_canonical || result_class_original || class_name` matches

## Data Attributes (sailor-row-clickable)
- `data-sailor-id`
- `data-helm-name`
- `data-club`
- `data-class`: use same Class resolution as display (`result_class_canonical || result_class_original || class_name || …`)

## Files to Apply Rules

| File | Scope |
|------|-------|
| sailingsa/frontend/index.html | Popup results, multi-block view |
| sailingsa/frontend/regatta/results.html | Full regatta, all blocks |
| sailingsa/frontend/regatta/class/class-results.html | Single class, Open Fleet section |
| sailingsa/frontend/regatta/class/podium/podium.html | Podium block matching |

## Optional Columns (show if any row has data)
- Boat Name, Jib No, Bow No, Hull No, Crew
- Race columns (R1, R2, … or HYC, ZVYC, TSC for series)
