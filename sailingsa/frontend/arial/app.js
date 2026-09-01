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
        if (!lcd) return;
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
            setLed(document.getElementById("led-status"), "armed flash-fast");
        } else if (st === "arm" || st === "stay" || st === "sleep") {
            setLed(document.getElementById("led-status"), "armed");
        } else if (st === "notready") {
            setLed(document.getElementById("led-status"), "disarmed flash");
        } else {
            setLed(document.getElementById("led-status"), "disarmed");
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
            document.getElementById("lcd-2").textContent = lastStatus;
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
        "7302": { name: "Marc", from: "Pingoa", logo: "/arial/users/pingoa.png", code: "7302" }
    };

    function showUserLogo(user) {
        var lcd = document.querySelector(".lcd");
        var img = document.getElementById("lcd-user-logo");
        if (!lcd || !img) return;
        if (user && user.logo) {
            img.src = user.logo;
            lcd.classList.add("logged-in");
        } else {
            img.removeAttribute("src");
            lcd.classList.remove("logged-in");
        }
    }

    function setWelcome(text, holdMs) {
        var el = document.getElementById("lcd-welcome");
        if (el) {
            if (el._roll) {
                clearInterval(el._roll);
                el._roll = null;
            }
            el.textContent = text || "";
        }
        if (lcdHold) clearTimeout(lcdHold);
        lcdHold = null;
        if (holdMs) {
            lcdHold = setTimeout(function () {
                lcdHold = null;
                pin = "";
                if (el) el.textContent = "";
            }, holdMs);
        }
    }

    function unlockAudio() {
        var AC = window.AudioContext || window.webkitAudioContext;
        if (!AC) return;
        if (!audioCtx) audioCtx = new AC();
        if (audioCtx.state === "suspended") audioCtx.resume();
    }

    function tone(freq, dur, peak) {
        unlockAudio();
        if (!audioCtx) return;
        try {
            var t = audioCtx.currentTime;
            var osc = audioCtx.createOscillator();
            var gain = audioCtx.createGain();
            osc.type = "square";
            osc.frequency.setValueAtTime(freq, t);
            gain.gain.setValueAtTime(0.0001, t);
            gain.gain.exponentialRampToValueAtTime(peak || 0.38, t + 0.01);
            gain.gain.exponentialRampToValueAtTime(0.0001, t + dur);
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start(t);
            osc.stop(t + dur + 0.03);
        } catch (e) {}
    }

    function beep() {
        tone(2100, 0.09, 0.38);
    }

    function disarmBeep() {
        tone(1200, 0.95, 0.42);
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
            try { sessionStorage.setItem("arialUser", JSON.stringify(user)); } catch (e) {}
            showUserLogo(user);
            applyLcd(window.arialDevice);
            if (lcdHold) clearTimeout(lcdHold);
            lcdHold = setTimeout(function () {
                lcdHold = null;
                pin = "";
                var el = document.getElementById("lcd-welcome");
                if (el && el._roll) {
                    clearInterval(el._roll);
                    el._roll = null;
                }
                if (el) el.textContent = "";
            }, 5000);
            rollText(document.getElementById("lcd-welcome"), "Welcome Pingoa");
            } else {
                beep();
                setWelcome("Invalid Code", 2000);
            }
    }

    function showDisarmed() {
        lastStatus = "System Ready";
        var st = document.getElementById("lcd-2");
        if (st) st.textContent = lastStatus;
        var lcd = document.querySelector(".lcd");
        if (lcd) {
            lcd.classList.remove("armed");
            lcd.classList.add("disarmed");
        }
        setLed(document.getElementById("led-status"), "disarmed");
    }

    function sendLiveAction(cmd) {
        var user = window.arialUser;
        if (!user || !user.code) {
            setWelcome("Enter Code", 2000);
            return;
        }
        fetch("/api/arial/keypad", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({ code: user.code, actionCmd: cmd, actionNum: 1 })
        }).then(function (res) {
            return res.json().then(function (data) {
                if (!res.ok) {
                    setWelcome((data && data.detail) || "Failed", 2000);
                    return;
                }
                loadStatus();
                setTimeout(loadStatus, 1200);
                setTimeout(loadStatus, 3000);
            });
        }).catch(function () {
            setWelcome("No Link", 2000);
        });
    }

    function onKey(key) {
        if (!key) return;
        var now = Date.now();
        if (key === onKey._k && now - onKey._t < 70) return;
        onKey._k = key;
        onKey._t = now;
        var willAccept = /^[0-9]$/.test(key) && pin.length === 3 && CODES[pin + key];
        if (key === "DISARM") disarmBeep();
        else if (!willAccept) beep();
        if (/^[0-9]$/.test(key)) {
            if (pin.length >= 4) {
                pin = key;
                setWelcome("*");
            } else {
                pin += key;
                if (pin.length === 4) submitPin();
                else setWelcome(new Array(pin.length + 1).join("*"));
            }
        } else if (key === "CLEAR") {
            pin = "";
            setWelcome("");
        } else if (key === "ENTER") {
            if (pin) submitPin();
        } else if (key === "DISARM") {
            if (window.arialUser && window.arialUser.code) showDisarmed();
            sendLiveAction("area-disarm");
        } else if (key === "ARM") {
            sendLiveAction("area-arm");
        } else if (key === "STAY") {
            sendLiveAction("area-stay");
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
        unlockAudio();
        onKey(btn.getAttribute("data-key"));
    });
    keypad.addEventListener("click", function (ev) {
        var btn = ev.target.closest("[data-key]");
        if (!btn) return;
        unlockAudio();
        onKey(btn.getAttribute("data-key"));
    });

    try {
        var saved = JSON.parse(sessionStorage.getItem("arialUser") || "null");
        if (saved && saved.logo) {
            if (!saved.code && saved.name === "Marc") saved.code = "7302";
            window.arialUser = saved;
            showUserLogo(saved);
        }
    } catch (e) {}

    tickTime();
    loadStatus();
    setInterval(tickTime, 1000);
    setInterval(loadStatus, 4000);
})();
