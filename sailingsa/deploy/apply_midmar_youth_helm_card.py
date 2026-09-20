#!/usr/bin/env python3
"""Midmar: small .card below the results sheet explaining blue Youth Helm scores."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

OLD = """    section_html = (
        f'<div class="fleet-section"{bid_attr}>'
        f"{late_part}"
        f'<div class="{_fleet_hdr_cls}">{_fleet_hdr_body}</div>'
        f'<div class="table-wrapper">{table_html}{course_footer_html}</div></div>'
    )
"""

NEW = """    _yh_card = ""
    if any(
        isinstance((r.get("race_scores") or {}), dict)
        and (r.get("race_scores") or {}).get("_no_discard")
        for r in rows
    ):
        _yh_card = (
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

CSS_OLD = '    ".youth-helm-nd{color:#0000ee!important;font-weight:700}"  # YOUTH_HELM_ND_v1\n'
CSS_NEW = (
    '    ".youth-helm-nd{color:#0000ee!important;font-weight:700}"  # YOUTH_HELM_ND_v1\n'
    '    "#midmar-youth-helm-note{margin-top:12px;margin-bottom:16px}"\n'
    '    "#midmar-youth-helm-note h2{margin:0 0 6px;font-size:0.85rem;font-weight:700;'
    "text-transform:uppercase;letter-spacing:0.02em;color:#001f3f;"
    'border-bottom:2px solid #001f3f}"\n'
    '    "#midmar-youth-helm-note p{margin:8px 0 0;color:#001f3f}"\n'
)


def main() -> None:
    text = API.read_text()
    if "YOUTH_HELM_CARD_v1" in text:
        print("CARD_ALREADY")
        return
    if text.count(OLD) != 1:
        raise SystemExit("ANCHOR_SECTION_" + str(text.count(OLD)))
    if text.count(CSS_OLD) != 1:
        raise SystemExit("ANCHOR_CSS_" + str(text.count(CSS_OLD)))
    text = text.replace(OLD, NEW, 1).replace(CSS_OLD, CSS_NEW, 1)
    API.write_text(text)
    print("CARD_OK")


if __name__ == "__main__":
    main()
