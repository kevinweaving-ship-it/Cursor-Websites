"""Compact portrait print stylesheet for standalone /regatta result sheets.

Print test / example sheet:
https://sailingsa.co.za/regatta/2025-12-19-hyc-youth-nationals
(7 fleets, 12 races, Age + Crew — A4 landscape so the race grid fits, SA.)

Print and Save-as-PDF both use this CSS on the live HTML tables so sailor / club /
class / sail links stay real hyperlinks in the PDF (not a screenshot).

Pagination (A4):
- Cape Classic (URL is truth): A4 **portrait** — the grid fits P. Do not flip to landscape.
- Page 1 always starts with the event header + first fleet.
- The next fleet stays on that page only if the whole fleet (header + full table) fits;
  otherwise the entire fleet moves to the next page.
- A fleet header must never sit on one page with its results table on the next.
- A fleet is never split across two pages.
- Every page footer (one small line): event name + the results URL.
"""

from pathlib import Path
import base64

_FONT_DIR = Path(__file__).resolve().parent / "fonts"


def _woff2_data_uri(name: str) -> str:
    raw = (_FONT_DIR / name).read_bytes()
    return "data:font/woff2;base64," + base64.b64encode(raw).decode("ascii")


def ibm_plex_print_font_css() -> str:
    """Do not embed IBM Plex variable fonts.

    Chrome headless print-to-PDF double-paints variable-font glyphs
    (Hostost / TheMidmarcuppionship). Liberation Sans is metric-stable.
    """
    return ""


IBM_PLEX_PRINT_FONT_CSS = ibm_plex_print_font_css()
_PRINT_SANS = '"Liberation Sans", Arial, Helvetica, sans-serif'

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
/* Race codes stay overlaid (no extra row height). Centre under score; lift off bottom. */
.fleet-results-table.rs-compact-row-logos td.race-col {
  position: relative !important;
}
.fleet-results-table.rs-compact-row-logos .wc-score {
  font-size: 1em !important;
  font-weight: 600 !important;
}
.fleet-results-table.rs-compact-row-logos .wc-code,
.fleet-results-table.rs-compact-row-logos span.code .wc-code,
.fleet-results-table.rs-compact-row-logos span.disc .wc-code {
  font-size: 50% !important;
  font-weight: 700 !important;
  position: absolute !important;
  left: 50% !important;
  right: auto !important;
  top: auto !important;
  bottom: 4px !important;
  transform: translateX(-50%) !important;
  margin: 0 !important;
  line-height: 1 !important;
  vertical-align: baseline !important;
  letter-spacing: 0.08em !important;
  opacity: 1 !important;
  width: auto !important;
  text-align: center !important;
}
/* Club col: logo | light rule | code. Codes start in one column. Col shrinks. */
.fleet-results-table.rs-compact-row-logos td.club-col,
.fleet-results-table.rs-compact-row-logos th.club-col {
  text-align: left !important;
  width: auto !important;
  max-width: none !important;
  white-space: nowrap !important;
}
.fleet-results-table.rs-compact-row-logos td.club-col .rs-club-with-logo {
  display: inline-flex !important;
  width: auto !important;
  justify-content: flex-start !important;
  align-items: center !important;
  gap: 0 !important;
}
.fleet-results-table.rs-compact-row-logos td.club-col .rs-club-row-logo-sm {
  flex: 0 0 22px !important;
  width: 22px !important;
  max-width: 22px !important;
  object-fit: contain !important;
  box-sizing: content-box !important;
  padding-right: 4px !important;
  margin-right: 4px !important;
  border-right: 1px solid rgba(26, 39, 80, 0.22) !important;
}
.fleet-results-table.rs-compact-row-logos td.club-col .rs-club-with-logo > a {
  margin-left: 0 !important;
  text-align: left !important;
}
/* Title-row fleet logos: same height as the word Fleet. No max-width (that
   squashed Extra / ILCA / Open). 420 and Optimist already filled the height. */
.fleet-title-with-logo {
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
  flex-wrap: nowrap !important;
}
.fleet-title-with-logo .rs-fleet-title-logo {
  height: 1.1em !important;
  width: auto !important;
  max-height: 1.1em !important;
  max-width: none !important;
  object-fit: contain !important;
  flex: 0 0 auto !important;
  display: inline-block !important;
  vertical-align: middle !important;
}
/* Class column logos: Sonnet is the tallest (16px). All class marks match that. */
.fleet-results-table.rs-compact-row-logos .rs-class-row-logo {
  height: 16px !important;
  width: auto !important;
  max-height: 16px !important;
  max-width: none !important;
  object-fit: contain !important;
  display: inline-block !important;
  vertical-align: middle !important;
  flex: 0 0 auto !important;
}
@media print {
  html, body { background: #fff !important; color: #1a2750 !important; margin: 0 !important; padding: 0 !important; }
  html, body, .regatta-page, .class-header, .sailed-line, table, th, td {
    font-family: """ + _PRINT_SANS + """ !important;
    font-variant-numeric: tabular-nums lining-nums !important;
    font-feature-settings: "tnum" 1, "lnum" 1 !important;
  }
  .site-header, footer, .site-footer, .app-footer, .action-buttons, .back-to-home,
  .regatta-back-row, .regatta-source-banner, #ssaPrintChooser,
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
    grid-template-columns: 88px minmax(0,1fr) 88px !important;
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
    width: 88px !important;
    min-width: 88px !important;
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
    width: 88px !important;
    min-width: 88px !important;
  }
  .regatta-header-logo-img, .regatta-header-left-logo-img {
    max-height: 48px !important;
    max-width: 48px !important;
    height: 48px !important;
    width: auto !important;
    object-fit: contain !important;
  }
  .regatta-header-club-logo-img { max-height: 56px !important; max-width: none !important; height: auto !important; width: auto !important; }
  .regatta-name { font-size: 13pt !important; line-height: 1.15 !important; margin: 0 0 1px 0 !important; text-align: center !important; width: 100% !important; }
  .host-club, .regatta-venue, .regatta-lipton-venue-line, .regatta-lipton-host-line { font-size: 8pt !important; line-height: 1.2 !important; margin: 0 0 1px 0 !important; text-align: center !important; width: 100% !important; }
  .status-line { font-size: 7.5pt !important; line-height: 1.2 !important; margin: 2px 0 0 0 !important; text-align: center !important; width: 100% !important; }
  .regatta-live-board-row { display: none !important; }

  /* Tight gap: main header → first fleet. Glue fleet header to the first
     table rows. Do not page-break-inside:avoid the whole Extra table — that
     overflows A4 and looks like a broken print. Stored PDF still moves a
     whole fleet with .ssa-print-new-page when leftover space is too small. */
  .fleet-section {
    display: block !important;
    width: 100% !important;
    margin-top: 6px !important;
    page-break-inside: auto;
    break-inside: auto;
    page-break-before: auto;
    break-before: auto;
  }
  .fleet-section .class-header,
  .fleet-section .class-header--with-logos {
    page-break-after: avoid !important;
    break-after: avoid-page !important;
    page-break-inside: avoid !important;
    break-inside: avoid-page !important;
  }
  .fleet-section .table-wrapper,
  .fleet-section table {
    page-break-before: avoid !important;
    break-before: avoid-page !important;
    page-break-inside: auto;
    break-inside: auto;
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

  /* Cape Classic: same card as the URL — left fleet logo | [logo] Fleet + sailed | right club. */
  .fleet-section:has(.rs-compact-row-logos) .class-header,
  .fleet-section:has(.rs-compact-row-logos) .class-header--with-logos {
    display: grid !important;
    grid-template-columns: minmax(52px, 22%) minmax(0, 1fr) minmax(52px, 22%) !important;
    grid-template-rows: auto !important;
    align-items: center !important;
    justify-items: stretch !important;
    text-align: center !important;
    gap: 2px 6px !important;
    column-gap: 6px !important;
  }
  .fleet-section:has(.rs-compact-row-logos) .class-header-logo-col {
    display: flex !important;
    grid-column: 1 !important;
    grid-row: 1 !important;
    justify-content: flex-start !important;
    align-items: center !important;
  }
  .fleet-section:has(.rs-compact-row-logos) .class-header-club-logo-col {
    display: flex !important;
    grid-column: 3 !important;
    grid-row: 1 !important;
    justify-content: flex-end !important;
    align-items: center !important;
  }
  .fleet-section:has(.rs-compact-row-logos) .class-header-logo-img,
  .fleet-section:has(.rs-compact-row-logos) .class-header-class-icon-img {
    max-height: 44px !important;
    max-width: 96px !important;
    width: auto !important;
    height: auto !important;
    object-fit: contain !important;
  }
  .fleet-section:has(.rs-compact-row-logos) .class-header-club-logo-col img {
    max-height: 44px !important;
    max-width: 96px !important;
    width: auto !important;
    height: auto !important;
    object-fit: contain !important;
  }
  .fleet-section:has(.rs-compact-row-logos) .class-header-main-col,
  .fleet-section:has(.rs-compact-row-logos) .class-header-text-col {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    grid-column: 2 !important;
    grid-row: 1 !important;
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
    height: 1.1em !important;
    width: auto !important;
    max-height: 1.1em !important;
    max-width: none !important;
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
  }
  .table-wrapper table, table.fleet-results-table, .fleet-section .table-wrapper table.fleet-results-table {
    width: calc(100% - 1.6pt) !important;
    min-width: 0 !important;
    max-width: calc(100% - 1.6pt) !important;
    table-layout: fixed !important;
    border-collapse: collapse !important;
    box-sizing: border-box !important;
    border: 0.7pt solid #1a2750 !important;
  }
  th, td {
    padding: 2.5px 4px !important;
    font-size: 8.5pt !important;
    font-weight: 400 !important;
    line-height: 1.25 !important;
    white-space: nowrap !important;
    overflow: visible !important;
    letter-spacing: 0 !important;
    box-sizing: border-box !important;
    border: 0.5pt solid #1a2750 !important;
    background: #fff !important;
  }
  th {
    background: #e9eefb !important;
    font-weight: 700 !important;
    text-align: center !important;
  }
  td { text-align: center !important; }
  td.helm-col, th.helm-col, td.crew-col, th.crew-col { text-align: left !important; }
  tr.medal-gold td { background: #D4AF37 !important; }
  tr.medal-silver td { background: #D7D7D7 !important; }
  tr.medal-bronze td { background: #CE8946 !important; }
  html.ssa-print-landscape .table-wrapper table,
  html.ssa-print-landscape table.fleet-results-table,
  html.ssa-print-landscape .fleet-section .table-wrapper table.fleet-results-table {
    table-layout: auto !important;
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
  }
  html.ssa-print-landscape th, html.ssa-print-landscape td {
    font-size: 9pt !important;
    white-space: nowrap !important;
    overflow: visible !important;
    width: auto !important;
  }
  html.ssa-print-landscape .race-col { font-size: 8.5pt !important; width: auto !important; }
  html.ssa-print-landscape .helm-col,
  html.ssa-print-landscape .fleet-section:has(th.crew-col) .helm-col { width: auto !important; }
  html.ssa-print-landscape .fleet-section:has(th.crew-col) .race-col { width: auto !important; }
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
    width: auto !important;
    white-space: nowrap !important;
    overflow: visible !important;
    text-align: left !important;
  }
  .rs-class-row-logo,
  .fleet-results-table .rs-class-row-logo,
  .fleet-results-table.rs-compact-row-logos .rs-class-row-logo {
    display: inline-block !important;
    height: 16px !important;
    width: auto !important;
    max-height: 16px !important;
    max-width: none !important;
    object-fit: contain !important;
    vertical-align: middle !important;
    flex: 0 0 auto !important;
  }
  .rs-club-row-logo-sm,
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
  .rs-class-with-logo {
    display: inline-flex !important;
    align-items: center !important;
    gap: 2px !important;
    flex-wrap: nowrap !important;
  }
  .fleet-results-table.rs-compact-row-logos .rs-club-with-logo {
    display: inline-flex !important;
    width: auto !important;
    justify-content: flex-start !important;
    align-items: center !important;
    gap: 4px !important;
    flex-wrap: nowrap !important;
  }
  .fleet-results-table.rs-compact-row-logos td.club-col .rs-club-with-logo > a {
    margin-left: 0 !important;
    text-align: left !important;
  }
  .rank-col, .total-col, .nett-col { width: 3.3% !important; }
  .wc-meta-col { width: 3% !important; }
  .sail-col { width: 5.4% !important; }
  .club-col { width: auto !important; white-space: nowrap !important; }
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
    position: relative !important;
  }
  .fleet-results-table .wc-score,
  .fleet-results-table.rs-compact-row-logos .wc-score {
    font-size: 1em !important;
    font-weight: 600 !important;
  }
  .fleet-results-table .wc-code,
  .fleet-results-table.rs-compact-row-logos .wc-code {
    font-size: 50% !important;
    font-weight: 700 !important;
    position: absolute !important;
    left: 50% !important;
    right: auto !important;
    bottom: 3px !important;
    transform: translateX(-50%) !important;
    margin: 0 !important;
    line-height: 1 !important;
    vertical-align: baseline !important;
    letter-spacing: 0.08em !important;
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
  .rs-class-row-logo,
  .fleet-results-table .rs-class-row-logo {
    display: inline-block !important;
    height: 16px !important;
    width: auto !important;
    max-height: 16px !important;
    max-width: none !important;
    object-fit: contain !important;
    vertical-align: middle !important;
    flex: 0 0 auto !important;
  }
  .rs-club-row-logo-sm,
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
  /* Same as the URL: small title-row logo beside the Fleet word. */
  .rs-fleet-title-logo, .fleet-title-with-logo .rs-fleet-title-logo {
    display: inline-block !important;
    height: 1.25em !important;
    max-height: 1.25em !important;
    width: auto !important;
    max-width: none !important;
    object-fit: contain !important;
  }
  .rs-club-with-logo, .rs-boat-name-sponsors { white-space: nowrap !important; }
  thead { display: table-header-group; }
  tbody { page-break-inside: auto; break-inside: auto; }
  tr { page-break-inside: avoid; break-inside: avoid; }

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
#ssaPrintChooser.is-open { display: flex !important; }
#ssaPrintChooser .card {
  max-width: 40rem; width: min(96%, 40rem); padding: 14px 14px 16px; margin: 0 0 18px;
  background: #fff !important; border: 2px solid #001f3f; overflow: hidden;
  border-radius: 8px; box-shadow: 0 8px 28px rgba(0,31,63,.18);
}
#ssaPrintChooser .ssa-print-chooser-note { font-size: 12px; color: #001f3f; margin: 0 0 8px; line-height: 1.35; text-align: center; }
#ssaPrintChooser .ssa-pdf-frame { width: 100%; height: 52vh; border: 2px solid #001f3f; background: #fff; margin: 0; border-radius: 8px; overflow: auto; padding: 0; }
#ssaPdfView { min-height: 100%; padding: 0; box-sizing: border-box; background: #fff; }
#ssaPdfView iframe, #ssaPdfView embed, #ssaPdfView object {
  display: block; width: 100%; height: 52vh; border: 0; background: #fff;
}
#ssaPdfView canvas, #ssaPdfView img.ssa-pdf-page {
  display: block; width: 100%; height: auto; margin: 0; background: #fff;
}
#ssaPdfView .ssa-pdf-status { margin: 24px 12px; text-align: center; color: #001f3f; font-size: 13px; }
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
  isolation: isolate; box-shadow: 0 1px 3px rgba(0,31,63,.2);
}
#ssaPrintChooser .ssa-ios-share-icon svg { width: 26px; height: 26px; display: block; }
#ssaPrintChooser .ssa-ios-share-icon--wa { background: #25D366; }
#ssaPrintChooser .ssa-ios-share-icon--mail { background: #007AFF; }
#ssaPrintChooser .ssa-ios-share-icon--down { background: #34C759; }
#ssaPrintChooser .ssa-ios-share-icon--print { background: #001f3f; }
#ssaPrintChooser .ssa-ios-share-icon--close { background: #DC143C; }
#ssaPrintChooser .ssa-ios-share-label {
  font-size: 11px; font-weight: 600; line-height: 1.15; text-align: center;
  color: #001f3f; max-width: 64px;
}
#ssaPrintChooser a.ssa-ios-share-item { color: #001f3f; }
@media (min-width: 700px) {
  #ssaPrintChooser { align-items: center; }
  #ssaPrintChooser .card { max-width: 44rem; width: min(96%, 44rem); margin: 0; }
  #ssaPrintChooser .ssa-pdf-frame, #ssaPdfView iframe { height: 62vh; }
}
@media print {
  #ssaPrintChooser, #ssaPrintChooser.is-open { display: none !important; }
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


PDF_SHARE_JS_SRC = "/js/regatta-pdf-share.js?v=20260919print9"


def _ios_share_svg(name: str) -> str:
    icons = {
        "wa": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M12.04 2c-5.46 0-9.91 4.4-9.91 9.83 0 1.73.46 3.43 1.33 4.93L2 22l5.39-1.41A10 10 0 0 0 12.04 22c5.46 0 9.91-4.4 9.91-9.83C21.95 6.4 17.5 2 12.04 2zm5.76 14.12c-.24.68-1.39 1.25-1.91 1.33-.49.08-1.1.11-1.77-.11-.41-.13-.93-.31-1.61-.61-2.83-1.23-4.67-4.09-4.81-4.28-.14-.19-1.15-1.53-1.15-2.92 0-1.39.71-2.07.96-2.35.24-.28.53-.35.7-.35h.5c.16 0 .37-.02.57.44.22.5.74 1.73.8 1.86.07.13.11.28.02.45-.09.18-.14.28-.27.44l-.4.48c-.13.16-.27.33-.12.64.15.31.67 1.1 1.44 1.78.99.87 1.8 1.14 2.07 1.27.27.13.43.11.59-.07.16-.18.67-.78.85-1.05.18-.27.36-.22.6-.13.24.09 1.54.73 1.8.86.27.13.44.2.51.31.07.11.07.64-.17 1.32z"/></svg>',
        "mail": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 17.5v-11zm1.7.5 6.05 4.32L17.3 7H5.7zM18 8.54l-6.06 4.33a.9.9 0 0 1-1.08 0L4.8 8.54V17.5c0 .28.22.5.5.5h11.4c.28 0 .5-.22.5-.5V8.54z"/></svg>',
        "down": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M11 3h2v10.2l3.4-3.4 1.4 1.4L12 17 6.2 11.2l1.4-1.4L11 13.2V3zm-6 16h14v2H5v-2z"/></svg>',
        "print": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M8 3h8v4H8V3zm-3 6h14a2 2 0 0 1 2 2v6h-4v4H8v-4H4v-6a2 2 0 0 1 2-2zm3 10h8v-4H8v4zm9-8.5a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"/></svg>',
        "close": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#fff" d="M6.7 6.7 12 12l5.3-5.3 1.4 1.4L13.4 13.4l5.3 5.3-1.4 1.4L12 14.8l-5.3 5.3-1.4-1.4 5.3-5.3-5.3-5.3z"/></svg>',
    }
    return icons[name]


def _ios_item(
    action: str,
    label: str,
    icon: str,
    *,
    href: bool = False,
    link_id: str = "",
    download: bool = False,
    target: str = "",
) -> str:
    glyph = _ios_share_svg(icon)
    inner = (
        f'<span class="ssa-ios-share-icon ssa-ios-share-icon--{icon}">{glyph}</span>'
        f'<span class="ssa-ios-share-label">{label}</span>'
    )
    if href:
        extra = f' id="{link_id}"' if link_id else ""
        if download:
            extra += " download"
        if target:
            extra += f' target="{target}" rel="noopener"'
        return (
            f'<a class="ssa-ios-share-item"{extra} href="#"'
            f' data-ssa-print="{action}" aria-label="{label}">{inner}</a>'
        )
    return (
        f'<button type="button" class="ssa-ios-share-item" data-ssa-print="{action}" '
        f'aria-label="{label}">{inner}</button>'
    )


def print_share_bar_html() -> str:
    """Print / share use the stored PDF file. Preview is an iframe of that file."""
    actions = (
        _ios_item("whatsapp", "WhatsApp", "wa")
        + _ios_item("email", "Email", "mail")
        + _ios_item("download", "Download", "down", href=True, link_id="ssaPdfDownload", download=True)
        + _ios_item("printer", "Print", "print", href=True, link_id="ssaPdfPrint", target="_blank")
        + _ios_item("cancel", "Close", "close")
    )
    fallback = (
        "(window.ssaRegattaPrint||function(){var p=(location.pathname||'').replace(/\\/+$/,'');"
        "if(p.indexOf('/regatta/')===0)window.open(p+'/results.pdf','_blank');})()"
    )
    return (
        '<style id="ssa-print-compact">' + PRINT_COMPACT_CSS + "</style>"
        '<div id="ssaPrintChooser" role="dialog" aria-label="Results PDF">'
        '<div class="card">'
        '<div class="section-title">Results PDF</div>'
        '<p class="ssa-print-chooser-note">WhatsApp, Email, Download and Print send this PDF file.</p>'
        '<div id="ssaPdfView" class="ssa-pdf-frame" role="document" aria-label="PDF preview"></div>'
        '<div class="ssa-print-chooser-actions">'
        + actions
        + "</div></div></div>"
        '<div class="action-buttons">'
        f'<button type="button" class="action-button" id="regattaPrintBtn" onclick="{fallback}">Print</button>'
        '<button type="button" class="action-button" id="regattaShareBtn">Share</button>'
        "</div>"
        '<script src="' + PDF_SHARE_JS_SRC + '" defer></script>'
    )
