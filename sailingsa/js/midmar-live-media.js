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
  // MIDMAR_MEDIA_ROTATE_v1
  // MIDMAR_TOGGLE_DROP_FIX_v1
  // MIDMAR_PUBLIC_DROP_v1
  // MIDMAR_DROP_PE_v1
  // MIDMAR_MEDIA_UNSQUASH_v1
  var JS_VER = "midmarwx57";
  var EVENT_PATH = "/regatta/" + RID;
  var STILL = "https://hmyccam1.nwsza.net/latest.jpg";
  var POLL_MS = 60000;
  var MM_ID = "mmLiptonReels";
  var TRAIN_SRC = "/img/Midmar-Last-Minute-Training.mp4";
  var TRAIN_THUMB = "/img/Midmar-Last-Minute-Training.jpg";
  var CUP_THUMB = "/img/midmar-cup-event.jpg";

  function currentRid() {
    var path = String((window.location && window.location.pathname) || "")
      .replace(/\/+$/, "")
      .toLowerCase();
    var m = path.match(/^\/regatta\/([^/]+)/);
    return m ? m[1] : RID;
  }
  function onMidmar() {
    var rid = currentRid();
    return rid === RID || rid === "2026-09-24-hmyc-dart-18-nationals" || rid === "2026-09-25-tsc-420-nationals";
  }
  function emptyMedia() {
    return currentRid() !== RID;
  }
  function isDartNats() {
    return currentRid().indexOf("2026-09-24-hmyc-dart-18-nationals") === 0;
  }

  function hasWxCam() {
    var rid = currentRid();
    return rid === RID || rid === "2026-09-24-hmyc-dart-18-nationals";
  }

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement("style");
    s.id = CSS_ID;
    s.textContent = [
      ".regatta-page > .midmar-live-media{width:100%;max-width:100%;box-sizing:border-box;display:flex;flex-direction:column;gap:0;margin:0;padding:0;border:0;background:transparent;box-shadow:none;}",
      ".regatta-page > .midmar-live-media .ssa-regatta-slot-card{order:0;margin-top:10px;width:100%;max-width:100%;padding:0!important;}",
      ".regatta-page > .midmar-live-media .midmar-mm-row{order:1;display:flex;flex-direction:column;flex-wrap:nowrap;align-items:stretch;gap:10px;margin-top:10px;width:100%;}",
      ".regatta-page > .midmar-live-media .midmar-mm-row > .mm-lipton-reels{flex:1 1 auto;width:100%!important;max-width:100%!important;}",
      ".regatta-page > .midmar-live-media .midmar-mm-row > .midmar-mm-sa{flex:0 0 auto;width:100%;max-width:100%;}",
      ".midmar-live-media .mm-lipton-reels-grid .mm-lipton-reels-thumb,.midmar-live-media .mm-lipton-reels-days .mm-lipton-reels-thumb{aspect-ratio:16/9!important;height:auto!important;}",
      ".regatta-page > .midmar-live-media .mm-lipton-reels-brand{display:none!important;}",".regatta-page > .midmar-live-media .mm-lipton-reels[data-regatta-id^='2026-09-24-hmyc-dart-18-nationals'] .mm-lipton-reels-brand{display:block!important;}",
      ".regatta-page > .midmar-live-media .mm-midmar-cup-thumb{flex:0 0 auto;position:sticky;left:0;z-index:3;align-self:stretch;}",
      ".midmar-live-media .mm-midmar-cup-thumb .mm-lipton-reels-play,.midmar-live-media .mm-lipton-reels-tile[aria-label=\"View photo\"] .mm-lipton-reels-play{display:none!important;}",
      ".midmar-live-media .mm-lipton-reels-compact .mm-lipton-reels-clip-chrome{display:none!important;}",
      ".midmar-live-media .mm-lipton-reels-thumb,.midmar-live-media .mm-lipton-reels-tile{overflow:hidden!important;}",
      ".midmar-live-media .mm-lipton-reels-tile--reel:not(.mm-midmar-cup-thumb){border-left:0!important;border-right:0!important;}",
      ".midmar-live-media .mm-lipton-reels:not([data-regatta-id^='2026-09-24-hmyc-dart-18-nationals']) .mm-lipton-reels-tile--reel:not(.mm-midmar-cup-thumb) .mm-lipton-reels-thumb{border-left:0!important;border-right:0!important;border-radius:0!important;background:#000;}",
      ".midmar-live-media .mm-lipton-reels-thumb img{display:block;width:100%;height:100%;object-fit:cover;object-position:center;}",
      ".midmar-live-media .mm-lipton-reels-when{position:absolute;left:3px;right:3px;bottom:3px;z-index:5;display:flex;flex-direction:row;flex-wrap:wrap;align-items:baseline;gap:4px;padding:2px 5px;border-radius:3px;background:rgba(0,16,24,.74);color:#fff;pointer-events:none;box-sizing:border-box;}",
      ".midmar-live-media .mm-lipton-reels-when-day,.midmar-live-media .mm-lipton-reels-when-time,.midmar-live-media .mm-lipton-reels-when-meet{font:700 8px/1.15 Arial,Helvetica,sans-serif;white-space:nowrap;}",
      ".midmar-live-media .mm-lipton-reels-clip-copy{min-width:max-content;flex:0 0 auto;}",
      ".midmar-live-media .mm-lipton-reels-clip-chrome--overlay{overflow:visible;width:max-content;max-width:none;z-index:6;}",
      ".midmar-live-media .mm-lipton-reels-clip-title,.midmar-live-media .mm-lipton-reels-clip-chrome--overlay .mm-lipton-reels-clip-title{white-space:nowrap!important;max-width:none!important;overflow:visible!important;display:block!important;-webkit-line-clamp:unset!important;line-clamp:unset!important;max-height:none!important;}",
      ".midmar-live-media .mm-lipton-reels-clip-sub,.midmar-live-media .mm-lipton-reels-clip-chrome--overlay .mm-lipton-reels-clip-sub{display:block!important;white-space:nowrap!important;overflow:visible!important;text-overflow:clip!important;max-width:none!important;}",
      ".midmar-live-media .mm-lipton-reels-stage video.mm-lipton-reels-video--contain{object-fit:contain!important;background:#001018;}",
      ".midmar-live-media .mm-lipton-reels-player-vol{flex:0 0 88px;width:88px;min-width:88px;height:44px;margin:0;padding:0;background:none;accent-color:#00B4FF;}",
      ".midmar-mm-sa[hidden],.regatta-page:not(.regatta-page--super-admin-edit) .midmar-mm-sa{display:none!important;pointer-events:none!important;}",
      ".regatta-page--super-admin-edit .midmar-live-media--sa .midmar-mm-sa:not([hidden]){display:block!important;pointer-events:auto!important;}",
      ".midmar-mm-sa-title{margin:0 0 6px;color:#001f3f;font:800 12px/1.2 Arial,Helvetica,sans-serif;letter-spacing:.04em;text-transform:uppercase;}",
      ".midmar-mm-sa-drop{position:relative;border:2px dashed #001f3f;border-radius:8px;min-height:72px;background:#f8fafc;overflow:hidden;cursor:pointer;}",
      ".midmar-mm-sa-drop.is-on{background:#e8eef5;}",
      ".midmar-mm-sa-file{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);border:0;opacity:0;pointer-events:none;}",
      ".midmar-mm-sa-drop{cursor:pointer;}",
      ".midmar-mm-sa-drop-visual{min-height:72px;display:flex;align-items:center;justify-content:flex-start;padding:8px;text-align:center;color:#334155;font:700 12px/1.3 Arial,Helvetica,sans-serif;}",
      ".midmar-mm-sa-drop-visual img,.midmar-mm-sa-drop-visual video{display:block;height:120px;width:auto;max-width:100%;object-fit:contain;background:#0b1c33;border-radius:6px;}",
      ".midmar-mm-sa-drop[data-mm-sa-orient=\"portrait\"] .midmar-mm-sa-drop-visual img,.midmar-mm-sa-drop[data-mm-sa-orient=\"portrait\"] .midmar-mm-sa-drop-visual video{height:120px;width:auto;aspect-ratio:9/16;object-fit:cover;}",
      ".midmar-mm-sa-drop[data-mm-sa-orient=\"landscape\"] .midmar-mm-sa-drop-visual img,.midmar-mm-sa-drop[data-mm-sa-orient=\"landscape\"] .midmar-mm-sa-drop-visual video{height:120px;width:auto;aspect-ratio:16/9;object-fit:cover;}",
      ".midmar-mm-sa-lab{display:block;margin-top:8px;color:#001f3f;font:700 12px/1.2 Arial,Helvetica,sans-serif;}",
      ".midmar-mm-sa-lab input{display:block;width:100%;min-height:44px;margin-top:4px;padding:8px;border:1.5px solid #1a2750;border-radius:8px;box-sizing:border-box;font:400 14px/1.2 Arial,Helvetica,sans-serif;}",
      ".midmar-mm-sa-save{display:block;width:100%;min-height:44px;margin-top:8px;padding:10px 12px;border:1.5px solid #001f3f;border-radius:8px;background:#001f3f;color:#fff;font:700 14px/1.2 Arial,Helvetica,sans-serif;cursor:pointer;}",
      ".midmar-mm-sa-msg{min-height:18px;margin:6px 0 0;color:#334155;font:400 12px/1.3 Arial,Helvetica,sans-serif;}",
      ".regatta-page > .midmar-live-media .midmar-hmyc-cam{order:2;margin-top:10px;width:100%;max-width:100%;padding:0!important;overflow:hidden;background:#000;}",
      ".regatta-page > .midmar-live-media .midmar-hmyc-cam[hidden]{display:none!important;}",
      ".regatta-page:has(.mm-lipton-reels[data-mm-autoplay=\"1\"]) > .midmar-live-media .midmar-hmyc-cam:not(.is-open){width:25%;max-width:25%;min-width:120px;margin-left:auto;margin-right:0;}",
      ".midmar-hmyc-cam .cam-frame{position:relative;display:block;width:100%;aspect-ratio:16/9;background:#000;overflow:hidden;margin:0;padding:0;border:0;cursor:pointer;-webkit-tap-highlight-color:transparent;}",
      ".midmar-hmyc-cam .cam-shot{position:relative;display:block;width:100%;height:100%;overflow:hidden;}",
      ".midmar-hmyc-cam .cam-shot img{display:block;width:100%;height:118%;margin-top:-10%;object-fit:cover;object-position:center bottom;background:#000;}.regatta-page > .fleet-section{margin-top:10px!important;}",
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
      "@media screen and (min-width:768px){",
      ".regatta-page > .midmar-live-media .mm-lipton-reels--expanded{width:100%;max-width:100%;margin-left:0;margin-right:0;border-left:2px solid #001f3f;border-right:2px solid #001f3f;border-radius:8px;}",
      "}",
      "@media screen and (orientation:portrait) and (max-width:767px){",
      ".regatta-page > .midmar-live-media .ssa-regatta-slot-card{width:100%;max-width:100%;margin-left:0;margin-right:0;border:2px solid #001f3f;border-radius:8px;box-sizing:border-box;}",
      ".regatta-page > .midmar-live-media .midmar-hmyc-cam:not(.is-open){width:100vw;max-width:100vw;margin-left:calc(50% - 50vw);margin-right:calc(50% - 50vw);border-left:0;border-right:0;border-radius:0;}",
      ".regatta-page:has(.mm-lipton-reels[data-mm-autoplay=\"1\"]) > .midmar-live-media .midmar-hmyc-cam:not(.is-open){width:25vw;max-width:25vw;min-width:120px;margin-left:auto;margin-right:0;border-radius:8px;}",
      "}",
      "@media print{.midmar-live-media,.mm-lipton-reels{display:none!important}}",
      ".class-header .fleet-results-status{margin-top:6px}",
      ".class-header .fleet-results-as-at,.class-header .fleet-results-as-at-time{margin-top:2px}",
    ].join("");
    document.head.appendChild(s);
  }

  function injectFleetResultsStatus() {
    document.querySelectorAll(".class-header").forEach(function (hdr) {
      hdr.querySelectorAll(
        ".fleet-results-status,.fleet-results-as-at,.fleet-results-as-at-time"
      ).forEach(function (n) {
        n.remove();
      });
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
    if (cam && cam.getAttribute("data-cam-bound") === "1") return cam;
    if (!cam) {
      cam = document.createElement("section");
      cam.id = CAM_ID;
    }
    cam.className = "card midmar-hmyc-cam";
    cam.setAttribute("aria-label", "HMYC club cam");
    cam.setAttribute("data-mm-cam-status", "/api/club-cam/hmyc");
    cam.setAttribute("hidden", "");
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

  function setCamVisible(cam, ok) {
    if (!cam) return;
    if (ok) cam.removeAttribute("hidden");
    else {
      cam.setAttribute("hidden", "");
      setOpen(cam, false);
    }
  }

  function paintCam(cam) {
    if (!cam) return;
    var img = cam.querySelector(".cam-shot img");
    var timeEl = cam.querySelector("[data-mm-cam-stamp-time]");
    fetch("/api/club-cam/hmyc?_=" + Date.now(), { cache: "no-store", credentials: "same-origin" })
      .then(function (r) {
        return r && r.ok ? r.json() : null;
      })
      .then(function (data) {
        if (!(data && data.valid === true)) {
          setCamVisible(cam, false);
          return;
        }
        var now = Date.now();
        if (img) {
          img.onload = function () {
            setCamVisible(cam, img.naturalWidth >= 32 && img.naturalHeight >= 16);
          };
          img.onerror = function () {
            setCamVisible(cam, false);
          };
          img.src = STILL + "?t=" + now;
        }
        if (timeEl) timeEl.textContent = "as at " + fmtHm(now);
      })
      .catch(function () {
        setCamVisible(cam, false);
      });
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
        pinned: true,
        title: "Midmar Cup",
        fb_title: "Midmar Cup",
        fb_sub: "The Midmar Cup",
        stamp: "The Midmar Cup",
        started_at: "1970-01-01T00:00:00+02:00",
        thumb: CUP_THUMB,
        play_url: CUP_THUMB,
        aspect: "9 / 16",
        width: 9,
        height: 16,
      },
      {
        id: "midmar-train-1",
        kind: "video",
        title: "Last minute Training and Setup",
        fb_title: "Last minute Training and Setup",
        fb_sub: "Fri 18 Sep 2026 - 13:59",
        stamp: "Fri 18 Sep 2026 - 13:59",
        started_at: "2026-09-18T13:59:16+02:00",
        thumb: TRAIN_THUMB,
        play_url: TRAIN_SRC,
        aspect: "9 / 16",
        width: 9,
        height: 16,
      },
    ];
  }

  function makeMmCard() {
    var mm = document.getElementById(MM_ID) || document.createElement("section");
    if (mm.getAttribute("data-mm-inited") === "1") return mm;
    mm.id = MM_ID;
    mm.className = "card mm-lipton-reels mm-lipton-reels--compact";
    mm.setAttribute("data-regatta-id", currentRid());
    mm.setAttribute("data-mm-poll", "1");
    if (isDartNats()) {
      mm.setAttribute(
        "data-mm-initial",
        JSON.stringify({ enabled: true, feed_source: "hmyc", fb_page: "henleymidmaryachtclub", videos: [] })
      );
      mm.innerHTML =
        '<div class="mm-lipton-reels-compact">' +
        '<div class="mm-lipton-reels-brand" aria-label="Event Reels">' +
        '<img src="/img/dart-event-reels.jpg?v=dartreel3" alt="Event Reels" width="320" height="213" decoding="async">' +
        '</div>' +
        '<div class="mm-lipton-reels-rail-wrap">' +
        '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--prev" data-mm-rail-prev aria-label="Previous clips" hidden>‹</button>' +
        '<div class="mm-lipton-reels-rail" data-mm-compact></div>' +
        '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--next" data-mm-rail-next aria-label="Next clips" hidden>›</button>' +
        "</div></div>";
      return mm;
    }
    if (emptyMedia()) {
      mm.setAttribute(
        "data-mm-initial",
        JSON.stringify({ enabled: true, feed_source: "event", videos: [] })
      );
      mm.innerHTML =
        '<div class="mm-lipton-reels-compact mm-lipton-reels-empty">' +
        '<h2 class="section-title">Media</h2>' +
        '<p class="midmar-lb-empty">No media yet</p>' +
        "</div>";
      return mm;
    }
    mm.setAttribute(
      "data-mm-initial",
      JSON.stringify({ enabled: true, feed_source: "midmar", videos: cupVideos() })
    );
    mm.innerHTML =
      '<div class="mm-lipton-reels-compact">' +
      '<button type="button" class="mm-lipton-reels-tile mm-lipton-reels-tile--reel mm-midmar-cup-thumb" data-mm-vid="midmar-cup-1" aria-label="View photo">' +
      '<div class="mm-lipton-reels-thumb" style="aspect-ratio:9 / 16">' +
      '<img src="' +
      CUP_THUMB +
      '" alt="Midmar Cup" loading="lazy" decoding="async">' +
      "</div></button>" +
      '<div class="mm-lipton-reels-rail-wrap">' +
      '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--prev" data-mm-rail-prev aria-label="Previous clips" hidden>‹</button>' +
      '<div class="mm-lipton-reels-rail" data-mm-compact></div>' +
      '<button type="button" class="mm-lipton-reels-rail-btn mm-lipton-reels-rail-btn--next" data-mm-rail-next aria-label="Next clips" hidden>›</button>' +
      "</div></div>";
    return mm;
  }

  function makeMmRow() {
    var row = document.getElementById("midmar-mm-row") || document.createElement("div");
    row.id = "midmar-mm-row";
    row.className = "midmar-mm-row";
    return row;
  }

  function nowLocalValue() {
    var d = new Date();
    var p = function (n) {
      return n < 10 ? "0" + n : String(n);
    };
    return (
      d.getFullYear() +
      "-" +
      p(d.getMonth() + 1) +
      "-" +
      p(d.getDate()) +
      "T" +
      p(d.getHours()) +
      ":" +
      p(d.getMinutes())
    );
  }

  function makeSaCard() {
    var sa = document.getElementById("midmar-mm-sa") || document.createElement("section");
    sa.id = "midmar-mm-sa";
    sa.className = "card midmar-mm-sa";
    sa.setAttribute("hidden", "");
    sa.innerHTML =
      '<div class="midmar-mm-sa-title">Add clip</div>' +
      '<div class="midmar-mm-sa-drop" data-mm-sa-drop>' +
      '<input class="midmar-mm-sa-file" type="file" accept="image/*,video/*,.heic,.mp4,.mov,.webm,.m4v,.3gp" aria-label="Drop or choose video or photo">' +
      '<div class="midmar-mm-sa-drop-visual" data-mm-sa-preview>Drop video or photo</div>' +
      "</div>" +
      '<label class="midmar-mm-sa-lab">Label<input type="text" data-mm-sa-label maxlength="120" placeholder="Last minute Training"></label>' +
      '<label class="midmar-mm-sa-lab">Time<input type="datetime-local" data-mm-sa-time></label>' +
      '<button type="button" class="midmar-mm-sa-rot" data-mm-sa-rot title="Rotate 90 degrees">Rotate 90°</button>' +
      '<button type="button" class="midmar-mm-sa-save" data-mm-sa-save>Save to card</button>' +
      '<p class="midmar-mm-sa-msg" data-mm-sa-msg></p>';
    var time = sa.querySelector("[data-mm-sa-time]");
    if (time && !time.value) time.value = nowLocalValue();
    return sa;
  }

  function applyVideos(videos) {
    var mm = document.getElementById(MM_ID);
    if (!mm || !videos) return;
    mm.setAttribute(
      "data-mm-initial",
      JSON.stringify({ enabled: true, feed_source: "midmar", videos: videos })
    );
    if (typeof window.mmLiptonReelsReplaceVideos === "function") {
      window.mmLiptonReelsReplaceVideos(videos);
    }
    if (typeof window.mmApplyClipRotations === "function") {
      window.mmApplyClipRotations(videos);
    }
  }

  function applyExifSize(w, h, orient) {
    w = parseInt(w, 10) || 0;
    h = parseInt(h, 10) || 0;
    if (orient >= 5 && orient <= 8) return { width: h, height: w };
    return { width: w, height: h };
  }

  function jpegOrient(buf) {
    try {
      var v = new DataView(buf);
      if (v.byteLength < 4 || v.getUint16(0) !== 0xffd8) return 1;
      var off = 2;
      while (off + 4 <= v.byteLength) {
        var marker = v.getUint16(off);
        off += 2;
        if (marker === 0xffda) break;
        var len = v.getUint16(off);
        if (len < 2) break;
        if (marker === 0xffe1 && off + len <= v.byteLength) {
          var start = off + 2;
          if (v.getUint32(start) === 0x45786966 && v.getUint16(start + 4) === 0) {
            var tiff = start + 6;
            var le = v.getUint16(tiff) === 0x4949;
            var u16 = function (p) {
              return le ? v.getUint16(p, true) : v.getUint16(p, false);
            };
            var u32 = function (p) {
              return le ? v.getUint32(p, true) : v.getUint32(p, false);
            };
            var ifd = tiff + u32(tiff + 4);
            var n = u16(ifd);
            var i;
            for (i = 0; i < n; i++) {
              var e = ifd + 2 + i * 12;
              if (u16(e) === 0x0112) return u16(e + 8) || 1;
            }
          }
        }
        off += len;
      }
    } catch (e) {}
    return 1;
  }

  function readJpegOrient(file) {
    if (!file || !/jpe?g/i.test(file.type || file.name || "")) {
      return Promise.resolve(1);
    }
    return file
      .slice(0, 131072)
      .arrayBuffer()
      .then(function (buf) {
        return jpegOrient(buf);
      })
      .catch(function () {
        return 1;
      });
  }

  function setDropOrient(drop, w, h) {
    if (!drop) return;
    var portrait = Number(h) > Number(w);
    drop.setAttribute("data-mm-sa-orient", portrait ? "portrait" : "landscape");
  }

  function mediaOk(f) {
    if (!f || !f.size) return false;
    var t = String(f.type || "").toLowerCase();
    var n = String(f.name || "").toLowerCase();
    if (t.indexOf("image/") === 0 || t.indexOf("video/") === 0) return true;
    if (/^vid[-_]/i.test(n) || /whatsapp/i.test(n)) return true;
    if (!t || t === "application/octet-stream") {
      if (/\.(jpe?g|png|gif|webp|heic|heif|mp4|mov|webm|m4v|3gp|3gpp)$/i.test(n)) return true;
      return !n && f.size > 8000;
    }
    return /\.(jpe?g|png|gif|webp|heic|heif|mp4|mov|webm|m4v|3gp|3gpp)$/i.test(n);
  }

  function isVideoFile(file) {
    var t = String((file && file.type) || "").toLowerCase();
    var n = String((file && file.name) || "").toLowerCase();
    return (
      t.indexOf("video/") === 0 ||
      /\.(mp4|mov|webm|m4v|3gp|3gpp)$/i.test(n) ||
      /^vid[-_]/i.test(n)
    );
  }

  function posterFromFile(file) {
    return new Promise(function (resolve) {
      var url = URL.createObjectURL(file);
      var doneOnce = false;
      var done = function (blob, w, h) {
        if (doneOnce) return;
        doneOnce = true;
        try {
          URL.revokeObjectURL(url);
        } catch (e0) {}
        resolve({ blob: blob, width: w, height: h });
      };
      window.setTimeout(function () {
        if (!doneOnce) done(null, isVideoFile(file) ? 9 : 0, isVideoFile(file) ? 16 : 0);
      }, 2200);
      if (isVideoFile(file)) {
        var v = document.createElement("video");
        v.muted = true;
        v.playsInline = true;
        v.preload = "auto";
        var grab = function () {
          var w = v.videoWidth || 0;
          var h = v.videoHeight || 0;
          if (!w || !h) {
            done(null, 9, 16);
            return;
          }
          var c = document.createElement("canvas");
          c.width = w;
          c.height = h;
          try {
            c.getContext("2d").drawImage(v, 0, 0, w, h);
            c.toBlob(
              function (b) {
                done(b, w, h);
              },
              "image/jpeg",
              0.85
            );
          } catch (e) {
            done(null, w, h);
          }
        };
        v.onerror = function () {
          done(null, 9, 16);
        };
        v.onloadedmetadata = function () {
          var dur = Number(v.duration);
          var t = 0.4;
          if (dur && dur === dur && dur > 0) t = Math.min(1, Math.max(0.15, dur * 0.08));
          v.onseeked = grab;
          try {
            v.currentTime = t;
          } catch (e2) {
            grab();
          }
          window.setTimeout(function () {
            if (!doneOnce) grab();
          }, 1400);
        };
        v.src = url;
        try {
          v.load();
        } catch (e4) {}
        return;
      }
      var img = new Image();
      img.onload = function () {
        done(null, img.naturalWidth || 0, img.naturalHeight || 0);
      };
      img.onerror = function () {
        done(null, 0, 0);
      };
      img.src = url;
    });
  }

  function bindSaCard(sa) {
    if (!sa || sa.getAttribute("data-wired") === "1") return;
    sa.setAttribute("data-wired", "1");
    var drop = sa.querySelector("[data-mm-sa-drop]");
    var fi = sa.querySelector(".midmar-mm-sa-file");
    var preview = sa.querySelector("[data-mm-sa-preview]");
    var label = sa.querySelector("[data-mm-sa-label]");
    var time = sa.querySelector("[data-mm-sa-time]");
    var save = sa.querySelector("[data-mm-sa-save]");
    var msg = sa.querySelector("[data-mm-sa-msg]");
    var pending = { file: null, width: 0, height: 0, rotation: 0 };
    function setMsg(t) {
      if (msg) msg.textContent = t || "";
    }
    function showFile(f) {
      pending = { file: f, width: 0, height: 0, rotation: 0 };
      if (drop) drop.classList.add("has-file");
      if (!preview) return;
      preview.textContent = "";
      if (drop) drop.removeAttribute("data-mm-sa-orient");
      var url = URL.createObjectURL(f);
      var isVid = isVideoFile(f);
      var el = isVid ? document.createElement("video") : document.createElement("img");
      el.src = url;
      if (el.tagName === "VIDEO") {
        el.muted = true;
        el.playsInline = true;
        el.preload = "metadata";
      }
      function sized(w, h, orient) {
        var sz = applyExifSize(w, h, orient || 1);
        pending.width = sz.width;
        pending.height = sz.height;
        setDropOrient(drop, sz.width, sz.height);
      }
      function fromEl() {
        var w = el.naturalWidth || el.videoWidth || 0;
        var h = el.naturalHeight || el.videoHeight || 0;
        readJpegOrient(f).then(function (orient) {
          if (w > 0 && h > 0) {
            var decodedPortrait = h > w;
            var filePortrait = applyExifSize(w, h, orient).height > applyExifSize(w, h, orient).width;
            if (decodedPortrait) sized(w, h, 1);
            else sized(w, h, orient);
            return;
          }
          sized(w, h, orient);
        });
      }
      el.onload = fromEl;
      el.onloadedmetadata = fromEl;
      if (el.complete && (el.naturalWidth || el.videoWidth)) fromEl();
      preview.appendChild(el);
    }
    function takeFile(f) {
      if (f && mediaOk(f)) showFile(f);
      else setMsg("Use a photo or video.");
    }
    function onDrop(e) {
      e.preventDefault();
      e.stopPropagation();
      if (drop) drop.classList.remove("is-on");
      var f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      takeFile(f);
    }
    function allowDrag(e) {
      e.preventDefault();
      e.stopPropagation();
      try { if (e.dataTransfer) e.dataTransfer.dropEffect = "copy"; } catch (err) {}
      if (drop) drop.classList.add("is-on");
    }
    if (fi) {
      fi.addEventListener("change", function () {
        var f = fi.files && fi.files[0];
        fi.value = "";
        takeFile(f);
      });
    }
    if (drop) {
      ["dragenter", "dragover"].forEach(function (ev) {
        drop.addEventListener(ev, allowDrag);
      });
      drop.addEventListener("dragleave", function (e) {
        if (!drop.contains(e.relatedTarget)) drop.classList.remove("is-on");
      });
      drop.addEventListener("drop", onDrop, true);
      drop.addEventListener("click", function (e) {
        if (e.target && e.target.closest && e.target.closest("button, input, textarea, a")) return;
        if (fi) fi.click();
      });
    }
    if (sa && sa.getAttribute("data-mm-sa-drag") !== "1") {
      sa.setAttribute("data-mm-sa-drag", "1");
      ["dragenter", "dragover"].forEach(function (ev) {
        sa.addEventListener(ev, allowDrag);
      });
      sa.addEventListener("drop", onDrop, true);
    }
    var rotBtn = sa.querySelector("[data-mm-sa-rot]");
    if (rotBtn) {
      rotBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        pending.rotation = ((pending.rotation || 0) + 90) % 360;
        window.__mmSaRotation = pending.rotation;
        rotBtn.textContent = "Rotate " + pending.rotation + "°";
        var vis = preview && preview.querySelector("img, video");
        if (vis) vis.style.transform = "rotate(" + pending.rotation + "deg)";
        if (drop && pending.width && pending.height) {
          var pw = pending.width, ph = pending.height;
          if (pending.rotation === 90 || pending.rotation === 270) { var t = pw; pw = ph; ph = t; }
          setDropOrient(drop, pw, ph);
        }
      });
    }
    if (save) {
      save.addEventListener("click", function () {
        if (!pending || !pending.file) {
          setMsg("Drop a video or photo first.");
          return;
        }
        var title = ((label && label.value) || "").trim();
        var file = pending.file;
        if (!title) {
          title =
            String(file.name || "")
              .replace(/\.[^.]+$/, "")
              .replace(/^VID[-_]/i, "WhatsApp ")
              .trim() || "WhatsApp clip";
          if (label) label.value = title;
        }
        if (file.size > 48 * 1024 * 1024) {
          setMsg("File too large (max 48MB). Use a shorter clip or compress it.");
          return;
        }
        var when = (time && time.value) || nowLocalValue();
        save.disabled = true;
        setMsg("Saving…");
        var dropW = pending.width;
        var dropH = pending.height;
        posterFromFile(file).then(function (meta) {
          var w = dropW || (meta && meta.width) || 0;
          var h = dropH || (meta && meta.height) || 0;
          if (!w || !h) {
            if (isVideoFile(file)) {
              w = 9;
              h = 16;
            } else {
              w = 16;
              h = 9;
            }
          }
          var fd = new FormData();
          var fname = file.name || (isVideoFile(file) ? "whatsapp.mp4" : "whatsapp.jpg");
          fd.append("file", file, fname);
          fd.append("label", title);
          fd.append("started_at", when);
          fd.append("width", String(w));
          fd.append("height", String(h));
          fd.append("rotation", String((pending && pending.rotation) || window.__mmSaRotation || 0));
          if (meta && meta.blob) fd.append("thumb", meta.blob, "thumb.jpg");
          return fetch("/api/super-admin/regatta/" + encodeURIComponent(currentRid()) + "/mm-clips", {
            method: "POST",
            body: fd,
            credentials: "include",
          }).then(function (r) {
            return r.text().then(function (t) {
              var j = null;
              try {
                j = JSON.parse(t);
              } catch (e) {}
              var detail = "";
              if (j && j.detail) {
                detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
              } else if (r.status === 413) {
                detail = "File too large for the server (max 48MB).";
              } else if (!r.ok) {
                detail = "Save failed (" + r.status + ").";
              }
              return { ok: r.ok, j: j, detail: detail };
            });
          });
        }).then(function (o) {
          save.disabled = false;
          if (!o || !o.ok) {
            setMsg((o && o.detail) || "Save failed.");
            return;
          }
          pending = { file: null, width: 0, height: 0, rotation: 0 };
          if (drop) drop.classList.remove("has-file");
          if (drop) drop.removeAttribute("data-mm-sa-orient");
          if (preview) preview.textContent = "Drop video or photo";
          if (label) label.value = "";
          if (time) time.value = nowLocalValue();
          setMsg("Saved.");
          applyVideos((o.j && o.j.videos) || []);
        }).catch(function (err) {
          save.disabled = false;
          setMsg((err && err.message) || "Save failed. Try a smaller MP4.");
        });
      });
    }
  }

  function saEditOn() {
    var i = document.getElementById("regattaSaEditToggle");
    if (i) return !!i.checked;
    var page = document.querySelector(".regatta-page");
    return !!(page && page.classList.contains("regatta-page--super-admin-edit"));
  }

  function applySaVis(host, sa, isSa) {
    var show = !!isSa && saEditOn();
    if (host) host.classList.toggle("midmar-live-media--sa", !!show);
    if (sa) {
      var row = document.getElementById("midmar-mm-row");
      if (show) {
        sa.removeAttribute("hidden");
        if (row && sa.parentNode !== row) row.appendChild(sa);
      } else {
        sa.setAttribute("hidden", "");
        if (sa.parentNode) sa.parentNode.removeChild(sa);
      }
    }
  }

  function mountSa(host, sa) {
    bindSaCard(sa);
    var isSa = false;
    function paint() {
      applySaVis(host, sa, isSa);
    }
    var tog = document.getElementById("regattaSaEditToggle");
    if (tog) tog.addEventListener("change", paint);
    var page = document.querySelector(".regatta-page");
    if (page && window.MutationObserver) {
      new MutationObserver(paint).observe(page, { attributes: true, attributeFilter: ["class"] });
    }
    var path = encodeURIComponent((window.location && window.location.pathname) || "/");
    fetch("/auth/session?path=" + path, { credentials: "include", cache: "no-store" })
      .then(function (r) {
        return r && r.ok ? r.json() : null;
      })
      .then(function (session) {
        if (typeof window.sailingSessionIsSuperAdmin === "function") {
          isSa = !!window.sailingSessionIsSuperAdmin(session);
        } else if (session && session.is_super_admin === true) isSa = true;
        paint();
      })
      .catch(function () {
        paint();
      });
  }

  function loadCss(href) {
    var base = href.split("?")[0];
    if (document.querySelector('link[href*="' + base + '"]')) return;
    var l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = href;
    document.head.appendChild(l);
  }

  function removeAbandoned() {
    var el = document.getElementById("midmar-abandoned");
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  function placeHost() {
    var existing = document.getElementById(HOST_ID);
    var host = existing || document.createElement("div");
    host.id = HOST_ID;
    host.className = "midmar-live-media club-live-media";
    host.setAttribute("aria-label", "Live weather and club camera");

    removeAbandoned();
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

    var row = makeMmRow();
    var mm = makeMmCard();
    var sa = makeSaCard();
    if (hasWxCam()) {
      var wx = makeWx();
      var cam = makeCam();
      if (wx.parentNode !== host) host.appendChild(wx);
      if (row.parentNode !== host) host.appendChild(row);
      if (mm.parentNode !== row) row.appendChild(mm);
      if (sa.parentNode !== row) row.appendChild(sa);
      if (cam.parentNode !== host) host.appendChild(cam);
      if (wx.nextSibling !== row) host.insertBefore(row, wx.nextSibling);
      if (row.nextSibling !== cam) host.insertBefore(cam, row.nextSibling);
      bindCam(cam);
    } else {
      host.setAttribute("aria-label", "Event media");
      if (mm.parentNode !== host) host.appendChild(mm);
      if (sa.parentNode !== host) host.appendChild(sa);
    }
    mountSa(host, sa);
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
    if (isDartNats()) {
    loadCss("/css/mm-lipton-reels.css?v=hmycdart24");
    loadScript("/js/mm-lipton-reels-card.js?v=hmycdart24").then(function () {
      if (typeof window.mmLiptonReelsInit === "function") window.mmLiptonReelsInit();
    });
    } else if (!emptyMedia()) {
    loadCss("/css/mm-lipton-reels.css?v=" + JS_VER);
    loadScript("/js/mm-lipton-reels-card.js?v=" + JS_VER).then(function () {
      fetch("/api/regatta/" + encodeURIComponent(currentRid()) + "/mm-clips", {
        credentials: "same-origin",
        cache: "no-store",
      })
        .then(function (r) {
          return r && r.ok ? r.json() : null;
        })
        .then(function (data) {
          if (data && data.videos && data.videos.length) applyVideos(data.videos);
        })
        .catch(function () {})
        .then(function () {
          if (typeof window.mmLiptonReelsInit === "function") window.mmLiptonReelsInit();
        });
    });
    }
    // MIDMAR_LEADERBOARD_v1: compact 1st/2nd/3rd between header and weather.
    loadScript("/js/midmar-leaderboard.js?v=mmlb17");
    if (hasWxCam()) {
    loadScript("/js/midmar-media-rotate.js?v=mmrot4");
    loadScript("/js/regatta-slot-card.js?v=" + JS_VER).then(function () {
      var wx = document.getElementById(WX_ID);
      if (wx && typeof window.ssaMountWeatherCard === "function") {
        window.ssaMountWeatherCard(wx, { club: "HMYC", slug: "agromet-midmar", role: "venue" });
      }
    });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
