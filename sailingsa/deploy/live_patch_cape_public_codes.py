#!/usr/bin/env python3
"""Live: store Cape Classic codes as public sheet cells (10.0 DSQ) and bump JS to ccr5."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

old_js = "club-score-edit.js?v=ccr4"
new_js = "club-score-edit.js?v=ccr5"
if new_js in src:
    print("JS_ALREADY_CCR5")
elif old_js not in src:
    raise SystemExit("ANCHOR_JS_MISSING")
else:
    src = src.replace(old_js, new_js, 1)
    print("JS_BUMPED_CCR5")

helpers = (
    "_RACE_PENALTY_CODES = (\"DNC\", \"DNS\", \"DNF\", \"RET\", \"DSQ\", \"UFD\", \"BFD\", \"DPI\", \"OCS\", \"NSC\", \"DNE\")\n"
    "\n"
    "\n"
    "def _normalize_race_score_value(raw) -> str:\n"
)
helpers_new = (
    "_RACE_PENALTY_CODES = (\"DNC\", \"DNS\", \"DNF\", \"RET\", \"DSQ\", \"UFD\", \"BFD\", \"DPI\", \"OCS\", \"NSC\", \"DNE\")\n"
    "_RACE_PENALTY_CODE_RE = re.compile(\n"
    "    r\"(?:^|\\d(?:\\.\\d+)?)(\" + \"|\".join(_RACE_PENALTY_CODES) + r\")$\",\n"
    "    re.I,\n"
    ")\n"
    "\n"
    "\n"
    "def _extract_penalty_code(raw):\n"
    "    bare = re.sub(r\"\\s+\", \"\", str(raw or \"\").strip().strip(\"()\").strip()).upper()\n"
    "    if not bare:\n"
    "        return None\n"
    "    if bare in _RACE_PENALTY_CODES:\n"
    "        return bare\n"
    "    m = _RACE_PENALTY_CODE_RE.search(bare)\n"
    "    return m.group(1).upper() if m else None\n"
    "\n"
    "\n"
    "def _public_race_code_cell(code, entries):\n"
    "    pts = max(int(entries or 0), 0) + 1\n"
    "    return f\"{pts}.0 {str(code or '').strip().upper()}\"\n"
    "\n"
    "\n"
    "def _normalize_race_score_value(raw) -> str:\n"
    "    v = str(raw or \"\").strip()\n"
    "    if not v:\n"
    "        return \"\"\n"
    "    code = _extract_penalty_code(v)\n"
    "    if code:\n"
    "        return code\n"
    "    bare = v.strip(\"()\").strip()\n"
    "    if re.fullmatch(r\"\\d+(?:\\.\\d+)?\", bare):\n"
    "        return str(int(float(bare)))\n"
    "    return bare\n"
    "\n"
    "\n"
    "def _normalize_race_score_value_UNUSED(raw) -> str:\n"
)

if "def _extract_penalty_code(" in src and "def _public_race_code_cell(" in src:
    print("HELPERS_ALREADY")
elif helpers not in src:
    raise SystemExit("ANCHOR_HELPERS_MISSING")
else:
    src = src.replace(helpers, helpers_new, 1)
    # Remove the leftover unused stub by restoring unique_place next...
    # The old normalize body still follows UNUSED. Cut it at _race_score_is_code.
    old_tail = (
        "def _normalize_race_score_value_UNUSED(raw) -> str:\n"
        "    v = str(raw or \"\").strip()\n"
        "    if not v:\n"
        "        return \"\"\n"
        "    bare = v.strip(\"()\").strip()\n"
        "    up = bare.upper()\n"
        "    if up in _RACE_PENALTY_CODES:\n"
        "        return up\n"
        "    if re.fullmatch(r\"\\d+\", bare):\n"
        "        return str(int(bare))\n"
        "    return bare\n"
        "\n"
        "\n"
        "def _race_score_is_code(value: str) -> bool:\n"
        "    return _normalize_race_score_value(value) in _RACE_PENALTY_CODES\n"
    )
    new_tail = (
        "def _race_score_is_code(value: str) -> bool:\n"
        "    return _extract_penalty_code(value) is not None\n"
    )
    if old_tail not in src:
        raise SystemExit("ANCHOR_TAIL_MISSING")
    src = src.replace(old_tail, new_tail, 1)
    print("HELPERS_PATCHED")

old_ret = "    if _race_score_is_code(v):\n        return v\n"
new_ret = (
    "    code = _extract_penalty_code(v)\n"
    "    if code:\n"
    "        return _public_race_code_cell(code, entries_n)\n"
)
if new_ret in src:
    print("VALIDATE_ALREADY")
elif old_ret not in src:
    raise SystemExit("ANCHOR_VALIDATE_MISSING")
else:
    src = src.replace(old_ret, new_ret, 1)
    print("VALIDATE_PATCHED")

API.write_text(src, encoding="utf-8")
print("PATCHED_OK")
print("extract", "def _extract_penalty_code(" in src)
print("ccr5", new_js in src)
