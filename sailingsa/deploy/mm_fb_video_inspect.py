#!/usr/bin/env python3
"""One-shot Facebook video inspect. Deletes the Chrome folder afterwards."""
from __future__ import annotations

import subprocess
import sys

sys.path.insert(0, "/var/www/sailingsa/deploy")
from ssa_headless_chrome import chrome_env, delete_chrome_run_dir, make_chrome_run_dir

CHROME = "/usr/bin/google-chrome"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def dump(url: str) -> str:
    profile = make_chrome_run_dir(prefix="ssa-chrome-inspect-")
    try:
        cmd = [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            f"--user-data-dir={profile}",
            "--timeout=18000",
            f"--user-agent={UA}",
            "--dump-dom",
            url,
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=50, env=chrome_env(profile)
        )
        return proc.stdout or ""
    finally:
        delete_chrome_run_dir(profile)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    if not url:
        raise SystemExit("usage: mm_fb_video_inspect.py URL")
    print(dump(url)[:2000])
