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
import re
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


def is_invalid_venue(s: str) -> bool:
    """Reject venue/host values that are HTML fragments. Do not store."""
    if not s or not isinstance(s, str):
        return True
    t = s.strip().lower()
    return "target=" in t or "href=" in t or "blank" in t


# Host normalization: single source of truth in sailingsa.utils.host_normalizer
try:
    from sailingsa.utils.host_normalizer import normalize_host_for_resolution, host_resolution_candidates
except ImportError:
    # Fallback when run from project root without sailingsa on path
    import sys
    from pathlib import Path
    _root = Path(__file__).resolve().parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from sailingsa.utils.host_normalizer import normalize_host_for_resolution, host_resolution_candidates


def get_or_create_unassigned_club_id(cur):
    """Virtual host for SAS events when no club matches. Same row as api._get_unassigned_club_id."""
    try:
        cur.execute(
            """
            SELECT club_id FROM clubs
            WHERE lower(trim(COALESCE(club_abbrev, ''))) = 'unassigned'
            LIMIT 1
            """
        )
        r = cur.fetchone()
        if r and r[0] is not None:
            return int(r[0])
        cur.execute(
            """
            INSERT INTO clubs (club_abbrev, club_fullname)
            VALUES ('Unassigned', 'Unassigned (SAS calendar)')
            RETURNING club_id
            """
        )
        r = cur.fetchone()
        return int(r[0]) if r and r[0] is not None else None
    except Exception:
        cur.execute(
            """
            SELECT club_id FROM clubs
            WHERE lower(trim(COALESCE(club_abbrev, ''))) = 'unassigned'
            LIMIT 1
            """
        )
        r = cur.fetchone()
        return int(r[0]) if r and r[0] is not None else None


def resolve_host_to_club_id(cur, host_val: str):
    """
    Return clubs.club_id when host_val matches one club. Uses exact match then
    fuzzy match so e.g. "Witbank Yacht Club" matches "Witbank Yacht And Aquatic Club"
    (same club — use existing validated code). Strips leading '>'. Rejects TBC/Unk/Teams.
    """
    if not host_val or not host_val.strip():
        return None
    h = host_val.strip().lstrip(">").strip()
    if not h or h.upper() in ("TBC", "UNK", "UNKNOWN", "TEAMS"):
        return None
    hl = h.lower()
    # Association/class is not a club (e.g. LASA, 29er Class Association) — don't resolve to club
    if "association" in hl or "associat" in hl or hl.strip().startswith("lasa ") or hl.strip() == "lasa" or "29er class" in hl or "laser associat" in hl:
        return None
    lookup_candidates = [c.lower().strip() for c in host_resolution_candidates(h)] or [hl]
    # 0) club_aliases (e.g. "Port Owen Yacht Club" -> POYC; "Witbank Yacht Club" -> WYAC)
    for candidate in lookup_candidates:
        try:
            cur.execute(
                "SELECT club_id FROM club_aliases WHERE lower(trim(alias)) = %s",
                (candidate,),
            )
            row = cur.fetchone()
            if row:
                return row[0]
        except Exception:
            pass
    # 1) Exact match on abbrev or fullname
    cur.execute(
        """
        SELECT club_id FROM clubs
        WHERE (club_fullname IS NOT NULL AND trim(lower(club_fullname)) = ANY(%s))
           OR (club_abbrev IS NOT NULL AND trim(lower(club_abbrev)) = ANY(%s))
        """,
        (lookup_candidates, lookup_candidates),
    )
    rows = cur.fetchall()
    if len(rows) == 1:
        return rows[0][0]
    if len(rows) > 1:
        return rows[0][0]
    # 2) Fuzzy: scraped name is subset of club name (e.g. "Witbank Yacht Club" -> "Witbank Yacht And Aquatic Club")
    #    All significant words in scraped must appear in club_fullname; return if exactly one club.
    words = [w for w in hl.replace(",", " ").replace("&", " ").split() if len(w) > 1 and w not in ("the", "and", "of")]
    if not words:
        return None
    like_conds = " AND ".join(["lower(trim(club_fullname)) LIKE %s" for _ in words])
    params = ["%" + w + "%" for w in words]
    cur.execute(
        f"""
        SELECT club_id FROM clubs
        WHERE club_fullname IS NOT NULL AND trim(club_fullname) != ''
          AND {like_conds}
        """,
        params,
    )
    rows = cur.fetchall()
    if len(rows) == 1:
        return rows[0][0]
    # 3) One-way contains: club fullname contains scraped string (e.g. "Witbank Yacht And Aquatic Club" contains "Witbank Yacht Club")
    cur.execute(
        """
        SELECT club_id FROM clubs
        WHERE club_fullname IS NOT NULL AND trim(club_fullname) != ''
          AND lower(trim(club_fullname)) LIKE %s
        """,
        ("%" + hl + "%",),
    )
    rows = cur.fetchall()
    if len(rows) == 1:
        return rows[0][0]
    # 4) Scraped contains club fullname (e.g. scraped "Witbank Yacht And Aquatic Club" vs DB "Witbank Yacht Club" — unlikely)
    cur.execute(
        """
        SELECT club_id FROM clubs
        WHERE club_fullname IS NOT NULL AND trim(club_fullname) != ''
          AND %s LIKE lower(trim(club_fullname))
        """,
        (hl,),
    )
    rows = cur.fetchall()
    if len(rows) == 1:
        return rows[0][0]
    return None


def resolve_club_from_event_name(cur, event_name: str):
    """
    If event_name contains exactly one club's club_abbrev or club_fullname (case-insensitive),
    return that club_id. Else return None. Prefer longest match when multiple match.
    """
    if not event_name or not event_name.strip():
        return None
    event_lower = event_name.strip().lower()
    cur.execute(
        """
        SELECT club_id, trim(lower(coalesce(club_abbrev, ''))) AS abbr, trim(lower(coalesce(club_fullname, ''))) AS fullname
        FROM clubs
        WHERE (club_abbrev IS NOT NULL AND trim(club_abbrev) != '')
           OR (club_fullname IS NOT NULL AND trim(club_fullname) != '')
        """
    )
    rows = cur.fetchall()
    candidates = []
    for (cid, abbr, fullname) in rows:
        if abbr and abbr in event_lower:
            candidates.append((cid, len(abbr)))
        if fullname and fullname in event_lower and (cid, len(fullname)) not in [(c[0], c[1]) for c in candidates]:
            candidates.append((cid, len(fullname)))
    if not candidates:
        return None
    # Prefer longest match; if same club matched multiple times take max length
    by_club = {}
    for cid, length in candidates:
        by_club[cid] = max(by_club.get(cid, 0), length)
    best = max(by_club.items(), key=lambda x: x[1])
    return best[0]


def main():
    parser = argparse.ArgumentParser(description="Load sas_events_list.csv into events table.")
    parser.add_argument("--csv", type=str, default=None, help="Path to CSV (default: sas_events_list.csv in cwd)")
    parser.add_argument("--dry-run", action="store_true", help="Print row count and sample, do not write to DB")
    parser.add_argument("--limit-upcoming", type=int, default=None, help="Only load N rows with start_date >= today, ordered by start_date")
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
            # Venue from detail location or list venue_text; reject HTML fragments (preserve for audit)
            venue_val = (row.get("location") or row.get("venue_text") or "").strip() or None
            if venue_val and is_invalid_venue(venue_val):
                venue_val = None
            # Host: single source order; normalize for resolution/display (association · • | club -> club only)
            raw_host_source = (
                row.get("host") or row.get("venue_text") or row.get("location") or row.get("venue") or ""
            ).strip() or ""
            if raw_host_source and is_invalid_venue(raw_host_source):
                raw_host_source = ""
            if not raw_host_source and venue_val:
                raw_host_source = venue_val
            normalized_host = normalize_host_for_resolution(raw_host_source) if raw_host_source else ""
            # Store normalized for display/resolution; keep venue_raw as-is for audit
            host_val = normalized_host if normalized_host else raw_host_source or None
            start_time_val = (row.get("start_time") or "").strip() or None
            end_time_val = (row.get("end_time") or "").strip() or None
            rows.append({
                "source": source,
                "source_event_id": eid,
                "source_url": (row.get("details_url") or "").strip() or None,
                "event_name": (row.get("title") or "").strip() or "Untitled",
                "start_date": start_date,
                "end_date": end_date,
                "start_time": start_time_val,
                "end_time": end_time_val,
                "event_year": event_year,
                "venue_raw": venue_val,
                "host_club_name_raw": host_val,
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

    today = datetime.utcnow().date()
    if args.limit_upcoming is not None:
        rows = [r for r in rows if r.get("start_date") and r["start_date"] >= today]
        rows.sort(key=lambda r: (r.get("start_date") or today, r.get("event_name") or ""))
        rows = rows[: args.limit_upcoming]
        print(f"Limited to {len(rows)} upcoming rows (start_date >= today, by start_date)", file=sys.stderr)

    print(f"Loaded {len(rows)} rows from {csv_path}", file=sys.stderr)
    if args.dry_run:
        print("Dry run: not writing to DB.", file=sys.stderr)
        for i, r in enumerate(rows[:3]):
            print(f"  {i+1}. {r['source']}/{r['source_event_id']} {r['event_name'][:50]}", file=sys.stderr)
        return

    scrape_run_id = datetime.utcnow().strftime("%Y%m%d%H%M")
    conn = psycopg2.connect(db_url)
    try:
        print(
            "SQL: INSERT INTO events (...) ON CONFLICT (source, source_event_id) DO UPDATE SET ... "
            "start_time = COALESCE(events.start_time, EXCLUDED.start_time), "
            "end_time = COALESCE(events.end_time, EXCLUDED.end_time). "
            "Existing rows with start_time already set are not overwritten.",
            file=sys.stderr,
        )
        resolved = 0
        with conn.cursor() as cur:
            for r in rows:
                # Club resolution: always use normalizer so association-prefixed raw is never used
                host_for_resolution = normalize_host_for_resolution(
                    r.get("host_club_name_raw") or r.get("venue_raw") or ""
                )
                club_id = resolve_host_to_club_id(cur, host_for_resolution) if host_for_resolution else None
                if club_id is None and r.get("event_name"):
                    club_id = resolve_club_from_event_name(cur, r["event_name"])
                if club_id is not None:
                    resolved += 1
                if club_id is None:
                    club_id = get_or_create_unassigned_club_id(cur)
                cur.execute("""
                    INSERT INTO events (
                        source, source_event_id, source_url,
                        event_name, start_date, end_date, start_time, end_time, event_year,
                        venue_raw, host_club_name_raw, host_club_id, location_raw, address,
                        nor_url, si_url, results_url, other_docs,
                        category, description, contact, organiser,
                        event_status, last_seen_at, scrape_run_id
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, now(), %s
                    )
                    ON CONFLICT (source, source_event_id) DO UPDATE SET
                        source_url = EXCLUDED.source_url,
                        event_name = EXCLUDED.event_name,
                        start_date = EXCLUDED.start_date,
                        end_date = EXCLUDED.end_date,
                        start_time = COALESCE(events.start_time, EXCLUDED.start_time),
                        end_time = COALESCE(events.end_time, EXCLUDED.end_time),
                        event_year = EXCLUDED.event_year,
                        venue_raw = EXCLUDED.venue_raw,
                        host_club_name_raw = EXCLUDED.host_club_name_raw,
                        host_club_id = EXCLUDED.host_club_id,
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
                    r["event_name"], r["start_date"], r["end_date"], r["start_time"], r["end_time"], r["event_year"],
                    r["venue_raw"], r["host_club_name_raw"], club_id, r["location_raw"], r["address"],
                    r["nor_url"], r["si_url"], r["results_url"], r["other_docs"],
                    r["category"], r["description"], r["contact"], r["organiser"],
                    r["event_status"], scrape_run_id,
                ))
        conn.commit()
        print(f"Upserted {len(rows)} events (scrape_run_id={scrape_run_id}), host_club_id resolved for {resolved}", file=sys.stderr)
        # Show upcoming rows: event_name, start_date, start_time, end_date, end_time, host_club_id
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT event_name, start_date, start_time, end_date, end_time, host_club_id
                FROM events
                WHERE start_date >= CURRENT_DATE
                ORDER BY start_date ASC NULLS LAST
                LIMIT 50
            """)
            show_rows = cur.fetchall()
            cur.close()
            print("\n--- Upcoming events (start_date >= today, limit 50) ---", file=sys.stderr)
            for r in show_rows:
                print(f"  {r[0][:50]:50} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]}", file=sys.stderr)
        except Exception as e:
            print(f"  (Could not SELECT: {e})", file=sys.stderr)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
