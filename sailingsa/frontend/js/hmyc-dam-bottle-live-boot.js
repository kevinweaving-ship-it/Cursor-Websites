/**
 * Dam Bottle Sprints — same HMYC Wind / Media / Live Cam / Leaderboard cards
 * as /regatta/2026-09-24-hmyc-dart-18-nationals.
 * Loaded only on this club event. Does not change live api.py.
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

  function placeOpenFleetHeader() {
    if (document.getElementById("dam-bottle-open-fleet")) return;
    var sec = document.createElement("div");
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
    var host = document.getElementById("midmar-live-media");
    var header = document.querySelector(".regatta-header-wrap");
    if (host && host.parentNode) host.parentNode.insertBefore(sec, host.nextSibling);
    else if (header && header.parentNode) header.parentNode.insertBefore(sec, header.nextSibling);
    else if (page) page.appendChild(sec);
  }
  placeOpenFleetHeader();
  window.setTimeout(placeOpenFleetHeader, 50);
  window.setTimeout(placeOpenFleetHeader, 400);

  function add(src) {
    var base = src.split("?")[0];
    if (document.querySelector('script[src*="' + base + '"]')) return;
    var s = document.createElement("script");
    s.src = src;
    s.defer = true;
    document.head.appendChild(s);
  }
  add("/js/midmar-live-media.js?v=midmarwx60dbs1");
  add("/js/midmar-leaderboard.js?v=mmlb17dbs1");
  add("/js/midmar-media-rotate.js?v=mmrot4dbs1");
  add("/js/club-score-edit.js?v=ccr38dbs1");
})();
