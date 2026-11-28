#!/usr/bin/env python3
"""Surgical live api.py patch: Staff list only for logged-in users; same sign-in popup."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

OLD_CSS = '''    ".cape-crew .helm-col a{color:#1a2750;font-weight:700;text-decoration:underline}"
    ".cape-crew .fleet-title-row a{color:#1a2750;font-weight:bold;text-decoration:none}"
    ".cape-crew .fleet-title-row a:hover{color:#e65100}"
    "@media print{.cape-crew-sa{display:none!important}.cape-crew--hidden{display:none!important}}"
)'''

NEW_CSS = '''    ".cape-crew .helm-col a{color:#1a2750;font-weight:700;text-decoration:underline}"
    ".cape-crew .fleet-title-row a{color:#1a2750;font-weight:bold;text-decoration:none}"
    ".cape-crew .fleet-title-row a:hover{color:#e65100}"
    ".cape-crew .table-wrapper{display:none}"
    ".cape-crew.cape-crew--authed .table-wrapper{display:block}"
    ".regatta-page--super-admin-edit .cape-crew .table-wrapper,"
    ".regatta-page--club-score-edit .cape-crew .table-wrapper,"
    ".cape-crew--admin .table-wrapper{display:block}"
    ".ssa-wa-gate{display:none;position:fixed;inset:0;z-index:4000;background:rgba(0,0,0,.55);align-items:center;justify-content:center;padding:20px;box-sizing:border-box;}"
    ".ssa-wa-gate.is-open{display:flex;}"
    ".ssa-wa-gate-card{background:#fff;border:1.5px solid #1a2750;border-radius:8px;padding:16px 18px;max-width:300px;width:100%;box-shadow:0 8px 28px rgba(0,0,0,.28);box-sizing:border-box;}"
    ".ssa-wa-gate-card p{margin:0 0 14px;font:600 14px/1.35 Arial,Helvetica,sans-serif;color:#1a2750;}"
    ".ssa-wa-gate-actions{display:flex;flex-direction:column;gap:8px;}"
    ".ssa-wa-gate-actions a,.ssa-wa-gate-actions button{display:flex;align-items:center;justify-content:center;min-height:44px;padding:10px 12px;border-radius:6px;font:700 14px/1.2 Arial,Helvetica,sans-serif;text-decoration:none;box-sizing:border-box;cursor:pointer;}"
    ".ssa-wa-gate-actions a.ssa-wa-gate-in{background:#1a2750;color:#fff;border:1px solid #1a2750;}"
    ".ssa-wa-gate-actions a.ssa-wa-gate-up{background:#e65100;color:#fff;border:1px solid #e65100;}"
    ".ssa-wa-gate-actions button{background:#fff;color:#1a2750;border:1px solid #1a2750;}"
    "@media print{.cape-crew-sa{display:none!important}.cape-crew--hidden{display:none!important}}"
)'''

OLD_TAIL = '''        + sa_bar
        + "</div>"
    )


def _regatta_print_share_buttons_html() -> str:'''

NEW_TAIL = r'''        + sa_bar
        + "</div>"
        + _CAPE_CLASSIC_CREW_LOGIN_GATE_JS
    )


def _regatta_print_share_buttons_html() -> str:'''

GATE_JS_ASSIGN = r'''
_CAPE_CLASSIC_CREW_LOGIN_GATE_JS = (
    "<script>(function(){"
    "var root=document.getElementById('capeClassicCrew');if(!root)return;"
    "var MSG='You must be signed up and logged in to see the staff list.';"
    "function hideGate(){var el=document.getElementById('ssaWaGate');if(el)el.classList.remove('is-open');}"
    "function showGate(msg){"
    "if(typeof window.ssaShowLoginGate==='function'){window.ssaShowLoginGate(msg||MSG);return;}"
    "msg=msg||MSG;var el=document.getElementById('ssaWaGate');"
    "if(!el){var ret=encodeURIComponent(String(location.href||'/'));"
    "el=document.createElement('div');el.id='ssaWaGate';el.className='ssa-wa-gate';"
    "el.setAttribute('role','dialog');el.innerHTML='<div class=\"ssa-wa-gate-card\"><p></p>"
    "<div class=\"ssa-wa-gate-actions\"><a class=\"ssa-wa-gate-in\" href=\"/login.html?returnTo='+ret+'\">Login</a>"
    "<a class=\"ssa-wa-gate-up\" href=\"/signup.html?signup=1&amp;returnTo='+ret+'\">Sign Up</a>"
    "<button type=\"button\" data-wa-gate-close=\"1\">Close</button></div></div>';"
    "document.body.appendChild(el);"
    "el.addEventListener('click',function(e){if(e.target===el)hideGate();});"
    "var c=el.querySelector('[data-wa-gate-close]');if(c)c.addEventListener('click',hideGate);}"
    "var p=el.querySelector('.ssa-wa-gate-card p');if(p)p.textContent=msg;el.classList.add('is-open');}"
    "fetch('/auth/session?path='+encodeURIComponent(location.pathname||'/'),{credentials:'include',cache:'no-store'})"
    ".then(function(r){return r.ok?r.json():{valid:false};})"
    ".then(function(s){"
    "if(s&&s.valid===true){root.classList.add('cape-crew--authed');return;}"
    "var hit=root.querySelector('.fleet-title-row');"
    "if(!hit||hit.getAttribute('data-staff-gate')==='1')return;"
    "hit.setAttribute('data-staff-gate','1');hit.style.cursor='pointer';"
    "hit.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();showGate(MSG);},true);"
    "}).catch(function(){});"
    "})();</script>"
)


'''

OLD_JS = "regatta-slot-card.js?v=20260912wa6"
NEW_JS = "regatta-slot-card.js?v=20260912wa7"


def apply(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "_CAPE_CLASSIC_CREW_LOGIN_GATE_JS" in text:
        raise SystemExit(f"{path}: already patched")
    if text.count(OLD_CSS) != 1:
        raise SystemExit(f"{path}: css count {text.count(OLD_CSS)}")
    if text.count(OLD_TAIL) != 1:
        raise SystemExit(f"{path}: tail count {text.count(OLD_TAIL)}")
    if text.count(OLD_JS) != 1:
        raise SystemExit(f"{path}: js ver count {text.count(OLD_JS)}")
    text = text.replace(OLD_CSS, NEW_CSS, 1)
    text = text.replace(OLD_TAIL, NEW_TAIL, 1)
    text = text.replace(
        "_CAPE_CLASSIC_CREW_CSS = (",
        GATE_JS_ASSIGN + "_CAPE_CLASSIC_CREW_CSS = (",
        1,
    )
    text = text.replace(OLD_JS, NEW_JS, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)


def main() -> int:
    apply(Path(sys.argv[1]) if len(sys.argv) > 1 else API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
