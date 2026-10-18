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
3. Reads club/class directory social links from SailingSA
4. Adds known club Facebook / Instagram / websites
5. Scrapes Open Graph metadata from discovered URLs
6. Runs REA-installed **gallery-dl** (Facebook / Instagram / YouTube extractors) and **yt-dlp** search
7. Calls Athena / SocialCrawl only if `APIFY_TOKEN` or `SOCIALCRAWL_API_KEY` is set

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
