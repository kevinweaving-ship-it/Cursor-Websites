/**
 * Lipton 2026 -dev only. Replay sandbox — not live, not Nett.
 * Rank re-sorts at each mark *pass* (M1 can appear again on lap 2+).
 * Place deltas sit between consecutive passes. Times are mm:ss, no T+.
 * Data: /js/lipton-dev-replay.json
 */
(function () {
  var DATA_URL = "/js/lipton-dev-replay.json?v=20260827p";

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
      return data.passes.map(function (p, i) {
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

  fetch(DATA_URL, { cache: "no-store" })
    .then(function (res) {
      if (!res.ok) throw new Error("replay json " + res.status);
      return res.json();
    })
    .then(start)
    .catch(function (err) {
      var sailed = document.getElementById("lipton-dev-sailed");
      if (sailed) sailed.textContent = "Replay data failed to load";
      console.error(err);
    });

  function start(data) {
    var PASSES = loadPasses(data);
    var BOATS = data.boats || {};
    var GUN_TS = Number(data.gun_ts_ms);
    var PLAY_START_TS = Number(data.play_start_ts_ms);
    var PLAY_END_TS = Number(data.play_end_ts_ms || data.end_ts_ms);
    var FINISH = asBoats(data.finish);
    var RATE = Number(data.default_rate || 1);
    var SETTLE_MS = 4000;
    var playing = false;
    var trackerReady = false;
    var playTs = PLAY_START_TS;
    var lastWall = Date.now();
    var lastKey = "";
    var seen = {};
    var deltaSeen = {};
    var frameLocked = false;

    var tbody = document.getElementById("lipton-dev-tbody");
    var clockEl = document.getElementById("lipton-dev-clock");
    var sailedEl = document.getElementById("lipton-dev-sailed");
    var frameEl = document.getElementById("lipton-dev-vakaros");
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
    function loadTrackerOnce(ts) {
      if (!frameEl || frameLocked) return;
      frameLocked = true;
      frameEl.src = watchUrl(data, ts);
    }
    function setRateButtons() {
      [].forEach.call(document.querySelectorAll("[data-rate]"), function (btn) {
        btn.classList.toggle("is-active", Number(btn.getAttribute("data-rate")) === RATE);
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
        html += "<th class=\"timer-col\" title=\"Lap " + p.lap + " mark " + p.mark + "\">" + esc(p.label) + "</th>";
        if (i < PASSES.length - 1) {
          var nlab = PASSES[i + 1].label;
          html += "<th class=\"place-delta-col\" title=\"Places gained or lost " + esc(p.label) + " to " + esc(nlab) + "\" aria-label=\"Place change " + esc(p.label) + " to " + esc(nlab) + "\">±</th>";
        }
      }
      html += "<th class=\"timer-col\">Fin</th>";
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
    function splitCell(times, i) {
      var t = times[i];
      if (t == null) return "";
      var prev = i === 0 ? GUN_TS : times[i - 1];
      if (prev == null) return "";
      return fmtClock(t - prev);
    }
    function rankMapsAt(ts) {
      return PASSES.map(function (pass) {
        var hit = [];
        for (var i = 0; i < pass.boats.length; i++) {
          if (pass.boats[i].ts <= ts) hit.push(pass.boats[i]);
        }
        hit.sort(function (a, b) { return a.ts - b.ts; });
        var map = {};
        for (var j = 0; j < hit.length; j++) map[hit[j].boat] = j + 1;
        return map;
      });
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
        html += "<td class=\"timer-col\">" + splitCell(r.times, i) + "</td>";
        if (i < PASSES.length - 1) {
          html += deltaCell(r.boat, i, rankMaps[i], rankMaps[i + 1]);
        }
      }
      html += "<td class=\"timer-col\">" + finCell(r, playTs) + "</td>";
      html += "</tr>";
      return html;
    }
    function setSailed(rows) {
      if (!sailedEl) return;
      if (!rows.length) {
        sailedEl.textContent = "Race 5 replay · approaching M1";
        return;
      }
      var lead = rows[0];
      var n = 0;
      rows.forEach(function (r) { if (r.farIdx === lead.farIdx) n += 1; });
      var tot = PASSES[lead.farIdx] ? PASSES[lead.farIdx].boats.length : n;
      var lapBit = lead.farLap > 1 ? " · lap " + lead.farLap : "";
      sailedEl.textContent = "Race 5 replay · " + lead.farLab + lapBit + " · " + n + " of " + tot + " · rank by " + lead.farLab;
    }
    function clockText(ts, rows) {
      var clock = fmtClock(ts - GUN_TS);
      if (!rows.length) return clock + " → M1";
      return clock;
    }
    function render(ts) {
      var rows = rowsAt(ts);
      var rankMaps = rankMapsAt(ts);
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
      playing = true;
      setPlayLabel();
      render(playTs);
    }

    function waitForTracker() {
      if (sailedEl) sailedEl.textContent = "Loading tracker…";
      setPlayLabel();
      render(playTs);
      if (!frameEl) {
        window.setTimeout(beginAfterTracker, 0);
        return;
      }
      var shellSeen = false;
      function onShellLoad() {
        if (shellSeen) return;
        shellSeen = true;
        if (sailedEl) sailedEl.textContent = "Tracker loaded · waiting until stable";
        window.setTimeout(beginAfterTracker, SETTLE_MS);
      }
      frameEl.addEventListener("load", function () {
        var src = String(frameEl.src || "");
        if (src.indexOf("player.vakaros.com") === -1) return;
        onShellLoad();
      });
      loadTrackerOnce(PLAY_START_TS);
      window.setTimeout(function () {
        if (!trackerReady) onShellLoad();
      }, 12000);
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
        RATE = Number(btn.getAttribute("data-rate")) || 1;
        lastWall = Date.now();
        setRateButtons();
        try {
          if (frameEl && frameEl.contentWindow) {
            frameEl.contentWindow.postMessage({ playback_speed: RATE }, "https://player.vakaros.com");
          }
        } catch (err) {}
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

    fillHead();
    setRateButtons();
    waitForTracker();
    window.requestAnimationFrame(tick);
  }
})();
