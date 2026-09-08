"""This URL only: /regatta/2026-09-13-zvyc-cape-classic

1. Gold SailingSA header (live header.html via _html_with_gold_header)
2. Event header below it
No results table.
"""

TITLE = "ZVYC Cape Classic"
CANONICAL = "https://sailingsa.co.za/regatta/2026-09-13-zvyc-cape-classic"
DETAILS = "https://www.revolutionise.com.au/zeekoevleiyc/events/375411"


def zvyc_cape_classic_2026_extra_head() -> str:
    return (
        f'<link rel="canonical" href="{CANONICAL}">'
        '<meta name="description" content="ZVYC Cape Classic, 12–13 September 2026 at Zeekoe Vlei Yacht Club.">'
        '<link rel="stylesheet" href="/css/gold-list-tables.css?v=20260723m5">'
    )


def zvyc_cape_classic_2026_body() -> str:
    return (
        '<div class="container">'
        '<div class="card home-intro-box">'
        f"<h1>{TITLE}</h1>"
        "<p>12–13 September 2026 · Zeekoe Vlei Yacht Club</p>"
        '<p>Host: <a href="/club/zvyc">ZVYC - Zeekoe Vlei Yacht Club</a></p>'
        f'<p><a href="{DETAILS}" target="_blank" rel="noopener">Event notice</a></p>'
        "</div></div>"
    )
