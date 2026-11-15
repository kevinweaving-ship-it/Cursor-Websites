# GSC server-first monitoring

Ubuntu (24/7) is the **primary** collector. Mac Chrome stays as fallback until Google exposes Page Indexing in an API. **No website fixes. No GSC Validate Fix.**

Official API docs used (2025-08-28 / current):

- https://developers.google.com/webmaster-tools/v1/api_reference_index
- https://developers.google.com/webmaster-tools/v1/how-tos/authorizing
- https://developers.google.com/webmaster-tools/limits
- https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect
- https://developers.google.com/webmaster-tools/v1/sitemaps
- https://support.google.com/webmasters/answer/12918484 (BigQuery bulk export = Search **performance** only)

## Capability matrix

| Data we use from Chrome GSC UI | Official API | Server can get it? |
|---|---|---|
| Page Indexing issue/cohort **names + counts** | **No endpoint.** Search Analytics is clicks/impressions only. Bulk export tables are `searchdata_*` only. | **NO** |
| Example URLs inside each cohort | **No.** | **NO** (watchlist + sitemap sample instead) |
| Validation status (Validate Fix) | **No.** | **NO** |
| Last crawl per URL | URL Inspection `indexStatusResult.lastCrawlTime` | **YES, per URL, 2000 QPD/site** |
| Indexed / not-indexed **dashboard totals** (8.14k / 5.96k) | **No.** Sitemap `contents[].indexed` is **deprecated**. | **NO** |
| Sitemap status | `sitemaps.list` / `get` (path, submitted, lastDownloaded, errors, warnings, isPending) | **YES** |
| URL Inspection (verdict, coverageState, pageFetchState, canonicals) | `POST urlInspection/index:inspect` | **YES, per URL** |
| Search traffic 7d | `searchAnalytics.query` | **YES** (not an index count) |

Indexing API (`indexing.googleapis.com`) only **notifies** Google about JobPosting/BroadcastEvent URLs. It does not read Page Indexing.

## Auth

Google: **OAuth 2.0 only** for Search Console private data.  
Daily inspect/list: `webmasters.readonly`.  
Sitemap submit/delete: **`webmasters`** (write). New consent uses write (includes read).

Sitemap cleanup (server, no Mac Chrome):

```bash
PYTHONPATH=/opt/sailingsa-gsc python3 -m sailingsa.tools.gsc_daily.sitemap_cleanup
```

Deletes obsolete submitted feeds Google lists, then PUT `https://sailingsa.co.za/sitemap.xml`. Does not recreate `sitemap-priority.xml`. Does not call Validate Fix.

**Not used:** Chrome cookies, Google password, 2FA, copying the Mac profile to Ubuntu.

**Service account:** GSC “Add user” empirically rejects `*.iam.gserviceaccount.com`. Do not rely on it.

**Method:** Desktop OAuth client + refresh token on Ubuntu `/etc/sailingsa/gsc/` (mode 0600).

## One-time human action

Kevin, signed in as **kevinweaving@gmail.com**, clicks **Allow** on the Google consent screen (Search Console write). The collector stores the refresh token under `/etc/sailingsa/gsc/` (mode 0600). Not git, not `/var/www`.

## Daily architecture (SAST / GMT+2)

| When | What |
|---|---|
| **09:00** | `/etc/cron.d/sailingsa_gsc_daily` → live sitemap + watchlist + API (if token) + classify. Writes `/var/lib/sailingsa/gsc-daily/` |
| **10:30** | **Existing** `/etc/cron.d/sailingsa_server_monitor` `--daily` WhatsApp (Baileys `arial-whatsapp-poc`). Now appends `whatsapp_gsc.txt`. |

No second WhatsApp engine.

Mac `com.kevinweaving.gsc-daily` **stays enabled**.

## Data lost vs Chrome workflow

Until Google ships a Page Indexing API: cohort counts, Google’s example lists, Validate Fix status, and dashboard indexed/not-indexed totals. Server substitutes: sitemap submitted + errors, URL Inspection **sample**, live HTTP classification of a watchlist (prior REAL URLs + core paths + sitemap sample).

**MAC FALLBACK STILL REQUIRED: YES** — only for those UI-only Page Indexing fields.
