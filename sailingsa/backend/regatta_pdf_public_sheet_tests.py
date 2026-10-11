"""Class PY stays after Class on the public PDF sheet."""
from __future__ import annotations

from sailingsa.backend.regatta_pdf_public_sheet import sanitize_public_fleet_html

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


def test_py_stays_after_class_and_hidden_calc_cols_drop() -> None:
    out = sanitize_public_fleet_html(_TABLE)
    labs = _labels(out)
    assert labs[:3] == ["Rank", "Class", "PY"], labs
    assert "Age" not in labs
    assert "Elapsed" not in labs
    assert "Corrected" not in labs
    assert "832" in out
    assert "1102" in out
    assert "18:46" not in out
    assert "wc-score" in out and "DNC" in out


def test_already_after_class_is_stable() -> None:
    html = (
        "<table><thead><tr>"
        "<th>Rank</th><th>Class</th><th>PY</th><th>Sail No</th>"
        "</tr></thead><tbody><tr>"
        "<td>1</td><td>Dart 18</td><td>832</td><td>520</td>"
        "</tr></tbody></table>"
    )
    out = sanitize_public_fleet_html(html)
    assert _labels(out) == ["Rank", "Class", "PY", "Sail No"]


if __name__ == "__main__":
    test_py_stays_after_class_and_hidden_calc_cols_drop()
    test_already_after_class_is_stable()
    print("ok")
