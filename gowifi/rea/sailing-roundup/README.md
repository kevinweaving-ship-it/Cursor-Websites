# Independent Sailing Weekend Roundup

Standalone Monday publication. SailingSA is a **read-only** results and Media-tab source. This app never writes to SailingSA, nginx on gowifi.co.za, or the REA MCP tunnel.

**Project docs:** [PROJECT.md](PROJECT.md) · **Tool deep-dive:** [docs/TOOL_RESEARCH.md](docs/TOOL_RESEARCH.md)

Reference weekend: **26–27 September 2026** (issue Monday 2026-09-28). Driven from the public `events` table, not a homepage scrape.

## What it publishes

Each Monday it builds:

- Landing page: `public/issues/YYYY-MM-DD/index.html`
- PDF edition: `public/issues/YYYY-MM-DD/edition.pdf`
- Issue JSON: `public/issues/YYYY-MM-DD/issue.json`
- Archive: `public/index.html`, `public/latest/`, `public/feed.json`

Live URL (REA box default vhost only): https://box.gowifi.co.za/sailing-roundup/

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

No login walls are bypassed. Unlicensed photos are linked, not republished.

## Automation

`sailing-roundup.timer` runs 06:00 Mondays (Africa/Johannesburg) and on boot if a run was missed (`Persistent=true`). It publishes the current Monday plus the previous three if they are missing, and refreshes social on existing drafts.

```bash
sudo -u rea -H /opt/rea/work/sailing-roundup/.venv/bin/python3 \
  /opt/rea/work/sailing-roundup/app/publish_weekend.py --due
```

## Install (GoWifi only)

```bash
bash gowifi/rea/sailing-roundup/deploy/install.sh /path/to/gowifi/rea/sailing-roundup
```
