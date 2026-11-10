#!/usr/bin/env python3
"""Replace /regattas and /sailors directory UL lists with gold-header card pages + fuzzy search."""
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
t = path.read_text(encoding="utf-8")

if "def _regattas_directory_page_html" in t:
    print("already patched")
    sys.exit(0)

src = Path(__file__).with_name("directory_pages_gold.py").read_text(encoding="utf-8")
# Strip module docstring
src = re.sub(r'^"""[\s\S]*?"""\n\n', "", src, count=1)
# Drop comment line about insertion
src = re.sub(r"^# Insert these functions.*\n\n", "", src)

old_handlers = re.search(
    r"@app\.get\(\"/sailors\", response_class=HTMLResponse\)\ndef _directory_sailors_page\(\):[\s\S]*?"
    r"@app\.get\(\"/regattas\", response_class=HTMLResponse\)\ndef _directory_regattas_page\(\):[\s\S]*?"
    r"return HTMLResponse\(_directory_page_html\(\"/regattas\", items, \"regatta\", \"Regattas\"\)\)\n\n",
    t,
)
if not old_handlers:
    raise SystemExit("old sailors/regattas handlers not found")

new_handlers = '''@app.get("/sailors", response_class=HTMLResponse)
def _directory_sailors_page():
    """Directory: sailors with hub-style fuzzy search and full profile cards."""
    extra_head, inner = _sailors_directory_page_html()
    return _directory_gold_page_response("Sailors | SailingSA", inner, extra_head)


@app.get("/regattas", response_class=HTMLResponse)
def _directory_regattas_page():
    """Directory: regatta cards (parents only) with fuzzy search — same as landing list."""
    extra_head, inner = _regattas_directory_page_html()
    return _directory_gold_page_response("Regattas | SailingSA", inner, extra_head)

'''

insert_at = old_handlers.start()
t = t[:insert_at] + src + "\n" + new_handlers + t[old_handlers.end() :]

path.write_text(t, encoding="utf-8")
print("patched regattas/sailors directory pages")
