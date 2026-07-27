# Event Type URLs

Future URLs: **`/events/type/{slug}`**

For each distinct `events.category`, produce:

- **slug** (e.g. `regional-championships`, `nationals`)
- **display name** (original category)
- **event count**

**Source:** `SELECT DISTINCT category FROM events WHERE category IS NOT NULL ORDER BY category` plus `COUNT(*)` per category.

| slug | display name | event count |
|------|---------------|-------------|
| *(run script to populate)* | | |

Example:
- `regional-championships` → Regional Championships → 23 events
- `nationals` → Nationals → 15 events
