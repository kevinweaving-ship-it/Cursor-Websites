#!/usr/bin/env python3
"""Throwaway home for every headless Chrome run, then delete it.

Chrome always writes a profile plus /tmp/.com.google.Chrome.* scratch
dirs. Callers must set HOME/TMPDIR inside a temp folder and rmtree it
when the peek/PDF finishes. A sweeper bins orphans left by crashes.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

CHROME_TMP = Path(os.environ.get("SSA_CHROME_TMP") or os.environ.get("MM_FB_CHROME_TMP") or "/var/tmp")

ORPHAN_GLOBS = (
    "/tmp/.com.google.Chrome.*",
    "/tmp/com.google.Chrome.*",
    "/tmp/scoped_dir*",
    "/tmp/ssa-regatta-pdf-*",
    "/tmp/ssa-mm-chrome-*",
    "/tmp/ssa-chrome-home",
    "/tmp/.cache/google-chrome-headless",
    "/tmp/.config/google-chrome-headless",
    "/tmp/.config/google-chrome",
    "/tmp/.cache/google-chrome",
    "/var/tmp/ssa-mm-chrome-*",
    "/var/tmp/ssa-chrome-*",
)


def make_chrome_run_dir(prefix: str = "ssa-chrome-") -> Path:
    CHROME_TMP.mkdir(parents=True, exist_ok=True)
    path = Path(tempfile.mkdtemp(prefix=prefix, dir=str(CHROME_TMP)))
    (path / "tmp").mkdir(exist_ok=True)
    return path


def chrome_env(profile: Path) -> dict:
    """Force Chrome scratch into this folder so nothing lands in /tmp."""
    tmp = profile / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = str(profile)
    env["XDG_CACHE_HOME"] = str(profile / "cache")
    env["XDG_CONFIG_HOME"] = str(profile / "config")
    env["TMPDIR"] = str(tmp)
    env["TMP"] = str(tmp)
    env["TEMP"] = str(tmp)
    return env


def delete_chrome_run_dir(profile: Path | str | None) -> None:
    if not profile:
        return
    shutil.rmtree(profile, ignore_errors=True)


def _iter_orphans() -> list[Path]:
    found: list[Path] = []
    for pattern in ORPHAN_GLOBS:
        parent = Path(pattern).parent
        name = Path(pattern).name
        if parent.is_dir():
            found.extend(parent.glob(name))
    unique: dict[str, Path] = {}
    for path in found:
        try:
            unique[str(path)] = path
        except OSError:
            continue
    return [unique[k] for k in sorted(unique)]


def sweep_orphaned_chrome(min_age_sec: float = 600, now: float | None = None) -> dict:
    """Delete leftover Chrome folders older than min_age_sec."""
    now = time.time() if now is None else now
    removed: list[str] = []
    skipped: list[str] = []
    for path in _iter_orphans():
        try:
            age = now - path.stat().st_mtime
        except OSError:
            continue
        if age < min_age_sec:
            skipped.append(str(path))
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            try:
                path.unlink()
            except OSError:
                pass
        if not path.exists():
            removed.append(str(path))
    return {"ok": True, "removed": len(removed), "skipped_fresh": len(skipped)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sweep", action="store_true", help="Bin leftover Chrome folders")
    parser.add_argument(
        "--min-age-sec",
        type=float,
        default=600,
        help="Only delete leftovers older than this many seconds (0 = all)",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.sweep:
        payload = sweep_orphaned_chrome(min_age_sec=args.min_age_sec)
        print(json.dumps(payload) if args.json else f"removed {payload['removed']} chrome leftovers")
        return 0
    print("use --sweep to bin leftover Chrome folders")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
