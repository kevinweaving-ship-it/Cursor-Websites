# URL standard – all pages (https://sailingsa.co.za/)

All pages must use the same URL rules. This is the single source of truth.

**Database IDs are never part of a public path.** Do not glue `{id}-{slug}`. `/class/7-420` is not a public class URL. `7` is `classes.class_id` for 420.

---

## 1. Internal links (same site)

- **Format:** Relative path, no trailing slash, no origin in the path.
- **Examples:** `/`, `/about`, `/class/420`, `/sailor/jane-doe`, `/regatta/hyc-cape-classic-2026`, `/club/hyc`.
- **Rule:** Use relative paths so the app works on any host (localhost, sailingsa.co.za). Do not hardcode `https://sailingsa.co.za` in internal navigation links.

### Path patterns

| Page / resource | Pattern | Example |
|-----------------|---------|--------|
| **Home** | `/` | https://sailingsa.co.za/ |
| **About** | `/about` | https://sailingsa.co.za/about |
| **Class** | `/class/{slug}` | https://sailingsa.co.za/class/420 |
| **Sailor** | `/sailor/{slug}` | https://sailingsa.co.za/sailor/jane-doe |
| **Regatta (results)** | `/regatta/{slug}` | https://sailingsa.co.za/regatta/hyc-cape-classic-2026 |
| **Regatta + class** | `/regatta/{slug}/class-{classSlug}` | `/regatta/hyc-cape-classic-2026/class-420` |
| **Club** | `/club/{slug}` | https://sailingsa.co.za/club/hyc |
| **Event catalogue** | `/events-logos/{slug}` | https://sailingsa.co.za/events-logos/420-nationals |

### Banned (never emit)

| Banned | Why |
|--------|-----|
| `/class/7-420`, `/class/62-optimist-a` | `7` / `62` are database `class_id` values. Public path is `/class/420` / `/class/optimist-a`. |
| `/class/7` | Numeric class_id is not a public URL. |
| `/club/club-12` | Do not invent a club path from `club_id`. Skip if there is no slug. |
| Any `/{entity}/{numeric_db_id}-{slug}` | Internal primary keys are not public identifiers. |

Old `/class/{id}-{slug}` bookmarks **301** to `/class/{slug}`. Accept inbound; never emit.

### Slug encoding in paths

- **Path segments:** Use `encodeURIComponent(slug)` when building hrefs (sailor, club, regatta, class slug). Do not use HTML escaping in the URL path.
- **Class URLs:** `/class/{slug}` only. `slug` = `classSlugFromName(displayName)` (lowercase, spaces to hyphens, strip non-alphanumeric except hyphen). Use `_class_public_path()` in Python. Guard: `python3 sailingsa/scripts/forbid_id_slug_public_urls.py`.

---

## 2. Canonical and SEO (absolute)

- **Canonical:** Absolute URL: `https://sailingsa.co.za/class/420` (or current origin in dev). Use `window.location.origin` + path, no trailing slash.
- **og:url:** Same as canonical when set.

---

## 3. API and assets

- **API:** `window.API_BASE` or `window.location.origin` (no trailing slash). Fetch: `API_BASE + '/api/class/' + encodeURIComponent(slug)`. The API may still resolve a numeric id or an old id-slug for compatibility; public hrefs must use the slug.
- **Assets:** Relative, e.g. `/assets/class-icons/optimist-a.svg`, `/favicon-48.png`.

---

## 4. Class URLs

- **Link:** Always `/class/{slug}`. Never prefix `class_id`.
- **Route match:** Path `/class/{slug}` (example `/class/420`). Resolve the class from the slug. Do **not** parse `/^\/class\/(\d+)-/` to pull a database id out of the path.
- **Back to results:** Link to `/` (home).

---

## 5. What “same standard” means

- Every internal link uses a relative path from the table above.
- Every path segment that is a slug uses `encodeURIComponent`.
- No trailing slash on internal paths.
- Canonical and og:url use absolute URL (origin + path) when set.
- No page-specific URL format that sneaks a database id into the path.
