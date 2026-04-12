# Phase 7 — Beta Smoke Test (Production-Ready)

Run these checks against **https://sailingsa.co.za** (or your beta URL). All must PASS for Phase 7 complete.

---

## A) Backend sanity (~1 min)

| # | Action | PASS | FAIL |
|---|--------|------|------|
| 1 | Open **https://sailingsa.co.za/api/news/latest** (or `curl -s https://sailingsa.co.za/api/news/latest \| jq .`) | Response is JSON array, length > 0; each item has `title`, `url`, `published_at`; `image` may be `""`; no `news.google.com` in any `url` | Empty array, 500, 404, or all URLs are Google redirects |

---

## B) News page (~2 min)

| # | Action | PASS | FAIL |
|---|--------|------|------|
| 2 | Open **https://sailingsa.co.za/sailingsa/news/** | Page loads, header “Latest News”, single-column readable on desktop | Errors, wrong header, broken layout |
| 3 | Check layout | Item 1 = lead (large headline, 16:9 image or no image block, ~3-line excerpt). Items 2–N = compact rows (small thumb or empty, headline + Source · Date, thin divider) | Wrong layout |
| 4 | Click any headline | Opens in new tab, goes to article (not publisher homepage, not Google News) | Same tab, homepage, or Google intermediate |

---

## C) Empty + failure (~2 min)

| # | Action | PASS | FAIL |
|---|--------|------|------|
| 5 | Block `/api/news/latest` (DevTools → Network → Request blocking) or return `[]` from backend; reload **/sailingsa/news/** | Page: “No sailing news available at the moment.”; console: **exactly one** line `[news] Empty: API returned 0 items (check backend SA filter / sources).`; no retries, no spam | Wrong text, multiple log lines, retries |
| 6 | Simulate API down (offline or block domain); reload page | Same neutral empty message; console: **exactly one** line `[news] Empty: fetch failed – <message>` | Wrong message or multiple lines |

---

## D) Header + landing (~1–2 min)

| # | Action | PASS | FAIL |
|---|--------|------|------|
| 7 | Click **News** in header (desktop and mobile width) | Goes to **/sailingsa/news/** on both | Wrong URL or broken on mobile |
| 8 | Open **https://sailingsa.co.za/**; scroll to “Latest News” | Max 3 items; headline + date only; “See all” → /sailingsa/news/; if API empty → “No news at the moment.”; no console errors | Wrong count, wrong content, errors |

---

## Final gate

- **All PASS** → Phase 7 COMPLETE. Beta production ready.
- **Any FAIL** → Fix and re-run before Phase 8/9.

Optional next (only if you approve):

- **Phase 8A:** SEO + OG tags for news pages  
- **Phase 8B:** Schema.org NewsArticle markup  
- **Phase 9:** Announcement + monitoring  
