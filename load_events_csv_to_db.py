#!/usr/bin/env python3
"""
Load sas_events_list.csv into the events table (upsert on source + source_event_id).
Run after: (1) migration 145 + 146, (2) scrape_sas_events_list.py [--no-detail] producing sas_events_list.csv.
Usage: python3 load_events_csv_to_db.py [--csv PATH] [--dry-run]
Env: DATABASE_URL or DB_URL.

Provenance (single chain architecture):
- If scrape_metadata.json exists alongside CSV:
  - Uses scrape_artifact_id as primary evidence (SAS Website → Scrape Run → Events)
  - Does NOT create separate CSV artifact (CSV is output of scrape, not separate source)
- If no scrape_metadata.json (manual run):
  - Creates CSV artifact as fallback
- Each row's source_url = original event artifact (never overwritten)
- Source type inferred from URL using shared _infer_source_type_from_url()
- Authority levels based on source type (calendar data < official results)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from hashlib import md5
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None

# Import provenance helpers from shared module
try:
    from results_ingestion_common import (
        create_source_artifact,
        _infer_source_type_from_url,
        AUTHORITY_LEVELS,
    )
    HAS_PROVENANCE = True
except ImportError:
    HAS_PROVENANCE = False
    create_source_artifact = None
    _infer_source_type_from_url = None
    AUTHORITY_LEVELS = {}


# Calendar/event metadata has lower authority than official results
CALENDAR_AUTHORITY_REDUCTION = 20


def get_db_url() -> str | None:
    return os.getenv("DATABASE_URL") or os.getenv("DB_URL")


def _compute_csv_checksum(path: Path) -> str | None:
    """Compute MD5 checksum of CSV file for artifact tracking."""
    try:
        hasher = md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None


def _check_provenance_tables_exist(cur) -> bool:
    """Check if provenance tables exist (graceful degradation)."""
    try:
        cur.execute("""
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'source_artifacts' 
            AND table_schema = 'public'
        """)
        return cur.fetchone() is not None
    except Exception:
        return False


def _check_events_provenance_columns(cur) -> bool:
    """Check if events table has provenance columns."""
    try:
        cur.execute("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'events' 
            AND column_name = 'artifact_id'
            AND table_schema = 'public'
        """)
        return cur.fetchone() is not None
    except Exception:
        return False


def _load_scrape_metadata(csv_path: Path) -> dict | None:
    """
    Load scrape_metadata.json if it exists alongside the CSV.
    
    Returns metadata dict or None if not found.
    """
    # Look for scrape_metadata.json in same directory as CSV
    metadata_path = csv_path.parent / "scrape_metadata.json"
    if not metadata_path.exists():
        return None
    
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        # Validate that it has the expected structure
        if "scrape_artifact_id" in metadata or "csv_checksum_md5" in metadata:
            return metadata
        return None
    except Exception as e:
        print(f"[provenance] Failed to load scrape_metadata.json: {e}", file=sys.stderr)
        return None


def _create_csv_import_artifact(conn, csv_path: Path, scrape_run_id: str) -> int | None:
    """
    Create artifact for the CSV file itself (fallback when no scrape metadata).
    
    Only called when scrape_metadata.json doesn't exist (manual CSV load).
    Returns artifact_id or None if provenance not available.
    """
    if not HAS_PROVENANCE or not create_source_artifact:
        return None
    
    checksum = _compute_csv_checksum(csv_path)
    
    # CSV imports are internal transfers, lower authority than original sources
    return create_source_artifact(
        conn=conn,
        source_url=None,  # Local file, no URL
        source_type="external_scrape",  # CSV is an import mechanism, not original source
        import_method="csv_import",
        authority_level=30,  # Low authority - just a transfer format
        raw_file_path=str(csv_path.resolve()),
        checksum_md5=checksum,
        captured_by=f"load_events_csv_to_db:{scrape_run_id}",
        parse_notes=f"CSV import (manual, no scrape metadata): {csv_path.name}, run {scrape_run_id}",
    )


def _create_event_source_artifact(conn, source_url: str, source: str) -> int | None:
    """
    Create artifact for an event's source_url (original source).
    
    Uses URL inference to determine source type.
    Calendar metadata has reduced authority vs. results.
    
    Returns artifact_id or None.
    """
    if not HAS_PROVENANCE or not create_source_artifact or not _infer_source_type_from_url:
        return None
    
    if not source_url or len(source_url.strip()) <= 10:
        return None
    
    # Infer source type from URL
    source_type = _infer_source_type_from_url(source_url)
    
    # Calendar/event pages have reduced authority compared to results
    # (this is metadata about events, not official results)
    base_authority = AUTHORITY_LEVELS.get(source_type, AUTHORITY_LEVELS.get("unknown", 10))
    authority = max(10, base_authority - CALENDAR_AUTHORITY_REDUCTION)
    
    return create_source_artifact(
        conn=conn,
        source_url=source_url,
        source_type=source_type,
        import_method="scrape_auto",
        authority_level=authority,
        raw_file_path=None,  # URL source, no local file
        checksum_md5=None,
        captured_by="load_events_csv_to_db",
        parse_notes=f"Event calendar source from {source}",
    )


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
            # Check if provenance tables and columns exist
            has_provenance_tables = _check_provenance_tables_exist(cur)
            has_provenance_columns = _check_events_provenance_columns(cur)
            use_provenance = HAS_PROVENANCE and has_provenance_tables and has_provenance_columns
            
            if use_provenance:
                print(f"Provenance enabled: tracking artifacts", file=sys.stderr)
            else:
                if not HAS_PROVENANCE:
                    print(f"Provenance disabled: results_ingestion_common not available", file=sys.stderr)
                elif not has_provenance_tables:
                    print(f"Provenance disabled: source_artifacts table not found", file=sys.stderr)
                elif not has_provenance_columns:
                    print(f"Provenance disabled: events.artifact_id column not found", file=sys.stderr)
            
            # Provenance: check for scrape_metadata.json (single chain architecture)
            # If scrape ran first, it created the artifact; we use that instead of creating CSV artifact
            scrape_metadata = _load_scrape_metadata(csv_path)
            scrape_artifact_id = None
            csv_artifact_id = None
            
            if use_provenance:
                if scrape_metadata and scrape_metadata.get("scrape_artifact_id"):
                    # Use scrape artifact (single provenance chain)
                    scrape_artifact_id = scrape_metadata["scrape_artifact_id"]
                    print(f"  Using scrape artifact: {scrape_artifact_id} (from scrape_metadata.json)", file=sys.stderr)
                    
                    # Verify CSV checksum matches if available
                    expected_checksum = scrape_metadata.get("csv_checksum_md5")
                    if expected_checksum:
                        actual_checksum = _compute_csv_checksum(csv_path)
                        if actual_checksum == expected_checksum:
                            print(f"  CSV checksum verified: {actual_checksum[:16]}...", file=sys.stderr)
                        else:
                            print(f"  WARNING: CSV checksum mismatch! Expected {expected_checksum[:16]}..., got {actual_checksum[:16] if actual_checksum else 'None'}...", file=sys.stderr)
                else:
                    # Fallback: create CSV artifact (manual load without scrape)
                    csv_artifact_id = _create_csv_import_artifact(conn, csv_path, scrape_run_id)
                    if csv_artifact_id:
                        print(f"  CSV artifact created (fallback): {csv_artifact_id}", file=sys.stderr)
            
            # The import artifact is scrape_artifact_id if from scrape, else csv_artifact_id
            import_artifact_id = scrape_artifact_id or csv_artifact_id
            
            # Track statistics
            stats = {"inserted": 0, "updated": 0, "artifacts_created": 0, "artifacts_reused": 0}
            
            for r in rows:
                # Create artifact for source_url (original source) if provenance enabled
                event_artifact_id = None
                if use_provenance and r["source_url"]:
                    # Check if artifact already exists for this URL
                    cur.execute(
                        "SELECT artifact_id FROM source_artifacts WHERE source_url = %s LIMIT 1",
                        (r["source_url"],)
                    )
                    existing = cur.fetchone()
                    if existing:
                        event_artifact_id = existing[0]
                        stats["artifacts_reused"] += 1
                    else:
                        event_artifact_id = _create_event_source_artifact(conn, r["source_url"], r["source"])
                        if event_artifact_id:
                            stats["artifacts_created"] += 1
                
                # Build provenance status JSON
                provenance_status = None
                if use_provenance:
                    provenance_status = json.dumps({
                        "status": "scrape_import" if scrape_artifact_id else "csv_import",
                        "import_artifact_id": import_artifact_id,
                        "scrape_artifact_id": scrape_artifact_id,  # None if manual CSV load
                        "scrape_run_id": scrape_run_id,
                        "imported_at": datetime.utcnow().isoformat(),
                    })
                
                if use_provenance:
                    # UPSERT with provenance columns
                    # Key principle: NEVER overwrite original artifact_id
                    cur.execute("""
                        INSERT INTO events (
                            source, source_event_id, source_url,
                            event_name, start_date, end_date, event_year,
                            venue_raw, host_club_name_raw, location_raw, address,
                            nor_url, si_url, results_url, other_docs,
                            category, description, contact, organiser,
                            event_status, last_seen_at, scrape_run_id,
                            artifact_id, provenance_status
                        ) VALUES (
                            %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, now(), %s,
                            %s, %s
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
                            scrape_run_id = EXCLUDED.scrape_run_id,
                            -- NEVER overwrite original artifact_id (COALESCE preserves existing)
                            artifact_id = COALESCE(events.artifact_id, EXCLUDED.artifact_id),
                            -- Update provenance_status to track latest import
                            provenance_status = EXCLUDED.provenance_status
                        RETURNING (xmax = 0) AS inserted
                    """, (
                        r["source"], r["source_event_id"], r["source_url"],
                        r["event_name"], r["start_date"], r["end_date"], r["event_year"],
                        r["venue_raw"], r["host_club_name_raw"], r["location_raw"], r["address"],
                        r["nor_url"], r["si_url"], r["results_url"], r["other_docs"],
                        r["category"], r["description"], r["contact"], r["organiser"],
                        r["event_status"], scrape_run_id,
                        event_artifact_id, provenance_status,
                    ))
                    result = cur.fetchone()
                    if result and result[0]:
                        stats["inserted"] += 1
                    else:
                        stats["updated"] += 1
                else:
                    # Legacy UPSERT without provenance columns
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
        
        # Print summary
        if use_provenance:
            print(f"Upserted {len(rows)} events (scrape_run_id={scrape_run_id})", file=sys.stderr)
            print(f"  Inserted: {stats['inserted']}, Updated: {stats['updated']}", file=sys.stderr)
            print(f"  Artifacts: {stats['artifacts_created']} created, {stats['artifacts_reused']} reused", file=sys.stderr)
        else:
            print(f"Upserted {len(rows)} events (scrape_run_id={scrape_run_id})", file=sys.stderr)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
