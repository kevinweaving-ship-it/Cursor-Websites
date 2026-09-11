/* Cape Classic slot: Voelklip wind dial + Wind2Speed Zeekoevlei (station 35).
   Dial copied from live /voelklip/index.html.bak_shared_202609070100:
   72-tick compass, 16-point history marks (not min–max blob), inward FROM arrow,
   BANDS colours on arc/arrow/values. */
(function () {
  var CSS_ID = "ssa-regatta-slot-card-css";
  var ROOT_ID = "ssa-regatta-slot-card";
  var CAPE_CLASSIC_ID = "2026-09-13-zvyc-cape-classic";
  var JS_VER = "20260911w2s9";
  var PTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  var BANDS = [[0, 5, "#12b028"], [5, 11, "#2563eb"], [11, 17, "#e67e00"], [17, 23, "#7c3aed"], [23, 60, "#DC143C"]];

  function injectCss() {
    var s = document.getElementById(CSS_ID);
    if (!s) {
      s = document.createElement("style");
      s.id = CSS_ID;
      document.head.appendChild(s);
    }
    s.textContent = [
      ".regatta-page:has(#ssa-regatta-slot-card)>.regatta-header-wrap .header{margin-bottom:0!important;}",
      ".ssa-regatta-slot-card{display:flex;width:100%;order:2;margin:10px 0 0;padding:0;box-sizing:border-box;height:122px;min-height:122px;background:#fff;border:1.5px solid #1a2750;border-radius:8px;box-shadow:0 1px 3px rgba(0,31,63,.08);overflow:hidden;}",
      ".ssa-regatta-slot-card .wx-wp-top{display:flex;align-items:stretch;flex:1;height:100%;width:100%;padding:0 6px 0 0;gap:4px;box-sizing:border-box;}",
      ".ssa-regatta-slot-card .wx-wp-comp{flex:0 0 auto;height:100%;aspect-ratio:1/1;overflow:visible;}",
      ".ssa-regatta-slot-card .wx-dial{display:block;width:100%;height:100%;overflow:visible;}",
      ".ssa-regatta-slot-card .wx-spark{flex:1 1 0;min-width:48px;height:100%;display:flex;flex-direction:column;padding:6px 2px 4px;box-sizing:border-box;min-height:0;}",
      ".ssa-regatta-slot-card .wx-spark-row{flex:1 1 auto;min-height:0;display:flex;align-items:stretch;gap:3px;}",
      ".ssa-regatta-slot-card .wx-scale{flex:0 0 16px;display:flex;flex-direction:column;justify-content:space-between;align-items:flex-end;padding:1px 0;box-sizing:border-box;}",
      ".ssa-regatta-slot-card .wx-scale span{font:700 9px/1 Arial,Helvetica,sans-serif;color:#64748b;}",
      ".ssa-regatta-slot-card .wx-plot{flex:1 1 auto;min-width:0;height:100%;display:block;}",
      ".ssa-regatta-slot-card .wx-spark-x{flex:0 0 auto;display:flex;justify-content:space-between;padding:2px 0 0 19px;}",
      ".ssa-regatta-slot-card .wx-spark-x span{font:700 9px/1 Arial,Helvetica,sans-serif;color:#64748b;}",
      ".ssa-regatta-slot-card .wx-info{flex:0 0 auto;min-width:92px;height:100%;display:flex;flex-direction:column;justify-content:stretch;gap:4px;padding:8px 8px 8px 4px;box-sizing:border-box;}",
      ".ssa-regatta-slot-card .wx-dial .dt{stroke:#9ca3af;stroke-width:1;}",
      ".ssa-regatta-slot-card .wx-dial .dt.card{stroke:#111;stroke-width:1.4;}",
      ".ssa-regatta-slot-card .wx-dial .darc{fill:none;stroke:#93c5fd;stroke-width:7;stroke-linecap:butt;}",
      ".ssa-regatta-slot-card .wx-dial .darc.prev{opacity:.45;}",
      ".ssa-regatta-slot-card .wx-dial .dhead{fill:#3b82f6;}",
      ".ssa-regatta-slot-card .wx-dial .dpt{font:700 24px Arial,Helvetica,sans-serif;fill:#15803d;}",
      ".ssa-regatta-slot-card .wx-dial .ddeg{font:700 9px Arial,Helvetica,sans-serif;fill:#166534;}",
      ".ssa-regatta-slot-card .wx-ir{flex:1 1 0;display:flex;flex-direction:column;justify-content:center;align-items:flex-end;gap:2px;min-width:0;min-height:0;}",
      ".ssa-regatta-slot-card .wx-il{font:700 10px/1 Arial,Helvetica,sans-serif;color:#64748b;letter-spacing:.06em;text-transform:uppercase;white-space:nowrap;}",
      ".ssa-regatta-slot-card .wx-iv,.ssa-regatta-slot-card .wx-iv small{font:800 18px/1 Arial,Helvetica,sans-serif;white-space:nowrap;}",
      ".ssa-regatta-slot-card .wx-iv{color:#1a2750;text-align:right;}",
      ".ssa-regatta-slot-card .wx-iv small{margin-left:3px;color:inherit;font-size:11px;}",
      "@media screen and (orientation:portrait) and (max-width:767px){",
      ".ssa-regatta-slot-card{margin-top:10px;}",
      ".ssa-regatta-slot-card .wx-iv,.ssa-regatta-slot-card .wx-iv small{font-size:16px;}",
      ".ssa-regatta-slot-card .wx-iv small{font-size:10px;}",
      "}"
    ].join("");
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
    var i;
    for (i = 0; i < BANDS.length; i += 1) {
      if (kn < BANDS[i][1]) return BANDS[i][2];
    }
    return "#DC143C";
  }
  function dirIdx(deg) {
    if (deg == null || isNaN(deg)) return null;
    return Math.round((((Number(deg) % 360) + 360) % 360) / 22.5) % 16;
  }
  function recentIdx(data) {
    var last = dirIdx(data.wind_dir);
    var out = [];
    var wds = data.wds;
    var i;
    if (Array.isArray(wds)) {
      for (i = 0; i < wds.length && i < 16; i += 1) {
        if (Number(wds[i]) > 0) out.push(i);
      }
    }
    if (last != null && out.indexOf(last) === -1) out.push(last);
    return { last: last, uniq: out };
  }

  function drawDial(data) {
    var CX = 50, CY = 50, R = 44;
    var lastDeg = data.wind_dir;
    var rec = recentIdx(data);
    var dirLast = rec.last;
    var deg = lastDeg != null && !isNaN(lastDeg) ? Number(lastDeg) : (dirLast != null ? dirLast * 22.5 : null);
    var pt = data.wind_dir_name || (dirLast != null ? PTS[dirLast] : "");
    var col = bandCol(data.wind_kt);
    var svg = '<svg class="wx-dial" viewBox="-10 -10 120 120" aria-hidden="true">';
    var k;
    for (k = 0; k < 72; k += 1) {
      var card = k % 18 === 0;
      var q0 = pol(CX, CY, R - (card ? 7 : 4.5), k * 5);
      var q1 = pol(CX, CY, R + (card ? 2 : 0), k * 5);
      svg += '<line class="' + (card ? "dt card" : "dt") + '" x1="' + q0[0].toFixed(1) + '" y1="' + q0[1].toFixed(1) + '" x2="' + q1[0].toFixed(1) + '" y2="' + q1[1].toFixed(1) + '"/>';
    }
    if (dirLast != null) {
      rec.uniq.forEach(function (idx) {
        var a0 = idx * 22.5 - 11.25;
        var a1 = idx * 22.5 + 11.25;
        var p0 = pol(CX, CY, R - 2, a0);
        var p1 = pol(CX, CY, R - 2, a1);
        svg += '<path class="darc' + (idx === dirLast ? "" : " prev") + '" style="stroke:' + col + '" d="M' + p0[0].toFixed(1) + " " + p0[1].toFixed(1) + " A" + (R - 2) + " " + (R - 2) + " 0 0 1 " + p1[0].toFixed(1) + " " + p1[1].toFixed(1) + '"/>';
      });
      if (deg != null) {
        var hp = pol(CX, CY, R + 4, deg);
        svg += '<g transform="translate(' + hp[0].toFixed(1) + " " + hp[1].toFixed(1) + ") rotate(" + (deg + 180) + ')"><path class="dhead" style="fill:' + col + '" d="M0 -14L11 7L0 2.5L-11 7Z"/></g>';
      }
    }
    svg += '<text class="dpt" x="50" y="45" text-anchor="middle" dominant-baseline="central">' + (pt || "—") + "</text>";
    if (deg != null) {
      svg += '<text class="ddeg" x="50" y="64" text-anchor="middle">' + Math.round(deg) + "°</text>";
    }
    svg += "</svg>";
    return svg;
  }

  function drawSpark(data) {
    var pts = (data.hour || []).filter(function (p) { return p && p.avg_kt != null && !isNaN(p.avg_kt); });
    var html = '<div class="wx-spark" aria-label="Wind last hour">';
    if (pts.length < 2) {
      return html + "</div>";
    }
    var W = 100, H = 100, i;
    var maxKn = 10;
    for (i = 0; i < pts.length; i += 1) {
      var hi = pts[i].high_kt != null ? Number(pts[i].high_kt) : Number(pts[i].avg_kt);
      if (hi > maxKn) maxKn = hi;
    }
    maxKn = Math.max(10, Math.ceil(maxKn / 5) * 5);
    var ticks = [];
    var step = maxKn <= 20 ? 5 : 10;
    for (i = maxKn; i >= 0; i -= step) ticks.push(i);
    function x(idx) { return (W * idx) / (pts.length - 1); }
    function y(kn) { return H * (1 - Math.max(0, Math.min(maxKn, Number(kn))) / maxKn); }
    var svg = '<svg class="wx-plot" viewBox="0 0 ' + W + " " + H + '" preserveAspectRatio="none" aria-hidden="true">';
    BANDS.forEach(function (b) {
      var y0 = y(Math.min(maxKn, b[1]));
      var y1 = y(Math.min(maxKn, b[0]));
      if (y1 <= y0) return;
      svg += '<rect x="0" y="' + y0.toFixed(1) + '" width="' + W + '" height="' + (y1 - y0).toFixed(1) + '" fill="' + b[2] + '" opacity=".22"/>';
    });
    ticks.forEach(function (t) {
      if (t === 0 || t === maxKn) return;
      var yy = y(t).toFixed(1);
      svg += '<line x1="0" y1="' + yy + '" x2="' + W + '" y2="' + yy + '" stroke="#fff" stroke-width="0.6" vector-effect="non-scaling-stroke"/>';
    });
    var highD = "", avgD = "";
    for (i = 0; i < pts.length; i += 1) {
      var xi = x(i).toFixed(1);
      avgD += (i ? "L" : "M") + xi + " " + y(pts[i].avg_kt).toFixed(1);
      highD += (i ? "L" : "M") + xi + " " + y(pts[i].high_kt != null ? pts[i].high_kt : pts[i].avg_kt).toFixed(1);
    }
    var last = pts[pts.length - 1];
    var area = highD + "L" + x(pts.length - 1).toFixed(1) + " " + H + "L0 " + H + "Z";
    svg += '<path d="' + area + '" fill="#1a2750" opacity=".12"/>';
    svg += '<path d="' + highD + '" fill="none" stroke="#64748b" stroke-width="1.4" stroke-dasharray="3 2" vector-effect="non-scaling-stroke"/>';
    svg += '<path d="' + avgD + '" fill="none" stroke="#1a2750" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>';
    svg += '<circle cx="' + x(pts.length - 1).toFixed(1) + '" cy="' + y(last.avg_kt).toFixed(1) + '" r="1.8" fill="' + bandCol(last.avg_kt) + '" vector-effect="non-scaling-stroke"/>';
    svg += "</svg>";
    var scale = '<div class="wx-scale">' + ticks.map(function (t) { return "<span>" + t + "</span>"; }).join("") + "</div>";
    html += '<div class="wx-spark-row">' + scale + svg + "</div>";
    html += '<div class="wx-spark-x"><span>1h</span><span>now</span></div>';
    return html + "</div>";
  }

  function render(slot, data) {
    var wnow = data.wind_kt;
    var wavg = data.avg_kt;
    var whigh = data.high_kt != null ? data.high_kt : data.gust_kt;
    var colN = bandCol(wnow);
    var colA = bandCol(wavg);
    var colH = bandCol(whigh);
    slot.innerHTML =
      '<div class="wx-wp-top">' +
        '<div class="wx-wp-comp">' + drawDial(data) + "</div>" +
        drawSpark(data) +
        '<div class="wx-info">' +
          '<div class="wx-ir"><span class="wx-il">Now</span><span class="wx-iv" style="color:' + colN + '">' + n1(wnow) + " <small>kn</small></span></div>" +
          '<div class="wx-ir"><span class="wx-il">Avg</span><span class="wx-iv" style="color:' + colA + '">' + n1(wavg) + " <small>kn</small></span></div>" +
          '<div class="wx-ir"><span class="wx-il">High</span><span class="wx-iv" style="color:' + colH + '">' + n1(whigh) + " <small>kn</small></span></div>" +
        "</div>" +
      "</div>";
  }

  function fitGauge(slot) {
    var comp = slot && slot.querySelector(".wx-wp-comp");
    if (!slot || !comp) return;
    var h = slot.clientHeight;
    if (h > 0) {
      comp.style.height = h + "px";
      comp.style.width = h + "px";
    }
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
    fitGauge(slot);
  }

  var loading = false;
  var pollTimer = null;
  var POLL_MS = 40000;

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
      fitGauge(slot);
      var next = Number(data.interval);
      if (next >= 10000 && next <= 120000 && next !== POLL_MS) {
        POLL_MS = next;
        if (pollTimer) {
          clearInterval(pollTimer);
          pollTimer = setInterval(function () { if (!document.hidden) load(slot); }, POLL_MS);
        }
      }
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
    pollTimer = setInterval(function () { if (!document.hidden) load(el); }, POLL_MS);
    document.addEventListener("visibilitychange", function () { if (!document.hidden) load(el); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
  window.__ssaRegattaSlotCard = JS_VER;
})();
