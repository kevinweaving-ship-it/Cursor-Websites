#!/usr/bin/env python3
"""Load data/lipton_telemetry.sqlite into Postgres (live sailors_master)."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQLITE = Path(os.environ.get("LIPTON_SQLITE") or ROOT / "data" / "lipton_telemetry.sqlite")
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


def main() -> int:
    url = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DB_URL or DATABASE_URL required")
    if not SQLITE.exists():
        raise SystemExit(f"missing {SQLITE}")
    import psycopg2
    from psycopg2.extras import Json, execute_batch

    src = sqlite3.connect(SQLITE)
    src.row_factory = None
    q = """SELECT race, sn, sail_number, ts, latitude, longitude, heading, sog, role, fetch_pass, rec_json FROM telemetry"""
    conn = psycopg2.connect(url)
    inserted = 0
    with conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
            batch = []
            for r in src.execute(q):
                batch.append(
                    (
                        r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9],
                        Json(json.loads(r[10])),
                    )
                )
                if len(batch) >= 1000:
                    execute_batch(
                        cur,
                        """
                        INSERT INTO public.lipton_telemetry (
                            race_number, sn, sail_number, ts, latitude, longitude,
                            heading, sog, role, fetch_pass, rec
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (race_number, sn, sail_number, ts, latitude, longitude) DO NOTHING
                        """,
                        batch,
                        page_size=1000,
                    )
                    inserted += len(batch)
                    batch = []
            if batch:
                execute_batch(
                    cur,
                    """
                    INSERT INTO public.lipton_telemetry (
                        race_number, sn, sail_number, ts, latitude, longitude,
                        heading, sog, role, fetch_pass, rec
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (race_number, sn, sail_number, ts, latitude, longitude) DO NOTHING
                    """,
                    batch,
                    page_size=1000,
                )
                inserted += len(batch)
            cur.execute("SELECT race_number, COUNT(*) FROM public.lipton_telemetry GROUP BY 1 ORDER BY 1")
            counts = cur.fetchall()
    print(json.dumps({"ok": True, "inserted_from": inserted, "per_race": counts}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
