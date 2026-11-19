#!/usr/bin/env python3
"""Exclude scanner probes like /wp-backup.zip from guest/sailor traffic."""
from __future__ import annotations
import pathlib, sys, re

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

# 1) Expand probe blocked paths: any /wp-* plus backup archives
OLD_PROBE_END = '''    # Scanner junk. Real certbot tokens are long; "/file" etc. are probes.
    if path_only == "/.well-known" or path_only.startswith("/.well-known/"):
        acme = re.match(r"^/\\.well-known/acme-challenge/[A-Za-z0-9_-]{20,}$", path_only)
        if not acme:
            return True
    return False
'''

NEW_PROBE_END = '''    # Scanner junk. Real certbot tokens are long; "/file" etc. are probes.
    if path_only == "/.well-known" or path_only.startswith("/.well-known/"):
        acme = re.match(r"^/\\.well-known/acme-challenge/[A-Za-z0-9_-]{20,}$", path_only)
        if not acme:
            return True
    # WordPress / CMS probes that are not real SailingSA pages (e.g. /wp-backup.zip)
    if path_only.startswith("/wp-") or path_only.startswith("/wordpress"):
        return True
    # Backup / archive / dump probes — never guest traffic
    if any(
        base.endswith(ext) or path_only.endswith(ext)
        for ext in (
            ".zip",
            ".tar",
            ".tar.gz",
            ".tgz",
            ".gz",
            ".rar",
            ".7z",
            ".sql",
            ".sql.gz",
            ".bak",
            ".old",
            ".dump",
        )
    ):
        return True
    if any(tok in base for tok in ("backup", "dump", "wp-backup", "db_backup", "site-backup")):
        return True
    return False
'''

if "wp-backup" in text and '".zip"' in text and "Backup / archive / dump probes" in text:
    print("probe block already expanded")
elif OLD_PROBE_END in text:
    text = text.replace(OLD_PROBE_END, NEW_PROBE_END, 1)
    print("expanded _is_probe_blocked_path")
else:
    print("WARN: probe end block not found", file=sys.stderr)

# 2) Add archive extensions to trackable false list
OLD_EXTS = '''            ".php",
            ".asp",
            ".aspx",
            ".jsp",
            ".cgi",
        )
    ):
        return False
    return True


def _admin_current_page_label(path: Optional[str]) -> str:
'''

NEW_EXTS = '''            ".php",
            ".asp",
            ".aspx",
            ".jsp",
            ".cgi",
            ".zip",
            ".tar",
            ".gz",
            ".tgz",
            ".rar",
            ".7z",
            ".sql",
            ".bak",
            ".old",
            ".dump",
        )
    ):
        return False
    return True


def _admin_current_page_label(path: Optional[str]) -> str:
'''

if '".zip",\n            ".tar"' in text or '".zip",\n            ".tar",' in text:
    print("trackable exts already include zip")
elif OLD_EXTS in text:
    text = text.replace(OLD_EXTS, NEW_EXTS, 1)
    print("added archive exts to trackable deny list")
else:
    print("WARN: trackable ext block not found", file=sys.stderr)

# 3) Live labelling: non-trackable / probe path => bot, never Guest
OLD_LIVE = '''                is_bot = False
                ua_live = d.get("device") or ""
                try:
                    # Real Chrome/Safari/etc on a valid page path => pass as guest (not bot).
                    if _lean_human_traffic_pass(ua_live, path):
                        is_bot = False
                        if ip and _lean_ip_is_quarantined(cur, ip):
                            try:
                                cur.execute(
                                    "UPDATE public.traffic_quarantine_ips SET active = false, "
                                    "reason = LEFT(COALESCE(reason,'') || '|released_human_browser', 80), "
                                    "last_seen_at = NOW() WHERE ip_address = %s AND COALESCE(active, true) = true",
                                    (ip[:80],),
                                )
                            except Exception:
                                pass
                    elif ip and (_lean_ip_is_quarantined(cur, ip) or _lean_ip_is_cloud_datacenter(ip)):
                        is_bot = True
                        if not _is_human_browser_ua(ua_live):
                            _lean_quarantine_ip(
                                cur,
                                ip,
                                "cloud_datacenter" if _lean_ip_is_cloud_datacenter(ip) else "quarantine",
                            )
                except Exception:
                    if _lean_human_traffic_pass(ua_live, path):
                        is_bot = False
                    else:
                        is_bot = bool(ip and _lean_ip_is_cloud_datacenter(ip))
'''

NEW_LIVE = '''                is_bot = False
                ua_live = d.get("device") or ""
                try:
                    # Probe / junk paths (e.g. /wp-backup.zip) are never Guest / sailor / registered.
                    if (not _is_trackable_page_path(path)) or _is_probe_blocked_path(path):
                        is_bot = True
                        if ip:
                            try:
                                _lean_quarantine_ip(cur, ip, "probe_path")
                            except Exception:
                                pass
                    # Real Chrome/Safari/etc on a valid page path => pass as guest (not bot).
                    elif _lean_human_traffic_pass(ua_live, path):
                        is_bot = False
                        if ip and _lean_ip_is_quarantined(cur, ip):
                            try:
                                cur.execute(
                                    "UPDATE public.traffic_quarantine_ips SET active = false, "
                                    "reason = LEFT(COALESCE(reason,'') || '|released_human_browser', 80), "
                                    "last_seen_at = NOW() WHERE ip_address = %s AND COALESCE(active, true) = true",
                                    (ip[:80],),
                                )
                            except Exception:
                                pass
                    elif ip and (_lean_ip_is_quarantined(cur, ip) or _lean_ip_is_cloud_datacenter(ip)):
                        is_bot = True
                        if not _is_human_browser_ua(ua_live):
                            _lean_quarantine_ip(
                                cur,
                                ip,
                                "cloud_datacenter" if _lean_ip_is_cloud_datacenter(ip) else "quarantine",
                            )
                except Exception:
                    if (not _is_trackable_page_path(path)) or _is_probe_blocked_path(path):
                        is_bot = True
                    elif _lean_human_traffic_pass(ua_live, path):
                        is_bot = False
                    else:
                        is_bot = bool(ip and _lean_ip_is_cloud_datacenter(ip))
'''

if "probe_path" in text and "never Guest / sailor / registered" in text:
    print("live labelling already hardened")
elif OLD_LIVE in text:
    text = text.replace(OLD_LIVE, NEW_LIVE, 1)
    print("hardened live visitor labelling for probe paths")
else:
    print("WARN: live is_bot block not found", file=sys.stderr)

# 4) lean SQL path filter: exclude zip/backup probes
OLD_SQL = '''      AND {col} NOT LIKE '{pct}.php'
      AND {col} NOT LIKE '{pct}.env{pct}'
      AND {col} NOT LIKE '{pct}.git{pct}'
    """
'''

NEW_SQL = '''      AND {col} NOT LIKE '{pct}.php'
      AND {col} NOT LIKE '{pct}.env{pct}'
      AND {col} NOT LIKE '{pct}.git{pct}'
      AND {col} NOT LIKE '{pct}.zip'
      AND {col} NOT LIKE '{pct}.sql'
      AND {col} NOT LIKE '{pct}.bak'
      AND {col} NOT LIKE '{pct}backup{pct}'
      AND {col} NOT LIKE '/wp-backup{pct}'
    """
'''

if "NOT LIKE '{pct}.zip'" in text or 'NOT LIKE \'{pct}.zip\'' in text:
    print("lean SQL already excludes zip")
elif OLD_SQL in text:
    text = text.replace(OLD_SQL, NEW_SQL, 1)
    print("lean path SQL excludes zip/backup")
else:
    print("WARN: lean SQL block not found", file=sys.stderr)

if text == orig:
    print("no file changes")
    sys.exit(0)
API.write_text(text, encoding="utf-8")
print("wrote", API)
