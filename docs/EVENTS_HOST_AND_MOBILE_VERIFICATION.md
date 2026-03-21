# Events host parsing + mobile header — verification

## PART 1 — Verify stored host strings

Run on your DB:

```sql
SELECT
  event_name,
  host_club_name_raw
FROM events
WHERE host_club_name_raw LIKE '%·%'
LIMIT 30;
```

Or to catch middle dot (U+00B7), bullet (U+2022), or pipe:

```sql
SELECT event_name, host_club_name_raw
FROM events
WHERE host_club_name_raw LIKE '%·%'
   OR host_club_name_raw LIKE '%•%'
   OR host_club_name_raw LIKE '%|%'
LIMIT 30;
```

Expected pattern: `LASA (Laser Association of South Africa) · Saldanha Bay Yacht Club`  
Parsing supports **·** (U+00B7), **•** (U+2022), and **|**. If your data uses another character, add it to `_HOST_SEPARATORS` in `api.py`.

---

## PART 2 — Parsed host display

In **`_event_row_to_card()`** host is derived **before** any other host logic:

1. `raw_from_db = (r.get("host_club_name_raw") or "").strip() or (r.get("venue_raw") or "").strip()`
2. `host_display = _parse_host_after_separator(raw_from_db) or ""`
3. **`host_display`** is the only value used for club matching and fallback display.

**`_parse_host_after_separator(raw)`** returns the segment **after** the last occurrence of ·, •, or |. So the association part is never used for display or matching.

---

## PART 3 — Club match query

One query per page load (in `_get_upcoming_events` and `_get_events_by_type_slug`):

```sql
SELECT club_id, club_abbrev, club_fullname
FROM clubs
WHERE lower(trim(COALESCE(club_fullname,''))) = ANY(%s)
   OR lower(trim(COALESCE(club_abbrev,''))) = ANY(%s)
```

Params = list of normalized `host_display` values (e.g. `"Saldanha Bay Yacht Club"`).  
If the clubs row has `club_abbrev = 'SBYC'` and `club_fullname = 'Saldanha Bay Yacht Club'`, that row is returned and the event card gets `host_code = SBYC`, `host_club_fullname = Saldanha Bay Yacht Club`.

---

## PART 4 — Event card output

When a club is matched, the card shows:

**Host: SBYC (Saldanha Bay Yacht Club)**

Not the association (e.g. not "LASA (Laser Association...)" or "29er Class Associati").  
Template uses parentheses: `' (' + esc(e.host_club_fullname) + ')'`.

---

## PART 5 — Mobile header CSS

In **`sailingsa/frontend/css/main.css`** inside `@media (max-width: 768px)`:

```css
/* Header nav: single row on mobile, no wrapping */
.site-header nav,
.site-header .nav-inline {
    display: flex;
    flex-wrap: nowrap;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-right: 0;
}
.site-header nav a {
    font-size: 12px;
    white-space: nowrap;
}
```

There is **no** `flex-wrap: wrap` or `display: block` on header nav in this breakpoint; the block above overrides the desktop `.site-header .nav-inline { flex-wrap: wrap }`.

---

## PART 6 — Mobile check

On a viewport ≤ 768px the header should show:

**Home Sailors Regattas Classes Clubs Statistics About**

on a **single line** (no wrap).
