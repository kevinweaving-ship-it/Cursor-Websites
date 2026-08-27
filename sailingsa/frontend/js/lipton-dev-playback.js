/**
 * Lipton 2026 -dev only. Replay sandbox — not live, not Nett.
 * Rank re-sorts at each mark *pass* (M1 can appear again on lap 2+).
 * Place deltas sit between consecutive passes. Times are mm:ss, no T+.
 * Data: /js/lipton-dev-replay.json
 */
(function () {
  var DATA_URL = "/js/lipton-dev-replay.json?v=20260827af";
  var TRAIL_URL = "/js/lipton-dev-trail.json?v=20260827af";

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
    var cam = null;
    function expandBounds(lat, lon, box) {
      if (lat == null || lon == null) return;
      if (lat < box.minLat) box.minLat = lat;
      if (lat > box.maxLat) box.maxLat = lat;
      if (lon < box.minLon) box.minLon = lon;
      if (lon > box.maxLon) box.maxLon = lon;
    }
    function distM(a, b) {
      var c = Math.cos(((a.lat + b.lat) / 2) * Math.PI / 180);
      var y = (a.lat - b.lat) * 111000;
      var x = (a.lon - b.lon) * 111000 * c;
      return Math.sqrt(x * x + y * y);
    }
    var BOAT_LEN_M = 6.71;
    var TAIL_M = BOAT_LEN_M * 10;
    var focusMarkKey = null;
    var focusGate = null;
    function sizeCanvas() {
      if (!mapEl) return;
      var w = mapEl.clientWidth || 640;
      var h = mapEl.clientHeight || 480;
      var dpr = window.devicePixelRatio || 1;
      var needW = Math.floor(w * dpr);
      var needH = Math.floor(h * dpr);
      if (!mapCtx || mapEl.width !== needW || mapEl.height !== needH) {
        mapEl.width = needW;
        mapEl.height = needH;
        mapCtx = mapEl.getContext("2d");
      }
      mapCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
      mapCtx.imageSmoothingEnabled = true;
      mapCtx.imageSmoothingQuality = "high";
      mapCtx.lineJoin = "round";
      mapCtx.lineCap = "round";
      if (!mapBounds) {
        mapBounds = { w: w, h: h, midLat: -33.87, midLon: 18.46, cos: Math.cos(-33.87 * Math.PI / 180), scale: 0.2 };
      } else {
        mapBounds.w = w;
        mapBounds.h = h;
      }
    }
    function boundsFromPts(pts, w, h) {
      var box = { minLat: 90, maxLat: -90, minLon: 180, maxLon: -180 };
      pts.forEach(function (p) { expandBounds(p.lat, p.lon, box); });
      var midLat = (box.minLat + box.maxLat) / 2;
      var midLon = (box.minLon + box.maxLon) / 2;
      var cos = Math.cos(midLat * Math.PI / 180);
      var heightM = (box.maxLat - box.minLat) * 111000;
      var widthM = (box.maxLon - box.minLon) * 111000 * cos;
      if (heightM < 320) heightM = 320;
      if (widthM < 320) widthM = 320;
      var scale = Math.min(w / (widthM * 1.22), h / (heightM * 1.22));
      return { w: w, h: h, midLat: midLat, midLon: midLon, cos: cos, scale: scale };
    }
    function countPassed(pass, ts) {
      var n = 0;
      for (var i = 0; i < pass.boats.length; i++) {
        if (pass.boats[i].ts <= ts) n += 1;
      }
      return n;
    }
    function focusForFleet(ts, fleet) {
      var lastKey = null;
      var nextKey = null;
      var lastGate = null;
      var nextGate = null;
      var onWater = 0;
      Object.keys(trail.boats || {}).forEach(function (sail) {
        if (sampleAt(trail.boats[sail], ts)) onWater += 1;
      });
      for (var i = 0; i < PASSES.length; i++) {
        var p = PASSES[i];
        var n = countPassed(p, ts);
        if (p.id === "ST" || p.label === "ST") {
          if (n > 0) lastGate = "start_line";
          continue;
        }
        if (p.id === "FIN" || p.label === "Fin") {
          if (n > 0) lastGate = "finish_line";
          if (n < onWater) nextGate = "finish_line";
          continue;
        }
        var key = String(p.mark);
        if (n > 0) lastKey = key;
        if (n < onWater) {
          nextKey = key;
          break;
        }
      }
      var lastPos = lastKey ? markAt(lastKey, ts) : null;
      var nextPos = nextKey ? markAt(nextKey, ts) : null;
      var pickKey = null;
      var pickGate = null;
      function gateMid(name) {
        var ln = trail[name];
        if (!ln || !ln.left || !ln.right) return null;
        return { lat: (ln.left.lat + ln.right.lat) / 2, lon: (ln.left.lon + ln.right.lon) / 2 };
      }
      var candidates = [];
      if (lastPos) candidates.push({ mark: lastKey, pos: lastPos });
      if (nextPos && nextKey !== lastKey) candidates.push({ mark: nextKey, pos: nextPos });
      if (!lastKey && trail.start_line) {
        var sm = gateMid("start_line");
        if (sm) candidates.push({ gate: "start_line", pos: sm });
      }
      if (nextGate === "finish_line" || lastGate === "finish_line") {
        var fm = gateMid("finish_line");
        if (fm) candidates.push({ gate: "finish_line", pos: fm });
      }
      if (!candidates.length && trail.start_line) {
        pickGate = "start_line";
      } else if (candidates.length) {
        var best = candidates[0];
        var bestD = distM(fleet, best.pos);
        for (var c = 1; c < candidates.length; c++) {
          var d = distM(fleet, candidates[c].pos);
          if (d < bestD) { best = candidates[c]; bestD = d; }
        }
        pickKey = best.mark || null;
        pickGate = best.gate || null;
      }
      return { mark: pickKey, gate: pickGate };
    }
    function frameCam(ts) {
      sizeCanvas();
      if (!mapEl) return;
      var w = mapEl.clientWidth || 640;
      var h = mapEl.clientHeight || 480;
      var pts = [];
      Object.keys(trail.boats || {}).forEach(function (sail) {
        var pos = sampleAt(trail.boats[sail], ts);
        if (pos) pts.push(pos);
      });
      if (!pts.length) return;
      var cx = 0;
      var cy = 0;
      pts.forEach(function (p) { cx += p.lat; cy += p.lon; });
      var fleet = { lat: cx / pts.length, lon: cy / pts.length };
      var focus = focusForFleet(ts, fleet);
      focusMarkKey = focus.mark;
      focusGate = focus.gate;
      if (focus.mark) {
        var mk = markAt(focus.mark, ts);
        if (mk) pts.push(mk);
      }
      if (focus.gate && trail[focus.gate]) {
        var ln = trail[focus.gate];
        if (ln.left) pts.push(ln.left);
        if (ln.right) pts.push(ln.right);
      }
      var target = boundsFromPts(pts, w, h);
      if (!cam) {
        cam = target;
      } else {
        var a = playing ? Math.min(1, 0.16 + RATE / 70) : 1;
        cam.midLat += (target.midLat - cam.midLat) * a;
        cam.midLon += (target.midLon - cam.midLon) * a;
        cam.scale += (target.scale - cam.scale) * a;
        cam.cos = Math.cos(cam.midLat * Math.PI / 180);
        cam.w = w;
        cam.h = h;
      }
      mapBounds = cam;
    }
    function xy(lat, lon) {
      var b = mapBounds;
      return {
        x: (lon - b.midLon) * 111000 * b.cos * b.scale + b.w / 2,
        y: -(lat - b.midLat) * 111000 * b.scale + b.h / 2
      };
    }
    var lastHdg = {};
    var lastPosEase = {};
    function hitBack(series, i) {
      var k = i;
      while (k >= 0 && series.lat[k] == null) k -= 1;
      return k;
    }
    function hitFwd(series, i) {
      var k = i;
      while (k < series.lat.length && series.lat[k] == null) k += 1;
      return k < series.lat.length ? k : -1;
    }
    function ptAt(series, i) {
      if (i < 0 || !series || series.lat[i] == null) return null;
      return { lat: series.lat[i], lon: series.lon[i], i: i };
    }
    function catmull(p0, p1, p2, p3, t) {
      var t2 = t * t;
      var t3 = t2 * t;
      function axis(a, b, c, d) {
        return 0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
      }
      return {
        lat: axis(p0.lat, p1.lat, p2.lat, p3.lat),
        lon: axis(p0.lon, p1.lon, p2.lon, p3.lon)
      };
    }
    function sampleAt(series, ts) {
      if (!series) return null;
      if (typeof series.lat === "number") return { lat: series.lat, lon: series.lon, i: 0, j: 0 };
      var t = (ts - trail.gun_ts_ms) / trail.step_ms;
      var i = hitBack(series, Math.min(series.lat.length - 1, Math.max(0, Math.floor(t))));
      if (i < 0) {
        var fwd = hitFwd(series, 0);
        if (fwd < 0) return null;
        return { lat: series.lat[fwd], lon: series.lon[fwd], i: fwd, j: fwd };
      }
      var j = hitFwd(series, i + 1);
      if (j < 0 || j - i > 2) {
        return { lat: series.lat[i], lon: series.lon[i], i: i, j: i };
      }
      var f = (t - i) / (j - i);
      if (f < 0) f = 0;
      if (f > 1) f = 1;
      var p0 = ptAt(series, hitBack(series, i - 1)) || ptAt(series, i);
      var p1 = ptAt(series, i);
      var p2 = ptAt(series, j);
      var p3 = ptAt(series, hitFwd(series, j + 1)) || p2;
      var cr = catmull(p0, p1, p2, p3, f);
      cr.i = i;
      cr.j = j;
      return cr;
    }
    function headingAt(b, sample) {
      if (!b || !sample) return 0;
      if (sample.j != null && sample.j > sample.i && b.lat[sample.j] != null && b.lat[sample.i] != null) {
        return Math.atan2(b.lon[sample.j] - b.lon[sample.i], b.lat[sample.j] - b.lat[sample.i]) * 180 / Math.PI;
      }
      var k = hitBack(b, sample.i - 1);
      if (k < 0) return 0;
      return Math.atan2(b.lon[sample.i] - b.lon[k], b.lat[sample.i] - b.lat[k]) * 180 / Math.PI;
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
      var k = playing ? Math.min(1, 0.18 + RATE / 55) : 1;
      var out = prev + d * k;
      lastHdg[sail] = out;
      return out;
    }
    function easePos(sail, pos) {
      if (!pos) return null;
      var prev = lastPosEase[sail];
      if (!prev || !playing) {
        lastPosEase[sail] = { lat: pos.lat, lon: pos.lon };
        return pos;
      }
      if (distM(prev, pos) > 45) {
        lastPosEase[sail] = { lat: pos.lat, lon: pos.lon };
        return pos;
      }
      var k = Math.min(1, 0.2 + RATE / 50);
      var out = {
        lat: prev.lat + (pos.lat - prev.lat) * k,
        lon: prev.lon + (pos.lon - prev.lon) * k,
        i: pos.i,
        j: pos.j,
        hdg: pos.hdg
      };
      lastPosEase[sail] = { lat: out.lat, lon: out.lon };
      return out;
    }
    function posAt(sail, ts) {
      var b = trail.boats[sail];
      var pos = sampleAt(b, ts);
      if (!pos) return null;
      pos = easePos(sail, pos);
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
    function tailHits(b, ts) {
      var now = sampleAt(b, ts);
      if (!now) return [];
      var hits = [now];
      var acc = 0;
      var idx = hitBack(b, Math.floor((ts - trail.gun_ts_ms) / trail.step_ms) - 1);
      var lastI = now.i != null ? now.i : Math.floor((ts - trail.gun_ts_ms) / trail.step_ms);
      while (idx >= 0) {
        if (lastI - idx > 2) break;
        var cur = { lat: b.lat[idx], lon: b.lon[idx], i: idx };
        acc += distM(hits[hits.length - 1], cur);
        hits.push(cur);
        if (acc >= TAIL_M) break;
        lastI = idx;
        idx = hitBack(b, idx - 1);
      }
      hits.reverse();
      if (hits.length < 2) return hits;
      var dense = [];
      for (var s = 0; s < hits.length - 1; s++) {
        var a = hits[s];
        var c = hits[s + 1];
        var p0 = hits[s - 1] || a;
        var p3 = hits[s + 2] || c;
        dense.push(a);
        var steps = 5;
        for (var u = 1; u < steps; u++) dense.push(catmull(p0, a, c, p3, u / steps));
      }
      dense.push(hits[hits.length - 1]);
      return dense;
    }
    function drawTail(sail, ts) {
      var b = trail.boats[sail];
      if (!b) return;
      var hits = tailHits(b, ts);
      if (hits.length < 2) return;
      var screen = hits.map(function (pt) { return xy(pt.lat, pt.lon); });
      var left = [];
      var right = [];
      for (var i = 0; i < screen.length; i++) {
        var dx, dy;
        if (i === 0) {
          dx = screen[1].x - screen[0].x;
          dy = screen[1].y - screen[0].y;
        } else if (i === screen.length - 1) {
          dx = screen[i].x - screen[i - 1].x;
          dy = screen[i].y - screen[i - 1].y;
        } else {
          dx = screen[i + 1].x - screen[i - 1].x;
          dy = screen[i + 1].y - screen[i - 1].y;
        }
        var len = Math.sqrt(dx * dx + dy * dy) || 1;
        var nx = -dy / len;
        var ny = dx / len;
        var along = i / (screen.length - 1);
        var w = 0.35 + along * along * 3.1;
        left.push({ x: screen[i].x + nx * w, y: screen[i].y + ny * w });
        right.push({ x: screen[i].x - nx * w, y: screen[i].y - ny * w });
      }
      mapCtx.beginPath();
      mapCtx.moveTo(left[0].x, left[0].y);
      for (var L = 1; L < left.length; L++) mapCtx.lineTo(left[L].x, left[L].y);
      for (var R = right.length - 1; R >= 0; R--) mapCtx.lineTo(right[R].x, right[R].y);
      mapCtx.closePath();
      mapCtx.fillStyle = OCS[sail] ? "rgba(252,165,165,0.22)" : "rgba(226,232,240,0.22)";
      mapCtx.fill();
      mapCtx.beginPath();
      mapCtx.moveTo(screen[0].x, screen[0].y);
      for (var s = 1; s < screen.length; s++) mapCtx.lineTo(screen[s].x, screen[s].y);
      mapCtx.strokeStyle = OCS[sail] ? "rgba(254,202,202,0.7)" : "rgba(248,250,252,0.7)";
      mapCtx.lineWidth = 1.15;
      mapCtx.lineJoin = "round";
      mapCtx.lineCap = "round";
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
      frameCam(ts);
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
        var focus = k === focusMarkKey;
        mapCtx.beginPath();
        mapCtx.arc(p.x, p.y, zone, 0, Math.PI * 2);
        mapCtx.strokeStyle = focus ? "rgba(251,191,36,0.7)" : "rgba(245,158,11,0.28)";
        mapCtx.lineWidth = focus ? 2 : 1;
        mapCtx.stroke();
        mapCtx.beginPath();
        mapCtx.arc(p.x, p.y, focus ? 5 : 3.5, 0, Math.PI * 2);
        mapCtx.fillStyle = focus ? "#fbbf24" : "#f59e0b";
        mapCtx.fill();
        mapCtx.fillStyle = "#ffffff";
        mapCtx.font = focus ? "bold 12px sans-serif" : "bold 10px sans-serif";
        mapCtx.fillText("M" + k, p.x + 8, p.y + 4);
      });
      Object.keys(trail.boats || {}).forEach(function (sail) {
        drawTail(sail, ts);
      });
      drawGate(trail.start_line, focusGate === "start_line" ? "#38bdf8" : "rgba(56,189,248,0.4)", "START", "Pin", "RC");
      drawGate(trail.finish_line, focusGate === "finish_line" ? "#fbbf24" : "rgba(251,191,36,0.35)", "FINISH", "Pin", "RC");
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
      lastHdg = {};
      lastPosEase = {};
      cam = null;
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
      frameCam(playTs);
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
      cam = null;
      frameCam(playTs);
      drawMap(playTs);
    });

    fillHead();
    setRateButtons();
    waitForTracker();
    window.requestAnimationFrame(tick);
  }
})();
