#!/usr/bin/env python3
"""Mark MAC TSL WC Event URL results Final (existing status mechanism).

Does not touch flight_sheet, rosters, or score_adjust.

  export DB_URL=postgresql://sailors_user:...@localhost:5432/sailors_master
  python3 sailingsa/deploy/apply_mac_tsl_final_status.py --dry-run
  python3 sailingsa/deploy/apply_mac_tsl_final_status.py
"""
from __future__ import annotations

import argparse
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

from sailingsa.backend.tsl_team_racing import stamp_tsl_final

RID = "2026-10-17-mac-tsl-wc-team-sailing"


def get_db_url() -> str:
    url = (os.getenv("DATABASE_URL") or os.getenv("DB_URL") or "").strip()
    if not url:
        print("ERROR: DATABASE_URL or DB_URL not set.", file=sys.stderr)
        sys.exit(1)
    return url


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
            "SELECT result_status, as_at_time FROM public.regattas WHERE regatta_id = %s",
            (RID,),
        )
        row = cur.fetchone() or {}
        print("before", dict(row))
        if args.dry_run:
            print("dry-run: no write")
            conn.rollback()
            return 0
        stamp_tsl_final(cur, RID)
        conn.commit()
        cur.execute(
            "SELECT result_status, as_at_time FROM public.regattas WHERE regatta_id = %s",
            (RID,),
        )
        print("after", dict(cur.fetchone() or {}))
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
