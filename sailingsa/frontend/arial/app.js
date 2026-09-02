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

    function applyLeds(device) {
        if (Date.now() < loginErrorUntil) {
            showLoginError(true);
            syncArmToggle();
            return;
        }
        setLed(document.getElementById("led-ac"), powerAcOk(device) ? "on" : "flash");
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

    function applyPanelDevice(hanse) {
        if (!hanse) return;
        var siteEl = document.getElementById("lcd-site");
        if (siteEl) siteEl.textContent = siteName(hanse);
        window.arialDevice = hanse;
        applyLeds(hanse);
        setActivityPower(hanse.arialPower);
        lastStatus = (document.getElementById("lcd-status-main") || {}).textContent || statusFromDevice(hanse);
        var st = areaState(hanse);
        if (isLoggedIn() && applyPanelDevice._area && applyPanelDevice._area !== st) {
            if (st === "disarm" || st === "notready") prependActivity("DISARMED");
            else if (st === "arm" || st === "stay" || st === "sleep") prependActivity("ARMED");
        }
        applyPanelDevice._area = st;
        loadStatus._area = st;
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

    var activityTab = "all";
    var activityExpanded = false;
    var activityRows = [];
    var activityLastKey = "";
    var activityChecksumLocal = "";
    var ACTIVITY_PREVIEW = 4;
    var ACTIVITY_KEEP_MS = 30 * 24 * 60 * 60 * 1000;
    var ACTIVITY_STORE = "arialActivity.hansekop";

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
                site: "hansekop",
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

    function renderActivity() {
        var body = document.getElementById("arial-activity-body");
        var more = document.getElementById("activity-more");
        if (!body) return;
        activityRows = tidyActivity(activityRows);
        var rows = activityRows.filter(function (r) { return !skipActivityRow(r); });
        if (activityTab !== "all") {
            rows = rows.filter(function (r) { return r.tab === activityTab; });
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
                t.textContent = r.time || "";
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
        if (currentSite().id !== "hansekop") return;
        if (loadActivity._busy) return;
        loadActivity._busy = true;
        try {
            var res = await fetch("/api/arial/activity", { credentials: "same-origin", cache: "no-store" });
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

    var BREAKER_STORE = "arialBreaker.hansekop";
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

    function breakerDialState(kind, value) {
        if (value == null || !isFinite(value)) return "";
        if (kind === "v") {
            if (value < 207 || value > 253) return "crit";
            if (value < 216 || value > 244) return "warn";
            return "ok";
        }
        if (kind === "a") {
            if (value >= 10) return "crit";
            if (value >= 9.5) return "warn";
            return "ok";
        }
        if (value >= 2300) return "crit";
        if (value >= 2200) return "warn";
        return "ok";
    }

    function setBreakerGauge(kind, value, min, max) {
        var pct = 0;
        if (value != null && max > min) pct = (value - min) / (max - min);
        if (pct < 0) pct = 0;
        if (pct > 1) pct = 1;
        var needle = document.getElementById("breaker-needle-" + kind);
        if (needle) needle.setAttribute("transform", "rotate(" + (pct * 180).toFixed(1) + " 50 50)");
        var arc = document.getElementById("breaker-arc-" + kind);
        if (arc) arc.setAttribute("stroke-dasharray", (value == null ? 0 : pct * 100).toFixed(1) + " 100");
        var dial = document.querySelector('#arial-breaker .breaker-dial[data-kind="' + kind + '"]');
        if (dial) {
            var state = breakerDialState(kind, value);
            if (state) dial.setAttribute("data-state", state);
            else dial.removeAttribute("data-state");
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
            if (kwh > 0.05) {
                breakerEnergy.hidden = true;
                if (row) row.hidden = true;
                saveBreakerStore();
                return;
            }
            breakerEnergy.midnightAddEle = kwh;
            breakerEnergy.midnightYmd = saYmdNow();
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

    function renderBreaker(data) {
        var stateEl = document.getElementById("breaker-state");
        var vEl = document.getElementById("breaker-v");
        var aEl = document.getElementById("breaker-a");
        var wEl = document.getElementById("breaker-w");
        var energyRow = document.getElementById("breaker-energy");
        if (!stateEl) return;
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
        setBreakerGauge("v", volts, 200, 253);
        setBreakerGauge("a", amps, 0, 11);
        setBreakerGauge("w", watts, 0, 2530);
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
        if (!isLoggedIn()) return;
        if (loadBreaker._busy) return;
        loadBreaker._busy = true;
        try {
            var res = await fetch("/api/arial/tuya/probe?device_id=bf90676b1341ecb34dse39", {
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
            var res = await fetch("/api/arial/tuya/energy?device_id=bf90676b1341ecb34dse39", {
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
        var max = 0;
        for (j = 0; j < 24; j += 1) if (day.hours[j] != null && day.hours[j] > max) max = day.hours[j];
        var y = 60;
        if (val != null && max > 0) y = 60 - (val / max) * 56;
        tip.style.left = x + "px";
        tip.style.top = Math.max(y - 4, 14) + "px";
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
        var max = 0;
        var i;
        for (i = 0; i < 24; i += 1) if (hours[i] != null && hours[i] > max) max = hours[i];
        if (empty) empty.hidden = !!max;
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
            var h = Math.max(1.5, (v / max) * 56);
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
            var es = new EventSource("/api/arial/live");
            startOlarmLive._es = es;
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
        "7102": { name: "Amoroc", from: "Amoroc", logo: "/arial/users/amoroc.png?v=43", code: "7102" },
        "7777": { name: "Onguard", from: "Onguard", logo: "/arial/users/onguard.png?v=1", code: "7777" },
        "2640": { name: "Comnet", from: "Comnet", logo: "/arial/users/comnet.png?v=1", code: "2640" }
    };

    function resolvedUser(user) {
        if (!user) return null;
        if (user.code && CODES[user.code]) return CODES[user.code];
        if (/comnet/i.test(String(user.name || user.from || user.logo || ""))) return CODES["2640"];
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
        if (on) {
            restoreActivityStore();
            loadActivity();
            loadBreaker();
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

    function onKey(key) {
        if (!key) return;
        var now = Date.now();
        if (key === onKey._k && now - onKey._t < 280) return;
        onKey._k = key;
        onKey._t = now;
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
            if (/comnet/i.test(String(saved.name || saved.from || saved.logo || ""))) saved.code = "2640";
            if (/onguard/i.test(String(saved.name || saved.from || saved.logo || ""))) saved.code = "7777";
            if (!saved.code && /aerial/i.test(String(saved.logo || saved.name || ""))) saved.code = "7102";
            if (/aerial/i.test(String(saved.logo || ""))) saved.code = saved.code || "7102";
            if (!saved.code && saved.name === "Marc") saved.code = "7302";
            if (/amoroc/i.test(String(saved.name || saved.from || saved.logo || ""))) saved.code = "7102";
            if (saved.code && CODES[saved.code]) setLoggedIn(CODES[saved.code]);
        }
    } catch (e) {}

    try {
        var savedSite = localStorage.getItem("arialSite");
        if (savedSite === "tuys") {
            localStorage.setItem("arialSite", "hansekop");
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
    document.addEventListener("visibilitychange", function () {
        if (!document.hidden) kickExitAudio();
    });
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
    setInterval(loadBreaker, 10000);
    setInterval(function () {
        if (localExitLeft() > 0 || disarmPending || armPending || panelIsExiting(window.arialDevice)) loadStatus();
    }, 1000);
    setInterval(syncArmToggle, 400);
    setInterval(function () {
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
