#!/usr/bin/env python3
"""Live results pass: 2026 420 Nationals, 505 Nationals, Dabchick Gauteng Regionals.

Official sheets as written. SAS id_personal names are display truth.
Do not invent SAS IDs.
"""
from __future__ import annotations

import json

import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
CANON = (
    "COALESCE(NULLIF(TRIM(full_name),''), "
    "TRIM(BOTH FROM (COALESCE(first_name,'') || ' ' || COALESCE(last_name,''))))"
)

RID420 = "2026-09-25-tsc-420-nationals"
BLK420 = "2026-09-25-tsc-420-nationals:420"
RID505 = "2026-09-24-ayc-505-nationals"
BLK505 = "2026-09-24-ayc-505-nationals:505"
RIDDAB = "2026-09-24-ayc-dabchick-gauteng-regionals"
BLKDAB = "2026-09-24-ayc-dabchick-gauteng-regionals:dabchick"


def sc(dne: int, place: str | float, code: str = "", discard: bool = False) -> str:
    if isinstance(place, str) and any(c.isalpha() for c in place):
        raw = place
    else:
        num = float(place)
        raw = f"{num:.1f}" if num != int(num) else f"{int(num)}.0"
        if code:
            raw = f"{raw} {code}"
    if discard and not raw.startswith("("):
        raw = f"({raw})"
    return raw


def scores(*pairs) -> dict:
    out = {}
    for i, p in enumerate(pairs, 1):
        if isinstance(p, tuple):
            if len(p) == 3:
                out[f"R{i}"] = sc(0, p[0], p[1], p[2])
            else:
                out[f"R{i}"] = sc(0, p[0], p[1] if len(p) > 1 else "", False)
        else:
            out[f"R{i}"] = sc(0, p)
    return out


def canon_name(cur, sas_id, fallback: str) -> str:
    if not sas_id:
        return fallback
    cur.execute(f"SELECT {CANON} AS n FROM sas_id_personal WHERE sa_sailing_id::text=%s", (str(sas_id),))
    row = cur.fetchone()
    n = (row or {}).get("n") if row else None
    return (n or fallback).strip()


def class_id(cur, name: str) -> int | None:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name='classes'
        """
    )
    cols = {r["column_name"] for r in cur.fetchall()}
    if not cols:
        return None
    id_col = "class_id" if "class_id" in cols else None
    if not id_col:
        return None
    name_cols = [c for c in ("class_name", "class_canonical", "name", "canonical_name") if c in cols]
    if not name_cols:
        return None
    where = " OR ".join(f"{c} ILIKE %s" for c in name_cols)
    cur.execute(
        f"SELECT {id_col} AS class_id FROM classes WHERE {where} ORDER BY {id_col} LIMIT 1",
        tuple([name] * len(name_cols)),
    )
    row = cur.fetchone()
    return row["class_id"] if row else None


def upsert_regatta(cur, rid, name, host_id, host_code, host_name, start, end, status, as_at, scoring):
    cur.execute("SELECT 1 FROM regattas WHERE regatta_id=%s", (rid,))
    if cur.fetchone():
        cur.execute(
            """
            UPDATE regattas
            SET event_name=%s, host_club_id=%s, start_date=%s, end_date=%s,
                result_status=%s, as_at_time=%s, year=2026, scoring_system=%s
            WHERE regatta_id=%s
            """,
            (name, host_id, start, end, status, as_at, scoring, rid),
        )
        print("REG_UPD", rid)
        return
    cur.execute(
        """
        INSERT INTO regattas (
            regatta_id, event_name, year, host_club_id, start_date, end_date,
            result_status, as_at_time, scoring_system, import_status
        ) VALUES (%s,%s,2026,%s,%s,%s,%s,%s,%s,'ok')
        """,
        (rid, name, host_id, start, end, status, as_at, scoring),
    )
    print("REG_INS", rid)


def upsert_block(cur, bid, rid, class_orig, class_can, cid, sailed, disc, to_count, scoring):
    cur.execute("SELECT 1 FROM regatta_blocks WHERE block_id=%s", (bid,))
    if cur.fetchone():
        cur.execute(
            """
            UPDATE regatta_blocks
            SET races_sailed=%s, discard_count=%s, to_count=%s, scoring_system=%s,
                class_canonical=%s, class_original=%s
            WHERE block_id=%s
            """,
            (sailed, disc, to_count, scoring, class_can, class_orig, bid),
        )
        print("BLK_UPD", bid)
        return
    cur.execute(
        """
        INSERT INTO regatta_blocks (
            block_id, regatta_id, class_original, class_canonical, class_id,
            races_sailed, discard_count, to_count, scoring_system, block_label_raw
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (bid, rid, class_orig, class_can, cid, sailed, disc, to_count, scoring, class_orig),
    )
    print("BLK_INS", bid)


def insert_result(cur, rid, bid, row, cid, sailed, disc, status, as_at):
    helm = canon_name(cur, row.get("hs"), row["helm"])
    crew = None
    if row.get("crew") or row.get("cs"):
        crew = canon_name(cur, row.get("cs"), row.get("crew") or "")
    cur.execute(
        """
        INSERT INTO results (
            regatta_id, block_id, rank, rank_ordinal, pos, class_original, class_canonical,
            class_id, sail_number, jib_no, club_raw, club_id, helm_name, helm_sa_sailing_id,
            crew_name, crew_sa_sailing_id, races_sailed, discard_count, race_scores,
            total_points_raw, nett_points_raw, raced, result_status, as_at_time
        ) VALUES (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,true,%s,%s
        )
        """,
        (
            rid,
            bid,
            row["rank"],
            row.get("ord") or _ord(row["rank"]),
            row["rank"],
            row.get("cls") or "505",
            row.get("cls") or "505",
            cid,
            row.get("sail"),
            row.get("jib"),
            row.get("club"),
            row.get("cid"),
            helm,
            row.get("hs"),
            crew or None,
            row.get("cs"),
            sailed,
            disc,
            json.dumps(row["sc"]),
            row["tot"],
            row["nett"],
            status,
            as_at,
        ),
    )


def _ord(n: int) -> str:
    if n % 100 in (11, 12, 13):
        return f"{n}th"
    return f"{n}{'st' if n%10==1 else 'nd' if n%10==2 else 'rd' if n%10==3 else 'th'}"


def apply_420(cur) -> None:
    as_at = "2026-09-27 15:24:00"
    cur.execute(
        """
        UPDATE regattas
        SET result_status='Final', as_at_time=%s, scoring_system='Appendix A'
        WHERE regatta_id=%s
        """,
        (as_at, RID420),
    )
    cur.execute(
        """
        UPDATE regatta_blocks
        SET races_sailed=8, discard_count=1, to_count=7, scoring_system='Appendix A'
        WHERE regatta_id=%s
        """,
        (RID420,),
    )
    boats = [
        {"match": ("helm", 25), "sail": "53001", "jib": "5", "club": "HYC", "cid": 10,
         "helm": "Dale Rae", "hs": 25, "crew": "James Rae", "cs": 15737, "rank": 1,
         "tot": 14, "nett": 10,
         "sc": scores((4, "", True), 1, 1, 1, 4, 1, 1, 1)},
        {"match": ("helm", 3709), "sail": "5309", "jib": "16", "club": "RNYC", "cid": 20,
         "helm": "Howard Leoto", "hs": 3709, "crew": "Lebogang January", "cs": 1485, "rank": 2,
         "tot": 27, "nett": 20,
         "sc": scores(1, 3, 3, 3, 5, (7, "", True), 3, 2)},
        {"match": ("helm", 13516), "sail": "54809", "jib": "11", "club": "MAC", "cid": 58,
         "helm": "Kamva Mgcubhe", "hs": 13516, "crew": "Maddison Smit", "cs": 21052, "rank": 3,
         "tot": 36, "nett": 27,
         "sc": scores(3, 2, 6, 6, 2, 2, (9, "", True), 6)},
        {"match": ("helm", 1521), "sail": "52997", "jib": "4", "club": "ZVYC", "cid": 3,
         "helm": "Jemayne Wolmarans", "hs": 1521, "crew": "Dylan Swart", "cs": None, "rank": 4,
         "tot": 37, "nett": 28,
         "sc": scores(2, 4, 2, 4, (9, "", True), 6, 7, 3)},
        {"match": ("helm", 18020), "sail": "54806", "jib": "14", "club": "HYC", "cid": 10,
         "helm": "Ben Henshilwood", "hs": 18020, "crew": "Thomas Henshilwood", "cs": 9612, "rank": 5,
         "tot": 43, "nett": 34,
         "sc": scores((9, "", True), 6, 7, 5, 1, 5, 5, 5)},
        {"match": ("insert", None), "sail": "5299", "jib": "18", "club": "RCYC", "cid": 11,
         "helm": "Robyn Patrick", "hs": 6903, "crew": "Theo Yon", "cs": 2562, "rank": 6,
         "tot": 64, "nett": 47,
         "sc": scores((17, "NSC", True), 9, 4, 7, 8, 8, 4, 7)},
        {"match": ("any", (1491, 15834)), "sail": "54050", "jib": "10", "club": "MAC", "cid": 58,
         "helm": "Siphelele Gayeka", "hs": 1491, "crew": "Aisha Knobloch", "cs": 15834, "rank": 7,
         "tot": 59, "nett": 49,
         "sc": scores(5, 5, 5, 9, 6, (10, "", True), 10, 9)},
        {"match": ("helm", 8704), "sail": "52996", "jib": "50", "club": "ZVYC", "cid": 3,
         "helm": "Joshua Nankin", "hs": 8704, "crew": "Joshua Keytel", "cs": 13522, "rank": 8,
         "tot": 64, "nett": 52,
         "sc": scores(11, (12, "", True), 9, 2, 11, 9, 2, 8)},
        {"match": ("helm", 15738), "sail": "3", "jib": "81", "club": "HYC", "cid": 10,
         "helm": "Hayley Rae", "hs": 15738, "crew": "Faith Lyons", "cs": 12998, "rank": 9,
         "tot": 76, "nett": 63,
         "sc": scores(8, 8, 12, (13, "", True), 10, 4, 11, 10)},
        {"match": ("helm", 21172), "sail": "53095", "jib": "88", "club": "RNYC", "cid": 20,
         "helm": "Timothy Weaving", "hs": 21172, "crew": "Hayden Miller", "cs": 8683, "rank": 10,
         "tot": 81, "nett": 64,
         "sc": scores(10, 7, (17, "RET", True), (17, "DSQ", False), 3, (17, "DSQ", False), 6, 4)},
        {"match": ("helm", 21517), "sail": "53002", "jib": "6", "club": "HYC", "cid": 10,
         "helm": "Nathan McCombe", "hs": 21517, "crew": "Liam Geldenhuys", "cs": 25653, "rank": 11,
         "tot": 87, "nett": 70,
         "sc": scores(6, 10, 8, 11, 7, 11, (17, "DNF", True), (17, "DNS", False))},
        {"match": ("helm", 9515), "sail": "53100", "jib": "20", "club": "ZVYC", "cid": 3,
         "helm": "Theodor Scheder-Bieschin", "hs": 9515, "crew": "Carina Grabner", "cs": None, "rank": 12,
         "tot": 89, "nett": 72,
         "sc": scores(7, 14, 11, 8, (17, "DNS", True), 3, 12, (17, "RET", False))},
        {"match": ("row", 21276), "sail": "52998", "jib": "15", "club": "IZI", "cid": 28,
         "helm": "Simamkele Mtshofeni", "hs": None, "crew": "Kamvaelihle Matomela", "cs": 23596, "rank": 13,
         "tot": 99, "nett": 82,
         "sc": scores(12, 15, 13, 10, (17, "DNS", True), 12, 8, 12)},
        {"match": ("helm", 6497), "sail": "53093", "jib": "4", "club": "MAC", "cid": 58,
         "helm": "Chiara Fruet", "hs": 6497, "crew": "Bazolele Mseswa", "cs": 26437, "rank": 14,
         "tot": 109, "nett": 92,
         "sc": scores(13, 11, 14, (17, "RET", True), (17, "DNS", False), 13, 13, 11)},
        {"match": ("row", 21269), "sail": "53007", "jib": "13", "club": "IZI", "cid": 28,
         "helm": "Athenkosi Mahluma", "hs": 12512, "crew": "Buhle Majavu", "cs": 13040, "rank": 15,
         "tot": 114, "nett": 97,
         "sc": scores(14, 13, 10, 12, (17, "DNS", True), 14, (17, "DNC", False), (17, "DNS", False))},
        {"match": ("row", 21277), "sail": "1", "jib": "2", "club": "ZVSC", "cid": 72,
         "helm": "Thaakir Martin", "hs": 24190, "crew": "Xavier Stone", "cs": 24218, "rank": 16,
         "tot": 133, "nett": 116,
         "sc": scores(15, 16, (17, "TLE", True), (17, "RET", False), (17, "DNS", False),
                      (17, "DNF", False), (17, "TLE", False), (17, "RET", False))},
    ]
    for b in boats:
        helm = canon_name(cur, b.get("hs"), b["helm"])
        crew = canon_name(cur, b.get("cs"), b["crew"]) if (b.get("crew") or b.get("cs")) else None
        vals = (
            b["sail"], b["jib"], b["club"], b["cid"], helm, b.get("hs"), crew, b.get("cs"),
            json.dumps(b["sc"]), b["tot"], b["nett"], b["rank"], _ord(b["rank"]),
            as_at, RID420,
        )
        kind, key = b["match"]
        if kind == "insert":
            cur.execute("SELECT 1 FROM results WHERE regatta_id=%s AND helm_sa_sailing_id=%s", (RID420, b["hs"]))
            if cur.fetchone():
                cur.execute(
                    """
                    UPDATE results SET sail_number=%s, jib_no=%s, club_raw=%s, club_id=%s,
                        helm_name=%s, helm_sa_sailing_id=%s, crew_name=%s, crew_sa_sailing_id=%s,
                        race_scores=%s::jsonb, total_points_raw=%s, nett_points_raw=%s,
                        rank=%s, rank_ordinal=%s, pos=%s, races_sailed=8, discard_count=1,
                        raced=true, result_status='Final', as_at_time=%s
                    WHERE regatta_id=%s AND helm_sa_sailing_id=%s
                    """,
                    vals[:-1] + (b["rank"], as_at, RID420, b["hs"]),
                )
                print("420_UPD_INS", helm)
            else:
                insert_result(
                    cur, RID420, BLK420,
                    {**b, "cls": "420", "ord": _ord(b["rank"])},
                    7, 8, 1, "Final", as_at,
                )
                print("420_INS", helm)
            continue
        if kind == "helm":
            cur.execute(
                """
                UPDATE results SET sail_number=%s, jib_no=%s, club_raw=%s, club_id=%s,
                    helm_name=%s, helm_sa_sailing_id=%s, crew_name=%s, crew_sa_sailing_id=%s,
                    race_scores=%s::jsonb, total_points_raw=%s, nett_points_raw=%s,
                    rank=%s, rank_ordinal=%s, pos=%s, races_sailed=8, discard_count=1,
                    raced=true, result_status='Final', as_at_time=%s
                WHERE regatta_id=%s AND helm_sa_sailing_id=%s
                """,
                (b["sail"], b["jib"], b["club"], b["cid"], helm, b.get("hs"), crew, b.get("cs"),
                 json.dumps(b["sc"]), b["tot"], b["nett"], b["rank"], _ord(b["rank"]),
                 b["rank"], as_at, RID420, key),
            )
        elif kind == "any":
            cur.execute(
                """
                UPDATE results SET sail_number=%s, jib_no=%s, club_raw=%s, club_id=%s,
                    helm_name=%s, helm_sa_sailing_id=%s, crew_name=%s, crew_sa_sailing_id=%s,
                    race_scores=%s::jsonb, total_points_raw=%s, nett_points_raw=%s,
                    rank=%s, rank_ordinal=%s, pos=%s, races_sailed=8, discard_count=1,
                    raced=true, result_status='Final', as_at_time=%s
                WHERE regatta_id=%s AND (
                    helm_sa_sailing_id IN %s OR crew_sa_sailing_id IN %s
                    OR helm_name ILIKE 'Aisha%%' OR crew_name ILIKE 'Sphelele%%'
                )
                """,
                (b["sail"], b["jib"], b["club"], b["cid"], helm, b.get("hs"), crew, b.get("cs"),
                 json.dumps(b["sc"]), b["tot"], b["nett"], b["rank"], _ord(b["rank"]),
                 b["rank"], as_at, RID420, key, key),
            )
        else:
            cur.execute(
                """
                UPDATE results SET sail_number=%s, jib_no=%s, club_raw=%s, club_id=%s,
                    helm_name=%s, helm_sa_sailing_id=%s, crew_name=%s, crew_sa_sailing_id=%s,
                    race_scores=%s::jsonb, total_points_raw=%s, nett_points_raw=%s,
                    rank=%s, rank_ordinal=%s, pos=%s, races_sailed=8, discard_count=1,
                    raced=true, result_status='Final', as_at_time=%s
                WHERE result_id=%s AND regatta_id=%s
                """,
                (b["sail"], b["jib"], b["club"], b["cid"], helm, b.get("hs"), crew, b.get("cs"),
                 json.dumps(b["sc"]), b["tot"], b["nett"], b["rank"], _ord(b["rank"]),
                 b["rank"], as_at, key, RID420),
            )
        print("420_UPD", helm, "rank", b["rank"], "rows", cur.rowcount)
    cur.execute(
        "UPDATE events SET regatta_id=%s, event_status='completed' WHERE event_id=184126",
        (RID420,),
    )
    cur.execute("SELECT COUNT(*) n, COUNT(jib_no) j FROM results WHERE regatta_id=%s", (RID420,))
    print("420_DONE", dict(cur.fetchone()))


def apply_505(cur) -> None:
    as_at = "2026-09-26 16:30:00"
    cid = class_id(cur, "505")
    upsert_regatta(
        cur, RID505, "505 Nationals", 117, "AYC", "Aeolians Yacht Club",
        "2026-09-24", "2026-09-27", "Final", as_at, "Appendix A",
    )
    upsert_block(cur, BLK505, RID505, "505", "505", cid, 12, 2, 10, "Appendix A")
    cur.execute("DELETE FROM results WHERE regatta_id=%s", (RID505,))
    boats = [
        {"sail": "9094", "club": "AYC", "cid": 117, "helm": "Peter Funke", "hs": 2686,
         "crew": "Thomas Funke", "cs": 2530, "rank": 1, "tot": 18, "nett": 14,
         "sc": scores(1, (2, "", True), 1, (2, "", True), 2, 2, 2, 2, 1, 1, 1, 1)},
        {"sail": "8445", "club": "PSC", "cid": 1, "helm": "Kyle Klaas", "hs": 1350,
         "crew": "Robert Von Gruenewaldt", "cs": 1311, "rank": 2, "tot": 18, "nett": 14,
         "sc": scores((2, "", True), 1, (2, "", True), 1, 1, 1, 1, 1, 2, 2, 2, 2)},
        {"sail": "8471", "club": "VLC", "cid": 68, "helm": "Aaron Biagio", "hs": 9393,
         "crew": "C-J Milln", "cs": 3121, "rank": 3, "tot": 41, "nett": 30,
         "sc": scores((3, "", True), 3, 3, 3, (3, "TLE", False), 3, 3, 3, 3, 3, 3, (8, "DNF", True))},
        {"sail": "7722", "club": "BSC", "cid": 50, "helm": "Dudley Thomson", "hs": 9168,
         "crew": "Patrick Loubser", "cs": 18385, "rank": 4, "tot": 50, "nett": 40,
         "sc": scores((5, "", True), (5, "", True), 4, 4, (3, "TLE", False), 4, 4, 5, 5, 4, 4, 3)},
        {"sail": "9016", "club": "PSC", "cid": 1, "helm": "Arend Van Wamelen", "hs": 8388,
         "crew": "David Nieman", "cs": 16060, "rank": 5, "tot": 68, "nett": 52,
         "sc": scores(6, 4, 5, 5, (3, "TLE", False), (8, "DNC", True), (8, "DNC", True), 4, 4, 5,
                      (8, "DNC", False), (8, "DNC", False))},
        {"sail": "8587", "club": "ESC", "cid": None, "helm": "Andrew Arthur", "hs": 2742,
         "crew": "Jacques Faure", "cs": 20418, "rank": 6, "tot": 66, "nett": 52,
         "sc": scores((7, "", True), (7, "", True), (6, "TLE", False), (6, "TLE", False),
                      (3, "TLE", False), 5, 5, 6, 6, 6, (5, "TLE", False), 4)},
        {"sail": "7457", "club": "PSC", "cid": 1, "helm": "Jan Zuidersma", "hs": 6467,
         "crew": "Jean Zuidersma", "cs": None, "rank": 7, "tot": 84, "nett": 68,
         "sc": scores(4, 6, 6, (8, "TLE", True), (8, "DNC", True), (8, "DNC", False),
                      (8, "DNC", False), (8, "DNF", False), (8, "DNC", False), 7,
                      (5, "TLE", False), (8, "DNF", False))},
    ]
    for b in boats:
        insert_result(cur, RID505, BLK505, {**b, "cls": "505"}, cid, 12, 2, "Final", as_at)
        print("505_INS", b["helm"], b["rank"])
    cur.execute(
        """
        UPDATE events
        SET regatta_id=%s, host_club_id=117, event_status='completed'
        WHERE event_id=43
        """,
        (RID505,),
    )
    print("505_LINK event 43")


def apply_dab(cur) -> None:
    cid = class_id(cur, "Dabchick")
    upsert_regatta(
        cur, RIDDAB, "Dabchick Gauteng Regionals", 117, "AYC", "Aeolians Yacht Club",
        "2026-09-24", "2026-09-26", "Final", None, "Appendix A",
    )
    upsert_block(cur, BLKDAB, RIDDAB, "Dabchick", "Dabchick", cid, 12, 2, 10, "Appendix A")
    cur.execute("DELETE FROM results WHERE regatta_id=%s", (RIDDAB,))
    boats = [
        {"sail": "3471", "club": "HYC", "cid": 10, "helm": "Dylan Hall", "hs": 12583,
         "crew": None, "cs": None, "rank": 1, "tot": 12, "nett": 10,
         "sc": scores((1, "", True), (1, "", True), 1, 1, 1, 1, 1, 1, 1, 1, 1, 1)},
        {"sail": "3434", "club": "VLC", "cid": 68, "helm": "Maximilian Malan", "hs": 12878,
         "crew": None, "cs": None, "rank": 2, "tot": 42, "nett": 21,
         "sc": scores(2, 2, 2, 2, 2, (3, "", True), 2, 3, 2, 2, 2, (18, "DNC", True))},
        {"sail": "3316", "club": "PSC", "cid": 1, "helm": "Megan Stegen", "hs": 22702,
         "crew": None, "cs": None, "rank": 3, "tot": 47, "nett": 35,
         "sc": scores((5, "", True), 3, 3, 5, 3, 2, 4, (7, "", True), 4, 5, 3, 3)},
        {"sail": "3380", "club": "LDYC", "cid": 85, "helm": "Kgotso Koetle", "hs": 21135,
         "crew": None, "cs": None, "rank": 4, "tot": 71, "nett": 54,
         "sc": scores(7, 7, 4, 4, 7, 5, 7, (9, "", True), (8, "", True), 3, 5, 5)},
        {"sail": "3443", "club": "VLC", "cid": 68, "helm": "Mika Malan", "hs": 12879,
         "crew": None, "cs": None, "rank": 5, "tot": 86, "nett": 59,
         "sc": scores(3, 4, 5, 6, (8, "TLE", False), (9, "", True), 9, 2, 6, 8, 8, (18, "DNC", True))},
        {"sail": "34", "club": "VLC", "cid": 68, "helm": "David Smith", "hs": 3952,
         "crew": None, "cs": None, "rank": 6, "tot": 79, "nett": 60,
         "sc": scores((8, "", True), 8, 8, 7, 4, 4, 6, 8, 7, (11, "", True), 4, 4)},
        {"sail": "3334", "club": "LDYC", "cid": 85, "helm": "Wianro Bester", "hs": 18628,
         "crew": None, "cs": None, "rank": 7, "tot": 90, "nett": 62,
         "sc": scores(6, (10, "", True), 9, 3, 5, 7, 3, 5, 5, 9, 10, (18, "DNC", True))},
        {"sail": "3452", "club": "VLC", "cid": 68, "helm": "Ethan Biagio", "hs": 13961,
         "crew": None, "cs": None, "rank": 8, "tot": 90, "nett": 66,
         "sc": scores((12, "", True), 6, 7, 8, 6, 10, 4, (11, "", True), 6, 6, 2, 12)},
        {"sail": "3410", "club": "BYC", "cid": 86, "helm": "Angus Poppmeier", "hs": 18076,
         "crew": None, "cs": None, "rank": 9, "tot": 88, "nett": 67,
         "sc": scores((10, "", True), 5, 6, (11, "", True), (8, "TLE", False), 8, 5, 10, 3, 7, 9, 6)},
        {"sail": "3431", "club": "PYC", "cid": 5, "helm": "Gust Funke", "hs": 21715,
         "crew": None, "cs": None, "rank": 10, "tot": 93, "nett": 69,
         "sc": scores(4, 9, (10, "TLE", True), (14, "TLE", True), 8, 6, 8, 6, 9, 4, 7, 8)},
        {"sail": "3460", "club": "VLC", "cid": 68, "helm": "Reese McCulloch", "hs": 24737,
         "crew": None, "cs": None, "rank": 11, "tot": 135, "nett": 109,
         "sc": scores(9, 11, 12, (13, "", True), (8, "TLE", False), 11, 12, (13, "", True), 11, 13, 13, 9)},
        {"sail": "3387", "club": "LDYC", "cid": 85, "helm": "Taylor Milln", "hs": 20848,
         "crew": "Kayden Gibbons", "cs": 20780, "rank": 12, "tot": 146, "nett": 115,
         "sc": scores((16, "", True), 12, 13, (15, "", True), (8, "TLE", False), 12, 11, 11, 10, 14, 14, 10)},
        {"sail": "8380", "club": "LDYC", "cid": 85, "helm": "Michael Bill", "hs": 22145,
         "crew": None, "cs": None, "rank": 13, "tot": 160, "nett": 124,
         "sc": scores(14, 15, 11, 10, 8, 15, 17, (18, "DSQ", True), 12, 10, 12, (18, "DNF", True))},
        {"sail": "3364", "club": "VLC", "cid": 68, "helm": "Phillip Nyamakura", "hs": 28586,
         "crew": None, "cs": None, "rank": 14, "tot": 159, "nett": 126,
         "sc": scores(15, 13, 14, (16, "", True), 8, (17, "TLE", True), 16, 14, 16, 12, 11, 7)},
        {"sail": "3391", "club": "LDYC", "cid": 85, "helm": "Anthony Latsky", "hs": 24676,
         "crew": None, "cs": None, "rank": 15, "tot": 171, "nett": 135,
         "sc": scores(11, (18, "RET", True), (18, "DNC", True), 12, 8, 13, 14, 12, 16, 16, 15, (18, "DNC", False))},
        {"sail": "2986", "club": "LDYC", "cid": 85, "helm": "Riley Doel", "hs": 22231,
         "crew": None, "cs": None, "rank": 16, "tot": 174, "nett": 138,
         "sc": scores(17, 14, 15, 9, 8, 14, 13, 16, 15, 17, (18, "DNF", True), (18, "DNC", True))},
        {"sail": "3264", "club": "VLC", "cid": 68, "helm": "Sebastian Marschall", "hs": 23953,
         "crew": None, "cs": None, "rank": 17, "tot": 181, "nett": 145,
         "sc": scores(13, 16, (18, "RET", True), 17, 8, 16, 15, 15, 14, 15, 16, (18, "DNC", True))},
    ]
    for b in boats:
        insert_result(cur, RIDDAB, BLKDAB, {**b, "cls": "Dabchick"}, cid, 12, 2, "Final", None)
        print("DAB_INS", b["helm"], b["rank"])
    cur.execute(
        """
        UPDATE events
        SET regatta_id=%s, host_club_id=117, event_status='completed'
        WHERE event_id=139941
        """,
        (RIDDAB,),
    )
    print("DAB_LINK event 139941")


def main() -> None:
    with psycopg2.connect(DSN) as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        apply_420(cur)
        apply_505(cur)
        apply_dab(cur)
        conn.commit()
        for rid in (RID420, RID505, RIDDAB):
            cur.execute(
                """
                SELECT COUNT(*) n, MIN(rank) mn, MAX(rank) mx,
                       COUNT(NULLIF(helm_sa_sailing_id::text,'')) sas
                FROM results WHERE regatta_id=%s
                """,
                (rid,),
            )
            print("SUM", rid, dict(cur.fetchone()))


if __name__ == "__main__":
    main()
