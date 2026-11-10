#!/usr/bin/env python3
"""Align /stats overview counts with homepage + /sailors + /regattas (_get_site_stats)."""
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
t = path.read_text(encoding="utf-8")

if "public_stats_full_v2" in t:
    print("already patched")
    sys.exit(0)

t = t.replace("public_stats_full_v1", "public_stats_full_v2", 1)

old_doc = '''    """Aggregated counts and top lists for public /stats page. Uses existing tables only. Lightweight, limited rows.
    Data validation: total_regattas = COUNT(regattas), total_races = COUNT(results). No placeholders; totals match canonical DB."""'''

new_doc = '''    """Aggregated counts and top lists for public /stats page.

    Overview card totals match homepage /api/site-stats (_get_site_stats): active sailors,
    regattas with raced results, races sailed (raced=TRUE), classes sailed — same sources
    as /sailors search and /regattas with-counts. Cached 3min."""'''

if old_doc not in t:
    raise SystemExit("docstring block not found")
t = t.replace(old_doc, new_doc, 1)

old_counts = '''        # Total sailors: distinct helm + crew from results
        if table_exists("results"):
            cur.execute("""
                SELECT COUNT(DISTINCT sailor_id) AS n FROM (
                    SELECT helm_sa_sailing_id::text AS sailor_id FROM results WHERE helm_sa_sailing_id IS NOT NULL
                    UNION ALL
                    SELECT crew_sa_sailing_id::text AS sailor_id FROM results WHERE crew_sa_sailing_id IS NOT NULL
                ) u
            """)
            row = cur.fetchone()
            out["total_sailors"] = int(row["n"]) if row and row.get("n") is not None else 0
        if table_exists("regattas"):
            cur.execute("SELECT COUNT(*) AS n FROM regattas")
            row = cur.fetchone()
            out["total_regattas"] = int(row["n"]) if row and row.get("n") is not None else 0
        if table_exists("results"):
            cur.execute("SELECT COUNT(*) AS n FROM results")
            row = cur.fetchone()
            out["total_races"] = int(row["n"]) if row and row.get("n") is not None else 0
        if table_exists("classes"):
            cur.execute("SELECT COUNT(*) AS n FROM classes")
            row = cur.fetchone()
            out["total_classes"] = int(row["n"]) if row and row.get("n") is not None else 0
        if table_exists("clubs"):
            cur.execute("SELECT COUNT(*) AS n FROM clubs")
            row = cur.fetchone()
            out["total_clubs"] = int(row["n"]) if row and row.get("n") is not None else 0
        if table_exists("results"):'''

new_counts = '''        # Overview cards: same 4 metrics as homepage (/api/site-stats) — updates when results/SAS IDs added
        site = _get_site_stats()
        out["total_sailors"] = int(site.get("active_sailors") or 0)
        out["total_regattas"] = int(site.get("regattas_sailed") or 0)
        out["total_races"] = int(site.get("races_raced") or 0)
        out["total_classes"] = int(site.get("classes_sailed") or 0)
        if table_exists("clubs"):
            cur.execute("""
                SELECT COUNT(*) AS n FROM clubs
                WHERE ((club_fullname IS NOT NULL AND TRIM(club_fullname) != '')
                   OR (club_abbrev IS NOT NULL AND TRIM(club_abbrev) != ''))
                  AND lower(trim(COALESCE(club_abbrev, ''))) != 'unassigned'
                  AND lower(trim(COALESCE(club_fullname, ''))) != 'unassigned'
            """)
            row = cur.fetchone()
            out["total_clubs"] = int(row["n"]) if row and row.get("n") is not None else 0
        if table_exists("results"):'''

if old_counts not in t:
    raise SystemExit("count queries block not found")
t = t.replace(old_counts, new_counts, 1)

old_labels = 'labels = ("Total Sailors", "Total Regattas", "Total Races", "Total Classes", "Total Clubs")'
new_labels = 'labels = ("Active Sailors", "Regattas with Results", "Races Sailed", "Classes Sailed", "Clubs")'
if old_labels not in t:
    raise SystemExit("labels line not found")
t = t.replace(old_labels, new_labels, 1)

path.write_text(t, encoding="utf-8")
print("patched stats counts alignment")
