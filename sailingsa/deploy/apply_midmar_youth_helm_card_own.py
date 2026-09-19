#!/usr/bin/env python3
"""Midmar Youth Helm note: own full-width card, same chrome as LB/weather, MP first."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

HTML_OLD = """        _yh_card = (
            '<div class="card" id="midmar-youth-helm-note">'
            "<h2>🔵 Youth Helm Races</h2>"
            "<p>Blue scores = declared youth-helm races and cannot be discarded.</p>"
            "</div>"
        )  # YOUTH_HELM_CARD_v1
    section_html = (
        f'<div class="fleet-section"{bid_attr}>'
        f"{late_part}"
        f'<div class="{_fleet_hdr_cls}">{_fleet_hdr_body}</div>'
        f'<div class="table-wrapper">{table_html}{course_footer_html}</div>'
        f"{_yh_card}</div>"
    )
"""

HTML_NEW = """        _yh_card = (
            '<div class="card" id="midmar-youth-helm-note">'
            '<h2 class="section-title">🔵 Youth Helm Races</h2>'
            "<p>Blue scores = declared youth-helm races and cannot be discarded.</p>"
            "</div>"
        )  # YOUTH_HELM_CARD_v2
    section_html = (
        f'<div class="fleet-section"{bid_attr}>'
        f"{late_part}"
        f'<div class="{_fleet_hdr_cls}">{_fleet_hdr_body}</div>'
        f'<div class="table-wrapper">{table_html}{course_footer_html}</div></div>'
        f"{_yh_card}"
    )
"""

CSS_OLD = (
    '    "#midmar-youth-helm-note{margin-top:12px;margin-bottom:16px}"\n'
    '    "#midmar-youth-helm-note h2{margin:0 0 6px;font-size:0.85rem;font-weight:700;'
    "text-transform:uppercase;letter-spacing:0.02em;color:#001f3f;"
    'border-bottom:2px solid #001f3f}"\n'
    '    "#midmar-youth-helm-note p{margin:8px 0 0;color:#001f3f}"\n'
)

CSS_NEW = (
    '    ".regatta-page>#midmar-youth-helm-note.card{'
    "order:4;width:100%!important;max-width:100%!important;"
    "box-sizing:border-box!important;margin:12px 0 0!important;"
    "padding:10px 16px;background:#fff;"
    "border:2px solid #001f3f!important;border-radius:8px!important;"
    "box-shadow:0 1px 3px rgba(0,31,63,0.08)!important;overflow:hidden}"
    "  # YOUTH_HELM_CARD_v2\n"
    '    "@media screen and (orientation:portrait) and (max-width:767px){"'
    '".regatta-page>#midmar-youth-helm-note.card{'
    "width:100%!important;max-width:100%!important;"
    "margin-left:0!important;margin-right:0!important;"
    "padding:10px 16px;box-sizing:border-box!important}"
    "#midmar-youth-helm-note .section-title,"
    "#midmar-youth-helm-note p{white-space:normal;overflow-wrap:anywhere;"
    'word-break:break-word;max-width:100%}}"\n'
    '    "#midmar-youth-helm-note .section-title{margin:0 0 6px;padding:0 0 4px;'
    "font-size:0.85rem;line-height:1.25;font-weight:700;text-transform:uppercase;"
    'letter-spacing:0.02em;color:#001f3f;border-bottom:2px solid #001f3f}"\n'
    '    "#midmar-youth-helm-note p{margin:8px 0 0;color:#001f3f;font-size:0.95rem;'
    'line-height:1.35}"\n'
)


def main() -> None:
    text = API.read_text()
    if "YOUTH_HELM_CARD_v2" in text:
        print("CARD_OWN_ALREADY")
        return
    if text.count(HTML_OLD) != 1:
        raise SystemExit("ANCHOR_HTML_" + str(text.count(HTML_OLD)))
    if text.count(CSS_OLD) != 1:
        raise SystemExit("ANCHOR_CSS_" + str(text.count(CSS_OLD)))
    text = text.replace(HTML_OLD, HTML_NEW, 1).replace(CSS_OLD, CSS_NEW, 1)
    API.write_text(text)
    print("CARD_OWN_OK")


if __name__ == "__main__":
    main()
