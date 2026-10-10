/**
 * Dam Bottle Sprints — emergency live boot.
 * Bottle logos + Open Fleet only. No observers. Does not load other JS.
 * Does not change live api.py.
 */
(function () {
  "use strict";
  var RID = "2026-10-10-hmyc-dam-bottle-sprints";
  var path = String((window.location && window.location.pathname) || "")
    .replace(/\/+$/, "")
    .toLowerCase();
  if (path !== "/regatta/" + RID && path.indexOf("/regatta/" + RID + "/") !== 0) return;

  var SRC = "/artwork/Event%20Logo/Dam-Bottle-Sprints.png";

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

  paint();
  [100, 400, 1200].forEach(function (ms) {
    window.setTimeout(paint, ms);
  });
})();
