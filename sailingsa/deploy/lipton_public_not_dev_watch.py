#!/usr/bin/env python3
"""Keep the public Lipton URL on the live board. -dev stays playback. 27–29 Aug 2026.

Never restore a public-slug alias to lipton-dev.html. Lock nginx immediately after a
good write so PLAYBACK_LOCK cannot win a long curl-check window.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RID = "2026-08-29-lipton-challenge-cup"
NGINX = Path("/etc/nginx/sites-enabled/sailingsa")
API = Path("/var/www/sailingsa/api/api.py")
STATE = Path("/var/tmp/sailingsa_live_race_2026-08-29-lipton-challenge-cup.json")
LOG = Path("/var/log/lipton_public_not_dev_watch.log")
PY = "/var/www/sailingsa/api/venv/bin/python"

HIJACK = re.compile(
    r"\n    if slug_s == \"2026-08-29-lipton-challenge-cup\":\n"
    r"        return serve_lipton_dev_playback_page\(request, public=True\)\n"
)
PLAY_HEAD = '''def serve_lipton_dev_playback_page(_request, public: bool = False):
    """Lipton playback page. Public slug is indexable; -dev stays noindex."""
    from pathlib import Path as _P
'''
PLAY_GUARD = '''def serve_lipton_dev_playback_page(_request, public: bool = False):
    """Lipton playback page. Public slug is indexable; -dev stays noindex."""
    if public:
        # LIPTON_PUBLIC_NOT_DEV_V4 hijack public=True must still render the live board.
        return _serve_regatta_standalone_impl("2026-08-29-lipton-challenge-cup", _request)
    from pathlib import Path as _P
'''
DEV_BLOCK = '''    location = /regatta/2026-08-29-lipton-challenge-cup-dev {
        default_type text/html;
        add_header Cache-Control "no-store";
        add_header X-Robots-Tag "noindex, nofollow";
        alias /var/www/sailingsa/lipton-dev.html;
    }
'''

PUBLIC_PROXY = '''    location = /regatta/2026-08-29-lipton-challenge-cup {
        # LIPTON_NGINX_PUBLIC_PROXY_V1
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store";
    }
    location = /regatta/2026-08-29-lipton-challenge-cup/ {
        # LIPTON_NGINX_PUBLIC_PROXY_V1
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        add_header Cache-Control "no-store";
    }
'''
PLAYBACK_LOCK = "# LIPTON_NGINX_PLAYBACK_LOCK public + -dev slugs serve lipton-dev.html (not API event page)."
PUBLIC_KEEP = (
    "# LIPTON_NGINX_PUBLIC_NOT_DEV_V2 public slug MUST proxy to the API live board.\n"
    "    # Only -dev may alias lipton-dev.html. Do not add a public-slug alias."
)

# Any exact public-slug location (alias or leftover proxy) so we can insert one pair.
PUB_LOC = re.compile(
    r"\n[ \t]*(?:# LIPTON_NGINX[^\n]*\n[ \t]*)?"
    r"location = /regatta/"
    + re.escape(RID)
    + r"(?:/)?"
    r"\s*\{[^{}]*\}",
    re.S,
)
PUB_ALIAS = re.compile(
    r"\n    location = /regatta/2026-08-29-lipton-challenge-cup(?:/)? \{\n"
    r"        default_type text/html;\n"
    r"        add_header Cache-Control \"no-store\";\n"
    r"        alias /var/www/sailingsa/lipton-dev.html;\n"
    r"    \}",
)


def _log(msg: str) -> None:
    line = datetime.now(ZoneInfo("Africa/Johannesburg")).strftime("%Y-%m-%d %H:%M:%S SAST ") + msg
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line)


def _event_day() -> bool:
    day = datetime.now(ZoneInfo("Africa/Johannesburg")).strftime("%Y-%m-%d")
    return day in ("2026-08-27", "2026-08-28", "2026-08-29")


def _chattr(path: Path, plus_i: bool) -> None:
    flag = "+i" if plus_i else "-i"
    subprocess.run(["chattr", flag, str(path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _write(path: Path, text: str) -> None:
    tmp = Path("/tmp") / (path.name + ".watchtmp")
    tmp.write_text(text, encoding="utf-8")
    _chattr(path, False)
    subprocess.check_call(["cp", str(tmp), str(path)])


def _race_underway() -> bool:
    try:
        st = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return False
    gun = st.get("gun_at")
    phase = str(st.get("phase") or "").strip().lower()
    return bool(gun) and phase == "racing" and not bool(st.get("race_complete"))


def _public_aliased(text: str) -> bool:
    if PLAYBACK_LOCK in text:
        return True
    for m in re.finditer(
        r"location = /regatta/" + re.escape(RID) + r"(?:/)?\s*\{([^{}]*)\}",
        text,
        re.S,
    ):
        if "lipton-dev.html" in m.group(1):
            return True
    return False


DEV_LOC = re.compile(
    r"(    location = /regatta/" + re.escape(RID) + r"-dev \{[^{}]*\n    \})",
    re.S,
)


def fix_nginx(text: str) -> tuple[str, int]:
    n = 0
    new = text
    if _public_aliased(text) or PUB_ALIAS.search(text):
        new, n1 = PUB_ALIAS.subn("", new)
        n += n1
        # Drop leftover public-slug locations (missed alias format or duplicate proxy).
        new2, n2 = PUB_LOC.subn("", new)
        n += n2
        new = new2
    if PLAYBACK_LOCK in new:
        new = new.replace(PLAYBACK_LOCK, PUBLIC_KEEP)
        n += 1
    if "LIPTON_NGINX_PUBLIC_PROXY_V1" not in new:
        inserted = False
        if DEV_BLOCK in new:
            new = new.replace(DEV_BLOCK, DEV_BLOCK + "\n" + PUBLIC_PROXY, 1)
            inserted = True
        else:
            m = DEV_LOC.search(new)
            if m:
                new = new.replace(m.group(1), m.group(1) + "\n\n" + PUBLIC_PROXY, 1)
                inserted = True
        if not inserted:
            for needle in (
                "    location /regatta/ {",
                "    location = /regatta {",
                "        location = /regatta {",
            ):
                if needle in new:
                    new = new.replace(needle, PUBLIC_PROXY + "\n" + needle, 1)
                    inserted = True
                    break
        if inserted:
            n += 1
    return new, n


def fix_api(text: str) -> tuple[str, bool]:
    changed = False
    new, n = HIJACK.subn("\n", text)
    if n:
        changed = True
        text = new
    if PLAY_HEAD in text and "LIPTON_PUBLIC_NOT_DEV_V4 hijack public=True" not in text:
        text = text.replace(PLAY_HEAD, PLAY_GUARD, 1)
        changed = True
    return text, changed


def main() -> int:
    if not _event_day():
        return 0
    nginx_changed = False
    api_changed = False
    if NGINX.is_file():
        raw = NGINX.read_text(encoding="utf-8")
        new, n = fix_nginx(raw)
        needs = n or _public_aliased(raw) or new != raw or "LIPTON_NGINX_PUBLIC_PROXY_V1" not in new
        if needs and new != raw:
            _write(NGINX, new)
            chk = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
            if chk.returncode != 0:
                _log("nginx -t failed; not restoring aliased public slug")
                if not _public_aliased(raw):
                    _write(NGINX, raw)
                return 1
            subprocess.check_call(["nginx", "-s", "reload"])
            _chattr(NGINX, True)
            nginx_changed = True
            _log(f"nginx public proxy locked n={n} (never restore alias)")
        else:
            _chattr(NGINX, True)
    if API.is_file():
        raw = API.read_text(encoding="utf-8")
        new, changed = fix_api(raw)
        if changed:
            _write(API, new)
            py = PY if Path(PY).is_file() else sys.executable
            chk = subprocess.run([py, "-m", "py_compile", str(API)], capture_output=True, text=True)
            if chk.returncode != 0:
                _write(API, raw)
                _log("api.py compile failed; reverted")
                return 1
            os.system("chown www-data:www-data /var/www/sailingsa/api/api.py >/dev/null 2>&1")
            api_changed = True
            if _race_underway():
                _log("api.py hijack stripped; skipped restart (race underway)")
            else:
                subprocess.check_call(["systemctl", "restart", "sailingsa-api"])
                _log("api.py hijack stripped; sailingsa-api restarted")
    if not nginx_changed and not api_changed:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
