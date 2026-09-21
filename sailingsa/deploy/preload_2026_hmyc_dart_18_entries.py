#!/usr/bin/env python3
"""Preload Dart 18 Nationals 2026 entries onto live Event URL — two fleets DH + SH.

CSV Entry Type:
  Dart 18 Single          -> SH
  Dart 18 Double / Youth  -> DH

Apply on live (agent SSH, not the user):

  python3 sailingsa/deploy/preload_2026_hmyc_dart_18_entries.py --apply
"""

from __future__ import annotations

import csv
import os
import re
import sys
from pathlib import Path

SLUG = "2026-09-24-hmyc-dart-18-nationals"
BLOCK_SH = f"{SLUG}:dart-18-sh"
BLOCK_DH = f"{SLUG}:dart-18-dh"
OLD_BLOCK = f"{SLUG}:dart-18"
CLASS_NAME = "Dart 18"
CLASS_ID = 246
CSV_NAME = "dart_18_nationals_2026_entry_list.csv"

CLUB_MAP = {
    "HMYC": ("HMYC", 98),
    "SYC": ("SYC", 65),
    "VYC": ("VYC", 70),
    "ZYC": ("ZYC", 108),
    "TCC": ("TCC", 146),
    "VOGELVLEI YC": ("VYC", 70),
    "VOGELVLEI": ("VYC", 70),
}

# Forced SA IDs after dry-run (canonical names come from sas_id_personal).
FORCE_HELM = {
    "aydin ohara": 9357,
    "mathew olsen": 17575,
    "joaquim bernardes": 24708,
}
FORCE_CREW = {
    ("bradley stemmett", "saskia"): 271,
    ("owen hemingway", "ian hemingway"): 17876,
}

ALIASES = {
    "aydin ohara": "aydin o'hara",
    "matthew dunninbg": "matthew dunning",
}


def norm(s: str) -> str:
    s = str(s or "").replace("'", "'").replace("'", "'").lower().strip()
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return ALIASES.get(s, s)


def title_name(s: str) -> str:
    return " ".join(w[:1].upper() + w[1:] if w else "" for w in str(s or "").split())


def clean_crew(s: str) -> str:
    s = str(s or "").strip()
    if not s or s.lower() in ("n/a", "na", "-", "none"):
        return ""
    return s


def fleet_of(entry_type: str) -> str:
    t = str(entry_type or "").lower()
    if "single" in t or re.search(r"\bsh\b", t):
        return "SH"
    return "DH"


def club_of(raw: str) -> tuple[str, int | None]:
    key = re.sub(r"\s+", " ", str(raw or "").strip()).upper()
    return CLUB_MAP.get(key, (key or "UNK", None))


def find_person(cur, name: str, club: str | None = None):
    n = norm(name)
    if not n:
        return None
    parts = n.replace("'", "").split()
    last = parts[-1] if parts else ""
    first = parts[0] if parts else ""
    cur.execute(
        """
        SELECT sa_sailing_id::text AS sid, full_name
        FROM public.sas_id_personal
        WHERE lower(full_name) = %s
           OR lower(replace(full_name, '''', '')) = %s
           OR lower(coalesce(nickname,'')) = %s
        LIMIT 5
        """,
        (n, n.replace("'", ""), n),
    )
    rows = list(cur.fetchall())
    if not rows and last and first:
        cur.execute(
            """
            SELECT sa_sailing_id::text AS sid, full_name
            FROM public.sas_id_personal
            WHERE lower(full_name) LIKE %s
              AND (lower(full_name) LIKE %s OR lower(coalesce(nickname,'')) LIKE %s)
            LIMIT 8
            """,
            (f"%{last}%", f"{first}%", f"{first}%"),
        )
        rows = list(cur.fetchall())
        # Require last token in the matched name.
        rows = [r for r in rows if last in norm(r["full_name"]).replace("'", "")]
    if club and len(rows) > 1:
        # no primary_club in this select; keep exact name
        exact = [r for r in rows if norm(r["full_name"]) == n]
        if exact:
            rows = exact
    if len(rows) == 1:
        return dict(rows[0])
    if len(rows) > 1:
        exact = [r for r in rows if norm(r["full_name"]) == n]
        if len(exact) == 1:
            return dict(exact[0])
    return None


def ensure_blocks(cur) -> None:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema='public' AND table_name='regatta_blocks'
        """
    )
    cols = {r["column_name"] for r in cur.fetchall()}
    extra = []
    extra_vals = []
    if "class_id" in cols:
        extra.append("class_id")
        extra_vals.append(CLASS_ID)
    if "scoring_system" in cols:
        extra.append("scoring_system")
        extra_vals.append("Appendix A")
    if "handicap_system" in cols:
        extra.append("handicap_system")
        extra_vals.append("Appendix A")
    extra_sql = (", " + ", ".join(extra)) if extra else ""
    extra_ph = (", " + ", ".join(["%s"] * len(extra_vals))) if extra_vals else ""
    for bid, fleet, label in (
        (BLOCK_SH, "SH", "Dart 18 SH"),
        (BLOCK_DH, "DH", "Dart 18 DH"),
    ):
        cur.execute(
            f"""
            INSERT INTO public.regatta_blocks (
              block_id, regatta_id, class_original, class_canonical, fleet_label,
              races_sailed, discard_count, to_count, block_label_raw{extra_sql}
            ) VALUES (
              %s, %s, %s, %s, %s, 0, 0, 0, %s{extra_ph}
            )
            ON CONFLICT (block_id) DO UPDATE SET
              class_original = EXCLUDED.class_original,
              class_canonical = EXCLUDED.class_canonical,
              fleet_label = EXCLUDED.fleet_label,
              block_label_raw = EXCLUDED.block_label_raw
            """,
            (bid, SLUG, CLASS_NAME, CLASS_NAME, fleet, label, *extra_vals),
        )
    cur.execute(
        "SELECT count(*) FROM public.results WHERE block_id = %s",
        (OLD_BLOCK,),
    )
    n = int(cur.fetchone()["count"])
    if n == 0:
        cur.execute("DELETE FROM public.regatta_blocks WHERE block_id = %s", (OLD_BLOCK,))


def next_tmp(cur) -> int:
    cur.execute(
        """
        SELECT GREATEST(
          COALESCE(MAX(NULLIF(regexp_replace(coalesce(helm_temp_id,''), '\\D', '', 'g'), '')::int), 0),
          COALESCE(MAX(NULLIF(regexp_replace(coalesce(crew_temp_id,''), '\\D', '', 'g'), '')::int), 0)
        ) AS n FROM public.results
        """
    )
    return int((cur.fetchone() or {}).get("n") or 0) + 1


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _sid(val) -> int | None:
    if val is None or val == "":
        return None
    try:
        return int(str(val).strip())
    except (TypeError, ValueError):
        return None


def resolve_sailor(cur, name: str, club: str, forced: int | None, tmp_n: list[int]):
    if not name:
        return None, None, None
    if forced:
        cur.execute(
            "SELECT sa_sailing_id::text AS sid, full_name FROM public.sas_id_personal WHERE sa_sailing_id::text = %s",
            (str(forced),),
        )
        hit = cur.fetchone()
        if hit:
            return _sid(hit["sid"]), hit["full_name"], None
    hit = find_person(cur, name, club)
    if hit:
        return _sid(hit["sid"]), hit["full_name"], None
    tid = f"TMP:{tmp_n[0]}"
    tmp_n[0] += 1
    return None, title_name(name), tid


def apply(url: str, csv_path: Path) -> int:
    import psycopg2
    import psycopg2.extras

    rows = load_rows(csv_path)
    if len(rows) < 10:
        sys.stderr.write(f"CSV too short: {csv_path}\n")
        return 2
    conn = psycopg2.connect(url)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        ensure_blocks(cur)
        cur.execute("DELETE FROM public.entries WHERE regatta_id = %s", (SLUG,))
        cur.execute("DELETE FROM public.results WHERE regatta_id = %s", (SLUG,))
        tmp_n = [next_tmp(cur)]
        sh = dh = 0
        tmp_used = []
        for raw in rows:
            fleet = fleet_of(raw.get("Entry Type") or "")
            bid = BLOCK_SH if fleet == "SH" else BLOCK_DH
            if fleet == "SH":
                sh += 1
            else:
                dh += 1
            helm_raw = (raw.get("Skipper Name") or "").strip()
            crew_raw = clean_crew(raw.get("Crew Name") or "")
            club_code, club_id = club_of(raw.get("Yacht Club") or "")
            sail = str(raw.get("Sail Number") or "").strip() or None
            youth = "youth" in str(raw.get("Entry Type") or "").lower()
            h_key = norm(helm_raw)
            c_key = (h_key, norm(crew_raw)) if crew_raw else None
            h_id, h_name, h_tmp = resolve_sailor(
                cur, helm_raw, club_code, FORCE_HELM.get(h_key), tmp_n
            )
            c_force = FORCE_CREW.get(c_key) if c_key else None
            c_id = c_name = c_tmp = None
            if crew_raw and fleet == "DH":
                c_id, c_name, c_tmp = resolve_sailor(cur, crew_raw, club_code, c_force, tmp_n)
            if h_tmp:
                tmp_used.append((helm_raw, h_tmp, "helm"))
            if c_tmp:
                tmp_used.append((crew_raw, c_tmp, "crew"))
            cur.execute(
                """
                INSERT INTO public.results (
                  regatta_id, block_id, fleet_label, class_original, class_canonical, class_id,
                  sail_number, club_raw, club_id,
                  helm_name, helm_sa_sailing_id, helm_temp_id,
                  crew_name, crew_sa_sailing_id, crew_temp_id,
                  races_sailed, discard_count, ranks_sailed, race_scores,
                  raced, age_category, event_name, start_date, end_date,
                  host_club_name, result_status, row_validation_status, manually_parsed
                ) VALUES (
                  %s, %s, %s, %s, %s, %s,
                  %s, %s, %s,
                  %s, %s, %s,
                  %s, %s, %s,
                  0, 0, 0, '{}'::jsonb,
                  FALSE, %s, %s, DATE '2026-09-24', DATE '2026-09-27',
                  'Henley Midmar Yacht Club', 'Provisional', 'preloaded', FALSE
                )
                RETURNING result_id
                """,
                (
                    SLUG,
                    bid,
                    fleet,
                    CLASS_NAME,
                    CLASS_NAME,
                    CLASS_ID,
                    sail,
                    club_code,
                    club_id,
                    h_name,
                    h_id,
                    h_tmp,
                    c_name,
                    c_id,
                    c_tmp,
                    "Youth" if youth else None,
                    "Dart 18 Nationals incorporating the KZN provincials",
                ),
            )
            cur.execute(
                """
                INSERT INTO public.entries (
                  regatta_id, block_id, sail_number, helm_sas_id, crew_sas_id,
                  helm_temp_id, crew_temp_id, club_code, verified
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE)
                """,
                (
                    SLUG,
                    bid,
                    sail,
                    str(h_id) if h_id else None,
                    str(c_id) if c_id else None,
                    h_tmp,
                    c_tmp,
                    club_code,
                ),
            )
        conn.commit()
        print(f"ok {SLUG} entries={sh + dh} SH={sh} DH={dh}")
        if tmp_used:
            print("TMP (no SA ID):")
            for name, tid, role in tmp_used:
                print(f"  {tid} {role} {name}")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def main() -> int:
    apply_flag = "--apply" in sys.argv
    url = os.getenv("DATABASE_URL") or os.getenv("DB_URL")
    here = Path(__file__).resolve().parent
    csv_path = here / CSV_NAME
    if not csv_path.is_file():
        csv_path = Path("/tmp/Dart_18_Nationals_Entry_List.csv")
    if not apply_flag:
        rows = load_rows(csv_path) if csv_path.is_file() else []
        sh = sum(1 for r in rows if fleet_of(r.get("Entry Type") or "") == "SH")
        dh = len(rows) - sh
        print(f"dry-run csv={csv_path} rows={len(rows)} SH={sh} DH={dh}")
        print("blocks", BLOCK_SH, BLOCK_DH)
        print("Pass --apply with DATABASE_URL to write live.")
        return 0
    if not url:
        sys.stderr.write("Set DATABASE_URL or DB_URL (SSH live).\n")
        return 2
    return apply(url, csv_path)


if __name__ == "__main__":
    raise SystemExit(main())
