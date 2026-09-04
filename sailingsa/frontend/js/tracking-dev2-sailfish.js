/**
 * Sailfish (saill.cn) open_trac parity UI for tracking-dev2.
 * Applies viewConfig flags and shows transport/API status bar.
 * Feature toggles are bit-by-bit: turn off anything you do not want.
 */
(function () {
  function el(id) {
    return document.getElementById(id);
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

  function overlayState(vc) {
    var prev = window.__sailfishOverlay || {};
    return {
      board: prev.board === true,
      marks: prev.marks !== false,
      dots: prev.dots !== false,
      layline: vc.layline !== false,
      leaderline: vc.leaderline !== false,
      frontline: prev.frontline !== false,
      windCompass: vc.windCompass !== false,
      colSOG: !!vc.ColSOG,
      colCOG: !!vc.ColCOG,
      camera: vc.camera !== false,
      laylineAngle: Number(vc.laylineAngle) || 44.2
    };
  }

  function syncBoard(state) {
    var board = el("tracking-dev2-ranking");
    if (!board) return;
    var on = !!(state && state.board);
    board.classList.toggle("is-hidden", !on);
    board.hidden = !on;
    board.setAttribute("aria-hidden", on ? "false" : "true");
    board.style.display = on ? "" : "none";
  }
  window.__sailfishSyncBoard = syncBoard;
  window.__sailfishToggleFlag = function (name) {
    var state = window.__sailfishOverlay || overlayState({});
    state[name] = !state[name];
    window.__sailfishOverlay = state;
    syncBoard(state);
    paintFlags(el("tracking-dev2-sailfish-flags"), state);
    if (typeof window.__sailfishRedraw === "function") {
      try { window.__sailfishRedraw(); } catch (err) {}
    }
    return state[name];
  };

  function paintFlags(flags, state) {
    if (!flags) return;
    var items = [
      ["Board", "board"],
      ["Marks", "marks"],
      ["Dots", "dots"],
      ["SOG", "colSOG"],
      ["COG", "colCOG"],
      ["Layline", "layline"],
      ["Leader", "leaderline"],
      ["Front", "frontline"],
      ["Wind", "windCompass"],
      ["Camera", "camera"]
    ];
    flags.innerHTML = "";
    var raceN = Number(new URLSearchParams(location.search).get("race") || 1) || 1;
    items.forEach(function (pair) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "tracking-dev2-flag tracking-dev2-flag--" + (state[pair[1]] ? "on" : "off");
      btn.setAttribute("data-flag", pair[1]);
      btn.textContent = pair[0];
      btn.title = "Toggle " + pair[0] + (pair[1] === "leaderline"
        ? (raceN >= 2
          ? " (regatta overall leader — prior nett + live race place)"
          : " (race leader — same as Front on Race 1)")
        : pair[1] === "frontline"
          ? " (who is 1st in this race right now)"
          : pair[1] === "board"
            ? " (Sailfish left ranking board overlay)"
            : pair[1] === "marks"
              ? " (Sailfish Start/Finish/numbered marks)"
              : pair[1] === "dots"
                ? " (breadcrumb dotted tracks)"
                : "");
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        state[pair[1]] = !state[pair[1]];
        window.__sailfishOverlay = state;
        syncBoard(state);
        paintFlags(flags, state);
        if (typeof window.__sailfishRedraw === "function") {
          try { window.__sailfishRedraw(); } catch (err) {}
        }
      });
      flags.appendChild(btn);
    });
  }

  window.applySailfishDev2 = function (bootstrap) {
    if (!bootstrap) return {};
    var vc = bootstrap.viewConfig || {};
    var mode = el("tracking-dev2-sailfish-mode");
    var meta = el("tracking-dev2-sailfish-meta");
    var flags = el("tracking-dev2-sailfish-flags");
    var wind = el("tracking-dev2-wind-compass");
    var state = overlayState(vc);
    window.__sailfishOverlay = state;
    syncBoard(state);

    var hideBtn = el("tracking-dev2-ranking-hide");
    if (hideBtn) {
      hideBtn.onclick = function (ev) {
        if (ev) {
          ev.preventDefault();
          ev.stopPropagation();
        }
        state.board = false;
        window.__sailfishOverlay = state;
        syncBoard(state);
        paintFlags(flags, state);
        if (typeof window.__sailfishRedraw === "function") {
          try { window.__sailfishRedraw(); } catch (err) {}
        }
      };
    }

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
    paintFlags(flags, state);
    if (wind) {
      wind.hidden = false;
      wind.setAttribute("aria-hidden", "false");
      wind.title = "Toggle wind compass";
      wind.style.cursor = "pointer";
      wind.onclick = function () {
        state.windCompass = !state.windCompass;
        window.__sailfishOverlay = state;
        paintFlags(flags, state);
        if (typeof window.__sailfishRedraw === "function") window.__sailfishRedraw();
      };
    }

    document.title = (bootstrap.matchName || "Tracking") + " — SF-TrajX dev2";

    var label = el("lipton-dev-race-label");
    if (label && bootstrap.raceName) {
      label.textContent = bootstrap.raceName + (bootstrap.status === "99" ? " — REPLAY" : "");
    }

    var checksum = el("lipton-dev-checksum");
    if (checksum) {
      checksum.textContent = "Sailfish ranking · " + (bootstrap.raceCd || "") +
        " · R1–R10 Lipton sample";
    }

    return {
      replaySpeed: Number(vc.replaySpeed) || 5,
      maxPlaySpeed: Number(vc.maxPlaySpeed) || 500,
      layline: state.layline,
      laylineAngle: state.laylineAngle,
      leaderline: state.leaderline,
      windCompass: state.windCompass,
      colSOG: state.colSOG,
      colCOG: state.colCOG,
      board: state.board,
      trackLength: Number(vc.trackLength) || 90,
      nearestRate: nearestRate
    };
  };
})();
