#!/usr/bin/env python3
"""Login-gate popup uses the same Sign Up / Login header boxes."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

OLD_CSS = '''    ".ssa-wa-gate-actions{display:flex;flex-direction:column;gap:8px;}"
    ".ssa-wa-gate-actions a,.ssa-wa-gate-actions button{display:flex;align-items:center;justify-content:center;min-height:44px;padding:10px 12px;border-radius:6px;font:700 14px/1.2 Arial,Helvetica,sans-serif;text-decoration:none;box-sizing:border-box;cursor:pointer;}"
    ".ssa-wa-gate-actions a.ssa-wa-gate-in{background:#1a2750;color:#fff;border:1px solid #1a2750;}"
    ".ssa-wa-gate-actions a.ssa-wa-gate-up{background:#e65100;color:#fff;border:1px solid #e65100;}"
    ".ssa-wa-gate-actions button{background:#fff;color:#1a2750;border:1px solid #1a2750;}"
'''

NEW_CSS = '''    ".ssa-wa-gate-actions{display:flex;flex-direction:column;align-items:center;gap:12px;}"
    ".ssa-wa-gate-auth{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:32px;}"
    ".ssa-wa-gate-actions a.ssa-wa-gate-in,.ssa-wa-gate-actions a.ssa-wa-gate-up{display:inline-flex;align-items:center;justify-content:center;gap:5px;box-sizing:border-box;border-style:solid;border-width:3px;border-radius:10px;height:32px;min-height:32px;max-height:32px;line-height:32px;padding:0 10px;font:700 13px/32px inherit;text-decoration:none;flex-shrink:0;box-shadow:0 1px 2px rgba(15,23,42,.18);-webkit-tap-highlight-color:transparent;}"
    ".ssa-wa-gate-actions a.ssa-wa-gate-in{min-width:88px;background:#fff;color:#001f3f;border-color:#f1f5f9;}"
    ".ssa-wa-gate-actions a.ssa-wa-gate-up{min-width:94px;background:#eab308;color:#000;border-color:#eab308;}"
    ".ssa-wa-gate-actions a img{display:block;width:16px;height:16px;flex-shrink:0;object-fit:contain;background:none;border:0;padding:0;margin:0;}"
    ".ssa-wa-gate-actions a.ssa-wa-gate-in img{filter:invert(8%) sepia(92%) saturate(2500%) hue-rotate(185deg) brightness(92%) contrast(105%);}"
    ".ssa-wa-gate-actions a.ssa-wa-gate-up img{filter:brightness(0) saturate(100%);}"
    ".ssa-wa-gate-actions a span{display:inline-block;line-height:32px;font-weight:700;font-size:13px;}"
    ".ssa-wa-gate-actions button{display:flex;align-items:center;justify-content:center;min-height:44px;width:100%;padding:10px 12px;border-radius:6px;font:700 14px/1.2 Arial,Helvetica,sans-serif;background:#fff;color:#1a2750;border:1px solid #1a2750;cursor:pointer;box-sizing:border-box;}"
'''

OLD_HTML = (
    r'''    "<div class=\"ssa-wa-gate-actions\"><a class=\"ssa-wa-gate-in\" href=\"/login.html?returnTo='+ret+'\">Login</a>"'''
    "\n"
    r'''    "<a class=\"ssa-wa-gate-up\" href=\"/signup.html?signup=1&amp;returnTo='+ret+'\">Sign Up</a>"'''
    "\n"
    r'''    "<button type=\"button\" data-wa-gate-close=\"1\">Close</button></div></div>';"'''
)

NEW_HTML = (
    r'''    "<div class=\"ssa-wa-gate-actions\"><div class=\"ssa-wa-gate-auth\">"'''
    "\n"
    r'''    "<a class=\"ssa-wa-gate-up\" href=\"/signup.html?signup=1&amp;returnTo='+ret+'\">"'''
    "\n"
    r'''    "<img src=\"/icons/assets/iconoir/regular/edit.svg\" alt=\"\" width=\"16\" height=\"16\"><span>Sign Up</span></a>"'''
    "\n"
    r'''    "<a class=\"ssa-wa-gate-in\" href=\"/login.html?returnTo='+ret+'\">"'''
    "\n"
    r'''    "<img src=\"/icons/assets/phosphor/bold/user-circle-gear-bold.svg\" alt=\"\" width=\"16\" height=\"16\"><span>Login</span></a>"'''
    "\n"
    r'''    "</div><button type=\"button\" data-wa-gate-close=\"1\">Close</button></div></div>';"'''
)

OLD_JS = "regatta-slot-card.js?v=20260912wa8"
NEW_JS = "regatta-slot-card.js?v=20260912wa9"


def apply(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "ssa-wa-gate-auth" in text and "wa9" in text:
        raise SystemExit(f"{path}: already patched")
    if text.count(OLD_CSS) != 1:
        raise SystemExit(f"{path}: css count {text.count(OLD_CSS)}")
    if text.count(OLD_HTML) != 1:
        raise SystemExit(f"{path}: html count {text.count(OLD_HTML)}")
    if text.count(OLD_JS) != 1:
        raise SystemExit(f"{path}: js ver count {text.count(OLD_JS)}")
    text = text.replace(OLD_CSS, NEW_CSS, 1)
    text = text.replace(OLD_HTML, NEW_HTML, 1)
    text = text.replace(OLD_JS, NEW_JS, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)


def main() -> int:
    apply(Path(sys.argv[1]) if len(sys.argv) > 1 else API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
