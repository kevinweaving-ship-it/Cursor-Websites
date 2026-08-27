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

GPS **trails** come from `teleapi.regatta.app` (not Firestore). Archive them: `python3 sailingsa/scripts/lipton_mark_rounding.py --fetch` then `--save`. Frozen Race 5 mark-1 file: `docs/lipton_2026_r5_mark1_rounding.json`.

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

Gun 15:50:01 SAST. Mark 1 = windward, port.

Telemetry (`teleapi.regatta.app`, not HTML): first boat **about to round** mark 1 = **HYC 16:22:03 SAST**. Replay: `?race-day=2&ts=1787840523900`.

Rounding order (closest to mark 1, then HDG change). **>90°** = bear-away at the mark. Smaller Δ = already on a reaching heading when they got there (tack, then a smaller turn).

| # | Boat | Time SAST | ΔHDG | in→out |
|---|---|---|---|---|
| 1 | HYC | 16:22:15 | 127° | 310→183 |
| 2 | RCYC | 16:22:19 | 104° | 327→223 |
| 3 | KYC | 16:22:25 | 91° | 317→226 |
| 4 | RCYC Academy | 16:22:58 | 22° | 163→141 |
| 5 | RNYC | 16:23:16 | 130° | 330→200 |
| 6 | UCTYC | 16:23:10 | 52° | 222→170 |
| 7 | SBYC | 16:23:28 | 141° | 323→182 |
| 8 | PYC | 16:23:35 | 133° | 334→201 |
| 9 | FBYC | 16:23:35 | 112° | 339→227 |
| 10 | WBYC | 16:23:38 | 53° | 240→187 |
| 11 | IZIVUNGUVUNGU | 16:23:46 | 81° | 242→161 |
| 12 | LDYC | 16:24:05 | 59° | 231→172 |
| 13 | GLYC | 16:24:13 | 121° | 330→209 |
| 14 | BYC | 16:24:37 | 45° | 237→192 |
| 15 | TSC | 16:24:48 | 86° | 237→151 |
| 16 | LYC | 16:25:07 | 45° | 232→187 |
| 17 | WYAC | 16:25:42 | 68° | 239→171 |

## Can we rank 1st–17th at each mark? (Race 5 trail)

**Yes for lap 1 mark 1 and mark 2 — all 17.** Frozen: `docs/lipton_2026_r5_mark_orders.json`. Not finish order. Not Nett. Not live yet.

At ~11 kn, **5 m GPS ≈ 1 s** of boat travel. Gaps **>2.5 s** are a real 1st/2nd/… Gaps **under ~2 s** are a near-tie.

| Mark | 1st–17th? | First | Note |
|---|---|---|---|
| **1 WindW** | **all 17** | HYC 16:22:03 | RNYC/UCTYC +0.9 s = near-tie for 5th/6th |
| **2 Wing** | **all 17** | HYC 16:25:06 | Clean. HYC still 1st, RCYC 2nd (+4.7 s) |
| **3 Leeward** | **front 14** | HYC 16:29:11 | Academy, UCTYC, SBYC not in this pack — do not invent |
| **4 Wing 2** | **front 14** | HYC 16:32:32 | Same three missing. Device 4 is also the finish pin — do not use finish times as a rounding |
| **Finish** | all 17 | **RCYC** 17:02:00 | Firestore finish line. RCYC 1st here, HYC 1st at the marks |

Lap 2 / 3: trail exists, not a clean 17 yet. Wait for raw live GPS before showing those ranks.

## Metres to the mark / pin — when accuracy is lost

**Metres-to-mark is always computed.** It does not fade with range. 400 m out is the same GPS as 40 m out.

The error is a **fixed number of metres**, not a percent of distance:

| What | Metres |
|---|---|
| Typical trail error | **~5 m** |
| Conservative (p95) | **~10 m** |
| Do not claim closer than | **~3 m** |
| Useful precision lost inside | **~10 m** of the buoy |

So:

- **400 m → 50 m from the mark:** distance is good. “12 m vs 18 m” is real. “Going to the mark” (heading tracks the buoy, distance falling) is clean from **~300 m** down to **~50 m**.
- **~30 m:** they are already turning. Heading-to-mark is the rounding, not the approach.
- **Inside ~10 m:** GPS error is as big as the distance. “2 m from the pin” is **not** real. Closest pings in Race 5 were 2–14 m (HYC 8.5 m). That is “at the mark”, not a millimetre DTL.
- **Past the mark:** same **~5 / ~10 m**. Rounding is clear by **10–20 m past** (distance increasing + heading swung). Still accurate at 200 m past. Course to mark 2 is clearest **10–75 m** past.

**Start-gun pin DTL** is the exception: Vakaros stores millimetres (`dtlMm`) **at the gun only**. The live trail never has that.

3-length zone (~20 m) is usable (several times the noise).

## Speed at Race 5 mark 1 (knots)

**Assumption checked: they do not have to slow to round.** Median **11.3 kn** at 50 m in, **11.3 kn** at the mark, **12.1 kn** 50 m out. Only 7 of 17 dropped ≥0.8 kn.

The three big bear-aways (**>90° HDG**: HYC, RNYC, PYC) *did* dip (especially PYC 12.3→7.2 then back to 12.5). Boats already reaching kept or gained speed. So a speed dip is a **style** flag for a hard turn, not the rounding detector. Rounding is still **heading change + closest distance**.

| # | Boat | kn 50 m in | kn at mark | kn 50 m out | slowed? |
|---|---|---:|---:|---:|---|
| 1 | HYC | 11.7 | 10.2 | 11.7 | yes (−1.5) |
| 2 | RCYC | 11.3 | 10.6 | 12.1 | no |
| 3 | KYC | 10.2 | 11.0 | 12.3 | no |
| 4 | RCYC Academy | 11.0 | 12.8 | 12.1 | no |
| 5 | RNYC | 11.7 | 10.6 | 11.3 | yes (−1.1) |
| 6 | UCTYC | 11.9 | 11.0 | 10.6 | yes |
| 7 | SBYC | 9.8 | 11.3 | 12.5 | no |
| 8 | PYC | 12.3 | 7.2 | 12.5 | yes (−5.1) |
| 9 | FBYC | 12.1 | 9.4 | 14.2 | yes |
| 10 | WBYC | 11.3 | 11.3 | 12.3 | no |
| 11 | IZIVUNGUVUNGU | 9.6 | 13.6 | 11.9 | no |
| 12 | LDYC | 12.3 | 11.3 | 11.7 | yes |
| 13 | GLYC | 11.3 | 9.4 | 11.3 | yes |
| 14 | BYC | 11.1 | 12.1 | 14.0 | no |
| 15 | TSC | 11.5 | 12.5 | 12.8 | no |
| 16 | LYC | 11.3 | 11.7 | 12.3 | no |
| 17 | WYAC | 11.0 | 12.1 | 11.9 | no |

## Heel and trim (Race 5 mark 1)

Trail has **roll** (heel) and **pitch** (trim).

- **Heel is of some use.** Median |roll| **~16°** inbound (upwind) → **~9°** at the mark → **~8°** outbound (flatter on the reach). Supports “they have borne away” together with heading. Too noisy to time the rounding on its own.
- **Trim is not useful.** Pitch only moves a few degrees (median ~2° in / ~2° at / ~4° out), integer and noisy. Do not use as a rounding signal.

