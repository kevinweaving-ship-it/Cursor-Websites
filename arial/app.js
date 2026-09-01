(function () {
    var state = { devices: [], idx: 0, areaIdx: 0, pin: "", lcdHold: null };

    function $(id) { return document.getElementById(id); }

    function lcdDate() {
        var d = new Date();
        var months = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"];
        var hh = String(d.getHours()).padStart(2, "0");
        var mm = String(d.getMinutes()).padStart(2, "0");
        return { left: months[d.getMonth()] + " " + d.getDate(), right: hh + ":" + mm };
    }

    function areaLine(device) {
        var areas = (device && device.arialAreas) || [];
        if (!areas.length) return "No area";
        if (state.areaIdx >= areas.length) state.areaIdx = 0;
        var a = areas[state.areaIdx];
        var st = String(a.state || "").toLowerCase();
        var map = {
            arm: "System Armed",
            stay: "Stay Armed",
            sleep: "Sleep Armed",
            disarm: "System Ready",
            notready: "Not Ready"
        };
        return (a.label ? a.label + " · " : "") + (map[st] || a.state || "—");
    }

    function paintLcd(statusOverride) {
        var clock = lcdDate();
        $("lcd-left").textContent = clock.left;
        $("lcd-right").textContent = clock.right;
        var device = state.devices[state.idx];
        var line = statusOverride;
        if (!line) {
            if (state.pin) line = "Code  " + "*".repeat(state.pin.length);
            else line = device ? areaLine(device) : "Connecting…";
        }
        $("lcd-status").textContent = line;
        var ac = device && device.deviceState && device.deviceState.powerAC === "ok";
        var online = device && device.deviceStatus === "online";
        var armed = false;
        var alarm = false;
        ((device && device.arialAreas) || []).forEach(function (a) {
            var s = String(a.state || "").toLowerCase();
            if (s === "arm" || s === "stay" || s === "sleep") armed = true;
            if (s.indexOf("alarm") !== -1) alarm = true;
        });
        $("led-ac").classList.toggle("on", !!ac);
        $("led-status").className = "kp-dot kp-dot-status" + (alarm ? " alarm" : (online || armed ? " on" : ""));
    }

    function paintSites() {
        var box = $("site-chips");
        box.innerHTML = state.devices.map(function (d, i) {
            var name = (d.deviceName || "Site").replace(/^Arial\s*-\s*/i, "");
            return '<button type="button" data-i="' + i + '" class="' + (i === state.idx ? "is-on" : "") + '">' + name + "</button>";
        }).join("");
    }

    async function loadDevices() {
        try {
            var res = await fetch("/api/arial/devices", { credentials: "same-origin" });
            var data = await res.json();
            if (!res.ok) throw new Error(data.detail || data.error || "Load failed");
            state.devices = data.devices || [];
            if (state.idx >= state.devices.length) state.idx = 0;
            paintSites();
            if (!state.lcdHold) paintLcd();
        } catch (e) {
            paintLcd(String(e.message || e));
        }
    }

    function flashLcd(msg, ms) {
        state.lcdHold = msg;
        paintLcd(msg);
        clearTimeout(flashLcd._t);
        flashLcd._t = setTimeout(function () {
            state.lcdHold = null;
            paintLcd();
        }, ms || 1600);
    }

    function onKey(key) {
        if (key === "CLEAR") {
            state.pin = "";
            flashLcd("Cleared", 800);
            return;
        }
        if (key === "UP" || key === "DOWN") {
            var n = ((state.devices[state.idx] || {}).arialAreas || []).length || 1;
            state.areaIdx = (state.areaIdx + (key === "UP" ? -1 : 1) + n) % n;
            paintLcd();
            return;
        }
        if (key === "1") {
            var n1 = ((state.devices[state.idx] || {}).arialAreas || []).length || 1;
            state.areaIdx = (state.areaIdx + 1) % n1;
            paintLcd();
            return;
        }
        if (/^[0-9]$/.test(key)) {
            if (state.pin.length < 8) state.pin += key;
            paintLcd();
            return;
        }
        if (key === "ENTER" || key === "ARM" || key === "DISARM" || key === "STAY" || key === "FORCE") {
            flashLcd("Code later");
            state.pin = "";
            return;
        }
        flashLcd(key);
    }

    $("site-chips").addEventListener("click", function (ev) {
        var b = ev.target.closest("button");
        if (!b) return;
        state.idx = Number(b.getAttribute("data-i"));
        state.areaIdx = 0;
        paintSites();
        paintLcd();
    });

    $("keypad").addEventListener("click", function (ev) {
        var b = ev.target.closest("button[data-key]");
        if (!b) return;
        onKey(b.getAttribute("data-key"));
    });

    paintLcd();
    loadDevices();
    setInterval(function () {
        if (!state.lcdHold) paintLcd();
    }, 15000);
    setInterval(loadDevices, 8000);
})();
