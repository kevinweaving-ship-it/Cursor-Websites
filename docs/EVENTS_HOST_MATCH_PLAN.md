# Events Host Club Auto-Match Plan

**Do NOT update the DB yet.** This document proposes mappings from `host_club_name_raw` → `club_id` for events where `host_club_id IS NULL`.

## Clubs reference

**Query:**
```sql
SELECT club_id, club_abbrev, club_fullname
FROM clubs;
```

Compare with unresolved hosts using fuzzy comparison:
- `LOWER(host_club_name_raw)` vs `LOWER(club_fullname)` / `LOWER(club_abbrev)`
- Exact match or substring match (e.g. scraped name contained in club fullname)

## Proposed mapping table

| host_club_name_raw | club_id | club_abbrev | club_fullname |
|--------------------|--------|-------------|---------------|
| *(run script to populate)* | | | |

**Unresolved count (no match):** *—*

After review, apply with:
```sql
UPDATE events SET host_club_id = :club_id WHERE host_club_name_raw = :raw AND host_club_id IS NULL;
```
