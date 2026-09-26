#!/usr/bin/env python3
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
OLD_IF = (
    "                if is_wc_fleet_sheet or sa_fleet_ops:\n"
    "                    # Display only: discard from stored parens; split number vs code for typography (WC only).\n"
)
NEW_IF = (
    "                if is_wc_fleet_sheet or sa_fleet_ops or str(fleet.get(\"regatta_id\") or \"\").startswith(\"2026-09-24-hmyc-dart-18-nationals\"):\n"
    "                    # Display only: discard from stored parens; split number vs code for typography (WC only).\n"
)
OLD_INNER = """                    _inner = (
                        f'<span class="{cell_class}"{_style}>{html_module.escape(score_display)}</span>'
                        if cell_class
                        else html_module.escape(score_display)
                    )
"""
NEW_INNER = """                    _pn, _pc = _wc_parse_race_cell_parts(
                        str(_score_raw)[1:-1].strip()
                        if is_discarded
                        else str(_score_raw or "").strip()
                    )
                    if _pc:
                        _val = (
                            _wc_format_points_for_display(float(_pn), use_decimals_in_block)
                            if _pn is not None
                            else ""
                        )
                        _inner = (
                            f'<span class="code{" disc" if is_discarded else ""}">'
                            f'<span class="wc-score">{html_module.escape(_val)}</span>'
                            f'<span class="wc-code">{html_module.escape(_pc)}</span>'
                            f"</span>"
                        )
                    else:
                        _inner = (
                            f'<span class="{cell_class}"{_style}>{html_module.escape(score_display)}</span>'
                            if cell_class
                            else html_module.escape(score_display)
                        )
"""


def main() -> None:
    t = API.read_text()
    print("IF", t.count(OLD_IF), "INNER", t.count(OLD_INNER))
    if t.count(OLD_IF) != 1:
        raise SystemExit("IF_MARK")
    t = t.replace(OLD_IF, NEW_IF, 1)
    if t.count(OLD_INNER) != 1:
        raise SystemExit("INNER_MARK")
    t = t.replace(OLD_INNER, NEW_INNER, 1)
    API.write_text(t)
    print("DART_IF", NEW_IF[:40] in open(API).read())
    print("CHANGED True")
    print("DONE")


if __name__ == "__main__":
    main()
