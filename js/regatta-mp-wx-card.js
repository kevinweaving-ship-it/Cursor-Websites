/* Compact MP weather strip: under the event header, above the Marine Megastore card.
   Data: GET /api/live-wx/table-bay (same feed as the full live weather panel). */
(function () {
  var CSS_ID = "ssa-regatta-mp-wx-css";
  var ROOT_ID = "ssa-regatta-mp-wx";
  var CAPE_CLASSIC_ID = "2026-09-13-zvyc-cape-classic";
  var JS_VER = "20260911wx1";

  function injectCss() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement("style");
    s.id = CSS_ID;
    s.textContent = [
      ".ssa-regatta-mp-wx{display:block;width:100%;margin:10px 0 0;padding:8px;box-sizing:border-box;background:#fff;border:1.5px solid #1a2750;border-radius:8px;box-shadow:0 1px 3px rgba(0,31,63,.08);}",
      ".ssa-regatta-mp-wx-bar{display:flex;align-items:baseline;justify-content:space-between;gap:8px;margin:0 0 6px;min-height:18px;}",
      ".ssa-regatta-mp-wx-title{font-size:11px;font-weight:800;color:#1a2750;letter-spacing:.02em;text-transform:uppercase;line-height:1.2;}",
      ".ssa-regatta-mp-wx-stamp{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#64748b;font-size:9px;font-weight:700;line-height:1.2;text-align:right;}",
      ".ssa-regatta-mp-wx-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:5px;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card{border-radius:8px;border:1px solid #cbd5e1;background:#f8fafc;padding:6px 7px;min-width:0;color:#1a2750;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card .lbl{font-size:9px;font-weight:700;color:#64748b;line-height:1.1;margin:0 0 2px;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card .val{font-size:13px;font-weight:800;line-height:1.15;letter-spacing:-.01em;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card .val .u{font-size:10px;font-weight:600;color:#64748b;margin-left:2px;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card--too-low{background:#1e3a5f;border-color:#60a5fa;color:#dbeafe;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card--too-low .lbl,.ssa-regatta-mp-wx .regatta-live-wx-card--too-low .val .u{color:#93c5fd;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card--safe{background:#14532d;border-color:#22c55e;color:#fff;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card--safe .lbl,.ssa-regatta-mp-wx .regatta-live-wx-card--safe .val .u{color:#bbf7d0;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card--caution{background:#92400e;border-color:#f59e0b;color:#fff;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card--caution .lbl,.ssa-regatta-mp-wx .regatta-live-wx-card--caution .val .u{color:#fde68a;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card--stop{background:#b91c1c;border-color:#ef4444;color:#fff;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card--stop .lbl,.ssa-regatta-mp-wx .regatta-live-wx-card--stop .val .u{color:#fecaca;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card--cold{background:#1e3a8a;border-color:#60a5fa;color:#fff;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card--cold .lbl,.ssa-regatta-mp-wx .regatta-live-wx-card--cold .val .u{color:#bfdbfe;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card--warm{background:#b45309;border-color:#fbbf24;color:#fff;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card--warm .lbl,.ssa-regatta-mp-wx .regatta-live-wx-card--warm .val .u{color:#fde68a;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card--hot{background:#c2410c;border-color:#fb923c;color:#fff;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card--hot .lbl,.ssa-regatta-mp-wx .regatta-live-wx-card--hot .val .u{color:#ffedd5;}",
      "@media screen and (orientation:portrait) and (max-width:767px){",
      ".ssa-regatta-mp-wx{margin:8px 0 0;padding:7px;}",
      ".ssa-regatta-mp-wx-title{font-size:10px;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card{padding:5px 6px;}",
      ".ssa-regatta-mp-wx .regatta-live-wx-card .val{font-size:12px;}",
      "}"
    ].join("");
    document.head.appendChild(s);
  }

  function fmt(n, d) {
    if (n == null || isNaN(n)) return "—";
    return Number(n).toFixed(d);
  }
  function dirL(deg) {
    var d = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
    return d[Math.round(deg / 22.5) % 16];
  }
  function windBand(kt) {
    if (kt == null || isNaN(kt)) return "";
    if (kt >= 25) return "stop";
    if (kt >= 20) return "caution";
    if (kt >= 5) return "safe";
    return "too-low";
  }
  function tempBand(c) {
    if (c == null || isNaN(c)) return "";
    if (c < 14) return "cold";
    if (c < 20) return "warm";
    return "hot";
  }
  function waveBand(h, p) {
    if (h == null || isNaN(h)) return "";
    if (h >= 2.5) return "stop";
    if (p != null && !isNaN(p) && p < 7 && h >= 1.5) return "stop";
    if (h >= 1.8) return "caution";
    if (p != null && !isNaN(p) && p >= 7 && p <= 9 && h >= 1.5) return "caution";
    return "safe";
  }
  function periodBand(h, p) {
    if (p == null || isNaN(p)) return "";
    if (p < 7 && h != null && h >= 1.5) return "stop";
    if (p >= 7 && p <= 9 && h != null && h >= 1.5) return "caution";
    return h != null && h >= 1.8 ? waveBand(h, p) : "safe";
  }
  function card(label, valueHtml, band) {
    return (
      '<div class="regatta-live-wx-card' +
      (band ? " regatta-live-wx-card--" + band : "") +
      '"><div class="lbl">' +
      label +
      '</div><div class="val">' +
      valueHtml +
      "</div></div>"
    );
  }
  function fmtStamp(ms) {
    try {
      return new Date(Number(ms)).toLocaleString("en-ZA", {
        timeZone: "Africa/Johannesburg",
        weekday: "short",
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
      });
    } catch (e) {
      return "—";
    }
  }

  function mount() {
    if (document.getElementById(ROOT_ID)) return true;
    var marine = document.getElementById("mmLiptonReels");
    if (!marine) return false;
    var rid = (marine.getAttribute("data-regatta-id") || "").trim();
    if (rid !== CAPE_CLASSIC_ID) return false;
    var page = marine.closest(".regatta-page") || document.querySelector(".regatta-page");
    var header = page && page.querySelector(":scope > .regatta-header-wrap");
    if (!header) return false;
    injectCss();
    var el = document.createElement("section");
    el.id = ROOT_ID;
    el.className = "card ssa-regatta-mp-wx";
    el.setAttribute("aria-label", "Weather");
    el.innerHTML =
      '<div class="ssa-regatta-mp-wx-bar">' +
      '<span class="ssa-regatta-mp-wx-title">Weather</span>' +
      '<span class="ssa-regatta-mp-wx-stamp" data-ssa-mp-wx-stamp>—</span>' +
      "</div>" +
      '<div class="ssa-regatta-mp-wx-grid" data-ssa-mp-wx-grid>' +
      card("Wind", "…", "") +
      card("Gust", "…", "") +
      card("Temp", "…", "") +
      card("Waves", "…", "") +
      card("Period", "…", "") +
      card("Wave dir", "…", "") +
      "</div>";
    marine.parentNode.insertBefore(el, marine);
    return true;
  }

  function paint(data) {
    var grid = document.querySelector("[data-ssa-mp-wx-grid]");
    var stamp = document.querySelector("[data-ssa-mp-wx-stamp]");
    if (!grid) return;
    var windKt = data.wind_kt;
    var gustKt = data.gust_kt;
    var tempC = data.temp_c;
    var wh = data.waves_m;
    var wp = data.period_s;
    var wd = data.wave_dir;
    var wdir = data.wind_dir;
    var html = "";
    html += card("Wind", fmt(windKt, 1) + (wdir != null ? " " + dirL(wdir) : "") + ' <span class="u">kt</span>', windBand(windKt));
    html += card("Gust", fmt(gustKt, 1) + ' <span class="u">kt</span>', windBand(gustKt));
    html += card("Temp", fmt(tempC, 1) + ' <span class="u">°C</span>', tempBand(tempC));
    html += card("Waves", fmt(wh, 1) + ' <span class="u">m</span>', waveBand(wh, wp));
    html += card("Period", fmt(wp, 1) + ' <span class="u">s</span>', periodBand(wh, wp));
    html += card("Wave dir", wd != null ? dirL(wd) + " (" + Math.round(wd) + "°)" : "—", waveBand(wh, wp));
    grid.innerHTML = html;
    if (stamp) stamp.textContent = "Table Bay · " + fmtStamp(Date.now());
  }

  var loading = false;
  async function load() {
    if (loading) return;
    loading = true;
    try {
      var res = await fetch("/api/live-wx/table-bay?_=" + Date.now(), {
        cache: "no-store",
        credentials: "same-origin"
      });
      if (!res.ok) throw new Error("wx " + res.status);
      var data = await res.json();
      if (!data || data.ok === false) throw new Error((data && data.err) || "wx fail");
      paint(data);
    } catch (err) {
      try {
        console.warn(err);
      } catch (e) {}
    } finally {
      loading = false;
    }
  }

  function boot() {
    if (!mount()) return;
    load();
    setInterval(function () {
      if (!document.hidden) load();
    }, 15000);
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) load();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
  window.__ssaRegattaMpWx = JS_VER;
})();
