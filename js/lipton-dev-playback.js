/**
 * Lipton 2026 -dev only. Playback ranks from Race 5 mark-1 trail.
 * Do not use on the public Lipton URL. Not a Nett source.
 */
(function () {
  var GUN_TS = 1787838601000; /* 2026-08-27 15:50:01 SAST */
  var PLAY_START_TS = 1787840490000; /* 16:21:30 SAST, ~30s before first mark-1 */
  var RATE = 8;
  var CLUB = {
    BYC: "Benoni Yacht Club",
    FBYC: "False Bay Yacht Club",
    GLYC: "Germiston Lakes Yacht Club",
    HYC: "Hermanus Yacht Club",
    IZIVUNGUVUNGU: "Izivunguvungu",
    KYC: "Knysna Yacht Club",
    LDYC: "Lake Deneys Yacht Club",
    LYC: "Langebaan Yacht Club",
    PYC: "Point Yacht Club",
    RCYC: "Royal Cape Yacht Club",
    "RCYC Academy": "Royal Cape Yacht Club Academy",
    RNYC: "Royal Natal Yacht Club",
    SBYC: "Saldanha Bay Yacht Club",
    TSC: "Transvaal Sailing Club",
    UCTYC: "UCT Yacht Club",
    WBYC: "Walvis Bay Yacht Club",
    WYAC: "Wits Yacht Club"
  };
  /* Race 5 lap-1 mark 1 — all 17 from trail */
  var MARK1 = [
    { boat: "HYC", ts: 1787840523900 },
    { boat: "RCYC", ts: 1787840541600 },
    { boat: "KYC", ts: 1787840551400 },
    { boat: "RCYC Academy", ts: 1787840578100 },
    { boat: "RNYC", ts: 1787840589100 },
    { boat: "UCTYC", ts: 1787840590000 },
    { boat: "SBYC", ts: 1787840598100 },
    { boat: "PYC", ts: 1787840608400 },
    { boat: "FBYC", ts: 1787840615600 },
    { boat: "WBYC", ts: 1787840618300 },
    { boat: "IZIVUNGUVUNGU", ts: 1787840626100 },
    { boat: "LDYC", ts: 1787840645000 },
    { boat: "GLYC", ts: 1787840653400 },
    { boat: "BYC", ts: 1787840677800 },
    { boat: "TSC", ts: 1787840688900 },
    { boat: "LYC", ts: 1787840707500 },
    { boat: "WYAC", ts: 1787840742900 }
  ];

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
  function fmtGap(ms) {
    if (ms == null) return "—";
    if (ms <= 0) return "0:00";
    var s = Math.floor(ms / 1000);
    return "+" + Math.floor(s / 60) + ":" + pad(s % 60);
  }
  function ordinal(n) {
    var v = n % 100;
    if (v >= 11 && v <= 13) return n + "th";
    if (n % 10 === 1) return n + "st";
    if (n % 10 === 2) return n + "nd";
    if (n % 10 === 3) return n + "rd";
    return n + "th";
  }

  var tbody = document.getElementById("lipton-dev-tbody");
  var clockEl = document.getElementById("lipton-dev-clock");
  var sailedEl = document.getElementById("lipton-dev-sailed");
  if (!tbody) return;

  var playTs = PLAY_START_TS;
  var lastWall = Date.now();
  var lastRounded = -1;

  function rowsAt(ts) {
    var rounded = MARK1.filter(function (b) { return b.ts <= ts; });
    var waiting = MARK1.filter(function (b) { return b.ts > ts; });
    var leadTs = rounded.length ? rounded[0].ts : null;
    var out = rounded.map(function (b, i) {
      return {
        rank: i + 1,
        boat: b.boat,
        gap: leadTs == null ? 0 : b.ts - leadTs,
        done: true
      };
    });
    waiting.forEach(function (b) {
      out.push({ rank: null, boat: b.boat, gap: null, done: false });
    });
    return out;
  }

  function render(ts) {
    var rows = rowsAt(ts);
    var html = "";
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var medal = r.rank === 1 ? " medal-gold" : r.rank === 2 ? " medal-silver" : r.rank === 3 ? " medal-bronze" : "";
      html += "<tr class=\"" + (r.done ? "" : "strike-out") + "\">";
      html += "<td class=\"rank-col" + medal + "\">" + (r.rank ? ordinal(r.rank) : "—") + "</td>";
      html += "<td>" + r.boat + "</td>";
      html += "<td class=\"club-col\">" + (CLUB[r.boat] || r.boat) + "</td>";
      html += "<td>" + fmtGap(r.gap) + "</td>";
      html += "</tr>";
    }
    tbody.innerHTML = html;
    if (clockEl) clockEl.textContent = fmtT(ts - GUN_TS);
    var n = MARK1.filter(function (b) { return b.ts <= ts; }).length;
    if (sailedEl) {
      sailedEl.textContent = n === 0
        ? "Race 5 playback · approaching mark 1"
        : (n === 17
          ? "Race 5 playback · all 17 around mark 1"
          : "Race 5 playback · " + n + " of 17 around mark 1");
    }
  }

  function tick() {
    var now = Date.now();
    var dt = now - lastWall;
    lastWall = now;
    playTs += dt * RATE;
    var endTs = MARK1[MARK1.length - 1].ts + 8000;
    if (playTs > endTs) playTs = endTs;
    var n = MARK1.filter(function (b) { return b.ts <= playTs; }).length;
    if (n !== lastRounded) {
      lastRounded = n;
      render(playTs);
    } else if (clockEl) {
      clockEl.textContent = fmtT(playTs - GUN_TS);
    }
    if (playTs < endTs) window.requestAnimationFrame(tick);
  }

  render(playTs);
  window.requestAnimationFrame(tick);
})();
