#!/usr/bin/env python3
"""Update /regattas and /sailors directory pages to landing-parity card lists."""
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
t = path.read_text(encoding="utf-8")

src = Path(__file__).with_name("directory_pages_gold.py").read_text(encoding="utf-8")
src = re.sub(r'^"""[\s\S]*?"""\n\n', "", src, count=1)
src = re.sub(r"^# Insert these functions.*\n\n", "", src)
# Drop _directory_gold_page_response — already in api.py
src = re.sub(
    r"^def _directory_gold_page_response[\s\S]*?^def _DIRECTORY_PAGE_ABOUT_CSS",
    "def _DIRECTORY_PAGE_ABOUT_CSS",
    src,
    count=1,
    flags=re.M,
)

m = re.search(
    r"def _DIRECTORY_PAGE_ABOUT_CSS[\s\S]*?^@app\.get\(\"/sailors\", response_class=HTMLResponse\)\ndef _directory_sailors_page\(\):",
    t,
    flags=re.M,
)
if not m:
    raise SystemExit("_DIRECTORY_PAGE_ABOUT_CSS block not found in target")

replacement = src.rstrip() + '\n\n@app.get("/sailors", response_class=HTMLResponse)\ndef _directory_sailors_page():'
t = t[: m.start()] + replacement + t[m.end() :]

path.write_text(t, encoding="utf-8")
print("patched directory landing parity in", path)
