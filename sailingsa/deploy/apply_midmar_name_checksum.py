#!/usr/bin/env python3
"""Checksum Midmar names to unique SAS IDs and official spelling.

Does not invent SAS IDs. Duplicate-name SAS records stay name-only.
Helm is never copied into crew. Clubs only change when the sheet code
exists in clubs (ELYC). Missing codes DRYC/PRSC/WYC are left as-is.
Gust 2018 crew from H19 history: Kai Funke + Thomas Funke.
"""
from __future__ import annotations

import psycopg2

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
BLOCK = "2026-09-19-hmyc-midmar-cup:hunter-19"


def person(sid, name):
    return {"sid": sid, "name": name}


def key_name(name: str) -> str:
    return " ".join((name or "").lower().split())


# helm_sid currently on the boat
BOATS = [
    {
        "helm_sid": 1218,
        "helm": person(1218, "Paul Changuion"),
        "crew": [person(15511, "Taylor Pretorius"), person(None, "Chiara Delvaux")],
        "club": None,
    },
    {
        "helm_sid": 177,
        "helm": person(177, "Craig Millar"),
        "crew": [person(None, "Erin Millar"), person(None, "Lia Millar")],
        "club": None,
    },
    {
        "helm_sid": 1221,
        "helm": person(1221, "Tony Cockerill"),
        "crew": [person(15510, "Cailee Pretorius"), person(21324, "Mia Strydom-Wallis")],
        "club": None,
    },
    {
        "helm_sid": 22984,
        "helm": person(22984, "Paige Smith"),
        "crew": [person(23999, "Bryan Paxman"), person(25125, "Ziva Filday")],
        "club": ("ELYC", 121),
    },
    {
        "helm_sid": 15579,
        "helm": person(15579, "Daniela Cantarelli"),
        "crew": [person(8444, "Nick Somerville"), person(None, "Tharyana")],
        "club": None,
    },
    {
        "helm_sid": 729,
        "helm": person(729, "Luke Wagner"),
        "crew": [person(12789, "Josh Pretorius"), person(None, "Carlotta Delvaux")],
        "club": None,
    },
    {
        "helm_sid": 21715,
        "helm": person(21715, "Gust Funke"),
        "crew": [person(22836, "Kai Funke"), person(2530, "Thomas Funke")],
        "club": None,
    },
    {
        "helm_sid": 8683,
        "helm": person(8683, "Hayden Miller"),
        "crew": [person(21172, "Timothy Weaving"), person(3709, "Howard Leoto")],
        "club": None,
    },
    {
        "helm_sid": 18659,
        "helm": person(18659, "Penny Macpherson"),
        "crew": [person(None, "Luke Curtis"), person(None, "Ethan")],
        "club": None,
    },
    {
        "helm_sid": 19130,
        "helm": person(19130, "Jethro Milne"),
        "crew": [person(15791, "Matthew Macpherson"), person(28155, "Caitlin Macpherson")],
        "club": None,
    },
    {
        "helm_sid": 14193,
        "helm": person(14193, "Shalin Naidoo"),
        "crew": [person(None, "Aaron Maharaj"), person(11291, "Melany Honicke")],
        "club": None,
    },
]

CHECKS = [
    (1218, "Paul", "Changuion"),
    (15511, "Taylor", "Pretorius"),
    (177, "Craig", "Millar"),
    (1221, "Tony", "Cockerill"),
    (15510, "Cailee", "Pretorius"),
    (21324, "Mia", "Strydom-wallis"),
    (22984, "Paige", "Smith"),
    (23999, "Bryan", "Paxman"),
    (25125, "Ziva", "Filday"),
    (15579, "Daniela", "Cantarelli"),
    (8444, "Nick", "Somerville"),
    (729, "Luke", "Wagner"),
    (12789, "Josh", "Pretorius"),
    (21715, "Gust", "Funke"),
    (22836, "Kai", "Funke"),
    (2530, "Thomas", "Funke"),
    (8683, "Hayden", "Miller"),
    (21172, "Timothy", "Weaving"),
    (3709, "Howard", "Leoto"),
    (18659, "Penny", "Macpherson"),
    (19130, "Jethro", "Milne"),
    (15791, "Matthew", "Macpherson"),
    (28155, "Caitlin", "Macpherson"),
    (14193, "Shalin", "Naidoo"),
    (11291, "Melany", "Honicke"),
]


def unique_sas(cur, sid: int, expect_fn: str, expect_ln: str) -> str:
    cur.execute(
        """
        SELECT sa_sailing_id::text, full_name, first_name, last_name
        FROM sas_id_personal WHERE sa_sailing_id::text = %s
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
    return row[1]


def crew_clean(helm, crew):
    hk = key_name(helm["name"])
    hid = helm.get("sid")
    out = []
    seen = {hk}
    for p in crew:
        nk = key_name(p["name"])
        if hid and p.get("sid") == hid:
            print("SKIP_DUP_SID", p["name"])
            continue
        if nk == hk or nk in seen:
            print("SKIP_DUP_NAME", p["name"])
            continue
        seen.add(nk)
        out.append(p)
    return out


def apply() -> int:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    official = {}
    for sid, fn, ln in CHECKS:
        official[sid] = unique_sas(cur, sid, fn, ln)

    cur.execute("SELECT club_id FROM clubs WHERE club_abbrev='ELYC'")
    if cur.fetchone()[0] != 121:
        raise SystemExit("REFUSE: ELYC")

    for boat in BOATS:
        helm = boat["helm"]
        if helm["sid"] in official:
            helm["name"] = official[helm["sid"]]
        crew = []
        for p in boat["crew"]:
            if p["sid"] and p["sid"] in official:
                # Keep readable hyphen case for Mia
                name = official[p["sid"]]
                if p["sid"] == 21324:
                    name = "Mia Strydom-Wallis"
                p = person(p["sid"], name)
            crew.append(p)
        crew = crew_clean(helm, crew)
        c1 = crew[0] if crew else None
        c2 = crew[1] if len(crew) > 1 else None

        sets = {
            "helm_name": helm["name"],
            "crew_name": c1["name"] if c1 else None,
            "crew_sa_sailing_id": c1["sid"] if c1 else None,
            "crew2_name": c2["name"] if c2 else None,
            "crew2_sa_sailing_id": c2["sid"] if c2 else None,
            "block_id": BLOCK,
        }
        if boat.get("club"):
            sets["club_raw"] = boat["club"][0]
            sets["club_id"] = boat["club"][1]
        sql = "UPDATE results SET " + ", ".join(f"{k}=%s" for k in sets)
        sql += " WHERE regatta_id=%s AND helm_sa_sailing_id=%s"
        cur.execute(sql, list(sets.values()) + [RID, boat["helm_sid"]])
        print("UPDATE", helm["name"], "crew=", sets["crew_name"], sets["crew2_name"], "n", cur.rowcount)

        crew_sid = str(c1["sid"]) if c1 and c1["sid"] else None
        if boat.get("club"):
            cur.execute(
                """
                UPDATE entries
                SET crew_sas_id=%s, club_code=%s, block_id=%s, verified=TRUE
                WHERE regatta_id=%s AND helm_sas_id=%s
                """,
                (crew_sid, boat["club"][0], BLOCK, RID, str(boat["helm_sid"])),
            )
        else:
            cur.execute(
                """
                UPDATE entries
                SET crew_sas_id=%s, block_id=%s, verified=TRUE
                WHERE regatta_id=%s AND helm_sas_id=%s
                """,
                (crew_sid, BLOCK, RID, str(boat["helm_sid"])),
            )

    conn.commit()
    print("\n===== AFTER =====")
    cur.execute(
        """
        SELECT rank, helm_name, helm_sa_sailing_id, crew_name, crew2_name,
               crew_sa_sailing_id, crew2_sa_sailing_id, sail_number, club_raw
        FROM results WHERE regatta_id=%s
        ORDER BY COALESCE(rank,99999), result_id
        """,
        (RID,),
    )
    for r in cur.fetchall():
        print(r)
        helm = key_name(r[1] or "")
        if helm and helm in {key_name(r[3] or ""), key_name(r[4] or "")}:
            raise SystemExit(f"REFUSE_AFTER dup helm {r}")
        if key_name(r[3] or "") and key_name(r[3] or "") == key_name(r[4] or ""):
            raise SystemExit(f"REFUSE_AFTER dup crew {r}")
    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(apply())
