#!/usr/bin/env python3
"""Hide Meta / Alibaba / AWS / Google crawler cloud IPs from traffic Guest lists.

Apply on live:
  python3 sailingsa/deploy/patch_crawler_cloud_hide.py
Then: systemctl restart sailingsa-api
"""
from pathlib import Path
from typing import Optional
import ipaddress
import sys

API = Path("/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

HELPER = '''
def _lean_is_google_crawler_ip(ip: str) -> bool:
    """Googlebot / Google crawler egress prefixes (common published ranges)."""
    ip = (ip or "").strip()
    if not ip:
        return False
    return any(
        ip.startswith(p)
        for p in (
            "66.249.",
            "64.233.",
            "72.14.",
            "74.125.",
            "209.85.",
            "216.239.",
            "142.250.",
            "172.217.",
            "172.253.",
            "108.177.",
            "35.247.",  # sometimes Google cloud crawlers
        )
    )


def _lean_is_google_crawler_ua(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    if not ua:
        return False
    return any(
        x in ua
        for x in (
            "googlebot",
            "google-inspectiontool",
            "storebot-google",
            "adsbot-google",
            "apis-google",
            "mediapartners-google",
            "feedfetcher-google",
        )
    )


def _lean_is_crawler_cloud_ip(ip: str) -> bool:
    """Hard hide from Guest/Done: Meta, Google crawler, AWS/Alibaba datacenter ranges.

    These ranges are overwhelmingly scrapers/link-preview bots on this site — not SA home/mobile.
    """
    ip = (ip or "").strip()
    if not ip:
        return False
    try:
        if _lean_is_facebook_crawler_ip(ip):
            return True
    except Exception:
        pass
    try:
        if _lean_is_google_crawler_ip(ip):
            return True
    except Exception:
        pass
    try:
        if _lean_ip_is_cloud_datacenter(ip):
            return True
    except Exception:
        pass
    return False

'''

anchor = 'def _lean_bounce_home_bot(page_trail: list, current_path: str = "") -> bool:'
if "_lean_is_crawler_cloud_ip" not in text:
    if anchor not in text:
        print("FAIL: bounce_home anchor missing", file=sys.stderr)
        sys.exit(1)
    text = text.replace(anchor, HELPER + "\n" + anchor, 1)
    print("OK: inserted crawler cloud helpers")
else:
    print("SKIP: helpers already present")

old_offline = """            is_bot = False
            try:
                if ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
                elif (not is_staff) and (
                    _is_sailor_sas_id_path(path)
                    or _lean_behavior_confident_bot(trail, path, ip)
                    or _lean_same_page_swarm_bot(cur, ip=ip, path=path, page_trail=trail, window_minutes=30)
                    or _lean_sterile_short_trail_bot(trail, path, ip or "")
                    or _lean_is_junk_false_path(path)
                    or _lean_bounce_home_bot(trail, path)
                    or any(_lean_is_junk_false_path((t or {}).get("path") if isinstance(t, dict) else "") for t in (trail or []))
                ):
                    is_bot = True
                    try:
                        if _lean_trail_has_engagement(trail):
                            is_bot = False
                    except Exception:
                        pass
                    try:
                        if _lean_trail_is_club_share_only(trail, path):
                            is_bot = False
                    except Exception:
                        pass"""

new_offline = """            is_bot = False
            try:
                # Hard: Meta / Google / AWS / Alibaba ranges never count as Guest (IP-sure).
                if (not is_staff) and ip and _lean_is_crawler_cloud_ip(ip):
                    is_bot = True
                elif ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
                elif (not is_staff) and (
                    _is_sailor_sas_id_path(path)
                    or _lean_behavior_confident_bot(trail, path, ip)
                    or _lean_same_page_swarm_bot(cur, ip=ip, path=path, page_trail=trail, window_minutes=30)
                    or _lean_sterile_short_trail_bot(trail, path, ip or "")
                    or _lean_is_junk_false_path(path)
                    or _lean_bounce_home_bot(trail, path)
                    or any(_lean_is_junk_false_path((t or {}).get("path") if isinstance(t, dict) else "") for t in (trail or []))
                ):
                    is_bot = True
                    # Engagement / club-share pardon never clears crawler-cloud IPs
                    if not (ip and _lean_is_crawler_cloud_ip(ip)):
                        try:
                            if _lean_trail_has_engagement(trail):
                                is_bot = False
                        except Exception:
                            pass
                        try:
                            if _lean_trail_is_club_share_only(trail, path):
                                is_bot = False
                        except Exception:
                            pass"""

if old_offline in text:
    text = text.replace(old_offline, new_offline, 1)
    print("OK: patched offline is_bot")
elif "_lean_is_crawler_cloud_ip(ip):\n                    is_bot = True\n                elif ip and _lean_ip_is_quarantined" in text:
    print("SKIP: offline already patched")
else:
    print("FAIL: offline is_bot block not found", file=sys.stderr)
    sys.exit(2)

old_soft = """                    elif ip and (_lean_ip_is_quarantined(cur, ip) or _lean_ip_is_cloud_datacenter(ip)):
                        # Soft: cloud/quarantine alone is NOT 100% sure — let human browsers through
                        # unless quarantine reason is a hard probe/SAS signal."""

new_soft = """                    elif ip and _lean_is_crawler_cloud_ip(ip):
                        # Hard: Meta/Google/AWS/Alibaba ranges are scrapers on this site — never Guest.
                        is_bot = True
                        if ip:
                            try:
                                _lean_quarantine_ip(cur, ip, "crawler_cloud_ip")
                            except Exception:
                                pass
                    elif ip and _lean_ip_is_quarantined(cur, ip):
                        # Soft: quarantine alone is NOT 100% sure — let human browsers through
                        # unless quarantine reason is a hard probe/SAS signal."""

if old_soft in text:
    text = text.replace(old_soft, new_soft, 1)
    print("OK: patched live soft cloud")
elif "Hard: Meta/Google/AWS/Alibaba ranges are scrapers" in text:
    print("SKIP: live soft already patched")
else:
    print("FAIL: soft cloud live block not found", file=sys.stderr)
    sys.exit(3)

old_live_start = """                is_bot = False
                ua_live = d.get("device") or ""
                try:
                    # Probe / junk paths (e.g. /wp-backup.zip) are never Guest / sailor / registered.
                    if (not _is_trackable_page_path(path)) or _is_probe_blocked_path(path):"""

new_live_start = """                is_bot = False
                ua_live = d.get("device") or ""
                try:
                    # Hard IP ranges first (Meta / Google / AWS / Alibaba)
                    if ip and _lean_is_crawler_cloud_ip(ip):
                        is_bot = True
                        if ip:
                            try:
                                _lean_quarantine_ip(cur, ip, "crawler_cloud_ip")
                            except Exception:
                                pass
                    elif _lean_is_facebook_crawler_ua(ua_live) or _lean_is_google_crawler_ua(ua_live):
                        is_bot = True
                        if ip:
                            try:
                                _lean_quarantine_ip(cur, ip, "crawler_ua")
                            except Exception:
                                pass
                    # Probe / junk paths (e.g. /wp-backup.zip) are never Guest / sailor / registered.
                    elif (not _is_trackable_page_path(path)) or _is_probe_blocked_path(path):"""

if old_live_start in text:
    text = text.replace(old_live_start, new_live_start, 1)
    print("OK: patched live early crawler checks")
elif "Hard IP ranges first (Meta / Google / AWS / Alibaba)" in text:
    print("SKIP: live early already patched")
else:
    print("FAIL: live start block not found", file=sys.stderr)
    sys.exit(4)

old_nets = """                "34.0.0.0/8",
                "35.0.0.0/8",
                "52.0.0.0/8",
                "54.0.0.0/8","""
new_nets = """                "34.0.0.0/8",
                "35.0.0.0/8",
                "44.0.0.0/8",  # Amazon AWS (EC2 etc.) — link scrapers on this site
                "50.16.0.0/14",  # AWS legacy
                "52.0.0.0/8",
                "54.0.0.0/8","""
if old_nets in text:
    text = text.replace(old_nets, new_nets, 1)
    print("OK: added AWS 44.x / 50.16 nets")
elif "44.0.0.0/8" in text:
    print("SKIP: AWS 44.x already in nets")
else:
    print("WARN: cloud nets block not found for 44.x")

if text != orig:
    compile(text, str(API), "exec")
    API.write_text(text, encoding="utf-8")
    print("WROTE", API, "delta_bytes", len(text) - len(orig))
else:
    print("NO FILE CHANGE (already applied)")
