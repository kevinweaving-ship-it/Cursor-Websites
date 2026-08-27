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
WATCH_URL = (
    f"https://player.vakaros.com/watch/{LIPTON_EVENT_ID}/{LIPTON_FLEET}?live=true"
)
FIREBASE_PROJECT = "vakaros-racesense"
# Public web API key shipped in player.vakaros.com/main.dart.js
FIREBASE_WEB_API_KEY = "AIzaSyDoQfjoAtx9g3sS7MzKUM0gGwW8tREKxwk"
SAST = ZoneInfo("Africa/Johannesburg")
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
        "source_fields": ["divisions[].races[]", "starts[].startTime", "finishes[].finishingTime", "currentStage"],
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
        "races": races,
        "days": [{"date_sast": d, "races": nums} for d, nums in sorted(days.items())],
        "last_finished_race": last_finished["race_number"] if last_finished else None,
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
