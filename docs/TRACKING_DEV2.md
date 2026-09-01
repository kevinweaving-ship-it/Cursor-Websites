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
| **Series nett at gun** | 0 for all | Sum of **all** prior-race points (club series — no discard) |
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
| `sailingsa/frontend/js/lipton-dev-series-scores.json` | Official R1–R10 points (Lipton overall PDF); R6 protest metadata |

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

## Protest mode (R6 sample — dev2v21+)

**Built for R6:** official Lipton overall scores drive series nett (R7+ overall leader fixed). **Scores: Official / Provisional** toggle on Race 6 replay. Orange **⚑ Possible protest · 57:25** marker when scrubbing near the pre-flag time.

See **Later — full auto-detection** below for planned heuristics across all races.

## Later — Protest auto-detection (partial — R6 manual scores live)

**Goal:** Auto-flag *possible* protests from GPS; let scorer toggle **With protest / Without protest** and adjust rank/score. Default view = standard finish (no DSQ) until a protest is confirmed.

| Piece | Behaviour |
|-------|-----------|
| **Possible protest alerts** | Heuristics: finished boat lingering near finish/mark; racing boat closing; close pass (&lt;~10 m); large course change to avoid. Timeline marker + “Review” list — *not* a jury decision. |
| **Protest flags** | Mark boats **protestor / protestee / DSQ / cleared** per race (manual or from published PC decision). |
| **Adjust score/rank toggle** | **Without protest:** GPS finish order, no DSQ. **With protest:** apply DSQ/redress (e.g. drop protestee from results, optionally bump others). Board + map numbers follow active mode. |

**Reference — Lipton 2026 R6 (two protests, three DSQs by end R7):**

- **Provisional R6 sheet** (on-water / pre-hearing): FBYC 1, RCYC Academy 2, UCTYC 3 … KYC 7, RNYC 8, LDYC 5, RCYC 12 — no DSQ yet.
- **Official corrected R6** (overall PDF, by end R7): same top 4; then **18.0 DSQ** for **KYC, LDYC, RNYC** (entries+1 scoring). RCYC stays 9th (no redress).
- **Case 02** (ONB PDF): RCYC vs KYC/LDYC/RNYC @ ~57:25 — DSQ **LDYC & RNYC**; **KYC cleared** in that hearing; no redress for RCYC (RRS 61.4(b)).
- **KYC on final sheet:** still **18 DSQ** → implies a **second protest/hearing** (Case 01 not yet on ONB when checked).
- **RNYC overall:** was leading after 6 on provisional; drops to **6th after 7** once R6 DSQ applied (63 pts total in final overall).
- **Tracking pre-flag @ 57:25.1:** finished boats clustered at pin; RCYC closing; ~5 m pass; course change — `Scores: Official` / `Provisional` toggle on R6 replay.
