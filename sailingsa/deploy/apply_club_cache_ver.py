#!/usr/bin/env python3
"""Bust stale club HTML cache so every slug rebuilds gold HMYC cards."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARK = "CLUB_PAGE_CACHE_VER_gold_hmyc_v1"
text = API.read_text()
if MARK in text:
    print("ALREADY")
    raise SystemExit(0)

old_dir = '_CLUB_PAGE_DISK_DIR = "/var/tmp/sailingsa_club_pages"\n'
new_dir = (
    '_CLUB_PAGE_DISK_DIR = "/var/tmp/sailingsa_club_pages"\n'
    f'_CLUB_PAGE_CACHE_VER = "gold_hmyc_v1"  # {MARK}\n'
)
if old_dir not in text:
    raise SystemExit("DISK_DIR_NOT_FOUND")

old_disk = (
    '    disk = os.path.join(_CLUB_PAGE_DISK_DIR, re.sub(r"[^a-z0-9_-]+", "_", key) + ".html")\n'
)
new_disk = (
    '    disk = os.path.join(_CLUB_PAGE_DISK_DIR, re.sub(r"[^a-z0-9_-]+", "_", key) + "." + _CLUB_PAGE_CACHE_VER + ".html")\n'
)
if old_disk not in text:
    raise SystemExit("DISK_JOIN_NOT_FOUND")

text = text.replace(old_dir, new_dir, 1).replace(old_disk, new_disk, 1)
API.write_text(text)
print("CACHE_VER")
