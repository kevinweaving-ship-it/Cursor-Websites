#!/usr/bin/env python3
"""Keep the public Lipton URL on the live board. -dev stays playback. 27–29 Aug 2026."""
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

PUB_ALIAS = re.compile(
    r"\n    location = /regatta/2026-08-29-lipton-challenge-cup(?:/)? \{\n"
    r"        default_type text/html;\n"
    r"        add_header Cache-Control \"no-store\";\n"
    r"        alias /var/www/sailingsa/lipton-dev.html;\n"
    r"    \}",
)
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
PLAYBACK_LOCK = "# LIPTON_NGINX_PLAYBACK_LOCK public + -dev slugs serve lipton-dev.html (not API event page)."
PUBLIC_KEEP = (
    "# LIPTON_NGINX_PUBLIC_NOT_DEV_V2 public slug MUST proxy to the API live board.\n"
    "    # Only -dev may alias lipton-dev.html. Do not add a public-slug alias."
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


def _write(path: Path, text: str) -> None:
    tmp = Path("/tmp") / (path.name + ".watchtmp")
    tmp.write_text(text, encoding="utf-8")
    subprocess.check_call(["cp", str(tmp), str(path)])


def _race_underway() -> bool:
    try:
        st = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return False
    gun = st.get("gun_at")
    phase = str(st.get("phase") or "").strip().lower()
    return bool(gun) and phase == "racing" and not bool(st.get("race_complete"))


def _public_is_live_board() -> bool:
    try:
        subprocess.run(
            [
                "curl",
                "-sk",
                "-o",
                "/tmp/lipton_watch_pub.html",
                "--max-time",
                "20",
                "--resolve",
                "sailingsa.co.za:443:127.0.0.1",
                f"https://sailingsa.co.za/regatta/{RID}",
            ],
            check=False,
            timeout=25,
        )
        body = Path("/tmp/lipton_watch_pub.html").read_text(encoding="utf-8", errors="replace")
        return "regatta-page" in body and "data-lipton-dev" not in body and len(body) > 50000
    except Exception:
        return False


def fix_nginx(text: str) -> tuple[str, int]:
    new, n = PUB_ALIAS.subn("", text)
    if PLAYBACK_LOCK in new:
        new = new.replace(PLAYBACK_LOCK, PUBLIC_KEEP)
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
        if n or (PLAYBACK_LOCK in raw):
            _write(NGINX, new)
            chk = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
            if chk.returncode != 0:
                _write(NGINX, raw)
                _log("nginx -t failed; reverted")
                return 1
            subprocess.check_call(["systemctl", "reload", "nginx"])
            ok = False
            for _ in range(4):
                if _public_is_live_board():
                    ok = True
                    break
            if not ok:
                _write(NGINX, raw)
                subprocess.check_call(["systemctl", "reload", "nginx"])
                _log("nginx public URL not live board after strip; reverted")
                return 1
            nginx_changed = True
            _log(f"nginx stripped public aliases n={n} reloaded")
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
