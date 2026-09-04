(function () {
    // Per-URL config (set inline in index.html). Same app serves /arial (Hansekop) and /voelklip (Home).
    var CFG = window.ARIAL_CONFIG || {};
    var API = String(CFG.apiBase || "/api/arial").replace(/\/$/, "");
    var SITE_ID = String(CFG.siteId || "hansekop");
    var SITE_LABEL = String(CFG.siteLabel || "HANSEKOP");
    var SITE_TUYA = CFG.tuya !== false;
    var STORE = "arialKeyClicks" + (SITE_ID === "hansekop" ? "" : "." + SITE_ID);
    var audioCtx = null;
    var lastStatus = "";
    var SITES = [
        { id: SITE_ID, name: SITE_LABEL, linked: true },
        { id: "tuys", name: "TUYS", linked: false }
    ];
    var siteId = SITE_ID;

    function currentSite() {
        var i;
        for (i = 0; i < SITES.length; i += 1) {
            if (SITES[i].id === siteId) return SITES[i];
        }
        return SITES[0];
    }

    function selectSite(id) {
        siteId = id || SITE_ID;
        try { localStorage.setItem(siteKey("arialSite"), siteId); } catch (e) {}
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
        // The keypad shows the configured site label (HANSEKOP / HOME), not Olarm's device name.
        return SITE_LABEL;
    }

    var EXIT_DEFAULT = 60;
    var EXIT_SHOW_FROM = 20;
    var EXIT_FAST_FROM = 7;
    var pendingExitUntil = 0;
    var armPending = false;
    var armSettled = false;
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
        // Site config wins (the installer knows the panel's exit delay); else Olarm profile; else default.
        var cfg = Number(CFG.exitDelay);
        if (isFinite(cfg) && cfg >= 5 && cfg <= 180) return cfg;
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

    // Panel/exit state is per site; the default site keeps the legacy key names.
    function siteKey(k) {
        return SITE_ID === "hansekop" ? k : k + "." + SITE_ID;
    }

    function storeSet(k, v) {
        k = siteKey(k);
        try { localStorage.setItem(k, v); } catch (e) {}
        try { sessionStorage.setItem(k, v); } catch (e2) {}
    }

    function storeGet(k) {
        k = siteKey(k);
        try {
            var a = localStorage.getItem(k);
            if (a != null && a !== "") return a;
        } catch (e) {}
        try { return sessionStorage.getItem(k); } catch (e2) { return null; }
    }

    function storeDel(k) {
        k = siteKey(k);
        try { localStorage.removeItem(k); } catch (e) {}
        try { sessionStorage.removeItem(k); } catch (e2) {}
    }

    function persistExit() {
        if (armSettled) {
            storeSet("arialArmSettled", "1");
            storeDel("arialExitUntil");
            storeDel("arialArmPending");
            storeDel("arialExitStarted");
            return;
        }
        storeDel("arialArmSettled");
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

    function localExitExpired() {
        return !!(pendingExitUntil && pendingExitUntil <= Date.now());
    }

    function startLocalExit(seconds) {
        var n = seconds && seconds > 0 ? seconds : EXIT_DEFAULT;
        pendingExitUntil = Date.now() + n * 1000;
        exitCountStarted = true;
        exitIntroUntil = 0;
        persistExit();
    }

    function inExitIntro() {
        if (!armPending || armSettled) return false;
        if (!exitCountStarted) return true;
        return localExitLeft() > EXIT_SHOW_FROM;
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
        armSettled = false;
        exitCountStarted = false;
        exitClockFromApi = false;
        armWaitSince = 0;
        exitIntroUntil = 0;
        longArmedBeep._done = false;
        stopExitBeeps();
        persistExit();
    }

    function holdSystemArmed() {
        stopIssueCycle();
        stopExitBeeps();
        setLcdStatus("System Armed", "");
        var lcd = document.querySelector(".lcd");
        if (lcd) {
            lcd.classList.remove("disarmed", "arming", "arming-fast", "zone-open", "hold-disarmed", "alarm");
            lcd.classList.add("armed");
        }
        setLed(document.getElementById("led-status"), "armed");
        syncArmToggle();
        fitLcdStatus();
    }

    function settleArm() {
        if (armSettled) {
            holdSystemArmed();
            return;
        }
        armSettled = true;
        armPending = false;
        pendingExitUntil = 0;
        exitCountStarted = false;
        exitClockFromApi = false;
        armWaitSince = 0;
        exitIntroUntil = 0;
        persistExit();
        showArmed();
    }

    function stillExiting(device) {
        if (disarmPending || armSettled) return false;
        if (localExitLeft() > 0) return true;
        if (armPending && !exitCountStarted) return true;
        return false;
    }

    function syncLocalExitFromApi(seconds) {
        if (!(seconds > 0) || armSettled || disarmPending) return;
        if (localExitExpired()) return;
        var local = localExitLeft();
        if (!exitClockFromApi && seconds > 10) {
            exitClockFromApi = true;
            startLocalExit(seconds);
            return;
        }
        if (!local) {
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
        if (armSettled || disarmPending) return 0;
        if (localExitExpired()) return 0;
        var apiCd = deviceCountdown(device);
        var stampCd = stampRemaining(device);
        if (apiCd > 0) syncLocalExitFromApi(apiCd);
        else if (stampCd > 0) syncLocalExitFromApi(stampCd);
        return localExitLeft();
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
            var label = String(z.label || "").trim();
            if (!label) label = "Zone " + (z.num != null ? z.num : (i + 1));
            out.push(label);
        }
        return out;
    }

    function powerAcOk(device) {
        var p = (device && device.arialPower) || {};
        if (typeof p.acOk === "boolean") return p.acOk;
        var raw = ((device && device.deviceState) || {}).powerAC;
        return !raw || String(raw).toLowerCase() === "ok";
    }

    function powerBatteryOk(device) {
        var p = (device && device.arialPower) || {};
        if (typeof p.batteryOk === "boolean") return p.batteryOk;
        var raw = ((device && device.deviceState) || {}).powerBattery;
        return !raw || String(raw).toLowerCase() === "ok";
    }

    function panelIssues(device) {
        var out = openZoneIssues(device);
        if (!powerAcOk(device)) out.push("Power Failure");
        if (!powerBatteryOk(device)) out.push("Low Battery");
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
        var issues = panelIssues(window.arialDevice);
        if (!issues.length) {
            stopIssueCycle();
            setLcdStatus("System Ready", "");
            applyLcd(window.arialDevice);
            setLed(document.getElementById("led-status"), "disarmed");
            return;
        }
        issueCycle.i = (issueCycle.i + 1) % issues.length;
        setLcdStatus(issueMainStatus(window.arialDevice), issues[issueCycle.i]);
    }

    function issueMainStatus(device) {
        if (openZoneIssues(device).length) return "System Not Ready";
        return statusFromDevice(device) || "System Ready";
    }

    function ensureIssueCycle() {
        var issues = panelIssues(window.arialDevice);
        if (!issues.length) {
            stopIssueCycle();
            return false;
        }
        if (issueCycle.i >= issues.length) issueCycle.i = 0;
        setLcdStatus(issueMainStatus(window.arialDevice), issues[issueCycle.i]);
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
            lcd.classList.remove("arming", "armed", "arming-fast", "zone-open", "has-trouble", "alarm");
            lcd.classList.add("disarmed", "hold-disarmed");
            syncArmToggle();
            fitLcdStatus();
            return;
        }
        lcd.classList.remove("hold-disarmed");
        var st = areaState(device);
        var alarm = isAlarmState(st);
        var arming = !armSettled && (stillExiting(device) || (armPending && (localExitLeft() > 0 || !exitCountStarted)));
        var armed = armSettled || (!arming && !alarm && isArmedState(st));
        var zoneOpen = !arming && !armed && !alarm && openZoneIssues(device).length > 0;
        var trouble = !arming && !armed && !alarm && panelIssues(device).length > 0;
        var disarmed = !arming && !armed && !alarm && (st === "disarm" || st === "notready" || !st);
        lcd.classList.toggle("arming", arming);
        lcd.classList.toggle("armed", armed);
        lcd.classList.toggle("alarm", alarm);
        lcd.classList.toggle("disarmed", disarmed);
        lcd.classList.toggle("zone-open", zoneOpen);
        lcd.classList.toggle("has-trouble", trouble);
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
        if (armSettled) return true;
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

    // ---- Partitioned panel LCD (Home): real per-area countdown, then "System Armed" + which areas ----
    function isMultiArea(device) {
        return !!(device && Array.isArray(device.arialAreas) && device.arialAreas.length >= 2);
    }

    function areaKeyLabel(idx, area) {
        var key = document.querySelector('.hot[data-key="' + AREA_KEYS[idx] + '"] .key-label');
        var txt = key ? String(key.textContent || "").trim() : "";
        return (txt || String((area && area.label) || ("Area " + (idx + 1)))).toUpperCase();
    }

    function areaCountdownLeft(idx, device) {
        var p = typeof areaPending !== "undefined" ? areaPending[idx + 1] : null;
        if (p && p.until) return Math.max(0, Math.ceil((p.until - Date.now()) / 1000));
        var n = deviceCountdown(device);          // Olarm-reported seconds when someone else armed
        return n > 0 ? n : 0;
    }

    // Optimistic per-area state: what the user just asked for, shown instantly until the panel confirms (max 20 s).
    var areaOverride = {};   // num -> { state, until }

    function setAreaOverride(num, state) {
        areaOverride[num] = { state: state, until: Date.now() + 20000 };
    }

    function effectiveAreaState(idx, areas) {
        var st = String((areas[idx] && areas[idx].state) || "").toLowerCase();
        var o = areaOverride[idx + 1];
        if (!o) return st;
        if (Date.now() > o.until) { delete areaOverride[idx + 1]; return st; }
        var armedNow = st === "arm" || st === "stay" || st === "sleep";
        if (o.state === "disarm" && (st === "disarm" || st === "notready")) { delete areaOverride[idx + 1]; return st; }
        if (o.state === "countdown" && armedNow) { delete areaOverride[idx + 1]; return st; }
        return o.state;
    }

    function applyMultiAreaLcd(device) {
        // Single-area state machine must not fight this display.
        if (armSettled || armPending || disarmPending || localExitLeft() > 0) {
            armSettled = false; armPending = false; disarmPending = false; disarmNeedsStatus = false;
            clearLocalExit();
            storeDel("arialArmSettled");
        }
        var areas = device.arialAreas;
        if (armSettled || armPending || disarmPending || localExitLeft() > 0) {
            armSettled = false; armPending = false; disarmPending = false; disarmNeedsStatus = false;
            clearLocalExit();
            storeDel("arialArmSettled");
        }
        var lcd = document.querySelector(".lcd");
        var led = document.getElementById("led-status");
        var arming = [], armed = [], alarm = [];
        var i;
        for (i = 0; i < areas.length && i < AREA_KEYS.length; i += 1) {
            var st = effectiveAreaState(i, areas);
            var pending = typeof areaPending !== "undefined" && areaPending[i + 1];
            if (isAlarmState(st)) alarm.push(i);
            else if (st === "countdown" || (pending && st !== "arm" && st !== "stay" && st !== "sleep")) arming.push(i);
            else if (st === "arm" || st === "stay" || st === "sleep") armed.push(i);
        }
        function names(list) { return list.map(function (ix) { return areaKeyLabel(ix, areas[ix]); }).join(" · "); }
        if (lcd) lcd.classList.remove("armed", "disarmed", "arming", "arming-fast", "zone-open", "hold-disarmed", "alarm");
        if (alarm.length) {
            stopIssueCycle();
            setLcdStatus("ALARM", names(alarm));
            if (lcd) lcd.classList.add("alarm");
            setLed(led, "alarm");
        } else if (arming.length) {
            stopIssueCycle();
            var left = 0;
            for (i = 0; i < arming.length; i += 1) left = Math.max(left, areaCountdownLeft(arming[i], device));
            setLcdStatus(left ? ("Exit Delay " + left) : "Exit Delay", "ARMING " + names(arming));
            if (lcd) { lcd.classList.add("arming"); if (left && left <= 7) lcd.classList.add("arming-fast"); }
            setLed(led, "arming");
        } else if (armed.length) {
            stopIssueCycle();
            setLcdStatus("System Armed", names(armed));
            if (lcd) lcd.classList.add("armed");
            setLed(led, "armed");
        } else {
            var open = openZoneIssues(device);
            if (lcd) { lcd.classList.add("disarmed"); lcd.classList.toggle("zone-open", open.length > 0); }
            if (!ensureIssueCycle()) setLcdStatus("System Ready", "");
            setLed(led, open.length ? "disarmed flash" : "disarmed");
        }
        syncArmToggle();
        fitLcdStatus();
    }

    function applyLeds(device) {
        if (Date.now() < loginErrorUntil) {
            showLoginError(true);
            syncArmToggle();
            return;
        }
        setLed(document.getElementById("led-ac"), powerAcOk(device) ? "on" : "flash");
        if (isMultiArea(device)) {
            applyMultiAreaLcd(device);
            return;
        }
        var st = areaState(device);
        var apiCd = deviceCountdown(device);
        var stampCd = stampRemaining(device);
        if (!armSettled && !localExitExpired()) {
            if (apiCd > 0) syncLocalExitFromApi(apiCd);
            else if (stampCd > 0) syncLocalExitFromApi(stampCd);
        }

        if (armSettled && !disarmPending && !isAlarmState(st)) {
            holdSystemArmed();
            return;
        }

        if (isAlarmState(st)) {
            if (disarmPending) {
                showSystemDisarmed();
                return;
            }
            clearLocalExit();
            stopIssueCycle();
            setLcdStatus("ALARM", "");
            applyLcd(device);
            setLed(document.getElementById("led-status"), "alarm");
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
            showArming(localExitLeft());
            maybeExitBeeps();
            return;
        }
        if (armPending && exitCountStarted && localExitLeft() === 0) {
            settleArm();
            return;
        }
        if (st === "arm" || st === "stay" || st === "sleep") {
            if (armPending && localExitLeft() > 0) {
                showArming(localExitLeft());
                maybeExitBeeps();
                return;
            }
            if (armPending || localExitExpired()) {
                settleArm();
                return;
            }
            armSettled = true;
            persistExit();
            holdSystemArmed();
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

    // Multi-partition panels: the HOUSE (FORCE) and GARAGE (ARM) keys show their own area's state.
    var AREA_KEYS = ["FORCE", "ARM"];

    function syncAreaKeys(device) {
        var areas = device && Array.isArray(device.arialAreas) ? device.arialAreas : [];
        var multi = areas.length >= 2;
        var i;
        for (i = 0; i < AREA_KEYS.length; i += 1) {
            var key = document.querySelector('.hot[data-key="' + AREA_KEYS[i] + '"]');
            if (!key) continue;
            if (!multi || !areas[i]) { key.classList.remove("area-armed", "area-disarmed", "area-notready", "area-arming"); continue; }
            var st = effectiveAreaState(i, areas);
            var pending = typeof areaPending !== "undefined" && areaPending[i + 1];
            if (pending && st !== "arm" && st !== "stay" && st !== "sleep") continue;   // keep flashing until the panel says armed
            if (pending) stopAreaPending(i + 1);
            key.classList.remove("area-armed", "area-disarmed", "area-notready", "area-arming");
            if (st === "arm" || st === "stay" || st === "sleep") key.classList.add("area-armed");
            else if (st === "countdown") key.classList.add("area-arming");
            else if (st === "notready") key.classList.add("area-notready");
            else if (st === "disarm") key.classList.add("area-disarmed");
            key.title = String(areas[i].label || "") + (st ? " · " + st.toUpperCase() : "");
        }
    }

    var lastAreaStates = {};

    function trackRemoteAreaChanges(device) {
        if (!isMultiArea(device)) return;
        var areas = device.arialAreas;
        var i;
        for (i = 0; i < areas.length && i < AREA_KEYS.length; i += 1) {
            var num = i + 1;
            var st = String((areas[i] && areas[i].state) || "").toLowerCase();
            var prev = lastAreaStates[num];
            lastAreaStates[num] = st;
            if (prev === undefined || prev === st) continue;
            var pending = typeof areaPending !== "undefined" && areaPending[num];
            if (st === "countdown" && !pending) {
                // Someone else started arming this area: show the same countdown, flash and beeps here.
                startAreaPending(num);
            } else if (st === "arm" || st === "stay" || st === "sleep") {
                if (pending) stopAreaPending(num);
                if (isLoggedIn()) { unlockAudio(); tone(1200, 0.35, 0.5); }
            } else if (st === "disarm" || st === "notready") {
                if (pending) stopAreaPending(num);
                if (prev === "arm" || prev === "stay" || prev === "sleep" || prev === "countdown") { if (isLoggedIn()) disarmBeep(); }
            }
        }
    }

    function applyPanelDevice(hanse) {
        if (!hanse) return;
        trackRemoteAreaChanges(hanse);
        var siteEl = document.getElementById("lcd-site");
        if (siteEl) siteEl.textContent = siteName(hanse);
        window.arialDevice = hanse;
        applyLeds(hanse);
        setActivityPower(hanse.arialPower);
        syncAreaKeys(hanse);
        var padWrap = document.getElementById("pad-frame");
        if (padWrap) padWrap.classList.toggle("multi-area", Array.isArray(hanse.arialAreas) && hanse.arialAreas.length >= 2);
        lastStatus = (document.getElementById("lcd-status-main") || {}).textContent || statusFromDevice(hanse);
        var st = areaState(hanse);
        if (isLoggedIn() && !isMultiArea(hanse) && applyPanelDevice._area && applyPanelDevice._area !== st) {
            if (st === "disarm" || st === "notready") prependActivity("DISARMED");
            else if (st === "arm" || st === "stay" || st === "sleep") prependActivity("ARMED");
        }
        applyPanelDevice._area = st;
        loadStatus._area = st;
        try {
            var lcd = document.querySelector(".lcd");
            localStorage.setItem(siteKey("arialPanel"), JSON.stringify({
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

    var activityTab = "all";
    var activityExpanded = false;
    var activityRows = [];
    var activityLastKey = "";
    var activityChecksumLocal = "";
    var ACTIVITY_PREVIEW = 4;
    var ACTIVITY_KEEP_MS = 30 * 24 * 60 * 60 * 1000;
    var ACTIVITY_STORE = "arialActivity." + SITE_ID;

    function activityMark(r) {
        var tab = String(r.tab || "");
        var st = String(r.state || r.action || "").toLowerCase();
        var act = String(r.action || "").toLowerCase();
        var text = String(r.activity || r.title || "").toLowerCase();
        if (act.indexOf("alarm") !== -1 || st === "alarm" || st === "panic" || st === "emergency" || text.indexOf("in alarm") !== -1) return "alarm";
        if (tab === "power") return /fail|low/.test(st) ? "power" : "power-ok";
        if (tab === "zones") {
            if (st === "closed" || st === "restore") return "zone-ok";
            return "zone";
        }
        if (tab === "areas") {
            if (/disarm/.test(st)) return "disarm";
            if (/arm|stay|sleep/.test(st)) return "arm";
            return "area";
        }
        return tab || "area";
    }

    function activityRecordKey(r) {
        return [r.at || "", r.tab || "", r.state || "", r.title || "", r.num || ""].join("|");
    }

    function areaTitle() {
        var d = window.arialDevice || {};
        var areas = d.arialAreas || [];
        var i;
        for (i = 0; i < areas.length; i += 1) {
            if (areas[i] && areas[i].label) return String(areas[i].label);
        }
        return "Facility Building";
    }

    function saHHmm() {
        var d = new Date(new Date().toLocaleString("en-US", { timeZone: "Africa/Johannesburg" }));
        return ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2);
    }

    function areaCycleState(r) {
        var st = String((r && r.state) || "").toUpperCase();
        if (!st) st = String((r && r.activity) || "").toUpperCase();
        if (st.indexOf("COUNTDOWN") !== -1) return "";
        if (st.indexOf("NOT READY") !== -1 || st.indexOf("NOTREADY") !== -1) return "";
        if (st.indexOf("DISARM") !== -1) return "DISARMED";
        if (st.indexOf("ARM") !== -1 || st.indexOf("STAY") !== -1 || st.indexOf("SLEEP") !== -1) return "ARMED";
        return "";
    }

    function isPlainZoneTraffic(r) {
        if (!r || r.tab !== "zones") return false;
        var st = String(r.state || "").toUpperCase();
        var act = String(r.action || "").toLowerCase();
        if (act.indexOf("alarm") !== -1 || act.indexOf("bypass") !== -1 || act.indexOf("tamper") !== -1 || act.indexOf("chime") !== -1) return false;
        if (/ALARM|PANIC|EMERGENCY|FIRE|MEDICAL|BYPASS|TAMPER|TROUBLE|CHIME/.test(st)) return false;
        return st === "ACTIVE" || st === "CLOSED" || st === "OPEN" || st === "RESTORE" || st === "";
    }

    function skipActivityRow(r) {
        if (!r || typeof r !== "object") return false;
        var blob = [
            r.state,
            r.activity,
            r.title,
            r.msg,
            r.action,
            r.eventState
        ].join(" ").toUpperCase().replace(/[\s_\-·.]+/g, "");
        return blob.indexOf("COUNTDOWN") !== -1 || blob.indexOf("NOTREADY") !== -1;
    }

    function tidyActivity(rows) {
        var out = [];
        var armed = {};
        var i;
        for (i = 0; i < (rows || []).length; i += 1) {
            var r = rows[i];
            if (skipActivityRow(r)) continue;
            var title = String((r && r.title) || "").trim() || "_";
            var cycle = areaCycleState(r);
            if (cycle === "ARMED") {
                if (armed[title]) continue;
                armed[title] = true;
            } else if (cycle === "DISARMED") {
                armed[title] = false;
            }
            out.push(r);
        }
        return out;
    }

    function prependActivity(stateLab) {
        var state = String(stateLab || "").toUpperCase();
        if (!state || skipActivityRow({ state: state })) return;
        var user = resolvedUser(window.arialUser);
        var who = user && user.from ? String(user.from) : "";
        var title = areaTitle();
        var cycle = /DISARM/.test(state) ? "DISARMED" : "ARMED";
        var i;
        for (i = 0; i < activityRows.length; i += 1) {
            if (String(activityRows[i].title || "") !== title) continue;
            var prev = areaCycleState(activityRows[i]);
            if (!prev) continue;
            if (prev === cycle) return;
            break;
        }
        var row = {
            tab: "areas",
            time: saHHmm(),
            title: title,
            state: state,
            actor: who,
            via: who ? "Remote" : "",
            activity: who ? (title + " " + state + " · " + who + " · Remote") : (title + " " + state),
            at: Date.now(),
            local: true
        };
        activityRows = tidyActivity([row].concat(activityRows));
        saveActivityStore();
        renderActivity();
    }

    function activityChecksum(rows) {
        var s = "";
        var i;
        var list = rows || [];
        for (i = 0; i < list.length; i += 1) s += activityRecordKey(list[i]) + "\n";
        var h = 5381;
        for (i = 0; i < s.length; i += 1) h = ((h << 5) + h) + s.charCodeAt(i);
        return (h >>> 0).toString(16);
    }

    function pruneActivity(rows) {
        var cut = Date.now() - ACTIVITY_KEEP_MS;
        return (rows || []).filter(function (r) {
            var t = Number(r && r.at) || 0;
            if (t && t < 10000000000) t *= 1000;
            return !t || t >= cut;
        });
    }

    function saveActivityStore() {
        activityRows = pruneActivity(activityRows);
        activityChecksumLocal = activityChecksum(activityRows);
        try {
            localStorage.setItem(ACTIVITY_STORE, JSON.stringify({
                site: SITE_ID,
                lastKey: activityLastKey,
                checksum: activityChecksumLocal,
                savedAt: Date.now(),
                events: activityRows
            }));
        } catch (e) {}
    }

    function restoreActivityStore() {
        try {
            var raw = JSON.parse(localStorage.getItem(ACTIVITY_STORE) || "null");
            if (!raw || !Array.isArray(raw.events) || !raw.events.length) return false;
            activityRows = pruneActivity(raw.events);
            activityRows = tidyActivity(activityRows);
            activityLastKey = raw.lastKey || (activityRows[0] ? activityRecordKey(activityRows[0]) : "");
            activityChecksumLocal = activityChecksum(activityRows);
            saveActivityStore();
            renderActivity();
            return true;
        } catch (e2) {
            return false;
        }
    }

    function allActivityThere(incoming) {
        if (!incoming || !incoming.length) return true;
        var have = {};
        var i;
        for (i = 0; i < activityRows.length; i += 1) have[activityRecordKey(activityRows[i])] = true;
        for (i = 0; i < incoming.length; i += 1) {
            if (!have[activityRecordKey(incoming[i])]) return false;
        }
        return true;
    }

    function insertNewerActivity(incoming) {
        if (!incoming || !incoming.length) return "ack";
        if (!activityRows.length) {
            activityRows = incoming.slice();
            return "history";
        }
        var have = {};
        var i;
        for (i = 0; i < activityRows.length; i += 1) {
            have[activityRecordKey(activityRows[i])] = true;
        }
        var added = [];
        for (i = 0; i < incoming.length; i += 1) {
            var r = incoming[i];
            if (have[activityRecordKey(r)]) continue;
            added.push(r);
        }
        if (!added.length) return "ack";
        activityRows = activityRows.filter(function (row) {
            if (!row.local) return true;
            var j;
            for (j = 0; j < added.length; j += 1) {
                if (added[j].state === row.state && added[j].title === row.title) return false;
            }
            return true;
        });
        activityRows = tidyActivity(added.concat(activityRows));
        saveActivityStore();
        return "insert";
    }

    function activityLine(r) {
        var text = String(r.activity || r.title || "").replace(/\s+/g, " ").trim();
        var who = String(r.actor || "").trim();
        var via = String(r.via || "").trim();
        if (r.tab === "areas" && who && !via) via = "Remote";
        if (who && text.toLowerCase().indexOf(who.toLowerCase()) === -1) text += " · " + who;
        if (via && text.toLowerCase().indexOf(via.toLowerCase()) === -1) text += " · " + via;
        return text;
    }

    function setActivityPower(power) {
        var el = document.getElementById("activity-power");
        if (!el) return;
        power = power || {};
        var acOk = power.acOk !== false;
        var batOk = power.batteryOk !== false;
        el.textContent = (acOk ? "●" : "○") + " AC  " + (batOk ? "●" : "○") + " Bat";
        el.classList.toggle("fault", !acOk || !batOk);
    }

    function shortStamp(r) {
        // "02 Sep 2026" -> "02 Sep 26", then " · 11:25"
        var d = String(r.date || "").replace(/(\d{2} \w{3}) (\d{2})(\d{2})$/, "$1 $3");
        return (d ? d + " · " : "") + (r.time || "");
    }

    function renderActivity() {
        var body = document.getElementById("arial-activity-body");
        var more = document.getElementById("activity-more");
        if (!body) return;
        activityRows = tidyActivity(activityRows);
        var rows = activityRows.filter(function (r) { return !skipActivityRow(r); });
        if (activityTab !== "all") {
            rows = rows.filter(function (r) { return r.tab === activityTab; });
        } else {
            // All = headline events only. Plain zone open/close traffic lives under Zones.
            rows = rows.filter(function (r) { return !isPlainZoneTraffic(r); });
        }
        var show = activityExpanded ? rows : rows.slice(0, ACTIVITY_PREVIEW);
        body.textContent = "";
        var i;
        if (!show.length) {
            var empty = document.createElement("li");
            empty.className = "activity-empty";
            empty.textContent = "No activity";
            body.appendChild(empty);
        } else {
            for (i = 0; i < show.length; i += 1) {
                var r = show[i];
                var row = document.createElement("li");
                row.className = "activity-row";
                var mark = document.createElement("span");
                mark.className = "activity-mark " + activityMark(r);
                mark.setAttribute("aria-hidden", "true");
                var t = document.createElement("span");
                t.className = "activity-time";
                t.textContent = shortStamp(r);
                var line = document.createElement("span");
                line.className = "activity-text";
                line.textContent = activityLine(r);
                line.title = (r.date ? r.date + "  " : "") + activityLine(r);
                row.appendChild(mark);
                row.appendChild(t);
                row.appendChild(line);
                body.appendChild(row);
            }
        }
        if (more) {
            if (rows.length > ACTIVITY_PREVIEW) {
                more.hidden = false;
                more.setAttribute("aria-expanded", activityExpanded ? "true" : "false");
                var lab = more.querySelector(".activity-more-label");
                if (lab) lab.textContent = activityExpanded ? "Less" : "More";
            } else {
                more.hidden = true;
            }
        }
    }

    function applyActivityPayload(data) {
        if (!data) return;
        var incoming = Array.isArray(data.events) ? data.events : [];
        var key = data.lastKey || (incoming[0] ? activityRecordKey(incoming[0]) : "");
        setActivityPower(data.power || ((window.arialDevice || {}).arialPower));
        var before = activityRows.length;
        activityRows = tidyActivity(activityRows);
        if (!activityRows.length) {
            activityRows = tidyActivity(pruneActivity(incoming.slice()));
            activityLastKey = key;
            activityChecksumLocal = data.checksum || activityChecksum(activityRows);
            saveActivityStore();
            renderActivity();
            return;
        }
        if ((key && key === activityLastKey) || allActivityThere(incoming)) {
            if (activityRows.length !== before) {
                saveActivityStore();
                renderActivity();
            }
            return;
        }
        var mode = insertNewerActivity(incoming);
        if (key) activityLastKey = key;
        if (mode !== "ack" || activityRows.length !== before) renderActivity();
    }

    async function loadActivity() {
        if (!isLoggedIn()) return;
        if (currentSite().id !== SITE_ID) return;
        if (loadActivity._busy) return;
        loadActivity._busy = true;
        try {
            var res = await fetch(API + "/activity", { credentials: "same-origin", cache: "no-store" });
            var data = await res.json();
            if (!res.ok) return;
            applyActivityPayload(data);
        } catch (e) {
        } finally {
            loadActivity._busy = false;
        }
    }

    function breakerScale(code, value) {
        var n = Number(value);
        if (!isFinite(n)) return null;
        // Tuya DP spec for the GR2PWS meter: V scale 2, A scale 3, W scale 2, kWh scale 2.
        if (code === "cur_voltage") return n / 100;
        if (code === "cur_current") return n / 1000;
        if (code === "cur_power") return n / 100;
        if (code === "add_ele") return n / 100;
        return n;
    }

    var BREAKER_STORE = "arialBreaker." + SITE_ID;
    var BREAKER_HIST = 90;
    var BREAKER_HIST_MS = 15 * 60 * 1000;
    var breakerHist = [];
    var breakerEnergy = { hidden: false, last: null, midnightYmd: "", midnightAddEle: null };

    function saYmdNow() {
        return new Date().toLocaleDateString("en-CA", { timeZone: "Africa/Johannesburg" });
    }

    function restoreBreakerStore() {
        try {
            var raw = JSON.parse(localStorage.getItem(BREAKER_STORE) || "null");
            if (!raw || typeof raw !== "object") return;
            var now = Date.now();
            var samples = Array.isArray(raw.samples) ? raw.samples : [];
            var kept = [];
            var i;
            for (i = 0; i < samples.length; i += 1) {
                var t = Number(samples[i] && samples[i].t);
                var w = Number(samples[i] && samples[i].w);
                if (!isFinite(t) || !isFinite(w)) continue;
                if (now - t > BREAKER_HIST_MS) continue;
                kept.push({ t: t, w: w });
            }
            breakerHist = kept.slice(-BREAKER_HIST);
            breakerEnergy.hidden = !!raw.energyHidden;
            if (isFinite(Number(raw.lastAddEle))) breakerEnergy.last = Number(raw.lastAddEle);
            breakerEnergy.midnightYmd = String(raw.midnightYmd || "");
            if (isFinite(Number(raw.midnightAddEle))) breakerEnergy.midnightAddEle = Number(raw.midnightAddEle);
        } catch (e) {}
    }

    function saveBreakerStore() {
        try {
            localStorage.setItem(BREAKER_STORE, JSON.stringify({
                samples: breakerHist,
                energyHidden: breakerEnergy.hidden,
                lastAddEle: breakerEnergy.last,
                midnightYmd: breakerEnergy.midnightYmd,
                midnightAddEle: breakerEnergy.midnightAddEle
            }));
        } catch (e) {}
    }

    restoreBreakerStore();

    var breakerLatestWatts = null;

    // low = blue (below normal), ok = green, warn = amber, crit = red (too high / out of spec).
    function breakerDialState(kind, value) {
        if (value == null || !isFinite(value)) return "";
        if (kind === "v") {
            if (value > 253) return "crit";
            if (value > 244) return "warn";
            if (value < 216) return "low";           // under-voltage: below normal
            return "ok";
        }
        // Hard supply limits first (20 A supply).
        if (kind === "a" ? value >= 19 : value >= 4370) return "crit";
        if (kind === "a" ? value >= 18 : value >= 4140) return "warn";
        // Then relative to the running average (same bands as the day chart).
        var base = breakerEnergyData && breakerEnergyData.baselineKw != null ? breakerEnergyData.baselineKw * 1000 : null;
        var watts = kind === "w" ? value : breakerLatestWatts;
        if (base && base > 0 && watts != null) {
            var r = watts / base;
            if (r < 0.85) return "low";
            if (r <= 1.15) return "ok";
            if (r <= 1.35) return "warn";
            return "crit";
        }
        return "ok";
    }

    function breakerStateColour(state) {
        if (state === "crit") return ARIAL_THEME.crit;
        if (state === "warn") return ARIAL_THEME.warn;
        if (state === "low") return ARIAL_THEME.low;
        if (state === "ok") return ARIAL_THEME.ok;
        return ARIAL_THEME.track;
    }

    // ---- Arial chart theme (white background always): one palette for every gauge/chart on the site ----
    var ARIAL_THEME = {
        navy: "#001f3f",
        ink: "#0f172a",
        muted: "#64748b",
        track: "#e2e8f0",
        ok: "#12b028",
        warn: "#e67e00",
        crit: "#DC143C",
        low: "#1565c0",
        band: { ok: "rgba(18,176,40,0.28)", warn: "rgba(230,126,0,0.32)", crit: "rgba(220,20,60,0.32)" },
        font: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif'
    };

    // Gauge definitions: scale, threshold bands (values) and the hard limit mark.
    var BREAKER_GAUGES = {
        v: { min: 200, max: 255, unit: "V", name: "Volts", decimals: 1, bands: [["crit", 207], ["warn", 216], ["ok", 244], ["warn", 253], ["crit", 255]], limit: null, splitNumber: 11, labelEvery: 10, tip: "Normal 216–244 V · Watch 207–216 / 244–253 V · Out of spec below 207 V or above 253 V" },
        a: { min: 0, max: 20, unit: "A", name: "Amps", decimals: 2, bands: [["ok", 18], ["warn", 19], ["crit", 20]], limit: null, splitNumber: 10, labelEvery: 5, tip: "20 A supply · Watch from 18 A" },
        w: { min: 0, max: 4600, unit: "W", name: "Watts", decimals: 0, bands: [["ok", 4140], ["warn", 4370], ["crit", 4600]], limit: null, splitNumber: 10, labelEvery: 1000, tip: "20 A supply (4600 W at 230 V) · Watch from 4140 W" }
    };

    var breakerCharts = {};
    var breakerLastValues = {};

    function breakerGaugeOption(kind, widthPx) {
        var g = BREAKER_GAUGES[kind];
        var span = g.max - g.min;
        var f = Math.max(0.7, Math.min(1.8, (widthPx || 100) / 100));   // scale everything with the dial size
        var thick = (kind === "w" ? 5 : 4) * f;                            // thin, clean arc
        var bands = g.bands.map(function (b) { return [(b[1] - g.min) / span, ARIAL_THEME.band[b[0]]]; });
        var half = ((widthPx || 100) * 0.8) / 2;                         // container is 100:80; radius % is of the shorter side / 2
        var geo = { center: ["50%", "58%"], radius: "100%", startAngle: 200, endAngle: -20, min: g.min, max: g.max };
        function base(extra) {
            var o = { type: "gauge", pointer: { show: false }, anchor: { show: false }, title: { show: false }, detail: { show: false },
                axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false } };
            Object.keys(geo).forEach(function (k) { o[k] = geo[k]; });
            Object.keys(extra).forEach(function (k) { o[k] = extra[k]; });
            return o;
        }
        var main = base({
            axisLine: { lineStyle: { width: thick, color: bands } },
            progress: { show: true, width: thick, roundCap: true, itemStyle: { color: ARIAL_THEME.ok } },
            // Diamond rides the arc at value / full scale; colour follows state.
            pointer: {
                show: true,
                icon: "path://M0,-10 L8,0 L0,10 L-8,0 Z",
                length: (12 * f) + "",
                width: 12 * f,
                offsetCenter: [0, (-(100 - ((thick / 2 + 6 * f) / half) * 100)).toFixed(1) + "%"],
                keepAspect: true,
                itemStyle: { color: ARIAL_THEME.ok, borderColor: "#ffffff", borderWidth: 1.2 }
            },
            title: {
                show: true,
                offsetCenter: [0, "38%"],
                fontSize: (kind === "w" ? 12 : 9) * f,
                fontWeight: 800,
                fontFamily: ARIAL_THEME.font,
                color: ARIAL_THEME.muted
            },
            detail: {
                show: true,
                valueAnimation: true,
                offsetCenter: [0, "-6%"],
                fontSize: (kind === "w" ? 22 : 15) * f,
                fontWeight: 800,
                fontFamily: ARIAL_THEME.font,
                color: ARIAL_THEME.navy,
                formatter: function (v) { return v == null || isNaN(v) ? "—" : Number(v).toFixed(g.decimals); }
            },
            data: [{ value: g.min, name: g.unit }],
            animationDuration: 900,
            animationDurationUpdate: 700,
            animationEasingUpdate: "cubicOut"
        });
        var series = [main];
        if (g.limit != null) {
            series.push(base({
                axisLine: { show: false },
                progress: { show: false },
                pointer: { show: false },
                title: {
                    show: true,
                    offsetCenter: [0, "72%"],
                    fontSize: 6.5 * f,
                    fontWeight: 800,
                    fontFamily: ARIAL_THEME.font,
                    color: ARIAL_THEME.crit
                },
                data: [{ value: g.limit, name: "MAX " + g.limit + " " + g.unit }],
                silent: true,
                animation: false
            }));
        }
        return {
            animation: true,
            tooltip: {
                trigger: "item",
                confine: true,
                backgroundColor: ARIAL_THEME.navy,
                borderWidth: 0,
                textStyle: { color: "#fff", fontSize: 11, fontFamily: ARIAL_THEME.font },
                formatter: function () { return g.tip; }
            },
            series: series
        };
    }

    function breakerGaugeName(kind) {
        var g = BREAKER_GAUGES[kind];
        return g.limit != null ? g.name + "  ·  max " + g.limit + " " + g.unit : g.name;
    }

    function initBreakerCharts() {
        if (typeof window.echarts === "undefined") {
            // ECharts is deferred so the keypad never waits for it; try again shortly.
            initBreakerCharts._tries = (initBreakerCharts._tries || 0) + 1;
            if (initBreakerCharts._tries < 60) setTimeout(function () { initBreakerCharts(); Object.keys(breakerCharts).forEach(function (k) { breakerCharts[k].resize(); }); if (breakerLastValues.w != null) Object.keys(breakerLastValues).forEach(function (k) { setBreakerGauge(k, breakerLastValues[k], 0, 1); }); }, 250);
            return;
        }
        Object.keys(BREAKER_GAUGES).forEach(function (kind) {
            var el = document.getElementById("breaker-chart-" + kind);
            if (!el || breakerCharts[kind]) return;
            var chart = window.echarts.init(el, null, { renderer: "svg" });
            chart.setOption(breakerGaugeOption(kind, el.clientWidth));
            breakerCharts[kind] = chart;
            var dial = el.closest(".breaker-dial");
            if (dial) dial.classList.add("has-chart");
        });
        if (!initBreakerCharts._bound) {
            initBreakerCharts._bound = true;
            window.addEventListener("resize", function () {
                Object.keys(breakerCharts).forEach(function (k) {
                    var el = document.getElementById("breaker-chart-" + k);
                    breakerCharts[k].resize();
                    breakerCharts[k].setOption(breakerGaugeOption(k, el ? el.clientWidth : 100));
                    breakerLastValues[k] != null && setBreakerGauge(k, breakerLastValues[k], 0, 1);
                });
            });
        }
    }

    function setBreakerGauge(kind, value, min, max) {
        var state = breakerDialState(kind, value);
        var dial = document.querySelector('#arial-breaker .breaker-dial[data-kind="' + kind + '"]');
        if (dial) {
            if (state) dial.setAttribute("data-state", state);
            else dial.removeAttribute("data-state");
        }
        var chart = breakerCharts[kind];
        breakerLastValues[kind] = value;
        if (chart) {
            var g = BREAKER_GAUGES[kind];
            var colour = breakerStateColour(state);
            var v = value == null ? g.min : Math.min(g.max, Math.max(g.min, value));
            chart.setOption({
                series: [{
                    data: [{ value: v, name: g.unit }],
                    progress: { itemStyle: { color: colour } },
                    pointer: { itemStyle: { color: colour } },
                    detail: { color: state === "crit" || state === "warn" || state === "low" ? colour : ARIAL_THEME.navy }
                }]
            });
            return;
        }
        // No ECharts: fall back to the plain number under the dial.
        var needle = document.getElementById("breaker-needle-" + kind);
        if (needle) {
            var pct = 0;
            if (value != null && max > min) pct = Math.min(1, Math.max(0, (value - min) / (max - min)));
            needle.setAttribute("transform", "rotate(" + (pct * 180).toFixed(1) + " 50 50)");
        }
    }

    function sinceLabel(seconds) {
        var s = Math.max(0, Math.floor(seconds));
        var y = Math.floor(s / 31557600); s -= y * 31557600;
        var mo = Math.floor(s / 2629800); s -= mo * 2629800;
        var d = Math.floor(s / 86400); s -= d * 86400;
        var h = Math.floor(s / 3600); s -= h * 3600;
        var m = Math.floor(s / 60);
        var parts = [];
        if (y) parts.push(y + "y");
        if (y || mo) parts.push(mo + "mo");
        if (y || mo || d) parts.push(d + "d");
        parts.push(h + "h");
        parts.push(m + "m");
        return parts.join(" ");
    }

    var breakerEnergyData = null;

    function renderBreakerMeta() {
        var rangeEl = document.getElementById("breaker-hist-range");
        var wNow = document.getElementById("breaker-w-now");
        var flag = document.getElementById("breaker-flag");
        var flagText = document.getElementById("breaker-flag-text");
        var flagAvg = document.getElementById("breaker-flag-avg");
        var d = breakerEnergyData;
        if (rangeEl) {
            var pw = d && d.power;
            if (pw && pw.sinceRestoreS != null) {
                var since = pw.sinceRestoreS + Math.floor((Date.now() - breakerDayTick) / 1000);
                rangeEl.textContent = "Since restore " + sinceLabel(since);
            } else {
                rangeEl.textContent = "Since restore —";
            }
        }
        if (wNow) {
            var today = d && d.days && d.days[0];
            wNow.textContent = today && today.totalKwh != null ? "Today " + fmtKwhShort(today.totalKwh) : "Today —";
        }
        if (!flag || !flagText) return;
        var f = d && d.flag ? d.flag : "learning";
        flag.setAttribute("data-flag", f);
        var txt = {
            learning: "Learning baseline",
            recovery: "Recovery after restore",
            normal: "Normal load",
            above: "Above average",
            check: "Check load"
        }[f] || "Learning baseline";
        if ((f === "above" || f === "check") && d && d.deltaPct != null) txt += " +" + d.deltaPct + "%";
        flagText.textContent = txt;
        if (flagAvg) {
            var bits = [];
            if (d && d.recentKw != null) bits.push("now " + d.recentKw.toFixed(2) + " kW");
            if (d && d.baselineKw != null) bits.push("avg " + d.baselineKw.toFixed(2) + " kW");
            flagAvg.textContent = bits.join(" · ");
        }
    }

    function drawBreakerSpark() {
        var line = document.getElementById("breaker-spark-line");
        if (!line) return;
        if (breakerHist.length < 2) {
            line.setAttribute("points", "");
            return;
        }
        var w = 320;
        var h = 28;
        var pad = 3;
        var i;
        var max = 1;
        var t0 = breakerHist[0].t;
        var t1 = breakerHist[breakerHist.length - 1].t;
        var span = t1 - t0;
        for (i = 0; i < breakerHist.length; i += 1) {
            if (breakerHist[i].w > max) max = breakerHist[i].w;
        }
        var pts = [];
        for (i = 0; i < breakerHist.length; i += 1) {
            var x = span > 0
                ? pad + ((breakerHist[i].t - t0) / span) * (w - pad * 2)
                : pad + (i / (breakerHist.length - 1)) * (w - pad * 2);
            var y = h - pad - (breakerHist[i].w / max) * (h - pad * 2);
            pts.push(x.toFixed(1) + "," + y.toFixed(1));
        }
        line.setAttribute("points", pts.join(" "));
    }

    function fmtKwh(n) {
        if (n == null || !isFinite(n)) return "—";
        return (n >= 10 ? n.toFixed(1) : n.toFixed(2)) + " kWh";
    }

    function updateBreakerEnergy(rawAdd) {
        var row = document.getElementById("breaker-energy");
        var todayEl = document.getElementById("breaker-kwh-today");
        var totalEl = document.getElementById("breaker-kwh-total");
        var kwh = breakerScale("add_ele", rawAdd);
        if (kwh == null || breakerEnergy.hidden) {
            if (row) row.hidden = true;
            return;
        }
        if (breakerEnergy.last != null && kwh < breakerEnergy.last - 0.001) {
            // A cumulative register never decreases; this meter's add_ele is a per-report pulse, so hide the row.
            breakerEnergy.hidden = true;
            if (row) row.hidden = true;
            saveBreakerStore();
            return;
        }
        var ymd = saYmdNow();
        if (breakerEnergy.midnightYmd !== ymd || breakerEnergy.midnightAddEle == null) {
            breakerEnergy.midnightYmd = ymd;
            breakerEnergy.midnightAddEle = kwh;
        }
        breakerEnergy.last = kwh;
        var today = kwh - breakerEnergy.midnightAddEle;
        if (today < 0) today = 0;
        if (totalEl) totalEl.textContent = fmtKwh(kwh);
        if (todayEl) todayEl.textContent = fmtKwh(today);
        if (row) row.hidden = false;
    }

    function setBreakerOn(text, fault) {
        var stateEl = document.getElementById("breaker-state");
        var label = document.getElementById("breaker-on-label");
        if (label) label.textContent = text;
        if (!stateEl) return;
        stateEl.classList.toggle("fault", !!fault);
        stateEl.classList.toggle("is-on", text === "ON" && !fault);
        stateEl.classList.toggle("is-off", text === "OFF");
    }

    var breakerFailStreak = 0;
    var BREAKER_FAILS_BEFORE_BLANK = 3;

    function renderBreaker(data) {
        var stateEl = document.getElementById("breaker-state");
        var vEl = document.getElementById("breaker-v");
        var aEl = document.getElementById("breaker-a");
        var wEl = document.getElementById("breaker-w");
        var energyRow = document.getElementById("breaker-energy");
        if (!stateEl) return;
        var healthy = !!(data && data.configured && data.tokenOk && data.deviceOk);
        if (!healthy) {
            breakerFailStreak += 1;
            // Tuya drops the odd request; hold the last good reading unless the link is really down.
            if (breakerFailStreak < BREAKER_FAILS_BEFORE_BLANK && breakerHist.length) return;
        } else {
            breakerFailStreak = 0;
        }
        function blankGauges() {
            setBreakerGauge("v", null, 0, 1);
            setBreakerGauge("a", null, 0, 1);
            setBreakerGauge("w", null, 0, 1);
            if (vEl) vEl.textContent = "—";
            if (aEl) aEl.textContent = "—";
            if (wEl) wEl.textContent = "—";
            if (energyRow) energyRow.hidden = true;
            drawBreakerSpark();
        }
        if (!data || !data.configured) {
            setBreakerOn("Tuya off", true);
            blankGauges();
            return;
        }
        if (!data.tokenOk) {
            setBreakerOn("No token", true);
            blankGauges();
            return;
        }
        if (!data.deviceOk) {
            setBreakerOn("No link", true);
            blankGauges();
            return;
        }
        var rows = Array.isArray(data.status) ? data.status : [];
        var map = {};
        var i;
        for (i = 0; i < rows.length; i += 1) {
            if (rows[i] && rows[i].code) map[rows[i].code] = rows[i].value;
        }
        var on = map.switch_1 === true || map.switch === true;
        var volts = breakerScale("cur_voltage", map.cur_voltage);
        var amps = breakerScale("cur_current", map.cur_current);
        var watts = breakerScale("cur_power", map.cur_power);
        setBreakerOn(on ? "ON" : "OFF", !on);
        if (vEl) vEl.textContent = volts != null ? volts.toFixed(1) : "—";
        if (aEl) aEl.textContent = amps != null ? amps.toFixed(2) : "—";
        if (wEl) wEl.textContent = watts != null ? String(Math.round(watts)) : "—";
        breakerLatestWatts = watts;
        setBreakerGauge("v", volts, 200, 255);
        setBreakerGauge("a", amps, 0, 20);
        setBreakerGauge("w", watts, 0, 4600);
        if (watts != null) {
            breakerHist.push({ t: Date.now(), w: watts });
            var cut = Date.now() - BREAKER_HIST_MS;
            var kept = [];
            for (i = 0; i < breakerHist.length; i += 1) {
                if (breakerHist[i].t >= cut) kept.push(breakerHist[i]);
            }
            breakerHist = kept.slice(-BREAKER_HIST);
        }
        updateBreakerEnergy(map.add_ele);
        drawBreakerSpark();
        saveBreakerStore();
    }

    async function loadBreaker() {
        if (!isLoggedIn() || !SITE_TUYA) return;
        if (loadBreaker._busy) return;
        loadBreaker._busy = true;
        try {
            var res = await fetch(API + "/tuya/probe?device_id=bf90676b1341ecb34dse39", {
                credentials: "same-origin",
                cache: "no-store"
            });
            var data = await res.json();
            renderBreaker(data);
        } catch (e) {
            renderBreaker({ configured: true, tokenOk: false, tuyaMsg: "No link" });
        } finally {
            loadBreaker._busy = false;
        }
        loadBreakerEnergy();
    }

    var breakerDays = [];
    var breakerDayIdx = 0;
    var breakerDayTick = 0;

    function fmtKwhShort(n) {
        if (n == null || !isFinite(n)) return "—";
        return (n >= 10 ? n.toFixed(1) : n.toFixed(2)) + " kWh";
    }

    async function loadBreakerEnergy() {
        if (!isLoggedIn()) return;
        if (loadBreakerEnergy._busy) return;
        var now = Date.now();
        if (breakerDayTick && now - breakerDayTick < 30000) {
            renderBreakerMeta();
            return;
        }
        loadBreakerEnergy._busy = true;
        try {
            var res = await fetch(API + "/tuya/energy?device_id=bf90676b1341ecb34dse39", {
                credentials: "same-origin",
                cache: "no-store"
            });
            var data = await res.json();
            breakerDayTick = Date.now();
            breakerEnergyData = data || null;
            breakerDays = data && Array.isArray(data.days) ? data.days : [];
            if (breakerDayIdx > breakerDays.length - 1) breakerDayIdx = 0;
            renderBreakerDay();
            renderBreakerMeta();
        } catch (e) {
        } finally {
            loadBreakerEnergy._busy = false;
        }
    }

    function hideBreakerTip() {
        var tip = document.getElementById("breaker-tip");
        if (tip) tip.hidden = true;
        var hot = document.querySelector("#breaker-bars .bar.hot");
        if (hot) hot.classList.remove("hot");
    }

    function showBreakerTip(hour) {
        var day = breakerDays[breakerDayIdx];
        var tip = document.getElementById("breaker-tip");
        var chart = document.getElementById("breaker-day-chart");
        var svg = document.getElementById("breaker-bars");
        if (!day || !tip || !chart || !svg) return;
        var val = day.hours && day.hours[hour];
        var bars = svg.querySelectorAll(".bar");
        var j;
        for (j = 0; j < bars.length; j += 1) bars[j].classList.toggle("hot", Number(bars[j].getAttribute("data-hour")) === hour);
        var h2 = String(hour).padStart(2, "0");
        var h3 = String(hour + 1).padStart(2, "0");
        tip.textContent = h2 + ":00–" + h3 + ":00 · " + (val == null ? "no data" : fmtKwhShort(val) + breakerBandText(val, breakerAvgKwh(day)));
        tip.hidden = false;
        var rect = chart.getBoundingClientRect();
        var x = ((hour + 0.5) / 24) * rect.width;
        var tw = tip.offsetWidth;
        if (x - tw / 2 < 0) x = tw / 2;
        if (x + tw / 2 > rect.width) x = rect.width - tw / 2;
        var max = breakerDaysMax();
        var y = 60;
        if (val != null && max > 0) y = 60 - (val / max) * 56;
        tip.style.left = x + "px";
        tip.style.top = Math.max(y - 4, 14) + "px";
    }

    // Dynamic chart ceiling: highest hourly peak in the available history plus 15% headroom.
    var BREAKER_PEAK_HEADROOM = 1.15;

    function breakerDaysMax() {
        var peak = 0;
        var d, i;
        for (d = 0; d < breakerDays.length; d += 1) {
            var hours = breakerDays[d] && Array.isArray(breakerDays[d].hours) ? breakerDays[d].hours : [];
            for (i = 0; i < hours.length; i += 1) if (hours[i] != null && hours[i] > peak) peak = hours[i];
        }
        return peak > 0 ? peak * BREAKER_PEAK_HEADROOM : 0.1;
    }

    function breakerAvgKwh(day) {
        // Only the multi-day baseline (kW == kWh per hour). A single day's own mean is not an average worth colouring against.
        if (breakerEnergyData && breakerEnergyData.baselineKw != null) return breakerEnergyData.baselineKw;
        return null;
    }

    function breakerBandClass(v, avg) {
        if (v == null || avg == null || !(avg > 0)) return "band-none";
        var r = v / avg;
        if (r < 0.6) return "band-cold2";
        if (r < 0.85) return "band-cold";
        if (r <= 1.15) return "band-avg";
        if (r <= 1.35) return "band-warm";
        if (r <= 1.6) return "band-hot";
        return "band-danger";
    }

    function breakerBandText(v, avg) {
        if (v == null || avg == null || !(avg > 0)) return "";
        var pct = Math.round((v / avg - 1) * 100);
        return (pct >= 0 ? " · +" : " · ") + pct + "% vs avg";
    }

    function renderBreakerDay() {
        var wrap = document.getElementById("breaker-day");
        var svg = document.getElementById("breaker-bars");
        var label = document.getElementById("breaker-day-label");
        var total = document.getElementById("breaker-day-total");
        var empty = document.getElementById("breaker-day-empty");
        var prev = document.getElementById("breaker-day-prev");
        var next = document.getElementById("breaker-day-next");
        if (!wrap || !svg) return;
        hideBreakerTip();
        var day = breakerDays[breakerDayIdx];
        wrap.setAttribute("data-day", String(breakerDayIdx));
        if (prev) prev.disabled = breakerDayIdx >= breakerDays.length - 1;
        if (next) next.disabled = breakerDayIdx <= 0;
        while (svg.firstChild) svg.removeChild(svg.firstChild);
        if (!day) {
            if (label) label.textContent = "Today";
            if (total) total.textContent = "—";
            if (empty) empty.hidden = false;
            return;
        }
        if (label) label.textContent = day.label || day.ymd || "";
        if (total) total.textContent = fmtKwhShort(day.totalKwh);
        var hours = Array.isArray(day.hours) ? day.hours : [];
        var max = breakerDaysMax();
        var i;
        var any = false;
        for (i = 0; i < 24; i += 1) if (hours[i] != null) any = true;
        if (empty) empty.hidden = any;
        var ns = "http://www.w3.org/2000/svg";
        var base = document.createElementNS(ns, "line");
        base.setAttribute("class", "base");
        base.setAttribute("x1", "0"); base.setAttribute("x2", "320");
        base.setAttribute("y1", "59.5"); base.setAttribute("y2", "59.5");
        svg.appendChild(base);
        var nowHour = Number(new Date().toLocaleString("en-GB", { timeZone: "Africa/Johannesburg", hour: "2-digit", hour12: false }).slice(0, 2));
        var avg = breakerAvgKwh(day);
        var slotW = 320 / 24;
        for (i = 0; i < 24; i += 1) {
            var slot = document.createElementNS(ns, "rect");
            slot.setAttribute("class", "slot");
            slot.setAttribute("x", (i * slotW).toFixed(2));
            slot.setAttribute("y", "0");
            slot.setAttribute("width", slotW.toFixed(2));
            slot.setAttribute("height", "60");
            slot.setAttribute("data-hour", String(i));
            svg.appendChild(slot);
            var v = hours[i];
            if (v == null || !(max > 0)) continue;
            var h = Math.max(3.5, Math.min(1, v / max) * 56);
            var bar = document.createElementNS(ns, "rect");
            var isNow = breakerDayIdx === 0 && i === nowHour;
            bar.setAttribute("class", "bar " + breakerBandClass(isNow ? null : v, avg) + (isNow ? " now" : ""));
            bar.setAttribute("x", (i * slotW + 1.2).toFixed(2));
            bar.setAttribute("y", (59 - h).toFixed(2));
            bar.setAttribute("width", (slotW - 2.4).toFixed(2));
            bar.setAttribute("height", h.toFixed(2));
            bar.setAttribute("rx", "1");
            bar.setAttribute("data-hour", String(i));
            svg.appendChild(bar);
        }
    }

    function bindBreakerDay() {
        var wrap = document.getElementById("breaker-day");
        var chart = document.getElementById("breaker-day-chart");
        var prev = document.getElementById("breaker-day-prev");
        var next = document.getElementById("breaker-day-next");
        if (!wrap || !chart) return;
        function go(delta) {
            var n = breakerDayIdx + delta;
            if (n < 0 || n > breakerDays.length - 1) return;
            breakerDayIdx = n;
            renderBreakerDay();
        }
        if (prev) prev.addEventListener("click", function () { go(1); });
        if (next) next.addEventListener("click", function () { go(-1); });
        function hourAt(clientX) {
            var rect = chart.getBoundingClientRect();
            if (!rect.width) return -1;
            var h = Math.floor(((clientX - rect.left) / rect.width) * 24);
            return h < 0 || h > 23 ? -1 : h;
        }
        chart.addEventListener("mousemove", function (ev) {
            var h = hourAt(ev.clientX);
            if (h < 0) hideBreakerTip(); else showBreakerTip(h);
        });
        chart.addEventListener("mouseleave", hideBreakerTip);
        var sx = 0;
        var sy = 0;
        var moved = false;
        wrap.addEventListener("touchstart", function (ev) {
            var t = ev.touches[0];
            sx = t.clientX; sy = t.clientY; moved = false;
            var h = hourAt(t.clientX);
            if (h >= 0 && ev.target && ev.target.closest && ev.target.closest(".breaker-day-chart")) showBreakerTip(h);
        }, { passive: true });
        wrap.addEventListener("touchmove", function (ev) {
            var t = ev.touches[0];
            if (Math.abs(t.clientX - sx) > 10 || Math.abs(t.clientY - sy) > 10) moved = true;
            if (!moved) return;
            if (Math.abs(t.clientX - sx) > Math.abs(t.clientY - sy)) hideBreakerTip();
        }, { passive: true });
        wrap.addEventListener("touchend", function (ev) {
            var t = ev.changedTouches[0];
            var dx = t.clientX - sx;
            var dy = t.clientY - sy;
            if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy) * 1.5) {
                hideBreakerTip();
                go(dx < 0 ? -1 : 1);
                return;
            }
            if (!moved) setTimeout(hideBreakerTip, 2500);
        });
    }

    function bindActivityCard() {
        var tabs = document.querySelectorAll("#arial-activity .tabs button");
        var i;
        for (i = 0; i < tabs.length; i += 1) {
            tabs[i].addEventListener("click", function () {
                var btn = this;
                var t = btn.getAttribute("data-tab") || "all";
                activityTab = t;
                var j;
                for (j = 0; j < tabs.length; j += 1) {
                    var on = tabs[j] === btn;
                    tabs[j].classList.toggle("on", on);
                    tabs[j].setAttribute("aria-selected", on ? "true" : "false");
                }
                renderActivity();
            });
        }
        var more = document.getElementById("activity-more");
        if (more) {
            more.addEventListener("click", function () {
                activityExpanded = !activityExpanded;
                renderActivity();
            });
        }
    }

    function startOlarmLive() {
        if (startOlarmLive._es) return;
        if (typeof EventSource === "undefined") return;
        try {
            var es = new EventSource(API + "/live");
            startOlarmLive._es = es;
            es.onerror = function () {
                if (es.readyState === 2) {
                    startOlarmLive._es = null;
                    setTimeout(startOlarmLive, 3000);
                }
            };
            es.onmessage = function (ev) {
                try {
                    var data = JSON.parse(ev.data || "{}");
                    if (data && data.device) applyPanelDevice(data.device);
                    if (data && data.activity && isLoggedIn()) applyActivityPayload(data.activity);
                } catch (err) {}
            };
        } catch (e2) {}
    }

    async function loadStatus() {
        if (currentSite().id !== SITE_ID) return;
        if (loadStatus._busy) return;
        loadStatus._busy = true;
        try {
            var res = await fetch(API + "/panel", { credentials: "same-origin", cache: "no-store" });
            var data = await res.json();
            if (!res.ok) {
                setLcdStatus(lastStatus || "Connecting", lastIssue);
                if (!lastStatus) setTimeout(loadStatus, 2000);
                return;
            }
            var hanse = data.device;
            if (!hanse) {
                setLcdStatus(lastStatus || "No Device", lastIssue);
                return;
            }
            applyPanelDevice(hanse);
        } catch (e) {
            setLcdStatus(lastStatus || "Connecting", lastIssue);
            if (!lastStatus) setTimeout(loadStatus, 2000);
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
        "7102": { name: "Amoroc", from: "Amoroc", logo: "/arial/users/amoroc.png?v=43", code: "7102" },
        "7777": { name: "Onguard", from: "Onguard", logo: "/arial/users/onguard.png?v=1", code: "7777" },
        "2640": { name: "Comnet", from: "Comnet", logo: "/arial/users/comnet.png?v=1", code: "2640" },
        "6114": { name: "Kevin", from: "Kevin", logo: null, code: "6114" },
        "2525": { name: "Bugsy", from: "Bugsy", logo: null, code: "2525" },
        "1111": { name: "Tim", from: "Tim", logo: null, code: "1111" }
    };

    function resolvedUser(user) {
        if (!user) return null;
        if (user.code && CODES[user.code]) return CODES[user.code];
        if (/comnet/i.test(String(user.name || user.from || user.logo || ""))) return CODES["2640"];
        if (/^kevin$/i.test(String(user.name || user.from || ""))) return CODES["6114"];
        if (/^bugsy$/i.test(String(user.name || user.from || ""))) return CODES["2525"];
        if (/^tim$/i.test(String(user.name || user.from || ""))) return CODES["1111"];
        if (/onguard/i.test(String(user.name || user.from || user.logo || ""))) return CODES["7777"];
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
        var below = document.querySelector(".arial-below");
        if (below) below.hidden = !on;
        var breakerCard = document.getElementById("arial-breaker");
        if (breakerCard) breakerCard.hidden = !SITE_TUYA;
        if (on) {
            restoreActivityStore();
            loadActivity();
            // Card is display:none until login, so charts can only size themselves now.
            if (SITE_TUYA) {
                initBreakerCharts();
                Object.keys(breakerCharts).forEach(function (k) { breakerCharts[k].resize(); });
                loadBreaker();
            }
        } else {
            saveActivityStore();
            activityRows = [];
        }
    }

    function logOut() {
        window.arialUser = null;
        pin = "";
        try { localStorage.removeItem("arialUser"); } catch (e) {}
        try { sessionStorage.removeItem("arialUser"); } catch (e) {}
        try { localStorage.removeItem(siteKey("arialSite")); } catch (e) {}
        siteId = SITE_ID;
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
        var nameEl = document.getElementById("lcd-user-name");
        if (!lcd || !img) return;
        if (user && user.logo) {
            img.removeAttribute("hidden");
            img.style.display = "";
            img.src = user.logo;
            img.alt = user.from || user.name || "";
            if (nameEl) { nameEl.hidden = true; nameEl.textContent = ""; }
            lcd.classList.add("logged-in");
        } else if (user && (user.name || user.from)) {
            // No company logo yet: the name stands in the logo slot.
            img.removeAttribute("src");
            img.src = "";
            img.alt = "";
            img.setAttribute("hidden", "");
            if (nameEl) { nameEl.textContent = user.from || user.name; nameEl.hidden = false; }
            lcd.classList.add("logged-in");
        } else {
            img.removeAttribute("src");
            img.src = "";
            img.alt = "";
            img.style.display = "";
            img.setAttribute("hidden", "");
            if (nameEl) { nameEl.hidden = true; nameEl.textContent = ""; }
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
            lcd.classList.remove("disarmed", "arming", "arming-fast", "zone-open", "hold-disarmed", "alarm");
            lcd.classList.add("armed");
        }
        setLed(document.getElementById("led-status"), "armed");
        syncArmToggle();
        fitLcdStatus();
        prependActivity("ARMED");
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
                lcdBusy.classList.remove("armed", "arming", "arming-fast", "hold-disarmed", "alarm");
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
            lcd.classList.remove("armed", "arming", "arming-fast", "zone-open", "hold-disarmed", "alarm");
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
        setWelcome("");
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

    function sendLiveAction(cmd, areaNum) {
        var user = resolvedUser(window.arialUser);
        if (!user || !user.code) {
            rejectNeedLogin();
            return Promise.resolve(false);
        }
        if (!currentSite().linked) {
            setWelcome("Not Linked", 2000);
            return Promise.resolve(false);
        }
        return fetch(API + "/keypad", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({ code: user.code, actionCmd: cmd, actionNum: areaNum || 1 })
        }).then(function (res) {
            return res.json().then(function (data) {
                if (!res.ok) {
                    setWelcome((data && data.detail) || "Failed", 2000);
                    return false;
                }
                if (data && data.device) applyPanelDevice(data.device);
                loadStatus();
                loadActivity();
                setTimeout(loadStatus, 400);
                setTimeout(loadActivity, 400);
                setTimeout(loadStatus, 1200);
                setTimeout(loadActivity, 1200);
                setTimeout(loadStatus, 2800);
                setTimeout(loadActivity, 2800);
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
        armSettled = false;
        exitCountStarted = false;
        pendingExitUntil = 0;
        armWaitSince = 0;
        longArmedBeep._done = false;
        exitClockFromApi = false;
        disarmPending = false;
        disarmNeedsStatus = false;
        startLocalExit(exitDelaySecs(window.arialDevice));
        persistExit();
        showArming(localExitLeft());
        unlockAudio();
        tone(1600, 0.14, 0.55);
        maybeExitBeeps();
        sendLiveAction("area-arm").then(function (ok) {
            if (!ok) {
                clearLocalExit();
                loadStatus();
                return;
            }
            var apiCd = deviceCountdown(window.arialDevice);
            if (apiCd > 10) syncLocalExitFromApi(apiCd);
            showArming(localExitLeft());
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
        var flash = openZoneIssues(window.arialDevice).length > 0;
        if (lcd) {
            lcd.classList.remove("armed", "arming", "arming-fast", "login-error", "alarm");
            lcd.classList.add("disarmed", "hold-disarmed");
            lcd.classList.toggle("zone-open", flash);
        }
        setLed(document.getElementById("led-status"), flash ? "disarmed flash" : "disarmed");
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
        prependActivity("DISARMED");
        sendLiveAction("area-disarm").then(function (ok) {
            if (!ok) {
                disarmPending = false;
                disarmNeedsStatus = false;
                loadStatus();
            }
        });
    }

    // ---- Partition keys (HOUSE = area 1, GARAGE = area 2) on multi-area panels ----
    var areaPending = {};   // areaNum -> { timer, until, key }

    function areaKeyFor(num) {
        return document.querySelector('.hot[data-key="' + AREA_KEYS[num - 1] + '"]');
    }

    function stopAreaPending(num) {
        var p = areaPending[num];
        if (!p) return;
        if (p.timer) clearInterval(p.timer);
        delete areaPending[num];
        var key = areaKeyFor(num);
        if (key) key.classList.remove("area-arming");
    }

    function startAreaPending(num) {
        stopAreaPending(num);
        var key = areaKeyFor(num);
        if (key) { key.classList.remove("area-disarmed", "area-notready"); key.classList.add("area-arming"); }
        var secs = exitDelaySecs(window.arialDevice);
        var until = Date.now() + secs * 1000;
        var p = { until: until, timer: null };
        p.timer = setInterval(function () {
            var left = Math.ceil((p.until - Date.now()) / 1000);
            if (left <= 0) { stopAreaPending(num); syncAreaKeys(window.arialDevice); loadStatus(); return; }
            unlockAudio();
            tone(left <= 7 ? 1900 : 1500, left <= 7 ? 0.08 : 0.06, 0.35);
            if (window.arialDevice) applyMultiAreaLcd(window.arialDevice);
        }, 1000);
        if (window.arialDevice) applyMultiAreaLcd(window.arialDevice);
        areaPending[num] = p;
    }

    function toggleArea(num) {
        if (!requireLogin()) return;
        var areas = window.arialDevice && Array.isArray(window.arialDevice.arialAreas) ? window.arialDevice.arialAreas : [];
        var area = areas[num - 1];
        if (!area) { setWelcome("No Area " + num, 1500); return; }
        var st = effectiveAreaState(num - 1, areas);
        var armed = st === "arm" || st === "stay" || st === "sleep" || st === "countdown";
        var key = areaKeyFor(num);
        unlockAudio();
        if (armed || areaPending[num]) {
            disarmBeep();
            stopAreaPending(num);
            setAreaOverride(num, "disarm");
            syncAreaKeys(window.arialDevice);
            if (key) { key.classList.remove("area-armed", "area-arming"); key.classList.add("area-disarmed"); }
            if (window.arialDevice) applyMultiAreaLcd(window.arialDevice);
            sendLiveAction("area-disarm", num).then(function (ok) { if (!ok) { delete areaOverride[num]; loadStatus(); } });
            return;
        }
        tone(1600, 0.14, 0.55);
        setAreaOverride(num, "countdown");
        startAreaPending(num);
        sendLiveAction("area-arm", num).then(function (ok) {
            if (!ok) { stopAreaPending(num); delete areaOverride[num]; syncAreaKeys(window.arialDevice); if (window.arialDevice) applyMultiAreaLcd(window.arialDevice); }
        });
    }

    function onKey(key) {
        if (!key) return;
        var now = Date.now();
        if (key === onKey._k && now - onKey._t < 280) return;
        onKey._k = key;
        onKey._t = now;
        var multiArea = window.arialDevice && Array.isArray(window.arialDevice.arialAreas) && window.arialDevice.arialAreas.length >= 2;
        if (multiArea && (key === "FORCE" || key === "ARM")) {
            if (!isLoggedIn()) { rejectNeedLogin(); saveClick(key); return; }
            toggleArea(key === "FORCE" ? 1 : 2);
            saveClick(key);
            if (typeof window.onArialKey === "function") window.onArialKey(key);
            return;
        }
        if (multiArea && key === "TOGGLE") {
            // Multi-partition panel: the lock has no function for now; each area key is its own lock.
            beep();
            saveClick(key);
            return;
        }
        var isArmed = panelLooksArmed(window.arialDevice);
        if (disarmPending && key === "TOGGLE") {
            saveClick(key);
            if (typeof window.onArialKey === "function") window.onArialKey(key);
            return;
        }
        if (key === "TOGGLE" && !isLoggedIn()) {
            rejectNeedLogin();
            saveClick(key);
            if (typeof window.onArialKey === "function") window.onArialKey(key);
            return;
        }
        if (key === "TOGGLE" && isArmed && isLoggedIn()) {
            unlockAudio();
            disarmBeep();
        }
        else if (key === "TOGGLE") { /* panel countdown + beeps */ }
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
        } else if (key === "TOGGLE") {
            if (isArmed) doDisarm();
            else doArm();
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

    // ---- LIGHTS key (was STAY): tap = popup, hold = all lights on ----
    var LIGHTS_DEVICE = "bf7f4a91ef39b11261xcua";
    var LIGHTS_HOLD_MS = 650;
    var lightsPress = null;
    var lightsPoll = null;
    var lightsState = {};

    function lightsOpen() {
        return !document.getElementById("lights-pop").hidden;
    }

    function renderLights(data) {
        var note = document.getElementById("lights-note");
        var rows = data && Array.isArray(data.switches) ? data.switches : [];
        var i;
        for (i = 0; i < rows.length; i += 1) {
            var code = rows[i].code;
            var on = rows[i].on;
            lightsState[code] = on;
            var btn = document.querySelector('#lights-grid .light-btn[data-switch="' + code + '"]');
            if (!btn) continue;
            btn.classList.remove("pending");
            btn.classList.toggle("on", on === true);
            btn.classList.toggle("unknown", on == null);
            var st = btn.querySelector(".light-state");
            if (st) st.textContent = on == null ? "—" : on ? "ON" : "OFF";
        }
        if (note) {
            if (data && data.online === false) { note.textContent = "Switch offline"; note.classList.add("fault"); }
            else if (data && !data.ok) { note.textContent = data.tuyaMsg || "No link"; note.classList.add("fault"); }
            else { note.textContent = ""; note.classList.remove("fault"); }
        }
    }

    async function loadLights() {
        if (loadLights._busy) return;
        loadLights._busy = true;
        try {
            var res = await fetch(API + "/tuya/lights?device_id=" + LIGHTS_DEVICE, { credentials: "same-origin", cache: "no-store" });
            renderLights(await res.json());
        } catch (e) {
            renderLights({ ok: false, tuyaMsg: "No link", switches: [] });
        } finally {
            loadLights._busy = false;
        }
    }

    async function setLight(target, value) {
        var user = window.arialUser;
        if (!user || !user.code) { rejectNeedLogin(); return; }
        var sel = target === "all" ? "#lights-grid .light-btn" : '#lights-grid .light-btn[data-switch="' + target + '"]';
        var btns = document.querySelectorAll(sel);
        var i;
        for (i = 0; i < btns.length; i += 1) btns[i].classList.add("pending");
        try {
            var res = await fetch(API + "/tuya/switch", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: user.code, device_id: LIGHTS_DEVICE, switch: target, value: !!value })
            });
            var data = await res.json();
            if (!res.ok) {
                renderLights({ ok: false, tuyaMsg: (data && data.detail) || "Switch failed", switches: [] });
                for (i = 0; i < btns.length; i += 1) btns[i].classList.remove("pending");
                return;
            }
            renderLights(data);
        } catch (e) {
            for (i = 0; i < btns.length; i += 1) btns[i].classList.remove("pending");
            renderLights({ ok: false, tuyaMsg: "No link", switches: [] });
        }
    }

    function openLights() {
        if (!isLoggedIn()) { rejectNeedLogin(); return; }
        if (!SITE_TUYA) { setWelcome("No lights here", 1800); return; }
        var pop = document.getElementById("lights-pop");
        if (!pop) return;
        pop.hidden = false;
        openLights._at = Date.now();
        loadLights();
        if (lightsPoll) clearInterval(lightsPoll);
        lightsPoll = setInterval(loadLights, 5000);
    }

    function closeLights() {
        var pop = document.getElementById("lights-pop");
        if (pop) pop.hidden = true;
        if (lightsPoll) clearInterval(lightsPoll);
        lightsPoll = null;
    }

    function bindLights() {
        var pop = document.getElementById("lights-pop");
        if (!pop) return;
        pop.addEventListener("click", function (ev) {
            // The key tap that opened us also emits a click on the overlay now under the finger; ignore it.
            if (Date.now() - (openLights._at || 0) < 400) return;
            if (ev.target === pop) closeLights();
        });
        document.getElementById("lights-close").addEventListener("click", closeLights);
        document.getElementById("lights-all-on").addEventListener("click", function () { setLight("all", true); });
        document.getElementById("lights-all-off").addEventListener("click", function () { setLight("all", false); });
        var grid = document.getElementById("lights-grid");
        grid.addEventListener("click", function (ev) {
            var btn = ev.target.closest(".light-btn");
            if (!btn) return;
            var code = btn.getAttribute("data-switch");
            setLight(code, !(lightsState[code] === true));
        });
        document.addEventListener("keydown", function (ev) {
            if (ev.key === "Escape" && lightsOpen()) closeLights();
        });
    }

    // Grouped-switch mode (Home for now): LIGHTS key drives a set of Tuya channels together and shows the live state.
    // Config: lights: { label, apiBase, targets: [{ device, code, name }] }  (legacy single form { device, switch } also accepted)
    var SINGLE_LIGHT = null;
    if (CFG.lights && Array.isArray(CFG.lights.targets) && CFG.lights.targets.length) {
        SINGLE_LIGHT = { label: CFG.lights.label, api: CFG.lights.apiBase || CFG.lights.api, targets: CFG.lights.targets };
    } else if (CFG.lights && CFG.lights.device) {
        SINGLE_LIGHT = { label: CFG.lights.label, api: CFG.lights.api, targets: [{ device: CFG.lights.device, code: CFG.lights.switch || "switch_1", name: CFG.lights.label }] };
    }
    var singleLightOn = null;          // true if any target is on, false if all known off, null unknown
    var singleLightStates = {};        // "device|code" -> bool

    function recomputeSingleLight() {
        var known = 0, on = 0;
        SINGLE_LIGHT.targets.forEach(function (t) {
            var v = singleLightStates[t.device + "|" + t.code];
            if (typeof v === "boolean") { known += 1; if (v) on += 1; }
        });
        singleLightOn = known ? on > 0 : null;
    }

    function renderSingleLight() {
        var lab = document.querySelector('.hot[data-key="STAY"] .key-label');
        if (!lab || !SINGLE_LIGHT) return;
        lab.classList.add("two-line");
        lab.textContent = "";
        var l1 = document.createElement("span"); l1.className = "kl-1"; l1.textContent = String(SINGLE_LIGHT.label || "Lights").toUpperCase();
        var l2 = document.createElement("span"); l2.className = "kl-2"; l2.textContent = singleLightOn == null ? "…" : (singleLightOn ? "On" : "Off");
        lab.appendChild(l1); lab.appendChild(l2);
        var key = lab.closest(".hot");
        if (key) {
            key.classList.toggle("light-on", singleLightOn === true);
            key.classList.toggle("light-off", singleLightOn === false);
            key.title = SINGLE_LIGHT.targets.map(function (t) {
                var v = singleLightStates[t.device + "|" + t.code];
                return (t.name || t.code) + ": " + (v == null ? "?" : v ? "on" : "off");
            }).join(" · ");
        }
    }

    async function loadSingleLight() {
        if (!SINGLE_LIGHT || loadSingleLight._busy) return;
        loadSingleLight._busy = true;
        try {
            var devices = {};
            SINGLE_LIGHT.targets.forEach(function (t) { devices[t.device] = true; });
            await Promise.all(Object.keys(devices).map(function (dev) {
                return fetch(String(SINGLE_LIGHT.api || API) + "/tuya/lights?device_id=" + dev, { credentials: "same-origin", cache: "no-store" })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        (data && data.switches || []).forEach(function (row) {
                            if (typeof row.on === "boolean") singleLightStates[dev + "|" + row.code] = row.on;
                        });
                    }).catch(function () {});
            }));
            recomputeSingleLight();
        } finally {
            loadSingleLight._busy = false;
            renderSingleLight();
        }
    }

    async function toggleSingleLight() {
        if (!isLoggedIn()) { rejectNeedLogin(); return; }
        var user = window.arialUser;
        var want = !(singleLightOn === true);
        var key = document.querySelector('.hot[data-key="STAY"]');
        if (key) key.classList.add("light-pending");
        try {
            await Promise.all(SINGLE_LIGHT.targets.map(function (t) {
                return fetch(String(SINGLE_LIGHT.api || API) + "/tuya/switch", {
                    method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ code: user.code, device_id: t.device, switch: t.code, value: want })
                }).then(function (res) { return res.json().then(function (data) {
                    if (!res.ok) { setWelcome((data && data.detail) || "Switch failed", 2000); return; }
                    (data && data.switches || []).forEach(function (row) {
                        if (typeof row.on === "boolean") singleLightStates[t.device + "|" + row.code] = row.on;
                    });
                }); }).catch(function () { setWelcome("No Link", 2000); });
            }));
            recomputeSingleLight();
        } finally {
            if (key) key.classList.remove("light-pending");
            renderSingleLight();
        }
    }

    if (SINGLE_LIGHT) {
        renderSingleLight();
        loadSingleLight();
        setInterval(loadSingleLight, 5000);
    }

    function lightsPressStart() {
        if (SINGLE_LIGHT) { unlockAudio(); beep(); toggleSingleLight(); return; }
        if (lightsPress && lightsPress.timer) clearTimeout(lightsPress.timer);
        lightsPress = { at: Date.now(), fired: false, timer: null };
        lightsPress.timer = setTimeout(function () {
            lightsPress.fired = true;
            if (!isLoggedIn()) { rejectNeedLogin(); return; }
            if (!SITE_TUYA) { setWelcome("No lights here", 1800); return; }
            openLights();
            setLight("all", true);
        }, LIGHTS_HOLD_MS);
    }

    function lightsPressEnd() {
        if (SINGLE_LIGHT) return;
        if (!lightsPress) return;
        var p = lightsPress;
        lightsPress = null;
        if (p.timer) clearTimeout(p.timer);
        if (!p.fired) openLights();
    }

    bindLights();

    var keypad = document.getElementById("pad-frame") || document.querySelector(".pad");
    keypad.addEventListener("pointerdown", function () {
        unlockAudio();
    }, true);
    keypad.addEventListener("pointerdown", function (ev) {
        var btn = ev.target.closest("[data-key]");
        if (!btn) return;
        unlockAudio();
        if (btn.getAttribute("data-key") === "STAY") lightsPressStart();
        onKey(btn.getAttribute("data-key"));
    });
    keypad.addEventListener("pointerup", function (ev) {
        var btn = ev.target.closest("[data-key]");
        if (btn && btn.getAttribute("data-key") === "STAY") lightsPressEnd();
        else if (lightsPress) { clearTimeout(lightsPress.timer); lightsPress = null; }
    });
    keypad.addEventListener("pointercancel", function () {
        if (lightsPress) { clearTimeout(lightsPress.timer); lightsPress = null; }
    });
    keypad.addEventListener("contextmenu", function (ev) {
        // Long-press on the LIGHTS key must not open the browser menu.
        var btn = ev.target.closest('[data-key="STAY"]');
        if (btn) ev.preventDefault();
    });
    keypad.addEventListener("pointerleave", function () {
        if (lightsPress) { clearTimeout(lightsPress.timer); lightsPress = null; }
    });

    try {
        var cached = JSON.parse(localStorage.getItem(siteKey("arialPanel")) || "null");
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
            if (/comnet/i.test(String(saved.name || saved.from || saved.logo || ""))) saved.code = "2640";
            if (/^kevin$/i.test(String(saved.name || saved.from || ""))) saved.code = "6114";
            if (/^bugsy$/i.test(String(saved.name || saved.from || ""))) saved.code = "2525";
            if (/^tim$/i.test(String(saved.name || saved.from || ""))) saved.code = "1111";
            if (/onguard/i.test(String(saved.name || saved.from || saved.logo || ""))) saved.code = "7777";
            if (!saved.code && /aerial/i.test(String(saved.logo || saved.name || ""))) saved.code = "7102";
            if (/aerial/i.test(String(saved.logo || ""))) saved.code = saved.code || "7102";
            if (!saved.code && saved.name === "Marc") saved.code = "7302";
            if (/amoroc/i.test(String(saved.name || saved.from || saved.logo || ""))) saved.code = "7102";
            if (saved.code && CODES[saved.code]) setLoggedIn(CODES[saved.code]);
        }
    } catch (e) {}

    try {
        var savedSite = localStorage.getItem(siteKey("arialSite"));
        if (savedSite === "tuys") {
            localStorage.setItem(siteKey("arialSite"), SITE_ID);
        }
    } catch (e) {}

    try {
        if (storeGet("arialArmSettled") === "1") {
            armSettled = true;
            holdSystemArmed();
        } else {
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
            settleArm();
        } else if (pending && !exitCountStarted) {
            armPending = true;
            startLocalExit(EXIT_DEFAULT);
            showArming(localExitLeft());
        }
        }
    } catch (e2) {}

    window.addEventListener("pageshow", kickExitAudio);
    function resumeLive() {
        // Phone came back from the home-screen icon / another tab: get the truth now and make sure the push channel is alive.
        kickExitAudio();
        loadStatus();
        loadActivity();
        loadBreaker();
        var es = startOlarmLive._es;
        if (es && es.readyState === 2) { startOlarmLive._es = null; startOlarmLive(); }
        else if (!es) startOlarmLive();
    }
    document.addEventListener("visibilitychange", function () {
        if (!document.hidden) resumeLive();
    });
    window.addEventListener("pageshow", resumeLive);
    window.addEventListener("focus", resumeLive);
    window.addEventListener("online", resumeLive);
    document.addEventListener("pointerdown", kickExitAudio, true);
    document.addEventListener("keydown", kickExitAudio, true);
    bindActivityCard();
    bindBreakerDay();
    tickTime();
    loadStatus();
    loadActivity();
    startOlarmLive();
    fitLcdStatus();
    window.addEventListener("resize", fitLcdStatus);
    setInterval(tickTime, 1000);
    setInterval(loadActivity, 3000);
    setInterval(loadBreaker, 3000);
    setInterval(loadStatus, 3000);   // fallback if the push channel is silent; served from the server snapshot

    // Auto-update: when a newer app.js is published, reload once the keypad is idle (never mid-countdown).
    function currentAssetVersion() {
        var tag = document.querySelector('script[src*="/arial/app.js?v="]');
        var m = tag && /app\.js\?v=(\d+)/.exec(tag.getAttribute("src") || "");
        return m ? m[1] : "";
    }
    function checkForNewVersion() {
        var mine = currentAssetVersion();
        if (!mine) return;
        fetch(location.pathname, { cache: "no-store", credentials: "same-origin" }).then(function (r) { return r.text(); }).then(function (html) {
            var m = /app\.js\?v=(\d+)/.exec(html || "");
            if (!m || m[1] === mine) return;
            var busy = Object.keys(typeof areaPending !== "undefined" ? areaPending : {}).length > 0 || localExitLeft() > 0 || armPending || disarmPending;
            if (busy) { setTimeout(checkForNewVersion, 15000); return; }
            location.reload();
        }).catch(function () {});
    }
    setInterval(checkForNewVersion, 120000);
    setTimeout(checkForNewVersion, 20000);
    setInterval(function () {
        if (localExitLeft() > 0 || disarmPending || armPending || panelIsExiting(window.arialDevice)) loadStatus();
    }, 1000);
    setInterval(syncArmToggle, 400);
    setInterval(function () {
        if (isMultiArea(window.arialDevice)) return;   // per-area LCD is driven by applyMultiAreaLcd
        if (disarmPending) return;
        if (armSettled) return;
        if (armPending && exitCountStarted && localExitLeft() === 0) {
            settleArm();
            return;
        }
        maybeExitBeeps();
        if (!(armPending || localExitLeft() > 0 || panelIsExiting(window.arialDevice))) return;
        showArming(localExitLeft());
    }, 250);
})();
