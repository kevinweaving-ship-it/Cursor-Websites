#!/usr/bin/env python3
"""Patch live api.py: Lipton apply-finishes updates as_at_time (SAST).

Status line is DB as_at, never wall-clock JS. After R6 lands, the stamp must
move. Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_APPLY_ASAT_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD = '''        _recalculate_fleet_block_scoring_and_ranks(conn, block_id, rid)
        conn.commit()
    return {
        "ok": True,
        "regatta_id": rid,
        "race_key": rk,
'''

NEW = '''        _recalculate_fleet_block_scoring_and_ranks(conn, block_id, rid)
        if "lipton" in rid.lower():
            # ''' + MARKER + ''' snapshot time for "Results are … as at"
            try:
                as_at = _regatta_sa_now()
            except Exception:
                as_at = datetime.now(timezone(timedelta(hours=2)))
            with conn.cursor() as cur2:
                cur2.execute(
                    "UPDATE results SET as_at_time = %s WHERE regatta_id::text = %s",
                    (as_at, rid),
                )
                try:
                    cur2.execute(
                        "UPDATE regattas SET as_at_time = %s WHERE regatta_id::text = %s",
                        (as_at, rid),
                    )
                except Exception:
                    pass
        conn.commit()
    return {
        "ok": True,
        "regatta_id": rid,
        "race_key": rk,
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n = text.count(OLD)
    if n != 1:
        print(f"FAIL apply-asat: found {n}", file=sys.stderr)
        return 1
    API_PATH.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
