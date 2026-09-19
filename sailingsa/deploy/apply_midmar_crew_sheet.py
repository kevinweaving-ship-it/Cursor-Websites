#!/usr/bin/env python3
"""Add Midmar Cup crews + new boats. Do not invent SAS IDs.

Helm is the Skipper column when that person has a unique SAS ID.
The Name-column person is crew only if listed as Crew 1/2.
Never write the helm name into crew fields.
Leave clubs that are already correct, marked ?, or not in clubs.
"""
from __future__ import annotations

import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
BLOCK = "2026-09-19-hmyc-midmar-cup:hunter-19"
CLASS_NAME = "Hunter 19"
CLASS_ID = 209


def person(sid, name):
    return {"sid": sid, "name": name}


def key_name(name: str) -> str:
    return " ".join((name or "").lower().split())


# find_sids = existing row keys (current and/or new helm).
# club None = leave existing club.
BOATS = [
    {
        "rank": 1,
        "find_sids": [1218],
        "helm": person(1218, "Paul Changuion"),
        "crew": [person(None, "Tamara Pretorius"), person(None, "Chiara Delvaux")],
        "club": ("BYC", 86),
    },
    {
        "rank": 2,
        "find_sids": [177],
        "helm": person(177, "Craig Millar"),
        "crew": [person(None, "Erin Millar"), person(None, "Lia Millar")],
        "club": None,  # ORYC not in clubs; keep HMYC
    },
    {
        "rank": 3,
        "find_sids": [1221],
        "helm": person(1221, "Tony Cockerill"),
        "crew": [person(15510, "Cailee Pretorius"), person(None, "Mat Strydom")],
        "club": None,  # HMYC? keep HMYC
    },
    {
        "rank": 4,
        "find_sids": [14790],
        "helm": person(14790, "Megan Gauld"),
        "crew": [],
        "club": None,  # Zululand? keep ELYC
    },
    {
        "rank": 5,
        "find_sids": [23999, 22984],
        "helm": person(22984, "Paige Smith"),
        "crew": [person(23999, "Bryan Paxman"), person(25125, "Ziva Filday")],
        "club": None,  # EUYC not in clubs; keep DAC
    },
    {
        "rank": 6,
        "find_sids": [8444, 15579],
        "helm": person(15579, "Daniela Cantarelli"),
        "crew": [person(None, "Vice Sommerville"), person(None, "Tatiana")],
        "club": None,  # PRSC not in clubs; keep HMYC
    },
    {
        "rank": 7,
        "find_sids": [729],
        "helm": person(729, "Luke Wagner"),
        "crew": [],
        "club": None,  # WYC not in clubs; keep PYC
    },
    {
        "rank": 8,
        "find_sids": [21715],
        "helm": person(21715, "Gust Funke"),
        "crew": [],
        "club": None,  # already PYC
    },
    {
        "rank": 9,
        "find_sids": [8683],
        "helm": person(8683, "Hayden Miller"),
        "crew": [person(21172, "Timothy Weaving"), person(3709, "Howard Leoto")],
        "club": None,  # RNYC? keep RNYC
        "keep_sail": True,
    },
    {
        "rank": 10,
        "find_sids": [18659],
        "helm": person(18659, "Penny Macpherson"),
        "crew": [person(None, "Luke Furtis"), person(None, "Ethan")],
        "club": ("VYC", 70),
    },
    {
        "rank": 11,
        "find_sids": [19130],
        "helm": person(19130, "Jethro Milne"),
        "crew": [person(15791, "Matthew Macpherson"), person(28155, "Caitlin Macpherson")],
        "club": ("POYC", 139),
    },
    {
        "rank": 12,
        "find_sids": [2348, 14193],
        "helm": person(14193, "Shalin Naidoo"),
        "crew": [person(None, "Aaron Maharaj"), person(2348, "Craig Deverson")],
        "club": ("KSYC", 106),
    },
]


def unique_sas(cur, sid: int, expect_fn: str, expect_ln: str) -> None:
    cur.execute(
        """
        SELECT sa_sailing_id::text, full_name, first_name, last_name
        FROM sas_id_personal
        WHERE sa_sailing_id::text = %s
        """,
        (str(sid),),
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"REFUSE: SAS {sid} missing")
    fn = (row[2] or "").strip().lower()
    ln = (row[3] or "").strip().lower()
    if fn != expect_fn.lower() or ln != expect_ln.lower():
        raise SystemExit(f"REFUSE: SAS {sid} is {row[1]!r}, not {expect_fn} {expect_ln}")
    cur.execute(
        """
        SELECT sa_sailing_id::text FROM sas_id_personal
        WHERE first_name ILIKE %s AND last_name ILIKE %s
        """,
        (expect_fn, expect_ln),
    )
    ids = {r[0] for r in cur.fetchall()}
    if ids != {str(sid)}:
        raise SystemExit(f"REFUSE: {expect_fn} {expect_ln} not unique: {ids}")
    print("SAS_OK", sid, row[1])


def crew_without_helm(helm: dict, crew: list) -> list:
    hk = key_name(helm["name"])
    hid = helm.get("sid")
    out = []
    seen = {hk}
    for p in crew:
        nk = key_name(p["name"])
        if hid and p.get("sid") == hid:
            print("SKIP_DUP_SID", p["name"], hid)
            continue
        if nk == hk:
            print("SKIP_DUP_NAME", p["name"])
            continue
        if nk in seen:
            print("SKIP_DUP_CREW", p["name"])
            continue
        seen.add(nk)
        out.append(p)
    return out


def apply() -> int:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()

    checks = [
        (1218, "Paul", "Changuion"),
        (177, "Craig", "Millar"),
        (1221, "Tony", "Cockerill"),
        (14790, "Megan", "Gauld"),
        (23999, "Bryan", "Paxman"),
        (22984, "Paige", "Smith"),
        (25125, "Ziva", "Filday"),
        (8444, "Nick", "Somerville"),
        (15579, "Daniela", "Cantarelli"),
        (729, "Luke", "Wagner"),
        (21715, "Gust", "Funke"),
        (8683, "Hayden", "Miller"),
        (21172, "Timothy", "Weaving"),
        (3709, "Howard", "Leoto"),
        (15510, "Cailee", "Pretorius"),
        (18659, "Penny", "Macpherson"),
        (19130, "Jethro", "Milne"),
        (15791, "Matthew", "Macpherson"),
        (28155, "Caitlin", "Macpherson"),
        (2348, "Craig", "Deverson"),
        (14193, "Shalin", "Naidoo"),
    ]
    for sid, fn, ln in checks:
        unique_sas(cur, sid, fn, ln)

    cur.execute(
        "SELECT club_id, club_abbrev FROM clubs WHERE club_abbrev = ANY(%s)",
        (["BYC", "VYC", "POYC", "KSYC", "HMYC", "RNYC", "PYC", "DAC", "ELYC"],),
    )
    clubs = {r[1]: r[0] for r in cur.fetchall()}
    print("CLUBS", clubs)
    for code, cid in (("BYC", 86), ("VYC", 70), ("POYC", 139), ("KSYC", 106)):
        if clubs.get(code) != cid:
            raise SystemExit(f"REFUSE: club {code} {cid} vs {clubs.get(code)}")

    for boat in BOATS:
        helm = boat["helm"]
        crew = crew_without_helm(helm, boat["crew"])
        crew1 = crew[0] if crew else None
        crew2 = crew[1] if len(crew) > 1 else None
        # Store one person per field. The Event URL joins crew_name + crew2_name.
        crew_disp = crew1["name"] if crew1 else None
        if crew1 and key_name(helm["name"]) == key_name(crew1["name"]):
            raise SystemExit(f"REFUSE: helm duplicated in crew1: {helm['name']}")
        if crew2 and key_name(helm["name"]) == key_name(crew2["name"]):
            raise SystemExit(f"REFUSE: helm duplicated in crew2: {helm['name']}")
        if crew1 and crew2 and key_name(crew1["name"]) == key_name(crew2["name"]):
            raise SystemExit(f"REFUSE: crew1/crew2 duplicate: {crew1['name']}")

        result_id = None
        for sid in boat["find_sids"]:
            cur.execute(
                """
                SELECT result_id FROM results
                WHERE regatta_id=%s AND helm_sa_sailing_id=%s
                ORDER BY result_id LIMIT 1
                """,
                (RID, sid),
            )
            row = cur.fetchone()
            if row:
                result_id = row[0]
                break

        club = boat.get("club")
        sets = {
            "block_id": BLOCK,
            "rank": boat["rank"],
            "class_original": CLASS_NAME,
            "class_canonical": CLASS_NAME,
            "class_id": CLASS_ID,
            "fleet_label": CLASS_NAME,
            "helm_name": helm["name"],
            "helm_sa_sailing_id": helm["sid"],
            "crew_name": crew_disp,
            "crew_sa_sailing_id": crew1["sid"] if crew1 else None,
            "crew2_name": crew2["name"] if crew2 else None,
            "crew2_sa_sailing_id": crew2["sid"] if crew2 else None,
            "raced": True,
            "result_status": "Provisional",
        }
        if club:
            sets["club_raw"] = club[0]
            sets["club_id"] = club[1]

        if result_id:
            assignments = ", ".join(f"{k}=%s" for k in sets)
            cur.execute(
                f"UPDATE results SET {assignments} WHERE result_id=%s",
                list(sets.values()) + [result_id],
            )
            print("UPDATE", boat["rank"], helm["name"], "crew=", crew_disp, crew2["name"] if crew2 else None, "result_id", result_id)
        else:
            sets.update(
                {
                    "regatta_id": RID,
                    "races_sailed": 0,
                    "discard_count": 0,
                    "race_scores": psycopg2.extras.Json({}),
                }
            )
            cols = list(sets)
            cur.execute(
                f"INSERT INTO results ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                list(sets.values()),
            )
            print("INSERT", boat["rank"], helm["name"], "crew=", crew_disp, crew2["name"] if crew2 else None)

        # entries: one row per helm SAS
        cur.execute(
            "SELECT entry_id FROM entries WHERE regatta_id=%s AND helm_sas_id = ANY(%s)",
            (RID, [str(s) for s in boat["find_sids"]]),
        )
        erows = cur.fetchall()
        club_code = club[0] if club else None
        crew_sid = str(crew1["sid"]) if crew1 and crew1["sid"] else None
        if erows:
            if club_code:
                cur.execute(
                    """
                    UPDATE entries
                    SET helm_sas_id=%s, crew_sas_id=%s, block_id=%s, verified=TRUE, club_code=%s
                    WHERE entry_id=%s
                    """,
                    (str(helm["sid"]), crew_sid, BLOCK, club_code, erows[0][0]),
                )
            else:
                cur.execute(
                    """
                    UPDATE entries
                    SET helm_sas_id=%s, crew_sas_id=%s, block_id=%s, verified=TRUE
                    WHERE entry_id=%s
                    """,
                    (str(helm["sid"]), crew_sid, BLOCK, erows[0][0]),
                )
            for extra in erows[1:]:
                cur.execute("DELETE FROM entries WHERE entry_id=%s", (extra[0],))
            print("ENTRY_UPDATE", helm["name"], club_code or "keep-club")
        else:
            ecols = ["regatta_id", "block_id", "helm_sas_id", "verified"]
            evals = [RID, BLOCK, str(helm["sid"]), True]
            if crew_sid:
                ecols.append("crew_sas_id")
                evals.append(crew_sid)
            if club_code:
                ecols.append("club_code")
                evals.append(club_code)
            cur.execute(
                f"INSERT INTO entries ({', '.join(ecols)}) VALUES ({', '.join(['%s'] * len(evals))})",
                evals,
            )
            print("ENTRY_INSERT", helm["name"], club_code)

    cur.execute(
        "UPDATE regatta_blocks SET entries_raced=%s WHERE block_id=%s",
        (len(BOATS), BLOCK),
    )
    print("BLOCK_ENTRIES", len(BOATS))
    conn.commit()

    print("\n===== RESULTS =====")
    cur.execute(
        """
        SELECT rank, helm_name, helm_sa_sailing_id, crew_name, crew2_name,
               crew_sa_sailing_id, crew2_sa_sailing_id, club_raw, club_id,
               sail_number, boat_name
        FROM results WHERE regatta_id=%s
        ORDER BY COALESCE(rank, 99999), result_id
        """,
        (RID,),
    )
    rows = cur.fetchall()
    for r in rows:
        print(r)
        helm = key_name(r[1] or "")
        c1 = key_name(r[3] or "")
        c2 = key_name(r[4] or "")
        if helm and helm in {c1, c2}:
            raise SystemExit(f"REFUSE_AFTER: helm duplicated in crew {r}")
        if c1 and c1 == c2:
            raise SystemExit(f"REFUSE_AFTER: crew1/crew2 duplicate {r}")
    print("n=", len(rows))
    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(apply())
