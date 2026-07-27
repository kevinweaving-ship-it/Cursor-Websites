# Final verification: class-filtered regatta pages

Run these in order. All tests must pass for production-ready.

---

## 1️⃣ Run migration

```bash
# From project root, with DB_URL set (e.g. source .env)
psql "$DB_URL" -f database/migrations/165_results_regatta_class_index.sql
```

Then confirm the index exists:

```bash
psql "$DB_URL" -c "SELECT indexname FROM pg_indexes WHERE tablename='results' ORDER BY indexname;"
```

**Expected:** `ix_results_regatta_class` appears in the list.

---

## 2️⃣ Test canonical redirects

| Test | URL | Expected |
|------|-----|----------|
| **Valid canonical** | `/regatta/385-2026-hyc-cape-classic/class-420` | 200, page shows 420 fleet only |
| **Event-name slug** | `/regatta/hyc-cape-classic-2026/class-420` | **301** → `/regatta/385-2026-hyc-cape-classic/class-420` |
| **Non-canonical class slug** | `/regatta/385-2026-hyc-cape-classic/class-7-420` | **301** → `/regatta/385-2026-hyc-cape-classic/class-420` |

How to test (local or live):

```bash
# Event-name redirect (replace origin with your host)
curl -sI "https://sailingsa.co.za/regatta/hyc-cape-classic-2026/class-420" | grep -E "HTTP|Location"

# Non-canonical class slug redirect
curl -sI "https://sailingsa.co.za/regatta/385-2026-hyc-cape-classic/class-7-420" | grep -E "HTTP|Location"
```

---

## 3️⃣ Test invalid classes (must 404)

| URL | Expected |
|-----|----------|
| `/regatta/385-2026-hyc-cape-classic/class-optimist` | **404** |
| `/regatta/385-2026-hyc-cape-classic/class-ilca` | **404** |
| `/regatta/385-2026-hyc-cape-classic/class-laser` | **404** |

These have no exact match in `classes` (e.g. "Optimist A" exists, "optimist" does not).

```bash
curl -sI "https://sailingsa.co.za/regatta/385-2026-hyc-cape-classic/class-optimist" | head -1
# Expected: HTTP/1.1 404 Not Found
```

---

## 4️⃣ Full regatta page fleet links

1. Open **`/regatta/385-2026-hyc-cape-classic`** (full regatta page).
2. Find the **420 Fleet** (or similar) section header.
3. The header should be a link.
4. Click it (or inspect): href must be **`/regatta/385-2026-hyc-cape-classic/class-420`**.

Same for other classes (e.g. **ILCA 6** → `/regatta/385-2026-hyc-cape-classic/class-ilca-6`).

---

## 5️⃣ Sitemap

1. Open **`https://sailingsa.co.za/sitemap.xml`** (or local equivalent).
2. Confirm entries exist for:
   - `/regatta/385-2026-hyc-cape-classic/class-420`
   - `/regatta/385-2026-hyc-cape-classic/class-ilca-6`
   - `/regatta/385-2026-hyc-cape-classic/class-optimist-a`

(Exact regatta slug in sitemap may be event-name slug; server will 301 to canonical.)

```bash
curl -s "https://sailingsa.co.za/sitemap.xml" | grep -o 'regatta/[^<]*class-[^<]*' | head -20
```

---

## Code reference (for reviewers)

- **Class validation:** `_resolve_class_slug_to_class_id()` → `_get_class_by_name_slug()` / `_get_class_name_by_id()`; only `classes` table.
- **Canonical:** `serve_regatta_class_standalone()` uses `regatta_id` and `_class_canonical_slug(class_name)`; 301 for event-name slug and non-canonical class slug.
- **Fleet count:** `if len(fleets) != 1: return 404`.
- **Fleet header link:** `_render_result_sheet_fleet()` builds `<a href="/regatta/{regatta_id}/class-{class_slug}">` when fleet has `regatta_id` and `class_slug`.
- **Sitemap:** `_sitemap_regatta_class_entries()` → `_build_sitemap_xml()` adds only distinct (regatta_slug, class_slug) with results.
- **Index:** `database/migrations/165_results_regatta_class_index.sql` creates `ix_results_regatta_class` on `results(regatta_id, class_id)`.

---

If all tests pass, the class-filtered regatta architecture is **production-ready**.
