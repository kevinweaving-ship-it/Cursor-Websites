# RACE SCORES STORAGE - GPT Rules & JSONB Format

## Purpose
Documents how race scores are stored in the `race_scores` JSONB field in the `results` table.

## Storage Format
Race scores are stored as JSONB with keys R1, R2, R3, etc.:

```json
{
  "R1": "1.0",
  "R2": "(2.0)", 
  "R3": "1.0",
  "R4": "6.0 DNC",
  "R5": "2.0",
  "R6": "1.0",
  "R7": "1.0",
  "R8": "1.0"
}
```

## Data Rules (from GPT instructions)

### Race Score Values (CRITICAL)
- **Normal finishes**: Store as numeric strings (e.g., "1.0", "2.0", "3.0")
- **Discarded scores**: Store in parentheses (e.g., "(2.0)", "(6.0)")
- **Penalty codes**: Store as score + code (e.g., "6.0 DNC", "5.0 OCS")

### World Sailing Result Codes (from GPT rules)
- **DNC**: Did Not Compete (score = entries + 1)
- **OCS**: On Course Side (score = entries + 1)  
- **DNS**: Did Not Start (score = entries + 1)
- **DSQ**: Disqualified (score = entries + 1)
- **DNF**: Did Not Finish (score = entries + 1)
- **RET**: Retired (score = entries + 1)
- **BFD**: Black Flag Disqualification
- **UFD**: U Flag Disqualification
- **DPI**: Discretionary Penalty Imposed

### Discard Identification
- **Discarded scores**: Always in parentheses `(score)`
- **Example**: `"(2.0)"` means score of 2.0 was discarded
- **Multiple discards**: Each in separate parentheses

### Display Formatting Rules
- **Non-ISP Discards**: Display in **YELLOW** brackets: `(14.0)`, `(11.0)`
- **ISP Codes**: Display in **RED**: `18.0 DNC`, `18.0 DNF`, `21.0 OCS`
- **ISP Discards**: Display in **RED** brackets: `(18.0 DNC)`, `(21.0 DNF)`
- See `docs/README_DISPLAY_RULES.md` for complete display formatting rules

### Data Integrity Rules
1. **NEVER modify penalty codes** - preserve exactly as in original
2. **NEVER remove parentheses** - they indicate discards
3. **NEVER convert to numeric** - keep as strings with codes
4. **ALWAYS preserve original format** from results sheet
5. **ALWAYS store both score and code** for penalties

## Calculation Rules (from GPT checksum rules)

### Total Points Calculation
- Sum ALL race scores (including discarded ones)
- **DNC/DNS/OCS codes**: Treat as `entries + 1` points
- **Example**: 5 entries, DNC = 6.0 points

### Nett Points Calculation  
- Total points MINUS discarded scores
- **Validation**: `nett + total_discard = total`
- **Example**: Total 11.0, discard 2.0, nett = 9.0

### Example Checksums (from GPT rules)
**1st Place**: 1.0+2.0+1.0+2.0+2.0+1.0+1.0+1.0 = 11.0 total, -2.0 discard = 9.0 nett ✓
**2nd Place**: 3.0+6.0+3.0+1.0+1.0+2.0+2.0+2.0 = 20.0 total, -6.0 discard = 14.0 nett ✓

## SQL Access Patterns
```sql
-- Get specific race score
SELECT race_scores->>'R1' FROM results WHERE result_id = 123;

-- Check for penalty codes
SELECT * FROM results WHERE race_scores::text ~* 'DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS';

-- Count penalty occurrences
SELECT SUM((race_scores::text ~* 'DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS')::int) 
FROM results WHERE regatta_id = '359-2025-zvyc-southern-charter-cape-classic';
```


-- Count penalty occurrences
SELECT SUM((race_scores::text ~* 'DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS')::int) 
FROM results WHERE regatta_id = '359-2025-zvyc-southern-charter-cape-classic';
```
