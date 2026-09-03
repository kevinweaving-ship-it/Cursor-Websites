#!/usr/bin/env python3
"""Offline contract: Vakaros names on a new Rn become official sheet identity."""
from __future__ import annotations

import traceback

# Mirror of live helper (same map / behaviour as patch_lipton_official_identity_overlay.py).
BY_BOW = {
    "26": ("Amtec Racing", "RCYC"),
    "32": ("Nitro Juice", "HYC"),
    "28": ("Ullman Racing", "RNYC"),
    "23": ("Phantom", "KYC"),
    "52": ("22-ATE", "WBYC"),
    "8": ("J-Walker powered by North Sails", "RCYCA"),
    "48": ("Ullman Sails Camissa", "FBYC"),
    "31": ("Nitro Maverick", "UCT"),
    "46": ("Wildcard", "LDYC"),
    "49": ("Nitro Monkey", "SBYC"),
    "34": ("G'day J", "PYC"),
    "14": ("Andiamo", "GLYC"),
    "44": ("H2O Tech", "BYC"),
    "63": ("Donna Mia Forever", "IZI"),
    "55": ("CaCanny", "TSC"),
    "51": ("Attacke", "LYCN"),
    "43": ("Laugh a minute", "WYAC"),
}


def overlay(rid: str, st: dict) -> None:
    if "lipton" not in str(rid or "").lower() or not isinstance(st, dict):
        return

    def _norm_bow(val) -> str:
        b = str(val or "").strip()
        if b.isdigit():
            b = str(int(b))
        return b

    def _apply_rows(rows) -> None:
        if not isinstance(rows, list):
            return
        for row in rows:
            if not isinstance(row, dict):
                continue
            b = _norm_bow(row.get("bow") or row.get("bow_no"))
            ident = BY_BOW.get(b)
            if not ident:
                continue
            boat, club = ident
            row["boat_name"] = boat
            row["club"] = club

    rt = st.get("race_times") if isinstance(st.get("race_times"), dict) else {}
    for rows in rt.values():
        _apply_rows(rows)
    _apply_rows(st.get("rankings"))


def main() -> int:
    rid = "2026-08-29-lipton-challenge-cup"
    st = {
        "race_times": {
            "R5": [
                {"bow": "26", "boat_name": "Amtec Racing", "club": "RCYC", "place": 1, "finish_ms": 1},
            ],
            "R6": [
                {"bow": "26", "boat_name": "VAKAROS Amtec", "club": "???", "place": 3, "finish_ms": 9},
                {"bow": "08", "boat_name": "J Walker", "club": "RCYC", "place": 1, "finish_ms": 5},
                {"bow": "63", "boat_name": "Donna", "place": 2, "finish_ms": 7},
            ],
        },
        "rankings": [{"bow": "26", "boat_name": "tracker", "place": 3, "finish_ms": 9}],
    }
    overlay(rid, st)
    r6 = {str(int(r["bow"])): r for r in st["race_times"]["R6"]}
    assert r6["26"]["boat_name"] == "Amtec Racing" and r6["26"]["club"] == "RCYC"
    assert r6["8"]["boat_name"] == "J-Walker powered by North Sails" and r6["8"]["club"] == "RCYCA"
    assert r6["63"]["boat_name"] == "Donna Mia Forever" and r6["63"]["club"] == "IZI"
    assert r6["26"]["place"] == 3 and r6["26"]["finish_ms"] == 9  # scores untouched
    assert st["rankings"][0]["boat_name"] == "Amtec Racing"
    other = {"race_times": {"R1": [{"bow": "26", "boat_name": "keep"}]}}
    overlay("hyc-cape-classic-2026", other)
    assert other["race_times"]["R1"][0]["boat_name"] == "keep"
    print("PASS official identity overlay")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
