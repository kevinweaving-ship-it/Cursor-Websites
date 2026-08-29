#!/usr/bin/env python3
"""Archive one GPS pass then pack replay + trail for finished Lipton races.

Saves our copy of teleapi rows (Vakaros will hide them). Does not invent GPS.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipton_dev_archive_telemetry import db, insert_rows, load_race_rows, write_jsonl  # noqa: E402
from lipton_dev_record_telemetry import race_window  # noqa: E402
from lipton_mark_rounding import fetch_rows  # noqa: E402
from lipton_vakaros import _j22_division, fetch_regatta_doc  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RACES_JSON = ROOT / "sailingsa/frontend/js/lipton-dev-races.json"
RACES_COPY = ROOT / "js/lipton-dev-races.json"
SAST = ZoneInfo("Africa/Johannesburg")
SCRIPTS = Path(__file__).resolve().parent


def dump_firestore() -> dict:
    doc = fetch_regatta_doc()
    out = ROOT / "data/lipton_vakaros_regatta.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False))
    return doc


def firestore_races(doc: dict) -> dict[int, dict]:
    out = {}
    for r in _j22_division(doc)["races"]:
        n = int(r.get("raceNumber") or 0)
        if not n:
            continue
        s0 = (r.get("starts") or [{}])[0]
        gun = s0.get("startTime")
        gun_sast = ""
        if gun:
            dt = datetime.fromisoformat(str(gun).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=SAST)
            gun_sast = dt.astimezone(SAST).isoformat()
        out[n] = {
            "n": n,
            "stage": "finished",
            "gun_sast": gun_sast,
            "finish_n": len(r.get("finishes") or []),
            "ocs": [str(x) for x in (s0.get("ocsParticipants") or [])],
            "packed": False,
            "held_live": False,
            "course": "",
            "course_id": "",
        }
    return out


def ensure_archive(race: int) -> int:
    rows = load_race_rows(race)
    if rows:
        print(json.dumps({"race": race, "archive_rows": len(rows), "source": "existing"}), flush=True)
        return len(rows)
    after, before = race_window(race)
    print(json.dumps({"race": race, "fetch": True, "after": after, "before": before}), flush=True)
    rows = fetch_rows(after, before, verbose=True)
    conn = db()
    added = insert_rows(conn, race, 1, rows)
    path = write_jsonl(race, conn)
    print(json.dumps({"race": race, "fetched": len(rows), "new": added, "jsonl": str(path)}), flush=True)
    return len(rows)


def pack_race(race: int) -> None:
    subprocess.check_call([sys.executable, str(SCRIPTS / "lipton_dev_pack_race4.py"), "--race", str(race)])
    subprocess.check_call([sys.executable, str(SCRIPTS / "lipton_dev_pack_trail.py"), "--race", str(race)])


def replay_path(race: int) -> Path:
    if race == 4:
        return ROOT / "sailingsa/frontend/js/lipton-dev-replay.json"
    return ROOT / f"sailingsa/frontend/js/lipton-dev-replay-r{race}.json"


def update_races_json(fs: dict[int, dict]) -> None:
    prev = json.loads(RACES_JSON.read_text()) if RACES_JSON.exists() else {"races": []}
    by = {int(r["n"]): r for r in prev.get("races") or []}
    for n in range(1, 11):
        row = dict(fs.get(n) or by.get(n) or {"n": n, "stage": "finished", "ocs": [], "packed": False})
        path = replay_path(n)
        if path.exists():
            pack = json.loads(path.read_text())
            cs = pack.get("checksum") or {}
            course = pack.get("course") or {}
            row["packed"] = True
            row["held_live"] = False
            row["stage"] = "finished"
            row["finish_n"] = len(pack.get("finish") or [])
            row["ocs"] = pack.get("ocs") or row.get("ocs") or []
            row["gun_sast"] = pack.get("gun_sast") or row.get("gun_sast") or ""
            row["course"] = course.get("label") if isinstance(course, dict) else (course or row.get("course") or "")
            row["course_id"] = course.get("id") if isinstance(course, dict) else row.get("course_id") or ""
            row["checksum_ok"] = bool(cs.get("ok"))
            row["sanity_ok"] = bool((cs.get("sanity") or {}).get("ok"))
            row["checksum_sha16"] = cs.get("sha256")
        by[n] = row
    prev["event_id"] = prev.get("event_id") or "Lv9A35uOBSBRmGpHgXtH"
    prev["fleet"] = "J22"
    prev["note"] = "All J22 races from Vakaros. packed=true means -dev has GPS replay JSON. Event over — no Live."
    prev["races"] = [by[n] for n in range(1, 11)]
    text = json.dumps(prev, indent=2, ensure_ascii=False) + "\n"
    RACES_JSON.write_text(text)
    RACES_COPY.parent.mkdir(parents=True, exist_ok=True)
    RACES_COPY.write_text(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--races", default="8,9,10,6")
    args = ap.parse_args()
    races = [int(x) for x in args.races.split(",") if x.strip()]
    doc = dump_firestore()
    fs = firestore_races(doc)
    update_races_json(fs)
    for race in races:
        ensure_archive(race)
        pack_race(race)
        update_races_json(fs)
    print(json.dumps({"ok": True, "races": races, "races_json": str(RACES_JSON)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
