/**
 * Lipton 2026 -dev only. Playback ranks from Race 5 mark-1 trail.
 * Identity (bow / boat name / club logos) is from the public Lipton sheet.
 * Tracker replay URL uses Vakaros race-day + ts (live=true omitted).
 * Do not use on the public Lipton URL. Not a Nett source.
 */
(function () {
  var GUN_TS = 1787838601000; /* tracker R5 gun 2026-08-27 15:50:01 SAST */
  var PLAY_START_TS = 1787840490000; /* 16:21:30 SAST, ~30s before first mark-1 */
  var RATE = 8;
  var RACE_DAY = 2;
  var WATCH = "https://player.vakaros.com/watch/Lv9A35uOBSBRmGpHgXtH/J22";
  var BOATS =
  {
    "HYC": {
      "bow": "32",
      "club": "HYC",
      "clubHref": "/club/hyc",
      "clubLogo": "/artwork/Club%20Logo/HYC.png?v=20260827a",
      "boatHref": "/boat/j22-1571",
      "nameHref": "/boat-name/nitro-juice",
      "title": "Nitro Juice",
      "nameInner": "<img class=\"rs-boat-sponsor-logo\" src=\"/artwork/Sponsor%20Logo/Nitro.png?v=20260827a\" alt=\"Nitro\" title=\"Nitro\"> Juice"
    },
    "RCYC": {
      "bow": "26",
      "club": "RCYC",
      "clubHref": "/club/rcyc",
      "clubLogo": "/artwork/Club%20Logo/RCYC.png?v=20260827a",
      "boatHref": "/boat/j22-766",
      "nameHref": "/boat-name/amtec-racing",
      "title": "Amtec Racing",
      "nameInner": "<img class=\"rs-boat-sponsor-logo\" src=\"/artwork/Sponsor%20Logo/AMTEC.png?v=20260827a\" alt=\"AMTEC\" title=\"AMTEC\"> Racing"
    },
    "KYC": {
      "bow": "23",
      "club": "KYC",
      "clubHref": "/club/kyc",
      "clubLogo": "/artwork/Club%20Logo/KYC.png?v=20260827a",
      "boatHref": "/boat/j22-763",
      "nameHref": "/boat-name/phantom",
      "title": "Phantom",
      "nameInner": "Phantom"
    },
    "RNYC": {
      "bow": "28",
      "club": "RNYC",
      "clubHref": "/club/rnyc",
      "clubLogo": "/artwork/Club%20Logo/RNYC.png?v=20260827a",
      "boatHref": "/boat/j22-768",
      "nameHref": "/boat-name/ullman-racing",
      "title": "Ullman Racing",
      "nameInner": "<img class=\"rs-boat-sponsor-logo\" src=\"/artwork/Sponsor%20Logo/Ullman-Sails.png?v=20260827a\" alt=\"Ullman Sails\" title=\"Ullman Sails\"> Racing"
    },
    "WBYC": {
      "bow": "52",
      "club": "WBYC",
      "clubHref": "/club/wbyc",
      "clubLogo": "/artwork/Club%20Logo/WBYC.png?v=20260827a",
      "boatHref": "/boat/j22-1277",
      "nameHref": "/boat-name/22-ate",
      "title": "22-ATE",
      "nameInner": "22-ATE"
    },
    "FBYC": {
      "bow": "48",
      "club": "FBYC",
      "clubHref": "/club/fbyc",
      "clubLogo": "/artwork/Club%20Logo/FBYC.png?v=20260827a",
      "boatHref": "/boat/j22-1169",
      "nameHref": "/boat-name/ullman-sails-camissa",
      "title": "Ullman Sails Camissa",
      "nameInner": "<img class=\"rs-boat-sponsor-logo\" src=\"/artwork/Sponsor%20Logo/Ullman-Sails.png?v=20260827a\" alt=\"Ullman Sails\" title=\"Ullman Sails\"> Camissa"
    },
    "SBYC": {
      "bow": "49",
      "club": "SBYC",
      "clubHref": "/club/sbyc",
      "clubLogo": "/artwork/Club%20Logo/SBYC.png?v=20260827a",
      "boatHref": "/boat/j22-1175",
      "nameHref": "/boat-name/nitro-monkey",
      "title": "Nitro Monkey",
      "nameInner": "<img class=\"rs-boat-sponsor-logo\" src=\"/artwork/Sponsor%20Logo/Nitro.png?v=20260827a\" alt=\"Nitro\" title=\"Nitro\"> Monkey"
    },
    "PYC": {
      "bow": "34",
      "club": "PYC",
      "clubHref": "/club/pyc",
      "clubLogo": "/artwork/Club%20Logo/PYC.png?v=20260827a",
      "boatHref": "/boat/j22-1116",
      "nameHref": "/boat-name/gday-j",
      "title": "G'day J",
      "nameInner": "G'day J"
    },
    "LDYC": {
      "bow": "46",
      "club": "LDYC",
      "clubHref": "/club/ldyc",
      "clubLogo": "/artwork/Club%20Logo/LDYC.png?v=20260827a",
      "boatHref": "/boat/j22-1167",
      "nameHref": "/boat-name/wildcard",
      "title": "Wildcard",
      "nameInner": "Wildcard"
    },
    "GLYC": {
      "bow": "14",
      "club": "GLYC",
      "clubHref": "/club/glyc",
      "clubLogo": "/artwork/Club%20Logo/GLYC.png?v=20260827a",
      "boatHref": "/boat/j22-185",
      "nameHref": "/boat-name/andiamo",
      "title": "Andiamo",
      "nameInner": "Andiamo"
    },
    "BYC": {
      "bow": "44",
      "club": "BYC",
      "clubHref": "/club/byc",
      "clubLogo": "/artwork/Club%20Logo/BYC.png?v=20260827a",
      "boatHref": "/boat/j22-1139",
      "nameHref": "/boat-name/h2o-tech",
      "title": "H2O Tech",
      "nameInner": "<img class=\"rs-boat-sponsor-logo\" src=\"/artwork/Sponsor%20Logo/H2O.png?v=20260827a\" alt=\"H2O\" title=\"H2O\"> Tech"
    },
    "TSC": {
      "bow": "55",
      "club": "TSC",
      "clubHref": "/club/tsc",
      "clubLogo": "/artwork/Club%20Logo/TSC.png?v=20260827a",
      "boatHref": "/boat/j22-1239",
      "nameHref": "/boat-name/cacanny",
      "title": "CaCanny",
      "nameInner": "CaCanny"
    },
    "WYAC": {
      "bow": "43",
      "club": "WYAC",
      "clubHref": "/club/wyac",
      "clubLogo": "/artwork/Club%20Logo/WYAC.png?v=20260827a",
      "boatHref": "/boat/j22-1138",
      "nameHref": "/boat-name/laugh-a-minute",
      "title": "Laugh a minute",
      "nameInner": "Laugh a minute"
    },
    "RCYC Academy": {
      "bow": "8",
      "club": "RCYCA",
      "clubHref": "/club/rcyc",
      "clubLogo": "/artwork/Club%20Logo/RCYC.png?v=20260827a",
      "boatHref": "/boat/j22-173",
      "nameHref": "/boat-name/j-walker-powered-by-north-sails",
      "title": "J-Walker powered by North Sails",
      "nameInner": "J-Walker powered by <img class=\"rs-boat-sponsor-logo\" src=\"/artwork/Sponsor%20Logo/North-Sails.png?v=20260827a\" alt=\"North Sails\" title=\"North Sails\">"
    },
    "UCTYC": {
      "bow": "31",
      "club": "UCT",
      "clubHref": "/club/uct",
      "clubLogo": "/artwork/Club%20Logo/UCT.png?v=20260827a",
      "boatHref": "/boat/j22-774",
      "nameHref": "/boat-name/nitro-maverick",
      "title": "Nitro Maverick",
      "nameInner": "<img class=\"rs-boat-sponsor-logo\" src=\"/artwork/Sponsor%20Logo/Nitro.png?v=20260827a\" alt=\"Nitro\" title=\"Nitro\"> Maverick"
    },
    "IZIVUNGUVUNGU": {
      "bow": "63",
      "club": "IZI",
      "clubHref": "/club/izi",
      "clubLogo": "/artwork/Club%20Logo/IZI.png?v=20260827a",
      "boatHref": "/boat/j22-771",
      "nameHref": "/boat-name/donna-mia-forever",
      "title": "Donna Mia Forever",
      "nameInner": "Donna Mia Forever"
    },
    "LYC": {
      "bow": "51",
      "club": "LYCN",
      "clubHref": "/club/lycn",
      "clubLogo": "/artwork/Club%20Logo/LYCN.png?v=20260827a",
      "boatHref": "/boat/j22-1237",
      "nameHref": "/boat-name/attacke",
      "title": "Attacke",
      "nameInner": "Attacke"
    }
  };
  /* Race 5 lap-1 mark 1 — all 17 from trail. Keys = tracker sail_number. */
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
  function watchUrl(ts) {
    return WATCH + "?race-day=" + RACE_DAY + "&ts=" + Math.floor(ts);
  }
  function ident(tracker) {
    return BOATS[tracker] || null;
  }
  function esc(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
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

  var tbody = document.getElementById("lipton-dev-tbody");
  var clockEl = document.getElementById("lipton-dev-clock");
  var sailedEl = document.getElementById("lipton-dev-sailed");
  var frameEl = document.getElementById("lipton-dev-vakaros");
  if (!tbody) return;

  var playTs = PLAY_START_TS;
  var lastWall = Date.now();
  var lastRounded = -1;

  if (frameEl) {
    frameEl.src = watchUrl(PLAY_START_TS);
  }

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
      var id = ident(r.boat);
      var medal = r.rank === 1 ? " medal-gold" : r.rank === 2 ? " medal-silver" : r.rank === 3 ? " medal-bronze" : "";
      html += "<tr class=\"" + (r.done ? "" : "strike-out") + medal + "\" data-bow=\"" + esc(id ? id.bow : "") + "\">";
      html += "<td class=\"rank-col\">" + (r.rank ? r.rank : "—") + "</td>";
      html += "<td class=\"wc-meta-col\">" + bowCell(id) + "</td>";
      html += "<td class=\"boat-name-col\">" + boatNameCell(id) + "</td>";
      html += "<td class=\"club-col\">" + clubCell(id) + "</td>";
      html += "<td class=\"timer-col\">" + fmtGap(r.gap) + "</td>";
      html += "</tr>";
    }
    tbody.innerHTML = html;
    if (clockEl) clockEl.textContent = fmtT(ts - GUN_TS);
    var n = MARK1.filter(function (b) { return b.ts <= ts; }).length;
    if (sailedEl) {
      sailedEl.textContent = n === 0
        ? "Race 5 tracker replay · approaching mark 1"
        : (n === 17
          ? "Race 5 tracker replay · all 17 around mark 1"
          : "Race 5 tracker replay · " + n + " of 17 around mark 1");
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
