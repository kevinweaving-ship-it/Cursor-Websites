#!/usr/bin/env bash
# Restore pre-Grok shared header behaviour on live SailingSA.
#
# GrokBot (3 Nov) restored shared /css/gold-header.css from an Oct 30 backup during
# a /dev1/ rollback. Combined with later blocking-script extraction, Mac/Chrome
# cold loads hang on session.js and the center name stays hidden/grey until late.
#
# This script (run from Mac Mini with sailingsa_live_key — see SSH_LIVE.md):
#   1) Backs up live gold-header.css + HTML that load session.js
#   2) Installs restored gold-header.css (white name without waiting for layout JS)
#   3) Installs fixed landing-roundup-cards.js (no 98k-px track blowout)
#   4) Defers body <script src> on every HTML that loads session.js
#   5) Forces #ffffff on the session.js center-name paint (surgical, keeps live session.js)
#
#   bash sailingsa/deploy/restore-pre-grok-header-live.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEY="${SAILINGSA_SSH_KEY:-$HOME/.ssh/sailingsa_live_key}"
HOST="${SAILINGSA_SSH_HOST:-root@102.218.215.253}"
WEB_ROOT="${SAILINGSA_WEB_ROOT:-/var/www/sailingsa}"
TS="$(date +%Y%m%d%H%M%S)"

scp -i "$KEY" \
  "$ROOT/sailingsa/optimize_index_script_loading.py" \
  "$ROOT/sailingsa/frontend/css/gold-header.css" \
  "$ROOT/sailingsa/frontend/js/landing-roundup-cards.js" \
  "$HOST:/tmp/"

ssh -i "$KEY" "$HOST" bash -s <<EOF
set -euo pipefail
WEB_ROOT="$WEB_ROOT"
TS="$TS"
mkdir -p "\$WEB_ROOT/_backup-pre-grok-\$TS/css" "\$WEB_ROOT/_backup-pre-grok-\$TS/js" "\$WEB_ROOT/_backup-pre-grok-\$TS/html"

# --- gold-header ---
if [[ -f "\$WEB_ROOT/css/gold-header.css" ]]; then
  cp -a "\$WEB_ROOT/css/gold-header.css" "\$WEB_ROOT/_backup-pre-grok-\$TS/css/gold-header.css"
fi
cp -a /tmp/gold-header.css "\$WEB_ROOT/css/gold-header.css"
chown www-data:www-data "\$WEB_ROOT/css/gold-header.css" 2>/dev/null || true
echo "Installed gold-header.css (\$(wc -c < "\$WEB_ROOT/css/gold-header.css") bytes)"

# --- roundup cards ---
if [[ -f "\$WEB_ROOT/js/landing-roundup-cards.js" ]]; then
  cp -a "\$WEB_ROOT/js/landing-roundup-cards.js" "\$WEB_ROOT/_backup-pre-grok-\$TS/js/landing-roundup-cards.js"
fi
cp -a /tmp/landing-roundup-cards.js "\$WEB_ROOT/js/landing-roundup-cards.js"
chown www-data:www-data "\$WEB_ROOT/js/landing-roundup-cards.js" 2>/dev/null || true

# Bust cache on roundup + gold-header query strings inside HTML
python3 - <<'PY'
from pathlib import Path
import re
root = Path("$WEB_ROOT")
html_files = []
for p in root.rglob("*.html"):
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    if "session.js" not in txt and "gold-header.css" not in txt and "landing-roundup-cards.js" not in txt:
        continue
    html_files.append(p)

backup_html = Path("$WEB_ROOT/_backup-pre-grok-$TS/html")
backup_html.mkdir(parents=True, exist_ok=True)

# Import optimizer
import sys
sys.path.insert(0, "/tmp")
from optimize_index_script_loading import optimize_html

patched = 0
for p in html_files:
    raw = p.read_text(encoding="utf-8", errors="replace")
    rel = p.relative_to(root)
    bak = backup_html / rel
    bak.parent.mkdir(parents=True, exist_ok=True)
    bak.write_text(raw, encoding="utf-8")
    out = optimize_html(raw, extract=False)
    # cache-bust shared assets
    out = re.sub(
        r'/css/gold-header\.css[^"\']*',
        '/css/gold-header.css?v=20261116pregrok',
        out,
    )
    out = re.sub(
        r'/js/landing-roundup-cards\.js[^"\']*',
        '/js/landing-roundup-cards.js?v=roundup-pregrok-20261116',
        out,
    )
    # ensure gold-header link exists when site-header is present
    if 'class="site-header"' in out and "gold-header.css" not in out and "</head>" in out.lower():
        out = re.sub(
            r"(</head>)",
            '<link rel="stylesheet" href="/css/gold-header.css?v=20261116pregrok">\\1',
            out,
            count=1,
            flags=re.I,
        )
    if out != raw:
        p.write_text(out, encoding="utf-8")
        patched += 1
        print("patched", rel)
print("html_patched", patched, "of", len(html_files))
PY

# --- surgical session.js: force white center name (keep live session.js ahead-of-git body) ---
if [[ -f "\$WEB_ROOT/js/session.js" ]]; then
  cp -a "\$WEB_ROOT/js/session.js" "\$WEB_ROOT/_backup-pre-grok-\$TS/js/session.js"
  python3 - <<'PY'
from pathlib import Path
p = Path("$WEB_ROOT/js/session.js")
t = p.read_text(encoding="utf-8", errors="replace")
needle = "nameRow.className = 'user-center-row-name';\n                    nameRow.textContent = displayName;"
insert = (
    "nameRow.className = 'user-center-row-name';\n"
    "                    nameRow.textContent = displayName;\n"
    "                    try { nameRow.style.setProperty('color','#ffffff','important'); } catch(_c){}"
)
if "nameRow.style.setProperty('color','#ffffff'" in t:
    print("session.js name color already patched")
elif needle in t:
    p.write_text(t.replace(needle, insert, 1), encoding="utf-8")
    print("session.js name color patched")
else:
    # looser match
    import re
    t2, n = re.subn(
        r"(nameRow\.className\s*=\s*['\"]user-center-row-name['\"];\s*\n\s*nameRow\.textContent\s*=\s*displayName;)",
        r"\1\n                    try { nameRow.style.setProperty('color','#ffffff','important'); } catch(_c){}",
        t,
        count=1,
    )
    if n:
        p.write_text(t2, encoding="utf-8")
        print("session.js name color patched (regex)")
    else:
        print("WARN: session.js nameRow paint site not found; CSS white rules still installed")
PY
  chown www-data:www-data "\$WEB_ROOT/js/session.js" 2>/dev/null || true
fi

# optimizer available next to api
cp -a /tmp/optimize_index_script_loading.py "\$WEB_ROOT/optimize_index_script_loading.py"

echo "DONE backup=\$WEB_ROOT/_backup-pre-grok-\$TS"
echo "Verify: curl -sI https://sailingsa.co.za/css/gold-header.css | head -5"
echo "Verify: curl -s https://sailingsa.co.za/ | tr '\"' '\\n' | grep -E 'session\\.js|gold-header|defer' | head -30"
EOF
