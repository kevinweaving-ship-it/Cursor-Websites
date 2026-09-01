# Landing page — live snapshot comparison (2026-09-01)

## What you see depends on URL

| URL | Served from | Size | Last modified | Version |
|-----|-------------|------|---------------|---------|
| `https://sailingsa.co.za/` | nginx → API proxy → `index.html` | 809,558 | 1 Sep 2026 | **Current** (landing fix) |
| `https://sailingsa.co.za/index.html` | static `index.html` | 809,558 | 1 Sep 2026 | **Current** |
| `https://sailingsa.co.za/blank.html` | static `blank.html` | 130,605 → **809,558 after sync** | was **25 Jul 2026** | was **stale hub** |

**Root cause:** Deploys updated `index.html` only. `SSH_LIVE.md` lists `/blank.html` as the canonical hub URL — that file was never updated and stayed at the Jul 25 build.

## Marker diff (grep on server)

| Marker | index.html (live) | blank.html (before fix) | Aug 24 backup `index.html.bak_cat2_*` |
|--------|-------------------|---------------------------|----------------------------------------|
| `20260901landingfix` | yes | no | no |
| `hideApprovedRankPanels` | yes | no | no |
| `mountSimpleSailorCard` | yes | no | no |
| `temp-landing-layout` | yes | no | yes |
| `landing-news-embed` | yes | no | yes |
| `sailor-search-pills` | yes | no | yes |
| `blank-landing` | no | yes | no |
| regatta search `limit: 400` | yes | no (`limit=500` in sailors fetch) | no (`limit=500`) |

## Server snapshots on live (`/var/www/sailingsa/`)

- `index.html` — current deploy (Sep 1)
- `index.html.bak_cat2_20260824_133118` — 794,245 bytes, Aug 24 “good” pre-breakage candidate
- `blank.html.bak_pre_index_sync_*` — Jul 25 blank hub before sync (created on fix)
- Many older `index.html.bak.*` from Jul–Aug header work

## Nginx (live)

```
location = /           → proxy_pass http://127.0.0.1:8000   (API serves index.html)
location = /blank.html → try_files /blank.html
location = /index.html → try_files /index.html
```

## Fix applied

Copied `index.html` → `blank.html` on live with backup. Both hub URLs now serve the same file.

## Verify

```bash
curl -s https://sailingsa.co.za/blank.html | grep -o 20260901landingfix
curl -s https://sailingsa.co.za/ | grep -o 20260901landingfix
```

Both should print `20260901landingfix`.
