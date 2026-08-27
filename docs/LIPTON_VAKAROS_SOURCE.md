# Lipton 2026 — Vakaros tracking source (do not invent)

**Event only:** `2026-08-29-lipton-challenge-cup`  
**Watch URL:** https://player.vakaros.com/watch/Lv9A35uOBSBRmGpHgXtH/J22?live=true

Race days, race numbers, guns, and finishes for this prototype come from the **tracking system**, not from our results table, not from the clock, and not from guessing.

## What the watch page is

`player.vakaros.com` is a **Flutter** app. A GET of the watch URL returns a splash shell (`Now Loading…`, `flutter.js`). It does **not** contain:

- Day 1 / Day 2
- Race 1 … Race 5
- T− / AP / Go Live chrome
- boat SOG / lat lon

Do **not** scrape that HTML for race state. You will make it up.

## Where the player actually gets the data

Same backend the player uses:

1. Anonymous Firebase Auth  
   `POST https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=<public web key from main.dart.js>`  
   Body: `{"returnSecureToken":true}`
2. Firestore GET (project `vakaros-racesense`)  
   `GET https://firestore.googleapis.com/v1/projects/vakaros-racesense/databases/(default)/documents/regattas/Lv9A35uOBSBRmGpHgXtH`  
   Header: `Authorization: Bearer <idToken>`

Public web API key is in `https://player.vakaros.com/main.dart.js` (also hardcoded in the checker as the key the live player ships).

## Fields we use (J22 division)

| Need | Firestore path | Rule |
|---|---|---|
| Event name | `name` | Must be present |
| Races | `divisions[]` where fleet is J22 → `races[]` | If missing, **fail**. Do not invent R1. |
| Race number | `races[].raceNumber` | Integer from tracker |
| Gun | `races[].starts[0].startTime` | Tracker gun. T− later overrides SA holding time. |
| Day | date of gun in `Africa/Johannesburg` | Not “today” from the server clock |
| Finishes | `races[].finishes[].finishingTime` | Store against that race number only |
| Done? | `races[].currentStage` | `finished` = that race is over |
| Next race | unfinished `raceNumber`, else `max(raceNumber)+1` | From tracker list, not our sheet |

`divisions[].networkRaceNumber` is a tracker field (last/current network race). It is **not** a substitute for walking `races[]`.

## What `?live=true` is not

The `live=true` query on **our saved watch URL** is a player view flag. It does not by itself mean they switched tracking on in the morning or off overnight. Overnight on/off still has to be observed from tracker state, not from the string we stored.

## How to check (must actually run)

```bash
python3 sailingsa/scripts/lipton_vakaros.py
```

The script prints JSON from Firestore. It also GETs the watch URL and records that the HTML is a shell. Exit `0` only if races were returned by the tracker.

Lipton-only. Do not reuse this against other regattas.
