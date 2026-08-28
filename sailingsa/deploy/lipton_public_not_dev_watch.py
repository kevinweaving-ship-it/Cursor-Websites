#!/usr/bin/env python3
"""Keep the public Lipton URL on the live board. -dev stays playback. 27–29 Aug 2026.

Never restore a public-slug alias to lipton-dev.html. Lock nginx immediately after a
good write so PLAYBACK_LOCK cannot win a long curl-check window.
LIPTON_WATCH_DEBOUNCE_V1
LIPTON_WATCH_UNIT_RESTORE_V1
LIPTON_WATCH_GUARD_EMBED_V1
LIPTON_WATCH_LOOP_V1
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
    r"\n[ \t]*if slug_s == \"2026-08-29-lipton-challenge-cup\""
    r"(?: and not allow_lipton_event)?:\r?\n"
    r"(?:[ \t]*\r?\n)*"
    r"[ \t]*return serve_lipton_dev_playback_page\(request, public=True\)\r?\n"
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
NGINX_RELOAD_STAMP = Path("/var/tmp/lipton_watch_nginx_reload")


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


def _seconds_since_nginx_reload() -> float:
    try:
        return time.time() - NGINX_RELOAD_STAMP.stat().st_mtime
    except Exception:
        return 10**9


def _mark_nginx_reload() -> None:
    try:
        NGINX_RELOAD_STAMP.write_text(str(time.time()), encoding="utf-8")
    except Exception:
        pass


def _origin_board_state() -> str:
    """live, playback, or down.

    Do not --resolve to 127.0.0.1:443 — that hits the timadvisor default SSL
    server (301). Probe public IPv4 SNI, then the API with forwarded proto.
    """
    probes = [
        [
            "curl",
            "-4sk",
            "--max-time",
            "3",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code} %{size_download}",
            f"https://sailingsa.co.za/regatta/{RID}",
        ],
        [
            "curl",
            "-sS",
            "--max-time",
            "3",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code} %{size_download}",
            "-H",
            "Host: sailingsa.co.za",
            "-H",
            "X-Forwarded-Proto: https",
            "-H",
            "X-Forwarded-Host: sailingsa.co.za",
            f"http://127.0.0.1:8000/regatta/{RID}",
        ],
    ]
    last = "down"
    for args in probes:
        try:
            p = subprocess.run(
                args,
                check=False,
                timeout=5,
                capture_output=True,
                text=True,
            )
            parts = (p.stdout or "").strip().split()
            code = parts[0] if parts else "000"
            size = int(parts[1]) if len(parts) > 1 else 0
        except Exception:
            last = "down"
            continue
        if size > 50000 and code == "200":
            return "live"
        if 500 <= size < 20000 and code == "200":
            return "playback"
        if code in ("502", "503", "000") or size < 500:
            last = "down"
            continue
        last = "down"
    return last


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
        r"location = /regatta/" + re.escape(RID) + r"(?:/)?(?!-)\s*\{([^{}]*)\}",
        text,
        re.S,
    ):
        if "lipton-dev.html" in m.group(1):
            return True
    return False


def _nginx_must_reload(board: str, aliased_on_disk: bool, had_include: bool = False) -> bool:
    """Reload as soon as a public-slug alias or snippet include is on disk."""
    if aliased_on_disk or had_include:
        return True
    return board == "playback"


def _public_slug_proxied(text: str) -> bool:
    """True only if the public slug proxies to the API and is not also aliased."""
    if _public_aliased(text):
        return False
    m = re.search(
        r"location = /regatta/" + re.escape(RID) + r"(?:/)?(?!-)\s*\{([^{}]*)\}",
        text,
        re.S,
    )
    if not m:
        return False
    body = m.group(1)
    return "proxy_pass" in body and "lipton-dev.html" not in body


def _unit_is_stub(text: str) -> bool:
    low = text.lower()
    if "must not restore" in low:
        return True
    if "ExecStart=/bin/true" in text or "ExecStart=/bin/false" in text:
        return True
    if "while true" not in text:
        return True
    if "lw-gold" not in text and "lipton_public_not_dev_watch.py" not in text:
        return True
    return False


DEV_LOC = re.compile(
    r"(    location = /regatta/" + re.escape(RID) + r"-dev \{[^{}]*\n    \})",
    re.S,
)


def fix_nginx(text: str) -> tuple[str, int]:
    if (
        _public_slug_proxied(text)
        and "include /etc/nginx/snippets/lipton-public-proxy.conf" not in text
        and PLAYBACK_LOCK not in text
    ):
        return text, 0
    n = 0
    new = text
    new, n1 = PUB_ALIAS.subn("", new)
    n += n1
    new2, n2 = PUB_LOC.subn("", new)
    n += n2
    new = new2
    stripped, n_inc = re.subn(
        r"[ \t]*include /etc/nginx/snippets/lipton-public-proxy\.conf;\r?\n?",
        "",
        new,
    )
    if n_inc:
        new = stripped
        n += n_inc
    if PLAYBACK_LOCK in new:
        new = new.replace(PLAYBACK_LOCK, PUBLIC_KEEP)
        n += 1
    has_public_proxy = _public_slug_proxied(new)
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
CRON_HOLD = Path("/etc/cron.d/aa-lipton-url-hold")
CRON_PUBLIC_BODY = """# Lipton 2026: undo public-slug playback hijack (nginx + api.py).
# Script no-ops except 27-29 Aug 2026. Does not run overnight restore.
# Skips API restart if a real race is underway.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
* * * * * root /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1; sleep 20; /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1; sleep 20; /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1
"""
CRON_ZZZ_BODY = "* * * * * root /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1\n"
CRON_HOLD_BODY = "* * * * * root /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1; sleep 15; /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1; sleep 15; /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1\n"

WATCH_UNIT = Path("/etc/systemd/system/sailingsa-lipton-public-watch.service")
HOLD_UNIT = Path("/etc/systemd/system/sailingsa-lipton-url-hold.service")
GOLD_PY = (
    "/root/lw-g14c.py /root/lw-g14.py /root/lw-g13b.py /root/lw-gold13.py /root/lw-gold7.py "
    "/root/lw-gold6.py /root/lw-gold5.py "
    "/usr/local/lib/lipton_public_not_dev_watch.py /usr/local/sbin/lipton_public_not_dev_watch.py"
)
WATCH_LOOP = (
    "while true; do "
    f"for f in {GOLD_PY}; do "
    'sz=$(wc -c < "$f" 2>/dev/null || echo 0); '
    'if [ "$sz" -gt 500 ] && grep -q LIPTON_WATCH_DEBOUNCE_V1 "$f" 2>/dev/null; then '
    '/usr/bin/python3 "$f" --loop; break; fi; done; sleep 1; done'
)
HOLD_LOOP = (
    "while true; do "
    "if systemctl is-active --quiet sailingsa-lipton-public-watch.service; then sleep 15; continue; fi; "
    f"for f in {GOLD_PY}; do "
    'sz=$(wc -c < "$f" 2>/dev/null || echo 0); '
    'if [ "$sz" -gt 500 ] && grep -q LIPTON_WATCH_DEBOUNCE_V1 "$f" 2>/dev/null; then '
    '/usr/bin/python3 "$f" --loop; break; fi; done; sleep 1; done'
)
WATCH_UNIT_BODY = f"""[Unit]
Description=Lipton 2026 public URL live-board watchdog
After=network.target nginx.service sailingsa-api.service

[Service]
Type=simple
Restart=always
RestartSec=1
ExecStart=/bin/bash -c '{WATCH_LOOP}'

[Install]
WantedBy=multi-user.target
"""
HOLD_UNIT_BODY = f"""[Unit]
Description=Lipton 2026 public URL hold loop
After=network.target nginx.service sailingsa-api.service

[Service]
Type=simple
Restart=always
RestartSec=2
ExecStart=/bin/bash -c '{HOLD_LOOP}'

[Install]
WantedBy=multi-user.target
"""
GUARD_PATH = Path("/usr/local/lib/lipton_public_watch_guard.sh")
GUARD_BODY = r'''#!/bin/bash
# Restore stubbed or stale Lipton public-URL watchdog copies, then run one.
set -euo pipefail
MARKER="LIPTON_WATCH_DEBOUNCE_V1"
COPIES=(
  /usr/local/lib/lipton_public_not_dev_watch.py
  /var/lib/sailingsa-lipton/watch.py
  /usr/local/sbin/lipton_public_not_dev_watch.py
)
GOLDS=(
  /root/lw-g14c.py
  /root/lw-g14.py
  /root/lw-g13b.py
  /root/lw-gold13.py
  /root/lw-gold7.py
  /root/lw-gold6.py
  /root/lw-gold5.py
  /root/lw-gold4.py
  /root/lw-gold3.py
  /root/lw-gold.py
  /root/lipton_public_not_dev_watch.py
  /var/lib/sailingsa-lipton/watch.py.gold
)

is_good() {
  local f="$1"
  [[ -f "$f" ]] || return 1
  local sz
  sz=$(wc -c < "$f" | tr -d ' ')
  [[ "$sz" -gt 500 ]] || return 1
  grep -q "$MARKER" "$f"
}

good=""
for f in "${GOLDS[@]}" "${COPIES[@]}"; do
  if is_good "$f"; then
    good=$f
    break
  fi
done
if [[ -z "$good" ]]; then
  echo "lipton watch: no good copy" >&2
  exit 1
fi
for f in "${COPIES[@]}"; do
  if ! is_good "$f"; then
    chattr -i "$f" 2>/dev/null || true
    mkdir -p "$(dirname "$f")"
    cp "$good" "$f"
    chmod 755 "$f"
    chattr +i "$f" 2>/dev/null || true
  fi
done

restore_unit() {
  local dest="$1"
  local src="$2"
  [[ -f "$src" ]] || return 0
  local need=0
  if [[ ! -f "$dest" ]]; then
    need=1
  elif grep -q 'ExecStart=/bin/true' "$dest" 2>/dev/null; then
    need=1
  elif grep -q 'must not restore' "$dest" 2>/dev/null; then
    need=1
  elif ! grep -q 'while true' "$dest" 2>/dev/null; then
    need=1
  elif ! grep -q 'lw-gold' "$dest" 2>/dev/null; then
    need=1
  fi
  if [[ "$need" -eq 1 ]]; then
    chattr -i "$dest" 2>/dev/null || true
    cp "$src" "$dest"
    chmod 644 "$dest"
    chattr +i "$dest" 2>/dev/null || true
    systemctl daemon-reload >/dev/null 2>&1 || true
  fi
}

restore_unit /etc/systemd/system/sailingsa-lipton-public-watch.service /usr/local/lib/sailingsa-lipton-public-watch.service
restore_unit /etc/systemd/system/sailingsa-lipton-url-hold.service /usr/local/lib/sailingsa-lipton-url-hold.service

exec /usr/bin/python3 "$good" "$@"
'''


def ensure_cron() -> bool:
    """Rewrite deleted watchdog crons. PLAYBACK_LOCK often removes these files."""
    changed = False
    for path, body in (
        (CRON_PUBLIC, CRON_PUBLIC_BODY),
        (CRON_ZZZ, CRON_ZZZ_BODY),
        (CRON_HOLD, CRON_HOLD_BODY),
    ):
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


def ensure_guard() -> bool:
    """Rewrite stubbed guard.sh (often `exit 0`) so cron copies still run."""
    try:
        cur = GUARD_PATH.read_text(encoding="utf-8") if GUARD_PATH.is_file() else ""
    except Exception:
        cur = ""
    stub = (len(cur) < 200) or ("LIPTON_WATCH_DEBOUNCE_V1" not in cur) or re.search(
        r"^exit 0\s*$", cur, re.M
    )
    if not stub and cur.strip() == GUARD_BODY.strip():
        _chattr(GUARD_PATH, True)
        return False
    try:
        _write(GUARD_PATH, GUARD_BODY if GUARD_BODY.endswith("\n") else GUARD_BODY + "\n")
        os.system(f"chmod 755 {GUARD_PATH} >/dev/null 2>&1")
        _chattr(GUARD_PATH, True)
        _log("watch guard restored")
        return True
    except Exception:
        return False


def _ensure_unit_file(path: Path, body: str, unit_name: str) -> bool:
    """Rewrite stub/oneshot/guard-only units back to the python gold loop."""
    try:
        cur = path.read_text(encoding="utf-8") if path.is_file() else ""
    except Exception:
        cur = ""
    if cur == body:
        _chattr(path, True)
        return False
    try:
        _write(path, body)
        os.system(f"chmod 644 {path} >/dev/null 2>&1")
        _chattr(path, True)
        subprocess.run(
            ["systemctl", "daemon-reload"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _log(f"systemd unit restored {unit_name}")
        return True
    except Exception:
        return False


def _start_unit_if_down(unit_name: str, *, restart: bool = False) -> None:
    try:
        p = subprocess.run(
            ["systemctl", "is-active", unit_name],
            capture_output=True,
            text=True,
        )
        active = (p.stdout or "").strip() in ("active", "activating")
        if active and not restart:
            return
        subprocess.run(
            ["systemctl", "unmask", unit_name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if restart and active:
            subprocess.run(
                ["systemctl", "restart", unit_name],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _log(f"watch systemd restarted {unit_name}")
            return
        subprocess.run(
            ["systemctl", "enable", "--now", unit_name],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _log(f"watch systemd started {unit_name}")
    except Exception:
        pass


def ensure_watch_service() -> None:
    """Cron copy can restart systemd if PLAYBACK_LOCK stubbed the unit to /bin/true."""
    restored = _ensure_unit_file(WATCH_UNIT, WATCH_UNIT_BODY, "sailingsa-lipton-public-watch.service")
    restored_hold = _ensure_unit_file(HOLD_UNIT, HOLD_UNIT_BODY, "sailingsa-lipton-url-hold.service")
    if restored or restored_hold:
        subprocess.run(
            ["systemctl", "daemon-reload"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    _start_unit_if_down("sailingsa-lipton-public-watch.service", restart=restored)
    _start_unit_if_down("sailingsa-lipton-url-hold.service", restart=restored_hold)


def main() -> int:
    if not _event_day():
        return 0
    nginx_changed = False
    api_changed = False
    try:
        if ensure_cron():
            _log("watchdog cron restored")
        if ensure_guard():
            _log("watchdog guard restored")
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
            or not _public_slug_proxied(new)
            or "include /etc/nginx/snippets/lipton-public-proxy.conf" in raw
            or snippet_changed
        )
        if needs and (new != raw or snippet_changed):
            if new != raw:
                _write(NGINX, new)
                chk = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
                if chk.returncode != 0:
                    _log("nginx -t failed; not restoring aliased public slug")
                    if not _public_aliased(raw):
                        _write(NGINX, raw)
                    return 1
                aliased = _public_aliased(raw)
                had_include = "include /etc/nginx/snippets/lipton-public-proxy.conf" in raw
                if aliased:
                    board = "aliased"
                elif had_include:
                    board = "include"
                else:
                    board = _origin_board_state()
                must_reload = _nginx_must_reload(board, aliased, had_include)
                if must_reload:
                    subprocess.check_call(["nginx", "-s", "reload"])
                    _mark_nginx_reload()
                    _log(
                        f"nginx public proxy locked n={n} snippet={snippet_changed} "
                        f"reload=1 board={board}"
                    )
                else:
                    _log(f"nginx public proxy rewritten; skipped reload (board={board})")
            elif snippet_changed:
                _log("nginx snippet restored; skipped reload (snippet-only)")
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
                    if board == "live":
                        _log(f"api.py hijack stripped; skipped restart (board={board})")
                    elif _overnight_hold() and board == "down":
                        _log("api.py hijack stripped; overnight skipped restart (bind window)")
                    elif _seconds_since_api_restart() < 90:
                        _log(f"api.py hijack stripped; skipped restart (debounce board={board})")
                    else:
                        subprocess.check_call(["systemctl", "restart", "sailingsa-api"])
                        _mark_api_restart()
                        _log(f"api.py hijack stripped; sailingsa-api restarted board={board}")
        elif not _race_underway():
            board = _origin_board_state()
            try:
                ngx = NGINX.read_text(encoding="utf-8") if NGINX.is_file() else ""
            except Exception:
                ngx = ""
            nginx_ok = _public_slug_proxied(ngx) and (
                "include /etc/nginx/snippets/lipton-public-proxy.conf" not in ngx
            )
            if board == "playback" and not nginx_ok:
                _log("origin playback; nginx not proxied; skipped API restart")
            elif (
                board == "playback"
                and nginx_ok
                and not _overnight_hold()
                and _seconds_since_api_restart() >= 90
            ):
                subprocess.check_call(["systemctl", "restart", "sailingsa-api"])
                _mark_api_restart()
                _log("origin playback with clean disk; sailingsa-api restarted")
                api_changed = True
    if not nginx_changed and not api_changed:
        return 0
    return 0


def _run_argv(argv: list[str]) -> int:
    loop = "--loop" in argv
    rc = 0
    while True:
        rc = main()
        if not loop or not _event_day():
            return rc
        time.sleep(1)


if __name__ == "__main__":
    raise SystemExit(_run_argv(sys.argv[1:]))
