(function () {
    var STORE = "arialKeyClicks";
    var audioCtx = null;
    var lastStatus = "";
    var SITES = [
        { id: "hansekop", name: "HANSEKOP", linked: true },
        { id: "tuys", name: "TUYS", linked: false }
    ];
    var siteId = "hansekop";

    function currentSite() {
        var i;
        for (i = 0; i < SITES.length; i += 1) {
            if (SITES[i].id === siteId) return SITES[i];
        }
        return SITES[0];
    }

    function selectSite(id) {
        siteId = id || "hansekop";
        try { localStorage.setItem("arialSite", siteId); } catch (e) {}
        var s = currentSite();
        var siteEl = document.getElementById("lcd-site");
        if (siteEl) siteEl.textContent = s.name;
        if (!s.linked) {
            lastStatus = "Coming Soon";
            var stEl = document.getElementById("lcd-2");
            if (stEl) stEl.textContent = lastStatus;
            var lcd = document.querySelector(".lcd");
            if (lcd) lcd.classList.remove("armed", "disarmed", "arming", "arming-fast");
            setLed(document.getElementById("led-status"), "");
            syncArmToggle();
            return;
        }
        loadStatus();
    }

    function pad(n) {
        return String(n).padStart(2, "0");
    }

    function siteName(device) {
        var name = (device && device.deviceName) || "HANSEKOP";
        var parts = String(name).split(" - ");
        var site = (parts.length > 1 ? parts[parts.length - 1] : name).trim();
        return site.toUpperCase() || "HANSEKOP";
    }

    var EXIT_DEFAULT = 10;
    var pendingExitUntil = 0;
    var armPending = false;

    function areaState(device) {
        var areas = (device && device.arialAreas) || [];
        var i;
        for (i = 0; i < areas.length; i += 1) {
            if (areas[i] && areas[i].state) return String(areas[i].state).toLowerCase();
        }
        var raw = ((device && device.deviceState) || {}).areas || [];
        return raw.length ? String(raw[0] || "").toLowerCase() : "";
    }

    function exitDelaySecs(device) {
        var n = device && device.arialExitDelay;
        return (typeof n === "number" && n >= 10 && n <= 180) ? n : EXIT_DEFAULT;
    }

    function deviceCountdown(device) {
        var n = device && device.arialCountdown;
        if (typeof n === "number" && n > 0 && n <= 180) return Math.ceil(n);
        var areas = (device && device.arialAreas) || [];
        var i;
        for (i = 0; i < areas.length; i += 1) {
            var cd = areas[i] && areas[i].countdown;
            if (typeof cd === "number" && cd > 0 && cd <= 180) return Math.ceil(cd);
        }
        return 0;
    }

    function stampRemaining(device) {
        var delay = exitDelaySecs(device);
        var areas = (device && device.arialAreas) || [];
        var stamps = (((device && device.deviceState) || {}).areasStamp) || [];
        var now = Date.now();
        var i;
        for (i = 0; i < areas.length; i += 1) {
            var st = String((areas[i] && areas[i].state) || "").toLowerCase();
            if (st !== "countdown") continue;
            var stamp = areas[i].stamp != null ? areas[i].stamp : stamps[i];
            var ms = Number(stamp);
            if (!ms) continue;
            if (ms < 1e12) ms *= 1000;
            var left = Math.ceil(delay - (now - ms) / 1000);
            if (left > 0) return left > delay ? delay : left;
        }
        return 0;
    }

    function localExitLeft() {
        if (!pendingExitUntil) return 0;
        var s = Math.ceil((pendingExitUntil - Date.now()) / 1000);
        return s > 0 ? s : 0;
    }

    function startLocalExit(seconds) {
        var n = seconds && seconds > 0 ? seconds : EXIT_DEFAULT;
        pendingExitUntil = Date.now() + n * 1000;
    }

    function clearLocalExit() {
        pendingExitUntil = 0;
        armPending = false;
        maybeExitBeeps._done = false;
    }

    function syncLocalExitFromApi(seconds) {
        if (!(seconds > 0)) return;
        pendingExitUntil = Date.now() + seconds * 1000;
    }

    function isAlarmState(st) {
        return !!(st && st.indexOf("alarm") !== -1);
    }

    function isArmedState(st) {
        return st === "arm" || st === "stay" || st === "sleep" || isAlarmState(st);
    }

    function remainingExit(device) {
        var apiCd = deviceCountdown(device);
        if (apiCd) return apiCd;
        var stampCd = stampRemaining(device);
        if (stampCd) return stampCd;
        return localExitLeft();
    }

    function panelIsExiting(device) {
        var st = areaState(device);
        if (isArmedState(st) && st !== "countdown") return false;
        if (st === "countdown") return true;
        if (deviceCountdown(device) > 0) return true;
        if (stampRemaining(device) > 0) return true;
        if (localExitLeft() > 0 && (st === "disarm" || st === "notready" || !st)) return true;
        if (armPending && !isArmedState(st)) return true;
        return false;
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
        if (panelIsExiting(device)) {
            var left = remainingExit(device);
            return left ? ("Exit Delay " + left) : "Exit Delay";
        }
        if (!st) return "";
        if (isAlarmState(st)) return "ALARM";
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
        var arming = panelIsExiting(device);
        var armed = !arming && isArmedState(st);
        var disarmed = !arming && !armed && (st === "disarm" || st === "notready" || !st);
        lcd.classList.toggle("arming", arming);
        lcd.classList.toggle("armed", armed);
        lcd.classList.toggle("disarmed", disarmed);
        if (!arming) lcd.classList.remove("arming-fast");
        syncArmToggle();
    }

    function panelLooksArmed(device) {
        var d = device || window.arialDevice;
        var st = areaState(d);
        if (panelIsExiting(d)) return true;
        if (isArmedState(st)) return true;
        var lcd = document.querySelector(".lcd");
        return !!(lcd && (lcd.classList.contains("armed") || lcd.classList.contains("arming")));
    }

    function syncArmToggle() {
        var btn = document.getElementById("arm-toggle");
        var face = document.getElementById("arm-toggle-face");
        if (!btn) return;
        var armed = panelLooksArmed();
        btn.classList.remove("mode-arm", "mode-disarm", "to-arm", "to-disarm");
        if (armed) {
            btn.setAttribute("aria-label", "DISARM");
            btn.classList.add("to-disarm");
            if (face && face.tagName === "IMG") face.src = "/arial/btn-disarm.png?v=45";
        } else {
            btn.setAttribute("aria-label", "ARM");
            btn.classList.add("to-arm");
            if (face && face.tagName === "IMG") face.src = "/arial/btn-arm.png?v=45";
        }
    }

    function applyLeds(device) {
        var st = areaState(device);
        var apiCd = deviceCountdown(device);
        if (apiCd > 0) syncLocalExitFromApi(apiCd);
        var stampCd = stampRemaining(device);
        if (!apiCd && stampCd > 0 && localExitLeft() === 0) syncLocalExitFromApi(stampCd);

        if (isAlarmState(st)) {
            clearLocalExit();
            lastStatus = "ALARM";
            var alarmEl = document.getElementById("lcd-2");
            if (alarmEl) alarmEl.textContent = lastStatus;
            applyLcd(device);
            setLed(document.getElementById("led-status"), "armed flash-fast");
            return;
        }
        if (st === "arm" || st === "stay" || st === "sleep") {
            clearLocalExit();
            lastStatus = statusFromDevice(device);
            var armedEl = document.getElementById("lcd-2");
            if (armedEl) armedEl.textContent = lastStatus;
            applyLcd(device);
            setLed(document.getElementById("led-status"), "armed");
            return;
        }
        if (panelIsExiting(device)) {
            showArming(remainingExit(device));
            maybeExitBeeps();
            return;
        }
        clearLocalExit();
        lastStatus = statusFromDevice(device);
        var readyEl = document.getElementById("lcd-2");
        if (readyEl) readyEl.textContent = lastStatus;
        applyLcd(device);
        if (st === "notready") {
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
        if (currentSite().id !== "hansekop") return;
        if (loadStatus._busy) return;
        loadStatus._busy = true;
        try {
            var res = await fetch("/api/arial/panel", { credentials: "same-origin", cache: "no-store" });
            var data = await res.json();
            if (!res.ok) {
                document.getElementById("lcd-2").textContent = lastStatus || "No Link";
                return;
            }
            var hanse = data.device;
            if (!hanse) {
                document.getElementById("lcd-2").textContent = lastStatus || "No Device";
                return;
            }
            document.getElementById("lcd-site").textContent = siteName(hanse);
            window.arialDevice = hanse;
            applyLeds(hanse);
            lastStatus = document.getElementById("lcd-2").textContent || statusFromDevice(hanse);
            loadStatus._area = areaState(hanse);
            try {
                var lcd = document.querySelector(".lcd");
                localStorage.setItem("arialPanel", JSON.stringify({
                    lastStatus: lastStatus,
                    site: siteName(hanse),
                    armed: !!(lcd && lcd.classList.contains("armed")),
                    arming: !!(lcd && lcd.classList.contains("arming")),
                    disarmed: !!(lcd && lcd.classList.contains("disarmed"))
                }));
            } catch (e) {}
        } catch (e) {
            document.getElementById("lcd-2").textContent = lastStatus || "No Link";
        } finally {
            loadStatus._busy = false;
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
        "7302": { name: "Marc", from: "Pingoa", logo: "/arial/users/pingoa.png?v=43", code: "7302" },
        "7102": { name: "Amoroc", from: "Amoroc", logo: "/arial/users/amoroc.png?v=43", code: "7102" }
    };

    function resolvedUser(user) {
        if (!user) return null;
        if (user.code && CODES[user.code]) return CODES[user.code];
        if (/aerial/i.test(String(user.logo || user.name || ""))) return CODES["7102"];
        if (/amoroc/i.test(String(user.name || user.from || user.logo || ""))) return CODES["7102"];
        return user;
    }

    function setPadLoggedIn(on) {
        var frame = document.getElementById("pad-frame");
        if (frame) frame.classList.toggle("compact", !!on);
        var up = document.querySelector('[data-key="UP"]');
        if (up) {
            up.hidden = !on;
            up.setAttribute("aria-label", on ? "Log Out" : "Up");
        }
    }

    function logOut() {
        window.arialUser = null;
        pin = "";
        try { localStorage.removeItem("arialUser"); } catch (e) {}
        try { sessionStorage.removeItem("arialUser"); } catch (e) {}
        try { localStorage.removeItem("arialSite"); } catch (e) {}
        siteId = "hansekop";
        showUserLogo(null);
        setPadLoggedIn(false);
        setWelcome("");
        loadStatus();
    }

    function setLoggedIn(user) {
        user = resolvedUser(user);
        window.arialUser = user;
        try { localStorage.setItem("arialUser", JSON.stringify(user)); } catch (e) {}
        try { sessionStorage.removeItem("arialUser"); } catch (e) {}
        showUserLogo(user);
        setPadLoggedIn(!!(user && user.code));
        if (window.arialDevice) applyLeds(window.arialDevice);
    }

    function showUserLogo(user) {
        var lcd = document.querySelector(".lcd");
        var img = document.getElementById("lcd-user-logo");
        if (!lcd || !img) return;
        if (user && user.logo) {
            img.removeAttribute("hidden");
            img.style.display = "block";
            img.src = user.logo;
            img.alt = user.from || user.name || "";
            lcd.classList.add("logged-in");
        } else {
            img.removeAttribute("src");
            img.src = "";
            img.alt = "";
            img.style.display = "none";
            img.setAttribute("hidden", "");
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
        if (!AC) return Promise.resolve();
        if (!audioCtx) audioCtx = new AC();
        function prime() {
            try {
                var buf = audioCtx.createBuffer(1, 1, audioCtx.sampleRate || 22050);
                var src = audioCtx.createBufferSource();
                src.buffer = buf;
                src.connect(audioCtx.destination);
                src.start(0);
            } catch (e) {}
        }
        if (audioCtx.state === "suspended") {
            return audioCtx.resume().then(function () {
                prime();
            }).catch(function () {});
        }
        prime();
        return Promise.resolve();
    }

    function tone(freq, dur, peak) {
        function play() {
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
        var ready = unlockAudio();
        if (ready && typeof ready.then === "function") ready.then(play);
        else play();
    }

    function beep() {
        tone(2100, 0.09, 0.45);
    }

    function disarmBeep() {
        tone(1200, 0.95, 0.5);
    }

    function logoutBeep() {
        tone(1500, 0.11, 0.45);
        setTimeout(function () { tone(880, 0.2, 0.42); }, 120);
    }

    function showArmed() {
        lastStatus = "System Armed";
        var st = document.getElementById("lcd-2");
        if (st) st.textContent = lastStatus;
        var lcd = document.querySelector(".lcd");
        if (lcd) {
            lcd.classList.remove("disarmed", "arming", "arming-fast");
            lcd.classList.add("armed");
        }
        setLed(document.getElementById("led-status"), "armed");
        syncArmToggle();
    }

    function showArming(n) {
        lastStatus = n ? ("Exit Delay " + n) : "Exit Delay";
        var st = document.getElementById("lcd-2");
        if (st) st.textContent = lastStatus;
        var lcd = document.querySelector(".lcd");
        if (lcd) {
            lcd.classList.remove("armed", "disarmed", "arming-fast");
            lcd.classList.add("arming");
        }
        var led = document.getElementById("led-status");
        if (led && !led.classList.contains("arming")) {
            setLed(document.getElementById("led-status"), "arming");
        }
        syncArmToggle();
    }

    function maybeExitBeeps() {
        if (maybeExitBeeps._done) return;
        maybeExitBeeps._done = true;
        armBeeps();
    }

    function armBeeps(done) {
        if (armBeeps._run) return;
        armBeeps._run = true;
        unlockAudio();
        var gaps = [420, 320, 230, 140, 70];
        var n = 0;
        function ping() {
            tone(1600, 0.12, 0.55);
            n += 1;
            if (n >= 6) {
                armBeeps._run = false;
                if (done) done();
                return;
            }
            setTimeout(ping, gaps[n - 1]);
        }
        ping();
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
            setLoggedIn(user);
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
            rollText(document.getElementById("lcd-welcome"), "Welcome " + (user.from || user.name));
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
            lcd.classList.remove("armed", "arming", "arming-fast");
            lcd.classList.add("disarmed");
        }
        setLed(document.getElementById("led-status"), "disarmed");
        syncArmToggle();
    }

    function sendLiveAction(cmd) {
        var user = resolvedUser(window.arialUser);
        if (!user || !user.code) {
            setWelcome("Enter Code", 2000);
            return Promise.resolve(false);
        }
        if (!currentSite().linked) {
            setWelcome("Not Linked", 2000);
            return Promise.resolve(false);
        }
        return fetch("/api/arial/keypad", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({ code: user.code, actionCmd: cmd, actionNum: 1 })
        }).then(function (res) {
            return res.json().then(function (data) {
                if (!res.ok) {
                    setWelcome((data && data.detail) || "Failed", 2000);
                    return false;
                }
                loadStatus();
                setTimeout(loadStatus, 1200);
                setTimeout(loadStatus, 3000);
                return true;
            });
        }).catch(function () {
            setWelcome("No Link", 2000);
            return false;
        });
    }

    function doArm() {
        var user = resolvedUser(window.arialUser);
        if (!user || !user.code) {
            setWelcome("Enter Code", 2000);
            return;
        }
        if (!currentSite().linked) {
            setWelcome("Not Linked", 2000);
            return;
        }
        var delay = EXIT_DEFAULT;
        armPending = true;
        startLocalExit(delay);
        showArming(localExitLeft());
        maybeExitBeeps();
        sendLiveAction("area-arm").then(function (ok) {
            if (!ok) {
                clearLocalExit();
                loadStatus();
            }
        });
    }

    function doDisarm() {
        clearLocalExit();
        showDisarmed();
        sendLiveAction("area-disarm");
    }

    function onKey(key) {
        if (!key) return;
        var now = Date.now();
        if (key === onKey._k && now - onKey._t < 280) return;
        onKey._k = key;
        onKey._t = now;
        var willAccept = /^[0-9]$/.test(key) && pin.length === 3 && CODES[pin + key];
        var isArmed = panelLooksArmed(window.arialDevice);
        if ((key === "DISARM" || key === "TOGGLE") && isArmed) disarmBeep();
        else if (key === "ARM" || key === "TOGGLE" || (key === "DISARM" && !isArmed)) { /* panel countdown + beeps */ }
        else if (!willAccept && key !== "LOGOUT" && key !== "UP") beep();
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
        } else if (key === "DISARM" || key === "TOGGLE") {
            if (isArmed) doDisarm();
            else doArm();
        } else if (key === "ARM") {
            doArm();
        } else if (key === "STAY") {
            if (window.arialUser && window.arialUser.code) selectSite("hansekop");
            else sendLiveAction("area-stay");
        } else if (key === "FORCE") {
            if (window.arialUser && window.arialUser.code) selectSite("tuys");
        } else if (key === "UP" || key === "LOGOUT") {
            if (window.arialUser && window.arialUser.code) {
                logoutBeep();
                logOut();
            }
        }
        saveClick(key);
        if (typeof window.onArialKey === "function") window.onArialKey(key);
    }

    window.setArialLcd = function (top, bottom) {
        if (top != null) document.getElementById("lcd-site").textContent = String(top);
        if (bottom != null) document.getElementById("lcd-2").textContent = String(bottom);
    };

    window.arialClicks = loadClicks();

    var keypad = document.getElementById("pad-frame") || document.querySelector(".pad");
    keypad.addEventListener("pointerdown", function (ev) {
        var btn = ev.target.closest("[data-key]");
        if (!btn) return;
        var key = btn.getAttribute("data-key");
        unlockAudio().then(function () {
            onKey(key);
        });
    });

    try {
        var cached = JSON.parse(localStorage.getItem("arialPanel") || "null");
        if (cached) {
            lastStatus = cached.lastStatus || "";
            if (cached.site) document.getElementById("lcd-site").textContent = cached.site;
            if (lastStatus) document.getElementById("lcd-2").textContent = lastStatus;
            var lcd0 = document.querySelector(".lcd");
            if (lcd0) {
                lcd0.classList.toggle("armed", !!cached.armed);
                lcd0.classList.toggle("arming", !!cached.arming);
                lcd0.classList.toggle("disarmed", !!cached.disarmed);
            }
            if (cached.arming) setLed(document.getElementById("led-status"), "arming");
            else if (cached.armed) setLed(document.getElementById("led-status"), "armed");
            else if (cached.disarmed) setLed(document.getElementById("led-status"), "disarmed");
            syncArmToggle();
        }
    } catch (e) {}

    setPadLoggedIn(false);

    try {
        var saved = JSON.parse(localStorage.getItem("arialUser") || "null");
        if (!saved) saved = JSON.parse(sessionStorage.getItem("arialUser") || "null");
        if (saved) {
            if (!saved.code && /aerial/i.test(String(saved.logo || saved.name || ""))) saved.code = "7102";
            if (/aerial/i.test(String(saved.logo || ""))) saved.code = saved.code || "7102";
            if (!saved.code && saved.name === "Marc") saved.code = "7302";
            if (/amoroc/i.test(String(saved.name || saved.from || saved.logo || ""))) saved.code = "7102";
            if (saved.code && CODES[saved.code]) setLoggedIn(CODES[saved.code]);
        }
    } catch (e) {}

    try {
        var savedSite = localStorage.getItem("arialSite");
        if (window.arialUser && window.arialUser.code && (savedSite === "tuys" || savedSite === "hansekop")) {
            selectSite(savedSite);
        }
    } catch (e) {}

    tickTime();
    loadStatus();
    setInterval(tickTime, 1000);
    setInterval(function () {
        if (localExitLeft() > 0 || panelIsExiting(window.arialDevice)) loadStatus();
    }, 1000);
    setInterval(loadStatus, 4000);
    setInterval(function () {
        if (!localExitLeft()) return;
        var st = areaState(window.arialDevice);
        if (isArmedState(st)) return;
        showArming(localExitLeft());
    }, 250);
})();
