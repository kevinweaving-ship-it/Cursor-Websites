#!/usr/bin/env python3
"""Surgical /traffic fix: Real visitors section follows top range (Live/24h/7d/30d/Ever).

- Title + note use selected range (not fixed "since reset")
- Cache keyed by lookback so switching ranges replaces the list
- API returns range + range_label for the UI
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def must_replace(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"PATCH FAIL {label}: count={n}")
    return text.replace(old, new, 1)


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    if 'id="realVisitorsTitle"' in text and "range_label" in text and 'lookback_hours' in text[text.find("_LEAN_RV_CACHE"):text.find("_LEAN_RV_CACHE") + 400]:
        # Heuristic: already has title id + cache lookback
        if "_LEAN_RV_CACHE" in text and '"lookback_hours": None' in text:
            print("ALREADY_PATCHED")
            return

    bak = Path(f"/root/backups/api.py.rv_range.{time.strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    print(f"BACKUP {bak}")

    # --- 1) HTML title ---
    text = must_replace(
        text,
        '<section class="card" style="margin-top:12px"><h2>Real visitors — since reset</h2><p class="note" id="realSinceNote">Every real visitor (scroll/click). All pages in the trail. Nothing hidden if real.</p><div id="offlineBox"><p class="note">Loading…</p></div></section>',
        '<section class="card" style="margin-top:12px"><h2 id="realVisitorsTitle">Real visitors — 24h</h2><p class="note" id="realSinceNote">In selected range — every real visitor (scroll/click). All pages in trail. Nothing hidden if real.</p><div id="offlineBox"><p class="note">Loading…</p></div></section>',
        "rv html title",
    )

    # --- 2) Cache: track lookback_hours ---
    text = must_replace(
        text,
        """_LEAN_RV_CACHE = {
    "lock": _lean_rv_threading.Lock(),
    "real_since": None,
    "humans_by_ip": {},  # ip -> item dict
    "bots_by_ip": {},
    "built_at": None,  # iso str of last full/diff build finish
    "building": False,
}""",
        """_LEAN_RV_CACHE = {
    "lock": _lean_rv_threading.Lock(),
    "real_since": None,
    "lookback_hours": None,
    "humans_by_ip": {},  # ip -> item dict
    "bots_by_ip": {},
    "built_at": None,  # iso str of last full/diff build finish
    "building": False,
}""",
        "rv cache fields",
    )

    text = must_replace(
        text,
        """def _lean_rv_cache_lists():
    with _LEAN_RV_CACHE["lock"]:
        humans = list(_LEAN_RV_CACHE["humans_by_ip"].values())
        bots = list(_LEAN_RV_CACHE["bots_by_ip"].values())
        built = _LEAN_RV_CACHE["built_at"]
        rs = _LEAN_RV_CACHE["real_since"]
    humans.sort(key=lambda r: str(r.get("last_activity") or ""), reverse=True)
    bots.sort(key=lambda r: str(r.get("last_activity") or ""), reverse=True)
    return humans, bots, built, rs

def _lean_rv_cache_apply(humans, bots, real_since, replace=False):
    from datetime import datetime, timezone
    with _LEAN_RV_CACHE["lock"]:
        if replace or _LEAN_RV_CACHE["real_since"] != real_since:
            _LEAN_RV_CACHE["humans_by_ip"] = {}
            _LEAN_RV_CACHE["bots_by_ip"] = {}
            _LEAN_RV_CACHE["real_since"] = real_since
        for it in humans or []:
            ip = (it.get("ip") or "").strip()
            if ip:
                _LEAN_RV_CACHE["humans_by_ip"][ip] = it
                _LEAN_RV_CACHE["bots_by_ip"].pop(ip, None)
        for it in bots or []:
            ip = (it.get("ip") or "").strip()
            if ip:
                _LEAN_RV_CACHE["bots_by_ip"][ip] = it
                _LEAN_RV_CACHE["humans_by_ip"].pop(ip, None)
        _LEAN_RV_CACHE["built_at"] = datetime.now(timezone.utc).isoformat()
        _LEAN_RV_CACHE["building"] = False
""",
        """def _lean_rv_cache_lists():
    with _LEAN_RV_CACHE["lock"]:
        humans = list(_LEAN_RV_CACHE["humans_by_ip"].values())
        bots = list(_LEAN_RV_CACHE["bots_by_ip"].values())
        built = _LEAN_RV_CACHE["built_at"]
        rs = _LEAN_RV_CACHE["real_since"]
    humans.sort(key=lambda r: str(r.get("last_activity") or ""), reverse=True)
    bots.sort(key=lambda r: str(r.get("last_activity") or ""), reverse=True)
    return humans, bots, built, rs

def _lean_rv_cache_apply(humans, bots, real_since, replace=False, lookback_hours=None):
    from datetime import datetime, timezone
    with _LEAN_RV_CACHE["lock"]:
        look_h = None if lookback_hours is None else int(lookback_hours)
        if (
            replace
            or _LEAN_RV_CACHE["real_since"] != real_since
            or (look_h is not None and _LEAN_RV_CACHE.get("lookback_hours") != look_h)
        ):
            _LEAN_RV_CACHE["humans_by_ip"] = {}
            _LEAN_RV_CACHE["bots_by_ip"] = {}
            _LEAN_RV_CACHE["real_since"] = real_since
            if look_h is not None:
                _LEAN_RV_CACHE["lookback_hours"] = look_h
        for it in humans or []:
            ip = (it.get("ip") or "").strip()
            if ip:
                _LEAN_RV_CACHE["humans_by_ip"][ip] = it
                _LEAN_RV_CACHE["bots_by_ip"].pop(ip, None)
        for it in bots or []:
            ip = (it.get("ip") or "").strip()
            if ip:
                _LEAN_RV_CACHE["bots_by_ip"][ip] = it
                _LEAN_RV_CACHE["humans_by_ip"].pop(ip, None)
        _LEAN_RV_CACHE["built_at"] = datetime.now(timezone.utc).isoformat()
        _LEAN_RV_CACHE["building"] = False
""",
        "rv cache apply",
    )

    text = must_replace(
        text,
        """            _lean_rv_cache_apply(humans, bots, rs, replace=False)
            return humans, bots
        except Exception:
            _lean_db_rollback(conn)
            # fall through to full
    h, b = _lean_traffic_offline_sessions(cur, live_minutes=_LEAN_TRAFFIC_LIVE_MINUTES, lookback_hours=look_h)
    _lean_rv_cache_apply(h or [], b or [], rs, replace=True)
    return h or [], b or []
""",
        """            _lean_rv_cache_apply(humans, bots, rs, replace=False, lookback_hours=look_h)
            return humans, bots
        except Exception:
            _lean_db_rollback(conn)
            # fall through to full
    h, b = _lean_traffic_offline_sessions(cur, live_minutes=_LEAN_TRAFFIC_LIVE_MINUTES, lookback_hours=look_h)
    _lean_rv_cache_apply(h or [], b or [], rs, replace=True, lookback_hours=look_h)
    return h or [], b or []
""",
        "rv rebuild apply lookback",
    )

    # --- 3) API: force rebuild when lookback changes; return range labels ---
    text = must_replace(
        text,
        """    after = (request.query_params.get("after") or "").strip() or None
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
            except Exception as e:
                _lean_db_rollback(conn)
                _LEAN_RV_CACHE["building"] = False
                # still return cache if any
        humans, bots, built, rs = _lean_rv_cache_lists()
        # If after set, only return rows newer than after (diff payload)
        if after and not full:
            def _newer(r):
                la = str(r.get("last_activity") or "")
                return la > after
            humans = [r for r in humans if _newer(r)]
            bots = [r for r in bots if _newer(r)]
        return JSONResponse(
            {
                "ok": True,
                "real_since": rs or _lean_traffic_real_since(),
                "offline": humans[:200],
                "offline_bots": bots[:40],
                "offline_fetched_at": built or "",
                "diff": bool(after) and not full,
            },
            headers={"Cache-Control": "no-store"},
        )
""",
        """    after = (request.query_params.get("after") or "").strip() or None
    full = (request.query_params.get("full") or "").strip() in ("1", "true", "yes")
    range_key, _, _ = _lean_traffic_parse_range(request.query_params.get("range"))
    look_h = _lean_lookback_hours_for_range(range_key)
    range_labels = {
        "live": "Live",
        "24h": "24h",
        "7d": "7d",
        "30d": "30d",
        "ever": "Ever",
    }
    range_label = range_labels.get(range_key, range_key or "24h")
    conn = None
    try:
        conn = get_db_connection()
        cache_look = _LEAN_RV_CACHE.get("lookback_hours")
        need_full = full or not _LEAN_RV_CACHE.get("built_at") or cache_look != look_h
        if need_full or after:
            try:
                _LEAN_RV_CACHE["building"] = True
                _lean_rv_rebuild(
                    conn,
                    after_iso=None if need_full or not after else after,
                    lookback_hours=look_h,
                )
            except Exception as e:
                _lean_db_rollback(conn)
                _LEAN_RV_CACHE["building"] = False
                # still return cache if any
        humans, bots, built, rs = _lean_rv_cache_lists()
        # If after set, only return rows newer than after (diff payload)
        if after and not need_full:
            def _newer(r):
                la = str(r.get("last_activity") or "")
                return la > after
            humans = [r for r in humans if _newer(r)]
            bots = [r for r in bots if _newer(r)]
        return JSONResponse(
            {
                "ok": True,
                "range": range_key,
                "range_label": range_label,
                "lookback_hours": look_h,
                "real_since": rs or _lean_traffic_real_since(),
                "offline": humans[:200],
                "offline_bots": bots[:40],
                "offline_fetched_at": built or "",
                "diff": bool(after) and not need_full,
            },
            headers={"Cache-Control": "no-store"},
        )
""",
        "rv api range response",
    )

    # --- 4) JS: title/note/empty follow RANGE ---
    text = must_replace(
        text,
        """  function renderOffline(d){
    var box=$("offlineBox");
    if(!box) return;
    var note=$("realSinceNote");
    if(note){
      var since=d && d.real_since ? String(d.real_since).replace("T"," ").slice(0,19) : "";
      note.textContent=(since?("Since reset "+since+" — "):"")+"every real visitor (scroll/click). All pages in trail. Nothing hidden if real.";
    }
    var rows=((d && d.offline)||[]).filter(function(r){ return r && r.kind!=="bot"; });
    if(!rows.length){
      box.innerHTML="<p class='note'>No real visitors since reset yet (need scroll or click).</p>";
""",
        """  function renderOffline(d){
    var box=$("offlineBox");
    if(!box) return;
    var rLab=(d && d.range_label) ? String(d.range_label) : (RANGE==="live"?"Live":(RANGE==="7d"?"7d":(RANGE==="30d"?"30d":(RANGE==="ever"?"Ever":"24h"))));
    var title=$("realVisitorsTitle");
    if(title) title.textContent="Real visitors — "+rLab;
    var note=$("realSinceNote");
    if(note){
      note.textContent=rLab+" — every real visitor (scroll/click). All pages in trail. Nothing hidden if real. Matches top range.";
    }
    var rows=((d && d.offline)||[]).filter(function(r){ return r && r.kind!=="bot"; });
    if(!rows.length){
      box.innerHTML="<p class='note'>No real visitors in "+rLab+" yet (need scroll or click).</p>";
""",
        "rv renderOffline labels",
    )

    # Merge path should preserve range_label
    text = must_replace(
        text,
        """    renderOffline({ok:true, offline:merged, real_since:d.real_since, offline_bots:d.offline_bots, offline_fb:d.offline_fb});
  };
""",
        """    renderOffline({ok:true, offline:merged, real_since:d.real_since, range:d.range, range_label:d.range_label, offline_bots:d.offline_bots, offline_fb:d.offline_fb});
  };
""",
        "rv merge range_label",
    )

    API.write_text(text, encoding="utf-8")
    print("PATCHED", API)


if __name__ == "__main__":
    main()
