#!/usr/bin/env python3
"""Patch live api.py: applying LIVE overnight must keep last completed Rn.

Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_LIVE_KEEP_LAST_RN_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD = '''            lr["applied"] = False
            lr["rankings"] = []
            # Prefer next empty Rn for header / sheet (R5 after R4 finishes).
            try:
                lr["race_key"] = _live_race_next_race_key(rid)
            except Exception:
                pass
            _write_live_race_state(rid, lr)
'''

NEW = '''            lr["applied"] = False
            lr["rankings"] = []
            overnight = bool(lr.get("day_done")) or str(lr.get("schedule_slot") or "") == "day_close"
            if overnight:
                # ''' + MARKER + '''
                lr["phase"] = "finished" if had_finishes else "idle"
                try:
                    rt = lr.get("race_times") if isinstance(lr.get("race_times"), dict) else {}
                    filled_n = []
                    for k, rows in (rt or {}).items():
                        m = re.match(r"^R(\\d+)$", str(k), re.I)
                        if not m:
                            continue
                        if isinstance(rows, list) and any(
                            isinstance(r, dict)
                            and (r.get("place") is not None or r.get("finish_ms") is not None)
                            for r in rows
                        ):
                            filled_n.append(int(m.group(1)))
                    if filled_n:
                        lr["race_key"] = "R" + str(max(filled_n))
                except Exception:
                    pass
            else:
                # Prefer next empty Rn for header / sheet (R5 after R4 finishes).
                try:
                    lr["race_key"] = _live_race_next_race_key(rid)
                except Exception:
                    pass
            _write_live_race_state(rid, lr)
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n = text.count(OLD)
    if n != 1:
        print(f"FAIL live-branch: found {n}", file=sys.stderr)
        return 1
    API_PATH.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
