#!/usr/bin/env python3
"""
Align J22 boat registry to North Sails sheet: 16 sails each with bow_no + boat_name.

- Match sail by digits only (SA prefix ignored)
- Ensure class_id=48 sail_number, bow_no, and current boat_name
- Duplicate names: merge only when sail digits match across boat_ids
"""
from __future__ import annotations

import os
import re
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor, Json

DB_URL = os.environ.get(
    "DB_URL",
    "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master",
)
CLASS_ID = 48
SOURCE_REGATTA = "2026-08-16-2026-north-sails-j22-championships"
SOURCE_TYPE = "manual"
CREATED_BY = "north_sails_j22_boat_fix"

SHEET = [
    # rank, bow, sail, boat_name
    (1, 32, "SA 1571", "Nitro Juice"),
    (2, 31, "SA 774", "Nitro Maverick"),
    (3, 48, "SA 1169", "Ullman Sails Camissa"),
    (4, 23, "SA 763", "Phantom"),
    (5, 34, "SA 1116", "G'day J"),
    (6, 49, "SA 1175", "Nitro Monkey"),
    (7, 26, "SA 766", "Amtec Racing"),
    (8, 28, "SA 768", "Ullman Racing"),
    (9, 8, "SA 173", "J-Walker powered by North Sails"),
    (10, 14, "SA 185", "Andiamo"),
    (11, 55, "SA 1239", "CaCanny"),
    (12, 52, "SA 1277", "22-ATE"),
    (13, 63, "SA 771", "Donna Mia Forever"),
    (14, 46, "SA 1176", "Wildcard"),
    (15, 43, "SA 1138", "Laugh a minute"),
    (16, 51, "SA 1237", "Attacke"),
]


def sail_digits(s: str) -> str:
    return re.sub(r"[^0-9]", "", s or "") or ""


def find_j22_boats_for_sail(cur, digits: str) -> list[dict]:
    cur.execute(
        """
        SELECT bi.identifier_id, bi.boat_id, bi.identifier_value, bi.is_current, bi.class_id
        FROM boat_identifiers bi
        WHERE bi.identifier_type = 'sail_number'
          AND bi.class_id = %s
          AND REGEXP_REPLACE(bi.identifier_value, '[^0-9]', '', 'g') = %s
        ORDER BY bi.is_current DESC NULLS LAST, bi.identifier_id
        """,
        (CLASS_ID, digits),
    )
    return list(cur.fetchall() or [])


def current_boat_name(cur, boat_id: int) -> Optional[str]:
    cur.execute(
        """
        SELECT boat_name FROM boat_names
        WHERE boat_id = %s
        ORDER BY last_seen_date DESC NULLS LAST, name_id DESC
        LIMIT 1
        """,
        (boat_id,),
    )
    row = cur.fetchone()
    return (row["boat_name"] if row else None) or None


def ensure_boat_name(cur, boat_id: int, name: str) -> str:
    cur_name = current_boat_name(cur, boat_id)
    if cur_name and cur_name.strip().casefold() == name.strip().casefold():
        cur.execute(
            """
            UPDATE boat_names SET last_seen_date = CURRENT_DATE,
              source_type = %s, source_regatta_id = %s
            WHERE name_id = (
              SELECT name_id FROM boat_names WHERE boat_id = %s
              ORDER BY last_seen_date DESC NULLS LAST, name_id DESC LIMIT 1
            )
            """,
            (SOURCE_TYPE, SOURCE_REGATTA, boat_id),
        )
        return "name_ok"
    cur.execute(
        """
        INSERT INTO boat_names (
          boat_id, boat_name, first_seen_date, last_seen_date,
          source_type, source_regatta_id, created_by, evidence
        ) VALUES (
          %s, %s, CURRENT_DATE, CURRENT_DATE,
          %s, %s, %s, %s
        )
        """,
        (
            boat_id,
            name,
            SOURCE_TYPE,
            SOURCE_REGATTA,
            CREATED_BY,
            Json({"sheet": "north_sails_j22_2026", "action": "set_name"}),
        ),
    )
    return "name_added" if not cur_name else "name_updated"


def ensure_bow(cur, boat_id: int, bow: int) -> str:
    bow_s = str(bow)
    cur.execute(
        """
        SELECT identifier_id, identifier_value, is_current
        FROM boat_identifiers
        WHERE boat_id = %s AND class_id = %s AND identifier_type = 'bow_no'
        ORDER BY is_current DESC NULLS LAST, identifier_id
        """,
        (boat_id, CLASS_ID),
    )
    rows = list(cur.fetchall() or [])
    current = next((r for r in rows if r.get("is_current")), rows[0] if rows else None)
    if current and str(current["identifier_value"]).strip() == bow_s and current.get("is_current"):
        return "bow_ok"
    # demote other current bows for this boat/class
    cur.execute(
        """
        UPDATE boat_identifiers
        SET is_current = FALSE, updated_at = NOW(), updated_by = %s
        WHERE boat_id = %s AND class_id = %s AND identifier_type = 'bow_no' AND is_current = TRUE
        """,
        (CREATED_BY, boat_id, CLASS_ID),
    )
    # if same value exists inactive, reactivate
    cur.execute(
        """
        SELECT identifier_id FROM boat_identifiers
        WHERE boat_id = %s AND class_id = %s AND identifier_type = 'bow_no'
          AND identifier_value = %s
        LIMIT 1
        """,
        (boat_id, CLASS_ID, bow_s),
    )
    hit = cur.fetchone()
    if hit:
        cur.execute(
            """
            UPDATE boat_identifiers
            SET is_current = TRUE, updated_at = NOW(), updated_by = %s,
                source_type = %s, source_regatta_id = %s
            WHERE identifier_id = %s
            """,
            (CREATED_BY, SOURCE_TYPE, SOURCE_REGATTA, hit["identifier_id"]),
        )
        return "bow_reactivated"
    cur.execute(
        """
        INSERT INTO boat_identifiers (
          boat_id, identifier_type, identifier_value, class_id,
          valid_from, is_current, source_type, source_regatta_id, confidence,
          created_by, evidence
        ) VALUES (
          %s, 'bow_no', %s, %s,
          CURRENT_DATE, TRUE, %s, %s, 100,
          %s, %s
        )
        """,
        (
            boat_id,
            bow_s,
            CLASS_ID,
            SOURCE_TYPE,
            SOURCE_REGATTA,
            CREATED_BY,
            Json({"sheet": "north_sails_j22_2026"}),
        ),
    )
    return "bow_added"


def ensure_sail(cur, boat_id: int, digits: str) -> str:
    cur.execute(
        """
        SELECT identifier_id, identifier_value, is_current
        FROM boat_identifiers
        WHERE boat_id = %s AND class_id = %s AND identifier_type = 'sail_number'
          AND REGEXP_REPLACE(identifier_value, '[^0-9]', '', 'g') = %s
        ORDER BY is_current DESC NULLS LAST
        LIMIT 1
        """,
        (boat_id, CLASS_ID, digits),
    )
    hit = cur.fetchone()
    if hit and hit.get("is_current"):
        # normalize stored value to digits-only (no SA prefix)
        if str(hit["identifier_value"]).strip() != digits:
            cur.execute(
                """
                UPDATE boat_identifiers
                SET identifier_value = %s, updated_at = NOW(), updated_by = %s,
                    source_type = %s, source_regatta_id = %s
                WHERE identifier_id = %s
                """,
                (digits, CREATED_BY, SOURCE_TYPE, SOURCE_REGATTA, hit["identifier_id"]),
            )
            return "sail_normalized"
        return "sail_ok"
    if hit:
        cur.execute(
            """
            UPDATE boat_identifiers
            SET is_current = TRUE, identifier_value = %s, updated_at = NOW(), updated_by = %s,
                source_type = %s, source_regatta_id = %s
            WHERE identifier_id = %s
            """,
            (digits, CREATED_BY, SOURCE_TYPE, SOURCE_REGATTA, hit["identifier_id"]),
        )
        return "sail_reactivated"
    # demote other current sails on this boat/class (unique index)
    cur.execute(
        """
        UPDATE boat_identifiers
        SET is_current = FALSE, updated_at = NOW(), updated_by = %s
        WHERE boat_id = %s AND class_id = %s AND identifier_type = 'sail_number' AND is_current = TRUE
        """,
        (CREATED_BY, boat_id, CLASS_ID),
    )
    cur.execute(
        """
        INSERT INTO boat_identifiers (
          boat_id, identifier_type, identifier_value, class_id,
          valid_from, is_current, source_type, source_regatta_id, confidence,
          created_by, evidence
        ) VALUES (
          %s, 'sail_number', %s, %s,
          CURRENT_DATE, TRUE, %s, %s, 100,
          %s, %s
        )
        """,
        (
            boat_id,
            digits,
            CLASS_ID,
            SOURCE_TYPE,
            SOURCE_REGATTA,
            CREATED_BY,
            Json({"sheet": "north_sails_j22_2026"}),
        ),
    )
    return "sail_added"


def create_boat(cur) -> int:
    cur.execute(
        """
        INSERT INTO boats (created_by, created_source, created_evidence, notes)
        VALUES (%s, %s, %s, %s)
        RETURNING boat_id
        """,
        (
            CREATED_BY,
            "manual",
            Json({"sheet": "north_sails_j22_2026"}),
            "Created for North Sails J22 Championships 2026 sheet",
        ),
    )
    return int(cur.fetchone()["boat_id"])


def merge_boats(cur, keep_id: int, drop_ids: list[int]) -> None:
    for drop_id in drop_ids:
        if drop_id == keep_id:
            continue
        # move identifiers (avoid unique conflicts on current sail)
        cur.execute(
            """
            UPDATE boat_identifiers
            SET is_current = FALSE, updated_at = NOW(), updated_by = %s,
                notes = COALESCE(notes,'') || ' [pre-merge demote]'
            WHERE boat_id = %s AND class_id = %s AND identifier_type = 'sail_number' AND is_current = TRUE
            """,
            (CREATED_BY, drop_id, CLASS_ID),
        )
        cur.execute(
            """
            UPDATE boat_identifiers SET boat_id = %s, updated_at = NOW(), updated_by = %s
            WHERE boat_id = %s
            """,
            (keep_id, CREATED_BY, drop_id),
        )
        cur.execute(
            """
            UPDATE boat_names SET boat_id = %s
            WHERE boat_id = %s
            """,
            (keep_id, drop_id),
        )
        cur.execute(
            """
            UPDATE boat_associations SET boat_id = %s, updated_at = NOW(), updated_by = %s
            WHERE boat_id = %s
            """,
            (keep_id, CREATED_BY, drop_id),
        )
        cur.execute("DELETE FROM boats WHERE boat_id = %s", (drop_id,))


def merge_same_sail_duplicates(cur, digits: str) -> Optional[int]:
    rows = find_j22_boats_for_sail(cur, digits)
    if not rows:
        return None
    boat_ids = []
    for r in rows:
        if r["boat_id"] not in boat_ids:
            boat_ids.append(r["boat_id"])
    keep = boat_ids[0]
    if len(boat_ids) > 1:
        merge_boats(cur, keep, boat_ids[1:])
        print(f"  MERGED sail {digits}: keep boat {keep}, dropped {boat_ids[1:]}")
    return keep


def fix_one(cur, rank: int, bow: int, sail: str, boat_name: str) -> dict:
    digits = sail_digits(sail)
    actions = []
    boat_id = merge_same_sail_duplicates(cur, digits)
    if boat_id is None:
        boat_id = create_boat(cur)
        actions.append(f"boat_created:{boat_id}")
        actions.append(ensure_sail(cur, boat_id, digits))
    else:
        actions.append(ensure_sail(cur, boat_id, digits))
    actions.append(ensure_boat_name(cur, boat_id, boat_name))
    actions.append(ensure_bow(cur, boat_id, bow))
    return {
        "rank": rank,
        "bow": bow,
        "sail": digits,
        "boat_name": boat_name,
        "boat_id": boat_id,
        "actions": actions,
    }


def report_dup_names(cur) -> list[dict]:
    cur.execute(
        """
        SELECT LOWER(TRIM(bn.boat_name)) AS n,
               COUNT(DISTINCT bi.boat_id) AS boats,
               array_agg(DISTINCT REGEXP_REPLACE(bi.identifier_value, '[^0-9]', '', 'g')) AS sails,
               array_agg(DISTINCT bi.boat_id) AS boat_ids
        FROM boat_identifiers bi
        JOIN LATERAL (
          SELECT boat_name FROM boat_names n WHERE n.boat_id = bi.boat_id
          ORDER BY last_seen_date DESC NULLS LAST, name_id DESC LIMIT 1
        ) bn ON TRUE
        WHERE bi.class_id = %s AND bi.identifier_type = 'sail_number' AND bi.is_current = TRUE
          AND bn.boat_name IS NOT NULL AND TRIM(bn.boat_name) <> ''
        GROUP BY 1
        HAVING COUNT(DISTINCT bi.boat_id) > 1
        ORDER BY boats DESC, n
        """,
        (CLASS_ID,),
    )
    return [dict(r) for r in cur.fetchall()]


def verify(cur) -> list[dict]:
    out = []
    for rank, bow, sail, boat_name in SHEET:
        digits = sail_digits(sail)
        rows = find_j22_boats_for_sail(cur, digits)
        boat_id = rows[0]["boat_id"] if rows else None
        name = current_boat_name(cur, boat_id) if boat_id else None
        cur.execute(
            """
            SELECT identifier_value FROM boat_identifiers
            WHERE boat_id = %s AND class_id = %s AND identifier_type = 'bow_no' AND is_current = TRUE
            LIMIT 1
            """,
            (boat_id, CLASS_ID),
        ) if boat_id else None
        bow_row = cur.fetchone() if boat_id else None
        bow_v = bow_row["identifier_value"] if bow_row else None
        ok = (
            boat_id is not None
            and name is not None
            and name.strip().casefold() == boat_name.strip().casefold()
            and str(bow_v) == str(bow)
            and len({r["boat_id"] for r in rows}) == 1
        )
        out.append(
            {
                "rank": rank,
                "ok": ok,
                "boat_id": boat_id,
                "sail": digits,
                "bow_db": bow_v,
                "bow_want": bow,
                "name_db": name,
                "name_want": boat_name,
                "sail_boat_ids": sorted({r["boat_id"] for r in rows}),
            }
        )
    return out


def main() -> int:
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    try:
        with conn.cursor() as cur:
            # fix boat_names update path: detect columns
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name='boat_names'
                """
            )
            bn_cols = {r["column_name"] for r in cur.fetchall()}
            print("boat_names cols", sorted(bn_cols))

            results = []
            for rank, bow, sail, boat_name in SHEET:
                print(f"fix {rank} {sail} bow {bow} {boat_name}")
                results.append(fix_one(cur, rank, bow, sail, boat_name))

            dups = report_dup_names(cur)
            print("\nDuplicate J22 names after fix (different sails = keep separate):")
            for d in dups:
                sails = d.get("sails") or []
                # only merge candidates already handled; report remaining
                print(f"  {d['n']}: boats={d['boats']} sails={sails} ids={d['boat_ids']}")

            ver = verify(cur)
            ok_n = sum(1 for v in ver if v["ok"])
            print(f"\nVERIFY {ok_n}/16 OK")
            for v in ver:
                if not v["ok"]:
                    print("  FAIL", v)
            for r in results:
                print("  ", r)
        conn.commit()
    finally:
        conn.close()
    return 0 if ok_n == 16 else 1


if __name__ == "__main__":
    raise SystemExit(main())
