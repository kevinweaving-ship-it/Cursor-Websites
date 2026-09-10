"""Compact portrait print stylesheet for standalone /regatta result sheets.

Print test / example sheet:
https://sailingsa.co.za/regatta/2025-12-19-hyc-youth-nationals
(7 fleets, 12 races, Age + Crew — A4 portrait, SA.)

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
"""

PRINT_COMPACT_CSS = """
@page { size: A4 portrait; margin: 8mm 8mm 14mm; }
.ssa-print-page-footer { display: none !important; }
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
    break-after: avoid-page;
  }
  .regatta-header-wrap {
    page-break-after: avoid;
    break-after: avoid-page;
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
  .fleet-title-row { font-size: 9pt !important; font-weight: 700 !important; margin: 0 !important; line-height: 1.15 !important; white-space: nowrap !important; }
  .sailed-line { font-size: 7pt !important; margin: 0 !important; line-height: 1.15 !important; white-space: nowrap !important; }

  /* Single-line rank table — A4 portrait, including 12-race Youth Nationals */
  .table-wrapper {
    overflow: visible !important;
    margin-top: 3px !important;
    width: 100% !important;
    max-width: 100% !important;
    page-break-before: avoid !important;
    break-before: avoid-page !important;
    page-break-inside: avoid !important;
    break-inside: avoid-page !important;
  }
  .table-wrapper table, table.fleet-results-table, .fleet-section .table-wrapper table.fleet-results-table {
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
    table-layout: fixed !important;
    page-break-inside: avoid !important;
    break-inside: avoid-page !important;
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
""".strip()


PRINT_PAGINATE_JS = r"""
function pagePx(){return (297-8-14)*96/25.4;}
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
  var page=pagePx()-8;
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
window.ssaRegattaPrint=function(){fillFooter();keepFleetsOnOnePage();window.print();};
window.addEventListener('beforeprint',keepFleetsOnOnePage);
window.addEventListener('afterprint',clearPrintPages);
""".replace("\n", "")


def print_share_bar_html() -> str:
    """Print + Share controls plus compact print CSS (one inject for live + repo)."""
    return (
        '<style id="ssa-print-compact">' + PRINT_COMPACT_CSS + "</style>"
        '<div id="ssaPrintPageFooter" class="ssa-print-page-footer">'
        '<span class="ssa-print-footer-name"></span>'
        '<a class="ssa-print-footer-url" href="#"></a>'
        "</div>"
        '<div class="action-buttons">'
        '<button type="button" class="action-button" onclick="window.ssaRegattaPrint?window.ssaRegattaPrint():window.print()">Print</button>'
        '<button type="button" class="action-button" id="regattaShareBtn">Share</button>'
        "</div>"
        "<script>(function(){"
        "function sheetUrl(){"
        "var c=document.querySelector('link[rel=\"canonical\"]');"
        "if(c&&c.href&&c.href.indexOf('http')===0)return c.href.split('#')[0].split('?')[0];"
        "var u=(location.href||'').split('#')[0].split('?')[0];"
        "if(u.indexOf('http')===0)return u;"
        "var p=location.pathname||'';"
        "if(p.indexOf('/regatta/')===0)return 'https://sailingsa.co.za'+p.replace(/\\/+$/,'');"
        "return '';"
        "}"
        "function fillFooter(){"
        "var f=document.getElementById('ssaPrintPageFooter');if(!f)return;"
        "var n=document.querySelector('.regatta-name');"
        "var name=(n&&n.textContent||document.title||'').replace(/\\s*\\|\\s*SailingSA\\s*$/i,'').replace(/\\s+/g,' ').trim();"
        "var url=sheetUrl();"
        "var ns=f.querySelector('.ssa-print-footer-name');"
        "var a=f.querySelector('a');"
        "if(ns)ns.textContent=name;"
        "if(a&&url){a.setAttribute('href',url);a.textContent=url;}"
        "}"
        "fillFooter();"
        "if(!document.querySelector('.regatta-name'))document.addEventListener('DOMContentLoaded',fillFooter);"
        + PRINT_PAGINATE_JS
        + "var b=document.getElementById('regattaShareBtn');"
        "if(!b)return;"
        "b.addEventListener('click',function(){"
        "var t=document.title||'SailingSA',u=sheetUrl()||location.href;"
        "if(navigator.share){navigator.share({title:t,url:u}).catch(function(){});return;}"
        "function copied(){b.textContent='Link copied';setTimeout(function(){b.textContent='Share';},1600);}"
        "if(navigator.clipboard&&navigator.clipboard.writeText){"
        "navigator.clipboard.writeText(u).then(copied).catch(function(){prompt('Copy this link:',u);});"
        "return;}"
        "prompt('Copy this link:',u);"
        "});"
        "})();</script>"
    )
