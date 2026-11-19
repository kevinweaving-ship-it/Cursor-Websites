#!/usr/bin/env python3
"""Tweak Live table header to Last page / session total."""
from pathlib import Path
import py_compile
import shutil
from datetime import datetime, timezone

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-live-hdr-{stamp}"))
    text = API.read_text(encoding="utf-8")
    old = 'var html="<table><thead><tr><th>Who</th><th>Page</th><th>When</th></tr></thead><tbody>";'
    new = 'var html="<table><thead><tr><th>Who</th><th>Last page / session</th><th>When</th></tr></thead><tbody>";'
    if old not in text:
        if "Last page / session" in text:
            print("OK already")
            return
        raise SystemExit("live header not found")
    text = text.replace(old, new, 1)
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print("OK live header")


if __name__ == "__main__":
    main()
