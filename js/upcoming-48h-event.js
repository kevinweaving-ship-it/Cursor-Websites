/**
 * Hub: 48h banner, then the Cape Classic page stack (one below the other):
 * event header, wind bar, MM + Live Cam strip. Any of the 3 opens
 * /regatta/2026-09-13-zvyc-cape-classic. Compact, mobile-portrait first.
 *
 * Visible on hub home only, when that event is loaded and now is within
 * 48 hours before start through event end (Africa/Johannesburg).
 *
 * Logged-in home sailor card below Regatta search is parked (not deleted)
 * so it can be restored. Set HIDE_LOGGED_IN_HOME_CARD = false to show it again.
 */
(function () {
  "use strict";

  var JS_VER = "20260911u48c";
  var ROOT_ID = "ssa-upcoming-48h";
  var PARK_ID = "ssa-saved-logged-in-home-card";
  var CSS_ID = "ssa-upcoming-48h-css";
  var HIDE_LOGGED_IN_HOME_CARD = true;
  var EVENT_HREF = "/regatta/2026-09-13-zvyc-cape-classic";
  var EVENT_ID = "2026-09-13-zvyc-cape-classic";
  var START_MS = Date.parse("2026-09-12T08:00:00+02:00");
  var END_MS = Date.parse("2026-09-13T17:00:00+02:00");
  var WINDOW_MS = 48 * 60 * 60 * 1000;
  var PTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  var BANDS = [[0, 5, "#12b028"], [5, 11, "#2563eb"], [11, 17, "#e67e00"], [17, 23, "#7c3aed"], [23, 60, "#DC143C"]];
  var windSlot = null;
  var windTimer = null;
  var windLoading = false;

  function isHubHome() {
    try {
      var path = String((window.location && window.location.pathname) || "/").replace(/\/+$/, "") || "/";
      if (path.indexOf("/sailor/") === 0) return false;
      if (path.indexOf("/class/") === 0) return false;
      if (path.indexOf("/regatta/") === 0) return false;
      if (path.indexOf("/club/") === 0) return false;
      if (path.indexOf("/events") === 0) return false;
      return path === "/" || path === "/index.html" || path === "/blank.html";
    } catch (e) {
      return false;
    }
  }

  function inFortyEightHourWindow(nowMs) {
    var now = nowMs != null ? nowMs : Date.now();
    if (!START_MS || !END_MS) return false;
    return now >= START_MS - WINDOW_MS && now <= END_MS;
  }

  function sailorSearchHasQuery() {
    try {
      var a = document.getElementById("sailor-search-input");
      var b = document.getElementById("temp-landing-regatta-input");
      if (a && String(a.value || "").trim()) return true;
      if (b && String(b.value || "").trim()) return true;
    } catch (e) {}
    return false;
  }

  function injectCss() {
    var s = document.getElementById(CSS_ID);
    if (!s) {
      s = document.createElement("style");
      s.id = CSS_ID;
      document.head.appendChild(s);
    }
    s.textContent = [
      ".ssa-upcoming-48h{width:100%;max-width:100%;margin:6px 0 8px;}",
      ".ssa-upcoming-48h[hidden]{display:none!important;}",
      ".ssa-upcoming-48h .card{margin:0!important;padding:0!important;}",
      ".ssa-upcoming-48h-banner{display:block;width:100%;height:auto;border-radius:8px;margin:0;}",
      ".ssa-upcoming-48h-cards{display:flex;flex-direction:column;gap:6px;margin:6px 0 0;align-items:stretch;}",
      ".ssa-upcoming-48h-card{display:block;width:100%;overflow:hidden;text-decoration:none;color:inherit;background:#fff;border:2px solid #1a2750;border-radius:8px;box-shadow:0 1px 3px rgba(0,31,63,.08);box-sizing:border-box;}",
      ".ssa-upcoming-48h-header{display:grid;grid-template-columns:minmax(0,auto) minmax(0,3fr) minmax(0,auto);align-items:center;column-gap:6px;row-gap:0;padding:4px 6px;}",
      ".ssa-upcoming-48h-logo-col,.ssa-upcoming-48h-club-col{display:flex;align-items:center;min-width:0;}",
      ".ssa-upcoming-48h-logo-col{justify-content:flex-start;}",
      ".ssa-upcoming-48h-club-col{justify-content:flex-end;}",
      ".ssa-upcoming-48h-logo-col img,.ssa-upcoming-48h-club-col img{display:block;max-height:72px;max-width:96px;width:auto;height:auto;object-fit:contain;pointer-events:none;}",
      ".ssa-upcoming-48h-main-col{min-width:0;text-align:center;}",
      ".ssa-upcoming-48h-name{font:700 clamp(11px,3.2vw,18px)/1.2 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1a2750;margin:0 0 2px;}",
      ".ssa-upcoming-48h-host,.ssa-upcoming-48h-venue{font:600 clamp(9px,2.5vw,13px)/1.2 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1a2750;margin:0;}",
      ".ssa-upcoming-48h-status,.ssa-upcoming-48h-entries{font:400 clamp(8px,2.2vw,12px)/1.2 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#334155;margin:1px 0 0;}",
      ".ssa-upcoming-48h-wx{height:96px;padding:0 4px 0 0;display:flex;align-items:stretch;gap:4px;box-sizing:border-box;}",
      ".ssa-upcoming-48h-wx .wx-wp-comp{flex:0 0 auto;height:100%;aspect-ratio:1/1;}",
      ".ssa-upcoming-48h-wx .wx-dial{display:block;width:100%;height:100%;overflow:visible;}",
      ".ssa-upcoming-48h-wx .wx-spark{flex:1 1 0;min-width:36px;height:100%;display:flex;flex-direction:column;padding:4px 2px 2px;box-sizing:border-box;min-height:0;}",
      ".ssa-upcoming-48h-wx .wx-spark-row{flex:1 1 auto;min-height:0;display:flex;align-items:stretch;gap:3px;}",
      ".ssa-upcoming-48h-wx .wx-scale{flex:0 0 14px;display:flex;flex-direction:column;justify-content:space-between;align-items:flex-end;padding:1px 0;}",
      ".ssa-upcoming-48h-wx .wx-scale span{font:700 8px/1 Arial,Helvetica,sans-serif;color:#64748b;}",
      ".ssa-upcoming-48h-wx .wx-plot{flex:1 1 auto;min-width:0;height:100%;display:block;}",
      ".ssa-upcoming-48h-wx .wx-spark-x{flex:0 0 auto;display:flex;justify-content:space-between;padding:1px 0 0 17px;}",
      ".ssa-upcoming-48h-wx .wx-spark-x span{font:700 8px/1 Arial,Helvetica,sans-serif;color:#64748b;}",
      ".ssa-upcoming-48h-wx .wx-info{flex:0 0 auto;min-width:78px;height:100%;display:flex;flex-direction:column;justify-content:stretch;gap:4px;padding:6px 6px 6px 2px;box-sizing:border-box;}",
      ".ssa-upcoming-48h-wx .wx-dial .dt{stroke:#9ca3af;stroke-width:1;}",
      ".ssa-upcoming-48h-wx .wx-dial .dt.card{stroke:#111;stroke-width:1.4;}",
      ".ssa-upcoming-48h-wx .wx-dial .darc{fill:none;stroke:#93c5fd;stroke-width:7;stroke-linecap:butt;}",
      ".ssa-upcoming-48h-wx .wx-dial .darc.prev{opacity:.45;}",
      ".ssa-upcoming-48h-wx .wx-dial .dhead{fill:#3b82f6;}",
      ".ssa-upcoming-48h-wx .wx-dial .dpt{font:700 18px Arial,Helvetica,sans-serif;fill:#15803d;}",
      ".ssa-upcoming-48h-wx .wx-dial .ddeg{font:700 13px Arial,Helvetica,sans-serif;fill:#166534;}",
      ".ssa-upcoming-48h-wx .wx-ir{flex:1 1 0;display:flex;flex-direction:row;justify-content:flex-end;align-items:baseline;gap:4px;min-width:0;}",
      ".ssa-upcoming-48h-wx .wx-il,.ssa-upcoming-48h-wx .wx-iv,.ssa-upcoming-48h-wx .wx-iv small{font:800 14px/1 Arial,Helvetica,sans-serif;white-space:nowrap;}",
      ".ssa-upcoming-48h-wx .wx-il{color:#334155;}",
      ".ssa-upcoming-48h-wx .wx-iv{text-align:right;}",
      ".ssa-upcoming-48h-media-row{display:flex;flex-wrap:nowrap;align-items:stretch;gap:6px;height:76px;padding:4px;box-sizing:border-box;background:#001f3f;}",
      ".ssa-upcoming-48h-mm{flex:0 0 auto;height:100%;aspect-ratio:320/213;overflow:hidden;border-radius:4px;background:#001f3f;}",
      ".ssa-upcoming-48h-mm img{display:block;width:100%;height:100%;object-fit:cover;pointer-events:none;}",
      ".ssa-upcoming-48h-cam{flex:0 0 auto;height:100%;aspect-ratio:16/9;position:relative;overflow:hidden;border-radius:4px;background:#000;}",
      ".ssa-upcoming-48h-cam img{display:block;width:100%;height:100%;object-fit:cover;pointer-events:none;}",
      ".ssa-upcoming-48h-ph{flex:1 1 0;min-width:0;background:#0a1630;border-radius:4px;}",
      ".ssa-upcoming-48h-cam-chrome{position:absolute;top:4px;left:4px;display:flex;align-items:center;gap:4px;pointer-events:none;}",
      ".ssa-upcoming-48h-cam-chrome img{width:22px;height:22px;object-fit:contain;border-radius:3px;}",
      ".ssa-upcoming-48h-cam-copy{color:#fff;font:700 9px/1.1 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;text-shadow:0 1px 2px rgba(0,0,0,.65);}",
      ".ssa-upcoming-48h-cam-sub{font-weight:600;opacity:.9;}",
      ".ssa-upcoming-48h-play{position:absolute;left:50%;top:50%;width:28px;height:28px;margin:-14px 0 0 -14px;border-radius:50%;background:rgba(0,0,0,.55);pointer-events:none;}",
      ".ssa-upcoming-48h-play:after{content:'';position:absolute;left:10px;top:8px;border-style:solid;border-width:6px 0 6px 10px;border-color:transparent transparent transparent #fff;}",
      "#ssa-saved-logged-in-home-card[hidden]{display:none!important;}",
      "body.ssa-hub-48h-no-home-profile .search-to-profile-separator{display:none;}",
      "body.ssa-hub-48h-no-home-profile #sailor-search-results:not([data-ssa-search-list='1']){display:none!important;}",
      "@media screen and (min-width:768px){",
      ".ssa-upcoming-48h-wx{height:110px;}",
      ".ssa-upcoming-48h-media-row{height:88px;}",
      ".ssa-upcoming-48h-wx .wx-il,.ssa-upcoming-48h-wx .wx-iv,.ssa-upcoming-48h-wx .wx-iv small{font-size:16px;}",
      "}",
      "@media screen and (max-width:767px){",
      ".ssa-upcoming-48h-header{grid-template-columns:minmax(0,min(22vw,72px)) minmax(0,1fr) minmax(0,min(22vw,72px));column-gap:3px;padding:3px;}",
      ".ssa-upcoming-48h-logo-col img,.ssa-upcoming-48h-club-col img{max-height:min(12vw,44px);max-width:min(18vw,72px);}",
      ".ssa-upcoming-48h-ph{display:none;}",
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
      svg += '<text class="ddeg" x="50" y="70" text-anchor="middle">' + Math.round(deg) + "°</text>";
    }
    svg += "</svg>";
    return svg;
  }

  function drawSpark(data) {
    var pts = (data.hour || []).filter(function (p) { return p && p.avg_kt != null && !isNaN(p.avg_kt); });
    var html = '<div class="wx-spark" aria-hidden="true">';
    if (pts.length < 2) return html + "</div>";
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
    var highD = "", avgD = "";
    for (i = 0; i < pts.length; i += 1) {
      var xi = x(i).toFixed(1);
      avgD += (i ? "L" : "M") + xi + " " + y(pts[i].avg_kt).toFixed(1);
      highD += (i ? "L" : "M") + xi + " " + y(pts[i].high_kt != null ? pts[i].high_kt : pts[i].avg_kt).toFixed(1);
    }
    var last = pts[pts.length - 1];
    svg += '<path d="' + highD + "L" + x(pts.length - 1).toFixed(1) + " " + H + "L0 " + H + 'Z" fill="#1a2750" opacity=".12"/>';
    svg += '<path d="' + highD + '" fill="none" stroke="#64748b" stroke-width="1.4" stroke-dasharray="3 2" vector-effect="non-scaling-stroke"/>';
    svg += '<path d="' + avgD + '" fill="none" stroke="#1a2750" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>';
    svg += '<circle cx="' + x(pts.length - 1).toFixed(1) + '" cy="' + y(last.avg_kt).toFixed(1) + '" r="1.8" fill="' + bandCol(last.avg_kt) + '" vector-effect="non-scaling-stroke"/>';
    svg += "</svg>";
    html += '<div class="wx-spark-row"><div class="wx-scale">' + ticks.map(function (t) { return "<span>" + t + "</span>"; }).join("") + "</div>" + svg + "</div>";
    html += '<div class="wx-spark-x"><span>1h</span><span>now</span></div>';
    return html + "</div>";
  }

  function renderWind(slot, data) {
    var wnow = data.wind_kt;
    var wavg = data.avg_kt;
    var whigh = data.high_kt != null ? data.high_kt : data.gust_kt;
    slot.innerHTML =
      '<div class="ssa-upcoming-48h-wx">' +
        '<div class="wx-wp-comp">' + drawDial(data) + "</div>" +
        drawSpark(data) +
        '<div class="wx-info">' +
          '<div class="wx-ir"><span class="wx-il">Now</span><span class="wx-iv" style="color:' + bandCol(wnow) + '">' + n1(wnow) + " <small>kn</small></span></div>" +
          '<div class="wx-ir"><span class="wx-il">Avg</span><span class="wx-iv" style="color:' + bandCol(wavg) + '">' + n1(wavg) + " <small>kn</small></span></div>" +
          '<div class="wx-ir"><span class="wx-il">High</span><span class="wx-iv" style="color:' + bandCol(whigh) + '">' + n1(whigh) + " <small>kn</small></span></div>" +
        "</div>" +
      "</div>";
  }

  function loadWind() {
    if (!windSlot || windLoading) return;
    windLoading = true;
    fetch("/api/wind2speed/zeekoevlei?_=" + Date.now(), { cache: "no-store", credentials: "same-origin" })
      .then(function (res) {
        if (!res.ok) throw new Error("w2s " + res.status);
        return res.json();
      })
      .then(function (data) {
        if (!data || data.ok === false) throw new Error("w2s fail");
        renderWind(windSlot, data);
      })
      .catch(function () {})
      .then(function () { windLoading = false; });
  }

  function cardsHtml() {
    return (
      '<img class="ssa-upcoming-48h-banner" src="/assets/upcoming-48h-banner.png" alt="Upcoming event(s) in the next 48 hours">' +
      '<div class="ssa-upcoming-48h-cards">' +
        '<a class="card ssa-upcoming-48h-card ssa-upcoming-48h-header" href="' + EVENT_HREF + '" aria-label="2026-09-13 ZVYC Cape Classic">' +
          '<div class="ssa-upcoming-48h-logo-col"><img src="/artwork/Event%20Logo/Cape-Classic-Series.png?v=20260827a" alt=""></div>' +
          '<div class="ssa-upcoming-48h-main-col">' +
            '<div class="ssa-upcoming-48h-name">2026-09-13 ZVYC Cape Classic</div>' +
            '<div class="ssa-upcoming-48h-host">Host: ZVYC - Zeekoe Vlei Yacht Club</div>' +
            '<div class="ssa-upcoming-48h-venue">Venue : Zeekoe Vlei Yacht Club</div>' +
            '<div class="ssa-upcoming-48h-status">Results are Provisional as at 13 September 2026 at 17:30</div>' +
            '<div class="ssa-upcoming-48h-entries">Total Entries = 51</div>' +
          "</div>" +
          '<div class="ssa-upcoming-48h-club-col"><img src="/artwork/Club%20Logo/ZVYC.png" alt=""></div>' +
        "</a>" +
        '<a class="card ssa-upcoming-48h-card" href="' + EVENT_HREF + '" aria-label="Zeekoevlei wind — open ZVYC Cape Classic">' +
          '<div class="ssa-upcoming-48h-wx-host" data-ssa-48h-wind></div>' +
        "</a>" +
        '<a class="card ssa-upcoming-48h-card" href="' + EVENT_HREF + '" aria-label="Marine Megastore and ZVYC Live Cam — open ZVYC Cape Classic">' +
          '<div class="ssa-upcoming-48h-media-row">' +
            '<div class="ssa-upcoming-48h-mm"><img src="/assets/adverts/mm-powered-by-coming-soon.jpg" alt="Powered by Marine Megastore Coming Soon"></div>' +
            '<div class="ssa-upcoming-48h-cam">' +
              '<img src="/api/regatta/' + EVENT_ID + '/zvyc-live-cam-thumb?t=' + Date.now() + '" alt="ZVYC Live Cam">' +
              '<div class="ssa-upcoming-48h-cam-chrome">' +
                '<img src="/artwork/Club%20Logo/ZVYC.png" alt="">' +
                '<div class="ssa-upcoming-48h-cam-copy">ZVYC Live Cam<div class="ssa-upcoming-48h-cam-sub">Zeekoevlei · live</div></div>' +
              "</div>" +
              '<span class="ssa-upcoming-48h-play" aria-hidden="true"></span>' +
            "</div>" +
            '<span class="ssa-upcoming-48h-ph" aria-hidden="true"></span>' +
            '<span class="ssa-upcoming-48h-ph" aria-hidden="true"></span>' +
            '<span class="ssa-upcoming-48h-ph" aria-hidden="true"></span>' +
            '<span class="ssa-upcoming-48h-ph" aria-hidden="true"></span>' +
          "</div>" +
        "</a>" +
      "</div>"
    );
  }

  function ensurePark() {
    var park = document.getElementById(PARK_ID);
    if (park) return park;
    park = document.createElement("div");
    park.id = PARK_ID;
    park.hidden = true;
    park.setAttribute("data-ssa-saved", "logged-in-home-profile");
    var results = document.getElementById("sailor-search-results");
    if (results && results.parentNode) {
      results.parentNode.insertBefore(park, results.nextSibling);
    } else {
      document.body.appendChild(park);
    }
    return park;
  }

  function parkLoggedInHomeCard() {
    if (!HIDE_LOGGED_IN_HOME_CARD || !isHubHome() || sailorSearchHasQuery()) {
      document.body.classList.remove("ssa-hub-48h-no-home-profile");
      var resultsLive = document.getElementById("sailor-search-results");
      if (resultsLive && sailorSearchHasQuery()) resultsLive.setAttribute("data-ssa-search-list", "1");
      return;
    }
    var results = document.getElementById("sailor-search-results");
    if (!results) return;
    results.removeAttribute("data-ssa-search-list");
    var card = results.querySelector(".sa-approved-sailor-card");
    if (!card) {
      if (!results.querySelector(".profile-card")) {
        document.body.classList.add("ssa-hub-48h-no-home-profile");
        results.style.display = "none";
      }
      return;
    }
    var park = ensurePark();
    while (results.firstChild) park.appendChild(results.firstChild);
    results.style.display = "none";
    results.innerHTML = "";
    document.body.classList.add("ssa-hub-48h-no-home-profile");
  }

  function wrapShowSailorStats() {
    var orig = window.showSailorStatsInResults;
    if (!orig || orig.__ssa48hWrapped) return !!orig;
    function wrapped(sid, name, club, classes, options) {
      options = options || {};
      var ret = orig.apply(this, arguments);
      function afterPaint() {
        if (
          HIDE_LOGGED_IN_HOME_CARD &&
          options.isLoggedInUser === true &&
          isHubHome() &&
          !sailorSearchHasQuery()
        ) {
          parkLoggedInHomeCard();
        }
      }
      if (ret && typeof ret.then === "function") {
        return ret.then(function (v) {
          afterPaint();
          return v;
        });
      }
      afterPaint();
      return ret;
    }
    wrapped.__ssa48hWrapped = true;
    window.showSailorStatsInResults = wrapped;
    return true;
  }

  function shouldShow() {
    return isHubHome() && inFortyEightHourWindow();
  }

  function mountRoot() {
    injectCss();
    var root = document.getElementById(ROOT_ID);
    var search = document.querySelector(".search-header-container");
    if (!root) {
      root = document.createElement("section");
      root.id = ROOT_ID;
      root.className = "ssa-upcoming-48h";
      root.setAttribute("aria-label", "Upcoming events in the next 48 hours");
      if (search && search.parentNode) {
        search.parentNode.insertBefore(root, search);
      } else {
        var col = document.querySelector(".main-column .container") || document.querySelector(".container");
        if (col) col.insertBefore(root, col.firstChild);
      }
    }
    if (!shouldShow()) {
      root.hidden = true;
      root.setAttribute("hidden", "");
      if (windTimer) {
        clearInterval(windTimer);
        windTimer = null;
      }
      return root;
    }
    root.hidden = false;
    root.removeAttribute("hidden");
    if (!root.querySelector(".ssa-upcoming-48h-header")) {
      root.innerHTML = cardsHtml();
    }
    windSlot = root.querySelector("[data-ssa-48h-wind]");
    if (windSlot) {
      loadWind();
      if (!windTimer) {
        windTimer = setInterval(function () {
          if (!document.hidden) loadWind();
        }, 40000);
      }
    }
    return root;
  }

  function bindSearch() {
    ["sailor-search-input", "temp-landing-regatta-input"].forEach(function (id) {
      var el = document.getElementById(id);
      if (!el || el.__ssa48hBound) return;
      el.__ssa48hBound = true;
      el.addEventListener("input", function () {
        if (sailorSearchHasQuery()) {
          document.body.classList.remove("ssa-hub-48h-no-home-profile");
          var results = document.getElementById("sailor-search-results");
          if (results) results.setAttribute("data-ssa-search-list", "1");
        } else {
          parkLoggedInHomeCard();
        }
      });
    });
  }

  function boot() {
    wrapShowSailorStats();
    bindSearch();
    ensurePark();
    mountRoot();
    parkLoggedInHomeCard();
    var n = 0;
    var t = setInterval(function () {
      n += 1;
      wrapShowSailorStats();
      bindSearch();
      parkLoggedInHomeCard();
      if (shouldShow()) mountRoot();
      if (n > 40) clearInterval(t);
    }, 250);
    var origMode = window.setMainColumnMode;
    if (origMode && !origMode.__ssa48hWrapped) {
      window.setMainColumnMode = function (mode) {
        origMode.apply(this, arguments);
        mountRoot();
      };
      window.setMainColumnMode.__ssa48hWrapped = true;
    }
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden && shouldShow()) loadWind();
    });
  }

  window.__ssaUpcoming48h = JS_VER;
  window.__ssaUpcoming48hRestoreHomeCard = function () {
    HIDE_LOGGED_IN_HOME_CARD = false;
    document.body.classList.remove("ssa-hub-48h-no-home-profile");
    var park = document.getElementById(PARK_ID);
    var results = document.getElementById("sailor-search-results");
    if (park && results && park.firstChild) {
      while (park.firstChild) results.appendChild(park.firstChild);
      results.style.display = "block";
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
