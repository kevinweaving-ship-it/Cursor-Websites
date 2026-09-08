#!/usr/bin/env python3
"""Upsert ZVYC Cape Classic 12–13 Sep 2026 into public.events.

SAS has not listed this edition yet; the event is real (club Revolutionise
entry + KYC calendar). Daily SAS scrape only upserts SAS list rows, so this
revolutionise/375411 row is not deleted by the scrape.

Usage:
  python3 sailingsa/deploy/add_zvyc_cape_classic_2026_event.py [--dry-run]
  bash sailingsa/deploy/add_zvyc_cape_classic_2026_event.sh --on-server

Env: DATABASE_URL or DB_URL.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, time

# Club listing (canonical): https://www.revolutionise.com.au/zeekoevleiyc/events/375411
# Calendar corroboration: KYC list — 12 Sep 08:00 – 13 Sep 17:00
EVENT = {
    "source": "revolutionise",
    "source_event_id": "375411",
    "source_url": "https://www.revolutionise.com.au/zeekoevleiyc/events/375411",
    "event_name": "ZVYC Cape Classic",
    "start_date": date(2026, 9, 12),
    "end_date": date(2026, 9, 13),
    "event_year": 2026,
    "start_time": time(8, 0),
    "end_time": time(17, 0),
    "venue_raw": "Zeekoe Vlei Yacht Club",
    "host_club_name_raw": "Zeekoe Vlei Yacht Club",
    "location_raw": "Governors Walk, Zeekoevlei, Cape Town",
    "address": "8 Governors Walk, Grassy Park, Western Cape",
    "category": "Dinghy Event",
    "event_status": "upcoming",
    "organiser": "Zeekoe Vlei Yacht Club",
    "contact": "+27 21 705 3373",
    "province_code": "WC",
    "description": (
        "ZVYC Cape Classic, 12–13 September 2026. "
        "SAS calendar listing pending; added from club Revolutionise event 375411 "
        "and KYC calendar (Sat 08:00 – Sun 17:00). "
        "Registration Sat 11:00–12:30; first start 14:00; prize-giving Sun 16:00. "
        "Entry: https://www.revolutionise.com.au/zeekoevleiyc/events/375411"
    ),
}


def get_db_url() -> str | None:
    return os.getenv("DATABASE_URL") or os.getenv("DB_URL")


def table_columns(cur, table: str) -> set[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,),
    )
    return {r[0] for r in cur.fetchall()}


def resolve_zvyc_club_id(cur) -> int:
    cur.execute(
        """
        SELECT club_id, club_abbrev, club_fullname
        FROM clubs
        WHERE lower(trim(club_abbrev)) = 'zvyc'
        ORDER BY club_id
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit("ERROR: clubs row for ZVYC not found")
    return int(row[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Upsert 2026 ZVYC Cape Classic into events.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned row; do not write")
    parser.add_argument("--on-server", action="store_true", help="Ignored here; used by the shell wrapper")
    args = parser.parse_args()

    print("ZVYC Cape Classic 2026-09-12/13  source=revolutionise/375411", file=sys.stderr)
    print(f"  name={EVENT['event_name']!r}  times={EVENT['start_time']}-{EVENT['end_time']}", file=sys.stderr)

    if args.dry_run:
        print("Dry run: not writing to DB.", file=sys.stderr)
        return 0

    try:
        import psycopg2  # noqa: WPS433 — optional unless writing
    except ImportError:
        print("ERROR: psycopg2 required. pip install psycopg2-binary", file=sys.stderr)
        return 1

    db_url = get_db_url()
    if not db_url:
        print("ERROR: DATABASE_URL or DB_URL not set.", file=sys.stderr)
        return 1

    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            cols = table_columns(cur, "events")
            need = {"source", "source_event_id", "event_name", "start_date", "end_date"}
            missing = need - cols
            if missing:
                print(f"ERROR: events table missing columns: {sorted(missing)}", file=sys.stderr)
                return 1

            club_id = resolve_zvyc_club_id(cur) if "host_club_id" in cols else None
            scrape_run_id = datetime.utcnow().strftime("%Y%m%d%H%M")

            row = dict(EVENT)
            if club_id is not None:
                row["host_club_id"] = club_id
            if "last_seen_at" in cols:
                row["last_seen_at"] = datetime.utcnow()
            if "scrape_run_id" in cols:
                row["scrape_run_id"] = scrape_run_id
            if "match_method" in cols:
                row["match_method"] = "manual"

            insert_cols = [c for c in row if c in cols]
            insert_sql = (
                "INSERT INTO events ("
                + ", ".join(insert_cols)
                + ") VALUES ("
                + ", ".join(["%s"] * len(insert_cols))
                + ") ON CONFLICT (source, source_event_id) DO UPDATE SET "
                + ", ".join(f"{c} = EXCLUDED.{c}" for c in insert_cols if c not in ("source", "source_event_id"))
            )
            cur.execute(insert_sql, tuple(row[c] for c in insert_cols))

            cur.execute(
                """
                SELECT event_id, event_name, start_date, end_date, event_status,
                       source, source_event_id, source_url, host_club_id, category
                FROM events
                WHERE source = %s AND source_event_id = %s
                """,
                (EVENT["source"], EVENT["source_event_id"]),
            )
            saved = cur.fetchone()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    if not saved:
        print("ERROR: upsert did not return a row", file=sys.stderr)
        return 1
    print(
        "Upserted event_id={0} {1} {2}..{3} host_club_id={4} {5}/{6}".format(
            saved[0], saved[1], saved[2], saved[3], saved[8], saved[5], saved[6]
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
