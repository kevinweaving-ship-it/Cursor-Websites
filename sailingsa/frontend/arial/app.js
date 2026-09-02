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
            stopIssueCycle();
            setLcdStatus("Coming Soon", "");
            var lcd = document.querySelector(".lcd");
            if (lcd) lcd.classList.remove("armed", "disarmed", "arming", "arming-fast", "zone-open");
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

    var EXIT_DEFAULT = 30;
    var EXIT_ACK_MS = 2500;
    var pendingExitUntil = 0;
    var armPending = false;
    var exitCountStarted = false;
    var exitClockFromApi = false;
    var disarmPending = false;
    var disarmNeedsStatus = false;
    var armWaitSince = 0;
    var exitIntroUntil = 0;
    var exitBeepTimer = null;
    var loginErrorUntil = 0;

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
        return (typeof n === "number" && n > 10 && n <= 180) ? n : EXIT_DEFAULT;
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

    function storeSet(k, v) {
        try { localStorage.setItem(k, v); } catch (e) {}
        try { sessionStorage.setItem(k, v); } catch (e2) {}
    }

    function storeGet(k) {
        try {
            var a = localStorage.getItem(k);
            if (a != null && a !== "") return a;
        } catch (e) {}
        try { return sessionStorage.getItem(k); } catch (e2) { return null; }
    }

    function storeDel(k) {
        try { localStorage.removeItem(k); } catch (e) {}
        try { sessionStorage.removeItem(k); } catch (e2) {}
    }

    function persistExit() {
        if (armPending) {
            storeSet("arialArmPending", "1");
            storeSet("arialExitStarted", exitCountStarted ? "1" : "0");
            if (pendingExitUntil) storeSet("arialExitUntil", String(pendingExitUntil));
            else storeDel("arialExitUntil");
            return;
        }
        storeDel("arialExitUntil");
        storeDel("arialArmPending");
        storeDel("arialExitStarted");
    }

    function startLocalExit(seconds) {
        var n = seconds && seconds > 0 ? seconds : EXIT_DEFAULT;
        pendingExitUntil = Date.now() + n * 1000;
        exitCountStarted = true;
        exitIntroUntil = 0;
        persistExit();
    }

    function inExitIntro() {
        return !!(exitIntroUntil && Date.now() < exitIntroUntil);
    }

    function stopExitBeeps() {
        if (exitBeepTimer) {
            clearTimeout(exitBeepTimer);
            exitBeepTimer = null;
        }
        startExitBeeps._on = false;
        startExitBeeps._lastSec = -1;
        maybeExitBeeps._done = false;
    }

    function clearLocalExit() {
        pendingExitUntil = 0;
        armPending = false;
        exitCountStarted = false;
        exitClockFromApi = false;
        armWaitSince = 0;
        exitIntroUntil = 0;
        longArmedBeep._done = false;
        stopExitBeeps();
        persistExit();
    }

    function stillExiting(device) {
        if (disarmPending) return false;
        if (localExitLeft() > 0) return true;
        if (armPending && exitCountStarted && pendingExitUntil && pendingExitUntil <= Date.now()) return false;
        if (deviceCountdown(device) > 0) return true;
        if (stampRemaining(device) > 0) return true;
        if (areaState(device) === "countdown") return true;
        if (armPending && !exitCountStarted) return true;
        return false;
    }

    function syncLocalExitFromApi(seconds) {
        if (!(seconds > 0)) return;
        var local = localExitLeft();
        if (!exitClockFromApi && seconds > 10) {
            exitClockFromApi = true;
            startLocalExit(seconds);
            return;
        }
        if (!local) {
            if (pendingExitUntil && pendingExitUntil <= Date.now()) {
                if (seconds <= 5) startLocalExit(seconds);
                return;
            }
            startLocalExit(seconds);
            return;
        }
        if (seconds < local - 1) {
            pendingExitUntil = Date.now() + seconds * 1000;
            persistExit();
            return;
        }
        if (Math.abs(local - seconds) <= 1) exitCountStarted = true;
    }

    function isAlarmState(st) {
        return !!(st && st.indexOf("alarm") !== -1);
    }

    function isArmedState(st) {
        return st === "arm" || st === "stay" || st === "sleep" || isAlarmState(st);
    }

    function remainingExit(device) {
        var apiCd = deviceCountdown(device);
        var stampCd = stampRemaining(device);
        if (apiCd > 0) syncLocalExitFromApi(apiCd);
        else if (stampCd > 0) syncLocalExitFromApi(stampCd);
        return localExitLeft() || apiCd || stampCd || 0;
    }

    function panelIsExiting(device) {
        if (disarmPending) return false;
        if (stillExiting(device)) return true;
        if (armPending && (localExitLeft() > 0 || !exitCountStarted)) return true;
        return false;
    }

    function zoneIsOpen(z) {
        var st = String((z && z.state) || "").toLowerCase();
        var lab = String((z && z.stateLabel) || "").toLowerCase();
        if (st === "c" || st === "closed" || lab === "closed") return false;
        if (st === "a" || st === "al" || st === "o" || st === "open") return true;
        if (st.indexOf("alarm") !== -1 || lab.indexOf("alarm") !== -1) return true;
        if (lab === "active" || lab === "open") return true;
        return false;
    }

    function openZoneIssues(device) {
        var out = [];
        var zones = (device && device.arialZones) || [];
        var i;
        for (i = 0; i < zones.length; i += 1) {
            var z = zones[i];
            if (!zoneIsOpen(z)) continue;
            var n = z.num != null ? z.num : (i + 1);
            out.push("Zone " + n + " Open");
        }
        return out;
    }

    function openZoneIssue(device) {
        var all = openZoneIssues(device);
        return all.length ? all[0] : "";
    }

    function openZoneLabel(device) {
        var zones = (device && device.arialZones) || [];
        var i;
        for (i = 0; i < zones.length; i += 1) {
            var z = zones[i];
            if (!zoneIsOpen(z)) continue;
            return String(z.label || ("Zone " + (z.num != null ? z.num : (i + 1)))).trim();
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
        if (st === "notready") return "System Not Ready";
        return st;
    }

    var lastIssue = "";
    var issueCycle = { i: 0, timer: null };

    function stopIssueCycle() {
        if (issueCycle.timer) {
            clearInterval(issueCycle.timer);
            issueCycle.timer = null;
        }
    }

    function showNextIssue() {
        var issues = openZoneIssues(window.arialDevice);
        if (!issues.length) {
            stopIssueCycle();
            setLcdStatus("System Ready", "");
            applyLcd(window.arialDevice);
            setLed(document.getElementById("led-status"), "disarmed");
            return;
        }
        issueCycle.i = (issueCycle.i + 1) % issues.length;
        setLcdStatus("System Not Ready", issues[issueCycle.i]);
    }

    function ensureIssueCycle() {
        var issues = openZoneIssues(window.arialDevice);
        if (!issues.length) {
            stopIssueCycle();
            return false;
        }
        if (issueCycle.i >= issues.length) issueCycle.i = 0;
        setLcdStatus("System Not Ready", issues[issueCycle.i]);
        if (!issueCycle.timer) {
            issueCycle.timer = setInterval(showNextIssue, 1150);
        }
        return true;
    }

    function setLcdStatus(main, issue) {
        if (main != null) lastStatus = String(main);
        lastIssue = issue ? String(issue) : "";
        var mainEl = document.getElementById("lcd-status-main");
        var issueEl = document.getElementById("lcd-status-issue");
        if (mainEl) mainEl.textContent = lastStatus || "";
        else {
            var box = document.getElementById("lcd-2");
            if (box) box.textContent = lastStatus || "";
        }
        if (issueEl) {
            issueEl.textContent = lastIssue;
            if (lastIssue) issueEl.removeAttribute("hidden");
            else issueEl.setAttribute("hidden", "");
        }
        fitLcdStatus();
    }

    function setLed(el, mode) {
        if (!el) return;
        var kind = el.classList.contains("ac") ? "led ac" : "led status";
        el.className = kind + (mode ? " " + mode : "");
    }

    function applyLcd(device) {
        var lcd = document.querySelector(".lcd");
        if (!lcd) return;
        if (Date.now() < loginErrorUntil) {
            lcd.classList.add("login-error");
            syncArmToggle();
            fitLcdStatus();
            return;
        }
        lcd.classList.remove("login-error");
        if (disarmPending && isLoggedIn()) {
            lcd.classList.remove("arming", "armed", "arming-fast", "zone-open");
            lcd.classList.add("disarmed", "hold-disarmed");
            syncArmToggle();
            fitLcdStatus();
            return;
        }
        lcd.classList.remove("hold-disarmed");
        var st = areaState(device);
        var arming = stillExiting(device) || (armPending && (localExitLeft() > 0 || !exitCountStarted));
        var armed = !arming && isArmedState(st);
        var zoneOpen = !arming && !armed && openZoneIssues(device).length > 0;
        var disarmed = !arming && !armed && (st === "disarm" || st === "notready" || !st);
        lcd.classList.toggle("arming", arming);
        lcd.classList.toggle("armed", armed);
        lcd.classList.toggle("disarmed", disarmed);
        lcd.classList.toggle("zone-open", zoneOpen);
        if (!arming) lcd.classList.remove("arming-fast");
        syncArmToggle();
        fitLcdStatus();
    }

    function fitLcdStatus() {
        var el = document.getElementById("lcd-status-main") || document.getElementById("lcd-2");
        var box = document.getElementById("lcd-2") || el;
        if (!el || !box) return;
        var w = box.clientWidth;
        var size = 32;
        el.style.fontSize = size + "px";
        if (box !== el) box.style.fontSize = size + "px";
        if (w < 12) return;
        var n = 0;
        while (n < 16 && size > 22 && el.scrollWidth > w + 1) {
            size -= 1;
            el.style.fontSize = size + "px";
            if (box !== el) box.style.fontSize = size + "px";
            n += 1;
        }
        var issueEl = document.getElementById("lcd-status-issue");
        if (issueEl && issueEl.textContent) {
            var iz = 16;
            issueEl.style.fontSize = iz + "px";
            n = 0;
            while (n < 12 && iz > 10 && issueEl.scrollWidth > w + 1) {
                iz -= 1;
                issueEl.style.fontSize = iz + "px";
                n += 1;
            }
        }
    }

    function panelLooksArmed(device) {
        if (disarmPending) return false;
        if (armPending || localExitLeft() > 0) return true;
        var d = device || window.arialDevice;
        if (panelIsExiting(d)) return true;
        var st = areaState(d);
        if (isAlarmState(st) || isArmedState(st)) return true;
        if (st === "disarm" || st === "notready") return false;
        var main = String(lastStatus || "").toLowerCase();
        if (main.indexOf("exit delay") !== -1 || main === "alarm") return true;
        if (/\barmed\b/.test(main) && main.indexOf("disarm") === -1) return true;
        if (main.indexOf("ready") !== -1 || main.indexOf("disarm") !== -1 || main.indexOf("coming") !== -1) return false;
        return false;
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
            btn.setAttribute("data-armed", "1");
            if (face && face.tagName === "IMG") face.src = "/arial/btn-disarm.png?v=45";
        } else {
            btn.setAttribute("aria-label", "ARM");
            btn.classList.add("to-arm");
            btn.setAttribute("data-armed", "0");
            if (face && face.tagName === "IMG") face.src = "/arial/btn-arm.png?v=45";
        }
    }

    function applyLeds(device) {
        if (Date.now() < loginErrorUntil) {
            showLoginError(true);
            syncArmToggle();
            return;
        }
        var st = areaState(device);
        var apiCd = deviceCountdown(device);
        if (apiCd > 0) syncLocalExitFromApi(apiCd);
        var stampCd = stampRemaining(device);
        if (!apiCd && stampCd > 0) syncLocalExitFromApi(stampCd);

        if (isAlarmState(st)) {
            if (disarmPending) {
                showSystemDisarmed();
                return;
            }
            clearLocalExit();
            stopIssueCycle();
            setLcdStatus("ALARM", "");
            applyLcd(device);
            setLed(document.getElementById("led-status"), "armed flash-fast");
            return;
        }
        if (disarmPending && !isLoggedIn()) {
            disarmPending = false;
            disarmNeedsStatus = false;
        }
        if (disarmPending) {
            var confirmed = (st === "disarm" || st === "notready");
            if (confirmed && disarmNeedsStatus) {
                disarmPending = false;
                disarmNeedsStatus = false;
            } else if (confirmed) {
                disarmNeedsStatus = true;
                showSystemDisarmed();
                setTimeout(loadStatus, 200);
                return;
            } else {
                showSystemDisarmed();
                return;
            }
        }
        if (stillExiting(device) || (armPending && !exitCountStarted)) {
            stopIssueCycle();
            showArming(remainingExit(device) || localExitLeft());
            maybeExitBeeps();
            return;
        }
        if (armPending && exitCountStarted && localExitLeft() === 0) {
            if (!armWaitSince) armWaitSince = Date.now();
            if (Date.now() - armWaitSince < EXIT_ACK_MS) {
                showArming(0);
                return;
            }
            showArmed();
            clearLocalExit();
            return;
        }
        if (st === "arm" || st === "stay" || st === "sleep") {
            clearLocalExit();
            stopIssueCycle();
            setLcdStatus(statusFromDevice(device), "");
            applyLcd(device);
            setLed(document.getElementById("led-status"), "armed");
            return;
        }
        clearLocalExit();
        if (ensureIssueCycle()) {
            applyLcd(device);
            setLed(document.getElementById("led-status"), "disarmed flash");
        } else {
            var readyLabel = statusFromDevice(device);
            if (readyLabel === "System Not Ready") readyLabel = "System Ready";
            setLcdStatus(readyLabel, "");
            applyLcd(device);
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

    function applyPanelDevice(hanse) {
        if (!hanse) return;
        var siteEl = document.getElementById("lcd-site");
        if (siteEl) siteEl.textContent = siteName(hanse);
        window.arialDevice = hanse;
        applyLeds(hanse);
        lastStatus = (document.getElementById("lcd-status-main") || {}).textContent || statusFromDevice(hanse);
        loadStatus._area = areaState(hanse);
        try {
            var lcd = document.querySelector(".lcd");
            localStorage.setItem("arialPanel", JSON.stringify({
                lastStatus: lastStatus,
                lastIssue: lastIssue,
                site: siteName(hanse),
                armed: !!(lcd && lcd.classList.contains("armed")),
                arming: !!(lcd && lcd.classList.contains("arming")),
                disarmed: !!(lcd && lcd.classList.contains("disarmed")),
                zoneOpen: !!(lcd && lcd.classList.contains("zone-open"))
            }));
        } catch (e) {}
    }

    function startOlarmLive() {
        if (startOlarmLive._es) return;
        if (typeof EventSource === "undefined") return;
        try {
            var es = new EventSource("/api/arial/live");
            startOlarmLive._es = es;
            es.onmessage = function (ev) {
                try {
                    var data = JSON.parse(ev.data || "{}");
                    if (data && data.device) applyPanelDevice(data.device);
                } catch (err) {}
            };
        } catch (e2) {}
    }

    async function loadStatus() {
        if (currentSite().id !== "hansekop") return;
        if (loadStatus._busy) return;
        loadStatus._busy = true;
        try {
            var res = await fetch("/api/arial/panel", { credentials: "same-origin", cache: "no-store" });
            var data = await res.json();
            if (!res.ok) {
                setLcdStatus(lastStatus || "No Link", lastIssue);
                return;
            }
            var hanse = data.device;
            if (!hanse) {
                setLcdStatus(lastStatus || "No Device", lastIssue);
                return;
            }
            applyPanelDevice(hanse);
        } catch (e) {
            setLcdStatus(lastStatus || "No Link", lastIssue);
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
            img.style.display = "";
            img.src = user.logo;
            img.alt = user.from || user.name || "";
            lcd.classList.add("logged-in");
        } else {
            img.removeAttribute("src");
            img.src = "";
            img.alt = "";
            img.style.display = "";
            img.setAttribute("hidden", "");
            lcd.classList.remove("logged-in");
            lcd.classList.remove("credits-playing");
            lcd.classList.remove("logo-in");
        }
    }

    function setWelcome(text, holdMs) {
        var el = document.getElementById("lcd-welcome");
        stopWelcomeCredits(el);
        if (el) el.textContent = text || "";
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
        if (AC) {
            if (!audioCtx) audioCtx = new AC();
            if (audioCtx.state === "suspended") {
                try {
                    var p = audioCtx.resume();
                    if (p && p.then) {
                        p.then(function () {
                            startExitBeeps._lastSec = -1;
                            startExitBeeps._nextFast = 0;
                            maybeExitBeeps();
                        }).catch(function () {});
                    }
                } catch (e) {}
            }
            if (!unlockAudio._primed) {
                try {
                    var buf = audioCtx.createBuffer(1, 1, audioCtx.sampleRate || 22050);
                    var src = audioCtx.createBufferSource();
                    src.buffer = buf;
                    src.connect(audioCtx.destination);
                    src.start(0);
                    unlockAudio._primed = true;
                } catch (e2) {}
            }
        }
        var beepEl = document.getElementById("key-beep");
        if (beepEl && !unlockAudio._html) {
            try { beepEl.load(); } catch (e3) {}
            unlockAudio._html = true;
        }
        var rejEl = document.getElementById("key-reject");
        if (rejEl && !unlockAudio._rej) {
            try { rejEl.load(); } catch (e4) {}
            unlockAudio._rej = true;
        }
        loadPinOkBuffer();
        loadRejectBuffer();
    }

    function playOsc(freq, dur, peak, solid) {
        if (!audioCtx) return;
        try {
            var t = audioCtx.currentTime;
            if (!(t > 0.001)) t += 0.02;
            var osc = audioCtx.createOscillator();
            var gain = audioCtx.createGain();
            var vol = peak || 0.38;
            osc.type = "square";
            osc.frequency.setValueAtTime(freq, t);
            gain.gain.setValueAtTime(0.0001, t);
            gain.gain.exponentialRampToValueAtTime(vol, t + 0.015);
            if (solid) {
                gain.gain.setValueAtTime(vol, t + Math.max(0.05, dur - 0.07));
                gain.gain.exponentialRampToValueAtTime(0.0001, t + dur);
            } else {
                gain.gain.exponentialRampToValueAtTime(0.0001, t + dur);
            }
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            osc.start(t);
            osc.stop(t + dur + 0.03);
        } catch (e) {}
    }

    function playHtmlBeep() {
        var el = document.getElementById("key-beep");
        if (!el) return false;
        try {
            el.pause();
            try { el.currentTime = 0; } catch (e2) {}
            el.volume = 0.85;
            var p = el.play();
            if (p && p.catch) p.catch(function () { playOsc(2100, 0.09, 0.45); });
            return true;
        } catch (e) {
            return false;
        }
    }

    function playExitChirp(fast) {
        unlockAudio();
        if (audioCtx && audioCtx.state === "running") {
            playOsc(1600, fast ? 0.08 : 0.11, fast ? 0.52 : 0.45);
            return;
        }
        playHtmlBeep();
    }

    function kickExitAudio() {
        unlockAudio();
        maybeExitBeeps();
    }

    function tone(freq, dur, peak) {
        unlockAudio();
        playOsc(freq, dur, peak);
    }

    function beep() {
        unlockAudio();
        playOsc(2100, 0.09, 0.45);
        if (!audioCtx || audioCtx.state !== "running") playHtmlBeep();
    }

    function disarmBeep() {
        if (disarmBeep._on) return;
        disarmBeep._on = true;
        unlockAudio();
        var start = Date.now();
        function ping() {
            tone(1400, 0.12, 0.58);
            if (Date.now() - start + 333 <= 2500) setTimeout(ping, 333);
            else disarmBeep._on = false;
        }
        ping();
    }

    function logoutBeep() {
        tone(1500, 0.11, 0.45);
        setTimeout(function () { tone(880, 0.2, 0.42); }, 120);
    }

    function showArmed() {
        stopIssueCycle();
        longArmedBeep();
        setLcdStatus("System Armed", "");
        var lcd = document.querySelector(".lcd");
        if (lcd) {
            lcd.classList.remove("disarmed", "arming", "arming-fast", "zone-open", "hold-disarmed");
            lcd.classList.add("armed");
        }
        setLed(document.getElementById("led-status"), "armed");
        syncArmToggle();
        fitLcdStatus();
    }

    function showArming(n) {
        stopIssueCycle();
        var intro = inExitIntro();
        setLcdStatus((!intro && n) ? ("Exit Delay " + n) : "Exit Delay", "");
        var lcd = document.querySelector(".lcd");
        if (lcd) {
            lcd.classList.remove("armed", "disarmed", "zone-open", "hold-disarmed");
            lcd.classList.add("arming");
            if (!intro && n && n <= 7) lcd.classList.add("arming-fast");
            else lcd.classList.remove("arming-fast");
        }
        var led = document.getElementById("led-status");
        if (led && !led.classList.contains("arming")) {
            setLed(document.getElementById("led-status"), "arming");
        }
        persistExit();
        syncArmToggle();
        fitLcdStatus();
    }

    function maybeExitBeeps() {
        if (!armPending && localExitLeft() <= 0) return;
        var left = remainingExit(window.arialDevice) || localExitLeft();
        if (left <= 0) return;
        if (startExitBeeps._on && !exitBeepTimer) startExitBeeps._on = false;
        startExitBeeps();
    }

    function startExitBeeps() {
        if (startExitBeeps._on) return;
        startExitBeeps._on = true;
        startExitBeeps._lastSec = -1;
        startExitBeeps._nextFast = 0;
        unlockAudio();
        function tick() {
            var left = remainingExit(window.arialDevice) || localExitLeft();
            if (left <= 0) {
                startExitBeeps._on = false;
                exitBeepTimer = null;
                return;
            }
            if (left > 20) {
                startExitBeeps._lastSec = left;
                exitBeepTimer = setTimeout(tick, 40);
                return;
            }
            if (left > 7) {
                if (left !== startExitBeeps._lastSec) {
                    startExitBeeps._lastSec = left;
                    playExitChirp(false);
                }
                exitBeepTimer = setTimeout(tick, 40);
                return;
            }
            var now = Date.now();
            if (now >= startExitBeeps._nextFast) {
                startExitBeeps._nextFast = now + 500;
                playExitChirp(true);
            }
            exitBeepTimer = setTimeout(tick, 40);
        }
        tick();
    }

    function longArmedBeep() {
        if (longArmedBeep._done) return;
        longArmedBeep._done = true;
        stopExitBeeps();
        unlockAudio();
        playOsc(1000, 2.0, 0.72, true);
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

    function stopWelcomeCredits(el) {
        el = el || document.getElementById("lcd-welcome");
        if (!el) return;
        if (el._roll) {
            clearInterval(el._roll);
            el._roll = null;
        }
        if (el._hold) {
            clearTimeout(el._hold);
            el._hold = null;
        }
        if (el._fade) {
            clearTimeout(el._fade);
            el._fade = null;
        }
        if (el._logo) {
            clearTimeout(el._logo);
            el._logo = null;
        }
        if (el._status) {
            clearTimeout(el._status);
            el._status = null;
        }
        el.classList.remove("credits", "credit-out", "credit-across");
        el.style.opacity = "";
        el.style.transform = "";
        el.style.clipPath = "";
        el.style.transition = "";
        el.style.removeProperty("--welcome-x");
        var lcd = document.querySelector(".lcd");
        if (lcd) {
            lcd.classList.remove("credits-playing");
            lcd.classList.remove("hero-credits");
        }
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

    function playWelcomeCredits() {
        var el = document.getElementById("lcd-welcome");
        if (!el) return;
        stopWelcomeCredits(el);
        var lcd = document.querySelector(".lcd");
        if (lcd) {
            lcd.classList.add("credits-playing");
            lcd.classList.add("hero-credits");
            lcd.classList.remove("logo-in");
        }
        function revealLogo() {
            if (!lcd) return;
            lcd.classList.remove("credits-playing");
            lcd.classList.remove("logo-in");
            void lcd.offsetWidth;
            lcd.classList.add("logo-in");
            var img = document.getElementById("lcd-user-logo");
            var shown = false;
            function showStatus() {
                if (shown) return;
                shown = true;
                lcd.classList.remove("hero-credits");
                fitLcdStatus();
            }
            function afterLogo() {
                if (el._status) clearTimeout(el._status);
                el._status = setTimeout(function () {
                    el._status = null;
                    showStatus();
                }, 500);
            }
            if (img) {
                img.addEventListener("animationend", function onEnd(ev) {
                    if (ev.animationName && ev.animationName.indexOf("logoRollIn") === -1) return;
                    img.removeEventListener("animationend", onEnd);
                    afterLogo();
                });
            }
            if (el._status) clearTimeout(el._status);
            el._status = setTimeout(afterLogo, 1600);
        }
        el.classList.add("credits");
        el.classList.remove("credit-out", "credit-across");
        el.textContent = "WELCOME";
        el.style.opacity = "1";
        el.style.removeProperty("--welcome-x");
        void el.offsetWidth;
        var travel = 0;
        if (lcd) travel = Math.max(0, lcd.clientWidth - el.offsetWidth - 12);
        el.style.setProperty("--welcome-x", travel + "px");
        void el.offsetWidth;
        el.classList.add("credit-across");
        el._hold = setTimeout(function () {
            el._hold = null;
            el.classList.add("credit-out");
            el.classList.remove("credit-across");
            el._fade = setTimeout(function () {
                el._fade = null;
                revealLogo();
            }, 220);
            el._logo = setTimeout(function () {
                el._logo = null;
                el.classList.remove("credits", "credit-out", "credit-across");
                el.textContent = "";
                el.style.opacity = "";
                el.style.transform = "";
                el.style.removeProperty("--welcome-x");
            }, 900);
        }, 2200);
    }
    var pinOkBuf = null;
    var rejectBuf = null;

    function loadPinOkBuffer() {
        if (pinOkBuf || !audioCtx || loadPinOkBuffer._busy) return;
        loadPinOkBuffer._busy = true;
        fetch("/arial/pin-accepted.wav", { credentials: "same-origin" }).then(function (res) {
            return res.arrayBuffer();
        }).then(function (ab) {
            return audioCtx.decodeAudioData(ab);
        }).then(function (buf) {
            pinOkBuf = buf;
        }).catch(function () {
            loadPinOkBuffer._busy = false;
        });
    }

    function pinAccepted() {
        unlockAudio();
        if (pinOkBuf && audioCtx) {
            try {
                var src = audioCtx.createBufferSource();
                var gain = audioCtx.createGain();
                src.buffer = pinOkBuf;
                gain.gain.setValueAtTime(0.9, audioCtx.currentTime);
                src.connect(gain);
                gain.connect(audioCtx.destination);
                src.start(0);
                return;
            } catch (e) {}
        }
        pinOk = pinOk || document.getElementById("pin-ok") || new Audio("/arial/pin-accepted.wav");
        try { pinOk.pause(); } catch (e2) {}
        try { pinOk.currentTime = 0; } catch (e3) {}
        pinOk.muted = false;
        var p = pinOk.play();
        if (p && p.catch) p.catch(function () { beep(); });
    }

    function submitPin() {
        var user = CODES[pin];
        pin = "";
        if (user) {
            loadPinOkBuffer();
            setTimeout(pinAccepted, 1000);
            setLoggedIn(user);
            if (lcdHold) clearTimeout(lcdHold);
            lcdHold = null;
            playWelcomeCredits();
            } else {
                beep();
                setWelcome("Invalid Code", 2000);
            }
    }

    function showDisarmed() {
        if (ensureIssueCycle()) {
            var lcdBusy = document.querySelector(".lcd");
            if (lcdBusy) {
                lcdBusy.classList.remove("armed", "arming", "arming-fast", "hold-disarmed");
                lcdBusy.classList.add("disarmed", "zone-open");
            }
            setLed(document.getElementById("led-status"), "disarmed flash");
            syncArmToggle();
            return;
        }
        stopIssueCycle();
        setLcdStatus("System Ready", "");
        var lcd = document.querySelector(".lcd");
        if (lcd) {
            lcd.classList.remove("armed", "arming", "arming-fast", "zone-open", "hold-disarmed");
            lcd.classList.add("disarmed");
        }
        setLed(document.getElementById("led-status"), "disarmed");
        syncArmToggle();
        fitLcdStatus();
    }

    function loadRejectBuffer() {
        if (rejectBuf || !audioCtx || loadRejectBuffer._busy) return;
        loadRejectBuffer._busy = true;
        fetch("/arial/key-reject.wav?v=151", { credentials: "same-origin" }).then(function (res) {
            return res.arrayBuffer();
        }).then(function (ab) {
            return audioCtx.decodeAudioData(ab);
        }).then(function (buf) {
            rejectBuf = buf;
        }).catch(function () {
            loadRejectBuffer._busy = false;
        });
    }

    function rejectGong() {
        if (rejectGong._on) return;
        rejectGong._on = true;
        unlockAudio();
        loadRejectBuffer();
        if (rejectBuf && audioCtx) {
            try {
                var src = audioCtx.createBufferSource();
                var gain = audioCtx.createGain();
                src.buffer = rejectBuf;
                gain.gain.setValueAtTime(1.0, audioCtx.currentTime);
                src.connect(gain);
                gain.connect(audioCtx.destination);
                src.start(0);
                setTimeout(function () { rejectGong._on = false; }, 1200);
                return;
            } catch (e) {}
        }
        var el = document.getElementById("key-reject");
        if (el) {
            try {
                el.pause();
                try { el.currentTime = 0; } catch (e2) {}
                el.volume = 1.0;
                var p = el.play();
                if (p && p.catch) p.catch(function () { playOsc(2100, 1.05, 0.95, true); });
                setTimeout(function () { rejectGong._on = false; }, 1200);
                return;
            } catch (e3) {}
        }
        playOsc(2100, 1.05, 0.95, true);
        setTimeout(function () { rejectGong._on = false; }, 1200);
    }

    function isLoggedIn() {
        var u = resolvedUser(window.arialUser);
        return !!(u && u.code);
    }

    function showLoginError() {
        stopIssueCycle();
        var d = window.arialDevice;
        var main = lastStatus || "";
        if (!main || /^login$/i.test(main)) main = statusFromDevice(d) || "System Ready";
        if (main === "System Armed" && d && !isArmedState(areaState(d)) && !panelIsExiting(d)) {
            main = statusFromDevice(d) || "System Ready";
        }
        setLcdStatus(main, "Login");
        var lcd = document.querySelector(".lcd");
        if (lcd) lcd.classList.add("login-error");
        syncArmToggle();
        fitLcdStatus();
    }

    function rejectNeedLogin() {
        rejectGong();
        loginErrorUntil = Date.now() + 2200;
        showLoginError();
        if (rejectNeedLogin._t) clearTimeout(rejectNeedLogin._t);
        rejectNeedLogin._t = setTimeout(function () {
            rejectNeedLogin._t = null;
            loginErrorUntil = 0;
            var lcd = document.querySelector(".lcd");
            if (lcd) lcd.classList.remove("login-error");
            if (window.arialDevice) applyLeds(window.arialDevice);
            setWelcome("");
        }, 2200);
    }

    function requireLogin() {
        if (isLoggedIn()) return true;
        rejectNeedLogin();
        return false;
    }

    function sendLiveAction(cmd) {
        var user = resolvedUser(window.arialUser);
        if (!user || !user.code) {
            rejectNeedLogin();
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
                if (data && data.device) applyPanelDevice(data.device);
                loadStatus();
                setTimeout(loadStatus, 400);
                setTimeout(loadStatus, 1200);
                setTimeout(loadStatus, 2800);
                return true;
            });
        }).catch(function () {
            setWelcome("No Link", 2000);
            return false;
        });
    }

    function doArm() {
        if (!requireLogin()) return;
        if (!currentSite().linked) {
            setWelcome("Not Linked", 2000);
            return;
        }
        armPending = true;
        exitCountStarted = false;
        pendingExitUntil = 0;
        armWaitSince = 0;
        longArmedBeep._done = false;
        exitClockFromApi = false;
        disarmPending = false;
        disarmNeedsStatus = false;
        exitIntroUntil = Date.now() + 20000;
        persistExit();
        showArming(0);
        unlockAudio();
        tone(1600, 0.14, 0.55);
        sendLiveAction("area-arm").then(function (ok) {
            if (!ok) {
                clearLocalExit();
                loadStatus();
                return;
            }
            var apiCd = deviceCountdown(window.arialDevice);
            var delay = exitDelaySecs(window.arialDevice);
            if (apiCd > 10) {
                exitClockFromApi = true;
                startLocalExit(apiCd);
            } else if (!exitCountStarted) startLocalExit(delay);
            showArming(remainingExit(window.arialDevice) || localExitLeft());
            maybeExitBeeps();
        });
    }

    function showSystemDisarmed() {
        if (!isLoggedIn()) {
            rejectNeedLogin();
            return;
        }
        stopIssueCycle();
        setLcdStatus("System Disarmed", "");
        var lcd = document.querySelector(".lcd");
        if (lcd) {
            lcd.classList.remove("armed", "arming", "arming-fast", "zone-open", "login-error");
            lcd.classList.add("disarmed", "hold-disarmed");
        }
        setLed(document.getElementById("led-status"), "disarmed flash");
        syncArmToggle();
        fitLcdStatus();
    }

    function doDisarm() {
        if (!requireLogin()) return;
        disarmBeep();
        disarmPending = true;
        disarmNeedsStatus = false;
        clearLocalExit();
        showSystemDisarmed();
        sendLiveAction("area-disarm").then(function (ok) {
            if (!ok) {
                disarmPending = false;
                disarmNeedsStatus = false;
                loadStatus();
            }
        });
    }

    function onKey(key) {
        if (!key) return;
        var now = Date.now();
        if (key === onKey._k && now - onKey._t < 280) return;
        onKey._k = key;
        onKey._t = now;
        var isArmed = panelLooksArmed(window.arialDevice);
        if (disarmPending && (key === "DISARM" || key === "TOGGLE" || key === "ARM")) {
            saveClick(key);
            if (typeof window.onArialKey === "function") window.onArialKey(key);
            return;
        }
        if ((key === "DISARM" || key === "TOGGLE" || key === "ARM") && !isLoggedIn()) {
            rejectNeedLogin();
            saveClick(key);
            if (typeof window.onArialKey === "function") window.onArialKey(key);
            return;
        }
        if ((key === "DISARM" || key === "TOGGLE") && isArmed && isLoggedIn()) {
            unlockAudio();
            disarmBeep();
        }
        else if (key === "ARM" || key === "TOGGLE" || (key === "DISARM" && !isArmed)) { /* panel countdown + beeps */ }
        else if (key !== "LOGOUT" && key !== "UP") beep();
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
        if (bottom != null) setLcdStatus(String(bottom), "");
    };

    window.arialClicks = loadClicks();

    var keypad = document.getElementById("pad-frame") || document.querySelector(".pad");
    keypad.addEventListener("pointerdown", function () {
        unlockAudio();
    }, true);
    keypad.addEventListener("pointerdown", function (ev) {
        var btn = ev.target.closest("[data-key]");
        if (!btn) return;
        unlockAudio();
        onKey(btn.getAttribute("data-key"));
    });

    try {
        var cached = JSON.parse(localStorage.getItem("arialPanel") || "null");
        if (cached) {
            lastStatus = cached.lastStatus || "";
            if (cached.site) document.getElementById("lcd-site").textContent = cached.site;
            if (lastStatus) setLcdStatus(lastStatus, cached.lastIssue || "");
            var lcd0 = document.querySelector(".lcd");
            if (lcd0) {
                lcd0.classList.toggle("armed", !!cached.armed);
                lcd0.classList.toggle("arming", !!cached.arming);
                lcd0.classList.toggle("disarmed", !!cached.disarmed);
                lcd0.classList.toggle("zone-open", !!cached.zoneOpen);
            }
            if (cached.arming) setLed(document.getElementById("led-status"), "arming");
            else if (cached.armed) setLed(document.getElementById("led-status"), "armed");
            else if (cached.zoneOpen) setLed(document.getElementById("led-status"), "disarmed flash");
            else if (cached.disarmed) setLed(document.getElementById("led-status"), "disarmed");
            syncArmToggle();
            fitLcdStatus();
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

    try {
        var until = Number(storeGet("arialExitUntil") || 0);
        var pending = storeGet("arialArmPending") === "1";
        exitCountStarted = storeGet("arialExitStarted") === "1";
        if (pending && until > Date.now()) {
            pendingExitUntil = until;
            armPending = true;
            exitCountStarted = true;
            exitClockFromApi = true;
            exitIntroUntil = 0;
            showArming(localExitLeft());
            startExitBeeps();
            kickExitAudio();
        } else if (pending && until && until <= Date.now() && until > Date.now() - 8000) {
            armPending = true;
            exitCountStarted = true;
            pendingExitUntil = until;
            showArmed();
        } else if (pending && !exitCountStarted) {
            armPending = true;
            exitIntroUntil = Date.now() + 20000;
            showArming(0);
        }
    } catch (e2) {}

    window.addEventListener("pageshow", kickExitAudio);
    document.addEventListener("visibilitychange", function () {
        if (!document.hidden) kickExitAudio();
    });
    document.addEventListener("pointerdown", kickExitAudio, true);
    document.addEventListener("keydown", kickExitAudio, true);
    tickTime();
    loadStatus();
    startOlarmLive();
    fitLcdStatus();
    window.addEventListener("resize", fitLcdStatus);
    setInterval(tickTime, 1000);
    setInterval(function () {
        if (localExitLeft() > 0 || disarmPending || armPending || panelIsExiting(window.arialDevice)) loadStatus();
    }, 1000);
    setInterval(syncArmToggle, 400);
    setInterval(function () {
        if (disarmPending) return;
        if (armPending && exitCountStarted && localExitLeft() === 0) return;
        maybeExitBeeps();
        if (!(armPending || localExitLeft() > 0 || panelIsExiting(window.arialDevice))) return;
        showArming(remainingExit(window.arialDevice) || localExitLeft());
    }, 250);
})();
