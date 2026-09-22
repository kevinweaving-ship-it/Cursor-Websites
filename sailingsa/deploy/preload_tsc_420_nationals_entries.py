#!/usr/bin/env python3
"""Preload the initial (incomplete) 2026 TSC 420 Nationals entry list.

Event URL:  https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals
Fleet URL:  https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals/class-420

Rows go into public.results on the existing :420 block so the Event / fleet
sheets can show them. raced is NULL (does not inflate stats, no strike-out).
No rank (no medals). validation_flag is SAS_PORTAL or NOT_ENTERED.

Names stored are sas_id_personal first_name + last_name (not the informal list).

Helm/crew amends:
  Nathan McCombe helm, Liam Geldenhuys crew.
  Kamva Mgcubhe helm, Maddison Smit crew (MAC) — one boat.
  Howard Leoto helm, Lebogang January crew, club RNYC.

Idempotent. Default is apply; use --dry-run to print the plan only.

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
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

REGATTA_ID = "2026-09-25-tsc-420-nationals"
BLOCK_ID = f"{REGATTA_ID}:420"
EVENT_NAME = "420 Nationals"
CLASS_NAME = "420"
SAS_PORTAL = "SAS_PORTAL"
NOT_ENTERED = "NOT_ENTERED"

# Names are sas_id_personal first_name + last_name only. Informal list spellings are not stored.
# helm_sas / crew_sas from live SAS table 22 Sep 2026. Do not invent IDs. TBA crew is omitted
# unless a prior 420 team (or current same-club team that has sailed 420) uniquely identifies them.
# Sheet order: 2025 420 Nationals overall rank (best rank of anyone on the 2026 boat),
# then new boats A–Z by helm surname. Source: /regatta/2025-10-04-420-national-championship.


def _helm_surname(name: str) -> str:
    parts = (name or "").strip().split()
    return parts[-1].lower() if parts else ""


def _helm_first(name: str) -> str:
    parts = (name or "").strip().split()
    return " ".join(parts[:-1]).lower() if len(parts) > 1 else (parts[0].lower() if parts else "")


ENTRIES = [
    {
        "helm_list": "Theodor Scheder-Bieschin",
        "helm_sas": 9515,
        "crew_list": "Anna Scheder-Bieschin",
        "crew_sas": 12797,
        "club_raw": "ZVYC",
        "club_abbrev": "ZVYC",
        "flag": NOT_ENTERED,
        "nationals_2025_best": None,
        "nationals_2025_helm": None,
        "issues": [
            "Partial 'Scheder Bischein' matched via SAS surname + prior 420 + current ZVYC team. "
            "Theodor 9515 helm (ZVYC; 420 Nationals 2018/2020/2021). "
            "Anna 12797 crew (420 Nationals 2021; Sonnet crew to Theodor at ZVYC Cape Classic 13 Sep 2026)."
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
        "nationals_2025_best": None,
        "nationals_2025_helm": None,
        "issues": ["Club Izivungu → IZI."],
    },
    {
        "helm_list": "Amir Yaghya",
        "helm_sas": 8382,
        "crew_list": None,
        "crew_sas": None,
        "club_raw": "ZVSC",
        "club_abbrev": "ZVSC",
        "flag": SAS_PORTAL,
        "nationals_2025_best": None,
        "nationals_2025_helm": None,
        "issues": ["SAS home club is ZVYC; entry club left as listed ZVSC."],
    },
    {
        "helm_list": "Jemayne Wolmarans",
        "helm_sas": 1521,
        "crew_list": None,
        "crew_sas": None,
        "club_raw": "ZVYC",
        "club_abbrev": "ZVYC",
        "flag": SAS_PORTAL,
        "nationals_2025_best": 3,
        "nationals_2025_helm": 3,
        "issues": ["2025 420 Nationals 3rd (Dillan Swarts crew last year)."],
    },
    {
        "helm_list": "Nathan McCombe",
        "helm_sas": 21517,
        "crew_list": "Liam Geldenhuys",
        "crew_sas": 25653,
        "club_raw": "HYC",
        "club_abbrev": "HYC",
        "flag": SAS_PORTAL,
        "nationals_2025_best": 5,
        "nationals_2025_helm": 5,
        "issues": [
            "AMENDED: Nathan McCombe 21517 helm, Liam Geldenhuys 25653 crew. "
            "2025 420 Nationals 5th as crew to Timothy Weaving. Dirty Nathan dup 28587 unused."
        ],
    },
    {
        "helm_list": "Kamva Mgcubhe",
        "helm_sas": 13516,
        "crew_list": "Maddison Smit",
        "crew_sas": 21052,
        "club_raw": "MAC",
        "club_abbrev": "MAC",
        "flag": SAS_PORTAL,
        "nationals_2025_best": 4,
        "nationals_2025_helm": None,
        "issues": [
            "AMENDED: one MAC boat. Maddison Smit 2025 420 Nationals 4th (crew to Athenkosi Vena). "
            "Prior 420 WC Dinghy Champs 2026 rank 2 (Kamva helm / Maddison crew)."
        ],
    },
    {
        "helm_list": "Joshua Nankin",
        "helm_sas": 8704,
        "crew_list": "Joshua Keytel",
        "crew_sas": 13522,
        "club_raw": "ZVYC",
        "club_abbrev": "ZVYC",
        "flag": SAS_PORTAL,
        "nationals_2025_best": None,
        "nationals_2025_helm": None,
        "issues": [],
    },
    {
        "helm_list": "Aisha Knobloch",
        "helm_sas": 15834,
        "crew_list": "Sphelele",
        "crew_sas": None,
        "club_raw": "MAC",
        "club_abbrev": "MAC",
        "flag": SAS_PORTAL,
        "nationals_2025_best": 8,
        "nationals_2025_helm": None,
        "issues": [
            "2025 420 Nationals 8th as crew to Tristan Gress. "
            "Crew Sphelele: no unique SAS. Not assigned."
        ],
    },
    {
        "helm_list": "Hayley Rae",
        "helm_sas": 15738,
        "crew_list": "Faith Lyons",
        "crew_sas": 12998,
        "club_raw": "HYC",
        "club_abbrev": "HYC",
        "flag": SAS_PORTAL,
        "nationals_2025_best": None,
        "nationals_2025_helm": None,
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
        "nationals_2025_best": None,
        "nationals_2025_helm": None,
        "issues": [],
    },
    {
        "helm_list": "Alexa Winzel",
        "helm_sas": None,
        "crew_list": None,
        "crew_sas": None,
        "club_raw": "MAC",
        "club_abbrev": "MAC",
        "flag": NOT_ENTERED,
        "nationals_2025_best": None,
        "nationals_2025_helm": None,
        "issues": [
            "No SAS surname Winzel. Only MAC Alexa is Alexa Aab 22974 (ILCA 4.7 / Optimist, no 420). Not assigned."
        ],
    },
    {
        "helm_list": "Ben Henshilwood",
        "helm_sas": 18020,
        "crew_list": "Thomas Henshilwood",
        "crew_sas": 9612,
        "club_raw": "HYC",
        "club_abbrev": "HYC",
        "flag": NOT_ENTERED,
        "nationals_2025_best": None,
        "nationals_2025_helm": None,
        "issues": ["Thomas Henshilwood 9612 (2009), not Thomas 7352 (1976)."],
    },
    {
        "helm_list": "Chiara Fruet",
        "helm_sas": 6497,
        "crew_list": None,
        "crew_sas": None,
        "club_raw": "MAC",
        "club_abbrev": "MAC",
        "flag": NOT_ENTERED,
        "nationals_2025_best": None,
        "nationals_2025_helm": None,
        "issues": [],
    },
    {
        "helm_list": "Timothy Weaving",
        "helm_sas": 21172,
        "crew_list": "Hayden Miller",
        "crew_sas": 8683,
        "club_raw": "HYC",
        "club_abbrev": "HYC",
        "flag": NOT_ENTERED,
        "nationals_2025_best": 2,
        "nationals_2025_helm": 5,
        "issues": [
            "2025 420 Nationals: Timothy 5th helm / Nathan McCombe. Hayden Miller was 2nd crew to Howard Leoto."
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
        "nationals_2025_best": 2,
        "nationals_2025_helm": 2,
        "issues": [
            "AMENDED: Howard Leoto 3709 / Lebogang January 1485, RNYC. "
            "2025 420 Nationals 2nd (Hayden Miller crew last year). Lebogang SAS home club is RCYC."
        ],
    },
]


def _entry_sheet_order(entry: dict) -> tuple:
    """Last year's 420 Nationals first (best rank, then helm's own rank), then new A–Z by surname."""
    best = entry.get("nationals_2025_best")
    helm_r = entry.get("nationals_2025_helm")
    name = entry.get("helm_list") or ""
    if best is not None:
        return (0, int(best), int(helm_r) if helm_r is not None else 99, _helm_surname(name), _helm_first(name))
    return (1, 99, 99, _helm_surname(name), _helm_first(name))


ENTRIES.sort(key=_entry_sheet_order)


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
        WHERE sa_sailing_id = %s
        LIMIT 1
        """,
        (sas_id,),
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
            WHERE regatta_id = %s AND block_id = %s AND helm_sa_sailing_id = %s
            ORDER BY result_id LIMIT 1
            """,
            (REGATTA_ID, block_id, helm_sas),
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
                    helm_sa_sailing_id = %s
                    OR crew_sa_sailing_id = %s
                    OR (helm_sa_sailing_id = %s AND crew_sa_sailing_id = %s)
                  )
                ORDER BY result_id LIMIT 1
                """,
                (REGATTA_ID, block_id, crew_sas, helm_sas, crew_sas, helm_sas),
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
        "rank": None,
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
        "race_scores": None,
        "total_points_raw": None,
        "nett_points_raw": None,
        "match_status_helm": "matched" if entry.get("helm_sas") else "unmatched",
        "match_status_crew": (
            "matched" if entry.get("crew_sas") else ("unmatched" if entry.get("crew_name") else None)
        ),
    }
    return {k: values[k] for k in cols if k in values}


def upsert_entry(cur, entry: dict, block: dict, class_420: dict, club: dict, cols: list[str], dry_run: bool) -> str:
    existing = find_existing(cur, block["block_id"], entry)
    values = build_row_values(entry, block, class_420, club, cols)
    helm = values.get("helm_name")
    crew = values.get("crew_name") or "—"
    flag = values.get("validation_flag")
    if existing:
        rid = existing.get("result_id")
        has_scores = bool(existing.get("race_scores")) or existing.get("rank") is not None
        if has_scores:
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

        print(f"Regatta: {REGATTA_ID}")
        print(f"Block:   {block['block_id']} class_id={class_420['class_id']} {class_420['class_name']}")
        print(f"Status:  {block.get('result_status')} (unchanged)")
        print(f"Event:   https://sailingsa.co.za/regatta/{REGATTA_ID}")
        print(f"Fleet:   https://sailingsa.co.za/regatta/{REGATTA_ID}/class-420")
        print()

        for i, raw in enumerate(ENTRIES, start=1):
            entry = dict(raw)
            club = resolve_club(cur, entry["club_abbrev"])
            entry["helm_name"] = official_name(cur, entry.get("helm_sas"), entry.get("helm_list"))
            entry["crew_name"] = official_name(cur, entry.get("crew_sas"), entry.get("crew_list"))
            print(f"{i:2d}. {entry['helm_name']} / {entry['crew_name'] or '—'} "
                  f"{club['club_abbrev']} {entry['flag']}")
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

        leftover = fetch_one(
            cur,
            """
            SELECT result_id, helm_name FROM results
            WHERE regatta_id = %s AND block_id = %s
              AND helm_sa_sailing_id = 21052
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
