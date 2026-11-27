#!/usr/bin/env python3
"""TSL Event URL team-name pass: drop izivungu, keep RCYCA B, rename RCYCA A.

  export DB_URL=...
  python3 sailingsa/deploy/rename_tsl_rcyca_teams.py --dry-run
  python3 sailingsa/deploy/rename_tsl_rcyca_teams.py
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
IZIVUNGU_ID = 16
RCYCA_A_ID = 8
RCYCA_B_ID = 17
RCYCA_A_NAME = "RCYC Sailing Academy A"
RCYCA_A_ABBREV = "RCYCA A"
RCYCA_B_NAME = "RCYC Sailing Academy B"
RCYCA_B_ABBREV = "RCYCA B"


def get_db_url() -> str:
    url = (os.getenv("DATABASE_URL") or os.getenv("DB_URL") or "").strip()
    if not url:
        print("ERROR: DATABASE_URL or DB_URL not set.", file=sys.stderr)
        sys.exit(1)
    return url


def load_team(cur, team_id: int):
    cur.execute(
        """
        SELECT team_id, team_name, team_abbrev, result_id
        FROM tsl_event_teams
        WHERE team_id = %s AND regatta_id = %s
        """,
        (team_id, REGATTA_ID),
    )
    return cur.fetchone()


def rename_team(cur, team: dict, name: str, abbrev: str, *, dry_run: bool) -> None:
    tid = int(team["team_id"])
    already = team["team_name"] == name and (team["team_abbrev"] or "") == abbrev
    print(f"team {tid} {team['team_abbrev']!r} · {team['team_name']!r} -> {abbrev} · {name}")
    if already:
        print("  already named")
        return
    if dry_run:
        print("  dry-run")
        return
    cur.execute(
        """
        UPDATE tsl_event_teams
           SET team_name = %s, team_abbrev = %s
         WHERE team_id = %s AND regatta_id = %s
        """,
        (name, abbrev, tid, REGATTA_ID),
    )
    if team.get("result_id"):
        cur.execute(
            """
            UPDATE results
               SET boat_name = %s
             WHERE result_id = %s AND regatta_id = %s
            """,
            (name, int(team["result_id"]), REGATTA_ID),
        )
    print("  updated")


def remove_izivungu(cur, *, dry_run: bool) -> None:
    team = load_team(cur, IZIVUNGU_ID)
    if not team:
        print("izivungu already removed")
        return
    name = (team["team_name"] or "").strip()
    if name.lower() != "izivungu":
        raise SystemExit(f"ERROR: team_id={IZIVUNGU_ID} is {name!r}, not izivungu")
    cur.execute(
        """
        SELECT match_id FROM tsl_event_matches
        WHERE regatta_id = %s AND status = 'complete'
          AND (team_a_id = %s OR team_b_id = %s)
        LIMIT 1
        """,
        (REGATTA_ID, IZIVUNGU_ID, IZIVUNGU_ID),
    )
    if cur.fetchone():
        raise SystemExit("ERROR: izivungu has a completed match")
    print(f"remove izivungu team_id={IZIVUNGU_ID} result_id={team['result_id']}")
    if dry_run:
        print("  dry-run")
        return
    cur.execute(
        """
        DELETE FROM tsl_event_matches
        WHERE regatta_id = %s AND (team_a_id = %s OR team_b_id = %s)
          AND status <> 'complete'
        """,
        (REGATTA_ID, IZIVUNGU_ID, IZIVUNGU_ID),
    )
    cur.execute(
        "DELETE FROM tsl_event_teams WHERE team_id = %s AND regatta_id = %s",
        (IZIVUNGU_ID, REGATTA_ID),
    )
    if team.get("result_id"):
        cur.execute(
            "DELETE FROM results WHERE result_id = %s AND regatta_id = %s",
            (int(team["result_id"]), REGATTA_ID),
        )
    print("  deleted")


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
        remove_izivungu(cur, dry_run=args.dry_run)

        team_a = load_team(cur, RCYCA_A_ID)
        if not team_a:
            print(f"ERROR: team_id={RCYCA_A_ID} missing", file=sys.stderr)
            return 1
        rename_team(cur, team_a, RCYCA_A_NAME, RCYCA_A_ABBREV, dry_run=args.dry_run)

        team_b = load_team(cur, RCYCA_B_ID)
        if not team_b:
            print(f"ERROR: team_id={RCYCA_B_ID} missing", file=sys.stderr)
            return 1
        rename_team(cur, team_b, RCYCA_B_NAME, RCYCA_B_ABBREV, dry_run=args.dry_run)

        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()
        return 0
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
