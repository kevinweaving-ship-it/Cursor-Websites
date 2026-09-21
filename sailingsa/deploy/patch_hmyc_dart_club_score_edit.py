#!/usr/bin/env python3
"""Enable Cape Classic club-score-edit on HMYC Dart 18 Nationals + club_manager role."""

from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
JS = Path("/var/www/sailingsa/js/club-score-edit.js")

REPLACES = [
    (
        API,
        '    return _normalize_account_role(_get_session_role(request)) in ("club_admin", "clubadmin")\n',
        '    return _normalize_account_role(_get_session_role(request)) in ("club_admin", "clubadmin", "club_manager")\n',
    ),
    (
        API,
        '            if not str(regatta_id or "").startswith("2026-09-13-zvyc-cape-classic"):\n                raise HTTPException(status_code=404, detail="not Cape Classic")\n',
        '            if not (\n                str(regatta_id or "").startswith("2026-09-13-zvyc-cape-classic")\n                or str(regatta_id or "").startswith("2026-09-24-hmyc-dart-18-nationals")\n            ):\n                raise HTTPException(status_code=404, detail="not a club-score event")\n',
    ),
    (
        JS,
        '  if (path.indexOf("2026-09-13-zvyc-cape-classic") === -1) return;\n',
        '  if (\n    path.indexOf("2026-09-13-zvyc-cape-classic") === -1 &&\n    path.indexOf("2026-09-24-hmyc-dart-18-nationals") === -1\n  )\n    return;\n',
    ),
    (
        JS,
        '      role === "club_admin" ||\n      role === "clubadmin" ||\n      role === "admin" ||\n',
        '      role === "club_admin" ||\n      role === "clubadmin" ||\n      role === "club_manager" ||\n      role === "admin" ||\n',
    ),
]


def _add_club_manager_to_role_tuples(text: str) -> str:
    old = '("super_admin", "superadmin", "club_admin", "clubadmin")'
    new = '("super_admin", "superadmin", "club_admin", "clubadmin", "club_manager")'
    if old not in text:
        raise SystemExit("role tuple not found")
    text = text.replace(old, new)
    old2 = 'role_n in ("club_admin", "clubadmin")'
    new2 = 'role_n in ("club_admin", "clubadmin", "club_manager")'
    if old2 not in text:
        raise SystemExit("club_admin host-check tuple not found")
    return text.replace(old2, new2)


def _split_hmyc_script(text: str) -> str:
    old = '''        elif str(regatta_id) in ("2026-09-19-hmyc-midmar-cup", "2026-09-24-hmyc-dart-18-nationals"):
            # MIDMAR_HMYC_WX_CAM_v1 + Dart 18 Nationals inherits the same HMYC stack.
            mm_card = ""
            mm_card_script = '<script src="/js/midmar-live-media.js?v=midmarwx55dart2" defer></script><script src="/js/midmar-leaderboard.js?v=mmlb16dart1" defer></script><script src="/js/midmar-media-rotate.js?v=mmrot4" defer></script>'
'''
    new = '''        elif str(regatta_id) == "2026-09-19-hmyc-midmar-cup":
            # MIDMAR_HMYC_WX_CAM_v1
            mm_card = ""
            mm_card_script = '<script src="/js/midmar-live-media.js?v=midmarwx55dart2" defer></script><script src="/js/midmar-leaderboard.js?v=mmlb16dart1" defer></script><script src="/js/midmar-media-rotate.js?v=mmrot4" defer></script>'
        elif str(regatta_id).startswith("2026-09-24-hmyc-dart-18-nationals"):
            # Same HMYC cards + Cape Classic club-score-edit (DH/SH).
            mm_card = ""
            mm_card_script = '<script src="/js/midmar-live-media.js?v=midmarwx55dart2" defer></script><script src="/js/midmar-leaderboard.js?v=mmlb16dart1" defer></script><script src="/js/midmar-media-rotate.js?v=mmrot4" defer></script><script src="/js/club-score-edit.js?v=ccr22" defer></script>'
'''
    if old not in text:
        if "club-score-edit.js?v=ccr22" in text:
            return text
        raise SystemExit("HMYC script block not found")
    return text.replace(old, new, 1)


def main() -> int:
    api = API.read_text()
    if "club-score-edit.js?v=ccr22" not in api:
        api = _add_club_manager_to_role_tuples(api)
        api = _split_hmyc_script(api)
    js = JS.read_text()
    for path, old, new in REPLACES:
        blob = api if path == API else js
        if new.strip() in blob and old not in blob:
            continue
        if old not in blob:
            raise SystemExit(f"pattern not found in {path}")
        blob = blob.replace(old, new, 1)
        if path == API:
            api = blob
        else:
            js = blob
    API.write_text(api)
    JS.write_text(js)
    print("patched", API, JS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
