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

## Watch URL map (what you see vs what we store)

The player does **not** put T− in the HTML. Chrome is computed in Flutter from Firestore guns + a playback clock.

**URL shape** (from `player.vakaros.com` `main.dart.js`, route builder `avt.gCy` / parser `bJ1`):

`https://player.vakaros.com/watch/{eventId}/{fleet}?race-day={n}&live=true&ts={ms}`

| Piece | On the URL | Pulls from | What you see |
|---|---|---|---|
| `eventId` | path | Firestore `regattas/{id}` | which event |
| `fleet` | path (`J22`) | `divisions[].name` | which fleet |
| `race-day` | query, **omitted if 1** | 1-based index of SAST dates that have guns | Day dropdown (Day 1 = 26 Aug, Day 2 = 27 Aug) |
| `live=true` | query, **omitted if replay** | player mode, not overnight on/off | live watch vs replay. **Go Live** appears when this is off |
| `ts` | query, unix **milliseconds** | scrubber / replay position | **left-hand clock** in replay |

**Left-hand time** (`adU`): replay = `ts` (playback). Live = wall clock. It is **not** T−.

**T− / T+** (`adG` / `akT`): `playback` vs that race’s `starts[0].startTime`.  
- before gun → **T−** (gun − playback)  
- after gun → **T+** (playback − gun)  
There is no T− field in Firestore. We can rebuild it for checksums and simulations from stored guns + a chosen `ts`.

Division also has `countdownType=traditional`, `startLength=fiveMin` (5-minute sequence). That is the RO start sequence, not a separate stored T− string.

### Example: between Race 4 and Race 5 (Day 2)

From tracker guns (not guessed):

- R4 gun 13:55:01 SAST, R4 end 15:34:28 SAST  
- R5 gun 15:50:01 SAST  
- Gap ≈ 15.5 minutes. In that gap, if the chip is on **R5**, you see **T−** to 15:50.

Replay URL at R4 finish (left clock ≈ 15:34, T− vs R5 ≈ 15.5 min):

`https://player.vakaros.com/watch/Lv9A35uOBSBRmGpHgXtH/J22?race-day=2&ts=<R4 end ms>`

Each race summary also stores `replay.at_gun`, `replay.at_end`, `replay.prestart_5min` for later sims.

Open those with `live` **omitted** (replay). `python3 sailingsa/scripts/lipton_vakaros.py` prints `replay_examples`.

## Marks, pin, committee boat (Race 5 checked)

Devices on this event (Firestore `rcDevices` + course `achievements`):

| Name on tracker | Role | Used as |
|---|---|---|
| **RC** | coordinator | Committee boat. `startRight` and `finishRight` |
| **4** | mark | **Pin** end of start/finish (`startLeft` / `finishLeft`). Also a wing rounding later |
| **1** | mark | Windward (`WindW`) |
| **2** | mark | Wing |
| **3** | mark | Leeward |
| **Media** | mark | Extra tracker, radius 0 |

There is **no device named Pin**. The pin is device **4**.

**What we can measure (already in the archive):**

- **At the gun:** pin + RC lat/lon (`starts[].startLine`), every boat lat/lon, and official **distance to the start line in millimetres** (`startingStats[].dtlMm`). Player column: “DTL at Start (m)”.
- **At the finish:** boat lat/lon + the live pin/RC positions at that instant (`lineLeftLocation` / `lineRightLocation`). The line **moves** (pin drifted ~187 m from R5 gun to first finish; RC ~15 m).
- Distance from a boat to pin or to RC at those two instants: compute from those coordinates (haversine).

**Race 5 gun (checked):** start line ~174 m. Closest boat LDYC DTL **0.13 m**, ~11 m from the pin. No OCS. Replay at gun (no `live`): see `races[R5].replay.at_gun`.

**Rounding direction (on the course, not guessed)**

Every rounding on this course is **port** (`roundingDirection: port`, role `markPort`). Zone is **on**, **3 boat lengths** (`markZoneEnabled`, `numBoatLengthsForZone`).

| Mark | Round | Leave to |
|---|---|---|
| 1 Windward | port | port |
| 2 Wing | port | port |
| 3 Leeward | port | port |
| 4 (also a wing later) | port | port |

Start and finish are **lines**, not roundings (pin–RC). That direction arrow on the map is how we know a boat is approaching the mark it must round, and which way. Detecting “now in the 3-length zone” still needs the GPS trail (not in the spectator document yet). The **rule** is stored; the **when** waits on frames.

**What we cannot get yet:** lat/lon for marks **1 / 2 / 3** during the race, or a boat’s distance to them **while racing**. The replay map draws those from GPS frame streams. Spectator Firestore has the course (which SN is which mark) but not the ping trail. Do not invent those positions.

## How to check (must actually run)

```bash
python3 sailingsa/scripts/lipton_vakaros.py
```

The script prints JSON from Firestore. It also GETs the watch URL and records that the HTML is a shell. Exit `0` only if races were returned by the tracker.

## Store it — the feed will disappear

After the event, this Firestore document is gone. Archive **the whole spectator document** (boats, marks, courses, guns, OCS, finish lat/lon, times), not a guessed subset.

Table: `public.vakaros_snapshots` (append-only). Each fetch is a new row.

```bash
# on live
DB_URL=... python3 sailingsa/scripts/lipton_vakaros.py --save
```

Or: `expect sailingsa/deploy/apply-lipton-vakaros-archive.exp`

`payload` = decoded document (usable JSON).  
`payload_raw` = Firestore REST body (lossless).  
`summary` = days / race numbers derived from `races[].starts[].startTime` (SAST date), not from our clock.

**Not in this document (cannot invent):** GPS replay / frame bundles. Spectator auth can read `regattas/{id}` only. Storage was empty. If those streams become readable later, snapshot them into new rows with a different `source`.

Lipton-only ingest (`regatta_id = 2026-08-29-lipton-challenge-cup`). Do not reuse against other regattas.
