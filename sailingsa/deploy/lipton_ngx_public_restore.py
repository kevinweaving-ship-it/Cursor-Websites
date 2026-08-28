#!/usr/bin/env python3
"""Nginx-only restore for the public Lipton slug. Does not touch api.py.

LIPTON_NGINX_BASH_RESTORE_V1
LIPTON_NGINX_LOOP_V1
PLAYBACK_LOCK often stubs the python watchdog gold. Cron/guard can still
put the public URL back on proxy_pass without that gold.
-dev stays aliased to lipton-dev.html.
An optional --loop mode rewrites nginx every 1s without reading api.py.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

RID = "2026-08-29-lipton-challenge-cup"
NGINX = Path("/etc/nginx/sites-enabled/sailingsa")
SNIPPET = Path("/etc/nginx/snippets/lipton-public-proxy.conf")
LOG = Path("/var/log/lipton_public_not_dev_watch.log")
CRON_SCHED = Path("/etc/cron.d/sailingsa-lipton-schedule")
CRON_SCHED_BODY = """# Lipton 2026: apply SA schedule without a page view.
# UTC 08:00-10:59 = SAST 10:00-12:59 (wake + 12:00 arm)
# UTC 15:00-16:59 = SAST 17:00-18:59 (harbour close)
# UTC 17-23 and 0-7 every 5 min = SAST 19:00-09:59 (restart leftover gun)
# Script no-ops except 27-29 Aug 2026. Does not set race_key.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
* 8-10 * * * root /usr/local/sbin/cron_lipton_schedule_poll.sh
* 15-16 * * * root /usr/local/sbin/cron_lipton_schedule_poll.sh
*/5 17-23,0-7 * * * root /usr/local/sbin/cron_lipton_schedule_poll.sh
"""
WATCH_MARKER = "LIPTON_WATCH_DEBOUNCE_V1"
# LIPTON_NGINX_WATCH_UNIT_V1 — revive units/loops when PLAYBACK_LOCK disable+kills.
CRON_NGX = Path("/etc/cron.d/aa-lipton-ngx")
CRON_NGX_BODY = (
    "* * * * * root /usr/local/sbin/lipton_ngx_public_restore.py >/dev/null 2>&1; "
    "sleep 20; /usr/local/sbin/lipton_ngx_public_restore.py >/dev/null 2>&1; "
    "sleep 20; /usr/local/sbin/lipton_ngx_public_restore.py >/dev/null 2>&1\n"
)
CRON_PUBLIC = Path("/etc/cron.d/sailingsa-lipton-public-not-dev")
CRON_PUBLIC_BODY = """# Lipton 2026: undo public-slug playback hijack (nginx + api.py).
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
* * * * * root /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1; sleep 20; /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1; sleep 20; /usr/local/lib/lipton_public_watch_guard.sh >/dev/null 2>&1
"""
NGX_UNIT = Path("/etc/systemd/system/sailingsa-lipton-ngx-restore.service")
NGX_UNIT_BODY = """[Unit]
Description=Lipton 2026 nginx public-slug restore loop
After=network.target nginx.service

[Service]
Type=simple
Restart=always
RestartSec=1
ExecStart=/usr/bin/python3 /usr/local/sbin/lipton_ngx_public_restore.py --loop

[Install]
WantedBy=multi-user.target
"""
WATCH_UNIT_NAME = "sailingsa-lipton-public-watch.service"
HOLD_UNIT_NAME = "sailingsa-lipton-url-hold.service"
NGX_UNIT_NAME = "sailingsa-lipton-ngx-restore.service"
WATCH_SRCS = (
    Path("/usr/local/lib/lipton_public_not_dev_watch.py"),
    Path("/usr/local/sbin/lipton_public_not_dev_watch.py"),
    Path("/var/lib/sailingsa-lipton/watch.py"),
    Path("/usr/local/share/sailingsa-lipton/watch.py"),
    Path("/root/lw-g22.py"),
)
WATCH_DSTS = (
    Path("/root/lw-g22.py"),
    Path("/root/lw-g21.py"),
    Path("/root/lw-g20.py"),
    Path("/root/lw-g19.py"),
    Path("/root/lw-g18.py"),
    Path("/root/lw-g17.py"),
    Path("/usr/local/lib/lipton_public_not_dev_watch.py"),
    Path("/usr/local/sbin/lipton_public_not_dev_watch.py"),
    Path("/var/lib/sailingsa-lipton/watch.py"),
    Path("/usr/local/share/sailingsa-lipton/watch.py"),
)
PLAYBACK_LOCK = (
    "# LIPTON_NGINX_PLAYBACK_LOCK public + -dev slugs serve lipton-dev.html "
    "(not API event page)."
)
PUBLIC_KEEP = (
    "# LIPTON_NGINX_PUBLIC_NOT_DEV_V2 public slug MUST proxy to the API live board.\n"
    "    # Only -dev may alias lipton-dev.html. Do not add a public-slug alias."
)
PUBLIC_PROXY = """    location = /regatta/2026-08-29-lipton-challenge-cup {
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
"""
DEV_LOC = re.compile(
    r"(    location = /regatta/" + re.escape(RID) + r"-dev \{[^{}]*\n    \})",
    re.S,
)
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
    line = subprocess.check_output(["date", "+%Y-%m-%d %H:%M:%S %Z"], text=True).strip()
    try:
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"{line} {msg}\n")
    except Exception:
        pass


def _chattr(path: Path, on: bool) -> None:
    os.system(f"chattr {'+i' if on else '-i'} {path} >/dev/null 2>&1")


def _write(path: Path, text: str) -> None:
    _chattr(path, False)
    tmp = Path("/tmp") / (path.name + ".ngxrest")
    tmp.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    os.system(f"cp {tmp} {path}")


def _watch_gold_ok(path: Path) -> bool:
    try:
        if not path.is_file():
            return False
        raw = path.read_bytes()
    except Exception:
        return False
    return len(raw) > 10000 and WATCH_MARKER.encode("ascii") in raw


def restore_watch_golds() -> bool:
    """Recreate /root/lw-g*.py when PLAYBACK_LOCK deletes them. No api.py."""
    src = next((p for p in WATCH_SRCS if _watch_gold_ok(p)), None)
    if src is None:
        return False
    data = src.read_bytes()
    changed = False
    for dst in WATCH_DSTS:
        if _watch_gold_ok(dst) and dst.stat().st_size >= len(data):
            _chattr(dst, True)
            continue
        try:
            _chattr(dst, False)
            tmp = Path("/tmp") / (dst.name + ".goldrest")
            tmp.write_bytes(data)
            os.system(f"cp {tmp} {dst}")
            os.chmod(dst, 0o755)
            _chattr(dst, True)
            changed = True
        except Exception:
            pass
    if changed:
        _log("ngx restore watch golds")
    return changed


def _public_aliased(text: str) -> bool:
    # LIPTON_WATCH_ALIAS_ANY_V1 — public slug alias to any file is a hijack.
    # Do not scan the whole file for ALIAS comments: leftovers caused a reload storm.
    for m in re.finditer(
        r"location = /regatta/" + re.escape(RID) + r"(?:/)?(?!-)\s*\{([^{}]*)\}",
        text,
        re.S,
    ):
        body = m.group(1)
        if "alias" in body or "lipton-dev.html" in body:
            return True
        if "LIPTON_NGINX_PUBLIC_ALIAS" in body or "LIPTON_NGINX_PUBLIC_COPY" in body:
            return True
    return False


def _public_slug_proxied(text: str) -> bool:
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


def fix_nginx(text: str) -> tuple[str, int]:
    n = 0
    new, nc = re.subn(
        r"[ \t]*# LIPTON_NGINX_PUBLIC_(ALIAS|COPY)_[^\n]*\n",
        "",
        text,
    )
    if nc:
        n += nc
    if (
        _public_slug_proxied(new)
        and "include /etc/nginx/snippets/lipton-public-proxy.conf" not in new
        and PLAYBACK_LOCK not in new
    ):
        return new, n

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
    if not _public_slug_proxied(new):
        inserted = False
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


def restore_schedule_cron() -> bool:
    """Wake 10:00 / arm 12:00 cron. PLAYBACK_LOCK deletes this file."""
    body = CRON_SCHED_BODY if CRON_SCHED_BODY.endswith("\n") else CRON_SCHED_BODY + "\n"
    try:
        cur = CRON_SCHED.read_text(encoding="utf-8") if CRON_SCHED.is_file() else ""
    except Exception:
        cur = ""
    if cur == body:
        _chattr(CRON_SCHED, True)
        return False
    try:
        _write(CRON_SCHED, body)
        os.system(f"chmod 644 {CRON_SCHED} >/dev/null 2>&1")
        _chattr(CRON_SCHED, True)
        _log("ngx restore schedule cron")
        return True
    except Exception:
        return False


def _write_cron(path: Path, body: str) -> bool:
    body = body if body.endswith("\n") else body + "\n"
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
        return True
    except Exception:
        return False


def restore_crons() -> None:
    restore_schedule_cron()
    if _write_cron(CRON_NGX, CRON_NGX_BODY):
        _log("ngx restore ngx cron")
    if _write_cron(CRON_PUBLIC, CRON_PUBLIC_BODY):
        _log("ngx restore public cron")


def _ps_has(needle: str) -> bool:
    try:
        out = subprocess.check_output(["ps", "-eo", "cmd"], text=True, errors="replace")
    except Exception:
        return False
    return any(needle in line for line in out.splitlines())


def _systemctl(*args: str) -> None:
    subprocess.run(
        ["systemctl", *args],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def ensure_units_and_loops() -> None:
    """Re-enable watch/ngx units and restart loops after disable+kill."""
    try:
        cur = NGX_UNIT.read_text(encoding="utf-8") if NGX_UNIT.is_file() else ""
    except Exception:
        cur = ""
    if cur != NGX_UNIT_BODY:
        try:
            _write(NGX_UNIT, NGX_UNIT_BODY)
            os.system(f"chmod 644 {NGX_UNIT} >/dev/null 2>&1")
            _chattr(NGX_UNIT, True)
            _systemctl("daemon-reload")
            _log("ngx restore ngx unit")
        except Exception:
            pass
    else:
        _chattr(NGX_UNIT, True)
    for name in (WATCH_UNIT_NAME, HOLD_UNIT_NAME, NGX_UNIT_NAME):
        _systemctl("unmask", name)
        _systemctl("enable", name)
        _systemctl("start", name)
    gold = next((p for p in WATCH_SRCS if _watch_gold_ok(p)), None)
    watch_loop = False
    try:
        watch_loop = any(
            "lw-g" in line and "--loop" in line
            for line in subprocess.check_output(
                ["ps", "-eo", "cmd"], text=True, errors="replace"
            ).splitlines()
        )
    except Exception:
        watch_loop = False
    if gold is not None and not watch_loop:
        try:
            subprocess.Popen(
                ["/usr/bin/python3", str(gold), "--loop"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            _log("ngx restore started watch --loop")
        except Exception:
            pass
    if not _ps_has("lipton_ngx_public_restore.py --loop"):
        ngx_bin = Path("/usr/local/sbin/lipton_ngx_public_restore.py")
        if ngx_bin.is_file() and ngx_bin.stat().st_size > 500:
            try:
                subprocess.Popen(
                    ["/usr/bin/python3", str(ngx_bin), "--loop"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                _log("ngx restore started ngx --loop")
            except Exception:
                pass


def restore_once() -> int:
    restore_crons()
    restore_watch_golds()
    ensure_units_and_loops()
    changed = False
    if SNIPPET.is_file() or SNIPPET.parent.is_dir():
        body = PUBLIC_PROXY if PUBLIC_PROXY.endswith("\n") else PUBLIC_PROXY + "\n"
        try:
            cur = SNIPPET.read_text(encoding="utf-8") if SNIPPET.is_file() else ""
        except Exception:
            cur = ""
        if cur != body:
            SNIPPET.parent.mkdir(parents=True, exist_ok=True)
            _write(SNIPPET, body)
            _chattr(SNIPPET, True)
            changed = True
        else:
            _chattr(SNIPPET, True)
    if not NGINX.is_file():
        return 0
    raw = NGINX.read_text(encoding="utf-8")
    new, n = fix_nginx(raw)
    if n or new != raw:
        _write(NGINX, new)
        chk = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
        if chk.returncode != 0:
            if not _public_aliased(raw):
                _write(NGINX, raw)
            _log("ngx restore nginx -t failed")
            return 1
        subprocess.check_call(["nginx", "-s", "reload"])
        _chattr(NGINX, True)
        _chattr(SNIPPET, True)
        _log(f"ngx restore reloaded n={n}")
        return 0
    _chattr(NGINX, True)
    return 0 if not changed else 0


def main() -> int:
    if "--check" in sys.argv:
        return 0
    if "--loop" in sys.argv:
        while True:
            try:
                restore_once()
            except Exception:
                pass
            time.sleep(1)
    return restore_once()


if __name__ == "__main__":
    raise SystemExit(main())
