# REA tool research — auto weekend media + news recap

Deep-dive of public services that do the same job as this project: **take a weekend fixture list, collect social/media, emit a recap article**. Findings are mapped onto the 26–27 September 2026 test weekend.

Researched 18 October 2026. No paid accounts were created.

## The product we are copying

Newsrooms and sports platforms already automate this shape:

1. **Fixture slice** — “what happened this Saturday–Sunday?”
2. **Results enrich** — scores / tables from the sport’s own data
3. **Media ingest** — club and athlete social, search, photo dumps
4. **Templated article** — one weekend recap + per-event reports
5. **Schedule** — Friday preview or Monday publish
6. **Distribute** — HTML, PDF, CMS card, social carousel

Our calendar is `public.events`. Our Monday issue is the recap.

## Recap / article generators

| Service | What it does | Useful part for us |
| --- | --- | --- |
| [Sportradar GenAI recap](https://developer.sportradar.com/images-and-editorials/reference/gen-ai-overview) | Post-match article 30 minutes after an event, from sport IDs | Same contract: event id → headline + HTML/plaintext recap. We do this from `regatta_id` + results, not GenAI. |
| [Narrative Sports recaps](https://docs.narrative-sports.com/api-reference/sports/create-recap) | Selects highlights into a timed video recap | Video is optional later via yt-dlp links. We keep attributed source links. |
| [Weekend football Slack preview](https://www.generalinput.com/prompts/weekend-football-matchday-preview-posted-to-slack) | Friday job: this weekend’s fixtures → one recap, skip empty weekends | Exact schedule pattern. Our timer is Monday 06:00; empty weekends still publish a “no scored events” page. |
| [Automated sports update workflows](https://content.directory/automated-sports-update-workflow-tools-and-templates-to-publ) | Ingest fixtures → template prose → CMS / newsletter / social | Feature article + per-event `regatta_report` is that template. |
| [FixtureSync](https://fixturesync.com/how-it-works/) | Daily fixture sync + email digest | Events-table overlap is our fixture sync. |
| [n8n Instagram event carousel](https://n8n.io/workflows/14656-create-event-recap-instagram-carousels-from-photo-dumps-using-upload-to-url/) | Photo dump → IG carousel | We collect OG/gallery-dl images and **link** them; we do not republish to Instagram. |
| [sdvplotR social graphics](https://sdvplotr.sportsdataverse.org/articles/automation-social.html) | Weekly scheduled graphics from open sports APIs | Same “Monday job, no extra API key” idea. Our graphics are HTML/PDF tables. |

**Takeaway:** every serious recap product starts from a **fixture table + date window**, then writes one story. That is why discovery is `events_weekend.py`, not a scrape of `/events` HTML.

## Social / media ingest (all platforms)

| Service | Platforms | Useful part for us |
| --- | --- | --- |
| [SocialCrawl Search Everywhere](https://www.socialcrawl.dev/platforms/search/everywhere) | Instagram, YouTube, TikTok, Facebook, X, Reddit, Threads, … (60+) | One query, `lookback_days`, unified schema. Already wired as `social_aggregators.socialcrawl`. Needs `SOCIALCRAWL_API_KEY`. |
| [Apify Instagram Scraper](https://apify.com/apify/instagram-scraper) | Instagram posts, reels, hashtags | Official actor `apify/instagram-scraper`. Date filter + API run. |
| [Apify Facebook Posts Scraper](https://apify.com/apify/facebook-posts-scraper) | Facebook pages/profiles | Official actor `apify/facebook-posts-scraper`. Captions, timestamps, images. |
| [Apify Facebook Events Scraper](https://apify.com/apify/facebook-events-scraper) | Facebook events | Match club event pages to the weekend window. |
| [Apify YouTube Scraper](https://apify.com/streamers/youtube-scraper) | YouTube search, videos, playlists | Complements yt-dlp search. |
| gallery-dl | Facebook, Instagram, YouTube extractors (already on the REA box) | Free, no key. Used first. Login walls fail cleanly. |
| yt-dlp | YouTube search + metadata | `ytsearch5:{event} sailing 2026` |
| Open Graph | Any public URL | Title / description / image. Same trick the Media tab uses for sailor-added URLs. |
| SailingSA Media tab | Stored mentions (FB, IG, news) | `GET /api/member/{sa_id}/public-mentions`. Proven on Tim 21172 and Josh Keytel 13522. |
| SearXNG / Bing / Google News RSS | Web + images + news | `media_research.py` fallback when social APIs are dark. |
| [SociaVault sports listening](https://sociavault.com/blog/build-world-cup-social-listening-dashboard) | Scheduled social snapshots | Same store-then-render pattern as `issues/YYYY-MM-DD/sources/`. |

**Not used (on purpose):** CrowdTangle (retired), unofficial Facebook private APIs, cookie/login bypass, Bright Data residential proxies. Those break the isolation and rights rules.

## What REA already had vs what was missing

On the box (`/opt/rea/work/sailing-roundup`) before this work:

- Pieces existed: `auto_weekend.py`, `social_weekend.py`, `social_aggregators.py`, gallery-dl, yt-dlp
- **No timer** — nothing ran on Monday
- **HTML `/events` scrape only** — missed the events-table overlap rule
- **Social not wired** into auto publish (OG only on URLs already in `sources`)
- **Athena actor** was an unofficial `ranil~athena-social-scraper`; official Apify actors are now preferred
- **No credentials** for Apify / SocialCrawl on the box — free path must work without them
- **Sailor Media-tab API** was not called, even though Tim and Josh already prove it works
- Issues stopped at 2026-10-05

## Mapping onto 26–27 Sep 2026

For that weekend the events table is the source of truth. The publisher:

1. Selects every non-meeting row whose dates overlap 26–27 Sep
2. Writes a **feature** (“Weekend sailing roundup”) from those rows
3. For each slugged event, writes a **regatta_report** from `/api/regatta/{slug}`
4. For podium SAS IDs, pulls Media-tab mentions (the Tim / Josh tool)
5. Adds club Facebook/Instagram from SailingSA club records (HMYC, TSC, AYC)
6. Runs gallery-dl / yt-dlp / OG on those URLs
7. Renders landing HTML + PDF

That is the same architecture as Sportradar + SocialCrawl + a Monday newsroom job, implemented with our events table and without writing to SailingSA.
