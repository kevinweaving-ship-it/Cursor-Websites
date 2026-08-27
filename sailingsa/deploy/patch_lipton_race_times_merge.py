#!/usr/bin/env python3
"""Patch live api.py: keep prior Rn when tracker starts the next race with pending rows.

Incoming R6 without finishes used to replace race_times with disk R4+R5 and drop R6.
Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARKER = "LIPTON_RACE_TIMES_MERGE_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD = '''        prev_rt = (prev or {}).get("race_times") if isinstance((prev or {}).get("race_times"), dict) else None
        cur_rt = st.get("race_times") if isinstance(st.get("race_times"), dict) else None
        if prev_rt and (not cur_rt or not any(
            isinstance(v, list) and any(isinstance(r, dict) and (r.get("place") is not None or r.get("finish_ms") is not None) for r in v)
            for v in prev_rt.values()
        ) is False):
            # If incoming has no finished rows but disk does, keep disk times (merge keys).
            has_fin = False
            if cur_rt:
                for v in cur_rt.values():
                    if isinstance(v, list) and any(
                        isinstance(r, dict) and (r.get("place") is not None or r.get("finish_ms") is not None)
                        for r in v
                    ):
                        has_fin = True
                        break
            if not has_fin:
                st["race_times"] = prev_rt
            else:
                merged = dict(prev_rt)
                merged.update(cur_rt or {})
                st["race_times"] = merged
'''

NEW = '''        prev_rt = (prev or {}).get("race_times") if isinstance((prev or {}).get("race_times"), dict) else None
        cur_rt = st.get("race_times") if isinstance(st.get("race_times"), dict) else None
        if prev_rt:
            # ''' + MARKER + ''' keep finished Rn; do not drop pending next-Rn rows.
            def _rt_has_fin(rows) -> bool:
                return isinstance(rows, list) and any(
                    isinstance(r, dict) and (r.get("place") is not None or r.get("finish_ms") is not None)
                    for r in rows
                )
            merged = dict(prev_rt)
            for k, rows in (cur_rt or {}).items():
                if _rt_has_fin(rows) or not _rt_has_fin(merged.get(k)):
                    merged[k] = rows
            st["race_times"] = merged
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n = text.count(OLD)
    if n != 1:
        print(f"FAIL merge: found {n}", file=sys.stderr)
        return 1
    API_PATH.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
