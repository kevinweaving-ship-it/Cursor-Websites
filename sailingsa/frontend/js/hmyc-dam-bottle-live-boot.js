/**
 * Dam Bottle Sprints — Bottle logos + Open Fleet + Dart R+/R−.
 * No observers. Does not change live api.py.
 */
(function () {
  "use strict";
  var RID = "2026-10-10-hmyc-dam-bottle-sprints";
  var path = String((window.location && window.location.pathname) || "")
    .replace(/\/+$/, "")
    .toLowerCase();
  if (path !== "/regatta/" + RID && path.indexOf("/regatta/" + RID + "/") !== 0) return;

  var SRC = "/artwork/Event%20Logo/Dam-Bottle-Sprints.png";

  if (!document.getElementById("dam-bottle-race-step-css")) {
    var css = document.createElement("style");
    css.id = "dam-bottle-race-step-css";
    css.textContent =
      ".regatta-page--club-score-edit .fleet-section[data-block-id='" + RID + ":open'] .club-race-step," +
      ".regatta-page--super-admin-edit .fleet-section[data-block-id='" + RID + ":open'] .club-race-step{" +
      "display:flex!important;visibility:visible!important;}";
    document.head.appendChild(css);
  }

  function paint() {
    var sec = document.querySelector(
      '.fleet-section[data-block-id="' + RID + ':open"]'
    );
    if (!sec) return;
    sec.id = "dam-bottle-open-fleet";
    sec.querySelectorAll(".class-header-logo-col img, .fleet-title-with-logo img").forEach(function (img) {
      if (img.getAttribute("src") !== SRC) img.src = SRC;
      img.alt = "Dam Bottle Sprints";
      img.removeAttribute("title");
    });
    var title = sec.querySelector(".fleet-title-with-logo");
    if (title) {
      var hasText = false;
      Array.prototype.forEach.call(title.childNodes, function (n) {
        if (n.nodeType === 3) {
          if (n.nodeValue !== " Open Fleet") n.nodeValue = " Open Fleet";
          hasText = true;
        }
      });
      if (!hasText) title.appendChild(document.createTextNode(" Open Fleet"));
    }
    sec.querySelectorAll("thead th").forEach(function (th) {
      if (String(th.textContent || "").trim() === "Age") th.textContent = "Cat";
    });
  }

  function add(src) {
    var base = src.split("?")[0];
    if (document.querySelector('script[src*="' + base + '"]')) return;
    var s = document.createElement("script");
    s.src = src;
    s.defer = true;
    document.head.appendChild(s);
  }

  paint();
  add("/js/club-score-edit.js?v=ccr38dbs4");
  [100, 400, 1200, 2500].forEach(function (ms) {
    window.setTimeout(paint, ms);
  });
})();
