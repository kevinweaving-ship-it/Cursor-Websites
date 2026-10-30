#!/usr/bin/env python3
"""Flag sterile list-page only trails (/events, /classes, …) as bots; never soft-release them."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

HELPER = '''def _lean_is_sterile_list_path(path: Optional[str]) -> bool:
    """Listing/probe pages bots hit alone with no click-through (not a real browse trail)."""
    p = (path or "").split("?", 1)[0].strip().rstrip("/") or "/"
    if p in ("/events", "/classes", "/clubs", "/vendor", "/class", "/club"):
        return True
    # bare directory probes sometimes omit trailing entity
    if p in ("/regattas", "/sailors", "/boats", "/sponsors"):
        return True
    return False


def _lean_sterile_short_trail_bot(page_trail: list, current_path: str = "", ip: str = "") -> bool:
    """Only sterile list URL(s), no home, no scroll/click → bot (esp. cloud).

    Real guests who land on /events then click through get more paths / engagement.
    """
    trail = page_trail if isinstance(page_trail, list) else []
    paths = []
    for pt in trail:
        if not isinstance(pt, dict):
            continue
        pp = (pt.get("path") or "").split("?", 1)[0].strip() or "/"
        paths.append(pp)
    if not paths:
        p0 = (current_path or "").split("?", 1)[0].strip() or "/"
        paths = [p0]
    if any(p in ("/", "/index.html") for p in paths):
        return False
    try:
        if _lean_trail_has_engagement(trail):
            return False
    except Exception:
        pass
    uniq = {p for p in paths if p}
    if not uniq or len(uniq) > 2:
        return False
    if not all(_lean_is_sterile_list_path(p) for p in uniq):
        return False
    # Sterile-only short trail with zero engage = bot
    try:
        if ip and _lean_ip_is_cloud_datacenter(ip):
            return True
    except Exception:
        pass
    return True


'''


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-sterile-bot-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    if "def _lean_sterile_short_trail_bot" not in text:
        anchor = text.find("def _lean_same_page_swarm_bot")
        if anchor < 0:
            anchor = text.find("def _lean_behavior_confident_bot")
        if anchor < 0:
            raise SystemExit("no insert anchor for sterile helper")
        text = text[:anchor] + HELPER + text[anchor:]

    # Wire after same_page_swarm in live classify
    old_wire = '''                if (not is_bot) and _lean_same_page_swarm_bot(
                    cur, ip=ip or "", path=path, page_trail=_trail_pre, window_minutes=30
                ):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "same_page_swarm_no_engage")
                        except Exception:
                            pass
                likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}
'''
    new_wire = '''                if (not is_bot) and _lean_same_page_swarm_bot(
                    cur, ip=ip or "", path=path, page_trail=_trail_pre, window_minutes=30
                ):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "same_page_swarm_no_engage")
                        except Exception:
                            pass
                if (not is_bot) and _lean_sterile_short_trail_bot(_trail_pre, path, ip or ""):
                    is_bot = True
                    if ip:
                        try:
                            reason = (
                                "cloud_sterile_short"
                                if _lean_ip_is_cloud_datacenter(ip)
                                else "sterile_single_page"
                            )
                            _lean_quarantine_ip(cur, ip, reason)
                        except Exception:
                            pass
                likely = {"name": "", "slug": "", "hits": 0, "sas_id": ""}
'''
    if old_wire not in text:
        raise SystemExit("live swarm wire not found")
    text = text.replace(old_wire, new_wire, 1)

    # Expand soft hard-reason list (cloud/quarantine branch)
    old_hard = '''                        hard = any(
                            x in (qreason or "")
                            for x in ("sailor_sas_id_url", "probe_path", "agent_test")
                        )
'''
    new_hard = '''                        hard = any(
                            x in (qreason or "")
                            for x in (
                                "sailor_sas_id_url",
                                "probe_path",
                                "agent_test",
                                "cloud_bot",
                                "offline_bot",
                                "agent_junk",
                                "behavior_",
                                "same_page_swarm",
                                "sterile_",
                                "cloud_sterile",
                                "live_bot",
                            )
                        )
'''
    if old_hard not in text:
        raise SystemExit("hard=any block not found")
    text = text.replace(old_hard, new_hard, 1)

    # Expand human_pass re-bot hard reasons
    old_hp = '''                                if any(
                                    x in (qreason or "")
                                    for x in (
                                        "sailor_sas_id_url",
                                        "agent_test",
                                        "probe_path",
                                    )
                                ):
'''
    new_hp = '''                                if any(
                                    x in (qreason or "")
                                    for x in (
                                        "sailor_sas_id_url",
                                        "agent_test",
                                        "probe_path",
                                        "cloud_bot",
                                        "offline_bot",
                                        "agent_junk",
                                        "behavior_",
                                        "same_page_swarm",
                                        "sterile_",
                                        "cloud_sterile",
                                        "live_bot",
                                    )
                                ):
'''
    if old_hp not in text:
        raise SystemExit("human_pass hard reasons not found")
    text = text.replace(old_hp, new_hp, 1)

    # Release SQL: never release sterile reasons
    old_rel = '''                                            " AND COALESCE(reason,'') NOT LIKE '%%probe_path%%'",
'''
    new_rel = '''                                            " AND COALESCE(reason,'') NOT LIKE '%%probe_path%%'"
                                            " AND COALESCE(reason,'') NOT LIKE '%%sterile_%%'"
                                            " AND COALESCE(reason,'') NOT LIKE '%%cloud_sterile%%'"
                                            " AND COALESCE(reason,'') NOT LIKE '%%live_bot%%'",
'''
    if old_rel not in text:
        # try already patched
        if "sterile_" in text[text.find("SET active = false") : text.find("SET active = false") + 900]:
            print("WARN release sterile already present")
        else:
            raise SystemExit("release NOT LIKE probe_path not found")
    else:
        text = text.replace(old_rel, new_rel, 1)

    # Offline classifier: sterile short trail
    old_off = '''                if _is_sailor_sas_id_path(path) or _lean_behavior_confident_bot(trail, path, ip):
                    is_bot = True
                elif _lean_same_page_swarm_bot(cur, ip=ip or "", path=path, page_trail=trail, window_minutes=30):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "same_page_swarm_no_engage")
                        except Exception:
                            pass
                elif ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
'''
    if old_off in text:
        text = text.replace(
            old_off,
            '''                if _is_sailor_sas_id_path(path) or _lean_behavior_confident_bot(trail, path, ip):
                    is_bot = True
                elif _lean_same_page_swarm_bot(cur, ip=ip or "", path=path, page_trail=trail, window_minutes=30):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "same_page_swarm_no_engage")
                        except Exception:
                            pass
                elif _lean_sterile_short_trail_bot(trail, path, ip or ""):
                    is_bot = True
                    if ip:
                        try:
                            reason = (
                                "cloud_sterile_short"
                                if _lean_ip_is_cloud_datacenter(ip)
                                else "sterile_single_page"
                            )
                            _lean_quarantine_ip(cur, ip, reason)
                        except Exception:
                            pass
                elif ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
''',
            1,
        )
    else:
        print("WARN offline sterile wire skipped (block differs)")

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK sterile events bot (+{len(text) - len(orig)} bytes)")


if __name__ == "__main__":
    main()
