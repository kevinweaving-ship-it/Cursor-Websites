/**
 * TSC venue outlook — SailingSA compact card (test: /club/tsc?wx=v2).
 * Own layout/tokens. Does not clone Theewater Weather chrome.
 * Leaves #ssa-regatta-slot-card (122px station card) and the club cam untouched.
 */
(function (global) {
  "use strict";

  var ROOT_ID = "ssa-wx-venue-tsc";
  var CSS_ID = "ssa-wx-venue-tsc-css";
  var JS_VER = "tscv1";
  var TWW_API = "https://weather.theewater.co.za/wp-json/theewater-weather/v1";
  var OM_URL =
    "https://api.open-meteo.com/v1/forecast?latitude=-34.0264&longitude=19.2624" +
    "&hourly=wind_speed_10m,wind_gusts_10m,wind_direction_10m,weather_code,is_day" +
    "&forecast_days=3&wind_speed_unit=kn&timezone=Africa%2FJohannesburg";
  var CLUB = { lat: -34.0264, lon: 19.2624, label: "TSC" };
  var W2S = { lat: -34.078, lon: 19.289, label: "W2S" };
  var BANDS = [
    [0, 5, "#12b028"],
    [5, 11, "#2563eb"],
    [11, 17, "#e67e00"],
    [17, 23, "#7c3aed"],
    [23, 60, "#DC143C"]
  ];
  var PTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];

  function shouldRun(loc) {
    if (global && global.__SSA_WX_TSC_COMPACT_FORCE__) return true;
    loc = loc || (typeof global.location !== "undefined" ? global.location : null);
    if (!loc) return false;
    var path = String(loc.pathname || "").replace(/\/+$/, "").toLowerCase();
    if (path !== "/club/tsc") return false;
    try {
      return new URLSearchParams(loc.search || "").get("wx") === "v2";
    } catch (e) {
      return /(?:^|[?&])wx=v2(?:&|$)/.test(String(loc.search || ""));
    }
  }

  function bandCol(kn) {
    if (kn == null || isNaN(kn)) return "#94a3b8";
    var i;
    for (i = 0; i < BANDS.length; i += 1) {
      if (kn < BANDS[i][1]) return BANDS[i][2];
    }
    return "#DC143C";
  }

  function dirName(deg) {
    if (deg == null || isNaN(deg)) return "—";
    var i = Math.round((((Number(deg) % 360) + 360) % 360) / 22.5) % 16;
    return PTS[i];
  }

  function n1(x) {
    return x == null || isNaN(x) ? "—" : String(Math.round(Number(x) * 10) / 10);
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function tzTime(ms) {
    try {
      return new Date(ms).toLocaleTimeString("en-GB", {
        timeZone: "Africa/Johannesburg",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
      });
    } catch (e) {
      var d = new Date(ms);
      var h = d.getHours();
      var m = d.getMinutes();
      return (h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m;
    }
  }

  function tzDay(ms) {
    try {
      return new Date(ms).toLocaleDateString("en-GB", {
        timeZone: "Africa/Johannesburg",
        weekday: "short"
      });
    } catch (e) {
      return "";
    }
  }

  function jhbHour(ms) {
    try {
      return Number(
        new Date(ms).toLocaleString("en-GB", {
          timeZone: "Africa/Johannesburg",
          hour: "2-digit",
          hour12: false
        })
      );
    } catch (e) {
      return new Date(ms).getHours();
    }
  }

  function isDaylight(hour) {
    return hour.day !== false && jhbHour(hour.t) >= 6 && jhbHour(hour.t) < 19;
  }

  function rateSail(w, g, thunder) {
    if (thunder) return { lvl: 0, label: "Stay ashore", why: "Thunder in the model — unvalidated" };
    if (w == null || isNaN(w)) return null;
    if (g == null || g < w) g = w;
    if (w < 5) return { lvl: 1, label: "Light", why: "Under 5 kn at 10 m" };
    if (w > 23 || g > 28) return { lvl: 0, label: "Stay ashore", why: "Above the red band on this card" };
    if (w > 17 || g > 22) return { lvl: 1, label: "Fresh", why: "17–23 kn band — experienced crews" };
    return { lvl: 2, label: "Sailable", why: "5–17 kn on SailingSA bands" };
  }

  function ratePower(w, g, thunder) {
    if (thunder) return { lvl: 0, label: "Stay in", why: "Thunder in the model — unvalidated" };
    if (w == null || isNaN(w)) return null;
    if (g == null || g < w) g = w;
    if (w < 11 && g < 15) return { lvl: 2, label: "Usable", why: "Below 11 kn — small-boat chop guide only" };
    if (w < 17 && g < 22) return { lvl: 1, label: "Choppy", why: "11–17 kn — not a racing forecast" };
    return { lvl: 0, label: "Stay in", why: "Above 17 kn — unvalidated for powerboats" };
  }

  function windows(hours, rates, minLvl) {
    var out = [];
    var run = null;
    hours.forEach(function (h, i) {
      var ok = isDaylight(h) && rates[i] && rates[i].lvl >= minLvl;
      if (ok && run && tzDay(h.t) === tzDay(run.start)) run.end = h.t + 3600000;
      else if (ok) {
        if (run) out.push(run);
        run = { start: h.t, end: h.t + 3600000 };
      } else if (run) {
        out.push(run);
        run = null;
      }
    });
    if (run) out.push(run);
    return out.filter(function (r) {
      return r.end - r.start >= 7200000;
    });
  }

  function windowText(r) {
    if (!r) return "No 2-hour daylight window in 48 h";
    return tzDay(r.start) + " " + tzTime(r.start) + "–" + tzTime(r.end);
  }

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement("style");
    s.id = CSS_ID;
    s.textContent = [
      "#ssa-wx-venue-tsc.card{padding:8px 8px 6px!important;margin:10px 0 0;width:100%;max-width:100%;box-sizing:border-box;border:1.5px solid #1a2750;border-radius:8px;background:#fff;box-shadow:0 1px 3px rgba(0,31,63,.08);}",
      "#ssa-wx-venue-tsc .ssa-wxv-head{display:flex;align-items:baseline;justify-content:space-between;gap:8px;margin:0 0 6px;}",
      "#ssa-wx-venue-tsc .ssa-wxv-title{margin:0;font:700 11px/1.2 Arial,Helvetica,sans-serif;letter-spacing:.04em;text-transform:uppercase;color:#001f3f;}",
      "#ssa-wx-venue-tsc .ssa-wxv-test{font:600 10px/1.2 Arial,Helvetica,sans-serif;color:#64748b;}",
      "#ssa-wx-venue-tsc .ssa-wxv-now{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin:0 0 6px;}",
      "#ssa-wx-venue-tsc .ssa-wxv-src{border:1px solid #e2e8f0;border-radius:6px;padding:6px 8px;min-height:44px;box-sizing:border-box;}",
      "#ssa-wx-venue-tsc .ssa-wxv-src b{display:block;font:700 10px/1.2 Arial,Helvetica,sans-serif;text-transform:uppercase;letter-spacing:.03em;color:#64748b;margin:0 0 2px;}",
      "#ssa-wx-venue-tsc .ssa-wxv-src strong{font:800 16px/1.1 Arial,Helvetica,sans-serif;color:#001f3f;}",
      "#ssa-wx-venue-tsc .ssa-wxv-src span{font:600 11px/1.2 Arial,Helvetica,sans-serif;color:#334155;}",
      "#ssa-wx-venue-tsc .ssa-wxv-map{position:relative;height:128px;width:100%;border:1px solid #e2e8f0;border-radius:6px;overflow:hidden;background:#e8eef4;}",
      "#ssa-wx-venue-tsc .ssa-wxv-map .leaflet-container{height:100%;width:100%;background:#e8eef4;font:11px/1.2 Arial,Helvetica,sans-serif;}",
      "#ssa-wx-venue-tsc .ssa-wxv-map .leaflet-control-zoom a{width:28px;height:28px;line-height:28px;}",
      "#ssa-wx-venue-tsc .ssa-wxv-map .leaflet-control-attribution{font-size:9px;background:rgba(255,255,255,.85);}",
      "#ssa-wx-venue-tsc .ssa-wxv-mark{display:flex;flex-direction:column;align-items:center;line-height:0;}",
      "#ssa-wx-venue-tsc .ssa-wxv-pin{background:#001f3f;color:#fff;border:1px solid #fff;border-radius:3px;font:700 9px/16px Arial,Helvetica,sans-serif;padding:0 5px;white-space:nowrap;box-shadow:0 1px 2px rgba(0,31,63,.35);}",
      "#ssa-wx-venue-tsc .ssa-wxv-pin.is-w2s{background:#64748b;}",
      "#ssa-wx-venue-tsc .ssa-wxv-vane{width:0;height:0;margin:0 0 3px;border-left:5px solid transparent;border-right:5px solid transparent;border-bottom:12px solid #001f3f;filter:drop-shadow(0 1px 1px rgba(0,0,0,.35));}",
      "#ssa-wx-venue-tsc .ssa-wxv-map-fallback{display:flex;align-items:center;justify-content:center;height:100%;padding:8px;font:600 12px/1.3 Arial,Helvetica,sans-serif;color:#334155;text-align:center;}",
      "#ssa-wx-venue-tsc .ssa-wxv-hour{display:flex;align-items:center;gap:8px;margin:6px 0;min-height:44px;}",
      "#ssa-wx-venue-tsc .ssa-wxv-hour input{flex:1 1 auto;min-width:0;height:44px;margin:0;}",
      "#ssa-wx-venue-tsc .ssa-wxv-hour-read{flex:0 0 auto;min-width:92px;font:700 12px/1.25 Arial,Helvetica,sans-serif;color:#001f3f;text-align:right;}",
      "#ssa-wx-venue-tsc .ssa-wxv-strip{display:flex;height:18px;gap:1px;margin:0 0 6px;border-radius:3px;overflow:hidden;}",
      "#ssa-wx-venue-tsc .ssa-wxv-strip i{flex:1 1 0;min-width:0;display:block;opacity:.92;}",
      "#ssa-wx-venue-tsc .ssa-wxv-strip i.is-night{opacity:.38;}",
      "#ssa-wx-venue-tsc .ssa-wxv-strip i.is-on{outline:1px solid #001f3f;outline-offset:-1px;}",
      "#ssa-wx-venue-tsc .ssa-wxv-acts{display:grid;gap:4px;margin:0 0 6px;}",
      "#ssa-wx-venue-tsc .ssa-wxv-act{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 8px;align-items:baseline;padding:6px 8px;border:1px solid #e2e8f0;border-radius:6px;min-height:44px;box-sizing:border-box;}",
      "#ssa-wx-venue-tsc .ssa-wxv-act b{font:700 13px/1.2 Arial,Helvetica,sans-serif;color:#001f3f;}",
      "#ssa-wx-venue-tsc .ssa-wxv-act em{grid-column:1 / -1;font:600 11px/1.3 Arial,Helvetica,sans-serif;color:#475569;font-style:normal;}",
      "#ssa-wx-venue-tsc .ssa-wxv-pill{font:800 11px/1 Arial,Helvetica,sans-serif;text-transform:uppercase;letter-spacing:.02em;}",
      "#ssa-wx-venue-tsc .ssa-wxv-pill.lvl-2{color:#12b028;}",
      "#ssa-wx-venue-tsc .ssa-wxv-pill.lvl-1{color:#e67e00;}",
      "#ssa-wx-venue-tsc .ssa-wxv-pill.lvl-0{color:#DC143C;}",
      "#ssa-wx-venue-tsc .ssa-wxv-note{margin:0;padding:4px 2px 0;font:700 9px/1.35 Arial,Helvetica,sans-serif;color:#64748b;text-align:center;}",
      "@media (max-width:480px){",
      "#ssa-wx-venue-tsc .ssa-wxv-now{grid-template-columns:1fr;}",
      "#ssa-wx-venue-tsc .ssa-wxv-map{height:120px;}",
      "#ssa-wx-venue-tsc .ssa-wxv-hour-read{min-width:84px;font-size:11px;}",
      "#ssa-wx-venue-tsc .ssa-wxv-src strong{font-size:15px;}",
      "}",
      "@media (prefers-reduced-motion:reduce){#ssa-wx-venue-tsc .leaflet-fade-anim .leaflet-tile,#ssa-wx-venue-tsc .leaflet-zoom-animated{transition:none!important;}}"
    ].join("");
    document.head.appendChild(s);
  }

  function srcHtml(title, wind, gust, dir, extra) {
    var col = bandCol(wind);
    return (
      '<div class="ssa-wxv-src"><b>' +
      esc(title) +
      "</b><strong style=\"color:" +
      col +
      '">' +
      n1(wind) +
      " kn</strong> <span>G " +
      n1(gust) +
      " · " +
      esc(dirName(dir)) +
      (dir != null && !isNaN(dir) ? " " + Math.round(dir) + "°" : "") +
      (extra ? " · " + esc(extra) : "") +
      "</span></div>"
    );
  }

  function actHtml(name, rate, win) {
    if (!rate) {
      return (
        '<div class="ssa-wxv-act"><b>' +
        esc(name) +
        '</b><span class="ssa-wxv-pill">No data</span><em>Waiting for a forecast hour.</em></div>'
      );
    }
    return (
      '<div class="ssa-wxv-act"><b>' +
      esc(name) +
      '</b><span class="ssa-wxv-pill lvl-' +
      rate.lvl +
      '">' +
      esc(rate.label) +
      "</span><em>" +
      esc(rate.why) +
      " · Best: " +
      esc(windowText(win)) +
      "</em></div>"
    );
  }

  function next48(hours) {
    var now = Date.now();
    return (hours || []).filter(function (h) {
      return h.t >= now - 3600000 && h.t <= now + 48 * 3600000;
    });
  }

  function parseHybrid(fc) {
    var m = fc && fc.models && fc.models.hybrid;
    var time = (fc && fc.time) || [];
    if (!m || !m.wind || !time.length) return { hours: [], source: "" };
    var hours = [];
    var i;
    for (i = 0; i < time.length; i += 1) {
      hours.push({
        t: Number(time[i]) * 1000,
        w: m.wind[i],
        g: m.gust && m.gust[i] != null ? m.gust[i] : m.wind[i],
        dir: m.dir ? m.dir[i] : null,
        day: !m.day || m.day[i] !== 0,
        thunder: m.code && m.code[i] >= 95
      });
    }
    return {
      hours: hours,
      source: "Theewater hybrid (ECMWF/GFS/ICON), station-tuned. Layout is SailingSA."
    };
  }

  function parseOpenMeteo(d) {
    var h = d && d.hourly;
    if (!h || !h.time) return { hours: [], source: "" };
    var hours = [];
    var i;
    for (i = 0; i < h.time.length; i += 1) {
      hours.push({
        t: Date.parse(h.time[i]),
        w: h.wind_speed_10m[i],
        g: h.wind_gusts_10m[i],
        dir: h.wind_direction_10m[i],
        day: !h.is_day || h.is_day[i] === 1,
        thunder: h.weather_code && h.weather_code[i] >= 95
      });
    }
    return { hours: hours, source: "Open-Meteo 10 m wind — not tuned to the club anemometer." };
  }

  function loadJson(url, opts) {
    return fetch(url, opts || { cache: "no-store", credentials: "omit" }).then(function (r) {
      if (!r || !r.ok) throw new Error("http " + (r && r.status));
      return r.json();
    });
  }

  function leafletUrls() {
    var localJs = "/js/vendor/leaflet/leaflet.js";
    var localCss = "/js/vendor/leaflet/leaflet.css";
    var liveJs = "https://sailingsa.co.za/js/vendor/leaflet/leaflet.js";
    var liveCss = "https://sailingsa.co.za/js/vendor/leaflet/leaflet.css";
    var here = typeof global.location !== "undefined" ? String(global.location.origin || "") : "";
    if (here.indexOf("sailingsa.co.za") !== -1) return { js: localJs, css: localCss };
    return { js: liveJs, css: liveCss, fallbackJs: localJs, fallbackCss: localCss };
  }

  function loadLeaflet() {
    if (global.L) return Promise.resolve(global.L);
    var urls = leafletUrls();
    return new Promise(function (resolve) {
      if (!document.querySelector('link[href*="leaflet.css"]')) {
        var css = document.createElement("link");
        css.rel = "stylesheet";
        css.href = urls.css;
        document.head.appendChild(css);
      }
      function tag(src, next) {
        var s = document.createElement("script");
        s.src = src;
        s.onload = function () {
          resolve(global.L || null);
        };
        s.onerror = function () {
          if (next) tag(next);
          else resolve(null);
        };
        document.head.appendChild(s);
      }
      tag(urls.js, urls.fallbackJs);
    });
  }

  function pinIcon(L, extra) {
    return L.divIcon({
      className: "",
      html: '<div class="ssa-wxv-pin' + (extra ? " " + extra : "") + '">' + (extra === "is-w2s" ? "W2S" : "TSC") + "</div>",
      iconSize: [34, 18],
      iconAnchor: [17, 18]
    });
  }

  function clubIcon(L, deg) {
    var rot = deg == null || isNaN(deg) ? 0 : Number(deg) + 180;
    return L.divIcon({
      className: "",
      html:
        '<div class="ssa-wxv-mark"><div class="ssa-wxv-vane" style="transform:rotate(' +
        rot +
        'deg)"></div><div class="ssa-wxv-pin">TSC</div></div>',
      iconSize: [36, 34],
      iconAnchor: [18, 34]
    });
  }

  function bindMap(root, state) {
    var box = root.querySelector(".ssa-wxv-map");
    if (!box) return Promise.resolve();
    return loadLeaflet().then(function (L) {
      if (!L) {
        box.innerHTML =
          '<div class="ssa-wxv-map-fallback">Club ' +
          CLUB.lat.toFixed(3) +
          ", " +
          CLUB.lon.toFixed(3) +
          " · Wind2Speed " +
          W2S.lat.toFixed(3) +
          ", " +
          W2S.lon.toFixed(3) +
          "</div>";
        return;
      }
      box.innerHTML = "";
      var map = L.map(box, { zoomControl: false, attributionControl: true, scrollWheelZoom: false });
      L.control.zoom({ position: "topright" }).addTo(map);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap",
        maxZoom: 16
      }).addTo(map);
      var club = L.marker([CLUB.lat, CLUB.lon], { icon: clubIcon(L, 0), title: "TSC club station" }).addTo(map);
      L.marker([W2S.lat, W2S.lon], { icon: pinIcon(L, "is-w2s"), title: "Wind2Speed dam station" }).addTo(map);
      map.fitBounds(
        [
          [CLUB.lat, CLUB.lon],
          [W2S.lat, W2S.lon]
        ],
        { padding: [28, 28], maxZoom: 11 }
      );
      state.map = map;
      state.clubMarker = club;
      state.L = L;
      setTimeout(function () {
        map.invalidateSize();
      }, 80);
      club.getElement();
    });
  }

  function paintVane(state, hour) {
    if (!state.clubMarker || !state.L) return;
    state.clubMarker.setIcon(clubIcon(state.L, hour && hour.dir));
  }

  function mountRoot() {
    var existing = document.getElementById(ROOT_ID);
    if (existing) return existing;
    var el = document.createElement("section");
    el.id = ROOT_ID;
    el.className = "card ssa-wx-venue-tsc";
    el.setAttribute("aria-label", "TSC venue outlook test");
    var host = document.getElementById("club-live-media");
    var wx = document.getElementById("ssa-regatta-slot-card");
    var cam =
      document.getElementById("tsc-club-cam") ||
      document.querySelector(".club-tsc-cam, .club-live-cam");
    if (wx && wx.parentNode) {
      if (cam && cam.parentNode === wx.parentNode) wx.parentNode.insertBefore(el, cam);
      else wx.parentNode.insertBefore(el, wx.nextSibling);
    } else if (host) {
      host.appendChild(el);
    } else {
      var ident = document.querySelector(".club-story-identity");
      if (ident && ident.parentNode) ident.parentNode.insertBefore(el, ident.nextSibling);
      else return null;
    }
    return el;
  }

  function render(root, state) {
    var hours = next48(state.hours);
    if (state.idx == null || state.idx >= hours.length) state.idx = 0;
    var hour = hours[state.idx] || hours[0];
    var club = state.club;
    var dam = state.dam;
    var sailNow = rateSail(hour && hour.w, hour && hour.g, hour && hour.thunder);
    var powerNow = ratePower(hour && hour.w, hour && hour.g, hour && hour.thunder);
    var sailRates = hours.map(function (h) {
      return rateSail(h.w, h.g, h.thunder);
    });
    var powerRates = hours.map(function (h) {
      return ratePower(h.w, h.g, h.thunder);
    });
    var sailWin = windows(hours, sailRates, 2)[0] || windows(hours, sailRates, 1)[0];
    var powerWin = windows(hours, powerRates, 2)[0] || windows(hours, powerRates, 1)[0];
    var strip = hours
      .map(function (h, i) {
        var night = !isDaylight(h);
        return (
          '<i class="' +
          (i === state.idx ? "is-on" : "") +
          (night ? " is-night" : "") +
          '" style="background:' +
          bandCol(h.w) +
          '" title="' +
          esc(tzDay(h.t) + " " + tzTime(h.t) + " " + n1(h.w) + " kn") +
          '"></i>'
        );
      })
      .join("");
    var clubLine = club
      ? srcHtml("Club anemometer", club.wind, club.gust, club.dir, club.age)
      : srcHtml("Club anemometer", null, null, null, "Not on this origin");
    var damLine = dam
      ? srcHtml("Wind2Speed (card above)", dam.wind, dam.gust, dam.dir, dam.age)
      : srcHtml("Wind2Speed (card above)", null, null, null, "No reading");

    if (!root.getAttribute("data-wxv-ready")) {
      root.innerHTML =
        '<div class="ssa-wxv-head"><h2 class="ssa-wxv-title">Venue outlook</h2><span class="ssa-wxv-test">Test layout · wx=v2</span></div>' +
        '<div class="ssa-wxv-now" data-wxv-now></div>' +
        '<div class="ssa-wxv-map" role="region" aria-label="TSC and Wind2Speed station map"></div>' +
        '<div class="ssa-wxv-hour"><input type="range" min="0" max="0" value="0" aria-label="Forecast hour"><div class="ssa-wxv-hour-read"></div></div>' +
        '<div class="ssa-wxv-strip" aria-hidden="true"></div>' +
        '<div class="ssa-wxv-acts"></div>' +
        '<p class="ssa-wxv-note"></p>';
      root.setAttribute("data-wxv-ready", "1");
      bindMap(root, state);
      var slider = root.querySelector('input[type="range"]');
      slider.addEventListener("input", function () {
        state.idx = Number(slider.value) || 0;
        render(root, state);
      });
    }

    root.querySelector("[data-wxv-now]").innerHTML = clubLine + damLine;
    root.querySelector(".ssa-wxv-strip").innerHTML = strip || "";
    root.querySelector(".ssa-wxv-acts").innerHTML =
      actHtml("Sailing", sailNow, sailWin) + actHtml("Powerboats", powerNow, powerWin);
    var sliderEl = root.querySelector('input[type="range"]');
    sliderEl.max = String(Math.max(0, hours.length - 1));
    sliderEl.value = String(state.idx || 0);
    root.querySelector(".ssa-wxv-hour-read").textContent = hour
      ? tzDay(hour.t) + " " + tzTime(hour.t) + " · " + n1(hour.w) + " kn G " + n1(hour.g)
      : "No forecast";
    root.querySelector(".ssa-wxv-note").textContent =
      (state.source || "Forecast unavailable.") +
      " Sailing/powerboat rows are a wind-band guide only — not class, skipper or safety advice. Instrument readings are at the mast, not on the water.";
    paintVane(state, hour);
    if (state.map) {
      setTimeout(function () {
        state.map.invalidateSize();
      }, 40);
    }
  }

  function ageLabel(iso) {
    var ms = Date.parse(iso);
    if (isNaN(ms)) return "";
    var min = Math.round((Date.now() - ms) / 60000);
    if (min <= 1) return "now";
    if (min < 60) return min + " min ago";
    return tzTime(ms);
  }

  function pickDam(payload) {
    var list = (payload && payload.stations) || [];
    var i;
    var row;
    for (i = 0; i < list.length; i += 1) {
      row = list[i];
      if (row && row.station_slug === "w2s-theewater" && row.usable_for_current) return row;
    }
    for (i = 0; i < list.length; i += 1) {
      if (list[i] && list[i].role === "venue") return list[i];
    }
    return null;
  }

  function loadAll() {
    var clubP = loadJson(TWW_API + "/current?_=" + Date.now()).then(
      function (c) {
        return {
          wind: c.wind_10min_kt != null ? c.wind_10min_kt : c.wind_kt,
          gust: c.gust_max_10min_kt != null ? c.gust_max_10min_kt : c.gust_kt,
          dir: c.dir,
          age: "club push"
        };
      },
      function () {
        return null;
      }
    );
    var damP = loadJson("/api/weather/clubs/TSC/stations?_=" + Date.now(), {
      cache: "no-store",
      credentials: "same-origin"
    }).catch(function () {
      return loadJson("https://sailingsa.co.za/api/weather/clubs/TSC/stations?_=" + Date.now(), {
        cache: "no-store",
        credentials: "omit"
      });
    }).then(
      function (body) {
        var row = pickDam(body);
        if (!row) return null;
        return {
          wind: row.wind_kt != null ? row.wind_kt : row.wind_avg_kt,
          gust: row.wind_gust_kt,
          dir: row.wind_dir_deg != null ? row.wind_dir_deg : row.wind_dir_avg_deg,
          age: ageLabel(row.observed_at)
        };
      },
      function () {
        return null;
      }
    );
    var fcP = loadJson(TWW_API + "/forecast?_=" + Date.now()).then(
      function (d) {
        return parseHybrid(d);
      },
      function () {
        return loadJson(OM_URL).then(parseOpenMeteo);
      }
    );
    return Promise.all([clubP, damP, fcP]);
  }

  function boot() {
    if (!shouldRun()) return;
    if (global.__SSA_WX_TSC_COMPACT__) return;
    global.__SSA_WX_TSC_COMPACT__ = true;
    injectCss();
    var tries = 0;
    function go() {
      var root = mountRoot();
      if (!root) {
        tries += 1;
        if (tries < 40) {
          setTimeout(go, 200);
        }
        return;
      }
      var state = { hours: [], idx: 0, source: "" };
      function tick() {
        loadAll()
          .then(function (parts) {
            state.club = parts[0];
            state.dam = parts[1];
            state.hours = (parts[2] && parts[2].hours) || [];
            state.source = (parts[2] && parts[2].source) || "Forecast unavailable.";
            if (state.idx == null) state.idx = 0;
            render(root, state);
          })
          .catch(function () {
            render(root, state);
          });
      }
      tick();
      setInterval(function () {
        if (!document.hidden) tick();
      }, 60000);
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go);
    else go();
  }

  var api = {
    shouldRun: shouldRun,
    bandCol: bandCol,
    rateSail: rateSail,
    ratePower: ratePower,
    parseHybrid: parseHybrid,
    parseOpenMeteo: parseOpenMeteo,
    next48: next48,
    JS_VER: JS_VER
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
    return;
  }
  boot();
})(typeof window !== "undefined" ? window : globalThis);
