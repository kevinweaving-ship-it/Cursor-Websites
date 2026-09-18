#!/usr/bin/env python3
"""Reuse one pooled connection for all serve_dev1_rank_page lookups.

After the nine connect() sites were moved onto db_connection(), each
lookup checked out a new pool slot. Under the 390 pileup that exhausted
the 2-12 pool. One shared checkout + _use_db_connection(held) keeps the
same SQL and still cannot exceed the pool.
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
    raise SystemExit(f"bounds start={start} end={end}")

# Insert shared checkout just before the first lookup try (club_slug = "" then try).
anchor = None
for i in range(start, end):
    if "club_slug: str = \"\"" in lines[i]:
        anchor = i
        break
if anchor is None:
    raise SystemExit("club_slug init not found")

insert = [
    "    _dev1_held = None\n",
    "    try:\n",
    "        _dev1_held = get_db_connection()\n",
    "    except Exception as _dev1_held_ex:\n",
    "        print(f\"[DEV1] shared pool conn failed: {_dev1_held_ex}\", flush=True)\n",
]
# avoid double insert
if "_dev1_held = None" in "".join(lines[start:end]):
    raise SystemExit("already patched shared held")

lines[anchor + 1 : anchor + 1] = insert
end += len(insert)

n = 0
for i in range(start, end):
    if "with db_connection() as " in lines[i]:
        lines[i] = lines[i].replace("with db_connection() as ", "with _use_db_connection(_dev1_held) as ")
        n += 1
if n != 9:
    raise SystemExit(f"expected 9 db_connection wraps, found {n}")

# Return after next-event except block: look for `_dev1_next_event_html = ""` following the ne_conn / pick_next_events block.
ret_at = None
for i in range(start, end):
    if "_dev1_next_event_html = \"\"" in lines[i] and i > start + 50:
        # the second assignment is in except; take the line after that except body
        ret_at = i
# find the last such in-function
for i in range(start, end):
    if lines[i].strip() == "_dev1_next_event_html = \"\"":
        ret_at = i
if ret_at is None:
    raise SystemExit("next-event except not found")

# insert after that assignment line (the except reset)
release = [
    "    if _dev1_held is not None:\n",
    "        try:\n",
    "            return_db_connection(_dev1_held)\n",
    "        except Exception:\n",
    "            pass\n",
    "        _dev1_held = None\n",
]
if "return_db_connection(_dev1_held)" in "".join(lines[start:end]):
    raise SystemExit("release already present")
lines[ret_at + 1 : ret_at + 1] = release

# Also close #116 hole: _club_regatta_entry_counts must not open unbounded connects.
club_n = 0
for i, l in enumerate(lines):
    if "conn = psycopg2.connect(DB_URL)" in l and i > 0 and "get_db_connection()" in lines[i - 2] + lines[i - 1] + l:
        # only the fallback inside _club_regatta_entry_counts
        if "own = True" in (lines[i + 1] if i + 1 < len(lines) else ""):
            lines[i] = l.replace(
                "conn = psycopg2.connect(DB_URL)",
                "raise",
            )
            club_n += 1
if club_n != 1:
    raise SystemExit(f"club fallback replacements={club_n}")

p.write_text("".join(lines), encoding="utf-8")
print(f"patched {p} reused={n} club_fallback_removed={club_n}")
