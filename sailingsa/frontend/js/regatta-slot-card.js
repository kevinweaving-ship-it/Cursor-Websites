/* Generic weather station card for every catalog station, now and later.
   Bind with data-weather-station="{slug}" or data-weather-club="{CODE}"
   (optional data-weather-role="venue|nearby|regional"). Never average stations.
   Now  = latest reading wind_kt
   Avg  = mean of last hour (wind_avg_kt else wind_kt)
   High = max last-hour gust if any gusts exist, else max of that hour's avgs
   Arrow = latest wind_dir_deg. Petals = last-hour direction mix.
   Graph = stored history, last hour in view, swipe older.
   Adding a station is a catalog row + ingest, not a new card. */
(function () {
  var CSS_ID = "ssa-regatta-slot-card-css";
  var ROOT_ID = "ssa-regatta-slot-card";
  var CAPE_CLASSIC_ID = "2026-09-13-zvyc-cape-classic";
  var JS_VER = "20260917wxg1";
  var HOUR_MS = 3600000;
  var WA_FEED = "/js/event-whatsapp-live.json";
  var WA_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#25D366" d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.435 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>';
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
      ".ssa-regatta-slot-card{position:relative;display:flex;width:100%;order:2;align-self:start;margin:10px 0 0;padding:0;box-sizing:border-box;height:122px!important;min-height:122px!important;max-height:122px!important;flex:0 0 122px!important;background:#fff;border:1.5px solid #1a2750;border-radius:8px;box-shadow:0 1px 3px rgba(0,31,63,.08);overflow:hidden;}",
      ".regatta-page:has(.mm-lipton-reels--expanded) .ssa-regatta-slot-card{height:122px!important;min-height:122px!important;max-height:122px!important;flex:0 0 122px!important;align-self:start!important;}",
      ".ssa-regatta-slot-card .wx-wp-top{display:flex;align-items:stretch;flex:1;height:100%;width:100%;padding:0 6px 0 0;gap:4px;box-sizing:border-box;}",
      ".ssa-regatta-slot-card .wx-wp-comp{flex:0 0 122px;width:122px!important;height:122px!important;max-width:122px;max-height:122px;aspect-ratio:1/1;overflow:hidden;}",
      ".ssa-regatta-slot-card .wx-dial{display:block;width:100%;height:100%;overflow:visible;}",
      ".ssa-regatta-slot-card .wx-spark{flex:1 1 0;min-width:48px;height:100%;display:flex;flex-direction:column;padding:6px 2px 4px;box-sizing:border-box;min-height:0;}",
      ".ssa-regatta-slot-card .wx-spark-row{flex:1 1 auto;min-height:0;display:flex;align-items:stretch;gap:3px;}",
      ".ssa-regatta-slot-card .wx-scale{flex:0 0 16px;display:flex;flex-direction:column;justify-content:space-between;align-items:flex-end;padding:1px 0;box-sizing:border-box;}",
      ".ssa-regatta-slot-card .wx-scale span{font:700 9px/1 Arial,Helvetica,sans-serif;color:#64748b;}",
      ".ssa-regatta-slot-card.card,.ssa-wx-card.card{padding:0!important;}",
      ".ssa-regatta-slot-card .wx-plot-clip{flex:1 1 auto;min-width:0!important;height:100%;overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;touch-action:pan-x;scrollbar-width:none;}",
      ".ssa-regatta-slot-card .wx-plot-clip::-webkit-scrollbar{display:none;}",
      ".ssa-regatta-slot-card .wx-plot{height:100%!important;display:block;min-width:100%;max-width:none!important;flex:0 0 auto;}",
      ".ssa-regatta-slot-card .wx-spark-x{flex:0 0 auto;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:2px 0 0 19px;gap:4px;box-sizing:border-box;}",
      ".ssa-regatta-slot-card .wx-spark-x span{font:700 9px/1 Arial,Helvetica,sans-serif;color:#64748b;white-space:nowrap;}",
      ".ssa-regatta-slot-card .wx-x-left{justify-self:start;}",
      ".ssa-regatta-slot-card .wx-x-mid{justify-self:center;text-align:center;}",
      ".ssa-regatta-slot-card .wx-x-right{justify-self:end;}",
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
      ".ssa-regatta-slot-card .wx-il{color:#334155;letter-spacing:0;text-transform:none;}",
      ".ssa-regatta-slot-card .wx-iv{color:#1a2750;text-align:right;}",
      ".ssa-regatta-slot-card .wx-iv small{margin-left:4px;color:inherit;}",
      ".ssa-regatta-slot-card .wx-wa-btn{position:absolute;top:0;left:0;z-index:6;width:44px;height:44px;margin:0;border:0;background:transparent;cursor:pointer;display:flex;align-items:flex-start;justify-content:flex-start;padding:4px 0 0 4px;box-sizing:border-box;-webkit-tap-highlight-color:transparent;}",
      ".ssa-regatta-slot-card .wx-wa-btn svg{width:14px;height:14px;display:block;filter:drop-shadow(0 1px 1px rgba(0,0,0,.28));}",
      ".ssa-regatta-slot-card .wx-wa-layer{display:none;position:absolute;top:0;right:0;bottom:0;left:44px;z-index:5;background:#ece5dd;overflow:auto;-webkit-overflow-scrolling:touch;padding:6px 8px;box-sizing:border-box;}",
      ".ssa-regatta-slot-card.ssa-wa-open .wx-wa-layer{display:block;}",
      ".ssa-regatta-slot-card.ssa-wa-off .wx-wa-btn,.ssa-regatta-slot-card.ssa-wa-off .wx-wa-layer{display:none!important;}",
      ".ssa-regatta-slot-card .wx-wa-row{display:flex;margin:0 0 4px;}",
      ".ssa-regatta-slot-card .wx-wa-row.is-out{justify-content:flex-end;}",
      ".ssa-regatta-slot-card .wx-wa-b{max-width:92%;border-radius:10px;padding:5px 7px 3px;font:600 11px/1.25 -apple-system,BlinkMacSystemFont,Arial,sans-serif;box-shadow:0 1px 0 rgba(0,0,0,.08);}",
      ".ssa-regatta-slot-card .wx-wa-row.is-in .wx-wa-b{background:#fff;color:#111;border-top-left-radius:3px;}",
      ".ssa-regatta-slot-card .wx-wa-row.is-out .wx-wa-b{background:#d9fdd3;color:#111;border-top-right-radius:3px;}",
      ".ssa-regatta-slot-card .wx-wa-who{display:block;font:700 10px/1.2 Arial,sans-serif;color:#075e54;margin:0 0 2px;}",
      ".ssa-regatta-slot-card .wx-wa-text{white-space:pre-wrap;word-break:break-word;}",
      ".ssa-regatta-slot-card .wx-wa-meta{display:block;text-align:right;font:500 9px/1 Arial,sans-serif;color:#667781;margin-top:2px;}",
      ".ssa-regatta-slot-card .wx-wa-empty{font:600 12px/1.3 Arial,sans-serif;color:#54656f;padding:18px 8px;}",
      ".ssa-regatta-slot-card .wx-wa-voice{display:flex;align-items:center;gap:5px;min-width:108px;}",
      ".ssa-regatta-slot-card .wx-wa-play{flex:0 0 20px;height:20px;border-radius:50%;background:#00a884;color:#fff;font:700 9px/20px Arial,sans-serif;text-align:center;}",
      ".ssa-regatta-slot-card .wx-wa-wave{flex:1 1 auto;height:14px;border-radius:2px;background:repeating-linear-gradient(90deg,#8696a0 0 1px,transparent 1px 3px);}",
      ".ssa-regatta-slot-card .wx-wa-dur{flex:0 0 auto;font:700 10px/1 Arial,sans-serif;color:#54656f;}",
      ".ssa-wa-gate{display:none;position:fixed;inset:0;z-index:4000;background:rgba(0,0,0,.55);align-items:center;justify-content:center;padding:20px;box-sizing:border-box;}",
      ".ssa-wa-gate.is-open{display:flex;}",
      ".ssa-wa-gate-card{background:#fff;border:1.5px solid #1a2750;border-radius:8px;padding:16px 18px;max-width:300px;width:100%;box-shadow:0 8px 28px rgba(0,0,0,.28);box-sizing:border-box;}",
      ".ssa-wa-gate-card p{margin:0 0 14px;font:600 14px/1.35 Arial,Helvetica,sans-serif;color:#1a2750;}",
      ".ssa-wa-gate-actions{display:flex;flex-direction:column;align-items:center;gap:12px;}",
      ".ssa-wa-gate-auth{display:inline-flex;align-items:center;justify-content:center;gap:6px;height:32px;}",
      ".ssa-wa-gate-actions a.ssa-wa-gate-in,.ssa-wa-gate-actions a.ssa-wa-gate-up{display:inline-flex;align-items:center;justify-content:center;gap:5px;box-sizing:border-box;border-style:solid;border-width:3px;border-radius:10px;height:32px;min-height:32px;max-height:32px;line-height:32px;padding:0 10px;font:700 13px/32px inherit;text-decoration:none;flex-shrink:0;box-shadow:0 1px 2px rgba(15,23,42,.18);-webkit-tap-highlight-color:transparent;}",
      ".ssa-wa-gate-actions a.ssa-wa-gate-in{min-width:88px;background:#fff;color:#001f3f;border-color:#f1f5f9;}",
      ".ssa-wa-gate-actions a.ssa-wa-gate-up{min-width:94px;background:#eab308;color:#000;border-color:#eab308;}",
      ".ssa-wa-gate-actions a img{display:block;width:16px;height:16px;flex-shrink:0;object-fit:contain;background:none;border:0;padding:0;margin:0;}",
      ".ssa-wa-gate-actions a.ssa-wa-gate-in img{filter:invert(8%) sepia(92%) saturate(2500%) hue-rotate(185deg) brightness(92%) contrast(105%);}",
      ".ssa-wa-gate-actions a.ssa-wa-gate-up img{filter:brightness(0) saturate(100%);}",
      ".ssa-wa-gate-actions a span{display:inline-block;line-height:32px;font-weight:700;font-size:13px;}",
      ".ssa-wa-gate-auth .ssa-wa-gate-header-btn{width:auto;min-width:0;flex:0 0 auto;}",
      ".ssa-wa-gate-actions button[data-wa-gate-close]{display:flex;align-items:center;justify-content:center;min-height:44px;width:100%;padding:10px 12px;border-radius:6px;font:700 14px/1.2 Arial,Helvetica,sans-serif;background:#fff;color:#1a2750;border:1px solid #1a2750;cursor:pointer;box-sizing:border-box;}",
      "@media screen and (orientation:portrait) and (max-width:767px){",
      ".ssa-regatta-slot-card{margin-top:10px;}",
      ".ssa-regatta-slot-card .wx-il,.ssa-regatta-slot-card .wx-iv,.ssa-regatta-slot-card .wx-iv small{font-size:17px;}",
      "}"
    ].join("");
  }

  var sparkState = { stickNow: true, scrollLeft: 0 };

  function n1(x) {
    return x == null || isNaN(x) ? "—" : String(Math.round(Number(x) * 10) / 10);
  }
  function parseMs(t) {
    if (t == null || t === "") return NaN;
    if (typeof t === "number" && isFinite(t)) return t < 1e12 ? t * 1000 : t;
    var ms = Date.parse(String(t));
    return isNaN(ms) ? NaN : ms;
  }
  function fmtHm(ms) {
    if (ms == null || isNaN(ms)) return "";
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
  function mean(arr) {
    if (!arr || !arr.length) return null;
    var s = 0;
    var i;
    for (i = 0; i < arr.length; i += 1) s += arr[i];
    return s / arr.length;
  }
  function pickClubStation(payload, role) {
    var list = (payload && payload.stations) || [];
    var want = String(role || "venue").toLowerCase();
    var venue = [];
    var i;
    var row;
    for (i = 0; i < list.length; i += 1) {
      row = list[i];
      if (!row || !row.station_slug) continue;
      if (String(row.role || "").toLowerCase() === want) venue.push(row);
    }
    for (i = 0; i < venue.length; i += 1) {
      if (venue[i].usable_for_current) return venue[i].station_slug;
    }
    if (venue[0]) return venue[0].station_slug;
    for (i = 0; i < list.length; i += 1) {
      if (list[i] && list[i].usable_for_current && list[i].station_slug) return list[i].station_slug;
    }
    return list[0] && list[0].station_slug ? list[0].station_slug : "";
  }
  async function resolveSlug(slot) {
    var slug = String((slot && slot.getAttribute("data-weather-station")) || "").trim();
    if (slug) return slug;
    var club = String((slot && slot.getAttribute("data-weather-club")) || "").trim().toUpperCase();
    if (!club) return "";
    var role = String((slot && slot.getAttribute("data-weather-role")) || "venue").trim();
    var res = await fetch("/api/weather/clubs/" + encodeURIComponent(club) + "/stations?_=" + Date.now(), {
      cache: "no-store",
      credentials: "same-origin"
    });
    if (!res.ok) throw new Error("club wx " + res.status);
    var body = await res.json();
    if (!body || body.ok === false) throw new Error((body && body.err) || "club wx fail");
    return pickClubStation(body, role);
  }
  function viewFromReadings(readings) {
    var pts = (readings || []).slice().sort(function (a, b) {
      return parseMs(a.observed_at) - parseMs(b.observed_at);
    });
    var last = pts.length ? pts[pts.length - 1] : {};
    var nowMs = parseMs(last.observed_at);
    if (isNaN(nowMs)) nowMs = Date.now();
    var hour = [];
    var avgs = [];
    var highs = [];
    var wds = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    var nDir = 0;
    var i;
    var r;
    var ms;
    var avg;
    var gust;
    var di;
    for (i = 0; i < pts.length; i += 1) {
      r = pts[i];
      ms = parseMs(r.observed_at);
      avg = r.wind_avg_kt != null ? r.wind_avg_kt : r.wind_kt;
      gust = r.wind_gust_kt;
      hour.push({ t: r.observed_at, avg_kt: avg, high_kt: gust != null && !isNaN(gust) ? Number(gust) : null });
      if (!isNaN(ms) && nowMs - ms <= HOUR_MS) {
        if (avg != null && !isNaN(avg)) avgs.push(Number(avg));
        if (gust != null && !isNaN(gust)) highs.push(Number(gust));
        di = dirIdx(r.wind_dir_deg != null ? r.wind_dir_deg : r.wind_dir_avg_deg);
        if (di != null) {
          wds[di] += 1;
          nDir += 1;
        }
      }
    }
    var wdsPct = nDir ? wds.map(function (c) { return Math.round((100 * c) / nDir); }) : wds;
    var high = highs.length ? Math.max.apply(null, highs) : (avgs.length ? Math.max.apply(null, avgs) : null);
    var nowVal = last.wind_kt != null ? last.wind_kt : last.wind_avg_kt;
    var deg = last.wind_dir_deg != null ? last.wind_dir_deg : last.wind_dir_avg_deg;
    var diLast = dirIdx(deg);
    return {
      ok: true,
      slug: last.station_slug || "",
      wind_kt: nowVal,
      avg_kt: mean(avgs),
      high_kt: high,
      wind_dir: deg,
      wind_dir_name: diLast != null ? PTS[diLast] : "",
      wds: wdsPct,
      history: pts,
      hour: hour,
      interval: 40000
    };
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

  function sparkPoints(data) {
    var pts = [];
    var seen = {};
    function add(t, avg, high) {
      var ms = parseMs(t);
      if (isNaN(ms) || avg == null || isNaN(avg)) return;
      var key = String(ms);
      if (seen[key]) return;
      seen[key] = 1;
      pts.push({
        t: t,
        ms: ms,
        avg_kt: Number(avg),
        high_kt: high != null && !isNaN(high) ? Number(high) : null
      });
    }
    var hist = data && data.history;
    var i;
    if (Array.isArray(hist)) {
      for (i = 0; i < hist.length; i += 1) {
        var r = hist[i];
        if (!r) continue;
        var avg = r.wind_avg_kt != null ? r.wind_avg_kt : r.wind_kt;
        add(r.observed_at, avg, r.wind_gust_kt);
      }
    }
    var hour = data && data.hour;
    if (Array.isArray(hour)) {
      for (i = 0; i < hour.length; i += 1) {
        var p = hour[i];
        if (!p) continue;
        add(p.t, p.avg_kt, p.high_kt);
      }
    }
    pts.sort(function (a, b) { return a.ms - b.ms; });
    return pts;
  }

  function drawSpark(data) {
    var pts = sparkPoints(data);
    var html = '<div class="wx-spark" aria-label="Wind last hour, swipe right for older">';
    if (pts.length < 2) {
      return html + "</div>";
    }
    var lastMs = pts[pts.length - 1].ms;
    var firstMs = pts[0].ms;
    var t0 = (lastMs - firstMs) < HOUR_MS ? lastMs - HOUR_MS : firstMs;
    var hours = Math.max(1, (lastMs - t0) / HOUR_MS);
    var W = 100 * hours;
    var H = 100;
    var i;
    var maxKn = 10;
    for (i = 0; i < pts.length; i += 1) {
      if (pts[i].avg_kt > maxKn) maxKn = pts[i].avg_kt;
      if (pts[i].high_kt != null && pts[i].high_kt > maxKn) maxKn = pts[i].high_kt;
    }
    maxKn = Math.max(10, Math.ceil(maxKn / 5) * 5);
    var ticks = [];
    var step = maxKn <= 20 ? 5 : 10;
    for (i = maxKn; i >= 0; i -= step) ticks.push(i);
    function x(ms) { return 100 * (ms - t0) / HOUR_MS; }
    function y(kn) { return H * (1 - Math.max(0, Math.min(maxKn, Number(kn))) / maxKn); }
    var svg = '<svg class="wx-plot" data-hours="' + hours.toFixed(4) + '" data-t0="' + t0 + '" data-last-ms="' + lastMs + '" viewBox="0 0 ' + W + " " + H + '" height="100%" preserveAspectRatio="none" aria-hidden="true">';
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
    var hourMs = Math.ceil(t0 / HOUR_MS) * HOUR_MS;
    for (; hourMs < lastMs; hourMs += HOUR_MS) {
      var hx = x(hourMs);
      if (hx < 0 || hx > W) continue;
      svg += '<line x1="' + hx.toFixed(1) + '" y1="0" x2="' + hx.toFixed(1) + '" y2="' + H + '" stroke="#fff" stroke-width="0.7" opacity=".7" vector-effect="non-scaling-stroke"/>';
    }
    var highD = "";
    var avgD = "";
    var hiCount = 0;
    for (i = 0; i < pts.length; i += 1) {
      var xi = x(pts[i].ms).toFixed(1);
      avgD += (i ? "L" : "M") + xi + " " + y(pts[i].avg_kt).toFixed(1);
      if (pts[i].high_kt != null) {
        highD += (hiCount ? "L" : "M") + xi + " " + y(pts[i].high_kt).toFixed(1);
        hiCount += 1;
      }
    }
    var last = pts[pts.length - 1];
    if (hiCount >= 2) {
      var lastHi = null;
      for (i = pts.length - 1; i >= 0; i -= 1) {
        if (pts[i].high_kt != null) { lastHi = pts[i]; break; }
      }
      if (lastHi) {
        svg += '<path d="' + highD + "L" + x(lastHi.ms).toFixed(1) + " " + H + "L" + x(pts[0].ms).toFixed(1) + " " + H + 'Z" fill="#1a2750" opacity=".12"/>';
        svg += '<path d="' + highD + '" fill="none" stroke="#64748b" stroke-width="1.4" stroke-dasharray="3 2" vector-effect="non-scaling-stroke"/>';
      }
    }
    svg += '<path d="' + avgD + '" fill="none" stroke="#1a2750" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>';
    svg += '<circle cx="' + x(last.ms).toFixed(1) + '" cy="' + y(last.avg_kt).toFixed(1) + '" r="1.8" fill="' + bandCol(last.avg_kt) + '" vector-effect="non-scaling-stroke"/>';
    svg += "</svg>";
    var scale = '<div class="wx-scale">' + ticks.map(function (t) { return "<span>" + t + "</span>"; }).join("") + "</div>";
    html += '<div class="wx-spark-row">' + scale + '<div class="wx-plot-clip">' + svg + "</div></div>";
    html += '<div class="wx-spark-x"><span class="wx-x-left">Last Hour</span><span class="wx-x-mid">' + fmtHm(lastMs) + '</span><span class="wx-x-right"></span></div>';
    return html + "</div>";
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function waClock(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    var h = d.getHours();
    var m = d.getMinutes();
    return (h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m;
  }

  function fmtDur(sec) {
    var n = Number(sec);
    if (!n || n < 0 || isNaN(n)) return "0:00";
    var m = Math.floor(n / 60);
    var s = Math.floor(n % 60);
    return m + ":" + (s < 10 ? "0" : "") + s;
  }

  function waBubble(m) {
    var out = !!(m && m.from_me);
    var kind = String((m && m.kind) || "text");
    var body = String((m && m.body) || "");
    var cap = String((m && m.caption) || "");
    var inner = "";
    if (!out && m && m.sender_name) {
      inner += '<span class="wx-wa-who">' + esc(m.sender_name) + "</span>";
    }
    if (kind === "voice" || kind === "audio") {
      inner += '<span class="wx-wa-voice"><span class="wx-wa-play" aria-hidden="true">▶</span><span class="wx-wa-wave"></span><span class="wx-wa-dur">' + esc(fmtDur(m.duration_sec)) + "</span></span>";
    } else if (kind === "photo") {
      inner += '<span class="wx-wa-text">' + esc(cap || "Photo") + "</span>";
    } else if (kind === "video") {
      inner += '<span class="wx-wa-text">' + esc(cap || "Video") + "</span>";
    } else {
      inner += '<span class="wx-wa-text">' + esc(body || cap || "") + "</span>";
    }
    inner += '<span class="wx-wa-meta">' + esc(waClock(m && m.occurred_at)) + "</span>";
    return '<div class="wx-wa-row ' + (out ? "is-out" : "is-in") + '"><div class="wx-wa-b">' + inner + "</div></div>";
  }

  function paintWa(slot, data) {
    var layer = slot.querySelector(".wx-wa-layer");
    if (!layer) return;
    var msgs = (data && data.messages) || [];
    var html = "";
    var i;
    for (i = 0; i < msgs.length; i += 1) {
      html += waBubble(msgs[i]);
    }
    layer.innerHTML = html || '<div class="wx-wa-empty">No group messages yet.</div>';
    layer.scrollTop = layer.scrollHeight;
  }

  function loadWa(slot) {
    fetch("/api/regatta/" + encodeURIComponent(CAPE_CLASSIC_ID) + "/event-whatsapp?_=" + Date.now(), {
      cache: "no-store",
      credentials: "same-origin"
    })
      .then(function (res) { return res.ok ? res.json() : Promise.reject(res.status); })
      .then(function (data) { paintWa(slot, data); })
      .catch(function () {
        var layer = slot.querySelector(".wx-wa-layer");
        if (layer) layer.innerHTML = '<div class="wx-wa-empty">WhatsApp feed unavailable.</div>';
      });
  }

  function hideWaGate() {
    var el = document.getElementById("ssaWaGate");
    if (el) el.classList.remove("is-open");
  }

  var WA_GATE_MSG = "You must be signed up and logged in to see WhatsApp messages.";

  function cloneHeaderAuthButtons(authWrap, ret) {
    var up = document.getElementById("authSignUpBtn");
    var inn = document.getElementById("authSignInBtn");
    if (!up || !inn || !authWrap) return false;
    function cloneOne(src, kind) {
      var b = src.cloneNode(true);
      b.removeAttribute("id");
      b.classList.add("ssa-wa-gate-header-btn");
      b.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        hideWaGate();
        var fn = kind === "up" ? window.sailingHandleHeaderSignUp : window.sailingHandleHeaderSignIn;
        if (typeof fn === "function") {
          try { fn.call(src, e); } catch (err) {}
          return;
        }
        window.location.href = kind === "up"
          ? "/signup.html?signup=1&returnTo=" + ret
          : "/login.html?returnTo=" + ret;
      });
      return b;
    }
    authWrap.appendChild(cloneOne(up, "up"));
    authWrap.appendChild(cloneOne(inn, "in"));
    return true;
  }

  function showWaGate(msg) {
    msg = msg || WA_GATE_MSG;
    var old = document.getElementById("ssaWaGate");
    if (old && old.parentNode) old.parentNode.removeChild(old);
    var ret = encodeURIComponent(String(location.href || "/"));
    var el = document.createElement("div");
    el.id = "ssaWaGate";
    el.className = "ssa-wa-gate";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-modal", "true");
    el.setAttribute("aria-label", "Login required");
    el.innerHTML =
      '<div class="ssa-wa-gate-card">' +
        "<p></p>" +
        '<div class="ssa-wa-gate-actions">' +
          '<div class="ssa-wa-gate-auth"></div>' +
          '<button type="button" data-wa-gate-close="1">Close</button>' +
        "</div>" +
      "</div>";
    var auth = el.querySelector(".ssa-wa-gate-auth");
    if (!cloneHeaderAuthButtons(auth, ret)) {
      auth.innerHTML =
        '<a class="ssa-wa-gate-up" href="/signup.html?signup=1&amp;returnTo=' + ret + '">' +
          '<img src="/icons/assets/iconoir/regular/edit.svg" alt="" width="16" height="16">' +
          "<span>Sign Up</span></a>" +
        '<a class="ssa-wa-gate-in" href="/login.html?returnTo=' + ret + '">' +
          '<img src="/icons/assets/phosphor/bold/user-circle-gear-bold.svg" alt="" width="16" height="16">' +
          "<span>Login</span></a>";
    }
    document.body.appendChild(el);
    el.addEventListener("click", function (e) {
      if (e.target === el) hideWaGate();
    });
    var close = el.querySelector("[data-wa-gate-close]");
    if (close) close.addEventListener("click", hideWaGate);
    var p = el.querySelector(".ssa-wa-gate-card p");
    if (p) p.textContent = msg;
    el.classList.add("is-open");
  }
  window.ssaShowLoginGate = showWaGate;

  function sessionIsRegistered() {
    return fetch("/auth/session?path=" + encodeURIComponent(location.pathname || "/"), {
      credentials: "include",
      cache: "no-store"
    })
      .then(function (res) { return res.ok ? res.json() : { valid: false }; })
      .then(function (s) { return !!(s && s.valid === true); })
      .catch(function () { return false; });
  }

  function bindWa(slot) {
    var btn = slot.querySelector(".wx-wa-btn");
    if (!btn || btn.getAttribute("data-bound") === "1") return;
    btn.setAttribute("data-bound", "1");
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      if (waShow === false) return;
      if (slot.classList.contains("ssa-wa-open")) {
        slot.classList.remove("ssa-wa-open");
        btn.setAttribute("aria-pressed", "false");
        return;
      }
      sessionIsRegistered().then(function (ok) {
        if (!ok) {
          showWaGate();
          return;
        }
        slot.classList.add("ssa-wa-open");
        btn.setAttribute("aria-pressed", "true");
        loadWa(slot);
      });
    });
  }

  function rememberSparkScroll(slot) {
    var clip = slot && slot.querySelector(".wx-plot-clip");
    if (!clip) return;
    sparkState.scrollLeft = clip.scrollLeft;
    sparkState.stickNow = (clip.scrollWidth - clip.clientWidth - clip.scrollLeft) < 12;
  }

  function sizeSparkPlot(slot) {
    var clip = slot && slot.querySelector(".wx-plot-clip");
    var plot = slot && slot.querySelector(".wx-plot");
    if (!clip || !plot) return;
    var hours = Number(plot.getAttribute("data-hours") || "1");
    if (!isFinite(hours) || hours < 1) hours = 1;
    var w = clip.clientWidth || 0;
    if (w <= 0) return;
    // Visible window is always one hour, sized to this container (MP, tablet, desktop).
    plot.style.maxWidth = "none";
    plot.style.width = Math.round(w * hours) + "px";
    plot.style.height = "100%";
    plot.removeAttribute("width");
    updateSparkTime(slot);
  }

  function updateSparkTime(slot) {
    var clip = slot && slot.querySelector(".wx-plot-clip");
    var plot = slot && slot.querySelector(".wx-plot");
    var mid = slot && slot.querySelector(".wx-x-mid");
    if (!clip || !plot || !mid) return;
    var hours = Number(plot.getAttribute("data-hours") || "1");
    var t0 = Number(plot.getAttribute("data-t0") || "0");
    var lastMs = Number(plot.getAttribute("data-last-ms") || "0");
    if (!isFinite(hours) || hours < 1) hours = 1;
    var sw = clip.scrollWidth || 0;
    var cw = clip.clientWidth || 0;
    var ms = lastMs;
    if (sw > 0 && cw > 0 && t0) {
      var right = (clip.scrollLeft + cw) / sw;
      if (right > 1) right = 1;
      if (right < 0) right = 0;
      ms = t0 + right * hours * HOUR_MS;
      if (lastMs && ms > lastMs) ms = lastMs;
    }
    mid.textContent = fmtHm(ms);
  }

  function bindSpark(slot) {
    var clip = slot && slot.querySelector(".wx-plot-clip");
    if (!clip) return;
    sizeSparkPlot(slot);
    if (sparkState.stickNow) {
      clip.scrollLeft = clip.scrollWidth;
    } else {
      clip.scrollLeft = sparkState.scrollLeft || 0;
    }
    updateSparkTime(slot);
    clip.addEventListener("scroll", function () {
      sparkState.scrollLeft = clip.scrollLeft;
      sparkState.stickNow = (clip.scrollWidth - clip.clientWidth - clip.scrollLeft) < 12;
      updateSparkTime(slot);
    }, { passive: true });
    window.requestAnimationFrame(function () {
      sizeSparkPlot(slot);
      if (sparkState.stickNow) clip.scrollLeft = clip.scrollWidth;
      updateSparkTime(slot);
    });
  }

  function render(slot, data) {
    rememberSparkScroll(slot);
    var wnow = data.wind_kt;
    var wavg = data.avg_kt;
    var whigh = data.high_kt;
    var colN = bandCol(wnow);
    var colA = bandCol(wavg);
    var colH = bandCol(whigh);
    var withWa = slot.getAttribute("data-weather-wa") === "1";
    slot.innerHTML =
      '<div class="wx-wp-top">' +
        '<div class="wx-wp-comp">' + drawDial(data) + "</div>" +
        drawSpark(data) +
        '<div class="wx-info">' +
          '<div class="wx-ir"><span class="wx-il">Now</span><span class="wx-iv" style="color:' + colN + '">' + n1(wnow) + " <small>kn</small></span></div>" +
          '<div class="wx-ir"><span class="wx-il">Avg</span><span class="wx-iv" style="color:' + colA + '">' + n1(wavg) + " <small>kn</small></span></div>" +
          '<div class="wx-ir"><span class="wx-il">High</span><span class="wx-iv" style="color:' + colH + '">' + n1(whigh) + " <small>kn</small></span></div>" +
        "</div>" +
      "</div>" +
      (withWa
        ? '<button type="button" class="wx-wa-btn" aria-label="Cape Classic WhatsApp" aria-pressed="false">' + WA_ICON + "</button>" +
          '<div class="wx-wa-layer" aria-label="Cape Classic WhatsApp"></div>'
        : "");
    bindSpark(slot);
    if (withWa) {
      bindWa(slot);
      applyWaShow(slot);
      refreshWaShow(slot);
    }
  }

  function fitGauge(slot) {
    var comp = slot && slot.querySelector(".wx-wp-comp");
    if (!slot || !comp) return;
    slot.style.height = "122px";
    slot.style.minHeight = "122px";
    slot.style.maxHeight = "122px";
    comp.style.height = "122px";
    comp.style.width = "122px";
    comp.style.maxHeight = "122px";
    comp.style.maxWidth = "122px";
  }

  function syncToMarine(slot, marine) {
    if (!slot || !marine) return;
    slot.style.height = "122px";
    slot.style.minHeight = "122px";
    slot.style.maxHeight = "122px";
    var mt = getComputedStyle(marine).marginTop;
    if (mt) slot.style.marginTop = mt;
    fitGauge(slot);
  }

  var POLL_MS = 40000;
  var waShow = true;

  function applyWaShow(slot) {
    if (!slot) return;
    if (waShow === false) {
      slot.classList.add("ssa-wa-off");
      slot.classList.remove("ssa-wa-open");
    } else {
      slot.classList.remove("ssa-wa-off");
    }
  }

  function refreshWaShow(slot) {
    fetch(WA_FEED + "?_=" + Date.now(), { cache: "no-store", credentials: "same-origin" })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        if (data && data.show === false) waShow = false;
        else if (data && data.show === true) waShow = true;
        applyWaShow(slot);
      })
      .catch(function () {});
  }

  async function load(slot) {
    if (!slot || slot._wxLoading) return;
    slot._wxLoading = true;
    try {
      var slug = slot._wxSlug || (await resolveSlug(slot));
      if (!slug) throw new Error("no weather station");
      slot._wxSlug = slug;
      slot.setAttribute("data-weather-station", slug);
      var href =
        slug === "agromet-midmar"
          ? "/api/weather/agromet-midmar/history?hours=12&_=" + Date.now()
          : "/api/weather/stations/" + encodeURIComponent(slug) + "/history?hours=12&_=" + Date.now();
      var hres = await fetch(href, { cache: "no-store", credentials: "same-origin" });
      if (!hres.ok) throw new Error("wx history " + hres.status);
      var hist = await hres.json();
      if (!hist || hist.ok === false) throw new Error((hist && hist.err) || "wx history fail");
      var data = viewFromReadings(hist.readings || []);
      data.slug = slug;
      if (slot.classList.contains("ssa-wa-open")) {
        loadWa(slot);
      } else {
        render(slot, data);
        fitGauge(slot);
        sizeSparkPlot(slot);
      }
    } catch (err) {
      try { console.warn(err); } catch (e) {}
    } finally {
      slot._wxLoading = false;
    }
  }

  function startCard(el) {
    if (!el || el.getAttribute("data-wx-bound") === "1") return el;
    el.setAttribute("data-wx-bound", "1");
    injectCss();
    function tick() { if (!document.hidden) load(el); }
    load(el);
    setInterval(tick, POLL_MS);
    document.addEventListener("visibilitychange", tick);
    window.addEventListener("resize", function () {
      fitGauge(el);
      sizeSparkPlot(el);
    });
    return el;
  }

  function mountCapeClassic() {
    if (document.getElementById(ROOT_ID)) return;
    var marine = document.getElementById("mmLiptonReels");
    if (!marine) return;
    if ((marine.getAttribute("data-regatta-id") || "").trim() !== CAPE_CLASSIC_ID) return;
    // Club page mounts its own weather slot (no WhatsApp overlay).
    if (marine.getAttribute("data-mm-club-page") === "1") return;
    var el = document.createElement("section");
    el.id = ROOT_ID;
    el.className = "card ssa-wx-card ssa-regatta-slot-card";
    el.setAttribute("data-weather-club", "ZVYC");
    el.setAttribute("data-weather-role", "venue");
    el.setAttribute("data-weather-wa", "1");
    el.setAttribute("aria-label", "Venue wind");
    marine.parentNode.insertBefore(el, marine);
    syncToMarine(el, marine);
    if (typeof MutationObserver === "function") {
      new MutationObserver(function () { fitGauge(el); }).observe(marine, {
        attributes: true,
        attributeFilter: ["class"]
      });
    }
    startCard(el);
  }

  function mountMarked() {
    var nodes = document.querySelectorAll("[data-weather-station], [data-weather-club]");
    var i;
    for (i = 0; i < nodes.length; i += 1) {
      nodes[i].classList.add("card", "ssa-wx-card", "ssa-regatta-slot-card");
      startCard(nodes[i]);
    }
  }

  function mount() {
    injectCss();
    mountCapeClassic();
    mountMarked();
  }

  window.ssaMountWeatherCard = function (el, opts) {
    opts = opts || {};
    if (!el) return null;
    if (opts.slug) el.setAttribute("data-weather-station", String(opts.slug));
    if (opts.club) el.setAttribute("data-weather-club", String(opts.club).toUpperCase());
    if (opts.role) el.setAttribute("data-weather-role", String(opts.role));
    el.classList.add("card", "ssa-wx-card", "ssa-regatta-slot-card");
    return startCard(el);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
  window.__ssaRegattaSlotCard = JS_VER;
  window.__ssaWeatherCard = JS_VER;
})();
