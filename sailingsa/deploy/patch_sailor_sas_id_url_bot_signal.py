#!/usr/bin/env python3
"""Treat /sailor/{SAS_ID} numeric URLs as bot signal (not from Google slug index).

Real users use /sailor/{slug}. Crawlers often hit /sailor/12345 then redirect to slug.
"""
from __future__ import annotations
import pathlib, sys, re

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

HELPER_MARKER = "def _is_sailor_sas_id_path(path: Optional[str]) -> bool:"
HELPER = '''
def _is_sailor_sas_id_path(path: Optional[str]) -> bool:
    """True for /sailor/{digits} — SAS ID URLs (not slug).

    Real users (and Google index) use /sailor/{slug}. Numeric SAS ID sailor URLs are a
    bot/scraper signal for testing and labelling.
    """
    p = _sanitize_session_path(path or "")
    path_only = (p.split("?", 1)[0] or "/").rstrip("/") or "/"
    m = re.match(r"^/sailor/(\\d+)$", path_only)
    return bool(m)

'''

if HELPER_MARKER in text:
    print("helper already present")
else:
    anchor = "def _is_human_browser_ua(user_agent: str) -> bool:"
    if anchor not in text:
        # fallback after trackable
        anchor = "def _is_trackable_page_path(path: Optional[str]) -> bool:"
    if anchor not in text:
        print("ERROR: no insert anchor", file=sys.stderr)
        sys.exit(1)
    text = text.replace(anchor, HELPER + "\n" + anchor, 1)
    print("inserted _is_sailor_sas_id_path")

# Live labelling: SAS ID sailor URL => bot (unless staff IP)
# Find the probe_path block we added earlier and extend
OLD = '''                    # Probe / junk paths (e.g. /wp-backup.zip) are never Guest / sailor / registered.
                    if (not _is_trackable_page_path(path)) or _is_probe_blocked_path(path):
                        is_bot = True
                        if ip:
                            try:
                                _lean_quarantine_ip(cur, ip, "probe_path")
                            except Exception:
                                pass
'''

NEW = '''                    # Probe / junk paths (e.g. /wp-backup.zip) are never Guest / sailor / registered.
                    if (not _is_trackable_page_path(path)) or _is_probe_blocked_path(path):
                        is_bot = True
                        if ip:
                            try:
                                _lean_quarantine_ip(cur, ip, "probe_path")
                            except Exception:
                                pass
                    # /sailor/{SAS_ID} numeric URLs are not from Google slug index → bot signal
                    elif _is_sailor_sas_id_path(path):
                        is_bot = True
                        if ip:
                            try:
                                _lean_quarantine_ip(cur, ip, "sailor_sas_id_url")
                            except Exception:
                                pass
'''

if "sailor_sas_id_url" in text and "_is_sailor_sas_id_path(path)" in text:
    print("live SAS-id bot signal already present")
elif OLD in text:
    text = text.replace(OLD, NEW, 1)
    print("patched live labelling for SAS-id sailor URLs")
else:
    print("WARN: live probe block not found for SAS-id patch", file=sys.stderr)

# Public upsert: if path is SAS id sailor URL, quarantine (still record hit for audit)
OLD_UPSERT_START = '''def _upsert_public_session(cur, visitor_id: str, path: str, user_agent: str, ip_address: str) -> None:
    """Upsert anonymous visitor; one live row per unique IP; session history; page hits."""
    if not visitor_id or not _is_trackable_page_path(path):
        return
    if _is_bot_user_agent(user_agent):
        return
    if _is_noise_public_ip(ip_address):
        return
'''

NEW_UPSERT_START = '''def _upsert_public_session(cur, visitor_id: str, path: str, user_agent: str, ip_address: str) -> None:
    """Upsert anonymous visitor; one live row per unique IP; session history; page hits."""
    if not visitor_id or not _is_trackable_page_path(path):
        return
    if _is_bot_user_agent(user_agent):
        return
    if _is_noise_public_ip(ip_address):
        return
    # Numeric /sailor/{SAS_ID} — record then quarantine (bot/scraper signal; not Google slug traffic)
    try:
        if _is_sailor_sas_id_path(path) and ip_address:
            _lean_quarantine_ip(cur, ip_address, "sailor_sas_id_url")
    except Exception:
        pass
'''

if "Numeric /sailor/{SAS_ID}" in text:
    print("upsert SAS-id quarantine already present")
elif OLD_UPSERT_START in text:
    text = text.replace(OLD_UPSERT_START, NEW_UPSERT_START, 1)
    print("patched upsert to quarantine SAS-id sailor URL hits")
else:
    print("WARN: upsert start not found", file=sys.stderr)

# Lean path SQL: still count slug pages; optionally we keep SAS id paths out of Hits/Vis via quarantine
# Add note in lean path filter - exclude /sailor/{digits} from unified stats
OLD_SQL = '''      AND {col} NOT LIKE '/wp-backup{pct}'
    """
'''
NEW_SQL = '''      AND {col} NOT LIKE '/wp-backup{pct}'
      AND {col} !~ '^/sailor/[0-9]+/?$'
    """
'''
if "!~ '^/sailor/[0-9]+/?$'" in text or "~ '^/sailor/[0-9]+'" in text:
    print("lean SQL already excludes numeric sailor URLs")
elif OLD_SQL in text:
    text = text.replace(OLD_SQL, NEW_SQL, 1)
    print("lean Hits/Vis exclude numeric /sailor/{id} URLs")
else:
    print("WARN: lean SQL zip block not found for SAS-id exclude", file=sys.stderr)

if text == orig:
    print("no changes")
    sys.exit(0)
API.write_text(text, encoding="utf-8")
print("wrote", API)
