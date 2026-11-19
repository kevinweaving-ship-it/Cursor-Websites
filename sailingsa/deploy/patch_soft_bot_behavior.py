#!/usr/bin/env python3
"""Softer Live bot gate: Guest unless high-confidence bot behaviour."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

BEHAVIOR_FN = '''def _lean_behavior_confident_bot(page_trail: list, current_path: str = "") -> bool:
    """High-confidence scraper pattern (not a maybe).

    Confirmed shape we have seen (e.g. Alibaba deep-link swarm):
      - never touches home/landing
      - enters on /boat/ or /sailor/
      - short hop trail (3–8 URLs)
      - almost all dwells <= 2s (then often stops)
    """
    trail = page_trail if isinstance(page_trail, list) else []
    paths = []
    dwells = []
    for pt in trail:
        if not isinstance(pt, dict):
            continue
        p = (pt.get("path") or "").split("?", 1)[0].strip() or "/"
        paths.append(p)
        d = pt.get("dwell_seconds")
        # ignore still-open last hop for the "all short" test
        if pt.get("open"):
            continue
        try:
            dwells.append(int(d) if d is not None else 0)
        except Exception:
            dwells.append(0)
    if not paths:
        p0 = (current_path or "").split("?", 1)[0].strip() or "/"
        paths = [p0]
    n = len(paths)
    if n < 3 or n > 8:
        return False
    if any(p in ("/", "/index.html") for p in paths):
        return False
    first = paths[0]
    if not (first.startswith("/boat/") or first.startswith("/sailor/")):
        return False
    # Need enough closed hops to judge dwell; if all open/unknown, not confident yet
    if len(dwells) < max(2, n - 1):
        # deep-link entry alone is only a smell — not 100% sure
        return False
    short = sum(1 for d in dwells if d <= 2)
    if short < len(dwells) * 0.75:
        return False
    return True


'''


def _replace_bot_block(text: str, start_marker: str, end_marker: str) -> str:
    """Replace is_bot decision block between markers once."""
    # We'll do targeted replacements instead
    return text


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-soft-bot-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    if "def _lean_behavior_confident_bot" not in text:
        anchor = text.find("def _lean_human_traffic_pass")
        if anchor < 0:
            raise SystemExit("human_pass missing")
        text = text[:anchor] + BEHAVIOR_FN + text[anchor:]

    # Soften main live row bot logic: after building trail, re-evaluate with behavior;
    # and change cloud/quarantine branch to not bot human browsers on valid pages.
    old = '''                    elif ip and (_lean_ip_is_quarantined(cur, ip) or _lean_ip_is_cloud_datacenter(ip)):
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
                likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}
                if not is_bot:
                    try:
                        likely = _public_likely_sailor_for_ip(cur, ip, path) or likely
                    except Exception:
                        pass
                likely_name = (likely.get("name") or "").strip()
                likely_slug = (likely.get("slug") or "").strip()
                # Identity = IP
'''

    # Find the exact block from live file
    if old not in text:
        # try without trailing comment
        old2 = old.replace("                # Identity = IP\n", "")
        if old2 not in text:
            # print nearby for debug
            i = text.find("elif ip and (_lean_ip_is_quarantined")
            print("NEAR:\n", text[i : i + 900])
            raise SystemExit("main bot elif block not found")
        old = old2

    new = '''                    elif ip and (_lean_ip_is_quarantined(cur, ip) or _lean_ip_is_cloud_datacenter(ip)):
                        # Soft: cloud/quarantine alone is NOT 100% sure — let human browsers through
                        # unless quarantine reason is a hard probe/SAS signal.
                        qreason = ""
                        try:
                            qreason = _lean_quarantine_reason(cur, ip) if ip else ""
                        except Exception:
                            qreason = ""
                        hard = any(
                            x in (qreason or "")
                            for x in ("sailor_sas_id_url", "probe_path", "agent_test")
                        )
                        if hard:
                            is_bot = True
                        elif _lean_human_traffic_pass(ua_live, path):
                            is_bot = False
                        elif not _is_human_browser_ua(ua_live):
                            is_bot = True
                            try:
                                _lean_quarantine_ip(
                                    cur,
                                    ip,
                                    "cloud_datacenter" if _lean_ip_is_cloud_datacenter(ip) else "quarantine",
                                )
                            except Exception:
                                pass
                        else:
                            is_bot = False
                except Exception:
                    if (not _is_document_page_path_for_hit(path)) or _is_probe_blocked_path(path):
                        is_bot = True
                    elif _lean_human_traffic_pass(ua_live, path):
                        is_bot = False
                    else:
                        is_bot = False  # unsure → Guest
                # Behaviour pattern (deep-link + tiny dwell + short stop) = confident bot
                try:
                    _trail_pre = _lean_session_page_trail(cur, visitor_id=full_vid, ip=ip)
                except Exception:
                    _trail_pre = []
                if (not is_bot) and _lean_behavior_confident_bot(_trail_pre, path):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "behavior_deep_link_swarm")
                        except Exception:
                            pass
                likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}
                if not is_bot:
                    try:
                        likely = _public_likely_sailor_for_ip(cur, ip, path) or likely
                    except Exception:
                        pass
                likely_name = (likely.get("name") or "").strip()
                likely_slug = (likely.get("slug") or "").strip()
'''
    text = text.replace(old, new, 1)

    # Also soften orphan-recovery bot branch (second is_bot block in live)
    old_orphan = '''                        if _is_sailor_sas_id_path(path) or _lean_visitor_used_sas_id_url(cur, full_vid, ip):
                            is_bot = True
                        elif _lean_human_traffic_pass(ua_live or "Mozilla/5.0 (iPhone) Safari/604.1", path):
                            is_bot = False
                        elif ip and (_lean_ip_is_quarantined(cur, ip) or _lean_ip_is_cloud_datacenter(ip)):
                            is_bot = True
                    except Exception:
                        is_bot = False
                    likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}
                    if not is_bot:
                        try:
                            likely = _public_likely_sailor_for_ip(cur, ip, path) or likely
                        except Exception:
                            pass
'''
    new_orphan = '''                        if _is_sailor_sas_id_path(path) or _lean_visitor_used_sas_id_url(cur, full_vid, ip):
                            is_bot = True
                        elif _is_probe_blocked_path(path) or (not _is_document_page_path_for_hit(path)):
                            is_bot = True
                        elif _lean_human_traffic_pass(ua_live or "Mozilla/5.0 (iPhone) Safari/604.1", path):
                            is_bot = False
                        else:
                            # Unsure / soft cloud — Guest unless behaviour pattern says bot
                            is_bot = False
                        if not is_bot:
                            try:
                                _tr = _lean_session_page_trail(cur, visitor_id=full_vid, ip=ip)
                            except Exception:
                                _tr = []
                            if _lean_behavior_confident_bot(_tr, path):
                                is_bot = True
                    except Exception:
                        is_bot = False
                    likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}
                    if not is_bot:
                        try:
                            likely = _public_likely_sailor_for_ip(cur, ip, path) or likely
                        except Exception:
                            pass
'''
    if old_orphan not in text:
        print("WARN orphan bot block not found (may already differ)")
    else:
        text = text.replace(old_orphan, new_orphan, 1)

    # Soften human_pass branch: don't re-bot on soft quarantine
    old_hard = '''                            if ip and _lean_ip_is_quarantined(cur, ip):
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
'''
    # leave as-is (already only hard reasons) — good

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK soft bot gate (+{len(text)-len(orig)} bytes)")


if __name__ == "__main__":
    main()
