/**
 * Lipton 2026 -dev only. Replay sandbox — not live, not Nett.
 * Rank re-sorts at each mark *pass* (M1 can appear again on lap 2+).
 * Place deltas sit between consecutive passes. Times are mm:ss, no T+.
 * Data: /js/lipton-dev-replay.json
 */
(function () {
  var DATA_URL = "/js/lipton-dev-replay.json?v=20260827y";
  var TRAIL_URL = "/js/lipton-dev-trail.json?v=20260827y";

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
    function fitMap() {
      if (!mapEl) return;
      var w = mapEl.clientWidth || 640;
      var h = mapEl.clientHeight || 480;
      var dpr = window.devicePixelRatio || 1;
      mapEl.width = Math.floor(w * dpr);
      mapEl.height = Math.floor(h * dpr);
      mapCtx = mapEl.getContext("2d");
      mapCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var minLat = 90, maxLat = -90, minLon = 180, maxLon = -180;
      Object.keys(trail.boats || {}).forEach(function (sail) {
        var b = trail.boats[sail];
        for (var i = 0; i < (b.lat || []).length; i++) {
          if (b.lat[i] == null) continue;
          if (b.lat[i] < minLat) minLat = b.lat[i];
          if (b.lat[i] > maxLat) maxLat = b.lat[i];
          if (b.lon[i] < minLon) minLon = b.lon[i];
          if (b.lon[i] > maxLon) maxLon = b.lon[i];
        }
      });
      Object.keys(trail.marks || {}).forEach(function (k) {
        var m = trail.marks[k];
        if (!m) return;
        if (m.lat < minLat) minLat = m.lat;
        if (m.lat > maxLat) maxLat = m.lat;
        if (m.lon < minLon) minLon = m.lon;
        if (m.lon > maxLon) maxLon = m.lon;
      });
      var padLat = (maxLat - minLat) * 0.08 || 0.002;
      var padLon = (maxLon - minLon) * 0.08 || 0.002;
      mapBounds = { minLat: minLat - padLat, maxLat: maxLat + padLat, minLon: minLon - padLon, maxLon: maxLon + padLon, w: w, h: h };
    }
    function xy(lat, lon) {
      var b = mapBounds;
      var x = ((lon - b.minLon) / (b.maxLon - b.minLon)) * b.w;
      var y = (1 - (lat - b.minLat) / (b.maxLat - b.minLat)) * b.h;
      return { x: x, y: y };
    }
    function posAt(sail, ts) {
      var b = trail.boats[sail];
      if (!b) return null;
      var t = (ts - trail.gun_ts_ms) / trail.step_ms;
      var i = Math.floor(t);
      var f = t - i;
      if (i < 0) { i = 0; f = 0; }
      if (i >= b.lat.length) { i = b.lat.length - 1; f = 0; }
      if (b.lat[i] == null) return null;
      if (f < 0.001 || i + 1 >= b.lat.length || b.lat[i + 1] == null) {
        return { lat: b.lat[i], lon: b.lon[i] };
      }
      return {
        lat: b.lat[i] + (b.lat[i + 1] - b.lat[i]) * f,
        lon: b.lon[i] + (b.lon[i + 1] - b.lon[i]) * f
      };
    }
    function drawMap(ts) {
      if (!mapCtx || !mapBounds) return;
      var w = mapBounds.w;
      var h = mapBounds.h;
      mapCtx.fillStyle = "#001f3f";
      mapCtx.fillRect(0, 0, w, h);
      mapCtx.strokeStyle = "rgba(255,255,255,0.12)";
      mapCtx.lineWidth = 1;
      Object.keys(trail.marks || {}).forEach(function (k) {
        var m = trail.marks[k];
        if (!m) return;
        var p = xy(m.lat, m.lon);
        mapCtx.beginPath();
        mapCtx.arc(p.x, p.y, 7, 0, Math.PI * 2);
        mapCtx.fillStyle = "#f59e0b";
        mapCtx.fill();
        mapCtx.fillStyle = "#ffffff";
        mapCtx.font = "bold 11px sans-serif";
        mapCtx.fillText("M" + k, p.x + 9, p.y + 4);
      });
      Object.keys(trail.boats || {}).forEach(function (sail) {
        var pos = posAt(sail, ts);
        if (!pos) return;
        var p = xy(pos.lat, pos.lon);
        mapCtx.beginPath();
        mapCtx.arc(p.x, p.y, 5, 0, Math.PI * 2);
        mapCtx.fillStyle = OCS[sail] ? "#ef4444" : "#f8fafc";
        mapCtx.fill();
        mapCtx.fillStyle = OCS[sail] ? "#fecaca" : "#e2e8f0";
        mapCtx.font = "bold 10px sans-serif";
        mapCtx.fillText(sail, p.x + 7, p.y - 2);
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
