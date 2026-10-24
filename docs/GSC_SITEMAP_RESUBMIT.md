# Google Search Console — SailingSA

Property (live): **`sc-domain:sailingsa.co.za`** — not the URL-prefix `https://sailingsa.co.za/`.

## Submit once (write access)

Indexing → Sitemaps → Add:

| Feed | Why |
| --- | --- |
| `https://sailingsa.co.za/sitemap.xml` | Already submitted 20 Sep 2026; last fetched 23 Oct 2026 01:15 SAST |
| `https://sailingsa.co.za/sitemap-roundups.xml` | **Not in GSC yet** — hub + `/latest/` + every Monday issue |
| `https://sailingsa.co.za/sitemap-news.xml` | **Not in GSC yet** — last 48 hours only |

The live OAuth token is `webmasters.readonly`. API cannot PUT those feeds or press **Request indexing**. A Search Console owner must submit the two new feeds once (or add a service-account owner with Indexing API for `request_google_index.py --until-quota`).

## Errors Google actually raised (24 Oct 2026, Africa/Johannesburg)

Pulled from URL Inspection on `sc-domain:sailingsa.co.za`. Each row is fixed on the site so the next crawl can clear it. GSC will not flip the status until Google recrawls.

| GSC finding | Cause | Fix (verified live 24 Oct 2026 10:10 SAST) |
| --- | --- | --- |
| Events rich result **ERROR**: missing `startDate`, `location` on `/sailing-roundup/issues/2026-10-19/` | `NewsArticle.about[]` emitted a bare `SportsEvent` | Live JSON-LD now has `startDate` + `location` (ZA) + `endDate` on both 10-19 events |
| `userCanonical` missing on hub / recent issues | Tags added after last crawl | Live HTML has `<!-- ssa-gsc -->` canonical + robots. Recrawl will pick them up |
| `https://www.sailingsa.co.za/sailing-roundup/` and www issue URLs **200 duplicate** | www shared the apex 443 `server` block | www 443 now **301** to the same path on `https://sailingsa.co.za` |
| `/home` **200 duplicate** of `/` | nginx served `/home.html` | `location = /home` and `/home/` **301** to `/` |
| `…/regatta/class/podium/podium.html?regatta_id=` **200 soft-404** | Empty query served the podium shell | Apex **301** to `/events`. Valid `?regatta_id=…` still 200 |
| `/sailors` crawled, **currently not indexed** | Title was the single word `Sailors` | Title/H1 is now `South African Sailors`. Google still decides whether to index |
| Child sitemaps “not a submitted or known sitemap” | Only the index was added in GSC | Files are 200. Owner must submit `sitemap-roundups.xml` and `sitemap-news.xml` |
| `/sailing-roundup/latest/` + 23 older issues **Unknown** | Never fetched | Listed in `sitemap-roundups.xml`. Submit that feed (or Request indexing on `/latest/` first) |

Live nginx: `/etc/nginx/sites-enabled/sailingsa` is a **real file** (not a symlink to `sites-available`). Both that file and `/var/www/sailingsa/api/api.py` are `chattr +i`. Apply with `apply-gsc-fixes-live.exp` (clears/restores the immutable bit).

Not bugs: `www` homepage already 301s to apex; sitemap.xml itself is “Crawled - currently not indexed” (expected for a sitemap file); JSON feeds are `Disallow` in robots.

## Inspection 24 Oct 2026 (Africa/Johannesburg)

36 URL Inspections. Google did **not** hit the daily inspect cap (that cap is ~2000).

**Already indexed (PASS)**

| URL | Last crawl (SAST) |
| --- | --- |
| `/` | Sat 24 Oct 2026 08:54 |
| `/sailing-roundup/` | Sat 24 Oct 2026 08:54 |
| `/sailing-roundup/issues/2026-10-19/` | Wed 21 Oct 2026 04:27 |
| `/sailing-roundup/issues/2026-10-12/` | Wed 21 Oct 2026 04:27 |
| `/sailing-roundup/issues/2026-10-05/` | Wed 21 Oct 2026 04:27 |
| `/sailing-roundup/issues/2026-09-28/` | Wed 21 Oct 2026 04:25 |
| `/about` `/stats` `/events` `/classes` `/clubs` | indexed |

**Unknown to Google — ask indexing (priority order)**

1. `https://sailingsa.co.za/sailing-roundup/latest/`
2. Older issue URLs from `2026-09-21` back to `2025-12-01` (23 pages)
3. `/sailors` — recrawl after the title fix

GSC UI **Request indexing** is a small daily cap (about 10–20 URLs). Use it on `/latest/` first, then the newest unknown issues. Submitting `sitemap-roundups.xml` covers all of them without burning the per-URL cap.

## Automation

- Live files: `write_google_sitemaps.py` on Monday publish + daily cron
- Live apply: `expect sailingsa/deploy/apply-gsc-fixes-live.exp` (nginx www/`/home`/empty-podium + surgical API + re-patch issue JSON-LD)
- Optional Indexing API: `GOOGLE_INDEXING_SA_JSON` + `python3 app/request_google_index.py --until-quota` (stops when Google returns quota exhausted). Needs a service account that **owns** `sc-domain:sailingsa.co.za`.
