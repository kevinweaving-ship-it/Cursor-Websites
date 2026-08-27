#!/usr/bin/env python3
"""Lipton 2026 only — read race days from the Vakaros tracking system.

The public watch page is a Flutter shell. It does not contain Race 1 / Day 1
in the HTML. The player loads event data from Firebase Firestore
(project vakaros-racesense), collection `regattas/{eventId}`.

This module talks to that same backend. It does not invent race numbers,
days, or start times. If Firestore has no races, this returns an error.

Watch URL (Lipton J22):
  https://player.vakaros.com/watch/Lv9A35uOBSBRmGpHgXtH/J22?live=true

`?live=true` is a player view flag in *our* saved URL. It is not proof the
race officer switched tracking on or off overnight. Overnight on/off must
be observed from tracker state, not from our stored query string.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

LIPTON_SLUG = "2026-08-29-lipton-challenge-cup"
LIPTON_EVENT_ID = "Lv9A35uOBSBRmGpHgXtH"
LIPTON_FLEET = "J22"
WATCH_PATH = f"/watch/{LIPTON_EVENT_ID}/{LIPTON_FLEET}"
WATCH_ORIGIN = "https://player.vakaros.com"
WATCH_URL = f"{WATCH_ORIGIN}{WATCH_PATH}?live=true"
FIREBASE_PROJECT = "vakaros-racesense"
# Public web API key shipped in player.vakaros.com/main.dart.js
FIREBASE_WEB_API_KEY = "AIzaSyDoQfjoAtx9g3sS7MzKUM0gGwW8tREKxwk"
SAST = ZoneInfo("Africa/Johannesburg")
FINISHED_STAGES = {"finished"}
SNAPSHOT_DDL = """
CREATE TABLE IF NOT EXISTS public.vakaros_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    regatta_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    fleet TEXT,
    source TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tracker_modified_ts TIMESTAMPTZ,
    tracker_create_time TIMESTAMPTZ,
    tracker_update_time TIMESTAMPTZ,
    sequence_number INTEGER,
    payload_sha256 TEXT NOT NULL,
    payload JSONB NOT NULL,
    payload_raw JSONB NOT NULL,
    summary JSONB,
    player_html JSONB,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS vakaros_snapshots_regatta_fetched_idx
    ON public.vakaros_snapshots (regatta_id, fetched_at DESC);
CREATE INDEX IF NOT EXISTS vakaros_snapshots_event_idx
    ON public.vakaros_snapshots (event_id, fetched_at DESC);
"""


def ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(SNAPSHOT_DDL)
    conn.commit()


class VakarosSourceError(RuntimeError):
    pass


def _http_json(url: str, *, data: bytes | None = None, headers: dict | None = None, timeout: int = 30):
    hdrs = {"User-Agent": "SailingSA-LiptonVakaros/1.0", "Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw.decode("utf-8") if raw else "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"raw": body[:500]}
        return e.code, parsed


def _decode_val(v):
    if not isinstance(v, dict):
        return v
    if "stringValue" in v:
        return v["stringValue"]
    if "integerValue" in v:
        return int(v["integerValue"])
    if "doubleValue" in v:
        return v["doubleValue"]
    if "booleanValue" in v:
        return v["booleanValue"]
    if "timestampValue" in v:
        return v["timestampValue"]
    if "nullValue" in v:
        return None
    if "arrayValue" in v:
        return [_decode_val(x) for x in v["arrayValue"].get("values", [])]
    if "mapValue" in v:
        return {k: _decode_val(x) for k, x in v["mapValue"].get("fields", {}).items()}
    return v


def decode_firestore_doc(doc: dict) -> dict:
    fields = doc.get("fields") or {}
    return {k: _decode_val(v) for k, v in fields.items()}


def parse_ts(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        s = str(value).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def to_sast(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.astimezone(SAST)


def anonymous_id_token(api_key: str = FIREBASE_WEB_API_KEY) -> str:
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}"
    status, body = _http_json(
        url,
        data=json.dumps({"returnSecureToken": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    token = (body or {}).get("idToken") if isinstance(body, dict) else None
    if status != 200 or not token:
        raise VakarosSourceError(f"Firebase anonymous auth failed HTTP {status}: {body}")
    return token


def ms_utc(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)


def build_watch_url(*, race_day: int = 1, live: bool = False, ts_ms: int | None = None) -> str:
    """Same query rules as player.vakaros.com (Flutter route `avt.gCy`).

    - race-day omitted when 1
    - live omitted when false
    - ts = playback instant in unix milliseconds
    """
    q: list[str] = []
    if int(race_day) != 1:
        q.append(f"race-day={int(race_day)}")
    if live:
        q.append("live=true")
    if ts_ms is not None:
        q.append(f"ts={int(ts_ms)}")
    url = f"{WATCH_ORIGIN}{WATCH_PATH}"
    return url + (("?" + "&".join(q)) if q else "")


def t_sign_and_seconds(*, playback: datetime | None, gun: datetime | None) -> dict | None:
    """Player T-/T+ chip: compare playback clock to that race's gun.

    From main.dart.js adG/akT: before gun → T- (gun-now); at/after gun → T+ (now-gun).
    Not a stored Firestore field.
    """
    if playback is None or gun is None:
        return None
    delta = (gun - playback).total_seconds()
    if delta > 0:
        return {"sign": "T-", "seconds": round(delta, 3), "label": "before gun"}
    return {"sign": "T+", "seconds": round(-delta, 3), "label": "after gun"}


def race_day_index(day_sast: str | None, day_list: list[str]) -> int | None:
    if not day_sast:
        return None
    try:
        return day_list.index(day_sast) + 1
    except ValueError:
        return None


def fetch_player_html(url: str = WATCH_URL) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SailingSA-LiptonVakaros/1.0", "Accept": "text/html"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def player_html_is_shell_only(html: str) -> dict:
    """The watch URL is a Flutter splash page. Race lists are not in this HTML."""
    low = html.lower()
    return {
        "is_flutter_shell": "flutter.js" in low or "racesense" in low,
        "has_now_loading": "now loading" in low,
        "mentions_race_1": "race 1" in low,
        "mentions_day_1": "day 1" in low or "day 1." in low,
        "mentions_network_race_number": "networkracenumber" in low,
    }


def fetch_regatta_raw(event_id: str = LIPTON_EVENT_ID, token: str | None = None) -> dict:
    """Raw Firestore REST document. Keep this — it is the lossless archive."""
    tok = token or anonymous_id_token()
    url = (
        "https://firestore.googleapis.com/v1/projects/"
        f"{FIREBASE_PROJECT}/databases/(default)/documents/regattas/{event_id}"
    )
    status, body = _http_json(url, headers={"Authorization": f"Bearer {tok}"})
    if status != 200:
        raise VakarosSourceError(f"Firestore regattas/{event_id} HTTP {status}: {body}")
    if not isinstance(body, dict) or "fields" not in body:
        raise VakarosSourceError(f"Firestore regattas/{event_id} had no fields")
    return body


def fetch_regatta_doc(event_id: str = LIPTON_EVENT_ID, token: str | None = None) -> dict:
    return decode_firestore_doc(fetch_regatta_raw(event_id=event_id, token=token))


def _j22_division(doc: dict) -> dict:
    divisions = doc.get("divisions") or []
    for div in divisions:
        if not isinstance(div, dict):
            continue
        name = str(div.get("name") or "")
        boat = str(div.get("boatClass") or "")
        if name.upper() == "J22" or "J/22" in boat or "J22" in boat.replace(" ", ""):
            return div
    if len(divisions) == 1 and isinstance(divisions[0], dict):
        return divisions[0]
    raise VakarosSourceError("No J22 division in Vakaros regatta document")


def _summarize_race(race: dict) -> dict:
    starts = race.get("starts") or []
    start0 = starts[0] if starts and isinstance(starts[0], dict) else {}
    gun = parse_ts(start0.get("startTime"))
    finishes = race.get("finishes") or []
    finish_ts = [parse_ts(f.get("finishingTime")) for f in finishes if isinstance(f, dict)]
    finish_ts = [t for t in finish_ts if t is not None]
    gun_sast = to_sast(gun)
    first_finish = to_sast(min(finish_ts)) if finish_ts else None
    last_finish = to_sast(max(finish_ts)) if finish_ts else None
    end_sast = to_sast(parse_ts(race.get("endTime")))
    day = None
    if gun_sast is not None:
        day = gun_sast.date().isoformat()
    elif first_finish is not None:
        day = first_finish.date().isoformat()
    stage = str(race.get("currentStage") or "").strip().lower()
    race_no = race.get("raceNumber")
    try:
        race_no = int(race_no)
    except (TypeError, ValueError):
        raise VakarosSourceError(f"Race missing integer raceNumber: {race.get('raceNumber')!r}")
    return {
        "race_number": race_no,
        "network_race_number": race.get("networkRaceNumber"),
        "name": race.get("name"),
        "stage": stage,
        "is_practice": bool(race.get("isPractice")),
        "gun_at_utc": gun.isoformat() if gun else None,
        "gun_at_sast": gun_sast.isoformat() if gun_sast else None,
        "day_sast": day,
        "finish_count": len(finishes),
        "first_finish_sast": first_finish.isoformat() if first_finish else None,
        "last_finish_sast": last_finish.isoformat() if last_finish else None,
        "end_sast": end_sast.isoformat() if end_sast else None,
        "ocs": list(start0.get("ocsParticipants") or []),
        "prep_flag": start0.get("prepFlag"),
        "start_line": start0.get("startLine"),
        "dtl_at_gun_mm": {
            s.get("sailNumber"): s.get("dtlMm")
            for s in (start0.get("startingStats") or [])
            if isinstance(s, dict) and s.get("sailNumber")
        },
        "source_fields": [
            "divisions[].races[]",
            "starts[].startTime",
            "starts[].startLine",
            "starts[].startingStats.dtlMm",
            "finishes[].finishingTime",
            "currentStage",
        ],
    }


def extract_course_hardware(doc: dict, div: dict) -> dict:
    """What the map is drawing: RC, pin, marks 1–4. Positions only where Firestore stored them."""
    devices = []
    for d in doc.get("rcDevices") or []:
        if not isinstance(d, dict):
            continue
        devices.append(
            {
                "name": d.get("name"),
                "role": d.get("role"),
                "sn": d.get("sn"),
                "mark_type": d.get("markType"),
                "mark_radius_cm": d.get("markRadius"),
            }
        )
    by_sn = {d["sn"]: d for d in devices if d.get("sn")}
    legs = []
    courses = div.get("courses") or []
    course0 = courses[0] if courses and isinstance(courses[0], dict) else {}
    for a in course0.get("achievements") or []:
        if not isinstance(a, dict):
            continue
        roles = []
        for r in a.get("deviceRoles") or []:
            sn = r.get("sn")
            roles.append(
                {
                    "role": r.get("role"),
                    "sn": sn,
                    "device_name": (by_sn.get(sn) or {}).get("name"),
                    "device_role": (by_sn.get(sn) or {}).get("role"),
                }
            )
        legs.append(
            {
                "title": a.get("title"),
                "type": a.get("type"),
                "rounding": a.get("roundingDirection"),
                "roles": roles,
            }
        )
    start = next((x for x in legs if x.get("type") == "startLine"), None)
    finish = next((x for x in legs if x.get("type") == "finishLine"), None)

    def _end(line, want):
        if not line:
            return None
        for r in line.get("roles") or []:
            if r.get("role") == want:
                return r
        return None

    return {
        "devices": devices,
        "course_name": course0.get("name"),
        "legs": legs,
        "line_ends": {
            "pin": _end(start, "startLeft"),
            "committee_boat": _end(start, "startRight"),
            "finish_pin": _end(finish, "finishLeft"),
            "finish_committee": _end(finish, "finishRight"),
        },
        "rounding_zone": {
            "enabled": bool(div.get("markZoneEnabled")),
            "boat_lengths": div.get("numBoatLengthsForZone"),
            "mark_role_on_course": "markPort means leave the mark to port (round to port)",
        },
        "note": (
            "Tracker does not label a device 'Pin'. Start/finish left end is device name '4'. "
            "Committee boat is device name 'RC' (role coordinator). "
            "Marks 1=windward, 2=wing, 3=leeward. "
            "Lat/lon for pin+RC exist at each gun (startLine) and at each finish "
            "(lineLeftLocation/lineRightLocation). Mark 1/2/3 lat/lon are not in this "
            "spectator document — replay map draws them from GPS frames we cannot download yet. "
            "Distance-to-line at the gun is stored as dtlMm (millimetres)."
        ),
    }


def summarize_event(doc: dict) -> dict:
    name = doc.get("name")
    if not name:
        raise VakarosSourceError("Vakaros document has no event name")
    div = _j22_division(doc)
    raw_races = div.get("races")
    if not isinstance(raw_races, list) or not raw_races:
        raise VakarosSourceError("Vakaros J22 division has no races[] — refusing to invent")
    races = [_summarize_race(r) for r in raw_races if isinstance(r, dict)]
    races.sort(key=lambda r: r["race_number"])
    days: dict[str, list[int]] = {}
    for r in races:
        if r["day_sast"]:
            days.setdefault(r["day_sast"], []).append(r["race_number"])
    unfinished = [r for r in races if r["stage"] not in FINISHED_STAGES]
    if unfinished:
        next_race = min(r["race_number"] for r in unfinished)
        next_reason = f"unfinished race on tracker (stage={unfinished[0]['stage']})"
    else:
        next_race = max(r["race_number"] for r in races) + 1
        next_reason = "all tracker races currentStage=finished"
    last_finished = None
    finished = [r for r in races if r["stage"] in FINISHED_STAGES]
    if finished:
        last_finished = max(finished, key=lambda r: r["race_number"])
    last_finished_no = last_finished["race_number"] if last_finished else None
    day_list = sorted(days.keys())
    for r in races:
        r["race_day"] = race_day_index(r.get("day_sast"), day_list)
        gun = parse_ts(r.get("gun_at_utc"))
        end = parse_ts(r.get("end_sast"))
        day_n = r["race_day"] or 1
        r["replay"] = {
            "at_gun": build_watch_url(race_day=day_n, ts_ms=ms_utc(gun)) if gun else None,
            "at_end": build_watch_url(race_day=day_n, ts_ms=ms_utc(end)) if end else None,
            "prestart_5min": build_watch_url(race_day=day_n, ts_ms=ms_utc(gun) - 5 * 60 * 1000) if gun else None,
        }
    replay_examples = []
    by_no = {r["race_number"]: r for r in races}
    if 4 in by_no and 5 in by_no:
        r4, r5 = by_no[4], by_no[5]
        g4, e4 = parse_ts(r4.get("gun_at_utc")), parse_ts(r4.get("end_sast"))
        g5 = parse_ts(r5.get("gun_at_utc"))
        day_n = r5.get("race_day") or r4.get("race_day") or 2
        gap_ts = ms_utc(e4)
        replay_examples.append(
            {
                "name": "between_r4_and_r5",
                "note": "Replay after R4 finished, before R5 gun. Left clock = ts. T- chip = R5 gun minus ts.",
                "race_day": day_n,
                "playback_sast": e4.isoformat() if e4 else None,
                "r4_gun_sast": r4.get("gun_at_sast"),
                "r4_end_sast": r4.get("end_sast"),
                "r5_gun_sast": r5.get("gun_at_sast"),
                "url": build_watch_url(race_day=day_n, ts_ms=gap_ts) if gap_ts else None,
                "t_minus_vs_r5_gun": t_sign_and_seconds(playback=e4, gun=g5),
                "t_plus_vs_r4_gun": t_sign_and_seconds(playback=e4, gun=g4),
            }
        )
    return {
        "ok": True,
        "source": {
            "system": "vakaros_racesense",
            "method": "firebase_anonymous_auth + firestore_get",
            "project": FIREBASE_PROJECT,
            "collection": "regattas",
            "event_id": doc.get("id") or LIPTON_EVENT_ID,
            "watch_url": WATCH_URL,
            "not_used": [
                "player HTML (Flutter shell has no race list)",
                "SailingSA results table",
                "wall clock / 12:00 / 17:00",
                "saved URL ?live=true query string as overnight on/off",
            ],
        },
        "event_name": name,
        "start_date": doc.get("startDate"),
        "end_date": doc.get("endDate"),
        "modified_ts": doc.get("modifiedTs"),
        "fleet": div.get("name"),
        "network_race_number": div.get("networkRaceNumber"),
        "countdown_type": div.get("countdownType"),
        "start_length": div.get("startLength"),
        "player_chrome": {
            "url": {
                "path": WATCH_PATH,
                "race-day": "1-based day index from tracker guns (Day 1 omitted in URL)",
                "live": "true only while the player is in live mode; omitted = replay",
                "ts": "unix ms playback instant; left-hand clock in replay",
            },
            "left_clock": "Replay: URL ts / scrubber. Live: wall clock. Not T-.",
            "t_minus_t_plus": "Computed in player: playback vs selected race starts[].startTime. Not stored.",
            "go_live": "Shown when live=false. Does not mean racing.",
        },
        "replay_examples": replay_examples,
        "marks": extract_course_hardware(doc, div),
        "races": races,
        "days": [{"date_sast": d, "races": nums, "race_day": i} for i, (d, nums) in enumerate(sorted(days.items()), start=1)],
        "last_finished_race": last_finished_no,
        "next_race_number": next_race,
        "next_race_reason": next_reason,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def fetch_lipton_archive() -> dict:
    """Full tracker pull for DB archive: raw REST + decoded payload + summary."""
    html = fetch_player_html()
    html_probe = player_html_is_shell_only(html)
    raw = fetch_regatta_raw()
    doc = decode_firestore_doc(raw)
    summary = summarize_event(doc)
    summary["player_html"] = html_probe
    if html_probe.get("mentions_race_1") or html_probe.get("mentions_day_1"):
        summary["player_html_note"] = (
            "HTML unexpectedly mentioned a race/day label — re-check scrape vs Firestore"
        )
    else:
        summary["player_html_note"] = (
            "Confirmed: watch URL HTML is the Flutter shell only. "
            "Race/day list came from Firestore, which is what the player loads."
        )
    payload_bytes = json.dumps(doc, sort_keys=True, default=str).encode("utf-8")
    return {
        "summary": summary,
        "payload": doc,
        "payload_raw": raw,
        "player_html": html_probe,
        "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
    }


def fetch_lipton_from_tracker() -> dict:
    return fetch_lipton_archive()["summary"]


def _db_url() -> str:
    url = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise VakarosSourceError("DB_URL or DATABASE_URL required to save a snapshot")
    return url


def save_snapshot(archive: dict, db_url: str | None = None) -> dict:
    """Append-only insert of the full tracker document. Lipton slug only."""
    import psycopg2
    from psycopg2.extras import Json

    summary = archive["summary"]
    if not summary.get("races"):
        raise VakarosSourceError("refusing to save: tracker returned no races")
    conn = psycopg2.connect(db_url or _db_url())
    try:
        ensure_table(conn)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.vakaros_snapshots (
                        regatta_id, event_id, fleet, source,
                        tracker_modified_ts, tracker_create_time, tracker_update_time,
                        sequence_number, payload_sha256, payload, payload_raw,
                        summary, player_html, notes
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s
                    )
                    RETURNING snapshot_id, fetched_at
                    """,
                    (
                        LIPTON_SLUG,
                        LIPTON_EVENT_ID,
                        summary.get("fleet"),
                        "firestore_regattas",
                        summary.get("modified_ts"),
                        (archive["payload_raw"] or {}).get("createTime"),
                        (archive["payload_raw"] or {}).get("updateTime"),
                        archive["payload"].get("sequenceNumber"),
                        archive["payload_sha256"],
                        Json(archive["payload"]),
                        Json(archive["payload_raw"]),
                        Json(summary),
                        Json(archive["player_html"]),
                        "Full Vakaros spectator document. GPS replay frames are not in this collection.",
                    ),
                )
                row = cur.fetchone()
    finally:
        conn.close()
    return {
        "ok": True,
        "snapshot_id": row[0],
        "fetched_at": row[1].isoformat() if row[1] else None,
        "payload_sha256": archive["payload_sha256"],
        "bytes": len(json.dumps(archive["payload"], default=str)),
        "races": len(summary.get("races") or []),
        "last_finished_race": summary.get("last_finished_race"),
        "next_race_number": summary.get("next_race_number"),
        "days": summary.get("days"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Lipton Vakaros tracker source")
    ap.add_argument(
        "--save",
        action="store_true",
        help="Insert the full tracker document into public.vakaros_snapshots (needs DB_URL)",
    )
    args = ap.parse_args()
    try:
        archive = fetch_lipton_archive()
        summary = archive["summary"]
        if args.save:
            result = save_snapshot(archive)
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(summary, indent=2))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, indent=2))
        return 1
    if not summary.get("races") or summary.get("next_race_number") is None:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
