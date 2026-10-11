"""Patch live stored PDF writer to print the parent sheet (header + fleet + table).

Does not change gold api.py. Parent links stay clickable.
"""
from __future__ import annotations

from pathlib import Path

P = Path("/var/www/sailingsa/sailingsa/backend/regatta_stored_pdf.py")

OLD_INIT = "    header_html = \"\"\n"
NEW_INIT = "    header_html = \"\"\n    style_html = \"\"\n"

OLD_HDR = "        header_html = packet.get(\"header_html\") or \"\"\n"
NEW_HDR = (
    "        header_html = packet.get(\"header_html\") or \"\"\n"
    "        style_html = packet.get(\"style_html\") or style_html\n"
)

OLD_HDR2 = "        if packet.get(\"header_html\"):\n            header_html = packet[\"header_html\"]\n"
NEW_HDR2 = (
    "        if packet.get(\"header_html\"):\n"
    "            header_html = packet[\"header_html\"]\n"
    "        if packet.get(\"style_html\"):\n"
    "            style_html = packet[\"style_html\"]\n"
)

OLD_BUILD = """    parent_fleets = paginate_fleet_htmls(fleets, orient)
    parent_html = build_print_document(
        event_name=event_name,
        host=host,
        status_line=status_line,
        sheet_url=sheet_url or f"https://sailingsa.co.za/regatta/{slug}",
        fleets=parent_fleets,
        orient=orient,
        left_logo=left_logo,
        right_logo=right_logo,
        left_href=left_href,
        right_href=right_href,
        host_href=host_href,
        header_html=header_html,
    )
"""

NEW_BUILD = """    parent_fleets = paginate_fleet_htmls(fleets, orient)
    sheet = sheet_url or f"https://sailingsa.co.za/regatta/{slug}"
    if header_html:
        from sailingsa.backend.regatta_pdf_public_sheet import build_parent_mirror_document
        parent_html = build_parent_mirror_document(
            header_html=header_html,
            fleets=parent_fleets,
            orient=orient,
            event_name=event_name,
            style_html=style_html,
            sheet_url=sheet,
        )
    else:
        parent_html = build_print_document(
            event_name=event_name,
            host=host,
            status_line=status_line,
            sheet_url=sheet,
            fleets=parent_fleets,
            orient=orient,
            left_logo=left_logo,
            right_logo=right_logo,
            left_href=left_href,
            right_href=right_href,
            host_href=host_href,
            header_html=header_html,
        )
"""

OLD_CHILD = """                html = build_print_document(
                    event_name=event_name,
                    host=host,
                    status_line=status_line,
                    sheet_url=url,
                    fleets=child_fleets,
                    orient=child_orient,
                    left_logo=left_logo,
                    right_logo=right_logo,
                    left_href=left_href,
                    right_href=right_href,
                    host_href=host_href,
                    header_html=header_html,
                )
"""

NEW_CHILD = """                if header_html:
                    from sailingsa.backend.regatta_pdf_public_sheet import build_parent_mirror_document
                    html = build_parent_mirror_document(
                        header_html=header_html,
                        fleets=child_fleets,
                        orient=child_orient,
                        event_name=event_name,
                        style_html=style_html,
                        sheet_url=url,
                    )
                else:
                    html = build_print_document(
                        event_name=event_name,
                        host=host,
                        status_line=status_line,
                        sheet_url=url,
                        fleets=child_fleets,
                        orient=child_orient,
                        left_logo=left_logo,
                        right_logo=right_logo,
                        left_href=left_href,
                        right_href=right_href,
                        host_href=host_href,
                        header_html=header_html,
                    )
"""


def main() -> None:
    t = P.read_text(encoding="utf-8")
    if "build_parent_mirror_document" in t:
        print("stored_pdf already parent-mirror")
        return
    if OLD_INIT not in t:
        raise SystemExit("init header_html missing")
    t = t.replace(OLD_INIT, NEW_INIT, 1)
    if OLD_HDR in t:
        t = t.replace(OLD_HDR, NEW_HDR, 1)
    if OLD_HDR2 in t:
        t = t.replace(OLD_HDR2, NEW_HDR2, 1)
    if OLD_BUILD not in t:
        raise SystemExit("parent build_print_document block missing")
    t = t.replace(OLD_BUILD, NEW_BUILD, 1)
    if OLD_CHILD not in t:
        raise SystemExit("child build_print_document block missing")
    t = t.replace(OLD_CHILD, NEW_CHILD, 1)
    P.write_text(t, encoding="utf-8")
    print("stored_pdf parent-mirror applied")


if __name__ == "__main__":
    main()
