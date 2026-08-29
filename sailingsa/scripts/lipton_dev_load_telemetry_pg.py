#!/usr/bin/env python3
"""Load Lipton GPS into Postgres (live sailors_master).

Reads data/lipton_telemetry.sqlite, or a jsonl file via LIPTON_JSONL.
Does not invent points. Unique pings only.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

_here = Path(__file__).resolve()
try:
    ROOT = _here.parents[2]
except IndexError:
    ROOT = _here.parent
SQLITE = Path(os.environ.get("LIPTON_SQLITE") or ROOT / "data" / "lipton_telemetry.sqlite")
JSONL = Path(os.environ["LIPTON_JSONL"]) if os.environ.get("LIPTON_JSONL") else None
DDL = """
CREATE TABLE IF NOT EXISTS public.lipton_telemetry (
    id BIGSERIAL PRIMARY KEY,
    race_number INTEGER NOT NULL,
    sn TEXT,
    sail_number TEXT,
    ts BIGINT NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    heading DOUBLE PRECISION,
    sog DOUBLE PRECISION,
    role TEXT,
    fetch_pass INTEGER,
    rec JSONB NOT NULL,
    UNIQUE (race_number, sn, sail_number, ts, latitude, longitude)
);
CREATE INDEX IF NOT EXISTS lipton_telemetry_race_ts_idx
    ON public.lipton_telemetry (race_number, ts);
"""
SQL = """
INSERT INTO public.lipton_telemetry (
    race_number, sn, sail_number, ts, latitude, longitude,
    heading, sog, role, fetch_pass, rec
) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (race_number, sn, sail_number, ts, latitude, longitude) DO NOTHING
"""


def iter_rows():
    if JSONL:
        race = int(os.environ.get("LIPTON_RACE") or 0)
        with JSONL.open(encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                rn = race or int(rec.get("race_number") or rec.get("race") or 0)
                yield (
                    rn,
                    str(rec.get("sn") or ""),
                    rec.get("sail_number"),
                    int(rec["ts"]),
                    rec.get("latitude"),
                    rec.get("longitude"),
                    rec.get("heading"),
                    rec.get("sog"),
                    rec.get("role"),
                    int(rec.get("fetch_pass") or 1),
                    rec,
                )
        return
    if not SQLITE.exists():
        raise SystemExit(f"missing {SQLITE}")
    src = sqlite3.connect(SQLITE)
    q = """SELECT race, sn, sail_number, ts, latitude, longitude, heading, sog, role, fetch_pass, rec_json FROM telemetry"""
    for r in src.execute(q):
        yield (
            r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9],
            json.loads(r[10]),
        )


def main() -> int:
    url = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DB_URL or DATABASE_URL required")
    import psycopg2
    from psycopg2.extras import Json, execute_batch

    conn = psycopg2.connect(url)
    inserted = 0
    with conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
            batch = []
            seen = 0
            for r in iter_rows():
                batch.append(
                    (
                        r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9],
                        Json(r[10]),
                    )
                )
                if len(batch) >= 1000:
                    execute_batch(cur, SQL, batch, page_size=1000)
                    inserted += len(batch)
                    seen += len(batch)
                    batch = []
                    if seen % 50000 == 0:
                        print(json.dumps({"progress": seen}), flush=True)
            if batch:
                execute_batch(cur, SQL, batch, page_size=1000)
                inserted += len(batch)
            cur.execute("SELECT race_number, COUNT(*) FROM public.lipton_telemetry GROUP BY 1 ORDER BY 1")
            counts = cur.fetchall()
    print(json.dumps({"ok": True, "inserted_from": inserted, "per_race": counts, "source": str(JSONL or SQLITE)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
