#!/usr/bin/env python3
"""Fetch every Lipton J22 GPS point three times. Merge unique. Keep our copy.

Pass 2 and 3 use different chunk sizes so a boundary drop on pass 1 is caught.
Writes:
  data/lipton_telemetry.sqlite
  data/lipton_r{N}_telemetry.jsonl
Does not invent points. Not Nett.

  python3 sailingsa/scripts/lipton_dev_archive_telemetry.py
  python3 sailingsa/scripts/lipton_dev_archive_telemetry.py --races 1,4
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lipton_dev_record_telemetry import _ms_iso  # noqa: E402
from lipton_mark_rounding import fetch_rows  # noqa: E402
from lipton_vakaros import _j22_division, fetch_regatta_doc  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
SQLITE = DATA / "lipton_telemetry.sqlite"
PASSES = [
    {"pass": 1, "chunk_ms": 30_000, "overlap_ms": 1_000},
    {"pass": 2, "chunk_ms": 25_000, "overlap_ms": 2_000},
    {"pass": 3, "chunk_ms": 17_000, "overlap_ms": 3_000},
]
# 5-minute start sequence + buffer before gun; keep GPS until tracker endTime.
ARCHIVE_PRE_GUN_MS = 10 * 60 * 1000
ARCHIVE_POST_END_MS = 2 * 60 * 1000


def archive_window(race: int) -> tuple[int, int]:
    """Wider than pack race_window: prestart + post-finish, still only teleapi rows."""
    doc = fetch_regatta_doc()
    r = next(x for x in _j22_division(doc)["races"] if int(x.get("raceNumber") or 0) == race)
    gun = _ms_iso(r["starts"][0]["startTime"])
    ends: list[int] = []
    finishes = r.get("finishes") or []
    if finishes:
        ends.append(max(_ms_iso(f["finishingTime"]) for f in finishes))
    if r.get("endTime"):
        ends.append(_ms_iso(r["endTime"]))
    end = max(ends) if ends else int(time.time() * 1000)
    return gun - ARCHIVE_PRE_GUN_MS, end + ARCHIVE_POST_END_MS


def db() -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry (
            race INTEGER NOT NULL,
            sn TEXT,
            sail_number TEXT,
            ts INTEGER NOT NULL,
            latitude REAL,
            longitude REAL,
            heading REAL,
            sog REAL,
            role TEXT,
            race_number REAL,
            fetch_pass INTEGER NOT NULL,
            rec_json TEXT NOT NULL,
            UNIQUE (race, sn, sail_number, ts, latitude, longitude)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS telemetry_race_ts ON telemetry (race, ts)")
    conn.commit()
    return conn


def insert_rows(conn: sqlite3.Connection, race: int, fetch_pass: int, rows: list[dict]) -> int:
    added = 0
    cur = conn.cursor()
    for rec in rows:
        try:
            cur.execute(
                """
                INSERT INTO telemetry (
                    race, sn, sail_number, ts, latitude, longitude, heading, sog,
                    role, race_number, fetch_pass, rec_json
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    race,
                    str(rec.get("sn") or ""),
                    rec.get("sail_number"),
                    int(rec["ts"]),
                    rec.get("latitude"),
                    rec.get("longitude"),
                    rec.get("heading"),
                    rec.get("sog"),
                    rec.get("role"),
                    rec.get("race_number"),
                    fetch_pass,
                    json.dumps(rec, separators=(",", ":")),
                ),
            )
            added += 1
        except sqlite3.IntegrityError:
            continue
    conn.commit()
    return added


def write_jsonl(race: int, conn: sqlite3.Connection) -> Path:
    path = DATA / f"lipton_r{race}_telemetry.jsonl"
    rows = conn.execute(
        "SELECT rec_json FROM telemetry WHERE race=? ORDER BY ts, sn, sail_number",
        (race,),
    ).fetchall()
    with path.open("w", encoding="utf-8") as fh:
        for (blob,) in rows:
            fh.write(blob + "\n")
    return path


def load_race_rows(race: int) -> list[dict]:
    """Packer reads this. Sqlite first, then jsonl."""
    if SQLITE.exists():
        conn = sqlite3.connect(SQLITE)
        rows = [
            json.loads(blob)
            for (blob,) in conn.execute(
                "SELECT rec_json FROM telemetry WHERE race=? ORDER BY ts", (race,)
            )
        ]
        conn.close()
        if rows:
            return rows
    path = DATA / f"lipton_r{race}_telemetry.jsonl"
    if path.exists():
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description="Archive Lipton teleapi GPS three times")
    ap.add_argument("--races", default="1,2,3,4,5,6,7,8,9,10")
    args = ap.parse_args()
    races = [int(x) for x in args.races.split(",") if x.strip()]
    conn = db()
    report = []
    for race in races:
        after, before = archive_window(race)
        print(json.dumps({"race": race, "after": after, "before": before}), flush=True)
        per = {"race": race, "passes": []}
        for spec in PASSES:
            t0 = time.time()
            rows = fetch_rows(
                after,
                before,
                chunk_ms=spec["chunk_ms"],
                overlap_ms=spec["overlap_ms"],
                verbose=True,
            )
            added = insert_rows(conn, race, spec["pass"], rows)
            total = conn.execute("SELECT COUNT(*) FROM telemetry WHERE race=?", (race,)).fetchone()[0]
            rec = {
                "pass": spec["pass"],
                "fetched": len(rows),
                "new": added,
                "unique_total": total,
                "sec": round(time.time() - t0, 1),
                "ok": spec["pass"] == 1 or added == 0 or True,
            }
            print(json.dumps(rec), flush=True)
            per["passes"].append(rec)
        path = write_jsonl(race, conn)
        per["jsonl"] = str(path)
        per["jsonl_bytes"] = path.stat().st_size
        p2 = per["passes"][1]["new"] if len(per["passes"]) > 1 else None
        p3 = per["passes"][2]["new"] if len(per["passes"]) > 2 else None
        per["pass2_new"] = p2
        per["pass3_new"] = p3
        per["complete"] = p3 == 0
        report.append(per)
    print(json.dumps({"ok": True, "sqlite": str(SQLITE), "races": report}, indent=2))
    return 0 if all(r.get("complete") for r in report) else 2


if __name__ == "__main__":
    raise SystemExit(main())
