/**
 * Sailfish (saill.cn) open_trac parity UI for tracking-dev2.
 * Applies viewConfig flags and shows transport/API status bar.
 */
(function () {
  function el(id) {
    return document.getElementById(id);
  }

  function flag(on) {
    return on ? "on" : "off";
  }

  function nearestRate(rates, want) {
    var n = Number(want) || 1;
    var best = rates[0];
    var i;
    for (i = 0; i < rates.length; i++) {
      if (rates[i] <= n) best = rates[i];
    }
    return best;
  }

  window.applySailfishDev2 = function (bootstrap) {
    if (!bootstrap) return {};
    var vc = bootstrap.viewConfig || {};
    var bar = el("tracking-dev2-sailfish-bar");
    var mode = el("tracking-dev2-sailfish-mode");
    var meta = el("tracking-dev2-sailfish-meta");
    var flags = el("tracking-dev2-sailfish-flags");
    var wind = el("tracking-dev2-wind-compass");

    if (mode) {
      mode.textContent = bootstrap.status === "99" ? "REPLAY" : "LIVE";
      mode.className = "tracking-dev2-sailfish-mode tracking-dev2-sailfish-mode--" +
        (bootstrap.status === "99" ? "replay" : "live");
    }
    if (meta) {
      meta.textContent = [
        bootstrap.matchName || "",
        bootstrap.raceName || "",
        bootstrap.raceCd || "",
        "status " + (bootstrap.status || "?"),
        (bootstrap.teamList || []).length + " teams"
      ].filter(Boolean).join(" · ");
    }
    if (flags && vc) {
      flags.innerHTML = [
        ["SOG", vc.ColSOG],
        ["COG", vc.ColCOG],
        ["Layline", vc.layline],
        ["Leader", vc.leaderline],
        ["Wind", vc.windCompass],
        ["Camera", vc.camera]
      ].map(function (pair) {
        return '<span class="tracking-dev2-flag tracking-dev2-flag--' + flag(pair[1]) + '">' +
          pair[0] + "</span>";
      }).join("");
    }
    if (wind) {
      wind.hidden = !vc.windCompass;
      wind.setAttribute("aria-hidden", vc.windCompass ? "false" : "true");
    }

    document.title = (bootstrap.matchName || "Tracking") + " — SF-TrajX dev2";

    var label = el("lipton-dev-race-label");
    if (label && bootstrap.raceName) {
      label.textContent = bootstrap.raceName + (bootstrap.status === "99" ? " — REPLAY" : "");
    }

    var checksum = el("lipton-dev-checksum");
    if (checksum) {
      checksum.textContent = "Sailfish dev2 · " + (bootstrap.raceCd || "") +
        " · replay2/static-json · R1–R10 Lipton sample";
    }

    return {
      replaySpeed: Number(vc.replaySpeed) || 5,
      maxPlaySpeed: Number(vc.maxPlaySpeed) || 500,
      layline: vc.layline !== false,
      laylineAngle: Number(vc.laylineAngle) || 44.2,
      leaderline: vc.leaderline !== false,
      windCompass: vc.windCompass !== false,
      colSOG: !!vc.ColSOG,
      colCOG: !!vc.ColCOG,
      trackLength: Number(vc.trackLength) || 90,
      nearestRate: nearestRate
    };
  };

  window.verifySailfishDev2Apis = function (race) {
    race = race || 1;
    var urls = [
      "/api/tracking-dev2/getRace?race=" + race,
      "/api/tracking-dev2/replay2/getRaceDatas?race=" + race,
      "/api/tracking-dev2/replay2/getEncryptionReplayData?race=" + race,
      "/api/tracking-dev2/ws-config?race=" + race
    ];
    return Promise.all(
      urls.map(function (u) {
        return fetch(u, { cache: "no-store" }).then(function (res) {
          return res.json().then(function (body) {
            return { url: u, ok: res.ok, success: body && body.success };
          });
        });
      })
    );
  };
})();
