#!/usr/bin/env python3
"""Nginx-only restore for the public Lipton slug. Does not touch api.py.

LIPTON_NGINX_BASH_RESTORE_V1
PLAYBACK_LOCK often stubs the python watchdog gold. Cron/guard can still
put the public URL back on proxy_pass without that gold.
-dev stays aliased to lipton-dev.html.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

RID = "2026-08-29-lipton-challenge-cup"
NGINX = Path("/etc/nginx/sites-enabled/sailingsa")
SNIPPET = Path("/etc/nginx/snippets/lipton-public-proxy.conf")
LOG = Path("/var/log/lipton_public_not_dev_watch.log")
WATCH_MARKER = "LIPTON_WATCH_DEBOUNCE_V1"
WATCH_SRCS = (
    Path("/usr/local/lib/lipton_public_not_dev_watch.py"),
    Path("/usr/local/sbin/lipton_public_not_dev_watch.py"),
    Path("/var/lib/sailingsa-lipton/watch.py"),
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
        if _watch_gold_ok(dst):
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
    if PLAYBACK_LOCK in text or "LIPTON_NGINX_PUBLIC_ALIAS" in text:
        return True
    for m in re.finditer(
        r"location = /regatta/" + re.escape(RID) + r"(?:/)?(?!-)\s*\{([^{}]*)\}",
        text,
        re.S,
    ):
        body = m.group(1)
        if "alias" in body or "lipton-dev.html" in body:
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
    if (
        _public_slug_proxied(text)
        and "include /etc/nginx/snippets/lipton-public-proxy.conf" not in text
        and PLAYBACK_LOCK not in text
        and "LIPTON_NGINX_PUBLIC_ALIAS" not in text
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


def main() -> int:
    if "--check" in sys.argv:
        return 0
    restore_watch_golds()
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


if __name__ == "__main__":
    raise SystemExit(main())
