# Layout check: Home (/) vs Class (/class/62-optimist-a)

**Live:** [Home](https://sailingsa.co.za/) | [Class](https://sailingsa.co.za/class/62-optimist-a)

---

## Expected structure

### Home (/)
- **Same wrapper:** `layout-three-col` → `main-column` → `.container`
- **Visible:** datetime → intro box (2 paras) → search (Sailor/Regatta/Club/Class) → profile placeholder → site-stats iframe → Latest News
- **Styles:** `/css/main.css` (root-relative so it loads); intro uses `.home-intro-box` (border, radius, shadow)

### Class (/class/62-optimist-a)
- **Same wrapper:** same `layout-three-col` → `main-column` → `.container`
- **Visible:** only `#class-view`; all other `.container` children are `display:none`
- **Inside #class-view:** datetime → intro ("About" + "Class results, regattas…") → Back to results → **Title card (Optimist A)** → **Stats card (Regattas 26, Clubs 22, …)** → **REGATTAS card (table)** → Clubs card (if any) → Sailors card
- **Styles:** same `/css/main.css`; cards use `.card` (same box style as intro: border, radius, shadow from main.css)

---

## Layout issues to check (live)

1. **Class page: boxes not visible**  
   - Cause: `/css/main.css` not loading (e.g. old relative `css/main.css` on class path → 404).  
   - Fix in code: use `href="/css/main.css"` (done). Verify live has that link.

2. **Class page: looks like home (search + profile visible)**  
   - Cause: JS not hiding other `.container` children or not showing `#class-view`.  
   - Check: route match `/^\/class\/(\d+)-/`, API `/api/class/{id}` returns 200, `renderClassPage` runs, then hide loop runs.

3. **Class page: double padding or narrow content**  
   - Cause: `.container` twice (outer + `.master-page-layout.container`).  
   - Acceptable; both use same padding. If too narrow, reduce inner container padding or max-width in main.css.

4. **Mobile: class page different from home**  
   - Both use same `.container` padding (0.75rem 12px), same `.card` (mobile first).  
   - If class looks different, compare `.card` and `.home-intro-box` in main.css and inline styles.

5. **Class page: iframe or script errors**  
   - `site-stats-embed` is hidden on class page but iframe still has `src="site-stats.html"` → on class URL that resolves to `/class/site-stats.html` (404). Doesn’t affect layout; iframe is hidden. Optional: set iframe `src` only when not on class route.

---

## Quick verification (manual)

| Check | Home | Class |
|-------|------|--------|
| Page title | South African Sailing Results… | Optimist A – Class \| SailingSA |
| Datetime at top | Yes | Yes (from #class-page-datetime) |
| Intro-style box | Yes (2 paras) | Yes ("About" + 1 para) |
| Search bar | Yes | No (hidden) |
| Back to results | In profile placeholder | Yes (above title card) |
| Bordered cards | N/A (profile card, news) | Title, Stats, REGATTAS, Clubs, Sailors |
| main.css loaded | Yes | Yes (check DevTools Network for /css/main.css 200) |

---

## Fetch comparison (static content)

- **Home fetch:** Returns SPA shell + visible copy (search, Sailor Profile, Latest News, modals).
- **Class fetch:** Same shell; title is "Optimist A – Class | SailingSA". Class-specific content (Optimist A card, stats, table) is injected by JS after load, so it may not appear in a simple HTML fetch. Use DevTools or Cursor Browser to confirm boxes and table after load.
