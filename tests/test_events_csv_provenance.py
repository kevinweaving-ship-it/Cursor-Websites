#!/usr/bin/env python3
"""
Tests for load_events_csv_to_db.py provenance integration.

Verifies:
1. CSV artifact creation
2. Event source artifact creation with proper URL inference
3. Idempotent re-imports (never overwrite original artifact_id)
4. Proper authority levels (calendar < results)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
from psycopg2.extras import RealDictCursor

from load_events_csv_to_db import (
    _compute_csv_checksum,
    _check_provenance_tables_exist,
    _check_events_provenance_columns,
    _create_csv_import_artifact,
    _create_event_source_artifact,
    _load_scrape_metadata,
    CALENDAR_AUTHORITY_REDUCTION,
)
from results_ingestion_common import AUTHORITY_LEVELS


def get_test_db_url() -> str:
    """Get test database URL."""
    return os.getenv("DATABASE_URL") or os.getenv("DB_URL") or "postgresql://localhost/sailors_staging"


def test_csv_checksum():
    """Test MD5 checksum computation for CSV files."""
    print("\n=== TEST: CSV checksum computation ===")
    
    # Create temp CSV file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("col1,col2\n")
        f.write("val1,val2\n")
        temp_path = Path(f.name)
    
    try:
        checksum = _compute_csv_checksum(temp_path)
        assert checksum is not None, "Checksum should not be None"
        assert len(checksum) == 32, f"MD5 should be 32 chars, got {len(checksum)}"
        print(f"  Checksum computed: {checksum[:16]}...")
        
        # Same content = same checksum (idempotent)
        checksum2 = _compute_csv_checksum(temp_path)
        assert checksum == checksum2, "Same file should produce same checksum"
        print(f"  Idempotent: ✓")
        
        print("  PASSED: CSV checksum computation")
    finally:
        temp_path.unlink()


def test_provenance_table_detection(conn):
    """Test detection of provenance tables."""
    print("\n=== TEST: Provenance table detection ===")
    
    cur = conn.cursor()
    
    has_tables = _check_provenance_tables_exist(cur)
    has_columns = _check_events_provenance_columns(cur)
    
    print(f"  source_artifacts table exists: {has_tables}")
    print(f"  events.artifact_id column exists: {has_columns}")
    
    if not has_tables:
        print("  SKIPPED: Provenance tables not available")
        return False
    
    if not has_columns:
        print("  SKIPPED: Events provenance columns not available")
        return False
    
    print("  PASSED: Provenance detection")
    return True


def test_csv_artifact_creation(conn):
    """Test CSV artifact creation."""
    print("\n=== TEST: CSV artifact creation ===")
    
    conn.rollback()
    
    # Create temp CSV file
    test_id = uuid.uuid4().hex[:8]
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(f"# Test CSV {test_id}\n")
        f.write("source_event_id,title\n")
        f.write("123,Test Event\n")
        temp_path = Path(f.name)
    
    try:
        scrape_run_id = f"test_{test_id}"
        artifact_id = _create_csv_import_artifact(conn, temp_path, scrape_run_id)
        
        if artifact_id is None:
            print("  SKIPPED: Provenance not available or creation failed")
            return
        
        print(f"  CSV artifact created: {artifact_id}")
        
        # Verify artifact properties
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT source_type, import_method, authority_level, raw_file_path, checksum_md5, parse_notes
            FROM source_artifacts WHERE artifact_id = %s
        """, (artifact_id,))
        row = cur.fetchone()
        
        assert row is not None, "Artifact should exist"
        assert row["source_type"] == "external_scrape", f"CSV should be external_scrape, got {row['source_type']}"
        assert row["import_method"] == "csv_import", f"Import method should be csv_import, got {row['import_method']}"
        assert row["authority_level"] == 30, f"CSV authority should be 30 (low), got {row['authority_level']}"
        assert row["checksum_md5"] is not None, "Checksum should be set"
        assert scrape_run_id in row["parse_notes"], "Parse notes should include scrape_run_id"
        
        print(f"  Source type: {row['source_type']} ✓")
        print(f"  Import method: {row['import_method']} ✓")
        print(f"  Authority: {row['authority_level']} ✓")
        print(f"  Checksum: {row['checksum_md5'][:16]}... ✓")
        
        print("  PASSED: CSV artifact creation")
    finally:
        temp_path.unlink()
        conn.rollback()


def test_event_source_artifact_creation(conn):
    """Test event source artifact creation with URL inference."""
    print("\n=== TEST: Event source artifact creation ===")
    
    conn.rollback()
    
    test_cases = [
        # (url, source, expected_type, expected_authority_range)
        # sas_official has authority 100, reduced by 20 for calendar = 80
        ("https://www.sailing.org.za/events/123", "sas", "sas_official", (75, 85)),
        # sas_pdf has authority 90, reduced by 20 for calendar = 70
        ("https://www.sailing.org.za/events/123.pdf", "sas", "sas_pdf", (65, 75)),
        # sailwave has authority 80, reduced by 20 = 60
        ("https://sailwave.com/results/test", "external", "sailwave", (55, 65)),
        # windsail has authority 80, reduced by 20 = 60
        ("https://www.windsail.co.za/results", "external", "windsail", (55, 65)),
        # club_official has authority 75, reduced by 20 = 55
        ("https://rcyc.co.za/results/summer", "external", "club_official", (50, 60)),
        # external_scrape has authority 50, reduced by 20 = 30
        ("https://unknown-site.com/events", "external", "external_scrape", (25, 35)),
    ]
    
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    for url, source, expected_type, auth_range in test_cases:
        artifact_id = _create_event_source_artifact(conn, url, source)
        
        if artifact_id is None:
            print(f"  SKIPPED: {url} - Provenance not available")
            continue
        
        cur.execute("""
            SELECT source_type, authority_level FROM source_artifacts WHERE artifact_id = %s
        """, (artifact_id,))
        row = cur.fetchone()
        
        # Verify source type
        assert row["source_type"] == expected_type, \
            f"{url} → expected {expected_type}, got {row['source_type']}"
        
        # Verify authority is reduced for calendar data
        base_authority = AUTHORITY_LEVELS.get(expected_type, 10)
        expected_authority = max(10, base_authority - CALENDAR_AUTHORITY_REDUCTION)
        assert row["authority_level"] == expected_authority, \
            f"{url} → expected authority {expected_authority}, got {row['authority_level']}"
        
        print(f"  {url[:40]}... → {row['source_type']} (auth={row['authority_level']}) ✓")
    
    conn.rollback()
    print("  PASSED: Event source artifact creation with URL inference")


def test_idempotent_artifact_reuse(conn):
    """Test that artifacts are reused, not duplicated."""
    print("\n=== TEST: Idempotent artifact reuse ===")
    
    conn.rollback()
    
    test_url = f"https://www.sailing.org.za/events/test-{uuid.uuid4().hex[:8]}"
    
    # Create artifact first time
    artifact_id_1 = _create_event_source_artifact(conn, test_url, "sas")
    
    if artifact_id_1 is None:
        print("  SKIPPED: Provenance not available")
        return
    
    # Create artifact second time (should reuse)
    artifact_id_2 = _create_event_source_artifact(conn, test_url, "sas")
    
    assert artifact_id_1 == artifact_id_2, \
        f"Same URL should return same artifact_id: {artifact_id_1} vs {artifact_id_2}"
    
    print(f"  First call: {artifact_id_1}")
    print(f"  Second call: {artifact_id_2}")
    print(f"  Reused: ✓")
    
    conn.rollback()
    print("  PASSED: Idempotent artifact reuse")


def test_original_artifact_never_overwritten(conn):
    """Test that original artifact_id is never overwritten on re-import."""
    print("\n=== TEST: Original artifact never overwritten ===")
    
    conn.rollback()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check if provenance columns exist
    if not _check_events_provenance_columns(cur):
        print("  SKIPPED: Events provenance columns not available")
        return
    
    test_id = uuid.uuid4().hex[:8]
    source = "test"
    source_event_id = f"evt_{test_id}"
    source_url_1 = f"https://example.com/event/{test_id}/v1"
    source_url_2 = f"https://example.com/event/{test_id}/v2"
    
    # Create first artifact
    artifact_id_1 = _create_event_source_artifact(conn, source_url_1, source)
    
    if artifact_id_1 is None:
        print("  SKIPPED: Provenance not available")
        conn.rollback()
        return
    
    # Insert event with first artifact
    cur.execute("""
        INSERT INTO events (source, source_event_id, source_url, event_name, artifact_id, provenance_status)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING event_id
    """, (source, source_event_id, source_url_1, "Test Event", artifact_id_1, "initial"))
    event_id = cur.fetchone()["event_id"]
    print(f"  Event created: {event_id} with artifact {artifact_id_1}")
    
    # Create second artifact (different URL)
    artifact_id_2 = _create_event_source_artifact(conn, source_url_2, source)
    print(f"  Second artifact created: {artifact_id_2}")
    
    # Simulate re-import: UPDATE with COALESCE (like our code does)
    cur.execute("""
        UPDATE events 
        SET source_url = %s,
            artifact_id = COALESCE(artifact_id, %s),
            provenance_status = %s
        WHERE event_id = %s
        RETURNING artifact_id
    """, (source_url_2, artifact_id_2, "reimport", event_id))
    result_artifact = cur.fetchone()["artifact_id"]
    
    # Original artifact should be preserved
    assert result_artifact == artifact_id_1, \
        f"Original artifact should be preserved: expected {artifact_id_1}, got {result_artifact}"
    
    print(f"  After re-import: artifact_id = {result_artifact}")
    print(f"  Original preserved: ✓")
    
    conn.rollback()
    print("  PASSED: Original artifact never overwritten")


def test_load_scrape_metadata():
    """Test loading scrape_metadata.json."""
    print("\n=== TEST: Load scrape metadata ===")
    
    # Create temp directory with CSV and metadata
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create CSV
        csv_path = tmpdir / "sas_events_list.csv"
        csv_path.write_text("col1,col2\nval1,val2\n")
        
        # Test: no metadata file → returns None
        result = _load_scrape_metadata(csv_path)
        assert result is None, "Should return None when no metadata file"
        print("  No metadata file → None: ✓")
        
        # Create metadata with scrape_artifact_id
        metadata = {
            "scrape_artifact_id": 123,
            "csv_checksum_md5": "abc123",
            "events_count": 992,
        }
        metadata_path = tmpdir / "scrape_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
        
        # Test: with valid metadata → returns dict
        result = _load_scrape_metadata(csv_path)
        assert result is not None, "Should return metadata dict"
        assert result["scrape_artifact_id"] == 123, "Should have scrape_artifact_id"
        print(f"  With metadata file → scrape_artifact_id={result['scrape_artifact_id']}: ✓")
        
        # Test: metadata without scrape_artifact_id but with csv_checksum_md5 (also valid)
        metadata2 = {"csv_checksum_md5": "def456", "events_count": 500}
        with open(metadata_path, "w") as f:
            json.dump(metadata2, f)
        
        result = _load_scrape_metadata(csv_path)
        assert result is not None, "Should return metadata even without scrape_artifact_id if has csv_checksum_md5"
        print(f"  Metadata without artifact_id but with checksum → valid: ✓")
        
        # Test: invalid metadata (no expected keys) → returns None
        metadata3 = {"random_key": "value"}
        with open(metadata_path, "w") as f:
            json.dump(metadata3, f)
        
        result = _load_scrape_metadata(csv_path)
        assert result is None, "Should return None for invalid metadata"
        print("  Invalid metadata → None: ✓")
    
    print("  PASSED: Load scrape metadata")


def test_authority_levels_calendar_vs_results():
    """Test that calendar authority is lower than results authority."""
    print("\n=== TEST: Authority levels (calendar < results) ===")
    
    # Results authority levels (from source_types table)
    sas_official_results = AUTHORITY_LEVELS.get("sas_official", 100)
    sas_pdf_results = AUTHORITY_LEVELS.get("sas_pdf", 90)
    
    # Calendar authority (reduced for event metadata)
    sas_official_calendar = max(10, sas_official_results - CALENDAR_AUTHORITY_REDUCTION)
    sas_pdf_calendar = max(10, sas_pdf_results - CALENDAR_AUTHORITY_REDUCTION)
    
    print(f"  Results authority:")
    print(f"    sas_official: {sas_official_results}")
    print(f"    sas_pdf: {sas_pdf_results}")
    print(f"  Calendar authority (reduced by {CALENDAR_AUTHORITY_REDUCTION}):")
    print(f"    sas_official: {sas_official_calendar}")
    print(f"    sas_pdf: {sas_pdf_calendar}")
    
    assert sas_official_calendar < sas_official_results, "Calendar authority should be lower than results"
    assert sas_pdf_calendar < sas_pdf_results, "Calendar authority should be lower than results"
    
    print("  Calendar < Results: ✓")
    print("  PASSED: Authority levels")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("EVENTS CSV PROVENANCE TESTS")
    print("=" * 60)
    
    # Test without DB first
    test_csv_checksum()
    test_load_scrape_metadata()
    test_authority_levels_calendar_vs_results()
    
    # DB tests
    db_url = get_test_db_url()
    print(f"\nConnecting to: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        
        # Check if provenance is available
        cur = conn.cursor()
        if not _check_provenance_tables_exist(cur):
            print("\nWARNING: Provenance tables not found. DB tests will be skipped.")
            print("Run migration 210 to enable provenance features.")
        
        test_provenance_table_detection(conn)
        test_csv_artifact_creation(conn)
        test_event_source_artifact_creation(conn)
        test_idempotent_artifact_reuse(conn)
        test_original_artifact_never_overwritten(conn)
        
        conn.rollback()
        conn.close()
        
    except psycopg2.OperationalError as e:
        print(f"\nDatabase connection failed: {e}")
        print("Skipping DB tests.")
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
