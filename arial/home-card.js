    (function () {
      var box = document.getElementById("home-sensors");
      if (!box || !((window.ARIAL_CONFIG || {}).homeCard || String((window.ARIAL_CONFIG || {}).siteId) === "voelklip")) return;
      var API = String((window.ARIAL_CONFIG || {}).apiBase || "/api/voelklip").replace(/\/$/, "");
      var cardTitle = String((window.ARIAL_CONFIG || {}).homeCardTitle || "").trim();
      var HOME_LABELS = (window.ARIAL_CONFIG || {}).homeLabels || {};
      function neatName(x) {
        if (HOME_LABELS[x.id]) return HOME_LABELS[x.id];
        var n = String(x.name || "").trim();
        n = n.replace(/^Smart Water Valve\b.*$/i, "Water meter");
        n = n.replace(/^Bing Heights\s+/i, "");
        n = n.replace(/\s+-\s+Noordhoek\s*$/i, "");
        n = n.replace(/\s+BV\d+\s*$/i, "");
        return n || x.name || x.id;
      }
      function switchCodes(status) {
        var keys = Object.keys(status || {});
        var named = keys.filter(function (k) { return /^switch(_\d+)?$/.test(k); });
        if (named.length) {
          return named.sort(function (a, b) {
            var na = a === "switch" ? 0 : Number(String(a).replace(/^switch_?/, "")) || 0;
            var nb = b === "switch" ? 0 : Number(String(b).replace(/^switch_?/, "")) || 0;
            return na - nb;
          });
        }
        if (Object.prototype.hasOwnProperty.call(status || {}, "1")) return ["1"];
        return [];
      }
      if (cardTitle) {
        var titleEl = box.querySelector(".section-title");
        if (titleEl) titleEl.textContent = cardTitle;
      }
      var below = document.querySelector(".arial-below");
      function sc(v, units, code, dflt) { var u = (units || {})[code] || {}; var s = Number(u.scale); if (!isFinite(s)) s = dflt || 0; return typeof v === "number" ? v / Math.pow(10, s) : null; }
      function tile(ic, v, l, cls) { return '<div class="hs-tile ' + (cls || "") + '"><span class="ic">' + ic + '</span><span class="v">' + v + '</span><span class="l">' + l + '</span></div>'; }
      function dur(since) { if (!since) return ""; var s = Math.max(0, Date.now() / 1000 - since), h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60); return h ? h + "h" + (m < 10 ? "0" : "") + m : m + "m"; }
      function n1(x) { return x == null ? "—" : (Math.round(x * 10) / 10).toString(); }
      function hm(sec) { if (!sec || sec < 60) return "0m"; var h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60); return h ? h + "h" + (m < 10 ? "0" : "") + m : m + "m"; }
      var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      function monLabel() { return MON[new Date(Date.now() + 7200000).getUTCMonth()]; }
      function prevMonLabel() { return MON[(new Date(Date.now() + 7200000).getUTCMonth() + 11) % 12]; }
      function litres(n) {
        if (n == null || !isFinite(Number(n))) return "\u2014";
        var L = Math.round(Number(n));
        if (L > 1000) return (L / 1000).toFixed(3) + " KL";
        return L.toLocaleString("fr-FR") + " L";
      }
      function waterAmt(n) {
        if (n == null || !isFinite(Number(n))) return "<b>\u2014</b>";
        return "<b>" + litres(n) + "</b>";
      }
      function waterLine(l) {
        var wu = l && l.waterUse;
        if (!wu || (wu.todayL == null && wu.monthL == null && wu.lastMonthL == null)) return "";
        function cell(n, lab) { return '<span class="hs-wcell">' + waterAmt(n) + "<i>" + lab + "</i></span>"; }
        return '<span class="hs-wuse">' + cell(wu.todayL, "today") + cell(wu.monthL, monLabel()) + cell(wu.lastMonthL, prevMonLabel()) + "</span>";
      }
      function kwhAmt(n) {
        if (n == null || !isFinite(Number(n))) return "<b>\u2014</b>";
        return "<b>" + Number(n).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " kWh</b>";
      }
      function eleLine(l) {
        var eu = l && l.eleUse;
        if (!eu || (eu.todayKwh == null && eu.monthKwh == null && eu.lastMonthKwh == null)) return "";
        function cell(n, lab) { return '<span class="hs-wcell">' + kwhAmt(n) + "<i>" + lab + "</i></span>"; }
        return '<span class="hs-wuse">' + cell(eu.todayKwh, "today") + cell(eu.monthKwh, monLabel()) + cell(eu.lastMonthKwh, prevMonLabel()) + "</span>";
      }
      function eleLive(e) {
        var st = (e && e.status) || {};
        var V = sc(st.cur_voltage != null ? st.cur_voltage : st["20"], e.units, "cur_voltage", 1);
        var A = sc(st.cur_current != null ? st.cur_current : st["18"], e.units, "cur_current", 3);
        var W = sc(st.cur_power != null ? st.cur_power : st["19"], e.units, "cur_power", 1);
        function f(v, d, u) { return "<span>" + (v == null || !isFinite(v) ? "\u2014" : v.toFixed(d)) + " " + u + "</span>"; }
        return '<span class="hs-elive">' + f(V, 1, "V") + f(A, 3, "A") + f(W, 1, "W") + "</span>";
      }
      var pend = {};   // "dev:code" -> {on, until}: tapped state shown instantly and held until the device confirms
      function pendOn(dev, code, on) { var k = dev + ":" + code, p = pend[k]; if (p && Date.now() < p.until) return p.on; return on; }
      var ICONS = {};   // device id -> local /assets/tuya/... path (from the resolver; never a CDN URL)
      function tico(id, cls) { var p = ICONS[id] || "/assets/tuya/fallback/device.svg"; return '<img class="tico ' + (cls || "") + '" src="' + p + '" alt="" loading="lazy" decoding="async">'; }
      var lastData = null, gangDev = null;
      function render(d) {
        lastData = d;
        ICONS = d.icons || {};
        Object.keys(pend).forEach(function (k) { if (Date.now() > pend[k].until) delete pend[k]; });
        (d.devices || []).forEach(function (x) { Object.keys(x.status || {}).forEach(function (c) { if (/^switch(_\d+)?$/.test(c) || c === "1") x.status[c] = pendOn(x.id, c, x.status[c]); }); });
        var devs = d.devices || [], wx = null, indoor = null, lock = null, plugs = [], lights = [], meters = [];
        devs.forEach(function (x) {
          if (x.category === "qxj") wx = x;
          else if (x.category === "wsdcg") indoor = x;
          else if (x.category === "jtmspro") lock = x;
          else if (x.eleUse || x.category === "cz") meters.push(x);
          else if ("cur_power" in x.status) plugs.push(x);
          else if (x.category === "kg" || x.category === "tdq" || x.category === "dlq" || x.category === "pc" || x.category === "sfkzq") lights.push(x);
        });
        var h = "";
        if (wx) {
          var s = wx.status, u = wx.units, off = wx.online ? "" : "off", raw = wx.raw || {};
          // Arc gauge (270deg) in the breaker-dial style: grey track, ok/warn/crit zones, value arc, needle, big number.
          function pol(cx, cy, r, a) { var t = (a - 90) * Math.PI / 180; return [cx + r * Math.cos(t), cy + r * Math.sin(t)]; }
          function arc(cx, cy, r, a0, a1) { var p0 = pol(cx, cy, r, a0), p1 = pol(cx, cy, r, a1); return "M" + p0[0].toFixed(1) + " " + p0[1].toFixed(1) + " A" + r + " " + r + " 0 " + (a1 - a0 > 180 ? 1 : 0) + " 1 " + p1[0].toFixed(1) + " " + p1[1].toFixed(1); }
          function gauge(val, min, max, zones, label, unit, extra, cls) {
            // zones: [[from,to,"ok|warn|crit"],...] in value units; angle span 225..495 (270deg, gap at bottom)
            var A0 = 225, SPAN = 270, cx = 50, cy = 52, r = 40;
            function ang(v) { var f = (Math.max(min, Math.min(max, v)) - min) / (max - min); return A0 + f * SPAN; }
            var g = '<svg class="wx-gauge" viewBox="0 0 100 92" aria-hidden="true">';
            g += '<path class="track" d="' + arc(cx, cy, r, A0, A0 + SPAN) + '"/>';
            (zones || []).forEach(function (z) { g += '<path class="zone zone-' + z[2] + '" d="' + arc(cx, cy, r, ang(z[0]), ang(z[1])) + '"/>'; });
            if (val != null) g += '<path class="arc" d="' + arc(cx, cy, r, A0, Math.max(A0 + 0.5, ang(val))) + '"/>';
            for (var i = 0; i <= 6; i += 1) { var aa = A0 + i * SPAN / 6, p0 = pol(cx, cy, r - 7, aa), p1 = pol(cx, cy, r - 3.5, aa); g += '<line class="tick" x1="' + p0[0].toFixed(1) + '" y1="' + p0[1].toFixed(1) + '" x2="' + p1[0].toFixed(1) + '" y2="' + p1[1].toFixed(1) + '"/>'; }
            if (extra && extra.prev != null) { var ap = ang(extra.prev), q0 = pol(cx, cy, r - 9, ap), q1 = pol(cx, cy, r + 4, ap); g += '<line class="prev" x1="' + q0[0].toFixed(1) + '" y1="' + q0[1].toFixed(1) + '" x2="' + q1[0].toFixed(1) + '" y2="' + q1[1].toFixed(1) + '"/>'; }
            if (extra && extra.mark != null) { var am = ang(extra.mark), m0 = pol(cx, cy, r - 9, am), m1 = pol(cx, cy, r + 4, am); g += '<line class="limit" x1="' + m0[0].toFixed(1) + '" y1="' + m0[1].toFixed(1) + '" x2="' + m1[0].toFixed(1) + '" y2="' + m1[1].toFixed(1) + '"/>'; }
            if (val != null) { var an = ang(val), n0 = pol(cx, cy, 6, an + 180), n1 = pol(cx, cy, r - 11, an); g += '<line class="needle" x1="' + n0[0].toFixed(1) + '" y1="' + n0[1].toFixed(1) + '" x2="' + n1[0].toFixed(1) + '" y2="' + n1[1].toFixed(1) + '"/><circle class="hub" cx="' + cx + '" cy="' + cy + '" r="3.2"/>'; }
            g += '<text class="gv" x="50" y="78" text-anchor="middle">' + (val == null ? "\u2014" : (Math.round(val * 10) / 10)) + '</text>';
            g += '<text class="gu" x="50" y="89" text-anchor="middle">' + unit + '</text></svg>';
            return '<div class="hs-tile wx-g ' + (cls || "") + '">' + g + '<span class="l">' + label + '</span></div>';
          }
          var KN = 1 / 1.852;   // station reports km/h; the site works in knots
          var wavg = sc(s.windspeed_avg, u, "windspeed_avg", 1), wgust = sc(s.windspeed_gust, u, "windspeed_gust", 1);
          if (wavg != null) wavg *= KN; if (wgust != null) wgust *= KN;
          var PTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
          var pt = "", deg = null;
          try { if (typeof raw.dp134 === "string") { var bts = atob(raw.dp134), letters = bts.slice(0, 5).replace(/[^NESW]/g, ""); if (PTS.indexOf(letters) !== -1) pt = letters; } } catch (e) {}
          if (pt) deg = PTS.indexOf(pt) * 22.5;
          // wind speed gauge 0-60 km/h: ok <20, warn 20-40, crit >40; red marker = gust
          // ================= WIND PANEL v2: banded gauge, direction sector compass, 24 h history + 7 day Windguru forecast timeline
          var wd = wx.wind || {}, KNc = KN, scW = function (v) { return v == null ? null : sc(v, u, "windspeed_gust", 1) * KNc; };
          var outAge = wx.outdoorLastTs ? (Date.now() / 1000 - wx.outdoorLastTs) : null, outOff = outAge != null && outAge > 360;
          var outLast = wx.outdoorLastTs ? new Date(wx.outdoorLastTs * 1000).toLocaleString("en-GB", { timeZone: "Africa/Johannesburg", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).replace(",", " \u00b7") : "";
          var BANDS = [[0, 10, "#12b028"], [10, 20, "#e67e00"], [20, 30, "#7c3aed"], [30, 50, "#DC143C"], [50, 60, "#7f0d1f"]];
          function bandCol(kn) { if (kn == null) return "#94a3b8"; for (var i = 0; i < BANDS.length; i += 1) if (kn < BANDS[i][1]) return BANDS[i][2]; return "#7f0d1f"; }
          var prevG = scW(wd.prevGust), trendG = wd.trendGust != null ? scW(wd.trendGust) : null, pTrend = wd.pressureTrend;
          var mx = wd.max24Gust ? { v: scW(wd.max24Gust.v), t: new Date(wd.max24Gust.t * 1000).toLocaleTimeString("en-GB", { timeZone: "Africa/Johannesburg", hour: "2-digit", minute: "2-digit" }) } : null;
          var trendTxt = outOff ? "no wind data \u2014 outside unit offline" : trendG == null ? "" : Math.abs(trendG) < 1 ? "\u2192 steady" : trendG > 0 ? "\u2197 rising +" + n1(trendG) : "\u2198 dropping " + n1(trendG);
          var trendCls = trendG == null ? "" : Math.abs(trendG) < 1 ? "" : trendG > 0 ? " up" : " down";
          var worse = (trendG != null && trendG >= 1) || (pTrend != null && pTrend <= -2), better = (trendG != null && trendG <= -1) || (pTrend != null && pTrend >= 2);
          var outlook = outOff ? (pTrend != null ? "pressure only" : "") : worse && !better ? "getting worse" : better && !worse ? "improving" : "no change";
          var outlookCls = worse && !better ? " bad" : better && !worse ? " good" : "";
          // --- speed gauge 0-60 kn with the site's bands; >50 flashes
          var zones = BANDS.map(function (b) { return [b[0], b[1], b[2]]; });
          function gaugeB(val) {
            var A0 = 225, SPAN = 270, cx = 50, cy = 52, r = 40, min = 0, max = 60;
            function ang(v) { return A0 + (Math.max(min, Math.min(max, v)) - min) / (max - min) * SPAN; }
            var g = '<svg class="wx-gauge" viewBox="0 0 100 92" aria-hidden="true"><path class="track" d="' + arc(cx, cy, r, A0, A0 + SPAN) + '"/>';
            zones.forEach(function (z) { g += '<path class="zone" style="stroke:' + z[2] + '" d="' + arc(cx, cy, r, ang(z[0]), ang(z[1])) + '"/>'; });
            if (val != null) g += '<path class="arc" style="stroke:' + bandCol(val) + '" d="' + arc(cx, cy, r, A0, Math.max(A0 + 0.5, ang(val))) + '"/>';
            for (var i = 0; i <= 6; i += 1) { var aa = A0 + i * SPAN / 6, p0 = pol(cx, cy, r - 7, aa), p1 = pol(cx, cy, r - 3.5, aa); g += '<line class="tick" x1="' + p0[0].toFixed(1) + '" y1="' + p0[1].toFixed(1) + '" x2="' + p1[0].toFixed(1) + '" y2="' + p1[1].toFixed(1) + '"/>'; }
            [0, 10, 20, 30, 40, 50, 60].forEach(function (v) { var p = pol(cx, cy, r - 13, ang(v)); g += '<text class="gt" x="' + p[0].toFixed(1) + '" y="' + (p[1] + 2.5).toFixed(1) + '" text-anchor="middle">' + v + '</text>'; });
            if (prevG != null) { var ap = ang(prevG), q0 = pol(cx, cy, r - 9, ap), q1 = pol(cx, cy, r + 4, ap); g += '<line class="prev" x1="' + q0[0].toFixed(1) + '" y1="' + q0[1].toFixed(1) + '" x2="' + q1[0].toFixed(1) + '" y2="' + q1[1].toFixed(1) + '"/>'; }
            if (wgust != null) { var am = ang(wgust), m0 = pol(cx, cy, r - 9, am), m1 = pol(cx, cy, r + 4, am); g += '<line class="limit" style="stroke:' + bandCol(wgust) + '" x1="' + m0[0].toFixed(1) + '" y1="' + m0[1].toFixed(1) + '" x2="' + m1[0].toFixed(1) + '" y2="' + m1[1].toFixed(1) + '"/>'; }
            if (val != null) { var an = ang(val), n0 = pol(cx, cy, 6, an + 180), n1p = pol(cx, cy, r - 11, an); g += '<line class="needle" x1="' + n0[0].toFixed(1) + '" y1="' + n0[1].toFixed(1) + '" x2="' + n1p[0].toFixed(1) + '" y2="' + n1p[1].toFixed(1) + '"/><circle class="hub" cx="' + cx + '" cy="' + cy + '" r="3.2"/>'; }
            g += '<text class="gv" style="fill:' + bandCol(val) + '" x="50" y="78" text-anchor="middle">' + (val == null ? "\u2014" : Math.round(val * 10) / 10) + '</text><text class="gu" x="50" y="89" text-anchor="middle">knots \u00b7 gust ' + n1(wgust) + '</text></svg>';
            return g;
          }
          // --- THE wind dial, as the Smart Life app draws it: fine grey tick ring with 4 cardinal marks, a light-blue arc on
          //     the ring covering the recent direction readings with a darker arrow head at the current direction, and the
          //     compass point in green in the middle. Text block beside it: Wind Speed (current) / GUST | AVG.
          var PTS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
          var dirLast = wd.dirLast != null ? wd.dirLast : null, recent = wd.dirRecent || [];
          var pt = dirLast != null ? PTS[dirLast] : "", deg = dirLast != null ? dirLast * 22.5 : null;
          var wcur = wd.curKn != null ? wd.curKn : (raw.dp131 != null ? (Number(raw.dp131) / 10) * KNc : null);
          var od = wx.outdoor || {}, outOff = od.online === false, odLast = od.lastTs ? new Date(od.lastTs * 1000).toLocaleTimeString("en-GB", { timeZone: "Africa/Johannesburg", hour: "2-digit", minute: "2-digit" }) : "";
          var col = outOff ? "#94a3b8" : bandCol(wcur != null ? wcur : wavg), colG = outOff ? "#94a3b8" : bandCol(wgust), prevCur = wd.prevCurKn != null ? wd.prevCurKn : null;
          var CX = 50, CY = 50, R = 44;
          var comp = '<svg class="wx-dial" viewBox="0 0 100 100" aria-hidden="true">';
          for (var k = 0; k < 72; k += 1) { var card = k % 18 === 0, q0 = pol(CX, CY, R - (card ? 7 : 4.5), k * 5), q1 = pol(CX, CY, R + (card ? 2 : 0), k * 5); comp += '<line class="' + (card ? "dt card" : "dt") + '" x1="' + q0[0].toFixed(1) + '" y1="' + q0[1].toFixed(1) + '" x2="' + q1[0].toFixed(1) + '" y2="' + q1[1].toFixed(1) + '"/>'; }
          if (dirLast != null) {
            // Band = one 22.5-degree mark per direction reported in the last ~8 minutes (16 reports): a steady wind is one
            // mark under the arrow, a shifting wind shows separate marks with gaps. Arrow = the most recent reading, on the
            // ring at the current direction, facing where the wind comes from. Arrow and band take the wind-speed band
            // colour (<=10 green, 10-20 orange, 20-30 purple, 30-50 red, >50 red flashing).
            var win = recent.slice(-16); if (!win.length || win[win.length - 1] !== dirLast) win.push(dirLast);
            var uniq = win.filter(function (v, i, arr) { return arr.indexOf(v) === i; });
            uniq.forEach(function (idx) { var a0 = idx * 22.5 - 11.25, a1 = idx * 22.5 + 11.25, p0 = pol(CX, CY, R - 2, a0), p1 = pol(CX, CY, R - 2, a1); comp += '<path class="darc' + (idx === dirLast ? "" : " prev") + '" style="stroke:' + col + '" d="M' + p0[0].toFixed(1) + ' ' + p0[1].toFixed(1) + ' A' + (R - 2) + ' ' + (R - 2) + ' 0 0 1 ' + p1[0].toFixed(1) + ' ' + p1[1].toFixed(1) + '"/>'; });
            // arrow sits on the ring at the direction the wind comes FROM and points inwards, i.e. the way the wind blows
            // across the site (SE wind: head at SE pointing towards the centre / NW)
            var hp = pol(CX, CY, R + 4, deg);
            comp += '<g transform="translate(' + hp[0].toFixed(1) + ' ' + hp[1].toFixed(1) + ') rotate(' + (deg + 180) + ')"><path class="dhead" style="fill:' + col + '" d="M0 -14L11 7L0 2.5L-11 7Z"/></g>';
          }
          comp += '<text class="dpt' + (outOff ? " off" : "") + '" x="50" y="50" text-anchor="middle" dominant-baseline="central">' + (pt || "\u2014") + '</text>';
          if (outOff) comp += '<g class="obatt" transform="translate(38 61) scale(1)" fill="none" stroke="#b45309" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 7h11a2 2 0 0 1 2 2v.5a.5 .5 0 0 0 .5 .5a.5 .5 0 0 1 .5 .5v3a.5 .5 0 0 1 -.5 .5a.5 .5 0 0 0 -.5 .5v.5a2 2 0 0 1 -2 2h-11a2 2 0 0 1 -2 -2v-6a2 2 0 0 1 2 -2" /> <path d="M7 10l0 4" /></g>';
          comp += '</svg>';
          // forecast for this hour (nearest model row) -> "now vs forecast"
          var fnow = null; if (wg && wg.rows) { var best = 1e12; wg.rows.forEach(function (r) { var dd = Math.abs(r.t - Date.now() / 1000); if (dd < best) { best = dd; fnow = r; } }); if (best > 5400) fnow = null; }
          var PTS16 = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
          var fdir = fnow && fnow.dir != null ? PTS16[Math.round(fnow.dir / 22.5) % 16] : "";
          var vsLine = fnow ? "forecast now " + n1(fnow.spd) + " | " + n1(fnow.gust) + " kn " + fdir + (wcur != null && fnow.spd != null ? " \u00b7 \u0394 " + (wcur - fnow.spd > 0 ? "+" : "") + n1(wcur - fnow.spd) + " kn" : "") : "";
          var offLine = outOff ? '<div class="wx-ur wx-offline"><span class="wx-il">Outside unit offline</span><span class="l">no report since ' + outLast + ' \u00b7 battery \u00b7 inside console OK</span></div>' : "";
          var under = '<div class="wx-under' + (outOff ? " stale" : "") + '">' + offLine +
            '<div class="wx-ur"><span class="wx-il">Wind Speed</span><span class="wx-iv big" style="color:' + col + '">' + (wcur == null ? "\u2014" : n1(wcur)) + ' <small>knots</small>' + (prevCur != null ? ' <span class="wx-prev">(' + n1(prevCur) + ')</span>' : "") + '</span></div>' +
            '<div class="wx-ur"><span class="wx-il">GUST | AVG</span><span class="wx-iv big2"><span style="color:' + colG + '">' + n1(wgust) + '</span> | ' + n1(wavg) + ' <small>knots</small></span></div>' +
            '</div>';
          var info = '<div class="wx-info">' +
            '<div class="wx-ir"><span class="wx-trend' + trendCls + '">' + (trendTxt || "\u2014") + '</span><span class="wx-outlook' + outlookCls + '">' + outlook + (pTrend != null ? " \u00b7 " + (pTrend > 0 ? "+" : "") + n1(pTrend) + " hPa/6h" : "") + '</span></div>' +
            '<div class="wx-ir"><span class="l">' + (mx ? "24 h max <b>" + n1(mx.v) + "</b> kn @ " + mx.t : "24 h max \u2014") + '</span><span class="l">' + (wg ? wg.model + (wg.stale ? " (stale)" : "") : "forecast loading\u2026") + '</span></div>' +
            (vsLine ? '<div class="wx-ir"><span class="l wx-vs">' + vsLine + '</span></div>' : "") +
            '</div>';
          // --- timeline, Windguru style: gust as Beaufort-coloured area with numbers, wind speed black line with numbers,
          //     direction arrows underneath, day/3-hour axis with night shading. Left of "now" = our station (15-min bins),
          //     right = Windguru forecast (hourly). Swipeable.
          var vw = (document.getElementById("wx-tlwrap") || {}).clientWidth || Math.min(440, (box.clientWidth || 380) - 20);
          var PXH = Math.max(40, Math.floor(vw / 3)), nowS = Date.now() / 1000, tStart = nowS - 24 * 3600, wg = window.__wg || null, rows = wg && wg.rows ? wg.rows.filter(function (r) { return r.t >= tStart - 1800; }) : [];
          var tEnd = rows.length ? rows[rows.length - 1].t + 3600 : nowS + 24 * 3600, hoursTotal = (tEnd - tStart) / 3600, Wt = Math.round(hoursTotal * PXH);
          var Ht = 146, top = 24, base = 112, arrowY = 130;
          function X(t) { return ((t - tStart) / 3600) * PXH; }
          var maxKn = 30; rows.forEach(function (r) { if (r.gust > maxKn) maxKn = r.gust; }); (wd.series24hGust || []).forEach(function (v) { if (v != null && scW(v) > maxKn) maxKn = scW(v); }); maxKn = Math.ceil((maxKn + 2) / 5) * 5;
          function Y(kn) { return base - (Math.min(maxKn, Math.max(0, kn)) / maxKn) * (base - top); }
          // Windguru / Beaufort colour stops (knots -> colour)
          var BF = [[0, "#ffffff"], [4, "#d6f4f8"], [7, "#b9eef3"], [11, "#a9f0a3"], [14, "#d9f58a"], [17, "#f7f26e"], [20, "#f8cf60"], [23, "#f79f62"], [26, "#f27065"], [30, "#e94b6b"], [34, "#d84a92"], [41, "#b04bc4"], [50, "#7c3a9e"]];
          var grad = '<defs><linearGradient id="wgg" x1="0" y1="' + Y(0).toFixed(1) + '" x2="0" y2="' + Y(maxKn).toFixed(1) + '" gradientUnits="userSpaceOnUse">' +
            BF.filter(function (s) { return s[0] <= maxKn; }).map(function (s) { return '<stop offset="' + (s[0] / maxKn).toFixed(3) + '" stop-color="' + s[1] + '"/>'; }).join("") + '</linearGradient></defs>';
          var tl = '<svg class="wx-tl" width="' + Wt + '" height="' + Ht + '" viewBox="0 0 ' + Wt + ' ' + Ht + '" aria-hidden="true">' + grad;
          // day columns, night shading (sunset..sunrise from Windguru, fallback 18:30-06:30), labels
          var d0 = new Date((tStart + 7200) * 1000); d0.setUTCHours(0, 0, 0, 0); var dayT = d0.getTime() / 1000 - 7200;
          var sr = wg && wg.sunrise ? wg.sunrise : "06:30", ss = wg && wg.sunset ? wg.sunset : "18:30";
          function hm2s(x) { var p = String(x).split(":"); return (Number(p[0]) || 0) * 3600 + (Number(p[1]) || 0) * 60; }
          for (var t = dayT; t < tEnd; t += 86400) {
            var xa = Math.max(0, X(t)), xb = Math.min(Wt, X(t + 86400));
            var n0 = X(t), n1x = X(t + hm2s(sr)), n2 = X(t + hm2s(ss)), n3 = X(t + 86400);
            tl += '<rect class="night" x="' + Math.max(0, n0).toFixed(0) + '" y="0" width="' + Math.max(0, Math.min(Wt, n1x) - Math.max(0, n0)).toFixed(0) + '" height="' + Ht + '"/>';
            tl += '<rect class="night" x="' + Math.max(0, n2).toFixed(0) + '" y="0" width="' + Math.max(0, Math.min(Wt, n3) - Math.max(0, n2)).toFixed(0) + '" height="' + Ht + '"/>';
            tl += '<line class="dayline" x1="' + X(t).toFixed(0) + '" y1="0" x2="' + X(t).toFixed(0) + '" y2="' + Ht + '"/>';
            var lab = new Date((t + 7200) * 1000).toLocaleDateString("en-GB", { timeZone: "UTC", weekday: "short", day: "numeric", month: "numeric" }).replace(",", "").replace(/(\d+)\/(\d+)/, "$1.$2.");
            if (xb - xa > 70) tl += '<text class="dl" x="' + ((xa + xb) / 2).toFixed(0) + '" y="10" text-anchor="middle">' + lab + '</text>';
            for (var hh = 0; hh < 24; hh += 1) { var xh = X(t + hh * 3600); if (xh > 4 && xh < Wt - 4) tl += '<text class="hl" x="' + xh.toFixed(0) + '" y="19" text-anchor="middle">' + hh + 'h</text>'; }
          }
          // ---- gust area + numbers, wind line + numbers, arrows: build unified hourly point list (history then forecast)
          var pts = [];
          rows.forEach(function (r) { pts.push({ t: r.t, gust: r.gust, spd: r.spd, dir: r.dir, hist: false }); });
          function smooth(ptsXY) {   // [[x,y],...] -> smooth cubic path (Catmull-Rom)
            if (ptsXY.length < 3) return ptsXY.map(function (p, i) { return (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1); }).join("");
            var d = "M" + ptsXY[0][0].toFixed(1) + " " + ptsXY[0][1].toFixed(1);
            for (var i = 0; i < ptsXY.length - 1; i += 1) {
              var p0 = ptsXY[i - 1] || ptsXY[i], p1 = ptsXY[i], p2 = ptsXY[i + 1], p3 = ptsXY[i + 2] || p2;
              var c1x = p1[0] + (p2[0] - p0[0]) / 6, c1y = p1[1] + (p2[1] - p0[1]) / 6, c2x = p2[0] - (p3[0] - p1[0]) / 6, c2y = p2[1] - (p3[1] - p1[1]) / 6;
              d += "C" + c1x.toFixed(1) + " " + c1y.toFixed(1) + " " + c2x.toFixed(1) + " " + c2y.toFixed(1) + " " + p2[0].toFixed(1) + " " + p2[1].toFixed(1);
            }
            return d;
          }
          // gust area (one polygon per contiguous run)
          var runs = [], cur = [];
          pts.forEach(function (p) { if (p.gust == null) { if (cur.length) runs.push(cur); cur = []; return; } cur.push([X(p.t), Y(p.gust)]); });
          if (cur.length) runs.push(cur);
          var area = "";
          runs.forEach(function (r) { area += "M" + r[0][0].toFixed(1) + " " + base + "L" + r[0][0].toFixed(1) + " " + r[0][1].toFixed(1) + smooth(r).slice(smooth(r).indexOf("C") >= 0 ? smooth(r).indexOf("C") : 1) + "L" + r[r.length - 1][0].toFixed(1) + " " + base + "Z"; });
          tl += '<path class="garea" d="' + area + '"/>';
          // wind speed line (smooth)
          var lruns = [], lc = [];
          pts.forEach(function (p) { if (p.spd == null) { if (lc.length) lruns.push(lc); lc = []; return; } lc.push([X(p.t), Y(p.spd)]); });
          if (lc.length) lruns.push(lc);
          lruns.forEach(function (r) { tl += '<path class="wline" d="' + smooth(r) + '"/>'; });
          // labels + arrows every 3 h (history every hour for the last 24 h -> every 3 h too)
          var lastLabX = -99;
          pts.forEach(function (p) {
            var x = X(p.t);
            if (x - lastLabX < 34) return;
            lastLabX = x;
            if (p.gust != null) tl += '<text class="gn" x="' + x.toFixed(1) + '" y="' + (Y(p.gust) - 3).toFixed(1) + '" text-anchor="middle">' + Math.round(p.gust) + '</text>';
            if (p.spd != null) tl += '<text class="sn" x="' + x.toFixed(1) + '" y="' + (base + 12) + '" text-anchor="middle">' + Math.round(p.spd) + '</text>';

          });
          // ---- OUR STATION (real, recorded) overlaid on the past only: gust = red line, wind = blue line, blue arrows
          var hg = wd.series24hGust || [], ha = wd.series24hAvg || [], hd = wd.dir24h || [], hc = wd.series24hCur || [];
          var BIN = (wd.binMin || 15) * 60;
          function hx(i) { return X(tStart + (i + 0.5) * BIN); }
          var rg = "", rp = false, rw = "", rwp = false;
          for (var i = 0; i < hg.length; i += 1) {
            var tt = tStart + (i + 0.5) * BIN; if (tt > nowS) break;
            if (hg[i] != null) { rg += (rp ? "L" : "M") + hx(i).toFixed(1) + " " + Y(scW(hg[i])).toFixed(1); rp = true; } else rp = false;
            var cur = hc[i] != null ? scW(hc[i]) : (ha[i] != null ? scW(ha[i]) : null);
            if (cur != null) { rw += (rwp ? "L" : "M") + hx(i).toFixed(1) + " " + Y(cur).toFixed(1); rwp = true; } else rwp = false;
          }
          if (rg) tl += '<path class="rgust" d="' + rg + '"/>';
          if (rw) tl += '<path class="rwind" d="' + rw + '"/>';
          var firstReal = null; for (var q = 0; q < hg.length; q += 1) { if (hg[q] != null || hc[q] != null) { firstReal = hx(q); break; } }
          if (firstReal != null) { tl += '<rect class="realband" x="' + firstReal.toFixed(1) + '" y="0" width="' + (X(nowS) - firstReal).toFixed(1) + '" height="' + Ht + '"/><text class="rl" x="' + (firstReal + 3).toFixed(1) + '" y="' + (top + 8) + '">LIVE \u2014 our station</text>'; }
          tl += '<text class="fl" x="' + (X(nowS) + 28).toFixed(1) + '" y="' + (Ht - 4) + '">FORECAST \u2192</text>';
          // now marker
          tl += '<line class="now" x1="' + X(nowS).toFixed(1) + '" y1="0" x2="' + X(nowS).toFixed(1) + '" y2="' + Ht + '"/><text class="nl" x="' + (X(nowS) + 3).toFixed(1) + '" y="' + (Ht - 4) + '">now</text>';
          tl += '</svg>';
          var tlWrap = '<div class="wx-tlwrap" id="wx-tlwrap" data-nowx="' + X(nowS).toFixed(0) + '">' + tl + '</div>';
          h += '<div class="hs-tile wx-windpanel ' + off + (outOff ? " outoff src-off" : " src-on") + (!outOff && wgust != null && wgust > 50 ? " flash" : "") + '">' +
               (outOff ? '<div class="wx-offline">\u26A0 OUTDOOR UNIT OFFLINE \u2014 no wind/rain/UV since ' + odLast + ' (solar/battery) \u00b7 indoor console online</div>' : "") +
               '<div class="wx-wp-top">' +
                 '<div class="wx-wp-comp">' + comp + under + '</div>' + info +
               '</div>' +
               tlWrap +
               '<div class="wx-wp-row wx-legend"><span class="l">showing 1 h back / 2 h ahead \u00b7 swipe \u2190 history \u00b7 forecast \u2192 \u00b7 forecast: coloured gust area, black wind line, <i class="k" style="background:#DC143C"></i>real gust <i class="k" style="background:#1d6fe0"></i>real wind</span></div>' +
               '</div>';
          // Which unit each reading comes from: OUTDOOR solar/battery unit (wind, rain, UV, light, outside temp/humidity)
          // vs INDOOR USB console (inside temp/humidity, barometer). Tile background: pale green = its unit is reporting,
          // pale red = its unit has stopped reporting (values shown are the last received, greyed).
          var inAge = wx.indoorLastTs ? (Date.now() / 1000 - wx.indoorLastTs) : null, inOff = wx.online === false || (inAge != null && inAge > 1800);
          var OUT = "src-out " + (outOff ? "src-off" : "src-on"), IN = "src-in " + (inOff ? "src-off" : "src-on");
          var outT = sc(s.temp_current_external, u, "temp_current_external", 1), outH = sc(s.humidity_outdoor, u, "humidity_outdoor", 0);
          var WX = {
            temp: wsvg('<path d="M10 13.5a4 4 0 1 0 4 0v-8.5a2 2 0 0 0 -4 0v8.5" /> <path d="M10 9l4 0" />'),
            hum: wsvg('<path d="M7.502 19.423c2.602 2.105 6.395 2.105 8.996 0c2.602 -2.105 3.262 -5.708 1.566 -8.546l-4.89 -7.26c-.42 -.625 -1.287 -.803 -1.936 -.397a1.376 1.376 0 0 0 -.41 .397l-4.893 7.26c-1.695 2.838 -1.035 6.441 1.567 8.546" />'),
            baro: wsvg('<path d="M3 12a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" /> <path d="M11 12a1 1 0 1 0 2 0a1 1 0 1 0 -2 0" /> <path d="M13.41 10.59l2.59 -2.59" /> <path d="M7 12a5 5 0 0 1 5 -5" />'),
            uv: wsvg('<path d="M3 12h1m16 0h1m-15.4 -6.4l.7 .7m12.1 -.7l-.7 .7m-9.7 5.7a4 4 0 1 1 8 0" /> <path d="M12 4v-1" /> <path d="M13 16l2 5h1l2 -5" /> <path d="M6 16v3a2 2 0 1 0 4 0v-3" />'),
            rain: wsvg('<path d="M7 18a4.6 4.4 0 0 1 0 -9a5 4.5 0 0 1 11 2h1a3.5 3.5 0 0 1 0 7" /> <path d="M11 13v2m0 3v2m4 -5v2m0 3v2" />'),
            home: wsvg('<path d="M5 12l-2 0l9 -9l9 9l-2 0" /> <path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-7" /> <path d="M9 21v-6a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v6" />'),
            sun: wsvg('<path d="M8 12a4 4 0 1 0 8 0a4 4 0 1 0 -8 0" /> <path d="M3 12h1m8 -9v1m8 8h1m-9 8v1m-6.4 -15.4l.7 .7m12.1 -.7l-.7 .7m0 11.4l.7 .7m-12.1 -.7l-.7 .7" />')
          };
          function wtile(ic, v, l, cls) { return '<div class="hs-tile wx-t ' + (cls || "") + '">' + ic + '<span class="v">' + v + '</span><span class="l">' + l + '</span></div>'; }
          var offTag = outOff ? " \u00b7 offline" : "";
          function ago(sec) { return sec == null ? "\u2014" : sec < 90 ? Math.round(sec) + " s ago" : Math.round(sec / 60) + " min ago"; }
          function every(sec) { return sec == null ? "" : sec < 120 ? "every " + sec + " s" : "every " + Math.round(sec / 60) + " min"; }
          // ---- OUTSIDE unit sub-card wraps the wind panel + outdoor tiles (h so far = wind panel)
          h = '<div class="wx-unit ' + (outOff ? "src-off" : "src-on") + '"><div class="wx-unit-head"><b>OUTSIDE</b> \u00b7 solar/battery unit \u00b7 ' + (outOff ? "OFFLINE \u00b7 last report " + ago(outAge) : "reporting " + every(wx.outdoorIntervalS) + " \u00b7 last " + ago(outAge)) + '</div>' + h;
          // OUTDOOR unit readings
          h += wtile(WX.temp, n1(outT) + "\u00b0", "outside temp" + offTag, OUT);
          h += wtile(WX.hum, n1(outH) + "%", "outside humidity" + offTag, OUT);
          var rr = sc(s.rain_rate, u, "rain_rate", 1);
          h += wtile(WX.rain, n1(sc(s.rain_24h, u, "rain_24h", 1)) + " mm", "rain 24 h" + (rr ? " \u00b7 " + n1(rr) + " mm/h now" : "") + offTag, OUT);
          h += wtile(WX.uv, "UV " + n1(sc(s.uv_index, u, "uv_index", 0)), "UV \u00b7 feels " + n1(sc(s.feellike_temp, u, "feellike_temp", 1)) + "\u00b0" + offTag, OUT);
          h += wtile(WX.sun, (raw.dp135 != null ? n1(Number(raw.dp135) / 100) + " klux" : "\u2014"), "light" + offTag, OUT);
          h += '</div><div class="wx-unit ' + (inOff ? "src-off" : "src-on") + '"><div class="wx-unit-head"><b>INSIDE</b> \u00b7 USB console \u00b7 ' + (inOff ? "OFFLINE" + (wx.online === false ? " \u00b7 station offline in Tuya" : "") + " \u00b7 last report " + ago(inAge) : "reporting " + every(wx.indoorIntervalS) + " \u00b7 last " + ago(inAge)) + '</div>';
          // INDOOR console readings
          h += wtile(WX.home, n1(sc(s.temp_current, u, "temp_current", 1)) + "\u00b0 " + n1(sc(s.humidity_value, u, "humidity_value", 0)) + "%", "inside (console)" + (inOff ? " \u00b7 offline" : ""), IN);
          h += wtile(WX.baro, n1(sc(s.atmospheric_pressture, u, "atmospheric_pressture", 0)), "pressure hPa (console)" + (pTrend != null ? " " + (pTrend > 0 ? "\u2197" : pTrend < 0 ? "\u2198" : "\u2192") : "") + (inOff ? " \u00b7 offline" : ""), IN);
        }
        if (wx) h += '</div>';
        document.getElementById("hs-weather").innerHTML = h;
        placeTimeline();
        document.getElementById("home-weather").hidden = !wx && !indoor;
        if (wx) document.getElementById("hw-upd").textContent = "page refresh 10 s \u00b7 outside " + (every(wx.outdoorIntervalS) || "\u2014") + " \u00b7 console " + (every(wx.indoorIntervalS) || "\u2014") + " \u00b7 live push";
        h = "";
        var items = [];   // {ts, html} -> newest activity first, ageing downwards
        function wsvg(p) { return '<svg class="wx-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + p + '</svg>'; }
        if (indoor) {
          var si = indoor.status, ui = indoor.units, ioff = indoor.online ? "" : "off";
          h += '<div class="hs-tile wx-t ' + (si.battery_state === "low" ? "warn " : "") + ioff + '">' + wsvg('<path d="M5 12l-2 0l9 -9l9 9l-2 0" /> <path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-7" /> <path d="M9 21v-6a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v6" />') + '<span class="v">' + n1(sc(si.va_temperature, ui, "va_temperature", 1)) + "\u00b0 " + n1(sc(si.va_humidity, ui, "va_humidity", 0)) + '%</span><span class="l">inside sensor' + (si.battery_state === "low" ? " \u00b7 batt low" : "") + '</span></div>';
        }
        if (lock) {
          var sl = lock.status, bat = sl.residual_electricity;
          var lu = d.lockUsers || {}, unassigned = null;
          var last = ["fingerprint", "password", "card", "face", "app", "key", "temporary"].filter(function (k) { return sl["unlock_" + k]; })
            .map(function (k) { var id = String(sl["unlock_" + k]); var who = (lu[k] || {})[id]; if (!who && !unassigned) unassigned = { method: k, slot: id }; return { k: k, id: id, who: who }; });
          // Line icons (stroke, currentColor) so the row reads as one set: door | person | method.
          function svg(paths) { return '<svg class="hs-svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + paths + '</svg>'; }
          var I = {
            // person walking through an open door (one icon, replaces separate door + person)
            door: svg('<path d="M13 12v.01" /> <path d="M3 21h18" /> <path d="M5 21v-16a2 2 0 0 1 2 -2h6m4 10.5v7.5" /> <path d="M21 7h-7m3 -3l-3 3l3 3" />'),
            person: "",
            fingerprint: svg('<path d="M18.9 7a8 8 0 0 1 1.1 5v1a6 6 0 0 0 .8 3" /> <path d="M8 11a4 4 0 0 1 8 0v1a10 10 0 0 0 2 6" /> <path d="M12 11v2a14 14 0 0 0 2.5 8" /> <path d="M8 15a18 18 0 0 0 1.8 6" /> <path d="M4.9 19a22 22 0 0 1 -.9 -7v-1a8 8 0 0 1 12 -6.95" />'),
            password: svg('<path d="M2 8a2 2 0 0 1 2 -2h16a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-16a2 2 0 0 1 -2 -2l0 -8" /> <path d="M6 10l0 .01" /> <path d="M10 10l0 .01" /> <path d="M14 10l0 .01" /> <path d="M18 10l0 .01" /> <path d="M6 14l0 .01" /> <path d="M18 14l0 .01" /> <path d="M10 14l4 .01" />'),
            card: svg('<path d="M3 8a3 3 0 0 1 3 -3h12a3 3 0 0 1 3 3v8a3 3 0 0 1 -3 3h-12a3 3 0 0 1 -3 -3l0 -8" /> <path d="M3 10l18 0" /> <path d="M7 15l.01 0" /> <path d="M11 15l2 0" />'),
            face: svg('<path d="M4 8v-2a2 2 0 0 1 2 -2h2" /> <path d="M4 16v2a2 2 0 0 0 2 2h2" /> <path d="M16 4h2a2 2 0 0 1 2 2v2" /> <path d="M16 20h2a2 2 0 0 0 2 -2v-2" /> <path d="M9 10l.01 0" /> <path d="M15 10l.01 0" /> <path d="M9.5 15a3.5 3.5 0 0 0 5 0" />'),
            app: svg('<path d="M6 5a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v14a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2v-14" /> <path d="M11 4h2" /> <path d="M12 17v.01" />'),
            key: svg('<path d="M16.555 3.843l3.602 3.602a2.877 2.877 0 0 1 0 4.069l-2.643 2.643a2.877 2.877 0 0 1 -4.069 0l-.301 -.301l-6.558 6.558a2 2 0 0 1 -1.239 .578l-.175 .008h-1.172a1 1 0 0 1 -.993 -.883l-.007 -.117v-1.172a2 2 0 0 1 .467 -1.284l.119 -.13l.414 -.414h2v-2h2v-2l2.144 -2.144l-.301 -.301a2.877 2.877 0 0 1 0 -4.069l2.643 -2.643a2.877 2.877 0 0 1 4.069 0" /> <path d="M15 9h.01" />'),
            temporary: svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>')
          };
          var MICON = { fingerprint: I.fingerprint, password: I.password, card: I.card, face: I.face, app: I.app, key: I.key, temporary: I.temporary };
          var lastTxt = last.length ? (MICON[last[0].k] || "") + " " + (last[0].who || ("#" + last[0].id)) : "\u2014";
          box.__lockUnassigned = unassigned;
          var who = last.length ? (last[0].who || ("#" + last[0].id)) : "\u2014", mic = last.length ? (MICON[last[0].k] || "") : "";
          var lt = lock.lastUnlock && lock.lastUnlock.ts ? new Date(lock.lastUnlock.ts * 1000) : null;
          var when = lt ? lt.toLocaleString("en-GB", { timeZone: "Africa/Johannesburg", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).replace(",", " \u00b7") : "";
          var alarmTxt = sl.alarm_lock && sl.alarm_lock !== "none" && sl.alarm_lock !== "low_battery" ? String(sl.alarm_lock).replace(/_/g, " ") : "";
          // 2nd-last opening (from the recorded unlock log): method icon + name, smaller, same door/battery.
          var prevHtml = "";
          if (lock.prevUnlock) {
            var pu = lock.prevUnlock, pwho = (lu[pu.method] || {})[String(pu.slot)] || ("#" + pu.slot);
            var pwhen = new Date(pu.ts * 1000).toLocaleString("en-GB", { timeZone: "Africa/Johannesburg", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).replace(",", " \u00b7");
            prevHtml = '<div class="hs-lock-prev">' + (MICON[pu.method] || "") + '<span><span class="v">' + pwho + '</span><span class="l">' + pwhen + '</span></span></div>';
          }
          var bl = bat == null ? 0 : Math.max(0, Math.min(100, Number(bat))), bcol = bl <= 20 ? "#dc2626" : bl <= 40 ? "#f59e0b" : "#16a34a";
          var battery = '<svg viewBox="0 0 40 20" width="44" height="22" aria-hidden="true"><rect x="1" y="3" width="34" height="14" rx="3" fill="none" stroke="#475569" stroke-width="1.8"/><rect x="36" y="7" width="3" height="6" rx="1" fill="#475569"/><rect x="3" y="5" width="' + (30 * bl / 100) + '" height="10" rx="2" fill="' + bcol + '"/></svg>';
          items.push({ grp: "door", use: 0, ts: (lock.lastUnlock && lock.lastUnlock.ts) || lock.lastEvent || 0, html: '<div class="hs-lockbox' + (unassigned ? " warn" : "") + (lock.online ? "" : " off") + '">' +
               '<div class="hs-lock-icons hs-lock-last">' + I.door + mic + '</div>' +
               '<div class="hs-lock-mid hs-lock-last"><span class="v">' + who + '</span><span class="l">' + (when || "last unlock") + (unassigned ? " \u00b7 hold to name" : "") + (alarmTxt ? ' \u00b7 <b style="color:#b91c1c">' + alarmTxt + '</b>' : "") + '</span></div>' +
               prevHtml +
               '<div class="hs-lock-batt" style="color:' + bcol + '">' + battery + '<span class="l">' + (bat == null ? "\u2014" : bl + "%") + (bl <= 20 ? " low" : "") + (lock.online ? "" : " \u00b7 offline") + '</span></div>' +
               '</div>' });
        }
        document.getElementById("hs-indoor").innerHTML = "";
        var wxEl = document.getElementById("hs-weather"), lastUnit = wxEl.querySelector(".wx-unit:last-child");
        if (lastUnit && h) lastUnit.insertAdjacentHTML("beforeend", h);
        h = "";
        h = "";
        plugs.sort(function (a, b) { return (b.status.cur_power || 0) - (a.status.cur_power || 0); });
        plugs.forEach(function (p) {
          var w = sc(p.status.cur_power, p.units, "cur_power", 1), kwh = p.todayAddEle != null ? sc(p.todayAddEle, p.units, "add_ele", 3) : null;
          var on = p.status.switch_1 === true, sw = "switch_1" in p.status;
          // Plug tile = power reading + its own switch button (tap to turn the plug/pump on or off, PIN login required).
          // Colour by draw vs this plug's own 7-day average: green = light load, orange = around average, red = >10% above average.
          var avg = p.avgPowerRaw != null ? sc(p.avgPowerRaw, p.units, "cur_power", 1) : null, lvl = "";
          if (p.online && w != null && w > 5) lvl = avg == null ? " run" : (w > avg * 1.1 ? " hi" : (w < avg * 0.5 ? " run" : " mid"));
          var pUse = (p.usage && p.usage.monthKwh ? p.usage.monthKwh * 1000 : 0) + (p.usage && p.usage.monthOnS ? p.usage.monthOnS / 3600 : 0) + (w || 0);
          var pDorm = !p.online || (!on && !pUse && !(w > 5));
          items.push({ grp: pDorm ? "dormant" : "plugs", use: pUse, ts: p.lastEvent || 0, html: '<div class="hs-tile hs-plug' + (!p.online ? " off" : lvl) + '">' +
               '<span class="ic">' + tico(p.id) + '</span>' +
               '<span class="v">' + (w == null ? "\u2014" : Math.round(w) + " W") + '</span>' +
               '<span class="l">' + neatName(p) + (avg != null ? " \u00b7 avg " + Math.round(avg) + " W" : "") + '</span>' +
               '<span class="l">' + (p.usage && p.usage.todayKwh != null ? n1(p.usage.todayKwh) + " kWh today \u00b7 " + n1(p.usage.monthKwh) + " kWh " + monLabel() : (kwh != null ? n1(kwh) + " kWh today" : "")) +
                 (p.usage && p.usage.todayOnS != null ? " \u00b7 on " + hm(p.usage.todayOnS) : "") + '</span>' +
               (sw ? '<button type="button" class="hs-gang hs-plugsw' + (on ? " on" : "") + '" data-dev="' + p.id + '" data-sw="switch_1" data-on="' + (on ? 1 : 0) + '" title="' + p.name + '"><span class="ic ctl ctl-power" aria-hidden="true"></span><span class="gl">' + (on ? "ON" : "OFF") + (on && (p.since || {}).switch_1 ? " \u00b7 " + dur(p.since.switch_1) : "") + '</span></button>' : "") +
               '</div>' });
        });
        // Lights by device, one button per gang (icon + app label), lit when on with time-on underneath.
        var ln = d.lightNames || {}, lh = "";
        lights.filter(function (l) { return ["kg", "tdq", "dlq", "pc", "sfkzq"].indexOf(l.category) !== -1; }).sort(function (a, b) { return neatName(a).localeCompare(neatName(b)); }).forEach(function (l) {
          var codes = switchCodes(l.status);
          var labels = ln[l.id] || [];
          var shown = neatName(l);
          var isWater = l.category === "sfkzq";
          var g = codes.map(function (c, i) {
            var on = l.status[c] === true, lab = labels[i] || (codes.length > 1 ? String(i + 1) : "");
            var gt = l.usage && l.usage.gangs && l.usage.gangs[c] ? l.usage.gangs[c].todayS : null;
            return '<button type="button" class="hs-gang' + (on ? " on" : "") + '" data-dev="' + l.id + '" data-sw="' + c + '" data-on="' + (on ? 1 : 0) + '" title="' + shown + (lab ? " \u00b7 " + lab : "") + (gt != null ? " \u00b7 today " + hm(gt) : "") + '">' +
              '<span class="ic ctl ctl-power" aria-hidden="true"></span>' + (lab ? '<span class="gl">' + lab + '</span>' : "") + (on ? '<span class="dur">' + dur((l.since || {})[c]) + '</span>' : (gt ? '<span class="dur">' + hm(gt) + '</span>' : "")) + '</button>';
          }).join("");
          var us = l.usage || {};
          var wu = l.waterUse || {};
          var hasWater = isWater && (wu.todayL != null || wu.monthL != null || wu.lastMonthL != null);
          var lGrp = isWater ? "water" : (l.category === "tdq" || l.category === "pc") ? "relays" : "lights";
          var keepDev = String((window.ARIAL_CONFIG || {}).siteId) === "bing" && !isWater;
          var lUse = hasWater ? (Number(wu.monthL) || 0) + (Number(wu.todayL) || 0) : ((us.monthOnS || 0) + (us.todayOnS || 0));
          var tot = us.todayOnS != null ? '<span class="tot">' + hm(us.todayOnS) + " today \u00b7 " + hm(us.monthOnS) + " " + monLabel() + '</span>' : "";
          var anyOn = codes.some(function (c) { return l.status[c] === true; });
          var waterCls = isWater ? " hs-water" : "";
          var wHtml = waterLine(l);
          var wTip = hasWater ? " \u00b7 " + litres(wu.todayL) + " today \u00b7 " + litres(wu.monthL) + " " + monLabel() + " \u00b7 " + litres(wu.lastMonthL) + " " + prevMonLabel() : "";
          if (codes.length > 1) {
            // compact multi-gang tile: icon + name + ON / OFF / n/m ON + master power (any on -> all off, all off -> all on)
            var nOn = codes.filter(function (c) { return l.status[c] === true; }).length, allOn = nOn === codes.length;
            var stTxt = allOn ? "ON" : nOn === 0 ? "OFF" : nOn + "/" + codes.length + " ON";
            items.push({ grp: (!l.online || (!keepDev && !nOn && !lUse && !hasWater)) ? "dormant" : lGrp, use: lUse, ts: l.lastEvent || 0, html: '<div class="hs-light gang' + waterCls + (l.online ? "" : " off") + (nOn ? (allOn ? " allon" : " mixed") : "") + '" data-dev="' + l.id + '" title="' + shown + ' \u00b7 ' + codes.length + ' gangs' + (us.todayOnS != null ? " \u00b7 " + hm(us.todayOnS) + " today" : "") + wTip + '">' +
              '<span class="nm">' + tico(l.id, "sm") + shown + '</span><span class="st">' + stTxt + '</span><span class="gc" title="' + codes.length + ' switches \u00b7 tap for each">' + codes.length + '<i>\u203a</i></span>' +
              '<button type="button" class="hs-master' + (nOn ? " on" : "") + '" data-dev="' + l.id + '" data-any="' + (nOn ? 1 : 0) + '" data-codes="' + codes.join(",") + '" aria-label="' + (nOn ? "all off" : "all on") + '"><span class="ctl ctl-power" aria-hidden="true"></span></button>' + wHtml + '</div>' });
            return;
          }
          // single gang: same compact tile as multi-gang (one cell, name, ON/OFF/OFFLINE, one power button via gangTap)
          var c1 = codes[0], on1 = l.online && l.status[c1] === true;
          var st1 = !l.online ? "OFFLINE" : on1 ? "ON" : "OFF";
          var sub1 = !l.online ? "" : on1 && (l.since || {})[c1] ? " \u00b7 " + dur(l.since[c1]) : (us.todayOnS >= 60 ? " \u00b7 " + hm(us.todayOnS) + " today" : "");
          items.push({ grp: (!l.online || (!keepDev && !on1 && !lUse && !hasWater)) ? "dormant" : lGrp, use: lUse, ts: l.lastEvent || 0, html: '<div class="hs-light gang single' + waterCls + (l.online ? "" : " off") + (on1 ? " allon" : "") + '" data-dev="' + l.id + '" title="' + shown + (us.todayOnS != null ? " \u00b7 " + hm(us.todayOnS) + " today \u00b7 " + hm(us.monthOnS) + " " + monLabel() : "") + wTip + '">' +
            '<span class="nm">' + tico(l.id, "sm") + shown + '</span><span class="st">' + st1 + (sub1 ? '<span class="sub">' + sub1 + '</span>' : "") + '</span>' +
            '<button type="button" class="hs-master hs-gang' + (on1 ? " on" : "") + '" data-dev="' + l.id + '" data-sw="' + c1 + '" data-on="' + (on1 ? 1 : 0) + '" aria-label="' + (on1 ? "turn off" : "turn on") + '"><span class="ctl ctl-power" aria-hidden="true"></span></button>' + wHtml + '</div>' });
        });
        meters.sort(function (a, b) { return neatName(a).localeCompare(neatName(b)); }).forEach(function (e) {
          var eu = e.eleUse || {};
          var eUse = Number(eu.monthKwh) || 0;
          var eTip = eu.todayKwh != null ? " \u00b7 " + Number(eu.todayKwh).toFixed(2) + " kWh today \u00b7 " + Number(eu.monthKwh).toFixed(2) + " kWh " + monLabel() + " \u00b7 " + Number(eu.lastMonthKwh).toFixed(2) + " kWh " + prevMonLabel() : "";
          items.push({ grp: e.online || eUse ? "power" : "dormant", use: eUse, ts: e.lastEvent || 0, html: '<div class="hs-light gang single hs-power' + (e.online ? "" : " off") + '" data-dev="' + e.id + '" title="' + neatName(e) + eTip + '">' +
            '<span class="nm">' + tico(e.id, "sm") + '<span class="hs-enm">' + neatName(e) + "</span>" + eleLive(e) + "</span>" +
            eleLine(e) + "</div>" });
        });
        var known = {};
        if (wx) known[wx.id] = 1;
        if (indoor) known[indoor.id] = 1;
        if (lock) known[lock.id] = 1;
        plugs.forEach(function (p) { known[p.id] = 1; });
        lights.forEach(function (l) { known[l.id] = 1; });
        meters.forEach(function (e) { known[e.id] = 1; });
        devs.forEach(function (x) {
          if (!x || !x.id || known[x.id]) return;
          items.push({ grp: "other", use: 0, ts: x.lastEvent || 0, html: '<div class="hs-tile' + (x.online ? "" : " off") + '">' +
            '<span class="ic">' + tico(x.id) + '</span>' +
            '<span class="v">' + (x.online ? "ON" : "OFFLINE") + '</span>' +
            '<span class="l">' + neatName(x) + '</span></div>' });
        });
        var lightHead = String((window.ARIAL_CONFIG || {}).siteId) === "bing" ? "Devices" : "Lights";
        var GROUPS = [["door", "Door"], ["water", "Water"], ["power", "Power"], ["lights", lightHead], ["plugs", "Smart plugs & timers"], ["relays", "Receivers & relays"], ["other", "Other"], ["dormant", "Not in use"]];
        var gh = "";
        GROUPS.forEach(function (g) {
          var its = items.filter(function (x) { return x.grp === g[0]; });
          if (!its.length) return;
          // most used first (month + today on-time, or kWh + watts for plugs); dormant alphabetical by tile text
          if (g[0] === "dormant") its.sort(function (a, b) { return a.html.replace(/<[^>]+>/g, "").localeCompare(b.html.replace(/<[^>]+>/g, "")); });
          else its.sort(function (a, b) { return (b.use || 0) - (a.use || 0) || (b.ts || 0) - (a.ts || 0); });
          gh += '<div class="hs-sub hs-sub-' + g[0] + '"><h3>' + g[1] + (g[0] === "dormant" ? ' <span>' + its.length + '</span>' : "") + '</h3><div class="hs-sub-grid">' + its.map(function (x) { return x.html; }).join("") + '</div></div>';
        });
        if (!gh) {
          var src = d.source === "cbi" ? "CBI Home" : "home";
          gh = '<div class="hs-sub"><h3>Devices</h3><div class="hs-sub-grid"><div class="hs-tile"><span class="v">\u2014</span><span class="l">No ' + src + ' devices yet</span></div></div></div>';
        }
        document.getElementById("hs-items").innerHTML = gh;
        if (gangDev) renderGangPop();
        if (!wx) document.getElementById("hw-upd").textContent = new Date(d.at * 1000).toLocaleTimeString("en-GB", { timeZone: "Africa/Johannesburg", hour: "2-digit", minute: "2-digit" });
        document.getElementById("hs-upd").textContent = new Date(d.at * 1000).toLocaleTimeString("en-GB", { timeZone: "Africa/Johannesburg", hour: "2-digit", minute: "2-digit" });
        box.hidden = false;
      }
      // ---- multi-gang popup: every real switch_N gang of one device, All on / All off, live refresh from the poll
      var gp = document.createElement("div");
      gp.className = "lights-pop"; gp.id = "gang-pop"; gp.hidden = true;
      gp.innerHTML = '<div class="lights-panel card" role="dialog" aria-modal="true" aria-labelledby="gang-title"><div class="activity-head lights-head"><h2 class="section-title" id="gang-title">Lights</h2><div class="lights-all"><button type="button" class="lights-all-btn" id="gang-all-on">All on</button><button type="button" class="lights-all-btn" id="gang-all-off">All off</button><button type="button" class="lights-close" id="gang-close" aria-label="Close">&times;</button></div></div><div class="lights-grid" id="gang-grid"></div><p class="lights-note" id="gang-note"></p></div>';
      document.body.appendChild(gp);
      function gangCodes(dev) { return switchCodes(dev.status); }
      function renderGangPop() {
        var dev = (lastData && lastData.devices || []).filter(function (x) { return x.id === gangDev; })[0];
        if (!dev) { closeGangPop(); return; }
        var names = (lastData.lightNames || {})[dev.id] || [], codes = gangCodes(dev);
        document.getElementById("gang-title").textContent = dev.name;
        document.getElementById("gang-grid").innerHTML = codes.map(function (c, i) {
          var on = dev.status[c] === true, lab = names[i] || ("Gang " + (i + 1));
          return '<button type="button" class="light-btn' + (on ? " on" : "") + '" data-dev="' + dev.id + '" data-sw="' + c + '" data-on="' + (on ? 1 : 0) + '"><span class="light-icon" aria-hidden="true"></span><span class="light-name">' + lab + '</span><span class="light-state">' + (on ? "ON" : "OFF") + '</span></button>';
        }).join("");
        document.getElementById("gang-note").textContent = dev.online ? "" : "Device offline";
      }
      function openGangPop(id) { gangDev = id; openGangPop._at = Date.now(); renderGangPop(); gp.hidden = false; }
      function closeGangPop() { gangDev = null; gp.hidden = true; }
      function gangAll(want) {
        var dev = (lastData && lastData.devices || []).filter(function (x) { return x.id === gangDev; })[0]; if (!dev) return;
        var user = window.arialUser; if (!user || !user.code) { if (typeof window.arialRejectNeedLogin === "function") window.arialRejectNeedLogin(); return; }
        var codes = gangCodes(dev);
        codes.forEach(function (c) { pend[dev.id + ":" + c] = { on: want, until: Date.now() + 8000 }; dev.status[c] = want; });
        renderGangPop();
        fetch(API + "/tuya/switch", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code: user.code, device_id: dev.id, switch: "all", value: want }) })
          .then(function (r) { return r.json().then(function (j) { if (r.status === 401 && typeof window.arialRejectNeedLogin === "function") window.arialRejectNeedLogin(); if (!r.ok) throw new Error(j.detail || "failed"); }); })
          .catch(function () { codes.forEach(function (c) { delete pend[dev.id + ":" + c]; }); })
          .then(function () { setTimeout(poll, 1200); });
      }
      gp.addEventListener("click", function (ev) {
        if (Date.now() - (openGangPop._at || 0) < 400) return;   // the tap that opened us
        if (ev.target === gp) { closeGangPop(); return; }
        var b = ev.target.closest(".light-btn");
        if (b) { var st = b.querySelector(".light-state"); gangTap(b); if (st) st.textContent = b.getAttribute("data-on") === "1" ? "ON" : "OFF"; }
      });
      document.getElementById("gang-close").addEventListener("click", closeGangPop);
      document.getElementById("gang-all-on").addEventListener("click", function () { gangAll(true); });
      document.getElementById("gang-all-off").addEventListener("click", function () { gangAll(false); });
      document.getElementById("hs-items").addEventListener("click", function (ev) {
        var gt = ev.target.closest(".hs-light.gang");
        if (gt && !gt.classList.contains("single") && !ev.target.closest(".hs-master")) { openGangPop(gt.getAttribute("data-dev")); return; }
        var mb = ev.target.closest(".hs-master:not(.hs-gang)");
        if (mb) {
          ev.stopPropagation(); ev.preventDefault();
          var user = window.arialUser;
          if (!user || !user.code) { if (typeof window.arialRejectNeedLogin === "function") window.arialRejectNeedLogin(); return; }
          var dev = mb.getAttribute("data-dev"), codes = (mb.getAttribute("data-codes") || "").split(",").filter(Boolean), want = mb.getAttribute("data-any") !== "1";
          codes.forEach(function (c) { pend[dev + ":" + c] = { on: want, until: Date.now() + 8000 }; });
          mb.classList.toggle("on", want); mb.setAttribute("data-any", want ? "1" : "0"); mb.classList.add("pending");
          var tile = mb.closest(".hs-light"); if (tile) { tile.classList.toggle("allon", want); tile.classList.remove("mixed"); var stEl = tile.querySelector(".st"); if (stEl) stEl.textContent = want ? "ON" : "OFF"; }
          fetch(API + "/tuya/switch", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: user.code, device_id: dev, switch: "all", value: want }) })
            .then(function (r) { return r.json().then(function (j) { if (r.status === 401 && typeof window.arialRejectNeedLogin === "function") window.arialRejectNeedLogin(); if (!r.ok) throw new Error(j.detail || "failed"); }); })
            .catch(function () { codes.forEach(function (c) { delete pend[dev + ":" + c]; }); mb.classList.toggle("on", !want); mb.setAttribute("data-any", want ? "0" : "1"); })
            .then(function () { mb.classList.remove("pending"); setTimeout(poll, 1200); });
          return;
        }
        var b = ev.target.closest(".hs-gang"); if (!b) return;
        gangTap(b);
      });
      function gangTap(b) {
        var user = window.arialUser;
        if (!user || !user.code) { if (typeof window.arialRejectNeedLogin === "function") window.arialRejectNeedLogin(); return; }
        var want = b.getAttribute("data-on") !== "1";
        pend[b.getAttribute("data-dev") + ":" + b.getAttribute("data-sw")] = { on: want, until: Date.now() + 8000 };
        b.classList.toggle("on", want); b.setAttribute("data-on", want ? "1" : "0"); b.classList.add("pending");
        var stx = b.querySelector(".light-state"); if (stx) stx.textContent = want ? "ON" : "OFF";
        fetch(API + "/tuya/switch", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code: user.code, device_id: b.getAttribute("data-dev"), switch: b.getAttribute("data-sw"), value: want }) })
          .then(function (r) { return r.json().then(function (j) { if (r.status === 401 && typeof window.arialRejectNeedLogin === "function") window.arialRejectNeedLogin(); if (!r.ok) throw new Error(j.detail || "failed"); }); })
          .catch(function () { delete pend[b.getAttribute("data-dev") + ":" + b.getAttribute("data-sw")]; b.classList.toggle("on", !want); b.setAttribute("data-on", want ? "0" : "1"); })
          .then(function () { b.classList.remove("pending"); setTimeout(poll, 1200); });
      }
      // Unassigned credential slot: long-press the "last unlock" tile to name it (keypad login required).
      var holdT = null;
      function lockHoldStart(ev) {
        var t = ev.target.closest(".hs-lock-last"); if (!t || !box.__lockUnassigned) return;
        holdT = setTimeout(function () {
          holdT = null;
          var user = window.arialUser; if (!user || !user.code) return;
          var u = box.__lockUnassigned;
          var name = window.prompt("Who is " + u.method + " #" + u.slot + "?", "");
          if (!name || !name.trim()) return;
          fetch(API + "/home/lock_user", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: user.code, method: u.method, slot: u.slot, name: name.trim() }) })
            .then(function (r) { return r.json(); }).then(function () { poll(); }).catch(function () {});
        }, 650);
      }
      function lockHoldEnd() { if (holdT) { clearTimeout(holdT); holdT = null; } }
      box.addEventListener("pointerdown", lockHoldStart);
      box.addEventListener("pointerup", lockHoldEnd); box.addEventListener("pointerleave", lockHoldEnd); box.addEventListener("pointercancel", lockHoldEnd);
      box.addEventListener("contextmenu", function (ev) { if (ev.target.closest(".hs-lock-last")) ev.preventDefault(); });
      var wgTimer = null;
      function loadWg() { fetch(API + "/home/windguru", { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (d) { if (d && d.ok) { window.__wg = d; poll(); } }).catch(function () {}); }
      loadWg(); wgTimer = setInterval(loadWg, 1800000);
      var tlScroll = null;   // user's timeline position survives the 10 s re-render
      document.getElementById("hs-weather").addEventListener("scroll", function (ev) { if (ev.target.id === "wx-tlwrap") tlScroll = ev.target.scrollLeft; }, true);
      function placeTimeline() {
        var w = document.getElementById("wx-tlwrap"); if (!w) return;
        var nowX = Number(w.getAttribute("data-nowx")) || 0;
        w.scrollLeft = tlScroll != null ? tlScroll : Math.max(0, nowX - w.clientWidth / 3);
      }
      var timer = null;
      function poll() {
        if (below && below.hidden) { box.hidden = true; document.getElementById("home-weather").hidden = true; return; }
        fetch(API + "/home/sensors", { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (d) { if (d && d.ok) render(d); }).catch(function () {});
      }
      function loop(on) { if (timer) { clearInterval(timer); timer = null; } if (on) { poll(); timer = setInterval(poll, 10000); } }
      document.addEventListener("visibilitychange", function () { loop(!document.hidden); });
      if (below) new MutationObserver(function () { loop(!document.hidden); }).observe(below, { attributes: true, attributeFilter: ["hidden"] });
      loop(!document.hidden);
    })();
