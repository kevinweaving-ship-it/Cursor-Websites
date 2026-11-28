#!/usr/bin/env python3
"""Surgical live patch: scroll/click = human; range lookback for /traffic real list.

ONLY touches lean-traffic helpers inside /var/www/sailingsa/api/api.py.
Does not modify other URL handlers.
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

HELPER = '''
def _lean_ip_has_real_engage(cur, ip_address: Optional[str], *, hours: int = 168) -> bool:
    """True if IP has scrolled or clicked (non search-fake) recently."""
    ip = (ip_address or "").strip()
    if not ip:
        return False
    try:
        _lean_ensure_page_hit_engagement_column(cur)
        cur.execute(
            """
            SELECT 1 FROM public.public_page_hits
            WHERE ip_address = %s
              AND occurred_at > NOW() - make_interval(hours => %s)
              AND (
                engagement ~* 'scroll'
                OR (engagement ~* 'click' AND engagement !~* 'search')
              )
            LIMIT 1
            """,
            (ip[:80], int(hours)),
        )
        return bool(cur.fetchone())
    except Exception:
        return False


def _lean_release_quarantine_for_engage(cur, ip_address: Optional[str], *, note: str = "engage") -> None:
    """Deactivate quarantine when scroll/click proves human (bots cannot scroll/click)."""
    ip = (ip_address or "").strip()
    if not ip:
        return
    try:
        _lean_ensure_quarantine_table(cur)
        tag = ("|released_" + (note or "engage"))[:40]
        cur.execute(
            """
            UPDATE public.traffic_quarantine_ips
            SET active = false,
                reason = LEFT(COALESCE(reason,'') || %s, 80),
                last_seen_at = NOW()
            WHERE ip_address = %s
              AND COALESCE(active, true) = true
              AND COALESCE(reason,'') NOT LIKE '%%crawler_cloud%%'
              AND COALESCE(reason,'') NOT LIKE '%%facebook_crawler%%'
            """,
            (tag, ip[:80]),
        )
    except Exception:
        pass


def _lean_lookback_hours_for_range(range_key: Optional[str]) -> int:
    key = (range_key or "24h").strip().lower()
    if key in ("live", "1h"):
        return 1
    if key in ("24h", "1d", "day"):
        return 24
    if key in ("7d", "week"):
        return 24 * 7
    if key in ("30d", "month"):
        return 24 * 30
    if key in ("ever", "all"):
        return 24 * 365
    return 24

'''


def must_replace(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"PATCH FAIL: marker not found for {label}")
    if text.count(old) != 1:
        raise SystemExit(f"PATCH FAIL: marker not unique ({text.count(old)}) for {label}")
    return text.replace(old, new, 1)


def main() -> None:
    if not API.is_file():
        raise SystemExit(f"missing {API}")
    text = API.read_text(encoding="utf-8", errors="replace")
    if "_lean_ip_has_real_engage" in text and "_lean_lookback_hours_for_range" in text:
        print("ALREADY_PATCHED")
        return

    bak = Path(f"/root/backups/api.py.engage_human.{time.strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    print(f"BACKUP {bak}")

    # 1) Insert helpers after _lean_quarantine_ip block (before _lean_quarantine_age_seconds)
    anchor = "def _lean_quarantine_age_seconds(cur, ip_address: Optional[str]) -> Optional[float]:"
    text = must_replace(text, anchor, HELPER + "\n" + anchor, "insert helpers")

    # 2) Soft-quarantine refuse when IP already has real engage
    old_q = '''def _lean_quarantine_ip(cur, ip_address: Optional[str], reason: str = "bot") -> None:
    ip = (ip_address or "").strip()
    if not ip or _is_noise_public_ip(ip):
        return
    try:
        _lean_ensure_quarantine_table(cur)
        cur.execute(
'''
    new_q = '''def _lean_quarantine_ip(cur, ip_address: Optional[str], reason: str = "bot") -> None:
    ip = (ip_address or "").strip()
    if not ip or _is_noise_public_ip(ip):
        return
    soft = (reason or "bot").strip().lower()
    # Scroll/click humans must never land in soft quarantine (idle/offline/sterile/bounce).
    if soft in (
        "bot_final_idle_30s",
        "offline_bot",
        "sterile_single_page",
        "cloud_sterile_short",
        "bounce_home_no_engage",
        "no_engage_long_trail",
        "quarantine",
    ):
        try:
            if _lean_ip_has_real_engage(cur, ip, hours=24 * 30):
                return
        except Exception:
            pass
    try:
        _lean_ensure_quarantine_table(cur)
        cur.execute(
'''
    text = must_replace(text, old_q, new_q, "quarantine refuse engage")

    # 3) Release quarantine when engagement is merged onto a hit
    old_merge_end = '''        cur.execute(
            "UPDATE public.public_page_hits SET engagement = %s WHERE hit_id = %s",
            (",".join(uniq), hit_id),
        )
    except Exception:
        pass


def _lean_merge_open_hit_engagement(cur, *, ip: str = "", visitor_id: str = "", engage_raw: str = "") -> None:
'''
    new_merge_end = '''        cur.execute(
            "UPDATE public.public_page_hits SET engagement = %s WHERE hit_id = %s",
            (",".join(uniq), hit_id),
        )
        if ip_s and _lean_tokens_are_real_human_engage(uniq):
            _lean_release_quarantine_for_engage(cur, ip_s, note="hit_engage")
    except Exception:
        pass


def _lean_merge_open_hit_engagement(cur, *, ip: str = "", visitor_id: str = "", engage_raw: str = "") -> None:
'''
    text = must_replace(text, old_merge_end, new_merge_end, "merge path release")

    old_open_end = '''        cur.execute(
            "UPDATE public.public_page_hits SET engagement = %s WHERE hit_id = %s",
            (",".join(uniq), hit_id),
        )
    except Exception:
        pass


def _lean_ensure_page_hit_engagement_column(cur) -> None:
'''
    new_open_end = '''        cur.execute(
            "UPDATE public.public_page_hits SET engagement = %s WHERE hit_id = %s",
            (",".join(uniq), hit_id),
        )
        if ip_s and _lean_tokens_are_real_human_engage(uniq):
            _lean_release_quarantine_for_engage(cur, ip_s, note="open_engage")
    except Exception:
        pass


def _lean_ensure_page_hit_engagement_column(cur) -> None:
'''
    text = must_replace(text, old_open_end, new_open_end, "merge open release")

    # 4) Unified SQL: do not drop engaged IPs just because they were soft-quarantined
    old_unified = '''        AND (ip_address IS NULL OR ip_address NOT IN {_LEAN_TRAFFIC_QUARANTINE_IP_SQL})
        {real_ip_sql}
        {bot_prefix_sql}
'''
    new_unified = '''        {real_ip_sql}
        {bot_prefix_sql}
'''
    text = must_replace(text, old_unified, new_unified, "unified drop quarantine exclude")

    # 5) Offline sessions: quarantine + engage => human (not bot)
    old_off = '''            is_bot = False
            try:
                # Hard: Meta / Google / AWS / Alibaba ranges never count as Guest (IP-sure).
                if (not is_staff) and ip and _lean_is_crawler_cloud_ip(ip):
                    is_bot = True
                elif ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
                elif (not is_staff) and (
'''
    new_off = '''            is_bot = False
            try:
                # Hard: Meta / Google / AWS / Alibaba ranges never count as Guest (IP-sure).
                if (not is_staff) and ip and _lean_is_crawler_cloud_ip(ip):
                    is_bot = True
                elif ip and _lean_ip_is_quarantined(cur, ip):
                    # Soft quarantine must not override scroll/click (bots cannot do that).
                    try:
                        if _lean_trail_has_engagement(trail):
                            is_bot = False
                            _lean_release_quarantine_for_engage(cur, ip, note="offline_engage")
                        else:
                            is_bot = True
                    except Exception:
                        is_bot = True
                elif (not is_staff) and (
'''
    text = must_replace(text, old_off, new_off, "offline quarantine engage")

    # Do not re-quarantine engaged humans as offline_bot
    old_re_q = '''            if is_bot:
                if ip:
                    try:
                        _lean_quarantine_ip(cur, ip, "offline_bot")
                    except Exception:
                        pass
                bots.append(item)
            elif not in_live_window:
                humans.append(item)
'''
    new_re_q = '''            if is_bot:
                if ip:
                    try:
                        if not _lean_trail_has_engagement(trail):
                            _lean_quarantine_ip(cur, ip, "offline_bot")
                    except Exception:
                        pass
                bots.append(item)
            elif not in_live_window:
                humans.append(item)
'''
    text = must_replace(text, old_re_q, new_re_q, "no offline_bot if engage")

    # 6) Real visitors lookback follows dashboard range
    old_rv_rebuild = '''def _lean_rv_rebuild(conn, *, after_iso=None):
    """Full or incremental rebuild into cache. after_iso => only IPs active after that time."""
    rs = _lean_traffic_real_since()
    cur = conn.cursor()
    try:
        cur.execute("SET LOCAL statement_timeout = '60000'")
    except Exception:
        pass
    # Reuse existing builder for full; for incremental filter IPs first then build subset
    if after_iso:
        try:
            cur.execute(
                """
                SELECT h.ip_address
                FROM public.public_page_hits h
                WHERE h.ip_address IS NOT NULL AND TRIM(h.ip_address) <> ''
                  AND h.occurred_at >= %s::timestamptz
                  AND h.occurred_at > %s::timestamptz
                  AND h.ip_address <> '102.218.215.253'
                GROUP BY h.ip_address
                ORDER BY MAX(h.occurred_at) DESC
                LIMIT 80
                """,
                (rs, after_iso),
            )
            ips = []
            for row in cur.fetchall() or []:
                ip = (row.get("ip_address") if isinstance(row, dict) else row[0]) or ""
                ip = str(ip).strip()
                if ip:
                    ips.append(ip)
            humans, bots = [], []
            if ips:
                # Fall back to full builder then filter — still cheaper when few new IPs? 
                # Full builder scans 250 IPs; for diff we call offline_sessions then filter.
                h, b = _lean_traffic_offline_sessions(cur, live_minutes=_LEAN_TRAFFIC_LIVE_MINUTES, lookback_hours=24)
                ipset = set(ips)
                humans = [x for x in (h or []) if (x.get("ip") or "") in ipset]
                bots = [x for x in (b or []) if (x.get("ip") or "") in ipset]
                # Also include any of those IPs classified only as still-live (not in humans) — skip
            _lean_rv_cache_apply(humans, bots, rs, replace=False)
            return humans, bots
        except Exception:
            _lean_db_rollback(conn)
            # fall through to full
    h, b = _lean_traffic_offline_sessions(cur, live_minutes=_LEAN_TRAFFIC_LIVE_MINUTES, lookback_hours=24)
    _lean_rv_cache_apply(h or [], b or [], rs, replace=True)
    return h or [], b or []
'''
    new_rv_rebuild = '''def _lean_rv_rebuild(conn, *, after_iso=None, lookback_hours: int = 24):
    """Full or incremental rebuild into cache. after_iso => only IPs active after that time."""
    rs = _lean_traffic_real_since()
    look_h = max(1, int(lookback_hours or 24))
    cur = conn.cursor()
    try:
        cur.execute("SET LOCAL statement_timeout = '60000'")
    except Exception:
        pass
    # Reuse existing builder for full; for incremental filter IPs first then build subset
    if after_iso:
        try:
            cur.execute(
                """
                SELECT h.ip_address
                FROM public.public_page_hits h
                WHERE h.ip_address IS NOT NULL AND TRIM(h.ip_address) <> ''
                  AND h.occurred_at >= %s::timestamptz
                  AND h.occurred_at > %s::timestamptz
                  AND h.ip_address <> '102.218.215.253'
                GROUP BY h.ip_address
                ORDER BY MAX(h.occurred_at) DESC
                LIMIT 80
                """,
                (rs, after_iso),
            )
            ips = []
            for row in cur.fetchall() or []:
                ip = (row.get("ip_address") if isinstance(row, dict) else row[0]) or ""
                ip = str(ip).strip()
                if ip:
                    ips.append(ip)
            humans, bots = [], []
            if ips:
                # Fall back to full builder then filter — still cheaper when few new IPs? 
                # Full builder scans 250 IPs; for diff we call offline_sessions then filter.
                h, b = _lean_traffic_offline_sessions(cur, live_minutes=_LEAN_TRAFFIC_LIVE_MINUTES, lookback_hours=look_h)
                ipset = set(ips)
                humans = [x for x in (h or []) if (x.get("ip") or "") in ipset]
                bots = [x for x in (b or []) if (x.get("ip") or "") in ipset]
                # Also include any of those IPs classified only as still-live (not in humans) — skip
            _lean_rv_cache_apply(humans, bots, rs, replace=False)
            return humans, bots
        except Exception:
            _lean_db_rollback(conn)
            # fall through to full
    h, b = _lean_traffic_offline_sessions(cur, live_minutes=_LEAN_TRAFFIC_LIVE_MINUTES, lookback_hours=look_h)
    _lean_rv_cache_apply(h or [], b or [], rs, replace=True)
    return h or [], b or []
'''
    text = must_replace(text, old_rv_rebuild, new_rv_rebuild, "rv rebuild lookback")

    old_api_rv = '''    after = (request.query_params.get("after") or "").strip() or None
    full = (request.query_params.get("full") or "").strip() in ("1", "true", "yes")
    conn = None
    try:
        conn = get_db_connection()
        if full or not _LEAN_RV_CACHE.get("built_at") or after:
            try:
                _LEAN_RV_CACHE["building"] = True
                _lean_rv_rebuild(conn, after_iso=None if full or not after else after)
'''
    new_api_rv = '''    after = (request.query_params.get("after") or "").strip() or None
    full = (request.query_params.get("full") or "").strip() in ("1", "true", "yes")
    range_key, _, _ = _lean_traffic_parse_range(request.query_params.get("range"))
    look_h = _lean_lookback_hours_for_range(range_key)
    conn = None
    try:
        conn = get_db_connection()
        if full or not _LEAN_RV_CACHE.get("built_at") or after:
            try:
                _LEAN_RV_CACHE["building"] = True
                _lean_rv_rebuild(conn, after_iso=None if full or not after else after, lookback_hours=look_h)
'''
    text = must_replace(text, old_api_rv, new_api_rv, "api real-visitors range")

    # 7) Dashboard JS: pass RANGE into real-visitors; force full rebuild on range change
    old_js = '''  function loadRealVisitors(opts){
    opts = opts || {};
    var box=$("offlineBox");
    var q = opts.full ? "?full=1" : (window.__rvFetchedAt ? ("?after="+encodeURIComponent(window.__rvFetchedAt)) : "?full=1");
    if(box && !box.querySelector("table") && !opts.silent) box.innerHTML="<p class='note'>Loading real visitors…</p>";
    return fetchJson("/traffic/api/real-visitors"+q).then(function(d){
'''
    new_js = '''  function loadRealVisitors(opts){
    opts = opts || {};
    var box=$("offlineBox");
    var q = opts.full ? ("?full=1&range="+encodeURIComponent(RANGE)) : (window.__rvFetchedAt ? ("?after="+encodeURIComponent(window.__rvFetchedAt)+"&range="+encodeURIComponent(RANGE)) : ("?full=1&range="+encodeURIComponent(RANGE)));
    if(box && !box.querySelector("table") && !opts.silent) box.innerHTML="<p class='note'>Loading real visitors…</p>";
    return fetchJson("/traffic/api/real-visitors"+q).then(function(d){
'''
    text = must_replace(text, old_js, new_js, "js real-visitors range")

    old_range_click = '''    RANGE = b.getAttribute("data-r");
    history.replaceState(null,"","/traffic?range="+encodeURIComponent(RANGE));
    setRangeButtons();
    loadAll();
'''
    new_range_click = '''    RANGE = b.getAttribute("data-r");
    history.replaceState(null,"","/traffic?range="+encodeURIComponent(RANGE));
    setRangeButtons();
    window.__rvFetchedAt = "";
    loadAll();
'''
    text = must_replace(text, old_range_click, new_range_click, "js range reset cache")

    API.write_text(text, encoding="utf-8")
    print(f"WROTE {API} lines={text.count(chr(10))+1}")
    print("OK")


if __name__ == "__main__":
    main()
