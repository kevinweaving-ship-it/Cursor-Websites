/**
 * Lipton public playback only.
 * Event header / class header / results table is an exact copy of
 * /regatta/2026-08-29-lipton-challenge-cup/class-j22 (same look/size).
 * Cached in localStorage: refresh does not rebuild the sheet unless a new race result landed.
 * Keep the sheet visible in ?live=gps so DEV matches public.
 */
(function () {
  var FRAME = "lipton-event-sheet-frame";
  var HOST = "lipton-event-sheet";
  var SRC = "/regatta/2026-08-29-lipton-challenge-cup/class-j22";
  var STORE_HTML = "liptonSheetHtml";
  var STORE_FP = "liptonSheetFp";
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
  function showHost() {
    var host = hostEl();
    if (host) host.hidden = false;
  }
  function hideHost() {
    var host = hostEl();
    if (host) host.hidden = true;
  }
  function applyRaceMode() {
    var p = new URLSearchParams(location.search);
    var on = p.has("live") && String(p.get("live") || "") !== "0";
    document.body.setAttribute("data-lipton-race-mode", on ? "1" : "0");
  }
  function fingerprint(html) {
    var sailed = (String(html).match(/Sailed:\s*\d+/i) || [""])[0];
    var asAt = (String(html).match(/Results are[^<]{0,120}/i) || [""])[0];
    var heads = (String(html).match(/>R\d+</g) || []).join("");
    return sailed + "|" + asAt + "|" + heads;
  }
  function readCache() {
    try {
      return {
        html: localStorage.getItem(STORE_HTML) || "",
        fp: localStorage.getItem(STORE_FP) || ""
      };
    } catch (err) {
      return { html: "", fp: "" };
    }
  }
  function writeCache(html, fp) {
    try {
      localStorage.setItem(STORE_HTML, html);
      localStorage.setItem(STORE_FP, fp);
    } catch (err) {}
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
      "html,body{margin:0;padding:0;background:#fff;overflow-x:auto;}",
      ".regatta-page{width:100%!important;max-width:1100px!important;padding:16px!important;margin:0 auto!important;box-sizing:border-box;padding-top:0!important;}",
      ".regatta-page > .regatta-header-wrap,.regatta-page > .header.header--lipton,.regatta-page > .header{margin-top:20px!important;margin-bottom:0!important;}",
      ".regatta-page > .fleet-section{margin-top:20px!important;}",
      ".regatta-page .class-header{margin-bottom:0!important;}",
      ".regatta-page .fleet-section > .table-wrapper,.regatta-page .table-wrapper{margin-top:20px!important;overflow-x:auto!important;overflow-y:visible!important;}",
      ".fleet-results-table td.rank-col--live-icon{width:2.7rem;min-width:2.7rem;max-width:3rem;padding:2px 1px!important;text-align:center;vertical-align:middle;line-height:0;overflow:hidden;box-sizing:border-box;}",
      ".fleet-results-table .r10-live-icon,.fleet-results-table svg.lipton-boat-dot.r10-live-icon{width:36px!important;height:36px!important;max-width:36px;max-height:36px;display:inline-block;vertical-align:middle;}",
      ".regatta-live-board-row,.regatta-live-board,.regatta-live-wx,.regatta-live-track,.regatta-live-clip,.regatta-live-map,.regatta-live-camera{display:none!important;}"
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

  applyRaceMode();
  setTimeout(applyRaceMode, 0);
  window.addEventListener("popstate", applyRaceMode);

  var cached = readCache();
  if (cached.html) paint(cached.html);

  fetch(SRC, { cache: "no-store", headers: { Accept: "text/html" } })
    .then(function (res) { return res.ok ? res.text() : Promise.reject(res.status); })
    .then(function (html) {
      var fp = fingerprint(html);
      if (cached.html && cached.fp === fp) return;
      writeCache(html, fp);
      paint(html);
    })
    .catch(function () { if (!cached.html) hideHost(); });
})();
