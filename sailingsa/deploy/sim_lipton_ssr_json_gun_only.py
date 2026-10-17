#!/usr/bin/env python3
from pathlib import Path

p = Path(__file__).resolve().parent / "patch_lipton_ssr_json_gun_only.py"
text = p.read_text(encoding="utf-8")
assert "LIPTON_SSR_JSON_GUN_ONLY_V3" in text
assert 'if bool(lr.get("day_done")) or str(lr.get("schedule_slot") or "") == "day_close":' in text
assert "or bool(st.get(\"day_done\"))" in text
print("PASS ssr json-gun-only V3 patch strings")
