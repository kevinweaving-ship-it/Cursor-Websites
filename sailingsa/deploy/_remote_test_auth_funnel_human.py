#!/usr/bin/env python3
"""Smoke: auth-funnel trail is human; Robyn-shaped trail never confident-bot."""
import sys
sys.path.insert(0, "/var/www/sailingsa/api")

# Import helpers without starting uvicorn app side effects is hard;
# exec just the functions from api by reading symbols after import api.
import importlib
api = importlib.import_module("api")

trail = [
    {"path": "/", "engagement": ["scrolled", "clicked"], "dwell_seconds": 20},
    {"path": "/signup.html", "engagement": ["clicked"], "dwell_seconds": 2},
    {"path": "/", "engagement": ["clicked", "scrolled"], "dwell_seconds": 86},
    {"path": "/login.html", "engagement": ["clicked"], "dwell_seconds": 0},
    {"path": "/", "engagement": ["scrolled", "clicked"], "dwell_seconds": 40},
    {"path": "/club/rcyc", "engagement": ["clicked"], "dwell_seconds": 0},
    {"path": "/sailor/adrian-kuttel", "engagement": ["clicked", "scrolled"], "dwell_seconds": 36},
    {"path": "/regatta/2025-09-14-zvyc-southern-charter-cape-classic", "engagement": ["clicked"], "dwell_seconds": 0},
]

assert api._lean_is_auth_funnel_path("/signup.html")
assert api._lean_is_auth_funnel_path("/login.html")
assert api._lean_trail_is_auth_funnel_human(trail)
assert api._lean_behavior_confident_bot(trail) is False
assert api._lean_offline_path_is_public("/signup.html") is True
assert api._lean_offline_path_is_public("/login.html") is True
print("OK auth-funnel human learn smoke")

# Persist learn note in meta (audit)
import os, json, psycopg2
from datetime import datetime, timezone

url = os.environ.get("DB_URL")
if not url:
    # from running uvicorn
    import subprocess
    pid = subprocess.check_output(
        "pgrep -f 'uvicorn api:app' | head -1", shell=True, text=True
    ).strip()
    if pid:
        env = open(f"/proc/{pid}/environ", "rb").read().split(b"\0")
        for e in env:
            if e.startswith(b"DB_URL="):
                url = e.split(b"=", 1)[1].decode()
                break
if url:
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    note = {
        "pattern": "land_signup_login_browse",
        "example": {
            "who": "Robyn Patrick",
            "sas_id": "6903",
            "ip": "165.73.122.145",
            "date": "2026-08-15",
            "shape": "home → signup → login → club/sailor/regatta/rankings (same IP guest→signed-in)",
        },
        "learned_at": datetime.now(timezone.utc).isoformat(),
        "rule": "_lean_trail_is_auth_funnel_human",
    }
    cur.execute(
        """
        INSERT INTO traffic_tracking_meta (meta_key, meta_value_json, created_at, updated_at)
        VALUES ('learned_human_auth_funnel', %s::jsonb, NOW(), NOW())
        ON CONFLICT (meta_key) DO UPDATE
          SET meta_value_json = EXCLUDED.meta_value_json,
              updated_at = NOW()
        """,
        (json.dumps(note),),
    )
    conn.commit()
    cur.close()
    conn.close()
    print("OK wrote traffic_tracking_meta.learned_human_auth_funnel")
else:
    print("WARN no DB_URL — skipped meta write")
