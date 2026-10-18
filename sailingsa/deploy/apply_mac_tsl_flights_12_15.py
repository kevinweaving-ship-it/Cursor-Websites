#!/usr/bin/env python3
"""Write officials' TSL scoresheet races 12–15 onto the MAC TSL WC Event URL.

Place grid from the 17/18 Oct 2026 sheet. Does not touch flights 1–11 or
the audited F3 MATIES / F4 MAC +1 score_adjust rows.

  export DB_URL=postgresql://sailors_user:...@localhost:5432/sailors_master
  python3 sailingsa/deploy/apply_mac_tsl_flights_12_15.py --dry-run
  python3 sailingsa/deploy/apply_mac_tsl_flights_12_15.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

from sailingsa.backend.tsl_team_racing import (
    apply_official_flights_12_15,
    save_official_flights_12_15,
)

RID = "2026-10-17-mac-tsl-wc-team-sailing"


def get_db_url() -> str:
    url = (os.getenv("DATABASE_URL") or os.getenv("DB_URL") or "").strip()
    if not url:
        print("ERROR: DATABASE_URL or DB_URL not set.", file=sys.stderr)
        sys.exit(1)
    return url


def _summarize(sheet: dict) -> None:
    for fl in ("12", "13", "14", "15"):
        cells = [sheet[fl][str(b)] for b in range(1, 7)]
        blue = sum(int(c["rank"]) for c in cells[:3])
        green = sum(int(c["rank"]) for c in cells[3:])
        print(
            f"F{fl} blue t{cells[0]['team_id']} {blue}  green t{cells[3]['team_id']} {green}  "
            f"ranks {[c['rank'] for c in cells]}"
        )
    print("score_adjust", json.dumps(sheet.get("score_adjust") or {}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if psycopg2 is None:
        print("ERROR: psycopg2 required", file=sys.stderr)
        return 2

    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            "SELECT flight_sheet FROM tsl_event_settings WHERE regatta_id = %s",
            (RID,),
        )
        row = cur.fetchone() or {}
        current = row.get("flight_sheet") or {}
        planned = apply_official_flights_12_15(current)
        _summarize(planned)
        if args.dry_run:
            print("dry-run: no write")
            conn.rollback()
            return 0
        save_official_flights_12_15(cur, RID, actor="officials_scoresheet_12_15")
        conn.commit()
        print("wrote F12-F15")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
