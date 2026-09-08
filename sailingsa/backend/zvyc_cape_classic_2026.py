"""This URL only: /regatta/2026-09-13-zvyc-cape-classic

Gold SailingSA header, then the standard event header:
event logo left · details centred · host logo right.
No results table.
"""

TITLE = "ZVYC Cape Classic"
CANONICAL = "https://sailingsa.co.za/regatta/2026-09-13-zvyc-cape-classic"
EVENT_LOGO = "/artwork/Event%20Logo/Cape-Classic-Series.png"
HOST_LOGO = "/artwork/Club%20Logo/ZVYC.png"

# Header-only rules from live _RESULT_SHEET_CSS (event header std). No sheet/table CSS.
_EVENT_HEADER_CSS = """
.regatta-page{width:100%;max-width:100%;padding:16px;margin:0 auto;box-sizing:border-box}
.regatta-header-wrap{width:100%}
.header{display:grid;grid-template-columns:minmax(0,auto) minmax(0,3fr) minmax(0,auto);align-items:center;column-gap:6px;row-gap:4px;margin-bottom:30px;position:relative;border:2px solid #1a2750;border-radius:10px;padding:4px 6px;background:#ffffff;width:100%;box-sizing:border-box}
.regatta-header-logo-col{grid-column:1;grid-row:1;display:flex;align-items:center;justify-content:flex-start;min-width:0;padding:3px 8px 3px 3px}
.regatta-header-club-logo-col{grid-column:3;grid-row:1;display:flex;align-items:center;justify-content:flex-end;min-width:0;padding:3px 3px 3px 8px}
.regatta-header-logo-link{display:flex;align-items:center;justify-content:center;line-height:0;text-decoration:none;max-width:100%}
.regatta-header-logo-img{display:block;height:auto;max-height:min(24vw,104px);width:auto;max-width:min(54vw,320px);object-fit:contain}
.regatta-header-main-col{grid-column:2;grid-row:1;justify-self:center;align-self:center;text-align:center;width:100%;max-width:100%;min-width:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.regatta-name{font-size:24px;font-weight:bold;color:#1a2750;margin-bottom:8px;text-align:center}
.host-club{font-size:18px;color:#1a2750;margin-bottom:8px;text-align:center}
.host-club a{color:#1a2750;font-weight:600}
.status-line{font-size:14px;color:#1a2750;margin-top:8px;text-align:center}
@media (max-width:768px){
.regatta-page{padding:12px}
.regatta-name{font-size:18px}
.host-club{font-size:14px}
.status-line{font-size:12px}
.regatta-header-logo-img{max-height:min(20vw,88px);max-width:min(46vw,260px)}
}
"""


def zvyc_cape_classic_2026_extra_head() -> str:
    return (
        f'<link rel="canonical" href="{CANONICAL}">'
        '<meta name="description" content="ZVYC Cape Classic, 12–13 September 2026 at Zeekoe Vlei Yacht Club.">'
        f"<style>{_EVENT_HEADER_CSS}</style>"
    )


def zvyc_cape_classic_2026_body() -> str:
    return (
        '<div class="regatta-page">'
        '<div class="regatta-header-wrap">'
        '<div class="header">'
        '<div class="regatta-header-logo-col">'
        '<a href="/events" class="regatta-header-logo-link" title="Cape Classic Series">'
        f'<img src="{EVENT_LOGO}" alt="" class="regatta-header-logo-img" '
        'loading="lazy" decoding="async" />'
        "</a></div>"
        '<div class="regatta-header-main-col">'
        f'<div class="regatta-name">{TITLE}</div>'
        '<div class="host-club">Host: '
        '<a href="/club/zvyc">ZVYC - Zeekoe Vlei Yacht Club</a></div>'
        '<div class="status-line">12–13 September 2026</div>'
        "</div>"
        '<div class="regatta-header-club-logo-col">'
        '<a href="/club/zvyc" class="regatta-header-logo-link" title="Host club">'
        f'<img src="{HOST_LOGO}" alt="" class="regatta-header-logo-img regatta-header-club-logo-img" '
        'loading="lazy" decoding="async" />'
        "</a></div>"
        "</div></div></div>"
    )
