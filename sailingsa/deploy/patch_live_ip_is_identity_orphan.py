#!/usr/bin/env python3
from pathlib import Path
import py_compile
import subprocess

p = Path("/var/www/sailingsa/api/api.py")
t = p.read_text()
old = """                    if is_bot:
                        who = f\"Bot {vid}\" if vid else \"Bot\"
                        who_href = \"\"
                    else:
                        who = likely_name if likely_name else (f\"Guest {vid}\" if vid else \"Guest\")
                        who_href = f\"/sailor/{likely_slug}\" if likely_slug else \"\"
"""
new = """                    if is_bot:
                        who = f\"Bot {ip}\" if ip else (f\"Bot {vid}\" if vid else \"Bot\")
                        who_href = \"\"
                    else:
                        who = f\"Guest {ip}\" if ip else (f\"Guest {vid}\" if vid else \"Guest\")
                        who_href = \"\"
"""
if old not in t:
    raise SystemExit("orphan who missing")
t = t.replace(old, new, 1)
old2 = """                        \"guessed\": bool(likely_name) and not is_bot,
                        \"likely_hits\": int(likely.get(\"hits\") or 0) if not is_bot else 0,
                        \"sas_id\": (likely.get(\"sas_id\") or \"\") if not is_bot else \"\",
"""
new2 = """                        \"guessed\": False,
                        \"likely_name\": likely_name if not is_bot else \"\",
                        \"likely_slug\": likely_slug if not is_bot else \"\",
                        \"likely_hits\": int(likely.get(\"hits\") or 0) if not is_bot else 0,
                        \"sas_id\": (likely.get(\"sas_id\") or \"\") if not is_bot else \"\",
"""
if old2 in t:
    t = t.replace(old2, new2, 1)
    print("orphan append fixed")
p.write_text(t)
py_compile.compile(str(p), doraise=True)
chunk = t[t.find("def lean_traffic_api_live") : t.find("def lean_traffic_api_top")]
print("who=likely_name left", chunk.count("who = likely_name"))
print("Guest {ip}", chunk.count("Guest {ip}"))
subprocess.check_call(["systemctl", "restart", "sailingsa-api"])
print("OK")
