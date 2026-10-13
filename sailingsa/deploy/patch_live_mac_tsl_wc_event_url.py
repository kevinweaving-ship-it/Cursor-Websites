#!/usr/bin/env python3
"""Surgical live-only patches for MAC TSL WC Event URL.

Never wholesale-replace /var/www/sailingsa/api/api.py.
Idempotent. Run on the box after snapshot + chattr -i.

  python3 sailingsa/deploy/patch_live_mac_tsl_wc_event_url.py /var/www/sailingsa/api/api.py
"""
from __future__ import annotations

import sys
from pathlib import Path

SLUG = "2026-10-17-mac-tsl-wc-team-sailing"
TSL_CLASS_LOGO = "/artwork/Class Logo/TSL-Class-Logo.png"
TSL_LOGO = "/artwork/Event Logo/TSL-Team-Sailing.png"

WIND_ANCHOR = '''        return JSONResponse(
            content={"ok": False, "err": str(e)[:200]},
            status_code=502,
            headers={"Cache-Control": "no-store"},
        )



@app.get("/api/weather/stations/{slug}/latest")
'''

WIND_INSERT = '''        return JSONResponse(
            content={"ok": False, "err": str(e)[:200]},
            status_code=502,
            headers={"Cache-Control": "no-store"},
        )


@app.get("/api/wind2speed/mac")
def api_wind2speed_mac():
    """MAC Wind2Speed station 3 (W2SMAC01) — knots + direction for the TSL Event URL wind card."""
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.get("https://wind2speed.africa/apidata/wsdata/3")
            r.raise_for_status()
            payload = r.json()
        raw = payload.get("data") if isinstance(payload, dict) else None
        inner = json.loads(raw) if isinstance(raw, str) else (raw or {})
        stats = inner.get("stats") or {}
        station = inner.get("station") or {}
        kmh_kn = 1.852

        def _kn(v):
            if v is None:
                return None
            try:
                return round(float(v) / kmh_kn, 1)
            except (TypeError, ValueError):
                return None

        hour = []
        for row in inner.get("tableData") or []:
            if not isinstance(row, dict):
                continue
            hour.append(
                {
                    "t": row.get("obsTimeLocal"),
                    "avg_kt": _kn(row.get("windspeedAvg")),
                    "high_kt": _kn(row.get("windspeedHigh")),
                    "low_kt": _kn(row.get("windspeedLow")),
                }
            )
        hour.sort(key=lambda p: p.get("t") or "")
        if hour and hour[-1].get("t"):
            try:
                t1 = datetime.fromisoformat(str(hour[-1]["t"]).replace("Z", "").split(".")[0])
                t0 = t1 - timedelta(hours=1)
                hour = [
                    p
                    for p in hour
                    if p.get("t")
                    and datetime.fromisoformat(str(p["t"]).replace("Z", "").split(".")[0]) >= t0
                ]
            except Exception:
                hour = hour[-24:]

        try:  # WX_FOUNDATION_v1
            from sailingsa.backend.weather_store import ingest_wind2speed_payload
            ingest_wind2speed_payload(inner, payload)
        except Exception:
            pass
        body = {
            "ok": True,
            "source": "wind2speed.africa/widgetPage/3",
            "station": station.get("nam") or "Milnerton Aquatic Club",
            "code": station.get("cod"),
            "lr": stats.get("lr"),
            "wind_kt": stats.get("wslr"),
            "gust_kt": stats.get("wshlr"),
            "avg_kt": stats.get("wsa"),
            "low_kt": stats.get("wsl"),
            "high_kt": stats.get("wsh"),
            "wind_dir": stats.get("wdlr"),
            "wind_dir_name": stats.get("wdlrn"),
            "avg_dir": stats.get("wda"),
            "avg_dir_name": stats.get("wdn"),
            "dir_low": stats.get("wdrl"),
            "dir_high": stats.get("wdrh"),
            "wds": stats.get("wds") or [],
            "wdsm": stats.get("wdsm") or [],
            "hour": hour,
            "interval": payload.get("interval") or 40000,
            "pressure": stats.get("prs"),
        }
        return JSONResponse(
            content=body,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
            },
        )
    except Exception as e:
        return JSONResponse(
            content={"ok": False, "err": str(e)[:200]},
            status_code=502,
            headers={"Cache-Control": "no-store"},
        )


@app.get("/api/weather/stations/{slug}/latest")
'''

LOGO_ANCHOR = '''_CLUB_EVENT_LOGO_RULES = (
    # --- Named championship / series Event Logos (host must match DB) ---
    ("cape classic", "/artwork/Event Logo/Cape-Classic-Series.png", "Cape Classic"),
'''

LOGO_INSERT = f'''_CLUB_EVENT_LOGO_RULES = (
    # --- Named championship / series Event Logos (host must match DB) ---
    ("2026 10 17 mac tsl wc team sailing", "{TSL_LOGO}", "TSL Team Sailing"),
    ("team sailing league", "{TSL_LOGO}", "TSL Team Sailing"),
    ("team sailing", "{TSL_LOGO}", "TSL Team Sailing"),
    ("cape classic", "/artwork/Event Logo/Cape-Classic-Series.png", "Cape Classic"),
'''

STATUS_ANCHOR = '''    word = (status_word or "Final").strip() or "Final"
    escaped_word = html_module.escape(word)
    is_lipton = bool(regatta_id) and _regatta_is_lipton_challenge(str(regatta_id))
'''

STATUS_INSERT = '''    word = (status_word or "Final").strip() or "Final"
    escaped_word = html_module.escape(word)
    if str(regatta_id or "").strip() == "2026-10-17-mac-tsl-wc-team-sailing" and not as_at_time:
        return ""
    is_lipton = bool(regatta_id) and _regatta_is_lipton_challenge(str(regatta_id))
'''

TOOLBAR_ANCHOR = '''        sa_toolbar_script = (
            '<script src="/js/regatta-sa-toolbar.js?v=20260909mm2" defer></script><script src="/js/regatta-fleet-ops.js?v=20260723f2" defer></script>' if is_sa else ""
        )
        live_board_script = _regatta_live_board_toggle_script() + _regatta_live_race_autoscore_script(str(regatta_id)) + _regatta_as_at_live_clock_script()
'''

TOOLBAR_INSERT = '''        sa_toolbar_script = (
            '<script src="/js/regatta-sa-toolbar.js?v=20260909mm2" defer></script><script src="/js/regatta-fleet-ops.js?v=20260723f2" defer></script>' if is_sa else ""
        )
        is_mac_tsl = str(regatta_id) == "2026-10-17-mac-tsl-wc-team-sailing"
        mac_tsl_js = (
            '<script src="/js/mac-tsl-live-cards.js?v=20261012o" defer></script>'
            '<script src="/js/mac-tsl-admin.js?v=20261013i" defer></script>'
            if is_mac_tsl
            else ""
        )
        mac_tsl_page_attrs = ' data-mac-tsl="1" data-mac-cam="later"' if is_mac_tsl else ""
        live_board_script = _regatta_live_board_toggle_script() + _regatta_live_race_autoscore_script(str(regatta_id)) + _regatta_as_at_live_clock_script()
'''

PAGE_ANCHOR = '''            f"<div class=\\"regatta-page\\"{_regatta_page_live_board_attrs(str(regatta_id), start_d, end_d)}{_midmar_hide_crew_attr(str(regatta_id))}>{body_html}</div>{seo_sailors}{seo_disc}"
            f"{mm_card_script}{sa_toolbar_script}{wc_club_edit_script}{entry_script}{live_board_script}"
'''

PAGE_INSERT = '''            f"<div class=\\"regatta-page\\"{_regatta_page_live_board_attrs(str(regatta_id), start_d, end_d)}{_midmar_hide_crew_attr(str(regatta_id))}{mac_tsl_page_attrs}>{body_html}</div>{seo_sailors}{seo_disc}"
            f"{mm_card_script}{sa_toolbar_script}{wc_club_edit_script}{entry_script}{live_board_script}{mac_tsl_js}"
'''

PASS_B_WIPE = '''        if str(regatta_id) == "2026-10-17-mac-tsl-wc-team-sailing" and not as_at_time:
            status_line_text = ""
'''

STATUS_DEFAULT_ANCHOR = '''            result_status = (row.get("result_status") or "").strip() or "Final"
            as_at_time = row.get("as_at_time")
'''

STATUS_DEFAULT_INSERT = '''            result_status = (row.get("result_status") or "").strip()
            if str(regatta_id or "").strip() != "2026-10-17-mac-tsl-wc-team-sailing":
                result_status = result_status or "Final"
            as_at_time = row.get("as_at_time")
'''

ENTRIES_ANCHOR = '''    if n <= 0:
        return ""
    try:  # CC_EVENT_HEADER_ENTRIES_v1
        from sailingsa.backend.cape_classic_fleet_sheet import (
            cape_classic_entries_line_html,
        )
        return cape_classic_entries_line_html(n)
'''

ENTRIES_INSERT = '''    if n <= 0:
        if str(regatta_id or "").strip() != "2026-10-17-mac-tsl-wc-team-sailing":
            return ""
        n = 0
    try:  # CC_EVENT_HEADER_ENTRIES_v1
        from sailingsa.backend.cape_classic_fleet_sheet import (
            cape_classic_entries_line_html,
        )
        _entries_html = cape_classic_entries_line_html(n)
        if _entries_html:
            return _entries_html
        if str(regatta_id or "").strip() == "2026-10-17-mac-tsl-wc-team-sailing":
            from sailingsa.backend.cape_classic_fleet_sheet import _ENTRIES_USERS_SVG
            return (
                '<div class="entry-total-line entry-total-line--icon">'
                f'<span class="entry-total-ico">{_ENTRIES_USERS_SVG}</span>'
                f"{n} Entries</div>"
            )
        return _entries_html
'''

NOR_LINK_ANCHOR = '''                + _cape_classic_total_entries_line_html(str(regatta_id), fleets)
                + "</div>"
'''

NOR_LINK_INSERT = '''                + _cape_classic_total_entries_line_html(str(regatta_id), fleets)
                + (
                    '<div class="status-line"><a href="#nor" id="macTslNorOpen">Notice of Race</a></div>'
                    if str(regatta_id) == "2026-10-17-mac-tsl-wc-team-sailing"
                    else ""
                )
                + "</div>"
'''

SA_CHROME_ANCHOR = '''    ls_attr = html_module.escape(ls_key, quote=True)
    cur = _normalize_hub_news_badge_label_for_ui(hub_badge_label)
'''

EIS_FN_ANCHOR = '''    """Below main header / above first fleet — invite-style info + loud ENTER CTA."""
    # Cape Classic Event Header is locked: Super Admin / Admin never get the editor shell.
    if str(regatta_id or "").strip() == "2026-09-13-zvyc-cape-classic":
        is_super_admin = False
'''

EIS_FN_INSERT = '''    """Below main header / above first fleet — invite-style info + loud ENTER CTA."""
    # TSL Event URLs: no ENTER / event-info-strip (fleet-entry CTA is not used).
    if str(regatta_id or "").strip() == "2026-10-17-mac-tsl-wc-team-sailing":
        return ""
    # Cape Classic Event Header is locked: Super Admin / Admin never get the editor shell.
    if str(regatta_id or "").strip() == "2026-09-13-zvyc-cape-classic":
        is_super_admin = False
'''

EIS_CALL_ANCHOR = '''        event_info_frag = _render_event_info_strip_html(
            str(regatta_id),
            is_super_admin=bool(is_sa) and str(regatta_id) != "2026-09-13-zvyc-cape-classic",
        )
        # REGATTA_ENTRY_FLOW_2026_07_23
        _eis_cfg = _wc_regatta_event_info_strip_cfg(str(regatta_id))
        entry_script = (
            '<link rel="stylesheet" href="/js/regatta-entry.css?v=20260723e8">'
            '<script src="/js/regatta-entry.js?v=20260723e8" defer></script>'
            if (_eis_cfg.get("enter") or {}).get("url") or (_eis_cfg.get("enter") or {}).get("label")
            else ""
        )
'''

EIS_CALL_INSERT = '''        event_info_frag = _render_event_info_strip_html(
            str(regatta_id),
            is_super_admin=bool(is_sa) and str(regatta_id) != "2026-09-13-zvyc-cape-classic",
        )
        # REGATTA_ENTRY_FLOW_2026_07_23
        _eis_cfg = _wc_regatta_event_info_strip_cfg(str(regatta_id))
        _tsl_no_eis = str(regatta_id) == "2026-10-17-mac-tsl-wc-team-sailing"
        if _tsl_no_eis:
            event_info_frag = ""
        entry_script = (
            '<link rel="stylesheet" href="/js/regatta-entry.css?v=20260723e8">'
            '<script src="/js/regatta-entry.js?v=20260723e8" defer></script>'
            if (not _tsl_no_eis)
            and ((_eis_cfg.get("enter") or {}).get("url") or (_eis_cfg.get("enter") or {}).get("label"))
            else ""
        )
'''

SA_CHROME_INSERT = '''    ls_attr = html_module.escape(ls_key, quote=True)
    if str(regatta_id or "").strip() == "2026-10-17-mac-tsl-wc-team-sailing":
        return (
            '<div class="regatta-sa-mode-wrap" id="regattaSaModeWrap" data-regatta-id="'
            + rid_attr
            + '" data-ls-key="'
            + ls_attr
            + '">'
            '<span class="regatta-sa-mode-text regatta-sa-mode-text--public">Public</span>'
            '<label class="regatta-sa-switch" title="Off = Public view, On = Super Admin (edit)">'
            '<input type="checkbox" id="regattaSaEditToggle" autocomplete="off" aria-label="Public view; check for Super Admin edit mode">'
            '<span class="regatta-sa-slider" aria-hidden="true"></span>'
            "</label>"
            '<span class="regatta-sa-mode-text regatta-sa-mode-text--edit" title="Super Admin (edit mode)">Super Admin (edit)</span>'
            "</div>"
        )
    cur = _normalize_hub_news_badge_label_for_ui(hub_badge_label)
'''


def apply_one(text: str, anchor: str, insert: str, name: str, *, allow_multi: int = 1) -> str:
    if insert in text and name != "wind":
        print(f"skip {name}: already present")
        return text
    if name == "wind" and '@app.get("/api/wind2speed/mac")' in text:
        print("skip wind: already present")
        return text
    if name in {"toolbar", "page"} and "mac-tsl-live-cards.js" in text and 'data-mac-tsl="1"' in text:
        print(f"skip {name}: MAC TSL JS already injected")
        return text
    if anchor not in text:
        raise SystemExit(f"ERROR: anchor not found for {name}")
    found = text.count(anchor)
    if found != allow_multi:
        raise SystemExit(f"ERROR: anchor for {name} count={found} expected={allow_multi}")
    print(f"patch {name} x{found}")
    return text.replace(anchor, insert)


def revert_pass_b_wipe(text: str) -> str:
    if PASS_B_WIPE not in text:
        print("skip pass_b_status: wipe already removed")
        return text
    found = text.count(PASS_B_WIPE)
    if found != 1:
        raise SystemExit(f"ERROR: pass_b wipe count={found} expected=1")
    print("revert pass_b_status wipe (keep Upcoming Event + dates)")
    return text.replace(PASS_B_WIPE, "", 1)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: patch_live_mac_tsl_wc_event_url.py /path/to/api.py", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    orig = path.read_text(encoding="utf-8")
    text = orig
    text = apply_one(text, WIND_ANCHOR, WIND_INSERT, "wind")
    text = apply_one(text, LOGO_ANCHOR, LOGO_INSERT, "logo")
    text = apply_one(text, STATUS_ANCHOR, STATUS_INSERT, "status")
    text = apply_one(text, TOOLBAR_ANCHOR, TOOLBAR_INSERT, "toolbar")
    text = apply_one(text, PAGE_ANCHOR, PAGE_INSERT, "page")
    text = revert_pass_b_wipe(text)
    text = apply_one(text, STATUS_DEFAULT_ANCHOR, STATUS_DEFAULT_INSERT, "status_default", allow_multi=2)
    text = apply_one(text, ENTRIES_ANCHOR, ENTRIES_INSERT, "entries_icon")
    text = apply_one(text, NOR_LINK_ANCHOR, NOR_LINK_INSERT, "nor_link", allow_multi=3)
    text = apply_one(text, SA_CHROME_ANCHOR, SA_CHROME_INSERT, "sa_chrome")
    text = apply_one(text, EIS_FN_ANCHOR, EIS_FN_INSERT, "eis_fn")
    text = apply_one(text, EIS_CALL_ANCHOR, EIS_CALL_INSERT, "eis_call")
    for old_pin in (
        "mac-tsl-live-cards.js?v=20261012a",
        "mac-tsl-live-cards.js?v=20261012b",
        "mac-tsl-live-cards.js?v=20261012c",
        "mac-tsl-live-cards.js?v=20261012d",
        "mac-tsl-live-cards.js?v=20261012e",
        "mac-tsl-live-cards.js?v=20261012f",
        "mac-tsl-live-cards.js?v=20261012g",
        "mac-tsl-live-cards.js?v=20261012h",
        "mac-tsl-live-cards.js?v=20261012i",
        "mac-tsl-live-cards.js?v=20261012j",
        "mac-tsl-live-cards.js?v=20261012k",
        "mac-tsl-live-cards.js?v=20261012l",
        "mac-tsl-live-cards.js?v=20261012m",
        "mac-tsl-live-cards.js?v=20261012n",
    ):
        if old_pin in text:
            text = text.replace(old_pin, "mac-tsl-live-cards.js?v=20261012o")
            print("pin mac-tsl-live-cards.js?v=20261012o")
    # Listing / header left slot is Event Logo only (Class Logo is rejected by hub cards).
    if TSL_CLASS_LOGO in text and TSL_LOGO not in text:
        text = text.replace(
            f'("{SLUG.replace("-", " ")}", "{TSL_CLASS_LOGO}"',
            f'("2026 10 17 mac tsl wc team sailing", "{TSL_LOGO}"',
        )
        text = text.replace(
            f'("team sailing league", "{TSL_CLASS_LOGO}"',
            f'("team sailing league", "{TSL_LOGO}"',
        )
        text = text.replace(
            f'("team sailing", "{TSL_CLASS_LOGO}"',
            f'("team sailing", "{TSL_LOGO}"',
        )
        print("retarget TSL event-logo rules to Event Logo folder")
    text = text.replace(
        f'return "{TSL_CLASS_LOGO}"',
        f'return "{TSL_LOGO}"',
    )
    admin_tag = '<script src="/js/mac-tsl-admin.js?v=20261013i" defer></script>'
    cards_tag = '<script src="/js/mac-tsl-live-cards.js?v=20261012o" defer></script>'
    if "mac-tsl-admin.js?v=20261012a" in text:
        text = text.replace("mac-tsl-admin.js?v=20261012a", "mac-tsl-admin.js?v=20261013g")
    if "mac-tsl-admin.js?v=20261012b" in text:
        text = text.replace("mac-tsl-admin.js?v=20261012b", "mac-tsl-admin.js?v=20261013g")
    if "mac-tsl-admin.js?v=20261012p" in text:
        text = text.replace("mac-tsl-admin.js?v=20261012p", "mac-tsl-admin.js?v=20261013g")
    if "mac-tsl-admin.js?v=20261012t" in text:
        text = text.replace("mac-tsl-admin.js?v=20261012t", "mac-tsl-admin.js?v=20261013g")
    if "mac-tsl-admin.js?v=20261012u" in text:
        text = text.replace("mac-tsl-admin.js?v=20261012u", "mac-tsl-admin.js?v=20261013g")
    if "mac-tsl-admin.js?v=20261013a" in text:
        text = text.replace("mac-tsl-admin.js?v=20261013a", "mac-tsl-admin.js?v=20261013g")
    if "mac-tsl-admin.js?v=20261013b" in text:
        text = text.replace("mac-tsl-admin.js?v=20261013b", "mac-tsl-admin.js?v=20261013g")
    if "mac-tsl-admin.js?v=20261013c" in text:
        text = text.replace("mac-tsl-admin.js?v=20261013c", "mac-tsl-admin.js?v=20261013g")
    if "mac-tsl-admin.js?v=20261013d" in text:
        text = text.replace("mac-tsl-admin.js?v=20261013d", "mac-tsl-admin.js?v=20261013g")
    if "mac-tsl-admin.js?v=20261013e" in text:
        text = text.replace("mac-tsl-admin.js?v=20261013e", "mac-tsl-admin.js?v=20261013g")
    if "mac-tsl-admin.js?v=20261013f" in text:
        text = text.replace("mac-tsl-admin.js?v=20261013f", "mac-tsl-admin.js?v=20261013h")
    if "mac-tsl-admin.js?v=20261013g" in text:
        text = text.replace("mac-tsl-admin.js?v=20261013g", "mac-tsl-admin.js?v=20261013i")
    if "mac-tsl-admin.js?v=20261013h" in text:
        text = text.replace("mac-tsl-admin.js?v=20261013h", "mac-tsl-admin.js?v=20261013i")
        print("pin admin 20261013i")
    if cards_tag in text and admin_tag not in text:
        text = text.replace(cards_tag, cards_tag + admin_tag)
        print("inject mac-tsl-admin.js next to live-cards")
    if text == orig:
        print("No changes (already patched).")
        return 0
    path.write_text(text, encoding="utf-8")
    print(f"Wrote {path} ({len(orig.splitlines())} -> {len(text.splitlines())} lines)")
    for needle in (
        "/api/wind2speed/mac",
        "mac-tsl-live-cards.js",
        "mac-tsl-admin.js",
        'data-mac-tsl="1"',
        SLUG,
        TSL_LOGO,
        "Upcoming Event",
        "entry-total-line--icon",
        PASS_B_WIPE.strip(),
    ):
        print(f"  grep {needle!r}: {text.count(needle)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
