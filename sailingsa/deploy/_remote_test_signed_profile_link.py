#!/usr/bin/env python3
"""Smoke: signed-in Live rows get /sailor/{slug} under name."""
import os, sys, json, psycopg2

sys.path.insert(0, "/var/www/sailingsa/api")
import importlib
api = importlib.import_module("api")

url = os.environ.get("DB_URL")
if not url:
    import subprocess
    pid = subprocess.check_output(
        "pgrep -f 'uvicorn api:app' | head -1", shell=True, text=True
    ).strip()
    env = open(f"/proc/{pid}/environ", "rb").read().split(b"\0")
    for e in env:
        if e.startswith(b"DB_URL="):
            url = e.split(b"=", 1)[1].decode()
            break

conn = psycopg2.connect(url)
cur = conn.cursor()
prof = api._lean_signed_in_profile(cur, "6903", "6903")
assert prof["who_href"] == "/sailor/robyn-patrick", prof
assert "Robyn" in (prof["who"] or ""), prof
assert api._lean_signed_in_profile(cur, "", "")["who_href"] == ""
# UI marker present
src = open("/var/www/sailingsa/api/api.py", encoding="utf-8").read()
assert "Signed-in: name + profile URL under name" in src
assert '"who_href": prof.get("who_href")' in src
print("OK signed Live profile link", json.dumps(prof))
cur.close()
conn.close()
