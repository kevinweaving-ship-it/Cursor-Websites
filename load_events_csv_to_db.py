#!/usr/bin/env python3
"""
Load sas_events_list.csv into the events table (upsert on source + source_event_id).
Run after: (1) migration 145 + 146, (2) scrape_sas_events_list.py [--no-detail] producing sas_events_list.csv.
Usage: python3 load_events_csv_to_db.py [--csv PATH] [--dry-run]
Env: DATABASE_URL or DB_URL.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None


def get_db_url() -> str | None:
    return os.getenv("DATABASE_URL") or os.getenv("DB_URL")


def parse_date(s: str) -> tuple | None:
    """Return (date, year_int) or None. Accepts YYYY-MM-DD."""
    if not s or not s.strip():
        return None
    s = s.strip()[:10]
    try:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return (dt.date(), dt.year)
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser(description="Load sas_events_list.csv into events table.")
    parser.add_argument("--csv", type=str, default=None, help="Path to CSV (default: sas_events_list.csv in cwd)")
    parser.add_argument("--dry-run", action="store_true", help="Print row count and sample, do not write to DB")
    args = parser.parse_args()

    csv_path = Path(args.csv) if args.csv else Path("sas_events_list.csv")
    if not csv_path.is_file():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    if not psycopg2:
        print("ERROR: psycopg2 required. pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

    db_url = get_db_url()
    if not db_url and not args.dry_run:
        print("ERROR: DATABASE_URL or DB_URL not set.", file=sys.stderr)
        sys.exit(1)

    rows = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # source_event_id: sas_event_id or external_event_id
            eid = (row.get("sas_event_id") or "").strip() or (row.get("external_event_id") or "").strip()
            if not eid:
                continue
            source = "sas" if (row.get("sas_event_id") or "").strip() else (row.get("external_host") or "external").strip() or "external"
            is_past = (row.get("is_past") or "").strip().lower() == "true"
            event_status = "completed" if is_past else "upcoming"
            start_date, event_year = parse_date(row.get("start_date") or "") or (None, None)
            end_date, _ = parse_date(row.get("end_date") or "") or (None, None)
            rows.append({
                "source": source,
                "source_event_id": eid,
                "source_url": (row.get("details_url") or "").strip() or None,
                "event_name": (row.get("title") or "").strip() or "Untitled",
                "start_date": start_date,
                "end_date": end_date,
                "event_year": event_year,
                "venue_raw": (row.get("venue_text") or "").strip() or None,
                "host_club_name_raw": (row.get("host") or "").strip() or (row.get("venue_text") or "").strip() or None,
                "location_raw": (row.get("location") or "").strip() or None,
                "address": (row.get("address") or "").strip() or None,
                "nor_url": (row.get("nor_url") or "").strip() or None,
                "si_url": (row.get("si_url") or "").strip() or None,
                "results_url": (row.get("results_url") or "").strip() or None,
                "other_docs": (row.get("other_docs") or "").strip() or None,
                "category": (row.get("category") or "").strip() or None,
                "description": (row.get("description") or "").strip() or None,
                "contact": (row.get("contact") or "").strip() or None,
                "organiser": (row.get("organiser") or "").strip() or None,
                "event_status": event_status,
            })

    if not rows:
        print("No rows to load.", file=sys.stderr)
        return

    print(f"Loaded {len(rows)} rows from {csv_path}", file=sys.stderr)
    if args.dry_run:
        print("Dry run: not writing to DB.", file=sys.stderr)
        for i, r in enumerate(rows[:3]):
            print(f"  {i+1}. {r['source']}/{r['source_event_id']} {r['event_name'][:50]}", file=sys.stderr)
        return

    scrape_run_id = datetime.utcnow().strftime("%Y%m%d%H%M")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute("""
                    INSERT INTO events (
                        source, source_event_id, source_url,
                        event_name, start_date, end_date, event_year,
                        venue_raw, host_club_name_raw, location_raw, address,
                        nor_url, si_url, results_url, other_docs,
                        category, description, contact, organiser,
                        event_status, last_seen_at, scrape_run_id
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, now(), %s
                    )
                    ON CONFLICT (source, source_event_id) DO UPDATE SET
                        source_url = EXCLUDED.source_url,
                        event_name = EXCLUDED.event_name,
                        start_date = EXCLUDED.start_date,
                        end_date = EXCLUDED.end_date,
                        event_year = EXCLUDED.event_year,
                        venue_raw = EXCLUDED.venue_raw,
                        host_club_name_raw = EXCLUDED.host_club_name_raw,
                        location_raw = EXCLUDED.location_raw,
                        address = EXCLUDED.address,
                        nor_url = EXCLUDED.nor_url,
                        si_url = EXCLUDED.si_url,
                        results_url = EXCLUDED.results_url,
                        other_docs = EXCLUDED.other_docs,
                        category = EXCLUDED.category,
                        description = EXCLUDED.description,
                        contact = EXCLUDED.contact,
                        organiser = EXCLUDED.organiser,
                        event_status = EXCLUDED.event_status,
                        last_seen_at = now(),
                        scrape_run_id = EXCLUDED.scrape_run_id
                """, (
                    r["source"], r["source_event_id"], r["source_url"],
                    r["event_name"], r["start_date"], r["end_date"], r["event_year"],
                    r["venue_raw"], r["host_club_name_raw"], r["location_raw"], r["address"],
                    r["nor_url"], r["si_url"], r["results_url"], r["other_docs"],
                    r["category"], r["description"], r["contact"], r["organiser"],
                    r["event_status"], scrape_run_id,
                ))
        conn.commit()
        print(f"Upserted {len(rows)} events (scrape_run_id={scrape_run_id})", file=sys.stderr)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
