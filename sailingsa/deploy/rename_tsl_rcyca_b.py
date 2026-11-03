#!/usr/bin/env python3
"""Rename TSL team 17 from RCYC Sailing Academy to RCYCA B / RCYC Sailing Academy B.

  export DB_URL=...
  python3 sailingsa/deploy/rename_tsl_rcyca_b.py --dry-run
  python3 sailingsa/deploy/rename_tsl_rcyca_b.py
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

REGATTA_ID = "2026-10-17-mac-tsl-wc-team-sailing"
TEAM_ID = 17
OLD_NAME = "RCYC Sailing Academy"
NEW_NAME = "RCYC Sailing Academy B"
NEW_ABBREV = "RCYCA B"


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
            """
            SELECT team_id, team_name, team_abbrev, result_id
            FROM tsl_event_teams
            WHERE team_id = %s AND regatta_id = %s
            """,
            (TEAM_ID, REGATTA_ID),
        )
        team = cur.fetchone()
        if not team:
            print(f"ERROR: team_id={TEAM_ID} missing on {REGATTA_ID}", file=sys.stderr)
            return 1
        print(
            f"team {team['team_id']} name={team['team_name']!r} "
            f"abbrev={team['team_abbrev']!r} result_id={team['result_id']}"
        )
        already = (
            team["team_name"] == NEW_NAME and (team["team_abbrev"] or "") == NEW_ABBREV
        )
        if already:
            print("already renamed")
        elif team["team_name"] not in (OLD_NAME, NEW_NAME):
            print(f"ERROR: unexpected team_name {team['team_name']!r}", file=sys.stderr)
            return 1
        elif args.dry_run:
            print(f"dry-run: would set team_name={NEW_NAME!r} team_abbrev={NEW_ABBREV!r}")
        else:
            cur.execute(
                """
                UPDATE tsl_event_teams
                   SET team_name = %s, team_abbrev = %s
                 WHERE team_id = %s AND regatta_id = %s
                """,
                (NEW_NAME, NEW_ABBREV, TEAM_ID, REGATTA_ID),
            )
            if team["result_id"]:
                cur.execute(
                    """
                    UPDATE results
                       SET boat_name = %s
                     WHERE result_id = %s AND regatta_id = %s
                    """,
                    (NEW_NAME, int(team["result_id"]), REGATTA_ID),
                )
            conn.commit()
            print(f"OK renamed team_id={TEAM_ID} to {NEW_ABBREV} · {NEW_NAME}")
        return 0
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
