#!/usr/bin/env python3
"""Midmar: store declared Youth Helm races and paint those cells blue (cannot discard)."""
from pathlib import Path

import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-19-hmyc-midmar-cup"
API = Path("/var/www/sailingsa/api/api.py")

# Entries xlsx COMPULSARY RACE columns. Skip Megan. Checksum SAS + sail.
# Danie = Daniela Cantarelli (442). Youth helm name from the sheet.
YOUTH = {
    1218: (["R2", "R3"], "Taylor Pretorius", "2013", "Paul"),
    177: (["R1", "R2"], "Erin Millar", "200", "Craig"),
    1221: (["R2", "R3"], "Cailee Pretorius", "2019", "Tony"),
    22984: (["R2", "R3"], "Paige Smith", "741", "Paige"),
    15579: (["R2", "R3"], "Daniela Cantarelli", "442", "Dani"),
    729: (["R2", "R3"], "Josh Pretorius", "2004", "Luke"),
    21715: (["R1", "R2"], "Gust Funke", "2018", "Gust"),
    8683: (["R1", "R2"], "Hayden Miller", "403", "Hayden"),
    18659: (["R2", "R3"], "Ethan", "40", "Penny"),
    28155: (["R2", "R3"], "Matthew Macpherson", "297", "Caitlin"),
    14193: (["R2", "R3"], "Shalin Naidoo", "748", "Shalin"),
}

CSS_OLD = '    ".score-counts{font-weight:bold}"\n'
CSS_NEW = (
    '    ".score-counts{font-weight:bold}"\n'
    '    ".youth-helm-nd{color:#0000ee!important;font-weight:700}"  # YOUTH_HELM_ND_v1\n'
)

SHOW_OLD = """        if show_races:
            for rkey in race_columns:
                score = str(race_scores.get(rkey) or "").strip()
                if is_wc_fleet_sheet or sa_fleet_ops:
"""
SHOW_NEW = """        if show_races:
            _nd_raw = race_scores.get("_no_discard") if isinstance(race_scores, dict) else None
            _yh_no_discard = {str(x) for x in _nd_raw} if isinstance(_nd_raw, list) else set()
            for rkey in race_columns:
                score = str(race_scores.get(rkey) or "").strip()
                if is_wc_fleet_sheet or sa_fleet_ops:
"""

WC_OLD = """                    if has_penalty:
                        rc_parts.append("code")
                    elif score:
                        rc_parts.append("score-counts")
                    rc_cls = " ".join(rc_parts)
                    _rk_attr = html_module.escape(str(rkey), quote=True)
"""
WC_NEW = """                    if has_penalty:
                        rc_parts.append("code")
                    elif score:
                        rc_parts.append("score-counts")
                    if rkey in _yh_no_discard:
                        rc_parts.append("youth-helm-nd")
                    rc_cls = " ".join(rc_parts)
                    _rk_attr = html_module.escape(str(rkey), quote=True)
"""

INNER_OLD = """                    if _assigned:
                        inner_cls.append("assigned-time")
                    cell_class = " ".join(inner_cls)
"""
INNER_NEW = """                    if _assigned:
                        inner_cls.append("assigned-time")
                    if rkey in _yh_no_discard:
                        inner_cls.append("youth-helm-nd")
                    cell_class = " ".join(inner_cls)
"""

DISC_OLD = """            res_discard_idxs = set()
            if discard_count > 0 and res_scores_list:
                remaining = list(enumerate(res_scores_list))
                remaining.sort(key=lambda x: (-x[1]["val"], -int(str(x[1]["key"])[1:] or 0)))
                for i in range(min(discard_count, len(remaining))):
                    res_discard_idxs.add(remaining[i][0])
"""
DISC_NEW = """            res_discard_idxs = set()
            if discard_count > 0 and res_scores_list:
                _nd = res_race_scores.get("_no_discard") if isinstance(res_race_scores, dict) else None
                _locked = {str(x) for x in _nd} if isinstance(_nd, list) else set()
                remaining = [(i, s) for i, s in enumerate(res_scores_list) if s["key"] not in _locked]
                remaining.sort(key=lambda x: (-x[1]["val"], -int(str(x[1]["key"])[1:] or 0)))
                for i in range(min(discard_count, len(remaining))):
                    res_discard_idxs.add(remaining[i][0])
"""

SAILED_OLD = """    _sailed_parts.append(f"Scoring system: {score_line_disp}")
    sailed_line = ", ".join(_sailed_parts)
"""
SAILED_NEW = """    _sailed_parts.append(f"Scoring system: {score_line_disp}")
    if any(
        isinstance((r.get("race_scores") or {}), dict)
        and (r.get("race_scores") or {}).get("_no_discard")
        for r in rows
    ):
        _sailed_parts.append("Youth Helm races (blue) cannot be discarded")
    sailed_line = ", ".join(_sailed_parts)
"""


def load_scores(raw):
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def patch_api() -> None:
    text = API.read_text()
    if "YOUTH_HELM_ND_v1" in text and "youth-helm-nd" in text:
        print("API_ALREADY")
        return
    for label, old, new in (
        ("CSS", CSS_OLD, CSS_NEW),
        ("SHOW", SHOW_OLD, SHOW_NEW),
        ("WC", WC_OLD, WC_NEW),
        ("INNER", INNER_OLD, INNER_NEW),
        ("DISC", DISC_OLD, DISC_NEW),
        ("SAILED", SAILED_OLD, SAILED_NEW),
    ):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"ANCHOR_{label}_{n}")
        text = text.replace(old, new, 1)
        print("PATCH", label)
    API.write_text(text)
    print("API_OK")


def write_flags() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT result_id, helm_name, helm_sa_sailing_id, sail_number, race_scores
        FROM results WHERE regatta_id=%s ORDER BY result_id
        """,
        (RID,),
    )
    rows = cur.fetchall()
    if len(rows) != 11:
        raise SystemExit("REFUSE expected 11 results, got " + str(len(rows)))
    by_sid = {int(r["helm_sa_sailing_id"]): r for r in rows if r["helm_sa_sailing_id"] is not None}
    if set(by_sid) != set(YOUTH):
        raise SystemExit("REFUSE SAS set mismatch " + str(sorted(by_sid)) + " vs " + str(sorted(YOUTH)))

    for sid, (races, youth, sail, nick) in YOUTH.items():
        row = by_sid[sid]
        live_sail = str(row["sail_number"] or "").strip()
        if live_sail != sail:
            raise SystemExit(f"REFUSE sail {sid} expected {sail} got {live_sail}")
        live = (row["helm_name"] or "").strip()
        if nick.casefold() not in live.casefold() and not (
            sid == 15579 and "daniela" in live.casefold() and "cantarelli" in live.casefold()
        ):
            raise SystemExit(f"REFUSE name {sid} {nick!r} not in {live!r}")
        if sid == 15579 and "cantarelli" not in live.casefold():
            raise SystemExit("REFUSE Danie is Daniela Cantarelli, got " + live)
        scores = load_scores(row["race_scores"])
        scores["_no_discard"] = races
        scores["_youth_helm"] = youth
        cur.execute(
            "UPDATE results SET race_scores=%s WHERE result_id=%s AND regatta_id=%s",
            (psycopg2.extras.Json(scores), row["result_id"], RID),
        )
        print("YH", live, live_sail, races, youth)

    conn.commit()
    cur.execute(
        "SELECT helm_name, sail_number, race_scores FROM results WHERE regatta_id=%s ORDER BY rank NULLS LAST",
        (RID,),
    )
    print("===== YOUTH FLAGS =====")
    for r in cur.fetchall():
        sc = load_scores(r["race_scores"])
        nd = sc.get("_no_discard")
        print(r["helm_name"], r["sail_number"], nd, sc.get("_youth_helm"))
        if not isinstance(nd, list) or len(nd) != 2:
            raise SystemExit("REFUSE missing _no_discard on " + str(r["helm_name"]))
        for k in ("R1", "R2", "R3", "R4"):
            if k in sc and not str(sc.get(k) or "").strip():
                raise SystemExit("REFUSE blanked score " + r["helm_name"] + " " + k)
    cur.close()
    conn.close()


def main() -> None:
    write_flags()
    patch_api()


if __name__ == "__main__":
    main()
