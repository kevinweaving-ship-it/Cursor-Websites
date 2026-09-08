"""Default site header on results URLs. Event header is serve_regatta_standalone — do not change it.

Uses live header.html .site-header + session.js Sign Up / Login. No custom header.
"""

from __future__ import annotations

import re
from pathlib import Path

SLUG = "2026-09-13-zvyc-cape-classic"

# Exact hub markup from live /var/www/sailingsa/header.html. Absolute logo path
# (results URLs have no <base href="/">).
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

# Same scripts + boot as live header.html (session.js paints Sign Up + Login).
_SITE_HEADER_JS = (
    '<script src="/js/config.js"></script>'
    '<script src="/js/api.js?v=20260717regatta"></script>'
    '<script src="/js/session.js?v=20260806_PURE_CSS_GRID_ZERO_NUDGE"></script>'
    '<script id="ssa-default-site-header-boot">'
    "(function(){function boot(){try{if(typeof updateHeaderAuthStatus===\"function\")"
    "updateHeaderAuthStatus();}catch(e){}}"
    'if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot,{once:true});'
    "else setTimeout(boot,0);})();"
    "</script>"
)

# Verbatim lock from live header.html (navy 80px bar, logo left, auth right, 92px push).
_FALLBACK_SITE_HEADER_CSS = """
:root { --sa-header-h: 80px; --sa-header-gap: 12px; --sa-header-push: calc(var(--sa-header-h) + var(--sa-header-gap)); }
.site-header,
header.site-header,
header[class*="site-header"] {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  width: 100% !important;
  height: var(--sa-header-h) !important;
  min-height: var(--sa-header-h) !important;
  max-height: var(--sa-header-h) !important;
  z-index: 2147483647 !important;
  margin: 0 !important;
  padding: 0 !important;
  background: #001f3f;
  border: 0 !important;
  box-sizing: border-box !important;
  overflow: visible !important;
}
.site-header > .container,
header.site-header > .container,
.site-header .container,
header.site-header .container {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  width: 100% !important;
  height: var(--sa-header-h) !important;
  min-height: var(--sa-header-h) !important;
  max-height: var(--sa-header-h) !important;
  max-width: 1200px !important;
  margin: 0 auto !important;
  padding: 0 16px !important;
  box-sizing: border-box !important;
}
.site-header .logo,
header.site-header .logo {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  height: 80px !important;
  margin: 0 !important;
  padding: 0 !important;
  text-decoration: none !important;
}
.site-header .logo img,
header.site-header .logo img {
  display: block !important;
  max-width: 220px !important;
  width: auto !important;
  height: 76px !important;
  min-height: 76px !important;
  max-height: 76px !important;
  margin: 0 !important;
  padding: 0 !important;
  object-fit: contain !important;
}
.header-auth {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-end !important;
  margin: 0 !important;
  padding: 0 !important;
  height: 80px !important;
}
body::before {
  content: '' !important;
  display: block !important;
  width: 100% !important;
  height: var(--sa-header-push) !important;
  min-height: var(--sa-header-push) !important;
  max-height: var(--sa-header-push) !important;
  margin: 0 !important;
  padding: 0 !important;
  background: transparent !important;
  pointer-events: none !important;
  box-sizing: border-box !important;
}
"""


def _header_html_paths() -> list[Path]:
    return [
        Path("/var/www/sailingsa/header.html"),
        Path("/var/www/html/header.html"),
    ]


def _extract_site_header_css(header_html: str) -> str:
    """Keep only default-header rules from header.html. Never .header event rules."""
    kept: list[str] = []
    for css in re.findall(r"<style[^>]*>(.*?)</style>", header_html, flags=re.S | re.I):
        i = 0
        while True:
            b = css.find("{", i)
            if b < 0:
                break
            sel = css[i:b]
            depth = 1
            j = b + 1
            while j < len(css) and depth:
                if css[j] == "{":
                    depth += 1
                elif css[j] == "}":
                    depth -= 1
                j += 1
            blob = css[i:j]
            low = sel.lower()
            if (
                "site-header" in low
                or "--sa-header" in blob
                or "header-user-center" in low
                or re.search(r"(^|[,\s])\.header-auth(\s|,|:|$)", low)
            ):
                kept.append(blob.strip())
            i = j
    return "\n".join(kept)


def _site_header_css() -> str:
    for path in _header_html_paths():
        try:
            if path.is_file():
                extracted = _extract_site_header_css(
                    path.read_text(encoding="utf-8", errors="replace")
                )
                if "site-header" in extracted and "--sa-header-h" in extracted:
                    return extracted
        except OSError:
            continue
    return _FALLBACK_SITE_HEADER_CSS


def add_default_site_header(html: str) -> str:
    """Prepend default site-header. Do not alter .regatta-header-wrap / .header."""
    if not html:
        return html
    css = (
        '<link rel="stylesheet" href="/css/main.css">'
        if "/css/main.css" not in html
        else ""
    )
    if 'id="ssa-default-site-header-css"' not in html:
        css += (
            '<style id="ssa-default-site-header-css">'
            + _site_header_css()
            + "</style>"
        )
    if css and "</head>" in html:
        html = html.replace("</head>", css + "</head>", 1)
    if 'id="headerLogoLink"' not in html and "id='headerLogoLink'" not in html:
        if "<body>" in html:
            html = html.replace("<body>", "<body>" + _SITE_HEADER, 1)
        elif "<body " in html:
            i = html.find("<body")
            j = html.find(">", i)
            html = html[: j + 1] + _SITE_HEADER + html[j + 1 :]
    if 'id="ssa-default-site-header-boot"' not in html and "</body>" in html:
        html = html.replace("</body>", _SITE_HEADER_JS + "</body>", 1)
    return html
