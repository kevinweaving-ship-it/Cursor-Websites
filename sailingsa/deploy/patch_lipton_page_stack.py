#!/usr/bin/env python3
"""Lipton 2026 page stack: pin header, weather, fleet, results. Hide Public/SA toolbar."""
from __future__ import annotations

import shutil
import time
from pathlib import Path

API_PY = Path("/var/www/sailingsa/api/api.py")

TOOLBAR_OLD = '''def _wc_super_admin_regatta_toolbar_html(regatta_id: str, hub_badge_label: Optional[str] = None) -> str:
    """Toolbar: Public | toggle | Super Admin (edit) | News type → ``blank_hub_news_badge_label`` (same field as hub /blank.html cards)."""
    ls_key = "sailsa_regatta_sa_edit_" + str(regatta_id)
'''

TOOLBAR_NEW = '''def _wc_super_admin_regatta_toolbar_html(regatta_id: str, hub_badge_label: Optional[str] = None) -> str:
    """Toolbar: Public | toggle | Super Admin (edit) | News type → ``blank_hub_news_badge_label`` (same field as hub /blank.html cards)."""
    # Lipton 2026 live event: hide Public / Super Admin (edit) — in the way of the live stack.
    if "lipton" in str(regatta_id or "").strip().lower():
        return ""
    ls_key = "sailsa_regatta_sa_edit_" + str(regatta_id)
'''

CSS_OLD = (
    "    '.regatta-page[data-live-board-page-status=\"LIVE\"]:not([data-live-race-underway=\"1\"]) > .action-buttons,'\n"
    "    '.regatta-page[data-live-board-page-status=\"POSTPONED\"]:not([data-live-race-underway=\"1\"]) > .action-buttons{order:6}'\n"
)

CSS_NEW = (
    "    '.regatta-page[data-live-board-page-status=\"LIVE\"]:not([data-live-race-underway=\"1\"]) > .action-buttons,'\n"
    "    '.regatta-page[data-live-board-page-status=\"POSTPONED\"]:not([data-live-race-underway=\"1\"]) > .action-buttons{order:6}'\n"
    "    '/* Lipton 2026 stack: pin site header; event header; weather (show/hide); fleet header; results table. */'\n"
    "    'body:has(.regatta-page[data-live-lipton=\"1\"]) .site-header{position:sticky;top:0;z-index:5000;background:#001f3f}'\n"
    "    '.regatta-page[data-live-lipton=\"1\"]{display:flex;flex-direction:column}'\n"
    "    '.regatta-page[data-live-lipton=\"1\"] > .regatta-header-wrap{order:1;position:sticky;top:var(--ssa-header-h,4.5rem);z-index:40;background:#fff}'\n"
    "    '.regatta-page[data-live-lipton=\"1\"] > .regatta-live-wx{order:2;display:block}'\n"
    "    '.regatta-page[data-live-lipton=\"1\"] > .fleet-section{order:3;margin-top:12px}'\n"
    "    '.regatta-page[data-live-lipton=\"1\"] > .fleet-section .table-wrapper,'\n"
    "    '.regatta-page[data-live-lipton=\"1\"] > .fleet-section .results-table-container{display:block}'\n"
    "    '.regatta-page[data-live-lipton=\"1\"] > .regatta-live-clip{order:5}'\n"
    "    '.regatta-page[data-live-lipton=\"1\"] > .regatta-live-track{order:6}'\n"
    "    '.regatta-page[data-live-lipton=\"1\"] > .action-buttons{order:7}'\n"
    "    '.regatta-page[data-live-lipton=\"1\"] .regatta-sa-mode-wrap{display:none!important}'\n"
)


def main() -> int:
    s = API_PY.read_text(encoding="utf-8")
    orig = s
    for old, new, label in (
        (TOOLBAR_OLD, TOOLBAR_NEW, "hide SA toolbar"),
        (CSS_OLD, CSS_NEW, "lipton stack css"),
    ):
        if new in s and old not in s:
            print("already", label)
            continue
        n = s.count(old)
        if n != 1:
            raise SystemExit(f"{label}: expected 1, found {n}")
        s = s.replace(old, new, 1)
        print("ok", label)
    if s == orig:
        print("already patched")
        return 0
    bak = API_PY.with_name(API_PY.name + ".bak-lipton-stack-" + time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(API_PY, bak)
    API_PY.write_text(s, encoding="utf-8")
    print("patched", API_PY, "backup", bak)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
