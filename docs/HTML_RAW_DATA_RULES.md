# HTML Raw Data Display Rules

## Core Rule

**HTML displays raw values from database. NO data transformations allowed.**

## Current Implementation

### regatta_viewer.html

**Race Scores** (Line 475-477):
```javascript
const v = (r.race_scores && r.race_scores[k]) || '';
const cls = PEN.test(v) ? 'code' : (DISC.test(v) ? 'disc' : '');
return `<td>${v}</td>`;
```
✅ **Displays raw value directly** - no transformation

**Total/Nett Points** (Line 479-480):
```javascript
${r.total_points_raw != null ? Number(r.total_points_raw).toFixed(1) : ''}
${r.nett_points_raw != null ? Number(r.nett_points_raw).toFixed(1) : ''}
```
✅ **Display formatting only** - database already has correct format (`.0`)

### member-finder.html

**Race Scores** (Line 2190):
```javascript
const score = raceScores[raceKey] || '';
raceCells += `<td>${score}</td>`;
```
✅ **Displays raw value directly** - no transformation

**Total/Nett Points** (Line 2201-2202):
```javascript
${Number(result.total_points_raw).toFixed(1)}
${Number(result.nett_points_raw).toFixed(1)}
```
✅ **Display formatting only** - database already has correct format

## Allowed Operations

### ✅ Display Formatting (Acceptable)
- `.toFixed(1)` for numeric display
- CSS class assignment (for styling)
- Ordinal formatting (1st, 2nd, 3rd) for ranks
- Date formatting for display

### ❌ Data Transformation (NOT ALLOWED)
- Changing decimal places (`.0` → `.00`)
- Removing/adding brackets
- Adding/removing scores from ISP codes
- Transforming ISP code format
- Changing numeric values

## Pattern Detection (OK for Styling)

HTML uses regex patterns **only for CSS styling**, not data changes:

```javascript
const PEN = /\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b/i;  // For CSS class
const DISC = /^\(.*\)$/;  // For CSS class
```

This is acceptable - it adds CSS classes but **does not modify the displayed value**.

## Checksum Rules

### ❌ HTML Does NOT Perform Checksums

HTML should **never**:
- Calculate totals from race scores
- Calculate nett from total
- Validate discard counts
- Verify format consistency

### ✅ Database/API Performs Checksums

All validation at database/API level:
- SQL scripts validate totals
- API calculates sums
- Format validation in database

## Why This Approach?

1. **Consistency**: Same data everywhere
2. **Debugging**: Issues visible in database queries
3. **Reliability**: No hidden transformations
4. **Performance**: No processing needed
5. **Maintainability**: Single source of truth

## Enforcement

**CRITICAL**: If HTML needs to transform data, **fix the database instead**.

Example:
- ❌ HTML: `value.replace('.00', '.0')` → Fix database to store `.0`
- ❌ HTML: `value + ' DNC'` → Fix database to include score
- ✅ HTML: `value.toFixed(1)` → OK (display formatting only)

## Verification

Check HTML files for transformations:
```bash
grep -n "replace\|substring\|slice" regatta_viewer.html member-finder.html
```

Should only find:
- Display formatting (acceptable)
- Pattern matching for CSS classes (acceptable)
- NOT data value changes (not allowed)



## Core Rule

**HTML displays raw values from database. NO data transformations allowed.**

## Current Implementation

### regatta_viewer.html

**Race Scores** (Line 475-477):
```javascript
const v = (r.race_scores && r.race_scores[k]) || '';
const cls = PEN.test(v) ? 'code' : (DISC.test(v) ? 'disc' : '');
return `<td>${v}</td>`;
```
✅ **Displays raw value directly** - no transformation

**Total/Nett Points** (Line 479-480):
```javascript
${r.total_points_raw != null ? Number(r.total_points_raw).toFixed(1) : ''}
${r.nett_points_raw != null ? Number(r.nett_points_raw).toFixed(1) : ''}
```
✅ **Display formatting only** - database already has correct format (`.0`)

### member-finder.html

**Race Scores** (Line 2190):
```javascript
const score = raceScores[raceKey] || '';
raceCells += `<td>${score}</td>`;
```
✅ **Displays raw value directly** - no transformation

**Total/Nett Points** (Line 2201-2202):
```javascript
${Number(result.total_points_raw).toFixed(1)}
${Number(result.nett_points_raw).toFixed(1)}
```
✅ **Display formatting only** - database already has correct format

## Allowed Operations

### ✅ Display Formatting (Acceptable)
- `.toFixed(1)` for numeric display
- CSS class assignment (for styling)
- Ordinal formatting (1st, 2nd, 3rd) for ranks
- Date formatting for display

### ❌ Data Transformation (NOT ALLOWED)
- Changing decimal places (`.0` → `.00`)
- Removing/adding brackets
- Adding/removing scores from ISP codes
- Transforming ISP code format
- Changing numeric values

## Pattern Detection (OK for Styling)

HTML uses regex patterns **only for CSS styling**, not data changes:

```javascript
const PEN = /\b(DNC|DNS|DNF|RET|DSQ|UFD|BFD|DPI|OCS)\b/i;  // For CSS class
const DISC = /^\(.*\)$/;  // For CSS class
```

This is acceptable - it adds CSS classes but **does not modify the displayed value**.

## Checksum Rules

### ❌ HTML Does NOT Perform Checksums

HTML should **never**:
- Calculate totals from race scores
- Calculate nett from total
- Validate discard counts
- Verify format consistency

### ✅ Database/API Performs Checksums

All validation at database/API level:
- SQL scripts validate totals
- API calculates sums
- Format validation in database

## Why This Approach?

1. **Consistency**: Same data everywhere
2. **Debugging**: Issues visible in database queries
3. **Reliability**: No hidden transformations
4. **Performance**: No processing needed
5. **Maintainability**: Single source of truth

## Enforcement

**CRITICAL**: If HTML needs to transform data, **fix the database instead**.

Example:
- ❌ HTML: `value.replace('.00', '.0')` → Fix database to store `.0`
- ❌ HTML: `value + ' DNC'` → Fix database to include score
- ✅ HTML: `value.toFixed(1)` → OK (display formatting only)

## Verification

Check HTML files for transformations:
```bash
grep -n "replace\|substring\|slice" regatta_viewer.html member-finder.html
```

Should only find:
- Display formatting (acceptable)
- Pattern matching for CSS classes (acceptable)
- NOT data value changes (not allowed)


















