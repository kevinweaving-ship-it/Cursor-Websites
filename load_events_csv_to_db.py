#!/usr/bin/env python3
"""
Load sas_events_list.csv into the events table (upsert on source + source_event_id).

Soft-match: before inserting a *new* SAS/external identity, look for exactly one
pending/manual (or SAS-awaiting club) row matching date + venue + class + normalised
title. If found, adopt/enrich that row in place (preserve manual provenance and curated
fields). Zero matches → insert as usual. Multiple matches → skip insert/merge and log
for review.

Run after: (1) migration 145 + 146, (2) scrape_sas_events_list.py [--no-detail]
producing sas_events_list.csv.
Usage: python3 load_events_csv_to_db.py [--csv PATH] [--dry-run]
Env: DATABASE_URL or DB_URL.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None


PENDING_MANUAL_SOURCES = ("manual", "pending", "pending_sas", "admin", "club")
DATE_WINDOW_DAYS = 2
TITLE_TOKEN_OVERLAP_MIN = 0.55

CLASS_HINTS = (
    "optimist", "oppi", "dabchick", "mirror", "sonnet", "hobie", "laser", "ilca",
    "420", "470", "29er", "49er", "finn", "snipe", "fireball", "gp14", "505",
    "contender", "tempo", "windsurfer", "foiling", "multihull", "keel", "dinghy",
    "catamaran", "yacht",
)

STOPWORDS = {
    "the", "a", "an", "and", "or", "at", "for", "in", "on", "of", "to", "by",
    "hosted", "results", "result", "regatta", "event", "championship", "championships",
    "nationals", "national", "sa", "south", "african", "africa", "open", "class",
}


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


def normalize_title(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s]", " ", (s or "").lower())
    s = re.sub(r"\b(19|20)\d{2}\b", " ", s)
    parts = [p for p in s.split() if p and p not in STOPWORDS and len(p) > 1]
    return " ".join(parts)


def title_overlap_ratio(a: str, b: str) -> float:
    ta = set(normalize_title(a).split())
    tb = set(normalize_title(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / float(max(len(ta), len(tb)))


def normalize_venue(s: str) -> str:
    """Normalise venue/host; prefer part after · • | (association · club)."""
    if not s:
        return ""
    s = s.strip().lstrip(">").strip()
    parts = re.split(r"[\u00b7\u2022|]", s)
    if len(parts) > 1 and (parts[-1] or "").strip():
        s = parts[-1].strip()
    s = re.sub(r"[^a-zA-Z0-9\s]", " ", s.lower())
    return " ".join(s.split())


def extract_class_tokens(category: str | None, class_layout: str | None, event_name: str) -> set[str]:
    out: set[str] = set()
    for raw in (category, class_layout):
        if not raw:
            continue
        for t in normalize_title(raw).split():
            if t and t != "unknown":
                out.add(t)
    name_l = (event_name or "").lower()
    for hint in CLASS_HINTS:
        if hint in name_l:
            out.add(hint)
    for m in re.findall(r"\b(\d{2,3}er|\d{2,3}|ilca\s*\d*)\b", name_l):
        out.add(re.sub(r"\s+", "", m))
    return out


def class_tokens_compatible(a: set[str], b: set[str]) -> bool:
    if not a or not b:
        return True
    return bool(a & b)


def venue_compatible(
    csv_venue: str | None,
    csv_host: str | None,
    csv_club_id: int | None,
    row_venue: str | None,
    row_host: str | None,
    row_club_id: int | None,
) -> bool:
    if csv_club_id is not None and row_club_id is not None:
        return int(csv_club_id) == int(row_club_id)
    nv_csv = normalize_venue(csv_host or "") or normalize_venue(csv_venue or "")
    nv_row = normalize_venue(row_host or "") or normalize_venue(row_venue or "")
    if not nv_csv or not nv_row:
        return False
    if nv_csv == nv_row:
        return True
    return nv_csv in nv_row or nv_row in nv_csv


def _extras_dict(extras) -> dict:
    if isinstance(extras, dict):
        return dict(extras)
    if isinstance(extras, str):
        try:
            return dict(json.loads(extras) or {})
        except Exception:
            return {}
    return {}


def is_pending_manual_candidate(row: dict) -> bool:
    src = (row.get("source") or "").strip().lower()
    if src in ("manual", "pending", "pending_sas", "admin"):
        return True
    sid = (row.get("source_event_id") or "").strip().lower()
    if sid.startswith(("manual:", "pending:", "pending_sas:")):
        return True
    if src != "club":
        return False
    extras = _extras_dict(row.get("extras"))
    if str(extras.get("awaiting_sas") or "").lower() in ("1", "true", "yes"):
        return True
    if str(extras.get("sas_sanctioned") or "").lower() in ("1", "true", "yes"):
        return True
    auth = str(extras.get("event_authority") or "").upper()
    return auth in ("SAS", "PENDING_SAS", "SAS_PENDING")


def resolve_host_to_club_id(cur, host_val: str) -> int | None:
    """Return clubs.club_id when host_val matches exactly one club. Strips leading '>'."""
    if not host_val or not host_val.strip():
        return None
    h = host_val.strip().lstrip(">").strip()
    if not h or h.upper() in ("TBC", "UNK", "UNKNOWN"):
        return None
    hl = h.lower()
    cur.execute(
        """
        SELECT club_id FROM clubs
        WHERE (club_fullname IS NOT NULL AND TRIM(lower(club_fullname)) = %s)
           OR (club_abbrev IS NOT NULL AND TRIM(lower(club_abbrev)) = %s)
        """,
        (hl, hl),
    )
    rows = cur.fetchall()
    if len(rows) == 1:
        return rows[0]["club_id"] if isinstance(rows[0], dict) else rows[0][0]
    cur.execute(
        """
        SELECT club_id FROM clubs
        WHERE club_fullname IS NOT NULL AND TRIM(club_fullname) != ''
          AND (lower(club_fullname) LIKE %s OR %s LIKE lower(club_fullname))
        """,
        ("%" + hl + "%", hl),
    )
    rows = cur.fetchall()
    if len(rows) == 1:
        return rows[0]["club_id"] if isinstance(rows[0], dict) else rows[0][0]
    return None


def fetch_pending_manual_rows(cur) -> list[dict]:
    placeholders = ",".join(["%s"] * len(PENDING_MANUAL_SOURCES))
    cur.execute(
        f"""
        SELECT event_id, source, source_event_id, source_url, event_name,
               start_date, end_date, venue_raw, host_club_name_raw, host_club_id,
               location_raw, category, class_layout, regatta_id, extras,
               match_score, match_method, provenance_status
        FROM events
        WHERE lower(source) IN ({placeholders})
           OR source_event_id ILIKE 'manual:%%'
           OR source_event_id ILIKE 'pending:%%'
           OR source_event_id ILIKE 'pending_sas:%%'
        """,
        tuple(PENDING_MANUAL_SOURCES),
    )
    out = []
    for r in cur.fetchall() or []:
        d = dict(r)
        if (d.get("source") or "").lower() == "club" and not is_pending_manual_candidate(d):
            continue
        if not is_pending_manual_candidate(d):
            # non-club sources in PENDING_MANUAL_SOURCES already qualify via source name
            if (d.get("source") or "").lower() not in ("manual", "pending", "pending_sas", "admin"):
                continue
        out.append(d)
    return out


def find_soft_matches(csv_row: dict, club_id: int | None, candidates: list[dict]) -> list[dict]:
    if not csv_row.get("start_date"):
        return []
    csv_classes = extract_class_tokens(csv_row.get("category"), None, csv_row.get("event_name") or "")
    matches = []
    for cand in candidates:
        if not cand.get("start_date"):
            continue
        delta = abs((cand["start_date"] - csv_row["start_date"]).days)
        if delta > DATE_WINDOW_DAYS:
            continue
        if not venue_compatible(
            csv_row.get("venue_raw"),
            csv_row.get("host_club_name_raw"),
            club_id,
            cand.get("venue_raw"),
            cand.get("host_club_name_raw"),
            cand.get("host_club_id"),
        ):
            continue
        cand_classes = extract_class_tokens(
            cand.get("category"), cand.get("class_layout"), cand.get("event_name") or ""
        )
        if not class_tokens_compatible(csv_classes, cand_classes):
            continue
        overlap = title_overlap_ratio(csv_row.get("event_name") or "", cand.get("event_name") or "")
        if overlap < TITLE_TOKEN_OVERLAP_MIN:
            continue
        matches.append({**cand, "_overlap": overlap, "_date_delta": delta})
    return matches


def merge_extras_preserving_manual(existing_extras, csv_row: dict, prior: dict) -> dict:
    extras = _extras_dict(existing_extras)
    extras["manual_provenance"] = extras.get("manual_provenance") or {
        "source": prior.get("source"),
        "source_event_id": prior.get("source_event_id"),
        "event_name": prior.get("event_name"),
        "merged_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "match_overlap": prior.get("_overlap"),
    }
    extras["prior_source"] = prior.get("source")
    extras["prior_source_event_id"] = prior.get("source_event_id")
    extras["merged_from_manual"] = True
    extras["adopted_sas_source"] = csv_row.get("source")
    extras["adopted_sas_source_event_id"] = csv_row.get("source_event_id")
    return extras


def adopt_and_enrich(cur, event_id: int, csv_row: dict, club_id: int | None, prior: dict, scrape_run_id: str) -> None:
    """Adopt SAS identity onto manual/pending row; preserve curated host_club_id / regatta_id / extras."""
    extras = merge_extras_preserving_manual(prior.get("extras"), csv_row, prior)
    preserved_club_id = prior.get("host_club_id") if prior.get("host_club_id") is not None else club_id
    score = int(round(100 * float(prior.get("_overlap") or 0)))
    cur.execute(
        """
        UPDATE events SET
            source = %s,
            source_event_id = %s,
            source_url = COALESCE(%s, source_url),
            event_name = COALESCE(NULLIF(%s, ''), event_name),
            start_date = COALESCE(%s, start_date),
            end_date = COALESCE(%s, end_date),
            event_year = COALESCE(%s, event_year),
            venue_raw = COALESCE(%s, venue_raw),
            host_club_name_raw = COALESCE(%s, host_club_name_raw),
            host_club_id = COALESCE(host_club_id, %s),
            location_raw = COALESCE(%s, location_raw),
            address = COALESCE(%s, address),
            nor_url = COALESCE(%s, nor_url),
            si_url = COALESCE(%s, si_url),
            results_url = COALESCE(%s, results_url),
            other_docs = COALESCE(%s, other_docs),
            category = COALESCE(%s, category),
            description = COALESCE(%s, description),
            contact = COALESCE(%s, contact),
            organiser = COALESCE(%s, organiser),
            event_status = COALESCE(%s, event_status),
            last_seen_at = now(),
            scrape_run_id = %s,
            match_score = %s,
            match_method = %s,
            extras = %s::jsonb,
            provenance_status = COALESCE(NULLIF(provenance_status, ''), 'merged_from_manual')
        WHERE event_id = %s
        """,
        (
            csv_row["source"],
            csv_row["source_event_id"],
            csv_row.get("source_url"),
            csv_row.get("event_name"),
            csv_row.get("start_date"),
            csv_row.get("end_date"),
            csv_row.get("event_year"),
            csv_row.get("venue_raw"),
            csv_row.get("host_club_name_raw"),
            preserved_club_id,
            csv_row.get("location_raw"),
            csv_row.get("address"),
            csv_row.get("nor_url"),
            csv_row.get("si_url"),
            csv_row.get("results_url"),
            csv_row.get("other_docs"),
            csv_row.get("category"),
            csv_row.get("description"),
            csv_row.get("contact"),
            csv_row.get("organiser"),
            csv_row.get("event_status"),
            scrape_run_id,
            score,
            "soft_date_venue_class_title",
            json.dumps(extras),
            event_id,
        ),
    )


def upsert_sas_row(cur, r: dict, club_id: int | None, scrape_run_id: str) -> None:
    cur.execute(
        """
        INSERT INTO events (
            source, source_event_id, source_url,
            event_name, start_date, end_date, event_year,
            venue_raw, host_club_name_raw, host_club_id, location_raw, address,
            nor_url, si_url, results_url, other_docs,
            category, description, contact, organiser,
            event_status, last_seen_at, scrape_run_id
        ) VALUES (
            %s, %s, %s,
            %s, %s, %s, %s,
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
        """,
        (
            r["source"], r["source_event_id"], r["source_url"],
            r["event_name"], r["start_date"], r["end_date"], r["event_year"],
            r["venue_raw"], r["host_club_name_raw"], club_id, r["location_raw"], r["address"],
            r["nor_url"], r["si_url"], r["results_url"], r["other_docs"],
            r["category"], r["description"], r["contact"], r["organiser"],
            r["event_status"], scrape_run_id,
        ),
    )


def identity_exists(cur, source: str, source_event_id: str) -> bool:
    cur.execute(
        "SELECT 1 FROM events WHERE source = %s AND source_event_id = %s LIMIT 1",
        (source, source_event_id),
    )
    return cur.fetchone() is not None


def load_csv_rows(csv_path: Path) -> list[dict]:
    rows = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            eid = (row.get("sas_event_id") or "").strip() or (row.get("external_event_id") or "").strip()
            if not eid:
                continue
            source = (
                "sas"
                if (row.get("sas_event_id") or "").strip()
                else (row.get("external_host") or "external").strip() or "external"
            )
            is_past = (row.get("is_past") or "").strip().lower() == "true"
            event_status = "completed" if is_past else "upcoming"
            start_date, event_year = parse_date(row.get("start_date") or "") or (None, None)
            end_date, _ = parse_date(row.get("end_date") or "") or (None, None)
            venue_val = (row.get("location") or row.get("venue_text") or "").strip() or None
            host_val = (row.get("host") or "").strip() or venue_val
            if venue_val and is_invalid_venue(venue_val):
                venue_val = None
            if host_val and is_invalid_venue(host_val):
                host_val = None
            if not host_val and venue_val:
                host_val = venue_val
            rows.append({
                "source": source,
                "source_event_id": eid,
                "source_url": (row.get("details_url") or "").strip() or None,
                "event_name": (row.get("title") or "").strip() or "Untitled",
                "start_date": start_date,
                "end_date": end_date,
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
    return rows


def process_rows(cur, rows: list[dict], scrape_run_id: str, dry_run: bool) -> dict:
    counts = {
        "merged": 0,
        "inserted_or_updated": 0,
        "ambiguous": 0,
        "host_club_resolved": 0,
    }
    candidates = fetch_pending_manual_rows(cur)
    claimed_ids: set[int] = set()

    for r in rows:
        host_val = r.get("host_club_name_raw") or r.get("venue_raw") or ""
        club_id = resolve_host_to_club_id(cur, host_val) if host_val else None
        if club_id is not None:
            counts["host_club_resolved"] += 1

        if identity_exists(cur, r["source"], r["source_event_id"]):
            if not dry_run:
                upsert_sas_row(cur, r, club_id, scrape_run_id)
            counts["inserted_or_updated"] += 1
            continue

        open_candidates = [c for c in candidates if c["event_id"] not in claimed_ids]
        matches = find_soft_matches(r, club_id, open_candidates)

        if len(matches) == 1:
            m = matches[0]
            print(
                f"{'MERGE would adopt' if dry_run else 'MERGE'} event_id={m['event_id']} "
                f"({m.get('source')}/{m.get('source_event_id')}) "
                f"← {r['source']}/{r['source_event_id']} "
                f"'{r['event_name'][:50]}' overlap={m.get('_overlap'):.2f}",
                file=sys.stderr,
            )
            if not dry_run:
                adopt_and_enrich(cur, m["event_id"], r, club_id, m, scrape_run_id)
            claimed_ids.add(m["event_id"])
            counts["merged"] += 1
            continue

        if len(matches) > 1:
            counts["ambiguous"] += 1
            ids = ", ".join(str(m["event_id"]) for m in matches)
            print(
                f"AMBIGUOUS soft-match for {r['source']}/{r['source_event_id']} "
                f"'{r['event_name'][:50]}' → event_ids=[{ids}] "
                f"(no insert, no merge — review)",
                file=sys.stderr,
            )
            continue

        if not dry_run:
            upsert_sas_row(cur, r, club_id, scrape_run_id)
        counts["inserted_or_updated"] += 1

    return counts


def main():
    parser = argparse.ArgumentParser(description="Load sas_events_list.csv into events table.")
    parser.add_argument("--csv", type=str, default=None, help="Path to CSV (default: sas_events_list.csv in cwd)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate soft-match + upsert counts; do not write (still needs DB_URL for match lookup)",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv) if args.csv else Path("sas_events_list.csv")
    if not csv_path.is_file():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    if not psycopg2:
        print("ERROR: psycopg2 required. pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

    db_url = get_db_url()
    if not db_url:
        print("ERROR: DATABASE_URL or DB_URL not set.", file=sys.stderr)
        sys.exit(1)

    rows = load_csv_rows(csv_path)
    if not rows:
        print("No rows to load.", file=sys.stderr)
        return

    print(f"Loaded {len(rows)} rows from {csv_path}", file=sys.stderr)
    scrape_run_id = datetime.utcnow().strftime("%Y%m%d%H%M")
    conn = psycopg2.connect(db_url)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            counts = process_rows(cur, rows, scrape_run_id, dry_run=args.dry_run)
        if args.dry_run:
            conn.rollback()
            print(
                f"Dry run: merged={counts['merged']} "
                f"inserted_or_updated={counts['inserted_or_updated']} "
                f"ambiguous={counts['ambiguous']} "
                f"host_club_resolved={counts['host_club_resolved']} "
                f"(scrape_run_id={scrape_run_id}, not written)",
                file=sys.stderr,
            )
        else:
            conn.commit()
            print(
                f"Done: merged={counts['merged']} "
                f"inserted_or_updated={counts['inserted_or_updated']} "
                f"ambiguous={counts['ambiguous']} "
                f"host_club_resolved={counts['host_club_resolved']} "
                f"(scrape_run_id={scrape_run_id})",
                file=sys.stderr,
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
