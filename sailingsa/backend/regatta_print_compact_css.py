"""Compact portrait print stylesheet for standalone /regatta result sheets.

Print test / example sheet:
https://sailingsa.co.za/regatta/2025-12-19-hyc-youth-nationals
(7 fleets, 12 races, Age + Crew — A4 landscape so the race grid fits, SA.)

Print and Save-as-PDF both use this CSS on the live HTML tables so sailor / club /
class / sail links stay real hyperlinks in the PDF (not a screenshot).

Pagination (A4):
- Page 1 always starts with the event header + first fleet.
- The next fleet stays on that page only if the whole fleet fits; otherwise it
  moves to the next page. Same rule for every following fleet.
- A fleet header must never sit on one page with its results table on the next.
- A fleet is never split across two pages. If it does not fit the leftover space,
  the whole fleet (header + table) moves to the next page. If it is taller than
  one A4 page, it is tightened so it still stays on a single page.
- Every page footer (one small line): event name + the results URL. The URL is a
  real link in Print-to-PDF; on paper it can be typed to open the same sheet.
- Print button offers Printer or PDF. Both publish the same standalone A4
  document (header + fleets + footer only). Layout does not follow the screen
  URL (mobile stack, live cards, site chrome).
- Page is A4 portrait or landscape automatically from table fit: each fleet's
  columns are given a minimum readable width (mm). If any fleet is wider than
  A4 portrait (194mm), the sheet is landscape; otherwise portrait.
"""

from pathlib import Path
import base64

_FONT_DIR = Path(__file__).resolve().parent / "fonts"


def _woff2_data_uri(name: str) -> str:
    raw = (_FONT_DIR / name).read_bytes()
    return "data:font/woff2;base64," + base64.b64encode(raw).decode("ascii")


def ibm_plex_print_font_css() -> str:
    """IBM Plex Sans (SIL OFL) — high x-height, tabular figures, Medium/Semibold at 6–8pt.

    Regular (400) looks thin at table size. Medium (500) is the body; Semibold (600)
    is headers. Bold (700) blobs at 5–6pt. Half-size superscript for DNC etc.
    """
    try:
        latin = _woff2_data_uri("IBMPlexSans-Var-Latin.woff2")
        latin_ext = _woff2_data_uri("IBMPlexSans-Var-LatinExt.woff2")
    except OSError:
        return ""
    return f"""
@font-face {{
  font-family: "IBM Plex Sans";
  font-style: normal;
  font-weight: 100 700;
  font-display: block;
  src: url({latin}) format("woff2");
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}}
@font-face {{
  font-family: "IBM Plex Sans";
  font-style: normal;
  font-weight: 100 700;
  font-display: block;
  src: url({latin_ext}) format("woff2");
  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF;
}}
""".strip()


IBM_PLEX_PRINT_FONT_CSS = ibm_plex_print_font_css()
_PRINT_SANS = (
    '"IBM Plex Sans", "Liberation Sans", "Noto Sans", "Segoe UI", '
    "Calibri, Arial, Helvetica, sans-serif"
)

PRINT_COMPACT_CSS = (
    IBM_PLEX_PRINT_FONT_CSS
    + """
@page { size: A4 portrait; margin: 8mm 9mm 14mm 8mm; }
.ssa-print-page-footer { display: none !important; }
html.ssa-printing .site-header, html.ssa-printing footer, html.ssa-printing .site-footer,
html.ssa-printing .app-footer, html.ssa-printing .action-buttons, html.ssa-printing .back-to-home,
html.ssa-printing .regatta-back-row, html.ssa-printing .regatta-source-banner,
html.ssa-printing .regatta-sa-mode-wrap, html.ssa-printing .regatta-live-wx,
html.ssa-printing .regatta-live-track, html.ssa-printing .regatta-live-clip,
html.ssa-printing .mm-lipton-reels, html.ssa-printing #mmLiptonReels,
html.ssa-printing .cape-crew { display: none !important; }
html.ssa-printing .header, html.ssa-printing .header.header--lipton {
  display: grid !important;
  grid-template-columns: auto minmax(0,1fr) auto !important;
  grid-template-rows: auto !important;
}
html.ssa-printing th.class-col, html.ssa-printing td.class-col { display: none !important; }
html.ssa-printing .fleet-results-table.rs-compact-row-logos th.class-col,
html.ssa-printing .fleet-results-table.rs-compact-row-logos td.class-col { display: table-cell !important; }
html.ssa-printing .ssa-print-page-footer { display: flex !important; position: static !important; margin-top: 8px !important; }
@media print {
  html, body { background: #fff !important; color: #1a2750 !important; margin: 0 !important; padding: 0 !important; }
  html, body, .regatta-page, .class-header, .sailed-line, table, th, td {
    font-family: """ + _PRINT_SANS + """ !important;
    font-variant-numeric: tabular-nums lining-nums !important;
    font-feature-settings: "tnum" 1, "lnum" 1 !important;
  }
  .site-header, footer, .site-footer, .app-footer, .action-buttons, .back-to-home,
  .regatta-back-row, .regatta-source-banner,
  .regatta-sa-mode-wrap, .regatta-wc-icons-row, .regatta-sa-columns-panel, .regatta-sa-hub-news-wrap,
  .mm-lipton-reels, #mmLiptonReels, .regatta-live-wx, .regatta-live-track, .regatta-live-clip,
  .cape-crew, .cape-crew-sa, .seo-discovery-block, .regatta-name-editor, .host-club-sa-edit-hit,
  .fleet-sa-edit-hit, .regatta-host-picker, .wc-late-entry-strip, .wc-entry-holds-panel,
  .wc-fleet-icons-toggle-row { display: none !important; }
  .regatta-name-view { display: block !important; }
  .host-club-wrap .host-club-public-nav, .fleet-title-public-nav { display: inline !important; }

  .regatta-page { max-width: none !important; width: 100% !important; padding: 0 !important; margin: 0 !important; display: block !important; }
  .regatta-header-wrap { width: 100% !important; margin: 0 !important; }

  /* Event header: left event logo | centre details | right host — same as the URL, not the stacked MP layout */
  .header, .header.header--lipton {
    display: grid !important;
    grid-template-columns: 72px minmax(0,1fr) 72px !important;
    grid-template-rows: auto !important;
    align-items: center !important;
    justify-items: stretch !important;
    column-gap: 6px !important;
    row-gap: 0 !important;
    padding: 3px 5px !important;
    margin: 0 0 6px 0 !important;
    border-width: 1.5px !important;
    border-radius: 6px !important;
    page-break-after: avoid;
    break-after: avoid-page;
  }
  .regatta-header-wrap {
    page-break-after: avoid;
    break-after: avoid-page;
  }
  .regatta-header-logo-col {
    display: flex !important;
    grid-column: 1 !important;
    grid-row: 1 !important;
    justify-content: flex-start !important;
    align-items: center !important;
    padding: 0 !important;
    width: 72px !important;
    min-width: 72px !important;
  }
  .regatta-header-main-col {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    grid-column: 2 !important;
    grid-row: 1 !important;
    justify-self: stretch !important;
    padding: 0 6px !important;
    width: 100% !important;
    text-align: center !important;
  }
  .regatta-header-club-logo-col {
    display: flex !important;
    grid-column: 3 !important;
    grid-row: 1 !important;
    justify-content: flex-end !important;
    align-items: center !important;
    padding: 0 !important;
    width: 72px !important;
    min-width: 72px !important;
  }
  .regatta-header-logo-img, .regatta-header-left-logo-img { max-height: 40px !important; max-width: 72px !important; height: auto !important; width: auto !important; }
  .regatta-header-club-logo-img { max-height: 40px !important; max-width: 72px !important; height: auto !important; width: auto !important; }
  .regatta-name { font-size: 11pt !important; line-height: 1.15 !important; margin: 0 0 1px 0 !important; text-align: center !important; width: 100% !important; }
  .host-club, .regatta-venue, .regatta-lipton-venue-line, .regatta-lipton-host-line { font-size: 8pt !important; line-height: 1.2 !important; margin: 0 0 1px 0 !important; text-align: center !important; width: 100% !important; }
  .status-line { font-size: 7.5pt !important; line-height: 1.2 !important; margin: 2px 0 0 0 !important; text-align: center !important; width: 100% !important; }
  .regatta-live-board-row { display: none !important; }

  /* Tight gap: main header → first fleet. Keep each fleet together so a
     leftover sliver never gets a header with the table on the next page.
     If the next fleet does not fit, the whole fleet moves to the next page. */
  .fleet-section {
    display: inline-block !important;
    width: 100% !important;
    margin-top: 6px !important;
    page-break-inside: avoid !important;
    break-inside: avoid-page !important;
    page-break-before: auto;
    break-before: auto;
  }
  .regatta-page > .fleet-section:first-of-type {
    margin-top: 6px !important;
    page-break-before: avoid !important;
    break-before: avoid-page !important;
  }
  .fleet-section.ssa-print-new-page {
    page-break-before: always !important;
    break-before: page !important;
  }
  .fleet-section tbody {
    page-break-inside: avoid !important;
    break-inside: avoid-page !important;
  }

  /* Fleet card: one centred line — small class chip (event-list size) + title + sailed */
  .class-header, .class-header--with-logos {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    grid-template-columns: none !important;
    grid-template-rows: none !important;
    align-items: center !important;
    justify-content: center !important;
    justify-items: center !important;
    column-gap: 6px !important;
    row-gap: 0 !important;
    gap: 6px !important;
    padding: 2px 6px !important;
    margin: 0 !important;
    border-width: 1.5px !important;
    border-radius: 6px !important;
    font-size: 9pt !important;
    page-break-after: avoid;
    break-after: avoid-page;
    page-break-inside: avoid;
    break-inside: avoid-page;
  }
  .class-header-logo-col { display: flex !important; grid-column: auto !important; grid-row: auto !important; justify-content: center !important; padding: 0 !important; min-width: 0 !important; }
  .class-header-logo-img, .class-header-class-icon-img {
    max-height: 22px !important;
    max-width: 48px !important;
    width: auto !important;
    height: auto !important;
    object-fit: contain !important;
  }
  .class-header-club-logo-col { display: none !important; }
  .class-header-main-col, .class-header-text-col {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    grid-column: auto !important;
    grid-row: auto !important;
    min-width: 0 !important;
    padding: 0 !important;
  }
  .fleet-title-row { font-size: 9pt !important; font-weight: 600 !important; margin: 0 !important; line-height: 1.15 !important; white-space: nowrap !important; }
  .sailed-line { font-size: 7pt !important; font-weight: 500 !important; margin: 0 !important; line-height: 1.2 !important; white-space: nowrap !important; }

  /* Cape Classic: one centred line [FleetLogo] Fleet; sailed stats centred under it. */
  .fleet-section:has(.rs-compact-row-logos) .class-header,
  .fleet-section:has(.rs-compact-row-logos) .class-header--with-logos {
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    gap: 2px !important;
    column-gap: 0 !important;
  }
  .fleet-section:has(.rs-compact-row-logos) .class-header-logo-col,
  .fleet-section:has(.rs-compact-row-logos) .class-header-club-logo-col {
    display: none !important;
  }
  .fleet-section:has(.rs-compact-row-logos) .class-header-main-col,
  .fleet-section:has(.rs-compact-row-logos) .class-header-text-col {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    width: 100% !important;
    text-align: center !important;
    gap: 2px !important;
  }
  .fleet-section:has(.rs-compact-row-logos) .fleet-title-row,
  .fleet-section:has(.rs-compact-row-logos) .fleet-title-with-logo {
    display: inline-flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 5px !important;
    text-align: center !important;
    white-space: nowrap !important;
  }
  .fleet-section:has(.rs-compact-row-logos) .rs-fleet-title-logo,
  .fleet-section:has(.rs-compact-row-logos) .fleet-title-with-logo .rs-fleet-title-logo {
    display: inline-block !important;
    max-height: 24px !important;
    max-width: 52px !important;
    width: auto !important;
    height: auto !important;
    object-fit: contain !important;
    vertical-align: middle !important;
  }
  .fleet-section:has(.rs-compact-row-logos) .sailed-line {
    display: block !important;
    width: 100% !important;
    text-align: center !important;
    margin: 1px 0 0 0 !important;
    font-weight: 500 !important;
  }

  /* Rank table: smaller type, full cell text (no clip). Class is already on
     the fleet card so that column is dropped to free width for helm + races. */
  html, body, body.ssa-print-doc, .regatta-page {
    overflow: visible !important;
    box-sizing: border-box !important;
  }
  .table-wrapper {
    overflow: visible !important;
    margin-top: 3px !important;
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
    padding-right: 1.4pt !important;
    page-break-before: avoid !important;
    break-before: avoid-page !important;
    page-break-inside: avoid !important;
    break-inside: avoid-page !important;
  }
  .table-wrapper table, table.fleet-results-table, .fleet-section .table-wrapper table.fleet-results-table {
    width: calc(100% - 1.6pt) !important;
    min-width: 0 !important;
    max-width: calc(100% - 1.6pt) !important;
    table-layout: fixed !important;
    border-collapse: collapse !important;
    box-sizing: border-box !important;
    border: 0.7pt solid #1a2750 !important;
    page-break-inside: avoid !important;
    break-inside: avoid-page !important;
  }
  th, td {
    padding: 1.5px 2px !important;
    font-size: 6pt !important;
    font-weight: 500 !important;
    line-height: 1.28 !important;
    white-space: nowrap !important;
    overflow: visible !important;
    letter-spacing: 0.01em !important;
    box-sizing: border-box !important;
    border: 0.5pt solid #1a2750 !important;
    background: #fff !important;
  }
  th {
    background: #e9eefb !important;
    font-weight: 600 !important;
    text-align: center !important;
  }
  td { text-align: center !important; }
  td.helm-col, th.helm-col, td.crew-col, th.crew-col { text-align: left !important; }
  tr.medal-gold td { background: #D4AF37 !important; }
  tr.medal-silver td { background: #D7D7D7 !important; }
  tr.medal-bronze td { background: #CE8946 !important; }
  html.ssa-print-landscape th, html.ssa-print-landscape td { font-size: 7pt !important; }
  html.ssa-print-landscape .race-col { font-size: 6.5pt !important; width: 4.15% !important; }
  html.ssa-print-landscape .helm-col { width: 17% !important; }
  html.ssa-print-landscape .fleet-section:has(th.crew-col) .helm-col { width: 13% !important; }
  html.ssa-print-landscape .fleet-section:has(th.crew-col) .race-col { width: 3.65% !important; }
  .fleet-results-table th.class-col, .fleet-results-table td.class-col,
  th.class-col, td.class-col { display: none !important; }
  /* Cape Classic compact sheets: Class column stays; logo stands in for the name. */
  .fleet-results-table.rs-compact-row-logos th.class-col,
  .fleet-results-table.rs-compact-row-logos td.class-col {
    display: table-cell !important;
    width: 5.6% !important;
    white-space: nowrap !important;
    overflow: visible !important;
    text-align: center !important;
  }
  .fleet-results-table.rs-compact-row-logos .club-col {
    width: 7.2% !important;
    white-space: nowrap !important;
    overflow: visible !important;
    text-align: left !important;
  }
  .rs-class-row-logo, .rs-club-row-logo-sm,
  .fleet-results-table .rs-class-row-logo,
  .fleet-results-table .rs-club-row-logo-sm {
    display: inline-block !important;
    height: auto !important;
    width: auto !important;
    max-height: 12px !important;
    max-width: 22px !important;
    object-fit: contain !important;
    vertical-align: middle !important;
    flex: 0 0 auto !important;
  }
  .rs-class-with-logo, .fleet-results-table.rs-compact-row-logos .rs-club-with-logo {
    display: inline-flex !important;
    align-items: center !important;
    gap: 2px !important;
    flex-wrap: nowrap !important;
  }
  .rank-col, .total-col, .nett-col { width: 3.3% !important; }
  .wc-meta-col { width: 3% !important; }
  .sail-col { width: 5.4% !important; }
  .club-col { width: 4.2% !important; }
  .helm-col { width: 16.5% !important; }
  th.crew-col, td.crew-col { width: 12.5% !important; }
  .fleet-section:has(th.crew-col) .helm-col { width: 12.5% !important; }
  .fleet-section:has(th.crew-col) .race-col { width: 3.35% !important; }
  .race-col {
    width: 3.85% !important;
    padding-left: 0.5px !important;
    padding-right: 0.5px !important;
    font-size: 6pt !important;
    letter-spacing: 0.01em !important;
  }
  .fleet-results-table .wc-score {
    font-size: 1em !important;
    font-weight: 500 !important;
  }
  .fleet-results-table .wc-code {
    font-size: 50% !important;
    font-weight: 600 !important;
    vertical-align: super !important;
    margin-left: 0.08em !important;
    line-height: 0 !important;
    letter-spacing: 0.02em !important;
    opacity: 1 !important;
  }
  .fleet-results-table tbody tr, .fleet-results-table tbody td,
  html.ssa-printing .fleet-results-table tbody tr, html.ssa-printing .fleet-results-table tbody td {
    height: auto !important;
    max-height: none !important;
    min-height: 0 !important;
    overflow: visible !important;
    font-size: 6pt !important;
    line-height: 1.28 !important;
  }
  .rs-club-row-logo, .rs-boat-sponsor-logo, .fleet-results-table .rs-club-row-logo,
  .fleet-results-table .rs-boat-sponsor-logo { display: none !important; }
  .rs-class-row-logo, .rs-club-row-logo-sm,
  .fleet-results-table .rs-class-row-logo,
  .fleet-results-table .rs-club-row-logo-sm {
    display: inline-block !important;
    height: auto !important;
    width: auto !important;
    max-height: 14px !important;
    max-width: 28px !important;
    object-fit: contain !important;
    vertical-align: middle !important;
    flex: 0 0 auto !important;
  }
  /* URL keeps a small title-row logo; print already has the large left logo. */
  .rs-fleet-title-logo, .fleet-title-with-logo .rs-fleet-title-logo {
    display: none !important;
  }
  .rs-club-with-logo, .rs-boat-name-sponsors { white-space: nowrap !important; }
  thead { display: table-header-group; }
  tbody { page-break-inside: avoid !important; break-inside: avoid-page !important; }
  tr { page-break-inside: avoid; break-inside: avoid; }
  .fleet-section.ssa-print-fit-1 th, .fleet-section.ssa-print-fit-1 td { font-size: 5.8pt !important; padding: 0 1px !important; line-height: 1.08 !important; }
  .fleet-section.ssa-print-fit-2 th, .fleet-section.ssa-print-fit-2 td { font-size: 5.2pt !important; padding: 0 !important; line-height: 1.05 !important; }
  .fleet-section.ssa-print-fit-3 th, .fleet-section.ssa-print-fit-3 td { font-size: 4.6pt !important; padding: 0 !important; line-height: 1.02 !important; }

  a, a:visited { color: #0000ee !important; text-decoration: underline !important; }
  html, body, .regatta-page {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  /* Small repeating footer: event name + URL on one line (clickable in PDF). */
  .ssa-print-page-footer {
    display: flex !important;
    position: fixed !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 2px 0 0 !important;
    border-top: 0.4pt solid #1a2750 !important;
    background: #fff !important;
    color: #1a2750 !important;
    font-size: 6.5pt !important;
    line-height: 1.2 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    align-items: baseline !important;
    gap: 6px !important;
    z-index: 9999 !important;
  }
  .ssa-print-footer-name { font-weight: 700 !important; flex: 0 0 auto !important; }
  .ssa-print-page-footer a, .ssa-print-page-footer a:visited {
    color: #0000ee !important;
    text-decoration: underline !important;
    font-weight: 400 !important;
    min-width: 0 !important;
    overflow: hidden !important;
  }
}
#ssaPrintChooser { display: none; position: fixed; inset: 0; z-index: 2147483000; align-items: flex-end; justify-content: center; background: rgba(0,31,63,.45); }
#ssaPrintChooser.is-open { display: flex; }
#ssaPrintChooser .card {
  max-width: 26rem; width: min(96%, 26rem); padding: 14px 14px 18px; margin: 0 0 18px;
  border-radius: 18px; box-shadow: 0 8px 28px rgba(0,31,63,.18);
}
#ssaPrintChooser .ssa-print-chooser-note { font-size: 12px; color: #1a2750; margin: 0 0 8px; line-height: 1.35; text-align: center; }
#ssaPrintChooser .ssa-pdf-frame { width: 100%; height: 42vh; border: 1px solid #1a2750; background: #e8e8ed; margin: 0; border-radius: 10px; overflow: auto; }
#ssaPdfView { min-height: 100%; padding: 8px; box-sizing: border-box; }
#ssaPdfView canvas, #ssaPdfView img.ssa-pdf-page {
  display: block; width: 100%; height: auto; margin: 0 0 8px; background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,.15);
}
#ssaPdfView .ssa-pdf-status { margin: 24px 12px; text-align: center; color: #1a2750; font-size: 13px; }
#ssaPrintChooser .ssa-print-chooser-actions {
  display: flex; gap: 6px; flex-wrap: nowrap; justify-content: space-between;
  align-items: flex-start; margin-top: 14px; padding: 0 2px;
}
#ssaPrintChooser .ssa-ios-share-item {
  display: flex; flex-direction: column; align-items: center; justify-content: flex-start;
  gap: 6px; min-width: 52px; min-height: 44px; padding: 0; margin: 0;
  border: 0; background: transparent; box-shadow: none; cursor: pointer;
  text-decoration: none; color: #1a2750; font: inherit; -webkit-tap-highlight-color: transparent;
}
#ssaPrintChooser .ssa-ios-share-icon {
  width: 56px; height: 56px; border-radius: 50%; display: inline-flex;
  align-items: center; justify-content: center; flex: 0 0 auto;
}
#ssaPrintChooser .ssa-ios-share-icon svg { width: 28px; height: 28px; display: block; }
#ssaPrintChooser .ssa-ios-share-icon--wa { background: #25D366; }
#ssaPrintChooser .ssa-ios-share-icon--mail { background: #007AFF; }
#ssaPrintChooser .ssa-ios-share-icon--down { background: #34C759; }
#ssaPrintChooser .ssa-ios-share-icon--print { background: #8E8E93; }
#ssaPrintChooser .ssa-ios-share-icon--close { background: #636366; }
#ssaPrintChooser .ssa-ios-share-label {
  font-size: 11px; font-weight: 500; line-height: 1.15; text-align: center;
  color: #1a2750; max-width: 64px;
}
#ssaPrintChooser a.ssa-ios-share-item { color: #1a2750; }
@media (min-width: 700px) {
  #ssaPrintChooser { align-items: center; }
  #ssaPrintChooser .card { max-width: 32rem; width: min(96%, 32rem); margin: 0; }
  #ssaPrintChooser .ssa-pdf-frame { height: 56vh; }
}
"""
).strip()

def _document_css() -> str:
    text = PRINT_COMPACT_CSS
    start = text.find("@media print {")
    end = text.find("\n#ssaPrintChooser")
    inner = text[start + len("@media print {") : end if end > 0 else None].rstrip()
    if inner.endswith("}"):
        inner = inner[: inner.rfind("}")].rstrip()
    return (
        IBM_PLEX_PRINT_FONT_CSS
        + "\n@page { size: A4 portrait; margin: 8mm 9mm 14mm 8mm; }\n"
        + inner
    )


PRINT_DOCUMENT_CSS = _document_css()

# Minimum readable print widths (mm) at ~6.5pt.
# Class is hidden on most sheets; Cape Classic compact tables keep it.
PRINT_COL_MIN_MM = {
    "class": 0,
    "race": 11,
    "helm": 30,
    "crew": 26,
    "sail": 12,
    "club": 11,
    "rank": 8,
    "total": 8,
    "nett": 8,
    "disc": 8,
    "boat": 22,
    "meta": 9,
}
PRINT_COL_OTHER_MM = 10
PRINT_A4_PORTRAIT_CONTENT_MM = 193  # 210mm minus 8mm left + 9mm right


def print_col_need_mm(kind: str) -> int:
    return PRINT_COL_MIN_MM.get(kind, PRINT_COL_OTHER_MM)


def print_table_need_mm(kinds: list) -> int:
    return sum(print_col_need_mm(k) for k in kinds)


def print_orientation_for_tables(tables: list) -> str:
    worst = max((print_table_need_mm(cols) for cols in tables), default=0)
    return "landscape" if worst > PRINT_A4_PORTRAIT_CONTENT_MM else "portrait"


def _print_orientation_js() -> str:
    need_js = "".join(f"if(kind==='{k}')return {mm};" for k, mm in PRINT_COL_MIN_MM.items())
    return (
        "function printHeaderKind(el){"
        "var c=el.className||'';"
        "if(/\\bclass-col\\b/.test(c))return 'class';"
        "if(/\\brace-col\\b/.test(c))return 'race';"
        "if(/\\bhelm-col\\b/.test(c))return 'helm';"
        "if(/\\bcrew-col\\b/.test(c))return 'crew';"
        "if(/\\bsail-col\\b/.test(c))return 'sail';"
        "if(/\\bclub-col\\b/.test(c))return 'club';"
        "if(/\\brank-col\\b/.test(c))return 'rank';"
        "if(/\\btotal-col\\b/.test(c))return 'total';"
        "if(/\\bnett-col\\b/.test(c))return 'nett';"
        "if(/\\bdisc-col\\b/.test(c))return 'disc';"
        "if(/\\bboat-name-col\\b/.test(c))return 'boat';"
        "if(/\\bwc-meta-col\\b/.test(c))return 'meta';"
        "var t=(el.textContent||'').replace(/\\s+/g,' ').trim().toLowerCase();"
        "if(t==='class')return 'class';"
        "if(/^r\\d+$/.test(t))return 'race';"
        "if(t==='helm')return 'helm';"
        "if(t==='crew')return 'crew';"
        "if(t==='sail no'||t==='sail'||t==='sailno')return 'sail';"
        "if(t==='club')return 'club';"
        "if(t==='rank')return 'rank';"
        "if(t==='total')return 'total';"
        "if(t==='nett')return 'nett';"
        "if(t==='disc'||t==='discard')return 'disc';"
        "if(t==='boat name'||t==='boat')return 'boat';"
        "if(t==='age'||t==='bow'||t==='bow no'||t==='jib'||t==='jib no'||t==='hull'||t==='hull no')return 'meta';"
        "return 'other';"
        "}"
        "function printColNeedMm(kind){"
        + need_js
        + f"return {PRINT_COL_OTHER_MM};"
        "}"
        "function printTableNeedMm(t){"
        "var need=0,cells=t.querySelectorAll('thead th');"
        "if(!cells.length)cells=t.querySelectorAll('tbody tr:first-child td');"
        "cells.forEach(function(el){need+=printColNeedMm(printHeaderKind(el));});"
        "return need;"
        "}"
        "function printOrientation(){"
        "var worst=0;"
        "document.querySelectorAll('.fleet-section table').forEach(function(t){"
        "var n=printTableNeedMm(t);if(n>worst)worst=n;"
        "});"
        f"return worst>{PRINT_A4_PORTRAIT_CONTENT_MM}?'landscape':'portrait';"
        "}"
    )


PRINT_PAGINATE_JS = (
    _print_orientation_js()
    + r"""
function pagePx(orient){var h=(orient==='landscape')?(210-8-14):(297-8-14);return h*96/25.4;}
function fleetH(el){
  var rows=el.querySelectorAll('table.fleet-results-table tbody tr').length;
  return 42+16+rows*13;
}
function clearPrintPages(){
  document.querySelectorAll('.fleet-section').forEach(function(el){
    el.classList.remove('ssa-print-new-page','ssa-print-fit-1','ssa-print-fit-2','ssa-print-fit-3');
  });
}
function keepFleetsOnOnePage(){
  clearPrintPages();
  var page=pagePx(printOrientation())-8;
  var used=document.querySelector('.regatta-header-wrap,.header')?58:0;
  document.querySelectorAll('.fleet-section').forEach(function(el,i){
    var h=fleetH(el);
    if(h>page){
      el.classList.add(h>page*1.35?'ssa-print-fit-3':h>page*1.15?'ssa-print-fit-2':'ssa-print-fit-1');
      h=page;
    }
    if(i===0){used+=h;return;}
    if(used+h>page){el.classList.add('ssa-print-new-page');used=h;}
    else used+=h;
  });
}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function eventName(){var n=document.querySelector('.regatta-name');return (n&&n.textContent||document.title||'').replace(/\\s*\\|\\s*SailingSA\\s*$/i,'').replace(/\\s+/g,' ').trim();}
function buildPrintDoc(){
  var name=eventName(),url=sheetUrl()||location.href,cssEl=document.getElementById('ssaPrintDocumentCss');
  var orient=printOrientation();
  var css=cssEl?cssEl.textContent:'';
  css=css.replace('A4 portrait','A4 '+orient);
  var chunks=[],hdr=document.querySelector('.regatta-header-wrap');
  if(hdr){var h=hdr.cloneNode(true);h.querySelectorAll('.regatta-back-row,.back-to-home,.regatta-sa-mode-wrap,.regatta-live-board-row,.regatta-name-editor,.regatta-sa-hub-news-wrap').forEach(function(n){n.remove();});chunks.push(h.outerHTML);}
  document.querySelectorAll('.regatta-page > .fleet-section').forEach(function(sec){
    if(sec.classList.contains('cape-crew'))return;
    var c=sec.cloneNode(true);
    c.querySelectorAll('script,.fleet-sa-edit-hit,.wc-sa-ac-wrap,.wc-rank-action-pop,.regatta-sa-columns-panel,.wc-late-entry-strip').forEach(function(n){n.remove();});
    chunks.push(c.outerHTML);
  });
  chunks.push('<div class=\"ssa-print-page-footer\"><span class=\"ssa-print-footer-name\">'+esc(name)+'</span><a class=\"ssa-print-footer-url\" href=\"'+esc(url)+'\">'+esc(url)+'</a></div>');
  return '<!DOCTYPE html><html class=\"ssa-print-'+orient+'\" data-ssa-print-orient=\"'+orient+'\"><head><meta charset=\"UTF-8\"><base href=\"'+esc(location.origin)+'/\"><title>'+esc(name)+'</title><style>'+css+'</style></head><body class=\"ssa-print-doc\">'+chunks.join('')+'</body></html>';
}
function paginatePrintDoc(doc){
  var orient=(doc.documentElement.getAttribute('data-ssa-print-orient')||'portrait');
  var page=pagePx(orient)-8,used=58;
  doc.querySelectorAll('.fleet-section').forEach(function(el,i){
    var h=fleetH(el);
    if(h>page){el.classList.add('ssa-print-fit-1');h=page;}
    if(i===0){used+=h;return;}
    if(used+h>page){el.classList.add('ssa-print-new-page');used=h;}else used+=h;
  });
}
function openPrintSheet(){
  var w=window.open('', 'ssaRegattaPrint');
  if(!w){window.print();return;}
  w.document.open();w.document.write(buildPrintDoc());w.document.close();
  function go(){try{paginatePrintDoc(w.document);}catch(e){}w.focus();w.print();}
  var imgs=[].slice.call(w.document.images||[]),left=0;
  imgs.forEach(function(im){if(!im.complete){left+=1;im.onload=im.onerror=function(){left-=1;if(left<=0)go();};}});
  if(!left)setTimeout(go,200);else setTimeout(go,1500);
}
function openChooser(){var el=document.getElementById('ssaPrintChooser');if(el)el.classList.add('is-open');}
function closeChooser(){var el=document.getElementById('ssaPrintChooser');if(el)el.classList.remove('is-open');}
window.ssaRegattaPrint=openChooser;
window.ssaRegattaPrintSheet=openPrintSheet;
document.addEventListener('click',function(ev){
  var t=ev.target;if(!t||!t.getAttribute)return;
  var act=t.getAttribute('data-ssa-print');
  if(act==='printer'||act==='pdf'){ev.preventDefault();closeChooser();openPrintSheet();return;}
  if(act==='cancel'||(t.id==='ssaPrintChooser'&&t.classList.contains('is-open')))closeChooser();
});
""".replace("\n", "")
)


_PDF_SHARE_JS = r"""
var _pdfFile=null,_pdfWarm=null,_pdfJsWarm=null;
function sheetUrl(){
  var c=document.querySelector('link[rel="canonical"]');
  if(c&&c.href&&c.href.indexOf('http')===0)return c.href.split('#')[0].split('?')[0];
  var u=(location.href||'').split('#')[0].split('?')[0];
  if(u.indexOf('http')===0)return u;
  var p=location.pathname||'';
  if(p.indexOf('/regatta/')===0)return 'https://sailingsa.co.za'+p.replace(/\/+$/,'');
  return '';
}
function pdfPath(){
  var p=(location.pathname||'').replace(/\/+$/,'');
  if(p.indexOf('/regatta/')!==0)return '';
  if(/\/results\.pdf$/i.test(p))return p;
  return p+'/results.pdf';
}
function pdfAbs(){
  var p=pdfPath();if(!p)return '';
  if(p.indexOf('http')===0)return p;
  return (location.origin||'https://sailingsa.co.za')+p;
}
function pdfTitle(){
  var n=document.querySelector('.regatta-name');
  var t=(n&&n.textContent||document.title||'SailingSA results').replace(/\s*\|\s*SailingSA\s*$/i,'').replace(/\s+/g,' ').trim();
  return t||'SailingSA results PDF';
}
function pdfFileName(){
  var p=pdfPath().replace(/\/+$/,'').replace(/\/results\.pdf$/i,'');
  var tail=(p.split('/').filter(Boolean).pop()||'results').replace(/\.pdf$/i,'');
  return tail+'.pdf';
}
function setPdfStatus(msg){
  var host=document.getElementById('ssaPdfView');if(!host)return;
  host.innerHTML='<p class="ssa-pdf-status"></p>';
  host.firstChild.textContent=msg||'Loading PDF\u2026';
}
function loadPdfFile(){
  var u=pdfAbs();
  if(!u)return Promise.reject(new Error('no-pdf'));
  return fetch(u,{credentials:'same-origin',cache:'no-store'}).then(function(r){
    if(!r.ok)throw new Error('pdf');
    return r.blob();
  }).then(function(blob){
    var file=new File([blob],pdfFileName(),{type:'application/pdf'});
    _pdfFile=file;
    return file;
  });
}
function warmPdf(){
  if(!_pdfWarm)_pdfWarm=loadPdfFile().catch(function(err){_pdfWarm=null;throw err;});
  return _pdfWarm;
}
function withPdfFile(fn){
  if(_pdfFile)return Promise.resolve(fn(_pdfFile));
  return warmPdf().then(fn);
}
function loadPdfJs(){
  if(window.pdfjsLib)return Promise.resolve(window.pdfjsLib);
  if(_pdfJsWarm)return _pdfJsWarm;
  _pdfJsWarm=new Promise(function(res,rej){
    var s=document.createElement('script');
    s.src=(location.origin||'')+'/js/vendor/pdfjs/pdf.min.js';
    s.onload=function(){
      try{
        if(window.pdfjsLib&&pdfjsLib.GlobalWorkerOptions){
          pdfjsLib.GlobalWorkerOptions.workerSrc=(location.origin||'')+'/js/vendor/pdfjs/pdf.min.js';
        }
      }catch(e){}
      res(window.pdfjsLib);
    };
    s.onerror=function(){ _pdfJsWarm=null; rej(new Error('pdfjs')); };
    document.head.appendChild(s);
  });
  return _pdfJsWarm;
}
function renderPdfPreview(file){
  var host=document.getElementById('ssaPdfView');if(!host||!file)return Promise.reject(new Error('view'));
  setPdfStatus('Opening PDF\u2026');
  return file.arrayBuffer().then(function(buf){
    return loadPdfJs().then(function(pdfjs){
      if(!pdfjs||!pdfjs.getDocument)throw new Error('pdfjs');
      return pdfjs.getDocument({data:buf,disableWorker:true}).promise;
    }).then(function(pdf){
      host.innerHTML='';
      var scale=Math.max(1.15, (host.clientWidth||480)/612);
      var chain=Promise.resolve();
      for(var n=1;n<=pdf.numPages;n++){
        (function(pageNo){
          chain=chain.then(function(){return pdf.getPage(pageNo);}).then(function(page){
            var vp=page.getViewport({scale:scale});
            var canvas=document.createElement('canvas');
            canvas.width=vp.width;canvas.height=vp.height;
            canvas.setAttribute('aria-label','PDF page '+pageNo);
            host.appendChild(canvas);
            return page.render({canvasContext:canvas.getContext('2d'),viewport:vp}).promise;
          });
        })(n);
      }
      return chain;
    });
  });
}
function sharePdfFile(file){
  if(!file||!navigator.share)return Promise.reject(new Error('no-share'));
  var payload={files:[file],title:pdfTitle()};
  if(navigator.canShare&&!navigator.canShare(payload))return Promise.reject(new Error('no-files'));
  return navigator.share(payload);
}
function downloadPdfFile(file){
  if(!file)return;
  var url=URL.createObjectURL(file);
  var a=document.createElement('a');
  a.href=url;a.download=pdfFileName();a.rel='noopener';
  document.body.appendChild(a);a.click();a.remove();
  setTimeout(function(){URL.revokeObjectURL(url);},2500);
}
function sharePdfAttach(){
  withPdfFile(function(file){
    return sharePdfFile(file).catch(function(){downloadPdfFile(file);});
  }).catch(function(){downloadPdfAttach();});
}
function downloadPdfAttach(){
  withPdfFile(function(file){downloadPdfFile(file);}).catch(function(){
    var u=pdfAbs();if(!u)return;
    var a=document.createElement('a');
    a.href=u+(u.indexOf('?')>=0?'&':'?')+'download=1';
    a.download=pdfFileName();a.rel='noopener';
    document.body.appendChild(a);a.click();a.remove();
  });
}
function printPdfFromCanvases(){
  var host=document.getElementById('ssaPdfView');
  var canv=host?host.querySelectorAll('canvas'):[];
  if(!canv.length)return false;
  var w=window.open('', 'ssaPdfPrint');
  if(!w)return false;
  w.document.open();
  w.document.write('<!DOCTYPE html><html><head><meta charset="UTF-8"><title>'+
    String(pdfTitle()).replace(/[<>&]/g,'')+
    '</title><style>@page{size:A4;margin:0}html,body{margin:0;background:#fff}img{display:block;width:100%;page-break-after:always}</style></head><body></body></html>');
  w.document.close();
  Array.prototype.forEach.call(canv,function(c){
    var img=w.document.createElement('img');
    img.src=c.toDataURL('image/png');
    w.document.body.appendChild(img);
  });
  setTimeout(function(){try{w.focus();w.print();}catch(e){}},400);
  return true;
}
function printPdf(){
  withPdfFile(function(file){
    var url=URL.createObjectURL(file);
    var fr=document.getElementById('ssaPdfPrintFrame');
    if(!fr){
      fr=document.createElement('iframe');
      fr.id='ssaPdfPrintFrame';
      fr.setAttribute('title','Print PDF');
      fr.style.cssText='position:fixed;right:0;bottom:0;width:1px;height:1px;opacity:0;border:0';
      document.body.appendChild(fr);
    }
    var printed=false;
    var fallback=setTimeout(function(){
      if(printed)return;
      if(!printPdfFromCanvases())window.open(url,'_blank','noopener');
    },1400);
    fr.onload=function(){
      printed=true;clearTimeout(fallback);
      try{fr.contentWindow.focus();fr.contentWindow.print();}catch(e){
        if(!printPdfFromCanvases())window.open(url,'_blank','noopener');
      }
    };
    fr.src=url;
  }).catch(function(){
    if(!printPdfFromCanvases()){
      var u=pdfAbs();if(u)window.open(u,'_blank','noopener');
    }
  });
}
function shareEventUrl(){
  var t=pdfTitle(),u=sheetUrl()||location.href,b=document.getElementById('regattaShareBtn');
  function copied(){if(b){var old=b.textContent;b.textContent='URL copied';setTimeout(function(){b.textContent=old||'Share URL';},1600);}}
  if(navigator.share){navigator.share({title:t,url:u}).catch(function(){});return;}
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(u).then(copied).catch(function(){prompt('Copy this URL:',u);});
    return;
  }
  prompt('Copy this URL:',u);
}
function openChooser(){
  var el=document.getElementById('ssaPrintChooser');if(!el)return;
  if(!pdfPath())return;
  var dl=document.getElementById('ssaPdfDownload');
  if(dl){dl.setAttribute('href',pdfPath()+'?download=1');dl.setAttribute('download',pdfFileName());}
  setPdfStatus('Loading PDF\u2026');
  el.classList.add('is-open');
  withPdfFile(function(file){
    return renderPdfPreview(file).catch(function(){
      setPdfStatus('PDF is ready. Use Download or Print if the preview cannot open in this browser.');
    });
  }).catch(function(){setPdfStatus('Could not load the PDF file.');});
}
function closeChooser(){var el=document.getElementById('ssaPrintChooser');if(el)el.classList.remove('is-open');}
window.ssaRegattaPrint=openChooser;
document.addEventListener('click',function(ev){
  var t=ev.target;
  if(t&&t.id==='ssaPrintChooser'){closeChooser();return;}
  var hit=t&&t.closest?t.closest('[data-ssa-print]'):null;
  if(!hit)return;
  var act=hit.getAttribute('data-ssa-print');
  if(act==='whatsapp'||act==='email'){ev.preventDefault();sharePdfAttach();return;}
  if(act==='download'){ev.preventDefault();downloadPdfAttach();return;}
  if(act==='printer'){ev.preventDefault();printPdf();return;}
  if(act==='cancel'){ev.preventDefault();closeChooser();}
});
var b=document.getElementById('regattaShareBtn');
if(b)b.addEventListener('click',function(){shareEventUrl();});
warmPdf();
""".replace("\n", "")


def _ios_share_svg(name: str) -> str:
    icons = {
        "wa": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M12.04 2c-5.46 0-9.91 4.4-9.91 9.83 0 1.73.46 3.43 1.33 4.93L2 22l5.39-1.41A10 10 0 0 0 12.04 22c5.46 0 9.91-4.4 9.91-9.83C21.95 6.4 17.5 2 12.04 2zm5.76 14.12c-.24.68-1.39 1.25-1.91 1.33-.49.08-1.1.11-1.77-.11-.41-.13-.93-.31-1.61-.61-2.83-1.23-4.67-4.09-4.81-4.28-.14-.19-1.15-1.53-1.15-2.92 0-1.39.71-2.07.96-2.35.24-.28.53-.35.7-.35h.5c.16 0 .37-.02.57.44.22.5.74 1.73.8 1.86.07.13.11.28.02.45-.09.18-.14.28-.27.44l-.4.48c-.13.16-.27.33-.12.64.15.31.67 1.1 1.44 1.78.99.87 1.8 1.14 2.07 1.27.27.13.43.11.59-.07.16-.18.67-.78.85-1.05.18-.27.36-.22.6-.13.24.09 1.54.73 1.8.86.27.13.44.2.51.31.07.11.07.64-.17 1.32z"/></svg>',
        "mail": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 17.5v-11zm1.7.5 6.05 4.32L17.3 7H5.7zM18 8.54l-6.06 4.33a.9.9 0 0 1-1.08 0L4.8 8.54V17.5c0 .28.22.5.5.5h11.4c.28 0 .5-.22.5-.5V8.54z"/></svg>',
        "down": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M11 3h2v10.2l3.4-3.4 1.4 1.4L12 17 6.2 11.2l1.4-1.4L11 13.2V3zm-6 16h14v2H5v-2z"/></svg>',
        "print": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M8 3h8v4H8V3zm-3 6h14a2 2 0 0 1 2 2v6h-4v4H8v-4H4v-6a2 2 0 0 1 2-2zm3 10h8v-4H8v4zm9-8.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"/></svg>',
        "close": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M6.7 6.7 12 12l5.3-5.3 1.4 1.4L13.4 13.4l5.3 5.3-1.4 1.4L12 14.8l-5.3 5.3-1.4-1.4 5.3-5.3-5.3-5.3z"/></svg>',
    }
    return icons[name]


def _ios_item(action: str, label: str, icon: str, *, href: bool = False) -> str:
    glyph = _ios_share_svg(icon)
    inner = (
        f'<span class="ssa-ios-share-icon ssa-ios-share-icon--{icon}">{glyph}</span>'
        f'<span class="ssa-ios-share-label">{label}</span>'
    )
    if href:
        return (
            f'<a class="ssa-ios-share-item" id="ssaPdfDownload" href="#" download '
            f'data-ssa-print="{action}" aria-label="{label}">{inner}</a>'
        )
    return (
        f'<button type="button" class="ssa-ios-share-item" data-ssa-print="{action}" '
        f'aria-label="{label}">{inner}</button>'
    )


def print_share_bar_html() -> str:
    """Print opens the PDF file. Chooser preview paints PDF pages (no plugin needed)."""
    actions = (
        _ios_item("whatsapp", "WhatsApp", "wa")
        + _ios_item("email", "Email", "mail")
        + _ios_item("download", "Download", "down", href=True)
        + _ios_item("printer", "Print", "print")
        + _ios_item("cancel", "Close", "close")
    )
    return (
        '<style id="ssa-print-compact">' + PRINT_COMPACT_CSS + "</style>"
        '<div id="ssaPrintChooser" role="dialog" aria-label="Results PDF">'
        '<div class="card">'
        '<div class="section-title">Results PDF</div>'
        '<p class="ssa-print-chooser-note">This is the PDF file — WhatsApp, Email, Download and Print all use the file, not a page link.</p>'
        '<div id="ssaPdfView" class="ssa-pdf-frame" role="document" aria-label="PDF preview"></div>'
        '<div class="ssa-print-chooser-actions">'
        + actions
        + "</div></div></div>"
        '<div class="action-buttons">'
        '<button type="button" class="action-button" onclick="window.ssaRegattaPrint&&window.ssaRegattaPrint()">Print</button>'
        '<button type="button" class="action-button" id="regattaShareBtn">Share URL</button>'
        "</div>"
        "<script>(function(){" + _PDF_SHARE_JS + "})();</script>"
    )
