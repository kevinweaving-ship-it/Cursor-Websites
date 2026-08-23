#!/usr/bin/env python3
"""Replace slow active=1 EXISTS with INNER JOIN for /api/search."""
from pathlib import Path
import sys

path = Path(sys.argv[1])
t = path.read_text(encoding="utf-8")

ACTIVE_JOIN = """
                    active_join = ""
                    if active_on:
                        active_join = \"\"\"
                            INNER JOIN (
                                SELECT DISTINCT sailor_id FROM (
                                    SELECT r.helm_sa_sailing_id::text AS sailor_id
                                    FROM public.results r
                                    JOIN public.regattas reg ON reg.regatta_id = r.regatta_id
                                    WHERE r.raced = TRUE
                                      AND r.helm_sa_sailing_id IS NOT NULL AND r.helm_sa_sailing_id::text != ''
                                      AND (reg.end_date IS NOT NULL OR reg.start_date IS NOT NULL)
                                    UNION
                                    SELECT r.crew_sa_sailing_id::text AS sailor_id
                                    FROM public.results r
                                    JOIN public.regattas reg ON reg.regatta_id = r.regatta_id
                                    WHERE r.raced = TRUE
                                      AND r.crew_sa_sailing_id IS NOT NULL AND r.crew_sa_sailing_id::text != ''
                                      AND (reg.end_date IS NOT NULL OR reg.start_date IS NOT NULL)
                                ) u
                            ) active_sailors ON active_sailors.sailor_id = s.sa_sailing_id::text
                        \"\"\"
"""

OLD_EXISTS = """                if active_on:
                    conditions.append(\"\"\"
                        EXISTS (
                            SELECT 1 FROM public.results r
                            JOIN public.regattas reg ON reg.regatta_id = r.regatta_id
                            WHERE r.raced = TRUE
                              AND (reg.end_date IS NOT NULL OR reg.start_date IS NOT NULL)
                              AND (
                                r.helm_sa_sailing_id::text = s.sa_sailing_id::text
                                OR r.crew_sa_sailing_id::text = s.sa_sailing_id::text
                              )
                        )
                    \"\"\")
                
                # Check if we should skip SA ID query"""

NEW_BLOCK = ACTIVE_JOIN + """
                
                # Check if we should skip SA ID query"""

if "active_join = \"\"\"" in t and "active_sailors ON" in t:
    print("active JOIN already present")
elif OLD_EXISTS in t:
    t = t.replace(OLD_EXISTS, NEW_BLOCK, 1)
    # inject {active_join} before sail_boat_join in FROM
    t = t.replace(
        "                    sail_boat_join = \"\"",
        "                    sail_boat_join = \"\"\n" + ACTIVE_JOIN.strip().split("\n", 1)[1] if False else "",
        1,
    )
    # Simpler: add active_join var after sail_boat_params init block
    anchor = "                    # Build sail/boat name search JOIN if needed (replaces EXISTS clause)\n                    sail_boat_join = \"\""
    if anchor not in t:
        raise SystemExit("sail_boat anchor not found")
    insert = """                    # Active sailors only: join pre-filtered set (faster than per-row EXISTS)
                    active_join = ""
                    if active_on:
                        active_join = \"\"\"
                            INNER JOIN (
                                SELECT DISTINCT sailor_id FROM (
                                    SELECT r.helm_sa_sailing_id::text AS sailor_id
                                    FROM public.results r
                                    JOIN public.regattas reg ON reg.regatta_id = r.regatta_id
                                    WHERE r.raced = TRUE
                                      AND r.helm_sa_sailing_id IS NOT NULL AND r.helm_sa_sailing_id::text != ''
                                      AND (reg.end_date IS NOT NULL OR reg.start_date IS NOT NULL)
                                    UNION
                                    SELECT r.crew_sa_sailing_id::text AS sailor_id
                                    FROM public.results r
                                    JOIN public.regattas reg ON reg.regatta_id = r.regatta_id
                                    WHERE r.raced = TRUE
                                      AND r.crew_sa_sailing_id IS NOT NULL AND r.crew_sa_sailing_id::text != ''
                                      AND (reg.end_date IS NOT NULL OR reg.start_date IS NOT NULL)
                                ) u
                            ) active_sailors ON active_sailors.sailor_id = s.sa_sailing_id::text
                        \"\"\"
                    # Build sail/boat name search JOIN if needed (replaces EXISTS clause)
                    sail_boat_join = \"\""""
    t = t.replace(anchor, insert, 1)
    t = t.replace(OLD_EXISTS, "\n                # active_on uses active_join INNER JOIN (see above)\n                \n                # Check if we should skip SA ID query", 1)
    t = t.replace(
        "FROM public.sas_id_personal s\n                            {sail_boat_join}",
        "FROM public.sas_id_personal s\n                            {active_join}\n                            {sail_boat_join}",
    )
    t = t.replace(
        "FROM public.sas_id_personal s\n                        {sail_boat_join}",
        "FROM public.sas_id_personal s\n                        {active_join}\n                        {sail_boat_join}",
    )
    print("patched active INNER JOIN")
else:
    raise SystemExit("active EXISTS block not found")

path.write_text(t, encoding="utf-8")
print("done", path)
