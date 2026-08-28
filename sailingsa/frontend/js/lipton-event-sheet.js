/**
 * Lipton public playback only.
 * Inserts the official event result sheet between the site header and Lipton chrome:
 * Event Header, Class Header, Event Results.
 * Strips LIVE board, weather, Live cam, and tracking. Does not put the old event page on this URL.
 */
(function () {
  var FRAME = "lipton-event-sheet-frame";
  var HOST = "lipton-event-sheet";
  var SRC = "/regatta/2026-08-29-lipton-challenge-cup/class-j22";
  var HIDE = [
    ".regatta-live-board-row",
    ".regatta-live-board",
    ".regatta-live-wx",
    ".regatta-live-clip",
    ".regatta-live-track",
    ".action-buttons",
    ".back-to-home",
    ".regatta-sa-mode-wrap",
    ".regatta-sa-toolbar",
    ".seo-sailors-nav",
    ".seo-discovery"
  ].join(",");

  function hostEl() { return document.getElementById(HOST); }
  function frameEl() { return document.getElementById(FRAME); }
  function showHost() {}
  function hideHost() {
    var host = hostEl();
    if (host) host.hidden = true;
  }
  function strip(doc) {
    var page = doc.querySelector(".regatta-page");
    if (!page) return false;
    doc.querySelectorAll(HIDE).forEach(function (el) {
      if (el && el.parentNode) el.parentNode.removeChild(el);
    });
    doc.querySelectorAll("script").forEach(function (el) {
      if (el && el.parentNode) el.parentNode.removeChild(el);
    });
    var extra = doc.createElement("style");
    extra.textContent = [
      "html,body{margin:0;padding:0;background:#fff;overflow-x:hidden;}",
      ".regatta-page,.header,.class-header,.fleet-section,.table-wrapper{width:100%!important;max-width:100%!important;margin-left:0!important;margin-right:0!important;box-sizing:border-box;}",
      ".regatta-page{padding:8px 10px 12px;}",
      ".header{margin-bottom:0!important;}",
      ".fleet-section{margin-top:20px!important;}",
      ".table-wrapper{margin-top:20px!important;}",
      ".table-wrapper table,.table-wrapper th,.table-wrapper td{font-size:70%;}",
      "@media (max-width:768px){.header{margin-bottom:0!important;}.fleet-section{margin-top:12px!important;}.table-wrapper{margin-top:12px!important;}}",
      "@media (orientation:landscape) and (max-height:600px){.header{margin-bottom:0!important;}.fleet-section{margin-top:6px!important;}.table-wrapper{margin-top:6px!important;}}",
      ".header.header--lipton{display:grid!important;grid-template-columns:88px minmax(0,1fr) 88px!important;align-items:center;}",
      ".regatta-header-logo-col,.regatta-header-club-logo-col{width:88px;min-width:88px;}",
      ".regatta-live-board-row,.regatta-live-board{display:none!important;}"
    ].join("");
    (doc.head || doc.documentElement).appendChild(extra);
    return true;
  }
  function fit() {
    var iframe = frameEl();
    if (!iframe) return;
    var doc;
    try { doc = iframe.contentDocument; } catch (err) { return; }
    if (!doc) return;
    var page = doc.querySelector(".regatta-page") || doc.body;
    var h = Math.ceil(Math.max(page.scrollHeight || 0, page.offsetHeight || 0, 160));
    iframe.style.height = h + "px";
  }
  function paint(html) {
    var iframe = frameEl();
    if (!iframe) return;
    var doc = new DOMParser().parseFromString(html, "text/html");
    if (!strip(doc)) {
      hideHost();
      return;
    }
    iframe.addEventListener("load", function onLoad() {
      iframe.removeEventListener("load", onLoad);
      showHost();
      fit();
      if (typeof ResizeObserver === "function") {
        try {
          var inner = iframe.contentDocument && iframe.contentDocument.querySelector(".regatta-page");
          if (inner) new ResizeObserver(fit).observe(inner);
        } catch (err) {}
      }
    });
    iframe.srcdoc = "<!DOCTYPE html>" + doc.documentElement.outerHTML;
  }

  fetch(SRC, { cache: "no-store", headers: { Accept: "text/html" } })
    .then(function (res) { return res.ok ? res.text() : Promise.reject(res.status); })
    .then(paint)
    .catch(function () { hideHost(); });
})();
