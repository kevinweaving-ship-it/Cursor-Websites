#!/usr/bin/env python3
"""Replace serve_dev1_rank_page's unbounded psycopg2.connect() with db_connection().

SELECT-only blocks. No SQL/HTML/ranking changes.
Public /sailor/{slug} calls this same handler — that was the extra ~49 PG backends.
"""
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = p.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines(keepends=True)

start = end = None
for i, l in enumerate(lines):
    if l.startswith("def serve_dev1_rank_page"):
        start = i
        continue
    if start is not None and i > start and (l.startswith("def ") or l.startswith("async def ")):
        end = i
        break
if start is None or end is None:
    raise SystemExit(f"serve_dev1_rank_page bounds not found start={start} end={end}")

n = 0
sites = []
for i in range(start, end):
    if "psycopg2.connect(DB_URL)" in lines[i]:
        old = lines[i]
        lines[i] = lines[i].replace("psycopg2.connect(DB_URL)", "db_connection()")
        n += 1
        sites.append((i + 1, old.strip(), lines[i].strip()))

if n != 9:
    raise SystemExit(f"expected 9 connect sites in serve_dev1_rank_page, found {n}: {sites}")

new = "".join(lines)
if new == text:
    raise SystemExit("no change")
p.write_text(new, encoding="utf-8")
print(f"patched {p} sites={n}")
for lineno, a, b in sites:
    print(f"  L{lineno}: {a}  ->  {b}")
