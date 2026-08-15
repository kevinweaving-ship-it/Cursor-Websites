#!/usr/bin/env python3
"""Match North Sails J22 helms/crews to sas_id_personal; apply confident matches; list issues.

HARD RULE — SAS ID table = name truth:
  When a sailor is linked to sas_id_personal (or Temp id), results.helm_name /
  results.crew_name MUST be the canonical SAS name (first+last / full_name).
  Results-sheet spellings are match input only — never keep sheet typos,
  nicknames, or OCR mistakes once an ID is known.
"""
from __future__ import annotations

import os
import re
from difflib import SequenceMatcher

import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.environ.get(
    "DB_URL",
    "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master",
)
RID = "2026-08-16-2026-north-sails-j22-championships"
CLASS = "J22"


def norm(n: str | None) -> str:
    return re.sub(r"\s+", " ", (n or "").strip())


def ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").casefold(), (b or "").casefold()).ratio()


def name_keys(n: str) -> tuple[str, str]:
    parts = norm(n).split()
    if not parts:
        return "", ""
    return parts[0], parts[-1]


def sail_digits(s: str | None) -> str:
    return re.sub(r"[^0-9]", "", s or "")


def canonical_sql():
    return (
        "COALESCE(NULLIF(TRIM(full_name), ''), "
        "TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')))"
    )


def main() -> int:
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()

    def prior_by_sail(sail: str, role: str):
        col_id = "helm_sa_sailing_id" if role == "helm" else "crew_sa_sailing_id"
        col_name = "helm_name" if role == "helm" else "crew_name"
        cur.execute(
            f"""
            SELECT {col_id} AS sas_id, {col_name} AS nm, COUNT(*) AS n
            FROM results
            WHERE class_canonical = %s
              AND REGEXP_REPLACE(COALESCE(sail_number, ''), '[^0-9]', '', 'g') = %s
              AND {col_id} IS NOT NULL
              AND regatta_id <> %s
            GROUP BY 1, 2
            ORDER BY n DESC
            LIMIT 8
            """,
            (CLASS, sail_digits(sail), RID),
        )
        return list(cur.fetchall() or [])

    def prior_by_name(name: str, role: str):
        col_id = "helm_sa_sailing_id" if role == "helm" else "crew_sa_sailing_id"
        col_name = "helm_name" if role == "helm" else "crew_name"
        first, last = name_keys(name)
        cur.execute(
            f"""
            SELECT {col_id} AS sas_id, {col_name} AS nm, COUNT(*) AS n
            FROM results
            WHERE class_canonical = %s
              AND {col_id} IS NOT NULL
              AND {col_name} IS NOT NULL
              AND (
                LOWER({col_name}) = LOWER(%s)
                OR (
                  LOWER(split_part({col_name}, ' ', 1)) = LOWER(%s)
                  AND LOWER(split_part({col_name}, ' ', -1)) = LOWER(%s)
                )
              )
              AND regatta_id <> %s
            GROUP BY 1, 2
            ORDER BY n DESC
            LIMIT 5
            """,
            (CLASS, name, first, last, RID),
        )
        return list(cur.fetchall() or [])

    def sas_lookup(sas_id) -> dict | None:
        cur.execute(
            f"""
            SELECT sa_sailing_id::int AS id, {canonical_sql()} AS n
            FROM sas_id_personal
            WHERE sa_sailing_id::text = %s
            LIMIT 1
            """,
            (str(sas_id),),
        )
        return cur.fetchone()

    def sas_fuzzy(name: str) -> list[dict]:
        first, last = name_keys(name)
        cur.execute(
            f"""
            SELECT sa_sailing_id::int AS sas_id,
                   {canonical_sql()} AS canonical,
                   first_name, last_name, nickname
            FROM sas_id_personal
            WHERE last_name IS NOT NULL
              AND (LOWER(last_name) = LOWER(%s) OR LOWER(full_name) = LOWER(%s))
            LIMIT 25
            """,
            (last, name),
        )
        cands = []
        for r in cur.fetchall() or []:
            can = r["canonical"] or ""
            sim = max(
                ratio(name, can),
                ratio(first, r["first_name"] or "") * 0.45
                + ratio(last, r["last_name"] or "") * 0.55,
            )
            if r.get("nickname"):
                sim = max(sim, ratio(name, r["nickname"]))
            cands.append(
                {"sas_id": r["sas_id"], "canonical": can, "sim": sim}
            )
        try:
            cur.execute(
                f"""
                SELECT sa_sailing_id::int AS sas_id,
                       {canonical_sql()} AS canonical,
                       similarity(LOWER(COALESCE(full_name, '')), LOWER(%s)) AS sim
                FROM sas_id_personal
                WHERE similarity(LOWER(COALESCE(full_name, '')), LOWER(%s)) > 0.35
                ORDER BY sim DESC
                LIMIT 8
                """,
                (name, name),
            )
            for r in cur.fetchall() or []:
                if not any(x["sas_id"] == r["sas_id"] for x in cands):
                    cands.append(
                        {
                            "sas_id": r["sas_id"],
                            "canonical": r["canonical"],
                            "sim": float(r["sim"]),
                        }
                    )
        except Exception:
            conn.rollback()
        cands.sort(key=lambda x: -x["sim"])
        return cands[:5]

    def pair_prior(helm: str, crew: str):
        cur.execute(
            """
            SELECT helm_sa_sailing_id AS helm_id, crew_sa_sailing_id AS crew_id,
                   helm_name, crew_name, COUNT(*) AS n
            FROM results
            WHERE class_canonical = %s
              AND helm_sa_sailing_id IS NOT NULL
              AND crew_sa_sailing_id IS NOT NULL
              AND (
                (LOWER(helm_name) = LOWER(%s) AND LOWER(crew_name) = LOWER(%s))
                OR (
                  LOWER(split_part(helm_name, ' ', -1)) = LOWER(split_part(%s, ' ', -1))
                  AND LOWER(split_part(crew_name, ' ', -1)) = LOWER(split_part(%s, ' ', -1))
                )
              )
              AND regatta_id <> %s
            GROUP BY 1, 2, 3, 4
            ORDER BY n DESC
            LIMIT 5
            """,
            (CLASS, helm, crew, helm, crew, RID),
        )
        return list(cur.fetchall() or [])

    def resolve_person(name: str, sail: str, role: str) -> tuple[dict | None, str | None, list]:
        notes = []
        by_sail = prior_by_sail(sail, role)
        by_name = prior_by_name(name, role)
        fuzzy = sas_fuzzy(name)

        if by_sail:
            best = None
            for p in by_sail:
                nm = p.get("nm") or ""
                if ratio(name, nm) >= 0.75 or name_keys(name)[1].casefold() == name_keys(nm)[1].casefold():
                    best = p
                    break
            if best:
                s = sas_lookup(best["sas_id"])
                if s:
                    return (
                        {
                            "sas_id": s["id"],
                            "canonical": s["n"],
                            "via": "prior_sail_j22",
                            "sheet": name,
                            "sim": ratio(name, s["n"]),
                        },
                        None,
                        notes,
                    )
            notes.append(f"sail_hist={by_sail[:3]}")
            # fall through — may still fuzzy-match

        if by_name:
            s = sas_lookup(by_name[0]["sas_id"])
            if s:
                return (
                    {
                        "sas_id": s["id"],
                        "canonical": s["n"],
                        "via": "prior_name_j22",
                        "sheet": name,
                        "sim": ratio(name, s["n"]),
                    },
                    None,
                    notes,
                )

        if fuzzy:
            top = fuzzy[0]
            second = fuzzy[1]["sim"] if len(fuzzy) > 1 else 0
            if top["sim"] >= 0.88 or (top["sim"] >= 0.78 and top["sim"] - second >= 0.08):
                return (
                    {
                        "sas_id": top["sas_id"],
                        "canonical": top["canonical"],
                        "via": "sas_fuzzy",
                        "sheet": name,
                        "sim": top["sim"],
                    },
                    None,
                    notes,
                )
            if top["sim"] >= 0.55:
                notes.append(f"fuzzy={fuzzy[:3]}")
                return None, "AMBIGUOUS_OR_WEAK_FUZZY", notes
            notes.append(f"fuzzy_weak={fuzzy[:2]}")
        return None, "NO_MATCH", notes

    cur.execute(
        """
        SELECT result_id, rank, helm_name, crew_name, sail_number, club_raw
        FROM results WHERE regatta_id = %s ORDER BY rank
        """,
        (RID,),
    )
    rows = list(cur.fetchall() or [])
    report = []

    for r in rows:
        helm = norm(r["helm_name"])
        crew = norm(r["crew_name"]) if r.get("crew_name") else None
        sail = r["sail_number"]
        item = {
            "rank": r["rank"],
            "result_id": r["result_id"],
            "helm": helm,
            "crew": crew,
            "sail": sail,
            "helm_match": None,
            "crew_match": None,
            "helm_issue": None,
            "crew_issue": None,
            "notes": [],
        }

        hm, hi, hn = resolve_person(helm, sail, "helm")
        item["helm_match"], item["helm_issue"], item["notes"] = hm, hi, hn

        if crew:
            # pair boost
            pairs = pair_prior(helm, crew)
            if pairs and pairs[0].get("crew_id"):
                s = sas_lookup(pairs[0]["crew_id"])
                if s and (
                    ratio(crew, s["n"]) >= 0.7
                    or name_keys(crew)[1].casefold() == name_keys(s["n"])[1].casefold()
                ):
                    item["crew_match"] = {
                        "sas_id": s["id"],
                        "canonical": s["n"],
                        "via": "helm_crew_pair",
                        "sheet": crew,
                        "sim": ratio(crew, s["n"]),
                    }
            if not item["crew_match"]:
                cm, ci, cn = resolve_person(crew, sail, "crew")
                item["crew_match"], item["crew_issue"] = cm, ci
                item["notes"].extend(cn)

        report.append(item)

    applied = 0
    for item in report:
        sets, vals = [], []
        if item["helm_match"]:
            m = item["helm_match"]
            sets += [
                "helm_sa_sailing_id = %s",
                "helm_name = %s",
                "match_status_helm = %s",
            ]
            vals += [m["sas_id"], m["canonical"], "matched"]
        if item["crew_match"]:
            m = item["crew_match"]
            sets += [
                "crew_sa_sailing_id = %s",
                "crew_name = %s",
                "match_status_crew = %s",
            ]
            vals += [m["sas_id"], m["canonical"], "matched"]
        if sets:
            vals.append(item["result_id"])
            cur.execute(
                "UPDATE results SET " + ", ".join(sets) + " WHERE result_id = %s",
                vals,
            )
            applied += 1
    conn.commit()

    issues = [
        i
        for i in report
        if i["helm_issue"] or (i["crew"] and i["crew_issue"] and not i["crew_match"])
    ]

    print(f"APPLIED rows touched: {applied}")
    print(
        f"Helm matched {sum(1 for i in report if i['helm_match'])}/16 | "
        f"Crew matched {sum(1 for i in report if i['crew'] and i['crew_match'])}/"
        f"{sum(1 for i in report if i['crew'])}"
    )
    print("=== MATCHED ===")
    for i in report:
        if i["helm_match"] or i["crew_match"]:
            hm = i["helm_match"]
            cm = i["crew_match"]
            hbit = (
                f"{hm['canonical']}#{hm['sas_id']} via {hm['via']} sim={hm['sim']:.2f}"
                if hm
                else "—"
            )
            cbit = (
                f"{cm['canonical']}#{cm['sas_id']} via {cm['via']} sim={cm['sim']:.2f}"
                if cm
                else ("—" if not i["crew"] else "UNMATCHED")
            )
            print(f"  #{i['rank']:>2} sail {i['sail']:<5} helm={hbit} | crew={cbit}")

    print(f"=== ISSUES ({len(issues)}) — resolve one-by-one starting #1 ===")
    for n, i in enumerate(issues, 1):
        print(
            f"ISSUE {n}: rank {i['rank']} sail {i['sail']} "
            f"helm={i['helm']!r} crew={i['crew']!r}"
        )
        print(f"  helm_issue={i['helm_issue']} crew_issue={i['crew_issue']}")
        print(f"  notes={i['notes'][:4]}")
        # extra candidates for issue 1 detail
        if n == 1:
            print("  --- candidates for ISSUE 1 ---")
            for role, name in (("helm", i["helm"]), ("crew", i["crew"])):
                if not name:
                    continue
                print(f"  {role} fuzzy:", sas_fuzzy(name)[:5])
                print(f"  {role} prior sail:", prior_by_sail(i["sail"], role)[:5])
                print(f"  {role} prior name:", prior_by_name(name, role)[:5])

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
