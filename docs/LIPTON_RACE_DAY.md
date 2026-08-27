# Lipton 2026 — race day, step by step (this URL only)

**URL:** `/regatta/2026-08-29-lipton-challenge-cup`  
**Tracker:** Vakaros RaceSense (same Firestore document we archive in `public.vakaros_snapshots`).  
Do not invent positions, mark leaders, or Nett from the live map.

This is the day as it starts. Fill each slice only with what the tracker actually gives us. Current slice: **gun → mark 1**.

## Tools (whole day)

| Tool | Job |
|---|---|
| Vakaros player | What the RO/fleet see (T−/T+, map, marks). HTML scrape is useless (Flutter shell). |
| Firestore `regattas/{id}` | Guns, OCS, DTL at gun, finish times, course (marks + port + 3-length zone). `python3 sailingsa/scripts/lipton_vakaros.py` |
| `vakaros_snapshots` | Append-only archive. `--save` every phase change. Feed will disappear after the event. |
| Super Admin start field | Holding time until T− exists. T−/gun always wins. |
| SA chip LIVE / RACING / POSTPONED | Override if the feed is wrong. POSTPONED = racing-day AP, not “event moved”. |
| Lipton page | Display only. Do not write sheet Nett from tracker places. |

GPS **trails** (boats and marks 1/2/3 moving) are what the replay map draws. They are **not** in the spectator document yet. Anything that needs “who is closest to mark 1 right now” waits on that trail.

## Day skeleton (what we look for)

1. Overnight / morning — tracker on or off; boats in harbour. **LIVE**. Slow poll.
2. Holding start — briefing / WhatsApp / SA types a time. Still **LIVE**.
3. Heading out — SOG > ~1 kn, leaving harbour. Still **LIVE**. Wake poll.
4. T− on Vakaros — lock start from T−. Still **LIVE**. Countdown. Not racing.
5. AP on Vakaros — **POSTPONED**.
6. Gun (T− hits 0 / T+) — **RACING**. Hard poll. Do not write Nett.
7. **Gun → mark 1** — this file, below.
8. Mark 1 → 2 → 3 → … (later). Need trails for “first around”.
9. Finish — `finishes[].finishingTime` (we **do** have first to finish).
10. Idle / next race / 19:00 day close.

---

## Slice: gun → first mark

**Assume:** we already have T−, then the gun. Boats are off toward mark 1.

### What we are doing

Stay in **RACING** for this race number (next is **R6** when they start again; R1–R5 are finished). Show elapsed **T+**. Remember next rounding is **mark 1, port, 3 boat-length zone**. Snapshot the tracker document at gun (and again if it changes). Do **not** put tracker places into Nett.

### What we are looking for

| Signal | Have now? | Where |
|---|---|---|
| Race number | yes | `races[].raceNumber` / next unfinished |
| Gun | yes | `starts[0].startTime` (T+ = playback − gun) |
| OCS / DTL at gun | yes | `ocsParticipants`, `startingStats[].dtlMm` |
| Start line (pin + RC) at gun | yes | `startLine` left=device **4**, right=**RC** |
| Boat lat/lon **at the gun** | yes | `startingStats[].positionAtStart` |
| Heading at gun | yes | `headingAtStartDeg` |
| Next mark is 1, port, 3-length zone | yes | course `WindW` / `markPort` / `numBoatLengthsForZone=3` |
| Boat lat/lon **between** gun and mark 1 | **no** | GPS trail (not in spectator doc) |
| Mark 1 lat/lon while it sits out there | **no** | trail / mark pings |
| Who is closest to mark 1 / first to round | **no** | trail + zone |
| Finish of this race | later | `finishes[].finishingTime` |

Between start and mark 1 we **know the rules and the gun snapshot**. We do **not** yet know the live picture of the beat.

### How we record it

1. At gun (T− → T+): `--save` snapshot. Tag in summary: phase `racing_to_mark_1`, race n, gun, DTL, OCS, start line, next mark = 1 port.
2. Keep polling Firestore. If a new `races[]` row appears or `currentStage` changes, snapshot again.
3. If AP goes up: phase postponed; snapshot; chip **POSTPONED**.
4. Do not log a “mark 1 rounding” until a trail/rounding time exists. Finish times belong to the finish slice.

### How we store it

Same table: `public.vakaros_snapshots` (full `payload` + `summary`).  
Gun/DTL/OCS/course are already in the payload. Summary already has `marks.legs` (WindW = mark 1 port) and `dtl_at_gun_mm`.

When trails exist: new rows with `source` = frame stream, not invented points.

### How we display it (Lipton page only)

- Chip **RACING**
- Start chip **T+** from gun (tracker wins; 10 s player delay is why we look slightly ahead)
- Next mark line: **Mark 1 · port · 3-length zone** (from course, not from a guessed arrow)
- Results table: existing sheet / checksum. **No live tracker rank into Nett**
- Map: embed Vakaros (they have the trail). We do not fake our own mark-1 race.

If we cannot see boats on **our** map between gun and mark 1, that is correct until frames are archived. The embed still shows them.

### Race 5 check (already archived)

Gun 15:50:01 SAST. Mark 1 = windward, port. We have all 17 positions and DTL **at that gun**. We do **not** have who reached mark 1 first.
