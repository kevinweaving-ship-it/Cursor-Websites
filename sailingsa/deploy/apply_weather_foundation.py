#!/usr/bin/env python3
"""Apply generic weather schema + seed Wind2Speed Zeekoevlei + import Windguru sqlite."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path("/var/www/sailingsa")
SQL = ROOT / "sailingsa/backend/sql/001_weather_foundation.sql"
if not SQL.exists():
    SQL = Path(__file__).resolve().parents[1] / "backend/sql/001_weather_foundation.sql"


def main() -> None:
    sys.path.insert(0, str(ROOT if ROOT.exists() else Path(__file__).resolve().parents[2]))
    from sailingsa.backend.weather_store import _connect, import_windguru_sqlite

    sql = SQL.read_text(encoding="utf-8")
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            print("pg", cur.fetchone())
            buf = []
            for line in sql.splitlines():
                buf.append(line)
                joined = "\n".join(buf).strip()
                if joined.endswith(";"):
                    cur.execute(joined)
                    buf = []
            leftover = "\n".join(buf).strip()
            if leftover:
                cur.execute(leftover)
        conn.commit()
        print("schema ok")
        with conn.cursor() as cur:
            cur.execute(
                "SELECT slug, provider, provider_station_id, latitude, longitude FROM weather_stations ORDER BY id"
            )
            for row in cur.fetchall():
                print("station", dict(row))
    finally:
        conn.close()
    n = import_windguru_sqlite()
    print("windguru_forecasts_imported", n)


if __name__ == "__main__":
    main()
