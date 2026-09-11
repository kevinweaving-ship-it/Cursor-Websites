/* Placeholder card: under the Cape Classic event header, above the Marine Megastore card. Empty on purpose. */
(function () {
  var CSS_ID = "ssa-regatta-slot-card-css";
  var ROOT_ID = "ssa-regatta-slot-card";
  var CAPE_CLASSIC_ID = "2026-09-13-zvyc-cape-classic";
  var JS_VER = "20260911blank3";

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement("style");
    s.id = CSS_ID;
    s.textContent = [
      ".regatta-page:has(#ssa-regatta-slot-card)>.regatta-header-wrap .header{margin-bottom:0!important;}",
      ".ssa-regatta-slot-card{display:block;width:100%;order:2;margin:10px 0 0;padding:0;box-sizing:border-box;height:122px;min-height:122px;background:#fff;border:1.5px solid #1a2750;border-radius:8px;box-shadow:0 1px 3px rgba(0,31,63,.08);}",
      "@media screen and (orientation:portrait) and (max-width:767px){",
      ".ssa-regatta-slot-card{margin-top:10px;}",
      "}"
    ].join("");
    document.head.appendChild(s);
  }

  function syncToMarine(slot, marine) {
    if (!slot || !marine) return;
    var h = Math.round(marine.getBoundingClientRect().height);
    if (h > 0) {
      slot.style.height = h + "px";
      slot.style.minHeight = h + "px";
    }
    var mt = getComputedStyle(marine).marginTop;
    if (mt) slot.style.marginTop = mt;
  }

  function mount() {
    if (document.getElementById(ROOT_ID)) return;
    var marine = document.getElementById("mmLiptonReels");
    if (!marine) return;
    if ((marine.getAttribute("data-regatta-id") || "").trim() !== CAPE_CLASSIC_ID) return;
    injectCss();
    var el = document.createElement("section");
    el.id = ROOT_ID;
    el.className = "card ssa-regatta-slot-card";
    el.setAttribute("aria-label", "Placeholder");
    marine.parentNode.insertBefore(el, marine);
    syncToMarine(el, marine);
    if (typeof ResizeObserver === "function") {
      var ro = new ResizeObserver(function () { syncToMarine(el, marine); });
      ro.observe(marine);
    }
    window.addEventListener("resize", function () { syncToMarine(el, marine); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
  window.__ssaRegattaSlotCard = JS_VER;
})();
