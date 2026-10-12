/**
 * MAC TSL WC Event URL cards — wind (Wind2Speed station 3) + HMYC-style 5-clip media.
 * Media brand = MAC logo (same slot as HMYC logo on Dart/Midmar). Clips from MAC Media WhatsApp.
 * Live cam: not rendered until a MAC feed is supplied (data-mac-cam="later").
 * Only /regatta/2026-10-17-mac-tsl-wc-team-sailing. Gold wx chrome (Cape Classic slot).
 */
(function () {
  "use strict";
  if (window.__SSA_MAC_TSL_LIVE_CARDS__) return;
  window.__SSA_MAC_TSL_LIVE_CARDS__ = true;

  var RID = "2026-10-17-mac-tsl-wc-team-sailing";
  var HOST_ID = "mac-tsl-live-cards";
  var WX_ID = "ssa-regatta-slot-card";
  var MEDIA_ID = "mmLiptonReels";
  var CSS_ID = "mac-tsl-live-cards-css";
  var JS_VER = "20261012g";
  var NOR_SRC = "/js/mac-tsl-nor.html?v=" + JS_VER;
  var MAC_LOGO = "/artwork/Club Logo/MAC.png";
  var WX_API = "/api/wind2speed/mac";
  var PTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  var BANDS = [[0, 5, "#12b028"], [5, 11, "#2563eb"], [11, 17, "#e67e00"], [17, 23, "#7c3aed"], [23, 60, "#DC143C"]];

  function pathRid() {
    var path = String((window.location && window.location.pathname) || "").replace(/\/+$/, "").toLowerCase();
    var m = path.match(/^\/regatta\/([^/]+)/);
    return m ? m[1] : "";
  }

  function onThisEvent() {
    var page = document.querySelector(".regatta-page");
    return pathRid() === RID || (page && page.getAttribute("data-mac-tsl") === "1");
  }

  function injectCss() {
    var s = document.getElementById(CSS_ID);
    if (!s) {
      s = document.createElement("style");
      s.id = CSS_ID;
      document.head.appendChild(s);
    }
    s.textContent = [
      ".regatta-page:has(#mac-tsl-live-cards)>.regatta-header-wrap .header{margin-bottom:0!important;}",
      ".mac-tsl-live-cards{width:100%;max-width:100%;box-sizing:border-box;display:flex;flex-direction:column;gap:0;margin:0;padding:0;border:0;background:transparent;box-shadow:none;}",
      ".ssa-regatta-slot-card{display:flex;width:100%;margin:10px 0 0;padding:0;box-sizing:border-box;height:122px;min-height:122px;background:#fff;border:2px solid #001f3f;border-radius:8px;box-shadow:0 1px 3px rgba(0,31,63,.08);overflow:hidden;}",
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
      ".ssa-regatta-slot-card .wx-info{flex:0 0 auto;min-width:118px;height:100%;display:flex;flex-direction:column;justify-content:stretch;gap:6px;padding:10px 8px 10px 4px;box-sizing:border-box;}",
      ".ssa-regatta-slot-card .wx-dial .dt{stroke:#9ca3af;stroke-width:1;}",
      ".ssa-regatta-slot-card .wx-dial .dt.card{stroke:#111;stroke-width:1.4;}",
      ".ssa-regatta-slot-card .wx-dial .darc{fill:none;stroke:#93c5fd;stroke-width:7;stroke-linecap:butt;}",
      ".ssa-regatta-slot-card .wx-dial .darc.prev{opacity:.45;}",
      ".ssa-regatta-slot-card .wx-dial .dhead{fill:#3b82f6;}",
      ".ssa-regatta-slot-card .wx-dial .dpt{font:700 24px Arial,Helvetica,sans-serif;fill:#15803d;}",
      ".ssa-regatta-slot-card .wx-dial .ddeg{font:700 18px Arial,Helvetica,sans-serif;fill:#166534;}",
      ".ssa-regatta-slot-card .wx-ir{flex:1 1 0;display:flex;flex-direction:row;justify-content:flex-end;align-items:baseline;gap:6px;min-width:0;min-height:0;}",
      ".ssa-regatta-slot-card .wx-il,.ssa-regatta-slot-card .wx-iv,.ssa-regatta-slot-card .wx-iv small{font:800 18px/1 Arial,Helvetica,sans-serif;white-space:nowrap;}",
      ".ssa-regatta-slot-card .wx-il{color:#334155;}",
      ".ssa-regatta-slot-card .wx-iv{color:#1a2750;text-align:right;}",
      ".ssa-regatta-slot-card .wx-iv small{margin-left:4px;color:inherit;}",
      ".mac-tsl-live-cards .mm-lipton-reels{margin:10px 0 0;width:100%;box-sizing:border-box;}",
      ".mac-tsl-live-cards .mm-lipton-reels-brand{flex:0 0 auto;display:flex!important;align-items:center;justify-content:center;padding:8px!important;box-sizing:border-box;background:#fff!important;border:2px solid #001f3f;border-radius:8px;line-height:normal;cursor:pointer;filter:none!important;}",
      ".mac-tsl-live-cards .mm-lipton-reels-brand img{display:block!important;width:auto!important;height:auto!important;max-width:100%!important;max-height:100%!important;object-fit:contain!important;object-position:center;filter:none!important;background:transparent!important;border:0;}",
      "@media print{.mac-tsl-live-cards{display:none!important;}}",
      "#macTslNorDialog.card{max-width:44rem;width:calc(100% - 24px);max-height:90vh;overflow:auto;padding:0.5rem 0.75rem;border:2px solid #001f3f;border-radius:8px;box-shadow:0 4px 12px rgba(0,31,63,.12);}",
      "#macTslNorDialog::backdrop{background:rgba(0,31,63,.45);}",
      ".mac-tsl-nor-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:0.4rem;}",
      ".mac-tsl-nor-head .section-title{margin:0;flex:1 1 auto;}",
      ".mac-tsl-nor-close{min-height:44px;min-width:44px;padding:8px 12px;border:1.5px solid #001f3f;border-radius:8px;background:#001f3f;color:#fff;font:700 14px/1.2 Arial,Helvetica,sans-serif;cursor:pointer;}",
      ".mac-tsl-nor-doc p{margin:0 0 0.75rem;color:#1e293b;line-height:1.6;}",
      ".mac-tsl-nor-doc .section-title{margin:1rem 0 0.4rem;}",
      ".regatta-header-status-stack #macTslNorOpen{color:#1a2750;font-weight:700;}",
      ".regatta-page[data-mac-tsl=\"1\"] .regatta-sa-hub-news-wrap,",
      ".regatta-page[data-mac-tsl=\"1\"] #regattaHubNewsType,",
      ".regatta-page[data-mac-tsl=\"1\"] #regattaMmLiveFbFeed,",
      ".regatta-page[data-mac-tsl=\"1\"] #regattaMmFeedSource,",
      ".regatta-page[data-mac-tsl=\"1\"] #regattaMmFbPage,",
      ".regatta-page[data-mac-tsl=\"1\"] #regattaMmClipUrls,",
      ".regatta-page[data-mac-tsl=\"1\"] #regattaWaShowWrap,",
      ".regatta-page[data-mac-tsl=\"1\"] #mmLiveFbCard,",
      ".regatta-page[data-mac-tsl=\"1\"] .mm-live-fb-card{display:none!important;}"
    ].join("");
  }

  function n1(x) {
    return x == null || isNaN(x) ? "—" : String(Math.round(Number(x) * 10) / 10);
  }
  function pol(cx, cy, r, a) {
    var t = ((a - 90) * Math.PI) / 180;
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
    return Math.round(((((Number(deg) % 360) + 360) % 360) / 22.5)) % 16;
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
    var html = '<div class="wx-spark" aria-label="Wind last hour">';
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

  function renderWx(slot, data) {
    var wnow = data.wind_kt;
    var wavg = data.avg_kt;
    var whigh = data.high_kt != null ? data.high_kt : data.gust_kt;
    slot.innerHTML =
      '<div class="wx-wp-top">' +
      '<div class="wx-wp-comp">' + drawDial(data) + "</div>" +
      drawSpark(data) +
      '<div class="wx-info">' +
      '<div class="wx-ir"><span class="wx-il">Now</span><span class="wx-iv" style="color:' + bandCol(wnow) + '">' + n1(wnow) + "<small>kt</small></span></div>" +
      '<div class="wx-ir"><span class="wx-il">Avg</span><span class="wx-iv" style="color:' + bandCol(wavg) + '">' + n1(wavg) + "<small>kt</small></span></div>" +
      '<div class="wx-ir"><span class="wx-il">Gust</span><span class="wx-iv" style="color:' + bandCol(whigh) + '">' + n1(whigh) + "<small>kt</small></span></div>" +
      "</div></div>";
  }

  function loadCss(href) {
    var base = href.split("?")[0];
    if (document.querySelector('link[href*="' + base + '"]')) return;
    var l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = href;
    document.head.appendChild(l);
  }

  function loadScript(src) {
    return new Promise(function (resolve) {
      var base = src.split("?")[0];
      if (document.querySelector('script[src*="' + base + '"]')) {
        resolve();
        return;
      }
      var s = document.createElement("script");
      s.src = src;
      s.async = false;
      s.onload = function () { resolve(); };
      s.onerror = function () { resolve(); };
      document.head.appendChild(s);
    });
  }

  function openNorDialog() {
    var dlg = document.getElementById("macTslNorDialog");
    if (!dlg) return;
    if (typeof dlg.showModal === "function") dlg.showModal();
    else dlg.setAttribute("open", "open");
    if (window.location.hash !== "#nor") {
      try { history.replaceState(null, "", "#nor"); } catch (e) { window.location.hash = "nor"; }
    }
  }

  function closeNorDialog() {
    var dlg = document.getElementById("macTslNorDialog");
    if (!dlg) return;
    if (typeof dlg.close === "function") dlg.close();
    else dlg.removeAttribute("open");
    if (window.location.hash === "#nor") {
      try { history.replaceState(null, "", window.location.pathname + window.location.search); } catch (e) {}
    }
  }

  function bindNor() {
    var stack = document.querySelector(".regatta-header-status-stack");
    if (stack && !document.getElementById("macTslNorOpen")) {
      var line = document.createElement("div");
      line.className = "status-line";
      line.innerHTML = '<a href="#nor" id="macTslNorOpen">Notice of Race</a>';
      stack.appendChild(line);
    }
    var dlg = document.getElementById("macTslNorDialog");
    if (!dlg) {
      dlg = document.createElement("dialog");
      dlg.id = "macTslNorDialog";
      dlg.className = "card";
      dlg.setAttribute("aria-labelledby", "macTslNorTitle");
      dlg.innerHTML =
        '<div class="mac-tsl-nor-head">' +
        '<h2 class="section-title" id="macTslNorTitle">Notice of Race</h2>' +
        '<button type="button" class="mac-tsl-nor-close" data-mac-tsl-nor-close>Close</button>' +
        "</div>" +
        '<div class="mac-tsl-nor-body"><p>Loading Notice of Race…</p></div>';
      document.body.appendChild(dlg);
      fetch(NOR_SRC, { cache: "no-store" })
        .then(function (res) {
          if (!res.ok) throw new Error("nor " + res.status);
          return res.text();
        })
        .then(function (html) {
          var body = dlg.querySelector(".mac-tsl-nor-body");
          if (body) body.innerHTML = html;
        })
        .catch(function () {
          var body = dlg.querySelector(".mac-tsl-nor-body");
          if (body) body.innerHTML = "<p>Notice of Race could not be loaded. Refresh the Event URL and try again.</p>";
        });
    }
    var openBtn = document.getElementById("macTslNorOpen");
    if (openBtn && !openBtn.getAttribute("data-mac-tsl-nor-bound")) {
      openBtn.setAttribute("data-mac-tsl-nor-bound", "1");
      openBtn.addEventListener("click", function (ev) {
        ev.preventDefault();
        openNorDialog();
      });
    }
    var closeBtn = dlg.querySelector("[data-mac-tsl-nor-close]");
    if (closeBtn && !closeBtn.getAttribute("data-mac-tsl-nor-bound")) {
      closeBtn.setAttribute("data-mac-tsl-nor-bound", "1");
      closeBtn.addEventListener("click", function () { closeNorDialog(); });
    }
    if (!dlg.getAttribute("data-mac-tsl-nor-bound")) {
      dlg.setAttribute("data-mac-tsl-nor-bound", "1");
      dlg.addEventListener("cancel", function () { closeNorDialog(); });
    }
    if (window.location.hash === "#nor") openNorDialog();
  }

  function mount() {
    if (!onThisEvent()) return;
    var page = document.querySelector(".regatta-page");
    if (!page) return;
    injectCss();
    bindNor();
    var junk = page.querySelectorAll(
      ".regatta-sa-hub-news-wrap, #regattaWaShowWrap, #mmLiveFbCard, .mm-live-fb-card"
    );
    for (var ji = 0; ji < junk.length; ji += 1) {
      if (junk[ji] && junk[ji].parentNode) junk[ji].parentNode.removeChild(junk[ji]);
    }
    var host = document.getElementById(HOST_ID);
    if (!host) {
      host = document.createElement("div");
      host.id = HOST_ID;
      host.className = "mac-tsl-live-cards";
      var header = page.querySelector(".regatta-header-wrap");
      if (header && header.nextSibling) page.insertBefore(host, header.nextSibling);
      else page.insertBefore(host, page.firstChild);
    }

    var wx = document.getElementById(WX_ID);
    if (!wx) {
      wx = document.createElement("div");
      wx.id = WX_ID;
      wx.className = "card ssa-wx-card ssa-regatta-slot-card";
      wx.setAttribute("data-weather-club", "MAC");
      wx.setAttribute("data-weather-station", "w2s-mac-3");
      wx.setAttribute("data-weather-role", "venue");
      wx.setAttribute("aria-label", "Milnerton Aquatic Club wind");
      host.appendChild(wx);
    }

    var oldShell = document.getElementById("mac-tsl-media-card");
    if (oldShell && oldShell.parentNode) oldShell.parentNode.removeChild(oldShell);
    var oldSa = document.getElementById("mac-tsl-mm-sa");
    if (oldSa && oldSa.parentNode) oldSa.parentNode.removeChild(oldSa);

    var media = document.getElementById(MEDIA_ID);
    if (!media) {
      media = document.createElement("section");
      media.id = MEDIA_ID;
      media.className = "card mm-lipton-reels mm-lipton-reels--compact";
      media.setAttribute("data-regatta-id", RID);
      media.setAttribute("data-mm-poll", "1");
      media.setAttribute("data-mm-club-logo", MAC_LOGO);
      media.setAttribute("data-mm-club-href", "/club/mac");
      media.setAttribute("data-mm-club-alt", "MAC");
      media.setAttribute("data-mm-brand-soon", MAC_LOGO);
      media.setAttribute("data-mm-brand-live", MAC_LOGO);
      media.setAttribute(
        "data-mm-initial",
        JSON.stringify({ enabled: true, feed_source: "mac", videos: [] })
      );
      media.innerHTML =
        '<div class="mm-lipton-reels-compact">' +
        '<a class="mm-lipton-reels-brand" href="/club/mac" aria-label="MAC">' +
        '<img src="' + MAC_LOGO + '" alt="MAC" width="440" height="180" decoding="async">' +
        "</a>" +
        '<div class="mm-lipton-reels-rail-wrap">' +
        '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--prev" data-mm-rail-prev aria-label="Previous clips" hidden>‹</button>' +
        '<div class="mm-lipton-reels-rail" data-mm-compact></div>' +
        '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--next" data-mm-rail-next aria-label="Next clips" hidden>›</button>' +
        "</div></div>";
      host.appendChild(media);
    }

    loadCss("/css/mm-lipton-reels.css?v=" + JS_VER);
    loadScript("/js/mm-lipton-reels-card.js?v=mactslmedia1").then(function () {
      if (typeof window.mmLiptonReelsInit === "function") window.mmLiptonReelsInit();
    });

    function loadWx() {
      fetch(WX_API + "?_=" + Date.now(), { cache: "no-store" })
        .then(function (res) {
          if (!res.ok) throw new Error("w2s " + res.status);
          return res.json();
        })
        .then(function (data) {
          if (!data || data.ok === false) throw new Error((data && data.err) || "w2s fail");
          renderWx(wx, data);
          var wait = Number(data.interval) || 40000;
          window.setTimeout(loadWx, Math.max(15000, wait));
        })
        .catch(function () {
          if (!wx.getAttribute("data-wx-ready")) {
            wx.innerHTML = '<div class="wx-wp-top"><div class="wx-info"><div class="wx-ir"><span class="wx-il">MAC wind</span><span class="wx-iv">—</span></div></div></div>';
          }
          window.setTimeout(loadWx, 30000);
        });
    }
    loadWx();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
  window.__ssaMacTslLiveCards = JS_VER;
})();
