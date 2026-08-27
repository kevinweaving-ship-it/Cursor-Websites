#!/usr/bin/env python3
"""Align Lipton live-race race_times boat/club to official results. Do not change places."""
from __future__ import annotations

import json
import os
from pathlib import Path

RID = "2026-08-29-lipton-challenge-cup"
STATE = Path("/var/tmp/sailingsa_live_race_2026-08-29-lipton-challenge-cup.json")

# Official sheet (API boat_name + club_abbrev). Bow 8 visible club is RCYCA.
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


def _write(path: Path, data) -> None:
    tmp = Path("/tmp") / (path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.system(f"cp {tmp} {path}")
    os.system(f"chown www-data:www-data {path} >/dev/null 2>&1 || true")
    os.system(f"chmod 664 {path} >/dev/null 2>&1 || true")


def main() -> None:
    st = json.loads(STATE.read_text(encoding="utf-8"))
    rt = st.get("race_times") if isinstance(st.get("race_times"), dict) else {}
    n = 0
    for rk, rows in list(rt.items()):
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            b = str(row.get("bow") or "").strip()
            if b.isdigit():
                b = str(int(b))
            ident = BY_BOW.get(b)
            if not ident:
                continue
            boat, club = ident
            if row.get("boat_name") != boat or row.get("club") != club:
                row["boat_name"] = boat
                row["club"] = club
                n += 1
    st["race_times"] = rt
    _write(STATE, st)
    print("updated_rows", n, "race_key", st.get("race_key"), "gun", st.get("gun_at"), "day_done", st.get("day_done"))


if __name__ == "__main__":
    main()
