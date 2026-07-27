# URL standard – all pages (https://sailingsa.co.za/)

All pages must use the same URL rules. This is the single source of truth.

---

## 1. Internal links (same site)

- **Format:** Relative path, no trailing slash, no origin in the path.
- **Examples:** `/`, `/about`, `/class/62-optimist-a`, `/sailor/jane-doe`, `/regatta/hyc-cape-classic-2026`, `/club/hyc`.
- **Rule:** Use relative paths so the app works on any host (localhost, sailingsa.co.za). Do not hardcode `https://sailingsa.co.za` in internal navigation links.

### Path patterns

| Page / resource | Pattern | Example |
|-----------------|---------|--------|
| **Home** | `/` | https://sailingsa.co.za/ |
| **About** | `/about` | https://sailingsa.co.za/about |
| **Class** | `/class/{id}-{slug}` | https://sailingsa.co.za/class/62-optimist-a |
| **Sailor** | `/sailor/{slug}` | https://sailingsa.co.za/sailor/jane-doe |
| **Regatta (results)** | `/regatta/{slug}` or `/regatta/results.html?regatta_id=…` | https://sailingsa.co.za/regatta/hyc-cape-classic-2026 |
| **Regatta + class** | `/regatta/{slug}/class-{classSlug}` | Used in links from class page to regatta filtered by class |
| **Club** | `/club/{slug}` | https://sailingsa.co.za/club/hyc |

### Slug encoding in paths

- **Path segments:** Use `encodeURIComponent(slug)` when building hrefs (sailor, club, regatta, class slug). Do not use HTML escaping (`escapeClassHtml` etc.) in the URL path.
- **Class URLs:** `/class/{id}-{slug}` where `id` is numeric (no encoding), `slug` = `encodeURIComponent(classSlugFromName(displayName))`.

---

## 2. Canonical and SEO (absolute)

- **Canonical:** Set to absolute URL: `https://sailingsa.co.za/class/62-optimist-a` (or current origin in dev). Use `window.location.origin` + path, no trailing slash.
- **og:url:** Same as canonical when set (e.g. sailor page, class page).

---

## 3. API and assets

- **API:** `window.API_BASE` or `window.location.origin` (no trailing slash). Fetch URLs: `API_BASE + '/api/class/' + encodeURIComponent(id)`.
- **Assets:** Relative, e.g. `/assets/class-icons/optimist-a.svg`, `/favicon-48.png`.

---

## 4. Class URLs – standard

- **Link to class page:** Always `/class/{id}-{slug}` when `class_id` is known; otherwise `/class/{slug}`. Slug from `classSlugFromName(name)` (lowercase, spaces to hyphens, strip non‑alphanumeric except hyphen), then `encodeURIComponent(slug)` in the href.
- **Route match:** Path like `/class/62-optimist-a` is matched by `/^\/class\/(\d+)-/` to get numeric id; API call uses that id.
- **Back to results:** Link to `/` (home).

---

## 5. What “same standard” means

- Every internal link uses a relative path from the table above.
- Every path segment that is a slug uses `encodeURIComponent`.
- No trailing slash on internal paths.
- Canonical and og:url use absolute URL (origin + path) when set.
- All pages (Class, Sailor, Regatta, Club, About, Home) follow this; no page-specific URL format.
