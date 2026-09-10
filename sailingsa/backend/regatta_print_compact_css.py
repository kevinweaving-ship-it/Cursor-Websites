"""Compact portrait print stylesheet for standalone /regatta result sheets.

Print test / example sheet:
https://sailingsa.co.za/regatta/2025-12-19-hyc-youth-nationals
(7 fleets, 12 races, Age + Crew — must fit A4 portrait.)

Print and Save-as-PDF both use this CSS on the live HTML tables so sailor / club /
class / sail links stay real hyperlinks in the PDF (not a screenshot).
"""

PRINT_COMPACT_CSS = """
@page { size: A4 portrait; margin: 8mm 8mm 10mm; }
@media print {
  html, body { background: #fff !important; color: #1a2750 !important; margin: 0 !important; padding: 0 !important; }
  .site-header, footer, .site-footer, .app-footer, .action-buttons, .back-to-home,
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
    grid-template-columns: auto minmax(0,1fr) auto !important;
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
    break-after: avoid;
  }
  .regatta-header-logo-col { grid-column: 1 !important; grid-row: 1 !important; justify-content: flex-start !important; padding: 0 4px 0 0 !important; width: auto !important; }
  .regatta-header-main-col { grid-column: 2 !important; grid-row: 1 !important; justify-self: stretch !important; padding: 0 4px !important; width: 100% !important; }
  .regatta-header-club-logo-col { grid-column: 3 !important; grid-row: 1 !important; justify-content: flex-end !important; padding: 0 0 0 4px !important; width: auto !important; }
  .regatta-header-logo-img, .regatta-header-left-logo-img { max-height: 40px !important; max-width: 96px !important; height: auto !important; width: auto !important; }
  .regatta-header-club-logo-img { max-height: 40px !important; max-width: 96px !important; height: auto !important; width: auto !important; }
  .regatta-name { font-size: 11pt !important; line-height: 1.15 !important; margin: 0 0 1px 0 !important; }
  .host-club, .regatta-venue, .regatta-lipton-venue-line, .regatta-lipton-host-line { font-size: 8pt !important; line-height: 1.2 !important; margin: 0 0 1px 0 !important; }
  .status-line { font-size: 7.5pt !important; line-height: 1.2 !important; margin: 2px 0 0 0 !important; }
  .regatta-live-board-row { display: none !important; }

  /* Tight gap: main header → first fleet card */
  .fleet-section { width: 100% !important; margin-top: 6px !important; page-break-inside: auto; }
  .regatta-page > .fleet-section:first-of-type { margin-top: 6px !important; }

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
    break-after: avoid;
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
  .fleet-title-row { font-size: 9pt !important; font-weight: 700 !important; margin: 0 !important; line-height: 1.15 !important; white-space: nowrap !important; }
  .sailed-line { font-size: 7pt !important; margin: 0 !important; line-height: 1.15 !important; white-space: nowrap !important; }

  /* Single-line rank table — A4 portrait, including 12-race Youth Nationals */
  .table-wrapper { overflow: visible !important; margin-top: 3px !important; width: 100% !important; max-width: 100% !important; }
  .table-wrapper table, table.fleet-results-table, .fleet-section .table-wrapper table.fleet-results-table {
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    table-layout: fixed !important;
  }
  th, td {
    padding: 1px 1px !important;
    font-size: 6.5pt !important;
    line-height: 1.15 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
  }
  .rank-col, .total-col, .nett-col, .wc-meta-col { width: 3.6% !important; }
  .class-col { width: 7% !important; }
  .sail-col { width: 6% !important; }
  .club-col { width: 5.5% !important; }
  .helm-col, td.crew-col, th.crew-col { width: 10% !important; }
  .race-col { width: 3.15% !important; padding-left: 0 !important; padding-right: 0 !important; }
  .fleet-results-table tbody tr, .fleet-results-table tbody td { height: auto !important; max-height: none !important; }
  .rs-club-row-logo, .rs-boat-sponsor-logo, .fleet-results-table .rs-club-row-logo,
  .fleet-results-table .rs-boat-sponsor-logo { display: none !important; }
  .rs-club-with-logo, .rs-boat-name-sponsors { white-space: nowrap !important; }
  thead { display: table-header-group; }
  tr { page-break-inside: avoid; break-inside: avoid; }

  a, a:visited { color: #0000ee !important; text-decoration: underline !important; }
  html, body, .regatta-page {
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
}
""".strip()


def print_share_bar_html() -> str:
    """Print + Share controls plus compact print CSS (one inject for live + repo)."""
    return (
        '<style id="ssa-print-compact">' + PRINT_COMPACT_CSS + "</style>"
        '<div class="action-buttons">'
        '<button type="button" class="action-button" onclick="window.print()">Print</button>'
        '<button type="button" class="action-button" id="regattaShareBtn">Share</button>'
        "</div>"
        "<script>(function(){"
        "var b=document.getElementById('regattaShareBtn');"
        "if(!b)return;"
        "b.addEventListener('click',function(){"
        "var t=document.title||'SailingSA',u=location.href;"
        "if(navigator.share){navigator.share({title:t,url:u}).catch(function(){});return;}"
        "function copied(){b.textContent='Link copied';setTimeout(function(){b.textContent='Share';},1600);}"
        "if(navigator.clipboard&&navigator.clipboard.writeText){"
        "navigator.clipboard.writeText(u).then(copied).catch(function(){prompt('Copy this link:',u);});"
        "return;}"
        "prompt('Copy this link:',u);"
        "});"
        "})();</script>"
    )
