# Display Rules for Regatta Results

## Purpose
Documents the visual formatting rules for displaying regatta results in the HTML viewer, including rank ordinals, name display, and score formatting with colors and brackets.

## Rank Ordinal Display Rules (CRITICAL)

### Correct Ordinal Formatting
Ranks must be displayed with correct ordinal suffixes:
- **1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th, 9th, 10th**
- **11th, 12th, 13th** (special cases - always "th")
- **21st, 22nd, 23rd, 24th, 25th, etc.**

### ❌ NEVER Use Incorrect Ordinals
- **WRONG**: `"2st"`, `"3st"`, `"4st"`, `"5st"`, etc.
- **WRONG**: `"11st"`, `"12st"`, `"13st"`
- **WRONG**: `"21st"` when it should be `"21st"` (this one is correct, but 22nd, 23rd are different)

### Implementation
- Use database function `integer_to_ordinal(rank)` which correctly handles all cases
- Or implement proper logic:
  ```javascript
  function formatOrdinal(rank) {
    if (rank % 100 in [11, 12, 13]) return rank + 'th';
    if (rank % 10 === 1) return rank + 'st';
    if (rank % 10 === 2) return rank + 'nd';
    if (rank % 10 === 3) return rank + 'rd';
    return rank + 'th';
  }
  ```

## Name Display Rules (CRITICAL)

### ⚠️ HARD RULE: Use SA ID Table Name When SA ID Present

**When a result has an SA ID** (`helm_sa_sailing_id` or `crew_sa_sailing_id` is NOT NULL):
- **MUST use the exact name from `sas_id_personal` table**
- **NEVER use the name from the results sheet** if it doesn't match exactly
- The SA ID table is the authoritative source for names

### Examples
- Results sheet: "JP Myburgh" → SA ID 4176 has "Jean-Pierre Myburgh" → **Display: "Jean-Pierre Myburgh"**
- Results sheet: "Stephen Proudfoot" → SA ID 11898 has "Stephan Proudfoot" → **Display: "Stephan Proudfoot"**
- Results sheet: "Shawn Paul Pretorius" → SA ID 17764 has "Shawn Pretorius" → **Display: "Shawn Pretorius"**
- Results sheet: "Vaughn Klibbe" → SA ID 2063 has "Vaughan Klibbe" → **Display: "Vaughan Klibbe"**

### Implementation
```sql
-- When inserting/updating results with SA IDs:
UPDATE results r
SET helm_name = COALESCE(s.full_name, s.first_name || ' ' || s.last_name)
FROM sas_id_personal s
WHERE r.helm_sa_sailing_id::text = TRIM(LEADING '0' FROM s.sa_sailing_id::text)
  AND r.helm_name != COALESCE(s.full_name, s.first_name || ' ' || s.last_name);
```

## Race Score Display Rules

### Discard Display (Brackets)
- **All discarded scores MUST be displayed in parentheses**: `(11.0)`, `(4.0)`, `(18.0 DNC)`
- Brackets indicate the score was discarded and not counted in nett points
- Discards are calculated from worst scores (highest numeric value first)

### ISP Code Display (Red Color)
- **ISP codes MUST be displayed in RED color**
- ISP codes include: DNC, DNS, DNF, RET, DSQ, UFD, BFD, DPI, OCS
- Examples: `18.0 DNC`, `18.0 DNF`, `21.0 OCS`
- **Excluded**: ONF, DNE are NOT ISP codes (do not color red)

### Discard Color Rules
1. **Non-ISP Discards** (Yellow):
   - Discarded scores WITHOUT ISP codes
   - Display: `(14.0)`, `(11.0)`, `(4.0)` in **YELLOW** brackets
   - CSS class: `.disc` (color: #ffd166)

2. **ISP Discards** (Red):
   - Discarded scores WITH ISP codes
   - Display: `(18.0 DNC)`, `(21.0 DNF)`, `(18.0 OCS)` in **RED** brackets
   - CSS class: `.code.disc` (color: #ff6b6b)

3. **Non-Discarded ISP Codes** (Red):
   - ISP codes that are NOT discarded
   - Display: `18.0 DNC`, `21.0 DNF` (no brackets) in **RED**
   - CSS class: `.code` (color: #ff6b6b)

### Visual Examples
```
Normal score:        3.0          (white text)
Discarded (non-ISP): (11.0)       (yellow text)
ISP code:            18.0 DNC     (red text)
ISP discarded:       (18.0 DNC)   (red text)
```

### CSS Classes
```css
.disc { color: #ffd166; }              /* Yellow for non-ISP discards */
.code { color: #ff6b6b !important; }  /* Red for ISP codes */
.code.disc { color: #ff6b6b !important; } /* Red for ISP discards */
```

## Implementation Checklist

### When Inserting Results:
- [ ] Use `integer_to_ordinal(rank)` for `rank_ordinal` column
- [ ] Verify rank ordinals are correct (1st, 2nd, 3rd, not 2st, 3st)
- [ ] If SA ID exists, use name from `sas_id_personal` table, not results sheet
- [ ] Store race scores with ISP codes: `"18.0 DNC"`, not just `"18.0"`
- [ ] Store discards in parentheses: `"(11.0)"` for discarded scores

### When Displaying Results:
- [ ] Calculate which races are discarded (worst scores first)
- [ ] Add parentheses around discarded scores if not already present
- [ ] Detect ISP codes using pattern: `/[0-9]+\.0 (?!ONF|DNE)(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS|[A-Z]{3,})/i`
- [ ] Apply yellow class (`.disc`) for non-ISP discards
- [ ] Apply red class (`.code`) for ISP codes
- [ ] Apply red class (`.code.disc`) for ISP discards

## Related Documentation
- `docs/README_results_table.md` - Results table structure and rules
- `docs/README_race_scores_storage.md` - Race scores storage format
- `docs/README_sas_id_personal.md` - SA ID table structure



## Purpose
Documents the visual formatting rules for displaying regatta results in the HTML viewer, including rank ordinals, name display, and score formatting with colors and brackets.

## Rank Ordinal Display Rules (CRITICAL)

### Correct Ordinal Formatting
Ranks must be displayed with correct ordinal suffixes:
- **1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th, 9th, 10th**
- **11th, 12th, 13th** (special cases - always "th")
- **21st, 22nd, 23rd, 24th, 25th, etc.**

### ❌ NEVER Use Incorrect Ordinals
- **WRONG**: `"2st"`, `"3st"`, `"4st"`, `"5st"`, etc.
- **WRONG**: `"11st"`, `"12st"`, `"13st"`
- **WRONG**: `"21st"` when it should be `"21st"` (this one is correct, but 22nd, 23rd are different)

### Implementation
- Use database function `integer_to_ordinal(rank)` which correctly handles all cases
- Or implement proper logic:
  ```javascript
  function formatOrdinal(rank) {
    if (rank % 100 in [11, 12, 13]) return rank + 'th';
    if (rank % 10 === 1) return rank + 'st';
    if (rank % 10 === 2) return rank + 'nd';
    if (rank % 10 === 3) return rank + 'rd';
    return rank + 'th';
  }
  ```

## Name Display Rules (CRITICAL)

### ⚠️ HARD RULE: Use SA ID Table Name When SA ID Present

**When a result has an SA ID** (`helm_sa_sailing_id` or `crew_sa_sailing_id` is NOT NULL):
- **MUST use the exact name from `sas_id_personal` table**
- **NEVER use the name from the results sheet** if it doesn't match exactly
- The SA ID table is the authoritative source for names

### Examples
- Results sheet: "JP Myburgh" → SA ID 4176 has "Jean-Pierre Myburgh" → **Display: "Jean-Pierre Myburgh"**
- Results sheet: "Stephen Proudfoot" → SA ID 11898 has "Stephan Proudfoot" → **Display: "Stephan Proudfoot"**
- Results sheet: "Shawn Paul Pretorius" → SA ID 17764 has "Shawn Pretorius" → **Display: "Shawn Pretorius"**
- Results sheet: "Vaughn Klibbe" → SA ID 2063 has "Vaughan Klibbe" → **Display: "Vaughan Klibbe"**

### Implementation
```sql
-- When inserting/updating results with SA IDs:
UPDATE results r
SET helm_name = COALESCE(s.full_name, s.first_name || ' ' || s.last_name)
FROM sas_id_personal s
WHERE r.helm_sa_sailing_id::text = TRIM(LEADING '0' FROM s.sa_sailing_id::text)
  AND r.helm_name != COALESCE(s.full_name, s.first_name || ' ' || s.last_name);
```

## Race Score Display Rules

### Discard Display (Brackets)
- **All discarded scores MUST be displayed in parentheses**: `(11.0)`, `(4.0)`, `(18.0 DNC)`
- Brackets indicate the score was discarded and not counted in nett points
- Discards are calculated from worst scores (highest numeric value first)

### ISP Code Display (Red Color)
- **ISP codes MUST be displayed in RED color**
- ISP codes include: DNC, DNS, DNF, RET, DSQ, UFD, BFD, DPI, OCS
- Examples: `18.0 DNC`, `18.0 DNF`, `21.0 OCS`
- **Excluded**: ONF, DNE are NOT ISP codes (do not color red)

### Discard Color Rules
1. **Non-ISP Discards** (Yellow):
   - Discarded scores WITHOUT ISP codes
   - Display: `(14.0)`, `(11.0)`, `(4.0)` in **YELLOW** brackets
   - CSS class: `.disc` (color: #ffd166)

2. **ISP Discards** (Red):
   - Discarded scores WITH ISP codes
   - Display: `(18.0 DNC)`, `(21.0 DNF)`, `(18.0 OCS)` in **RED** brackets
   - CSS class: `.code.disc` (color: #ff6b6b)

3. **Non-Discarded ISP Codes** (Red):
   - ISP codes that are NOT discarded
   - Display: `18.0 DNC`, `21.0 DNF` (no brackets) in **RED**
   - CSS class: `.code` (color: #ff6b6b)

### Visual Examples
```
Normal score:        3.0          (white text)
Discarded (non-ISP): (11.0)       (yellow text)
ISP code:            18.0 DNC     (red text)
ISP discarded:       (18.0 DNC)   (red text)
```

### CSS Classes
```css
.disc { color: #ffd166; }              /* Yellow for non-ISP discards */
.code { color: #ff6b6b !important; }  /* Red for ISP codes */
.code.disc { color: #ff6b6b !important; } /* Red for ISP discards */
```

## Implementation Checklist

### When Inserting Results:
- [ ] Use `integer_to_ordinal(rank)` for `rank_ordinal` column
- [ ] Verify rank ordinals are correct (1st, 2nd, 3rd, not 2st, 3st)
- [ ] If SA ID exists, use name from `sas_id_personal` table, not results sheet
- [ ] Store race scores with ISP codes: `"18.0 DNC"`, not just `"18.0"`
- [ ] Store discards in parentheses: `"(11.0)"` for discarded scores

### When Displaying Results:
- [ ] Calculate which races are discarded (worst scores first)
- [ ] Add parentheses around discarded scores if not already present
- [ ] Detect ISP codes using pattern: `/[0-9]+\.0 (?!ONF|DNE)(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS|[A-Z]{3,})/i`
- [ ] Apply yellow class (`.disc`) for non-ISP discards
- [ ] Apply red class (`.code`) for ISP codes
- [ ] Apply red class (`.code.disc`) for ISP discards

## Related Documentation
- `docs/README_results_table.md` - Results table structure and rules
- `docs/README_race_scores_storage.md` - Race scores storage format
- `docs/README_sas_id_personal.md` - SA ID table structure


















