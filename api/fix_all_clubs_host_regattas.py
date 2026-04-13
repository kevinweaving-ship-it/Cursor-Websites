#!/usr/bin/env python3
"""Set host_club_id for regattas where event_name contains club abbrev or name
   but host_club_id is NULL or wrong. Universal for ALL clubs.
   Phase 1: club abbrev/name match. Phase 2: event_name pattern -> club mapping.
   Run: python3 fix_all_clubs_host_regattas.py
"""
import os
import psycopg2
import psycopg2.extras

DB_URL = os.getenv("DB_URL", "postgresql://sailors_user:change_me_strong@localhost:5432/sailors_master")

# Phase 2: event_name pattern (UPPER) -> club_abbrev for regattas with NULL host
EVENT_PATTERN_TO_CLUB = [
    (r"%MPUMALANGA%", "WYAC"),       # Witbank Yacht Club, Mpumalanga
    (r"%WEST COAST%", "TCC"),        # Table Bay Cruising Club
    (r"%FS PROVINCIALS%", "DAC"),   # Deneysville, Free State
    (r"%FS CHAMPS%", "DAC"),
    (r"%FREE STATE%", "DAC"),
    (r"%NKS GRAND PRIX%", "RCYC"),  # National Keelboat Series
    (r"%TRIPLE CROWN%", "HMYC"),    # Henley Midmar series
    (r"%STADT 23 WC%", "RCYC"),     # Western Cape provincials
    (r"%GP14 NATIONAL%", "RCYC"),
    (r"%FLYING FIFTEEN NATIONAL%", "RCYC"),
    (r"%SOLING NATIONAL%", "RCYC"),
    (r"%J22 NATIONAL%", "PYC"),     # Point Yacht Club, common J22 venue
    (r"%OPTIMIST FS%", "DAC"),
]

def run_fix_host_clubs(conn=None, verbose=True):
    """Fix host_club_id for regattas (NULL or wrong). Use conn if provided, else create.
    Returns count of regattas updated. Call after new regatta results are imported."""
    own_conn = conn is None
    if conn is None:
        conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT club_id, club_abbrev, club_fullname
        FROM clubs
        WHERE club_id IS NOT NULL
          AND (club_abbrev IS NOT NULL AND TRIM(club_abbrev) != ''
               OR club_fullname IS NOT NULL AND TRIM(club_fullname) != '')
          AND UPPER(TRIM(COALESCE(club_abbrev, ''))) NOT IN ('UNK', 'NONE', '')
    """)
    clubs = cur.fetchall()
    total_updated = 0

    for c in clubs:
        cid = c["club_id"]
        ab = (c["club_abbrev"] or "").strip().upper()
        fn = (c["club_fullname"] or "").strip()

        if not ab and not fn:
            continue

        # Build search patterns: abbrev + first word of full name (e.g. Hermanus, Zeekoe, ZVYC)
        patterns = []
        if ab:
            patterns.append(ab)
        if fn:
            words = [w for w in fn.split() if len(w) > 2 and w.lower() not in ("yacht", "club", "sailing", "bay", "the")]
            if words:
                patterns.append(words[0].upper())

        if not patterns:
            continue

        # Fix regattas where event_name matches club but host_club_id is NULL or wrong
        placeholders = " OR ".join(["UPPER(COALESCE(event_name, '')) LIKE %s" for _ in patterns])
        params = [f"%{p}%" for p in patterns]
        params.append(cid)

        cur.execute(f"""
            SELECT regatta_id, event_name, host_club_id
            FROM regattas
            WHERE event_name IS NOT NULL
              AND (host_club_id IS NULL OR host_club_id != %s)
              AND ({placeholders})
        """, [cid] + params[:-1])
        to_fix = cur.fetchall()

        if not to_fix:
            continue

        cur.execute(f"""
            UPDATE regattas
            SET host_club_id = %s
            WHERE event_name IS NOT NULL
              AND (host_club_id IS NULL OR host_club_id != %s)
              AND ({placeholders})
        """, [cid, cid] + params[:-1])
        n = cur.rowcount
        total_updated += n
        if verbose:
            print(f"{ab or fn[:20]}: updated {n} regattas")

    # Phase 2: event_name pattern -> club for NULL host_club_id
    cur.execute("SELECT club_id, UPPER(TRIM(club_abbrev)) AS ab FROM clubs WHERE club_abbrev IS NOT NULL")
    abbrev_to_id = {r["ab"]: r["club_id"] for r in cur.fetchall()}

    for pattern, club_abbrev in EVENT_PATTERN_TO_CLUB:
        cid = abbrev_to_id.get(club_abbrev.upper())
        if not cid:
            continue
        cur.execute("""
            UPDATE regattas SET host_club_id = %s
            WHERE host_club_id IS NULL AND event_name IS NOT NULL
              AND UPPER(event_name) LIKE %s
        """, (cid, pattern))
        n = cur.rowcount
        if n:
            total_updated += n
            if verbose:
                print(f"pattern {pattern[:30]}: -> {club_abbrev} updated {n}")

    conn.commit()
    if verbose:
        print(f"\nTotal updated: {total_updated}")
    cur.close()
    if own_conn:
        conn.close()
    return total_updated


def main():
    run_fix_host_clubs(verbose=True)


if __name__ == "__main__":
    main()
