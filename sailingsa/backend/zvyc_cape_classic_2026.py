"""This URL only: add the default .site-header above the standard event-results page.

Event header is serve_regatta_standalone — do not change it.
"""

SLUG = "2026-09-13-zvyc-cape-classic"

# Default site header markup from live header.html (hub .site-header). Not the event .header.
_SITE_HEADER = """<header class="site-header">
        <div class="container">
            <a href="/" class="logo js-go-home" id="headerLogoLink" title="Home – clear search and return to sailingsa.co.za">
                <img src="/assets/logos/sailingsa-logo.png" alt="SailingSA Logo">
            </a>
            <div class="header-user-center" id="headerUserCenter"></div>
            <div class="header-auth" id="headerAuth">
                <div id="loggedInStatus" style="display: none;"></div>
                <div id="loginBox" style="display: none;"></div>
            </div>
        </div>
    </header>"""

_SITE_HEADER_ASSETS = (
    '<link rel="stylesheet" href="/css/main.css">'
)

_SITE_HEADER_JS = (
    '<script src="/js/config.js"></script>'
    '<script src="/js/api.js?v=20260717regatta"></script>'
    '<script src="/js/session.js?v=20260806_PURE_CSS_GRID_ZERO_NUDGE"></script>'
)


def add_default_site_header(html: str) -> str:
    """Prepend default site-header. Do not alter .regatta-header-wrap / .header."""
    if "id=\"headerLogoLink\"" in html or "id='headerLogoLink'" in html:
        return html
    if "</head>" in html and "/css/main.css" not in html:
        html = html.replace("</head>", _SITE_HEADER_ASSETS + "</head>", 1)
    if "<body>" in html:
        html = html.replace("<body>", "<body>" + _SITE_HEADER, 1)
    elif "<body " in html:
        i = html.find("<body")
        j = html.find(">", i)
        html = html[: j + 1] + _SITE_HEADER + html[j + 1 :]
    if "</body>" in html and "session.js" not in html:
        html = html.replace("</body>", _SITE_HEADER_JS + "</body>", 1)
    return html
