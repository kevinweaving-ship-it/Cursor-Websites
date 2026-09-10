#!/usr/bin/env python3
"""Cape Classic: boats missing the current race stay last. Do not replace api.py."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

anchor = '''            (block_id,),
        )

    if not str(regatta_id or "").startswith("2026-09-13-zvyc-cape-classic"):
        _ensure_snapshot_integrity(conn, regatta_id)
'''
insert = '''            (block_id,),
        )

        if str(regatta_id or "").startswith("2026-09-13-zvyc-cape-classic"):
            cur.execute(
                "SELECT result_id, nett_points_raw, race_scores FROM results WHERE block_id = %s",
                (block_id,),
            )
            parsed = []
            max_idx = 0
            for r in cur.fetchall() or []:
                rs = r.get("race_scores") or {}
                if isinstance(rs, str):
                    rs = json.loads(rs)
                if not isinstance(rs, dict):
                    rs = {}
                parsed.append((r["result_id"], r.get("nett_points_raw"), rs))
                for k, v in rs.items():
                    if not str(v or "").strip():
                        continue
                    ku = str(k or "").strip().upper()
                    if ku.startswith("R") and ku[1:].isdigit():
                        max_idx = max(max_idx, int(ku[1:]))

            def _has(rs, n):
                if not n:
                    return True
                return bool(str((rs or {}).get("R" + str(n)) or "").strip())

            def _key(item):
                rid, nett, rs = item
                waiting = 0 if _has(rs, max_idx) else 1
                try:
                    nf = float(nett) if nett is not None else 0.0
                except Exception:
                    nf = 0.0
                unscored = 1 if (nett is None or nf == 0.0) else 0
                return (waiting, unscored, nf, int(rid))

            parsed.sort(key=_key)
            for i, item in enumerate(parsed, start=1):
                cur.execute(
                    "UPDATE results SET rank = %s WHERE result_id = %s",
                    (i, item[0]),
                )

    if not str(regatta_id or "").startswith("2026-09-13-zvyc-cape-classic"):
        _ensure_snapshot_integrity(conn, regatta_id)
'''

if "waiting = 0 if _has(rs, max_idx) else 1" in src:
    print("WAIT_RANK_ALREADY")
elif anchor not in src:
    raise SystemExit("ANCHOR_MISSING")
else:
    src = src.replace(anchor, insert, 1)
    print("WAIT_RANK_INSERTED")

API.write_text(src, encoding="utf-8")
print("ok", "waiting = 0 if _has(rs, max_idx) else 1" in src)
