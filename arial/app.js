(function () {
    var STORE = "arialKeyClicks";
    var audioCtx = null;
    var ROLL_MS = 110;

    function pad(n) {
        return String(n).padStart(2, "0");
    }

    function rollText(el, text) {
        if (!el) return;
        text = text == null ? "" : String(text);
        if (el._want === text) return;
        el._want = text;
        if (el._roll) clearInterval(el._roll);
        el.textContent = "";
        var i = 0;
        if (!text) return;
        el._roll = setInterval(function () {
            i += 1;
            el.textContent = text.slice(0, i);
            if (i >= text.length) {
                clearInterval(el._roll);
                el._roll = null;
            }
        }, ROLL_MS);
    }

    function tickTime() {
        var d = new Date();
        var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        var dateStr = pad(d.getDate()) + " " + months[d.getMonth()] + " " + d.getFullYear();
        var timeStr = pad(d.getHours()) + ":" + pad(d.getMinutes());
        var dateEl = document.getElementById("lcd-date");
        var timeEl = document.getElementById("lcd-time");
        if (dateEl) dateEl.textContent = dateStr;
        if (timeEl) timeEl.textContent = timeStr;
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
        return st ? st : "System Ready";
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
            rollText(document.getElementById("lcd-2"), statusFromDevice(hanse));
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
        osc.frequency.setValueAtTime(2100, t);
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.exponentialRampToValueAtTime(0.38, t + 0.004);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.09);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start(t);
        osc.stop(t + 0.1);
    }

    function onKey(key) {
        if (!key) return;
        beep();
        saveClick(key);
        if (typeof window.onArialKey === "function") window.onArialKey(key);
    }

    window.setArialLcd = function (top, bottom) {
        if (top != null) {
            var parts = String(top).split(/\s+/);
            var timeEl = document.getElementById("lcd-time");
            var dateEl = document.getElementById("lcd-date");
            if (parts.length && timeEl) timeEl.textContent = parts[parts.length - 1];
            if (parts.length > 1 && dateEl) dateEl.textContent = parts.slice(0, -1).join(" ");
        }
        if (bottom != null) rollText(document.getElementById("lcd-2"), String(bottom));
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
