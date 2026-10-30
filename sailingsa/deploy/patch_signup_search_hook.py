#!/usr/bin/env python3
from pathlib import Path
import shutil
import time

p = Path("/var/www/sailingsa/signup.html")
t = p.read_text(encoding="utf-8", errors="replace")
if "trackClaimFunnel('sailor_search'" in t or 'trackClaimFunnel("sailor_search"' in t:
    # may already be from result click only
    pass
bak = Path(f"/root/backups/signup.html.searchhook.{time.strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(p, bak)
print("BACKUP", bak)

old = """            console.log('[DEBUG] handleProfileSearch: Starting search with query:', query);
            showLoading();
            hideError();

            try {
                const results = await searchProfiles(query);
"""
new = """            console.log('[DEBUG] handleProfileSearch: Starting search with query:', query);
            showLoading();
            hideError();
            try {
                claimSearchQuery = String(query || '').trim();
                if (claimSearchQuery) trackClaimFunnel('sailor_search', claimSelectedSasId || '', true, '', { query: claimSearchQuery, entry: claimEntry });
            } catch (eSearch) {}

            try {
                const results = await searchProfiles(query);
"""
if old not in t:
    raise SystemExit("block not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("OK")
