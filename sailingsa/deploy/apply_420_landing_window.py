#!/usr/bin/env python3
"""Show 420 Nationals on landing: live window today+5 missed start_date +8 days."""
from pathlib import Path
import os, glob

API = Path("/var/www/sailingsa/api/api.py")
MARK = "LANDING_420_WINDOW_v1"
OLD = "AND r.start_date <= (timezone('Africa/Johannesburg', now()))::date + 5"
NEW = (
    "AND r.start_date <= (timezone('Africa/Johannesburg', now()))::date + 10"
    "  # " + MARK
)
text = API.read_text()
if MARK in text:
    print("ALREADY")
else:
    if OLD not in text:
        raise SystemExit("ERROR: live window +5 not found")
    n = text.count(OLD)
    if n != 1:
        raise SystemExit("ERROR: expected 1 window, found %s" % n)
    API.write_text(text.replace(OLD, NEW, 1))
    print("PATCHED", MARK)

# drop with-counts disk cache if present
for pat in (
    "/var/tmp/sailingsa_regatta_with_counts.json",
    "/var/tmp/sailingsa_regatta_with_counts*",
):
    for p in glob.glob(pat):
        try:
            os.remove(p)
            print("DEL", p)
        except OSError as e:
            print("DEL_ERR", p, e)
