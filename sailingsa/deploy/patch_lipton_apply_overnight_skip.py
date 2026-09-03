#!/usr/bin/env python3
"""Patch live api.py: skip Lipton apply-finishes while harbour is closed.

Overnight leftover rankings must not overwrite R5/R6 in the DB.
Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_APPLY_OVERNIGHT_SKIP_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD = '''    st = _read_live_race_state(rid)
    race_key = str(body.get("race_key") or st.get("race_key") or "").strip().upper() or _live_race_next_race_key(rid)
    rankings = body.get("rankings") if isinstance(body.get("rankings"), list) else (st.get("rankings") or [])
'''

NEW = '''    st = _read_live_race_state(rid)
    if _lipton_overnight_harbour(rid, st):
        # ''' + MARKER + '''
        return {"ok": True, "overnight": True, "skipped": True, "regatta_id": rid}
    race_key = str(body.get("race_key") or st.get("race_key") or "").strip().upper() or _live_race_next_race_key(rid)
    rankings = body.get("rankings") if isinstance(body.get("rankings"), list) else (st.get("rankings") or [])
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n = text.count(OLD)
    if n != 1:
        print(f"FAIL apply-skip: found {n}", file=sys.stderr)
        return 1
    API_PATH.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
