/* Parent-truth on /regatta/{id}: Event Logo left is the only event mark.
 * Single-class named events: replace Open/class mark in the fleet header
 * left slot with the same Event Logo, smaller and in line. Do not leave
 * that slot empty. Multi-class events keep fleet class marks.
 * Do not edit gold api.py.
 */
(function () {
  function norm(path) {
    try {
      return decodeURIComponent(String(path || "").split("?")[0]).toLowerCase();
    } catch (_) {
      return String(path || "").split("?")[0].toLowerCase();
    }
  }
  function isEventLogo(path) {
    return norm(path).indexOf("/artwork/event logo/") !== -1;
  }
  function isClassLogo(path) {
    return norm(path).indexOf("/artwork/class logo/") !== -1;
  }
  function leftImg() {
    return document.querySelector(
      ".regatta-header-logo-col img.regatta-header-left-logo-img, .regatta-header-logo-col img.regatta-header-logo-img"
    );
  }
  function fleetMarkImgs() {
    var out = [];
    var nodes = document.querySelectorAll(
      ".class-header-logo-col img, .fleet-title-with-logo img, img.rs-fleet-title-logo"
    );
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].closest && nodes[i].closest(".class-header-club-logo-col")) continue;
      out.push(nodes[i]);
    }
    return out;
  }
  function uniqueClassSrcs(imgs) {
    var seen = {};
    for (var i = 0; i < imgs.length; i++) {
      var src = imgs[i].getAttribute("src") || imgs[i].src || "";
      if (!isClassLogo(src)) continue;
      var key = norm(src);
      if (key) seen[key] = 1;
    }
    return Object.keys(seen);
  }
  function showCol(img) {
    if (!img) return;
    img.style.display = "";
    img.style.visibility = "";
    img.removeAttribute("data-sa-event-logo-superseded");
    var col = img.closest ? img.closest(".class-header-logo-col") : null;
    if (col) {
      col.style.display = "";
      col.style.visibility = "";
      col.setAttribute("data-sa-event-logo-fleet", "1");
    }
  }
  function paintFleetEventLogo(eventSrc) {
    var marks = fleetMarkImgs();
    if (uniqueClassSrcs(marks).length > 1) return;
    for (var i = 0; i < marks.length; i++) {
      var img = marks[i];
      var cur = img.getAttribute("src") || img.src || "";
      if (isClassLogo(cur) || !cur || img.getAttribute("data-sa-event-logo-superseded") === "1") {
        img.src = eventSrc;
        img.alt = img.alt && !/open/i.test(img.alt) ? img.alt : "Event";
        img.removeAttribute("title");
      }
      showCol(img);
    }
    document.documentElement.setAttribute("data-sa-event-logo-parent", "1");
  }
  function apply() {
    var left = leftImg();
    if (!left) return false;
    var src = left.getAttribute("src") || left.src || "";
    if (!isEventLogo(src)) return false;
    left.setAttribute("loading", "eager");
    left.setAttribute("fetchpriority", "high");
    left.loading = "eager";
    try {
      left.fetchPriority = "high";
    } catch (_) {}
    paintFleetEventLogo(src);
    return true;
  }
  if (!document.getElementById("sa-parent-event-logo-fleet-css")) {
    var css = document.createElement("style");
    css.id = "sa-parent-event-logo-fleet-css";
    css.textContent =
      ".class-header-logo-col[data-sa-event-logo-fleet='1']{display:flex!important;visibility:visible!important;align-items:center;}" +
      ".class-header-logo-col[data-sa-event-logo-fleet='1'] img{display:block!important;visibility:visible!important;" +
      "height:auto;width:auto;max-height:min(18vw,80px);max-width:min(42vw,220px);object-fit:contain;}" +
      "#dam-bottle-open-fleet .table-container,#dam-bottle-open-fleet .table-wrapper{" +
      "overflow-x:auto;-webkit-overflow-scrolling:touch;width:100%!important;max-width:100%;box-sizing:border-box;}" +
      "#dam-bottle-open-fleet table.fleet-results-table{width:100%!important;min-width:100%!important;max-width:none;box-sizing:border-box;}";
    (document.head || document.documentElement).appendChild(css);
  }
  apply();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply);
  }
  try {
    var mo = new MutationObserver(function () {
      apply();
    });
    mo.observe(document.documentElement, { childList: true, subtree: true });
    setTimeout(function () {
      try {
        mo.disconnect();
      } catch (_) {}
    }, 8000);
  } catch (_) {}
})();
