# Tracking Dev2 — Sailfish logic on Lipton fallback data

Dev sandbox for applying **Sailfish Sports (saill.cn)** open-trac patterns to SailingSA tracking, using **Lipton Challenge Cup** packed GPS replay as the sample dataset (races **R1–R10**).

## URLs

| URL | Purpose |
|-----|---------|
| `/regatta/2026-08-29-lipton-challenge-cup-dev2` | Canonical dev2 page (default `?race=1`) |
| `/regatta/2026-08-29-lipton-challenge-cup-dev2?race=N` | Replay race N (1–10) |
| `/tracking-dev2` | Shortcut → dev2 slug with `?race=1` |
| `GET /api/tracking-dev2/bootstrap?race=N` | Sailfish-shaped JSON bootstrap |

`noindex` on dev2 — not for public SEO.

## Sailfish → SailingSA mapping

| Sailfish concept | Dev2 implementation |
|------------------|---------------------|
| `getRace` / `status=99` | `bootstrap.status: "99"`, `replayFlag: "1"` |
| `replay2` static chunks | `/js/lipton-dev-replay[-rN].json` + trail JSON |
| `teamList[]` + `teamCd` | Built from Lipton `boats` map in bootstrap module |
| `runtime[]` 51-slot ticks | Documented index map in bootstrap; playback still uses packed Lipton grid |
| `viewConfig` (SOG, laylines, replay speed) | Returned in bootstrap; hook in `tracking-dev2-playback.js` |
| Live `stomp` / WSS | `transport.mode: "replay"` — deferred until live China capture |

### Runtime index (Sailfish `runtime[]`)

See `sailingsa/backend/tracking_dev2_bootstrap.py` → `RUNTIME_IDX` and `docs/sailfish-china-extracts/WS_PAYLOAD_SCHEMA.md` (PR #40).

## Files

| Path | Role |
|------|------|
| `sailingsa/frontend/tracking-dev2.html` | Page shell |
| `sailingsa/frontend/css/tracking-dev2.css` | Styles (fork of lipton-dev) |
| `sailingsa/frontend/js/tracking-dev2-playback.js` | Replay UI (fork of lipton-dev-playback; replay-only) |
| `sailingsa/backend/tracking_dev2_bootstrap.py` | Bootstrap builder |
| `sailingsa/frontend/js/lipton-dev-replay*.json` | Sample replay chunks R1–R10 |
| `sailingsa/frontend/js/lipton-dev-trail*.json` | Trail grids R1–R10 |
| `sailingsa/frontend/js/lipton-dev-races.json` | Race manifest |

**Note:** R4 uses unsuffixed files (`lipton-dev-replay.json`, `lipton-dev-trail.json`).

## vs Lipton `-dev`

| | `-dev` (lipton branch) | `-dev2` |
|--|------------------------|---------|
| Default mode | Live GPS + replay | **Replay only** |
| Default race | R4 / live | **R1** |
| Bootstrap API | None | `/api/tracking-dev2/bootstrap` |
| Sailfish schema | No | Yes (teamList, runtimeIndex, viewConfig) |

## Deploy to live (Mac — project root)

```bash
git checkout cursor/tracking-dev2-lipton-925c   # or main after merge
bash sailingsa/deploy/deploy-tracking-dev2-live.sh
```

Requires `~/.ssh/sailingsa_live_key`. Script uploads frontend zip, `api.py`, and `sailingsa/backend/tracking_dev2_bootstrap.py`, then verifies bootstrap + page URLs.

## Local test

```bash
# API must serve frontend js under /js/ (deploy layout) or use STATIC_DIR
curl -s 'http://localhost:8000/api/tracking-dev2/bootstrap?race=1' | python3 -m json.tool
# Browser: /regatta/2026-08-29-lipton-challenge-cup-dev2?race=1
```

## Features (apply / hide one at a time)

Feature toggles on the SF-TrajX bar (**SOG / COG / Layline / Leader / Front / Wind / Camera**) turn Sailfish-style overlays on or off so each can be kept or dropped.

**We do not have the full saill.cn proprietary app source.** What we have is reverse-engineered extracts under research (getRace bootstrap, viewConfig, replay2 chunk shape, WS topic notes in PR #40 / `docs/sailfish-china-extracts/`). Dev2 reimplements useful bits against Lipton R1–R10 sample GPS.

**Layout bit (dev2v12):** ranking board overlaid on the left of the map (Sailfish open_trac style), with **Board** toggle / × to hide. Bottom REPLAY dock remains.