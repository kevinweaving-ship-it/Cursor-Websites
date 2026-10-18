# Weekend Sailing Roundup — project

Independent Monday publication that turns the **SailingSA `events` table** into a weekend news article, landing page, and PDF, then attaches public social/media for each event.

SailingSA is read-only. This app does not write to the SailingSA database, frontend, cron, or nginx.

## Why this exists

The 26–27 September 2026 weekend (Monday issue **2026-09-28**) is the reference test:

| Event (events table) | Dates | `regatta_id` | Results |
| --- | --- | --- | --- |
| 420 Nationals | 26–27 Sep | `2026-09-25-tsc-420-nationals` | 16 entries, 8 races |
| Dart 18 Nationals + KZN provincials | 24–27 Sep | `2026-09-24-hmyc-dart-18-nationals` | 8 races |
| Gauteng Regionals (Dabchick) | 24–26 Sep | `2026-09-24-ayc-dabchick-gauteng-regionals` | 17 entries, 12 races |
| 505 Nationals | 24–27 Sep | `2026-09-24-ayc-505-nationals` | 7 entries, 12 races |
| DF95 WC Regional Champs | 25–27 Sep | none | listed, no slug |
| J22 Nationals | 24–27 Sep | none | listed, no slug |
| FBYC Spring Regatta | 24–27 Sep | none | listed, no slug |

Meetings / courses (for example the multi-year DSO appointment row) are excluded.

## Club / class URL directory

Clubs already list website + Facebook + Instagram on `/club/{slug}`. The independent catalog scrapes those into `app/club_sources.json`.

Classes are South African only. `app/catalog_sources.py` pulls SA class websites from sailing.org.za/sasclasses and SailingSA `/api/class/{slug}`. International class association pages (Int420Class, int505.org, dart18class.com) may be stored but every URL has `locality: local | not_local`.

Facebook share links are resolved. The local 420 example:

`https://www.facebook.com/share/g/1Jh51CDMew/` → **420 Class RSA** group `https://www.facebook.com/groups/120115671476306/` → `https://sailingsa.co.za/class/420`

Cross-shared Facebook posts (`X shared Y's post`) are matched back to the SailingSA club, class, sailor, or sponsor URL and added to that entity's directory.

```bash
python3 app/catalog_sources.py
```

Rebuild that edition:

```bash
python3 app/publish_weekend.py --test-weekend
```

## Pipeline

```text
public.events  --GET /api/events-->  Saturday–Sunday overlap
        |                                  |
        v                                  v
  weekend feature article          slugged events
                                           |
                                           v
                         GET /api/regatta/{slug}  (results, SAS IDs)
                                           |
           +-------------------------------+------------------+
           |                               |                  |
 sailor Media tab              club/class social         web / social
 /api/member/{id}/public-mentions   directory + OG     gallery-dl / yt-dlp
           |                               |           (+ Apify / SocialCrawl if keyed)
           +-------------------------------+------------------+
                                           |
                                           v
                    issue.json  →  landing HTML  →  edition.pdf
                    public/index.html   public/latest/   public/feed.json
```

Monday 06:00 Africa/Johannesburg (`sailing-roundup.timer`) runs `--due` (current Monday plus three missing weeks).

## Events-table rule

An event belongs to the issue dated Monday *M* when its `[start_date, end_date]` overlaps **Saturday–Sunday** before *M*.

For Monday 28 Sep 2026 that window is **26–27 Sep**. Nationals that started on Thursday 24 Sep still count if they were still racing on Saturday.

Source: `GET https://sailingsa.co.za/api/events`  
Code: `app/events_weekend.py`

## Outputs

| File | Role |
| --- | --- |
| `issues/YYYY-MM-DD/issue.json` | Editorial JSON (feature + per-event reports) |
| `issues/YYYY-MM-DD/sources/events-weekend.json` | Events-table snapshot |
| `issues/YYYY-MM-DD/sources/{slug}-social.json` | Social/media evidence |
| `public/issues/YYYY-MM-DD/index.html` | Landing page |
| `public/issues/YYYY-MM-DD/edition.pdf` | Print edition |
| `public/index.html` | Archive landing |
| `public/feed.json` | Card feed for a future consumer |

Live URL: https://sailingsa.co.za/sailing-roundup/

Reference weekend (26–27 Sep 2026): https://sailingsa.co.za/sailing-roundup/issues/2026-09-28/

## Sailor Media tab tool

Already live. Used read-only.

- `GET /api/member/{sa_id}/public-mentions`
- Reference: Timothy Weaving **21172** (media_score 8, 22 items — Facebook / Instagram / optimist.org.za)
- Reference: Joshua Keytel **13522** (media_score 8, 9 items — Facebook / Instagram)

```bash
python3 app/sailor_mentions.py --check-reference
```

The write job documented as `jobs/sailor_media_fetch.py` is **not in this repo or on live**. The roundup does not invent that job; it consumes the public Media-tab API.

## Social tools REA mapped

See **[docs/TOOL_RESEARCH.md](docs/TOOL_RESEARCH.md)** for the web deep-dive. In short:

| Layer | Tool | Needs key? | Used for |
| --- | --- | --- | --- |
| Calendar | SailingSA `events` table | no | Which events ran this weekend |
| Results | `/api/regatta/{slug}` | no | Leaderboard + SAS IDs |
| Sailor media | public-mentions API | no | Tim / Josh / podium sailors |
| Official links | club/class directory | no | Scraped from SailingSA club URLs; SA class pages + SAS class sites. International class URLs stored as `not_local`. Facebook share/cross-posts matched back to `/club/`, `/class/`, `/sailor/`, sponsor. |
| Page metadata | Open Graph | no | Title, caption, image |
| Public extractors | gallery-dl, yt-dlp | no | FB / IG / YouTube public URLs |
| Everywhere search | Google News + Bing `site:` Facebook / Instagram / TikTok / YouTube / X / Reddit | no | `search_everywhere.py` |
| Cross-network search | SocialCrawl `/v1/search/everywhere` | `SOCIALCRAWL_API_KEY` | One query, 60+ platforms |
| Platform scrapers | Apify official actors | `APIFY_TOKEN` | FB posts, IG posts, YouTube, FB events |

A post is attached only after `event_social_verify.verify_post` matches the **event URL**, **class + host club**, or **results names**. A Dart 18 club post will not attach to the 420 Nationals article.

No login walls are bypassed. Unlicensed photos are linked, not republished.

## What this is not

- Not a SailingSA frontend change
- Not the landing-page “Sailing Magazine” scrape of sailing.co.za
- Not licensed photo reuse
- Not a second MCP tunnel or REA reinstall
