"""
Fill regattas.host_club_code from clubs.club_abbrev when host_club_id is set and code is still empty.

Used by api.py, header_validation (revalidate), and ingestion scripts — no circular imports.
"""
from __future__ import annotations


def persist_regatta_host_club_code_from_clubs_cur(cur, regatta_id: str) -> None:
    """Set host_club_code from the host club row when column exists and code is NULL/blank."""
    if not regatta_id:
        return
    try:
        cur.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'regattas' AND column_name = 'host_club_code'
            LIMIT 1
            """
        )
        if not cur.fetchone():
            return
    except Exception:
        return
    try:
        cur.execute(
            """
            UPDATE regattas r
            SET host_club_code = NULLIF(TRIM(c.club_abbrev), '')
            FROM clubs c
            WHERE c.club_id = r.host_club_id
              AND r.regatta_id = %s
              AND r.host_club_id IS NOT NULL
              AND NULLIF(TRIM(COALESCE(r.host_club_code, '')), '') IS NULL
            """,
            (regatta_id,),
        )
    except Exception as e:
        print(f"[persist_regatta_host_club_code_from_clubs_cur] {regatta_id}: {e}")
