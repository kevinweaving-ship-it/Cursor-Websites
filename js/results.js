/**
 * SailingSA SPA results engine — globals only (no IIFE / no module scope).
 * Inline HTML must use window.resolveResultsEngine() — never bare engine globals.
 */

window.resultsEngine = window.resultsEngine || {};
window.seriesResults = window.seriesResults || {};

Object.assign(window.seriesResults, {
  version: 1,
  name: 'seriesResults',
});

Object.assign(window.resultsEngine, {
  version: 1,
  name: 'sailingsa-results-engine',
});

/** engine.seriesResults() returns the series results data object */
window.resultsEngine.seriesResults = function () {
  return window.seriesResults;
};

if (typeof window.resultsEngine.render !== 'function') {
  window.resultsEngine.render = function () {
    console.warn('resultsEngine.render: no-op (wire implementation in results engine)');
  };
}

if (typeof window.showError !== 'function') {
  window.showError = function (message) {
    var m = message != null ? String(message) : 'Error';
    console.error(m);
    try {
      alert(m);
    } catch (e) {}
  };
}

/**
 * Resolve results engine: same window first, then parent frame (iframe).
 * @returns {object|null}
 */
window.resolveResultsEngine = function () {
  try {
    if (window.resultsEngine && window.resultsEngine.version !== undefined) {
      return window.resultsEngine;
    }
  } catch (e) {}
  try {
    if (window.parent && window.parent !== window) {
      var p = window.parent;
      if (p.resultsEngine && p.resultsEngine.version !== undefined) {
        return p.resultsEngine;
      }
    }
  } catch (e) {
    /* cross-origin parent */
  }
  return null;
};

/**
 * @returns {boolean} false if engine missing
 */
window.assertResultsEngineOrAbort = function () {
  const engine = typeof window.resolveResultsEngine === 'function' ? window.resolveResultsEngine() : null;
  if (!engine) {
    console.error('Results engine missing');
    if (typeof window.showError === 'function') {
      window.showError('Results engine not loaded');
    }
    return false;
  }
  return true;
};

/* Print / PDF sheets (class-results + full results): split OCF like DNC, always print full expanded. */
(function () {
  var VER = "PRINT_FULL_2";
  var LITE_IDS = ["table-lite", "sections-lite", "table-lite-open-fleet-full"];
  var FULL_IDS = ["table-expanded", "sections-expanded", "table-expanded-open-fleet-full"];
  var CODES = /^(DNC|DNS|DNF|DNR|RET|DSQ|UFD|BFD|DPI|OCS|OCF|NSC|DNE|TLE)$/i;
  var NUM_CODE = /^(\d+(?:\.\d+)?)\s+(DNC|DNS|DNF|DNR|RET|DSQ|UFD|BFD|DPI|OCS|OCF|NSC|DNE|TLE)$/i;
  var CSS =
    "td.code{font-size:10px;line-height:1.15;white-space:normal!important}" +
    "td.code .wc-score{display:block;font-size:10px;font-weight:700;color:#1a2750;line-height:1.15}" +
    "td.code .wc-code{display:block;font-size:6px;font-weight:700;color:#d32f2f;line-height:1;margin:0}" +
    "@media print{" +
    ".view-toggle{display:none!important}" +
    "#table-lite,#sections-lite,#table-lite-open-fleet-full{display:none!important;visibility:hidden!important}" +
    "#table-expanded,#sections-expanded,#table-expanded-open-fleet-full{display:block!important;visibility:visible!important}" +
    ".results-table-view{display:none!important}" +
    "#table-expanded.results-table-view,#sections-expanded.results-table-view,#table-expanded-open-fleet-full.results-table-view{display:block!important}" +
    "#table-expanded .table-expanded-right,#sections-expanded .table-expanded-right,#table-expanded-open-fleet-full .table-expanded-right{overflow:visible!important}" +
    "td.code .wc-score{display:block;font-size:10px;font-weight:700;color:#1a2750}" +
    "td.code .wc-code{display:block;font-size:6px;font-weight:700;color:#d32f2f;margin:0}" +
    "}";

  function injectCss() {
    if (document.getElementById("ssa-print-ocf-css")) return;
    var s = document.createElement("style");
    s.id = "ssa-print-ocf-css";
    s.setAttribute("data-ssa", VER);
    s.textContent = CSS;
    (document.head || document.documentElement).appendChild(s);
  }

  function splitCodes(root) {
    var scope = root || document;
    var cells = scope.querySelectorAll(
      "#content td, #table-expanded td, #sections-expanded td, #table-expanded-open-fleet-full td, #table-lite td, #sections-lite td, #table-lite-open-fleet-full td"
    );
    for (var i = 0; i < cells.length; i++) {
      var td = cells[i];
      if (td.querySelector(".wc-code")) continue;
      var raw = String(td.textContent || "").replace(/\u00a0/g, " ").trim();
      var disc = raw.charAt(0) === "(" && raw.slice(-1) === ")";
      var src = disc ? raw.slice(1, -1).trim() : raw;
      var m = src.match(NUM_CODE);
      var codeOnly = !m && CODES.test(src);
      if (!m && !codeOnly) continue;
      td.classList.add("code");
      if (disc) td.classList.add("disc");
      if (m) {
        td.innerHTML =
          '<span class="wc-score">' +
          m[1] +
          '</span><span class="wc-code">' +
          m[2].toUpperCase() +
          "</span>";
      } else {
        td.innerHTML = '<span class="wc-code">' + src.toUpperCase() + "</span>";
      }
    }
  }

  function showFullResults() {
    var i;
    for (i = 0; i < LITE_IDS.length; i++) {
      var lite = document.getElementById(LITE_IDS[i]);
      if (!lite) continue;
      lite.classList.remove("active");
      lite.style.setProperty("display", "none", "important");
    }
    for (i = 0; i < FULL_IDS.length; i++) {
      var full = document.getElementById(FULL_IDS[i]);
      if (!full) continue;
      full.classList.add("active");
      full.style.setProperty("display", "block", "important");
      var rights = full.querySelectorAll(".table-expanded-right");
      for (var r = 0; r < rights.length; r++) {
        rights[r].style.setProperty("overflow", "visible", "important");
      }
    }
  }

  function preparePrint() {
    injectCss();
    showFullResults();
    splitCodes(document);
  }

  function run() {
    injectCss();
    splitCodes(document);
  }

  function boot() {
    injectCss();
    run();
    document.addEventListener("DOMContentLoaded", run);
    window.addEventListener("beforeprint", preparePrint);
    if (window.matchMedia) {
      try {
        var mq = window.matchMedia("print");
        var onMq = function (e) {
          if (e && e.matches) preparePrint();
        };
        if (mq.addEventListener) mq.addEventListener("change", onMq);
        else if (mq.addListener) mq.addListener(onMq);
      } catch (e) {}
    }
    var origPrint = window.print;
    window.print = function () {
      preparePrint();
      return origPrint.apply(this, arguments);
    };
    var target = document.getElementById("content") || document.body;
    if (target && window.MutationObserver) {
      var t;
      new MutationObserver(function () {
        window.clearTimeout(t);
        t = window.setTimeout(run, 0);
      }).observe(target, { childList: true, subtree: true });
    }
    window.addEventListener(
      "message",
      function (e) {
        if (!e.data) return;
        if (e.data.type === "captureSheet" || e.data.type === "setView") run();
      },
      true
    );
  }
  boot();
})();
