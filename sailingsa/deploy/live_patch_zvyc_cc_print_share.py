#!/usr/bin/env python3
"""Add Share next to Print on live standalone /regatta pages (ZVYC Cape Classic).

Surgical replace only — does not overwrite live api.py wholesale.
Run on the server after copying this file, then restart sailingsa-api.
"""

from pathlib import Path

LIVE_API = Path("/var/www/sailingsa/api/api.py")
OLD = '<div class="action-buttons"><button class="action-button" onclick="window.print()">Print</button></div>'
NEW = (
    '<div class="action-buttons">'
    '<button type="button" class="action-button" onclick="window.print()">Print</button>'
    '<button type="button" class="action-button" id="regattaShareBtn">Share</button>'
    "</div>"
    "<script>(function(){"
    "var b=document.getElementById('regattaShareBtn');"
    "if(!b)return;"
    "b.addEventListener('click',function(){"
    "var t=document.title||'SailingSA',u=location.href;"
    "if(navigator.share){navigator.share({title:t,url:u}).catch(function(){});return;}"
    "function copied(){b.textContent='Link copied';setTimeout(function(){b.textContent='Share';},1600);}"
    "if(navigator.clipboard&&navigator.clipboard.writeText){"
    "navigator.clipboard.writeText(u).then(copied).catch(function(){prompt('Copy this link:',u);});"
    "return;}"
    "prompt('Copy this link:',u);"
    "});"
    "})();</script>"
)


def main() -> None:
    text = LIVE_API.read_text(encoding="utf-8")
    if "id='regattaShareBtn'" in text or 'id="regattaShareBtn"' in text:
        print("already patched")
        return
    if OLD not in text:
        raise SystemExit("Print-only action-buttons HTML not found")
    count = text.count(OLD)
    LIVE_API.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print(f"patched Print/Share in {count} place(s)")


if __name__ == "__main__":
    main()
