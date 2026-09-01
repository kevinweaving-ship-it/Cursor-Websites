(function () {
    var STORE = "arialKeyClicks";
    var audioCtx = null;
    var statusText = "";

    function pad(n) {
        return String(n).padStart(2, "0");
    }

    function tickTime() {
        var d = new Date();
        var el = document.getElementById("lcd-time");
        if (el) el.textContent = pad(d.getHours()) + ":" + pad(d.getMinutes());
    }

    function statusFromDevice(device) {
        var areas = (device && device.arialAreas) || [];
        var st = areas.length ? String(areas[0].state || "").toLowerCase() : "";
        if (st.indexOf("alarm") !== -1) return "Alarm";
        if (st === "arm") return "System Armed";
        if (st === "stay") return "Stay Armed";
        if (st === "sleep") return "Sleep Armed";
        if (st === "disarm") return "System Ready";
        if (st === "notready") return "Not Ready";
        return st ? st : "";
    }

    async function loadStatus() {
        try {
            var res = await fetch("/api/arial/devices", { credentials: "same-origin" });
            var data = await res.json();
            if (!res.ok) return;
            var devices = data.devices || [];
            var hanse = devices.filter(function (d) {
                return /hansekop/i.test(d.deviceName || "");
            })[0] || devices[0];
            statusText = statusFromDevice(hanse);
            var el = document.getElementById("lcd-2");
            if (el) el.textContent = statusText;
        } catch (e) { /* keep last status */ }
    }

    function loadClicks() {
        try {
            var raw = localStorage.getItem(STORE);
            var list = raw ? JSON.parse(raw) : [];
            return Array.isArray(list) ? list : [];
        } catch (e) {
            return [];
        }
    }

    function saveClick(key) {
        var list = loadClicks();
        list.push({ key: key, at: new Date().toISOString() });
        if (list.length > 500) list = list.slice(-500);
        localStorage.setItem(STORE, JSON.stringify(list));
        window.arialClicks = list;
    }

    function beep() {
        var AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return;
        if (!audioCtx) audioCtx = new AC();
        if (audioCtx.state === "suspended") audioCtx.resume();
        var t = audioCtx.currentTime;
        var osc = audioCtx.createOscillator();
        var gain = audioCtx.createGain();
        osc.type = "square";
        osc.frequency.setValueAtTime(1850, t);
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.exponentialRampToValueAtTime(0.08, t + 0.005);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.07);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start(t);
        osc.stop(t + 0.08);
    }

    function onKey(key) {
        if (!key) return;
        beep();
        saveClick(key);
        if (typeof window.onArialKey === "function") window.onArialKey(key);
    }

    window.setArialLcd = function (top, bottom) {
        var site = document.getElementById("lcd-site");
        if (site && top != null) site.textContent = String(top);
        var line2 = document.getElementById("lcd-2");
        if (line2 && bottom != null) line2.textContent = String(bottom);
    };

    window.arialClicks = loadClicks();

    var pad = document.querySelector(".pad");
    pad.addEventListener("pointerdown", function (ev) {
        var btn = ev.target.closest("[data-key]");
        if (!btn) return;
        ev.preventDefault();
        onKey(btn.getAttribute("data-key"));
    });

    tickTime();
    loadStatus();
    setInterval(tickTime, 1000);
    setInterval(loadStatus, 8000);
})();
