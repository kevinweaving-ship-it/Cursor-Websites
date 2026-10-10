/**
 * Dam Bottle Sprints — clone Dart Nationals event URL stack.
 * Order: event header → Leader Board → Wind → Media → Live Cam → Open Fleet header.
 * Name / event logo / dates differ. Results table is not built yet.
 * Does not change live api.py.
 */
(function () {
  "use strict";
  var RID = "2026-10-10-hmyc-dam-bottle-sprints";
  var path = String((window.location && window.location.pathname) || "")
    .replace(/\/+$/, "")
    .toLowerCase();
  if (path !== "/regatta/" + RID && path.indexOf("/regatta/" + RID + "/") !== 0) return;

  var page = document.querySelector(".regatta-page");
  if (page) {
    page.setAttribute("data-hmyc-live", "1");
    page.setAttribute("data-club-live-cards", "HMYC");
  }

  if (!document.getElementById("dam-bottle-dart-media-css")) {
    var css = document.createElement("style");
    css.id = "dam-bottle-dart-media-css";
    css.textContent =
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='2026-10-10-hmyc-dam-bottle-sprints']{" +
      "height:auto!important;max-height:none!important;}" +
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='2026-10-10-hmyc-dam-bottle-sprints'] .mm-lipton-reels-brand{" +
      "display:block!important;cursor:pointer;flex:0 0 auto;}" +
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='2026-10-10-hmyc-dam-bottle-sprints'] .mm-lipton-reels-compact{" +
      "display:flex!important;}" +
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='2026-10-10-hmyc-dam-bottle-sprints'] .mm-lipton-reels-expanded," +
      ".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='2026-10-10-hmyc-dam-bottle-sprints'] [data-mm-expanded]{" +
      "display:none!important;height:0!important;overflow:hidden!important;}";
    document.head.appendChild(css);
  }

  function placeOpenFleetHeader() {
    var host = document.getElementById("midmar-live-media");
    if (!host || !host.parentNode) return;
    var sec = document.getElementById("dam-bottle-open-fleet");
    if (!sec) {
      sec = document.createElement("div");
      sec.id = "dam-bottle-open-fleet";
      sec.className = "fleet-section";
      sec.setAttribute("data-block-id", RID + ":open");
      sec.setAttribute("data-fleet-label", "Open");
      sec.innerHTML =
        '<div class="class-header class-header--with-logos">' +
        '<div class="class-header-logo-col">' +
        '<img src="/artwork/Event%20Logo/Dam-Bottle-Sprints.png" alt="Dam Bottle Sprints" class="class-header-logo-img" loading="lazy" decoding="async">' +
        "</div>" +
        '<div class="class-header-main-col">' +
        '<div class="fleet-title-row"><span class="fleet-title-with-logo">Open Fleet</span></div>' +
        "</div>" +
        '<div class="class-header-club-logo-col">' +
        '<img src="/artwork/Club%20Logo/HMYC.png" alt="HMYC" class="class-header-logo-img" loading="lazy" decoding="async">' +
        "</div>" +
        "</div>";
    }
    if (sec.previousSibling !== host) host.parentNode.insertBefore(sec, host.nextSibling);
  }

  function syncDartStack() {
    var header = document.querySelector(".regatta-header-wrap");
    var host = document.getElementById("midmar-live-media");
    var lb = document.getElementById("midmar-leaderboard");
    var wx = document.getElementById("ssa-regatta-slot-card");
    if (header && host && host.parentNode && host.previousSibling !== header) {
      header.parentNode.insertBefore(host, header.nextSibling);
    }
    if (host && lb) {
      if (lb.parentNode !== host) host.insertBefore(lb, host.firstChild);
      if (wx && wx.parentNode === host && lb.nextSibling !== wx) host.insertBefore(lb, wx);
    }
    placeOpenFleetHeader();
  }

  function add(src) {
    var base = src.split("?")[0];
    if (document.querySelector('script[src*="' + base + '"]')) return;
    var s = document.createElement("script");
    s.src = src;
    s.defer = true;
    document.head.appendChild(s);
  }
  /* Same as Dart: live-media boots first and then loads leaderboard into the host. */
  add("/js/midmar-live-media.js?v=midmarwx60dbs3");
  add("/js/club-score-edit.js?v=ccr38dbs3");

  syncDartStack();
  [50, 200, 600, 1200, 2500].forEach(function (ms) {
    window.setTimeout(syncDartStack, ms);
  });
  if (window.MutationObserver && page) {
    var obs = new MutationObserver(syncDartStack);
    obs.observe(page, { childList: true, subtree: true });
    window.setTimeout(function () {
      try {
        obs.disconnect();
      } catch (e) {}
    }, 8000);
  }
})();
