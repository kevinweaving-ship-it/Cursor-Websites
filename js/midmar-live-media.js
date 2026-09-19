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
  var JS_VER = "midmarwx6";
  var EVENT_PATH = "/regatta/" + RID;
  var STILL = "https://hmyccam1.nwsza.net/latest.jpg";
  var POLL_MS = 60000;

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
      ".regatta-page > .midmar-live-media .midmar-hmyc-cam{order:1;margin-top:10px;width:100%;max-width:100%;padding:0!important;overflow:hidden;background:#000;}",
      ".midmar-hmyc-cam .cam-frame{position:relative;display:block;width:100%;aspect-ratio:16/9;background:#000;overflow:hidden;margin:0;padding:0;border:0;cursor:pointer;-webkit-tap-highlight-color:transparent;}",
      ".midmar-hmyc-cam .cam-frame img{display:block;width:100%;height:118%;margin-top:-10%;object-fit:cover;object-position:center bottom;background:#000;}",
      "body:has(.midmar-hmyc-cam.is-open) .site-header{display:none!important;}",
      "body.midmar-cam-open{overflow:hidden;}",
      ".midmar-hmyc-cam.is-open{position:fixed;inset:0;z-index:2147483000;width:100vw;max-width:100vw;height:100vh;height:100dvh;margin:0;border:0;border-radius:0;background:#000;overflow:hidden;}",
      ".midmar-hmyc-cam.is-open .cam-frame{height:100%;aspect-ratio:auto;cursor:default;}",
      ".midmar-hmyc-cam.is-open .cam-frame img{width:100%;height:100%;margin:0;object-fit:contain;object-position:center center;}",
      ".midmar-hmyc-cam .mm-lipton-reels-expanded-bar{display:none;}",
      ".midmar-hmyc-cam.is-open .mm-lipton-reels-expanded-bar{display:flex;position:absolute;top:0;right:0;z-index:6;justify-content:flex-end;align-items:flex-start;margin:0;padding:0;pointer-events:none;}",
      ".midmar-hmyc-cam .mm-lipton-reels-hide{display:none;}",
      ".midmar-hmyc-cam.is-open .mm-lipton-reels-hide{display:flex;align-items:center;justify-content:center;min-height:44px;min-width:44px;padding:10px 12px;margin:0;border:0;background:transparent;cursor:pointer;pointer-events:auto;color:#dc2626!important;font-size:0.95rem!important;font-weight:800!important;letter-spacing:.02em;font-family:Arial,Helvetica,sans-serif;}",
      ".midmar-hmyc-cam .mm-lipton-reels-cam-stamp{position:absolute;left:8px;top:8px;z-index:3;pointer-events:none;display:flex;flex-direction:row;align-items:center;gap:5px;padding:2px 8px;border-radius:4px;background:rgba(0,16,24,.72);color:#fff;white-space:nowrap;text-shadow:0 1px 2px rgba(0,0,0,.85);font:700 11px/1.2 Arial,Helvetica,sans-serif;}",
      ".midmar-hmyc-cam .mm-lipton-reels-cam-stamp-dot{flex:0 0 auto;width:8px;height:8px;border-radius:50%;background:#94a3b8;}",
      ".midmar-hmyc-cam .mm-lipton-reels-cam-stamp [data-mm-cam-stamp-label]{font-weight:800;letter-spacing:.03em;}",
      ".midmar-hmyc-cam .mm-lipton-reels-cam-stamp [data-mm-cam-stamp-time]{font-weight:700;opacity:.95;}",
      ".midmar-hmyc-cam .midmar-cam-wx{display:none;}",
      ".midmar-hmyc-cam.is-open .midmar-cam-wx{position:absolute;top:48px;right:8px;z-index:4;pointer-events:none;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;gap:1px;min-width:0;padding:0;border:0;border-radius:0;background:none;color:#fff;text-align:center;text-shadow:0 1px 2px rgba(0,0,0,.85);box-sizing:border-box;}",
      ".midmar-hmyc-cam .midmar-cam-wx-temp,.midmar-hmyc-cam .midmar-cam-wx-kn{display:block;width:100%;margin:0;padding:0;text-align:center;font:800 8px/1.1 Arial,Helvetica,sans-serif;letter-spacing:.02em;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge{display:block;width:36px;height:36px;margin:0 auto;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge svg{display:block;width:36px;height:36px;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .dt{stroke:#cbd5e1;stroke-width:1;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .dt.card{stroke:#fff;stroke-width:1.4;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .darc{fill:none;stroke:#93c5fd;stroke-width:5;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .dhead{fill:#3b82f6;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .dpt{font:700 16px Arial,Helvetica,sans-serif;fill:#fff;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .ddeg{font:700 12px Arial,Helvetica,sans-serif;fill:#fff;}",
      ".midmar-hmyc-cam .midmar-cam-wx-gauge .dcard{font:700 10px Arial,Helvetica,sans-serif;fill:#e2e8f0;}",
      "@media screen and (orientation:portrait) and (max-width:767px){",
      ".regatta-page > .midmar-live-media .midmar-hmyc-cam:not(.is-open){width:100vw;max-width:100vw;margin-left:calc(50% - 50vw);margin-right:calc(50% - 50vw);border-left:0;border-right:0;border-radius:0;}",
      "}",
      "@media print{.midmar-live-media{display:none!important}}",
    ].join("");
    document.head.appendChild(s);
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
      '<img alt="HMYC club cam" width="1600" height="900" decoding="async">' +
      '<div class="mm-lipton-reels-cam-stamp mm-lipton-reels-cam-stamp--off" data-mm-cam-stamp>' +
      '<span class="mm-lipton-reels-cam-stamp-dot" aria-hidden="true"></span>' +
      '<span data-mm-cam-stamp-label>SNAPSHOT</span>' +
      '<span data-mm-cam-stamp-time></span>' +
      "</div>" +
      '<div class="midmar-cam-wx" data-mm-cam-wx aria-hidden="true">' +
      '<div class="midmar-cam-wx-temp" data-mm-cam-wx-temp>—</div>' +
      '<div class="midmar-cam-wx-gauge" data-mm-cam-wx-gauge></div>' +
      '<div class="midmar-cam-wx-kn" data-mm-cam-wx-kn>— kn</div>' +
      "</div></button>";
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

  function drawMiniGauge(deg, kn) {
    var CX = 50;
    var CY = 50;
    var R = 40;
    var col = bandCol(kn);
    var d = deg != null && !isNaN(deg) ? ((Number(deg) % 360) + 360) % 360 : null;
    var di = dirIdx(d);
    var pt = di != null ? PTS[di] : "";
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
    if (d != null) {
      var a0 = d - 11.25;
      var a1 = d + 11.25;
      var p0 = pol(CX, CY, R - 3, a0);
      var p1 = pol(CX, CY, R - 3, a1);
      svg +=
        '<path class="darc" style="stroke:' +
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
      var hp = pol(CX, CY, R + 2, d);
      svg +=
        '<g transform="translate(' +
        hp[0].toFixed(1) +
        " " +
        hp[1].toFixed(1) +
        ") rotate(" +
        (d + 180) +
        ')"><path class="dhead" style="fill:' +
        col +
        '" d="M0 -10L8 5L0 2L-8 5Z"/></g>';
    }
    svg +=
      '<text class="dpt" x="50" y="46" text-anchor="middle" dominant-baseline="central">' +
      (pt || "—") +
      "</text>";
    if (d != null) {
      svg +=
        '<text class="ddeg" x="50" y="64" text-anchor="middle">' +
        Math.round(d) +
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
    fetch("/api/weather/agromet-midmar/history?hours=1&_=" + Date.now(), {
      cache: "no-store",
      credentials: "same-origin",
    })
      .then(function (r) {
        if (!r.ok) throw new Error("wx");
        return r.json();
      })
      .then(function (body) {
        var rows = (body && body.readings) || [];
        var last = rows.length ? rows[rows.length - 1] : {};
        var kn = last.wind_kt != null ? last.wind_kt : last.wind_avg_kt;
        var deg = last.wind_dir_deg != null ? last.wind_dir_deg : last.wind_dir_avg_deg;
        var temp = last.temp_c;
        tempEl.textContent = temp == null || isNaN(temp) ? "—" : n1(temp) + "°C";
        knEl.textContent = kn == null || isNaN(kn) ? "— kn" : n1(kn) + " kn";
        gaugeEl.innerHTML = drawMiniGauge(deg, kn);
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
    var cam = makeCam();
    if (wx.parentNode !== host) host.appendChild(wx);
    if (cam.parentNode !== host) host.appendChild(cam);
    if (wx.nextSibling !== cam) host.insertBefore(wx, cam);
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
    if (!placeHost()) return;
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
