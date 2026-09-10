#!/usr/bin/env python3
"""Cape Classic: discard only after 1st has R5/R10/R15; always pick current worst. Do not replace api.py."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

old_cape = """        # Cape Classic: discard only after 5 races with scores. Empty R+ columns do not count.
        if str(regatta_id or "").startswith("2026-09-13-zvyc-cape-classic"):
            scored = set()
            max_idx = 0
            for res in all_results:
                rs = res.get("race_scores") or {}
                if isinstance(rs, str):
                    rs = json.loads(rs)
                if not isinstance(rs, dict):
                    continue
                for k, v in rs.items():
                    if not str(v or "").strip():
                        continue
                    ku = str(k or "").strip().upper()
                    if ku.startswith("R") and ku[1:].isdigit():
                        scored.add(ku)
                        max_idx = max(max_idx, int(ku[1:]))
            completed = len(scored)
            max_rs = max(int(max_idx or 0), 1)
            discard_count = completed // 5 if completed else 0
"""

new_cape = """        # Cape Classic: 1 discard after 1st has Race 5; 2 after Race 10; 3 after Race 15.
        if str(regatta_id or "").startswith("2026-09-13-zvyc-cape-classic"):
            maps = []
            max_idx = 0
            for res in all_results:
                rs = res.get("race_scores") or {}
                if isinstance(rs, str):
                    rs = json.loads(rs)
                if not isinstance(rs, dict):
                    rs = {}
                maps.append(rs)
                for k, v in rs.items():
                    if not str(v or "").strip():
                        continue
                    ku = str(k or "").strip().upper()
                    if ku.startswith("R") and ku[1:].isdigit():
                        max_idx = max(max_idx, int(ku[1:]))
            max_rs = max(int(max_idx or 0), 1)
            entries_n = max(int(entries_plus_one) - 1, 0)
            leader = None
            leader_nett = None
            for rs in maps:
                tot = 0.0
                any_s = False
                for i in range(1, max_rs + 1):
                    val = str((rs or {}).get(f"R{i}") or "").strip()
                    if not val:
                        continue
                    any_s = True
                    if re.search(r"[A-Za-z]", val):
                        tot += float(entries_n + 1)
                    else:
                        m = re.search(r"[\\d.]+", val)
                        if m:
                            tot += abs(float(m.group(0)))
                if not any_s:
                    continue
                if leader_nett is None or tot < leader_nett:
                    leader_nett = tot
                    leader = rs
            discard_count = 0
            if leader:
                for gate in (5, 10, 15, 20):
                    if str(leader.get(f"R{gate}") or "").strip():
                        discard_count += 1
"""

if "1 discard after 1st has Race 5" in src:
    print("CAPE_ALREADY")
elif old_cape not in src:
    raise SystemExit("ANCHOR_CAPE_MISSING")
else:
    src = src.replace(old_cape, new_cape, 1)
    print("CAPE_GATES")

old_br = """            res_discard_idxs = set()
            if discard_count > 0 and res_scores_list:
                bracketed = [i for i, s in enumerate(res_scores_list) if s["is_br"]]
                for idx in bracketed[:discard_count]:
                    res_discard_idxs.add(idx)

                remaining_needed = discard_count - len(res_discard_idxs)
                if remaining_needed > 0:
                    remaining = [
                        (i, s) for i, s in enumerate(res_scores_list) if i not in res_discard_idxs
                    ]
                    remaining.sort(key=lambda x: x[1]["val"], reverse=True)
                    for i in range(min(remaining_needed, len(remaining))):
                        res_discard_idxs.add(remaining[i][0])
"""

new_br = """            res_discard_idxs = set()
            if discard_count > 0 and res_scores_list:
                remaining = list(enumerate(res_scores_list))
                remaining.sort(key=lambda x: (-x[1]["val"], -int(str(x[1]["key"])[1:] or 0)))
                for i in range(min(discard_count, len(remaining))):
                    res_discard_idxs.add(remaining[i][0])
"""

if "(-x[1][\"val\"], -int(str(x[1][\"key\"])[1:] or 0))" in src:
    print("WORST_ALREADY")
elif old_br not in src:
    raise SystemExit("ANCHOR_BRACKET_MISSING")
else:
    src = src.replace(old_br, new_br, 1)
    print("WORST_RECALC")

if "bracketed = [i for i, s in enumerate(res_scores_list) if s[\"is_br\"]]" in src:
    raise SystemExit("STICKY_STILL_PRESENT")

API.write_text(src, encoding="utf-8")
print("cape_gate", "1 discard after 1st has Race 5" in src)
print("no_sticky", "bracketed = [i for i, s in enumerate(res_scores_list) if s[\"is_br\"]]" not in src)
