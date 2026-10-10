/* Parent-truth on /regatta/{id}: Event Logo left is the only event mark.
 * Single-class named events: hide superseded Class Logo in class-header / fleet title.
 * Multi-class events keep fleet class marks. Do not edit gold api.py.
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
  function classMarkImgs() {
    var out = [];
    var nodes = document.querySelectorAll(".class-header-logo-img, .rs-fleet-title-logo");
    for (var i = 0; i < nodes.length; i++) {
      var src = nodes[i].getAttribute("src") || nodes[i].src || "";
      if (isClassLogo(src)) out.push(nodes[i]);
    }
    return out;
  }
  function uniqueClassSrcs(imgs) {
    var seen = {};
    for (var i = 0; i < imgs.length; i++) {
      var key = norm(imgs[i].getAttribute("src") || imgs[i].src || "");
      if (key) seen[key] = 1;
    }
    return Object.keys(seen);
  }
  function hide(el) {
    if (!el) return;
    el.style.display = "none";
    el.setAttribute("data-sa-event-logo-superseded", "1");
    var col = el.closest ? el.closest(".class-header-logo-col") : null;
    if (col) col.style.display = "none";
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
    var marks = classMarkImgs();
    if (uniqueClassSrcs(marks).length !== 1) return true;
    for (var i = 0; i < marks.length; i++) hide(marks[i]);
    document.documentElement.setAttribute("data-sa-event-logo-parent", "1");
    return true;
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
