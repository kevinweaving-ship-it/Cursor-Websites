"""Public PDF drops PY / Age / elapsed JSON. Parent admin keeps Class PY."""
from __future__ import annotations

from sailingsa.backend.regatta_pdf_public_sheet import (
    build_parent_mirror_document,
    sanitize_public_fleet_html,
)

_TABLE = """
<div class="fleet-section">
<table class="fleet-results-table">
<thead><tr>
<th class="rank-col">Rank</th>
<th class="class-col">Class</th>
<th class="sail-col">Sail No</th>
<th class="club-col">Club</th>
<th class="wc-meta-col">Age</th>
<th class="helm-col">Helm</th>
<th class="race-col">R1</th>
<th class="wc-meta-col">PY</th>
<th class="wc-meta-col">Elapsed</th>
<th class="wc-meta-col">Corrected</th>
<th class="total-col">Total</th>
<th class="nett-col">Nett</th>
</tr></thead>
<tbody>
<tr data-result-id="1">
<td class="rank-col">1st</td>
<td class="class-col"><a title="Dart 18" href="/class/dart-18">Dart 18</a></td>
<td class="sail-col">520</td>
<td class="club-col">HMYC</td>
<td class="wc-meta-col">Snr</td>
<td class="helm-col">Lorrian Wells</td>
<td class="race-col"><span class="wc-score">1</span></td>
<td class="wc-meta-col">832</td>
<td class="wc-meta-col">{&quot;R1&quot;: &quot;18:46&quot;}</td>
<td class="wc-meta-col">{&quot;R1&quot;: &quot;22:33.4&quot;}</td>
<td class="total-col">1</td>
<td class="nett-col">1</td>
</tr>
<tr data-result-id="2">
<td class="rank-col">2nd</td>
<td class="class-col"><a title="ILCA 7" href="/class/ilca-7">ILCA 7</a></td>
<td class="sail-col">2</td>
<td class="club-col">HMYC</td>
<td class="wc-meta-col">Snr</td>
<td class="helm-col">Simon Dommett</td>
<td class="race-col"><span class="wc-code">DNC</span></td>
<td class="wc-meta-col">1102</td>
<td class="wc-meta-col">{&quot;R1&quot;: &quot;0:00&quot;}</td>
<td class="wc-meta-col"></td>
<td class="total-col">3</td>
<td class="nett-col">3</td>
</tr>
</tbody>
</table>
</div>
"""


def _labels(html: str) -> list[str]:
    import re

    head = re.search(r"<thead[\s\S]+?</thead>", html)
    assert head, html
    cells = re.findall(r"<th[^>]*>(.*?)</th>", head.group(0))
    return [re.sub(r"<[^>]+>", "", c).strip() for c in cells]


def test_public_pdf_drops_py_and_hidden_calc_cols() -> None:
    out = sanitize_public_fleet_html(_TABLE)
    labs = _labels(out)
    assert labs[:3] == ["Rank", "Class", "Sail No"], labs
    assert "PY" not in labs
    assert "Age" not in labs
    assert "Elapsed" not in labs
    assert "Corrected" not in labs
    assert "832" not in out
    assert "1102" not in out
    assert "18:46" not in out
    assert "wc-score" in out and "DNC" in out


def test_public_pdf_drops_entries_closed_badge() -> None:
    html = (
        '<div class="fleet-section">'
        '<span class="fleet-title-with-logo">Fleet</span>'
        '<span class="fleet-entries-closed-badge">Entries closed</span>'
        '<table class="fleet-results-table"><thead><tr>'
        '<th class="rank-col">Rank</th><th class="helm-col">Helm</th>'
        "</tr></thead><tbody><tr>"
        '<td class="rank-col">1st</td><td class="helm-col">A</td>'
        "</tr></tbody></table></div>"
    )
    out = sanitize_public_fleet_html(html)
    assert "Entries closed" not in out
    assert "fleet-entries-closed-badge" not in out
    assert "Fleet" in out
    assert "Helm" in out


def test_parent_sub_urls_stay_clickable() -> None:
    html = (
        '<div class="fleet-section">'
        '<span class="fleet-title-with-logo">'
        '<img class="rs-fleet-title-logo" src="/artwork/Event Logo/Dam-Bottle-Sprints.png" alt="Event">'
        "Fleet</span>"
        "<table><tbody><tr>"
        '<td class="class-col"><a href="/class/ilca-7">ILCA 7</a></td>'
        '<td class="sail-col"><a href="/boat/ilca-7-2">2</a></td>'
        '<td class="club-col"><a href="/club/hmyc">HMYC</a></td>'
        '<td class="helm-col"><a href="/sailor/simon-dommett">Simon Dommett</a></td>'
        "</tr></tbody></table></div>"
    )
    out = sanitize_public_fleet_html(html, "/artwork/Event Logo/Dam-Bottle-Sprints.png")
    assert "Open Fleet" in out
    assert 'href="https://sailingsa.co.za/class/ilca-7"' in out
    assert 'href="https://sailingsa.co.za/boat/ilca-7-2"' in out
    assert 'href="https://sailingsa.co.za/club/hmyc"' in out
    assert 'href="https://sailingsa.co.za/sailor/simon-dommett"' in out
    assert "Entries closed" not in out


def test_parent_mirror_document_keeps_parent_links() -> None:
    header = (
        '<div class="regatta-header-wrap"><div class="header">'
        '<a href="/classes"><img class="regatta-header-left-logo-img" '
        'src="/artwork/Event Logo/Dam-Bottle-Sprints.png"></a>'
        '<h1 class="regatta-name">2026 Dam Bottle Sprints</h1>'
        '<a href="/club/hmyc">HMYC</a></div></div>'
    )
    fleet = {
        "html": (
            '<div class="fleet-section"><a href="/sailor/lorrian-wells">Lorrian Wells</a></div>'
        )
    }
    doc = build_parent_mirror_document(
        header_html=header,
        fleets=[fleet],
        orient="landscape",
        event_name="2026 Dam Bottle Sprints",
        style_html='<link rel="stylesheet" href="/css/main.css">',
        sheet_url="https://sailingsa.co.za/regatta/2026-10-10-hmyc-dam-bottle-sprints",
    )
    assert "2026 Dam Bottle Sprints" in doc
    assert "main.css" in doc
    assert "https://sailingsa.co.za/sailor/lorrian-wells" in doc
    assert "https://sailingsa.co.za/club/hmyc" in doc
    assert "ssa-print-footer" not in doc
    assert "mark-on-color" not in doc
    assert "Entries closed" not in doc
    assert 'data-dbs-ready="1"' in doc
    assert "border:0.45pt solid #94a3b8" in doc
    assert "border-left:1.1pt solid #1a2750" in doc
    assert "border-right:1.1pt solid #1a2750" in doc
    dirty = (
        "<style>body{color:#001f3f}@media print{.fleet-section{display:none}}</style>"
        '<link rel="stylesheet" href="/css/main.css">'
    )
    from sailingsa.backend.regatta_pdf_public_sheet import parent_page_style_html

    styles = parent_page_style_html(dirty)
    assert "@media print" not in styles
    assert "main.css" in styles
    assert "<style>" not in styles


_PARENT_HEADER = """
<div class="regatta-header-wrap"><div class="header">
<div class="regatta-header-logo-col"><img class="regatta-header-left-logo-img" src="/artwork/Event Logo/Dam-Bottle-Sprints.png" alt=""></div>
<div class="regatta-header-main-col">
<h1 class="regatta-name">2026 Dam Bottle Sprints</h1>
<div class="host-club">Host: HMYC - Henley Midmar Yacht Club</div>
<div class="regatta-header-status-stack">
<div class="status-line">Results are Final</div>
<div class="status-line status-line--asat"><span class="regatta-status-as-at-date">11 Oct 2026 10:23</span></div>
<div class="entry-total-line entry-total-line--icon">4 Entries</div>
</div></div>
<div class="regatta-header-club-logo-col"><img class="regatta-header-club-logo-img" src="/artwork/Club Logo/HMYC.png" alt=""></div>
</div></div>
"""


def test_parent_header_is_copied() -> None:
    from sailingsa.backend.regatta_pdf_public_sheet import (
        extract_parent_header_html,
        parent_page_entries_count,
        parent_page_event_name,
        parent_page_status_line,
        pdf_page_orientation,
    )

    html = extract_parent_header_html(_PARENT_HEADER)
    assert "2026 Dam Bottle Sprints" in html
    assert "entry-total-line" in html
    assert "4 Entries" in html
    assert "regatta-header-club-logo-img" in html
    assert html.count("<div") == html.lower().count("</div>")
    assert parent_page_event_name(_PARENT_HEADER) == "2026 Dam Bottle Sprints"
    assert parent_page_status_line(_PARENT_HEADER) == "Results are Final as at 11 October 2026 at 10:23"
    assert parent_page_entries_count(_PARENT_HEADER) == "4"
    assert pdf_page_orientation("2026-10-10-hmyc-dam-bottle-sprints") == ""


def test_parent_header_keeps_right_logo_through_nested_divs() -> None:
    from sailingsa.backend.regatta_pdf_public_sheet import extract_parent_header_html

    nested = (
        '<div class="regatta-header-wrap"><div class="header">'
        '<div class="regatta-header-logo-col"><img class="regatta-header-left-logo-img" src="/artwork/Event Logo/Dam-Bottle-Sprints.png"></div>'
        '<div class="regatta-header-main-col"><h1 class="regatta-name">2026 Dam Bottle Sprints</h1>'
        '<div class="regatta-header-status-stack"><div class="status-line">Results are Final</div>'
        '<div class="entry-total-line">4 Entries</div></div></div>'
        '<div class="regatta-header-club-logo-col"><img class="regatta-header-club-logo-img" src="/artwork/Club Logo/HMYC.png"></div>'
        "</div></div>"
        '<div class="fleet-section"><span class="fleet-title-with-logo">Open Fleet</span></div>'
    )
    html = extract_parent_header_html(nested)
    assert "regatta-header-club-logo-img" in html
    assert "fleet-section" not in html
    assert html.count("<div") == html.lower().count("</div>")


if __name__ == "__main__":
    test_public_pdf_drops_py_and_hidden_calc_cols()
    test_public_pdf_drops_entries_closed_badge()
    test_parent_sub_urls_stay_clickable()
    test_parent_mirror_document_keeps_parent_links()
    test_parent_header_is_copied()
    test_parent_header_keeps_right_logo_through_nested_divs()
    print("ok")

