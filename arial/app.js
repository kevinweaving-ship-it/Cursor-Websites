(function () {
    var STORE = "arialKeyClicks";
    var audioCtx = null;
    var lastStatus = "";

    function pad(n) {
        return String(n).padStart(2, "0");
    }

    function siteName(device) {
        var name = (device && device.deviceName) || "HANSEKOP";
        var parts = String(name).split(" - ");
        var site = (parts.length > 1 ? parts[parts.length - 1] : name).trim();
        return site.toUpperCase() || "HANSEKOP";
    }

    function areaState(device) {
        var areas = (device && device.arialAreas) || [];
        var i;
        for (i = 0; i < areas.length; i += 1) {
            if (areas[i] && areas[i].state) return String(areas[i].state).toLowerCase();
        }
        var raw = ((device && device.deviceState) || {}).areas || [];
        return raw.length ? String(raw[0] || "").toLowerCase() : "";
    }

    function openZoneLabel(device) {
        var zones = (device && device.arialZones) || [];
        var i;
        for (i = 0; i < zones.length; i += 1) {
            var z = zones[i];
            var st = String((z && z.state) || "").toLowerCase();
            if (st === "a" || st === "al" || st.indexOf("alarm") !== -1) {
                return String(z.label || ("Zone " + z.num)).trim();
            }
        }
        return "";
    }

    function statusFromDevice(device) {
        var st = areaState(device);
        if (!st) return "";
        if (st.indexOf("alarm") !== -1) return "ALARM";
        if (st === "arm") return "System Armed";
        if (st === "stay") return "Stay Armed";
        if (st === "sleep") return "Sleep Armed";
        if (st === "disarm") return "System Ready";
        if (st === "notready") return openZoneLabel(device) || "Not Ready";
        return st;
    }

    function setLed(el, mode) {
        if (!el) return;
        var kind = el.classList.contains("ac") ? "led ac" : "led status";
        el.className = kind + (mode ? " " + mode : "");
    }

    function applyLcd(device) {
        var lcd = document.querySelector(".lcd");
        if (!lcd || lcdHold) return;
        var st = areaState(device);
        var armed = st === "arm" || st === "stay" || st === "sleep" || st.indexOf("alarm") !== -1;
        var disarmed = st === "disarm" || st === "notready";
        lcd.classList.toggle("armed", armed);
        lcd.classList.toggle("disarmed", disarmed);
    }

    function applyLeds(device) {
        var state = (device && device.deviceState) || {};
        var st = areaState(device);
        var acOk = String(state.powerAC || "").toLowerCase() === "ok";
        applyLcd(device);
        setLed(document.getElementById("led-ac"), acOk ? "on" : "flash");
        if (st.indexOf("alarm") !== -1) {
            setLed(document.getElementById("led-status"), "on flash-fast");
        } else if (st === "notready") {
            setLed(document.getElementById("led-status"), "on flash");
        } else if (st === "disarm") {
            setLed(document.getElementById("led-status"), "on");
        } else {
            setLed(document.getElementById("led-status"), "");
        }
    }

    function tickTime() {
        var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        var d = new Date(new Date().toLocaleString("en-US", { timeZone: "Africa/Johannesburg" }));
        var when = document.getElementById("lcd-when") || document.getElementById("lcd-date");
        var timeEl = document.getElementById("lcd-time");
        var dateStr = pad(d.getDate()) + " " + months[d.getMonth()] + " " + d.getFullYear();
        var timeStr = pad(d.getHours()) + ":" + pad(d.getMinutes());
        if (timeEl) {
            var dateEl = document.getElementById("lcd-date");
            if (dateEl) dateEl.textContent = dateStr;
            timeEl.textContent = timeStr;
        } else if (when) {
            when.textContent = dateStr + "  " + timeStr;
        }
    }

    async function loadStatus() {
        try {
            var res = await fetch("/api/arial/devices", { credentials: "same-origin", cache: "no-store" });
            var data = await res.json();
            if (!res.ok) {
                document.getElementById("lcd-2").textContent = "No Link";
                return;
            }
            var devices = data.devices || [];
            var hanse = devices.filter(function (d) {
                return /hansekop/i.test(d.deviceName || "");
            })[0] || devices[0];
            if (!hanse) {
                document.getElementById("lcd-2").textContent = "No Device";
                return;
            }
            document.getElementById("lcd-site").textContent = siteName(hanse);
            lastStatus = statusFromDevice(hanse);
            if (!pin && !lcdHold) document.getElementById("lcd-2").textContent = lastStatus;
            applyLeds(hanse);
            window.arialDevice = hanse;
        } catch (e) {
            document.getElementById("lcd-2").textContent = lastStatus || "No Link";
        }
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

    var pinOk = null;
    var pin = "";
    var lcdHold = null;
    var CODES = {
        "7302": { name: "Marc", from: "Pingoa" }
    };

    function setStatusLine(text, holdMs) {
        var el = document.getElementById("lcd-2");
        if (el) el.textContent = text;
        if (lcdHold) clearTimeout(lcdHold);
        lcdHold = null;
        if (holdMs) {
                lcdHold = setTimeout(function () {
                    lcdHold = null;
                    pin = "";
                    el.textContent = lastStatus;
                    applyLcd(window.arialDevice);
                }, holdMs);
        }
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

    function rollText(el, text) {
        if (!el) return;
        text = text == null ? "" : String(text);
        if (el._roll) clearInterval(el._roll);
        el.textContent = "";
        var i = 0;
        el._roll = setInterval(function () {
            i += 1;
            el.textContent = text.slice(0, i);
            if (i >= text.length) {
                clearInterval(el._roll);
                el._roll = null;
            }
        }, 110);
    }
    function pinAccepted() {
        pinOk = pinOk || document.getElementById("pin-ok") || new Audio("/arial/pin-accepted.wav");
        pinOk.pause();
        pinOk.currentTime = 0;
        var p = pinOk.play();
        if (p && p.catch) p.catch(function () { beep(); });
    }

    function submitPin() {
        var user = CODES[pin];
        pin = "";
        if (user) {
            pinAccepted();
            window.arialUser = user;
            var lcd = document.querySelector(".lcd");
            if (lcd) lcd.classList.remove("armed", "disarmed");
            if (lcdHold) clearTimeout(lcdHold);
            lcdHold = setTimeout(function () {
                lcdHold = null;
                pin = "";
                var el = document.getElementById("lcd-2");
                if (el && el._roll) {
                    clearInterval(el._roll);
                    el._roll = null;
                }
                if (el) el.textContent = lastStatus;
                applyLcd(window.arialDevice);
            }, 5000);
            rollText(document.getElementById("lcd-2"), "Welcome Pingoa");
        } else {
            beep();
            setStatusLine("Invalid Code", 2000);
        }
    }

    function onKey(key) {
        if (!key) return;
        if (/^[0-9]$/.test(key)) {
            if (pin.length >= 4) return;
            pin += key;
            if (pin.length === 4) submitPin();
            else {
                beep();
                setStatusLine(new Array(pin.length + 1).join("*"));
            }
        } else if (key === "CLEAR") {
            beep();
            pin = "";
            setStatusLine(lastStatus);
        } else if (key === "ENTER") {
            if (pin) submitPin();
            else beep();
        } else {
            beep();
        }
        saveClick(key);
        if (typeof window.onArialKey === "function") window.onArialKey(key);
    }

    window.setArialLcd = function (top, bottom) {
        if (top != null) document.getElementById("lcd-site").textContent = String(top);
        if (bottom != null) document.getElementById("lcd-2").textContent = String(bottom);
    };

    window.arialClicks = loadClicks();

    var keypad = document.querySelector(".pad");
    keypad.addEventListener("pointerdown", function (ev) {
        var btn = ev.target.closest("[data-key]");
        if (!btn) return;
        ev.preventDefault();
        onKey(btn.getAttribute("data-key"));
    });

    tickTime();
    loadStatus();
    setInterval(tickTime, 1000);
    setInterval(loadStatus, 4000);
})();
