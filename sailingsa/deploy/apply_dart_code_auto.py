#!/usr/bin/env python3
"""Insert Dart auto remap: stored code points follow current block entries+1."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
RID = "2026-09-24-hmyc-dart-18-nationals"
FN = '''
def _refresh_block_penalty_points(cur, block_id, entries):
    entries_n = max(int(entries or 0), 0)
    pts = entries_n + 1 if entries_n else 0
    if not pts or not block_id:
        return 0
    cur.execute(
        "SELECT result_id, race_scores FROM results WHERE block_id = %s",
        (block_id,),
    )
    n = 0
    for row in cur.fetchall() or []:
        rs = row.get("race_scores") or {}
        if isinstance(rs, str):
            try:
                rs = json.loads(rs)
            except Exception:
                rs = {}
        if not isinstance(rs, dict):
            continue
        new_rs = dict(rs)
        changed = False
        total = 0.0
        for k, raw in list(new_rs.items()):
            v = str(raw or "").strip()
            code = _extract_penalty_code(v)
            if code:
                cell = _public_race_code_cell(code, entries_n)
                if cell != v:
                    new_rs[k] = cell
                    changed = True
                v = cell
            try:
                num = str(v).strip().strip("()").split()[0]
                total += float(num)
            except Exception:
                pass
        if changed:
            cur.execute(
                """
                UPDATE results
                SET race_scores = %s,
                    total_points_raw = %s,
                    nett_points_raw = %s
                WHERE result_id = %s
                """,
                (json.dumps(new_rs), total, total, row["result_id"]),
            )
            n += 1
    return n

'''
CALL = (
    '            if str(regatta_id) == "2026-09-24-hmyc-dart-18-nationals":\n'
    "                _refresh_block_penalty_points(cur, block_id, fleet_entries)\n"
)


def main() -> None:
    t = API.read_text()
    before = t
    if "_refresh_block_penalty_points" not in t:
        mark = "def _public_race_code_cell(code, entries):"
        i = t.find(mark)
        if i < 0:
            raise SystemExit("NO_CELL_FN")
        # insert after this function (next def)
        j = t.find("\n\ndef ", i + 10)
        if j < 0:
            raise SystemExit("NO_NEXT")
        t = t[:j] + "\n" + FN + t[j:]
    needle = "            fleet_entries = int((ent_row or {}).get(\"c\") or 0)\n"
    if CALL not in t:
        if needle not in t:
            raise SystemExit("NO_ASSIGN")
        t = t.replace(
            needle,
            needle + "\n" + CALL,
            1,
        )
    if t != before:
        API.write_text(t)
    t2 = API.read_text()
    print("HAS_FN", "_refresh_block_penalty_points" in t2)
    print("HAS_CALL", CALL in t2)
    print("CHANGED", t2 != before)
    print("DONE")


if __name__ == "__main__":
    main()
