#!/usr/bin/env bash
# On live server: add light-green for events with results to already-deployed sa-home-regatta cards.
# Safe to re-run. Does not replace full api.py.
set -euo pipefail
API="${1:-/var/www/sailingsa/api.py}"
cp -a "$API" "${API}.bak.has-results.$(date +%Y%m%d%H%M%S)"
python3 - <<PY
from pathlib import Path
p = Path("$API")
t = p.read_text()
css = """.sa-home-regatta-card--has-results{background:#dcfce7;border-color:#86efac;}
.sa-home-regatta-card--has-results .sa-home-regatta-btn{border-color:#4ade80;background:#f0fdf4;color:#166534;}
"""
if "sa-home-regatta-card--has-results" not in t:
    needle = ".events-cards.sa-home-regatta-list { display: flex; flex-direction: column; gap: 10px; }"
    if needle in t:
        t = t.replace(needle, needle + "\n" + css, 1)
    else:
        t = t.replace(".sa-home-regatta-card{", css + ".sa-home-regatta-card{", 1)
old = "return '<article class=\"sa-home-regatta-card\" data-panel=\"'"
new = """var hasRes = !!e.result_yes;
    var cardCls = 'sa-home-regatta-card' + (hasRes ? ' sa-home-regatta-card--has-results' : '');
    return '<article class="' + cardCls + '" data-panel="'"""
# live may already use single-quoted return
count = 0
import re
def repl(m):
    global count
    count += 1
    return ("var hasRes = !!e.result_yes;\n"
            "    var cardCls = 'sa-home-regatta-card' + (hasRes ? ' sa-home-regatta-card--has-results' : '');\n"
            "    return '<article class=\"' + cardCls + '\" data-panel=\"' + esc(panelId)")
# Match: return '<article class="sa-home-regatta-card" data-panel="' + esc(panelId)
pat = re.compile(r"return '<article class=\"sa-home-regatta-card\" data-panel=\"' \+ esc\(panelId\)")
t2, n = pat.subn(r"var hasRes = !!e.result_yes;\n    var cardCls = 'sa-home-regatta-card' + (hasRes ? ' sa-home-regatta-card--has-results' : '');\n    return '<article class=\"' + cardCls + '\" data-panel=\"' + esc(panelId)", t)
print("css ok", "sa-home-regatta-card--has-results" in t2, "js replacements", n)
p.write_text(t2)
PY
systemctl restart sailingsa-api
echo "Done. Hard-refresh /events"
