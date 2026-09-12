#!/usr/bin/env python3
"""Remove Lipton Table Bay weather + Table Mountain cam from generic live regatta URLs.

Those widgets were a Lipton once-off. They must not render on ZVYC Cape Classic
or any future live event page.
"""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

REPLACEMENTS = [
    (
        "        body_html = header_html + _regatta_live_wx_panel_html(start_d, end_d, str(regatta_id)) + banner_top + sa_columns_frag + fleet_picker_frag + fleet_wrapped + \"\\n\" + banner_bottom + print_btn\n",
        "        body_html = header_html + banner_top + sa_columns_frag + fleet_picker_frag + fleet_wrapped + \"\\n\" + banner_bottom + print_btn\n",
    ),
    (
        "            header_html + mm_card + _regatta_live_wx_panel_html(start_d, end_d, str(regatta_id)) + banner_top + event_info_frag + sa_columns_frag + \"\\n\"\n",
        "            header_html + mm_card + banner_top + event_info_frag + sa_columns_frag + \"\\n\"\n",
    ),
    (
        '    ".regatta-live-wx{margin:8px 0 10px;padding:6px;border:1.5px solid #1a2750;border-radius:8px;background:#fff;box-sizing:border-box}"',
        '    ".regatta-page:not([data-live-lipton=\\"1\\"])>.regatta-live-wx,.regatta-page:not([data-live-lipton=\\"1\\"])>.regatta-live-clip{display:none!important}"\n'
        '    ".regatta-live-wx{margin:8px 0 10px;padding:6px;border:1.5px solid #1a2750;border-radius:8px;background:#fff;box-sizing:border-box}"',
    ),
]


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    text = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(REPLACEMENTS, start=1):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: replacement {i}: expected 1 match, found {n} for:\n{old[:180]!r}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
