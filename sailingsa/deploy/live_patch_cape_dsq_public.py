#!/usr/bin/env python3
"""Cape Classic: store codes as '15 DSQ'; discarded '(15 DSQ)'. Bump JS ccr8."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

old_js = "club-score-edit.js?v=ccr7"
new_js = "club-score-edit.js?v=ccr8"
if new_js in src:
    print("JS_ALREADY_CCR8")
elif old_js not in src:
    raise SystemExit("ANCHOR_JS_MISSING")
else:
    src = src.replace(old_js, new_js, 1)
    print("JS_BUMPED_CCR8")

old_br = (
    "                if should_be_bracketed and not is_currently_bracketed:\n"
    "                    res_race_scores[rkey] = f\"({current_val})\"\n"
    "                elif not should_be_bracketed and is_currently_bracketed:\n"
    "                    res_race_scores[rkey] = current_val.strip(\"()\")\n"
)
new_br = (
    "                if str(regatta_id or \"\").startswith(\"2026-09-13-zvyc-cape-classic\"):\n"
    "                    code = _extract_penalty_code(current_val)\n"
    "                    if code:\n"
    "                        current_val = _public_race_code_cell(code, entries_plus_one - 1)\n"
    "                    else:\n"
    "                        current_val = current_val.strip(\"()\").strip()\n"
    "                    res_race_scores[rkey] = (\n"
    "                        f\"({current_val})\" if should_be_bracketed else current_val\n"
    "                    )\n"
    "                elif should_be_bracketed and not is_currently_bracketed:\n"
    "                    res_race_scores[rkey] = f\"({current_val})\"\n"
    "                elif not should_be_bracketed and is_currently_bracketed:\n"
    "                    res_race_scores[rkey] = current_val.strip(\"()\")\n"
)
if "Cape Classic public code cell" in src or (
    "if str(regatta_id or \"\").startswith(\"2026-09-13-zvyc-cape-classic\"):\n"
    "                    code = _extract_penalty_code(current_val)"
    in src
):
    print("BR_ALREADY")
elif old_br not in src:
    raise SystemExit("ANCHOR_BR_MISSING")
else:
    src = src.replace(old_br, new_br, 1)
    print("BR_PATCHED")

API.write_text(src, encoding="utf-8")
print("PATCHED_OK")
print("ccr8", new_js in src)
