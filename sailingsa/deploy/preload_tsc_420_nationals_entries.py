#!/usr/bin/env python3
"""Preload the initial (incomplete) 2026 TSC 420 Nationals entry list.

Event URL:  https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals
Fleet URL:  https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals/class-420

Rows go into public.results on the existing :420 block only.
Do not edit api.py, headers, or the Event URL page. Rank is NULL.

Names stored are sas_id_personal first_name + last_name (not the informal list).

Helm/crew amends:
  Nathan McCombe helm, Liam Geldenhuys crew.
  Kamva Mgcubhe helm, Maddison Smit crew (MAC) — one boat.
  Howard Leoto helm, Lebogang January crew, club RNYC.

Staging sheet order (rank stays blank until Race 1):
  1. 2025 pair-rank average (missing teammate = DNC 13)
  2. New boats alphabetical by helm last name, then first name

Sheet display is ORDER BY rank NULLS LAST, result_id — restage writes this
list onto existing result_ids. Never DELETE (docs/README_results_table.md).

Total / nett / discards are not written here. Live PATCH /api/result/{id}/race
already recalculates them via _recalculate_fleet_block_scoring_and_ranks
(legacy Appendix A for this slug: discard_count = races_sailed // 5).

  export DB_URL=...   # from sailingsa-api.service on live
  python3 sailingsa/deploy/preload_tsc_420_nationals_entries.py --dry-run
  python3 sailingsa/deploy/preload_tsc_420_nationals_entries.py
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    import psycopg2
    from psycopg2.extras import Json, RealDictCursor
except ImportError:
    psycopg2 = None
    Json = None
    RealDictCursor = None

REGATTA_ID = "2026-09-25-tsc-420-nationals"
BLOCK_ID = f"{REGATTA_ID}:420"
EVENT_NAME = "420 Nationals"
CLASS_NAME = "420"
SAS_PORTAL = "SAS_PORTAL"
NOT_ENTERED = "NOT_ENTERED"
# 2025 420 Nationals overall had 12 boats. Missing teammate = DNC (entries+1).
DNC_2025 = 13

# Names are sas_id_personal first_name + last_name only. Informal list spellings are not stored.
# helm_sas / crew_sas from live SAS table 22 Sep 2026. Do not invent IDs. TBA crew is omitted
# unless a prior 420 team (or current same-club team that has sailed 420) uniquely identifies them.
# Sheet order is computed: 2025 pair-avg, then new boats A–Z. Rank stays NULL / blank.
# First race PATCH recalculates total, nett, discards, and rank.

ENTRIES = [
    {
        "helm_list": "Timothy Weaving",
        "helm_sas": 21172,
        "crew_list": "Hayden Miller",
        "crew_sas": 8683,
        "club_raw": "HYC",
        "club_abbrev": "HYC",
        "flag": NOT_ENTERED,
        "helm_2025_rank": 5,
        "crew_2025_rank": 2,
        "issues": [
            "New pair. Timothy 2025 5th + Hayden 2025 2nd (was Howard's crew). Sort avg 3.5."
        ],
    },
    {
        "helm_list": "Howard Leoto",
        "helm_sas": 3709,
        "crew_list": "Lebogang January",
        "crew_sas": 1485,
        "club_raw": "RNYC",
        "club_abbrev": "RNYC",
        "flag": NOT_ENTERED,
        "helm_2025_rank": 2,
        "crew_2025_rank": None,
        "issues": [
            "New pair. Howard 2025 2nd was with Hayden, not Lebogang. "
            "Lebogang did not sail 2025 Nationals = DNC 13. Sort avg (2+13)/2 = 7.5."
        ],
    },
    {
        "helm_list": "Jemayne Wolmarans",
        "helm_sas": 1521,
        "crew_list": None,
        "crew_sas": None,
        "club_raw": "ZVYC",
        "club_abbrev": "ZVYC",
        "flag": SAS_PORTAL,
        "helm_2025_rank": 3,
        "crew_2025_rank": None,
        "issues": ["New pair vs 2025 (Dillan not listed). Jemayne 3 + crew DNC 13. Sort avg 8.0."],
    },
    {
        "helm_list": "Kamva Mgcubhe",
        "helm_sas": 13516,
        "crew_list": "Maddison Smit",
        "crew_sas": 21052,
        "club_raw": "MAC",
        "club_abbrev": "MAC",
        "flag": SAS_PORTAL,
        "helm_2025_rank": None,
        "crew_2025_rank": 4,
        "issues": [
            "New pair. Kamva DNC 13 + Maddison 2025 4th. Sort avg 8.5."
        ],
    },
    {
        "helm_list": "Nathan McCombe",
        "helm_sas": 21517,
        "crew_list": "Liam Geldenhuys",
        "crew_sas": 25653,
        "club_raw": "HYC",
        "club_abbrev": "HYC",
        "flag": SAS_PORTAL,
        "helm_2025_rank": 5,
        "crew_2025_rank": None,
        "issues": [
            "New pair. Nathan 2025 5th + Liam DNC 13. Sort avg 9.0. Dirty Nathan dup 28587 unused."
        ],
    },
    {
        "helm_list": "Aisha Knobloch",
        "helm_sas": 15834,
        "crew_list": "Sphelele",
        "crew_sas": None,
        "club_raw": "MAC",
        "club_abbrev": "MAC",
        "flag": SAS_PORTAL,
        "helm_2025_rank": 8,
        "crew_2025_rank": None,
        "issues": [
            "New pair. Aisha 2025 8th + Sphelele DNC 13. Sort avg 10.5. Sphelele no SAS."
        ],
    },
    {
        "helm_list": "Kenwin Daniels",
        "helm_sas": 3184,
        "crew_list": None,
        "crew_sas": None,
        "club_raw": "Izivungu",
        "club_abbrev": "IZI",
        "flag": SAS_PORTAL,
        "helm_2025_rank": None,
        "crew_2025_rank": None,
        "issues": ["Club Izivungu → IZI."],
    },
    {
        "helm_list": "Chiara Fruet",
        "helm_sas": 6497,
        "crew_list": None,
        "crew_sas": None,
        "club_raw": "MAC",
        "club_abbrev": "MAC",
        "flag": NOT_ENTERED,
        "helm_2025_rank": None,
        "crew_2025_rank": None,
        "issues": [],
    },
    {
        "helm_list": "Ben Henshilwood",
        "helm_sas": 18020,
        "crew_list": "Thomas Henshilwood",
        "crew_sas": 9612,
        "club_raw": "HYC",
        "club_abbrev": "HYC",
        "flag": NOT_ENTERED,
        "helm_2025_rank": None,
        "crew_2025_rank": None,
        "issues": ["Thomas Henshilwood 9612 (2009), not Thomas 7352 (1976)."],
    },
    {
        "helm_list": "Joshua Nankin",
        "helm_sas": 8704,
        "crew_list": "Joshua Keytel",
        "crew_sas": 13522,
        "club_raw": "ZVYC",
        "club_abbrev": "ZVYC",
        "flag": SAS_PORTAL,
        "helm_2025_rank": None,
        "crew_2025_rank": None,
        "issues": [],
    },
    {
        "helm_list": "Dale Rae",
        "helm_sas": 25,
        "crew_list": "James Rae",
        "crew_sas": 15737,
        "club_raw": "HYC",
        "club_abbrev": "HYC",
        "flag": SAS_PORTAL,
        "helm_2025_rank": None,
        "crew_2025_rank": None,
        "issues": [],
    },
    {
        "helm_list": "Hayley Rae",
        "helm_sas": 15738,
        "crew_list": "Faith Lyons",
        "crew_sas": 12998,
        "club_raw": "HYC",
        "club_abbrev": "HYC",
        "flag": SAS_PORTAL,
        "helm_2025_rank": None,
        "crew_2025_rank": None,
        "issues": [],
    },
    {
        "helm_list": "Theodor Scheder-Bieschin",
        "helm_sas": 9515,
        "crew_list": "Anna Scheder-Bieschin",
        "crew_sas": 12797,
        "club_raw": "ZVYC",
        "club_abbrev": "ZVYC",
        "flag": NOT_ENTERED,
        "helm_2025_rank": None,
        "crew_2025_rank": None,
        "issues": [
            "Partial 'Scheder Bischein' matched via SAS surname + prior 420 + current ZVYC team. "
            "Theodor 9515 helm (ZVYC; 420 Nationals 2018/2020/2021). "
            "Anna 12797 crew (420 Nationals 2021; Sonnet crew to Theodor at ZVYC Cape Classic 13 Sep 2026)."
        ],
    },
    {
        "helm_list": "Alexa Winzel",
        "helm_sas": None,
        "crew_list": None,
        "crew_sas": None,
        "club_raw": "MAC",
        "club_abbrev": "MAC",
        "flag": NOT_ENTERED,
        "helm_2025_rank": None,
        "crew_2025_rank": None,
        "issues": [
            "No SAS surname Winzel. Only MAC Alexa is Alexa Aab 22974 (ILCA 4.7 / Optimist, no 420). Not assigned."
        ],
    },
    {
        "helm_list": "Amir Yaghya",
        "helm_sas": 8382,
        "crew_list": None,
        "crew_sas": None,
        "club_raw": "ZVSC",
        "club_abbrev": "ZVSC",
        "flag": SAS_PORTAL,
        "helm_2025_rank": None,
        "crew_2025_rank": None,
        "issues": ["SAS home club is ZVYC; entry club left as listed ZVSC."],
    },
]


def pair_avg_2025(entry: dict) -> float | None:
    """Average of helm + crew 2025 overall places. Missing sailor = DNC 13. None if both new."""
    helm = entry.get("helm_2025_rank")
    crew = entry.get("crew_2025_rank")
    if helm is None and crew is None:
        return None
    h = DNC_2025 if helm is None else int(helm)
    c = DNC_2025 if crew is None else int(crew)
    return (h + c) / 2.0


def helm_sort_name(entry: dict) -> tuple[str, str, str]:
    raw = (entry.get("helm_name") or entry.get("helm_list") or "").strip()
    parts = raw.split()
    last = parts[-1].lower() if parts else ""
    first = parts[0].lower() if parts else ""
    return (last, first, raw.lower())


def staging_sort_key(entry: dict) -> tuple:
    avg = pair_avg_2025(entry)
    if avg is not None:
        return (0, avg, *helm_sort_name(entry))
    return (1, 0.0, *helm_sort_name(entry))


def sorted_staging_entries(entries: list[dict]) -> list[dict]:
    return sorted(entries, key=staging_sort_key)


def staging_label(entry: dict) -> str:
    avg = pair_avg_2025(entry)
    if avg is not None:
        return f"2025 avg {avg:.1f}"
    return "new A–Z"


def get_db_url() -> str:
    url = (os.getenv("DATABASE_URL") or os.getenv("DB_URL") or "").strip()
    if not url:
        print("ERROR: DATABASE_URL or DB_URL not set.", file=sys.stderr)
        sys.exit(1)
    return url


def col_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def fetch_one(cur, sql: str, args=()):
    cur.execute(sql, args)
    return cur.fetchone()


def official_name(cur, sas_id: int | None, fallback: str | None) -> str | None:
    """SAS table is truth: first_name + last_name. List spelling is only used when there is no SAS ID."""
    if sas_id is None:
        return (fallback or "").strip() or None
    row = fetch_one(
        cur,
        """
        SELECT TRIM(first_name) AS first_name,
               TRIM(last_name) AS last_name,
               TRIM(full_name) AS full_name
        FROM sas_id_personal
        WHERE sa_sailing_id::text = %s
        LIMIT 1
        """,
        (str(sas_id),),
    )
    if not row:
        raise SystemExit(f"ERROR: no sas_id_personal row for SA ID {sas_id}. Do not invent a name.")
    first = (row.get("first_name") or "").strip()
    last = (row.get("last_name") or "").strip()
    if first and last:
        return f"{first} {last}"
    full = (row.get("full_name") or "").strip()
    if full:
        return full
    raise SystemExit(
        f"ERROR: sas_id_personal {sas_id} has no first_name/last_name. Do not use the informal list."
    )


def resolve_club(cur, abbrev: str) -> dict:
    row = fetch_one(
        cur,
        """
        SELECT club_id, club_abbrev, club_fullname
        FROM clubs
        WHERE upper(trim(club_abbrev)) = %s
        ORDER BY club_id
        LIMIT 1
        """,
        (abbrev.upper(),),
    )
    if not row:
        raise SystemExit(f"ERROR: club abbrev {abbrev!r} not found in clubs.")
    return dict(row)


def resolve_block(cur) -> dict:
    row = fetch_one(
        cur,
        """
        SELECT rb.block_id, rb.regatta_id, rb.class_id, rb.class_original, rb.class_canonical,
               rb.fleet_label, r.event_name, r.start_date, r.end_date, r.result_status
        FROM regatta_blocks rb
        JOIN regattas r ON r.regatta_id = rb.regatta_id
        WHERE rb.block_id = %s
           OR (rb.regatta_id = %s AND lower(trim(COALESCE(rb.class_canonical, rb.class_original, ''))) = '420')
        ORDER BY CASE WHEN rb.block_id = %s THEN 0 ELSE 1 END
        LIMIT 1
        """,
        (BLOCK_ID, REGATTA_ID, BLOCK_ID),
    )
    if not row:
        raise SystemExit(
            f"ERROR: block {BLOCK_ID} not found. Run create_tsc_420_nationals_2026_event_url.py first."
        )
    return dict(row)


def resolve_class(cur, block: dict) -> dict:
    cid = block.get("class_id")
    if cid is not None:
        row = fetch_one(
            cur,
            "SELECT class_id, class_name FROM classes WHERE class_id = %s",
            (cid,),
        )
        if row:
            return dict(row)
    row = fetch_one(
        cur,
        "SELECT class_id, class_name FROM classes WHERE trim(class_name) = '420' LIMIT 1",
    )
    if not row:
        raise SystemExit("ERROR: class_name '420' not found in classes.")
    return dict(row)


def raced_is_nullable(cur) -> bool:
    cur.execute(
        """
        SELECT is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'results' AND column_name = 'raced'
        """
    )
    row = cur.fetchone()
    if not row:
        return True
    return str(row.get("is_nullable") or "").upper() == "YES"


def find_existing(cur, block_id: str, entry: dict) -> dict | None:
    helm_sas = entry.get("helm_sas")
    crew_sas = entry.get("crew_sas")
    names = [n for n in (entry.get("helm_name"), entry.get("helm_list")) if n]
    if helm_sas is not None:
        row = fetch_one(
            cur,
            """
            SELECT * FROM results
            WHERE regatta_id = %s AND block_id = %s AND helm_sa_sailing_id::text = %s
            ORDER BY result_id LIMIT 1
            """,
            (REGATTA_ID, block_id, str(helm_sas)),
        )
        if row:
            return dict(row)
        # Pair stored the other way around (Liam helm / Nathan crew before amend).
        if crew_sas is not None:
            row = fetch_one(
                cur,
                """
                SELECT * FROM results
                WHERE regatta_id = %s AND block_id = %s
                  AND (
                    helm_sa_sailing_id::text = %s
                    OR crew_sa_sailing_id::text = %s
                    OR (helm_sa_sailing_id::text = %s AND crew_sa_sailing_id::text = %s)
                  )
                ORDER BY result_id LIMIT 1
                """,
                (REGATTA_ID, block_id, str(crew_sas), str(helm_sas), str(crew_sas), str(helm_sas)),
            )
            if row:
                return dict(row)
    if names:
        row = fetch_one(
            cur,
            """
            SELECT * FROM results
            WHERE regatta_id = %s AND block_id = %s
              AND lower(trim(helm_name)) = ANY(%s)
            ORDER BY result_id LIMIT 1
            """,
            (REGATTA_ID, block_id, [n.strip().lower() for n in names]),
        )
        if row:
            return dict(row)
    return None


def build_row_values(entry: dict, block: dict, class_420: dict, club: dict, cols: list[str]) -> dict:
    class_name = (class_420.get("class_name") or CLASS_NAME).strip()
    values = {
        "regatta_id": REGATTA_ID,
        "block_id": block["block_id"],
        "rank": None,  # blank staging; first race will sort
        "fleet_label": (block.get("fleet_label") or class_name).strip() or class_name,
        "class_original": class_name,
        "class_canonical": class_name,
        "sail_number": None,
        "helm_name": entry["helm_name"],
        "helm_sa_sailing_id": entry.get("helm_sas"),
        "crew_name": entry.get("crew_name"),
        "crew_sa_sailing_id": entry.get("crew_sas"),
        "club_raw": entry["club_raw"],
        "club_id": club["club_id"],
        "class_id": class_420["class_id"],
        "raced": None,
        "validation_flag": entry["flag"],
        "result_status": "Provisional",
        "event_name": block.get("event_name") or EVENT_NAME,
        "start_date": block.get("start_date"),
        "end_date": block.get("end_date"),
        "race_scores": Json({}) if Json is not None else {},  # NOT NULL; empty = no races yet
        "total_points_raw": None,
        "nett_points_raw": None,
        "match_status_helm": "matched" if entry.get("helm_sas") else "unmatched",
        "match_status_crew": (
            "matched" if entry.get("crew_sas") else ("unmatched" if entry.get("crew_name") else None)
        ),
    }
    return {k: values[k] for k in cols if k in values}


def _row_has_scores_or_rank(row: dict) -> bool:
    scores = row.get("race_scores")
    has_real_scores = bool(scores) and str(scores).strip() not in ("{}", "null", "None")
    if isinstance(scores, dict):
        has_real_scores = any(str(v).strip() for v in scores.values())
    return has_real_scores or row.get("rank") is not None


def upsert_entry(cur, entry: dict, block: dict, class_420: dict, club: dict, cols: list[str], dry_run: bool) -> str:
    existing = find_existing(cur, block["block_id"], entry)
    values = build_row_values(entry, block, class_420, club, cols)
    helm = values.get("helm_name")
    crew = values.get("crew_name") or "—"
    flag = values.get("validation_flag")
    if existing:
        rid = existing.get("result_id")
        if _row_has_scores_or_rank(existing):
            safe_cols = [
                c
                for c in (
                    "helm_name",
                    "helm_sa_sailing_id",
                    "crew_name",
                    "crew_sa_sailing_id",
                    "club_raw",
                    "club_id",
                    "validation_flag",
                    "match_status_helm",
                    "match_status_crew",
                )
                if c in cols
            ]
        else:
            safe_cols = [c for c in cols if c not in ("regatta_id", "block_id")]
        sets = ", ".join(f"{c} = %s" for c in safe_cols)
        args = [values[c] for c in safe_cols] + [rid]
        print(f"UPDATE result_id={rid} {helm} / {crew} {entry['club_abbrev']} {flag}")
        if not dry_run:
            cur.execute(f"UPDATE results SET {sets} WHERE result_id = %s", args)
        return "update"
    insert_cols = [c for c in cols if c in values]
    placeholders = ", ".join(["%s"] * len(insert_cols))
    print(f"INSERT {helm} / {crew} {entry['club_abbrev']} {flag}")
    if not dry_run:
        cur.execute(
            f"INSERT INTO results ({', '.join(insert_cols)}) VALUES ({placeholders})",
            tuple(values[c] for c in insert_cols),
        )
    return "insert"


def restage_onto_existing_ids(
    cur,
    block: dict,
    class_420: dict,
    ordered: list[dict],
    cols: list[str],
    dry_run: bool,
) -> bool:
    """Write staging order onto existing result_ids. Never DELETE. Skip if races exist."""
    cur.execute(
        """
        SELECT result_id, helm_name, race_scores, rank
        FROM results
        WHERE regatta_id = %s AND block_id = %s
        ORDER BY result_id
        """,
        (REGATTA_ID, block["block_id"]),
    )
    rows = list(cur.fetchall() or [])
    if len(rows) != len(ordered):
        print(f"RESTAGE skip: {len(rows)} live rows vs {len(ordered)} list")
        return False
    if any(_row_has_scores_or_rank(dict(r)) for r in rows):
        print("RESTAGE skip: scores or ranks present — Race 1 already sorts")
        return False
    payloads = []
    for entry in ordered:
        club = resolve_club(cur, entry["club_abbrev"])
        payloads.append((entry, build_row_values(entry, block, class_420, club, cols)))
    ids = [r["result_id"] for r in rows]
    if not dry_run:
        cur.execute(
            """
            UPDATE results
            SET helm_sa_sailing_id = NULL, crew_sa_sailing_id = NULL
            WHERE regatta_id = %s AND block_id = %s
            """,
            (REGATTA_ID, block["block_id"]),
        )
    safe_cols = [c for c in cols if c not in ("regatta_id", "block_id")]
    print()
    print("RESTAGE onto existing result_ids (2025 pair-avg, then new A–Z):")
    for rid, (entry, values) in zip(ids, payloads):
        sets = ", ".join(f"{c} = %s" for c in safe_cols)
        args = [values[c] for c in safe_cols] + [rid]
        helm = values.get("helm_name")
        crew = values.get("crew_name") or "—"
        print(f"  result_id={rid} {helm} / {crew}  {staging_label(entry)}")
        if not dry_run:
            cur.execute(f"UPDATE results SET {sets} WHERE result_id = %s", args)
    return True


def clear_entries_raced_so_count_wins(cur, block_id: str, dry_run: bool) -> None:
    """entries_raced=0 beats COALESCE count and shows Entries: 0. NULL uses row count."""
    if not col_exists(cur, "regatta_blocks", "entries_raced"):
        return
    print("entries_raced=NULL (sailed Entries uses row count; scoring still auto on PATCH)")
    if not dry_run:
        cur.execute(
            "UPDATE regatta_blocks SET entries_raced = NULL WHERE block_id = %s",
            (block_id,),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Preload TSC 420 Nationals 2026 entry list.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan; do not write.")
    args = parser.parse_args()
    if psycopg2 is None or RealDictCursor is None:
        print("ERROR: psycopg2 required. pip install psycopg2-binary", file=sys.stderr)
        return 1

    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor(cursor_factory=RealDictCursor)
    inserted = updated = 0
    issues = []
    try:
        block = resolve_block(cur)
        class_420 = resolve_class(cur, block)
        if not raced_is_nullable(cur):
            raise SystemExit(
                "ERROR: results.raced is NOT NULL. Preload needs raced=NULL so rows "
                "are not struck out and do not inflate raced stats."
            )
        wanted = [
            "regatta_id",
            "block_id",
            "rank",
            "fleet_label",
            "class_original",
            "class_canonical",
            "sail_number",
            "helm_name",
            "helm_sa_sailing_id",
            "crew_name",
            "crew_sa_sailing_id",
            "club_raw",
            "club_id",
            "class_id",
            "raced",
            "validation_flag",
            "result_status",
            "event_name",
            "start_date",
            "end_date",
            "race_scores",
            "total_points_raw",
            "nett_points_raw",
            "match_status_helm",
            "match_status_crew",
        ]
        cols = [c for c in wanted if col_exists(cur, "results", c)]
        for req in ("regatta_id", "block_id", "class_original", "helm_name", "validation_flag", "raced"):
            if req not in cols:
                raise SystemExit(f"ERROR: results.{req} missing.")

        ordered: list[dict] = []
        for raw in sorted_staging_entries(ENTRIES):
            entry = dict(raw)
            entry["helm_name"] = official_name(cur, entry.get("helm_sas"), entry.get("helm_list"))
            entry["crew_name"] = official_name(cur, entry.get("crew_sas"), entry.get("crew_list"))
            ordered.append(entry)

        print(f"Regatta: {REGATTA_ID}")
        print(f"Block:   {block['block_id']} class_id={class_420['class_id']} {class_420['class_name']}")
        print(f"Status:  {block.get('result_status')} (unchanged)")
        print(f"Event:   https://sailingsa.co.za/regatta/{REGATTA_ID}")
        print(f"Fleet:   https://sailingsa.co.za/regatta/{REGATTA_ID}/class-420")
        print("Rank:    blank (2025 pair-avg, then new A–Z; Race 1 auto-sorts)")
        print("Score:   total / nett / discards built in on PATCH /api/result/{id}/race")
        print()

        for i, entry in enumerate(ordered, start=1):
            club = resolve_club(cur, entry["club_abbrev"])
            print(
                f"{i:2d}. {entry['helm_name']} / {entry['crew_name'] or '—'} "
                f"{club['club_abbrev']} {entry['flag']}  {staging_label(entry)}"
            )
            if entry.get("helm_sas") is None:
                issues.append(f"{entry['helm_name']}: no helm SA ID (and no temp ID created).")
            if entry.get("crew_list") and entry.get("crew_sas") is None:
                issues.append(f"{entry['crew_name']}: crew listed, no SA ID.")
            for note in entry.get("issues") or []:
                issues.append(f"{entry['helm_name']}: {note}")
            action = upsert_entry(cur, entry, block, class_420, club, cols, args.dry_run)
            if action == "insert":
                inserted += 1
            else:
                updated += 1

        restage_onto_existing_ids(cur, block, class_420, ordered, cols, args.dry_run)
        clear_entries_raced_so_count_wins(cur, block["block_id"], args.dry_run)

        leftover = fetch_one(
            cur,
            """
            SELECT result_id, helm_name FROM results
            WHERE regatta_id = %s AND block_id = %s
              AND helm_sa_sailing_id::text = '21052'
              AND raced IS NULL AND rank IS NULL
            ORDER BY result_id LIMIT 1
            """,
            (REGATTA_ID, block["block_id"]),
        )
        if leftover:
            issues.append(
                f"Leftover standalone Maddison helm row result_id={leftover.get('result_id')} "
                "— she is now crew on Kamva; do not keep a second boat."
            )

        print()
        print(f"Rows: {inserted} insert, {updated} update. List is initial / incomplete ({len(ENTRIES)} boats).")
        print("Class /class/420 sailors list is raced=TRUE only — these rows will not appear there yet.")
        print("Locked iframe sheets (class-results.html / results.html) are not styled.")
        if issues:
            print()
            print("ISSUES before deploy:")
            seen = set()
            for item in issues:
                if item in seen:
                    continue
                seen.add(item)
                print(f"  - {item}")

        if args.dry_run:
            conn.rollback()
            print()
            print("DRY RUN — no writes. Re-run without --dry-run to apply.")
        else:
            conn.commit()
            print()
            print("Applied.")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
