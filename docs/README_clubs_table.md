# CLUBS Table - GPT Rules & Data Structure

## Purpose
Stores sailing club information with proper normalization and aliasing.

## Table Structure
```sql
CREATE TABLE clubs (
    club_id SERIAL PRIMARY KEY,
    club_name TEXT NOT NULL,
    club_abbrev TEXT,  -- Short code (e.g., 'ZVYC', 'RNYC')
    province TEXT,     -- Province abbreviation (KZN, WC, GP, EC, FS, NC, MP, LP, NW)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Data Rules (from GPT instructions)

### Province Abbreviations (CRITICAL)
- **ONLY use these codes**: KZN, WC, GP, EC, FS, NC, MP, LP, NW
- **NEVER invent provinces** - use NULL if unknown
- **Extract from original data** - don't guess

### Province Icons (special icons)
- Place province icons in **artwork/Province Icons/** named by code: **WC.png**, **KZN.png**, **GP.png**, **EC.png**, **FS.png**, **NC.png**, **MP.png**, **LP.png**, **NW.png** (or .jpg / .svg). The frontend loads by province code (e.g. WC) and tries .png, then .jpg, then .svg; if none load, the code is shown as text.

### Club Abbreviation Rules
- Store short codes as they appear in results (e.g., 'ZVYC', 'RNYC')
- **NEVER modify** original abbreviations from regatta sheets
- Use `club_abbrev` for display in results tables
- Keep `club_name` for full official names

### Data Integrity Rules
1. **NEVER use placeholders** - only real data or NULL
2. **NEVER hardcode values** - always extract from source
3. **ALWAYS lookup club information** in database before inserting
4. **Preserve original abbreviations** exactly as they appear

## Related Tables
- `club_aliases` - Alternative names/abbreviations for same club
- `results.club_id` - Links to this table
- `regattas.host_club_id` - Links to this table

## API
- **GET /api/clubs** returns `{ code, name, province }`. `province` is the province abbreviation (e.g. WC, KZN) when the `clubs` table has a `province` or `province_code` column; otherwise `null`.

## Example Data
```sql
INSERT INTO clubs (club_name, club_abbrev, province) VALUES
('Zeekoevlei Yacht Club', 'ZVYC', 'WC'),
('Royal Natal Yacht Club', 'RNYC', 'KZN'),
('Henley Midmar Yacht Club', 'HMYC', 'KZN');
```
