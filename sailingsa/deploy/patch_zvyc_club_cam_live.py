#!/usr/bin/env python3
"""Surgical live api.py patch: ZVYC club-cam alias + event-page cam card.

Run on the live box after LIVE EDIT PROTOCOL snapshot + chattr -i.
Does not replace api.py. Exits 0 if already applied.
"""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

HELPERS = '''
def _zvyc_event_wants_club_cam(regatta_id: str, host_code: str = "") -> bool:
    """ZVYC-hosted events that do not already mount the Cape Classic MM cam tile."""
    rid = str(regatta_id or "").strip().lower()
    cape = str(_CAPE_CLASSIC_MM_REGATTA_ID).strip().lower()
    if not rid:
        return False
    if rid == cape or rid.startswith(cape + "-"):
        return False
    if "zvyc" in rid:
        return True
    return str(host_code or "").strip().upper() == "ZVYC"


def _zvyc_event_cam_card_html() -> str:
    """Standalone HLS club-cam card. Player is /js/zvyc-club-cam.js (proxy only)."""
    return (
        '<section id="zvyc-club-cam" class="card club-live-cam club-zvyc-cam" '
        'data-zvyc-club-cam aria-label="ZVYC club cam">'
        '<div class="cam-shot cam-cell" data-cam="zvyc">'
        '<span class="cam-cap">ZVYC</span>'
        '<video muted playsinline poster="/assets/adverts/mm-cape-classic/zvyc-live-cam.jpg"></video>'
        "</div></section>"
    )


'''

CLUB_CAM_ROUTE = '''
@app.get("/api/club-cam/zvyc")
def api_club_cam_zvyc():
    """ZVYC Zeekoevlei cam status. Stream lives on the Cape Classic proxy path."""
    live = False
    try:
        live = bool(_zvyc_cam_probe_live(""))
    except Exception as e:
        print(f"[zvyc_club_cam] status failed: {e}", flush=True)
    return {
        "ok": True,
        "kind": "hls",
        "label": "ZVYC club cam",
        "live": live,
        "play_url": "/api/regatta/2026-09-13-zvyc-cape-classic/zvyc-live-cam",
        "status_url": "/api/regatta/2026-09-13-zvyc-cape-classic/zvyc-live-cam-status",
        "thumb_url": "/api/regatta/2026-09-13-zvyc-cape-classic/zvyc-live-cam-thumb",
    }

'''


def main() -> int:
    text = API.read_text(encoding="utf-8")
    changed = False

    if "_zvyc_event_wants_club_cam" not in text:
        needle = "def _cape_classic_mm_reels_card_html(regatta_id: str) -> str:"
        if needle not in text:
            raise SystemExit("missing _cape_classic_mm_reels_card_html")
        text = text.replace(needle, HELPERS + needle, 1)
        changed = True

    old_script = '<script src="/js/mm-lipton-reels-card.js?v=mmr142" defer></script>'
    new_script = '<script src="/js/mm-lipton-reels-card.js?v=mmr143" defer></script>'
    if old_script in text:
        text = text.replace(old_script, new_script)
        changed = True

    old_club = (
        r'<script src=\"/js/live-cam-sources.js?v=clubwx18\" defer></script>'
        r'<script src=\"/js/club-live-media.js?v=clubwx22\" defer></script>'
    )
    new_club = (
        r'<script src=\"/js/live-cam-sources.js?v=clubwx23\" defer></script>'
        r'<script src=\"/js/club-live-media.js?v=clubwx23\" defer></script>'
    )
    if old_club in text:
        text = text.replace(old_club, new_club)
        changed = True
    if "/css/mm-lipton-reels.css?v=clubwx22" in text:
        text = text.replace(
            "/css/mm-lipton-reels.css?v=clubwx22",
            "/css/mm-lipton-reels.css?v=clubwx23",
        )
        changed = True

    inject = (
        '        elif _zvyc_event_wants_club_cam(str(regatta_id), _host_code_logo):\n'
        '            mm_card = _zvyc_event_cam_card_html()\n'
        '            mm_card_script = \'<script src="/js/zvyc-club-cam.js?v=zvycam1" defer></script>\'\n'
    )
    if "_zvyc_event_wants_club_cam(str(regatta_id)" not in text:
        anchor = (
            '            mm_card_script = (\n'
            '                \'<script src="/js/midmar-leaderboard.js?v=mmlb20day" defer></script>\'\n'
            '            )\n'
        )
        if anchor not in text:
            raise SystemExit("missing mm_card elif anchor")
        text = text.replace(anchor, anchor + inject, 1)
        changed = True

    prepend = (
        '        if \'id="zvyc-club-cam"\' not in (mm_card or "") and (\n'
        '            "zvyc" in str(regatta_id or "").lower()\n'
        '            or str(_host_code_logo or "").strip().upper() == "ZVYC"\n'
        '        ):\n'
        '            mm_card = _zvyc_event_cam_card_html() + (mm_card or "")\n'
        '            mm_card_script = (\n'
        '                \'<script src="/js/zvyc-club-cam.js?v=zvycam1" defer></script>\'\n'
        '                + (mm_card_script or "")\n'
        '            )\n'
    )
    if 'id="zvyc-club-cam"\' not in (mm_card or "")' not in text:
        banner = '        banner_top = _wc_regatta_source_banner_html(str(regatta_id), position="top")\n'
        marker = (
            '            mm_card_script = \'<script src="/js/zvyc-club-cam.js?v=zvycam1" defer></script>\'\n'
            + banner
        )
        if marker not in text:
            raise SystemExit("missing cape prepend banner anchor")
        text = text.replace(marker, marker.replace(banner, prepend + banner), 1)
        changed = True

    if '@app.get("/api/club-cam/zvyc")' not in text:
        anchor = (
            '@app.get("/api/club-cam/hmyc")\n'
            "\n"
            "def api_club_cam_hmyc():\n"
        )
        if anchor not in text:
            raise SystemExit("missing /api/club-cam/hmyc anchor")
        # Insert after the hmyc function's return — keep it simple: before TSL routes.
        tsl = "# TSL_TEAM_RACING_ROUTES_v1"
        if tsl not in text:
            raise SystemExit("missing TSL anchor")
        text = text.replace(tsl, CLUB_CAM_ROUTE + tsl, 1)
        changed = True

    if not changed:
        print("already applied")
        return 0
    API.write_text(text, encoding="utf-8")
    print("patched", API)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
