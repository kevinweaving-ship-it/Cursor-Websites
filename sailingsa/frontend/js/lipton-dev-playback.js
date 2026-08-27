/**
 * Lipton 2026 -dev only. Replay sandbox — not live, not Nett.
 * Rank re-sorts at each mark *pass* (M1 can appear again on lap 2+).
 * Place deltas sit between consecutive passes. Times are mm:ss, no T+.
 * Data: /js/lipton-dev-replay.json
 */
(function () {
  var DATA_URL = "/js/lipton-dev-replay.json?v=20260827ac";
  var TRAIL_URL = "/js/lipton-dev-trail.json?v=20260827ac";

  function pad(n) {
    return n < 10 ? "0" + n : String(n);
  }
  function fmtClock(ms) {
    if (ms < 0) {
      var a = Math.abs(ms);
      var s = Math.floor(a / 1000);
      return "−" + pad(Math.floor(s / 60)) + ":" + pad(s % 60);
    }
    var s2 = Math.floor(ms / 1000);
    return Math.floor(s2 / 60) + ":" + pad(s2 % 60);
  }
  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }
  function watchUrl(data, ts) {
    var q = [];
    if (Number(data.race_day) !== 1) q.push("race-day=" + Number(data.race_day));
    q.push("ts=" + Math.floor(ts));
    return data.watch_path + "?" + q.join("&");
  }
  function asBoats(list) {
    return (list || []).map(function (b) {
      return { boat: b.boat, ts: b.ts_ms != null ? Number(b.ts_ms) : Number(b.ts) };
    });
  }
  function loadPasses(data) {
    if (Array.isArray(data.passes) && data.passes.length) {
      return data.passes.filter(function (p) {
        return p && (p.id === "FIN" || (p.boats && p.boats.length));
      }).map(function (p, i) {
        return {
          id: p.id || ("P" + i),
          label: p.label || ("M" + (p.mark || i + 1)),
          lap: Number(p.lap || 1),
          mark: Number(p.mark || i + 1),
          boats: asBoats(p.boats)
        };
      });
    }
    var labels = data.mark_labels || Object.keys(data.marks || {});
    return labels.map(function (lab, i) {
      var n = parseInt(String(lab).replace(/^M/i, ""), 10);
      if (isNaN(n)) n = i + 1;
      return {
        id: "L1-" + n,
        label: lab,
        lap: 1,
        mark: n,
        boats: asBoats((data.marks || {})[lab])
      };
    });
  }

  Promise.all([
    fetch(DATA_URL, { cache: "no-store" }).then(function (res) {
      if (!res.ok) throw new Error("replay json " + res.status);
      return res.json();
    }),
    fetch(TRAIL_URL, { cache: "no-store" }).then(function (res) {
      if (!res.ok) throw new Error("trail json " + res.status);
      return res.json();
    })
  ])
    .then(function (pair) { start(pair[0], pair[1]); })
    .catch(function (err) {
      var sailed = document.getElementById("lipton-dev-sailed");
      if (sailed) sailed.textContent = "Replay data failed to load";
      console.error(err);
    });

  function start(data, trail) {
    var PASSES = loadPasses(data);
    var BOATS = data.boats || {};
    var GUN_TS = Number(data.gun_ts_ms);
    var PLAY_START_TS = Number(data.play_start_ts_ms);
    var PLAY_END_TS = Number(data.play_end_ts_ms || data.end_ts_ms);
    var FINISH = asBoats(data.finish);
    if (FINISH.length) {
      PASSES.push({
        id: "FIN",
        label: "Fin",
        lap: 0,
        mark: 0,
        boats: FINISH
      });
    }
    var OCS = {};
    (data.ocs || []).forEach(function (name) { OCS[name] = true; });
    var ST_LEAD_TS = null;
    PASSES.forEach(function (p) {
      if ((p.id === "ST" || p.label === "ST") && p.boats.length) {
        for (var si = 0; si < p.boats.length; si++) {
          if (!OCS[p.boats[si].boat]) {
            ST_LEAD_TS = p.boats[si].ts;
            break;
          }
        }
        if (ST_LEAD_TS == null) ST_LEAD_TS = p.boats[0].ts;
      }
    });
    var GUN_CLOCK = String(data.gun_sast || "").slice(11, 19) || "15:50:01";
    var RACE_NO = Number(data.race_number || 5);
    var RACE_LAB = "Race " + RACE_NO;
    var RATE = Number(data.default_rate || 1);
    var SETTLE_MS = 2500;
    var playing = false;
    var trackerReady = false;
    var playTs = PLAY_START_TS;
    var lastWall = Date.now();
    var lastKey = "";
    var seen = {};
    var deltaSeen = {};

    var tbody = document.getElementById("lipton-dev-tbody");
    var clockEl = document.getElementById("lipton-dev-clock");
    var sailedEl = document.getElementById("lipton-dev-sailed");
    var mapEl = document.getElementById("lipton-dev-map");
    var playBtn = document.getElementById("lipton-dev-play");
    var headRow = document.getElementById("lipton-dev-thead-row");
    if (!tbody) return;

    function ident(tracker) {
      return BOATS[tracker] || null;
    }
    function clubCode(sail) {
      var id = ident(sail);
      if (!id) return sail;
      return id.mapClub || id.club || sail;
    }
    function boatNameCell(id) {
      if (!id) return "";
      return "<a href=\"" + esc(id.nameHref) + "\" class=\"rs-boat-name-sponsors rs-boat-name-sponsors--link\" title=\"" + esc(id.title) + "\">" + id.nameInner + "</a>";
    }
    function clubCell(id) {
      if (!id) return "";
      return "<span class=\"rs-club-with-logo\"><a href=\"" + esc(id.clubHref) + "\">" + esc(id.club) + "</a><img class=\"rs-club-row-logo\" src=\"" + esc(id.clubLogo) + "\" alt=\"" + esc(id.club) + "\" title=\"" + esc(id.club) + "\"></span>";
    }
    function bowCell(id) {
      if (!id) return "";
      return "<span class=\"wc-boat-linked\"><a href=\"" + esc(id.boatHref) + "\">" + esc(id.bow) + "</a></span>";
    }
    var mapCtx = null;
    var mapBounds = null;
    function expandBounds(lat, lon, box) {
      if (lat == null || lon == null) return;
      if (lat < box.minLat) box.minLat = lat;
      if (lat > box.maxLat) box.maxLat = lat;
      if (lon < box.minLon) box.minLon = lon;
      if (lon > box.maxLon) box.maxLon = lon;
    }
    function eachSeriesPoint(series, fn) {
      if (!series) return;
      if (typeof series.lat === "number") {
        fn(series.lat, series.lon);
        return;
      }
      var lat = series.lat || [];
      for (var i = 0; i < lat.length; i++) {
        if (lat[i] == null) continue;
        fn(lat[i], series.lon[i]);
      }
    }
    function fitMap() {
      if (!mapEl) return;
      var w = mapEl.clientWidth || 640;
      var h = mapEl.clientHeight || 480;
      var dpr = window.devicePixelRatio || 1;
      mapEl.width = Math.floor(w * dpr);
      mapEl.height = Math.floor(h * dpr);
      mapCtx = mapEl.getContext("2d");
      mapCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
      mapCtx.imageSmoothingEnabled = true;
      mapCtx.imageSmoothingQuality = "high";
      mapCtx.lineJoin = "round";
      mapCtx.lineCap = "round";
      var box = { minLat: 90, maxLat: -90, minLon: 180, maxLon: -180 };
      Object.keys(trail.boats || {}).forEach(function (sail) {
        eachSeriesPoint(trail.boats[sail], function (lat, lon) { expandBounds(lat, lon, box); });
      });
      Object.keys(trail.marks || {}).forEach(function (k) {
        eachSeriesPoint(trail.marks[k], function (lat, lon) { expandBounds(lat, lon, box); });
      });
      ["start_line", "finish_line"].forEach(function (key) {
        var ln = trail[key];
        if (!ln) return;
        if (ln.left) expandBounds(ln.left.lat, ln.left.lon, box);
        if (ln.right) expandBounds(ln.right.lat, ln.right.lon, box);
      });
      var midLat = (box.minLat + box.maxLat) / 2;
      var midLon = (box.minLon + box.maxLon) / 2;
      var cos = Math.cos(midLat * Math.PI / 180);
      var heightM = (box.maxLat - box.minLat) * 111000;
      var widthM = (box.maxLon - box.minLon) * 111000 * cos;
      if (heightM < 200) heightM = 200;
      if (widthM < 200) widthM = 200;
      var scale = Math.min(w / (widthM * 1.16), h / (heightM * 1.16));
      mapBounds = { w: w, h: h, midLat: midLat, midLon: midLon, cos: cos, scale: scale };
    }
    function xy(lat, lon) {
      var b = mapBounds;
      return {
        x: (lon - b.midLon) * 111000 * b.cos * b.scale + b.w / 2,
        y: -(lat - b.midLat) * 111000 * b.scale + b.h / 2
      };
    }
    var lastHdg = {};
    function sampleAt(series, ts) {
      if (!series) return null;
      if (typeof series.lat === "number") return { lat: series.lat, lon: series.lon, i: 0, j: 0 };
      var t = (ts - trail.gun_ts_ms) / trail.step_ms;
      var i = Math.floor(t);
      if (i < 0) i = 0;
      if (i >= series.lat.length) i = series.lat.length - 1;
      while (i >= 0 && series.lat[i] == null) i -= 1;
      if (i < 0) return null;
      var j = i + 1;
      var maxJ = Math.min(series.lat.length, i + 3);
      while (j < maxJ && series.lat[j] == null) j += 1;
      if (j < maxJ && series.lat[j] != null) {
        var f = (t - i) / (j - i);
        if (f < 0) f = 0;
        if (f > 1) f = 1;
        return {
          lat: series.lat[i] + (series.lat[j] - series.lat[i]) * f,
          lon: series.lon[i] + (series.lon[j] - series.lon[i]) * f,
          i: i,
          j: j
        };
      }
      return { lat: series.lat[i], lon: series.lon[i], i: i, j: i };
    }
    function headingAt(b, sample) {
      if (!b || !sample) return 0;
      var i = sample.i;
      var j = sample.j;
      if (j != null && j > i && b.lat[j] != null && b.lat[i] != null) {
        return Math.atan2(b.lon[j] - b.lon[i], b.lat[j] - b.lat[i]) * 180 / Math.PI;
      }
      var k = i - 1;
      while (k >= 0 && b.lat[k] == null) k -= 1;
      if (k < 0 || b.lat[i] == null) return 0;
      return Math.atan2(b.lon[i] - b.lon[k], b.lat[i] - b.lat[k]) * 180 / Math.PI;
    }
    function blendHdg(sail, target) {
      if (target == null || isNaN(target)) return lastHdg[sail] || 0;
      var prev = lastHdg[sail];
      if (prev == null) {
        lastHdg[sail] = target;
        return target;
      }
      var d = target - prev;
      while (d > 180) d -= 360;
      while (d < -180) d += 360;
      var k = playing ? Math.min(1, 0.28 + RATE / 70) : 1;
      var out = prev + d * k;
      lastHdg[sail] = out;
      return out;
    }
    function posAt(sail, ts) {
      var b = trail.boats[sail];
      var pos = sampleAt(b, ts);
      if (!pos) return null;
      pos.hdg = blendHdg(sail, headingAt(b, pos));
      return pos;
    }
    function markAt(k, ts) {
      return sampleAt(trail.marks[k], ts);
    }
    function metersPx(m) {
      return Math.max(4, m * mapBounds.scale);
    }
    function drawBoatIcon(p, hdg, ocs) {
      mapCtx.save();
      mapCtx.translate(p.x, p.y);
      mapCtx.rotate((hdg || 0) * Math.PI / 180);
      mapCtx.lineJoin = "round";
      mapCtx.lineCap = "round";
      mapCtx.beginPath();
      mapCtx.moveTo(0, -5.6);
      mapCtx.quadraticCurveTo(2.4, -0.8, 2.2, 3.8);
      mapCtx.lineTo(-2.2, 3.8);
      mapCtx.quadraticCurveTo(-2.4, -0.8, 0, -5.6);
      mapCtx.closePath();
      mapCtx.fillStyle = ocs ? "#b42318" : "#0b1b33";
      mapCtx.fill();
      mapCtx.strokeStyle = ocs ? "#fecaca" : "#f8fafc";
      mapCtx.lineWidth = 0.7;
      mapCtx.stroke();
      mapCtx.beginPath();
      mapCtx.moveTo(0.15, 2.6);
      mapCtx.lineTo(0.15, -4.6);
      mapCtx.lineTo(3.8, 1.2);
      mapCtx.closePath();
      mapCtx.fillStyle = ocs ? "#fecaca" : "#ffffff";
      mapCtx.fill();
      mapCtx.beginPath();
      mapCtx.moveTo(-0.15, 1.8);
      mapCtx.lineTo(-0.15, -3.2);
      mapCtx.lineTo(-2.4, 0.8);
      mapCtx.closePath();
      mapCtx.fillStyle = ocs ? "#f87171" : "#cbd5e1";
      mapCtx.fill();
      mapCtx.restore();
    }
    function strokeTrack(series, ts, fromIdx, stroke, width) {
      if (!series || !series.lat) return;
      var t = Math.floor((ts - trail.gun_ts_ms) / trail.step_ms);
      if (t < 0) return;
      mapCtx.beginPath();
      var lastI = -999;
      var any = false;
      for (var i = fromIdx; i <= t && i < series.lat.length; i++) {
        if (series.lat[i] == null) continue;
        var p = xy(series.lat[i], series.lon[i]);
        if (!any || i - lastI > 1) mapCtx.moveTo(p.x, p.y);
        else mapCtx.lineTo(p.x, p.y);
        lastI = i;
        any = true;
      }
      if (!any) return;
      mapCtx.strokeStyle = stroke;
      mapCtx.lineWidth = width;
      mapCtx.stroke();
    }
    function drawGate(line, color, label, pinLabel, rcLabel) {
      if (!line || !line.left || !line.right) return;
      var a = xy(line.left.lat, line.left.lon);
      var b = xy(line.right.lat, line.right.lon);
      mapCtx.beginPath();
      mapCtx.moveTo(a.x, a.y);
      mapCtx.lineTo(b.x, b.y);
      mapCtx.strokeStyle = color;
      mapCtx.lineWidth = 2.4;
      mapCtx.setLineDash([7, 4]);
      mapCtx.stroke();
      mapCtx.setLineDash([]);
      mapCtx.beginPath();
      mapCtx.arc(a.x, a.y, 4, 0, Math.PI * 2);
      mapCtx.fillStyle = color;
      mapCtx.fill();
      mapCtx.fillStyle = "#e2e8f0";
      mapCtx.font = "bold 9px sans-serif";
      mapCtx.fillRect(b.x - 7, b.y - 5, 14, 10);
      mapCtx.strokeStyle = color;
      mapCtx.lineWidth = 1;
      mapCtx.strokeRect(b.x - 7, b.y - 5, 14, 10);
      mapCtx.fillStyle = "#0b1b33";
      mapCtx.fillText(rcLabel || "RC", b.x - 6, b.y + 3);
      mapCtx.fillStyle = "#ffffff";
      mapCtx.font = "bold 10px sans-serif";
      mapCtx.fillText(pinLabel || "Pin", a.x + 6, a.y - 6);
      mapCtx.fillText(label, (a.x + b.x) / 2 + 6, (a.y + b.y) / 2 - 6);
    }
    function drawMap(ts) {
      if (!mapCtx || !mapBounds) return;
      var w = mapBounds.w;
      var h = mapBounds.h;
      mapCtx.fillStyle = "#001f3f";
      mapCtx.fillRect(0, 0, w, h);
      var zone = metersPx(20.1);
      Object.keys(trail.marks || {}).forEach(function (k) {
        var pos = markAt(k, ts);
        if (!pos) return;
        var p = xy(pos.lat, pos.lon);
        mapCtx.beginPath();
        mapCtx.arc(p.x, p.y, zone, 0, Math.PI * 2);
        mapCtx.strokeStyle = "rgba(245,158,11,0.4)";
        mapCtx.lineWidth = 1;
        mapCtx.stroke();
        mapCtx.beginPath();
        mapCtx.arc(p.x, p.y, 4, 0, Math.PI * 2);
        mapCtx.fillStyle = "#f59e0b";
        mapCtx.fill();
        mapCtx.fillStyle = "#ffffff";
        mapCtx.font = "bold 11px sans-serif";
        mapCtx.fillText("M" + k, p.x + 8, p.y + 4);
      });
      Object.keys(trail.boats || {}).forEach(function (sail) {
        var t = Math.floor((ts - trail.gun_ts_ms) / trail.step_ms);
        strokeTrack(trail.boats[sail], ts, 0, OCS[sail] ? "rgba(239,68,68,0.16)" : "rgba(148,163,184,0.18)", 1);
        strokeTrack(trail.boats[sail], ts, Math.max(0, t - 90), OCS[sail] ? "rgba(252,165,165,0.7)" : "rgba(248,250,252,0.55)", 1.6);
      });
      drawGate(trail.start_line, "#38bdf8", "START", "Pin", "RC");
      drawGate(trail.finish_line, "#fbbf24", "FINISH", "Pin", "RC");
      Object.keys(trail.boats || {}).forEach(function (sail) {
        var pos = posAt(sail, ts);
        if (!pos) return;
        var p = xy(pos.lat, pos.lon);
        drawBoatIcon(p, pos.hdg, OCS[sail]);
        mapCtx.fillStyle = OCS[sail] ? "#fecaca" : "#e2e8f0";
        mapCtx.font = "bold 8px sans-serif";
        mapCtx.fillText(clubCode(sail), p.x + 6, p.y - 6);
      });
    }
    function setRateButtons() {
      [].forEach.call(document.querySelectorAll("[data-rate]"), function (btn) {
        btn.classList.toggle("is-active", Number(btn.getAttribute("data-rate")) === RATE);
        btn.disabled = !trackerReady;
      });
    }
    function setPlayLabel() {
      if (!playBtn) return;
      if (!trackerReady) {
        playBtn.disabled = true;
        playBtn.textContent = "Wait";
        return;
      }
      playBtn.disabled = false;
      playBtn.textContent = playing ? "Pause" : "Play";
    }
    function fillHead() {
      if (!headRow) return;
      var html = "<th class=\"rank-col\">Rank</th><th class=\"wc-meta-col\">Bow</th><th class=\"boat-name-col\">Boat</th><th class=\"club-col\">Club</th>";
      for (var i = 0; i < PASSES.length; i++) {
        var p = PASSES[i];
        var title = "Lap " + p.lap + " mark " + p.mark;
        if (p.id === "FIN" || p.label === "Fin") title = "Finish";
        else if (p.id === "ST" || p.label === "ST") title = "Seconds after first boat over the start line. OCS if recalled.";
        html += "<th class=\"timer-col\" title=\"" + esc(title) + "\">" + esc(p.label) + "</th>";
        if (i < PASSES.length - 1) {
          var nlab = PASSES[i + 1].label;
          html += "<th class=\"place-delta-col\" title=\"Places gained or lost " + esc(p.label) + " to " + esc(nlab) + "\" aria-label=\"Place change " + esc(p.label) + " to " + esc(nlab) + "\">±</th>";
        }
      }
      headRow.innerHTML = html;
    }
    function tsAtPass(pass, boat) {
      for (var i = 0; i < pass.boats.length; i++) {
        if (pass.boats[i].boat === boat) return pass.boats[i].ts;
      }
      return null;
    }
    function boatTimes(boat, ts) {
      var out = [];
      for (var i = 0; i < PASSES.length; i++) {
        var t = tsAtPass(PASSES[i], boat);
        out.push(t != null && t <= ts ? t : null);
      }
      return out;
    }
    function furthest(times) {
      var k = -1;
      for (var i = 0; i < times.length; i++) {
        if (times[i] != null) k = i;
      }
      if (k < 0) return { idx: -1, lab: null, ts: null, lap: 1 };
      var p = PASSES[k];
      return { idx: k, lab: p.label, ts: times[k], lap: p.lap };
    }
    function finishTs(boat) {
      for (var i = 0; i < FINISH.length; i++) {
        if (FINISH[i].boat === boat) return FINISH[i].ts;
      }
      return null;
    }
    function finCell(r, ts) {
      var ft = finishTs(r.boat);
      if (ft != null && ft <= ts) return fmtClock(ft - GUN_TS);
      return "";
    }
    function fmtBehindFirst(t) {
      if (ST_LEAD_TS == null) return "";
      var sec = (t - ST_LEAD_TS) / 1000;
      if (sec <= -0.05) return sec.toFixed(1);
      if (sec < 0.05) return "0.0";
      return "+" + sec.toFixed(1);
    }
    function splitCell(times, i, boat) {
      var t = times[i];
      if (t == null) return "";
      if (PASSES[i] && (PASSES[i].id === "ST" || PASSES[i].label === "ST")) {
        var gap = fmtBehindFirst(t);
        if (OCS[boat]) return "OCS " + gap;
        return gap;
      }
      if (PASSES[i] && (PASSES[i].id === "FIN" || PASSES[i].label === "Fin")) {
        return fmtClock(t - GUN_TS);
      }
      var prev = GUN_TS;
      for (var j = i - 1; j >= 0; j--) {
        if (times[j] != null) {
          prev = times[j];
          break;
        }
      }
      return fmtClock(t - prev);
    }
    function pairRankMaps(ts) {
      var out = [];
      for (var i = 0; i < PASSES.length - 1; i++) {
        var a = PASSES[i];
        var b = PASSES[i + 1];
        var both = {};
        for (var x = 0; x < a.boats.length; x++) {
          if (a.boats[x].ts > ts) continue;
          var t2 = tsAtPass(b, a.boats[x].boat);
          if (t2 != null && t2 <= ts) both[a.boats[x].boat] = true;
        }
        function rankOf(pass) {
          var hit = [];
          for (var k = 0; k < pass.boats.length; k++) {
            if (both[pass.boats[k].boat] && pass.boats[k].ts <= ts) hit.push(pass.boats[k]);
          }
          hit.sort(function (p, q) { return p.ts - q.ts; });
          var map = {};
          for (var n = 0; n < hit.length; n++) map[hit[n].boat] = n + 1;
          return map;
        }
        out.push({ prev: rankOf(a), next: rankOf(b) });
      }
      return out;
    }
    function deltaCell(boat, passIdx, prevMap, nextMap) {
      if (!prevMap || !nextMap) return "<td class=\"place-delta-col\"></td>";
      var prev = prevMap[boat];
      var next = nextMap[boat];
      if (prev == null || next == null) return "<td class=\"place-delta-col\"></td>";
      var gained = prev - next;
      var key = boat + "|" + passIdx;
      var flash = deltaSeen[key] !== gained;
      deltaSeen[key] = gained;
      var flashCls = flash && gained !== 0 ? " place-delta--flash" : "";
      if (gained > 0) {
        return "<td class=\"place-delta-col\"><span class=\"place-delta place-delta--up" + flashCls + "\" title=\"Gained " + gained + "\" aria-label=\"Gained " + gained + "\">▲" + gained + "</span></td>";
      }
      if (gained < 0) {
        var lost = -gained;
        return "<td class=\"place-delta-col\"><span class=\"place-delta place-delta--down" + flashCls + "\" title=\"Lost " + lost + "\" aria-label=\"Lost " + lost + "\">▼" + lost + "</span></td>";
      }
      return "<td class=\"place-delta-col\"><span class=\"place-delta place-delta--same\" title=\"No change\" aria-label=\"No change\">■0</span></td>";
    }
    function rowsAt(ts) {
      var names = {};
      PASSES.forEach(function (pass) {
        pass.boats.forEach(function (b) {
          if (b.ts <= ts) names[b.boat] = true;
        });
      });
      var rows = Object.keys(names).map(function (boat) {
        var times = boatTimes(boat, ts);
        var far = furthest(times);
        return {
          boat: boat,
          times: times,
          farIdx: far.idx,
          farTs: far.ts,
          farLab: far.lab,
          farLap: far.lap
        };
      });
      rows.sort(function (a, b) {
        if (b.farIdx !== a.farIdx) return b.farIdx - a.farIdx;
        return a.farTs - b.farTs;
      });
      rows.forEach(function (r, i) { r.rank = i + 1; });
      return rows;
    }
    function leadMark(rows) {
      return rows.length ? rows[0].farLab : null;
    }
    function stateKey(rows) {
      return rows.map(function (r) { return r.rank + ":" + r.boat + ":" + r.farIdx; }).join("|");
    }
    function rowHtml(r, unroll, rankMaps) {
      var id = ident(r.boat);
      var medal = r.rank === 1 ? " medal-gold" : r.rank === 2 ? " medal-silver" : r.rank === 3 ? " medal-bronze" : "";
      var cls = medal + (unroll ? " lipton-unroll" : "");
      var html = "<tr class=\"" + cls + "\" data-bow=\"" + esc(id ? id.bow : "") + "\" data-boat=\"" + esc(r.boat) + "\">";
      html += "<td class=\"rank-col\">" + r.rank + "</td>";
      html += "<td class=\"wc-meta-col\">" + bowCell(id) + "</td>";
      html += "<td class=\"boat-name-col\">" + boatNameCell(id) + "</td>";
      html += "<td class=\"club-col\">" + clubCell(id) + "</td>";
      for (var i = 0; i < PASSES.length; i++) {
        html += "<td class=\"timer-col\">" + splitCell(r.times, i, r.boat) + "</td>";
        if (i < PASSES.length - 1) {
          html += deltaCell(r.boat, i, rankMaps[i].prev, rankMaps[i].next);
        }
      }
      html += "</tr>";
      return html;
    }
    function setSailed(rows) {
      if (!sailedEl) return;
      if (!rows.length) {
        sailedEl.textContent = "Race " + RACE_NO + " · gun " + GUN_CLOCK + " · approaching start";
        return;
      }
      var lead = rows[0];
      var n = 0;
      rows.forEach(function (r) { if (r.farIdx === lead.farIdx) n += 1; });
      var tot = PASSES[lead.farIdx] ? PASSES[lead.farIdx].boats.length : n;
      var p = PASSES[lead.farIdx];
      var isFin = p && (p.id === "FIN" || p.label === "Fin");
      var isSt = p && (p.id === "ST" || p.label === "ST");
      var lapBit = !isFin && !isSt && lead.farLap > 1 ? " · lap " + lead.farLap : "";
      var ocsBit = isSt && Object.keys(OCS).length ? " · OCS " + Object.keys(OCS).join(",") : "";
      var rankLab = isSt ? "start" : lead.farLab;
      sailedEl.textContent = (isSt ? RACE_LAB + " · gun " + GUN_CLOCK : RACE_LAB + " replay") + " · " + lead.farLab + lapBit + " · " + n + " of " + tot + " · rank by " + rankLab + ocsBit;
    }
    function clockText(ts, rows) {
      var clock = fmtClock(ts - GUN_TS);
      if (!rows.length) return clock + " → start";
      return clock;
    }
    function render(ts) {
      var rows = rowsAt(ts);
      var rankMaps = pairRankMaps(ts);
      var html = "";
      for (var i = 0; i < rows.length; i++) {
        var first = !seen[rows[i].boat];
        seen[rows[i].boat] = true;
        html += rowHtml(rows[i], first, rankMaps);
      }
      tbody.innerHTML = html;
      if (clockEl) clockEl.textContent = clockText(ts, rows);
      setSailed(rows);
      lastKey = stateKey(rows);
      drawMap(ts);
    }

    function jump(ts) {
      playTs = ts;
      lastWall = Date.now();
      lastKey = "";
      seen = {};
      deltaSeen = {};
      render(ts);
    }

    function tick() {
      if (playing && trackerReady) {
        var now = Date.now();
        playTs += (now - lastWall) * RATE;
        lastWall = now;
        if (playTs > PLAY_END_TS) {
          playTs = PLAY_END_TS;
          playing = false;
          setPlayLabel();
        }
        var rows = rowsAt(playTs);
        var key = stateKey(rows);
        if (key !== lastKey) {
          render(playTs);
        } else if (clockEl) {
          clockEl.textContent = clockText(playTs, rows);
        }
        drawMap(playTs);
      } else {
        lastWall = Date.now();
      }
      window.requestAnimationFrame(tick);
    }

    function beginAfterTracker() {
      if (trackerReady) return;
      trackerReady = true;
      playTs = PLAY_START_TS;
      lastWall = Date.now();
      playing = false;
      fitMap();
      setPlayLabel();
      setRateButtons();
      render(playTs);
      if (sailedEl) sailedEl.textContent = RACE_LAB + " · gun " + GUN_CLOCK + " · press Play";
    }

    function waitForTracker() {
      if (sailedEl) sailedEl.textContent = "Loading GPS trail…";
      setPlayLabel();
      setRateButtons();
      beginAfterTracker();
    }

    document.querySelectorAll("[data-jump]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var key = btn.getAttribute("data-jump");
        var ts = key === "gun" ? GUN_TS : key === "finish" ? (FINISH[0] ? FINISH[0].ts : PLAY_START_TS) : PLAY_START_TS;
        if (!ts) return;
        jump(ts);
      });
    });
    document.querySelectorAll("[data-rate]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (!trackerReady) return;
        RATE = Number(btn.getAttribute("data-rate")) || 1;
        lastWall = Date.now();
        setRateButtons();
      });
    });
    if (playBtn) {
      playBtn.addEventListener("click", function () {
        if (!trackerReady) return;
        playing = !playing;
        lastWall = Date.now();
        setPlayLabel();
      });
    }

    window.addEventListener("resize", function () {
      fitMap();
      drawMap(playTs);
    });

    fillHead();
    setRateButtons();
    waitForTracker();
    window.requestAnimationFrame(tick);
  }
})();
