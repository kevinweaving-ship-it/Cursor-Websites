#!/usr/bin/env python3
"""Dev-1 embed: ?no_claim=1 puts stats in header (like verified sailors), skips claim banner."""
from pathlib import Path
import sys

path = Path(sys.argv[1])
t = path.read_text(encoding="utf-8")
marker = '_dev1_embed = str(request.query_params.get("embed") or "").strip().lower() in ("1", "true", "yes")'
if marker not in t:
    raise SystemExit("embed marker not found")
if '_dev1_no_claim' in t:
    print("already patched")
    sys.exit(0)

insert = (
    marker
    + '\n    _dev1_no_claim = _dev1_embed and str(request.query_params.get("no_claim") or "").strip().lower() in ("1", "true", "yes")'
)
t = t.replace(marker, insert, 1)

anchor = "    # Unclaimed → claim in header mid; next-event waits in ranks mid until SSA opens."
if anchor not in t:
    raise SystemExit("claim placement anchor not found")
t = t.replace(
    anchor,
    "    if _dev1_no_claim:\n"
    "        _dev1_claim_banner_html = \"\"\n"
    "        _dev1_claim_banner_js = \"\"\n"
    + anchor,
    1,
)

path.write_text(t, encoding="utf-8")
print("patched dev-1 no_claim for", path)
