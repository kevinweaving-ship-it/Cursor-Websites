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

## Leader vs Front vs numbers

| | **Race 1** | **Race 2+** |
|--|------------|-------------|
| **Series nett at gun** | 0 for all | Sum of prior-race points (1 discard after 4 prior races) |
| **Front** (red line) | Who is 1st **this race** | Same |
| **Leader** (yellow line + gold ring) | **Same as Front** | **Overall regatta leader** — lowest `prior nett + live race place` |
| **Number on map icon** | **This race place** (always) | **This race place** (locks to finish order when done) |
| **Board sort + Rank column** | This race order | **Overall regatta order** |
| **Overall sticker rings (map)** | Hidden | **1st yellow, 2nd blue, 3rd red** (World Sailing Reg 20.4.3 bib colours) |

## Board (left overlay, compact)

| Column | Meaning |
|--------|---------|
| Rank | Overall rank (R2+) or race rank (R1); boat icon shows this number |
| Bow / Boat / Club | Identity |
| **Gap** | Seconds behind **race** leader on this leg (was ST) |
| **Start** | Start position this race (1–17) |
| **O/all** | Overall places gained ▲ / lost ▼ / none ■ since race gun (vs standing at gun) |

Expanded mark-time columns still available via the Fin twist control.

## Files

| Path | Role |
|------|------|
| `sailingsa/frontend/tracking-dev2.html` | Page shell |
| `sailingsa/frontend/css/tracking-dev2.css` | Styles |
| `sailingsa/frontend/js/tracking-dev2-playback.js` | Replay UI |
| `sailingsa/backend/tracking_dev2_bootstrap.py` | Bootstrap builder |
| `sailingsa/frontend/js/lipton-dev-replay*.json` | Sample replay chunks R1–R10 |
| `sailingsa/frontend/js/lipton-dev-trail*.json` | Trail grids R1–R10 |

## Deploy to live (Mac — project root)

```bash
bash sailingsa/deploy/deploy-tracking-dev2-live.sh
```

## Features (apply / hide one at a time)

| Toggle | What it is | Default |
|--------|------------|---------|
| Board | Ranking table overlay on the map | on |
| Marks | Start/Finish halos, numbered marks | on |
| Dots | Breadcrumb dotted tracks | on |
| SOG / COG | Speed / heading on map labels | off unless viewConfig |
| Layline | Red V from active mark | on |
| Leader | Yellow line to overall leader (R2+) or race leader (R1) | on |
| Front | Red perpendicular through this-race leader | on |
| Wind | Compass | on |
| Camera | Recenter / follow fleet | on |

**Finish lock:** once all finishers are in, map numbers stay on that race’s finish order (not GPS drift).
