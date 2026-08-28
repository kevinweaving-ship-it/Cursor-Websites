#!/usr/bin/env python3
"""Lipton playback hook. Always includes the public slug — never -dev only."""
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
sys.exit(runpy.run_path(str(HERE / "patch_lipton_public_slug.py"), run_name="__main__") or 0)
