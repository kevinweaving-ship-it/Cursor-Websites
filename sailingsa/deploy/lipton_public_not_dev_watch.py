#!/usr/bin/env python3
"""Keep the public Lipton URL on the live board. -dev stays playback. 27–29 Aug 2026.

Never restore a public-slug alias to lipton-dev.html. Lock nginx immediately after a
good write so PLAYBACK_LOCK cannot win a long curl-check window.
LIPTON_WATCH_DEBOUNCE_V1
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
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
    r"\n[ \t]*if slug_s == \"2026-08-29-lipton-challenge-cup\"(?: and not allow_lipton_event)?:\n"
    r"[ \t]*return serve_lipton_dev_playback_page\(request, public=True\)\n"
)
PLAY_DOC = re.compile(
    r"(def serve_lipton_dev_playback_page\([^)]*\):\n"
    r"    \"\"\"[\s\S]*?\"\"\"\n)"
    r"(?!    if public:)"
)
PLAY_GUARD_BLOCK = (
    "    if public:\n"
    "        # LIPTON_PUBLIC_NOT_DEV_V4 hijack public=True must still render the live board.\n"
    '        return _serve_regatta_standalone_impl("2026-08-29-lipton-challenge-cup", _request)\n'
)
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
SNIPPET = Path("/etc/nginx/snippets/lipton-public-proxy.conf")
INCLUDE = """    # LIPTON_NGINX_PUBLIC_PROXY_V1
    include /etc/nginx/snippets/lipton-public-proxy.conf;
"""

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


def _overnight_hold() -> bool:
    """17:00–10:00 SAST: last official Rn, no invented gun, avoid API restart storms."""
    now = datetime.now(ZoneInfo("Africa/Johannesburg"))
    mins = now.hour * 60 + now.minute
    return mins >= 17 * 60 or mins < 10 * 60


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


RESTART_STAMP = Path("/var/tmp/lipton_watch_api_restart")
STRIP_STAMP = Path("/var/tmp/lipton_watch_api_strip")


def _seconds_since_api_restart() -> float:
    try:
        return time.time() - RESTART_STAMP.stat().st_mtime
    except Exception:
        return 10**9


def _mark_api_restart() -> None:
    try:
        RESTART_STAMP.write_text(str(time.time()), encoding="utf-8")
    except Exception:
        pass


def _seconds_since_api_strip() -> float:
    try:
        return time.time() - STRIP_STAMP.stat().st_mtime
    except Exception:
        return 10**9


def _mark_api_strip() -> None:
    try:
        STRIP_STAMP.write_text(str(time.time()), encoding="utf-8")
    except Exception:
        pass


def _origin_board_state() -> str:
    """live, playback, or down. Probe nginx→API on loopback; use size only (no 400k download)."""
    try:
        p = subprocess.run(
            [
                "curl",
                "-sk",
                "--max-time",
                "8",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code} %{size_download}",
                "--resolve",
                "sailingsa.co.za:443:127.0.0.1",
                f"https://sailingsa.co.za/regatta/{RID}",
            ],
            check=False,
            timeout=10,
            capture_output=True,
            text=True,
        )
        parts = (p.stdout or "").strip().split()
        code = parts[0] if parts else "000"
        size = int(parts[1]) if len(parts) > 1 else 0
    except Exception:
        return "down"
    if size > 50000 and code == "200":
        return "live"
    if code in ("502", "503", "000") or size < 500:
        return "down"
    if 500 <= size < 20000:
        return "playback"
    return "down"


def ensure_snippet() -> bool:
    """Write the public-slug proxy locations into an immutable include file."""
    try:
        SNIPPET.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        return False
    body = PUBLIC_PROXY if PUBLIC_PROXY.endswith("\n") else PUBLIC_PROXY + "\n"
    if SNIPPET.is_file():
        try:
            if SNIPPET.read_text(encoding="utf-8") == body:
                _chattr(SNIPPET, True)
                return False
        except Exception:
            pass
    _write(SNIPPET, body)
    _chattr(SNIPPET, True)
    return True


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
    new, n1 = PUB_ALIAS.subn("", new)
    n += n1
    new2, n2 = PUB_LOC.subn("", new)
    n += n2
    new = new2
    if "include /etc/nginx/snippets/lipton-public-proxy.conf" in new:
        new = new.replace("    include /etc/nginx/snippets/lipton-public-proxy.conf;\n", "")
        new = new.replace("include /etc/nginx/snippets/lipton-public-proxy.conf;\n", "")
        n += 1
    if PLAYBACK_LOCK in new:
        new = new.replace(PLAYBACK_LOCK, PUBLIC_KEEP)
        n += 1
    has_public_proxy = bool(
        re.search(
            r"location = /regatta/" + re.escape(RID) + r"(?:/)?\s*\{[^}]*proxy_pass",
            new,
            re.S,
        )
    )
    if not has_public_proxy:
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
    if "LIPTON_PUBLIC_NOT_DEV_V4 hijack public=True" not in text:
        patched, pn = PLAY_DOC.subn(r"\1" + PLAY_GUARD_BLOCK, text, count=1)
        if pn:
            text = patched
            changed = True
    return text, changed


CRON_PUBLIC = Path("/etc/cron.d/sailingsa-lipton-public-not-dev")
CRON_ZZZ = Path("/etc/cron.d/zzz-lipton-public-live")
CRON_PUBLIC_BODY = """# Lipton 2026: undo public-slug playback hijack (nginx + api.py).
# Script no-ops except 27-29 Aug 2026. Does not run overnight restore.
# Skips API restart if a real race is underway.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
* * * * * root /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1; sleep 20; /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1; sleep 20; /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1
"""
CRON_ZZZ_BODY = "* * * * * root /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1\n"


def ensure_cron() -> bool:
    """Rewrite deleted watchdog crons. PLAYBACK_LOCK often removes these files."""
    changed = False
    for path, body in ((CRON_PUBLIC, CRON_PUBLIC_BODY), (CRON_ZZZ, CRON_ZZZ_BODY)):
        try:
            cur = path.read_text(encoding="utf-8") if path.is_file() else ""
        except Exception:
            cur = ""
        if cur != body:
            try:
                _write(path, body)
                os.system(f"chmod 644 {path} >/dev/null 2>&1")
                changed = True
            except Exception:
                pass
        _chattr(path, True)
    return changed


def ensure_watch_service() -> None:
    """Cron copy can restart systemd if PLAYBACK_LOCK stopped the loop."""
    try:
        p = subprocess.run(
            ["systemctl", "is-active", "sailingsa-lipton-public-watch.service"],
            capture_output=True,
            text=True,
        )
        if (p.stdout or "").strip() in ("active", "activating"):
            return
        subprocess.run(
            ["systemctl", "unmask", "sailingsa-lipton-public-watch.service"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["systemctl", "enable", "--now", "sailingsa-lipton-public-watch.service"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _log("watch systemd started")
    except Exception:
        pass


def main() -> int:
    if not _event_day():
        return 0
    nginx_changed = False
    api_changed = False
    try:
        if ensure_cron():
            _log("watchdog cron restored")
        ensure_watch_service()
    except Exception:
        pass

    if NGINX.is_file():
        snippet_changed = ensure_snippet()
        raw = NGINX.read_text(encoding="utf-8")
        new, n = fix_nginx(raw)
        needs = (
            n
            or _public_aliased(raw)
            or new != raw
            or "LIPTON_NGINX_PUBLIC_PROXY_V1" not in new
            or "proxy_pass http://127.0.0.1:8000" not in new
            or snippet_changed
        )
        if needs and (new != raw or snippet_changed):
            if new != raw:
                _write(NGINX, new)
            chk = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
            if chk.returncode != 0:
                _log("nginx -t failed; not restoring aliased public slug")
                if new != raw and not _public_aliased(raw):
                    _write(NGINX, raw)
                return 1
            board = _origin_board_state()
            must_reload = new != raw or _public_aliased(raw) or board == "playback"
            if must_reload:
                subprocess.check_call(["nginx", "-s", "reload"])
                _log(
                    f"nginx public proxy locked n={n} snippet={snippet_changed} "
                    f"reload=1 board={board}"
                )
            else:
                _log(f"nginx snippet restored; skipped reload (board={board})")
            _chattr(NGINX, True)
            _chattr(SNIPPET, True)
            nginx_changed = True
        else:
            _chattr(NGINX, True)
            _chattr(SNIPPET, True)
    if API.is_file():
        raw = API.read_text(encoding="utf-8")
        new, changed = fix_api(raw)
        if changed:
            if _seconds_since_api_strip() < 8:
                _log("api.py hijack on disk; deferred strip")
            else:
                _write(API, new)
                py = PY if Path(PY).is_file() else sys.executable
                chk = subprocess.run([py, "-m", "py_compile", str(API)], capture_output=True, text=True)
                if chk.returncode != 0:
                    _write(API, raw)
                    _log("api.py compile failed; reverted")
                    return 1
                os.system("chown www-data:www-data /var/www/sailingsa/api/api.py >/dev/null 2>&1")
                _chattr(API, True)
                _mark_api_strip()
                api_changed = True
                if _race_underway():
                    _log("api.py hijack stripped; skipped restart (race underway)")
                else:
                    board = _origin_board_state()
                    if board != "playback":
                        _log(f"api.py hijack stripped; skipped restart (board={board})")
                    elif _seconds_since_api_restart() < 90:
                        _log(f"api.py hijack stripped; skipped restart (debounce board={board})")
                    else:
                        subprocess.check_call(["systemctl", "restart", "sailingsa-api"])
                        _mark_api_restart()
                        _log(f"api.py hijack stripped; sailingsa-api restarted board={board}")
        elif not _race_underway():
            board = _origin_board_state()
            if board == "playback" and _seconds_since_api_restart() >= 20:
                subprocess.check_call(["systemctl", "restart", "sailingsa-api"])
                _mark_api_restart()
                _log("origin playback with clean disk; sailingsa-api restarted")
                api_changed = True
    if not nginx_changed and not api_changed:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
