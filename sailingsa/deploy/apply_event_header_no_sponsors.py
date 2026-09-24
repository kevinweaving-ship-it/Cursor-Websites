#!/usr/bin/env python3
"""Remove sponsor names/logos from every event/regatta main header."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

MARK = "EVENT_HEADER_NO_SPONSORS_v1"
PATHS = (
    Path("/var/www/sailingsa/deploy/sponsor_profiles.py"),
    Path("/var/www/sailingsa/api/sponsor_profiles.py"),
)
OLD = '''def regatta_header_sponsor_html(regatta_id: str, event_name: str = "") -> str:
    """Standalone regatta header chip for explicitly assigned sponsors."""
    rid = _safe_text(regatta_id)
    if not rid:
        return ""
'''
NEW = (
    "def regatta_header_sponsor_html(regatta_id: str, event_name: str = \"\") -> str:\n"
    f'    """Sponsors stay on /sponsors pages — never in the event main header. {MARK}"""\n'
    "    return \"\"\n"
    "    rid = _safe_text(regatta_id)\n"
    "    if not rid:\n"
    "        return \"\"\n"
)


def patch(path: Path) -> None:
    if not path.is_file():
        print("MISS", path)
        return
    text = path.read_text()
    if MARK in text:
        print("ALREADY", path)
        return
    n = text.count(OLD)
    if n != 1:
        raise SystemExit(f"ANCHOR_{path.name}_{n}")
    path.write_text(text.replace(OLD, NEW, 1))
    subprocess.check_call(["python3", "-m", "py_compile", str(path)])
    print("OK", path)


def verify_fn() -> None:
    import sys
    sys.path.insert(0, "/var/www/sailingsa/deploy")
    import importlib
    import sponsor_profiles as sp
    importlib.reload(sp)
    samples = (
        "2026-08-29-lipton-challenge-cup",
        "2026-05-23-ullman-sails-womens-series-day-1",
        "2026-09-19-hmyc-midmar-cup",
        "2026-09-13-zvyc-cape-classic",
    )
    for rid in samples:
        html = sp.regatta_header_sponsor_html(rid, "")
        print("FN", rid, repr(html))
        if html:
            raise SystemExit("REFUSE function still returns header html")


def main() -> None:
    for p in PATHS:
        patch(p)
    verify_fn()
    subprocess.check_call(["systemctl", "restart", "sailingsa-api"])
    time.sleep(6)
    print("API_SVC", subprocess.check_output(["systemctl", "is-active", "sailingsa-api"], text=True).strip())
    print("DONE", MARK)


if __name__ == "__main__":
    main()
