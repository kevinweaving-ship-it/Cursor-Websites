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
3. `/sailors` — crawled 25 Sep 2026 18:31 SAST, **currently not indexed**

GSC UI **Request indexing** is a small daily cap (about 10–20 URLs). Use it on `/latest/` first, then the newest unknown issues. Submitting `sitemap-roundups.xml` covers all of them without burning the per-URL cap.

## Automation

- Live files: `write_google_sitemaps.py` on Monday publish + daily cron
- Optional Indexing API: `GOOGLE_INDEXING_SA_JSON` + `python3 app/request_google_index.py --until-quota` (stops when Google returns quota exhausted). Needs a service account that **owns** `sc-domain:sailingsa.co.za`.
