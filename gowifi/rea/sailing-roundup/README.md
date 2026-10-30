# Independent Sailing Weekend Roundup

Standalone Monday publication. Generation stays on GoWifi. SailingSA is a **read-only** results and Media-tab source for clustering; the only write is issue-scoped static files under `/sailing-roundup/`. This app never changes the SailingSA SPA, API, nginx on gowifi.co.za, or the REA MCP tunnel.

**Gold contract (master):** [docs/GOLD.md](docs/GOLD.md) — how 2026-09-28 was made and how every new Monday URL must publish the same way with no hand edit.

**Project docs:** [PROJECT.md](PROJECT.md) · **Unattended Monday publish:** [docs/UNATTENDED_MONDAY_PUBLISH.md](docs/UNATTENDED_MONDAY_PUBLISH.md) · **Verified evidence:** [docs/VERIFIED_EVIDENCE_FIX.md](docs/VERIFIED_EVIDENCE_FIX.md) · **Real aggregators to copy:** [docs/REAL_AGGREGATORS.md](docs/REAL_AGGREGATORS.md)

Reference weekend: **26–27 September 2026** (issue Monday 2026-09-28). Driven from the public `events` table, not a homepage scrape.

## What it publishes

Each Monday it builds:

- Landing page: `public/issues/YYYY-MM-DD/index.html`
- PDF edition: `public/issues/YYYY-MM-DD/edition.pdf`
- Issue JSON: `public/issues/YYYY-MM-DD/issue.json`
- Archive: `public/index.html`, `public/latest/`, `public/feed.json`

Live URL: https://sailingsa.co.za/sailing-roundup/

Reference weekend 26–27 Sep 2026: https://sailingsa.co.za/sailing-roundup/issues/2026-09-28/

## Sailor media tool

The sailor Media tab is already live:

`GET https://sailingsa.co.za/api/member/{sa_id}/public-mentions`

Reference sailors:

| Sailor | SAS ID | Check |
| --- | --- | --- |
| Timothy Weaving | 21172 | `python3 app/sailor_mentions.py --check-reference` |
| Joshua Keytel | 13522 | same command |

The write-side job documented as `jobs/sailor_media_fetch.py` is **not present** in this repo or on live. The roundup uses the public read API only.

## Social collection (all public sources)

For each weekend event the publisher:

1. Reads `/api/regatta/{slug}` (results, club, class, helm/crew SAS IDs)
2. Pulls Media-tab mentions for those sailors
3. Searches **everywhere**: Google News, DuckDuckGo web, Facebook, Instagram, TikTok, YouTube, X, Reddit
4. Reads the club/class URL directory (`club_sources.json` / `class_sources.json`) — same website + social list clubs already publish on `/club/{slug}`
5. Classes are **South African only**. International class association URLs may be stored but are labelled `not_local`
6. Facebook share links and cross-shared posts are resolved and matched back to the SailingSA `/club/`, `/class/`, `/sailor/`, or sponsor URL
7. Keeps a post only if it verifies against that event URL and/or published results names
8. Runs gallery-dl / yt-dlp; SocialCrawl / Apify run when those keys exist

Rebuild the directory (read-only against SailingSA):

```bash
python3 app/catalog_sources.py
```

Local 420 class Facebook group (user share link `facebook.com/share/g/1Jh51CDMew/`): **420 Class RSA** → `https://www.facebook.com/groups/120115671476306/` → `https://sailingsa.co.za/class/420`.

Host-club pages are the media source for that club’s events. Dart 18 Nationals uses **HMYC** (`https://sailingsa.co.za/club/hmyc`, Facebook `henleymidmaryachtclub`). Share posts such as `facebook.com/share/p/1PGpY1pGh1/` (Dart 18 Nationals final results) are resolved and auto-attached to the weekend-roundup `source_info` / `social_sources` list. Other HMYC posts about the same event are found by searching that club page.

Article generation is **not** those products yet. `app/event_rewrite.py` is a
results mad-lib plus an unverified search dump. The systems to reverse-engineer
(NewsCatcher / Perigon / Event Registry / Monok for clustering; Sportradar /
United Robots / Stats Perform for the recap) are listed in
`docs/REAL_AGGREGATORS.md`.

No login walls are bypassed. Photos are downloaded locally and credited.

## Automation

`sailing-roundup.timer` runs 06:00 Mondays (Africa/Johannesburg) unattended: cluster the weekend, rewrite each event, download a photo, write HTML/PDF/`cards.json`, then publish to sailingsa.co.za. `deploy/run-monday.sh` is the only command the timer needs.

```bash
sudo -u rea -H /opt/rea/work/sailing-roundup/.venv/bin/python3 \
  /opt/rea/work/sailing-roundup/app/publish_weekend.py --due
```

Historical year (same REA search + media path; skip empty weeks; keep existing editorial issues):

```bash
python3 app/publish_weekend.py --list-year 2026
python3 app/publish_weekend.py --year 2026
```

A multi-week event is published on the **Monday after the week it ended**. Landing Latest News is not changed. See **`docs/WEEKEND_ROUNDUP.md`**.

## Install (GoWifi only)

```bash
bash gowifi/rea/sailing-roundup/deploy/install.sh /path/to/gowifi/rea/sailing-roundup
```
