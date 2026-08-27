/**
 * Lipton 2026 -dev only. Replay sandbox — not live, not Nett.
 * Rank re-sorts at each mark from Race 5 tracker times.
 * Data: /js/lipton-dev-replay.json
 */
(function () {
  var DATA_URL = "/js/lipton-dev-replay.json?v=20260827h";

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
    var LABELS = data.mark_labels || ["M1", "M2", "M3", "M4"];
    var MARKS = {};
    LABELS.forEach(function (lab) {
      MARKS[lab] = ((data.marks || {})[lab] || []).map(function (b) {
        return { boat: b.boat, ts: b.ts_ms };
      });
    });
    var BOATS = data.boats || {};
    var GUN_TS = Number(data.gun_ts_ms);
    var PLAY_START_TS = Number(data.play_start_ts_ms);
    var PLAY_END_TS = Number(data.play_end_ts_ms || data.end_ts_ms);
    var FINISH = (data.finish || []).map(function (b) {
      return { boat: b.boat, ts: b.ts_ms };
    });
    var RATE = Number(data.default_rate || 10);
    var playing = true;
    var playTs = PLAY_START_TS;
    var lastWall = Date.now();
    var lastKey = "";
    var lastLead = "";
    var seen = {};

    var tbody = document.getElementById("lipton-dev-tbody");
    var clockEl = document.getElementById("lipton-dev-clock");
    var sailedEl = document.getElementById("lipton-dev-sailed");
    var frameEl = document.getElementById("lipton-dev-vakaros");
    var playBtn = document.getElementById("lipton-dev-play");
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
    function setFrame(ts) {
      if (frameEl) frameEl.src = watchUrl(data, ts);
    }
    function setRateButtons() {
      [].forEach.call(document.querySelectorAll("[data-rate]"), function (btn) {
        btn.classList.toggle("is-active", Number(btn.getAttribute("data-rate")) === RATE);
      });
    }
    function setPlayLabel() {
      if (playBtn) playBtn.textContent = playing ? "Pause" : "Play";
    }
    function tsAt(lab, boat) {
      var list = MARKS[lab] || [];
      for (var i = 0; i < list.length; i++) {
        if (list[i].boat === boat) return list[i].ts;
      }
      return null;
    }
    function boatTimes(boat, ts) {
      var out = {};
      for (var i = 0; i < LABELS.length; i++) {
        var t = tsAt(LABELS[i], boat);
        if (t != null && t <= ts) out[LABELS[i]] = t;
      }
      return out;
    }
    function furthest(times) {
      var k = -1;
      var lab = null;
      var t = null;
      for (var i = 0; i < LABELS.length; i++) {
        if (times[LABELS[i]] != null) {
          k = i;
          lab = LABELS[i];
          t = times[LABELS[i]];
        }
      }
      return { idx: k, lab: lab, ts: t };
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
    function splitCell(times, lab, i) {
      var t = times[lab];
      if (t == null) return "";
      var prev = i === 0 ? GUN_TS : times[LABELS[i - 1]];
      if (prev == null) return "";
      return fmtClock(t - prev);
    }
    function rowsAt(ts) {
      var names = {};
      LABELS.forEach(function (lab) {
        (MARKS[lab] || []).forEach(function (b) {
          if (b.ts <= ts) names[b.boat] = true;
        });
      });
      var rows = Object.keys(names).map(function (boat) {
        var times = boatTimes(boat, ts);
        var far = furthest(times);
        return { boat: boat, times: times, farIdx: far.idx, farTs: far.ts, farLab: far.lab };
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
      return rows.map(function (r) { return r.rank + ":" + r.boat + ":" + r.farLab; }).join("|");
    }
    function rowHtml(r, unroll) {
      var id = ident(r.boat);
      var medal = r.rank === 1 ? " medal-gold" : r.rank === 2 ? " medal-silver" : r.rank === 3 ? " medal-bronze" : "";
      var cls = medal + (unroll ? " lipton-unroll" : "");
      var html = "<tr class=\"" + cls + "\" data-bow=\"" + esc(id ? id.bow : "") + "\" data-boat=\"" + esc(r.boat) + "\">";
      html += "<td class=\"rank-col\">" + r.rank + "</td>";
      html += "<td class=\"wc-meta-col\">" + bowCell(id) + "</td>";
      html += "<td class=\"boat-name-col\">" + boatNameCell(id) + "</td>";
      html += "<td class=\"club-col\">" + clubCell(id) + "</td>";
      for (var i = 0; i < LABELS.length; i++) {
        html += "<td class=\"timer-col\">" + splitCell(r.times, LABELS[i], i) + "</td>";
      }
      html += "<td class=\"timer-col\">" + finCell(r, playTs) + "</td>";
      html += "</tr>";
      return html;
    }
    function setSailed(rows) {
      if (!sailedEl) return;
      var lab = leadMark(rows);
      if (!lab) {
        sailedEl.textContent = "Race 5 replay 10× · approaching M1";
        return;
      }
      var n = 0;
      rows.forEach(function (r) { if (r.farLab === lab) n += 1; });
      var tot = (MARKS[lab] || []).length;
      sailedEl.textContent = "Race 5 replay 10× · " + lab + " · " + n + " of " + tot + " · rank by " + lab;
    }
    function render(ts) {
      var rows = rowsAt(ts);
      var html = "";
      for (var i = 0; i < rows.length; i++) {
        var first = !seen[rows[i].boat];
        seen[rows[i].boat] = true;
        html += rowHtml(rows[i], first);
      }
      tbody.innerHTML = html;
      if (clockEl) {
        clockEl.textContent = rows.length === 0
          ? fmtClock(ts - GUN_TS) + " → M1"
          : fmtClock(ts - GUN_TS);
      }
      setSailed(rows);
      lastKey = stateKey(rows);
      var lead = leadMark(rows) || "";
      if (lead && lead !== lastLead) {
        lastLead = lead;
        setFrame(ts);
      }
    }

    function jump(ts) {
      playTs = ts;
      lastWall = Date.now();
      lastKey = "";
      seen = {};
      setFrame(ts);
      render(ts);
    }

    function tick() {
      if (playing) {
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
          clockEl.textContent = rows.length === 0
            ? fmtClock(playTs - GUN_TS) + " → M1"
            : fmtClock(playTs - GUN_TS);
        }
      } else {
        lastWall = Date.now();
      }
      window.requestAnimationFrame(tick);
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
      });
    });
    if (playBtn) {
      playBtn.addEventListener("click", function () {
        playing = !playing;
        lastWall = Date.now();
        setPlayLabel();
      });
    }

    setFrame(PLAY_START_TS);
    setRateButtons();
    setPlayLabel();
    render(playTs);
    window.requestAnimationFrame(tick);
  }
})();
