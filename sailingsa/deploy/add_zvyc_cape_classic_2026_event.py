#!/usr/bin/env python3
"""Upsert ZVYC Cape Classic 12–13 Sep 2026 into events + parent regatta.

SAS has not listed this edition yet. Creates:
  events: revolutionise/375411
  regattas: 2026-09-13-zvyc-cape-classic  (parent page; no fleets/entries yet)

Live URL: https://sailingsa.co.za/regatta/2026-09-13-zvyc-cape-classic
Header logos (once the row exists on live):
  left  /artwork/Event Logo/Cape-Classic-Series.png
  right /artwork/Club Logo/ZVYC.png  (from host_club_id)

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
REGATTA_ID = "2026-09-13-zvyc-cape-classic"
REGATTA_EVENT_NAME = "2026-09-13 ZVYC Cape Classic"
CAPE_CLASSIC_LOGO = "/artwork/Event Logo/Cape-Classic-Series.png"

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
    "regatta_id": REGATTA_ID,
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


def resolve_zvyc_club(cur) -> tuple[int, str, str]:
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
    return int(row[0]), (row[1] or "ZVYC").strip(), (row[2] or "Zeekoe Vlei Yacht Club").strip()


def next_regatta_number(cur) -> int:
    cur.execute("SELECT COALESCE(MAX(regatta_number), 0) + 1 FROM regattas WHERE regatta_number IS NOT NULL")
    row = cur.fetchone()
    return int((row[0] if row else 1) or 1)


def upsert_parent_regatta(cur, club_id: int, club_abbrev: str, club_fullname: str) -> None:
    cols = table_columns(cur, "regattas")
    need = {"regatta_id", "event_name"}
    missing = need - cols
    if missing:
        raise SystemExit(f"ERROR: regattas table missing columns: {sorted(missing)}")

    cur.execute("SELECT 1 FROM results WHERE regatta_id = %s LIMIT 1", (REGATTA_ID,))
    has_results = cur.fetchone() is not None

    existing_number = None
    if "regatta_number" in cols:
        cur.execute("SELECT regatta_number FROM regattas WHERE regatta_id = %s", (REGATTA_ID,))
        er = cur.fetchone()
        if er and er[0] is not None:
            existing_number = int(er[0])

    row = {
        "regatta_id": REGATTA_ID,
        "event_name": REGATTA_EVENT_NAME,
        "year": 2026,
        "start_date": date(2026, 9, 12),
        "end_date": date(2026, 9, 13),
        "host_club_id": club_id,
        "host_club_code": club_abbrev,
        "host_club_name": club_fullname,
        "province_name": "WC",
        "import_status": "pending",
        "slug": REGATTA_ID,
        "event_logo_url": CAPE_CLASSIC_LOGO,
    }
    if "regatta_number" in cols:
        row["regatta_number"] = existing_number if existing_number is not None else next_regatta_number(cur)
    if "result_status" in cols and not has_results:
        row["result_status"] = "Provisional"

    insert_cols = [c for c in row if c in cols]
    update_cols = [c for c in insert_cols if c not in ("regatta_id", "regatta_number")]
    if has_results:
        update_cols = [c for c in update_cols if c != "result_status"]
    sql = (
        "INSERT INTO regattas ("
        + ", ".join(insert_cols)
        + ") VALUES ("
        + ", ".join(["%s"] * len(insert_cols))
        + ") ON CONFLICT (regatta_id) DO UPDATE SET "
        + ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    )
    cur.execute(sql, tuple(row[c] for c in insert_cols))
    print(f"Upserted parent regatta {REGATTA_ID}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Upsert 2026 ZVYC Cape Classic parent event + regatta.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned row; do not write")
    parser.add_argument("--on-server", action="store_true", help="Ignored here; used by the shell wrapper")
    args = parser.parse_args()

    print("ZVYC Cape Classic parent  source=revolutionise/375411", file=sys.stderr)
    print(f"  events name={EVENT['event_name']!r}  {EVENT['start_date']}..{EVENT['end_date']}", file=sys.stderr)
    print(f"  parent URL /regatta/{REGATTA_ID}", file=sys.stderr)
    print(f"  header left={CAPE_CLASSIC_LOGO}  right=ZVYC club logo", file=sys.stderr)

    if args.dry_run:
        print("Dry run: not writing to DB.", file=sys.stderr)
        return 0

    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 required. pip install psycopg2-binary", file=sys.stderr)
        return 1

    db_url = get_db_url()
    if not db_url:
        print("ERROR: DATABASE_URL or DB_URL not set.", file=sys.stderr)
        return 1

    conn = psycopg2.connect(db_url)
    saved = None
    try:
        with conn.cursor() as cur:
            cols = table_columns(cur, "events")
            need = {"source", "source_event_id", "event_name", "start_date", "end_date"}
            missing = need - cols
            if missing:
                print(f"ERROR: events table missing columns: {sorted(missing)}", file=sys.stderr)
                return 1

            club_id, club_abbrev, club_fullname = resolve_zvyc_club(cur)
            upsert_parent_regatta(cur, club_id, club_abbrev, club_fullname)

            scrape_run_id = datetime.utcnow().strftime("%Y%m%d%H%M")
            row = dict(EVENT)
            if "host_club_id" in cols:
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
        print("ERROR: events upsert did not return a row", file=sys.stderr)
        return 1
    print(
        "Upserted event_id={0} {1} {2}..{3} host_club_id={4} linked {5}".format(
            saved[0], saved[1], saved[2], saved[3], saved[8], REGATTA_ID
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
