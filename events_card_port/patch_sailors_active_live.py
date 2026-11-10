#!/usr/bin/env python3
"""Patch LIVE api.py: /api/search?active=1 + /sailors page copy."""
from pathlib import Path
import sys

path = Path(sys.argv[1])
t = path.read_text(encoding="utf-8")

if "active_on = int(active or 0) == 1" not in t:
    old_sig = (
        '    hub: int = Query(0, description="1 = landing/hub search: higher cap, multi-word fuzzy on names"),\n'
        '):\n'
        '    """Search for members (SA IDs and Temp IDs) with last regatta info"""'
    )
    new_sig = (
        '    hub: int = Query(0, description="1 = landing/hub search: higher cap, multi-word fuzzy on names"),\n'
        '    active: int = Query(0, description="1 = only sailors with raced results on dated regattas (stats active count)"),\n'
        '):\n'
        '    """Search for members (SA IDs and Temp IDs) with last regatta info"""'
    )
    if old_sig not in t:
        raise SystemExit("api_search signature not found")
    t = t.replace(old_sig, new_sig, 1)

    old_limit = (
        "    max_cap = 500 if int(hub or 0) == 1 else 200\n"
        "    limit = min(max(1, int(limit or 200)), max_cap)\n"
        "    \n"
        "    rows = []"
    )
    new_limit = (
        "    max_cap = 500 if int(hub or 0) == 1 else 200\n"
        "    limit = min(max(1, int(limit or 200)), max_cap)\n"
        "    active_on = int(active or 0) == 1\n"
        "    \n"
        "    rows = []"
    )
    if old_limit not in t:
        raise SystemExit("api_search limit block not found")
    t = t.replace(old_limit, new_limit, 1)

    anchor = (
        "                if age_over:\n"
        "                    conditions.append(\"s.year_of_birth < %s\")\n"
        "                    params.append(current_year - age_over)\n"
        "                \n"
        "                # Check if we should skip SA ID query (if searching for temp IDs only)"
    )
    insert = (
        "                if age_over:\n"
        "                    conditions.append(\"s.year_of_birth < %s\")\n"
        "                    params.append(current_year - age_over)\n"
        "\n"
        "                if active_on:\n"
        "                    conditions.append(\"\"\"\n"
        "                        EXISTS (\n"
        "                            SELECT 1 FROM public.results r\n"
        "                            JOIN public.regattas reg ON reg.regatta_id = r.regatta_id\n"
        "                            WHERE r.raced = TRUE\n"
        "                              AND (reg.end_date IS NOT NULL OR reg.start_date IS NOT NULL)\n"
        "                              AND (\n"
        "                                r.helm_sa_sailing_id::text = s.sa_sailing_id::text\n"
        "                                OR r.crew_sa_sailing_id::text = s.sa_sailing_id::text\n"
        "                              )\n"
        "                        )\n"
        "                    \"\"\")\n"
        "                \n"
        "                # Check if we should skip SA ID query (if searching for temp IDs only)"
    )
    if anchor not in t:
        raise SystemExit("active filter anchor not found")
    t = t.replace(anchor, insert, 1)

    old_temp = """                should_show_temp_ids = (
                    (sas_id and (sas_id.strip().upper() == "T" or sas_id.upper().startswith("TMP"))) or
                    (not q or q.strip() == "" or q.strip().upper() == "T" or q.upper().startswith("TMP"))
                )"""
    new_temp = """                should_show_temp_ids = (
                    not active_on
                    and (
                        (sas_id and (sas_id.strip().upper() == "T" or sas_id.upper().startswith("TMP")))
                        or (not q or q.strip() == "" or q.strip().upper() == "T" or q.upper().startswith("TMP"))
                    )
                )"""
    if old_temp not in t:
        raise SystemExit("should_show_temp_ids block not found")
    t = t.replace(old_temp, new_temp, 1)
    print("patched api_search active=1")
else:
    print("api_search active=1 already present")

old_about = (
    '        "Search all South African sailors with complete regatta results, rankings, and performance history. "\n'
    '        "SailingSA is the most comprehensive South African sailing results database for sailors."'
)
new_about = (
    '        "Search active South African sailors — those with regatta results on SailingSA. "\n'
    '        "This is not the full SA Sailing ID register; only sailors who have raced appear here."'
)
if old_about in t:
    t = t.replace(old_about, new_about, 1)
    print("patched sailors about text")
elif new_about in t:
    print("sailors about text already patched")
else:
    print("WARN: sailors about text anchor not found")

t = t.replace(
    '<script src="/js/hub-sailor-directory.js?v=20260823dir3"></script>',
    '<script src="/js/hub-sailor-directory.js?v=20260823dir4"></script>',
)
t = t.replace(
    '<p class="sailor-directory-hint" id="sailors-hint">Loading sailors…</p>',
    '<p class="sailor-directory-hint" id="sailors-hint">Search active sailors by name, SA ID, club, or class.</p>',
)

path.write_text(t, encoding="utf-8")
print("done", path)
