#!/usr/bin/env python3
"""Patch live api.py: keep official Lipton boat/club on every race_times persist.

Tracker PUT for a new Rn starts with empty cur_race_rows, so Vakaros names
would otherwise become the row identity. Overlay official sheet names (and
club) at write time. Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_OFFICIAL_IDENTITY_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

HELPER = r'''
def _overlay_lipton_official_identity(rid: str, st: dict) -> None:
    """''' + MARKER + r''' Prefer official boat/club over tracker names on new Rn rows."""
    if "lipton" not in str(rid or "").lower() or not isinstance(st, dict):
        return
    by_bow = {
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
            ident = by_bow.get(b)
            if not ident:
                continue
            boat, club = ident
            row["boat_name"] = boat
            row["club"] = club

    rt = st.get("race_times") if isinstance(st.get("race_times"), dict) else {}
    for rows in rt.values():
        _apply_rows(rows)
    _apply_rows(st.get("rankings"))


'''

OLD_DEF = '''def _write_live_race_state(regatta_id: str, state: dict) -> dict:
    rid = str(regatta_id or "").strip()
    st = dict(state or {})
    st["regatta_id"] = rid
'''

NEW_DEF = HELPER + OLD_DEF

OLD_CALL = '''    except Exception:
        pass
    if st.get("gun_at"):
        st["gun_at"] = _normalize_gun_at_iso(st.get("gun_at"))
    st["updated_at"] = datetime.now(timezone.utc).isoformat()
    p = _live_race_state_path(rid)
'''

NEW_CALL = '''    except Exception:
        pass
    try:
        _overlay_lipton_official_identity(rid, st)
    except Exception:
        pass
    if st.get("gun_at"):
        st["gun_at"] = _normalize_gun_at_iso(st.get("gun_at"))
    st["updated_at"] = datetime.now(timezone.utc).isoformat()
    p = _live_race_state_path(rid)
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n_def = text.count(OLD_DEF)
    n_call = text.count(OLD_CALL)
    if n_def != 1 or n_call != 1:
        print(f"FAIL overlay: def={n_def} call={n_call}", file=sys.stderr)
        return 1
    text = text.replace(OLD_DEF, NEW_DEF, 1)
    text = text.replace(OLD_CALL, NEW_CALL, 1)
    API_PATH.write_text(text, encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
