"""Gold-header /regattas and /sailors directory pages — card list + fuzzy search (landing-style)."""

# Insert these functions into api.py (after _directory_page_html, before route handlers).


def _directory_gold_page_response(title: str, inner: str, extra_head: str):
    """Return HTMLResponse with gold header when available."""
    gold_fn = globals().get("_html_with_gold_header")
    if gold_fn:
        return gold_fn(title, inner, extra_head)
    return HTMLResponse(
        "<!DOCTYPE html><html lang=\"en-US\"><head><meta charset=\"UTF-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\">"
        f"<title>{html_module.escape(title)}</title>{extra_head}</head><body>{inner}</body></html>"
    )


_DIRECTORY_PAGE_ABOUT_CSS = """
.page-about-block{margin:0 0 1rem 0;padding:0.85rem 1rem;border:1px solid #dbe5ef;border-radius:8px;background:#f8fbff;color:#1e293b;line-height:1.45;font-size:0.95rem;}
.directory-results-label{margin:0 0 0.75rem 0;font-size:1.1rem;font-weight:700;color:#001f3f;}
#regattas-dashboard,#sailors-dashboard{padding-top:1rem;box-sizing:border-box;}
@media (min-width:640px){#regattas-dashboard,#sailors-dashboard{padding-top:1.25rem;}}
#public-regattas-list .sa-home-regatta-wrap{margin:0;}
.sailor-directory-hint{color:#64748b;font-size:0.95rem;margin:0.5rem 0 0;}
.sailor-directory-results{margin-top:0.5rem;display:flex;flex-direction:column;gap:0.75rem;padding-bottom:2.5rem;}
.sailor-directory-results .ssa-dev1-inject{margin:0 0 8px 0;max-width:100%;}
.sailor-directory-results .ssa-dev1-inject main,.sailor-directory-results .ssa-dev1-inject .main-column,.sailor-directory-results .ssa-dev1-inject .container{width:100%!important;max-width:100%!important;margin:0!important;padding:0!important;}
.sailor-directory-results .ssa-dev1-inject .sa-approved-sailor-card{margin-top:0;}
.sailor-directory-results .profile-card{margin:0;}
.sailor-directory-results .sa-claim-slot,.sailor-directory-results .sa-claim-banner,.sailor-directory-results .sailor-claim-cta,.sailor-directory-results #dev1-claim-slot,.sailor-directory-results #dev1-claim-banner{display:none!important;}
"""


def _regattas_directory_page_html():
    about = (
        "Explore South African sailing regattas with full race results, rankings, and performance history. "
        "Search by event name, host club, class, or year — same card list as the home page."
    )
    extra_head = (
        '<link rel="canonical" href="https://sailingsa.co.za/regattas">'
        '<link rel="stylesheet" href="/css/gold-list-tables.css?v=20260723m5">'
        "<style>"
        + _SECTION_HEADING_ROW_UNIFIED_CSS
        + _EVENTS_TOOLBAR_SEARCH_CSS
        + _DIRECTORY_PAGE_ABOUT_CSS
        + "</style>"
        '<script src="/js/config.js"></script>'
        '<script src="/js/api.js?v=20260717regatta"></script>'
        '<script src="/js/hub-regatta-list.js?v=20260823dir1"></script>'
    )
    inner = (
        '<div class="container" id="regattas-dashboard">'
        '<div class="card stats-section">'
        + _events_section_heading_row_html("Regattas")
        + f'<div class="page-about-block">{html_module.escape(about)}</div>'
        + '<section id="public-regattas-section" aria-label="Regatta list">'
        + '<div id="public-regattas-list"><p>Loading regattas…</p></div>'
        + "</section>"
        + "</div></div>"
        + _seo_discovery_block_html()
        + """
<footer class="site-footer-about" style="text-align:center;padding:2rem 1rem;font-size:0.9rem;color:#666;border-top:1px solid #e0e0e0;margin-top:2rem;">SailingSA – South African Sailing Results Database © <span id="year"></span></footer>
<script>document.getElementById("year").textContent=new Date().getFullYear();</script>
<script>
(function(){
  window.searchMode = "regatta";
  window.__ssaDirectoryRegattas = true;
  var inp = document.getElementById("events-dashboard-search");
  if (inp) {
    inp.setAttribute("placeholder", "Search regattas…");
    inp.setAttribute("aria-label", "Search regattas");
    var deb = null;
    inp.addEventListener("input", function() {
      clearTimeout(deb);
      deb = setTimeout(function() {
        if (typeof window.applyRegattaFilter === "function") window.applyRegattaFilter();
      }, 220);
    });
  }
  if (typeof window.applyRegattaFilter === "function") window.applyRegattaFilter();
})();
</script>"""
    )
    return (extra_head, inner)


def _sailors_directory_page_html():
    about = (
        "Search all South African sailors with complete regatta results, rankings, and performance history. "
        "SailingSA is the most comprehensive South African sailing results database for sailors."
    )
    extra_head = (
        '<link rel="canonical" href="https://sailingsa.co.za/sailors">'
        "<style>"
        + _SECTION_HEADING_ROW_UNIFIED_CSS
        + _EVENTS_TOOLBAR_SEARCH_CSS
        + _DIRECTORY_PAGE_ABOUT_CSS
        + ".profile-card{background:#fff;border-radius:8px;border:2px solid #001f3f;padding:0.5rem 0.85rem;cursor:pointer;line-height:1.35;}"
        + "</style>"
        '<script src="/js/hub-sailor-directory.js?v=20260823dir1"></script>'
    )
    inner = (
        '<div class="container" id="sailors-dashboard">'
        '<div class="card stats-section">'
        + _events_section_heading_row_html("Sailors")
        + f'<div class="page-about-block">{html_module.escape(about)}</div>'
        + '<p class="sailor-directory-hint" id="sailors-hint">Type at least 2 characters to search sailors by name, SA ID, club, or class.</p>'
        + '<div class="sailor-directory-results sailor-search-results" id="sailor-directory-results" role="list"></div>'
        + "</div></div>"
        + _seo_discovery_block_html()
        + """
<footer class="site-footer-about" style="text-align:center;padding:2rem 1rem;font-size:0.9rem;color:#666;border-top:1px solid #e0e0e0;margin-top:2rem;">SailingSA – South African Sailing Results Database © <span id="year"></span></footer>
<script>document.getElementById("year").textContent=new Date().getFullYear();</script>"""
    )
    return (extra_head, inner)
