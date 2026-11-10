#!/usr/bin/env python3
"""Fix broken claim CTA onclick quotes in index.html that broke sailor/regatta search JS."""
from pathlib import Path
import shutil, time
p = Path("/var/www/sailingsa/index.html")
bak = Path(f"/root/backups/index.html.fix_claim_onclick.{time.strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(p, bak)
t = p.read_text(encoding="utf-8", errors="replace")
# If already fixed, exit
if "\\'claim_cta_click\\'" in t and "window.__trackFunnelEvent('claim_cta_click'" not in t.split("claimCtaHtml")[1][:800]:
    print("already fixed")
else:
    print("check manually")
print("backup", bak)
