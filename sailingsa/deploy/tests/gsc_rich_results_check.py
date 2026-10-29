"""Event rich-results audit does not need a GSC paste."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sailingsa.tools.gsc_daily.rich_results import (
    audit_html,
    classify_event,
    events_from_html,
    from_audit_rows,
    issues_from_inspect,
    render_lines,
)


GOOD = """
<script type="application/ld+json">{"@context":"https://schema.org","@type":"SportsEvent","name":"Cape Classic","startDate":"2026-09-12","endDate":"2026-09-13","eventStatus":"https://schema.org/EventScheduled","description":"Cape Classic","location":{"@type":"Place","name":"ZVYC","address":{"@type":"PostalAddress","addressCountry":"ZA"}},"organizer":{"@type":"Organization","name":"ZVYC","url":"https://sailingsa.co.za/club/zvyc"}}</script>
"""

NESTED = """
<script type="application/ld+json">{"@type":"SportsEvent","name":"Cape Classic","startDate":"2026-09-12","location":{"@type":"Place","name":"ZVYC","address":{"@type":"PostalAddress","addressCountry":"ZA"}},"superEvent":{"@type":"SportsEvent","name":"ZVYC Cape Classic","url":"https://sailingsa.co.za/yearly-events"}}</script>
"""

CLASS_PAGE = """
<script type="application/ld+json">{"@type":"SportsEvent","name":"Cape Classic","startDate":"2026-09-12","eventStatus":"https://schema.org/EventScheduled"}</script>
<a href="/regatta/2026-09-13-zvyc-cape-classic/class-420">420</a>
"""


def test_nested_superevent_is_a_second_event_error():
    evs = events_from_html(NESTED)
    assert len(evs) == 2
    bad = [e for e in evs if e.get("name") == "ZVYC Cape Classic"][0]
    fields = {i["field"] for i in classify_event(bad) if i["severity"] == "ERROR"}
    assert "startDate" in fields
    assert "location" in fields


def test_class_page_missing_location():
    row = audit_html("https://sailingsa.co.za/regatta/x/class-420", CLASS_PAGE)
    assert row["n_event"] == 1
    assert any(i["field"] == "location" for i in row["errors"])
    assert row["class_hrefs"] == ["/regatta/2026-09-13-zvyc-cape-classic/class-420"]


def test_good_event_has_no_errors():
    row = audit_html("https://sailingsa.co.za/regatta/x", GOOD)
    assert row["errors"] == []


def test_inspect_parser_and_report_lines():
    inspect = {
        "richResultsResult": {
            "verdict": "FAIL",
            "detectedItems": [
                {
                    "richResultType": "Events",
                    "items": [
                        {
                            "name": "ZVYC Cape Classic",
                            "issues": [
                                {
                                    "issueMessage": 'Missing field "location"',
                                    "severity": "ERROR",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    }
    rows = issues_from_inspect(inspect)
    assert rows[0]["severity"] == "ERROR"
    payload = from_audit_rows(
        [audit_html("https://sailingsa.co.za/regatta/x", GOOD)],
        {"https://sailingsa.co.za/regatta/x": inspect},
    )
    text = "\n".join(render_lines(payload))
    assert "do not paste GSC" in text.lower() or "pulled here" in text.lower()
    assert payload["gsc"]["event_error_urls"] == 1


if __name__ == "__main__":
    test_nested_superevent_is_a_second_event_error()
    test_class_page_missing_location()
    test_good_event_has_no_errors()
    test_inspect_parser_and_report_lines()
    print("ok")
