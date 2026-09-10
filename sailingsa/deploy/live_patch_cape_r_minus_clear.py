#!/usr/bin/env python3
"""Cape Classic: R− clears last-race scores. JS ccr11. Do not replace api.py."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

old_js = "club-score-edit.js?v=ccr10"
new_js = "club-score-edit.js?v=ccr11"
if new_js in src:
    print("JS_ALREADY_CCR11")
elif old_js not in src:
    raise SystemExit("ANCHOR_JS_MISSING")
else:
    src = src.replace(old_js, new_js, 1)
    print("JS_BUMPED_CCR11")

old_plus = '''            if delta > 0:
                nxt = min(current + 1, 20)
                if nxt == current:
                    raise HTTPException(status_code=400, detail="Maximum 20 races")
            elif delta < 0:'''
new_plus = '''            if delta > 0:
                nxt = min(current + 1, 20)
                if nxt == current:
                    raise HTTPException(status_code=400, detail="Maximum 20 races")
                action = "add"
            elif delta < 0:'''
old_minus = '''            elif delta < 0:
                if last_filled:
                    raise HTTPException(
                        status_code=400,
                        detail="Clear " + last_key + " first before removing that race",
                    )
                nxt = max(current - 1, 1)
                if nxt == current:
                    raise HTTPException(status_code=400, detail="Need at least R1")
            else:
                raise HTTPException(status_code=400, detail="Use +1 or -1")

            if nxt < current:'''

new_minus = '''            elif delta < 0:
                if last_filled:
                    nxt = current
                    action = "clear"
                elif current <= 1:
                    nxt = 1
                    action = "noop"
                else:
                    nxt = current - 1
                    action = "drop"
            else:
                raise HTTPException(status_code=400, detail="Use +1 or -1")

            if action == "clear" or nxt < current:'''

old_update = '''                    changed = False
                    for drop_n in range(nxt + 1, current + 1):
                        if rs.pop("R" + str(drop_n), None) is not None:
                            changed = True'''

new_update = '''                    changed = False
                    if action == "clear":
                        rs[last_key] = ""
                        changed = True
                    for drop_n in range(nxt + 1, current + 1):
                        if rs.pop("R" + str(drop_n), None) is not None:
                            changed = True'''

# live patch_fleet_races has no action = yet
if "if action == \"clear\" or nxt < current:" in src and "rs[last_key] = \"\"" in src:
    print("EP_ALREADY_CLEAR")
elif old_plus not in src or old_minus not in src:
    raise SystemExit("ANCHOR_MINUS_MISSING")
elif old_update not in src:
    raise SystemExit("ANCHOR_UPDATE_MISSING")
else:
    src = src.replace(old_plus, new_plus, 1)
    src = src.replace(old_minus, new_minus, 1)
    src = src.replace(old_update, new_update, 1)
    print("EP_CLEAR_PATCHED")

# typed 0 clears on live validate if the 0-reject path exists
old_zero = '''    if re.fullmatch(r"\\d+", v):
        n = int(v)
        if entries_n and 1 <= n <= max_pts:'''
new_zero = '''    if re.fullmatch(r"\\d+", v):
        n = int(v)
        if n == 0:
            return ""
        if entries_n and 1 <= n <= max_pts:'''
if "if n == 0:\n            return \"\"" in src:
    print("ZERO_ALREADY")
elif old_zero not in src:
    print("ZERO_ANCHOR_MISSING")
else:
    src = src.replace(old_zero, new_zero, 1)
    print("ZERO_CLEARS")

API.write_text(src, encoding="utf-8")
print("PATCHED_OK")
print("ccr11", new_js in src)
print("clear", "action == \"clear\" or nxt < current" in src)
