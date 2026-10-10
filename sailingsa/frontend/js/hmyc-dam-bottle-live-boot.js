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
