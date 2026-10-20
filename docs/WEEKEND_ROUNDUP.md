# Weekend Roundup (Monday weekly)

Public URLs: `https://sailingsa.co.za/sailing-roundup/` and `…/issues/YYYY-MM-DD/`.

This is a **Monday weekly**, not Sat–Sun only. Midweek races, long weekends, and multi-week events are included. The name on the site stays Weekend Roundup.

## Assignment rule

An event is in **exactly one** Monday issue: the **Monday after the week the event ended**.

- Finish Sunday 27 Sep → issue Monday **28 Sep**
- Finish Wednesday 15 Apr → issue Monday **20 Apr** (week of 13–19 Apr)
- Multi-week event ending Tuesday 15 Dec → issue Monday **21 Dec** (week of 14–20 Dec)
- Empty weeks (no racing events finished) → **no URL**

SailingSA results (names, scores, classes, sailors) are the source of truth. REA then pulls club sites, class socials, Google, and sailor Media-tab mentions for copy and photographs. No Wikimedia. No invented photos.

Historical 2026 (and later years) is the same pipeline, not a results-only stub:

```bash
python3 gowifi/rea/sailing-roundup/app/publish_weekend.py --list-year 2026
python3 gowifi/rea/sailing-roundup/app/publish_weekend.py --year 2026
```

Run that on the GoWifi REA box (`/opt/rea/work/sailing-roundup`). Existing editorial issues are kept unless `--rebuild`. Then `deploy/publish-to-sailingsa.sh` publishes the static tree.

Later years: `--year 2025` back to 2017, one year at a time.

## Not for landing Latest News

Landing recency rules stay as they are. Historical issues are archive URLs for Google depth (`sitemap-roundups.xml`). They are not injected into `/api/news/latest`.

## Google

| File | Rule |
| --- | --- |
| `/sitemap-news.xml` | First-party roundup URLs from the last **48 hours** only (`news:news`, `news:publication_date`, `news:title`) |
| `/sitemap-roundups.xml` | All issue URLs (historical) |
| `/sitemap.xml` | Index lists both |
| Issue HTML | `NewsArticle` JSON-LD (`datePublished`, `headline`, `author`) |
| `/regatta/{id}` | `SportsEvent` — sport Sailing, yacht-club location, podium competitors |

Submit **https://sailingsa.co.za/sitemap-news.xml** once in Google Search Console.

Indexing API (`URL_UPDATED`) is optional: `--notify-google` or `GOOGLE_INDEXING_SA_JSON`. Google documents that API for JobPosting / livestream; failures must not block publish.

## Code

- REA pipeline: `gowifi/rea/sailing-roundup/`
- Week clustering: `app/events_weekend.py` (`issue_monday_for_end`, `year_issue_mondays`)
- Monday / year publish: `app/publish_weekend.py`
