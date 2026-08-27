/**
 * Lipton 2026 -dev only. Replay sandbox — not live, not Nett.
 * Data: /js/lipton-dev-replay.json (replace that file to refresh old data).
 */
(function () {
  var DATA_URL = "/js/lipton-dev-replay.json?v=20260827e";

  function pad(n) {
    return n < 10 ? "0" + n : String(n);
  }
  function fmtT(ms) {
    if (ms < 0) {
      var a = Math.abs(ms);
      var s = Math.floor(a / 1000);
      return "T−" + pad(Math.floor(s / 60)) + ":" + pad(s % 60);
    }
    var s2 = Math.floor(ms / 1000);
    var m = Math.floor(s2 / 60);
    var h = Math.floor(m / 60);
    m = m % 60;
    var sec = s2 % 60;
    if (h > 0) return "T+" + h + ":" + pad(m) + ":" + pad(sec);
    return "T+" + m + ":" + pad(sec);
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
    var MARK1 = (data.mark1 || []).map(function (b) {
      return { boat: b.boat, ts: b.ts_ms };
    });
    var BOATS = data.boats || {};
    var GUN_TS = Number(data.gun_ts_ms);
    var PLAY_START_TS = Number(data.play_start_ts_ms);
    var FINISH_TS = Number(data.first_finish_ts_ms || 0);
    var RATE = Number(data.default_rate || 8);
    var playing = true;
    var playTs = PLAY_START_TS;
    var lastWall = Date.now();
    var lastRounded = -1;
    var markEnd = MARK1.length ? MARK1[MARK1.length - 1].ts + 8000 : PLAY_START_TS;

    var tbody = document.getElementById("lipton-dev-tbody");
    var tableWrap = document.getElementById("lipton-dev-table-wrap");
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

    function rowsAt(ts) {
      return MARK1.filter(function (b) { return b.ts <= ts; }).map(function (b, i) {
        return { rank: i + 1, boat: b.boat, markTs: b.ts };
      });
    }
    function rowHtml(r, unroll) {
      var id = ident(r.boat);
      var medal = r.rank === 1 ? " medal-gold" : r.rank === 2 ? " medal-silver" : r.rank === 3 ? " medal-bronze" : "";
      var cls = medal + (unroll ? " lipton-unroll" : "");
      var html = "<tr class=\"" + cls + "\" data-bow=\"" + esc(id ? id.bow : "") + "\">";
      html += "<td class=\"rank-col\">" + r.rank + "</td>";
      html += "<td class=\"wc-meta-col\">" + bowCell(id) + "</td>";
      html += "<td class=\"boat-name-col\">" + boatNameCell(id) + "</td>";
      html += "<td class=\"club-col\">" + clubCell(id) + "</td>";
      html += "<td class=\"timer-col\">" + fmtT(r.markTs - GUN_TS) + "</td>";
      html += "</tr>";
      return html;
    }
    function setSailed(n) {
      if (!sailedEl) return;
      sailedEl.textContent = n === 0
        ? "Race 5 replay · approaching mark 1"
        : (n === 17
          ? "Race 5 replay · all 17 around mark 1"
          : "Race 5 replay · " + n + " of 17 around mark 1");
    }
    function render(ts, unrollNew) {
      var n = MARK1.filter(function (b) { return b.ts <= ts; }).length;
      var shown = tbody.rows.length;
      if (tableWrap) tableWrap.hidden = n === 0;
      if (n === 0) {
        tbody.innerHTML = "";
      } else if (n < shown || !unrollNew) {
        var rows = rowsAt(ts);
        var html = "";
        for (var i = 0; i < rows.length; i++) html += rowHtml(rows[i], false);
        tbody.innerHTML = html;
      } else if (n > shown) {
        var add = rowsAt(ts).slice(shown);
        var extra = "";
        for (var j = 0; j < add.length; j++) extra += rowHtml(add[j], true);
        tbody.insertAdjacentHTML("beforeend", extra);
      }
      if (clockEl) clockEl.textContent = fmtT(ts - GUN_TS);
      setSailed(n);
    }

    function jump(ts) {
      playTs = ts;
      lastWall = Date.now();
      lastRounded = -1;
      setFrame(ts);
      render(ts, false);
    }

    function tick() {
      if (playing) {
        var now = Date.now();
        playTs += (now - lastWall) * RATE;
        lastWall = now;
        if (playTs > markEnd) {
          playTs = markEnd;
          playing = false;
          setPlayLabel();
        }
        var n = MARK1.filter(function (b) { return b.ts <= playTs; }).length;
        if (n !== lastRounded) {
          lastRounded = n;
          render(playTs, true);
        } else if (clockEl) {
          clockEl.textContent = fmtT(playTs - GUN_TS);
        }
      } else {
        lastWall = Date.now();
      }
      window.requestAnimationFrame(tick);
    }

    document.querySelectorAll("[data-jump]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var key = btn.getAttribute("data-jump");
        var ts = key === "gun" ? GUN_TS : key === "finish" ? FINISH_TS : PLAY_START_TS;
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
    render(playTs, false);
    window.requestAnimationFrame(tick);
  }
})();
