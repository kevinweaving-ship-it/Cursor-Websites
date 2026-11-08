#!/usr/bin/env python3
"""Stop SAS-ID scrapers (e.g. Alibaba /sailor/1186 → slug) from showing as guessed guests.

- Never release sailor_sas_id_url quarantine for “human browser”
- Live: if session trail includes /sailor/{digits} → bot
- Live: if IP quarantined for sailor_sas_id_url → bot even on slug last_path
"""
from __future__ import annotations

import pathlib
import sys
import py_compile

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")
orig = text

# Helper near session trail helpers
HELPER = r'''
def _lean_visitor_used_sas_id_url(cur, visitor_id: str = "", ip: str = "") -> bool:
    """True if this visitor/IP opened /sailor/{digits} recently (scraper entry)."""
    vid = (visitor_id or "").strip()
    ip_s = (ip or "").strip()
    try:
        if not table_exists("public_page_hits"):
            return False
        if vid:
            cur.execute(
                """
                SELECT 1 FROM public.public_page_hits
                WHERE visitor_id = %s
                  AND occurred_at > NOW() - INTERVAL '45 minutes'
                  AND path ~ '^/sailor/[0-9]+$'
                LIMIT 1
                """,
                (vid,),
            )
            if cur.fetchone():
                return True
        if ip_s:
            cur.execute(
                """
                SELECT 1 FROM public.public_page_hits
                WHERE ip_address = %s
                  AND occurred_at > NOW() - INTERVAL '45 minutes'
                  AND path ~ '^/sailor/[0-9]+$'
                LIMIT 1
                """,
                (ip_s,),
            )
            if cur.fetchone():
                return True
    except Exception:
        return False
    return False


def _lean_quarantine_reason(cur, ip_address: str) -> str:
    ip = (ip_address or "").strip()
    if not ip:
        return ""
    try:
        _lean_ensure_quarantine_table(cur)
        cur.execute(
            """
            SELECT COALESCE(reason, '') FROM public.traffic_quarantine_ips
            WHERE ip_address = %s AND COALESCE(active, true) = true
            LIMIT 1
            """,
            (ip[:80],),
        )
        row = cur.fetchone()
        if not row:
            return ""
        return str(row[0] if not isinstance(row, dict) else next(iter(row.values())) or "")
    except Exception:
        return ""

'''

if "_lean_visitor_used_sas_id_url" not in text:
    mark = "def _lean_fmt_dwell_seconds(dwell) -> str:"
    if mark not in text:
        raise SystemExit("fmt dwell marker missing")
    text = text.replace(mark, HELPER + mark, 1)

# Fix live classification: after human pass block, don't release sas_id quarantine
old = '''                    # Real Chrome/Safari/etc on a valid page path => pass as guest (not bot).
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
                    elif ip and (_lean_ip_is_quarantined(cur, ip) or _lean_ip_is_cloud_datacenter(ip)):'''

new = '''                    # Real browser on a valid page — but SAS-ID entry (/sailor/123) is still bot.
                    elif _lean_human_traffic_pass(ua_live, path):
                        used_sas = False
                        try:
                            used_sas = _lean_visitor_used_sas_id_url(cur, full_vid if "full_vid" in dir() else "", ip)
                        except Exception:
                            used_sas = False
                        # full_vid is set in anon branch; signed uses sess vid below — check both
                        if not used_sas:
                            try:
                                used_sas = _lean_visitor_used_sas_id_url(
                                    cur, (d.get("visitor_id") or ""), ip
                                )
                            except Exception:
                                pass
                        qreason = ""
                        try:
                            qreason = _lean_quarantine_reason(cur, ip) if ip else ""
                        except Exception:
                            qreason = ""
                        if used_sas or ("sailor_sas_id_url" in (qreason or "")):
                            is_bot = True
                            if ip:
                                try:
                                    _lean_quarantine_ip(cur, ip, "sailor_sas_id_url")
                                except Exception:
                                    pass
                        else:
                            is_bot = False
                            if ip and _lean_ip_is_quarantined(cur, ip):
                                # Never release SAS-ID / agent / probe quarantines
                                if any(
                                    x in (qreason or "")
                                    for x in (
                                        "sailor_sas_id_url",
                                        "agent_test",
                                        "probe_path",
                                    )
                                ):
                                    is_bot = True
                                else:
                                    try:
                                        cur.execute(
                                            "UPDATE public.traffic_quarantine_ips SET active = false, "
                                            "reason = LEFT(COALESCE(reason,'') || '|released_human_browser', 80), "
                                            "last_seen_at = NOW() WHERE ip_address = %s AND COALESCE(active, true) = true",
                                            (ip[:80],),
                                        )
                                    except Exception:
                                        pass
                    elif ip and (_lean_ip_is_quarantined(cur, ip) or _lean_ip_is_cloud_datacenter(ip)):'''

# The live block uses `vid` before full_vid in older code - check actual live file for anon vars
# Better: use a cleaner replacement that references variables that exist in anon loop

# Find exact block in lean_traffic_api_live for anon
live_start = text.find("def lean_traffic_api_live")
live_chunk = text[live_start : live_start + 12000]
if "Real Chrome/Safari/etc on a valid page path" not in live_chunk and "Real browser on a valid page" not in live_chunk:
    # maybe already partially patched wording
    if "_lean_visitor_used_sas_id_url" in live_chunk and "sailor_sas_id_url" in live_chunk[live_chunk.find("human_traffic_pass"):]:
        print("live classify may already be patched")
    else:
        # find human pass in live
        i = live_chunk.find("_lean_human_traffic_pass(ua_live, path)")
        print("CONTEXT:\n", live_chunk[i - 200 : i + 600])
        raise SystemExit("human pass block wording mismatch")

if old in text:
    text = text.replace(old, new, 1)
else:
    # try already-new skip
    if "Never release SAS-ID" in text:
        print("release guard already present")
    else:
        raise SystemExit("old human-pass release block not found")

# Fix the messy full_vid/dir() hack - replace with clean version using full_vid only
# (anon branch has full_vid; the classify block is only in anon loop)
messy = '''                    elif _lean_human_traffic_pass(ua_live, path):
                        used_sas = False
                        try:
                            used_sas = _lean_visitor_used_sas_id_url(cur, full_vid if "full_vid" in dir() else "", ip)
                        except Exception:
                            used_sas = False
                        # full_vid is set in anon branch; signed uses sess vid below — check both
                        if not used_sas:
                            try:
                                used_sas = _lean_visitor_used_sas_id_url(
                                    cur, (d.get("visitor_id") or ""), ip
                                )
                            except Exception:
                                pass
                        qreason = ""
                        try:
                            qreason = _lean_quarantine_reason(cur, ip) if ip else ""
                        except Exception:
                            qreason = ""
                        if used_sas or ("sailor_sas_id_url" in (qreason or "")):
                            is_bot = True
                            if ip:
                                try:
                                    _lean_quarantine_ip(cur, ip, "sailor_sas_id_url")
                                except Exception:
                                    pass
                        else:
                            is_bot = False
                            if ip and _lean_ip_is_quarantined(cur, ip):
                                # Never release SAS-ID / agent / probe quarantines
                                if any(
                                    x in (qreason or "")
                                    for x in (
                                        "sailor_sas_id_url",
                                        "agent_test",
                                        "probe_path",
                                    )
                                ):
                                    is_bot = True
                                else:
                                    try:
                                        cur.execute(
                                            "UPDATE public.traffic_quarantine_ips SET active = false, "
                                            "reason = LEFT(COALESCE(reason,'') || '|released_human_browser', 80), "
                                            "last_seen_at = NOW() WHERE ip_address = %s AND COALESCE(active, true) = true",
                                            (ip[:80],),
                                        )
                                    except Exception:
                                        pass'''

clean = '''                    elif _lean_human_traffic_pass(ua_live, path):
                        used_sas = False
                        try:
                            used_sas = _lean_visitor_used_sas_id_url(cur, full_vid, ip)
                        except Exception:
                            used_sas = False
                        qreason = ""
                        try:
                            # Include inactive rows that were wrongly released after SAS-ID entry
                            cur.execute(
                                """
                                SELECT COALESCE(reason,'') FROM public.traffic_quarantine_ips
                                WHERE ip_address = %s
                                ORDER BY last_seen_at DESC NULLS LAST LIMIT 1
                                """,
                                (ip[:80],),
                            )
                            qr = cur.fetchone()
                            if qr:
                                qreason = str(qr[0] if not isinstance(qr, dict) else next(iter(qr.values())) or "")
                        except Exception:
                            qreason = _lean_quarantine_reason(cur, ip) if ip else ""
                        if used_sas or ("sailor_sas_id_url" in (qreason or "")):
                            is_bot = True
                            if ip:
                                try:
                                    _lean_quarantine_ip(cur, ip, "sailor_sas_id_url")
                                except Exception:
                                    pass
                        else:
                            is_bot = False
                            if ip and _lean_ip_is_quarantined(cur, ip):
                                if any(
                                    x in (qreason or "")
                                    for x in (
                                        "sailor_sas_id_url",
                                        "agent_test",
                                        "probe_path",
                                    )
                                ):
                                    is_bot = True
                                else:
                                    try:
                                        cur.execute(
                                            "UPDATE public.traffic_quarantine_ips SET active = false, "
                                            "reason = LEFT(COALESCE(reason,'') || '|released_human_browser', 80), "
                                            "last_seen_at = NOW() WHERE ip_address = %s AND COALESCE(active, true) = true"
                                            " AND COALESCE(reason,'') NOT LIKE '%%sailor_sas_id_url%%'",
                                            (ip[:80],),
                                        )
                                    except Exception:
                                        pass'''

if messy in text:
    text = text.replace(messy, clean, 1)
elif clean[:80] in text:
    print("clean classify already present")
else:
    # if new was applied with messy, fix; if neither, fail
    if "used_sas = _lean_visitor_used_sas_id_url(cur, full_vid" in text:
        print("partial clean ok")
    else:
        raise SystemExit("could not clean classify block")

# Also: upsert should not allow human pass to skip quarantine for sas id — already quarantines on sas path.
# Strengthen: don't call human release anywhere else for sailor_sas_id
text2 = text
# Fix released_human_browser updates sitewide to exclude sailor_sas_id_url
old_rel = '''                                cur.execute(
                                    "UPDATE public.traffic_quarantine_ips SET active = false, "
                                    "reason = LEFT(COALESCE(reason,'') || '|released_human_browser', 80), "
                                    "last_seen_at = NOW() WHERE ip_address = %s AND COALESCE(active, true) = true",
                                    (ip[:80],),
                                )'''
new_rel = '''                                cur.execute(
                                    "UPDATE public.traffic_quarantine_ips SET active = false, "
                                    "reason = LEFT(COALESCE(reason,'') || '|released_human_browser', 80), "
                                    "last_seen_at = NOW() WHERE ip_address = %s AND COALESCE(active, true) = true "
                                    "AND COALESCE(reason,'') NOT LIKE '%%sailor_sas_id_url%%' "
                                    "AND COALESCE(reason,'') NOT LIKE '%%agent_test%%'",
                                    (ip[:80],),
                                )'''
# Only replace remaining old-style releases (without NOT LIKE)
count = 0
while old_rel in text2:
    text2 = text2.replace(old_rel, new_rel, 1)
    count += 1
print("release guards replaced", count)
text = text2

if text == orig:
    raise SystemExit("no changes")
API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print(f"OK (+{len(text)-len(orig)} bytes)")
