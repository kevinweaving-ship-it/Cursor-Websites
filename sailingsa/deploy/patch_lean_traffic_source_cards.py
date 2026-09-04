#!/usr/bin/env python3
"""Add Direct / Google / Facebook first-touch source cards on /traffic (order: Direct, Google, FB).

Applied live 2026-08-25. Re-run only if id=\"kDirect\" missing from lean traffic HTML.
"""
from __future__ import annotations
import shutil, time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

def must(text, old, new, label):
    if text.count(old) != 1:
        raise SystemExit(f"FAIL {label}: count={text.count(old)}")
    return text.replace(old, new, 1)

def main():
    text = API.read_text(encoding="utf-8", errors="replace")
    if 'id="kDirect"' in text and "direct_landings" in text:
        print("ALREADY_PATCHED"); return
    bak = Path(f"/root/backups/api.py.source_cards.{time.strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    text = must(text,
'''    <div class="kpi"><div class="l">Google landings</div><div class="v" id="kGoogle">—</div><div class="s" id="kGoogleSub">referrer / gclid</div></div>
    <div class="kpi"><div class="l">Facebook landings</div><div class="v" id="kFb">—</div><div class="s" id="kFbSub">referrer / fbclid</div></div>
''',
'''    <div class="kpi"><div class="l">Direct</div><div class="v" id="kDirect">—</div><div class="s" id="kDirectSub">no external referrer</div></div>
    <div class="kpi"><div class="l">Google</div><div class="v" id="kGoogle">—</div><div class="s" id="kGoogleSub">via Google</div></div>
    <div class="kpi"><div class="l">Facebook</div><div class="v" id="kFb">—</div><div class="s" id="kFbSub">via Facebook</div></div>
''', "html")
    print("HTML OK — remaining overview/JS changes require matching pre-source-card api.py; prefer restore from live backup if needed.")
    API.write_text(text, encoding="utf-8")
    print("PARTIAL — overview SQL/JS already on live after full agent patch")

if __name__ == "__main__":
    main()
