# Weekly Roundup rebuild (one edition at a time)

Rebuilds **content** for the live Roundup system. It does **not** invent a new magazine layout.

Public surfaces (unchanged URLs):

| Surface | URL |
|---|---|
| Landing card (navy carousel) | https://sailingsa.co.za/dev1/ |
| Full edition | https://sailingsa.co.za/sailing-roundup/issues/YYYY-MM-DD/ |
| Card feed | `/sailing-roundup/feed.json` |
| Issue cards | `/sailing-roundup/cards.json` |

`/dev1/` already paints Weekly Roundup + Edition N + date, image carousel, overlay headline, dots/arrows, engagement row, **READ FULL ROUNDUP**. This package only replaces the **headline / excerpt / card order / story copy** that feed those shells.

## First edition: 2026-10-26

```bash
python3 -m sailingsa.roundup build --week 2026-10-26
python3 -m sailingsa.roundup test
python3 -m sailingsa.roundup publish --week 2026-10-26
```

Dry-run artifacts (not deployed):

- `artifacts/roundup/sailing-roundup/feed.2026-10-26.json` — `feed.json` item (`headline` is the /dev1/ overlay)
- `artifacts/roundup/sailing-roundup/cards.2026-10-26.json` — `cards.json` issue block
- `artifacts/roundup/sailing-roundup/issues/2026-10-26/index.html` — full edition, live class names
- `artifacts/roundup/sailing-roundup/issues/2026-10-26/edition.md`
- `.../media_pool/*.json` — proposed write-back onto the event URL (dry-run)

## Event-URL-first

For each event in the owned week (end date Mon–Sun before the Monday edition date):

1. `/api/events` → week filter → `/api/regatta/{id}` + `/regatta/{id}` page media
2. Draft fact sheet from that alone
3. External sources only on gaps (DF95 has no SailingSA results page)

## Non-negotiables

Fact sheet, conflict note, story score (Worlds/Nationals always a card), class tags from that event’s scoring fleets (PY mixed fleets → `PY (handicap)`), sources footer, image fallback, no `Venue - CODE` leaks, provisional verbs, week ownership by end date, media write-back as dry-run JSON.

## Next older edition (2026-10-19)

```bash
python3 -m sailingsa.roundup build --week 2026-10-19 --live
```

`--live` pulls `/api/events` and each `/api/regatta/{id}`. To freeze a fixture set (recommended):

1. Copy `sailingsa/roundup/fixtures/2026-10-26/` to `fixtures/2026-10-19/`
2. Replace `events.json` with that week’s rows (`end_date` 2026-10-12 … 2026-10-18)
3. Save each `results/{regatta_id}.json` and `summaries/{regatta_id}.json`
4. `python3 -m sailingsa.roundup build --week 2026-10-19`

DF95 (end 2026-10-23) must **not** get a card on 2026-10-19. At most a late-results mention after 10-26 has owned it.

## /dev1/ test (do not deploy from this job)

1. Open https://sailingsa.co.za/dev1/ at **390×844**
2. Confirm the existing navy card shell (do not restyle it)
3. After a reviewed copy of `feed.2026-10-26.json` into live `feed.json`, the overlay headline must be the DF95 lead, not the five-event list
4. Remove the DEV1-only Ullman hardcode in `/dev1/landing-roundup-cards.js` (see `patches/dev1-lead-override.md`)
5. Tap **READ FULL ROUNDUP** → `/sailing-roundup/issues/2026-10-26/`

This CLI only writes under `artifacts/roundup/`.
