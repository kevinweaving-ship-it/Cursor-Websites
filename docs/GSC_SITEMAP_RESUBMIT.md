# Google Search Console — SailingSA

Property (live): **`sc-domain:sailingsa.co.za`** — not the URL-prefix `https://sailingsa.co.za/`.

## Feeds Google already has (or was asked to take)

| Feed | Why |
| --- | --- |
| `https://sailingsa.co.za/sitemap.xml` | Already submitted 20 Sep 2026; last fetched 23 Oct 2026 01:15 SAST. Index lists classes, clubs, news, regattas, roundups, sailors |
| `https://sailingsa.co.za/sitemap-roundups.xml` | Hub + `/latest/` + every Monday issue. File 200. Not yet a GSC-submitted child |
| `https://sailingsa.co.za/sitemap-news.xml` | Last 48 hours only (`news:news`). File 200, currently empty urlset |

Tried from both boxes 24 Oct 2026 12:20 SAST and again 10:40 SAST:

| Path | Result |
| --- | --- |
| Sitemap PUT (`webmasters` write) | **403** insufficient scopes — live token is `webmasters.readonly` |
| Indexing API `URL_UPDATED` | **403** same token has no `auth/indexing` |
| `google.com/ping?sitemap=` | **404** (Google removed this in 2023) |
| URL Inspection of every loc in `sitemap-roundups.xml` plus the three sitemap files | **200** — this is the write the live token has. It does not press GSC **Request indexing** |
| Live Chrome `/root/.config/google-chrome` and `/root/gsc-oauth-chrome` | Not signed in (NID/OTZ/GAPS only) |
| Mac Mini worker `43e56b9a-…` | Connected, idle, approved, `eligibleForSubagent`. Task / `environment:local` still boot Linux. This Cloud session has no `CreateAgent` tool. Home IP `41.71.67.74:22` closed from both boxes |
| GoWifi → live publish key | Works (`rea` `id_rea_publish` → `root@102.218.215.253`) |

`/sailing-roundup/` and `/` are already **Submitted and indexed** (last crawl 24 Oct 2026 08:54 SAST). `/sailing-roundup/latest/` and 23 older issues are still **Unknown**. `/sailors` is still **Crawled - currently not indexed** (25 Sep 2026 18:31 SAST). `/home` is still listed indexed from 22 Oct — Google has not recrawled the new 301 yet.

## Errors Google actually raised (24 Oct 2026, Africa/Johannesburg)

Pulled from URL Inspection on `sc-domain:sailingsa.co.za`. Each row is fixed on the site so the next crawl can clear it. GSC will not flip the status until Google recrawls.

| GSC finding | Cause | Fix (verified live 24 Oct 2026 12:10 SAST) |
| --- | --- | --- |
| Events rich result **ERROR**: missing `startDate`, `location` on `/sailing-roundup/issues/2026-10-19/` | `NewsArticle.about[]` emitted a bare `SportsEvent` | Live JSON-LD now has `startDate` + `location` (ZA) + `endDate` on both 10-19 events |
| `userCanonical` missing on hub / recent issues | Tags added after last crawl | Live HTML has `<!-- ssa-gsc -->` canonical + robots. Recrawl will pick them up |
| `https://www.sailingsa.co.za/sailing-roundup/` and www issue URLs **200 duplicate** | www shared the apex 443 `server` block | www 443 now **301** to the same path on `https://sailingsa.co.za` |
| `/home` **200 duplicate** of `/` | nginx served `/home.html` | `location = /home` and `/home/` **301** to `/` |
| `…/regatta/class/podium/podium.html?regatta_id=` **200 soft-404** | Empty query served the podium shell | Apex **301** to `/events`. Valid `?regatta_id=…` still 200 |
| `/sailors` crawled, **currently not indexed** | Title was the single word `Sailors` | Title/H1 is now `South African Sailors`. Google still decides whether to index |
| Child sitemaps “not a submitted or known sitemap” | Only the index was added in GSC | Files are 200 and listed in the already-submitted `sitemap.xml` index. Sitemap PUT from both boxes is 403 (`webmasters.readonly`). URL Inspection of the three sitemap files ran 24 Oct 2026 10:40 SAST |
| `/sailing-roundup/latest/` + 23 older issues **Unknown** | Never fetched | Listed in `sitemap-roundups.xml`. URL Inspection of every loc in that feed ran from live; Indexing API `URL_UPDATED` is 403 without an owning service account |

Live nginx: `/etc/nginx/sites-enabled/sailingsa` is a **real file** (not a symlink to `sites-available`). Both that file and `/var/www/sailingsa/api/api.py` are `chattr +i`. Apply with `apply-gsc-fixes-live.exp` (clears/restores the immutable bit).

Not bugs: `www` homepage already 301s to apex; sitemap.xml itself is “Crawled - currently not indexed” (expected for a sitemap file); JSON feeds are `Disallow` in robots.

## Inspection 24 Oct 2026 (Africa/Johannesburg)

39 URL Inspections at 10:40 SAST (every loc in `sitemap-roundups.xml` plus the three sitemap files, `/`, `/sailors`, `/about`, `/events`, `/home`). Google did **not** hit the daily inspect cap (~2000). Live sitemaps were rewritten first: 28 issues / 30 roundup URLs / 0 news URLs (48h window).

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

**Unknown to Google after inspection (priority still queued via sitemap + inspect)**

1. `https://sailingsa.co.za/sailing-roundup/latest/`
2. Older issue URLs from `2026-09-21` back to `2025-12-01` (23 pages)
3. `/sailors` — recrawl after the title fix

GSC UI **Request indexing** (~10–20/day) and sitemap PUT need a signed-in Mac Chrome session (`~/Desktop/sailingsa-clean/sailingsa/tools/gsc_daily/chrome_mac.py`) or a `webmasters` + `indexing` token that owns `sc-domain:sailingsa.co.za`. Neither exists on live, GoWifi, or this Cloud VM. The Mac worker is connected; placement from this Cloud Agent is Task-only and stays on Linux.

## Automation

**One daily GSC tool:** `/etc/cron.d/sailingsa_gsc_daily` → `/usr/local/sbin/sailingsa-gsc-daily` at 09:00 Africa/Johannesburg → `python3 -m sailingsa.tools.gsc_daily.run_server_daily`. It inspects, classifies, and applies the known remediations (`autofix.py`). Do not add a second fixer cron. `--no-fix` collects only.

- Sitemap *files*: Monday publish `write_google_sitemaps.py` + `/etc/cron.d/sailingsa_sitemap_refresh` every 15 minutes (writer, not a second GSC checker)
- Manual live apply if cron is down: `expect sailingsa/deploy/apply-gsc-fixes-live.exp`
- Optional Indexing API: `GOOGLE_INDEXING_SA_JSON` + `python3 app/request_google_index.py --until-quota`. Needs a service account that **owns** `sc-domain:sailingsa.co.za`.
