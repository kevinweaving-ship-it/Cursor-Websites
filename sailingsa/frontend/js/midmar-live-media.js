/**
 * Midmar Cup Event URL — HMYC venue weather + club camera.
 * Place: between event header and fleet header.
 * Weather is identical to /club/hmyc (agromet-midmar).
 * Camera is the HMYC JPEG snapshot. Click = fullscreen cam only (no header).
 * Hide (top right) returns to the event page. Do not link out to Agromet.
 */
(function () {
  "use strict";
  if (window.__SSA_MIDMAR_LIVE_MEDIA__) return;
  window.__SSA_MIDMAR_LIVE_MEDIA__ = true;

  var RID = "2026-09-19-hmyc-midmar-cup";
  var HOST_ID = "midmar-live-media";
  var WX_ID = "ssa-regatta-slot-card";
  var CAM_ID = "midmar-hmyc-cam";
  var CSS_ID = "midmar-live-media-css";
  var JS_VER = "midmarwx16";
  var EVENT_PATH = "/regatta/" + RID;
  var STILL = "https://hmyccam1.nwsza.net/latest.jpg";
  var POLL_MS = 60000;
  var MM_ID = "mmLiptonReels";
  var CUP_SRC = "/artwork/Event Logo/Midmar-Cup-Event.jpg";
  var MM_BRAND = "/assets/adverts/mm-powered-by-event-reels.png?v=mmr2";

  function onMidmar() {
    var path = String((window.location && window.location.pathname) || "")
      .replace(/\/+$/, "")
      .toLowerCase();
    return path === "/regatta/" + RID || path.indexOf("/regatta/" + RID + "/") === 0;
  }

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement("style");
    s.id = CSS_ID;
    s.textContent = [
      ".regatta-page > .midmar-live-media{width:100%;max-width:100%;box-sizing:border-box;display:flex;flex-direction:column;gap:0;margin:0;padding:0;border:0;background:transparent;box-shadow:none;}",
      ".regatta-page > .midmar-live-media .ssa-regatta-slot-card{order:0;margin-top:10px;width:100%;max-width:100%;padding:0!important;}",
      ".regatta-page > .midmar-live-media .mm-lipton-reels{order:1;margin-top:10px;width:100%;max-width:100%;}",
      ".regatta-page > .midmar-live-media .midmar-hmyc-cam{order:2;margin-top:10px;width:100%;max-width:100%;padding:0!important;overflow:hidden;background:#000;}",
      ".midmar-hmyc-cam .cam-frame{position:relative;display:block;width:100%;aspect-ratio:16/9;background:#000;overflow:hidden;margin:0;padding:0;border:0;cursor:pointer;-webkit-tap-highlight-color:transparent;}",
      ".midmar-hmyc-cam .cam-shot{position:relative;display:block;width:100%;height:100%;overflow:hidden;}",
      ".midmar-hmyc-cam .cam-shot img{display:block;width:100%;height:118%;margin-top:-10%;object-fit:cover;object-position:center bottom;background:#000;}",
      "body:has(.midmar-hmyc-cam.is-open) .site-header{display:none!important;}",
      "body.midmar-cam-open{overflow:hidden;}",
      ".midmar-hmyc-cam.is-open{position:fixed;inset:0;z-index:2147483000;width:100vw;max-width:100vw;height:100vh;height:100dvh;margin:0;border:0;border-radius:0;background:#000;overflow:hidden;}",
      ".midmar-hmyc-cam.is-open .cam-frame{display:flex;align-items:center;justify-content:center;height:100%;aspect-ratio:auto;cursor:default;overflow:hidden;}",
      ".midmar-hmyc-cam.is-open .cam-shot{width:auto;height:auto;max-width:100%;max-height:100%;overflow:visible;}",
      ".midmar-hmyc-cam.is-open .cam-shot img{width:auto;height:auto;max-width:100vw;max-height:100vh;max-height:100dvh;margin:0;object-fit:contain;object-position:center center;}",
      ".midmar-hmyc-cam .mm-lipton-reels-expanded-bar{display:none;}",
      ".midmar-hmyc-cam.is-open .mm-lipton-reels-expanded-bar{display:flex;position:absolute;top:0;right:0;z-index:6;justify-content:flex-end;align-items:flex-start;margin:0;padding:0;pointer-events:none;}",
      ".midmar-hmyc-cam .mm-lipton-reels-hide{display:none;}",
      ".midmar-hmyc-cam.is-open .mm-lipton-reels-hide{display:flex;align-items:center;justify-content:center;min-height:44px;min-width:44px;padding:10px 12px;margin:0;border:0;background:transparent;cursor:pointer;pointer-events:auto;color:#dc2626!important;font-size:0.95rem!important;font-weight:800!important;letter-spacing:.02em;font-family:Arial,Helvetica,sans-serif;}",
      ".midmar-hmyc-cam .mm-lipton-reels-cam-stamp{position:absolute;left:8px;top:8px;z-index:3;pointer-events:none;display:flex;flex-direction:row;align-items:center;gap:5px;padding:2px 8px;border-radius:4px;background:rgba(0,16,24,.72);color:#fff;white-space:nowrap;text-shadow:0 1px 2px rgba(0,0,0,.85);font:700 11px/1.2 Arial,Helvetica,sans-serif;}",
      ".midmar-hmyc-cam .mm-lipton-reels-cam-stamp-dot{flex:0 0 auto;width:8px;height:8px;border-radius:50%;background:#94a3b8;}",
      ".midmar-hmyc-cam .mm-lipton-reels-cam-stamp [data-mm-cam-stamp-label]{font-weight:800;letter-spacing:.03em;}",
      ".midmar-hmyc-cam .mm-lipton-reels-cam-stamp [data-mm-cam-stamp-time]{font-weight:700;opacity:.95;}",
      ".midmar-hmyc-cam .midmar-cam-wx{display:none;}",
      ".midmar-hmyc-cam.is-open .cam-shot .midmar-cam-wx{position:absolute;top:8px;right:8px;left:auto;bottom:auto;z-index:5;pointer-events:none;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;gap:2px;min-width:0;padding:0;border:0;background:none;color:#000;text-align:center;text-shadow:none;box-sizing:border-box;}",
      ".midmar-hmyc-cam .midmar-cam-wx-temp,.midmar-hmyc-cam .midmar-cam-wx-kn{display:block;width:100%;margin:0;padding:0;text-align:center;color:#000;font:800 16px/1.1 Arial,Helvetica,sans-serif;letter-spacing:.02em;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge{display:block;width:72px;height:72px;margin:0 auto;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge svg{display:block;width:72px;height:72px;overflow:visible;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .dt{stroke:#000;stroke-width:1;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .dt.card{stroke:#000;stroke-width:1.4;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .darc{fill:none;stroke:#93c5fd;stroke-width:5;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .darc.prev{opacity:.45;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .dhead{fill:#000!important;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .dpt{font:700 16px Arial,Helvetica,sans-serif;fill:#000;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .ddeg{font:700 12px Arial,Helvetica,sans-serif;fill:#000;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .dcard{font:700 10px Arial,Helvetica,sans-serif;fill:#000;}",
      "@media screen and (orientation:portrait) and (max-width:767px){",
      ".regatta-page > .midmar-live-media .midmar-hmyc-cam:not(.is-open){width:100vw;max-width:100vw;margin-left:calc(50% - 50vw);margin-right:calc(50% - 50vw);border-left:0;border-right:0;border-radius:0;}",
      "}",
      "@media print{.midmar-live-media,.mm-lipton-reels{display:none!important}}",
      ".class-header .fleet-results-status{margin-top:6px}",
      ".class-header .fleet-results-as-at{margin-top:2px}",
    ].join("");
    document.head.appendChild(s);
  }

  function injectFleetResultsStatus() {
    document.querySelectorAll(".class-header").forEach(function (hdr) {
      if (hdr.querySelector(".fleet-results-status")) return;
      var line = hdr.querySelector(".sailed-line");
      if (!line) return;
      var status = document.createElement("div");
      status.className = "sailed-line fleet-results-status";
      status.textContent = "Results are Provisional";
      var date = document.createElement("div");
      date.className = "sailed-line fleet-results-as-at";
      date.textContent = "19 Sep 2026";
      line.insertAdjacentElement("afterend", date);
      line.insertAdjacentElement("afterend", status);
    });
  }

  function fmtHm(ms) {
    try {
      return new Date(ms).toLocaleTimeString("en-GB", {
        timeZone: "Africa/Johannesburg",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    } catch (e) {
      var d = new Date(ms);
      var h = d.getHours();
      var m = d.getMinutes();
      return (h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m;
    }
  }

  function makeWx() {
    var wx = document.getElementById(WX_ID);
    if (!wx) {
      wx = document.createElement("section");
      wx.id = WX_ID;
      wx.className = "card ssa-wx-card ssa-regatta-slot-card";
    }
    wx.setAttribute("data-weather-club", "HMYC");
    wx.setAttribute("data-weather-station", "agromet-midmar");
    wx.setAttribute("data-weather-role", "venue");
    wx.setAttribute("aria-label", "HMYC venue wind");
    return wx;
  }

  function setOpen(cam, open) {
    cam.classList.toggle("is-open", !!open);
    cam.setAttribute("aria-expanded", open ? "true" : "false");
    document.body.classList.toggle("midmar-cam-open", !!open);
    var frame = cam.querySelector(".cam-frame");
    if (frame) frame.setAttribute("aria-pressed", open ? "true" : "false");
  }

  function backToEvent(cam) {
    setOpen(cam, false);
    var path = EVENT_PATH;
    var here = String((window.location && window.location.pathname) || "").replace(/\/+$/, "");
    if (here !== path) {
      window.location.href = path;
      return;
    }
    if (window.location.hash) {
      try {
        window.history.replaceState(null, "", path);
      } catch (e) {}
    }
    var host = document.getElementById(HOST_ID);
    if (host && host.scrollIntoView) host.scrollIntoView({ block: "start" });
  }

  function makeCam() {
    var cam = document.getElementById(CAM_ID);
    if (!cam) {
      cam = document.createElement("section");
      cam.id = CAM_ID;
    }
    cam.className = "card midmar-hmyc-cam";
    cam.setAttribute("aria-label", "HMYC club cam");
    cam.setAttribute("data-mm-cam-status", "/api/club-cam/hmyc");
    setOpen(cam, false);
    cam.innerHTML =
      '<div class="mm-lipton-reels-expanded-bar">' +
      '<button type="button" class="mm-lipton-reels-hide" data-mm-hide>Hide</button>' +
      "</div>" +
      '<button type="button" class="cam-frame" aria-label="View HMYC club cam" aria-pressed="false">' +
      '<span class="cam-shot">' +
      '<img alt="HMYC club cam" width="1600" height="900" decoding="async">' +
      '<span class="mm-lipton-reels-cam-stamp mm-lipton-reels-cam-stamp--off" data-mm-cam-stamp>' +
      '<span class="mm-lipton-reels-cam-stamp-dot" aria-hidden="true"></span>' +
      '<span data-mm-cam-stamp-label>SNAPSHOT</span>' +
      '<span data-mm-cam-stamp-time></span>' +
      "</span>" +
      '<span class="midmar-cam-wx" data-mm-cam-wx aria-hidden="true">' +
      '<span class="midmar-cam-wx-temp" data-mm-cam-wx-temp>—</span>' +
      '<span class="midmar-cam-wx-gauge" data-mm-cam-wx-gauge></span>' +
      '<span class="midmar-cam-wx-kn" data-mm-cam-wx-kn>— kn</span>' +
      "</span></span></button>";
    return cam;
  }

  var BANDS = [[0, 5, "#12b028"], [5, 11, "#2563eb"], [11, 17, "#e67e00"], [17, 23, "#7c3aed"], [23, 60, "#DC143C"]];
  var PTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];

  function dirIdx(deg) {
    if (deg == null || isNaN(deg)) return null;
    return Math.round((((Number(deg) % 360) + 360) % 360) / 22.5) % 16;
  }

  function bandCol(kn) {
    if (kn == null || isNaN(kn)) return "#94a3b8";
    var i;
    for (i = 0; i < BANDS.length; i += 1) {
      if (kn < BANDS[i][1]) return BANDS[i][2];
    }
    return "#DC143C";
  }

  function pol(cx, cy, r, a) {
    var t = ((a - 90) * Math.PI) / 180;
    return [cx + r * Math.cos(t), cy + r * Math.sin(t)];
  }

  function n1(x) {
    return x == null || isNaN(x) ? "—" : String(Math.round(Number(x) * 10) / 10);
  }

  function parseMs(t) {
    if (t == null || t === "") return NaN;
    if (typeof t === "number" && isFinite(t)) return t < 1e12 ? t * 1000 : t;
    var ms = Date.parse(String(t));
    return isNaN(ms) ? NaN : ms;
  }

  function viewFromReadings(readings) {
    var pts = (readings || []).slice().sort(function (a, b) {
      return parseMs(a.observed_at) - parseMs(b.observed_at);
    });
    var last = pts.length ? pts[pts.length - 1] : {};
    var nowMs = parseMs(last.observed_at);
    if (isNaN(nowMs)) nowMs = Date.now();
    var wds = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    var i;
    var r;
    var ms;
    var di;
    for (i = 0; i < pts.length; i += 1) {
      r = pts[i];
      ms = parseMs(r.observed_at);
      if (!isNaN(ms) && nowMs - ms <= 3600000) {
        di = dirIdx(r.wind_dir_deg != null ? r.wind_dir_deg : r.wind_dir_avg_deg);
        if (di != null) wds[di] += 1;
      }
    }
    var deg = last.wind_dir_deg != null ? last.wind_dir_deg : last.wind_dir_avg_deg;
    var lastDi = dirIdx(deg);
    var uniq = [];
    for (i = 0; i < 16; i += 1) {
      if (wds[i] > 0) uniq.push(i);
    }
    if (lastDi != null && uniq.indexOf(lastDi) === -1) uniq.push(lastDi);
    return {
      wind_kt: last.wind_kt != null ? last.wind_kt : last.wind_avg_kt,
      wind_dir: deg,
      wind_dir_name: lastDi != null ? PTS[lastDi] : "",
      last_di: lastDi,
      uniq: uniq,
      temp_c: last.temp_c,
    };
  }

  function drawMiniGauge(data) {
    var CX = 50;
    var CY = 50;
    var R = 40;
    var kn = data.wind_kt;
    var col = bandCol(kn);
    var lastDi = data.last_di;
    var lastDeg = data.wind_dir;
    var deg =
      lastDeg != null && !isNaN(lastDeg)
        ? Number(lastDeg)
        : lastDi != null
        ? lastDi * 22.5
        : null;
    var pt = data.wind_dir_name || (lastDi != null ? PTS[lastDi] : "");
    var uniq = data.uniq || [];
    var svg = '<svg viewBox="0 0 100 100" aria-hidden="true">';
    var k;
    for (k = 0; k < 72; k += 1) {
      var card = k % 18 === 0;
      var q0 = pol(CX, CY, R - (card ? 7 : 4), k * 5);
      var q1 = pol(CX, CY, R + (card ? 1 : 0), k * 5);
      svg +=
        '<line class="' +
        (card ? "dt card" : "dt") +
        '" x1="' +
        q0[0].toFixed(1) +
        '" y1="' +
        q0[1].toFixed(1) +
        '" x2="' +
        q1[0].toFixed(1) +
        '" y2="' +
        q1[1].toFixed(1) +
        '"/>';
    }
    [[0, "N"], [90, "E"], [180, "S"], [270, "W"]].forEach(function (c) {
      var lp = pol(CX, CY, 28, c[0]);
      svg +=
        '<text class="dcard" x="' +
        lp[0].toFixed(1) +
        '" y="' +
        lp[1].toFixed(1) +
        '" text-anchor="middle" dominant-baseline="central">' +
        c[1] +
        "</text>";
    });
    uniq.forEach(function (idx) {
      var a0 = idx * 22.5 - 11.25;
      var a1 = idx * 22.5 + 11.25;
      var p0 = pol(CX, CY, R - 3, a0);
      var p1 = pol(CX, CY, R - 3, a1);
      svg +=
        '<path class="darc' +
        (idx === lastDi ? "" : " prev") +
        '" style="stroke:' +
        col +
        '" d="M' +
        p0[0].toFixed(1) +
        " " +
        p0[1].toFixed(1) +
        " A" +
        (R - 3) +
        " " +
        (R - 3) +
        " 0 0 1 " +
        p1[0].toFixed(1) +
        " " +
        p1[1].toFixed(1) +
        '"/>';
    });
    if (deg != null && !isNaN(deg)) {
      var d = ((Number(deg) % 360) + 360) % 360;
      var hp = pol(CX, CY, R + 2, d);
      svg +=
        '<g transform="translate(' +
        hp[0].toFixed(1) +
        " " +
        hp[1].toFixed(1) +
        ") rotate(" +
        (d + 180) +
        ')"><path class="dhead" d="M0 -10L8 5L0 2L-8 5Z"/></g>';
    }
    svg +=
      '<text class="dpt" x="50" y="46" text-anchor="middle" dominant-baseline="central">' +
      (pt || "—") +
      "</text>";
    if (deg != null && !isNaN(deg)) {
      svg +=
        '<text class="ddeg" x="50" y="64" text-anchor="middle">' +
        Math.round(Number(deg)) +
        "°</text>";
    }
    svg += "</svg>";
    return svg;
  }

  function paintWx(cam) {
    if (!cam.classList.contains("is-open")) return;
    var tempEl = cam.querySelector("[data-mm-cam-wx-temp]");
    var knEl = cam.querySelector("[data-mm-cam-wx-kn]");
    var gaugeEl = cam.querySelector("[data-mm-cam-wx-gauge]");
    if (!tempEl || !knEl || !gaugeEl) return;
    fetch("/api/weather/agromet-midmar/history?hours=12&_=" + Date.now(), {
      cache: "no-store",
      credentials: "same-origin",
    })
      .then(function (r) {
        if (!r.ok) throw new Error("wx");
        return r.json();
      })
      .then(function (body) {
        var data = viewFromReadings((body && body.readings) || []);
        var kn = data.wind_kt;
        var temp = data.temp_c;
        tempEl.textContent = temp == null || isNaN(temp) ? "—" : n1(temp) + "°C";
        knEl.textContent = kn == null || isNaN(kn) ? "— kn" : n1(kn) + " kn";
        gaugeEl.innerHTML = drawMiniGauge(data);
      })
      .catch(function () {});
  }

  function paintCam(cam) {
    var img = cam.querySelector("img");
    var timeEl = cam.querySelector("[data-mm-cam-stamp-time]");
    var now = Date.now();
    if (img) img.src = STILL + "?t=" + now;
    if (timeEl) timeEl.textContent = "as at " + fmtHm(now);
  }

  function bindCam(cam) {
    if (cam.getAttribute("data-cam-bound") === "1") return;
    cam.setAttribute("data-cam-bound", "1");
    var frame = cam.querySelector(".cam-frame");
    if (frame) {
      frame.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (!cam.classList.contains("is-open")) {
          setOpen(cam, true);
          paintWx(cam);
        }
      });
    }
    var hide = cam.querySelector("[data-mm-hide]");
    if (hide) {
      hide.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        backToEvent(cam);
      });
    }
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && cam.classList.contains("is-open")) backToEvent(cam);
    });
    paintCam(cam);
    paintWx(cam);
    window.setInterval(function () {
      if (!document.hidden) {
        paintCam(cam);
        paintWx(cam);
      }
    }, POLL_MS);
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) {
        paintCam(cam);
        paintWx(cam);
      }
    });
  }

  function cupVideos() {
    return [
      {
        id: "midmar-cup-1",
        kind: "photo",
        title: "Midmar Cup",
        fb_title: "Midmar Cup",
        fb_sub: "Henley Midmar Yacht Club",
        thumb: CUP_SRC,
        play_url: CUP_SRC,
        aspect: "3 / 4",
        width: 3,
        height: 4,
      },
    ];
  }

  function makeMmCard() {
    var mm = document.getElementById(MM_ID) || document.createElement("section");
    mm.id = MM_ID;
    mm.className = "card mm-lipton-reels mm-lipton-reels--compact";
    mm.setAttribute("data-regatta-id", RID);
    mm.setAttribute("data-mm-brand-soon", MM_BRAND);
    mm.setAttribute(
      "data-mm-initial",
      JSON.stringify({ enabled: true, feed_source: "midmar", videos: cupVideos() })
    );
    mm.innerHTML =
      '<div class="mm-lipton-reels-compact">' +
      '<a class="mm-lipton-reels-brand" href="https://www.marinemegastore.co.za/" target="_blank" rel="noopener noreferrer">' +
      '<img src="' +
      MM_BRAND +
      '" alt="Powered by Marine Megastore Event Reels" width="320" height="213" loading="lazy" decoding="async">' +
      "</a>" +
      '<div class="mm-lipton-reels-rail-wrap">' +
      '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--prev" data-mm-rail-prev aria-label="Previous clips" hidden>‹</button>' +
      '<div class="mm-lipton-reels-rail" data-mm-compact></div>' +
      '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--next" data-mm-rail-next aria-label="Next clips" hidden>›</button>' +
      "</div></div>";
    return mm;
  }

  function loadCss(href) {
    var base = href.split("?")[0];
    if (document.querySelector('link[href*="' + base + '"]')) return;
    var l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = href;
    document.head.appendChild(l);
  }

  function placeHost() {
    var existing = document.getElementById(HOST_ID);
    var host = existing || document.createElement("div");
    host.id = HOST_ID;
    host.className = "midmar-live-media club-live-media";
    host.setAttribute("aria-label", "Live weather and club camera");

    var header = document.querySelector(".regatta-header-wrap");
    var fleet = document.querySelector(".fleet-section");
    var page = document.querySelector(".regatta-page");
    if (header && header.parentNode) {
      if (host.previousSibling !== header) header.parentNode.insertBefore(host, header.nextSibling);
    } else if (fleet && fleet.parentNode) {
      fleet.parentNode.insertBefore(host, fleet);
    } else if (page) {
      page.insertBefore(host, page.firstChild);
    } else {
      return null;
    }

    var wx = makeWx();
    var mm = makeMmCard();
    var cam = makeCam();
    if (wx.parentNode !== host) host.appendChild(wx);
    if (mm.parentNode !== host) host.appendChild(mm);
    if (cam.parentNode !== host) host.appendChild(cam);
    if (wx.nextSibling !== mm) host.insertBefore(mm, wx.nextSibling);
    if (mm.nextSibling !== cam) host.insertBefore(cam, mm.nextSibling);
    bindCam(cam);
    return host;
  }

  function loadScript(src) {
    return new Promise(function (resolve) {
      var base = src.split("?")[0];
      var found = document.querySelector('script[src*="' + base + '"]');
      if (found) {
        resolve();
        return;
      }
      var s = document.createElement("script");
      s.src = src;
      s.async = false;
      s.onload = function () {
        resolve();
      };
      s.onerror = function () {
        resolve();
      };
      document.head.appendChild(s);
    });
  }

  function boot() {
    if (!onMidmar()) return;
    injectCss();
    injectFleetResultsStatus();
    if (!placeHost()) return;
    loadCss("/css/mm-lipton-reels.css?v=" + JS_VER);
    loadScript("/js/mm-lipton-reels-card.js?v=" + JS_VER);
    loadScript("/js/regatta-slot-card.js?v=" + JS_VER).then(function () {
      var wx = document.getElementById(WX_ID);
      if (wx && typeof window.ssaMountWeatherCard === "function") {
        window.ssaMountWeatherCard(wx, { club: "HMYC", slug: "agromet-midmar", role: "venue" });
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
