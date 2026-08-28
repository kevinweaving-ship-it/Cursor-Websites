#!/usr/bin/env python3
"""One-shot: public Lipton slug → proxy_pass. Never alias to lipton-dev.html."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import time
from pathlib import Path

WATCH = Path("/usr/local/lib/lipton_public_not_dev_watch.py")
if not WATCH.is_file() or WATCH.stat().st_size < 500:
    WATCH = Path("/usr/local/sbin/lipton_public_not_dev_watch.py")
if not WATCH.is_file() or WATCH.stat().st_size < 500:
    WATCH = Path(__file__).resolve().parent / "lipton_public_not_dev_watch.py"

spec = importlib.util.spec_from_file_location("lipton_watch", WATCH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

NGINX = Path("/etc/nginx/sites-enabled/sailingsa")
RID = "2026-08-29-lipton-challenge-cup"


def main() -> int:
    raw = NGINX.read_text(encoding="utf-8")
    new, n = mod.fix_nginx(raw)
    if new != raw:
        mod._write(NGINX, new)
        print("WROTE nginx public proxy n=", n)
    else:
        print("nginx already proxy or unchanged")
    chk = subprocess.run(["nginx", "-t"], capture_output=True, text=True)
    if chk.returncode != 0:
        print("FAIL nginx -t", chk.stderr, file=sys.stderr)
        if not mod._public_aliased(raw):
            mod._write(NGINX, raw)
        return 1
    subprocess.check_call(["nginx", "-s", "reload"])
    mod._chattr(NGINX, True)
    print("LOCKED")
    time.sleep(0.4)
    subprocess.run(
        [
            "curl",
            "-sk",
            "-o",
            "/tmp/lipton_apply_once.html",
            "--max-time",
            "12",
            "--resolve",
            "sailingsa.co.za:443:127.0.0.1",
            f"https://sailingsa.co.za/regatta/{RID}",
        ],
        check=False,
        timeout=15,
    )
    body = Path("/tmp/lipton_apply_once.html").read_bytes() if Path("/tmp/lipton_apply_once.html").is_file() else b""
    print(
        "ORIGIN",
        len(body),
        "dev",
        b"data-lipton-dev" in body,
        "page",
        b"regatta-page" in body,
    )
    return 0 if b"regatta-page" in body and b"data-lipton-dev" not in body else 2


if __name__ == "__main__":
    raise SystemExit(main())
