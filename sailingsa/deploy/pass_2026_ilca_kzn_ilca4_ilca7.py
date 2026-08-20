#!/usr/bin/env python3
"""Pass ILCA 4.7 / 6 / 7 fleets for 2026 ILCA KZN Regionals.

Column order (as sheet): Rank | Sail No | Club | Name | Category | Gender | R1–R6 | Total | Nett
Source: https://www.laser.org.za/events/364968
Requires DATABASE_URL or DB_URL.
"""
from __future__ import annotations

import json
import re
import sys
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_2026_ilca_kzn_regionals_stub import (  # noqa: E402
    REGATTA_ID,
    link_event,
    patch_header_icons,
    upsert_regatta,
    _db_url,
)

PEN = {"DNC", "OCS", "RET", "DNS", "DNF", "DSQ", "BFD", "UFD"}
NAME_ALIASES = {
    "connor lowe": "Conor Lowe",
    "anthony mcmillan": "Anthony MacMillan",
    "caitlin macpherson": "Caitlin MacPherson",
    "matthew macpherson": "Matthew MacPherson",
    "penny macpherson": "Penny MacPherson",
    "kees van welie": "Kees van Weelie",
    "michaels barrett": "Michael Barrett",
}

# Sheet rows: rank, sail, club, name, category, gender, r1..r6, total, nett
ILCA4 = {
    "class_original": "ILCA 4",
    "class_canonical": "Ilca 4.7",
    "block_slug": "ilca-4-7",
    "entries": 12,
    "discards": 1,
    "races": 6,
    "rows": [
        (1, "191090", "ZVYC", "Joshua Keytel", "Youth", "M", ["1.0", "(3.0)", "1.0", "1.0", "1.0", "1.0"], "8.0", "5.0"),
        (2, "191082", "HYC", "Nathan McCombe", "Youth", "M", ["2.0", "2.0", "(3.0)", "2.0", "3.0", "2.0"], "14.0", "11.0"),
        (3, "191056", "Aeolians", "Maximilian Malan", "Youth", "M", ["3.0", "1.0", "(4.0)", "3.0", "2.0", "3.0"], "16.0", "12.0"),
        (4, "55859", "HYC", "Connor Lowe", "Youth", "M", ["4.0", "(6.0)", "2.0", "4.0", "6.0", "4.0"], "26.0", "20.0"),
        (5, "160125", "ZYC", "Kai Law", "Youth", "M", ["6.0", "4.0", "5.0", "(OCS)", "4.0", "6.0"], "38.0", "25.0"),
        (6, "71", "PYC", "Jerome Vermaak", "Youth", "M", ["5.0", "5.0", "(DNC)", "OCS", "5.0", "5.0"], "46.0", "33.0"),
        (7, "191066", "HMYC", "Caitlin Macpherson", "Youth", "F", ["(DNC)", "DNC", "DNC", "6.0", "7.0", "9.0"], "61.0", "48.0"),
        (8, "205896", "ZYC", "Skyla Gaudin", "Youth", "F", ["(DNC)", "DNC", "DNC", "5.0", "9.0", "10.0"], "63.0", "50.0"),
        (9, "191055", "HMYC", "Matthew Macpherson", "Youth", "M", ["(DNC)", "DNC", "DNC", "7.0", "10.0", "7.0"], "63.0", "50.0"),
        (10, "208178", "PYC", "John-Alan Harding", "Youth", "M", ["(DNC)", "DNC", "DNC", "8.0", "8.0", "8.0"], "63.0", "50.0"),
        (11, "161595", "KSYC", "Shalin Naidoo", "Youth", "M", ["8.0", "7.0", "(DNC)", "DNC", "DNC", "DNC"], "67.0", "54.0"),
        (12, "19106", "ZYC", "Shelby Steenkamp", "Youth", "F", ["7.0", "8.0", "(DNC)", "DNC", "DNC", "DNC"], "67.0", "54.0"),
    ],
}
ILCA7 = {
    "class_original": "ILCA 7",
    "class_canonical": "Ilca 7",
    "block_slug": "ilca-7",
    "entries": 10,
    "discards": 1,
    "races": 6,
    "rows": [
        (1, "124133", "KSYC", "Rudy McNeill", "Senior", "M", ["(1.0)", "1.0", "1.0", "1.0", "1.0", "1.0"], "6.0", "5.0"),
        (2, "208177", "ZVYC", "Alistair Keytel", "Senior", "M", ["(2.0)", "2.0", "2.0", "2.0", "2.0", "2.0"], "12.0", "10.0"),
        (3, "191097", "PYC", "Luke Wagner", "Senior", "M", ["3.0", "3.0", "4.0", "(5.0)", "4.0", "5.0"], "24.0", "19.0"),
        (4, "214132", "PYC", "Campbell Alexander", "Senior", "M", ["4.0", "5.0", "3.0", "(7.0)", "5.0", "3.0"], "27.0", "20.0"),
        (5, "191093", "HMYC", "Anthony McMillan", "Senior", "M", ["5.0", "4.0", "5.0", "(6.0)", "3.0", "6.0"], "29.0", "23.0"),
        (6, "2337", "ESC", "Barry Hundley", "Senior", "M", ["6.0", "(OCS)", "6.0", "4.0", "7.0", "7.0"], "41.0", "30.0"),
        (7, "191033", "ELYC", "Shaun Gradwell", "Senior", "M", ["(DNC)", "DNC", "DNC", "3.0", "6.0", "4.0"], "46.0", "35.0"),
        (8, "TBA", "PYC", "Struan Alexander", "Senior", "M", ["7.0", "6.0", "(DNC)", "8.0", "9.0", "8.0"], "49.0", "38.0"),
        (9, "122771", "BSC", "Ian Campbell", "Senior", "M", ["(DNC)", "7.0", "RET", "9.0", "8.0", "10.0"], "56.0", "45.0"),
        (10, "12277", "BSC", "Stephan Deeke", "Senior", "M", ["(DNC)", "DNC", "DNC", "10.0", "10.0", "9.0"], "62.0", "51.0"),
    ],
}
ILCA6 = {
    "class_original": "ILCA 6",
    "class_canonical": "Ilca 6",
    "block_slug": "ilca-6",
    "entries": 10,
    "discards": 1,
    "races": 6,
    "rows": [
        (1, "188566", "ZVYC", "Blake Madel", "Youth", "M", ["3.0", "1.0", "1.0", "1.0", "(OCS)", "2.0"], "19.0", "8.0"),
        (2, "201753", "RNYC", "Paul Changuion", "Senior", "M", ["1.0", "3.0", "2.0", "2.0", "(OCS)", "4.0"], "23.0", "12.0"),
        (3, "160127", "SYC", "Aydin O'Hara", "Youth", "M", ["2.0", "4.0", "3.0", "(5.0)", "2.0", "3.0"], "19.0", "14.0"),
        (4, "144324", "HMYC", "Noah Clulow", "Youth", "M", ["(RET)", "2.0", "DNC", "7.0", "1.0", "1.0"], "33.0", "22.0"),
        (5, "144153", "RNYC", "Michaels Barrett", "Youth", "F", ["4.0", "(6.0)", "5.0", "4.0", "4.0", "6.0"], "29.0", "23.0"),
        (6, "188079", "HMYC", "Daniela Cantarelli", "Youth", "F", ["5.0", "5.0", "4.0", "6.0", "5.0", "(7.0)"], "32.0", "25.0"),
        (7, "19123", "HMYC", "Penny Macpherson", "Senior", "F", ["(DNC)", "DNC", "DNC", "3.0", "3.0", "5.0"], "44.0", "33.0"),
        (8, "42555", "BSC", "Stephan Deeke", "Senior", "M", ["7.0", "8.0", "6.0", "(DNC)", "DNC", "DNC"], "54.0", "43.0"),
        (9, "191233", "HMYC", "Kees van Welie", "Senior", "M", ["6.0", "7.0", "(DNC)", "DNC", "DNC", "DNC"], "57.0", "46.0"),
        (10, "37181", "BSC", "Mike Tainton", "Senior", "M", ["(DNC)", "DNC", "DNC", "8.0", "6.0", "RET"], "58.0", "47.0"),
    ],
}


def encode_score(raw: str, entries: int) -> str:
    s = (raw or "").strip()
    discarded = s.startswith("(") and s.endswith(")")
    inner = s[1:-1].strip() if discarded else s
    up = inner.upper()
    if up in PEN:
        body = f"{entries + 1}.0 {up}"
        return f"({body})" if discarded else body
    if re.fullmatch(r"\d+", inner):
        body = f"{inner}.0"
    elif re.fullmatch(r"\d+\.0", inner):
        body = inner
    else:
        body = inner
    return f"({body})" if discarded else body


def score_value(encoded: str) -> Decimal:
    inner = encoded[1:-1] if encoded.startswith("(") and encoded.endswith(")") else encoded
    m = re.match(r"(-?\d+(?:\.\d+)?)", inner.strip())
    if not m:
        raise ValueError(encoded)
    return Decimal(m.group(1))


def checksum_row(raw_scores: list[str], entries: int, total: str, nett: str) -> dict:
    enc = [encode_score(x, entries) for x in raw_scores]
    vals = [score_value(x) for x in enc]
    tot = sum(vals)
    disc = max(vals)  # one discard = worst (highest) including penalties
    net = tot - disc
    exp_t = Decimal(total)
    exp_n = Decimal(nett)
    ok = tot == exp_t and net == exp_n
    return {"ok": ok, "scores": enc, "total": tot, "nett": net, "exp_t": exp_t, "exp_n": exp_n}


def lookup_club(cur, code: str):
    c = (code or "").strip()
    cur.execute(
        """
        SELECT club_id, club_abbrev FROM clubs
        WHERE UPPER(TRIM(club_abbrev)) = UPPER(%s)
           OR LOWER(TRIM(club_fullname)) = LOWER(%s)
        LIMIT 1
        """,
        (c, c),
    )
    row = cur.fetchone()
    if row:
        return row[0], (row[1] or c)
    return None, c


def lookup_sailor(cur, name: str):
    n = (name or "").strip()
    aliases = [n]
    alt = NAME_ALIASES.get(n.lower())
    if alt:
        aliases.append(alt)
    for cand in aliases:
        cur.execute(
            """
            SELECT sa_sailing_id, COALESCE(NULLIF(TRIM(full_name), ''),
                   TRIM(COALESCE(first_name,'') || ' ' || COALESCE(last_name,''))) AS full_name
            FROM sas_id_personal
            WHERE LOWER(TRIM(full_name)) = LOWER(%s)
               OR LOWER(TRIM(COALESCE(first_name,'') || ' ' || COALESCE(last_name,''))) = LOWER(%s)
            LIMIT 1
            """,
            (cand, cand),
        )
        row = cur.fetchone()
        if row:
            return str(row[0]).strip(), (row[1] or cand).strip()
    return None, n


def class_id(cur, name: str) -> int:
    cur.execute(
        "SELECT class_id FROM classes WHERE TRIM(class_name) = %s LIMIT 1",
        (name,),
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"validated class not found: {name}")
    return int(row[0])


def table_cols(cur, table: str) -> set[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        """,
        (table,),
    )
    return {r[0] for r in cur.fetchall() or []}


def ensure_gender(cur) -> None:
    cols = table_cols(cur, "results")
    if "gender" not in cols:
        cur.execute("ALTER TABLE public.results ADD COLUMN gender TEXT")


def upsert_block(cur, fleet: dict, cid: int) -> str:
    bid = f"{REGATTA_ID}:{fleet['block_slug']}"
    cols = table_cols(cur, "regatta_blocks")
    wanted = {
        "block_id": bid,
        "regatta_id": REGATTA_ID,
        "fleet_label": fleet["class_canonical"],
        "class_original": fleet["class_original"],
        "class_canonical": fleet["class_canonical"],
        "class_id": cid,
        "races_sailed": fleet["races"],
        "discard_count": fleet["discards"],
        "to_count": fleet["races"] - fleet["discards"],
        "scoring_system": "Appendix A",
    }
    insert_cols = [c for c in wanted if c in cols]
    placeholders = ", ".join(["%s"] * len(insert_cols))
    col_sql = ", ".join(insert_cols)
    updates = ", ".join(f"{c}=EXCLUDED.{c}" for c in insert_cols if c != "block_id")
    cur.execute(
        f"""
        INSERT INTO public.regatta_blocks ({col_sql})
        VALUES ({placeholders})
        ON CONFLICT (block_id) DO UPDATE SET {updates}
        """,
        tuple(wanted[c] for c in insert_cols),
    )
    return bid


def insert_fleet(cur, fleet: dict) -> list[str]:
    cid = class_id(cur, fleet["class_canonical"])
    bid = upsert_block(cur, fleet, cid)
    rcols = table_cols(cur, "results")
    cur.execute("DELETE FROM public.results WHERE regatta_id=%s AND block_id=%s", (REGATTA_ID, bid))
    unmatched = []
    for rank, sail, club_code, name, cat, gender, races, total, nett in fleet["rows"]:
        chk = checksum_row(races, fleet["entries"], total, nett)
        if not chk["ok"]:
            raise SystemExit(
                f"checksum fail {name}: got {chk['total']}/{chk['nett']} expected {chk['exp_t']}/{chk['exp_n']}"
            )
        club_id, club_raw = lookup_club(cur, club_code)
        sas_id, canon = lookup_sailor(cur, name)
        if not sas_id:
            unmatched.append(f"{name} | {club_code} | {sail}")
        scores = {f"R{i+1}": chk["scores"][i] for i in range(6)}
        helm_id = None
        if sas_id and str(sas_id).isdigit():
            helm_id = int(sas_id)
        elif sas_id:
            helm_id = sas_id
        row = {
            "regatta_id": REGATTA_ID,
            "block_id": bid,
            "rank": rank,
            "fleet_label": fleet["class_canonical"],
            "class_original": fleet["class_original"],
            "class_canonical": fleet["class_canonical"],
            "class_id": cid,
            "sail_number": sail,
            "helm_name": canon,
            "club_raw": club_raw,
            "club_id": club_id,
            "helm_sa_sailing_id": helm_id,
            "race_scores": psycopg2.extras.Json(scores),
            "total_points_raw": Decimal(total),
            "nett_points_raw": Decimal(nett),
            "races_sailed": fleet["races"],
            "discard_count": fleet["discards"],
            "ranks_sailed": fleet["entries"],
            "raced": True,
            "age_category": cat,
            "gender": gender,
            "result_status": "Provisional",
        }
        insert_cols = [c for c in row if c in rcols and row[c] is not None]
        placeholders = ", ".join(["%s"] * len(insert_cols))
        cur.execute(
            f"INSERT INTO public.results ({', '.join(insert_cols)}) VALUES ({placeholders})",
            tuple(row[c] for c in insert_cols),
        )
    return unmatched


def main() -> None:
    patch_header_icons()
    conn = psycopg2.connect(_db_url())
    try:
        with conn.cursor() as cur:
            upsert_regatta(cur)
            n = link_event(cur)
            ensure_gender(cur)
            unmatched = []
            unmatched += insert_fleet(cur, ILCA4)
            unmatched += insert_fleet(cur, ILCA6)
            unmatched += insert_fleet(cur, ILCA7)
        conn.commit()
    finally:
        conn.close()
    print(f"regatta_id={REGATTA_ID}")
    print(f"events_linked={n}")
    print("source_url=https://www.laser.org.za/events/364968")
    print("url=https://sailingsa.co.za/regatta/2026-08-10-ilca-kzn-regional-championships")
    print("fleets=Ilca 4.7, Ilca 6, Ilca 7")
    if unmatched:
        print("UNMATCHED sailors (need SA ID / Temp):")
        for u in unmatched:
            print(f"  {u}")
    else:
        print("all helms matched to sas_id_personal")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
