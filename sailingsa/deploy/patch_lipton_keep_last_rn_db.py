#!/usr/bin/env python3
"""Overnight last-Rn must include DB race_scores (R6 applied, race_times only R4/R5)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

MARKER = "LIPTON_KEEP_LAST_RN_DB_V1"
API_PATH = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")

OLD = '''                    rt = lr.get("race_times") if isinstance(lr.get("race_times"), dict) else {}
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
'''

NEW = '''                    rt = lr.get("race_times") if isinstance(lr.get("race_times"), dict) else {}
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
                    # LIPTON_KEEP_LAST_RN_DB_V1 official scores may exist without race_times (R6).
                    try:
                        with psycopg2.connect(DB_URL) as _conn:
                            with _conn.cursor() as _cur:
                                _cur.execute(
                                    """
                                    SELECT r.race_scores FROM results r
                                    WHERE r.regatta_id::text = %s
                                      AND (r.raced IS DISTINCT FROM FALSE)
                                    """,
                                    (rid,),
                                )
                                for _row in _cur.fetchall():
                                    _rs = _row[0]
                                    if isinstance(_rs, str):
                                        try:
                                            _rs = json.loads(_rs)
                                        except Exception:
                                            _rs = None
                                    if isinstance(_rs, dict):
                                        for _k in _rs.keys():
                                            _m = re.match(r"^R(\\d+)$", str(_k), re.I)
                                            if _m:
                                                filled_n.append(int(_m.group(1)))
                    except Exception:
                        pass
                    if filled_n:
                        lr["race_key"] = "R" + str(max(filled_n))
'''


def main() -> int:
    text = API_PATH.read_text(encoding="utf-8")
    if MARKER in text:
        print("already", MARKER)
        print("ok", API_PATH)
        return 0
    n = text.count(OLD)
    if n != 1:
        print(f"FAIL keep-last-db: found {n}", file=sys.stderr)
        return 1
    tmp = Path("/tmp") / (API_PATH.name + ".keeprndb")
    tmp.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    rc = os.system(f"cp {tmp} {API_PATH}")
    if rc != 0:
        print("FAIL cp", rc, file=sys.stderr)
        return 1
    print("patched", MARKER)
    print("ok", API_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
