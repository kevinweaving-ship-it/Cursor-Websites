/* Cape Classic slot: Voelklip wind dial + Wind2Speed Zeekoevlei (station 35) data. */
(function () {
  var CSS_ID = "ssa-regatta-slot-card-css";
  var ROOT_ID = "ssa-regatta-slot-card";
  var CAPE_CLASSIC_ID = "2026-09-13-zvyc-cape-classic";
  var JS_VER = "20260911w2s1";
  var PTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement("style");
    s.id = CSS_ID;
    s.textContent = [
      ".regatta-page:has(#ssa-regatta-slot-card)>.regatta-header-wrap .header{margin-bottom:0!important;}",
      ".ssa-regatta-slot-card{display:block;width:100%;order:2;margin:10px 0 0;padding:0;box-sizing:border-box;height:122px;min-height:122px;background:#fff;border:1.5px solid #1a2750;border-radius:8px;box-shadow:0 1px 3px rgba(0,31,63,.08);overflow:hidden;}",
      ".ssa-regatta-slot-card .wx-wp-top{display:flex;align-items:center;height:100%;padding:6px 8px;gap:8px;box-sizing:border-box;}",
      ".ssa-regatta-slot-card .wx-wp-comp{flex:0 0 110px;width:110px;height:110px;}",
      ".ssa-regatta-slot-card .wx-dial{display:block;width:110px;height:110px;overflow:visible;}",
      ".ssa-regatta-slot-card .wx-dial .dt{stroke:#9ca3af;stroke-width:1;}",
      ".ssa-regatta-slot-card .wx-dial .dt.card{stroke:#111;stroke-width:1.4;}",
      ".ssa-regatta-slot-card .wx-dial .darc{fill:none;stroke:#93c5fd;stroke-width:7;stroke-linecap:butt;}",
      ".ssa-regatta-slot-card .wx-dial .dhead{fill:#3b82f6;}",
      ".ssa-regatta-slot-card .wx-dial .dpt{font:700 22px Arial,Helvetica,sans-serif;fill:#15803d;}",
      ".ssa-regatta-slot-card .wx-info{flex:1 1 auto;min-width:0;display:flex;flex-direction:column;justify-content:center;gap:3px;padding-left:2px;}",
      ".ssa-regatta-slot-card .wx-ir{display:flex;justify-content:space-between;align-items:baseline;gap:6px;min-width:0;}",
      ".ssa-regatta-slot-card .wx-il{font:700 11px Arial,Helvetica,sans-serif;color:#111;white-space:nowrap;}",
      ".ssa-regatta-slot-card .wx-iv{font:700 13px Arial,Helvetica,sans-serif;color:#1a2750;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:right;}",
      ".ssa-regatta-slot-card .wx-iv.big{font-size:22px;line-height:1;}",
      ".ssa-regatta-slot-card .wx-iv.big2{font-size:16px;line-height:1.1;color:#111;}",
      ".ssa-regatta-slot-card .wx-iv small{font-size:10px;font-weight:600;color:#475569;}",
      ".ssa-regatta-slot-card .wx-ir .l{font:500 10px Arial,Helvetica,sans-serif;color:#64748b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}",
      ".ssa-regatta-slot-card .wx-ir .l b{color:#1e293b;}",
      "@media screen and (orientation:portrait) and (max-width:767px){",
      ".ssa-regatta-slot-card{margin-top:10px;}",
      ".ssa-regatta-slot-card .wx-iv.big{font-size:20px;}",
      ".ssa-regatta-slot-card .wx-iv.big2{font-size:14px;}",
      "}"
    ].join("");
    document.head.appendChild(s);
  }

  function n1(x) {
    return x == null || isNaN(x) ? "—" : String(Math.round(Number(x) * 10) / 10);
  }
  function pol(cx, cy, r, a) {
    var t = (a - 90) * Math.PI / 180;
    return [cx + r * Math.cos(t), cy + r * Math.sin(t)];
  }
  function bandCol(kn) {
    if (kn == null || isNaN(kn)) return "#94a3b8";
    if (kn < 10) return "#12b028";
    if (kn < 20) return "#e67e00";
    if (kn < 30) return "#7c3aed";
    if (kn < 50) return "#DC143C";
    return "#7f0d1f";
  }
  function dirIdx(deg) {
    if (deg == null || isNaN(deg)) return null;
    return Math.round(((Number(deg) % 360) + 360) % 360 / 22.5) % 16;
  }

  function drawDial(data) {
    var CX = 50, CY = 50, R = 44;
    var lastDeg = data.wind_dir;
    var pt = data.wind_dir_name || (lastDeg != null ? PTS[dirIdx(lastDeg)] : "");
    var svg = '<svg class="wx-dial" viewBox="0 0 100 100" aria-hidden="true">';
    var k;
    for (k = 0; k < 72; k += 1) {
      var card = k % 18 === 0;
      var q0 = pol(CX, CY, R - (card ? 7 : 4.5), k * 5);
      var q1 = pol(CX, CY, R + (card ? 2 : 0), k * 5);
      svg += '<line class="' + (card ? "dt card" : "dt") + '" x1="' + q0[0].toFixed(1) + '" y1="' + q0[1].toFixed(1) + '" x2="' + q1[0].toFixed(1) + '" y2="' + q1[1].toFixed(1) + '"/>';
    }
    var a0 = data.dir_low;
    var a1 = data.dir_high;
    if (a0 != null && a1 != null && !isNaN(a0) && !isNaN(a1)) {
      a0 = Number(a0);
      a1 = Number(a1);
      var sweep = (a1 - a0 + 360) % 360;
      if (sweep < 2) sweep = 22.5;
      var aEnd = a0 + sweep;
      var p0 = pol(CX, CY, R - 2, a0);
      var p1 = pol(CX, CY, R - 2, aEnd);
      svg += '<path class="darc" d="M' + p0[0].toFixed(1) + " " + p0[1].toFixed(1) + " A" + (R - 2) + " " + (R - 2) + " 0 " + (sweep > 180 ? 1 : 0) + " 1 " + p1[0].toFixed(1) + " " + p1[1].toFixed(1) + '"/>';
      var headAt = lastDeg != null ? Number(lastDeg) : a0;
      var hp = pol(CX, CY, R - 2, headAt);
      svg += '<g transform="translate(' + hp[0].toFixed(1) + " " + hp[1].toFixed(1) + ") rotate(" + (headAt - 90) + ')"><path class="dhead" d="M0 -12L10 0L0 12L3 0Z"/></g>';
    } else if (lastDeg != null) {
      var hp2 = pol(CX, CY, R - 2, Number(lastDeg));
      svg += '<g transform="translate(' + hp2[0].toFixed(1) + " " + hp2[1].toFixed(1) + ") rotate(" + (Number(lastDeg) - 90) + ')"><path class="dhead" d="M0 -12L10 0L0 12L3 0Z"/></g>';
    }
    svg += '<text class="dpt" x="50" y="50" text-anchor="middle" dominant-baseline="central">' + (pt || "—") + "</text></svg>";
    return svg;
  }

  function render(slot, data) {
    var wcur = data.wind_kt;
    var wgust = data.gust_kt;
    var wavg = data.avg_kt;
    var col = bandCol(wcur);
    var stamp = data.lr || "—";
    var name = data.station || "Zeekoevlei";
    slot.innerHTML =
      '<div class="wx-wp-top">' +
        '<div class="wx-wp-comp">' + drawDial(data) + "</div>" +
        '<div class="wx-info">' +
          '<div class="wx-ir"><span class="wx-il">Wind Speed</span><span class="wx-iv big" style="color:' + (wcur != null && wcur > 10 ? col : "#3b82f6") + '">' + n1(wcur) + ' <small>knots</small></span></div>' +
          '<div class="wx-ir"><span class="wx-il">GUST | AVG</span><span class="wx-iv big2">' + n1(wgust) + " | " + n1(wavg) + ' <small>knots</small></span></div>' +
          '<div class="wx-ir"><span class="l"><b>' + name + "</b> · " + (data.wind_dir_name || "—") + (data.wind_dir != null ? " " + Math.round(Number(data.wind_dir)) + "°" : "") + "</span></div>" +
          '<div class="wx-ir"><span class="l">' + stamp + "</span></div>" +
        "</div>" +
      "</div>";
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

  var loading = false;
  async function load(slot) {
    if (loading) return;
    loading = true;
    try {
      var res = await fetch("/api/wind2speed/zeekoevlei?_=" + Date.now(), {
        cache: "no-store",
        credentials: "same-origin"
      });
      if (!res.ok) throw new Error("w2s " + res.status);
      var data = await res.json();
      if (!data || data.ok === false) throw new Error((data && data.err) || "w2s fail");
      render(slot, data);
    } catch (err) {
      try { console.warn(err); } catch (e) {}
    } finally {
      loading = false;
    }
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
    el.setAttribute("aria-label", "Zeekoevlei wind");
    marine.parentNode.insertBefore(el, marine);
    syncToMarine(el, marine);
    if (typeof ResizeObserver === "function") {
      var ro = new ResizeObserver(function () { syncToMarine(el, marine); });
      ro.observe(marine);
    }
    window.addEventListener("resize", function () { syncToMarine(el, marine); });
    load(el);
    setInterval(function () { if (!document.hidden) load(el); }, 40000);
    document.addEventListener("visibilitychange", function () { if (!document.hidden) load(el); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
  window.__ssaRegattaSlotCard = JS_VER;
})();
